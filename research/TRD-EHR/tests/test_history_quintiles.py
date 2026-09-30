"""Guards on Supplement Table S8, retrieval discrimination by history-length quintile.

(a) Five quintiles that partition the patients, in order of history length.
(b) Each quintile's AUC is the plain AUC of its own patients, inside its own interval.
(c) The same seed gives the same intervals.

Synthetic data only; nothing here reads RESULTS_DIR.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.append(str(Path(__file__).parent.parent))

from scripts.pipeline.review.history_quintiles import HISTORY_COLUMN, score_quintiles


def synthetic(n=1000, seed=0):
    rng = np.random.default_rng(seed)
    ids = [f"p{i}" for i in range(n)]
    y = rng.integers(0, 2, size=n)
    risk = np.clip(0.3 * y + rng.normal(0.3, 0.2, size=n), 0, 1)
    history = pd.Series(rng.integers(731, 5289, size=n), index=ids, name=HISTORY_COLUMN)
    frame = pd.DataFrame({'anchor_patient_id': ids, 'true_label': y, 'predicted_risk': risk})
    return frame, history


def test_quintiles_partition_and_match_plain_auc():
    frame, history = synthetic()
    table = score_quintiles(frame, history, seed=42, n_boot=200)
    assert list(table['quintile']) == [1, 2, 3, 4, 5]
    assert table['n'].sum() == len(frame)
    assert (table['low'].to_numpy()[1:] >= table['high'].to_numpy()[:-1]).all()
    joined = frame.join(history, on='anchor_patient_id')
    bins = pd.qcut(joined[HISTORY_COLUMN], q=5)
    for row, interval in zip(table.itertuples(), bins.cat.categories):
        part = joined[bins == interval]
        assert np.isclose(row.roc_auc, roc_auc_score(part['true_label'], part['predicted_risk']))
        assert row.ci_low <= row.roc_auc <= row.ci_high


def test_seeded():
    frame, history = synthetic()
    a = score_quintiles(frame, history, seed=7, n_boot=100)
    b = score_quintiles(frame, history, seed=7, n_boot=100)
    pd.testing.assert_frame_equal(a, b)
