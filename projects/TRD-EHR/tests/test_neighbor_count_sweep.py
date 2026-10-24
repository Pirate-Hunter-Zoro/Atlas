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

(d) Plain cosine is the control the weighted metric is read against, so it must be the
    PUBLISHED arm's space and nothing else: the raw embedding, L2-normalised, with no
    standardiser and no dimension weights anywhere in it. A control that quietly
    inherited either would make the metric look like it does nothing.
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
    to_plain_space,
    to_weighted_space,
)
from scripts.pipeline.predictions.neighbor_count_sweep import (
    METRICS,
    PRIMARY_METRIC,
    metric_suffix,
    risk_by_neighbour_count,
    roc_auc_by_column,
    to_metric_space,
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


def test_plain_space_rows_are_unit_length():
    """Plain cosine is a cosine only if the rows are normalised, same as the weighted one."""
    rng = np.random.default_rng(10)
    rows = to_plain_space(rng.normal(size=(5, 7)))
    assert np.allclose(np.linalg.norm(rows, axis=1), 1.0, atol=1e-6)


def test_plain_space_leaves_a_zero_vector_at_the_origin():
    """An all-zero embedding must come back zero rather than as a divide-by-zero."""
    rows = to_plain_space(np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 2.0]]))
    assert np.all(rows[0] == 0.0)
    assert np.isfinite(rows).all()
    assert rows[1] == pytest.approx(np.array([1.0, 2.0, 2.0]) / 3.0, abs=1e-6)


def test_plain_space_ignores_the_scaler_and_the_dimension_weights():
    """The control must not inherit the metric it is a control for.

    to_metric_space is handed the scaler and the weights whichever metric is asked for,
    because the caller does not branch. If `plain` ever consulted either of them, the
    comparison in the sweep would be two versions of the same arm.
    """
    rng = np.random.default_rng(11)
    vectors = rng.normal(size=(6, 4))
    sparse_weights = np.array([1.0, 0.0, 0.0, 0.0])
    even_weights = np.full(4, 0.25)

    one = to_metric_space('plain', vectors, IdentityScaler(4, mean=0.0, scale=1.0), sparse_weights)
    two = to_metric_space('plain', vectors, IdentityScaler(4, mean=17.0, scale=9.0), even_weights)
    assert np.allclose(one, two, atol=1e-7)
    assert np.allclose(one, to_plain_space(vectors), atol=1e-7)


def test_plain_and_weighted_spaces_disagree_when_the_metric_is_sparse():
    """The two arms must actually be two arms on a metric that drops most dimensions."""
    rng = np.random.default_rng(12)
    vectors = rng.normal(size=(8, 5))
    weights = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
    weighted = to_metric_space('weighted', vectors, IdentityScaler(5), weights)
    plain = to_metric_space('plain', vectors, IdentityScaler(5), weights)
    assert not np.allclose(weighted @ weighted.T, plain @ plain.T, atol=1e-3)


def test_every_metric_has_a_space_and_an_unknown_one_is_refused():
    """A typo in --metrics must stop the run rather than silently sweep one arm twice."""
    rng = np.random.default_rng(13)
    vectors = rng.normal(size=(4, 3))
    for metric in METRICS:
        rows = to_metric_space(metric, vectors, IdentityScaler(3), np.full(3, 1 / 3))
        assert rows.shape == vectors.shape
    with pytest.raises(ValueError):
        to_metric_space('cosine', vectors, IdentityScaler(3), np.full(3, 1 / 3))


def test_only_the_primary_metric_keeps_the_unsuffixed_filenames():
    """Two arms writing best_k_predictions_alpha1.csv would leave one of them on disk."""
    assert metric_suffix(PRIMARY_METRIC) == ''
    tails = {metric_suffix(m) for m in METRICS}
    assert len(tails) == len(METRICS)
    assert all(tail.startswith('_') for tail in tails if tail)


def test_risk_at_counts_matches_the_sweep_at_those_k():
    """An interval added later must be read off the same curve the sweep drew."""
    from scripts.pipeline.predictions.neighbor_count_sweep import (
        risk_at_counts, risk_by_neighbour_count)
    rng = np.random.default_rng(3)
    anchors = rng.normal(size=(9, 6)); anchors /= np.linalg.norm(anchors, axis=1, keepdims=True)
    pool = rng.normal(size=(40, 6)); pool /= np.linalg.norm(pool, axis=1, keepdims=True)
    labels = rng.integers(0, 2, size=40)
    ks = np.array([1, 5, 17, 40])
    full, _ = risk_by_neighbour_count(anchors, pool, labels, (1.0, 5.0), 0.2)
    cut = risk_at_counts(anchors, pool, labels, ks, (1.0, 5.0), 0.2)
    for alpha in (1.0, 5.0):
        np.testing.assert_allclose(cut[alpha], full[alpha][:, ks - 1], rtol=1e-5, atol=1e-6)


# ---- The random-neighbour arm ------------------------------------------------------------
#
# (e) The random arm is the floor the cosine arms are read against, so its risk must be the
#     plain mean label of k pool patients drawn at random, nested across k, and its fast
#     AUC must be the same AUC the cosine arms get. Its draws must be reproducible one at a
#     time, or the panels drawn from its "representative draw" would be of some other draw.

from scripts.pipeline.predictions.neighbor_count_sweep import (  # noqa: E402
    PIPELINE_NEIGHBOUR_COUNT,
    auc_of_count_columns,
    best_neighbour_index,
    effective_sample_sizes,
    random_draw_auc,
    random_draw_seeds,
    random_neighbour_counts,
    random_neighbour_risk,
    random_neighbour_sweep,
    representative_draw,
    summarise_random_draws,
)


def test_random_counts_are_a_running_count_along_a_shuffle_of_the_pool():
    """Each row steps by 0 or 1 and ends at the pool's TRD total: a permutation, cumsummed."""
    rng = np.random.default_rng(20)
    pool_labels = rng.integers(0, 2, size=37)
    counts = random_neighbour_counts(pool_labels, 300, np.random.default_rng(5)).astype(int)
    steps = np.diff(np.concatenate([np.zeros((300, 1), dtype=int), counts], axis=1), axis=1)
    assert set(np.unique(steps)) <= {0, 1}
    assert np.all(counts[:, -1] == pool_labels.sum())
    # Rows are independent orderings, not one ordering repeated.
    assert len({tuple(row) for row in counts}) > 1


def test_random_counts_draw_every_neighbour_equally_often():
    """Uniform draws: at k = 1 each anchor's neighbour is TRD at the pool prevalence."""
    pool_labels = np.array([1] * 3 + [0] * 7)
    counts = random_neighbour_counts(pool_labels, 20000, np.random.default_rng(6))
    assert counts[:, 0].mean() == pytest.approx(0.3, abs=0.015)
    assert counts[:, 4].mean() / 5 == pytest.approx(0.3, abs=0.01)


def test_random_risk_is_the_plain_mean_label_and_ends_at_the_prevalence():
    """Uniform weights: the risk at k is the count over k, and all neighbours give prevalence."""
    pool_labels = np.random.default_rng(21).integers(0, 2, size=25)
    risk = random_neighbour_risk(pool_labels, 7, np.random.default_rng(8))
    counts = random_neighbour_counts(pool_labels, 7, np.random.default_rng(8))
    np.testing.assert_allclose(risk, counts / np.arange(1, 26), rtol=1e-6)
    np.testing.assert_allclose(risk[:, -1], pool_labels.mean(), rtol=1e-6)
    assert risk.dtype == np.float32


def test_count_auc_matches_the_rank_auc_and_sklearn():
    """The histogram AUC is only a speed-up of the average-rank AUC, ties included."""
    rng = np.random.default_rng(22)
    y_true = rng.integers(0, 2, size=250)
    pool_labels = rng.integers(0, 2, size=60)
    counts = random_neighbour_counts(pool_labels, y_true.size, rng)
    risk = counts / np.arange(1, 61)
    mine = auc_of_count_columns(y_true, counts, column_block=7)
    np.testing.assert_allclose(mine, roc_auc_by_column(y_true, risk), atol=1e-12)
    for k in (1, 2, 13, 60):
        assert mine[k - 1] == pytest.approx(roc_auc_score(y_true, risk[:, k - 1]))
    assert mine[-1] == pytest.approx(0.5)  # every anchor tied at the prevalence


def test_count_auc_is_nan_without_both_classes():
    counts = np.array([[0, 1], [1, 1]])
    assert np.isnan(auc_of_count_columns(np.array([1, 1]), counts)).all()


def test_random_draws_are_reproducible_and_do_not_depend_on_the_worker_count():
    """A draw regenerated from its own seed must be the draw the sweep scored."""
    rng = np.random.default_rng(23)
    anchor_labels = rng.integers(0, 2, size=40)
    pool_labels = rng.integers(0, 2, size=30)
    serial = random_neighbour_sweep(anchor_labels, pool_labels, 6, seed=42, n_workers=1)
    parallel = random_neighbour_sweep(anchor_labels, pool_labels, 6, seed=42, n_workers=2)
    np.testing.assert_array_equal(serial, parallel)
    third = random_draw_auc(random_draw_seeds(6, 42)[3], pool_labels.astype(np.int8),
                            anchor_labels.astype(np.int8))
    np.testing.assert_array_equal(third, serial[3])
    assert not np.array_equal(serial[0], serial[1])
    other_seed = random_neighbour_sweep(anchor_labels, pool_labels, 6, seed=43, n_workers=1)
    assert not np.array_equal(serial, other_seed)


def test_random_band_brackets_the_mean_and_centres_on_one_half():
    """With no information in the draw, the band sits around 0.5 at every k."""
    rng = np.random.default_rng(24)
    anchor_labels = rng.integers(0, 2, size=300)
    pool_labels = rng.integers(0, 2, size=50)
    draws = random_neighbour_sweep(anchor_labels, pool_labels, 200, seed=42)
    curve = summarise_random_draws(draws)
    assert list(curve.columns) == ['n_neighbors', 'roc_auc', 'ci_low', 'ci_high']
    assert curve['n_neighbors'].tolist() == list(range(1, 51))
    assert np.all(curve['ci_low'] <= curve['roc_auc']) and np.all(curve['roc_auc'] <= curve['ci_high'])
    assert np.all(np.abs(curve['roc_auc'].iloc[:-1] - 0.5) < 0.02)
    assert curve['ci_low'].iloc[0] < 0.5 < curve['ci_high'].iloc[0]
    assert curve['ci_low'].iloc[-1] == curve['ci_high'].iloc[-1] == pytest.approx(0.5)


def test_best_k_takes_the_smallest_k_on_a_tie():
    assert best_neighbour_index(np.array([0.5, 0.7, 0.6, 0.7])) == 1
    assert best_neighbour_index(np.array([np.nan, 0.52, 0.51])) == 1


def test_representative_draw_is_the_one_nearest_the_mean():
    draws = np.array([[0.40, 0.1], [0.52, 0.2], [0.49, 0.3], [0.59, 0.4]])
    # Mean of column 0 is 0.50; draw 2 (0.49) is closest.
    assert representative_draw(draws, 0) == 2
    # Mean of column 1 is 0.25; draws 1 and 2 tie at 0.05, the lower index wins.
    assert representative_draw(draws, 1) == 1


def test_effective_sample_size_matches_the_direct_formula():
    """ESS at the best k is the pipeline's (sum w)^2 / sum w^2 over the k nearest."""
    rng = np.random.default_rng(25)
    anchors = rng.normal(size=(5, 4)); anchors /= np.linalg.norm(anchors, axis=1, keepdims=True)
    pool = rng.normal(size=(12, 4)); pool /= np.linalg.norm(pool, axis=1, keepdims=True)
    ess = effective_sample_sizes(anchors, pool, {1.0: 3, 5.0: 12})
    similarities = anchors @ pool.T
    for alpha, k in ((1.0, 3), (5.0, 12)):
        for i in range(5):
            top = np.sort(similarities[i])[::-1][:k]
            w = neighbour_weights(top, alpha)
            expected = w.sum() ** 2 / (w ** 2).sum() if (w ** 2).sum() > 0 else 0.0
            assert ess[alpha][i] == pytest.approx(expected, rel=1e-5)


def test_effective_sample_size_of_all_zero_weights_is_zero():
    anchors = np.array([[1.0, 0.0]])
    pool = np.array([[-1.0, 0.0], [0.0, -1.0]])
    assert effective_sample_sizes(anchors, pool, {1.0: 2})[1.0][0] == 0.0


def test_the_pipeline_neighbour_count_is_the_pipelines_k():
    assert PIPELINE_NEIGHBOUR_COUNT == 50
