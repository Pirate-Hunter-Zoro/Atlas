<!--
Section 14 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M13 Performance Metrics and Uncertainty
-->

# M13 Performance Metrics and Uncertainty

Discrimination was summarized by ROC AUC and AUPRC. The overall calibration summaries fit a line to binned observed and predicted probabilities. These binned slopes and intercepts are in section S3 and are not conventional individual-level logistic calibration parameters. Section S9 separately reports logistic calibration slopes and mean predicted minus observed risk. All estimates describe the enriched sample.

Sensitivity, specificity, and likelihood ratios were calculated at the test-set threshold maximizing Youden J. Selecting and evaluating a threshold in the same patients introduces optimism. These operating points are descriptive; a clinical threshold would require selection in development data and evaluation in an independent cohort.

Bootstrap resampling drew test patients with replacement. Paired contrasts applied identical resampled patient indices to both prediction vectors and recalculated their ROC AUC difference. The 2.5th and 97.5th percentiles formed the 95% CI.

Classifier-matched comparisons varied the representation while holding the learner fixed. The best-model comparison selected the leading classifier for each representation from test performance and is therefore post hoc. A common resampling matrix was used across contrasts.

No equivalence or noninferiority margin was prespecified. A paired confidence interval containing zero indicates that superiority was not established at the precision achieved; it does not establish equivalence.
