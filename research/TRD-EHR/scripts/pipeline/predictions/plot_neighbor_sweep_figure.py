"""The manuscript's retrieval figure, and the paired contrasts its text quotes.

`neighbor_count_sweep` draws a working figure: six curves, twelve legend entries, one
per metric and sharpening exponent. The paper needs three curves, because sharpening
moves nothing (alpha 1, 2 and 5 agree to three decimals) and the question is only
whether retrieval reaches a trained classifier at any neighborhood size. This script
draws that figure from the sweep's own outputs and refits nothing:

  * one curve per cosine metric at alpha 1, with the bootstrap 95% band from
    sweep_intervals.csv;
  * the random-neighbor arm with uniform weights, its mean AUC across draws at every
    k inside the band of the 2.5th to 97.5th percentile across draws, from
    random_neighbour_curve.csv;
  * a point at each arm's best k, the k its panels (best_k_panels) are drawn at;
  * horizontal lines at the two leading trained classifiers, each with its own
    bootstrap 95% band over the same resamples of test patients.

It also writes the contrasts the Results paragraph quotes, so every number there is
on disk: the best retrieval predictions against each leading classifier and the
importance-weighted metric against plain cosine, paired over resampled test patients
seeded off SEED; and each cosine metric against the random arm, each at its own best
k, whose interval also spans the 1,000 random draws (delta_against_random_draws). Best k is chosen on those same patients, so every best-k
number is optimistic.

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

# Where each best-k label sits relative to its point, in points, so the three labels do
# not collide: weighted above, plain below, random above its near-0.5 band, where the
# cosine curves have already climbed away.
LABEL_OFFSET = {"weighted": (6, 8), "plain": (8, -34), "random": (6, 10)}

# The two leading trained classifiers, as (label, representation, model column).
REFERENCES = (
    ("EMBEDDED logistic regression", "EMBEDDED", "logistic_regression"),
    ("FEATURE XGBoost",              "FEATURE",  "xgboost"),
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


def load_predictions(results_dir: Path) -> pd.DataFrame:
    """Join the retrieval and classifier held-out predictions on test patient.

    Args:
        results_dir (Path): RESULTS_DIR for the active encoder/judge pair.

    Returns:
        pd.DataFrame: One row per test patient: true_label, best_retrieval,
            weighted, plain, and one column per reference
            classifier label.
    """
    sweep_dir = results_dir / SWEEP_DIR_NAME
    frame = pd.read_csv(sweep_dir / BEST_RETRIEVAL).rename(
        columns={"predicted_risk": "best_retrieval"})[["anchor_patient_id", "true_label", "best_retrieval"]]
    for metric, name in METRIC_PAIR.items():
        other = pd.read_csv(sweep_dir / name)[["anchor_patient_id", "predicted_risk"]]
        frame = frame.merge(other.rename(columns={"predicted_risk": metric}),
                            on="anchor_patient_id", validate="one_to_one")
    for label, source, model in REFERENCES:
        classifier = pd.read_parquet(results_dir / f"test_predictions_{source}.parquet")
        classifier = classifier[["patient_id", model]].rename(
            columns={"patient_id": "anchor_patient_id", model: label})
        frame = frame.merge(classifier, on="anchor_patient_id", validate="one_to_one")
    return frame


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


def draw(curve: pd.DataFrame, intervals: pd.DataFrame, reference_aucs: dict,
         save_path: Path, random_curve: pd.DataFrame = None) -> None:
    """Draw the retrieval curves against the trained classifiers.

    Args:
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        reference_aucs (dict): Reference classifier label to (AUC, ci_low, ci_high).
        save_path (Path): Where the PNG goes.
        random_curve (pd.DataFrame, optional): random_neighbour_curve.csv; the random
            arm is left out when None.
    """
    plt.rcParams.update({"font.size": 10})
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    arms = arm_lines(curve, intervals, random_curve)
    for metric, (line, band) in arms.items():
        color = METRIC_COLOR[metric]
        axis.fill_between(band.n_neighbors, band.ci_low, band.ci_high,
                          color=color, alpha=0.15, linewidth=0)
        axis.plot(line.n_neighbors, line.roc_auc, color=color, linewidth=2,
                  label=METRIC_DISPLAY[metric])
        best = best_point(line)
        low, high = np.interp(best.n_neighbors, band.n_neighbors, band.ci_low), \
            np.interp(best.n_neighbors, band.n_neighbors, band.ci_high)
        axis.plot(best.n_neighbors, best.roc_auc, "o", color=color, markersize=7,
                  markeredgecolor="white", markeredgewidth=1.5)
        axis.annotate(f"best k = {int(best.n_neighbors):,}: {best.roc_auc:.3f} "
                      f"({low:.3f}\u2013{high:.3f})",
                      (best.n_neighbors, best.roc_auc),
                      textcoords="offset points",
                      xytext=LABEL_OFFSET[metric],
                      ha="left",
                      fontsize=8.5, color="#333333")
    for (label, (auc, low, high)), style in zip(reference_aucs.items(), (":", "--")):
        axis.axhspan(low, high, color="#555555", alpha=0.08, linewidth=0)
        axis.axhline(auc, color="#555555", linestyle=style, linewidth=1.2,
                     label=f"{label}, {auc:.3f} ({low:.3f}\u2013{high:.3f})")
    axis.set_xscale("log")
    axis.set_xlim(1, curve.n_neighbors.max())
    axis.set_ylim(*y_limits(arms, reference_aucs))
    axis.set_xlabel("Number of neighbors, k (log scale)")
    axis.set_ylabel("Test-set ROC AUC")
    axis.grid(True, which="major", color="#e6e6e6", linewidth=0.8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    # Below the axes: inside, every corner holds a curve or a band once the random arm
    # sits along the bottom.
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=8.5)
    figure.tight_layout()
    figure.savefig(save_path, dpi=FIGURE_DPI, bbox_inches="tight")
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
    frame = load_predictions(results_dir)
    y_true = frame.true_label.to_numpy()
    sample_indices = bootstrap_sample_indices(len(frame))

    deltas = {
        f"best_retrieval_minus_{label}": paired_delta(
            y_true, frame.best_retrieval.to_numpy(), frame[label].to_numpy(), sample_indices)
        for label, _, _ in REFERENCES
    }
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

    reference_aucs = {label: auc_interval(y_true, frame[label].to_numpy(), sample_indices)
                      for label, _, _ in REFERENCES}
    draw(pd.read_csv(sweep_dir / "sweep_curve.csv"),
         pd.read_csv(sweep_dir / "sweep_intervals.csv"),
         reference_aucs, sweep_dir / FIGURE_NAME,
         pd.read_csv(random_path) if random_path.exists() else None)
    print(json.dumps(deltas, indent=2))


if __name__ == "__main__":
    main()
