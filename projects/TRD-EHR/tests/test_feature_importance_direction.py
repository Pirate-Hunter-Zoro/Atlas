"""Guards on the two sign/label bugs the feature-importance panels once carried.

Both were found by eye, while regenerating Figure 6, and both are the kind that
produce a figure that looks finished and says the wrong thing. They are recorded
as a watch item in planning/TRD-EHR_TODO.txt; these assertions are the version
of that note that goes red instead of going stale.

(a) "importance" and "sign" in feature_importance_summary.json are NOT
    redundant and must never be multiplied together. "importance" is the raw
    model attribution -- a SIGNED coefficient for logistic regression, an
    UNSIGNED impurity/gain score for the tree models. "sign" comes separately
    from the univariate Spearman correlation between the feature and the risk
    score. Multiplying them turns every genuinely negative logistic predictor
    positive and colours it as risk-raising, which contradicts the manuscript's
    named negatives (missing smoking status, hyperlipidemia, longer pre-anchor
    history, male sex).

(b) plot_feature_importance's title once relied on operator precedence in a way
    that dropped the model name from the "direction unspecified" branch, so two
    tree panels arrived titled identically.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba

sys.path.append(str(Path(__file__).parent.parent))
from scripts.pipeline.predictions import feature_importance as fi
from scripts.pipeline.predictions import redraw_feature_importance as redraw

RISK_RAISING = to_rgba("steelblue")
RISK_LOWERING = to_rgba("firebrick")


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    """Point RESULTS_DIR at a scratch directory so panels are written nowhere real."""
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def drawn_axes(monkeypatch):
    """Capture the Axes plot_feature_importance draws on, which it otherwise closes."""
    captured = []
    real_subplots = plt.subplots

    def capturing_subplots(*args, **kwargs):
        (fig, ax) = real_subplots(*args, **kwargs)
        captured.append(ax)
        return (fig, ax)

    monkeypatch.setattr(fi.plt, "subplots", capturing_subplots)
    return captured


def bar_colors(ax):
    """The face colour of each bar, in the order they were drawn."""
    return [to_rgba(patch.get_facecolor()) for patch in ax.containers[0].patches]


def test_negative_logistic_coefficient_survives_the_round_trip(results_dir, monkeypatch):
    """A signed coefficient written to the summary must reach the panel unchanged.

    This is bug (a) end to end: summary on disk, redraw off disk, values as
    handed to the plotting helper. Multiplying importance by sign anywhere along
    that route turns -0.90 into +0.90 and the assertion fails.
    """
    fi.write_feature_importance_summary({
        "logistic_regression": [
            {"name": "num__age", "importance": np.float64(1.10), "sign": np.int64(1)},
            {"name": "cat__smoking_missing", "importance": np.float64(-0.90), "sign": np.int64(-1)},
        ],
    })

    summary_path = results_dir / "feature_importance" / "feature_importance_summary.json"
    on_disk = json.loads(summary_path.read_text())
    assert on_disk["logistic_regression"][1]["importance"] == -0.90
    assert on_disk["logistic_regression"][1]["sign"] == -1

    calls = []
    monkeypatch.setattr(redraw, "plot_feature_importance", lambda **kwargs: calls.append(kwargs))
    redraw.main()

    assert len(calls) == 1, "only logistic_regression has entries in this summary"
    passed = calls[0]
    assert list(passed["importances"]) == [1.10, -0.90]
    assert list(passed["direction_signs"]) == [1.0, -1.0]


def test_logistic_panel_takes_its_colour_from_the_coefficient(results_dir, drawn_axes):
    """For logistic regression the coefficient IS the direction; the Spearman sign is not.

    Both features here correlate positively with the risk score, so a panel that
    coloured from direction_signs would paint both blue and hide the negative
    predictor.
    """
    fi.plot_feature_importance(
        importances=np.array([1.10, -0.90]),
        feature_names=["num__age", "cat__smoking_missing"],
        model_name="logistic_regression",
        direction_signs=np.array([1.0, 1.0]),
    )

    assert bar_colors(drawn_axes[0]) == [RISK_RAISING, RISK_LOWERING]


def test_tree_panel_takes_its_colour_from_the_spearman_sign(results_dir, drawn_axes):
    """For the tree models the importance is unsigned, so direction comes from Spearman."""
    fi.plot_feature_importance(
        importances=np.array([0.50, 0.40]),
        feature_names=["num__age", "cat__smoking_missing"],
        model_name="random_forest",
        direction_signs=np.array([1.0, -1.0]),
    )

    assert bar_colors(drawn_axes[0]) == [RISK_RAISING, RISK_LOWERING]


def test_title_keeps_the_model_name_when_direction_is_unspecified(results_dir, drawn_axes):
    """Bug (b): the no-direction branch dropped the model name and both tree panels matched."""
    fi.plot_feature_importance(
        importances=np.array([0.50, 0.40]),
        feature_names=["num__age", "cat__smoking_missing"],
        model_name="random_forest",
        direction_signs=None,
    )

    title = drawn_axes[0].get_title()
    assert title.startswith("Random forest")
    assert "direction unspecified" in title


def test_title_keeps_the_model_name_and_the_colour_key_when_direction_is_known(results_dir, drawn_axes):
    """The other branch of the same conditional, so a fix cannot trade one for the other."""
    fi.plot_feature_importance(
        importances=np.array([0.50, 0.40]),
        feature_names=["num__age", "cat__smoking_missing"],
        model_name="gradient_boosting",
        direction_signs=np.array([1.0, -1.0]),
    )

    title = drawn_axes[0].get_title()
    assert title.startswith("Gradient boosting")
    assert "raises TRD risk" in title and "lowers TRD risk" in title
