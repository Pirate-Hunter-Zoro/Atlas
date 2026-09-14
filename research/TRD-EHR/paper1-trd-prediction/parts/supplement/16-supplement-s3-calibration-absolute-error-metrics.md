<!--
Section 16 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S3. Calibration absolute-error metrics
-->

# Supplement S3. Calibration absolute-error metrics

The main text reports calibration shape via the calibration slope and intercept
(main-text Table 3) and the calibration curves (main-text Figure 5). Here we report the two
absolute-error summaries: the Brier score and a weighted calibration error
(WCE), both lower-is-better (Table S3). Brier scores were uniformly near 0.137–0.140 across all eight models, dominated
by the base rate of 17.5% positive. The WCE separated the models more. Gradient
boosting on the embedded representation was lowest (0.004) and logistic
regression on the feature vector next (0.005), consistent with their near-ideal
slopes in main-text Table 3.

***Table S3.** Brier score and weighted calibration error (WCE) of the four
classifiers on each representation (held-out test set). Lower is better for
both. Calibration slope and intercept are in main-text Table 3.*

| Representation | Classifier | Brier | WCE |
| --- | --- | ---: | ---: |
| EMBEDDED | Logistic regression | 0.137 | 0.010 |
| EMBEDDED | Random forest | 0.140 | 0.006 |
| EMBEDDED | Gradient boosting | 0.139 | 0.004 |
| EMBEDDED | XGBoost | 0.139 | 0.013 |
| FEATURE | Logistic regression | 0.139 | 0.005 |
| FEATURE | Random forest | 0.139 | 0.018 |
| FEATURE | Gradient boosting | 0.138 | 0.010 |
| FEATURE | XGBoost | 0.138 | 0.012 |
