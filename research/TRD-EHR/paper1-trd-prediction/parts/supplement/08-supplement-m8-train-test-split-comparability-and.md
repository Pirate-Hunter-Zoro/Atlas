<!--
Section 8 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M8. Train/test split, comparability, and leakage safeguards
-->

# Supplement M8. Train/test split, comparability, and leakage safeguards

One stratified 80:20 train/test split was generated once and reused for all
models, representations, encoders, and ablations. The training set includes
34,063 patients (5,964 TRD-positive, 17.5%) and the test set 8,516 (1,491
TRD-positive, 17.5%). Standardized mean differences were calculated for every
predictor as the train-minus-test mean difference divided by the pooled
standard deviation. Across 100 predictor rows the largest absolute SMD is
0.036 and none reaches 0.10, and the distributions themselves are Supplement
S6. The largest SMD arises from a rare social-determinant flag present in 22
training patients and no test patient. Outcome frequency is matched by
stratification rather than by observation.

All data-dependent preprocessing occurred inside the cross-validation
pipeline. On each fold, numeric scaling parameters and categorical levels were
learned only from that fold's training rows and then applied to its validation
rows. The final pipeline was fitted on the full training set and evaluated
once on the test set.

In the retrieval analyses all test identifiers were removed from the
searchable index. Each test patient was a query anchor, but every neighbor and
neighbor outcome came from the training set, which prevents self-retrieval,
test-to-test outcome propagation, and any direct use of a test label in
prediction. Train/test comparability supports internal evaluation but does not
establish transportability, because both partitions inherit the same
case-enriched sampling frame.
