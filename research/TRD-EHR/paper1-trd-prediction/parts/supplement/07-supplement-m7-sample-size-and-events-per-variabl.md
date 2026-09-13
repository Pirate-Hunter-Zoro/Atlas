<!--
Section 7 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M7. Sample size and events per variable
-->

# Supplement M7. Sample size and events per variable

No formal a-priori sample-size calculation was performed, because cohort size
was fixed by the eligibility cascade. Model dimensionality is summarized as
events per variable (EPV), the number of TRD-positive patients in the
training set divided by the number of encoded input columns. The numerator is
5,964 events rather than the total training sample of 34,063, because what
limits how precisely a coefficient can be estimated is the size of the
minority class. The denominator is the matrix dimension actually supplied to
the estimator.

FEATURE contains 92 encoded columns, giving EPV = 5,964/92 ≈ 64.8. EMBEDDED
dimensionality is encoder-specific: `bge-small-en-v1.5` has 384 dimensions
(EPV ≈ 15.5), `Qwen3-Embedding-4B` has 2,560 (EPV ≈ 2.3), and `bge-en-icl`
and `Qwen3-Embedding-8B` each have 4,096 (EPV ≈ 1.5). Only the smallest
encoder exceeds the conventional threshold of 10 events per variable.

EPV was developed for lower-dimensional regression and is not a complete
adequacy criterion for high-dimensional regularized learners. The three
larger encoders are therefore interpreted as high-dimensional regularized
models rather than as the low-dimensional regressions for which EPV was
devised. The low ratios nevertheless emphasize overfitting risk. EPV does not
account for the discrimination ranking: `bge-small-en-v1.5` has the most
favorable ratio and is the weakest encoder.
