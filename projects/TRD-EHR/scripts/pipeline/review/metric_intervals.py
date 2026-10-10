"""Intervals for the numbers the paper prints that the pipeline wrote without one.

Usage:
    python -m scripts.pipeline.review.metric_intervals            # everything
    python -m scripts.pipeline.review.metric_intervals --replot   # Figure S12D only

The pipeline records a bootstrap CI for ROC AUC only. The paper also prints AUPRC,
Brier score, weighted calibration error (WCE) and the binned calibration slope and
intercept for every classifier, AUPRC for every encoder, and a handful of cohort
descriptives. This computes a 95% interval for each of them and refits nothing.

Three blocks:

  classifiers  the 8 primary models (4 classifiers x EMBEDDED/FEATURE), read from
               test_predictions_{EMBEDDED,FEATURE}.parquet. Every compute_metrics metric
               gets a percentile bootstrap CI over the test patients, cut from
               bootstrap_sample_indices: the SEED-seeded resamples the ROC band and the
               best-k retrieval panels already use, so all three sets of intervals come
               from the same draws. The ROC AUC and its CI are recomputed and must match
               classical_ml_results_<arm>.json, which is the check that the resamples
               really are the same.
  encoders     embedded logistic regression for each of the 4 encoders. Only the primary
               encoder persisted per-patient predictions, so the other three are rescored
               from their saved model and their own embeddings.db, on the shared test
               split. Their ROC AUC must match that encoder's classical_ml_results.
  cohort       over all 42,579 patients in the feature table: the same-day prescribing
               share (Figure 1), the Spearman correlations of the outcome with record
               length, encounter count and diagnosis-to-index interval, and the outcome
               frequency by prescription timing (Supplement S7). Proportions carry Wilson
               intervals; correlations a percentile bootstrap. Also draws Figure S12D.

Artifacts, in ARTIFACTS_DIR/review/metric_intervals/:
  classifier_intervals.csv    one row per (representation, classifier, metric)
  encoder_intervals.csv       one row per (encoder, metric), embedded logistic regression
  cohort_intervals.json       the cohort block
  trd_rate_by_prescription_timing.png   Figure S12D
"""

import json
import os
import sqlite3
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from dotenv import load_dotenv
load_dotenv()

from scripts.pipeline.predictions.trd_prediction_computation import compute_metrics
from scripts.pipeline.review.paths import review_output_dir
from scripts.shared.plots import N_BOOTSTRAP, bootstrap_sample_indices
from scripts.shared.utils import load_trd_set, wilson_interval

ANALYSIS_NAME = "metric_intervals"

REPRESENTATIONS = ("EMBEDDED", "FEATURE")
CLASSIFIERS = ("logistic_regression", "random_forest", "gradient_boosting", "xgboost")
METRICS = ("roc_score", "auprc", "brier_score", "weighted_calibration_error",
           "calibration_slope", "calibration_intercept")

# Encoder folder names under ARTIFACTS_DIR, in the order the supplement lists them.
ENCODERS = ("bge-small-en-v1.5", "bge-en-icl", "Qwen-Qwen3-Embedding-4B",
            "Qwen-Qwen3-Embedding-8B")

# Recomputed ROC AUCs must agree with the pipeline's to this tolerance. The pipeline
# stores float64, so anything larger means different patients or different resamples.
ROUNDTRIP_TOLERANCE = 1e-9

# Figure S12D splits prescribing at this many days after the first depression diagnosis:
# 0 or 1 day is "within 1 day", the grouping the supplement reports.
WITHIN_DAYS = 1
RECORD_COLUMNS = ("pre_anchor_history_days", "num_encounters", "mdd_to_anchor_days")


def bootstrap_metric_intervals(y_true: np.ndarray, y_prob: np.ndarray,
                               sample_indices: np.ndarray) -> dict:
    """Every compute_metrics metric with a percentile bootstrap 95% CI.

    Draws that lose a class are skipped, as the ROC band skips them.

    Args:
        y_true (np.ndarray): 0/1 labels, shape (n,).
        y_prob (np.ndarray): Predicted risk, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        dict: Metric name to {value, ci_low, ci_high}, for each name in METRICS.
    """
    point = compute_metrics(y_true, y_prob)
    draws = {name: [] for name in METRICS}
    for rows in sample_indices:
        labels = y_true[rows]
        if labels.min() == labels.max():
            continue
        values = compute_metrics(labels, y_prob[rows])
        for name in METRICS:
            draws[name].append(values[name])
    return {name: {"value": float(point[name]),
                   "ci_low": float(np.percentile(draws[name], 2.5)),
                   "ci_high": float(np.percentile(draws[name], 97.5))}
            for name in METRICS}


def check_roc(label: str, got: dict, recorded: dict, check_interval: bool) -> None:
    """Refuse a recomputed ROC AUC that disagrees with the pipeline's.

    Args:
        label (str): What is being checked, for the message.
        got (dict): {value, ci_low, ci_high} from bootstrap_metric_intervals.
        recorded (dict): The pipeline's classical_ml_results entry for the model.
        check_interval (bool): Also compare the CI. True where the pipeline's interval
            was cut from the same resamples.

    Raises:
        ValueError: On any disagreement beyond ROUNDTRIP_TOLERANCE.
    """
    pairs = [("roc_score", got["value"])]
    if check_interval:
        pairs += [("roc_score_ci_low", got["ci_low"]), ("roc_score_ci_high", got["ci_high"])]
    for key, value in pairs:
        if abs(value - recorded[key]) > ROUNDTRIP_TOLERANCE:
            raise ValueError(f"{label}: recomputed {key} {value:.12f} disagrees with the "
                             f"pipeline's {recorded[key]:.12f}; not the same patients or "
                             "not the same resamples.")


def classifier_intervals(results_dir: Path) -> pd.DataFrame:
    """The classifier block: all 8 primary models, every metric.

    Args:
        results_dir (Path): RESULTS_DIR for the primary encoder.

    Returns:
        pd.DataFrame: representation, classifier, metric, value, ci_low, ci_high.
    """
    rows = []
    for representation in REPRESENTATIONS:
        frame = pd.read_parquet(results_dir / f"test_predictions_{representation}.parquet")
        recorded = json.loads(
            (results_dir / f"classical_ml_results_{representation}.json").read_text())
        y_true = frame["true_label"].to_numpy().astype(int)
        indices = bootstrap_sample_indices(len(y_true))
        for classifier in CLASSIFIERS:
            y_prob = frame[classifier].to_numpy().astype(float)
            block = bootstrap_metric_intervals(y_true, y_prob, indices)
            check_roc(f"{representation} {classifier}", block["roc_score"],
                      recorded[classifier], check_interval=True)
            for metric, values in block.items():
                rows.append({"representation": representation, "classifier": classifier,
                             "metric": metric, **values})
    return pd.DataFrame(rows)


def encoder_test_predictions(encoder: str, test_ids: list[str]) -> np.ndarray:
    """Embedded logistic regression's held-out risk for one encoder, from its saved model.

    Args:
        encoder (str): Folder name under ARTIFACTS_DIR.
        test_ids (list[str]): Held-out patient ids, sorted, the order the pipeline uses.

    Returns:
        np.ndarray: Predicted TRD risk, shape (len(test_ids),).
    """
    artifacts = Path(os.environ["ARTIFACTS_DIR"])
    connection = sqlite3.connect(artifacts / encoder / "embeddings.db")
    placeholders = ",".join("?" * len(test_ids))
    fetched = connection.execute(
        f"SELECT patient_id, embedding FROM embeddings WHERE patient_id IN ({placeholders}) "
        "ORDER BY patient_id", test_ids).fetchall()
    connection.close()
    if [pid for pid, _ in fetched] != test_ids:
        raise ValueError(f"{encoder}: embeddings.db does not hold every held-out patient once.")
    matrix = pd.DataFrame(np.array([np.frombuffer(blob, dtype=np.float32) for _, blob in fetched]))
    model = joblib.load(artifacts / encoder / os.environ["VLLM_MODEL_NAME"] / "trained_models"
                        / "logistic_regression_EMBEDDED.joblib")
    return model.predict_proba(matrix)[:, 1]


def encoder_intervals(primary_predictions: pd.DataFrame) -> pd.DataFrame:
    """The encoder block: embedded logistic regression for every encoder.

    Args:
        primary_predictions (pd.DataFrame): test_predictions_EMBEDDED.parquet for the
            primary encoder, which supplies the test ids and labels.

    Returns:
        pd.DataFrame: encoder, metric, value, ci_low, ci_high.
    """
    artifacts = Path(os.environ["ARTIFACTS_DIR"])
    test_ids = primary_predictions["patient_id"].tolist()
    if test_ids != sorted(test_ids):
        raise ValueError("test_predictions_EMBEDDED.parquet is not in sorted patient order.")
    y_true = primary_predictions["true_label"].to_numpy().astype(int)
    indices = bootstrap_sample_indices(len(y_true))
    rows = []
    for encoder in ENCODERS:
        y_prob = encoder_test_predictions(encoder, test_ids)
        recorded = json.loads((artifacts / encoder / os.environ["VLLM_MODEL_NAME"]
                               / "classical_ml_results_EMBEDDED.json").read_text())
        block = bootstrap_metric_intervals(y_true, y_prob, indices)
        # The other encoders' pipeline intervals were cut from the same resamples too,
        # so the interval is checked as well as the point.
        check_roc(encoder, block["roc_score"], recorded["logistic_regression"],
                  check_interval=True)
        for metric, values in block.items():
            rows.append({"encoder": encoder, "metric": metric, **values})
    return pd.DataFrame(rows)


def spearman_interval(x: np.ndarray, y: np.ndarray, sample_indices: np.ndarray) -> dict:
    """Spearman rho with a percentile bootstrap 95% CI.

    Args:
        x (np.ndarray): Predictor, shape (n,).
        y (np.ndarray): 0/1 outcome, shape (n,).
        sample_indices (np.ndarray): Resample indices, shape (n_bootstrap, n).

    Returns:
        dict: value, ci_low, ci_high.
    """
    draws = [spearmanr(x[rows], y[rows]).statistic for rows in sample_indices]
    return {"value": float(spearmanr(x, y).statistic),
            "ci_low": float(np.percentile(draws, 2.5)),
            "ci_high": float(np.percentile(draws, 97.5))}


def proportion(successes: int, n: int) -> dict:
    """A proportion with its Wilson interval, as a dict.

    Args:
        successes (int): Count with the property.
        n (int): Denominator.

    Returns:
        dict: n, successes, value, ci_low, ci_high.
    """
    low, high = wilson_interval(successes, n)
    return {"n": int(n), "successes": int(successes), "value": successes / n,
            "ci_low": low, "ci_high": high}


def cohort_intervals(table: pd.DataFrame) -> dict:
    """The cohort block, over every patient in the feature table.

    Args:
        table (pd.DataFrame): RECORD_COLUMNS plus a 0/1 column trd_label.

    Returns:
        dict: same_day_prescribing, cohort_outcome, spearman (one entry per column),
            and outcome_by_timing (within_1_day, later).
    """
    y = table["trd_label"].to_numpy().astype(int)
    indices = bootstrap_sample_indices(len(y))
    within = (table["mdd_to_anchor_days"] <= WITHIN_DAYS).to_numpy()
    return {
        "n_patients": int(len(table)),
        "n_bootstrap": N_BOOTSTRAP,
        "same_day_prescribing": proportion(int((table["mdd_to_anchor_days"] == 0).sum()),
                                           len(table)),
        "cohort_outcome": proportion(int(y.sum()), len(y)),
        "spearman": {column: spearman_interval(table[column].to_numpy(), y, indices)
                     for column in RECORD_COLUMNS},
        "outcome_by_timing": {
            "within_days": WITHIN_DAYS,
            "within_1_day": proportion(int(y[within].sum()), int(within.sum())),
            "later": proportion(int(y[~within].sum()), int((~within).sum())),
        },
    }


def plot_timing(cohort: dict, save_path: Path) -> Path:
    """Figure S12D: outcome frequency by prescription timing, with Wilson 95% CIs.

    Args:
        cohort (dict): Output of cohort_intervals.
        save_path (Path): Destination PNG.

    Returns:
        Path: The written figure.
    """
    groups = cohort["outcome_by_timing"]
    bars = [("Within 1 day\nof diagnosis", groups["within_1_day"]),
            ("2 or more days\nafter diagnosis", groups["later"])]
    base = cohort["cohort_outcome"]
    figure, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.axhspan(base["ci_low"], base["ci_high"], color="0.85", zorder=0)
    ax.axhline(base["value"], color="0.45", linestyle="--", linewidth=1.0, zorder=1)
    ax.text(1.45, base["value"],
            f"All patients {100 * base['value']:.1f}%\n"
            f"(95% CI {100 * base['ci_low']:.1f}–{100 * base['ci_high']:.1f})",
            ha="left", va="center", fontsize=8, color="0.3")
    for position, (label, block) in enumerate(bars):
        ax.bar(position, block["value"], width=0.55, color="#4c78a8", zorder=2)
        ax.errorbar(position, block["value"],
                    yerr=[[block["value"] - block["ci_low"]], [block["ci_high"] - block["value"]]],
                    color="black", capsize=5, linewidth=1.2, zorder=3)
        # Inside the bar, clear of the reference band that crosses both bars' tops.
        ax.text(position, block["value"] / 2,
                f"{100 * block['value']:.1f}%\n(95% CI {100 * block['ci_low']:.1f}–"
                f"{100 * block['ci_high']:.1f})\n\n{block['successes']:,} of {block['n']:,}",
                ha="center", va="center", fontsize=8.5, color="white")
    ax.set_xticks(range(len(bars)))
    ax.set_xticklabels([label for label, _ in bars], fontsize=9)
    ax.set_xlim(-0.5, 2.3)
    ax.set_ylim(0, 0.22)
    ax.set_yticks(np.arange(0, 0.21, 0.05))
    ax.tick_params(axis="y", labelsize=9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))
    ax.set_ylabel("Outcome frequency (TRD proxy)", fontsize=9)
    ax.set_xlabel("Index prescription relative to the first depression diagnosis", fontsize=9)
    ax.set_title("Outcome frequency by prescription timing, with Wilson 95% CIs", fontsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    figure.savefig(save_path, dpi=150)
    plt.close(figure)
    return save_path


def load_cohort() -> pd.DataFrame:
    """RECORD_COLUMNS for every patient in the feature table, plus the 0/1 outcome.

    Returns:
        pd.DataFrame: One row per patient.
    """
    table = pd.read_parquet(Path(os.environ["FEATURE_DATAFRAME_PATH"]),
                            columns=list(RECORD_COLUMNS))
    trd = load_trd_set()
    table["trd_label"] = [1 if pid in trd else 0 for pid in table.index]
    return table


def replot():
    """Redraw Figure S12D from the saved cohort_intervals.json, recomputing nothing."""
    save_dir = review_output_dir(ANALYSIS_NAME)
    cohort = json.loads((save_dir / "cohort_intervals.json").read_text())
    print(f"Wrote {plot_timing(cohort, save_dir / 'trd_rate_by_prescription_timing.png')}")


def main():
    results_dir = Path(os.environ["RESULTS_DIR"])
    save_dir = review_output_dir(ANALYSIS_NAME)

    classifiers = classifier_intervals(results_dir)
    classifiers.to_csv(save_dir / "classifier_intervals.csv", index=False)
    print(classifiers.to_string(index=False), flush=True)

    primary = pd.read_parquet(results_dir / "test_predictions_EMBEDDED.parquet")
    encoders = encoder_intervals(primary)
    encoders.to_csv(save_dir / "encoder_intervals.csv", index=False)
    print(encoders.to_string(index=False), flush=True)

    cohort = cohort_intervals(load_cohort())
    (save_dir / "cohort_intervals.json").write_text(json.dumps(cohort, indent=2))
    print(json.dumps(cohort, indent=2), flush=True)
    plot_timing(cohort, save_dir / "trd_rate_by_prescription_timing.png")
    print(f"Wrote {save_dir}", flush=True)


if __name__ == "__main__":
    import sys
    replot() if "--replot" in sys.argv[1:] else main()
