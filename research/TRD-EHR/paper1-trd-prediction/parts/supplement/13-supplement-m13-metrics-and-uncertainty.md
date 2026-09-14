<!--
Section 13 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M13. Metrics and uncertainty
-->

# Supplement M13. Metrics and uncertainty

Discrimination was measured by ROC AUC. Calibration was summarized by
intercept and slope, with ideal values of 0 and 1. The extract was case-enriched, so the average predicted risk is anchored
to this cohort's own TRD frequency. Carrying the models to a population
with a different rate would require rescaling the probabilities to it.

Continuous probabilities were dichotomized at the test-set threshold
maximizing Youden's J, and sensitivity, specificity, and positive and negative
likelihood ratios were calculated from the resulting confusion matrix.
Selecting and evaluating the threshold in the same test set produces
optimistic operating characteristics. These estimates characterize the ROC
curve and are not proposed for deployment. A clinical threshold would have to
be selected entirely within development data and evaluated in a separate
temporal or external cohort.

Metric confidence intervals were estimated from 1,000 bootstrap
resamples of the test-set patients, drawn with replacement. For ablation contrasts, the same patient resample was applied to the baseline
and perturbed prediction vectors and the ROC AUC difference recomputed. The
point estimate is the full-sample difference, and the 2.5th and 97.5th
percentiles of the bootstrap distribution form the 95% confidence interval. Paired resampling preserves within-patient correlation
and avoids overstating the uncertainty of a difference.

Representation contrasts used the same paired bootstrap.
Classifier-matched comparisons held the learner constant and varied only
FEATURE versus EMBEDDED. The best-feature-versus-best-embedded contrast
compares each representation's strongest classifier, but that classifier
was identified post hoc on the test set, so the contrast is interpreted
descriptively. One resample matrix was reused across all contrasts to
keep them mutually comparable.

No equivalence or noninferiority margin was prespecified. A paired confidence
interval containing zero indicates that superiority was not established at the
precision achieved. It does not establish equivalence.
