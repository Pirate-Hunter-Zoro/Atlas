"""Guards on the intervals the paper prints for AUPRC, Brier, calibration and proportions.

(a) The Wilson interval matches a textbook value and stays inside [0, 1].
(b) The bootstrap ROC AUC interval is the plain resample-and-score interval, which is
    what makes the round-trip against classical_ml_results meaningful.
(c) A recomputed ROC AUC that disagrees with the pipeline's is refused.
(d) Spearman intervals bracket their point estimate.

Synthetic data only; nothing here reads RESULTS_DIR.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.review.metric_intervals import (
    METRICS,
    bootstrap_metric_intervals,
    check_roc,
    spearman_interval,
)
from scripts.shared.utils import wilson_interval


def synthetic(n=800, seed=0):
    rng = np.random.default_rng(seed)
    risk = rng.uniform(0.05, 0.6, size=n)
    y = (rng.uniform(size=n) < risk).astype(int)
    return y, risk


def test_wilson_textbook_value_and_bounds():
    low, high = wilson_interval(5, 10)
    assert np.isclose(low, 0.2366, atol=1e-4) and np.isclose(high, 0.7634, atol=1e-4)
    low, high = wilson_interval(0, 20)
    assert low == pytest.approx(0.0, abs=1e-12) and 0 < high < 1
    low, high = wilson_interval(25645, 42579)
    assert low < 25645 / 42579 < high


def test_bootstrap_roc_interval_is_the_plain_loop():
    y, risk = synthetic()
    indices = np.random.default_rng(3).integers(0, len(y), size=(200, len(y)))
    block = bootstrap_metric_intervals(y, risk, indices)
    assert set(block) == set(METRICS)
    aucs = [roc_auc_score(y[i], risk[i]) for i in indices]
    assert np.isclose(block['roc_score']['ci_low'], np.percentile(aucs, 2.5))
    assert np.isclose(block['roc_score']['ci_high'], np.percentile(aucs, 97.5))
    assert np.isclose(block['roc_score']['value'], roc_auc_score(y, risk))
    for name in ('roc_score', 'auprc', 'brier_score'):
        assert block[name]['ci_low'] <= block[name]['value'] <= block[name]['ci_high'], name


def test_check_roc_refuses_a_mismatch():
    got = {'value': 0.65, 'ci_low': 0.63, 'ci_high': 0.67}
    check_roc("same", got, {'roc_score': 0.65, 'roc_score_ci_low': 0.63,
                            'roc_score_ci_high': 0.67}, check_interval=True)
    with pytest.raises(ValueError):
        check_roc("different", got, {'roc_score': 0.651, 'roc_score_ci_low': 0.63,
                                     'roc_score_ci_high': 0.67}, check_interval=False)


def test_spearman_interval_brackets_point():
    y, risk = synthetic()
    indices = np.random.default_rng(5).integers(0, len(y), size=(200, len(y)))
    block = spearman_interval(risk, y, indices)
    assert block['ci_low'] <= block['value'] <= block['ci_high']
