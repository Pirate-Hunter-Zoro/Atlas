<!--
Section 20 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S6 Neighbor Prediction
-->

# S6 Neighbor Prediction

Retrieval over the embedding carried outcome information but did not reach the trained classifiers. Random retrieval stayed at chance at every k: its band across draws covered 0.5 at all 34,063. Its best k, 32,720, reached 0.500 (2.5th--97.5th percentile across draws 0.484--0.515), and that k is noise. Farthest retrieval reached 0.432 (95% CI 0.416--0.449) (Table S7). At their best k, importance-weighted retrieval exceeded random by 0.125 (95% CI 0.103--0.147) and plain cosine by 0.118 (95% CI 0.096--0.140). These intervals combine bootstrap resampling of the test patients with the spread across the 1,000 random draws. AUPRC at each arm's best k was 0.272 (95% CI 0.251--0.294) for importance-weighted, 0.264 (95% CI 0.244--0.286) for plain cosine, and 0.176 (95% CI 0.165--0.188) for random retrieval, against an outcome rate of 0.175 (section S2). Calibration is in section S3.

Neighborhood size mattered more than the metric. Both curves rose to a plateau from about 300 neighbors (manuscript Figure 4). Each metric at its own best k differed by 0.007 (95% CI −0.001 to 0.014). The best k was selected on test patients, so those maxima are optimistic. Using every training patient as a neighbor involves no selection and gave 0.624 (95% CI 0.607--0.639) for the importance-weighted metric and 0.608 (95% CI 0.592--0.624) for plain cosine. The sharpening exponent changed the maxima by at most 0.002.

The best retrieval result over every k and exponent, 0.625, remained below feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and below embedded logistic regression by 0.032 (95% CI 0.022--0.043), from paired bootstrap resampling of the 8,516 test patients.

Table S7. Neighbor-prediction ROC AUC for the primary encoder by retrieval scheme, similarity metric, and neighborhood size, with $\alpha$ = 1. Best k is the test-selected maximum and is optimistic. The uniform random row gives the mean across 1,000 draws and the 2.5th--97.5th percentile of the draws. Farthest retrieval uses the retrieval pipeline's k = 50 and $\alpha$ = 5.

| **Retrieval** | **Similarity** | **Neighbors (k)** | **ROC AUC (95% CI)** |
| ---------- | -------------------- | ------------------ | ---------------------- |
| Nearest | Plain cosine | best, 757 | 0.618 (0.602--0.634) |
| Nearest | Importance-weighted | best, 295 | 0.625 (0.610--0.641) |
| Nearest | Plain cosine | all, 34,063 | 0.608 (0.592--0.624) |
| Nearest | Importance-weighted | all, 34,063 | 0.624 (0.607--0.639) |
| Random | Uniform | best, 32,720 | 0.500 (0.484--0.515) |
| Farthest | Plain cosine | 50 | 0.432 (0.416--0.449) |

A Importance-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

B Plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

C Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_RANDOM_UNIFORM_k32720.png){width=5.8in}

Figure S8. ROC curves for importance-weighted (A) and plain-cosine (B) nearest retrieval and uniform random retrieval (C), each at its own test-selected best k, with $\alpha$ = 1 for A and B. C is the draw whose AUC at that k is closest to the mean of 1,000 draws. Shaded bands are bootstrap 95% CIs. ROC: receiver operating characteristic.

A Importance-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

B Plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

C Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_RANDOM_UNIFORM_k32720.png){width=5.8in}

Figure S9. Confusion matrices for the three arms of Figure S8 at the same k, at test-selected Youden J thresholds, with bootstrap 95% CIs on every metric at that threshold. These operating points were selected and evaluated in the same patients and are descriptive.
