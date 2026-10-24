"""Guards on the figure text the 2026-10-06 pre-circulation review asked to change.

(a) Figure 4: no best-k label sits on the plot; each arm's best k, value and interval
    are in a legend entry. Figure 4 is one PNG, all four encoders as panels A-D over one
    shared legend row, that fits a page with its caption at 6in wide; each panel names
    its embedding width, and a best k is a marker, never the line an arm is drawn as.
(b) Figure 3: 300 dpi, the paper's encoder names, panel B called concept permutation and
    its axis permuted minus baseline.
(c) Every confusion-matrix panel prints "F score", never the variable name, and the
    manuscript panels (S5 A-B, S13) carry the same bootstrap intervals the best-k ones do.
(d) Display names: classifiers, the S11 retrieval arm, the random arm's interval label,
    three-decimal ROC and PR legends.
(e) Figure S6 draws both distributions as densities, so the neighbour pairs show.
(f) Figure S7's pair histograms, accumulated by block, equal the all-pairs histograms,
    and a wrong driving token writes no PNG.

Synthetic data only; nothing here reads a real RESULTS_DIR.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.figure
import matplotlib.pyplot as plt
from matplotlib.text import Text
from PIL import Image

sys.path.append(str(Path(__file__).parent.parent))

from scripts.shared import plots
from scripts.shared.display_names import CLASSIFIER_DISPLAY
from scripts.pipeline.predictions import plot_neighbor_sweep_figure as sweep_figure
from scripts.pipeline.predictions import plot_cross_embedder_retrieval as cross_retrieval
from scripts.pipeline.predictions import plot_cross_embedder as cross_embedder
from scripts.pipeline.predictions import redraw_manuscript_panels
from scripts.pipeline.predictions import redraw_ablation_forest
from scripts.pipeline.predictions import trd_sanity_checks
from scripts.pipeline.predictions import feature_importance as fi
from scripts.pipeline.review import bge_small_token_decomposition as s7
from scripts.pipeline.review.subgroups import run_subgroups


@pytest.fixture
def saved_text(monkeypatch):
    """Every text string in each figure saved during the test, keyed by file name."""
    captured = {}
    real_savefig = matplotlib.figure.Figure.savefig

    def capturing(self, fname, *args, **kwargs):
        captured[Path(str(fname)).name] = [t.get_text() for t in self.findobj(Text) if t.get_text()]
        return real_savefig(self, fname, *args, **kwargs)

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", capturing)
    return captured


def labelled_predictions(n=600, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.2).astype(int)
    return y, np.clip(0.2 + 0.15 * y + rng.normal(0, 0.1, n), 0.001, 0.999)


# ---------------------------------------------------------------------------
# (a) Figure 4
# ---------------------------------------------------------------------------
def sweep_inputs():
    ks = np.arange(1, 3001)
    lk = np.log10(ks)
    lines = {"weighted": 0.51 + 0.03 * lk, "plain": 0.515 + 0.025 * lk}
    curve = pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": ks, "roc_auc": v})
                       for m, v in lines.items()])
    iks = np.array([1, 10, 100, 1000, 3000])
    intervals = pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": iks,
                                         "roc_auc": v[iks - 1], "ci_low": v[iks - 1] - 0.01,
                                         "ci_high": v[iks - 1] + 0.01}) for m, v in lines.items()])
    random_curve = pd.DataFrame({"n_neighbors": ks, "roc_auc": 0.5, "ci_low": 0.484, "ci_high": 0.515})
    references = {"EMBEDDED logistic regression": (0.645, 0.629, 0.660),
                  "FEATURE XGBoost": (0.649, 0.634, 0.664)}
    return curve, intervals, references, random_curve


def test_best_k_numbers_are_in_the_legend_not_on_the_curves():
    figure, axis = sweep_figure.build(*sweep_inputs())
    assert len(axis.texts) == 0, "no annotation may sit on the plot"
    legend = [a.get_legend() for a in figure.axes if a.get_legend() is not None][0]
    labels = [t.get_text() for t in legend.get_texts()]
    arms = [label for label in labels if "best k =" in label]
    assert len(arms) == 3
    assert "best k = 3,000: 0.614 (95% CI 0.604–0.624)" in arms[0]
    random_label = [label for label in arms if label.startswith("Random")][0]
    assert "percentile of draws 0.484–0.515" in random_label and "95% CI" not in random_label
    assert all(t.get_fontsize() >= 12 for t in legend.get_texts())
    assert min(t.get_fontsize() for t in axis.get_xticklabels()) >= 12
    plt.close(figure)


def test_sweep_figure_is_written_at_300_dpi(tmp_path):
    curve, intervals, references, random_curve = sweep_inputs()
    path = tmp_path / "figure.png"
    sweep_figure.draw(curve, intervals, references, path, random_curve)
    dpi = Image.open(path).info["dpi"]
    assert round(dpi[0]) == 300


def write_panel_sweep(directory: Path, embedded_auc: tuple, width: int = 4096) -> None:
    """The files Figure 4 reads for one encoder, from sweep_inputs."""
    curve, intervals, _, random_curve = sweep_inputs()
    sweep = directory / sweep_figure.SWEEP_DIR_NAME
    sweep.mkdir(parents=True)
    curve.to_csv(sweep / "sweep_curve.csv", index=False)
    intervals.to_csv(sweep / "sweep_intervals.csv", index=False)
    random_curve.to_csv(sweep / sweep_figure.RANDOM_CURVE, index=False)
    (sweep / "sweep_summary.json").write_text(json.dumps({"dimension_importance": {"n_dimensions": width}}))
    (directory / "classical_ml_results_EMBEDDED.json").write_text(json.dumps({"logistic_regression": dict(
        zip(("roc_score", "roc_score_ci_low", "roc_score_ci_high"), embedded_auc))}))


def test_figure_4_is_one_png_that_fits_a_page(tmp_path, monkeypatch, saved_text):
    embedded = {"bge-small-en-v1.5": (0.645, 0.629, 0.660), "bge-en-icl": (0.655, 0.641, 0.670),
                "Qwen-Qwen3-Embedding-4B": (0.656, 0.642, 0.671),
                "Qwen-Qwen3-Embedding-8B": (0.657, 0.643, 0.672)}
    widths = {"bge-small-en-v1.5": 384, "bge-en-icl": 4096, "Qwen-Qwen3-Embedding-4B": 2560,
              "Qwen-Qwen3-Embedding-8B": 4096}
    for name, auc in embedded.items():
        write_panel_sweep(tmp_path / name, auc, widths[name])
    (tmp_path / cross_retrieval.PRIMARY_EMBEDDER / "classical_ml_results_FEATURE.json").write_text(
        json.dumps({"xgboost": dict(roc_score=0.649, roc_score_ci_low=0.634, roc_score_ci_high=0.664)}))
    monkeypatch.setattr(cross_retrieval, "results_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(cross_retrieval, "OUT_DIR", tmp_path)

    path = cross_retrieval.plot_sweep_panels()
    assert path == tmp_path / "neighbor_count_sweep_panels.png"
    assert cross_retrieval.placed_height(path) <= 7.5
    assert round(Image.open(path).info["dpi"][0]) == 300
    text = saved_text[path.name]
    titles = [t for t in text if re.match(r"^[ABCD]   ", t)]
    assert titles == ["A   bge-small-en-v1.5", "B   bge-en-icl", "C   Qwen3-Embedding-4B",
                      "D   Qwen3-Embedding-8B"]
    for width in ("384", "4,096", "2,560"):
        assert f"{width} embedding dimensions" in text
    # Each panel carries its own nearest-arm numbers; the random arm and the shared line
    # are named once, in the legend row.
    assert sum("best k = 3,000: 0.614 (0.604\u20130.624)" == t for t in text) == 4
    for auc, low, high in embedded.values():
        assert f"{auc:.3f} ({low:.3f}\u2013{high:.3f})" in text
    assert sum("Feature-vector XGBoost" in t for t in text) == 1
    assert "0.649 (95% CI 0.634\u20130.664)" in [t for t in text if "Feature-vector XGBoost" in t][0]
    random_entries = [t for t in text if t.startswith("Random neighbors")]
    assert len(random_entries) == 1 and "percentile of draws" in random_entries[0]


def test_figure_4_draws_a_best_k_differently_from_an_arm():
    """In the legends an arm is a line with no marker and a best k is a marker with no line."""
    curve, intervals, references, random_curve = sweep_inputs()
    inputs = {"curve": curve, "intervals": intervals, "random_curve": random_curve,
              "reference_aucs": references, "n_dimensions": 4096}
    figure, axes = cross_retrieval.build_panels([("bge-en-icl", inputs)] * 4, references["FEATURE XGBoost"])
    legends = [a.get_legend() for a in figure.axes if a.get_legend() is not None]
    arms, bests = [], []
    for legend in legends:
        for handle, text in zip(legend.legend_handles, legend.get_texts()):
            if handle.get_color() not in sweep_figure.METRIC_COLOR.values() and "Best k" not in text.get_text():
                continue
            (bests if handle.get_marker() not in (None, "None", "") else arms).append(handle)
    assert arms and bests
    assert all(h.get_linestyle() != "None" and h.get_marker() in (None, "None", "") for h in arms)
    assert all(h.get_linestyle() == "None" and h.get_marker() == "D" for h in bests)
    plt.close(figure)


def test_figure_4_draws_what_each_encoders_own_figure_draws():
    """The composite and the single-encoder figure plot identical curves from the same inputs."""
    curve, intervals, references, random_curve = sweep_inputs()
    single, single_axis = sweep_figure.build(curve, intervals, references, random_curve)
    inputs = {"curve": curve, "intervals": intervals, "random_curve": random_curve,
              "reference_aucs": references, "n_dimensions": 4096}
    panels, axes = cross_retrieval.build_panels([("bge-en-icl", inputs)] * 4, references["FEATURE XGBoost"])
    def curves(axis):
        return [(tuple(line.get_xdata()), tuple(line.get_ydata()), line.get_color(), line.get_linestyle())
                for line in axis.get_lines() if len(line.get_xdata()) > 1 and line.get_linestyle() == "-"]
    for axis in axes:
        assert curves(axis) == curves(single_axis)
        assert axis.get_ylim() == single_axis.get_ylim()
    plt.close(single)
    plt.close(panels)


# ---------------------------------------------------------------------------
# (b) Figure 3
# ---------------------------------------------------------------------------
def cross_inputs():
    aucs = np.array([[0.629, 0.645, 0.660], [0.640, 0.655, 0.670],
                     [0.640, 0.655, 0.670], [0.643, 0.657, 0.672]])
    deltas = np.stack([np.array([[-0.038, -0.027, -0.017], [-0.032, -0.022, -0.013]])] * 4)
    return aucs, deltas


def test_figure_3_names_permutation_and_the_full_encoders(tmp_path, saved_text):
    names = ["bge-small-en-v1.5", "bge-en-icl", "Qwen3-Embedding-4B", "Qwen3-Embedding-8B"]
    path = cross_embedder.draw(*cross_inputs(), names, tmp_path / "figure3.png")
    text = saved_text["figure3.png"]
    assert any("Concept permutation" in t for t in text)
    assert any("permuted − baseline" in t for t in text)
    assert not any("ablat" in t.lower() for t in text)
    for name in names:
        assert name in text
    assert round(Image.open(path).info["dpi"][0]) == 300


def test_figure_3_legend_sits_off_the_points():
    figure, (_, right) = cross_embedder.build(*cross_inputs(), ["a", "b", "c", "d"])
    anchor = right.get_legend().get_bbox_to_anchor().transformed(right.transAxes.inverted())
    assert anchor.y0 < 0, "the legend is under the panel, not over its intervals"
    plt.close(figure)


# ---------------------------------------------------------------------------
# (c) confusion matrices and the manuscript panels
# ---------------------------------------------------------------------------
def test_no_metric_label_is_a_variable_name():
    for label in list(plots.CONFUSION_METRIC_LABELS.values()) + list(plots.CONFUSION_METRIC_SHORT_LABELS.values()):
        assert "_" not in label
    assert plots.CONFUSION_METRIC_LABELS["f_score"] == "F score"


def test_manuscript_panels_carry_bootstrap_intervals(tmp_path, monkeypatch, saved_text):
    monkeypatch.setattr(plots, "RESULTS_DIR", tmp_path)
    y, p = labelled_predictions()
    redraw_manuscript_panels.redraw_one(y, p, "logistic_regression_EMBEDDED")
    confusion = "\n".join(saved_text["confusion_matrix_logistic_regression_EMBEDDED.png"])
    assert "F score" in confusion and "F_Score" not in confusion
    assert "(95% CI, bootstrap)" in confusion
    assert re.search(r"Sensitivity: \d\.\d\d \(\d\.\d\d–\d\.\d\d\)", confusion)
    assert "Model (95% CI)" in saved_text["calibration_curve_logistic_regression_EMBEDDED.png"]


def test_roc_and_pr_legends_print_three_decimals(tmp_path, saved_text):
    y, p = labelled_predictions()
    plots.plot_receiving_operator_characteristic(y, p, "m", save_dir=tmp_path)
    plots.plot_precision_recall(y, p, "m", save_dir=tmp_path)
    roc = "\n".join(saved_text["roc_curve_m.png"])
    pr = "\n".join(saved_text["pr_curve_m.png"])
    assert re.search(r"ROC AUC \d\.\d{3} \(95% CI \d\.\d{3}–\d\.\d{3}\)", roc)
    assert re.search(r"Average precision \d\.\d{3} \(95% CI \d\.\d{3}–\d\.\d{3}\)", pr)
    assert re.search(r"No skill \(prevalence \d\.\d{3}\)", pr)


def test_random_draw_panels_never_say_95_percent_ci(tmp_path, saved_text):
    y, p = labelled_predictions()
    label = plots.RANDOM_DRAW_INTERVAL_LABEL
    plots.plot_receiving_operator_characteristic(y, p, "r", save_dir=tmp_path, interval_label=label)
    plots.plot_optimal_confusion_matrix(y, p, "r", save_dir=tmp_path, bootstrap=True, interval_label=label)
    roc = "\n".join(saved_text["roc_curve_r.png"])
    confusion = "\n".join(saved_text["confusion_matrix_r.png"])
    assert "representative draw" in roc and "95% CI [" not in roc and "(95% CI " not in roc
    assert "representative draw" in confusion.replace("\n", " ")
    assert "(95% CI, bootstrap)" not in confusion


def test_youden_operating_point_is_what_the_panel_prints(tmp_path):
    y, p = labelled_predictions()
    drawn = plots.plot_optimal_confusion_matrix(y, p, "o", save_dir=tmp_path, bootstrap=True)
    assert drawn == plots.youden_operating_point(y, p, bootstrap=True)


# ---------------------------------------------------------------------------
# (d) display names
# ---------------------------------------------------------------------------
def test_feature_importance_titles_use_display_names(tmp_path, monkeypatch, saved_text):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    fi.plot_feature_importance(np.array([0.3, 0.2, 0.1]), ["a", "b", "c"], "xgboost", top_k=3)
    assert any(t.startswith("XGBoost\n") for t in saved_text["feature_importance_xgboost.png"])
    fi.draw_pca_sweep("logistic_regression", [1, 2, 4], [0.6, 0.62, 0.63], tmp_path / "pca.png")
    assert "Logistic regression, embedded representation" in saved_text["pca.png"]
    assert not any("logistic_regression" in t for t in saved_text["pca.png"])


def test_knees_are_the_fewest_dimensions_holding_the_mass():
    magnitudes = np.array([-5.0, 3.0, 1.0, 1.0])     # cumulative shares 0.5, 0.8, 0.9, 1.0
    assert fi.knees(magnitudes) == (2, 3)


def test_a_redraw_never_refits(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    with pytest.raises(fi.CacheMiss):
        fi.refit_best_model("logistic_regression", fi.VectorSource.EMBEDDED, None, None, cache_only=True)


def test_permutation_forest_titles_use_display_names(tmp_path, saved_text):
    rows = []
    baseline = {}
    for clf in redraw_ablation_forest.CLASSIFIER_ORDER:
        baseline[clf] = {"roc_score": 0.65, "roc_score_ci_low": 0.63, "roc_score_ci_high": 0.67}
        for spec in redraw_ablation_forest.DISPLAY:
            rows.append({"spec_id": spec, "classifier": clf, "roc_score": 0.63, "roc_score_ci_low": 0.61,
                         "roc_score_ci_high": 0.65, "delta_roc_score": 0.63 - 0.65})
    pd.DataFrame(rows).to_csv(tmp_path / "ablation_summary.csv", index=False)
    (tmp_path / "classical_ml_results_EMBEDDED.json").write_text(json.dumps(baseline))
    redraw_ablation_forest.redraw(tmp_path)
    text = saved_text["ablation_roc_ci_EMBEDDED.png"]
    for clf in redraw_ablation_forest.CLASSIFIER_ORDER:
        assert CLASSIFIER_DISPLAY[clf] in text
    assert "xgboost" not in text


def test_subgroup_forest_names_the_retrieval_arm_as_the_paper_does():
    label = run_subgroups.ARM_LABELS[run_subgroups.ARM_KNN]
    assert "logistic-regression-weighted" in label and "importance" not in label


# ---------------------------------------------------------------------------
# (e) Figure S6
# ---------------------------------------------------------------------------
def test_cosine_panel_shows_both_distributions(tmp_path):
    rng = np.random.default_rng(3)
    random_sims = rng.normal(0.5, 0.1, 200_000)
    neighbor_sims = rng.normal(0.85, 0.02, 500)
    figure, axis = trd_sanity_checks.draw_cosine_densities(random_sims, neighbor_sims, tmp_path / "s6.png",
                                                           title="bge-en-icl", n_neighbors=50)
    top = axis.get_ylim()[1]
    peaks = [max(p.get_path().vertices[:, 1]) for p in axis.patches]
    assert len(peaks) == 4                      # a fill and an outline per distribution
    assert min(peaks) > 0.1 * top, "each distribution reaches at least a tenth of the axis"
    assert axis.get_ylabel() == "Density"
    labels = [t.get_text() for t in axis.get_legend().get_texts()]
    assert labels == ["Random pairs", "Nearest-neighbor pairs (k = 50 per patient)"]
    plt.close(figure)


# ---------------------------------------------------------------------------
# (f) Figure S7
# ---------------------------------------------------------------------------
def test_blockwise_pair_histograms_equal_all_pairs():
    rng = np.random.default_rng(4)
    vectors = rng.normal(size=(57, 6)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    contains = rng.random(57) < 0.4
    counts = s7.decomposition_counts(vectors, contains, bins=20, row_block=8)
    sims = vectors @ vectors.T
    rows, cols = np.triu_indices(57, k=1)
    pair = sims[rows, cols]
    differ = contains[rows] ^ contains[cols]
    edges = np.linspace(pair.min(), pair.max(), 21)
    assert np.allclose(counts["edges"], edges)
    assert np.array_equal(counts["all"], np.histogram(pair, bins=edges)[0])
    assert np.array_equal(counts["differ"], np.histogram(pair[differ], bins=edges)[0])
    assert np.array_equal(counts["same"], np.histogram(pair[~differ], bins=edges)[0])


def test_cluster_token_is_the_one_that_splits_the_clusters():
    rng = np.random.default_rng(5)
    a = rng.normal([1, 0, 0], 0.05, size=(30, 3))
    b = rng.normal([0, 1, 0], 0.05, size=(30, 3))
    vectors = np.vstack([a, b]).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    texts = ["mdd recurrent episode note"] * 30 + ["mdd single note"] * 30
    labels, token = s7.cluster_vectors(vectors, texts, seed=42)
    assert token in {"recurrent", "episode", "single"}
    assert len(set(labels[:30])) == 1 and len(set(labels[30:])) == 1


def test_figure_s7_panel_b_is_titled_cluster_a(tmp_path, saved_text):
    counts = {"edges": np.linspace(0, 1, 4), "all": np.array([1, 2, 3]),
              "differ": np.array([0, 1, 1]), "same": np.array([1, 1, 2])}
    s7.draw(counts, "recurrent", "Cluster A: pairs split by agreement on 'recurrent'", [tmp_path / "b.png"])
    text = saved_text["b.png"]
    assert "Cluster A: pairs split by agreement on 'recurrent'" in text
    assert not any("Cluster 0" in t for t in text)


def test_figure_s7_writes_nothing_when_a_token_is_not_the_expected_one(tmp_path, monkeypatch, capsys):
    rng = np.random.default_rng(6)
    a = rng.normal([1, 0, 0], 0.05, size=(40, 3))
    b = rng.normal([0, 1, 0], 0.05, size=(40, 3))
    vectors = np.vstack([a, b]).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    texts = ["mdd recurrent episode note"] * 40 + ["mdd single note"] * 40
    monkeypatch.setenv("SEED", "42")
    monkeypatch.setattr(s7, "load_bge_small", lambda: (vectors, texts))
    monkeypatch.setattr(s7, "OUTPUT_DIRS", (tmp_path / "results", tmp_path / "notebooks"))
    monkeypatch.setattr(s7, "EXPECTED_TOKENS", {"cohort": "not-a-token", "cluster_a": "not-a-token"})
    drawn = []
    monkeypatch.setattr(s7, "draw", lambda *args, **kwargs: drawn.append(args))
    assert s7.main() != 0
    assert drawn == [] and not any(tmp_path.rglob("*.png"))
    relay = [line for line in capsys.readouterr().out.splitlines() if line.startswith("RELAY:")]
    assert "RELAY: S7 cohort token is the expected one: no" in relay
    assert relay[-1].startswith("RELAY: S7 not drawn")
