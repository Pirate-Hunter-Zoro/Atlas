<!--
Section 9 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M8 Training and Test Split
-->

# M8 Training and Test Split

All models used the same stratified split: 34,063 training patients (5,964 positive) and 8,516 test patients (1,491 positive). Across 100 predictor rows, the largest absolute standardized mean difference was 0.036. The largest imbalance concerned a rare social-determinant flag present in 22 training patients and no test patient. Outcome frequencies matched by design. Selected distributions are in section S8.

Scaling parameters and category levels were estimated within each cross-validation training fold. The selected pipeline was then refitted on all training patients and applied to the test set; exploratory analyses subsequently reused these held-out predictions.

The retrieval index contained training patients only. Test patients served as query anchors, with no self-retrieval or test-patient labels used to predict another test patient. Internal balance does not establish transportability because both partitions share the same sampling frame.
