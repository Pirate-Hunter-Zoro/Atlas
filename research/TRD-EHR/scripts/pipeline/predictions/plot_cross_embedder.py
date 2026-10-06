"""Manuscript Figure 3: embedded logistic regression across the four encoders.

Panel A is each encoder's test ROC AUC with its bootstrap 95% CI, from
classical_ml_results_EMBEDDED.json. Panel B is the change in ROC AUC when a concept is
permuted in the narratives (permuted minus baseline), with its paired bootstrap 95% CI,
from each encoder's ablation_summary.csv. Nothing is refit; this reads two files per
encoder and draws.

The figure is placed at the 6in text width, so it is drawn at that width's proportions,
saved at 300 dpi, and its type is set in points that survive the placement. Encoders are
named as the caption names them, and panel B says "permutation", the paper's word for
what was done, never "ablation".

Output: ARTIFACTS_DIR/cross_embedder_robustness_EMBEDDED.png
"""

import os
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dotenv import load_dotenv
load_dotenv()

from scripts.shared.utils import VectorSource
from scripts.shared.display_names import encoder_display
from scripts.data_loading.ablation_registry import ABLATIONS

ABLATION_SPECS = ["permute_psych_history", "permute_med_burden"]
ABLATION_NAMES = [next(a['display'] for a in ABLATIONS if a['id'] == spec) for spec in ABLATION_SPECS]

EMBEDDERS = ["bge-small-en-v1.5", "bge-en-icl", "Qwen-Qwen3-Embedding-4B", "Qwen-Qwen3-Embedding-8B"]
# Short annotations for plot_cross_embedder_retrieval (Figure 6). Figure 3 prints the
# full names, encoder_display.
SHORT_NAME_EMBS = ["bge-small", "bge-en-icl", "Qwen3-4B", "Qwen3-8B"]

FIGURE_NAME = f"cross_embedder_robustness_{VectorSource.EMBEDDED.name}.png"
FIGURE_SIZE = (10.0, 4.6)
FIGURE_DPI = 300
# At 6in a 10in canvas is a 0.6 downscale, so these print at about 8-9pt.
FONT_SIZES = {"tick": 14, "label": 15, "title": 16, "legend": 14}
# Categorical slots 1 and 2 of the palette plot_neighbor_sweep_figure uses.
SPEC_COLORS = ("#2a78d6", "#eb6834")
REFERENCE_COLOR = "#555555"


def encoding_dirs() -> list[Path]:
    """Each encoder's RESULTS_DIR, in EMBEDDERS order."""
    artifacts = Path(os.environ['ARTIFACTS_DIR'])
    return [artifacts / name / os.environ['VLLM_MODEL_NAME'] for name in EMBEDDERS]


def load_inputs(dirs: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    """Read every number the figure draws.

    Args:
        dirs (list[Path]): One RESULTS_DIR per encoder, in EMBEDDERS order.

    Returns:
        tuple[np.ndarray, np.ndarray]: (aucs of shape (n_encoders, 3) holding ci_low,
            value, ci_high; deltas of shape (n_encoders, n_specs, 3), the same layout).
    """
    for directory in dirs:
        if not ((directory / f"classical_ml_results_{VectorSource.EMBEDDED.name}.json").exists()
                and (directory / "ablation_summary.csv").exists()):
            raise FileNotFoundError(
                f"Cannot run cross-embedder display as {directory} is missing some of its result files...")
    aucs = np.zeros((len(dirs), 3))
    deltas = np.zeros((len(dirs), len(ABLATION_SPECS), 3))
    for i, directory in enumerate(dirs):
        results = json.loads((directory / f"classical_ml_results_{VectorSource.EMBEDDED.name}.json").read_text())
        lr = results['logistic_regression']
        aucs[i] = (lr['roc_score_ci_low'], lr['roc_score'], lr['roc_score_ci_high'])
        summary = pd.read_csv(directory / "ablation_summary.csv")
        rows = summary[(summary['classifier'] == 'logistic_regression')
                       & summary['spec_id'].isin(ABLATION_SPECS)].set_index('spec_id')
        for j, spec in enumerate(ABLATION_SPECS):
            deltas[i, j] = (rows.loc[spec, 'delta_roc_score_ci_low'], rows.loc[spec, 'delta_roc_score'],
                            rows.loc[spec, 'delta_roc_score_ci_high'])
    return aucs, deltas


def _errors(block: np.ndarray) -> np.ndarray:
    """errorbar's (2, n) distances from (n, 3) rows of ci_low, value, ci_high."""
    return np.vstack([block[:, 1] - block[:, 0], block[:, 2] - block[:, 1]])


def build(aucs: np.ndarray, deltas: np.ndarray, names: list[str]):
    """The two-panel figure, unsaved.

    Args:
        aucs (np.ndarray): (n_encoders, 3), as load_inputs.
        deltas (np.ndarray): (n_encoders, n_specs, 3), as load_inputs.
        names (list[str]): Encoder display names, top to bottom.

    Returns:
        tuple: (figure, (left_axis, right_axis)).
    """
    figure, (left, right) = plt.subplots(nrows=1, ncols=2, figsize=FIGURE_SIZE, sharey=True)
    positions = np.arange(len(names))
    left.errorbar(aucs[:, 1], positions, xerr=_errors(aucs), fmt='o', color='#333333',
                  markersize=7, capsize=5, linewidth=1.6)
    left.axvline(0.5, color=REFERENCE_COLOR, linestyle=':', linewidth=1.2)
    left.set_xlabel("ROC AUC (95% CI)", fontsize=FONT_SIZES["label"])
    left.set_title("A  Embedded logistic regression", fontsize=FONT_SIZES["title"], loc='left')

    n = len(ABLATION_SPECS)
    offset = 0.36 / max(n - 1, 1)
    for j, (name, color) in enumerate(zip(ABLATION_NAMES, SPEC_COLORS)):
        right.errorbar(deltas[:, j, 1], positions + (j - (n - 1) / 2) * offset,
                       xerr=_errors(deltas[:, j, :]), fmt='o', color=color, markersize=7,
                       capsize=5, linewidth=1.6, label=name)
    right.axvline(0.0, color=REFERENCE_COLOR, linestyle=':', linewidth=1.2)
    right.set_xlabel("Δ ROC AUC (permuted − baseline)", fontsize=FONT_SIZES["label"])
    right.set_title("B  Concept permutation", fontsize=FONT_SIZES["title"], loc='left')
    # Under panel B, in one row: beside the panels it took a third of the canvas, and
    # inside them it covers an encoder's intervals.
    legend = right.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=n,
                          fontsize=FONT_SIZES["legend"], frameon=False, handletextpad=0.3,
                          columnspacing=1.2)
    legend.set_in_layout(False)
    right.set_xlim(right=max(0.006, float(deltas[:, :, 2].max()) + 0.004))

    left.set_yticks(positions, names)
    left.set_ylim(len(names) - 0.5, -0.5)
    for axis in (left, right):
        axis.tick_params(axis='both', labelsize=FONT_SIZES["tick"])
        axis.grid(True, axis='x', color='#e6e6e6', linewidth=0.8)
        axis.set_axisbelow(True)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
    return figure, (left, right)


def draw(aucs: np.ndarray, deltas: np.ndarray, names: list[str], save_path: Path) -> Path:
    """Build the figure and write it at FIGURE_DPI.

    Returns:
        Path: save_path.
    """
    figure, _ = build(aucs, deltas, names)
    figure.tight_layout()
    legends = [a.get_legend() for a in figure.axes if a.get_legend() is not None]
    figure.savefig(save_path, dpi=FIGURE_DPI, bbox_inches='tight', bbox_extra_artists=legends)
    plt.close(figure)
    return save_path


def main():
    aucs, deltas = load_inputs(encoding_dirs())
    path = draw(aucs, deltas, [encoder_display(name) for name in EMBEDDERS],
                Path(os.environ['ARTIFACTS_DIR']) / FIGURE_NAME)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
