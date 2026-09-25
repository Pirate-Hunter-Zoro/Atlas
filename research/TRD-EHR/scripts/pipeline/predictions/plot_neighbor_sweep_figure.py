"""The manuscript's retrieval figure, and the paired contrasts its text quotes.

`neighbor_count_sweep` draws a working figure: six curves, twelve legend entries, one
per metric and sharpening exponent. The paper needs two curves, because sharpening
moves nothing (alpha 1, 2 and 5 agree to three decimals) and the question is only
whether retrieval reaches a trained classifier at any neighborhood size. This script
draws that figure from the sweep's own outputs and refits nothing:

  * one curve per metric at alpha 1, with the bootstrap 95% band from
    sweep_intervals.csv;
  * a vertical line at k = 50, the neighborhood size of the primary retrieval arm;
  * horizontal lines at the two leading trained classifiers, each with its own
    bootstrap 95% band over the same resamples of test patients.

It also writes the paired bootstrap contrasts the Results paragraph quotes, so every
number there is on disk: the best retrieval predictions against each leading
classifier, and the importance-weighted metric against plain cosine, each arm at its
own best k. Resampling is over test patients, seeded off SEED.

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
PRIMARY_K = 50

METRIC_DISPLAY = {
    "weighted": "Importance-weighted cosine",
    "plain":    "Plain cosine",
}
# Categorical slots 1 and 2 of the validated default palette, in fixed order.
METRIC_COLOR = {"weighted": "#2a78d6", "plain": "#eb6834"}

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


def load_predictions(results_dir: Path) -> pd.DataFrame:
    """Join the retrieval and classifier held-out predictions on test patient.

    Args:
        results_dir (Path): RESULTS_DIR for the active encoder/judge pair.

    Returns:
        pd.DataFrame: One row per test patient: true_label, best_retrieval,
            weighted, plain, and one column per reference classifier label.
    """
    sweep_dir = results_dir / SWEEP_DIR_NAME
    frame = pd.read_csv(sweep_dir / BEST_RETRIEVAL).rename(
        columns={"predicted_risk": "best_retrieval"})
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


def draw(curve: pd.DataFrame, intervals: pd.DataFrame, reference_aucs: dict,
         save_path: Path) -> None:
    """Draw the two retrieval curves against the trained classifiers.

    Args:
        curve (pd.DataFrame): sweep_curve.csv, every k.
        intervals (pd.DataFrame): sweep_intervals.csv, bootstrap CIs at sampled k.
        reference_aucs (dict): Reference classifier label to (AUC, ci_low, ci_high).
        save_path (Path): Where the PNG goes.
    """
    plt.rcParams.update({"font.size": 10})
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    for metric in ("weighted", "plain"):
        line = curve[(curve.metric == metric) & (curve.alpha == ALPHA)].sort_values("n_neighbors")
        band = intervals[(intervals.metric == metric) & (intervals.alpha == ALPHA)].sort_values("n_neighbors")
        color = METRIC_COLOR[metric]
        axis.fill_between(band.n_neighbors, band.ci_low, band.ci_high,
                          color=color, alpha=0.15, linewidth=0)
        axis.plot(line.n_neighbors, line.roc_auc, color=color, linewidth=2,
                  label=METRIC_DISPLAY[metric])
        best = line.loc[line.roc_auc.idxmax()]
        axis.plot(best.n_neighbors, best.roc_auc, "o", color=color, markersize=7,
                  markeredgecolor="white", markeredgewidth=1.5)
        axis.annotate(f"best k = {int(best.n_neighbors):,}: {best.roc_auc:.3f}",
                      (best.n_neighbors, best.roc_auc),
                      textcoords="offset points",
                      xytext=(6, 8) if metric == "weighted" else (8, -34),
                      ha="left",
                      fontsize=8.5, color="#333333")
    for (label, (auc, low, high)), style in zip(reference_aucs.items(), (":", "--")):
        axis.axhspan(low, high, color="#555555", alpha=0.08, linewidth=0)
        axis.axhline(auc, color="#555555", linestyle=style, linewidth=1.2,
                     label=f"{label}, {auc:.3f} ({low:.3f}\u2013{high:.3f})")
    axis.axvline(PRIMARY_K, color="#999999", linewidth=1)
    axis.text(PRIMARY_K / 1.08, 0.505, f"k = {PRIMARY_K}", fontsize=8.5, color="#555555", ha="right")
    axis.set_xscale("log")
    axis.set_xlim(1, curve.n_neighbors.max())
    axis.set_ylim(0.50, 0.68)
    axis.set_xlabel("Number of nearest neighbors, k (log scale)")
    axis.set_ylabel("ROC AUC, 8,516 test patients")
    axis.grid(True, which="major", color="#e6e6e6", linewidth=0.8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    axis.legend(loc="lower right", frameon=False, fontsize=8.5)
    figure.tight_layout()
    figure.savefig(save_path, dpi=FIGURE_DPI)
    plt.close(figure)


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
    (sweep_dir / DELTAS_NAME).write_text(json.dumps(deltas, indent=2))

    reference_aucs = {label: auc_interval(y_true, frame[label].to_numpy(), sample_indices)
                      for label, _, _ in REFERENCES}
    draw(pd.read_csv(sweep_dir / "sweep_curve.csv"),
         pd.read_csv(sweep_dir / "sweep_intervals.csv"),
         reference_aucs, sweep_dir / FIGURE_NAME)
    print(json.dumps(deltas, indent=2))


if __name__ == "__main__":
    main()
