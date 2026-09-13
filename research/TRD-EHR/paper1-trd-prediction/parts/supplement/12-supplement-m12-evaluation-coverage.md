<!--
Section 12 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M12. Evaluation coverage
-->

# Supplement M12. Evaluation coverage

Standard machine learning, the cross-encoder comparison, and the semantic
ablation all ran on the complete 42,579-patient cohort. All three scored the
shared 8,516-patient test set, with `Qwen3-Embedding-8B` as the primary
encoder.

Retrieval used nearest and random schemes crossed with uniform and
cosine weighting, on all four encoders. The retrieval scheme dominated
the weighting strategy throughout: the two weightings were nearly
indistinguishable under both schemes, while nearest and random separated
cleanly (main text, Table 6). That is what establishes that the
nearest-versus-random ordering and the shortfall against a trained
classifier both generalize across encoders (main text, Table 7).
