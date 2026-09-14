<!--
Section 18 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S5. Discrimination stratified by length of pre-index history
-->

# Supplement S5. Discrimination stratified by length of pre-index history

The main text tests the volume and recency confound by correlating the TRD
label with three proxies for how much data a patient has, and finds all three
associations weak and negative (Results, *Validity checks*; Figure 11). That
test asks whether the *outcome* tracks data volume. This section asks the
stronger question: whether *discrimination* tracks it, which is what one would
expect if the predictor were partly reading data volume rather than clinical
content.

The held-out test set was divided into quintiles of pre-index history length
and the neighbor-weighted predictor was scored within each quintile. The
nearest-retrieval, cosine-weighted arm is reported in Table S4. The pattern is
the same under uniform weighting.

***Table S4.** Neighbor-weighted discrimination by quintile of pre-index
history length (nearest retrieval, cosine weighting, embedded representation,
held-out test set). Quintile bounds are in days of pre-index history.*

| Pre-index history (days) | Patients | ROC AUC |
| --- | ---: | ---: |
| 731–1,110 | 1,706 | 0.580 |
| 1,110–1,554 | 1,704 | 0.598 |
| 1,554–2,066 | 1,701 | 0.582 |
| 2,066–2,733 | 1,704 | 0.610 |
| 2,733–5,288 | 1,701 | 0.578 |

Discrimination is flat across the range. The spread between the best and worst
quintile is 0.032 ROC AUC with no monotone trend, across a span of history
length that varies more than fourfold from the shortest quintile to the
longest. Had the predictor been exploiting record volume, discrimination should
have risen with it. It does not.

Two limits on this analysis. It covers the neighbor-weighted arm only, not the
trained classifiers that carry the main comparison, because the stratification
was computed over the neighbor predictions. And each quintile holds roughly
1,700 patients, so the per-quintile estimates are individually imprecise. The
claim rests on the absence of a trend rather than on any single value. A
parallel stratification by embedding-neighborhood density was computed but is
not reported, because the density distribution is concentrated enough that
three of its five bins were empty, leaving too little coverage to interpret.
