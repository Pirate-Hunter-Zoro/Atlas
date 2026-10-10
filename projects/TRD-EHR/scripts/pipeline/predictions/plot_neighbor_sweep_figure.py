"""The manuscript's retrieval figure, and the paired contrasts its text quotes.

`neighbor_count_sweep` draws a working figure: six curves, twelve legend entries, one
per metric and sharpening exponent. The paper needs three curves, because sharpening
moves nothing (alpha 1, 2 and 5 agree to three decimals) and the question is only
whether retrieval reaches a trained classifier at any neighborhood size. This script
draws that figure from the sweep's own outputs and refits nothing:

  * one curve per cosine metric at alpha 1, logistic-regression-weighted and plain,
    with the bootstrap 95% band from sweep_intervals.csv;
  * the random-neighbor arm with uniform weights, its mean AUC across draws at every
    k inside the band of the 2.5th to 97.5th percentile across draws, from
    random_neighbour_curve.csv;
  * a point at each arm's best k, the k its panels (best_k_panels) are drawn at, whose
    value and interval are printed in that arm's legend entry rather than beside the
    point, where a label lands on whichever curve passes it;
  * horizontal lines at the two leading trained classifiers, each with its 95% band.

It runs once per encoder, on that encoder's RESULTS_DIR. The manuscript does not place
these PNGs: Figure 4 is one composite of all four encoders' panels sharing one legend
row, drawn after every sweep by plot_cross_embedder_retrieval with draw_curves below,
so the composite and each encoder's own PNG draw the same curves from the same files.

WHERE EACH CLASSIFIER LINE COMES FROM. Where a classifier's per-patient test
predictions (test_predictions_{EMBEDDED,FEATURE}.parquet) sit in RESULTS_DIR, its line
is bootstrapped over the same resamples of test patients as the retrieval contrasts,
and the retrieval-minus-classifier contrast is written. Only the primary encoder has
those files. Elsewhere the line is read from classical_ml_results_{source}.json, the
AUC and bootstrap CI classical_ml recorded, and no contrast against that classifier is
written. Feature-vector XGBoost does not depend on the encoder, so its line is read
from FEATURE_RESULTS_DIR when that is set; the recipe points it at the primary
encoder, which keeps that line the same in every panel.

It also writes the contrasts the Results paragraph quotes, so every number there is
on disk: the best retrieval predictions against each leading classifier whose
per-patient predictions exist, and the logistic-regression-weighted metric against
plain cosine, paired over resampled test patients seeded off SEED; and each cosine
metric against the random arm, each at its own best k, whose interval also spans the
1,000 random draws (delta_against_random_draws). Best k is chosen on those same
patients, so every best-k number is optimistic.

Outputs:
    RESULTS_DIR/neighbor_count_sweep/neighbor_count_sweep_manuscript.png
    RESULTS_DIR/neighbor_count_sweep/retrieval_paired_deltas.json
"""

import os
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

from dotenv import load_dotenv
load_dotenv()

from scripts.shared.plots import bootstrap_sample_indices

SWEEP_DIR_NAME = "neighbor_count_sweep"
FIGURE_NAME = "neighbor_count_sweep_manuscript.png"
DELTAS_NAME = "retrieval_paired_deltas.json"
FIGURE_DPI = 300

# The exponent the figure draws. Any of the three gives the same picture.
ALPHA = 1.0

METRIC_DISPLAY = {
    "weighted": "Logistic-regression-weighted cosine",
    "plain":    "Plain cosine",
    "random":   "Random neighbors, uniform weights",
}
# Categorical slots 1, 2 and 3 of the validated default palette, in fixed order; the
# first three validate all-pairs for colour-vision deficiency.
METRIC_COLOR = {"weighted": "#2a78d6", "plain": "#eb6834", "random": "#1baf7a"}

# Type sizes in points on a FIGURE_SIZE canvas. The saved PNG is about 7.5in wide with
# its legend, so placed at 6in every size shrinks by about 0.8.
FIGURE_SIZE = (7.0, 6.6)
# The plot over the legend's own row: three two-line arm entries and two reference lines.
LEGEND_ROW_RATIOS = (3.2, 1.9)
FONT_SIZES = {"tick": 13, "label": 14, "legend": 12}

X_LABEL = "Number of neighbors, k (log scale)"
Y_LABEL = "Test-set ROC AUC"
# The classifier lines, in REFERENCES order.
REFERENCE_COLOR = "#555555"
REFERENCE_STYLES = (":", "--")

# What each arm's interval is called in its legend entry. The cosine arms are bootstrapped
# over test patients; the random arm's band is the spread across draws, which the paper
# never calls a 95% CI.
INTERVAL_NAME = {"weighted": "95% CI", "plain": "95% CI",
                 "random": "2.5th–97.5th percentile of draws"}

# The two leading trained classifiers, as (label, representation, model column, shared).
# A shared classifier does not depend on the encoder, so one copy of it serves every
# encoder's panel (FEATURE_RESULTS_DIR).
REFERENCES = (
    ("EMBEDDED logistic regression", "EMBEDDED", "logistic_regression", False),
    ("FEATURE XGBoost",              "FEATURE",  "xgboost",             True),
)

# Which best-k prediction file stands for each retrieval arm in the paired contrasts.
# alpha 2 holds the maximum over every k and exponent; alpha 1 is the pair the metric
# contrast is read on, each metric at its own best k.
BEST_RETRIEVAL = "best_k_predictions_alpha2.csv"
METRIC_PAIR = {
    "weighted": "best_k_predictions_alpha1.csv",
    "plain":    "best_k_predictions_alpha1_plain.csv",
}
# The random arm's curve across draws.
RANDOM_CURVE = "random_neighbour_curve.csv"
# Every draw's AUC at the random arm's best k, from neighbor_count_sweep.
RANDOM_DRAWS_AT_BEST = "random_draw_aucs_at_best_k.csv"


def classifier_source(results_dir: Path, source: str, shared: bool) -> tuple[str, Path]:
    """Where one classifier line is read from: per-patient predictions, or a summary.

    Args:
        results_dir (Path): RESULTS_DIR for the active encoder/judge pair.
        source (str): EMBEDDED or FEATURE.
        shared (bool): True for a classifier that does not depend on the encoder; it is
            read from FEATURE_RESULTS_DIR when that is set.

    Returns:
        tuple[str, Path]: ("predictions", the parquet) when the per-patient test
            predictions are this RESULTS_DIR's own and on disk, otherwise ("summary",
            the classical_ml_results JSON the line is read from).
    """
    home = results_dir
    if shared and os.environ.get("FEATURE_RESULTS_DIR"):
        home = Path(os.environ["FEATURE_RESULTS_DIR"])
    parquet = home / f"test_predictions_{source}.parquet"
    if home.resolve() == results_dir.resolve() and parquet.exists():
        return "predictions", parquet
    return "summary", home / f"classical_ml_results_{source}.json"


def summary_line(path: Path, model: str) -> tuple:
    """A classifier's test ROC AUC and its bootstrap CI, as classical_ml recorded them.

    Args:
        path (Path): classical_ml_results_{source}.json.
        model (str): The model key in it, e.g. logistic_regression.

    Returns:
        tuple: (auc, ci_low, ci_high).
    """
    if not path.exists():
        raise FileNotFoundError(f"{path.name} is absent: no classifier line to draw.")
    entry = json.loads(path.read_text())[model]
    return (float(entry["roc_score"]), float(entry["roc_score_ci_low"]),
            float(entry["roc_score_ci_high"]))


def load_predictions(results_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    """Join the retrieval held-out predictions, and this encoder's per-patient classifier ones, on test patient.

    Args:
        results_dir (Path): RESULTS_DIR for the active encoder/judge pair.

    Returns:
        tuple[pd.DataFrame, list[str]]: One row per test patient: true_label,
            best_retrieval, weighted, plain, and one column per reference classifier
            whose per-patient predictions are in RESULTS_DIR; and those classifiers'
            labels, the ones a paired contrast can be read against.
    """
    sweep_dir = results_dir / SWEEP_DIR_NAME
    frame = pd.read_csv(sweep_dir / BEST_RETRIEVAL).rename(
        columns={"predicted_risk": "best_retrieval"})[["anchor_patient_id", "true_label", "best_retrieval"]]
    for metric, name in METRIC_PAIR.items():
        other = pd.read_csv(sweep_dir / name)[["anchor_patient_id", "predicted_risk"]]
        frame = frame.merge(other.rename(columns={"predicted_risk": metric}),
                            on="anchor_patient_id", validate="one_to_one")
    paired = []
    for label, source, model, shared in REFERENCES:
        kind, path = classifier_source(results_dir, source, shared)
        if kind != "predictions":
            continue
        classifier = pd.read_parquet(path)
        classifier = classifier[["patient_id", model]].rename(
            columns={"patient_id": "anchor_patient_id", model: label})
        frame = frame.merge(classifier, on="anchor_patient_id", validate="one_to_one")
        paired.append(label)
    return frame, paired


def paired_delta(y_true: np.ndarray, a: np.ndarray, b: np.ndarray,
                 sample_indices: np.ndarray) -> dict:
    """ROC AUC of a minus ROC AUC of b, with a paired percentile bootstrap 95% CI.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        a (np.ndarray): Scores of the first predictor, shape (n,).
        b (np.ndarray): Scores of the second predictor, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        dict: delta, ci_low, ci_high, and the two point AUCs.
    """
    deltas = []
    for rows in sample_indices:
        labels = y_true[rows]
        if labels.min() == labels.max():
            continue
        deltas.append(roc_auc_score(labels, a[rows]) - roc_auc_score(labels, b[rows]))
    auc_a, auc_b = roc_auc_score(y_true, a), roc_auc_score(y_true, b)
    low, high = np.percentile(deltas, [2.5, 97.5])
    return {"auc_a": auc_a, "auc_b": auc_b, "delta": auc_a - auc_b,
            "ci_low": float(low), "ci_high": float(high)}


def bootstrap_aucs(y_true: np.ndarray, scores: np.ndarray, sample_indices: np.ndarray) -> np.ndarray:
    """ROC AUC on every resample that holds both classes.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        scores (np.ndarray): Scores, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        np.ndarray: One AUC per usable resample.
    """
    return np.array([roc_auc_score(y_true[rows], scores[rows]) for rows in sample_indices
                     if y_true[rows].min() != y_true[rows].max()])


def delta_against_random_draws(y_true: np.ndarray, scores: np.ndarray, draw_aucs: np.ndarray,
                               sample_indices: np.ndarray) -> dict:
    """ROC AUC of a cosine arm minus the random arm's, with both sources of uncertainty.

    The random arm is a distribution over draws, not one predictor, so a contrast paired
    against a single draw would leave out the spread the random band is built from. The
    random predictions are drawn independently of every label, so the two uncertainties
    are independent: the interval is the 2.5th to 97.5th percentile of every difference
    between a bootstrap AUC of the cosine arm (resampled test patients) and one draw's AUC
    of the random arm, over all pairs.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        scores (np.ndarray): The cosine arm's predictions, shape (n,).
        draw_aucs (np.ndarray): The random arm's AUC in each draw at its best k.
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        dict: auc_a (the cosine arm), auc_b (mean across draws), delta, ci_low, ci_high,
            n_draws and the method.
    """
    auc_a = roc_auc_score(y_true, scores)
    differences = bootstrap_aucs(y_true, scores, sample_indices)[:, None] - draw_aucs[None, :]
    low, high = np.percentile(differences, [2.5, 97.5])
    auc_b = float(np.mean(draw_aucs))
    return {"auc_a": auc_a, "auc_b": auc_b, "delta": auc_a - auc_b,
            "ci_low": float(low), "ci_high": float(high), "n_draws": int(draw_aucs.size),
            "method": "test-patient bootstrap of the cosine arm against every random draw"}


def auc_interval(y_true: np.ndarray, scores: np.ndarray, sample_indices: np.ndarray) -> tuple:
    """ROC AUC with a percentile bootstrap 95% CI.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        scores (np.ndarray): Scores, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        tuple: (auc, ci_low, ci_high).
    """
    aucs = [roc_auc_score(y_true[rows], scores[rows]) for rows in sample_indices
            if y_true[rows].min() != y_true[rows].max()]
    low, high = np.percentile(aucs, [2.5, 97.5])
    return roc_auc_score(y_true, scores), float(low), float(high)


def arm_lines(curve: pd.DataFrame, intervals: pd.DataFrame,
              random_curve: pd.DataFrame = None) -> dict:
    """Each arm's curve at every k and its band, in the order the figure draws them.

    Args:
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        random_curve (pd.DataFrame, optional): random_neighbour_curve.csv, every k.

    Returns:
        dict: Arm to (line, band), both sorted by n_neighbors. A line has n_neighbors
            and roc_auc; a band has n_neighbors, ci_low and ci_high.
    """
    arms = {}
    for metric in ("weighted", "plain"):
        line = curve[(curve.metric == metric) & (curve.alpha == ALPHA)].sort_values("n_neighbors")
        band = intervals[(intervals.metric == metric) & (intervals.alpha == ALPHA)].sort_values("n_neighbors")
        arms[metric] = (line, band)
    if random_curve is not None:
        line = random_curve.sort_values("n_neighbors")
        arms["random"] = (line, line)
    return arms


def best_point(line: pd.DataFrame) -> pd.Series:
    """The row with the highest AUC; the smallest k wins a tie, as in the sweep."""
    return line.iloc[int(np.nanargmax(line.roc_auc.to_numpy()))]


def arm_legend_label(metric: str, best: pd.Series, low: float, high: float) -> str:
    """One arm's legend entry: its name, then its best k with the value and interval there.

    Args:
        metric (str): weighted, plain or random.
        best (pd.Series): best_point of the arm's line.
        low (float): Lower end of the arm's interval at that k.
        high (float): Upper end.

    Returns:
        str: Two lines, e.g. "Plain cosine" over "best k = 1,243: 0.602 (95% CI
            0.586-0.618)", so the legend stays inside the plot's width.
    """
    return (f"{METRIC_DISPLAY[metric]}\nbest k = {int(best.n_neighbors):,}: "
            f"{best.roc_auc:.3f} ({INTERVAL_NAME[metric]} {low:.3f}\u2013{high:.3f})")


def arm_best(line: pd.DataFrame, band: pd.DataFrame) -> tuple[pd.Series, float, float]:
    """An arm's best point and its interval there, read off the band at that k.

    Args:
        line (pd.DataFrame): The arm's curve, as arm_lines.
        band (pd.DataFrame): The arm's band, as arm_lines.

    Returns:
        tuple[pd.Series, float, float]: (best_point row, ci_low, ci_high).
    """
    best = best_point(line)
    low = float(np.interp(best.n_neighbors, band.n_neighbors, band.ci_low))
    high = float(np.interp(best.n_neighbors, band.n_neighbors, band.ci_high))
    return best, low, high


def reference_legend_label(label: str, auc: float, low: float, high: float) -> str:
    """A classifier line's legend entry on the single-encoder figure."""
    return f"{label}, {auc:.3f} (95% CI {low:.3f}\u2013{high:.3f})"


def draw_curves(axis, curve: pd.DataFrame, intervals: pd.DataFrame, reference_aucs: dict,
                random_curve: pd.DataFrame = None, arm_label=arm_legend_label,
                reference_label=reference_legend_label, best_marker: dict = None) -> dict:
    """Every curve, band, best-k point and classifier line of one encoder, on one axis.

    Both the single-encoder figure (build) and Figure 4's composite draw through this,
    so the two cannot disagree on what is drawn. Only the legend labels differ, and they
    are passed in.

    Args:
        axis: The matplotlib axis to draw on.
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        reference_aucs (dict): Reference classifier label to (AUC, ci_low, ci_high), in
            REFERENCES order: the first is drawn dotted, the second dashed.
        random_curve (pd.DataFrame, optional): random_neighbour_curve.csv; the random
            arm is left out when None.
        arm_label (callable): (metric, best, low, high) to the arm's legend label.
        reference_label (callable): (label, auc, low, high) to the line's legend label;
            a label starting with an underscore keeps the line out of the legend.
        best_marker (dict, optional): Marker style for the best-k point. When given, the
            point is its own artist carrying arm_label and the curve is left out of the
            legend, so a legend can show the arm as a line and its best k as a marker.
            When None, the point is a marker on the curve and the curve carries arm_label.

    Returns:
        dict: Arm to (best, ci_low, ci_high), as arm_best.
    """
    arms = arm_lines(curve, intervals, random_curve)
    bests = {}
    for metric, (line, band) in arms.items():
        color = METRIC_COLOR[metric]
        axis.fill_between(band.n_neighbors, band.ci_low, band.ci_high,
                          color=color, alpha=0.15, linewidth=0)
        best, low, high = bests[metric] = arm_best(line, band)
        if best_marker is not None:
            axis.plot(line.n_neighbors, line.roc_auc, color=color, linewidth=2, label=f"_{metric}")
            axis.plot([best.n_neighbors], [best.roc_auc], color=color, linestyle="none", zorder=5,
                      label=arm_label(metric, best, low, high), **best_marker)
            continue
        # The point sits on the curve and its numbers live in a legend: a label beside
        # the point lands on whichever curve or band passes through that corner.
        best_index = int(np.flatnonzero(line.n_neighbors.to_numpy() == best.n_neighbors)[0])
        axis.plot(line.n_neighbors, line.roc_auc, color=color, linewidth=2,
                  marker="o", markevery=[best_index], markersize=7,
                  markeredgecolor="white", markeredgewidth=1.5,
                  label=arm_label(metric, best, low, high))
    for (label, (auc, low, high)), style in zip(reference_aucs.items(), REFERENCE_STYLES):
        axis.axhspan(low, high, color=REFERENCE_COLOR, alpha=0.08, linewidth=0)
        axis.axhline(auc, color=REFERENCE_COLOR, linestyle=style, linewidth=1.2,
                     label=reference_label(label, auc, low, high))
    axis.set_xscale("log")
    axis.set_xlim(1, curve.n_neighbors.max())
    axis.set_ylim(*y_limits(arms, reference_aucs))
    axis.grid(True, which="major", color="#e6e6e6", linewidth=0.8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    return bests


def build(curve: pd.DataFrame, intervals: pd.DataFrame, reference_aucs: dict,
          random_curve: pd.DataFrame = None):
    """The retrieval figure, unsaved, so its text can be checked before it is written.

    Args:
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        reference_aucs (dict): Reference classifier label to (AUC, ci_low, ci_high).
        random_curve (pd.DataFrame, optional): random_neighbour_curve.csv; the random
            arm is left out when None.

    Returns:
        tuple: (figure, axis).
    """
    # The legend gets a row of its own under the axes. Hung off the axes instead, it is
    # counted as part of them by tight_layout, which then shrinks the plot to make room.
    figure, (axis, legend_axis) = plt.subplots(
        nrows=2, figsize=FIGURE_SIZE, gridspec_kw={"height_ratios": LEGEND_ROW_RATIOS})
    legend_axis.axis("off")
    draw_curves(axis, curve, intervals, reference_aucs, random_curve)
    axis.set_xlabel(X_LABEL, fontsize=FONT_SIZES["label"])
    axis.set_ylabel(Y_LABEL, fontsize=FONT_SIZES["label"])
    axis.tick_params(axis="both", which="major", labelsize=FONT_SIZES["tick"])
    # Below the axes, one entry per row: inside, every corner holds a curve or a band once
    # the random arm sits along the bottom, and each entry now carries its numbers.
    handles, labels = axis.get_legend_handles_labels()
    legend = legend_axis.legend(handles, labels, loc="upper left", bbox_to_anchor=(-0.1, 1.0),
                                ncol=1, frameon=False, fontsize=FONT_SIZES["legend"],
                                handlelength=2.4, labelspacing=0.45)
    # Out of tight_layout's reckoning, or it narrows the plot to any overhang; the save
    # names it as an extra artist so the tight bounding box still takes it in.
    legend.set_in_layout(False)
    return figure, axis


def draw(curve: pd.DataFrame, intervals: pd.DataFrame, reference_aucs: dict,
         save_path: Path, random_curve: pd.DataFrame = None) -> None:
    """Draw the retrieval curves against the trained classifiers and write the PNG.

    Args:
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        reference_aucs (dict): Reference classifier label to (AUC, ci_low, ci_high).
        save_path (Path): Where the PNG goes.
        random_curve (pd.DataFrame, optional): random_neighbour_curve.csv; the random
            arm is left out when None.
    """
    figure, _ = build(curve, intervals, reference_aucs, random_curve)
    figure.tight_layout()
    legends = [a.get_legend() for a in figure.axes if a.get_legend() is not None]
    figure.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight", bbox_extra_artists=legends)
    plt.close(figure)


def y_limits(arms: dict, reference_aucs: dict) -> tuple[float, float]:
    """Y range covering every curve, band and reference band, on a 0.02 grid.

    The random arm sits near 0.5, at the bottom of what the cosine arms need, so the
    range is read off the data rather than fixed.

    Args:
        arms (dict): arm_lines output.
        reference_aucs (dict): Reference label to (AUC, ci_low, ci_high).

    Returns:
        tuple[float, float]: (low, high).
    """
    values = [0.5]
    for line, band in arms.values():
        values += [line.roc_auc.min(), line.roc_auc.max(), band.ci_low.min(), band.ci_high.max()]
    for _, low, high in reference_aucs.values():
        values += [low, high]
    low, high = float(np.nanmin(values)), float(np.nanmax(values))
    return np.floor(low / 0.02) * 0.02, np.ceil(high / 0.02) * 0.02


def main():
    """Write the manuscript retrieval figure and its paired contrasts into RESULTS_DIR."""
    results_dir = Path(os.environ["RESULTS_DIR"])
    sweep_dir = results_dir / SWEEP_DIR_NAME
    frame, paired = load_predictions(results_dir)
    y_true = frame.true_label.to_numpy()
    sample_indices = bootstrap_sample_indices(len(frame))

    deltas = {
        f"best_retrieval_minus_{label}": paired_delta(
            y_true, frame.best_retrieval.to_numpy(), frame[label].to_numpy(), sample_indices)
        for label in paired
    }
    for label, _, _, _ in REFERENCES:
        if label not in paired:
            print(f"No per-patient predictions for {label} in this RESULTS_DIR: "
                  "its line is read from classical_ml_results, with no contrast against it.")
    deltas["weighted_minus_plain_at_own_best_k"] = paired_delta(
        y_true, frame.weighted.to_numpy(), frame.plain.to_numpy(), sample_indices)
    random_path = sweep_dir / RANDOM_CURVE
    draws_path = sweep_dir / RANDOM_DRAWS_AT_BEST
    if draws_path.exists():
        draw_aucs = pd.read_csv(draws_path).roc_auc.to_numpy()
        for metric in METRIC_PAIR:
            deltas[f"{metric}_minus_random_at_own_best_k"] = delta_against_random_draws(
                y_true, frame[metric].to_numpy(), draw_aucs, sample_indices)
    else:
        print(f"WARNING: {draws_path} is absent; no contrast against the random arm.")
    (sweep_dir / DELTAS_NAME).write_text(json.dumps(deltas, indent=2))

    reference_aucs = {}
    for label, source, model, shared in REFERENCES:
        if label in paired:
            reference_aucs[label] = auc_interval(y_true, frame[label].to_numpy(), sample_indices)
        else:
            reference_aucs[label] = summary_line(
                classifier_source(results_dir, source, shared)[1], model)
    draw(pd.read_csv(sweep_dir / "sweep_curve.csv"),
         pd.read_csv(sweep_dir / "sweep_intervals.csv"),
         reference_aucs, sweep_dir / FIGURE_NAME,
         pd.read_csv(random_path) if random_path.exists() else None)
    print(json.dumps(deltas, indent=2))


if __name__ == "__main__":
    main()
