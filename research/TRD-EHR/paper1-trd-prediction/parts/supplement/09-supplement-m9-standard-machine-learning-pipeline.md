<!--
Section 9 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M9. Standard machine-learning pipeline
-->

# Supplement M9. Standard machine-learning pipeline

Four classifiers were fitted to each representation: logistic regression,
random forest, gradient boosting, and XGBoost. For FEATURE, the column
transformer standardized the numeric block, one-hot encoded categorical
variables with binary categories collapsed and unknown inference-time levels
ignored, and cast boolean indicators to integer without further
transformation. EMBEDDED entered through the numeric branch only.

Each classifier and its preprocessing transformer were wrapped in a single
scikit-learn pipeline. Hyperparameters were selected by five-fold grid search
on the training set using ROC AUC as the optimization criterion. The best
configuration was refitted on all training patients and generated held-out
probabilities. The standardizer and the one-hot encoder both estimate their
parameters from data, so fitting either outside the cross-validation loop
would let held-out rows inform their own transformation. Bundling them with
the estimator prevents this. With no imputation anywhere in the pipeline,
these are the only two fitted preprocessing steps, so the cross-validated
estimates carry no preprocessing leakage. Tuning grids are keyed by classifier
only and are identical across representations.
