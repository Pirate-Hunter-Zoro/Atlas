"""Guards on the within-group intervals of the subgroup analysis (Supplement S9).

(a) The AUC interval is the one a plain resample-and-score loop gives for the same seed,
    so adding calibration intervals did not move a published AUC interval.
(b) Brier, calibration slope and mean risk difference get intervals from the same
    resamples, each bracketing its point estimate on well-behaved data.
(c) A group whose resamples lose a class drops those draws rather than failing.

Synthetic data only; nothing here reads RESULTS_DIR.
"""

import os
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('SEED', '42')

from scripts.pipeline.review.subgroups.core import (
    GROUP_METRICS,
    bootstrap_auc_ci,
    bootstrap_group_intervals,
    calibration,
)
from scripts.shared.plots import N_BOOTSTRAP


def synthetic(n=600, seed=0):
    rng = np.random.default_rng(seed)
    risk = rng.uniform(0.05, 0.6, size=n)
    y = (rng.uniform(size=n) < risk).astype(int)
    return y, risk


def test_auc_interval_matches_a_plain_loop():
    y, risk = synthetic()
    got = bootstrap_group_intervals(y, risk, np.random.default_rng(7))['roc_score']
    indices = np.random.default_rng(7).integers(0, len(y), size=(N_BOOTSTRAP, len(y)))
    aucs = [roc_auc_score(y[i], risk[i]) for i in indices if y[i].min() != y[i].max()]
    assert np.isclose(got[0], np.percentile(aucs, 2.5))
    assert np.isclose(got[1], np.percentile(aucs, 97.5))
    assert bootstrap_auc_ci(y, risk, np.random.default_rng(7)) == got


def test_every_metric_brackets_its_point():
    y, risk = synthetic()
    intervals = bootstrap_group_intervals(y, risk, np.random.default_rng(3))
    slope, in_the_large = calibration(y, risk)
    point = {'roc_score': roc_auc_score(y, risk), 'brier_score': brier_score_loss(y, risk),
             'calibration_slope': slope, 'calibration_in_the_large': in_the_large}
    assert set(intervals) == set(GROUP_METRICS)
    for metric, (low, high) in intervals.items():
        assert low <= point[metric] <= high, metric


def test_single_class_draws_are_dropped():
    y = np.zeros(40, dtype=int)
    y[0] = 1
    risk = np.linspace(0.1, 0.5, 40)
    intervals = bootstrap_group_intervals(y, risk, np.random.default_rng(1))
    assert all(np.isfinite(bound) for pair in intervals.values() for bound in pair)
