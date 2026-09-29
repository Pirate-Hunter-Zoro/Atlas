<!--
Section 13 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M12 Evaluation Coverage
-->

# M12 Evaluation Coverage

Standard classifiers, encoder comparisons, and concept permutations used the full cohort and common test split. The primary Qwen3-Embedding-8B encoder received both similarity metrics, the negative controls, and the neighborhood-size sweep. Other encoders were evaluated with nearest and random retrieval under plain cosine similarity at k = 50, so the importance-weighted metric and the sweep describe the primary encoder only.
