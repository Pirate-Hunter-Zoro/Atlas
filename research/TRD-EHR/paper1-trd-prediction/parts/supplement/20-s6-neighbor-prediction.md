<!--
Section 20 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S6 Neighbor Prediction
-->

# S6 Neighbor Prediction

Retrieval over the embedding carried outcome information but did not reach the trained classifiers. At k = 50 under plain cosine similarity, nearest retrieval achieved an ROC AUC of 0.594, against 0.499 for random and 0.432 for farthest retrieval (Table S7). Mean effective sample size was 50.0 for nearest and 48.9 for random retrieval, so cosine weights were close to equal within a neighborhood of 50.

Neighborhood size mattered more than the metric. Both curves rose to a plateau from about 300 neighbors (manuscript Figure 4). Each metric at its own best k differed by 0.007 (95% CI −0.001 to 0.014). The best k was selected on test patients, so those maxima are optimistic. Using every training patient as a neighbor involves no selection and gave 0.624 for the importance-weighted metric and 0.608 for plain cosine. The sharpening exponent changed the maxima by at most 0.002.

The best retrieval result over every k and exponent, 0.625, remained below feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and below embedded logistic regression by 0.032 (95% CI 0.022--0.043), from paired bootstrap resampling of the 8,516 test patients.

Table S7. Neighbor-prediction ROC AUC for the primary encoder by retrieval scheme, similarity metric, and neighborhood size. Rows at k = 50 use $\alpha$ = 5, the primary setting; rows from the sweep use $\alpha$ = 1. Best k is the test-selected maximum and is optimistic.

| **Retrieval** | **Similarity** | **Neighbors (k)** | **ROC AUC (95% CI)** |
| ---------- | -------------------- | ------------------ | ---------------------- |
| Nearest | Plain cosine | 50 (primary) | 0.594 (0.578--0.610) |
| Nearest | Importance-weighted | 50 | 0.602 (0.587--0.619) |
| Nearest | Plain cosine | best, 757 | 0.618 (0.602--0.634) |
| Nearest | Importance-weighted | best, 295 | 0.625 (0.610--0.641) |
| Nearest | Plain cosine | all, 34,063 | 0.608 (0.592--0.624) |
| Nearest | Importance-weighted | all, 34,063 | 0.624 (0.607--0.639) |
| Random | Plain cosine | 50 | 0.499 (0.483--0.515) |
| Farthest | Plain cosine | 50 | 0.432 (0.416--0.449) |

A Nearest retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_COSINE.png){width=5.8in}

B Random retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_RANDOM_COSINE.png){width=5.8in}

Figure S8. ROC curves for plain-cosine nearest (A) and random (B) retrieval at k = 50. Shaded bands are bootstrap 95% CIs. ROC: receiver operating characteristic.

A Nearest retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_NEAREST_COSINE.png){width=5.8in}

B Random retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_RANDOM_COSINE.png){width=5.8in}

Figure S9. Confusion matrices for plain-cosine nearest (A) and random (B) retrieval at k = 50, at test-selected Youden J thresholds. These operating points were selected and evaluated in the same patients and are descriptive.
