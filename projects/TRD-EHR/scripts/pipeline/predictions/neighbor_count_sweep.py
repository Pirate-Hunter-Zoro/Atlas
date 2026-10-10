"""Sweep the neighbourhood size of every retrieval arm and plot ROC against it.

Three arms, each scored at every k from a single neighbour to the whole training pool:

  * `weighted`: the importance-weighted cosine (importance_weighted_knn.py);
  * `plain`: plain cosine on the raw embedding, L2-normalised, with nothing supervised in
    it;
  * `random`: k training patients drawn at random for each anchor, weighted uniformly, so
    the risk is the plain mean TRD flag of the draw. It is the floor the other two are
    read against.

Under either cosine metric the whole similarity matrix is one matmul, so every k can be
scored at once: sort each anchor's candidates by similarity, take running sums of the
weights and of the weighted TRD flags, and the risk at every k falls out of one division.
The random arm has no ranking to sort by. Each anchor gets its own random ordering of the
pool, and the running count of TRD flags along that ordering divided by k is the risk at
every k, nested, so k + 1 neighbours are the k neighbours plus one more.

INTERVALS DIFFER BY ARM, BECAUSE THE UNCERTAINTY DOES. The cosine arms are deterministic
given the patients, so their intervals are a percentile bootstrap over the 8,516 test
patients, at N_INTERVAL_POINTS log-spaced k plus each curve's best k. The random arm's
uncertainty is the draw itself: it is repeated N_RANDOM_DRAWS times and its band at every
k is the 2.5th to 97.5th percentile of the AUC across draws, on the same test patients.
Draw r uses the generator seeded by SeedSequence(SEED).spawn(N_RANDOM_DRAWS)[r], so any
draw can be regenerated alone and the result does not depend on the worker count.

BEST k IS CHOSEN ON THE TEST PATIENTS AND IS OPTIMISTIC. For each arm it is the k with
the highest held-out AUC (for `random`, the highest mean AUC across draws), the smallest
such k on a tie. Nothing held out from the selection exists, so every best-k number is an
upper estimate by however much its curve is noise-peaked. That is worst for `random`,
whose true AUC is 0.5 at every k: its best k is the largest of thirty-four thousand noisy
means and says nothing about k. `roc_auc_at_all_neighbors` is each curve read at a k
nobody chose.

Run it with -m scripts.pipeline.predictions.neighbor_count_sweep; everything lands in
RESULTS_DIR/neighbor_count_sweep. The panels at each arm's best k are drawn afterwards by
scripts.pipeline.predictions.best_k_panels, from the files this writes.

To regenerate, submit slurm_jobs/quick_runs/neighbor_count_sweep.sbatch from the project
root: it runs this, plot_neighbor_sweep_figure and best_k_panels, and mirrors the folder
into results/. Two review analyses read best_k_predictions_*.csv and are re-run after
it: review/history_quintiles (Table S8) and review/subgroups (S9). review/metric_intervals
does not depend on the sweep.
"""

import argparse
import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
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

# The neighbourhood size the retrieval pipeline (trd_prediction_computation) uses for
# knn_results.json. It is a reference point, not an analysis: it always gets an error bar
# so the supplement's table can set both metrics at it beside their best k, and the random
# arm is read at it as a crosscheck against the pipeline's RANDOM_UNIFORM arm.
PIPELINE_NEIGHBOUR_COUNT = 50

# The random-neighbour arm. Its name in the summary and its filename tail.
RANDOM_ARM = 'random'

# How many independent random draws the random arm is repeated over. The same count as
# N_BOOTSTRAP, so its band's 2.5th and 97.5th percentiles are cut from as many values as
# every bootstrap interval in the repository.
N_RANDOM_DRAWS = N_BOOTSTRAP

# The percentiles of the AUC across draws that bound the random arm's band.
RANDOM_BAND_PERCENTILES = (2.5, 97.5)

# Every draw's AUC at the random arm's best k, one row per draw.
RANDOM_DRAWS_AT_BEST = 'random_draw_aucs_at_best_k.csv'

# Columns scored per bincount in auc_of_count_columns. Bounds memory at roughly
# block x (largest count + 1) x 8 bytes per histogram.
COUNT_COLUMN_BLOCK = 512


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


def random_neighbour_counts(pool_labels: np.ndarray, n_anchors: int, rng: np.random.Generator) -> np.ndarray:
    """Running TRD count along an independent random ordering of the pool, per anchor.

    Row i is anchor i's own shuffle of the pool labels, cumulatively summed, so entry
    (i, k - 1) is the number of TRD patients among anchor i's k random neighbours. The
    draws are nested: anchor i's k + 1 neighbours are its k neighbours plus one more.
    Rows are shuffled block by block in anchor order, so the same generator state always
    gives the same matrix.

    Args:
        pool_labels (np.ndarray): 0/1 TRD flag per candidate, shape (n_pool,).
        n_anchors (int): Number of anchors, one independent ordering each.
        rng (np.random.Generator): The draw's generator.

    Returns:
        np.ndarray: Unsigned integer counts, shape (n_anchors, n_pool); uint16 while the
            pool holds fewer than 65,536 TRD patients, which halves the memory of uint32.
    """
    labels = np.asarray(pool_labels).astype(np.int8)
    n_pool = labels.size
    dtype = np.uint16 if int(labels.sum()) < np.iinfo(np.uint16).max else np.uint32
    counts = np.empty((n_anchors, n_pool), dtype=dtype)
    for start in range(0, n_anchors, ANCHOR_BLOCK):
        stop = min(start + ANCHOR_BLOCK, n_anchors)
        shuffled = rng.permuted(np.broadcast_to(labels, (stop - start, n_pool)), axis=1)
        np.cumsum(shuffled, axis=1, dtype=dtype, out=counts[start:stop])
    return counts


def random_neighbour_risk(pool_labels: np.ndarray, n_anchors: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform-weight risk of k random neighbours, at every k, per anchor.

    Args:
        pool_labels (np.ndarray): 0/1 TRD flag per candidate, shape (n_pool,).
        n_anchors (int): Number of anchors.
        rng (np.random.Generator): The draw's generator.

    Returns:
        np.ndarray: float32 risk matrix of shape (n_anchors, n_pool), column j - 1 the
            mean TRD flag of the first j random neighbours. The last column is the pool
            prevalence for every anchor.
    """
    counts = random_neighbour_counts(pool_labels, n_anchors, rng)
    return (counts / np.arange(1, counts.shape[1] + 1)).astype(np.float32)


def auc_of_count_columns(y_true: np.ndarray, counts: np.ndarray, column_block: int = COUNT_COLUMN_BLOCK) -> np.ndarray:
    """ROC AUC of every column of an integer count matrix, without sorting.

    Every anchor's random-arm risk at k is its count divided by the same k, so ranking the
    counts ranks the risks and the AUC of a column is the AUC of its counts. Counts are
    small integers, so the Mann-Whitney statistic comes from two histograms: each positive
    beats every negative with a lower count and ties half of those with an equal one. That
    is the average-rank rule roc_auc_by_column uses, in linear time rather than a sort.

    Args:
        y_true (np.ndarray): Binary labels, shape (n_rows,).
        counts (np.ndarray): Non-negative integer scores, shape (n_rows, n_columns).
        column_block (int, optional): Columns histogrammed per call, to bound memory.

    Returns:
        np.ndarray: AUC per column, shape (n_columns,).
    """
    positives = np.asarray(y_true).astype(bool)
    n_positive = int(positives.sum())
    n_negative = int(positives.size - n_positive)
    if n_positive == 0 or n_negative == 0:
        return np.full(counts.shape[1], np.nan)
    out = np.empty(counts.shape[1], dtype=np.float64)
    for start in range(0, counts.shape[1], column_block):
        stop = min(start + column_block, counts.shape[1])
        block = counts[:, start:stop].astype(np.int64)
        width = int(block.max()) + 1
        offsets = block + np.arange(stop - start, dtype=np.int64) * width
        size = (stop - start) * width
        positive_hist = np.bincount(offsets[positives].ravel(), minlength=size).reshape(-1, width)
        negative_hist = np.bincount(offsets[~positives].ravel(), minlength=size).reshape(-1, width)
        negatives_below = np.cumsum(negative_hist, axis=1) - negative_hist
        wins = (positive_hist * (negatives_below + 0.5 * negative_hist)).sum(axis=1)
        out[start:stop] = wins / (n_positive * n_negative)
    return out


def random_draw_seeds(n_draws: int, seed: int) -> list[np.random.SeedSequence]:
    """One independent seed per random draw, all spawned from SEED.

    Args:
        n_draws (int): Number of draws.
        seed (int): The root seed, SEED in production.

    Returns:
        list[np.random.SeedSequence]: Entry r seeds draw r, whatever else is drawn.
    """
    return np.random.SeedSequence(seed).spawn(n_draws)


def random_draw_auc(seed: np.random.SeedSequence, pool_labels: np.ndarray, anchor_labels: np.ndarray) -> np.ndarray:
    """AUC at every k for one random draw. Top level, so a worker process can run it.

    Args:
        seed (np.random.SeedSequence): This draw's seed, from random_draw_seeds.
        pool_labels (np.ndarray): 0/1 TRD flag per candidate, shape (n_pool,).
        anchor_labels (np.ndarray): 0/1 TRD flag per anchor, shape (n_anchors,).

    Returns:
        np.ndarray: float32 AUC per k, shape (n_pool,).
    """
    counts = random_neighbour_counts(pool_labels, anchor_labels.size, np.random.default_rng(seed))
    return auc_of_count_columns(anchor_labels, counts).astype(np.float32)


def random_neighbour_sweep(anchor_labels: np.ndarray, pool_labels: np.ndarray, n_draws: int,
                           seed: int, n_workers: int = 1) -> np.ndarray:
    """AUC at every k for every random draw.

    Each draw holds one n_anchors x n_pool count matrix, about 0.6 GB at full size, so the
    draws run in worker processes, one draw per task. Seeds are fixed per draw before any
    worker starts, so the matrix is the same for one worker or thirty-two.

    Args:
        anchor_labels (np.ndarray): 0/1 TRD flag per anchor, shape (n_anchors,).
        pool_labels (np.ndarray): 0/1 TRD flag per candidate, shape (n_pool,).
        n_draws (int): How many draws.
        seed (int): Root seed for random_draw_seeds.
        n_workers (int, optional): Worker processes; 1 runs in this process.

    Returns:
        np.ndarray: float32 matrix of shape (n_draws, n_pool), row r draw r, column j - 1
            the AUC at k = j.
    """
    seeds = random_draw_seeds(n_draws, seed)
    pool_labels = np.asarray(pool_labels).astype(np.int8)
    anchor_labels = np.asarray(anchor_labels).astype(np.int8)
    out = np.empty((n_draws, pool_labels.size), dtype=np.float32)
    if n_workers <= 1:
        for r, draw_seed in enumerate(seeds):
            out[r] = random_draw_auc(draw_seed, pool_labels, anchor_labels)
        return out
    context = multiprocessing.get_context('fork')
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=context) as pool:
        futures = [pool.submit(random_draw_auc, draw_seed, pool_labels, anchor_labels)
                   for draw_seed in seeds]
        for r, future in enumerate(futures):
            out[r] = future.result()
            if (r + 1) % 50 == 0 or r + 1 == n_draws:
                print(f"  [{RANDOM_ARM}] {r + 1} of {n_draws} draws scored", flush=True)
    return out


def summarise_random_draws(draw_aucs: np.ndarray) -> pd.DataFrame:
    """The random arm's curve and its band across draws, at every k.

    Args:
        draw_aucs (np.ndarray): Output of random_neighbour_sweep, shape (n_draws, n_pool).

    Returns:
        pd.DataFrame: One row per k with columns n_neighbors, roc_auc (mean across draws),
            ci_low and ci_high (RANDOM_BAND_PERCENTILES across draws).
    """
    draws = draw_aucs.astype(np.float64)
    low, high = np.nanpercentile(draws, RANDOM_BAND_PERCENTILES, axis=0)
    return pd.DataFrame({
        'n_neighbors': np.arange(1, draws.shape[1] + 1),
        'roc_auc': np.nanmean(draws, axis=0),
        'ci_low': low,
        'ci_high': high,
    })


def best_neighbour_index(auc: np.ndarray) -> int:
    """Column of the highest AUC; the smallest k wins a tie.

    Args:
        auc (np.ndarray): AUC per k, column j - 1 for k = j.

    Returns:
        int: The 0-based column, so best k is this plus one.
    """
    return int(np.nanargmax(auc))


def representative_draw(draw_aucs: np.ndarray, column: int) -> int:
    """The draw whose AUC at one k sits closest to the mean across draws there.

    The panels at the random arm's best k need ONE vector of predictions, and the number
    printed on them should be the arm's number, not whichever draw came first. The lowest
    draw index wins a tie.

    Args:
        draw_aucs (np.ndarray): Shape (n_draws, n_pool).
        column (int): 0-based k column.

    Returns:
        int: Draw index.
    """
    values = draw_aucs[:, column].astype(np.float64)
    return int(np.nanargmin(np.abs(values - np.nanmean(values))))


def effective_sample_sizes(anchors: np.ndarray, pool: np.ndarray,
                           counts_by_alpha: dict[float, int]) -> dict[float, np.ndarray]:
    """Effective sample size of each anchor's weighted neighbourhood at one k per alpha.

    ESS is (sum of weights)^2 / (sum of squared weights), the formula
    trd_prediction_computation writes for the pipeline's arms. It depends only on the k
    largest similarities, not on which of two tied candidates is ranked first, so a
    partition is enough and no sort is needed.

    Args:
        anchors (np.ndarray): Anchor rows in the metric space, shape (n_anchors, d).
        pool (np.ndarray): Candidate rows in the same space, shape (n_pool, d).
        counts_by_alpha (dict[float, int]): alpha to the k to read it at.

    Returns:
        dict[float, np.ndarray]: alpha to ESS per anchor, shape (n_anchors,). An anchor
            whose k weights are all zero gets 0.
    """
    out = {alpha: np.empty(anchors.shape[0]) for alpha in counts_by_alpha}
    for start in range(0, anchors.shape[0], ANCHOR_BLOCK):
        stop = min(start + ANCHOR_BLOCK, anchors.shape[0])
        similarities = (anchors[start:stop] @ pool.T).astype(np.float64)
        for alpha, k in counts_by_alpha.items():
            nearest = -np.partition(-similarities, k - 1, axis=1)[:, :k]
            w = neighbour_weights(nearest, alpha)
            total, squares = w.sum(axis=1), (w ** 2).sum(axis=1)
            ess = np.zeros(stop - start)
            np.divide(total ** 2, squares, out=ess, where=squares > 0)
            out[alpha][start:stop] = ess
    return out


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


def published_reference_lines() -> dict[str, tuple[float, float, float]]:
    """The trained classifier on record for this cohort, with its interval, to draw the sweep against.

    The retrieval pipeline's own k = 50 arms are not drawn: the sweep holds both cosine
    metrics at every k, and its random arm is the uniform one swept here.

    Returns:
        dict[str, tuple[float, float, float]]: Label to (AUC, ci_low, ci_high), empty when
            the classifier results are not present.
    """
    references = {}
    ml_path = Path(os.environ['RESULTS_DIR']) / 'classical_ml_results_EMBEDDED.json'
    if ml_path.exists():
        entry = json.loads(ml_path.read_text()).get('logistic_regression')
        if entry:
            references['logistic regression on embeddings'] = (
                float(entry['roc_score']), float(entry['roc_score_ci_low']),
                float(entry['roc_score_ci_high']))
    return references


# How each metric is drawn. The colour carries the alpha and the line style carries the
# metric, so the reader compares two metrics at one k by looking down a vertical line.
METRIC_STYLES = {'weighted': ('-', "logistic-regression-weighted"), 'plain': ('--', "plain cosine")}


def plot_sweep(curves: pd.DataFrame, intervals: pd.DataFrame, save_path: Path,
               random_curve: pd.DataFrame = None) -> Path:
    """Draw ROC AUC against neighbourhood size, one line per metric and alpha.

    Args:
        curves (pd.DataFrame): Columns metric, alpha, n_neighbors, roc_auc -- every k.
        intervals (pd.DataFrame): Columns metric, alpha, n_neighbors, roc_auc, ci_low,
            ci_high.
        save_path (Path): Destination PNG.
        random_curve (pd.DataFrame, optional): summarise_random_draws output, drawn as a
            grey mean line inside its across-draw band. Defaults to None, not drawn.

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
    if random_curve is not None:
        axis.fill_between(random_curve['n_neighbors'], random_curve['ci_low'], random_curve['ci_high'],
                          color='0.2', alpha=0.15, linewidth=0,
                          label=f"random neighbours, uniform: {RANDOM_BAND_PERCENTILES[0]:g}"
                                f"\u2013{RANDOM_BAND_PERCENTILES[1]:g} percentile of draws")
        axis.plot(random_curve['n_neighbors'], random_curve['roc_auc'], color='0.2', linewidth=1.2,
                  label="random neighbours, uniform: mean over draws")
        best = random_curve.iloc[best_neighbour_index(random_curve['roc_auc'].to_numpy())]
        axis.plot([best['n_neighbors']], [best['roc_auc']], marker='*', markersize=16, color='0.2',
                  linestyle='none', label=f"random best k={int(best['n_neighbors'])}, "
                                          f"AUC={best['roc_auc']:.3f} ({best['ci_low']:.3f}\u2013{best['ci_high']:.3f})")
    reference_styles = ['--', '-.', ':']
    for index, (label, (value, low, high)) in enumerate(published_reference_lines().items()):
        axis.axhspan(low, high, color='0.35', alpha=0.08, linewidth=0)
        axis.axhline(value, color='0.35', linestyle=reference_styles[index % len(reference_styles)],
                     linewidth=1.3, label=f"{label} = {value:.3f} ({low:.3f}\u2013{high:.3f})")
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


def run_random_arm(anchor_ids: list[str], anchor_labels: np.ndarray, pool_labels: np.ndarray,
                   n_draws: int, out_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Sweep the random-neighbour arm, write its curve and its best-k predictions.

    Args:
        anchor_ids (list[str]): Anchor patient IDs, in row order.
        anchor_labels (np.ndarray): 0/1 TRD flag per anchor.
        pool_labels (np.ndarray): 0/1 TRD flag per candidate.
        n_draws (int): Number of random draws.
        out_dir (Path): The sweep's output folder.

    Returns:
        tuple[pd.DataFrame, dict]: (the curve written to random_neighbour_curve.csv, the
            summary block written under sweep_summary.json's `random` key).
    """
    seed = int(os.environ['SEED'])
    n_workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 1))
    print(f"[{RANDOM_ARM}] {n_draws} draws over k = 1 .. {pool_labels.size} on {n_workers} "
          f"worker(s), seed {seed}...", flush=True)
    draw_aucs = random_neighbour_sweep(anchor_labels, pool_labels, n_draws, seed, n_workers)
    curve = summarise_random_draws(draw_aucs)
    curve.to_csv(out_dir / 'random_neighbour_curve.csv', index=False)

    best_index = best_neighbour_index(curve['roc_auc'].to_numpy())
    best = curve.iloc[best_index]
    # The panels need one prediction vector: the draw closest to the arm's mean AUC at its
    # best k, regenerated from its own seed rather than kept from the sweep.
    draw = representative_draw(draw_aucs, best_index)
    rng = np.random.default_rng(random_draw_seeds(n_draws, seed)[draw])
    k = best_index + 1
    risk = random_neighbour_counts(pool_labels, anchor_labels.size, rng)[:, best_index] / k
    # Every draw's AUC at the best k, so a contrast against this arm can carry the spread
    # across draws and not only that of the one draw the panels are drawn from.
    pd.DataFrame({
        'draw': np.arange(n_draws),
        'n_neighbors': k,
        'roc_auc': draw_aucs[:, best_index].astype(np.float64),
    }).to_csv(out_dir / RANDOM_DRAWS_AT_BEST, index=False)
    del draw_aucs
    anchor_interval = intervals_of_columns(anchor_labels, risk[:, None], np.array([k])).iloc[0]
    pd.DataFrame({
        'anchor_patient_id': anchor_ids,
        'true_label': anchor_labels,
        'predicted_risk': risk,
        'ess': float(k),
    }).to_csv(out_dir / f"best_k_predictions_{RANDOM_ARM}.csv", index=False)

    pipeline = curve.iloc[min(PIPELINE_NEIGHBOUR_COUNT, len(curve)) - 1]
    summary = {
        'weighting': 'uniform',
        'n_draws': n_draws,
        'seed': seed,
        'seed_scheme': "draw r uses numpy default_rng(SeedSequence(SEED).spawn(n_draws)[r])",
        'band': f"{RANDOM_BAND_PERCENTILES[0]:g}th to {RANDOM_BAND_PERCENTILES[1]:g}th "
                "percentile of the AUC across draws, same test patients",
        'best_rule': "k with the highest mean AUC across draws, smallest k on a tie; chosen "
                     "on the test patients, so optimistic",
        'best_n_neighbors': k,
        'best_roc_auc': float(best['roc_auc']),
        'best_roc_auc_ci_low': float(best['ci_low']),
        'best_roc_auc_ci_high': float(best['ci_high']),
        'representative_draw': draw,
        'representative_draw_roc_auc': float(anchor_interval['roc_auc']),
        'representative_draw_roc_auc_ci_low': float(anchor_interval['ci_low']),
        'representative_draw_roc_auc_ci_high': float(anchor_interval['ci_high']),
        'roc_auc_at_pipeline_neighbors': {
            'n_neighbors': int(pipeline['n_neighbors']),
            'roc_auc': float(pipeline['roc_auc']),
            'ci_low': float(pipeline['ci_low']),
            'ci_high': float(pipeline['ci_high']),
        },
        'roc_auc_at_all_neighbors': float(curve['roc_auc'].iloc[-1]),
        'mean_ess_at_best': float(k),
    }
    print(f"  [{RANDOM_ARM}] best k={k}, mean AUC={best['roc_auc']:.4f} "
          f"[{best['ci_low']:.4f}, {best['ci_high']:.4f}] across draws; draw {draw} "
          f"AUC={anchor_interval['roc_auc']:.4f} [{anchor_interval['ci_low']:.4f}, "
          f"{anchor_interval['ci_high']:.4f}] over anchors", flush=True)
    return curve, summary


def run_sweep(alphas: tuple[float, ...], max_anchors: int = 0, max_pool: int = 0,
              metrics: tuple[str, ...] = METRICS, random_draws: int = N_RANDOM_DRAWS) -> dict:
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
        random_draws (int, optional): Draws of the random-neighbour arm. Defaults to
            N_RANDOM_DRAWS; 0 skips the arm.

    Returns:
        dict: The summary written to sweep_summary.json.
    """
    # A CAPPED RUN NEVER WRITES OVER THE REAL ONE. --max-anchors and --max-pool exist to
    # prove the wiring on a laptop-sized slice, and the summary they produce is the same
    # filename as the full job's. Sending it to its own directory is the difference
    # between a smoke run and losing the full result.
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
        best_counts, best_risks = {}, {}
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
            best_index = best_neighbour_index(auc)
            best_k = best_index + 1
            best_counts[alpha] = best_k
            interval = bootstrap_intervals(anchor_labels, risks[alpha],
                                           interval_neighbour_counts(len(pool_ids), [best_k, PIPELINE_NEIGHBOUR_COUNT]))
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
            best_risks[alpha] = risks[alpha][:, best_index].copy()
            print(f"  [{metric}] alpha={alpha:g}: best k={best_k}, AUC={auc[best_index]:.4f} "
                  f"[{best_row['ci_low']:.4f}, {best_row['ci_high']:.4f}], "
                  f"AUC at k=pool {auc[-1]:.4f}", flush=True)
        del risks
        # ESS at each alpha's best k, in one more pass over the similarities, so the ESS
        # panel the pipeline draws for its k = 50 arms can be drawn at the best k too.
        ess = effective_sample_sizes(anchors, pool, best_counts)
        for alpha in alphas:
            per_alpha[f"{alpha:g}"]['mean_ess_at_best'] = float(ess[alpha].mean())
            pd.DataFrame({
                'anchor_patient_id': anchor_ids,
                'true_label': anchor_labels,
                'predicted_risk': best_risks[alpha],
                'ess': ess[alpha],
            }).to_csv(out_dir / f"best_k_predictions_alpha{alpha:g}{suffix}.csv", index=False)
        summary['by_metric'][metric] = per_alpha
        del anchors, pool, best_risks

    # The primary metric also sits at the top level under its original name, so nothing
    # that already reads this file has to learn a new path.
    summary['by_alpha'] = summary['by_metric'].get(PRIMARY_METRIC, {})

    random_curve = None
    if random_draws:
        del raw_anchors, raw_pool
        random_curve, summary[RANDOM_ARM] = run_random_arm(
            anchor_ids, anchor_labels, pool_labels, random_draws, out_dir)

    curves = pd.concat(curve_frames, ignore_index=True)
    intervals = pd.concat(interval_frames, ignore_index=True)
    curves.to_csv(out_dir / 'sweep_curve.csv', index=False)
    intervals.to_csv(out_dir / 'sweep_intervals.csv', index=False)
    (out_dir / 'sweep_summary.json').write_text(json.dumps(summary, indent=4))
    figure_path = plot_sweep(curves, intervals, out_dir / 'neighbor_count_sweep.png', random_curve)
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

    The sweep holds a risk matrix for every k and costs minutes per metric; an interval at a handful of
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
    parser.add_argument('--random-draws', type=int, default=N_RANDOM_DRAWS,
                        help="Random draws of the uniform random-neighbour arm, each scored "
                             "at every k; 0 skips the arm.")
    parser.add_argument('--intervals-at', type=int, nargs='+', default=None,
                        help="Only add bootstrap intervals at these k to sweep_intervals.csv, "
                             "ranking neighbours exactly as the sweep does, without the full sweep.")
    parser.add_argument('--redraw', action='store_true',
                        help="Redraw neighbor_count_sweep.png from the sweep_curve.csv and "
                             "sweep_intervals.csv already on disk; computes nothing.")
    arguments = parser.parse_args()
    if arguments.redraw:
        random_path = SWEEP_DIR / 'random_neighbour_curve.csv'
        if not random_path.exists():
            print(f"WARNING: {random_path} is absent; the working figure has no random arm.", flush=True)
        print(plot_sweep(pd.read_csv(SWEEP_DIR / 'sweep_curve.csv'),
                         pd.read_csv(SWEEP_DIR / 'sweep_intervals.csv'),
                         SWEEP_DIR / 'neighbor_count_sweep.png',
                         pd.read_csv(random_path) if random_path.exists() else None))
        return
    if arguments.intervals_at:
        intervals_at(arguments.intervals_at, tuple(arguments.alphas), tuple(arguments.metrics))
        return
    run_sweep(tuple(arguments.alphas), arguments.max_anchors, arguments.max_pool,
              tuple(arguments.metrics), arguments.random_draws)


if __name__ == '__main__':
    main()
