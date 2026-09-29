<!--
Section 6 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M5 Deterministic Narratives and Embeddings
-->

# M5 Deterministic Narratives and Embeddings

Fixed rules rendered the pre-index structured record as a Markdown narrative. No generative model wrote the summaries, preserving traceability and avoiding unsupported generated content \[9\]. Example inputs appear in section S5.

Each narrative was mapped to a fixed-length vector with a pretrained sentence-transformer encoder \[10\]. The four independently evaluated encoders were bge-small-en-v1.5 \[11\], bge-en-icl \[12\], Qwen3-Embedding-4B, and Qwen3-Embedding-8B \[13\]. This serialization-and-encoding strategy follows evidence that general-purpose language-model embeddings of serialized EHR records can perform competitively with purpose-built EHR foundation models across prediction tasks \[14\].

The pipelines share a source record and temporal cutoff but differ in field content. Section S10 documents these differences. Accordingly, the primary comparison evaluates complete pipelines rather than the isolated effect of numeric versus language encoding.
