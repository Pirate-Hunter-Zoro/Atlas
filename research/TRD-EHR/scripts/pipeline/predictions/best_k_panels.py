"""Every panel the k = 50 retrieval arms get, drawn at each retrieval arm's best k instead.

The pipeline (trd_prediction_computation) draws ROC, precision-recall, calibration,
decision-curve, effective-sample-size and confusion-matrix panels for its retrieval arms at
NUM_NEIGHBOR_PATIENTS = 50, a size that was inherited, never chosen. The neighbourhood
sweep scores every k, so this draws the same six panels for three arms, each at its own
best k:

  * logistic-regression-weighted cosine, alpha 1 (mode prefix
    NEAREST_IMPORTANCE_WEIGHTED, kept so the paper's panel paths hold);
  * plain cosine, alpha 1;
  * random neighbours with uniform weights, from the draw whose AUC at the arm's best k
    sits closest to the mean across draws (neighbor_count_sweep.representative_draw).

Alpha 1 because Figure 4 draws alpha 1; the maxima under alpha 1, 2 and 5 agree within
0.002. It reads the files neighbor_count_sweep writes and refits nothing.

BEST k IS CHOSEN ON THE SAME TEST PATIENTS THESE PANELS ARE SCORED ON, so every number on
them is optimistic by however much the curve was noise-peaked. For the random arm that is
all of it: its true AUC is 0.5 at every k.

Every number carries an interval, a 95% percentile bootstrap over the test patients from
bootstrap_sample_indices, the SEED-seeded resamples the ROC band uses. The confusion matrix
holds its Youden J threshold fixed across resamples, so its intervals are the spread at
that operating point, not of the choice of point.

Outputs, all under RESULTS_DIR/neighbor_count_sweep/:
    best_k_panels/{roc_curve,pr_curve,calibration_curve,decision_curve,
                   ess_distribution,confusion_matrix}_{mode}.png
    best_k_panels.json
where mode names the arm and its k, e.g. NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.

Usage:
    python -m scripts.pipeline.predictions.best_k_panels
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from dotenv import load_dotenv
load_dotenv()

from scripts.pipeline.predictions.redraw_manuscript_panels import CSV_ROUNDTRIP_TOLERANCE, report
from scripts.pipeline.predictions.trd_prediction_computation import compute_metrics
from scripts.shared.plots import (
    bootstrap_sample_indices,
    plot_calibration,
    plot_decision_curve_analysis,
    plot_effective_sample_size_distribution,
    plot_optimal_confusion_matrix,
    plot_precision_recall,
    plot_receiving_operator_characteristic,
)

SWEEP_DIR_NAME = "neighbor_count_sweep"
PANEL_DIR_NAME = "best_k_panels"
SUMMARY_NAME = "best_k_panels.json"

# The exponent the cosine arms are drawn at, as Figure 4 draws them.
ALPHA_KEY = "1"

# (arm, prediction file, mode prefix). The mode is the prefix plus the arm's best k, so the
# k is in every filename.
ARMS = (
    ("weighted", "best_k_predictions_alpha1.csv",       "NEAREST_IMPORTANCE_WEIGHTED_alpha1"),
    ("plain",    "best_k_predictions_alpha1_plain.csv", "NEAREST_PLAIN_COSINE_alpha1"),
    ("random",   "best_k_predictions_random.csv",       "RANDOM_UNIFORM"),
)


def arm_record(summary: dict, arm: str) -> dict:
    """The sweep's summary block for one arm.

    Args:
        summary (dict): sweep_summary.json.
        arm (str): One of the ARMS names.

    Returns:
        dict: Carries best_n_neighbors and the recorded ROC AUC with its interval under
            roc_score, roc_score_ci_low and roc_score_ci_high, the keys report() checks.
    """
    if arm == "random":
        block = summary["random"]
        return {
            "best_n_neighbors": int(block["best_n_neighbors"]),
            "roc_score": block["representative_draw_roc_auc"],
            "roc_score_ci_low": block["representative_draw_roc_auc_ci_low"],
            "roc_score_ci_high": block["representative_draw_roc_auc_ci_high"],
        }
    block = summary["by_metric"][arm][ALPHA_KEY]
    return {
        "best_n_neighbors": int(block["best_n_neighbors"]),
        "roc_score": block["best_roc_auc"],
        "roc_score_ci_low": block["best_roc_auc_ci_low"],
        "roc_score_ci_high": block["best_roc_auc_ci_high"],
    }


def bootstrap_metrics(y_true: np.ndarray, y_prob: np.ndarray, ess: np.ndarray,
                      sample_indices: np.ndarray) -> dict:
    """The pipeline's knn_results metrics plus mean ESS, each with a bootstrap 95% CI.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        y_prob (np.ndarray): Predicted risk, shape (n,).
        ess (np.ndarray): Effective sample size per anchor, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        dict: Metric name to {value, ci_low, ci_high}; names as compute_metrics, plus
            mean_ESS.
    """
    point = compute_metrics(y_true, y_prob)
    point["mean_ESS"] = float(np.mean(ess))
    draws = {name: [] for name in point}
    for rows in sample_indices:
        labels = y_true[rows]
        if labels.min() == labels.max():
            continue
        values = compute_metrics(labels, y_prob[rows])
        values["mean_ESS"] = float(np.mean(ess[rows]))
        for name, value in values.items():
            draws[name].append(value)
    return {name: {"value": float(point[name]),
                   "ci_low": float(np.percentile(draws[name], 2.5)),
                   "ci_high": float(np.percentile(draws[name], 97.5))}
            for name in point}


def draw_arm(frame: pd.DataFrame, mode: str, panel_dir: Path) -> dict:
    """Write the six panels for one arm and return every number printed on them.

    Args:
        frame (pd.DataFrame): Columns true_label, predicted_risk, ess.
        mode (str): Filename suffix, carrying the arm and its k.
        panel_dir (Path): Where the PNGs go.

    Returns:
        dict: roc_auc and average_precision with intervals, the calibration bins, the
            confusion-matrix metrics, and bootstrap_metrics.
    """
    y_true = frame["true_label"].to_numpy().astype(int)
    y_prob = frame["predicted_risk"].to_numpy().astype(float)
    ess = frame["ess"].to_numpy().astype(float)
    roc = plot_receiving_operator_characteristic(y_true, y_prob, mode, save_dir=panel_dir)
    precision_recall = plot_precision_recall(y_true, y_prob, mode, save_dir=panel_dir)
    # Quantile bins: retrieval risks crowd into a narrow band near the prevalence, where ten
    # equal-width bins would put nearly every patient into one or two points.
    calibration = plot_calibration(y_true, y_prob, mode, save_dir=panel_dir,
                                   strategy="quantile", bootstrap=True)
    plot_decision_curve_analysis(y_true, y_prob, mode, save_dir=panel_dir)
    plot_effective_sample_size_distribution(ess, mode, save_dir=panel_dir)
    confusion = plot_optimal_confusion_matrix(y_true, y_prob, mode, save_dir=panel_dir, bootstrap=True)
    return {
        "roc_auc": dict(zip(("value", "ci_low", "ci_high"), roc)),
        "average_precision": dict(zip(("value", "ci_low", "ci_high"), precision_recall)),
        "calibration_bins": calibration,
        "confusion_matrix": confusion,
        "metrics": bootstrap_metrics(y_true, y_prob, ess, bootstrap_sample_indices(len(y_true))),
    }


def run(results_dir: Path) -> dict:
    """Draw every arm's panels at its best k and write best_k_panels.json.

    Args:
        results_dir (Path): RESULTS_DIR for the active encoder/judge pair.

    Returns:
        dict: What was written to best_k_panels.json, arm name to its block.

    Raises:
        FileNotFoundError: If sweep_summary.json or a cosine arm's predictions are absent.
        ValueError: If a redrawn AUC disagrees with the one the sweep recorded.
    """
    sweep_dir = results_dir / SWEEP_DIR_NAME
    summary = json.loads((sweep_dir / "sweep_summary.json").read_text())
    panel_dir = sweep_dir / PANEL_DIR_NAME
    os.makedirs(panel_dir, exist_ok=True)
    out = {}
    for arm, filename, prefix in ARMS:
        path = sweep_dir / filename
        if arm == "random" and ("random" not in summary or not path.exists()):
            print(f"WARNING: no random arm in {sweep_dir}; run the sweep with --random-draws "
                  "above 0 to draw its panels.", flush=True)
            continue
        record = arm_record(summary, arm)
        k = record["best_n_neighbors"]
        mode = f"{prefix}_k{k}"
        frame = pd.read_csv(path)
        if "ess" not in frame.columns:
            raise ValueError(f"{path} has no ess column; it predates the ESS the sweep now "
                             "writes. Re-run neighbor_count_sweep.")
        block = draw_arm(frame, mode, panel_dir)
        got = (block["roc_auc"]["value"], block["roc_auc"]["ci_low"], block["roc_auc"]["ci_high"])
        report(mode, got, record, CSV_ROUNDTRIP_TOLERANCE)
        block.update({"arm": arm, "mode": mode, "n_neighbors": k, "predictions": filename})
        if arm == "random":
            random_block = summary["random"]
            block["weighting"] = "uniform"
            block["across_draw_roc_auc"] = {
                "value": random_block["best_roc_auc"],
                "ci_low": random_block["best_roc_auc_ci_low"],
                "ci_high": random_block["best_roc_auc_ci_high"],
                "n_draws": random_block["n_draws"],
                "representative_draw": random_block["representative_draw"],
            }
        else:
            block["weighting"] = f"cosine, alpha {ALPHA_KEY}"
        out[arm] = block
    (sweep_dir / SUMMARY_NAME).write_text(json.dumps(out, indent=2))
    return out


def main():
    """Draw the best-k panels for every retrieval arm into RESULTS_DIR."""
    results_dir = Path(os.environ["RESULTS_DIR"])
    out = run(results_dir)
    for arm, block in out.items():
        auc = block["roc_auc"]
        print(f"{block['mode']}: ROC AUC {auc['value']:.4f} ({auc['ci_low']:.4f}-{auc['ci_high']:.4f})")


if __name__ == "__main__":
    main()
