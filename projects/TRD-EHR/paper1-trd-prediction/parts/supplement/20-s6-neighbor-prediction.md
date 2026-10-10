<!--
Section 20 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S6 Neighbor Prediction
-->

# S6 Neighbor Prediction

Retrieval over the embedding carried outcome information but did not reach the trained classifiers at any k. Random retrieval stayed at chance at every k: its band across draws covered 0.5 at every k from 1 to 34,063. Its best k, 32,720, reached 0.500 (2.5th--97.5th percentile across draws 0.484--0.515), and that k is noise (Table S7). At their best k, logistic-regression-weighted retrieval exceeded random by 0.125 (95% CI 0.103--0.147) and plain cosine by 0.118 (95% CI 0.096--0.140). These intervals combine bootstrap resampling of the test patients with the spread across the 1,000 random draws. AUPRC at each arm's best k was 0.272 (95% CI 0.251--0.294) for logistic-regression-weighted, 0.264 (95% CI 0.244--0.286) for plain cosine, and 0.176 (95% CI 0.165--0.188) for random retrieval, against an outcome rate of 0.175 (95% CI 0.167--0.183) (section S2). Calibration is in section S3.

Neighborhood size mattered more than the metric. Both curves rose with k up to a few hundred neighbors (manuscript Figure 4D). From k = 261 onward, logistic-regression-weighted retrieval stayed inside the interval at its best k. Plain cosine retrieval peaked at k = 757 and then drifted down, to 0.605 (95% CI 0.589--0.620) at k = 16,988, still inside the interval at its best k. Each metric at its own best k differed by 0.007 (95% CI −0.001 to 0.014). The best k was selected on test patients, so those maxima are optimistic. Using every training patient as a neighbor involves no selection and gave 0.624 (95% CI 0.607--0.639) for the logistic-regression-weighted metric and 0.608 (95% CI 0.592--0.624) for plain cosine. The sharpening exponent changed the maxima by at most 0.002.

The best retrieval result over every k and exponent was logistic-regression-weighted retrieval with $\alpha$ = 2 at k = 1,090, 0.625 (95% CI 0.610--0.640). It remained below feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and below embedded logistic regression by 0.032 (95% CI 0.022--0.043), from paired bootstrap resampling of the 8,516 test patients.

Table S7. Neighbor-prediction ROC AUC for the primary encoder by neighbor selection, similarity metric, and neighborhood size, with $\alpha$ = 1. Best k is the test-selected maximum and is optimistic. The uniform random row gives the mean across 1,000 draws and the 2.5th--97.5th percentile of the draws.

| **Retrieval** | **Similarity** | **Neighbors (k)** | **ROC AUC (95% CI)** |
| ---------- | -------------------- | ------------------ | ---------------------- |
| Nearest | Plain cosine | best, 757 | 0.618 (0.602--0.634) |
| Nearest | Logistic-regression-weighted | best, 295 | 0.625 (0.610--0.641) |
| Nearest | Plain cosine | all, 34,063 | 0.608 (0.592--0.624) |
| Nearest | Logistic-regression-weighted | all, 34,063 | 0.624 (0.607--0.639) |
| Random | Uniform | best, 32,720 | 0.500 (0.484--0.515) |

Figures S8 and S9 draw ROC curves and confusion matrices only at each arm's best k, for all 4 encoders. Panels A--C are the primary encoder's 3 arms. Panels D--I are each other encoder's 2 nearest-neighbor metrics, whose ROC AUCs at those k are reported in the manuscript (Nearest-Neighbor Retrieval Across Encoders). Random retrieval does not use the embedding, so it is drawn once, in panel C.

A Qwen3-Embedding-8B, logistic-regression-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

B Qwen3-Embedding-8B, plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

C Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_RANDOM_UNIFORM_k32720.png){width=5.8in}

D bge-small-en-v1.5, logistic-regression-weighted nearest retrieval, k = 579

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k579.png){width=5.8in}

E bge-small-en-v1.5, plain-cosine nearest retrieval, k = 1,243

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_PLAIN_COSINE_alpha1_k1243.png){width=5.8in}

F bge-en-icl, logistic-regression-weighted nearest retrieval, k = 1,519

![](../results/bge-en-icl/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k1519.png){width=5.8in}

G bge-en-icl, plain-cosine nearest retrieval, k = 413

![](../results/bge-en-icl/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_PLAIN_COSINE_alpha1_k413.png){width=5.8in}

H Qwen3-Embedding-4B, logistic-regression-weighted nearest retrieval, k = 684

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k684.png){width=5.8in}

I Qwen3-Embedding-4B, plain-cosine nearest retrieval, k = 493

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/roc_curve_NEAREST_PLAIN_COSINE_alpha1_k493.png){width=5.8in}

Figure S8. ROC curves at each arm's own test-selected best k, with $\alpha$ = 1 for nearest retrieval. A--C: the primary encoder, Qwen3-Embedding-8B, under logistic-regression-weighted (A) and plain-cosine (B) nearest retrieval and uniform random retrieval (C). D--I: logistic-regression-weighted and plain-cosine nearest retrieval for bge-small-en-v1.5 (D--E), bge-en-icl (F--G), and Qwen3-Embedding-4B (H--I), each weighted by its own embedded logistic regression. C is the draw whose AUC at that k is closest to the mean of 1,000 draws; its band, and the intervals in Figure S9C, are the bootstrap 95% CI of that one draw over test patients, not the 2.5th--97.5th percentile across draws in Table S7. Best k was chosen on the test patients, so every panel is optimistic. Shaded bands are bootstrap 95% CIs. ROC: receiver operating characteristic.

A Qwen3-Embedding-8B, logistic-regression-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

B Qwen3-Embedding-8B, plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

C Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_RANDOM_UNIFORM_k32720.png){width=5.8in}

D bge-small-en-v1.5, logistic-regression-weighted nearest retrieval, k = 579

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k579.png){width=5.8in}

E bge-small-en-v1.5, plain-cosine nearest retrieval, k = 1,243

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_PLAIN_COSINE_alpha1_k1243.png){width=5.8in}

F bge-en-icl, logistic-regression-weighted nearest retrieval, k = 1,519

![](../results/bge-en-icl/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k1519.png){width=5.8in}

G bge-en-icl, plain-cosine nearest retrieval, k = 413

![](../results/bge-en-icl/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_PLAIN_COSINE_alpha1_k413.png){width=5.8in}

H Qwen3-Embedding-4B, logistic-regression-weighted nearest retrieval, k = 684

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k684.png){width=5.8in}

I Qwen3-Embedding-4B, plain-cosine nearest retrieval, k = 493

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/confusion_matrix_NEAREST_PLAIN_COSINE_alpha1_k493.png){width=5.8in}

Figure S9. Confusion matrices for the 9 panels of Figure S8 at the same k, at test-selected Youden J thresholds, with bootstrap 95% CIs on every metric at that threshold; the panels' F score is F1. These operating points were selected and evaluated in the same patients and are descriptive.

Each encoder's logistic regression relied on a similar number of embedding dimensions for 3 of the 4 encoders. The fewest dimensions holding 90% of the absolute coefficient mass were 253 for bge-small-en-v1.5, 271 for bge-en-icl, 1,626 for Qwen3-Embedding-4B, and 236 for Qwen3-Embedding-8B. These counts describe each fitted model and carry no sampling interval. Best k did not follow them. Qwen3-Embedding-4B used the most dimensions, yet its best k, 684 and 493 for the 2 metrics, lay inside the range of the other encoders (Figure S10).

Dividing each count by the encoder's number of dimensions gives the share the model relied on: 65.9% for bge-small-en-v1.5 (253 of 384), 6.6% for bge-en-icl (271 of 4,096), 63.5% for Qwen3-Embedding-4B (1,626 of 2,560), and 5.8% for Qwen3-Embedding-8B (236 of 4,096). The share split the encoders by penalty, not by size. The grid search chose an L2 penalty for the 2 encoders near 65%, which keeps every coefficient, and an elastic-net penalty for the 2 near 6%, which sets most coefficients to zero. Best k did not follow the share either (Figure S11). The 2 encoders near 6% had both the highest and the lowest logistic-regression-weighted best k, 1,519 and 295.

These counts describe a fitted model in its own coordinates. They do not measure how many independent risk factors the records hold, and they need not match the number of neighbors that predicts best. With 4 encoders, both figures describe a relation and do not test one.

![](../results/cross_embedder_retrieval/lr_dimensions_vs_best_k.png){width=5.6in}

Figure S10. Logistic-regression dimensions against best k for the 4 encoders. The horizontal axis is the fewest embedding dimensions holding 90% of the absolute coefficient mass of each encoder's embedded logistic regression. The vertical axis is the best k of logistic-regression-weighted (filled markers) and plain cosine retrieval (open markers), chosen on the test patients and therefore optimistic. Both axes are logarithmic. In-plot labels abbreviate bge-small-en-v1.5, Qwen3-Embedding-4B, and Qwen3-Embedding-8B.

![](../results/cross_embedder_retrieval/lr_dimension_share_vs_best_k.png){width=5.6in}

Figure S11. Share of embedding dimensions against best k for the 4 encoders. The horizontal axis is the count in Figure S10 divided by the encoder's number of embedding dimensions; each label gives the count and the total. The vertical axis is as in Figure S10 and is logarithmic. The 2 encoders near 65% were fitted with an L2 penalty and the 2 near 6% with an elastic-net penalty.
