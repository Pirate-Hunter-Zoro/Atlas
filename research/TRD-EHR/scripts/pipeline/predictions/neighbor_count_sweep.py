"""Sweep the neighbourhood size of both retrieval metrics and plot ROC against it.

NUM_NEIGHBOR_PATIENTS is fixed at 50 for the published arms and has never been chosen,
only inherited. Under either metric the whole similarity matrix is one matmul, so every k
from a single neighbour to the entire pool can be scored at once: sort each anchor's
candidates by similarity, take running sums of the weights and of the weighted TRD flags,
and the risk score at every k falls out of one division. The output is a curve of held-out
ROC AUC against k, with bootstrapped intervals at a readable handful of k values rather
than at all of them.

TWO METRICS, ON ONE AXIS, BECAUSE THE PUBLISHED NUMBERS CHANGE TWO THINGS AT ONCE. Plain
cosine is on record at k = 50 and the importance-weighted metric peaks near k = 300, so
the difference between them is a difference of metric AND of neighbourhood size. Sweeping
plain cosine over the same k separates the two, and it carries no supervised component at
all: its space is the raw embedding, L2-normalised, with no classifier anywhere in it.

Run it with -m scripts.pipeline.predictions.neighbor_count_sweep; everything lands in
RESULTS_DIR/neighbor_count_sweep.
"""

import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from dotenv import load_dotenv
load_dotenv()

from scripts.pipeline.predictions.create_train_test_split import create_train_test_split
from scripts.pipeline.predictions.importance_weighted_knn import (
    candidate_pool_ids,
    concentration_summary,
    load_dimension_weights,
    load_raw_embeddings,
    neighbour_weights,
    to_plain_space,
    to_weighted_space,
)
from scripts.shared.plots import FIGURE_DPI, N_BOOTSTRAP, bootstrap_sample_indices
from scripts.shared.utils import load_trd_set

# Where the sweep files go. One folder, because they are only interpretable together.
SWEEP_DIR = Path(os.environ['RESULTS_DIR']) / 'neighbor_count_sweep'

# Anchors per similarity block. The blocking bounds peak memory at roughly
# block x pool x 8 bytes for the sort and the two running sums; it does not change any
# number the sweep produces.
ANCHOR_BLOCK = 256

# How many k values carry an error bar. Log-spaced, because the curve moves fast at small
# k and barely at all past a few thousand; one bar per decade-ish stays legible where
# thirty-four thousand bars would be a grey rectangle.
N_INTERVAL_POINTS = 16

# Sharpening exponents swept. 1.0 is the similarity used directly as the weight, which is
# what the risk formula asks for on its face. 5.0 is WEIGHTING_EXPONENT, the value the
# published cosine arm uses, kept so that arm and this one differ only in the metric;
# 2.0 sits between them.
DEFAULT_ALPHAS = (1.0, 2.0, 5.0)

# The two spaces a neighbour can be found in. `weighted` is the importance-weighted metric
# this module was written for; `plain` is the published arm's own cosine, swept over the
# same k so the metric and the neighbourhood size stop being one number. Order matters
# only for the figure's legend and for which arm keeps the unsuffixed filenames.
METRICS = ('weighted', 'plain')

# Which metric owns the unsuffixed outputs and the top-level `by_alpha` block, so a reader
# who knew this file before plain cosine was added finds the same numbers under the same
# names. Everything is also under `by_metric`.
PRIMARY_METRIC = 'weighted'

# The published arm's neighbourhood size. It always gets an error bar, because the
# supplement's table reads both metrics at it beside their best k.
PRIMARY_NEIGHBOUR_COUNT = 50


def to_metric_space(metric: str, vectors: np.ndarray, scaler, weights: np.ndarray) -> np.ndarray:
    """Put raw embeddings into whichever space this metric measures in.

    Args:
        metric (str): One of METRICS.
        vectors (np.ndarray): Raw embeddings, shape (n_patients, n_dimensions).
        scaler: The fitted StandardScaler from load_dimension_weights. Unused by `plain`.
        weights (np.ndarray): The dimension weights. Unused by `plain`.

    Returns:
        np.ndarray: float32 rows of unit length under that metric, so a dot product is the
            similarity.
    """
    if metric == 'weighted':
        return to_weighted_space(vectors, scaler, weights)
    if metric == 'plain':
        return to_plain_space(vectors)
    raise ValueError(f"Unknown metric {metric!r}; expected one of {METRICS}.")


def metric_suffix(metric: str) -> str:
    """The filename tail for a metric's own outputs. Empty for the primary one."""
    return '' if metric == PRIMARY_METRIC else f"_{metric}"


def roc_auc_by_column(y_true: np.ndarray, scores: np.ndarray, column_block: int = 2048) -> np.ndarray:
    """ROC AUC of every column of a score matrix against one label vector.

    The rank identity, not a curve: the AUC equals the mean rank of the positives, shifted
    and scaled. Ranking is what sklearn does internally anyway, and doing it for two
    thousand columns in one call is what makes thirty-four thousand AUCs affordable.
    Average ranks handle the heavy ties at small k, where a risk score can only be one of
    k + 1 values.

    Args:
        y_true (np.ndarray): Binary labels, shape (n_rows,).
        scores (np.ndarray): Score matrix, shape (n_rows, n_columns).
        column_block (int, optional): Columns ranked per call, to bound memory.

    Returns:
        np.ndarray: AUC per column, shape (n_columns,).
    """
    positives = y_true.astype(bool)
    n_positive = int(positives.sum())
    n_negative = int(y_true.size - n_positive)
    if n_positive == 0 or n_negative == 0:
        return np.full(scores.shape[1], np.nan)
    out = np.empty(scores.shape[1], dtype=np.float64)
    for start in range(0, scores.shape[1], column_block):
        stop = min(start + column_block, scores.shape[1])
        ranks = rankdata(scores[:, start:stop], axis=0)
        rank_sum = ranks[positives].sum(axis=0)
        out[start:stop] = (rank_sum - n_positive * (n_positive + 1) / 2) / (n_positive * n_negative)
    return out


def risk_by_neighbour_count(
    anchors: np.ndarray,
    pool: np.ndarray,
    pool_labels: np.ndarray,
    alphas: tuple[float, ...],
    fallback_risk: float,
) -> tuple[dict[float, np.ndarray], dict[float, int]]:
    """Risk score for every anchor at every neighbourhood size from 1 to the whole pool.

    Every alpha is filled from the SAME sorted similarity block. Ranking the pool is the
    expensive half and does not depend on alpha, so sorting once and sharpening three ways
    costs barely more than sweeping one exponent.

    Args:
        anchors (np.ndarray): Anchor rows in weighted space, shape (n_anchors, n_dimensions).
        pool (np.ndarray): Candidate rows in weighted space, shape (n_pool, n_dimensions).
        pool_labels (np.ndarray): TRD flag per candidate, shape (n_pool,).
        alphas (tuple[float, ...]): Sharpening exponents passed to neighbour_weights.
        fallback_risk (float): Risk assigned where the k nearest candidates all have
            non-positive similarity, so the weights sum to zero and the ratio is undefined.
            The pool prevalence is the no-information answer, and giving every such anchor
            the same constant leaves them tied rather than spuriously ordered.

    Returns:
        tuple[dict[float, np.ndarray], dict[float, int]]: (alpha to float32 risk matrix of
            shape (n_anchors, n_pool), where column j - 1 is the risk at k = j; alpha to
            the number of undefined entries filled with fallback_risk).
    """
    n_anchors, n_pool = anchors.shape[0], pool.shape[0]
    risks = {alpha: np.empty((n_anchors, n_pool), dtype=np.float32) for alpha in alphas}
    n_undefined = {alpha: 0 for alpha in alphas}
    labels = pool_labels.astype(np.float64)
    for start in range(0, n_anchors, ANCHOR_BLOCK):
        stop = min(start + ANCHOR_BLOCK, n_anchors)
        similarities = anchors[start:stop] @ pool.T
        order = np.argsort(-similarities, axis=1, kind='stable')
        sorted_similarities = np.take_along_axis(similarities, order, axis=1).astype(np.float64)
        sorted_labels = labels[order]
        for alpha in alphas:
            weights = neighbour_weights(sorted_similarities, alpha)
            numerator = np.cumsum(weights * sorted_labels, axis=1)
            denominator = np.cumsum(weights, axis=1)
            undefined = denominator <= 0
            n_undefined[alpha] += int(undefined.sum())
            np.divide(numerator, denominator, out=numerator, where=~undefined)
            numerator[undefined] = fallback_risk
            risks[alpha][start:stop] = numerator.astype(np.float32)
    return risks, n_undefined


def interval_neighbour_counts(n_pool: int, always_include: list[int]) -> np.ndarray:
    """The k values that get an error bar: log-spaced, plus whichever k won.

    Args:
        n_pool (int): Largest neighbourhood size.
        always_include (list[int]): Extra k values to force into the set, typically each
            curve's best k, so the bar the reader most wants is drawn.

    Returns:
        np.ndarray: Sorted unique k values.
    """
    spaced = np.unique(np.round(np.geomspace(1, n_pool, N_INTERVAL_POINTS)).astype(int))
    return np.unique(np.concatenate([spaced, np.asarray(always_include, dtype=int)]))


def bootstrap_intervals(y_true: np.ndarray, risks: np.ndarray, neighbour_counts: np.ndarray) -> pd.DataFrame:
    """Percentile bootstrap intervals for the AUC at the selected neighbourhood sizes.

    Resamples the anchors with bootstrap_sample_indices, the same SEED-seeded draws every
    other interval in this repository uses, so a bar here and a band on an ROC figure are
    cut from the same resamples.

    Args:
        y_true (np.ndarray): Anchor TRD labels, shape (n_anchors,).
        risks (np.ndarray): Risk matrix from risk_by_neighbour_count.
        neighbour_counts (np.ndarray): k values to interval, 1-based.

    Returns:
        pd.DataFrame: One row per k with columns n_neighbors, roc_auc, ci_low, ci_high.
    """
    return intervals_of_columns(y_true, risks[:, neighbour_counts - 1], neighbour_counts)


def intervals_of_columns(y_true: np.ndarray, columns: np.ndarray, neighbour_counts: np.ndarray) -> pd.DataFrame:
    """Percentile bootstrap intervals for risk columns already cut at their k values.

    Args:
        y_true (np.ndarray): Anchor TRD labels, shape (n_anchors,).
        columns (np.ndarray): Risk at each k, shape (n_anchors, len(neighbour_counts)).
        neighbour_counts (np.ndarray): The k each column was cut at, 1-based.

    Returns:
        pd.DataFrame: One row per k with columns n_neighbors, roc_auc, ci_low, ci_high.
    """
    point = roc_auc_by_column(y_true, columns)
    draws = bootstrap_sample_indices(y_true.size)
    sampled = np.empty((N_BOOTSTRAP, neighbour_counts.size), dtype=np.float64)
    for i in range(N_BOOTSTRAP):
        rows = draws[i]
        sampled[i] = roc_auc_by_column(y_true[rows], columns[rows])
    return pd.DataFrame({
        'n_neighbors': neighbour_counts,
        'roc_auc': point,
        'ci_low': np.nanpercentile(sampled, 2.5, axis=0),
        'ci_high': np.nanpercentile(sampled, 97.5, axis=0),
    })


def published_reference_lines() -> dict[str, float]:
    """AUCs already on record for this cohort, to draw the sweep against.

    Returns:
        dict[str, float]: Label to AUC, empty for any file not present.
    """
    references = {}
    results_dir = Path(os.environ['RESULTS_DIR'])
    knn_path = results_dir / 'knn_results.json'
    if knn_path.exists():
        knn = json.loads(knn_path.read_text())
        if 'NEAREST_COSINE' in knn:
            k = os.environ.get('NUM_NEIGHBOR_PATIENTS', '?')
            references[f"plain cosine KNN, k={k}"] = float(knn['NEAREST_COSINE']['roc_score'])
    ml_path = results_dir / 'classical_ml_results_EMBEDDED.json'
    if ml_path.exists():
        ml = json.loads(ml_path.read_text())
        if 'logistic_regression' in ml:
            references['logistic regression on embeddings'] = float(ml['logistic_regression']['roc_score'])
    return references


# How each metric is drawn. The colour carries the alpha and the line style carries the
# metric, so the reader compares two metrics at one k by looking down a vertical line.
METRIC_STYLES = {'weighted': ('-', "importance-weighted"), 'plain': ('--', "plain cosine")}


def plot_sweep(curves: pd.DataFrame, intervals: pd.DataFrame, save_path: Path) -> Path:
    """Draw ROC AUC against neighbourhood size, one line per metric and alpha.

    Args:
        curves (pd.DataFrame): Columns metric, alpha, n_neighbors, roc_auc -- every k.
        intervals (pd.DataFrame): Columns metric, alpha, n_neighbors, roc_auc, ci_low,
            ci_high.
        save_path (Path): Destination PNG.

    Returns:
        Path: save_path.
    """
    figure, axis = plt.subplots(figsize=(13.0, 6.0))
    colours = plt.rcParams['axes.prop_cycle'].by_key()['color']
    alphas = sorted(curves['alpha'].unique())
    metrics = [m for m in METRICS if m in set(curves['metric'])]
    for metric_index, metric in enumerate(metrics):
        style, metric_label = METRIC_STYLES[metric]
        for index, alpha in enumerate(alphas):
            colour = colours[index % len(colours)]
            selected = (curves['metric'] == metric) & (curves['alpha'] == alpha)
            curve = curves[selected].sort_values('n_neighbors')
            if curve.empty:
                continue
            axis.plot(curve['n_neighbors'], curve['roc_auc'], color=colour, linestyle=style,
                      linewidth=1.8, label=f"{metric_label}, alpha={alpha:g}")
            bars = intervals[(intervals['metric'] == metric)
                             & (intervals['alpha'] == alpha)].sort_values('n_neighbors')
            # Nudge the bars off each other on the log axis so two curves at the same k
            # stay separately readable; the line itself is drawn unshifted.
            slot = metric_index * len(alphas) + index
            offset = 1.0 + 0.06 * (slot - (len(alphas) * len(metrics) - 1) / 2)
            axis.errorbar(bars['n_neighbors'] * offset, bars['roc_auc'],
                          yerr=[bars['roc_auc'] - bars['ci_low'], bars['ci_high'] - bars['roc_auc']],
                          fmt='o', markersize=4, capsize=3, elinewidth=1.2, color=colour, alpha=0.85)
            best = curve.loc[curve['roc_auc'].idxmax()]
            axis.plot([best['n_neighbors']], [best['roc_auc']], marker='*', markersize=16,
                      color=colour, linestyle='none',
                      label=f"{metric_label} best k={int(best['n_neighbors'])}, "
                            f"AUC={best['roc_auc']:.3f}")
    reference_styles = ['--', ':']
    for index, (label, value) in enumerate(published_reference_lines().items()):
        axis.axhline(value, color='0.35', linestyle=reference_styles[index % len(reference_styles)],
                     linewidth=1.3, label=f"{label} = {value:.3f}")
    axis.axhline(0.5, color='0.7', linewidth=1.0)
    axis.set_xscale('log')
    axis.set_xlabel("Number of nearest neighbours, k")
    axis.set_ylabel("Held-out ROC AUC")
    axis.set_title("TRD risk from retrieved neighbours, by metric and neighbourhood size")
    axis.grid(alpha=0.3, which='both')
    axis.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9)
    figure.tight_layout()
    figure.savefig(save_path, dpi=FIGURE_DPI)
    plt.close(figure)
    return save_path


def run_sweep(alphas: tuple[float, ...], max_anchors: int = 0, max_pool: int = 0,
              metrics: tuple[str, ...] = METRICS) -> dict:
    """Score every neighbourhood size under every metric, write the tables and the figure.

    Metrics are swept one after another rather than together: each one holds an
    n_anchors x n_pool float32 risk matrix per alpha, so running them concurrently would
    multiply the peak by the number of metrics for no gain. The anchors, the pool and the
    labels are the same patients in the same order throughout, so the two curves are
    comparable at every k by construction.

    Args:
        alphas (tuple[float, ...]): Sharpening exponents to sweep.
        max_anchors (int, optional): Keep only this many anchors, for a smoke run.
            Defaults to 0, meaning all of them.
        max_pool (int, optional): Keep only this many candidates. Defaults to 0, all.
        metrics (tuple[str, ...], optional): Which spaces to sweep. Defaults to METRICS.

    Returns:
        dict: The summary written to sweep_summary.json.
    """
    # A CAPPED RUN NEVER WRITES OVER THE REAL ONE. --max-anchors and --max-pool exist to
    # prove the wiring on a laptop-sized slice, and the summary they produce is the same
    # filename as the six-hour job's. Sending it to its own directory is the difference
    # between a smoke run and losing the result nobody has re-run since.
    out_dir = SWEEP_DIR / 'smoke' if (max_anchors or max_pool) else SWEEP_DIR
    os.makedirs(out_dir, exist_ok=True)
    test_ids = create_train_test_split()[1]
    anchor_ids = sorted(test_ids)
    pool_ids = candidate_pool_ids(exclude_ids=test_ids)
    if max_anchors:
        anchor_ids = anchor_ids[:max_anchors]
    if max_pool:
        pool_ids = pool_ids[:max_pool]

    weights, scaler = load_dimension_weights()
    concentration = concentration_summary(weights)
    (out_dir / 'dimension_importance.json').write_text(json.dumps(concentration, indent=4))
    print(f"Dimension weights: {concentration['n_nonzero_dimensions']} of "
          f"{concentration['n_dimensions']} dimensions non-zero", flush=True)

    # Read once and keep the raw rows: both metrics start from the same embeddings and
    # differ only in what they do to them, so re-reading the table per metric would be
    # two minutes of sqlite to produce identical bytes.
    raw_anchors = load_raw_embeddings(anchor_ids)
    raw_pool = load_raw_embeddings(pool_ids)
    print(f"Anchors {raw_anchors.shape}, candidate pool {raw_pool.shape}", flush=True)

    trd_ids = load_trd_set()
    anchor_labels = np.array([1 if pid in trd_ids else 0 for pid in anchor_ids])
    pool_labels = np.array([1 if pid in trd_ids else 0 for pid in pool_ids])
    prevalence = float(pool_labels.mean())

    curve_frames = []
    interval_frames = []
    summary = {
        'n_anchors': len(anchor_ids),
        'n_pool': len(pool_ids),
        'anchor_trd_prevalence': float(anchor_labels.mean()),
        'pool_trd_prevalence': prevalence,
        'dimension_importance': concentration,
        'metrics': list(metrics),
        'by_metric': {},
    }
    for metric in metrics:
        anchors = to_metric_space(metric, raw_anchors, scaler, weights)
        pool = to_metric_space(metric, raw_pool, scaler, weights)
        suffix = metric_suffix(metric)
        per_alpha = {}
        print(f"[{metric}] sweeping alphas {list(alphas)} over k = 1 .. {len(pool_ids)}...",
              flush=True)
        risks, n_undefined = risk_by_neighbour_count(anchors, pool, pool_labels, alphas, prevalence)
        for alpha in alphas:
            auc = roc_auc_by_column(anchor_labels, risks[alpha])
            curve_frames.append(pd.DataFrame({
                'metric': metric,
                'alpha': alpha,
                'n_neighbors': np.arange(1, len(pool_ids) + 1),
                'roc_auc': auc,
            }))
            best_index = int(np.nanargmax(auc))
            best_k = best_index + 1
            interval = bootstrap_intervals(anchor_labels, risks[alpha],
                                           interval_neighbour_counts(len(pool_ids), [best_k, PRIMARY_NEIGHBOUR_COUNT]))
            interval.insert(0, 'metric', metric)
            interval.insert(1, 'alpha', alpha)
            interval_frames.append(interval)
            best_row = interval[interval['n_neighbors'] == best_k].iloc[0]
            # The best k is the largest of thirty-four thousand held-out AUCs, so it is
            # selected ON the anchors and is optimistic by however much the curve is
            # peaked. `roc_auc_at_all_neighbors` is the same curve read at a k nobody
            # chose, and is the number to quote when that matters.
            per_alpha[f"{alpha:g}"] = {
                'best_n_neighbors': best_k,
                'best_roc_auc': float(auc[best_index]),
                'best_roc_auc_ci_low': float(best_row['ci_low']),
                'best_roc_auc_ci_high': float(best_row['ci_high']),
                'roc_auc_at_all_neighbors': float(auc[-1]),
                'n_undefined_risk_entries': n_undefined[alpha],
            }
            pd.DataFrame({
                'anchor_patient_id': anchor_ids,
                'true_label': anchor_labels,
                'predicted_risk': risks[alpha][:, best_index],
            }).to_csv(out_dir / f"best_k_predictions_alpha{alpha:g}{suffix}.csv", index=False)
            print(f"  [{metric}] alpha={alpha:g}: best k={best_k}, AUC={auc[best_index]:.4f} "
                  f"[{best_row['ci_low']:.4f}, {best_row['ci_high']:.4f}], "
                  f"AUC at k=pool {auc[-1]:.4f}", flush=True)
        summary['by_metric'][metric] = per_alpha
        del risks, anchors, pool

    # The primary metric also sits at the top level under the name it had before plain
    # cosine joined it, so nothing that already reads this file has to learn a new path.
    summary['by_alpha'] = summary['by_metric'].get(PRIMARY_METRIC, {})

    curves = pd.concat(curve_frames, ignore_index=True)
    intervals = pd.concat(interval_frames, ignore_index=True)
    curves.to_csv(out_dir / 'sweep_curve.csv', index=False)
    intervals.to_csv(out_dir / 'sweep_intervals.csv', index=False)
    (out_dir / 'sweep_summary.json').write_text(json.dumps(summary, indent=4))
    figure_path = plot_sweep(curves, intervals, out_dir / 'neighbor_count_sweep.png')
    print(f"Wrote {figure_path}", flush=True)
    return summary


def risk_at_counts(anchors: np.ndarray, pool: np.ndarray, pool_labels: np.ndarray,
                   neighbour_counts: np.ndarray, alphas: tuple[float, ...],
                   fallback_risk: float) -> dict[float, np.ndarray]:
    """The risk score at a few k, ranked and weighted exactly as risk_by_neighbour_count.

    Args:
        anchors (np.ndarray): Anchor rows in the metric space, shape (n_anchors, d).
        pool (np.ndarray): Candidate rows in the same space, shape (n_pool, d).
        pool_labels (np.ndarray): Candidate TRD labels, shape (n_pool,).
        neighbour_counts (np.ndarray): Sorted k values, 1-based.
        alphas (tuple[float, ...]): Sharpening exponents.
        fallback_risk (float): Risk where every weight in the neighbourhood is zero.

    Returns:
        dict[float, np.ndarray]: alpha to a risk matrix of shape
            (n_anchors, len(neighbour_counts)).
    """
    ks = np.asarray(neighbour_counts, dtype=int)
    deepest = int(ks.max())
    labels_all = pool_labels.astype(np.float64)
    out = {alpha: np.empty((anchors.shape[0], ks.size)) for alpha in alphas}
    for start in range(0, anchors.shape[0], ANCHOR_BLOCK):
        stop = min(start + ANCHOR_BLOCK, anchors.shape[0])
        similarities = anchors[start:stop] @ pool.T
        order = np.argsort(-similarities, axis=1, kind='stable')[:, :deepest]
        nearest = np.take_along_axis(similarities, order, axis=1).astype(np.float64)
        labels = labels_all[order]
        for alpha in alphas:
            w = neighbour_weights(nearest, alpha)
            numerator = np.cumsum(w * labels, axis=1)[:, ks - 1]
            denominator = np.cumsum(w, axis=1)[:, ks - 1]
            risk = np.full(numerator.shape, fallback_risk)
            np.divide(numerator, denominator, out=risk, where=denominator > 0)
            out[alpha][start:stop] = risk
    return out


def intervals_at(neighbour_counts: list[int], alphas: tuple[float, ...],
                 metrics: tuple[str, ...] = METRICS) -> pd.DataFrame:
    """Add bootstrap intervals at chosen k to sweep_intervals.csv without re-running the sweep.

    The sweep holds a risk matrix for every k and costs hours; an interval at a handful of
    k needs only the risk at those k. Neighbours are ranked with the same stable sort and
    weighted with the same neighbour_weights, so a point estimate here equals the sweep's
    curve at that k, and the draws are the same SEED-seeded resamples.

    Args:
        neighbour_counts (list[int]): The k values to interval, 1-based.
        alphas (tuple[float, ...]): Sharpening exponents.
        metrics (tuple[str, ...], optional): Similarity spaces. Defaults to METRICS.

    Returns:
        pd.DataFrame: The rows written, with columns metric, alpha, n_neighbors, roc_auc,
            ci_low, ci_high.
    """
    ks = np.asarray(sorted(set(neighbour_counts)), dtype=int)
    test_ids = create_train_test_split()[1]
    anchor_ids = sorted(test_ids)
    pool_ids = candidate_pool_ids(exclude_ids=test_ids)
    weights, scaler = load_dimension_weights()
    raw_anchors = load_raw_embeddings(anchor_ids)
    raw_pool = load_raw_embeddings(pool_ids)
    trd_ids = load_trd_set()
    anchor_labels = np.array([1 if pid in trd_ids else 0 for pid in anchor_ids])
    pool_labels = np.array([1 if pid in trd_ids else 0 for pid in pool_ids], dtype=np.float64)
    prevalence = float(pool_labels.mean())
    frames = []
    for metric in metrics:
        anchors = to_metric_space(metric, raw_anchors, scaler, weights)
        pool = to_metric_space(metric, raw_pool, scaler, weights)
        columns = risk_at_counts(anchors, pool, pool_labels, ks, alphas, prevalence)
        for alpha in alphas:
            frame = intervals_of_columns(anchor_labels, columns[alpha], ks)
            frame.insert(0, 'metric', metric)
            frame.insert(1, 'alpha', alpha)
            frames.append(frame)
    new = pd.concat(frames, ignore_index=True)
    path = SWEEP_DIR / 'sweep_intervals.csv'
    old = pd.read_csv(path)
    key = ['metric', 'alpha', 'n_neighbors']
    kept = old.merge(new[key], on=key, how='left', indicator=True)
    kept = kept[kept['_merge'] == 'left_only'].drop(columns='_merge')
    pd.concat([kept, new], ignore_index=True).sort_values(key).to_csv(path, index=False)
    print(new.to_string(index=False), flush=True)
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alphas', type=float, nargs='+', default=list(DEFAULT_ALPHAS),
                        help="Sharpening exponents applied to the similarity before it is used as a weight.")
    parser.add_argument('--max-anchors', type=int, default=0,
                        help="Smoke-run cap on the number of anchors; 0 uses the whole test split.")
    parser.add_argument('--max-pool', type=int, default=0,
                        help="Smoke-run cap on the candidate pool; 0 uses every non-anchor patient.")
    parser.add_argument('--metrics', nargs='+', default=list(METRICS), choices=list(METRICS),
                        help="Which similarity spaces to sweep. Both, by default, because the "
                             "point of the second one is the comparison with the first.")
    parser.add_argument('--intervals-at', type=int, nargs='+', default=None,
                        help="Only add bootstrap intervals at these k to sweep_intervals.csv, "
                             "ranking neighbours exactly as the sweep does; minutes, not hours.")
    arguments = parser.parse_args()
    if arguments.intervals_at:
        intervals_at(arguments.intervals_at, tuple(arguments.alphas), tuple(arguments.metrics))
        return
    run_sweep(tuple(arguments.alphas), arguments.max_anchors, arguments.max_pool,
              tuple(arguments.metrics))


if __name__ == '__main__':
    main()
