from pathlib import Path
import matplotlib.pyplot as plt 
import sklearn.metrics
import numpy as np
import os

from dotenv import load_dotenv
load_dotenv()

RESULTS_DIR = Path(os.environ['RESULTS_DIR'])
N_BOOTSTRAP = 1000
FPR_GRID = np.linspace(0,1,100)
# Recall grid for the precision-recall band, the same construction as FPR_GRID: a draw's
# own recall breakpoints land wherever its resampled ties fall, so the draws are
# interpolated onto one shared grid before any percentile is taken across them.
RECALL_GRID = np.linspace(0,1,100)
# Bin count for every calibration curve in this module.
CALIBRATION_BINS = 10

# Raster resolution for every figure written by this module. Matplotlib's default
# of 100 dpi yields a 640x480 PNG, which is ~107 dpi once placed at the
# manuscript's 6in text width -- legible but visibly soft in print. These figures
# are line art at publication size, so they are saved at a resolution that
# survives it. Font sizes are unaffected: dpi scales the raster, not the
# figure-relative text metrics.
FIGURE_DPI = 220

# Panel geometry for the manuscript. Every panel is placed one per row at the
# 6in text width of a US Letter page with 1in top/bottom margins, which leaves
# 9in of column height. Word cannot reflow text around an image, so a panel
# taller than about half that column cannot share a page with a second panel:
# the remainder of the page is left blank and the next panel starts overleaf.
# Drawing the panels wide and short is what removes those gaps without giving
# up any display width -- at 6in on the page a 10x5.4in panel is 3.24in tall,
# so two panels, their bold labels, and the shared caption all fit one page.
#
# Font sizes are absolute points, so widening the figure without raising them
# would shrink the type on the page: 10in placed at 6in is a 0.6x downscale.
# The sizes below are set to land near 8-10pt after that downscale, which is
# where the previous 6.4x4.8in panels already sat.
PANEL_FIGSIZE = (10.0, 5.4)
plt.rcParams.update({
    "font.size": 15,
    "axes.titlesize": 17,
    "axes.labelsize": 15,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 13,
    "figure.figsize": PANEL_FIGSIZE,
})


def curve_figure_path(family: str, stem: str, mode: str, save_dir: Path = None) -> Path:
    """Resolve (and create the parent of) the destination for one curve figure.

    Two callers want two layouts. The prediction pipelines file every figure of a kind
    together under RESULTS_DIR, one folder per curve family, because they compare many
    models on the same axes. The counterfactual pipeline files every figure of one
    CONTRAST together, because a contrast is the unit anybody reads. Passing save_dir
    switches to the second layout without duplicating the plotting code.

    Args:
        family (str): Subfolder under RESULTS_DIR for the default layout, e.g. 'roc_curves'.
        stem (str): Filename prefix, e.g. 'roc_curve'.
        mode (str): What produced the curve; becomes the filename suffix.
        save_dir (Path, optional): Write here instead, with the family folder dropped.
            Defaults to None (the RESULTS_DIR layout).

    Returns:
        Path: The figure path, parent directory created.
    """
    save_path = (save_dir / f"{stem}_{mode}.png") if save_dir is not None else (RESULTS_DIR / family / f"{stem}_{mode}.png")
    os.makedirs(save_path.parent, exist_ok=True)
    return save_path


def bootstrap_sample_indices(n_rows: int) -> np.ndarray:
    """Draw the row indices for N_BOOTSTRAP resamples of n_rows rows, with replacement.

    Seeded off SEED rather than off a passed-in generator, so the ROC band, the PR band
    and the calibration bars computed for one set of predictions are all cut from the
    SAME resamples. Anything else makes their intervals disagree for no reason a reader
    could see.

    Args:
        n_rows (int): Number of observations being resampled.

    Returns:
        np.ndarray: Integer index matrix of shape (N_BOOTSTRAP, n_rows).
    """
    rng = np.random.default_rng(seed=int(os.environ['SEED']))
    return rng.integers(low=0, high=n_rows, size=(N_BOOTSTRAP, n_rows))


def calibration_bin_edges(y_prob: np.ndarray, strategy: str) -> np.ndarray:
    """Cut the bin edges a calibration curve is built on.

    Args:
        y_prob (np.ndarray): The predicted probabilities being binned.
        strategy (str): 'uniform' for CALIBRATION_BINS equal-WIDTH bins across the unit
            interval, 'quantile' for equal-COUNT bins cut at the empirical quantiles.
            Reach for 'quantile' when the predictions crowd into part of the interval:
            equal-width bins over a distribution that lives below 0.4 spend half their
            bins on nobody, and the bins that do get patients get them unequally, so the
            noisiest points on the curve are the ones drawn most prominently.

    Returns:
        np.ndarray: Monotone increasing edges. Length CALIBRATION_BINS + 1 for 'uniform';
            possibly shorter for 'quantile', where tied quantiles collapse.
    """
    if strategy == 'uniform':
        return np.linspace(0.0, 1.0, CALIBRATION_BINS + 1)
    if strategy == 'quantile':
        return np.unique(np.quantile(y_prob, np.linspace(0.0, 1.0, CALIBRATION_BINS + 1)))
    raise ValueError(f"Unknown calibration binning strategy {strategy!r}; expected 'uniform' or 'quantile'.")


def assign_calibration_bins(y_prob: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    """Label each prediction with the index of the bin it falls in.

    Digitizes against the INTERIOR edges only, which is what keeps the two open ends
    closed: every value below the first interior edge is bin 0 and everything above the
    last is the final bin, so a prediction of exactly 0.0 or exactly 1.0 is binned rather
    than pushed out of range. That matters for quantile edges, whose outermost edges ARE
    the observed minimum and maximum.

    Args:
        y_prob (np.ndarray): Predicted probabilities.
        bin_edges (np.ndarray): Output of calibration_bin_edges.

    Returns:
        np.ndarray: Integer bin index per prediction, in [0, len(bin_edges) - 2].
    """
    return np.digitize(y_prob, bin_edges[1:-1])


def calibration_points(y_true: np.ndarray, y_prob: np.ndarray, bin_indices: np.ndarray, n_bins: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean predicted probability, observed event fraction and count, per fixed bin.

    Args:
        y_true (np.ndarray): Binary outcome.
        y_prob (np.ndarray): Predicted probabilities, aligned with y_true.
        bin_indices (np.ndarray): Output of assign_calibration_bins, aligned with y_true.
        n_bins (int): Number of bins, so an EMPTY bin still gets a slot and the arrays
            returned here line up across bootstrap draws that empty different bins.

    Returns:
        tuple: (mean predicted, observed fraction, count) each of length n_bins, with
            float('nan') in both rates wherever the bin took no patients.
    """
    mean_predicted = np.full(n_bins, np.nan)
    observed_fraction = np.full(n_bins, np.nan)
    counts = np.zeros(n_bins, dtype=int)
    for b in range(n_bins):
        in_bin = bin_indices == b
        counts[b] = int(in_bin.sum())
        if counts[b]:
            mean_predicted[b] = float(np.mean(y_prob[in_bin]))
            observed_fraction[b] = float(np.mean(y_true[in_bin]))
    return mean_predicted, observed_fraction, counts


def bootstrap_calibration_band(y_true: np.ndarray, y_prob: np.ndarray, sample_indices: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    """Observed event fraction per calibration bin, once per bootstrap draw.

    The bin edges are FIXED by the caller and reused on every draw. A draw that re-cut its
    own quantile edges would put a different set of patients in "bin 3" each time, and the
    spread across draws would then be a mixture of sampling noise and bin-membership
    churn -- which is not an interval in anything.

    Args:
        y_true (np.ndarray): Binary outcome.
        y_prob (np.ndarray): Predicted probabilities, aligned with y_true.
        sample_indices (np.ndarray): Row index matrix from bootstrap_sample_indices.
        bin_edges (np.ndarray): Output of calibration_bin_edges, cut on the FULL data.

    Returns:
        np.ndarray: Observed fractions of shape (N_BOOTSTRAP, len(bin_edges) - 1), holding
            float('nan') wherever a draw left a bin empty.
    """
    n_bins = len(bin_edges) - 1
    observed = np.full(shape=(sample_indices.shape[0], n_bins), fill_value=np.nan)
    for i in range(sample_indices.shape[0]):
        rows = sample_indices[i]
        draw_bins = assign_calibration_bins(y_prob[rows], bin_edges)
        _, observed[i], _ = calibration_points(y_true[rows], y_prob[rows], draw_bins, n_bins)
    return observed


def bootstrap_precision_recall_band(y_true: np.ndarray, y_prob: np.ndarray, sample_indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Interpolated precision per draw on RECALL_GRID, paired with each draw's average precision.

    The precision-recall counterpart of bootstrap_roc_band. sklearn returns the curve with
    recall DESCENDING, so each draw is reversed before interpolation; np.interp requires an
    increasing x.

    Args:
        y_true (np.ndarray): Binary outcome.
        y_prob (np.ndarray): Predicted probabilities, aligned with y_true.
        sample_indices (np.ndarray): Row index matrix from bootstrap_sample_indices.

    Returns:
        tuple[np.ndarray, np.ndarray]: (precision matrix of shape
            (N_BOOTSTRAP, len(RECALL_GRID)), average-precision array of length
            N_BOOTSTRAP). Draws that sampled a single class are left as float('nan').
    """
    precision_matrix = np.full(shape=(sample_indices.shape[0], len(RECALL_GRID)), fill_value=np.nan)
    average_precision = np.full(shape=(sample_indices.shape[0],), fill_value=np.nan)
    for i in range(sample_indices.shape[0]):
        y_true_sample = y_true[sample_indices[i]]
        y_prob_sample = y_prob[sample_indices[i]]
        if len(np.unique(y_true_sample)) < 2:
            continue
        average_precision[i] = sklearn.metrics.average_precision_score(y_true_sample, y_prob_sample)
        sample_precision, sample_recall, _ = sklearn.metrics.precision_recall_curve(y_true=y_true_sample, y_score=y_prob_sample)
        precision_matrix[i] = np.interp(RECALL_GRID, sample_recall[::-1], sample_precision[::-1])
    return (precision_matrix, average_precision)


def bootstrap_roc_band(y_true: np.ndarray, y_prob: np.ndarray, sample_indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Boostrapping logic on the given flags and predicted probabilities

    Args:
        y_true (np.ndarray): Actual flags
        y_prob (np.ndarray): Predicted probabilities
        sample_indices (np.ndarray): Bootstrapping sample indices to draw the sampled predictions and ROC scores from

    Returns:
        tuple[np.ndarray, np.ndarray]: Resulting interpolated TPR matrix, paired with the respective ROC scores from each sample
    """
    tpr_matrix = np.full(shape=(N_BOOTSTRAP, len(FPR_GRID)), fill_value=np.nan)
    auc_array = np.full(shape=(N_BOOTSTRAP,), fill_value=np.nan)
    for i in range(N_BOOTSTRAP):
        y_true_sample = y_true[sample_indices[i]]
        y_prob_sample = y_prob[sample_indices[i]]
        if len(np.unique(y_true_sample)) < 2: # Make sure by chance we did not sample only one class
            continue
        auc_array[i] = sklearn.metrics.roc_auc_score(y_true_sample, y_prob_sample)
        sample_fp, sample_tp, _ = sklearn.metrics.roc_curve(y_true=y_true_sample, y_score=y_prob_sample)
        # For FP and TP values, interpolate them on standard np.linspace(0,1,100) to force false positive rates on grid and then estimating respective true positive values
        interpolated_roc_curve = np.interp(FPR_GRID, sample_fp, sample_tp)
        interpolated_roc_curve[0] = 0.0
        tpr_matrix[i] = interpolated_roc_curve
    return (tpr_matrix, auc_array)

def plot_receiving_operator_characteristic(y_true: np.ndarray, y_prob: np.ndarray, mode: str, save_dir: Path = None, title: str = None) -> tuple[float,float,float]:
    """Create and save the ROC AUC plot and return its score results

    Args:
        y_true (np.ndarray): True class labels
        y_prob (np.ndarray): Estimated class probabilities
        mode (str): Description of the prediction schema that produced results
        save_dir (Path, optional): Write the figure here instead of under RESULTS_DIR.
            Defaults to None.
        title (str, optional): Replace the axes title, for callers whose outcome is not
            TRD. Defaults to None (the generic title).

    Returns:
        tuple[float,float,float]: ROC score, lower 2.5% boostrapping CI bound, upper 97.5% boostrapping CI bound
    """
    score = sklearn.metrics.roc_auc_score(y_true=y_true, y_score=y_prob)
    false_positive_rate, true_positive_rate, _ = sklearn.metrics.roc_curve(y_true=y_true, y_score=y_prob)
    
    # Bootstrapping for error bands
    sample_indices = bootstrap_sample_indices(y_true.shape[0])
    interpolated_tp, auc_arr = bootstrap_roc_band(y_true, y_prob, sample_indices)

    plt.figure(figsize=PANEL_FIGSIZE)
    # Error bands are 2.5 percentile and 97.5 percentile for each FP x-value on ROC curve which generates 95% confidence interval
    q_low = np.nanpercentile(interpolated_tp, 2.5, axis=0)
    q_high = np.nanpercentile(interpolated_tp, 97.5, axis=0)
    plt.fill_between(FPR_GRID, q_low, q_high, color='gray', alpha=0.2, label='95% CI')
    ci_low = np.nanpercentile(auc_arr, 2.5)
    ci_high = np.nanpercentile(auc_arr, 97.5)
    
    plt.plot(false_positive_rate, true_positive_rate, color='red', label=f'ROC curve (score {score:.2f}, 95% CI [{ci_low:.2f},{ci_high:.2f}])')
    plt.plot([0,1], [0,1], color='green', linestyle='--')
    plt.title(title if title is not None else "Receiver Operating Characteristic")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    
    plt.legend()
    plt.tight_layout()
    save_path = curve_figure_path("roc_curves", "roc_curve", mode, save_dir)
    plt.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close()
    return float(score), float(ci_low), float(ci_high)

def plot_precision_recall(y_true: np.ndarray, y_prob: np.ndarray, mode: str, save_dir: Path = None, title: str = None) -> tuple[float,float,float]:
    """
    Create and save the precision recall graph for the given values and predictions
    
    Carries a bootstrap band and an interval on the average precision, cut from the same
    resamples as the ROC band. The no-skill line is the outcome's PREVALENCE, which is
    where a PR curve's floor sits -- unlike an ROC curve, whose floor is always the
    diagonal, a PR curve is only readable against that number.
    
    :param y_true: Actual labels
    :type y_true: np.ndarray
    :param y_prob: Predicted probability labels
    :type y_prob: np.ndarray
    :param mode: llm weighting, cosine, weighting, uniform weighting
    :type mode: str
    :param save_dir: Write the figure here instead of under RESULTS_DIR
    :type save_dir: Path
    :param title: Replace the axes title, for callers whose outcome is not TRD
    :type title: str
    :return: Average precision, lower 2.5% bootstrapping CI bound, upper 97.5% bound
    :rtype: tuple[float,float,float]
    """
    score = sklearn.metrics.average_precision_score(y_true=y_true, y_score=y_prob)
    precision, recall, _ = sklearn.metrics.precision_recall_curve(y_true=y_true, y_score=y_prob)
    
    sample_indices = bootstrap_sample_indices(y_true.shape[0])
    interpolated_precision, average_precision_arr = bootstrap_precision_recall_band(y_true, y_prob, sample_indices)
    ci_low = np.nanpercentile(average_precision_arr, 2.5)
    ci_high = np.nanpercentile(average_precision_arr, 97.5)
    
    plt.figure(figsize=PANEL_FIGSIZE)
    plt.fill_between(
        RECALL_GRID,
        np.nanpercentile(interpolated_precision, 2.5, axis=0),
        np.nanpercentile(interpolated_precision, 97.5, axis=0),
        color='gray', alpha=0.2, label='95% CI',
    )
    plt.plot(recall, precision, label=f'PR Curve (Average Precision = {score:.2f}, 95% CI [{ci_low:.2f},{ci_high:.2f}])')
    prevalence = float(np.mean(y_true))
    plt.axhline(prevalence, color='green', linestyle='--', label=f'No-skill (prevalence = {prevalence:.2f})')
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(title if title is not None else "Precision Recall Curve")
    plt.legend()
    plt.tight_layout()
    save_path = curve_figure_path("pr_curves", "pr_curve", mode, save_dir)
    plt.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close()
    return float(score), float(ci_low), float(ci_high)

def _calibration_axis_limits(mean_predicted: np.ndarray, observed: np.ndarray, error_low: np.ndarray, error_high: np.ndarray, drawn: np.ndarray) -> tuple[float, float]:
    """Square axis limits covering every drawn calibration point and its interval.

    Square rather than per-axis, because the reference line is the identity: stretching
    the two axes differently tilts a perfectly calibrated curve away from 45 degrees and
    makes it look like a finding.

    Args:
        mean_predicted (np.ndarray): x of the drawn points.
        observed (np.ndarray): y of the drawn points.
        error_low (np.ndarray): Downward error distances over ALL bins, or None.
        error_high (np.ndarray): Upward error distances over ALL bins, or None.
        drawn (np.ndarray): Boolean mask of the non-empty bins, to subset the error arrays.

    Returns:
        tuple[float, float]: (low, high), padded by 5% of the span and clipped to [0, 1].
    """
    values = [mean_predicted, observed]
    if error_low is not None:
        values += [observed - error_low[drawn], observed + error_high[drawn]]
    stacked = np.concatenate(values)
    low, high = float(np.nanmin(stacked)), float(np.nanmax(stacked))
    pad = 0.05 * max(high - low, 1e-6)
    return (max(0.0, low - pad), min(1.0, high + pad))


def plot_calibration(y_true: np.ndarray, y_prob: np.ndarray, mode: str, save_dir: Path = None, title: str = None, strategy: str = 'uniform', bootstrap: bool = False) -> list[dict]:
    """
    Create and save the calibration graph for the given values and predictions
    
    With bootstrap=True each bin carries a 95% interval on its observed event fraction,
    drawn as a vertical error bar and cut from the same resamples as the ROC and PR bands.
    Bins are counted as well as plotted, because a bin holding twelve patients and a bin
    holding twelve hundred look identical on this axes and mean nothing like the same
    thing; the returned table is what carries that to a report.
    
    :param y_true: Actual labels
    :type y_true: np.ndarray
    :param y_prob: Predicted probability labels
    :type y_prob: np.ndarray
    :param mode: llm weighting, cosine, weighting, uniform weighting
    :type mode: str
    :param save_dir: Write the figure here instead of under RESULTS_DIR
    :type save_dir: Path
    :param title: Replace the axes title, for callers whose outcome is not TRD
    :type title: str
    :param strategy: 'uniform' for equal-width bins, 'quantile' for equal-count bins
    :type strategy: str
    :param bootstrap: Draw a 95% interval on each bin's observed fraction
    :type bootstrap: bool
    :return: One dict per NON-EMPTY bin, carrying its edges, n, mean predicted probability,
        observed fraction, and the interval bounds when bootstrap is on
    :rtype: list[dict]
    """
    # For each bin, calculate average probability, and calculate true probability (average positive rating)
    bin_edges = calibration_bin_edges(y_prob, strategy)
    n_bins = len(bin_edges) - 1
    bin_indices = assign_calibration_bins(y_prob, bin_edges)
    prob_pred_per_bin, prob_true_per_bin, counts = calibration_points(y_true, y_prob, bin_indices, n_bins)
    
    error_low = error_high = None
    if bootstrap:
        observed = bootstrap_calibration_band(y_true, y_prob, bootstrap_sample_indices(y_true.shape[0]), bin_edges)
        # A bin can be empty in some draws; nanpercentile keeps the bin rather than
        # dropping the whole column because a handful of draws missed it.
        with np.errstate(invalid='ignore'):
            q_low = np.nanpercentile(observed, 2.5, axis=0)
            q_high = np.nanpercentile(observed, 97.5, axis=0)
        # errorbar wants DISTANCES from the point, not absolute bounds, and it will not
        # accept a negative one -- which rounding can produce when a bin is degenerate.
        error_low = np.clip(prob_true_per_bin - q_low, 0.0, None)
        error_high = np.clip(q_high - prob_true_per_bin, 0.0, None)
    
    drawn = counts > 0
    plt.figure(figsize=PANEL_FIGSIZE)
    if bootstrap:
        plt.errorbar(
            prob_pred_per_bin[drawn], prob_true_per_bin[drawn],
            yerr=np.vstack([error_low[drawn], error_high[drawn]]),
            marker='o', capsize=3, color='tab:blue', ecolor='gray', label="Model (95% CI)",
        )
    else:
        plt.plot(prob_pred_per_bin[drawn], prob_true_per_bin[drawn], marker='o', label="Model")
    # Quantile bins exist because the predictions occupy part of the unit interval, so the
    # axes are cropped to the part they occupy. Spanning [0, 1] regardless is what puts ten
    # points and every interval on them into the left third of the panel, where the
    # departure from the diagonal the figure is FOR cannot be seen.
    limits = _calibration_axis_limits(prob_pred_per_bin[drawn], prob_true_per_bin[drawn], error_low, error_high, drawn) if strategy == 'quantile' else (0.0, 1.0)
    plt.plot(limits, limits) # Representing perfect calibration
    plt.xlim(limits)
    plt.ylim(limits)
    plt.xlabel("Mean Predicted Probability")
    plt.ylabel("Fraction of Positives")
    plt.title(title if title is not None else "Calibration Curve")
    plt.legend()
    plt.tight_layout()
    save_path = curve_figure_path("calibration_curves", "calibration_curve", mode, save_dir)
    plt.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close()
    
    bin_table = []
    for b in range(n_bins):
        if not counts[b]:
            continue
        row = {
            "bin_low": float(bin_edges[b]),
            "bin_high": float(bin_edges[b+1]),
            "n": int(counts[b]),
            "mean_predicted": float(prob_pred_per_bin[b]),
            "observed_fraction": float(prob_true_per_bin[b]),
        }
        if bootstrap:
            row["observed_ci_low"] = float(prob_true_per_bin[b] - error_low[b])
            row["observed_ci_high"] = float(prob_true_per_bin[b] + error_high[b])
        bin_table.append(row)
    return bin_table

def plot_decision_curve_analysis(y_true: np.ndarray, y_prob: np.ndarray, mode: str):
    """
    Plot decision curve benefits - when only assuming patients above a certain threshold are positive, what is the benefit
    
    :param y_true: Actual labels
    :type y_true: np.ndarray
    :param y_prob: Predicted probability labels
    :type y_prob: np.ndarray
    :param mode: llm weighting, cosine, weighting, uniform weighting
    :type mode: str
    """
    thresholds = np.linspace(0.01, 0.99, 100)
    TP_ASSIGN_ALL_POSITIVE = np.sum(y_true) # Count of true positives
    FP_ASSIGN_ALL_POSITIVE = np.sum(1-y_true)
    N = y_true.shape[0]
    
    def positive_all_benefit(threshold: np.ndarray) -> np.ndarray:
        """
        Helper method to return the benefit attributed with applying the given threshold/penalty classifying all observations as positive
        
        :param threshold: Penalty for false positive
        :type threshold: np.ndarray
        :return: Resulting benefit
        :rtype: np.ndarray
        """
        return TP_ASSIGN_ALL_POSITIVE/N - FP_ASSIGN_ALL_POSITIVE/N*threshold/(1-threshold)
     
    plt.plot(thresholds, np.zeros_like(thresholds), label="Threshold One (All Negative) Benefit")
    
    # Calculate benefits over all thresholds
    expanded_y_prob = y_prob[:, None] # N x 1
    assign_at_thresholds = expanded_y_prob >= thresholds # row is observation, column is threshold, boolean value is if observation is positive at that threshold
    expanded_y_true = y_true[:, None]
    TP = assign_at_thresholds & (expanded_y_true == 1) # True positive flags at each threshold over all patients - N x 100
    FP = assign_at_thresholds & (expanded_y_true == 0) # False positive flags at each threshold over all patients
    TP_OVER_THRESHOLDS = np.sum(TP, axis=0) # (100,)
    FP_OVER_THRESHOLDS = np.sum(FP, axis=0) # (100,)
    benefits_by_threshold = TP_OVER_THRESHOLDS / N - (FP_OVER_THRESHOLDS / N)*(thresholds/(1-thresholds))
    plt.plot(thresholds, benefits_by_threshold, label="Model Benefit by Threshold")
    
    benefits_assign_all_positive = positive_all_benefit(thresholds)
    plt.plot(thresholds, benefits_assign_all_positive, label="Threshold Zero (All Positive) Benefit by False Positive Penalty")
    
    plt.xlabel("Threshold / False Positive Penalty")
    plt.ylabel("Net Benefit")
    plt.title("Decision Curve Analysis")
    plt.ylim(bottom=-0.1)
    plt.legend()
    save_path = RESULTS_DIR / "decision_curves" / f"decision_curve_{mode}.png"
    os.makedirs(save_path.parent, exist_ok=True)
    plt.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close()

def plot_effective_sample_size_distribution(ess_values: np.ndarray, mode: str):
    """
    Create a histogram of the effective sample sizes observed in the predictions
    
    :param ess_values: Effective sample sizes from predictions
    :type ess_values: np.ndarray
    :param mode: llm weighting, cosine, weighting, uniform weighting
    :type mode: str
    """
    plt.hist(ess_values, bins=100, edgecolor='black')
    plt.xlabel("Effective Sample Size")
    plt.ylabel("Frequency")
    plt.title("Effective Sample Size Distribution")
    plt.axvline(x=int(os.environ['LOW_CONFIDENCE_ESS_THRESHOLD']), color='red', linestyle='--', linewidth=2, label='Low Confidence (<20)')
    plt.legend()
    save_path = RESULTS_DIR / "ess_distributions" / f"ess_distribution_{mode}.png"
    os.makedirs(save_path.parent, exist_ok=True)
    plt.savefig(str(save_path), dpi=FIGURE_DPI)
    plt.close()
    
def plot_optimal_confusion_matrix(y_true: np.ndarray, y_prob: np.ndarray, mode: str):
    """
    Create confusion matrix for the given probability estimates with the optimal threshold
    
    :param y_true: Actual labels
    :type y_true: np.ndarray
    :param y_prob: Predicted probability labels
    :type y_prob: np.ndarray
    :param mode: llm weighting, cosine, weighting, uniform weighting
    :type mode: str
    """
    false_positive_rates, true_positive_rates, thresholds = sklearn.metrics.roc_curve(y_true=y_true, y_score=y_prob)
    # Find threshold that accomplished peak model performance
    j_statistics = true_positive_rates - false_positive_rates
    threshold = thresholds[np.argmax(j_statistics)]
    # Use threshold to make predictions
    predictions = np.where(y_prob >= threshold, 1, 0)
    matrix = sklearn.metrics.confusion_matrix(y_true=y_true, y_pred=predictions)
    
    # Obtain metric on the confusion matrix
    raveled_matrix = np.ravel(matrix)
    tn, fp, fn, tp = raveled_matrix[0], raveled_matrix[1], raveled_matrix[2], raveled_matrix[3]
    sensitivity = tp / (tp + fn) # proportion of all positive samples correctly flagged
    specificity = tn / (tn + fp) # proportion of all negative samples correctly flagged
    f_score = 2 * tp / (2 * tp + fp + fn)
    positive_likelihood_ratio = sensitivity / (1 - specificity + 1e-9)
    negative_likelihood_ratio = (1 - sensitivity) / (specificity + 1e-9)
    metrics = f"\
Sensitivity: {sensitivity:.2f}\n\
Specificity: {specificity:.2f}\n\
F_Score: {f_score:.2f}\n\
Positive Likelihood Ratio: {positive_likelihood_ratio:.2f}\n\
Negative Likelihood Ratio: {negative_likelihood_ratio:.2f}\
"

    # Create the confusion matrix display with the text report beside it rather
    # than beneath it. Hanging the metrics off the bottom of the axes with
    # figtext and then saving under bbox_inches='tight' grew the canvas
    # downwards, which is what made this the tallest panel in the manuscript
    # (a taller-than-wide raster that could not share a page with its
    # companion panel). Side by side, the panel keeps PANEL_FIGSIZE.
    fig, (matrix_ax, metrics_ax) = plt.subplots(
        nrows=1, ncols=2,
        figsize=PANEL_FIGSIZE,
        gridspec_kw={"width_ratios": [2.0, 1.0]},
    )
    display = sklearn.metrics.ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=['Non-TRD', 'TRD'])
    display.plot(cmap='Blues', ax=matrix_ax, colorbar=False)
    fig.colorbar(display.im_, ax=matrix_ax)
    metrics_ax.axis('off')
    metrics_ax.text(0.0, 0.5, metrics, ha='left', va='center', transform=metrics_ax.transAxes)
    # The threshold is a bootstrapped Youden-J cut point, not an exact
    # quantity; printing its full float repr put ~16 significant figures in
    # the title and disagreed with how the manuscript quotes it.
    matrix_ax.set_title(f'Threshold: {threshold:.3f}')
    fig.tight_layout()
    save_path = RESULTS_DIR / "confusion_matrices" / f"confusion_matrix_{mode}.png"
    os.makedirs(save_path.parent, exist_ok=True)
    fig.savefig(save_path, dpi=FIGURE_DPI)
    plt.close(fig)
    
def display_ablated_roc_deltas(classifier_name: str, labels: np.ndarray, probs: np.ndarray, ablated_scores: dict[str, np.ndarray], ablated_names: dict[str, str]) -> dict[str, tuple[float, float]]:
    """For the given classifier, display its base and ablated roc curves, as well as differences between the base and each ablation

    Args:
        classifier_name (str): Specifies model
        labels (np.ndarray): Actual labels
        probs (np.ndarray): Baseline predicted risk scores
        ablated_scores (dict[str, np.ndarray]): For each ablation, map to a new set of risk scores
        ablated_names (dict[str, str]): For each ablation, map to a display name for the graph

    Returns:
        dict[str, tuple[float, float]]: For each ablation, return the lower and upper 95% confidence bounds on the difference
    """
    deltas = {}
    bands = {}
    base_fp, base_tp, _ = sklearn.metrics.roc_curve(labels, probs)
    base_roc_score = sklearn.metrics.roc_auc_score(labels, probs)
    # One panel per ablation spec. This was fixed at five, which is how many
    # specs the slate happened to hold; a sixth spec indexed past the end of
    # `axes`. It is derived from the slate now, and `squeeze=False` keeps the
    # indexing below valid even for a single-spec slate.
    n_specs = len(ablated_scores)
    fig, axes = plt.subplots(nrows=1, ncols=n_specs, figsize=(5 * n_specs, 5), squeeze=False)
    axes = axes[0]
    for i, (spec, abl_probs) in enumerate(ablated_scores.items()):
        rng = np.random.default_rng(seed=[i, int(os.environ['SEED'])])
        sample_indices = rng.integers(low=0, high=labels.shape[0], size=(N_BOOTSTRAP, labels.shape[0]))
        tpr_base, auc_base = bootstrap_roc_band(labels, probs, sample_indices)
        tpr_spec, auc_spec = bootstrap_roc_band(labels, abl_probs, sample_indices)
        delta_tpr = tpr_spec - tpr_base # For each bootstrapped sample, take element-wise y-axis difference values
        delta_auc = auc_spec - auc_base # Numeric differences in ROC scores
        q_low = np.nanpercentile(delta_tpr, 2.5, axis=0)
        q_high = np.nanpercentile(delta_tpr, 97.5, axis=0)
        bands[spec] = (q_low, q_high)
        ci_low = np.nanpercentile(delta_auc, 2.5)
        ci_high = np.nanpercentile(delta_auc, 97.5)
        deltas[spec] = (ci_low, ci_high)
        
        # Now plot for this specific ablation spec
        abl_roc_score = sklearn.metrics.roc_auc_score(labels, abl_probs)
        ax = axes[i]
        abl_fp, abl_tp, _ = sklearn.metrics.roc_curve(labels, abl_probs)
        ax.plot(base_fp, base_tp, label=f'Base ROC curve (score {base_roc_score:.2f})')
        ax.plot(abl_fp, abl_tp, label=f'Ablated ROC curve (score {abl_roc_score:.2f})')
        ax.plot(FPR_GRID, FPR_GRID, linestyle='--')
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title(f"ROC Curve {ablated_names[spec]}")
        ax.legend()
        twin_axis = ax.twinx()
        twin_axis.fill_between(FPR_GRID, q_low, q_high, alpha=0.2, color='gray', label='Confidence Band')
        twin_axis.set_ylabel("Δ True Positive Rate (Ablated − Baseline)")
        twin_axis.axhline(0, linestyle='--')
        twin_axis.legend()
        
    fig.tight_layout()
    save_path = RESULTS_DIR / f"ROC_ablated_vs_baseline_{classifier_name}_EMBEDDED.png"
    os.makedirs(save_path.parent, exist_ok=True)
    plt.savefig(save_path, dpi=FIGURE_DPI)
    plt.close(fig)
    return deltas