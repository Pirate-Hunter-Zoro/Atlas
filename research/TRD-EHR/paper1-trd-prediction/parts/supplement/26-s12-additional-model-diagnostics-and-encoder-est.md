<!--
Section 26 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S12 Additional Model Diagnostics and Encoder Estimates
-->

# S12 Additional Model Diagnostics and Encoder Estimates

## S12.1 Primary ROC Curves and Descriptive Operating Points

The primary ROC curves are shown in Figure S12. At test-selected Youden J thresholds of 0.165 and 0.173, embedded logistic regression and feature-vector XGBoost had sensitivity 0.647 (95% CI 0.623--0.670) and 0.615 (95% CI 0.591--0.638) and specificity 0.583 (95% CI 0.570--0.594) and 0.606 (95% CI 0.594--0.618). Their F1 scores were 0.36 (95% CI 0.34--0.37) and 0.35 (95% CI 0.34--0.37), positive likelihood ratios 1.55 (95% CI 1.48--1.62) and 1.56 (95% CI 1.48--1.63), and negative likelihood ratios 0.61 (95% CI 0.56--0.65) and 0.64 (95% CI 0.60--0.68). They identified 964 and 917 of 1,491 positive patients, missing 527 and 574, with 2,932 and 2,768 false positives and 4,093 and 4,257 true negatives among 7,025 negative patients, respectively (Figure S13). These thresholds were chosen and evaluated in the same test patients; the estimates are optimistic descriptions and are not deployment thresholds.

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_xgboost_FEATURE.png){width=5.8in}

Figure S12. Primary ROC curves for embedded logistic regression (A) and feature-vector XGBoost (B). Shaded bands are bootstrap 95% CIs. ROC AUCs are reported in main-text Table 2.

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_xgboost_FEATURE.png){width=5.8in}

Figure S13. Confusion matrices at test-selected Youden J thresholds for embedded logistic regression (A) and feature-vector XGBoost (B). TRD refers to the treatment-switching proxy.

## S12.2 Structured Feature Importance

Positive logistic-regression coefficients included severe depression coding, suicidality, insomnia, obsessive-compulsive disorder, opioid use disorder, posttraumatic stress disorder, and anxiety. Negative coefficients included missing smoking status, hyperlipidemia, longer pre-index history, and male sex. Tree importance rankings varied and also emphasized record length, age, utilization, and psychiatric burden (Figure S14). For trees, plotted colors derive from univariate correlations and do not give the direction of the fitted model's conditional effect. None of these rankings supports causal interpretation.

A Logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_logistic_regression.png){width=5.7in}

B Random forest

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_random_forest.png){width=5.7in}

C Gradient boosting

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_gradient_boosting.png){width=5.7in}

D XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_xgboost.png){width=5.7in}

Figure S14. Structured feature importance for logistic regression (A), random forest (B), gradient boosting (C), and XGBoost (D). Logistic-regression bars show coefficient magnitude, with color giving the coefficient's sign. Tree bars show native importance; colors reflect univariate associations, not conditional model effects or causal directions.

## S12.3 Concept Permutation and Encoder Comparison

In the primary encoder, psychiatric-history permutation reduced AUC by 0.024 (95% CI 0.010--0.036) to 0.028 (95% CI 0.017--0.039) across classifiers; all paired CIs excluded zero. Medication burden reduced AUC by 0.003 (95% CI −0.004 to 0.011) to 0.027 (95% CI 0.018--0.037), with CIs excluding zero for 3 classifiers. Prior treatment reduced embedded logistic-regression AUC by 0.019 (95% CI 0.011--0.027) and the other models by 0.000 (95% CI −0.009 to 0.008) to 0.011 (95% CI 0.003--0.020), with CIs excluding zero for logistic regression and XGBoost. Among the remaining concepts, only the XGBoost contraindication contrast excluded zero (−0.005; 95% CI −0.008 to −0.001). Main-text Table 3 gives every difference with its paired CI; Figure S15 gives each model's absolute AUC.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/ablation_roc_ci_EMBEDDED.png){width=6in}

Figure S15. Absolute ROC AUC after concept permutation for each primary embedded classifier. Each panel includes the unperturbed baseline and 6 permutations. Bars are each run's bootstrap 95% CIs, rather than paired CIs for the differences. SDOH: social determinants of health.

Embedded logistic regression had the highest AUC for every encoder. Across encoders, psychiatric-history permutation reduced its AUC by 0.027 (95% CI 0.017--0.036) to 0.030 (95% CI 0.019--0.041) and medication-burden permutation by 0.022 (95% CI 0.013--0.032) to 0.034 (95% CI 0.023--0.044), with all paired CIs excluding zero. Medication burden exceeded psychiatric history in bge-en-icl (−0.034, 95% CI −0.044 to −0.023, versus −0.027, 95% CI −0.036 to −0.017); psychiatric history had the larger effect in the other 3 encoders. The ordering applies to these tested concepts and does not establish unique or causal contributions.

Table S15. Embedded logistic-regression discrimination by encoder. EPV is 5,964 positive training outcomes divided by input dimension and is descriptive for these regularized models.

  **Encoder**          **Dimensions**   **EPV**   **ROC AUC (95% CI)**
  -------------------- ---------------- --------- ----------------------
  bge-small-en-v1.5    384              15.5      0.645 (0.629--0.660)
  bge-en-icl           4,096            1.5       0.655 (0.641--0.670)
  Qwen3-Embedding-4B   2,560            2.3       0.655 (0.641--0.670)
  Qwen3-Embedding-8B   4,096            1.5       0.657 (0.643--0.672)
