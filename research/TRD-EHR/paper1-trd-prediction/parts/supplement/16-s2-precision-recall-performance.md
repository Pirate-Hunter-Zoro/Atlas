<!--
Section 16 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S2 Precision Recall Performance
-->

# S2 Precision Recall Performance

AUPRC complements ROC AUC by describing precision across recall levels. Its no-skill reference is the cohort's positive fraction, 0.175. Because it depends on outcome frequency, AUPRC should not be compared across populations without accounting for prevalence.

AUPRC remained modest across models (Tables S1--S2; Figure S4). The leading embedded and feature models achieved 0.302 and 0.298, respectively. These values are also summarized in Table 2.

Table S1. AUPRC of the four classifiers on each representation (held-out test set). No-skill baseline = 0.175 (the positive rate).

  **Representation**   **Classifier**        **AUPRC**
  -------------------- --------------------- -----------
  EMBEDDED             Logistic regression   0.302
  EMBEDDED             Random forest         0.270
  EMBEDDED             Gradient boosting     0.276
  EMBEDDED             XGBoost               0.278
  FEATURE              Logistic regression   0.278
  FEATURE              Random forest         0.293
  FEATURE              Gradient boosting     0.288
  FEATURE              XGBoost               0.298

Table S2. Embedded logistic-regression AUPRC by encoder (held-out test set). No-skill baseline = 0.175.

  **Encoder**          **AUPRC**
  -------------------- -----------
  bge-small-en-v1.5    0.281
  bge-en-icl           0.297
  Qwen3-Embedding-4B   0.297
  Qwen3-Embedding-8B   0.302

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png){width=5.8in}

Figure S4. Precision--recall curves for the best classifier on each representation (held-out test set; primary Qwen3-Embedding-8B encoder). (A) Embedded logistic regression; (B) feature-vector XGBoost. The no-skill AUPRC reference is 0.175, the positive rate.
