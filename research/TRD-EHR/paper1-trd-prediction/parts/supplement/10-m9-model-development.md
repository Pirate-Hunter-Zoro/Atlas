<!--
Section 10 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M9 Model Development
-->

# M9 Model Development

Four classifiers were fitted to each representation: logistic regression, random forest, gradient boosting, and XGBoost. For FEATURE, the column transformer standardized the numeric block, one-hot encoded categorical variables with binary categories collapsed and unknown inference-time levels ignored, and cast boolean indicators to integer without further transformation. EMBEDDED entered through the numeric branch only.

Each classifier and its preprocessing steps formed a single scikit-learn pipeline. Five-fold grid search optimized training-set ROC AUC, after which the selected pipeline was refitted on all training patients. Scaling and category encoding were fitted within each fold. Classifier-specific tuning grids were identical across representations.
