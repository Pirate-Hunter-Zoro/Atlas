"""Supplement Table S8: retrieval discrimination by quintile of pre-index history length.

Usage:
    python -m scripts.pipeline.review.history_quintiles

Scores each retrieval arm at its own best k -- importance-weighted cosine, plain cosine,
and uniform random -- inside each fifth of the held-out patients ordered by recorded
pre-index history. The predictions are the sweep's best_k_predictions_*.csv, so nothing is
re-derived and the overall AUCs match Figure 4 and Table S7. Each quintile AUC carries a
percentile bootstrap 95% CI over that quintile's own patients.

The question is descriptive: does retrieval work better or worse in patients with longer
records? The best k was chosen on the same test patients, so every value is optimistic
in the way the headline value is.

Artifacts, in ARTIFACTS_DIR/review/history_quintiles/:
  history_quintiles.csv    one row per (arm, quintile): bounds, n, events, AUC and CI
  history_quintiles.json   the same, with the arm definitions and the seed
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from dotenv import load_dotenv
load_dotenv()

from scripts.pipeline.review.paths import review_output_dir
from scripts.shared.plots import N_BOOTSTRAP

ANALYSIS_NAME = "history_quintiles"
HISTORY_COLUMN = 'pre_anchor_history_days'
N_BINS = 5

# arm -> (label, predictions file under RESULTS_DIR/neighbor_count_sweep/)
ARMS = {
    'weighted': ("Importance-weighted, k = 295", "best_k_predictions_alpha1.csv"),
    'plain': ("Plain cosine, k = 757", "best_k_predictions_alpha1_plain.csv"),
    'random': ("Random, uniform weights, k = 32,720", "best_k_predictions_random.csv"),
}


def bootstrap_auc(y_true: np.ndarray, y_score: np.ndarray, rng: np.random.Generator,
                  n_boot: int = N_BOOTSTRAP) -> tuple[float, float, float]:
    """ROC AUC with a percentile bootstrap 95% CI.

    Draws that lose a class are dropped, which is why the percentiles use nanpercentile.

    Args:
        y_true (np.ndarray): 0/1 outcomes, shape (n,).
        y_score (np.ndarray): Risk scores, shape (n,).
        rng (np.random.Generator): Seeded generator.
        n_boot (int): Number of resamples.

    Returns:
        tuple[float, float, float]: AUC, 2.5th percentile, 97.5th percentile.
    """
    n = len(y_true)
    aucs = np.full(n_boot, np.nan)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        sampled = y_true[idx]
        if sampled.min() == sampled.max():
            continue
        aucs[b] = roc_auc_score(sampled, y_score[idx])
    return (float(roc_auc_score(y_true, y_score)),
            float(np.nanpercentile(aucs, 2.5)), float(np.nanpercentile(aucs, 97.5)))


def score_quintiles(frame: pd.DataFrame, history: pd.Series, seed: int,
                    n_boot: int = N_BOOTSTRAP) -> pd.DataFrame:
    """Score one arm's predictions within each quintile of history length.

    Args:
        frame (pd.DataFrame): anchor_patient_id, true_label, predicted_risk.
        history (pd.Series): History length in days, indexed by patient id.
        seed (int): Seed; each quintile draws from its own child of it.
        n_boot (int): Number of bootstrap resamples.

    Returns:
        pd.DataFrame: One row per quintile, in order: quintile, low, high, n, events,
            roc_auc, ci_low, ci_high.
    """
    joined = frame.join(history, on='anchor_patient_id', how='left')
    if joined[HISTORY_COLUMN].isna().any():
        raise ValueError("A held-out patient has no recorded history length.")
    bins = pd.qcut(joined[HISTORY_COLUMN], q=N_BINS, duplicates='drop')
    children = np.random.SeedSequence(seed).spawn(len(bins.cat.categories))
    rows = []
    for i, (interval, child) in enumerate(zip(bins.cat.categories, children), start=1):
        part = joined[bins == interval]
        y = part['true_label'].to_numpy()
        auc, low, high = bootstrap_auc(y, part['predicted_risk'].to_numpy(),
                                       np.random.default_rng(child), n_boot=n_boot)
        rows.append({
            'quintile': i,
            'low': float(part[HISTORY_COLUMN].min()),
            'high': float(part[HISTORY_COLUMN].max()),
            'n': int(len(part)),
            'events': int(y.sum()),
            'roc_auc': auc,
            'ci_low': low,
            'ci_high': high,
        })
    return pd.DataFrame(rows)


def main():
    results = Path(os.environ['RESULTS_DIR']) / "neighbor_count_sweep"
    seed = int(os.environ['SEED'])
    history = pd.read_parquet(Path(os.environ['FEATURE_DATAFRAME_PATH']),
                              columns=[HISTORY_COLUMN])[HISTORY_COLUMN]
    frames = []
    for arm, (label, filename) in ARMS.items():
        predictions = pd.read_csv(results / filename)
        scored = score_quintiles(predictions, history, seed)
        scored.insert(0, 'label', label)
        scored.insert(0, 'arm', arm)
        frames.append(scored)
    table = pd.concat(frames, ignore_index=True)

    save_dir = review_output_dir(ANALYSIS_NAME)
    table.to_csv(save_dir / "history_quintiles.csv", index=False)
    with open(save_dir / "history_quintiles.json", 'w') as f:
        json.dump({
            'history_column': HISTORY_COLUMN,
            'n_bins': N_BINS,
            'n_bootstrap': N_BOOTSTRAP,
            'seed': seed,
            'arms': {arm: {'label': label, 'predictions': filename}
                     for arm, (label, filename) in ARMS.items()},
            'rows': table.to_dict(orient='records'),
        }, f, indent=2)
    print(table.to_string(index=False), flush=True)
    print(f"Wrote {save_dir}", flush=True)


if __name__ == "__main__":
    main()
