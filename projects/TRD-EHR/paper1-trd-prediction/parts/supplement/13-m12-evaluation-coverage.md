<!--
Section 13 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M12 Evaluation Coverage
-->

# M12 Evaluation Coverage

Standard classifiers, encoder comparisons, and concept permutations used the full cohort and common test split. All 4 encoders received both similarity metrics, random retrieval, and the neighborhood-size sweep under the same rules, each weighted by its own embedded logistic regression (manuscript, Nearest-Neighbor Retrieval Across Encoders; manuscript Figure 4; section S6). ROC curves and confusion matrices at best k are reported for all 4 encoders (section S6). Paired contrasts, the precision--recall and calibration panels at best k (sections S2--S3), and the subgroup analyses describe Qwen3-Embedding-8B only.
