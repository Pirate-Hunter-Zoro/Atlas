"""Logistic-regression-weighted nearest neighbors across the four encoders.

Reads each encoder's neighbor_count_sweep outputs and its fitted embedded logistic
regression, refits nothing, and writes three figures and one table:

  * neighbor_count_sweep_panels.png: manuscript Figure 5, the Figure-4-style plot for
    the three non-primary encoders as panels A-C, one above the other, sharing one
    legend row (below);
  * embedding_dimensions_vs_lr_dimensions.png: each encoder's embedding width against
    how many dimensions its logistic regression uses, counted two ways (below);
  * lr_dimensions_vs_best_k.png: the 90%-mass count against each metric's best k.
    Manuscript Figure 6;
  * cross_embedder_retrieval.csv: one row per encoder, every number the figures draw,
    and the source of the manuscript's cross-encoder retrieval numbers.

FIGURE 5 IS ONE PNG, SO IT FITS ONE PAGE WITH ITS CAPTION. It is drawn at the 6in text
width it is placed at, so its type prints at the point sizes set here, and is at most
PANELS_MAX_HEIGHT tall. Every line comes from plot_neighbor_sweep_figure.draw_curves,
the code that draws each encoder's own PNG, from the same files: the sweep's curves and
bands, the encoder's embedded logistic regression from its classical_ml_results JSON,
and feature-vector XGBoost from the primary encoder's, which is the same in every panel.
What the arms and lines are is said once, in the shared legend row; each panel's own
numbers (each arm's best k, ROC AUC and interval there, and its embedded logistic
regression) sit beside that panel. Figure 4 is still the primary encoder's own PNG.

TWO COUNTS OF "DIMENSIONS THE LOGISTIC REGRESSION USES", BECAUSE THE PENALTY DIFFERS.
The grid search picked an elastic-net penalty for bge-en-icl and Qwen3-8B, which zeroes
most coefficients, and an L2 penalty for bge-small and Qwen3-4B, which zeroes none. So
the non-zero count is the width itself for two of the four encoders and says nothing
there. The count of dimensions holding 90% of the absolute coefficient mass is defined
under either penalty and is the one the comparison can rest on.

Best k is chosen on the test patients, so every best-k value here is optimistic, as it
is in each encoder's own sweep.

Outputs land in ARTIFACTS_DIR/cross_embedder_retrieval.
slurm_jobs/quick_runs/plot_cross_embedder_retrieval.sbatch runs it, after every
encoder's neighbor_count_sweep has finished, and mirrors that folder into
results/cross_embedder_retrieval/, which the manuscript links.
"""

import json
import os
from pathlib import Path

import matplotlib
import matplotlib.ticker
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
from scripts.pipeline.predictions import plot_neighbor_sweep_figure as sweep_figure
from scripts.shared.display_names import encoder_display

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

# Figure 5: the encoders it draws, in panel order, and the primary encoder, whose plot is
# Figure 4 and whose feature-vector XGBoost line every panel shares.
PRIMARY_EMBEDDER = "Qwen-Qwen3-Embedding-8B"
PANEL_EMBEDDERS = ("bge-small-en-v1.5", "bge-en-icl", "Qwen-Qwen3-Embedding-4B")
PANELS_FIGURE_NAME = "neighbor_count_sweep_panels.png"
# Inches, drawn at the size it is placed at. The saved PNG is trimmed to its content, so
# PANELS_MAX_HEIGHT is checked on the trimmed image scaled to a 6in width.
PANELS_FIGURE_SIZE = (6.0, 7.0)
PANELS_PLACED_WIDTH = 6.0
PANELS_MAX_HEIGHT = 7.5
# Rows: three panels, then the shared legend. Columns: the plot, then its numbers.
PANELS_HEIGHT_RATIOS = (1.0, 1.0, 1.0, 0.42)
PANELS_WIDTH_RATIOS = (1.7, 1.0)
PANELS_FONT_SIZES = {"tick": 8, "label": 8.5, "title": 9, "legend": 7.5}


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


def plain_log_ticks(axis, ticks) -> None:
    """Label a log axis at these values in plain numbers; log-scale minor labels collide
    over the one-decade ranges these figures span."""
    axis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
    axis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    axis.set_minor_formatter(matplotlib.ticker.NullFormatter())


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
    # Room on the right for the 4,096-wide encoders' labels.
    ax.set_xlim(span[0], span[1] * 2.2)
    plain_log_ticks(ax.xaxis, sorted(set(widths)))
    plain_log_ticks(ax.yaxis, (250, 500, 1000, 2500, 4096))
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
    plain_log_ticks(ax.xaxis, (250, 500, 1000, 2000))
    plain_log_ticks(ax.yaxis, (300, 500, 1000, 1500))
    ax.set_xlim(200, 2500)
    # The upper left holds bge-en-icl's point; the middle of the plot is empty.
    ax.legend(loc="center", frameon=False, fontsize=8)
    ax.grid(True, which="major", color="#e6e6e6", linewidth=0.6)
    fig.tight_layout()
    path = OUT_DIR / "lr_dimensions_vs_best_k.png"
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)
    return path


def panel_inputs(embedder: str, feature_line: tuple) -> dict:
    """What one Figure 5 panel draws, read as plot_neighbor_sweep_figure reads it.

    Args:
        embedder (str): One of PANEL_EMBEDDERS.
        feature_line (tuple): Feature-vector XGBoost's (AUC, ci_low, ci_high), the same
            in every panel.

    Returns:
        dict: curve, intervals, random_curve (None when the sweep wrote none) and
            reference_aucs in plot_neighbor_sweep_figure.REFERENCES order.
    """
    sweep_dir = results_dir(embedder) / SWEEP_DIR_NAME
    random_path = sweep_dir / sweep_figure.RANDOM_CURVE
    (embedded_label, embedded_source, embedded_model, _), (feature_label, *_) = sweep_figure.REFERENCES
    return {
        "curve": pd.read_csv(sweep_dir / "sweep_curve.csv"),
        "intervals": pd.read_csv(sweep_dir / "sweep_intervals.csv"),
        "random_curve": pd.read_csv(random_path) if random_path.exists() else None,
        "reference_aucs": {
            embedded_label: sweep_figure.summary_line(
                results_dir(embedder) / f"classical_ml_results_{embedded_source}.json", embedded_model),
            feature_label: feature_line,
        },
    }


def panel_number_label(metric: str, best: pd.Series, low: float, high: float) -> str:
    """An arm's entry beside its panel: best k, then ROC AUC and interval there."""
    return f"best k {int(best.n_neighbors):,}: {best.roc_auc:.3f} ({low:.3f}\u2013{high:.3f})"


def panel_reference_label(label: str, auc: float, low: float, high: float) -> str:
    """A classifier line's entry beside its panel. The shared line is named once, in the
    legend row, so it is left out here."""
    if label == sweep_figure.REFERENCES[0][0]:
        return f"{auc:.3f} ({low:.3f}\u2013{high:.3f})"
    return "_shared"


def shared_legend(figure, axis, feature_line: tuple, has_random: bool) -> None:
    """The one legend row: what each arm and line is, and what its interval is."""
    from matplotlib.lines import Line2D
    marker = dict(marker="o", markersize=6, markeredgecolor="white", markeredgewidth=1.2, linewidth=2)
    entries = [
        (Line2D([], [], color=sweep_figure.METRIC_COLOR["weighted"], **marker),
         f"{sweep_figure.METRIC_DISPLAY['weighted']}\nat best k (95% CI)"),
        (Line2D([], [], color=sweep_figure.METRIC_COLOR["plain"], **marker),
         f"{sweep_figure.METRIC_DISPLAY['plain']} at best k (95% CI)"),
    ]
    if has_random:
        entries.append((Line2D([], [], color=sweep_figure.METRIC_COLOR["random"], **marker),
                        f"{sweep_figure.METRIC_DISPLAY['random']} at best k\n"
                        f"({sweep_figure.INTERVAL_NAME['random']})"))
    auc, low, high = feature_line
    entries += [
        (Line2D([], [], color=sweep_figure.REFERENCE_COLOR, linestyle=sweep_figure.REFERENCE_STYLES[0], linewidth=1.2),
         f"{sweep_figure.REFERENCES[0][0]},\nthe panel's encoder (95% CI)"),
        (Line2D([], [], color=sweep_figure.REFERENCE_COLOR, linestyle=sweep_figure.REFERENCE_STYLES[1], linewidth=1.2),
         f"{sweep_figure.REFERENCES[1][0]}, every panel:\n{auc:.3f} (95% CI {low:.3f}\u2013{high:.3f})"),
    ]
    handles, labels = zip(*entries)
    axis.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
                frameon=False, fontsize=PANELS_FONT_SIZES["legend"], handlelength=2.4,
                labelspacing=0.6, columnspacing=1.6)


def build_panels(panels: list[tuple[str, dict]], feature_line: tuple):
    """Figure 5, unsaved: one row per encoder, numbers beside each, one shared legend row.

    Args:
        panels (list[tuple[str, dict]]): (encoder, panel_inputs) in panel order.
        feature_line (tuple): Feature-vector XGBoost's (AUC, ci_low, ci_high).

    Returns:
        tuple: (figure, list of plot axes in panel order).
    """
    figure = plt.figure(figsize=PANELS_FIGURE_SIZE)
    grid = figure.add_gridspec(nrows=len(panels) + 1, ncols=2, height_ratios=PANELS_HEIGHT_RATIOS,
                               width_ratios=PANELS_WIDTH_RATIOS, hspace=0.42, wspace=0.04)
    axes = []
    for row, (embedder, inputs) in enumerate(panels):
        axis = figure.add_subplot(grid[row, 0], sharex=axes[0] if axes else None)
        sweep_figure.draw_curves(axis, inputs["curve"], inputs["intervals"], inputs["reference_aucs"],
                                 inputs["random_curve"], arm_label=panel_number_label,
                                 reference_label=panel_reference_label)
        axis.set_title(f"{chr(ord('A') + row)}   {encoder_display(embedder)}", loc="left",
                       fontsize=PANELS_FONT_SIZES["title"], fontweight="bold")
        axis.set_ylabel(sweep_figure.Y_LABEL, fontsize=PANELS_FONT_SIZES["label"])
        axis.tick_params(axis="both", which="major", labelsize=PANELS_FONT_SIZES["tick"])
        if row < len(panels) - 1:
            axis.tick_params(axis="x", which="both", labelbottom=False)
        numbers = figure.add_subplot(grid[row, 1])
        numbers.axis("off")
        handles, labels = axis.get_legend_handles_labels()
        numbers.legend(handles, labels, loc="center left", frameon=False,
                       fontsize=PANELS_FONT_SIZES["legend"], handlelength=2.0, labelspacing=0.55)
        axes.append(axis)
    axes[-1].set_xlabel(sweep_figure.X_LABEL, fontsize=PANELS_FONT_SIZES["label"])
    legend_axis = figure.add_subplot(grid[len(panels), :])
    legend_axis.axis("off")
    shared_legend(figure, legend_axis, feature_line,
                  any(inputs["random_curve"] is not None for _, inputs in panels))
    return figure, axes


def placed_height(path: Path, width: float = PANELS_PLACED_WIDTH) -> float:
    """The saved PNG's height in inches when it is placed at width inches."""
    from PIL import Image
    with Image.open(path) as image:
        pixels_wide, pixels_high = image.size
    return width * pixels_high / pixels_wide


def plot_sweep_panels() -> Path:
    """Write Figure 5 and refuse it if it would not fit a page with its caption.

    Returns:
        Path: The PNG written.

    Raises:
        ValueError: If the PNG placed at PANELS_PLACED_WIDTH is taller than PANELS_MAX_HEIGHT.
    """
    feature_label, feature_source, feature_model, _ = sweep_figure.REFERENCES[1]
    feature_line = sweep_figure.summary_line(
        results_dir(PRIMARY_EMBEDDER) / f"classical_ml_results_{feature_source}.json", feature_model)
    panels = [(embedder, panel_inputs(embedder, feature_line)) for embedder in PANEL_EMBEDDERS]
    figure, _ = build_panels(panels, feature_line)
    path = OUT_DIR / PANELS_FIGURE_NAME
    figure.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    height = placed_height(path)
    if height > PANELS_MAX_HEIGHT:
        raise ValueError(f"{path.name} is {height:.2f}in tall at {PANELS_PLACED_WIDTH:g}in wide, "
                         f"over the {PANELS_MAX_HEIGHT:g}in that fits a page with its caption.")
    return path


def main():
    missing = [e for e in EMBEDDERS if not (results_dir(e) / SWEEP_DIR_NAME / "sweep_summary.json").exists()]
    if missing:
        raise FileNotFoundError(f"No neighbor_count_sweep for {missing}; run that sweep first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame([encoder_row(e) for e in EMBEDDERS]).set_index("embedder", drop=False)
    table.to_csv(OUT_DIR / "cross_embedder_retrieval.csv", index=False)
    print(table.drop(columns="embedder").T.to_string(), flush=True)
    for path in (plot_sweep_panels(), plot_dimension_counts(table), plot_dimensions_vs_best_k(table)):
        print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
