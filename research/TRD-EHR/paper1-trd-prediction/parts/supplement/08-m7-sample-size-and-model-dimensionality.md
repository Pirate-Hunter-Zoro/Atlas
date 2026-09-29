<!--
Section 8 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M7 Sample Size and Model Dimensionality
-->

# M7 Sample Size and Model Dimensionality

Cohort size was determined by eligibility rather than a formal sample-size calculation. Events per variable (EPV) was calculated as 5,964 outcome-positive training patients divided by the number of encoded input columns.

FEATURE contains 92 encoded columns, giving EPV = 5,964/92 ≈ 64.8. EMBEDDED dimensionality is encoder-specific: bge-small-en-v1.5 has 384 dimensions (EPV ≈ 15.5), Qwen3-Embedding-4B has 2,560 (EPV ≈ 2.3), and bge-en-icl and Qwen3-Embedding-8B each have 4,096 (EPV ≈ 1.5). Only the smallest encoder exceeds the conventional threshold of 10.

EPV is a descriptive ratio, not a sufficient sample-size criterion for high-dimensional regularized models. The larger encoders nevertheless have many inputs relative to outcome events, reinforcing the need for independent validation. Sparsity in a fitted model does not establish stability of the selected dimensions.
