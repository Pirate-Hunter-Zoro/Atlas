<!--
Section 15 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S1 Embedding Dimensionality
-->

# S1 Embedding Dimensionality

Latent embedding coordinates do not have individual clinical interpretations. We therefore examined fitted sparsity, cumulative correlations, and performance after principal component reduction for Qwen3-Embedding-8B. These exploratory analyses describe the fitted representation rather than identify distinct clinical mechanisms.

## S1 1 Sparsity and cumulative built in importance

The selected logistic regression used elastic-net regularization (l1_ratio=0.25; C=0.01). It assigned nonzero coefficients to 385 of 4,096 dimensions; approximately 80% of total absolute coefficient magnitude fell in 179 dimensions and 90% in 236 (Figure S1). These are model-specific measures of coefficient concentration, not estimates of intrinsic dimensionality or independent predictive information.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_cumulative_EMBEDDED.png){width=5.8in}

Figure S1. Cumulative built-in importance across embedding dimensions, ranked within each classifier. For logistic regression, importance is absolute coefficient magnitude; tree models use native feature importance. K80 and K90 identify the numbers of coordinates accounting for 80% and 90% of that model-specific total.

## S1 2 Cumulative univariate correlation

We ranked coordinates by absolute Spearman correlation with the outcome and, separately, with each classifier's predicted risk (Figure S2). The cumulative curves were broadly distributed. A sparse coefficient vector and diffuse marginal correlations can coexist because embedding coordinates are correlated; neither identifies unique clinical factors.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png){width=5.8in}

Figure S2. Cumulative absolute univariate (Spearman) correlation. One model-agnostic baseline curve ranks dimensions by \|ρ(dim, outcome)\|; the four per-classifier curves rank by \|ρ(dim, predicted risk)\|. Cumulative fraction of total \|ρ\| mass versus rank, with K₈₀ / K₉₀ knees in the legend.

## S1 3 PCA K discrimination sweep

Each classifier was retrained on the top K principal components, with K in {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024}. Held-out ROC AUC generally improved as components were added, with model-specific plateaus and some deterioration at larger K (Figure S3). These curves do not identify a unique effective dimension, and choosing K from them would require further independent evaluation.

A Logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_logistic_regression_EMBEDDED.png){width=5.8in}

B Random forest

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_random_forest_EMBEDDED.png){width=5.8in}

Figure S3. Continued on the next page.

C Gradient boosting

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_gradient_boosting_EMBEDDED.png){width=5.8in}

D XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_xgboost_EMBEDDED.png){width=5.8in}

Figure S3. ROC AUC by retained principal components for logistic regression (A), random forest (B), gradient boosting (C), and XGBoost (D). The number of components is shown on a logarithmic scale. These are exploratory comparisons on the shared test set.
