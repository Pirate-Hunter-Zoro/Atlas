"""Guards on the importance-weighted KNN metric and the neighbourhood-size sweep.

Three things in this arm are easy to get wrong in a way that still produces a smooth,
finished-looking curve, so each gets an assertion rather than a comment.

(a) The similarity must actually ignore the dimensions the classifier zeroed out.
    Elastic net keeps a few hundred of 4096, and the whole claim of the arm is that
    noise on the discarded dimensions cannot move a neighbour ranking.

(b) roc_auc_by_column replaces thirty-four thousand sklearn calls with one rank
    identity. It must agree with sklearn to floating point, including on the heavy
    ties a small-k risk score produces, where a wrong tie rule silently inflates AUC.

(c) The running-sum risk must equal the direct weighted average at every k, and the
    weights must be the similarity itself -- clamped, then sharpened -- not some
    rescaling of it.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

import matplotlib
matplotlib.use("Agg")

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.predictions.importance_weighted_knn import (
    concentration_summary,
    neighbour_weights,
    to_weighted_space,
)
from scripts.pipeline.predictions.neighbor_count_sweep import (
    risk_by_neighbour_count,
    roc_auc_by_column,
)


class IdentityScaler:
    """Stand-in for the fitted StandardScaler, so the tests fix the standardisation."""

    def __init__(self, n_dimensions: int, mean: float = 0.0, scale: float = 1.0):
        self.mean_ = np.full(n_dimensions, mean, dtype=np.float64)
        self.scale_ = np.full(n_dimensions, scale, dtype=np.float64)


def test_zero_weight_dimensions_cannot_change_the_similarity():
    """A dimension the classifier dropped is invisible to the metric."""
    rng = np.random.default_rng(0)
    weights = np.array([0.5, 0.5, 0.0, 0.0])
    scaler = IdentityScaler(4)
    vectors = rng.normal(size=(6, 4))

    baseline = to_weighted_space(vectors, scaler, weights)
    perturbed_input = vectors.copy()
    perturbed_input[:, 2:] += rng.normal(scale=50.0, size=(6, 2))
    perturbed = to_weighted_space(perturbed_input, scaler, weights)

    assert np.allclose(baseline @ baseline.T, perturbed @ perturbed.T, atol=1e-6)


def test_weighted_space_rows_are_unit_length():
    """The dot product is a cosine only if the rows are normalised."""
    rng = np.random.default_rng(1)
    weights = np.array([0.7, 0.2, 0.1])
    rows = to_weighted_space(rng.normal(size=(5, 3)), IdentityScaler(3), weights)
    assert np.allclose(np.linalg.norm(rows, axis=1), 1.0, atol=1e-6)


def test_weighted_space_leaves_an_all_average_patient_at_the_origin():
    """A patient exactly at the scaler's mean gets zero similarity, not a divide-by-zero."""
    weights = np.array([0.5, 0.5])
    scaler = IdentityScaler(2, mean=3.0)
    rows = to_weighted_space(np.array([[3.0, 3.0], [4.0, 5.0]]), scaler, weights)
    assert np.all(rows[0] == 0.0)
    assert np.isfinite(rows).all()


def test_negative_similarity_never_becomes_a_weight():
    """Weights enter a probability; a negative one would push the risk outside [0, 1]."""
    similarities = np.array([-0.9, -1e-9, 0.0, 0.25, 1.0])
    for alpha in (1.0, 2.0, 5.0):
        weights = neighbour_weights(similarities, alpha)
        assert np.all(weights >= 0.0)
        assert np.all(weights[:3] == 0.0)
    assert neighbour_weights(np.array([0.5]), 1.0)[0] == pytest.approx(0.5)
    assert neighbour_weights(np.array([0.5]), 2.0)[0] == pytest.approx(0.25)


def test_roc_auc_by_column_matches_sklearn_including_ties():
    """The rank identity has to agree with the curve, tie rule included."""
    rng = np.random.default_rng(2)
    y_true = rng.integers(0, 2, size=400)
    scores = rng.random((400, 6))
    scores[:, 0] = np.round(scores[:, 0])          # two distinct values, maximal ties
    scores[:, 1] = np.round(scores[:, 1] * 3)      # four distinct values
    scores[:, 2] = 0.4                             # completely tied: AUC must be exactly 0.5
    scores[:, 3] = y_true * 0.5 + rng.random(400)  # genuinely discriminating

    mine = roc_auc_by_column(y_true, scores, column_block=2)
    theirs = np.array([roc_auc_score(y_true, scores[:, j]) for j in range(scores.shape[1])])
    assert np.allclose(mine, theirs)
    assert mine[2] == pytest.approx(0.5)


def test_running_sum_risk_equals_the_direct_weighted_average():
    """The cumulative trick is only a speed-up; it must reproduce the honest formula."""
    rng = np.random.default_rng(3)
    anchors = to_weighted_space(rng.normal(size=(4, 5)), IdentityScaler(5), np.full(5, 0.2))
    pool = to_weighted_space(rng.normal(size=(11, 5)), IdentityScaler(5), np.full(5, 0.2))
    pool_labels = rng.integers(0, 2, size=11)
    alpha = 2.0

    risks, _ = risk_by_neighbour_count(anchors, pool, pool_labels, (alpha,), fallback_risk=0.0)

    similarities = anchors @ pool.T
    for anchor_index in range(anchors.shape[0]):
        order = np.argsort(-similarities[anchor_index], kind='stable')
        for k in (1, 3, 7, 11):
            chosen = order[:k]
            weights = neighbour_weights(similarities[anchor_index][chosen].astype(np.float64), alpha)
            expected = np.dot(weights, pool_labels[chosen]) / weights.sum()
            assert risks[alpha][anchor_index, k - 1] == pytest.approx(expected, abs=1e-5)


def test_risk_at_one_neighbour_is_that_neighbours_label():
    """k=1 is the sanity anchor: the risk can only be the nearest patient's flag."""
    rng = np.random.default_rng(4)
    anchors = to_weighted_space(rng.normal(size=(5, 4)), IdentityScaler(4), np.full(4, 0.25))
    pool = to_weighted_space(rng.normal(size=(9, 4)), IdentityScaler(4), np.full(4, 0.25))
    pool_labels = rng.integers(0, 2, size=9)

    risks, _ = risk_by_neighbour_count(anchors, pool, pool_labels, (1.0,), fallback_risk=0.5)
    nearest = np.argmax(anchors @ pool.T, axis=1)
    assert np.array_equal(risks[1.0][:, 0].round().astype(int), pool_labels[nearest])


def test_undefined_risk_is_counted_and_filled_rather_than_left_as_a_nan():
    """Where every candidate in reach is anti-correlated the ratio has no value."""
    anchors = np.array([[1.0, 0.0]], dtype=np.float32)
    pool = np.array([[-1.0, 0.0], [0.0, -1.0]], dtype=np.float32)
    risks, n_undefined = risk_by_neighbour_count(anchors, pool, np.array([1, 0]), (1.0,), fallback_risk=0.14)
    assert n_undefined[1.0] == 2                      # neither k has a positive weight to divide by
    assert risks[1.0][0] == pytest.approx([0.14, 0.14])
    assert np.isfinite(risks[1.0]).all()


def test_concentration_summary_reports_a_sparse_metric_as_sparse():
    """The claim the arm rests on -- few dimensions, most of the mass -- has to be measurable."""
    weights = np.zeros(100)
    weights[:5] = 0.2
    summary = concentration_summary(weights)
    assert summary['n_dimensions'] == 100
    assert summary['n_nonzero_dimensions'] == 5
    assert summary['share_of_importance_by_top_fraction_of_dimensions']['top_5.00%']['share'] == pytest.approx(1.0)
