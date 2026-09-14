<!--
Section 14 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S1. Effective dimensionality of the embedded representation
-->

# Supplement S1. Effective dimensionality of the embedded representation

Individual embedding dimensions carry no clinical meaning. Per-feature
interpretability, available for the feature vector in main-text Figure 6,
therefore does not transfer to the 4,096-dimensional embedded representation. Instead we
characterize *how many* latent dimensions carry the predictive signal, using
three complementary views. All figures are for the primary
`Qwen3-Embedding-8B` encoder on the held-out test set.

## S1.1 Sparsity and cumulative built-in importance

The best logistic-regression fit used an elasticnet penalty (`l1_ratio` 0.25,
`C` 0.01) that zeroed most coefficients. Only 385 of the 4,096 dimensions carry
nonzero weight, so the signal is concentrated in a sparse subset of them. We then ranked dimensions by each fitted classifier's native importance, using
`|coef|` for logistic regression and `feature_importances_` for the tree
ensembles, and accumulated the importance mass. That confirms the
concentration. For logistic regression, 80% of the coefficient magnitude falls
in roughly 179 of the 4,096 dimensions and 90% in roughly 236 (main-text Figure
7). TRD-relevant information is therefore carried by a modest subset of
embedding dimensions rather than spread across the space.

## S1.2 Cumulative univariate correlation

An importance ranking is model-specific. As a model-agnostic check we ranked
dimensions by the absolute Spearman correlation between each dimension and the
outcome, |ρ(dim, y)|, and overlaid that baseline against per-classifier curves
ranking dimensions by |ρ(dim, risk score)| (Figure S1). Divergence between the model-agnostic baseline and a classifier's curve would
flag dimensions the classifier weights through regularization or interactions
that a univariate ranking cannot see. The model-agnostic correlation curve
remained diffuse, with many dimensions each weakly correlated with the outcome.
The elasticnet logistic-regression curve was far more concentrated, the
regularization having selected a compact predictive subset from a broadly
informative space. Only |ρ| is used, because the sign of a correlation on an unnamed latent
dimension is not interpretable.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png){width=6in}

***Figure S1.** Cumulative absolute univariate (Spearman) correlation. One
model-agnostic baseline curve ranks dimensions by |ρ(dim, outcome)|. The four
per-classifier curves rank by |ρ(dim, predicted risk)|. Cumulative fraction of
total |ρ| mass versus rank, with K₈₀ / K₉₀ knees in the legend.*

## S1.3 PCA-K discrimination sweep

To locate the geometric plateau, each classifier was retrained on the top
K ∈ {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024} principal components of the
embedding and its held-out ROC AUC plotted against K (Figure S2).
Discrimination rose steeply over the first handful of components and then
plateaued, with no single low-dimensional projection recovering the full-rank
performance. That matches the diffuse model-agnostic curve in S1.2. The
compact subset in S1.1 is what the elasticnet penalty selects out of a broadly
informative space, not a low-dimensional subspace the signal already occupies.

**(A) Logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_logistic_regression_EMBEDDED.png){width=6in}

**(B) Random forest**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_random_forest_EMBEDDED.png){width=6in}

**(C) Gradient boosting**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_gradient_boosting_EMBEDDED.png){width=6in}

**(D) XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_xgboost_EMBEDDED.png){width=6in}

***Figure S2.** ROC AUC versus number of retained principal components, one
panel per classifier: (A) logistic regression, (B) random forest,
(C) gradient boosting, (D) XGBoost. The plateau marks the effective number of
principal directions beyond which added components do not improve
discrimination.*
