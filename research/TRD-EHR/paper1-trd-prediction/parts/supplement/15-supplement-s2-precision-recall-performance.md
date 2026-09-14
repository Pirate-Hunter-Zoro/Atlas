<!--
Section 15 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S2. Precision–recall performance
-->

# Supplement S2. Precision–recall performance

The main text reports discrimination as ROC AUC. Under the cohort's ~5:1 class
imbalance (17.5% TRD-positive), ROC AUC can flatter apparent performance
because the true-negative-dominated specificity term stays high regardless of
how the positive class is ranked. The area under the precision–recall curve
(AUPRC) is the complementary view: its no-skill baseline is the positive rate
itself (0.175), not 0.5, and it exposes the precision cost of capturing TRD
cases. We report it here rather than in the main text.

AUPRC tracked ROC AUC closely and remained modest for every model (Table S1):
at this base rate, capturing high recall on the TRD proxy necessarily forces
low precision. No clinical role is inferred from these values. The main text's
Discussion, *Implications and future directions*, records that temporal
and external validation are prerequisites
for any such claim.

***Table S1.** AUPRC of the four classifiers on each representation (held-out
test set). No-skill baseline = 0.175 (the positive rate).*

| Representation | Classifier | AUPRC |
| --- | --- | ---: |
| EMBEDDED | Logistic regression | 0.302 |
| EMBEDDED | Random forest | 0.270 |
| EMBEDDED | Gradient boosting | 0.276 |
| EMBEDDED | XGBoost | 0.278 |
| FEATURE | Logistic regression | 0.278 |
| FEATURE | Random forest | 0.293 |
| FEATURE | Gradient boosting | 0.288 |
| FEATURE | XGBoost | 0.298 |

***Table S2.** Embedded logistic-regression AUPRC by encoder (held-out test
set). No-skill baseline = 0.175.*

| Encoder | AUPRC |
| --- | ---: |
| bge-small-en-v1.5 | 0.281 |
| bge-en-icl | 0.297 |
| Qwen3-Embedding-4B | 0.297 |
| Qwen3-Embedding-8B | 0.302 |

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png){width=6in}

***Figure S3.** Precision–recall curves for the best classifier on each
representation (held-out test set; primary `Qwen3-Embedding-8B` encoder).
(A) Embedded logistic regression; (B) feature-vector XGBoost. The horizontal
reference is the no-skill baseline (0.175, the positive rate).*
