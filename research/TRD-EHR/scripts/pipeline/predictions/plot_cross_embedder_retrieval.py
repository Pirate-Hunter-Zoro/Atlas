"""Logistic-regression-weighted nearest neighbors across the four encoders.

Reads each encoder's neighbor_count_sweep outputs and its fitted embedded logistic
regression, refits nothing, and writes three figures and one table:

  * cross_embedder_sweep.png: ROC AUC against k for every encoder, one panel for
    logistic-regression-weighted cosine and one for plain cosine, alpha 1, each curve's
    best k marked;
  * embedding_dimensions_vs_lr_dimensions.png: each encoder's embedding width against
    how many dimensions its logistic regression uses, counted two ways (below);
  * lr_dimensions_vs_best_k.png: that count against each metric's best k. Exploratory,
    and not in the manuscript until the authors decide what it means;
  * cross_embedder_retrieval.csv: one row per encoder, every number the figures draw.

TWO COUNTS OF "DIMENSIONS THE LOGISTIC REGRESSION USES", BECAUSE THE PENALTY DIFFERS.
The grid search picked an elastic-net penalty for bge-en-icl and Qwen3-8B, which zeroes
most coefficients, and an L2 penalty for bge-small and Qwen3-4B, which zeroes none. So
the non-zero count is the width itself for two of the four encoders and says nothing
there. The count of dimensions holding 90% of the absolute coefficient mass is defined
under either penalty and is the one the comparison can rest on.

Best k is chosen on the test patients, so every best-k value here is optimistic, as it
is in each encoder's own sweep.

Outputs land in ARTIFACTS_DIR/cross_embedder_retrieval. Run it with
-m scripts.pipeline.predictions.plot_cross_embedder_retrieval after every encoder's
neighbor_count_sweep has finished.
"""

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

from scripts.shared.utils import VectorSource
from scripts.pipeline.predictions.importance_weighted_knn import (
    IMPORTANCE_MODEL_NAME,
    dimensions_holding_share,
    load_dimension_weights,
)
from scripts.pipeline.predictions.plot_cross_embedder import EMBEDDERS, SHORT_NAME_EMBS

ARTIFACTS_DIR = Path(os.environ['ARTIFACTS_DIR'])
VLLM_MODEL_NAME = os.environ['VLLM_MODEL_NAME']
OUT_DIR = ARTIFACTS_DIR / "cross_embedder_retrieval"
SWEEP_DIR_NAME = "neighbor_count_sweep"
FIGURE_DPI = 300

# The exponent drawn. The per-encoder sweep found alpha 1, 2 and 5 agree within 0.002.
ALPHA = 1.0

# Share of absolute coefficient mass the penalty-independent count is cut at.
MASS_SHARE = 0.90

METRIC_DISPLAY = {
    "weighted": "Logistic-regression-weighted cosine",
    "plain":    "Plain cosine",
}
METRIC_MARKER = {"weighted": "o", "plain": "s"}
# One colour per encoder, in EMBEDDERS order; the first three are the sweep figure's.
EMBEDDER_COLOR = ["#2a78d6", "#eb6834", "#1baf7a", "#4B3F72"]


def results_dir(embedder: str) -> Path:
    """RESULTS_DIR for this encoder and the active judge."""
    return ARTIFACTS_DIR / embedder / VLLM_MODEL_NAME


def encoder_row(embedder: str) -> dict:
    """Every number this module reports for one encoder.

    Args:
        embedder (str): One of EMBEDDERS.

    Returns:
        dict: Width, LR penalty, both dimension counts, LR ROC AUC, and for each metric
            the best k and its AUC with CI and the AUC with every pool patient a neighbor.
    """
    directory = results_dir(embedder)
    cache_path = directory / "trained_models" / f"{IMPORTANCE_MODEL_NAME}_{VectorSource.EMBEDDED.name}.joblib"
    weights, _ = load_dimension_weights(cache_path=cache_path)
    grid = json.loads((directory / f"grid_search_ml_results_{VectorSource.EMBEDDED.name}.json").read_text())
    classifier = json.loads((directory / f"classical_ml_results_{VectorSource.EMBEDDED.name}.json").read_text())
    summary = json.loads((directory / SWEEP_DIR_NAME / "sweep_summary.json").read_text())
    row = {
        "embedder": embedder,
        "n_dimensions": int(weights.size),
        "lr_penalty": grid[IMPORTANCE_MODEL_NAME]["Best Parameters"]["model__penalty"],
        "lr_nonzero_dimensions": int((weights > 0).sum()),
        f"lr_dimensions_holding_{MASS_SHARE:.0%}_mass": dimensions_holding_share(weights, MASS_SHARE),
        "lr_roc_auc": classifier[IMPORTANCE_MODEL_NAME]["roc_score"],
        "lr_roc_auc_ci_low": classifier[IMPORTANCE_MODEL_NAME]["roc_score_ci_low"],
        "lr_roc_auc_ci_high": classifier[IMPORTANCE_MODEL_NAME]["roc_score_ci_high"],
    }
    for metric in METRIC_DISPLAY:
        best = summary["by_metric"][metric][f"{ALPHA:g}"]
        row[f"{metric}_best_k"] = best["best_n_neighbors"]
        row[f"{metric}_best_roc_auc"] = best["best_roc_auc"]
        row[f"{metric}_best_roc_auc_ci_low"] = best["best_roc_auc_ci_low"]
        row[f"{metric}_best_roc_auc_ci_high"] = best["best_roc_auc_ci_high"]
        row[f"{metric}_roc_auc_at_all_neighbors"] = best["roc_auc_at_all_neighbors"]
    row["random_best_roc_auc"] = summary["random"]["best_roc_auc"]
    return row


def plot_sweeps(table: pd.DataFrame) -> Path:
    """ROC AUC against k, one curve per encoder, one panel per metric."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, metric in zip(axes, METRIC_DISPLAY):
        for i, embedder in enumerate(EMBEDDERS):
            curve = pd.read_csv(results_dir(embedder) / SWEEP_DIR_NAME / "sweep_curve.csv")
            curve = curve[(curve["metric"] == metric) & (curve["alpha"] == ALPHA)]
            ax.plot(curve["n_neighbors"], curve["roc_auc"], color=EMBEDDER_COLOR[i],
                    linewidth=1.4, label=SHORT_NAME_EMBS[i])
            best = table.loc[embedder]
            ax.plot(best[f"{metric}_best_k"], best[f"{metric}_best_roc_auc"], marker="o",
                    color=EMBEDDER_COLOR[i], markersize=6, markeredgecolor="white")
        ax.axhline(0.5, color="#555555", linestyle=":", linewidth=1)
        ax.set_xscale("log")
        ax.set_xlabel("Neighbors, k")
        ax.set_title(METRIC_DISPLAY[metric])
        ax.grid(True, which="major", color="#e6e6e6", linewidth=0.6)
    axes[0].set_ylabel("ROC AUC, test patients")
    axes[1].legend(loc="lower right", frameon=False)
    fig.tight_layout()
    path = OUT_DIR / "cross_embedder_sweep.png"
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)
    return path


def plot_dimension_counts(table: pd.DataFrame) -> Path:
    """Embedding width against the dimensions the logistic regression uses."""
    mass_column = f"lr_dimensions_holding_{MASS_SHARE:.0%}_mass"
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    widths = table["n_dimensions"].to_numpy()
    span = np.array([widths.min() / 1.5, widths.max() * 1.5])
    ax.plot(span, span, color="#555555", linestyle="--", linewidth=1, label="Every dimension")
    for i, embedder in enumerate(EMBEDDERS):
        row = table.loc[embedder]
        ax.scatter(row["n_dimensions"], row["lr_nonzero_dimensions"], marker="o", s=60,
                   facecolor="none", edgecolor=EMBEDDER_COLOR[i], linewidth=1.6)
        ax.scatter(row["n_dimensions"], row[mass_column], marker="o", s=60,
                   color=EMBEDDER_COLOR[i])
        ax.annotate(f"{SHORT_NAME_EMBS[i]} ({row['lr_penalty']})",
                    (row["n_dimensions"], row[mass_column]), textcoords="offset points",
                    xytext=(8, -4), fontsize=8, color=EMBEDDER_COLOR[i])
    ax.scatter([], [], marker="o", facecolor="none", edgecolor="#333333", label="Non-zero coefficients")
    ax.scatter([], [], marker="o", color="#333333", label=f"Dimensions holding {MASS_SHARE:.0%} of |coefficient| mass")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*span)
    ax.set_xlabel("Embedding dimensions")
    ax.set_ylabel("Dimensions the logistic regression uses")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.grid(True, which="major", color="#e6e6e6", linewidth=0.6)
    fig.tight_layout()
    path = OUT_DIR / "embedding_dimensions_vs_lr_dimensions.png"
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)
    return path


def plot_dimensions_vs_best_k(table: pd.DataFrame) -> Path:
    """The penalty-independent dimension count against each metric's best k."""
    mass_column = f"lr_dimensions_holding_{MASS_SHARE:.0%}_mass"
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    for metric in METRIC_DISPLAY:
        for i, embedder in enumerate(EMBEDDERS):
            row = table.loc[embedder]
            ax.scatter(row[mass_column], row[f"{metric}_best_k"], marker=METRIC_MARKER[metric],
                       s=60, color=EMBEDDER_COLOR[i],
                       facecolor=EMBEDDER_COLOR[i] if metric == "weighted" else "none",
                       linewidth=1.6)
            if metric == "weighted":
                ax.annotate(SHORT_NAME_EMBS[i], (row[mass_column], row[f"{metric}_best_k"]),
                            textcoords="offset points", xytext=(8, 4), fontsize=8,
                            color=EMBEDDER_COLOR[i])
    for metric in METRIC_DISPLAY:
        ax.scatter([], [], marker=METRIC_MARKER[metric], color="#333333",
                   facecolor="#333333" if metric == "weighted" else "none",
                   label=METRIC_DISPLAY[metric])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(f"LR dimensions holding {MASS_SHARE:.0%} of |coefficient| mass")
    ax.set_ylabel("Best k (chosen on test patients)")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.grid(True, which="major", color="#e6e6e6", linewidth=0.6)
    fig.tight_layout()
    path = OUT_DIR / "lr_dimensions_vs_best_k.png"
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)
    return path


def main():
    missing = [e for e in EMBEDDERS if not (results_dir(e) / SWEEP_DIR_NAME / "sweep_summary.json").exists()]
    if missing:
        raise FileNotFoundError(f"No neighbor_count_sweep for {missing}; run that sweep first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame([encoder_row(e) for e in EMBEDDERS]).set_index("embedder", drop=False)
    table.to_csv(OUT_DIR / "cross_embedder_retrieval.csv", index=False)
    print(table.drop(columns="embedder").T.to_string(), flush=True)
    for path in (plot_sweeps(table), plot_dimension_counts(table), plot_dimensions_vs_best_k(table)):
        print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
