"""Guards on the round-2 data questions (scripts/pipeline/review/round2_questions.py).

Their answers travel in a public relay report that keeps 40 lines of at most 200
characters, so every question must fit that and print aggregates only. The numbers must
also be the ones the pipeline's own code would give: the curve's risks are the sweep's,
the equal-width calibration fit is compute_metrics', the equal-count bins are the ones
Figure S5 draws, and the operating point is the one the confusion-matrix panel prints.
The curve question prints raw values and no verdict.

Synthetic data only; nothing here reads a real RESULTS_DIR.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.review import round2_questions as q
from scripts.pipeline.predictions.neighbor_count_sweep import risk_at_counts
from scripts.pipeline.predictions.trd_prediction_computation import compute_metrics
from scripts.pipeline.predictions.best_k_panels import ARMS
from scripts.shared.plots import (bootstrap_sample_indices, calibration_bin_edges, plot_calibration,
                                  youden_operating_point)

RELAY_LINES, RELAY_CHARS = 40, 190


def fits_a_report(lines):
    return len(lines) <= RELAY_LINES and all(len(line) <= RELAY_CHARS for line in lines)


# ---------------------------------------------------------------------------
# curve
# ---------------------------------------------------------------------------
def test_curve_grid_covers_the_range_the_end_and_the_trough():
    ks = q.curve_grid(34_063, trough_k=30_017)
    assert ks[0] == 25_000 and ks[-1] == 34_063
    assert {25_250, 30_000, 30_017, 34_000} <= set(ks.tolist())
    assert len(ks) == 39


def test_curve_risks_are_the_sweeps():
    rng = np.random.default_rng(0)
    anchors = rng.normal(size=(40, 5)); anchors /= np.linalg.norm(anchors, axis=1, keepdims=True)
    pool = rng.normal(size=(90, 5)); pool /= np.linalg.norm(pool, axis=1, keepdims=True)
    labels = (rng.random(90) < 0.3).astype(float)
    ks = np.array([1, 7, 45, 89, 90])
    ours, kth, tied = q.risks_and_kth_similarity(anchors, pool, labels, ks, 1.0, 0.3, block=16)
    theirs = risk_at_counts(anchors, pool, labels, ks, (1.0,), 0.3)[1.0]
    assert np.allclose(ours, theirs)
    sorted_sims = -np.sort(-(anchors @ pool.T), axis=1)
    assert np.allclose(kth, sorted_sims[:, ks - 1])
    # Continuous similarities never tie, and the whole pool has no (k+1)-th to tie with.
    assert not tied.any()


def test_ties_at_the_cut_are_counted():
    anchors = np.array([[1.0, 0.0], [0.0, 1.0]])
    # Anchor 0 sees similarities 1, 0.6, 0.6, 0; anchor 1 sees 0, 0.8, 0.6, 1.
    pool = np.array([[1.0, 0.0], [0.6, 0.8], [0.6, 0.6], [0.0, 1.0]])
    ks = np.array([1, 2, 3, 4])
    _, _, tied = q.risks_and_kth_similarity(anchors, pool, np.array([1.0, 0, 1, 0]), ks, 1.0, 0.5)
    assert tied[0].tolist() == [False, True, False, False]
    assert tied[1].tolist() == [False, False, False, False]
    diagnostics = q.curve_diagnostics(np.array([1, 0]), np.array([[0.4] * 4, [0.6] * 4]),
                                      np.zeros((2, 4)), tied)
    assert diagnostics.tied_anchors.tolist() == [0, 1, 0, 0]
    assert diagnostics.nonpositive_anchors.tolist() == [2, 2, 2, 2]


def test_curve_answer_is_raw_values_and_fits_a_report_for_both_encoders():
    ks = q.curve_grid(34_063, trough_k=30_017)
    rng = np.random.default_rng(1)
    diagnostics = pd.DataFrame({"auc64": 0.58 + rng.normal(0, 0.01, ks.size), "auc32": 0.58,
                                "risk_sd": 1e-3, "distinct_risks": 8516, "nonpositive_anchors": 0,
                                "tied_anchors": 12})
    one = q.curve_lines("bge-small-en-v1.5", ks, diagnostics.auc64.to_numpy(), diagnostics, 8516, 34063)
    assert fits_a_report(one + one)
    assert not hasattr(q, "reason_flag")
    assert not any("reason" in line for line in one)
    assert "/12" in one[1] and "tied 12" in one[-1]


# ---------------------------------------------------------------------------
# subgroups
# ---------------------------------------------------------------------------
def contrasts_frame():
    rows = []
    for arm, models in (("EMBEDDED", ["logistic_regression", "random_forest", "gradient_boosting", "xgboost"]),
                        ("FEATURE", ["logistic_regression", "random_forest", "gradient_boosting", "xgboost"]),
                        ("KNN", ["NEAREST_COSINE", "NEAREST_WEIGHTED"])):
        for i, model in enumerate(models):
            for contrast, delta, survives in (("white_minus_non_white", 0.005 + 0.004 * i, False),
                                              ("male_minus_female", -0.012 + 0.002 * i, False),
                                              ("mdd_severity:Severe_minus_rest", 0.053 + 0.01 * i, False),
                                              ("mdd_recurrence:Single Episode_minus_rest", -0.065, True),
                                              ("mdd_recurrence:Recurrent_minus_rest", 0.06, True)):
                rows.append({"representation": arm, "model": model, "contrast": contrast, "family": "f",
                             "delta_roc": delta, "delta_ci_low": delta - 0.03, "delta_ci_high": delta + 0.03,
                             "p_value": 0.01, "p_bh": 0.15 if not survives else 0.015,
                             "survives_bh": survives})
    return pd.DataFrame(rows)


def test_race_answer_has_every_contrast_with_its_interval():
    lines = q.subgroup_race_lines(contrasts_frame())
    race = [line for line in lines if line.startswith("race ") and "contrasts" not in line]
    assert len(race) == 10
    assert all("(" in line and " to " in line for line in race)
    assert sum(line.startswith("severe ") for line in lines) == 2
    assert sum(line.startswith("sex largest") for line in lines) == 1
    assert fits_a_report(lines)


def test_bh_answer_lists_every_survivor():
    frame = contrasts_frame()
    lines = q.subgroup_bh_lines(frame)
    assert lines[0] == f"bh 20 of {len(frame)} contrasts survive"
    assert len(lines) == 21 and fits_a_report(lines)


# ---------------------------------------------------------------------------
# operating point
# ---------------------------------------------------------------------------
def test_operating_point_is_the_panels():
    rng = np.random.default_rng(2)
    y = (rng.random(800) < 0.2).astype(int)
    p = np.clip(0.2 + 0.1 * y + rng.normal(0, 0.1, 800), 0, 1)
    lines = q.operating_point_lines("EMBEDDED logistic_regression", y, p)
    point = youden_operating_point(y, p, bootstrap=True)
    sens = point["sensitivity"]
    assert f"sensitivity {sens['value']:.3f} ({sens['ci_low']:.3f} to {sens['ci_high']:.3f})" in lines[1]
    (tn, fp), (fn, tp) = point["confusion_matrix"]
    assert f"TP {tp} FN {fn} FP {fp} TN {tn}" in lines[0]
    assert fits_a_report(lines * 2)


# ---------------------------------------------------------------------------
# recurrence level
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value, expected", [
    ("", "<empty string>"), (None, "<missing>"), (float("nan"), "<missing>"), ("  ", "<blank>"),
    ("Single Episode", "Single Episode"), ("x" * 60, "<other, 60 characters>"),
])
def test_describe_level(value, expected):
    assert q.describe_level(value) == expected


def test_recurrence_answer_names_the_empty_level():
    performance = pd.DataFrame({"group": ["mdd_recurrence:", "mdd_recurrence:", "mdd_recurrence:Recurrent", "sex"],
                                "n": [32, 32, 2177, 10], "n_events": [7, 7, 433, 2]})
    cohort = pd.Series(["", "Recurrent", "Recurrent", None])
    lines = q.recurrence_lines(performance, cohort, pd.Series(["Severe"]))
    assert "recurrence test group <empty string>: n 32 events 7" in lines
    assert any("<empty string> 1" in line for line in lines if line.startswith("recurrence cohort"))
    assert lines[-1] == "recurrence empty-level severity Severe 1"


# ---------------------------------------------------------------------------
# calibration bins
# ---------------------------------------------------------------------------
def test_equal_width_fit_is_compute_metrics():
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.6, 2000)
    y = (rng.random(2000) < p).astype(int)
    slope, intercept, bins = q.binned_line(y, p, calibration_bin_edges(p, "uniform"))
    metrics = compute_metrics(y, p)
    assert np.isclose(slope, metrics["calibration_slope"]) and np.isclose(intercept, metrics["calibration_intercept"])
    assert bins == 6


def test_retrieval_rows_read_the_files_figure_s5_draws():
    assert {name for _, name in q.RETRIEVAL_FILES} == {filename for _, filename, _ in ARMS}


def test_equal_count_bins_are_the_ones_figure_s5_draws(tmp_path):
    rng = np.random.default_rng(6)
    p = rng.uniform(0.12, 0.3, 3000)
    y = (rng.random(3000) < p).astype(int)
    drawn = plot_calibration(y, p, "check", save_dir=tmp_path, strategy="quantile")
    edges = calibration_bin_edges(p, "quantile")
    predicted, observed, counts = q.binned_points(y, p, edges)
    ours = [(edges[b], edges[b + 1], counts[b], predicted[b], observed[b])
            for b in range(len(counts)) if counts[b]]
    theirs = [(row["bin_low"], row["bin_high"], row["n"], row["mean_predicted"], row["observed_fraction"])
              for row in drawn]
    assert np.allclose(np.array(ours, dtype=float), np.array(theirs, dtype=float), rtol=0, atol=0)


def test_equal_count_fit_recovers_a_calibrated_line():
    rng = np.random.default_rng(4)
    p = rng.uniform(0.1, 0.3, 20_000)
    y = (rng.random(20_000) < p).astype(int)
    fit = q.bootstrap_binned_line(y, p, calibration_bin_edges(p, "quantile"), bootstrap_sample_indices(20_000)[:200])
    assert fit["bins"] == 10
    assert fit["slope"]["ci_low"] < 1.0 < fit["slope"]["ci_high"]
    assert fit["slope"]["ci_low"] <= fit["slope"]["value"] <= fit["slope"]["ci_high"]


def test_calibration_answer_fits_and_says_when_no_line_fits():
    rng = np.random.default_rng(5)
    p = rng.uniform(0.1, 0.35, 1500)
    y = (rng.random(1500) < p).astype(int)
    lines = q.calibration_lines("plain", y, p)
    assert len(lines) == 3 and "equal-width" in lines[1] and "equal-count 10 bins" in lines[2]
    flat = q.calibration_lines("random", y, np.full(1500, 0.175) + rng.uniform(0, 0.002, 1500))
    assert flat[1] == "cal random equal-width 1 non-empty bin: no line"
    assert "equal-count 10 bins: slope" in flat[2]
    assert fits_a_report(lines * 3 + flat)


def test_an_unknown_question_is_refused(capsys):
    assert q.main(["everything"]) == 2
    assert capsys.readouterr().out.startswith("RELAY: round2 question refused")
