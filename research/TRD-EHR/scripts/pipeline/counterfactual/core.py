import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from dataclasses import dataclass
from joblib import Parallel, delayed, parallel_config
from sklearn.linear_model import (
    LogisticRegression,
    LinearRegression
)
from sklearn.model_selection import StratifiedKFold

from scripts.shared.utils import (
    load_trd_set,
    load_feature_matrix,
    get_AD_mappings
)
from scripts.pipeline.predictions.create_train_test_split import create_train_test_split
from scripts.pipeline.predictions.classical_ml import make_classifier
from scripts.pipeline.predictions.trd_prediction_computation import compute_metrics
from scripts.shared.plots import (
    N_BOOTSTRAP,
    bootstrap_sample_indices,
    plot_calibration,
    plot_precision_recall,
    plot_receiving_operator_characteristic,
)

PROB_FLOOR = 0.1
PROB_CEILING = 0.9
# The overlap weight at the band edges. e(1-e) is symmetric about a half, so
# e < PROB_FLOOR and e > PROB_CEILING are the SAME set of patients as
# w < TRIM_WEIGHT -- the hard trim is exactly a threshold on the weight axis, and
# the weighted estimand is that step replaced by a ramp. Derived, never typed twice.
TRIM_WEIGHT = PROB_FLOOR * (1 - PROB_FLOOR)

# Fold count for the cross-validation robustness layer. Five keeps each fold's test
# side about the size of the frozen split's (a fifth of the eligible population), so a
# per-fold estimate is comparable to the headline rather than being a different
# precision of thing.
N_CV_FOLDS = 5

# The two bootstrap schemes, named once here so the artifact keys, the figure
# filenames and the write-up all read from the same strings.
#   'estimation' -- resample the TRAINING rows only, average over the fixed test
#                   frame. Captures model-estimation uncertainty alone.
#   'total'      -- resample the training rows AND the test rows. Adds the
#                   sampling variability of the population being averaged over.
# 'estimation' is nested inside 'total'; they are not rival schemes.
SCHEME_ESTIMATION = "estimation"
SCHEME_TOTAL = "total"
BOOTSTRAP_SCHEMES = (SCHEME_ESTIMATION, SCHEME_TOTAL)


def contrast_output_dir(key: str, subdir: str = None) -> Path:
    """Return (and create) the per-contrast output directory for one pairwise contrast.

    Single source of truth for the counterfactual_pipeline on-disk layout, and the exact
    mirror of causal/core.py's helper of the same name so the two packages' outputs sit
    side by side under ARTIFACTS_DIR.

    Args:
        key (str): The contrast key (spec_dict['key']), e.g. 'bupropion_vs_snri'.
        subdir (str, optional): A per-family subfolder under the contrast dir. Defaults
            to None (the contrast root).

    Returns:
        Path: The created directory.
    """
    out = Path(os.environ['ARTIFACTS_DIR']) / 'counterfactual_pipeline' / key
    if subdir is not None:
        out = out / subdir
    os.makedirs(out, exist_ok=True)
    return out

@dataclass
class EligiblePopulations:
    ref_arm_train_matrix: pd.DataFrame
    ref_arm_train_labels: np.ndarray
    comp_arm_train_matrix: pd.DataFrame
    comp_arm_train_labels: np.ndarray
    # When scoring/testing, we don't need to break patients up by which medication arm they belong to - that will only come into play when testing the models on the patients with the same respective medication arm
    eligible_test_matrix: pd.DataFrame
    eligible_test_labels: np.ndarray
    # In the test patients, flag for each one part of the comparison arm
    test_comparison_flag: np.ndarray
    
def build_eligible_populations(spec_dict: dict) -> EligiblePopulations:
    """Break up the eligible patient population into training and testing populations and keep track of their features and TRD labels

    Args:
        spec_dict (dict): Specifies the reference and comparison arms

    Returns:
        EligiblePopulations: dataclass object containing all relevant information on the population
    """
    train_ids, test_ids = create_train_test_split()
    train_matrix, test_matrix = load_feature_matrix(train_ids), load_feature_matrix(test_ids)
    # Maps ALL patients to their respective medication arm
    mappings = get_AD_mappings()
    train_arms = train_matrix.index.map(mappings)
    train_arms = pd.Series(train_arms)
    test_arms = test_matrix.index.map(mappings)
    test_arms = pd.Series(test_arms)
    
    # Grab the reference and comparison arm markers
    ref_arm, compar_arm = spec_dict['reference_arm'], spec_dict['comparison_arm']
    
    # See which patients are in the reference/comparator arms
    train_keep_mask = train_arms.isin([ref_arm, compar_arm]).to_numpy()
    compar_flag_train = (train_arms == compar_arm).astype(int).to_numpy()
    test_keep_mask = test_arms.isin([ref_arm, compar_arm]).to_numpy()
    compar_flag_test = (test_arms == compar_arm).astype(int).to_numpy()
    
    # Load TRD flags
    trd_patients = load_trd_set()
    
    # Apply filtering
    kept_train_matrix = train_matrix[train_keep_mask]
    kept_compar_flag_train = compar_flag_train[train_keep_mask]
    kept_test_matrix = test_matrix[test_keep_mask]
    kept_compar_flag_test = compar_flag_test[test_keep_mask]
    
    kept_train_y, kept_test_y = np.array([int(id in trd_patients) for id in kept_train_matrix.index]),\
        np.array([int(id in trd_patients) for id in kept_test_matrix.index])
        
    return EligiblePopulations(
        ref_arm_train_matrix=kept_train_matrix[kept_compar_flag_train == 0],
        ref_arm_train_labels=kept_train_y[kept_compar_flag_train == 0],
        comp_arm_train_matrix=kept_train_matrix[kept_compar_flag_train == 1],
        comp_arm_train_labels=kept_train_y[kept_compar_flag_train == 1],
        eligible_test_matrix=kept_test_matrix,
        eligible_test_labels=kept_test_y,
        test_comparison_flag=kept_compar_flag_test
    )
    
def score_counterfactual_risks(population: EligiblePopulations) -> pd.DataFrame:
    """Returns predicted probabilities given each treatment group over the entire population

    Args:
        population (EligiblePopulations): Broken up into treatment groups, and train/test groups

    Returns:
        pd.DataFrame: Resulting risk scores in both scenarios of each medication being taken
    """
    ref_pipeline = make_classifier(LogisticRegression(max_iter=1000))
    ref_pipeline.fit(population.ref_arm_train_matrix, population.ref_arm_train_labels)
    comp_pipeline = make_classifier(LogisticRegression(max_iter=1000))
    comp_pipeline.fit(population.comp_arm_train_matrix, population.comp_arm_train_labels)
    
    # Second column of predictions for positive probability
    ref_world_probs = ref_pipeline.predict_proba(population.eligible_test_matrix)[:, 1]
    comp_world_probs = comp_pipeline.predict_proba(population.eligible_test_matrix)[:, 1]
    
    return pd.DataFrame(
        {
            'risk_ref': ref_world_probs,
            'risk_comp': comp_world_probs,
            'trd_label': population.eligible_test_labels,
            'is_comparison': population.test_comparison_flag
        }
    ).set_index(population.eligible_test_matrix.index)
    
def grade_arm_models(risk_scores: pd.DataFrame) -> dict:
    """For the risk scores which are gradable (not counterfactuals), grade them

    Args:
        risk_scores (pd.DataFrame): Counterfactual and non-counterfactual risk scores

    Returns:
        dict: Performance metrics for non-counterfactual risk scores
    """
    is_comp_mask = risk_scores['is_comparison'] == 1
    is_ref_mask = ~is_comp_mask
    non_counterfactual_comp_scores = risk_scores['risk_comp'][is_comp_mask]
    non_counterfactual_ref_scores = risk_scores['risk_ref'][is_ref_mask]
    comp_flags = risk_scores['trd_label'][is_comp_mask]
    ref_flags = risk_scores['trd_label'][is_ref_mask]
    
    # Now that we have broken up the non-counterfactual risk scores with their flags, grade them
    comp_scores = compute_metrics(comp_flags, non_counterfactual_comp_scores)
    comp_scores['n_gradable'] = int(is_comp_mask.sum())
    comp_scores['n_events'] = int(comp_flags.sum())
    ref_scores = compute_metrics(ref_flags, non_counterfactual_ref_scores)
    ref_scores['n_gradable'] = int(is_ref_mask.sum())
    ref_scores['n_events'] = int(ref_flags.sum())
    
    # Create weighted calibration slopes and intercepts
    bin_edges = np.linspace(0.0, 1.0, 11)
    binned_predictions_comp = np.digitize(non_counterfactual_comp_scores, bin_edges) - 1
    binned_predictions_ref = np.digitize(non_counterfactual_ref_scores, bin_edges) - 1
    # Any bin assignment greater than the maximum allowed bin gets subtracted by 1 - which would only matter if a prediction were exactly 1.0 - unlikely but we'll be pedantic
    overflow_mask_comp = binned_predictions_comp >= bin_edges.shape[0]-1
    binned_predictions_comp[overflow_mask_comp] = binned_predictions_comp[overflow_mask_comp] - 1
    overflow_mask_ref = binned_predictions_ref >= bin_edges.shape[0]-1
    binned_predictions_ref[overflow_mask_ref] = binned_predictions_ref[overflow_mask_ref] - 1
    
    # In order to weight calibration by bin sizes, we need to compute the bins of risk scores and find each of their counts
    comp_bins = []
    ref_bins = []
    for b_idx in range(bin_edges.shape[0]-1):
        bin_low, bin_high = bin_edges[b_idx], bin_edges[b_idx+1]
        in_bin_comp = binned_predictions_comp == b_idx
        if in_bin_comp.any():
            mean_bin_prediction = non_counterfactual_comp_scores[in_bin_comp].mean()
            observed_fraction = comp_flags[in_bin_comp].mean()
            bin_count = int(in_bin_comp.sum())
            comp_bins.append({
                "bin_low": bin_low,
                "bin_high": bin_high,
                "n": bin_count,
                "mean_predicted": mean_bin_prediction,
                "observed_fraction": observed_fraction,
            })
            
        in_bin_ref = binned_predictions_ref == b_idx
        if in_bin_ref.any():
            mean_bin_prediction = non_counterfactual_ref_scores[in_bin_ref].mean()
            observed_fraction = ref_flags[in_bin_ref].mean()
            bin_count = int(in_bin_ref.sum())
            ref_bins.append({
                "bin_low": bin_low,
                "bin_high": bin_high,
                "n": bin_count,
                "mean_predicted": mean_bin_prediction,
                "observed_fraction": observed_fraction,
            })  
    ref_scores = ref_scores | count_weighted_slope(pd.DataFrame(ref_bins))
    ref_scores['bins'] = ref_bins
    comp_scores = comp_scores | count_weighted_slope(pd.DataFrame(comp_bins))
    comp_scores['bins'] = comp_bins
    
    return {
        'reference': ref_scores,
        'comparison': comp_scores
    }
    
def count_weighted_slope(bin_table: pd.DataFrame) -> dict:
    """Given the bins that normally go into the slope calculation for a calibration curve, return the slope and intercept when each bin is weighted by its size

    Args:
        bin_table (pd.DataFrame): Calibration bins

    Returns:
        dict: Resulting weighted calibration slope and intercept
    """
    model = LinearRegression()
    model.fit(bin_table['mean_predicted'].to_numpy().reshape(-1,1), bin_table['observed_fraction'], bin_table['n']) # Third argument is sample weight
    return {
        "weighted_cal_slope": float(model.coef_[0]),
        "weighted_cal_intercept": float(model.intercept_)
    }
    
def pooled_training_frame(population: EligiblePopulations) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Glue the two training arms back into one frame, reference arm first.

    The concatenation ORDER is load-bearing: the arm flag and the label vector are built
    to match it position for position, so anything that re-splits the pool (the propensity
    target, the bootstrap resampler) can do so by the flag alone and cannot silently
    disagree with a second, separately written concatenation. This is the construction
    that used to be inlined in attach_propensity.

    Args:
        population (EligiblePopulations): Population broken up into the two medication arms.

    Returns:
        tuple: (pooled training matrix, arm flag as 0 for reference / 1 for comparison,
            pooled TRD labels) -- all three aligned by position.
    """
    train_matrix = pd.concat([population.ref_arm_train_matrix, population.comp_arm_train_matrix])
    arm_flag = np.concatenate([
        np.zeros(len(population.ref_arm_train_labels), dtype=int),
        np.ones(len(population.comp_arm_train_labels), dtype=int)
    ])
    train_labels = np.concatenate([population.ref_arm_train_labels, population.comp_arm_train_labels])
    return train_matrix, arm_flag, train_labels


def attach_propensity(population: EligiblePopulations, risk_frame: pd.DataFrame) -> pd.DataFrame:
    """For each patient, determine their probability of being in the comparison arm, and whether that lands in a reasonable interval

    Args:
        population (EligiblePopulations): Population broken up into the two medication arms
        risk_frame (pd.DataFrame): Inputted risk scores for the given counterfactual treatment

    Returns:
        pd.DataFrame: Risk dataframe with propensity scores appended
    """
    train_matrix, arm_target, _ = pooled_training_frame(population)
    classifier_pipeline = make_classifier(LogisticRegression(max_iter=1000))
    classifier_pipeline.fit(train_matrix, arm_target)
    arm_probs = classifier_pipeline.predict_proba(population.eligible_test_matrix)[:, 1]
    risk_frame['propensity'] = arm_probs
    risk_frame['in_prob_interval'] = risk_frame['propensity'].between(PROB_FLOOR, PROB_CEILING, inclusive='neither')
    return risk_frame

def summarize_effect(risk_df: pd.DataFrame) -> dict:
    """Collapse one scored, propensity-annotated risk frame into the trim report and the two average effects.

    This is the ESTIMATOR, and nothing else: no draws, no intervals, no randomness. It is
    called once on the full-data frame for the point estimates and once per bootstrap draw
    on that draw's frame, which is what makes the interval an interval of this estimator
    rather than of a frozen vector.

    Args:
        risk_df (pd.DataFrame): Output of attach_propensity -- carries risk_ref, risk_comp,
            is_comparison, propensity and in_prob_interval.

    Returns:
        dict: The per-arm trim report, plus 'ate_trimmed' (hard-trimmed average over the
            in-band patients) and 'ate_overlap_weighted' (the same per-patient contrasts
            re-averaged under overlap weights). Either average is float('nan') when its
            denominator is degenerate -- no in-band patient, or zero total weight.
            (NOTE - effect is comparison risk score minus reference risk score, so positive
            means the first-named arm raises P(TRD))
    """
    # Per-patient contrast. Comparison minus reference, so a positive value means
    # the first-named (comparison) arm raises P(TRD).
    per_patient_effect = (risk_df['risk_comp'] - risk_df['risk_ref']).to_numpy()
    # Probability of each patient being in the comparison arm.
    propensity = risk_df['propensity'].to_numpy()
    # Flag for whether that probability landed inside the band; its negation is the trimmed set.
    in_prob_interval = risk_df['in_prob_interval'].to_numpy()
    trimmed = ~in_prob_interval
    is_comparison = (risk_df['is_comparison'] == 1).to_numpy()
    is_reference = ~is_comparison

    # Trim report, broken out by arm: trimming heavily from one arm and barely from
    # the other localizes where overlap fails, which a pooled count hides.
    ref_arm_n = int(is_reference.sum())
    comp_arm_n = int(is_comparison.sum())
    ref_trimmed_count = int((is_reference & trimmed).sum())
    comp_trimmed_count = int((is_comparison & trimmed).sum())
    
    # Max weighting occurs at equal treatment probability.
    propensity_weights = propensity * (1 - propensity)
    # Both guards matter only inside the bootstrap, where a draw can land with nothing in
    # the band; on the full data they never fire. A degenerate draw becomes nan and is
    # dropped by the nanpercentile reduction rather than poisoning the interval.
    ate_trimmed = float(per_patient_effect[in_prob_interval].mean()) if in_prob_interval.any() else float("nan")
    ate_weighted = (
        float(np.average(per_patient_effect, weights=propensity_weights))
        if propensity_weights.sum() > 0 else float("nan")
    )

    trim_report = {
        "n_eligible": int(len(risk_df)),
        "reference_arm_n": ref_arm_n,
        "comparison_arm_n": comp_arm_n,
        "reference_trimmed_count": ref_trimmed_count,
        "comparison_trimmed_count": comp_trimmed_count,
        "reference_trimmed_share": float(ref_trimmed_count / ref_arm_n) if ref_arm_n else float("nan"),
        "comparison_trimmed_share": float(comp_trimmed_count / comp_arm_n) if comp_arm_n else float("nan"),
        # Observed extremes over the WHOLE column, in-band and out: how far the
        # propensity model actually reached, not where the band was drawn.
        "propensity_min": float(propensity.min()),
        "propensity_max": float(propensity.max()),
    }
    return {
        **trim_report,
        # HEADLINE: hard-trimmed average. Estimand is nameable in a sentence --
        # "patients whose propensity fell inside the band" -- and the band matches
        # the causal package's, keeping the two triangulating estimators comparable.
        "ate_trimmed": ate_trimmed,
        # SENSITIVITY: same per-patient contrasts re-averaged under overlap weights
        # (Li, Morgan & Zaslavsky 2018). Smooth analogue, no cliff at the floor.
        # NOTE the name: the local is ate_weighted but the persisted key has always
        # been ate_overlap_weighted, and nothing downstream catches a wrong string.
        "ate_overlap_weighted": ate_weighted,
    }


def in_band_effects(risk_df: pd.DataFrame) -> np.ndarray:
    """Per-patient treatment-effect contrasts for the in-band patients only.

    The same subset plot_effect_distribution draws and the same subset ate_trimmed
    averages, extracted once so the point-estimate histogram and the pooled bootstrap
    histogram cannot end up describing different populations.

    Args:
        risk_df (pd.DataFrame): Output of attach_propensity.

    Returns:
        np.ndarray: 1-D array of comparison-minus-reference contrasts, in-band rows only.
    """
    per_patient_effect = (risk_df['risk_comp'] - risk_df['risk_ref']).to_numpy()
    return per_patient_effect[risk_df['in_prob_interval'].to_numpy()]


# The label an index prescription carries when it maps to no antidepressant class at all.
# Named once here because it appears as a dictionary key in every population report and a
# reader has to be able to tell it apart from a real arm.
UNMAPPED_ARM = "unmapped"


def split_arm_census() -> pd.DataFrame:
    """One row per patient in the frozen 80/20 split: which side, which index class, TRD or not.

    The population report's denominators are SPLIT-WIDE -- every patient on each side,
    including the third arm and the patients whose index prescription maps to no class at
    all -- so they cannot be recovered from an EligiblePopulations, which has already
    dropped everyone outside the contrast's two arms. Built from the split id lists and the
    arm mapping directly rather than from the feature parquet: create_train_test_split
    reads that file's index to produce the ids in the first place, so the ids ARE the
    cohort and a second full-width read would buy nothing.

    Returns:
        pd.DataFrame: Indexed by patient_id. Columns 'split' ('train' or 'test'), 'arm' (the
            med_definitions class string, or UNMAPPED_ARM) and 'trd_label' (0/1 int).
    """
    train_ids, test_ids = create_train_test_split()
    mappings = get_AD_mappings()
    trd_patients = load_trd_set()

    census = pd.DataFrame(index=pd.Index(sorted(train_ids | test_ids), name='patient_id'))
    census['split'] = np.where(census.index.isin(test_ids), 'test', 'train')
    # A patient missing from the mapping, or carrying a med that get_med_arm could not
    # classify, lands as NaN. Both are the same thing to this report and both must be
    # counted rather than dropped, or the per-arm shares stop summing to the split.
    census['arm'] = census.index.map(mappings)
    census['arm'] = census['arm'].where(census['arm'].notna(), UNMAPPED_ARM)
    census['trd_label'] = census.index.isin(trd_patients).astype(int)
    return census


def _side_accounting(side_census: pd.DataFrame, ref_arm: str, comp_arm: str) -> dict:
    """Per-arm counts, shares and event rates for one side of the split.

    Args:
        side_census (pd.DataFrame): The rows of split_arm_census for a single split side.
        ref_arm (str): The contrast's reference (T=0) class.
        comp_arm (str): The contrast's comparison (T=1) class.

    Returns:
        dict: 'total_rows', 'contrast_rows', 'excluded_rows', and an 'arms' mapping from
            class name to its count, share of the split side, TRD events, TRD rate, and the
            'role' it plays in this contrast ('reference', 'comparison' or 'excluded').
    """
    total = int(len(side_census))
    arms = {}
    for arm_name, arm_rows in side_census.groupby('arm', observed=True):
        count = int(len(arm_rows))
        events = int(arm_rows['trd_label'].sum())
        arms[str(arm_name)] = {
            "count": count,
            "share_of_split": float(count / total) if total else float("nan"),
            "trd_events": events,
            "trd_rate": float(events / count) if count else float("nan"),
            "role": (
                "reference" if arm_name == ref_arm
                else "comparison" if arm_name == comp_arm
                else "excluded"
            ),
        }
    contrast_rows = sum(a['count'] for a in arms.values() if a['role'] != "excluded")
    return {
        "total_rows": total,
        "contrast_rows": contrast_rows,
        "excluded_rows": total - contrast_rows,
        "arms": arms,
    }


def _trim_accounting(risk_df: pd.DataFrame) -> dict:
    """Who the overlap band kept and who it removed, per arm, with the ratios either side of it.

    summarize_effect already reports the TRIMMED counts; this reports the RETAINED ones
    beside them, because nothing else in the artifacts states the analysis population and a
    reader who mistakes the trimmed count for the survivors misreads it by threefold. The
    before/after arm ratios are here for the same reason: the floor cuts the larger arm
    harder, so the trim does not merely shrink the population, it re-weights it.

    Args:
        risk_df (pd.DataFrame): Output of attach_propensity.

    Returns:
        dict: Per-arm eligible/trimmed/retained counts and shares, the in-band total, the
            observed propensity extremes, the band edges, and the reference-to-comparison
            arm ratio before and after trimming.
    """
    is_comparison = (risk_df['is_comparison'] == 1).to_numpy()
    in_band = risk_df['in_prob_interval'].to_numpy()
    propensity = risk_df['propensity'].to_numpy()

    report = {
        "band_floor": PROB_FLOOR,
        "band_ceiling": PROB_CEILING,
        "propensity_min": float(propensity.min()),
        "propensity_max": float(propensity.max()),
        "eligible_total": int(len(risk_df)),
        "in_band_total": int(in_band.sum()),
    }
    retained = {}
    for role, mask in (("reference", ~is_comparison), ("comparison", is_comparison)):
        eligible = int(mask.sum())
        kept = int((mask & in_band).sum())
        trimmed = eligible - kept
        retained[role] = kept
        report[f"{role}_eligible_count"] = eligible
        report[f"{role}_trimmed_count"] = trimmed
        report[f"{role}_trimmed_share"] = float(trimmed / eligible) if eligible else float("nan")
        report[f"{role}_retained_count"] = kept
        report[f"{role}_retained_share"] = float(kept / eligible) if eligible else float("nan")

    # Reference patients per comparison patient, before the band and after it. These differ
    # whenever the two arms are trimmed at different rates, which is the composition shift.
    before_denominator = int(is_comparison.sum())
    report["arm_ratio_before_trim"] = (
        float(int((~is_comparison).sum()) / before_denominator) if before_denominator else float("nan")
    )
    report["arm_ratio_after_trim"] = (
        float(retained["reference"] / retained["comparison"]) if retained["comparison"] else float("nan")
    )
    return report


def population_report(spec_dict: dict, census: pd.DataFrame, risk_df: pd.DataFrame) -> dict:
    """Everything about WHO this contrast was estimated on, on both sides of the split.

    Both sides are reported, not just the test side, because they answer different
    questions: the test side defines the ESTIMAND, while the train side bounds how well the
    three models can be known at all. Without it a reader cannot tell a small-arm precision
    problem from a trim problem.

    Args:
        spec_dict (dict): The pairwise contrast spec.
        census (pd.DataFrame): Output of split_arm_census.
        risk_df (pd.DataFrame): Output of attach_propensity, for the overlap-trim block.
            The propensity column is scored on TEST patients only, so the trim accounting
            has no train-side counterpart.

    Returns:
        dict: 'key', 'display_name', the two arm names, a 'train' and a 'test' accounting
            block, and an 'overlap_trim' block covering the test side.
    """
    ref_arm, comp_arm = spec_dict['reference_arm'], spec_dict['comparison_arm']
    return {
        "key": spec_dict['key'],
        "display_name": spec_dict['display_name'],
        "reference_arm": ref_arm,
        "comparison_arm": comp_arm,
        "train": _side_accounting(census[census['split'] == 'train'], ref_arm, comp_arm),
        "test": _side_accounting(census[census['split'] == 'test'], ref_arm, comp_arm),
        "overlap_trim": _trim_accounting(risk_df),
    }


def balance_frame(population: EligiblePopulations, risk_df: pd.DataFrame) -> pd.DataFrame:
    """The test-side feature matrix with arm, band membership and overlap weight attached.

    The single object the covariate-balance work reads: every covariate as the models saw
    it, plus the three columns that decide which patients each version of the balance table
    is computed over -- raw (all rows), hard-trimmed (in_prob_interval), and overlap-weighted
    (overlap_weight). Assembling it once means the three tables cannot silently disagree
    about which patient sat in which arm.

    Categorical columns arrive with their native dtype and are deliberately NOT expanded
    here. How a multi-level nominal field turns into a set of balance rows is a reporting
    decision rather than plumbing, and it belongs where the table is computed.

    Args:
        population (EligiblePopulations): The contrast's populations; only the test side is read.
        risk_df (pd.DataFrame): Output of attach_propensity, sharing the test matrix's index.

    Returns:
        pd.DataFrame: The eligible test matrix with 'is_comparison' (0/1 int),
            'in_prob_interval' (bool) and 'overlap_weight' (e(x)(1-e(x))) appended.
    """
    frame = population.eligible_test_matrix.copy()
    collisions = {'is_comparison', 'in_prob_interval', 'overlap_weight'} & set(frame.columns)
    if collisions:
        raise ValueError(f"feature matrix already carries balance column(s): {sorted(collisions)}")
    aligned = risk_df.loc[frame.index]
    frame['is_comparison'] = aligned['is_comparison'].to_numpy()
    frame['in_prob_interval'] = aligned['in_prob_interval'].to_numpy()
    frame['overlap_weight'] = (aligned['propensity'] * (1 - aligned['propensity'])).to_numpy()
    return frame


def resample_populations(population: EligiblePopulations, generator: np.random.Generator, resample_test: bool) -> EligiblePopulations:
    """Draw one bootstrap replicate of the eligible populations.

    Training rows are resampled POOLED ACROSS ARMS -- the two arms are glued back together
    by pooled_training_frame, one with-replacement draw is taken over the whole pool, and
    the replicate is re-split by the arm flag it carried through the draw. Arm sizes
    therefore wobble from draw to draw, which is the intended behaviour: the split between
    arms is itself a feature of the sample, not a design constant.

    What is NOT resampled, ever, is the train/test split. create_train_test_split /
    test_patient_ids.txt is shared with the classical-ML and neighbour pipelines, so
    "pooled" means pooled across arms, within train and within test separately.

    Rows are selected with .iloc, positionally. Label-based .loc would expand a repeated
    patient ID combinatorially and silently change the replicate's size.

    Args:
        population (EligiblePopulations): The full eligible population to resample from.
        generator (np.random.Generator): Source of the draw. One generator per draw, seeded
            by a child of the SEED sequence, so the result does not depend on the order in
            which parallel workers happen to finish.
        resample_test (bool): False for the 'estimation' scheme -- training rows resample,
            the test frame is passed through untouched. True for the 'total' scheme -- the
            test matrix, its labels and its comparison flag are all sliced by ONE shared
            index set, so a test patient's covariates, outcome and arm stay together.

    Returns:
        EligiblePopulations: The replicate, same dataclass shape as the input.
    """
    train_matrix, arm_flag, train_labels = pooled_training_frame(population)
    n_train = len(train_matrix)
    draw = generator.integers(low=0, high=n_train, size=n_train)
    drawn_matrix = train_matrix.iloc[draw]
    drawn_labels = train_labels[draw]
    drawn_flag = arm_flag[draw]
    is_reference = drawn_flag == 0
    is_comparison = ~is_reference

    if resample_test:
        n_test = len(population.eligible_test_matrix)
        test_draw = generator.integers(low=0, high=n_test, size=n_test)
        test_matrix = population.eligible_test_matrix.iloc[test_draw]
        test_labels = population.eligible_test_labels[test_draw]
        test_flag = population.test_comparison_flag[test_draw]
    else:
        test_matrix = population.eligible_test_matrix
        test_labels = population.eligible_test_labels
        test_flag = population.test_comparison_flag

    return EligiblePopulations(
        ref_arm_train_matrix=drawn_matrix[is_reference],
        ref_arm_train_labels=drawn_labels[is_reference],
        comp_arm_train_matrix=drawn_matrix[is_comparison],
        comp_arm_train_labels=drawn_labels[is_comparison],
        eligible_test_matrix=test_matrix,
        eligible_test_labels=test_labels,
        test_comparison_flag=test_flag
    )


def estimate_once(population: EligiblePopulations) -> pd.DataFrame:
    """Run the whole estimation pipeline over one population: fit, score, propensity, trim flag.

    Three calls, in the order the design requires. Because the propensity model is refitted
    here rather than reused, in_prob_interval is recomputed too and the trimmed population
    moves from draw to draw. That is deliberate: the trimming rule is part of the estimator,
    so its variability belongs inside the band, not outside it.

    Args:
        population (EligiblePopulations): Full data or one bootstrap replicate.

    Returns:
        pd.DataFrame: The scored, propensity-annotated risk frame, ready for summarize_effect.
    """
    risk_frame = score_counterfactual_risks(population)
    return attach_propensity(population, risk_frame)


def _bootstrap_draw(population: EligiblePopulations, seed_sequence: np.random.SeedSequence, resample_test: bool) -> dict:
    """One bootstrap replicate, end to end. Returns None if the replicate was degenerate.

    A pooled draw can hand an arm zero patients, or every patient the same TRD label, and
    sklearn raises ValueError rather than fitting. bupropion_vs_snri is the contrast at risk
    -- it is the smallest, at ~2,210 eligible. A failed replicate is dropped and counted,
    never silently absorbed into the interval.

    Args:
        population (EligiblePopulations): The population to resample from.
        seed_sequence (np.random.SeedSequence): This draw's own seed, spawned from SEED.
        resample_test (bool): Whether the test rows resample too. See resample_populations.

    Returns:
        dict: 'ate_trimmed', 'ate_overlap_weighted', the two per-arm trimmed shares, and
            'effects' (this replicate's in-band per-patient contrasts). None on failure.
    """
    try:
        replicate = resample_populations(population, np.random.default_rng(seed_sequence), resample_test)
        risk_frame = estimate_once(replicate)
    except ValueError:
        return None
    summary = summarize_effect(risk_frame)
    return {
        "ate_trimmed": summary['ate_trimmed'],
        "ate_overlap_weighted": summary['ate_overlap_weighted'],
        "reference_trimmed_share": summary['reference_trimmed_share'],
        "comparison_trimmed_share": summary['comparison_trimmed_share'],
        "effects": in_band_effects(risk_frame),
    }


def _bootstrap_chunk(population: EligiblePopulations, seed_sequences: list, resample_test: bool) -> list:
    """Run a contiguous block of draws inside one worker process.

    Draws are chunked rather than dispatched one at a time for a boring but decisive reason:
    a draw takes well under a second, and shipping the whole population to a worker costs
    more than that. Dispatched per draw, the parallel version measured SLOWER than the serial
    one. One chunk per worker-ish amortises the transfer over many draws.

    Chunking cannot change any result -- each draw still uses its own seed from the spawned
    sequence, so the chunk boundaries are invisible in the output.

    Args:
        population (EligiblePopulations): The population to resample from.
        seed_sequences (list): This chunk's np.random.SeedSequence objects.
        resample_test (bool): Whether the test rows resample too.

    Returns:
        list: One _bootstrap_draw result per seed, with None for degenerate replicates.
    """
    return [_bootstrap_draw(population, seed, resample_test) for seed in seed_sequences]


def bootstrap_effect(population: EligiblePopulations, resample_test: bool, scheme: str, n_jobs: int = None) -> tuple[dict, np.ndarray]:
    """Bootstrap the WHOLE pipeline -- fit, score, propensity, trim, average -- N_BOOTSTRAP times.

    This is the change the whole refactor existed for. The previous interval resampled a
    frozen per-patient effect vector, so it measured the sampling variability of a mean and
    omitted model-estimation uncertainty entirely -- the dominant term, since both risk
    columns are themselves predictions from fitted logistic regressions. Here every draw
    refits all three models, so the band contains that term.

    Both averages come out of the SAME replicate, which is what keeps "do the hard-trimmed
    and overlap-weighted answers agree" a meaningful question rather than a comparison of
    two independent noise draws.

    The draws are independent, so they are farmed out with joblib. Each gets its own seed
    spawned from SEED, so the result is identical however many workers run and in whatever
    order they return.

    Args:
        population (EligiblePopulations): The full eligible population.
        resample_test (bool): False for the estimation scheme, True for the total scheme.
        scheme (str): SCHEME_ESTIMATION or SCHEME_TOTAL. Suffixes every returned key.
        n_jobs (int, optional): Worker count. Defaults to SLURM_CPUS_PER_TASK if set, else 1.

    Returns:
        tuple: three elements.
            [0] dict of percentile-interval keys suffixed with the scheme name, plus
                'n_bootstrap_failures_<scheme>'.
            [1] the 1-D array of every in-band per-patient contrast from every surviving
                draw, pooled -- what plot_bootstrap_effect_distribution is drawn from.
            [2] dict of field name -> 1-D array of that field's value ONE PER SURVIVING
                DRAW, for 'ate_trimmed', 'ate_overlap_weighted' and the two trimmed
                shares. The ATE entries are the sampling distribution of the average and
                are what plot_ate_sampling_distribution is drawn from. Length is
                N_BOOTSTRAP minus the failure count, not N_BOOTSTRAP.
    """
    if n_jobs is None:
        n_jobs = int(os.environ.get('SLURM_CPUS_PER_TASK', 1))
    seeds = np.random.SeedSequence(int(os.environ['SEED'])).spawn(N_BOOTSTRAP)
    chunks = np.array_split(np.arange(N_BOOTSTRAP), min(N_BOOTSTRAP, max(n_jobs, 1) * 4))
    # inner_max_num_threads=1 pins BLAS inside each worker. Without it joblib sizes the inner
    # thread pool from the worker count, the reduction order inside lbfgs changes with it, and
    # the intervals move in the last few decimal places when n_jobs changes. Pinned, the run
    # is bit-identical however many cores it is given.
    with parallel_config(backend='loky', inner_max_num_threads=1):
        chunk_results = Parallel(n_jobs=n_jobs, verbose=5)(
            delayed(_bootstrap_chunk)(population, [seeds[i] for i in chunk], resample_test)
            for chunk in chunks
        )
    draws = [draw for chunk in chunk_results for draw in chunk]

    survived = [draw for draw in draws if draw is not None]
    n_failures = len(draws) - len(survived)

    # Every bootstrapped field's per-draw values, kept as arrays rather than collapsed
    # straight to percentiles. The intervals below are percentiles OF THESE, and the arrays
    # are handed back so the SAMPLING DISTRIBUTION OF THE AVERAGE can be plotted without
    # paying for the bootstrap a second time. This is the object the CI is actually cut
    # from -- one number per draw -- and it is not the pooled per-patient array, which is
    # wider by roughly the square root of the sample size.
    draw_values = {
        field: np.array([draw[field] for draw in survived], dtype=float)
        for field in ('ate_trimmed', 'ate_overlap_weighted',
                      'reference_trimmed_share', 'comparison_trimmed_share')
    }

    def interval(field: str) -> tuple[float, float]:
        values = draw_values[field]
        if values.size == 0 or np.isnan(values).all():
            return float("nan"), float("nan")
        low, high = np.nanpercentile(values, [2.5, 97.5])
        return float(low), float(high)

    trimmed_low, trimmed_high = interval('ate_trimmed')
    weighted_low, weighted_high = interval('ate_overlap_weighted')
    ref_share_low, ref_share_high = interval('reference_trimmed_share')
    comp_share_low, comp_share_high = interval('comparison_trimmed_share')

    pooled_effects = (
        np.concatenate([draw['effects'] for draw in survived])
        if survived else np.array([], dtype=float)
    )

    return {
        f"ate_trimmed_ci_low_{scheme}": trimmed_low,
        f"ate_trimmed_ci_high_{scheme}": trimmed_high,
        f"ate_overlap_weighted_ci_low_{scheme}": weighted_low,
        f"ate_overlap_weighted_ci_high_{scheme}": weighted_high,
        # The trim shares move per draw too, so they get their own bands. The point
        # estimate stays the full-data value in the trim report; these say how firm it is.
        # The lopsided ~2x reference-arm trimming in the SSRI-referenced contrasts is one
        # of the more informative numbers in this output and is entitled to error bars.
        f"reference_trimmed_share_ci_low_{scheme}": ref_share_low,
        f"reference_trimmed_share_ci_high_{scheme}": ref_share_high,
        f"comparison_trimmed_share_ci_low_{scheme}": comp_share_low,
        f"comparison_trimmed_share_ci_high_{scheme}": comp_share_high,
        f"n_bootstrap_failures_{scheme}": int(n_failures),
    }, pooled_effects, draw_values


def plot_effect_distribution(spec_dict: dict, risk_df: pd.DataFrame, save_dir: Path) -> None:
    """Render the marginal distribution of the per-patient treatment-effect contrasts for one contrast.

    The T-learner counterpart to causal/core.py's plot_cate_distribution, and deliberately drawn the
    same way so the two triangulating estimators can be read side by side: same 1st/99th percentile
    x-clip, same dashed zero line, same dashed mean line with the value called out in a box on the
    axes. Restricted to the patients INSIDE the overlap band, because that trimmed subset is the
    headline estimand -- drawing the trimmed patients too would show a spread no reported number
    describes. Purely a side-effect plot, no returned metric.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'key', 'display_name').
        risk_df (pd.DataFrame): Risk frame carrying risk_ref, risk_comp and in_prob_interval.
        save_dir (Path): Directory to write the figure into.
    """
    effects = in_band_effects(risk_df)
    mean_effect = float(effects.mean())

    fig, ax = plt.subplots()
    ax.hist(effects, bins=50, range=tuple(np.percentile(effects, [1, 99])))
    ax.axvline(x=0, color='green', linestyle='--', label="No effect")
    ax.axvline(x=mean_effect, color='red', linestyle='--', label=f"Average effect ({mean_effect:.4f})")
    # Print the mean directly on the plot at the red line, so the ATE is readable off the
    # figure itself and not only from the legend (and unambiguous when the mean sits close
    # to the zero line). Placed at mid-height to clear the upper-right legend.
    y_top = ax.get_ylim()[1]
    ax.text(
        mean_effect, y_top * 0.55, f" ATE = {mean_effect:.4f}",
        color='red', ha='left', va='center', fontweight='bold', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='red', alpha=0.85),
    )
    ax.set_xlabel("Effect on P(TRD): comparison arm minus reference arm")
    ax.set_ylabel("Number of patients")
    ax.set_title(spec_dict['display_name'])
    ax.legend(loc='upper right')
    fig.savefig(save_dir / "effect_histogram.png")
    plt.close(fig)


def plot_propensity_by_arm(spec_dict: dict, risk_df: pd.DataFrame, save_dir: Path) -> None:
    """Render the propensity distribution with the two arms in distinguishable colours.

    The standard positivity diagnostic, and the half of the overlap screen the trim report
    cannot supply: two counts stand in for a distribution, and a count cannot show WHERE the
    mass sits relative to the band. The shaded margins are the trimmed regions, so the
    removed mass is visible rather than inferred.

    Read it for the asymmetry, which tracks how unequal the two arms are. e(x) is
    P(comparison arm | X), so the more the reference arm outnumbers the comparison arm the
    further below a half the whole distribution sits, and the further INSIDE its bulk the
    floor lands -- against the 4:1 arms of snri_vs_ssri the mass centres near 0.2 and the
    floor cuts the reference arm in quantity, while a reference-arm patient would need
    e(x) > 0.9 to be cut at all. On the near-balanced arms of bupropion_vs_snri the same
    band is close to symmetric in its effect. So a fixed band over unequal arms is lopsided
    by construction rather than by defect, and how lopsided is what this figure shows.

    Drawn on the TEST side only, because that is where the propensity column is scored.
    Purely a side-effect plot, no returned metric.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'display_name' and the two arm names).
        risk_df (pd.DataFrame): Output of attach_propensity.
        save_dir (Path): Directory to write the figure into.
    """
    propensity = risk_df['propensity'].to_numpy()
    is_comparison = (risk_df['is_comparison'] == 1).to_numpy()
    in_band = risk_df['in_prob_interval'].to_numpy()

    # Fixed bins over the whole unit interval, shared by both arms: a shared grid is what
    # makes the two histograms comparable bar for bar, and the full [0, 1] range keeps the
    # band edges in their true position instead of rescaling to the observed support.
    bins = np.linspace(0.0, 1.0, 51)

    fig, ax = plt.subplots()
    ax.axvspan(0.0, PROB_FLOOR, color='grey', alpha=0.12,
               label=f"Trimmed (outside {PROB_FLOOR:g}-{PROB_CEILING:g})")
    ax.axvspan(PROB_CEILING, 1.0, color='grey', alpha=0.12)
    for mask, colour, role in ((~is_comparison, 'tab:blue', 'reference'),
                               (is_comparison, 'tab:orange', 'comparison')):
        arm_n = int(mask.sum())
        trimmed_share = float((mask & ~in_band).sum() / arm_n) if arm_n else float("nan")
        ax.hist(
            propensity[mask], bins=bins, color=colour, alpha=0.55,
            label=f"{spec_dict[f'{role}_arm']} ({role}, n={arm_n}, {trimmed_share:.1%} trimmed)",
        )
    ax.axvline(PROB_FLOOR, color='black', linestyle='--', linewidth=1.2)
    ax.axvline(PROB_CEILING, color='black', linestyle='--', linewidth=1.2)
    ax.set_xlabel("Propensity e(x) = P(comparison arm | X)")
    ax.set_ylabel("Number of patients")
    ax.set_title(f"{spec_dict['display_name']} -- propensity by arm (test set)")
    ax.legend(loc='upper right')
    fig.savefig(save_dir / "propensity_by_arm.png")
    plt.close(fig)


def plot_bootstrap_effect_distribution(spec_dict: dict, pooled_effects: np.ndarray, ate: float, scheme: str, save_dir: Path) -> None:
    """Render the per-patient treatment-effect distribution pooled over ALL patients and ALL bootstrap draws.

    The companion to plot_effect_distribution and deliberately drawn the same way, but from a
    different object. That figure shows one number per patient, computed once from models fitted
    on all the data: it is the spread of the estimate. This one pools every in-band patient from
    every surviving replicate, so each patient contributes many contrasts -- one per draw that
    kept them -- and the extra width over the point-estimate histogram is exactly the
    model-estimation uncertainty the old frozen-vector bootstrap could not see.

    Read the two side by side: same centre, wider tails here. If the tails were NOT wider, the
    refit inside the bootstrap did not take.

    The dashed red line is the full-data point estimate, not the pooled mean, so the figure is
    annotated with the number that gets reported. The shaded band is the central 95% of the
    pooled contrasts -- a spread over patients-and-draws, NOT the confidence interval of the
    average, which is narrower by roughly the square root of the sample size and lives in
    effect_results.json.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'key', 'display_name').
        pooled_effects (np.ndarray): Second element of bootstrap_effect's return.
        ate (float): The full-data point estimate (ate_trimmed) for the reference line.
        scheme (str): SCHEME_ESTIMATION or SCHEME_TOTAL; names the file and titles the plot.
        save_dir (Path): Directory to write the figure into.
    """
    if pooled_effects.size == 0:
        # Every replicate failed. Nothing to draw, and a blank axes would be worse than no file.
        return

    low, high = np.percentile(pooled_effects, [2.5, 97.5])
    fig, ax = plt.subplots()
    ax.hist(pooled_effects, bins=100, range=tuple(np.percentile(pooled_effects, [1, 99])))
    ax.axvspan(low, high, color='orange', alpha=0.15, label="Central 95% of pooled contrasts")
    ax.axvline(x=0, color='green', linestyle='--', label="No effect")
    ax.axvline(x=ate, color='red', linestyle='--', label=f"Point estimate ({ate:.4f})")
    y_top = ax.get_ylim()[1]
    ax.text(
        ate, y_top * 0.55, f" ATE = {ate:.4f}",
        color='red', ha='left', va='center', fontweight='bold', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='red', alpha=0.85),
    )
    ax.set_xlabel("Effect on P(TRD): comparison arm minus reference arm")
    ax.set_ylabel("Patient-draws")
    ax.set_title(f"{spec_dict['display_name']} -- pooled over {N_BOOTSTRAP} bootstrap draws ({scheme})")
    ax.legend(loc='upper right')
    fig.savefig(save_dir / f"bootstrap_effect_histogram_{scheme}.png")
    plt.close(fig)

def plot_ate_sampling_distribution(
    spec_dict: dict,
    ate_draws: np.ndarray,
    ate_point: float,
    ci_low: float,
    ci_high: float,
    scheme: str,
    estimand: str,
    save_dir: Path,
) -> None:
    """Render the SAMPLING DISTRIBUTION OF THE AVERAGE effect -- one value per bootstrap draw.

    The figure the other two histograms are not. plot_effect_distribution shows one number
    per patient from a single fit; plot_bootstrap_effect_distribution pools patients across
    draws, so its width mixes between-patient heterogeneity with estimation noise and is
    several times the width of the interval. THIS one plots the estimator itself: each bar
    counts bootstrap draws whose average effect landed in that bin, so the shaded 2.5/97.5
    span is literally the reported confidence interval rather than a lookalike.

    Read it for shape as well as width. A badly skewed or multi-modal sampling distribution
    means the percentile interval is describing something a symmetric +/- summary would
    misreport, which is exactly the thing that never shows up in a JSON key.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'key', 'display_name').
        ate_draws (np.ndarray): Third element of bootstrap_effect's return, indexed by the
            estimand -- one average per surviving draw. NaNs (degenerate draws that still
            fit) are dropped here exactly as np.nanpercentile dropped them when the
            interval was computed, so the figure and the interval see the same values.
        ate_point (float): The full-data point estimate for this estimand.
        ci_low (float): Lower reported bound, for the shaded span.
        ci_high (float): Upper reported bound.
        scheme (str): SCHEME_ESTIMATION or SCHEME_TOTAL; names the file and titles the plot.
        estimand (str): 'ate_trimmed' or 'ate_overlap_weighted'; names the file too, so the
            headline and sensitivity versions cannot overwrite each other.
        save_dir (Path): Directory to write the figure into.
    """
    values = ate_draws[~np.isnan(ate_draws)]
    if values.size == 0:
        # Every draw was degenerate. A blank axes would be worse than no file.
        return

    fig, ax = plt.subplots()
    ax.hist(values, bins=40, color='steelblue', edgecolor='white', linewidth=0.4)
    ax.axvspan(ci_low, ci_high, color='orange', alpha=0.18,
               label=f"95% CI [{ci_low:.4f}, {ci_high:.4f}]")
    ax.axvline(x=ci_low, color='darkorange', linestyle=':', linewidth=1.5)
    ax.axvline(x=ci_high, color='darkorange', linestyle=':', linewidth=1.5)
    ax.axvline(x=0, color='green', linestyle='--', label="No effect")
    ax.axvline(x=ate_point, color='red', linestyle='--',
               label=f"Point estimate ({ate_point:.4f})")

    y_top = ax.get_ylim()[1]
    ax.text(
        ate_point, y_top * 0.55, f" ATE = {ate_point:.4f}",
        color='red', ha='left', va='center', fontweight='bold', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='red', alpha=0.85),
    )
    # Whether the band clears zero is the single thing a reader looks for; say it in words
    # on the axes rather than making them squint at the green line.
    crosses = ci_low <= 0.0 <= ci_high
    ax.text(
        0.02, 0.98,
        f"n = {values.size} draws\n{'CI SPANS zero' if crosses else 'CI EXCLUDES zero'}",
        transform=ax.transAxes, ha='left', va='top', fontsize=9,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.85),
    )

    scheme_blurb = ("train rows resampled, test frame fixed" if scheme == SCHEME_ESTIMATION
                    else "train AND test rows resampled")
    ax.set_xlabel(f"Average effect on P(TRD) per bootstrap draw ({estimand})")
    ax.set_ylabel("Bootstrap draws")
    ax.set_title(f"{spec_dict['display_name']}\nsampling distribution of the ATE -- {scheme} ({scheme_blurb})",
                 fontsize=10)
    ax.legend(loc='upper right', fontsize=8)
    fig.tight_layout()
    fig.savefig(save_dir / f"ate_sampling_distribution_{estimand}_{scheme}.png", dpi=150)
    plt.close(fig)


# The scalar metrics compute_metrics returns that are worth an interval. The two
# extreme-prediction proportions it also returns are descriptions of the propensity
# column rather than measurements of fit, and the overlap report already carries them.
GRADEABLE_METRIC_KEYS = (
    'roc_score',
    'auprc',
    'brier_score',
    'weighted_calibration_error',
    'calibration_slope',
    'calibration_intercept',
)


def bootstrap_metric_intervals(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Percentile confidence intervals for every gradeable metric compute_metrics returns.

    Resamples PATIENTS and recomputes the metric, which is the right bootstrap for a
    model that is already fitted: the propensity model is trained on the TRAIN pool and
    scored on the test frame, so the uncertainty being described here is the uncertainty
    of MEASURING its performance on a test set of this size, not the uncertainty of the
    fit. That is the opposite of the effect bootstrap in this module, which refits inside
    every draw because there the estimand itself depends on the fit.

    Uses the same resamples as the curve bands in scripts/shared/plots.py, drawn from the
    same seed, so a reported interval and the band on the figure beside it cannot
    disagree.

    Args:
        y_true (np.ndarray): Binary outcome, one row per scored patient.
        y_prob (np.ndarray): Predicted probabilities, aligned with y_true.

    Returns:
        dict: metric name -> {'ci_low', 'ci_high', 'n_valid_draws'}, over the draws that
            produced a finite value. A draw that sampled one class only cannot have an
            AUC and is dropped rather than counted as zero.
    """
    sample_indices = bootstrap_sample_indices(len(y_true))
    per_draw = {key: np.full(sample_indices.shape[0], np.nan) for key in GRADEABLE_METRIC_KEYS}
    for i in range(sample_indices.shape[0]):
        rows = sample_indices[i]
        y_true_draw, y_prob_draw = y_true[rows], y_prob[rows]
        if len(np.unique(y_true_draw)) < 2:
            continue
        draw_metrics = compute_metrics(y_true_draw, y_prob_draw)
        for key in GRADEABLE_METRIC_KEYS:
            per_draw[key][i] = draw_metrics[key]
    intervals = {}
    for key, values in per_draw.items():
        finite = values[np.isfinite(values)]
        intervals[key] = {
            "ci_low": float(np.percentile(finite, 2.5)) if finite.size else float("nan"),
            "ci_high": float(np.percentile(finite, 97.5)) if finite.size else float("nan"),
            "n_valid_draws": int(finite.size),
        }
    return intervals


def grade_propensity_model(spec_dict: dict, risk_df: pd.DataFrame, save_dir: Path) -> dict:
    """Grade e(x) as what it is -- a binary classifier of which arm the patient got.

    The one honestly gradeable model in this pipeline. Both arm models predict TRD under a
    treatment half the cohort did not receive, so grade_arm_models can only score each on
    its own arm and neither counterfactual column can be checked at all. The propensity
    model has no such problem: its outcome, the arm actually prescribed, is observed for
    every patient, and it is fitted on the TRAIN pool and scored on the test frame, so
    these are held-out numbers.

    Read it for TWO different things, and do not collapse them:
      DISCRIMINATION says how strongly measured covariates determine the prescription. A
      near-0.5 AUC would mean assignment looks random given X, which is the comfortable
      case for a causal claim; a high AUC means confounding by indication has plenty of
      room, and the overlap trim is load-bearing rather than cosmetic.
      CALIBRATION says whether e(x) can be believed as a NUMBER, which is what the
      overlap band and the overlap weights both assume. A miscalibrated propensity makes
      the 0.10/0.90 edges cut somewhere other than where they claim to, and that lands in
      the reported estimand rather than in a diagnostic.
    So a POOR grade here is not a bad result and a good one is not reassurance -- they
    point in opposite directions, and the write-up has to say which.

    Binning is by QUANTILE, not equal width. e(x) is concentrated wherever the arms are
    unbalanced -- below 0.4 on the SSRI-referenced contrasts -- so equal-width bins would
    leave half of them empty and put the whole curve in three points.

    Writes roc_curve_propensity_<key>.png, pr_curve_propensity_<key>.png and
    calibration_curve_propensity_<key>.png into save_dir, all three with bootstrap 95%
    bands.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'key', 'display_name' and arms).
        risk_df (pd.DataFrame): Output of attach_propensity -- needs 'propensity' and
            'is_comparison'.
        save_dir (Path): Directory to write the three figures into.

    Returns:
        dict: Point estimates for every metric in compute_metrics, a 'ci' block from
            bootstrap_metric_intervals, the quantile calibration bin table with a 95%
            interval on each bin's observed fraction, and the grading population --
            n_scored, n_comparison and the comparison-arm prevalence the PR curve's
            no-skill line sits at.
    """
    arm_label = (risk_df['is_comparison'] == 1).to_numpy().astype(int)
    propensity = risk_df['propensity'].to_numpy()
    mode = f"propensity_{spec_dict['key']}"
    outcome_blurb = f"P(comparison arm = {spec_dict['comparison_arm']} | X)"

    metrics = compute_metrics(arm_label, propensity)
    roc_score, roc_ci_low, roc_ci_high = plot_receiving_operator_characteristic(
        y_true=arm_label, y_prob=propensity, mode=mode, save_dir=save_dir,
        title=f"{spec_dict['display_name']} -- propensity discrimination\n{outcome_blurb}",
    )
    auprc, auprc_ci_low, auprc_ci_high = plot_precision_recall(
        y_true=arm_label, y_prob=propensity, mode=mode, save_dir=save_dir,
        title=f"{spec_dict['display_name']} -- propensity precision-recall\n{outcome_blurb}",
    )
    calibration_bins = plot_calibration(
        y_true=arm_label, y_prob=propensity, mode=mode, save_dir=save_dir,
        title=f"{spec_dict['display_name']} -- propensity calibration (quantile bins)\n{outcome_blurb}",
        strategy='quantile', bootstrap=True,
    )

    # The curve functions recompute their own headline score; cross-check rather than
    # trust, because a silent disagreement here would mean the figure and the JSON are
    # describing different vectors.
    assert np.isclose(roc_score, metrics['roc_score']), "ROC score disagrees between compute_metrics and the figure"

    return {
        'key': spec_dict['key'],
        'display_name': spec_dict['display_name'],
        'outcome': outcome_blurb,
        'n_scored': int(len(risk_df)),
        'n_comparison': int(arm_label.sum()),
        'comparison_prevalence': float(arm_label.mean()),
        **metrics,
        'ci': bootstrap_metric_intervals(arm_label, propensity),
        # Kept separately from the AUPRC interval because the two curve functions return
        # the same quantity by different routes; this is the one the figure was drawn from.
        'auprc_curve_ci': {'ci_low': float(auprc_ci_low), 'ci_high': float(auprc_ci_high), 'average_precision': float(auprc)},
        'roc_curve_ci': {'ci_low': float(roc_ci_low), 'ci_high': float(roc_ci_high)},
        'calibration_bins': calibration_bins,
    }


def plot_overlap_weighted_effects(spec_dict: dict, risk_df: pd.DataFrame, save_dir: Path) -> None:
    """Render the population ate_overlap_weighted actually averages over, against the trimmed one.

    The figure the other effect histograms are not. All three of them are fed
    in_band_effects, so every one of them draws the HARD-TRIMMED population unweighted --
    and none of them shows the population behind the sensitivity estimand. The overlap
    weights e(x)(1 - e(x)) cannot be recovered from a plotted histogram after the fact,
    which is why this needs the propensity column rather than a re-bin of an existing
    figure.

    Both histograms are drawn as DENSITIES on one axes, because the weighted one has no
    patient count: its bar heights are sums of weights, and against a raw count they would
    be unreadably short. Densities put the two estimands' populations on a comparable
    vertical scale, so the thing to read off is the SHAPE difference -- where the weighting
    moves mass that the cliff at the band edge does not.

    The two vertical lines are the two reported averages. When they sit on top of each
    other the hard trim is not doing anything the smooth weighting does not, and the
    sensitivity estimand is redundant; when they separate, this figure is where the reason
    is visible. Purely a side-effect plot, no returned metric.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'display_name').
        risk_df (pd.DataFrame): Output of attach_propensity -- needs risk_ref, risk_comp,
            propensity and in_prob_interval.
        save_dir (Path): Directory to write the figure into.
    """
    per_patient_effect = (risk_df['risk_comp'] - risk_df['risk_ref']).to_numpy()
    propensity = risk_df['propensity'].to_numpy()
    in_band = risk_df['in_prob_interval'].to_numpy()
    overlap_weight = propensity * (1 - propensity)

    trimmed_effects = per_patient_effect[in_band]
    ate_trimmed = float(trimmed_effects.mean())
    ate_weighted = float(np.average(per_patient_effect, weights=overlap_weight))

    # One shared bin grid, clipped to the 1st/99th percentile of the WHOLE column exactly
    # as plot_effect_distribution clips: the weighted population includes the trimmed
    # patients, so a grid cut on the in-band rows alone would drop the very mass this
    # figure exists to show.
    bins = np.linspace(*np.percentile(per_patient_effect, [1, 99]), 51)

    fig, ax = plt.subplots()
    ax.hist(per_patient_effect, bins=bins, weights=overlap_weight, density=True,
            color='tab:purple', alpha=0.55,
            label=f"Overlap-weighted, all {len(per_patient_effect)} eligible")
    ax.hist(trimmed_effects, bins=bins, density=True,
            histtype='step', linewidth=1.8, color='black',
            label=f"Hard-trimmed, {int(in_band.sum())} in band")
    ax.axvline(x=0, color='green', linestyle='--', label="No effect")
    ax.axvline(x=ate_weighted, color='tab:purple', linestyle='--',
               label=f"Overlap-weighted ATE ({ate_weighted:.4f})")
    ax.axvline(x=ate_trimmed, color='red', linestyle=':',
               label=f"Hard-trimmed ATE ({ate_trimmed:.4f})")
    # The effective sample size of the weights, which is the number the weighted curve is
    # really worth. Kish's formula: (sum w)^2 / sum w^2, the n an unweighted mean would
    # need to match this weighted mean's variance.
    kish_ess = float(overlap_weight.sum() ** 2 / np.square(overlap_weight).sum())
    ax.text(
        0.02, 0.98,
        f"weighted ESS = {kish_ess:,.0f}\nof {len(per_patient_effect):,} eligible",
        transform=ax.transAxes, ha='left', va='top', fontsize=9,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.85),
    )
    ax.set_xlabel("Effect on P(TRD): comparison arm minus reference arm")
    ax.set_ylabel("Density")
    ax.set_title(f"{spec_dict['display_name']} -- overlap-weighted vs hard-trimmed population")
    ax.legend(loc='upper right', fontsize=9)
    fig.savefig(save_dir / "overlap_weighted_effects.png")
    plt.close(fig)


def plot_overlap_weight_distribution(spec_dict: dict, risk_df: pd.DataFrame, save_dir: Path) -> None:
    """Render the distribution of the overlap weights themselves, coloured by arm.

    The companion to plot_propensity_by_arm, on the axis the weighted estimand actually
    uses. Worth a separate figure because w = e(x)(1 - e(x)) FOLDS the propensity axis
    about a half: a patient at w = 0.02 is either an almost-certain reference patient or
    an almost-certain comparison patient, and the weight alone cannot say which. Those are
    two different ways for overlap to fail, so the arm colour is not decoration here -- it
    is the only thing that recovers the direction the weight threw away.

    The dashed line at TRIM_WEIGHT is the whole argument of the sensitivity analysis in one
    mark. Because w is symmetric about a half, the hard trim's two-sided cut on e is
    EXACTLY a one-sided cut on w, so the shaded region is the patients the headline
    estimand drops entirely and the weighted one keeps at reduced strength. The step
    against the ramp, drawn.

    Drawn on the TEST side only, where the propensity column is scored. Purely a
    side-effect plot, no returned metric.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'display_name' and the two arms).
        risk_df (pd.DataFrame): Output of attach_propensity.
        save_dir (Path): Directory to write the figure into.
    """
    propensity = risk_df['propensity'].to_numpy()
    overlap_weight = propensity * (1 - propensity)
    is_comparison = (risk_df['is_comparison'] == 1).to_numpy()
    in_band = risk_df['in_prob_interval'].to_numpy()

    # Fixed grid over the full range the weight can take: w peaks at 0.25 when the two
    # treatments are equally likely, so [0, 0.25] is the whole axis by construction and
    # rescaling to the observed support would hide how far from that peak the mass sits.
    bins = np.linspace(0.0, 0.25, 51)

    fig, ax = plt.subplots()
    ax.axvspan(0.0, TRIM_WEIGHT, color='grey', alpha=0.12,
               label=f"Dropped by the hard trim (w < {TRIM_WEIGHT:g})")
    for mask, colour, role in ((~is_comparison, 'tab:blue', 'reference'),
                               (is_comparison, 'tab:orange', 'comparison')):
        arm_n = int(mask.sum())
        mean_weight = float(overlap_weight[mask].mean()) if arm_n else float("nan")
        ax.hist(
            overlap_weight[mask], bins=bins, color=colour, alpha=0.55,
            label=f"{spec_dict[f'{role}_arm']} ({role}, n={arm_n}, mean w={mean_weight:.3f})",
        )
    ax.axvline(TRIM_WEIGHT, color='black', linestyle='--', linewidth=1.2)
    # The weighted average's own denominator, said on the axes: how many patients the
    # weighting leaves the estimate worth, against how many went into it.
    kish_ess = float(overlap_weight.sum() ** 2 / np.square(overlap_weight).sum())
    ax.text(
        0.02, 0.98,
        f"weighted ESS = {kish_ess:,.0f} of {len(overlap_weight):,}\n"
        f"hard trim keeps {int(in_band.sum()):,}",
        transform=ax.transAxes, ha='left', va='top', fontsize=9,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.85),
    )
    ax.set_xlabel("Overlap weight w = e(x)(1 - e(x)), peaking at 0.25 when the arms are equally likely")
    ax.set_ylabel("Number of patients")
    ax.set_title(f"{spec_dict['display_name']} -- overlap weights by arm (test set)")
    ax.legend(loc='upper right', fontsize=9)
    fig.savefig(save_dir / "overlap_weights_by_arm.png")
    plt.close(fig)


@dataclass
class EligiblePool:
    """Every patient eligible for one contrast, across the WHOLE cohort, loaded once.

    The frozen-split path (build_eligible_populations) reads the feature parquet once per
    side and never needs this. The cross-validation path would read it twice per fold,
    which is ten reads of the same file to produce five partitions of one population --
    so the pool is built once and every fold is a boolean mask over it.

    Attributes:
        matrix (pd.DataFrame): Feature rows for every eligible patient, index = patient id.
        comparison_flag (np.ndarray): 1 for the comparison arm, 0 for the reference arm,
            aligned with matrix by position.
        trd_labels (np.ndarray): Binary TRD outcome, aligned with matrix by position.
    """
    matrix: pd.DataFrame
    comparison_flag: np.ndarray
    trd_labels: np.ndarray


def eligible_pool(spec_dict: dict) -> EligiblePool:
    """Load every patient in either arm of one contrast, ignoring the frozen split entirely.

    The CV pool is the WHOLE eligible population, not the fifth of it that landed in the
    frozen test side. That is the point of the exercise: under the frozen split the
    estimand is whichever fifth of the cohort the partition happened to put in test, and
    five folds whose test sides tile the population replace that with an estimate every
    eligible patient contributed to exactly once.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'reference_arm', 'comparison_arm').

    Returns:
        EligiblePool: The pooled matrix, arm flag and TRD labels, aligned by position.
    """
    # get_AD_mappings spans the full SOURCE population, which is wider than the feature
    # parquet; intersecting first is what keeps load_feature_matrix's .loc from raising on
    # a patient who has an index prescription but no feature row.
    mappings = get_AD_mappings()
    cohort_ids = set(pd.read_parquet(Path(os.environ['FEATURE_DATAFRAME_PATH']), columns=[]).index)
    cohort_matrix = load_feature_matrix(set(mappings.keys()) & cohort_ids)
    arms = pd.Series(cohort_matrix.index.map(mappings))
    keep_mask = arms.isin([spec_dict['reference_arm'], spec_dict['comparison_arm']]).to_numpy()

    kept_matrix = cohort_matrix[keep_mask]
    kept_flag = (arms == spec_dict['comparison_arm']).astype(int).to_numpy()[keep_mask]
    trd_patients = load_trd_set()
    kept_labels = np.array([int(patient_id in trd_patients) for patient_id in kept_matrix.index])
    return EligiblePool(matrix=kept_matrix, comparison_flag=kept_flag, trd_labels=kept_labels)


def cv_fold_indices(pool: EligiblePool, n_splits: int = N_CV_FOLDS) -> list:
    """Row-index partitions for the CV layer, stratified on INDEX ARM AND TRD LABEL JOINTLY.

    Both matter and neither implies the other. The estimator's behaviour depends on the arm
    balance, because that is what the propensity model is predicting and what decides how
    lopsided the trim is; it also depends on the event rate, because that is what the two
    outcome models are fitted against. A fold that reproduced one and not the other would
    be a different estimation problem wearing the same name. The frozen split happens to be
    balanced on both; the folds reproduce that by design rather than inherit it by luck.

    Stratifying on the interaction rather than on two margins is what makes the guarantee
    joint: four strata, arm crossed with outcome, each spread evenly across folds.

    Args:
        pool (EligiblePool): Output of eligible_pool.
        n_splits (int, optional): Fold count. Defaults to N_CV_FOLDS.

    Returns:
        list: One (train row indices, test row indices) tuple per fold, in fold order.
            Every row appears in exactly one test side, and the test sides tile the pool.
    """
    joint_strata = pool.comparison_flag * 2 + pool.trd_labels
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(os.environ['SEED']))
    return list(splitter.split(pool.matrix, joint_strata))


def fold_populations(pool: EligiblePool, train_rows: np.ndarray, test_rows: np.ndarray) -> EligiblePopulations:
    """Assemble one fold's EligiblePopulations out of the pool and a pair of row-index arrays.

    Produces exactly the object build_eligible_populations produces for the frozen split, so
    every estimator, grader and figure downstream is the same code on a different partition.
    Nothing in this package should know whether it was handed a fold or the frozen split.

    Args:
        pool (EligiblePool): Output of eligible_pool.
        train_rows (np.ndarray): Positional indices of this fold's training rows.
        test_rows (np.ndarray): Positional indices of this fold's test rows.

    Returns:
        EligiblePopulations: Training arms split in two, test side whole with its arm flag.
    """
    train_matrix = pool.matrix.iloc[train_rows]
    train_flag = pool.comparison_flag[train_rows]
    train_labels = pool.trd_labels[train_rows]
    return EligiblePopulations(
        ref_arm_train_matrix=train_matrix[train_flag == 0],
        ref_arm_train_labels=train_labels[train_flag == 0],
        comp_arm_train_matrix=train_matrix[train_flag == 1],
        comp_arm_train_labels=train_labels[train_flag == 1],
        eligible_test_matrix=pool.matrix.iloc[test_rows],
        eligible_test_labels=pool.trd_labels[test_rows],
        test_comparison_flag=pool.comparison_flag[test_rows],
    )


# The estimands the CV layer reports across folds. Both, because the fold spread is a
# property of the averaging rule as much as of the partition, and the whole reason the
# sensitivity estimand exists is to be compared against the headline one.
CV_ESTIMANDS = ('ate_trimmed', 'ate_overlap_weighted')


def run_cv_folds(spec_dict: dict, save_dir: Path, n_splits: int = N_CV_FOLDS) -> list[dict]:
    """Estimate the contrast once per fold and persist each fold's own numbers.

    NO BOOTSTRAP IN HERE, and that is the design rather than a shortcut. Folding multiplies
    whatever it wraps by n_splits, and the bootstrap is the one expensive thing in this
    package -- 2 x N_BOOTSTRAP refits of three models. It also would not buy an interval
    anybody could report: between-fold spread measures sensitivity to the partition while
    the bootstrap measures sampling and estimation uncertainty, so pooling fold-by-draw
    averages into one percentile cut conflates two different quantities. The frozen split
    keeps the interval; the folds supply the partition-sensitivity term beside it.

    Each fold writes fold_<k>.json (its point estimates, arm grades and propensity grades)
    and fold_<k>_risks.csv (its risk frame) into save_dir. Deliberately no per-fold
    figures: five copies of every diagnostic is not five times the information, and the
    cross-fold figure is the one that answers the question folding was run to ask.

    Args:
        spec_dict (dict): The pairwise contrast spec.
        save_dir (Path): The cv/ directory for this contrast.
        n_splits (int, optional): Fold count. Defaults to N_CV_FOLDS.

    Returns:
        list[dict]: One row per fold, carrying 'fold', the summarize_effect keys, and
            'propensity_roc' / 'propensity_calibration_slope' lifted out of the fold's
            propensity grades so the cross-fold table can be read without reopening five
            files. Rows are in fold order.
    """
    pool = eligible_pool(spec_dict)
    fold_rows = []
    for fold_index, (train_rows, test_rows) in enumerate(cv_fold_indices(pool, n_splits)):
        population = fold_populations(pool, train_rows, test_rows)
        risk_df = estimate_once(population)
        point_estimates = summarize_effect(risk_df)
        # The propensity model is refitted per fold, so its grades are per fold too --
        # a fold whose e(x) went badly calibrated would make that fold's trim mean
        # something different, and that is exactly the kind of thing folding is for.
        arm_label = (risk_df['is_comparison'] == 1).to_numpy().astype(int)
        propensity_metrics = compute_metrics(arm_label, risk_df['propensity'].to_numpy())
        with open(save_dir / f"fold_{fold_index}.json", 'w') as f:
            json.dump({
                'fold': fold_index,
                'n_train': int(len(train_rows)),
                'n_test': int(len(test_rows)),
                **point_estimates,
                'arm_grades': grade_arm_models(risk_df),
                'propensity_grades': propensity_metrics,
            }, f, indent=4, default=float)
        risk_df.to_csv(save_dir / f"fold_{fold_index}_risks.csv", index_label="patient_id")
        fold_rows.append({
            'fold': fold_index,
            'n_train': int(len(train_rows)),
            'n_test': int(len(test_rows)),
            **point_estimates,
            'propensity_roc': propensity_metrics['roc_score'],
            'propensity_calibration_slope': propensity_metrics['calibration_slope'],
        })
    return fold_rows


def summarize_cv(spec_dict: dict, fold_rows: list[dict], frozen_point: dict, frozen_cis: dict) -> dict:
    """Collapse the folds into the THREE quantities, kept separate on purpose.

    They answer three different questions and fusing them would answer none:
      1. FOLD-AVERAGED POINT ESTIMATE -- the estimate every eligible patient contributed
         to exactly once, rather than the fifth of them the frozen partition happened to
         put in test. This is the robustness number.
      2. BOOTSTRAP INTERVAL -- quoted unchanged from the frozen split, which still owns it.
         It measures sampling and estimation uncertainty.
      3. BETWEEN-FOLD SPREAD -- sd, min and max across folds. It measures sensitivity to
         the partition, which is a different thing, and a reader comparing it against (2)
         is doing the comparison this layer exists to enable.
    A fold spread smaller than the interval half-width means the partition is not where
    the uncertainty lives. Larger means the frozen split's number is partly an artifact of
    which patients it tested on, and the headline should say so.

    Args:
        spec_dict (dict): The pairwise contrast spec.
        fold_rows (list[dict]): Output of run_cv_folds.
        frozen_point (dict): summarize_effect on the frozen split -- the headline estimates.
        frozen_cis (dict): The interval keys from bootstrap_effect, both schemes.

    Returns:
        dict: Per estimand, the three quantities plus the frozen point estimate and the
            signed gap between it and the fold average; and alongside them the per-fold
            propensity grades, because a fold spread driven by one badly fitted propensity
            model is a different finding from one spread evenly across folds.
    """
    summary = {
        'key': spec_dict['key'],
        'display_name': spec_dict['display_name'],
        'n_folds': len(fold_rows),
        'n_eligible_total': int(sum(row['n_test'] for row in fold_rows)),
        'estimands': {},
    }
    for estimand in CV_ESTIMANDS:
        values = np.array([row[estimand] for row in fold_rows], dtype=float)
        finite = values[np.isfinite(values)]
        fold_mean = float(finite.mean()) if finite.size else float("nan")
        summary['estimands'][estimand] = {
            'fold_estimates': [float(v) for v in values],
            # 1. the robustness point estimate
            'fold_mean': fold_mean,
            # 3. the partition-sensitivity term. ddof=1: five folds are a sample of
            # partitions, not the population of them.
            'fold_sd': float(finite.std(ddof=1)) if finite.size > 1 else float("nan"),
            'fold_min': float(finite.min()) if finite.size else float("nan"),
            'fold_max': float(finite.max()) if finite.size else float("nan"),
            # the frozen split's own numbers, quoted for the comparison
            'frozen_point': float(frozen_point[estimand]),
            'frozen_minus_fold_mean': float(frozen_point[estimand] - fold_mean),
            **{
                f"frozen_{bound}_{scheme}": float(frozen_cis[f"{estimand}_ci_{bound}_{scheme}"])
                for scheme in BOOTSTRAP_SCHEMES for bound in ('low', 'high')
            },
        }
    summary['per_fold_propensity'] = [
        {
            'fold': row['fold'],
            'n_test': row['n_test'],
            'roc_score': float(row['propensity_roc']),
            'calibration_slope': float(row['propensity_calibration_slope']),
        }
        for row in fold_rows
    ]
    return summary


def plot_cv_fold_estimates(spec_dict: dict, cv_summary: dict, estimand: str, save_dir: Path) -> None:
    """Render the per-fold estimates against the frozen split's point estimate and interval.

    The figure the three quantities are for. One marker per fold on a single axis, the
    fold average as a solid line, the frozen point estimate as a dashed one, and the
    frozen bootstrap interval as a shaded span -- so the reader's eye does the comparison
    the summary states in numbers: is the fold scatter narrow against the interval, or
    comparable to it?

    The two are NOT nested and the figure must not suggest they are. A fold marker falling
    outside the shaded span is not a significance test failing; the span is an interval for
    the frozen split's estimand and the marker is a different fold's estimand. What the
    picture licenses is a judgement about MAGNITUDE: scatter much narrower than the span
    means the partition is not where the uncertainty lives.

    Purely a side-effect plot, no returned metric.

    Args:
        spec_dict (dict): The pairwise contrast spec (its 'display_name').
        cv_summary (dict): Output of summarize_cv.
        estimand (str): Which of CV_ESTIMANDS to draw; names the file too.
        save_dir (Path): Directory to write the figure into.
    """
    block = cv_summary['estimands'][estimand]
    estimates = np.array(block['fold_estimates'], dtype=float)
    folds = np.arange(len(estimates))

    fig, ax = plt.subplots()
    # The TOTAL-scheme interval, the wider of the two, because this comparison is against
    # the whole reported uncertainty rather than its estimation-only component.
    ax.axhspan(block['frozen_low_total'], block['frozen_high_total'], color='orange', alpha=0.18,
               label=f"Frozen-split 95% CI, total scheme [{block['frozen_low_total']:.4f}, {block['frozen_high_total']:.4f}]")
    ax.axhline(0.0, color='green', linestyle='--', label="No effect")
    ax.axhline(block['frozen_point'], color='red', linestyle='--',
               label=f"Frozen-split point estimate ({block['frozen_point']:.4f})")
    ax.axhline(block['fold_mean'], color='navy', linestyle='-',
               label=f"Fold-averaged estimate ({block['fold_mean']:.4f})")
    ax.plot(folds, estimates, marker='o', linestyle='none', color='navy', markersize=9,
            label=f"Per-fold estimate (sd {block['fold_sd']:.4f})")
    ax.set_xticks(folds)
    ax.set_xticklabels([f"fold {k}" for k in folds])
    # Which of the two spreads is bigger is the actionable read, so state it rather than
    # leaving it to be measured off the axis.
    half_width = 0.5 * (block['frozen_high_total'] - block['frozen_low_total'])
    verdict = ("fold spread is SMALLER than the CI half-width:\npartition is not where the uncertainty lives"
               if block['fold_sd'] < half_width else
               "fold spread is COMPARABLE TO OR LARGER than the\nCI half-width: the frozen split's number is\npartly an artifact of its partition")
    ax.text(
        0.02, 0.02,
        f"fold sd {block['fold_sd']:.4f} vs CI half-width {half_width:.4f}\n{verdict}",
        transform=ax.transAxes, ha='left', va='bottom', fontsize=8,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.85),
    )
    ax.set_ylabel(f"Average effect on P(TRD) ({estimand})")
    ax.set_title(f"{spec_dict['display_name']} -- {N_CV_FOLDS}-fold cross-validation against the frozen split")
    ax.legend(loc='upper right', fontsize=8)
    fig.savefig(save_dir / f"cv_fold_estimates_{estimand}.png")
    plt.close(fig)
