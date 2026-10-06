"""Guards on the panels drawn at each retrieval arm's best k, and on Figure 4.

(a) Each arm's panels must be drawn at THAT arm's best k, with the k in the filename, and
    the AUC redrawn from the saved predictions must be the one the sweep recorded.
(b) Every number the panels print must carry an interval.
(c) Figure 4 must not draw a vertical line at k = 50, and must draw the random arm's band.

Synthetic data only; nothing here reads RESULTS_DIR.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.predictions import best_k_panels, plot_neighbor_sweep_figure
from scripts.pipeline.predictions.neighbor_count_sweep import roc_auc_by_column
from scripts.shared.plots import bootstrap_sample_indices, plot_optimal_confusion_matrix

N = 400
K = {"weighted": 29, "plain": 75, "random": 12}


def interval(y, p):
    """The sweep's own AUC and interval, as intervals_of_columns computes them."""
    point = roc_auc_by_column(y, p[:, None])[0]
    draws = [roc_auc_by_column(y[rows], p[rows][:, None])[0] for rows in bootstrap_sample_indices(y.size)]
    return float(point), float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5))


@pytest.fixture
def results_dir(tmp_path):
    """A RESULTS_DIR holding a sweep's summary and best-k predictions for three arms."""
    rng = np.random.default_rng(0)
    y = (rng.random(N) < 0.2).astype(int)
    sweep = tmp_path / "neighbor_count_sweep"
    sweep.mkdir()
    risks = {
        "weighted": np.clip(0.2 + 0.15 * y + rng.normal(0, 0.1, N), 0, 1),
        "plain": np.clip(0.2 + 0.08 * y + rng.normal(0, 0.1, N), 0, 1),
        "random": rng.binomial(K["random"], 0.2, N) / K["random"],
    }
    files = {"weighted": "best_k_predictions_alpha1.csv", "plain": "best_k_predictions_alpha1_plain.csv",
             "random": "best_k_predictions_random.csv"}
    summary = {"by_metric": {}, "random": {}}
    for arm, risk in risks.items():
        pd.DataFrame({"anchor_patient_id": [f"p{i}" for i in range(N)], "true_label": y,
                      "predicted_risk": risk, "ess": rng.uniform(1, K[arm], N)}).to_csv(sweep / files[arm], index=False)
        risk = pd.read_csv(sweep / files[arm])["predicted_risk"].to_numpy()
        auc, low, high = interval(y, risk)
        if arm == "random":
            summary["random"] = {"best_n_neighbors": K[arm], "best_roc_auc": 0.503, "best_roc_auc_ci_low": 0.49,
                                 "best_roc_auc_ci_high": 0.515, "n_draws": 1000, "representative_draw": 7,
                                 "representative_draw_roc_auc": auc, "representative_draw_roc_auc_ci_low": low,
                                 "representative_draw_roc_auc_ci_high": high}
        else:
            summary["by_metric"][arm] = {"1": {"best_n_neighbors": K[arm], "best_roc_auc": auc,
                                               "best_roc_auc_ci_low": low, "best_roc_auc_ci_high": high}}
    (sweep / "sweep_summary.json").write_text(json.dumps(summary))
    return tmp_path


def every_leaf_number_has_an_interval(node, path="") -> list[str]:
    """Paths of numbers not inside a {value, ci_low, ci_high} block."""
    missing = []
    if isinstance(node, dict):
        if "value" in node:
            if not {"ci_low", "ci_high"} <= set(node):
                missing.append(path)
            return missing
        for key, child in node.items():
            missing += every_leaf_number_has_an_interval(child, f"{path}.{key}")
    return missing


def test_each_arm_is_drawn_at_its_own_best_k(results_dir):
    out = best_k_panels.run(results_dir)
    panels = results_dir / "neighbor_count_sweep" / "best_k_panels"
    assert set(out) == {"weighted", "plain", "random"}
    for arm, prefix in (("weighted", "NEAREST_IMPORTANCE_WEIGHTED_alpha1"),
                        ("plain", "NEAREST_PLAIN_COSINE_alpha1"), ("random", "RANDOM_UNIFORM")):
        mode = f"{prefix}_k{K[arm]}"
        assert out[arm]["mode"] == mode and out[arm]["n_neighbors"] == K[arm]
        for stem in ("roc_curve", "pr_curve", "calibration_curve", "decision_curve",
                     "ess_distribution", "confusion_matrix"):
            assert (panels / f"{stem}_{mode}.png").exists(), f"{stem}_{mode}.png"
    written = json.loads((results_dir / "neighbor_count_sweep" / "best_k_panels.json").read_text())
    assert written["random"]["across_draw_roc_auc"]["n_draws"] == 1000


def test_every_number_on_the_panels_has_an_interval(results_dir):
    out = best_k_panels.run(results_dir)
    for arm, block in out.items():
        for key in ("roc_auc", "average_precision", "metrics"):
            assert every_leaf_number_has_an_interval(block[key]) == [], (arm, key)
        confusion = {k: v for k, v in block["confusion_matrix"].items() if k not in ("threshold", "confusion_matrix")}
        assert len(confusion) == 5 and every_leaf_number_has_an_interval(confusion) == []
        for row in block["calibration_bins"]:
            assert {"observed_ci_low", "observed_ci_high"} <= set(row)
        roc = block["roc_auc"]
        assert roc["ci_low"] <= roc["value"] <= roc["ci_high"]


def test_a_redrawn_auc_that_disagrees_with_the_sweep_is_fatal(results_dir):
    path = results_dir / "neighbor_count_sweep" / "sweep_summary.json"
    summary = json.loads(path.read_text())
    summary["by_metric"]["plain"]["1"]["best_roc_auc"] += 0.01
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError):
        best_k_panels.run(results_dir)


def test_a_missing_random_arm_is_skipped_not_invented(results_dir):
    (results_dir / "neighbor_count_sweep" / "best_k_predictions_random.csv").unlink()
    assert set(best_k_panels.run(results_dir)) == {"weighted", "plain"}


def test_random_arm_panels_label_their_band_as_the_representative_draws(results_dir, monkeypatch):
    """The random arm's spread is the percentile across draws; its panels show one draw, so
    their interval is that draw's bootstrap and never the arm's 95% CI."""
    import matplotlib.figure
    from matplotlib.text import Text
    texts = {}
    real_savefig = matplotlib.figure.Figure.savefig

    def capturing(self, fname, *args, **kwargs):
        texts[Path(str(fname)).name] = " ".join(t.get_text() for t in self.findobj(Text)).replace("\n", " ")
        return real_savefig(self, fname, *args, **kwargs)

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", capturing)
    best_k_panels.run(results_dir)
    mode = f"RANDOM_UNIFORM_k{K['random']}"
    for stem in ("roc_curve", "pr_curve", "calibration_curve", "confusion_matrix"):
        text = texts[f"{stem}_{mode}.png"]
        assert "representative draw" in text, stem
        assert "95% CI " not in text.replace("bootstrap 95% CI of", ""), stem
    weighted = f"NEAREST_IMPORTANCE_WEIGHTED_alpha1_k{K['weighted']}"
    assert "(95% CI, bootstrap)" in texts[f"confusion_matrix_{weighted}.png"]


def test_confusion_matrix_default_is_unchanged_and_bootstrap_adds_intervals(tmp_path):
    rng = np.random.default_rng(3)
    y = (rng.random(300) < 0.3).astype(int)
    p = np.clip(0.3 + 0.2 * y + rng.normal(0, 0.15, 300), 0, 1)
    plain = plot_optimal_confusion_matrix(y, p, "t", save_dir=tmp_path)
    boot = plot_optimal_confusion_matrix(y, p, "u", save_dir=tmp_path, bootstrap=True)
    assert isinstance(plain["sensitivity"], float)
    assert boot["sensitivity"]["value"] == pytest.approx(plain["sensitivity"])
    assert boot["sensitivity"]["ci_low"] <= boot["sensitivity"]["value"] <= boot["sensitivity"]["ci_high"]
    tn, fp = plain["confusion_matrix"][0]
    assert plain["specificity"] == pytest.approx(tn / (tn + fp))
    assert (tmp_path / "confusion_matrix_t.png").exists()


def test_confusion_matrix_survives_a_constant_predictor(tmp_path):
    """The random arm at k = pool gives everyone the prevalence: one class predicted."""
    y = np.array([0, 1, 0, 0, 1, 0])
    out = plot_optimal_confusion_matrix(y, np.full(6, 0.33), "c", save_dir=tmp_path, bootstrap=True)
    assert np.array(out["confusion_matrix"]).shape == (2, 2)


def sweep_frames():
    ks = np.arange(1, 1001)
    curve = pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": ks,
                                     "roc_auc": base + 0.02 * np.log10(ks) / 3})
                       for m, base in (("weighted", 0.60), ("plain", 0.59))])
    sampled = np.array([1, 10, 100, 1000])
    intervals = pd.concat([pd.DataFrame({"metric": m, "alpha": 1.0, "n_neighbors": sampled,
                                         "roc_auc": 0.6, "ci_low": 0.58, "ci_high": 0.63})
                           for m in ("weighted", "plain")])
    random_curve = pd.DataFrame({"n_neighbors": ks, "roc_auc": 0.5 + 0.002 * np.sin(ks),
                                 "ci_low": 0.47, "ci_high": 0.53})
    return curve, intervals, random_curve


def test_figure_four_has_no_line_at_fifty_and_draws_the_random_band(tmp_path, monkeypatch):
    curve, intervals, random_curve = sweep_frames()
    captured = {}
    monkeypatch.setattr(plt.Figure, "savefig", lambda self, *a, **k: captured.setdefault("figure", self))
    references = {"EMBEDDED logistic regression": (0.657, 0.64, 0.67)}
    plot_neighbor_sweep_figure.draw(curve, intervals, references, tmp_path / "f.png", random_curve)
    axis = captured["figure"].axes[0]
    vertical = [line for line in axis.lines
                if len(set(np.atleast_1d(line.get_xdata()))) == 1 and len(line.get_xdata()) == 2]
    assert vertical == []
    assert not any("k = 50" == text.get_text() for text in axis.texts)
    labels = [line.get_label() for line in axis.lines]
    assert any(label.startswith(plot_neighbor_sweep_figure.METRIC_DISPLAY["random"]) for label in labels)
    low, high = axis.get_ylim()
    assert low <= 0.47 and high >= 0.67
    # Each arm's best k is in its legend entry, not written on the plot beside the point.
    assert len(axis.texts) == 0
    assert sum("best k" in text for text in legend_texts(captured["figure"])) == 3
    plt.close("all")


def legend_texts(figure) -> list[str]:
    """Every legend entry's text in a figure, whichever axes holds the legend."""
    return [t.get_text() for a in figure.axes if a.get_legend() is not None
            for t in a.get_legend().get_texts()]


def test_figure_four_still_draws_without_a_random_arm(tmp_path, monkeypatch):
    curve, intervals, _ = sweep_frames()
    captured = {}
    monkeypatch.setattr(plt.Figure, "savefig", lambda self, *a, **k: captured.setdefault("figure", self))
    plot_neighbor_sweep_figure.draw(curve, intervals, {}, tmp_path / "f.png")
    assert sum("best k" in text for text in legend_texts(captured["figure"])) == 2
    plt.close("all")


def test_contrast_against_random_spans_the_draws_not_one_draw():
    """A cosine-minus-random interval must widen with the spread across random draws."""
    rng = np.random.default_rng(7)
    y = (rng.random(400) < 0.3).astype(int)
    scores = y * 0.4 + rng.random(400)
    indices = rng.integers(0, 400, size=(200, 400))
    tight = plot_neighbor_sweep_figure.delta_against_random_draws(y, scores, np.full(50, 0.5), indices)
    wide = plot_neighbor_sweep_figure.delta_against_random_draws(
        y, scores, 0.5 + rng.normal(0, 0.05, 50), indices)
    for result in (tight, wide):
        assert result["ci_low"] < result["delta"] < result["ci_high"]
        assert result["n_draws"] == 50
    assert tight["auc_b"] == pytest.approx(0.5)
    assert (wide["ci_high"] - wide["ci_low"]) > (tight["ci_high"] - tight["ci_low"])
