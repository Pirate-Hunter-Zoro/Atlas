"""One pairwise contrast of the counterfactual (T-learner) treatment-selection pipeline.

Mirrors scripts/pipeline/causal/run_one.py: the SLURM array index picks the contrast out of
the shared TREATMENT_REGISTRY, core.py stays a library with no main, and everything for the
contrast is written under ARTIFACTS_DIR/counterfactual_pipeline/<key>/.

Point estimates come from a single fit on the full data. The intervals come from
bootstrap_effect, which refits all three models inside every draw, and it is run TWICE --
once per scheme -- because the two are nested rather than rival:

  estimation : training rows resample, the test frame is held fixed.
  total      : training rows AND test rows resample.

Artifacts written:
  effect_results.json                        point estimates, trim report, 8 CI keys, failure counts
  model_grades.json                          gradeable (non-counterfactual) metrics per arm
  population_report.json                     who the contrast was estimated on: per-arm counts,
                                             shares and TRD rates on BOTH sides of the split,
                                             plus retained-and-trimmed counts and the arm ratio
                                             either side of the overlap band
  per_patient_risks.csv                      the full-data risk frame
  balance_frame.csv                          test-side covariates with arm, band membership and
                                             overlap weight attached; the input to the balance tables
  propensity_by_arm.png                      e(x) coloured by arm with the band edges drawn
  overlap_weights_by_arm.png                 the same patients on the weight axis w = e(1-e),
                                             where the hard trim is a single threshold
  propensity_grades.json                     e(x) graded as a binary classifier of the arm
                                             actually prescribed -- the one honestly
                                             gradeable model here -- with bootstrap 95% CIs
                                             and the quantile calibration bin table
  roc_curve_propensity_<key>.png             discrimination of e(x), bootstrap 95% band
  pr_curve_propensity_<key>.png              the same against the comparison-arm prevalence
  calibration_curve_propensity_<key>.png     quantile-binned calibration of e(x), 95% CI per bin
  effect_histogram.png                       per-patient effects, one number per patient
  overlap_weighted_effects.png               the population ate_overlap_weighted averages
                                             over, against the hard-trimmed one
  bootstrap_effect_histogram_<scheme>.png    per-patient effects pooled over every draw
  bootstrap_draws.csv                        the per-draw averages the intervals are cut from
  ate_sampling_distribution_<estimand>_<scheme>.png
                                             sampling distribution of the AVERAGE effect,
                                             with the reported 95% CI shaded

And under a cv/ subdirectory, the cross-validation robustness layer:
  fold_<k>.json                              that fold's point estimates, arm grades and
                                             propensity grades
  fold_<k>_risks.csv                         that fold's risk frame
  cv_summary.json                            the three quantities, kept separate: the
                                             fold-averaged point estimate, the frozen
                                             split's bootstrap interval, and the
                                             between-fold spread
  cv_fold_estimates_<estimand>.png           the per-fold estimates against the frozen
                                             split's point estimate and interval

THE SPLIT IS NOT REPLACED. The frozen 80/20 partition stays the headline and keeps the
interval; it is what makes this package's gradeable metrics comparable to Paper 1's
classical-ML numbers, and CV would break that comparison. The folds tile the WHOLE
eligible population and answer a different question -- how much of the headline depends
on which fifth of the cohort landed in test. Both are reported; neither is fused into the
other. No bootstrap runs inside the folds, so the layer costs five single fits rather
than five times the interval.
"""

import os
import json

import pandas as pd

from scripts.shared.treatment_registry import TREATMENT_REGISTRY
from scripts.pipeline.counterfactual.core import (
    SCHEME_ESTIMATION,
    SCHEME_TOTAL,
    build_eligible_populations,
    estimate_once,
    summarize_effect,
    grade_arm_models,
    bootstrap_effect,
    split_arm_census,
    population_report,
    balance_frame,
    grade_propensity_model,
    plot_effect_distribution,
    plot_propensity_by_arm,
    plot_overlap_weight_distribution,
    plot_overlap_weighted_effects,
    run_cv_folds,
    summarize_cv,
    plot_cv_fold_estimates,
    CV_ESTIMANDS,
    plot_bootstrap_effect_distribution,
    plot_ate_sampling_distribution,
    contrast_output_dir,
)

from dotenv import load_dotenv
load_dotenv()

task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
spec_dict = TREATMENT_REGISTRY[task_id]
save_dir = contrast_output_dir(spec_dict['key'])

population = build_eligible_populations(spec_dict)

# The full-data pass. Everything reported as a point estimate comes off this frame, so the
# numbers do not move because the bootstrap was added.
risk_df = estimate_once(population)
point_estimates = summarize_effect(risk_df)
grades = grade_arm_models(risk_df)

# Who this contrast was estimated on, and what the overlap band did to that population.
# Written BEFORE the bootstrap, which costs 2 x N_BOOTSTRAP refits: none of these three
# artifacts depends on it, and a re-run wanting only the accounting should not have to wait
# for an interval it already has.
census = split_arm_census()
with open(save_dir / "population_report.json", 'w') as f:
    json.dump(population_report(spec_dict, census, risk_df), f, indent=4)

# The object the covariate-balance tables are computed from -- persisted so the balance work
# is a read rather than a refit.
balance_frame(population, risk_df).to_csv(save_dir / "balance_frame.csv", index_label="patient_id")

plot_propensity_by_arm(spec_dict, risk_df, save_dir)
plot_overlap_weight_distribution(spec_dict, risk_df, save_dir)

# e(x) graded as the classifier it is. Also written before the bootstrap: the overlap
# screen is the reason to look at this pipeline's propensity model at all, and a re-run
# that only wants the screen should not pay for an effect interval to get it.
with open(save_dir / "propensity_grades.json", 'w') as f:
    json.dump(grade_propensity_model(spec_dict, risk_df, save_dir), f, indent=4, default=float)

# Scheme A: model-estimation uncertainty only. Scheme B: that plus the sampling variability
# of the population averaged over. B's band should contain A's.
estimation_cis, estimation_effects, estimation_draws = bootstrap_effect(
    population, resample_test=False, scheme=SCHEME_ESTIMATION
)
total_cis, total_effects, total_draws = bootstrap_effect(
    population, resample_test=True, scheme=SCHEME_TOTAL
)

results = {
    'key': spec_dict['key'],
    'display_name': spec_dict['display_name'],
    **point_estimates,
    **estimation_cis,
    **total_cis,
}

with open(save_dir / "effect_results.json", 'w') as f:
    json.dump(results, f, indent=4)
with open(save_dir / "model_grades.json", 'w') as f:
    json.dump(grades, f, indent=4, default=float)

risk_df.to_csv(save_dir / "per_patient_risks.csv", index_label="patient_id")

plot_effect_distribution(spec_dict, risk_df, save_dir)
plot_overlap_weighted_effects(spec_dict, risk_df, save_dir)
for scheme, pooled in ((SCHEME_ESTIMATION, estimation_effects), (SCHEME_TOTAL, total_effects)):
    plot_bootstrap_effect_distribution(
        spec_dict, pooled, point_estimates['ate_trimmed'], scheme, save_dir
    )

# The per-draw averages: the object the confidence interval is percentiles of. Persisted as
# well as plotted, so any later figure or re-cut of the interval costs a read rather than a
# 2 x N_BOOTSTRAP refit. One column per (field, scheme); columns may differ in length when a
# scheme loses draws to degenerate replicates, which is why this is built from a dict of
# Series rather than a 2-D array.
draw_columns = {}
for scheme, draws in ((SCHEME_ESTIMATION, estimation_draws), (SCHEME_TOTAL, total_draws)):
    for field, values in draws.items():
        draw_columns[f"{field}_{scheme}"] = pd.Series(values)
pd.DataFrame(draw_columns).to_csv(save_dir / "bootstrap_draws.csv", index_label="draw")

# Four sampling-distribution figures per contrast: the headline hard-trimmed estimand and
# the overlap-weighted sensitivity one, each under both bootstrap schemes.
for scheme, cis, draws in (
    (SCHEME_ESTIMATION, estimation_cis, estimation_draws),
    (SCHEME_TOTAL, total_cis, total_draws),
):
    for estimand in ('ate_trimmed', 'ate_overlap_weighted'):
        plot_ate_sampling_distribution(
            spec_dict,
            draws[estimand],
            point_estimates[estimand],
            cis[f"{estimand}_ci_low_{scheme}"],
            cis[f"{estimand}_ci_high_{scheme}"],
            scheme,
            estimand,
            save_dir,
        )

# The cross-validation robustness layer. Runs LAST because summarize_cv quotes the frozen
# split's interval beside the fold spread, so it needs the bootstrap to have finished; and
# because everything above it is the headline, which no fold result is allowed to move.
cv_dir = contrast_output_dir(spec_dict['key'], 'cv')
fold_rows = run_cv_folds(spec_dict, cv_dir)
cv_summary = summarize_cv(spec_dict, fold_rows, point_estimates, {**estimation_cis, **total_cis})
with open(cv_dir / "cv_summary.json", 'w') as f:
    json.dump(cv_summary, f, indent=4, default=float)
for estimand in CV_ESTIMANDS:
    plot_cv_fold_estimates(spec_dict, cv_summary, estimand, cv_dir)
