<!--
Section 5 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M5. Deterministic narrative and embedded representation
-->

# Supplement M5. Deterministic narrative and embedded representation

The same pre-index record was rendered deterministically into a human-readable
Markdown narrative, and two examples are reproduced in Supplement S4.
Rendering is rule-driven and reproducible: no generative language model
participates in construction. This choice prioritizes traceability over
fluency, because an unsupported generated statement would silently alter the
patient's model input [22].

**What the renderer is given, and what it is not.** It walks a fixed template
of section headings and field labels, in a fixed order, over the field
inventory selected in Supplement M4. That is the same inventory the feature
vector receives. Absent findings are printed explicitly and unrecorded ones as
a literal token, so every patient reaches the encoder through the same constant
form and the narrative's length varies only with how much of that inventory is
populated. The renderer never reads the record outside the 730-day lookback
window, and it never reads a field that predictor selection did not choose. An
untailored encoding of a whole record is therefore a different experiment and
not a variant of this one. The main text states why it was not attempted
(Methods, *Predictors and patient representations*).

Each narrative was mapped to a fixed-length vector with a pretrained
sentence-transformer encoder [28]. The four independently evaluated encoders
were `bge-small-en-v1.5` [23], `bge-en-icl` [24], `Qwen3-Embedding-4B`, and
`Qwen3-Embedding-8B` [25]. This serialization-and-encoding strategy follows
evidence that general-purpose language-model embeddings of serialized EHR
records can perform competitively with purpose-built EHR foundation models
across prediction tasks [15].

FEATURE and EMBEDDED use the same timeline-sliced source record but not an
identical set of rendered fields. The field-level crosswalk in Supplement S8
gives, for every source field, its FEATURE encoding, narrative rendering,
missing-value rule, and temporal availability. Because the field inventories
differ, the comparison is between complete representation pipelines and is
not a controlled comparison of numeric versus language encoding of identical
information.
