<!--
Section 16 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S2 Precision Recall Performance
-->

# S2 Precision Recall Performance

AUPRC complements ROC AUC by describing precision across recall levels. Its no-skill reference is the cohort's positive fraction, 0.175. Because it depends on outcome frequency, AUPRC should not be compared across populations without accounting for prevalence.

AUPRC remained modest across models (Tables S1--S2; Figure S4). The leading embedded and feature models achieved 0.302 (95% CI 0.281--0.325) and 0.298 (95% CI 0.276--0.322), respectively. These values are also summarized in Table 2. At each retrieval arm's best k, AUPRC was 0.272 (95% CI 0.251--0.294) for logistic-regression-weighted, 0.264 (95% CI 0.244--0.286) for plain cosine, and 0.176 (95% CI 0.165--0.188) for random retrieval. Random retrieval therefore sat at the no-skill reference. The best k was chosen on the test patients by ROC AUC, so these values are optimistic.

Table S1. AUPRC of the four classifiers on each representation and of the 3 retrieval arms, each arm at its own test-selected best k (held-out test set), with bootstrap 95% CIs. No-skill baseline = 0.175 (the positive rate, 95% CI 0.167--0.183).

| **Representation** | **Model** | **AUPRC (95% CI)** |
| ---------------------- | ------------------------------ | ---------------------- |
| EMBEDDED | Logistic regression | 0.302 (0.281--0.325) |
| EMBEDDED | Random forest | 0.270 (0.250--0.291) |
| EMBEDDED | Gradient boosting | 0.276 (0.256--0.298) |
| EMBEDDED | XGBoost | 0.278 (0.257--0.300) |
| FEATURE | Logistic regression | 0.278 (0.256--0.300) |
| FEATURE | Random forest | 0.293 (0.271--0.315) |
| FEATURE | Gradient boosting | 0.288 (0.267--0.309) |
| FEATURE | XGBoost | 0.298 (0.276--0.322) |
| Retrieval | Logistic-regression-weighted cosine, k = 295 | 0.272 (0.251--0.294) |
| Retrieval | Plain cosine, k = 757 | 0.264 (0.244--0.286) |
| Retrieval | Random, uniform weights, k = 32,720 | 0.176 (0.165--0.188) |

Table S2. Embedded logistic-regression AUPRC by encoder (held-out test set), with bootstrap 95% CIs. No-skill baseline = 0.175.

| **Encoder** | **AUPRC (95% CI)** |
| -------------------- | ---------------------- |
| bge-small-en-v1.5 | 0.281 (0.260--0.303) |
| bge-en-icl | 0.297 (0.277--0.320) |
| Qwen3-Embedding-4B | 0.297 (0.274--0.319) |
| Qwen3-Embedding-8B | 0.302 (0.281--0.325) |

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png){width=5.8in}

C Logistic-regression-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

D Plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

E Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/pr_curve_RANDOM_UNIFORM_k32720.png){width=5.8in}

Figure S4. Precision--recall curves (held-out test set; primary Qwen3-Embedding-8B encoder). (A) Embedded logistic regression; (B) feature-vector XGBoost; (C--E) the 3 retrieval arms, each at its own test-selected best k. E is the draw of 1,000 whose ROC AUC at that k is closest to their mean. Retrieval panels print average precision, which differs from the table AUPRC in the third decimal. The no-skill reference is 0.175, the positive rate; panel legends round both to 2 decimals.
