"""Paper 1, round-2 review: five data questions, answered in RELAY: lines only.

Usage:
    python -m scripts.pipeline.review.round2_questions <question>

Each question is one relay job (slurm_jobs/review/paper1_round2_questions.sbatch), because a
report keeps only its last 40 RELAY: lines. Every line is an aggregate: a curve value, a
count, an interval, a category label. No row, no patient id, no path. Nothing is written
to disk, and nothing is refit.

  curve             bge-small-en-v1.5 / bge-en-icl plain cosine (alpha 1), ROC AUC at k
                    from 25,000 to the whole pool in steps of 250, and at the curve's
                    lowest point in that range. Each k is recomputed in float64 beside the
                    float32 the sweep stores, with how many test patients' k-th and
                    (k+1)-th similarities tie; at the lowest point and at k = 25,000 also
                    the risks' spread and distinct-value count and how many patients'
                    neighbourhoods reach a non-positive similarity. Raw values only: why
                    the curve drops near k = 30,000 is the owner's reading, not this
                    module's. Runs on the encoder .env names; the recipe calls it once per
                    encoder.
  subgroup_race     the 10 White-minus-non-White contrasts with their bootstrap 95% CIs and
                    BH-adjusted P, the largest male-minus-female contrast, and the two
                    retrieval arms' "Severe vs rest" contrasts.
  subgroup_bh       every contrast surviving BH adjustment (Table S12), each with its CI.
  operating_point   S12.1: the Youden J operating points of embedded logistic regression and
                    feature-vector XGBoost, each metric with its bootstrap 95% CI (the same
                    resamples and fixed threshold as the CI-bearing confusion matrices).
  recurrence_level  what the MDD recurrence level of Table S11's unnamed n = 32 row is,
                    and how many patients in the cohort carry it.
  calibration_bins  Table S4's retrieval rows (binned calibration slope and intercept)
                    recomputed on the 10 equal-count bins Figure S5 draws, beside the
                    equal-width fit the table prints, each with a bootstrap 95% CI.
"""

import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

from scripts.shared.plots import (
    assign_calibration_bins,
    bootstrap_sample_indices,
    calibration_bin_edges,
    calibration_points,
    youden_operating_point,
)

# The relay keeps at most this many characters of a line; a little under, for the prefix.
MAX_LINE = 190
# How many curve values share one line.
VALUES_PER_LINE = 5

# The curve question's grid.
CURVE_START = 25_000
CURVE_STEP = 250
CURVE_ALPHA = 1.0
CURVE_METRIC = "plain"

# Subgroup contrast keys, as run_subgroups writes them.
RACE_CONTRAST = "white_minus_non_white"
SEX_CONTRAST = "male_minus_female"
SEVERE_CONTRAST = "mdd_severity:Severe_minus_rest"
RETRIEVAL_ARM = "KNN"

# The two S12.1 models.
OPERATING_POINTS = (("EMBEDDED", "logistic_regression"), ("FEATURE", "xgboost"))

# Table S4's retrieval rows: (label, best-k prediction file).
RETRIEVAL_FILES = (("weighted", "best_k_predictions_alpha1.csv"),
                   ("plain", "best_k_predictions_alpha1_plain.csv"),
                   ("random", "best_k_predictions_random.csv"))

_SAFE_LABEL = re.compile(r"^[A-Za-z0-9 ,/()+.-]{1,40}$")


def relay(text: str) -> None:
    """Print one RELAY: line, cut to MAX_LINE characters."""
    print(f"RELAY: {text}"[:MAX_LINE + len("RELAY: ")], flush=True)


def fmt_interval(value: float, low: float, high: float, digits: int = 3, signed: bool = False) -> str:
    """value (low to high), at a fixed number of decimals."""
    spec = f"{'+' if signed else ''}.{digits}f"
    return f"{value:{spec}} ({low:{spec}} to {high:{spec}})"


def pack(prefix: str, items: list[str], per_line: int = VALUES_PER_LINE) -> list[str]:
    """Group items into lines that each start with prefix."""
    return [f"{prefix} " + " ".join(items[i:i + per_line]) for i in range(0, len(items), per_line)]


def describe_level(value) -> str:
    """A category label fit for a relay line: the label itself when it is a plain short
    word or phrase, otherwise what kind of value it is."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "<missing>"
    text = str(value)
    if text == "":
        return "<empty string>"
    if not text.strip():
        return "<blank>"
    return text if _SAFE_LABEL.match(text) else f"<other, {len(text)} characters>"


# ---------------------------------------------------------------------------
# curve
# ---------------------------------------------------------------------------
def curve_grid(n_pool: int, trough_k: int = None, start: int = CURVE_START, step: int = CURVE_STEP) -> np.ndarray:
    """k from start to n_pool in steps, plus n_pool itself and the trough, sorted."""
    ks = set(range(start, n_pool + 1, step)) | {n_pool}
    if trough_k is not None:
        ks.add(int(trough_k))
    return np.array(sorted(k for k in ks if 1 <= k <= n_pool), dtype=int)


def risks_and_kth_similarity(anchors: np.ndarray, pool: np.ndarray, pool_labels: np.ndarray,
                             ks: np.ndarray, alpha: float, fallback_risk: float,
                             block: int = 256) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Float64 risk at each k, ranked and weighted as the sweep ranks and weights them,
    each anchor's k-th largest similarity, and whether it ties the (k+1)-th.

    The risk equals neighbor_count_sweep.risk_at_counts at the same k. The k-th similarity
    says whether non-positive cosines (weight zero after clipping) have entered the
    neighbourhood. A tie between the k-th and (k+1)-th similarity means the cut at k falls
    inside a run of equal scores, so which of them is in the neighbourhood is set by the
    sort's order, not by similarity. At k equal to the whole pool there is no (k+1)-th, and
    no tie.

    Returns:
        tuple[np.ndarray, np.ndarray, np.ndarray]: (risk, kth_similarity, tied_at_cut),
            each (n_anchors, len(ks)); tied_at_cut is boolean.
    """
    from scripts.pipeline.predictions.importance_weighted_knn import neighbour_weights
    labels_all = pool_labels.astype(np.float64)
    n_pool = pool.shape[0]
    width = min(int(ks.max()) + 1, n_pool)
    has_next = ks < n_pool
    risk = np.empty((anchors.shape[0], ks.size))
    kth = np.empty((anchors.shape[0], ks.size))
    tied = np.zeros((anchors.shape[0], ks.size), dtype=bool)
    for start in range(0, anchors.shape[0], block):
        stop = min(start + block, anchors.shape[0])
        similarities = anchors[start:stop] @ pool.T
        order = np.argsort(-similarities, axis=1, kind='stable')[:, :width]
        nearest = np.take_along_axis(similarities, order, axis=1).astype(np.float64)
        weights = neighbour_weights(nearest, alpha)
        numerator = np.cumsum(weights * labels_all[order], axis=1)[:, ks - 1]
        denominator = np.cumsum(weights, axis=1)[:, ks - 1]
        out = np.full(numerator.shape, fallback_risk)
        np.divide(numerator, denominator, out=out, where=denominator > 0)
        risk[start:stop] = out
        kth[start:stop] = nearest[:, ks - 1]
        tied[start:stop, has_next] = nearest[:, ks[has_next] - 1] == nearest[:, ks[has_next]]
    return risk, kth, tied


def curve_diagnostics(y_true: np.ndarray, risk: np.ndarray, kth: np.ndarray,
                      tied: np.ndarray) -> pd.DataFrame:
    """Per k, raw values only: the AUC in float64 and in float32, the risks' standard
    deviation and count of distinct float32 values, the count of anchors whose
    neighbourhood reaches a non-positive similarity, and the count whose k-th and
    (k+1)-th similarities tie.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        risk (np.ndarray): Float64 risks, shape (n, n_k).
        kth (np.ndarray): k-th largest similarity, shape (n, n_k).
        tied (np.ndarray): Boolean, k-th similarity equal to the (k+1)-th, shape (n, n_k).

    Returns:
        pd.DataFrame: auc64, auc32, risk_sd, distinct_risks, nonpositive_anchors,
            tied_anchors, one row per k.
    """
    from scripts.pipeline.predictions.neighbor_count_sweep import roc_auc_by_column
    risk32 = risk.astype(np.float32)
    return pd.DataFrame({
        "auc64": roc_auc_by_column(y_true, risk),
        "auc32": roc_auc_by_column(y_true, risk32),
        "risk_sd": risk.std(axis=0),
        "distinct_risks": [np.unique(risk32[:, j]).size for j in range(risk.shape[1])],
        "nonpositive_anchors": (kth <= 0).sum(axis=0),
        "tied_anchors": tied.sum(axis=0),
    })


def curve_lines(encoder: str, ks: np.ndarray, sweep_auc: np.ndarray, diagnostics: pd.DataFrame,
                n_anchors: int, n_pool: int) -> list[str]:
    """Every RELAY line the curve question prints for one encoder, about a dozen.

    Raw values only, and no verdict: the lowest float64 AUC in the range and the first k
    are printed in full, side by side, for the owner to read.
    """
    lines = [f"curve {encoder} {CURVE_METRIC} alpha {CURVE_ALPHA:g}: {n_anchors} test patients, "
             f"pool {n_pool}; k:sweep AUC/float64 AUC/patients whose k-th and (k+1)-th similarity tie"]
    items = [f"{k}:{s:.4f}/{a:.4f}/{int(t)}"
             for k, s, a, t in zip(ks, sweep_auc, diagnostics.auc64, diagnostics.tied_anchors)]
    lines += pack(f"curve {encoder}", items)
    in_range = diagnostics.reset_index(drop=True)
    trough_i = int(np.nanargmin(in_range.auc64.to_numpy()))
    start_i = int(np.flatnonzero(ks == ks.min())[0])
    for name, i in (("lowest", trough_i), ("start", start_i)):
        row = in_range.iloc[i]
        lines.append(f"curve {encoder} {name} k {ks[i]}: AUC64 {row['auc64']:.4f} AUC32 {row['auc32']:.4f} "
                     f"risk sd {row['risk_sd']:.2e} distinct risks {int(row['distinct_risks'])} "
                     f"non-positive k-th similarity {int(row['nonpositive_anchors'])} "
                     f"tied {int(row['tied_anchors'])}")
    return lines


def answer_curve() -> list[str]:
    """The curve question for the encoder .env names."""
    from scripts.pipeline.predictions.create_train_test_split import create_train_test_split
    from scripts.pipeline.predictions.importance_weighted_knn import (
        candidate_pool_ids, load_raw_embeddings, to_plain_space)
    from scripts.pipeline.predictions.neighbor_count_sweep import SWEEP_DIR
    from scripts.shared.utils import load_trd_set

    encoder = os.environ["EMBEDDER_MODEL_NAME"]
    test_ids = create_train_test_split()[1]
    anchor_ids = sorted(test_ids)
    pool_ids = candidate_pool_ids(exclude_ids=test_ids)
    trd = load_trd_set()
    y = np.array([1 if pid in trd else 0 for pid in anchor_ids])
    pool_labels = np.array([1 if pid in trd else 0 for pid in pool_ids], dtype=np.float64)
    curve = pd.read_csv(SWEEP_DIR / "sweep_curve.csv")
    curve = curve[(curve.metric == CURVE_METRIC) & (curve.alpha == CURVE_ALPHA)].set_index("n_neighbors").roc_auc
    tail = curve[curve.index >= CURVE_START]
    ks = curve_grid(len(pool_ids), int(tail.idxmin()) if len(tail) else None)
    anchors = to_plain_space(load_raw_embeddings(anchor_ids))
    pool = to_plain_space(load_raw_embeddings(pool_ids))
    risk, kth, tied = risks_and_kth_similarity(anchors, pool, pool_labels, ks, CURVE_ALPHA,
                                               float(pool_labels.mean()))
    diagnostics = curve_diagnostics(y, risk, kth, tied)
    return curve_lines(encoder, ks, curve.reindex(ks).to_numpy(), diagnostics, len(anchor_ids), len(pool_ids))


# ---------------------------------------------------------------------------
# subgroups
# ---------------------------------------------------------------------------
def contrast_line(row: pd.Series, tag: str) -> str:
    """One contrast: arm, model, contrast, delta with CI, raw and BH P."""
    return (f"{tag} {row['representation']} {row['model']} {row['contrast']}: "
            f"{fmt_interval(row['delta_roc'], row['delta_ci_low'], row['delta_ci_high'], signed=True)} "
            f"P {row['p_value']:.3f} BH {row['p_bh']:.3f}")


def subgroup_race_lines(contrasts: pd.DataFrame) -> list[str]:
    """The race contrasts, the largest sex contrast, and the retrieval Severe contrasts."""
    race = contrasts[contrasts.contrast == RACE_CONTRAST].sort_values("delta_roc")
    lines = [f"race {len(race)} White-minus-non-White contrasts, lowest to highest delta"]
    lines += [contrast_line(row, "race") for _, row in race.iterrows()]
    sex = contrasts[contrasts.contrast == SEX_CONTRAST]
    if len(sex):
        lines.append(contrast_line(sex.loc[sex.delta_roc.abs().idxmax()], "sex largest |delta|"))
    severe = contrasts[(contrasts.contrast == SEVERE_CONTRAST) & (contrasts.representation == RETRIEVAL_ARM)]
    lines += [contrast_line(row, "severe") for _, row in severe.iterrows()]
    return lines


def subgroup_bh_lines(contrasts: pd.DataFrame) -> list[str]:
    """Every contrast surviving BH adjustment, grouped as Table S12 groups them."""
    surviving = contrasts[contrasts.survives_bh.astype(bool)].sort_values(
        ["contrast", "representation", "delta_roc"])
    lines = [f"bh {len(surviving)} of {len(contrasts)} contrasts survive"]
    lines += [contrast_line(row, "bh") for _, row in surviving.iterrows()]
    return lines


def load_contrasts() -> pd.DataFrame:
    from scripts.pipeline.review.subgroups.core import subgroup_dir
    return pd.read_csv(subgroup_dir() / "subgroup_contrasts.csv")


# ---------------------------------------------------------------------------
# operating point
# ---------------------------------------------------------------------------
def operating_point_lines(label: str, y_true: np.ndarray, y_prob: np.ndarray) -> list[str]:
    """The Youden J operating point, its counts, and every metric with its bootstrap CI."""
    point = youden_operating_point(y_true, y_prob, bootstrap=True)
    (tn, fp), (fn, tp) = point["confusion_matrix"]
    metrics = " ".join(
        f"{name} {fmt_interval(point[name]['value'], point[name]['ci_low'], point[name]['ci_high'])}"
        for name in ("sensitivity", "specificity"))
    others = " ".join(
        f"{name} {fmt_interval(point[name]['value'], point[name]['ci_low'], point[name]['ci_high'], digits=2)}"
        for name in ("f_score", "positive_likelihood_ratio", "negative_likelihood_ratio"))
    return [f"op {label}: threshold {point['threshold']:.3f}, TP {tp} FN {fn} FP {fp} TN {tn}",
            f"op {label}: {metrics}",
            f"op {label}: {others}"]


def answer_operating_point() -> list[str]:
    results = Path(os.environ["RESULTS_DIR"])
    lines = []
    for source, model in OPERATING_POINTS:
        frame = pd.read_parquet(results / f"test_predictions_{source}.parquet")
        lines += operating_point_lines(f"{source} {model}", frame["true_label"].to_numpy().astype(int),
                                       frame[model].to_numpy().astype(float))
    return lines


# ---------------------------------------------------------------------------
# recurrence level
# ---------------------------------------------------------------------------
def recurrence_lines(performance: pd.DataFrame, cohort_levels: pd.Series, severity_of_unnamed: pd.Series) -> list[str]:
    """Each MDD recurrence group of the subgroup tables, and the cohort's counts by level.

    Args:
        performance (pd.DataFrame): subgroup_performance.csv.
        cohort_levels (pd.Series): The feature table's mdd_recurrence column.
        severity_of_unnamed (pd.Series): mdd_severity of the cohort patients whose
            recurrence is the empty string.
    """
    lines = []
    groups = performance[performance.group.astype(str).str.startswith("mdd_recurrence:")]
    for group, rows in groups.groupby("group"):
        level = group.split(":", 1)[1]
        lines.append(f"recurrence test group {describe_level(level)}: n {int(rows.n.iloc[0])} "
                     f"events {int(rows.n_events.iloc[0])}")
    counts = cohort_levels.map(describe_level).value_counts()
    lines.append("recurrence cohort " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    if len(severity_of_unnamed):
        severity = severity_of_unnamed.map(describe_level).value_counts()
        lines.append("recurrence empty-level severity " + ", ".join(f"{k} {v}" for k, v in severity.items()))
    return lines


def answer_recurrence_level() -> list[str]:
    from scripts.pipeline.review.subgroups.core import subgroup_dir
    performance = pd.read_csv(subgroup_dir() / "subgroup_performance.csv", keep_default_na=False)
    table = pd.read_parquet(Path(os.environ["FEATURE_DATAFRAME_PATH"]),
                            columns=["mdd_recurrence", "mdd_severity"])
    unnamed = table[table.mdd_recurrence.astype(object).eq("")]
    return recurrence_lines(performance, table.mdd_recurrence, unnamed.mdd_severity)


# ---------------------------------------------------------------------------
# calibration bins
# ---------------------------------------------------------------------------
# The equal-count fit is kept because its bins are exactly the ones Figure S5 C-E draws:
# best_k_panels.draw_arm calls plots.plot_calibration with strategy "quantile" on these
# same three best-k prediction files (best_k_panels.ARMS), and plot_calibration cuts its
# edges with calibration_bin_edges on the full predictions, assigns patients with
# assign_calibration_bins and averages with calibration_points, all three of which are
# what binned_line calls here. The bootstrap holds those edges fixed in every draw, as
# plots.bootstrap_calibration_band does, over the same seeded bootstrap_sample_indices.
# tests/test_round2_questions.py checks the bins against plot_calibration's own table.
def binned_points(y_true: np.ndarray, y_prob: np.ndarray, edges: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean predicted, observed fraction and count per bin on fixed edges, as plot_calibration bins them."""
    n_bins = len(edges) - 1
    return calibration_points(y_true, y_prob, assign_calibration_bins(y_prob, edges), n_bins)


def binned_line(y_true: np.ndarray, y_prob: np.ndarray, edges: np.ndarray) -> tuple[float, float, int]:
    """Unweighted least-squares line of observed on mean predicted, over non-empty bins.

    The fit compute_metrics makes on its equal-width bins, made on any fixed edges.

    Returns:
        tuple[float, float, int]: (slope, intercept, non-empty bins); nan slope and
            intercept with fewer than 2 bins.
    """
    predicted, observed, counts = binned_points(y_true, y_prob, edges)
    drawn = counts > 0
    if drawn.sum() < 2:
        return float("nan"), float("nan"), int(drawn.sum())
    slope, intercept = np.polyfit(predicted[drawn], observed[drawn], 1)
    return float(slope), float(intercept), int(drawn.sum())


def bootstrap_binned_line(y_true: np.ndarray, y_prob: np.ndarray, edges: np.ndarray,
                          sample_indices: np.ndarray) -> dict:
    """binned_line with a percentile bootstrap 95% CI, the edges held fixed in every draw.

    Returns:
        dict: slope and intercept as {value, ci_low, ci_high}, bins (point), and
            draws_used and draws_with_other_bin_count. With no draw holding 2 non-empty
            bins the interval is nan.
    """
    slope, intercept, bins = binned_line(y_true, y_prob, edges)
    draws = np.array([binned_line(y_true[rows], y_prob[rows], edges) for rows in sample_indices])
    usable = ~np.isnan(draws[:, 0])
    out = {"bins": bins, "draws_used": int(usable.sum()),
           "draws_with_other_bin_count": int((draws[:, 2] != bins).sum())}
    for index, (name, value) in enumerate((("slope", slope), ("intercept", intercept))):
        low, high = np.percentile(draws[usable, index], [2.5, 97.5]) if usable.any() else (np.nan, np.nan)
        out[name] = {"value": value, "ci_low": float(low), "ci_high": float(high)}
    return out


def calibration_lines(label: str, y_true: np.ndarray, y_prob: np.ndarray) -> list[str]:
    """Equal-width (as Table S4) and equal-count (as Figure S5) fits for one arm.

    Both fits are printed for every arm. Where fewer than 2 bins hold patients no line
    exists, and the line says so with the bin count rather than printing a slope.
    """
    indices = bootstrap_sample_indices(len(y_true))
    lines = [f"cal {label}: predicted risk {y_prob.min():.3f} to {y_prob.max():.3f}"]
    for name, strategy in (("equal-width", "uniform"), ("equal-count", "quantile")):
        edges = calibration_bin_edges(y_prob, strategy)
        slope, _, bins = binned_line(y_true, y_prob, edges)
        if np.isnan(slope):
            lines.append(f"cal {label} {name} {bins} non-empty bin{'s' if bins != 1 else ''}: no line")
            continue
        fit = bootstrap_binned_line(y_true, y_prob, edges, indices)
        lines.append(
            f"cal {label} {name} {fit['bins']} bins: slope "
            f"{fmt_interval(fit['slope']['value'], fit['slope']['ci_low'], fit['slope']['ci_high'], digits=2)} "
            f"intercept {fmt_interval(fit['intercept']['value'], fit['intercept']['ci_low'], fit['intercept']['ci_high'], digits=2, signed=True)} "
            f"draws {fit['draws_used']}, other bin count {fit['draws_with_other_bin_count']}")
    return lines


def answer_calibration_bins() -> list[str]:
    sweep = Path(os.environ["RESULTS_DIR"]) / "neighbor_count_sweep"
    lines = []
    for label, name in RETRIEVAL_FILES:
        frame = pd.read_csv(sweep / name)
        lines += calibration_lines(label, frame.true_label.to_numpy().astype(int),
                                   frame.predicted_risk.to_numpy().astype(float))
    return lines


ANSWERS = {
    "curve": answer_curve,
    "subgroup_race": lambda: subgroup_race_lines(load_contrasts()),
    "subgroup_bh": lambda: subgroup_bh_lines(load_contrasts()),
    "operating_point": answer_operating_point,
    "recurrence_level": answer_recurrence_level,
    "calibration_bins": answer_calibration_bins,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ANSWERS:
        relay(f"round2 question refused: expected one of {', '.join(ANSWERS)}")
        return 2
    for line in ANSWERS[argv[0]]():
        relay(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
