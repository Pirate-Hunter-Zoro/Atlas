<!-- Cut from the supplement on 2026-09-06. The bimodal pairwise-similarity
     histogram in bge-small-en-v1.5 is an encoder artifact. It serves neither
     point the paper makes, and the encoder it concerns is the weakest of the
     four and not the primary one. Complete and unretracted; nothing here was
     withdrawn, it simply is not what this paper is about. -->

# Supplement S4. Encoder similarity geometry: a bimodality artifact in bge-small-en-v1.5

A complementary view of how each encoder organizes the cohort is the
distribution of cosine similarities between patient embeddings.
Figure S4 contrasts, for each encoder, the similarities of random
patient pairs (red) against those of nearest-neighbor pairs (green). The
red random-pair histogram is the encoder's overall similarity
distribution. Three of the four encoders produce smooth, unimodal random-pair distributions:
bge-en-icl, Qwen3-Embedding-4B, and Qwen3-Embedding-8B. The smallest encoder, bge-small-en-v1.5, is the exception. Its random-pair
distribution is distinctly multimodal, with a sharp primary peak near 0.99 and
a separated secondary mode near 0.98. The cohort splits into two internally
similar groups rather than spreading along a single continuum.

**(A) bge-small-en-v1.5**

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(B) bge-en-icl**

![](../results/bge-en-icl/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(C) Qwen3-Embedding-4B**

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(D) Qwen3-Embedding-8B**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

***Figure S4.** Random-pair (red) versus nearest-neighbor-pair (green)
cosine similarities for each encoder (full cohort). (A) bge-small-en-v1.5,
(B) bge-en-icl, (C) Qwen3-Embedding-4B, (D) Qwen3-Embedding-8B. The red
random-pair histogram is the encoder's overall similarity distribution:
it is multimodal only for bge-small-en-v1.5 (A) and smoothly unimodal for
the other three. In every panel the neighbor-pair similarities (green)
sit above the bulk of the random-pair mass, confirming that
nearest-neighbor retrieval selects genuinely more similar patients. Axis
ranges differ per panel because the encoders occupy different absolute
similarity bands.*

To identify the split we clustered the L2-normalized bge-small
embeddings into two groups with k-means (k = 2), which partitioned the
42,579 patients into 14,438 and 28,141. The partition coincides almost perfectly with a single surface lexical feature.
The literal token "episode" appears in essentially every narrative of the
larger cluster and almost none of the smaller. The related MDD recurrence and
severity wording follows the same split (Table S4).

It is worth being precise about what each cluster is, because the two
clusters are *not* simply "recurrent" versus "non-recurrent". The
narrative renders each patient's MDD coding verbatim, e.g.
`MDD (Single Episode, Unspecified)` or `MDD (Recurrent, Moderate)`. Only
the single-episode wording contains the word "episode". So:

- **Cluster B (28,141)** = narratives that contain "episode", which are the
single-episode patients (28,206 in the cohort).
- **Cluster A (14,438)** = narratives that do not, a mixture of the 11,213
patients coded `Recurrent` and the ~3,200 coded `Unspecified` or `Dysthymia`,
neither of which uses the word "episode".

Cluster A is therefore best described as "no *episode* token", not as
"all recurrent". Roughly one patient in five inside it is not coded
recurrent at all. That distinction is what the second-order analysis
below turns on.

***Table S4.** Surface tokens that most strongly separate the two
k-means clusters of bge-small-en-v1.5 embeddings. Values are the
fraction of narratives in each cluster containing the token (binary
presence). Cluster A = 14,438 patients (narratives with no "episode"
token: recurrent-coded plus unspecified/dysthymia), cluster B = 28,141
(single-episode narratives). The token "single" is elevated in both
clusters because it also occurs as a marital status.*

| Token | P(present \| cluster A) | P(present \| cluster B) | \|Δ\| |
| --- | ---: | ---: | ---: |
| episode | 0.00 | 1.00 | 1.00 |
| recurrent | 0.78 | 0.00 | 0.78 |
| single | 0.30 | 1.00 | 0.70 |
| unspecified | 0.39 | 0.83 | 0.45 |
| moderate | 0.32 | 0.09 | 0.23 |

Figure S5 makes that mechanism visible. Both panels are histograms of *pairs of patients*, not of patients. For every
pair in the set shown we compute the cosine similarity between the two
embeddings and ask one yes/no question about the two narratives. Do they agree
on a particular word? Pairs that agree are drawn in blue, pairs that disagree in red, and
the grey histogram behind them is every pair in the set (the sum of the
two). If a single word were driving the geometry, blue and red would sit
at visibly different similarities. If it were not, they would lie on top
of each other.

Panel A asks this of all 42,579 patients, with the word "episode": *do
both narratives contain it, or does neither?* Blue is agreement (both
single-episode, or both non-single-episode) and red is disagreement (one
of each). The blue pairs pile up at ≈0.99 and the red pairs at ≈0.97, so the two modes of
Figure S4A are exactly these two groups. The encoder places two patients ≈0.02
further apart when their MDD coding is phrased differently, whatever else is in
their records.

Panel B asks it again inside cluster A alone, with the word "recurrent".
A second question is needed because every narrative in cluster A lacks
"episode", which makes panel A's question uninformative there. And "recurrent"
is a genuine question because cluster A is not uniformly recurrent: 11,425 of
its members are coded `Recurrent` and 3,013 are coded `Unspecified`. Blue pairs (both `Recurrent`, or both `Unspecified`)
again separate from red pairs, so cluster A carries a real second split,
once more on wording rather than on clinical content.

Cluster B (n = 28,141) was tested the same way and is not plotted. Its
only candidate second-order token is the narrative's `Missing` sentinel,
and there the blue and red histograms lie almost exactly on top of each other.
There is no second split to show. Those numbers are in Table S5.

**(A) All 42,579 patients, split by the "episode" token**

![](../notebooks/figures/bge_small_recurrence_bimodality.png){width=5.5in}

**(B) Cluster A only (n = 14,438), split by the "recurrent" token**

![](../notebooks/figures/bge_small_cluster0_subsplit.png){width=5.5in}

***Figure S5.** Pairwise cosine-similarity distributions for
bge-small-en-v1.5, decomposed by whether the two patients in a pair use
the same wording for one token (blue = same, red = different, grey = all
pairs in the set shown). **(A)** All 42,579 patients, split on the
"episode" token: same-wording pairs form the upper mode near 0.99 and
differing-wording pairs the lower mode near 0.97, so the bimodality in
Figure S4A is driven by recurrence phrasing rather than by holistic
clinical similarity. **(B)** Cluster A only (the 14,438 patients whose
narratives lack "episode"), split on the "recurrent" token: the two
colours again separate, so this cluster is itself genuinely divided, once more
along a surface-lexical axis. Cluster B admits no comparable
second split and is not plotted (Table S5).*

The lowest-capacity encoder therefore organizes its geometry around the
presence or absence of one recurrence-phrasing token rather than around
holistic clinical content, and that lexical split produces the second mode of
Figure S4A (Figure S5A). The higher-capacity encoders show no such artifact.

On visual inspection each of the two parent clusters looks as though it
might contain two further sub-modes. Table S5 tests whether those
apparent sub-modes are real. The test is the same one twice: take a
parent cluster on its own, re-run k-means (k = 2) inside it, ask how
clean the resulting two-way split is, and then ask which word the split
tracks.

Cleanliness is measured by the cosine silhouette (5,000-point subsample,
seed fixed), a score from −1 to 1 that asks, for each patient, whether it
sits closer to its own sub-cluster than to the other one. Higher means a
better-separated split. The number is only interpretable by comparison,
so the reference point is the top-level split of Table S4, which scores
0.48 under the same metric. A within-cluster split scoring well above
0.48 is more clearly separated than the split it came from. One scoring
well below is not really a split at all.

The two parents give opposite answers. Cluster A, the one with no "episode" token, subdivides **more** cleanly than
the parent split itself, at a silhouette of 0.69. It splits into an explicitly
recurrent subgroup (n = 11,425, the token "recurrent" present in 98% and
carrying the severity words "moderate", "mild" and "severe") and a smaller
unspecified-recurrence subgroup (n = 3,013, "unspecified" in 100% and no
severity wording). That smaller
subgroup is the same ≈3,000 patients (7% of the cohort) that a flat
three-cluster solution peels off. Cluster B (single-episode)
does **not** meaningfully subdivide: silhouette 0.21, well below the
parent 0.48. What little structure it has is keyed on the narrative's
`Missing` sentinel, present in 88% of one putative subgroup and 2% of the
other. That is a data-completeness gradient, meaning how much of the record was
filled in, rather than a clinical contrast. Consistent with that reading, the
better-populated side additionally carries named SSRIs (citalopram 0.24,
escitalopram 0.16, sertraline 0.17) simply because those patients have
more recorded medication.

***Table S5.** Do the two clusters of Table S4 split again? Each parent
cluster was re-clustered on its own with k-means (k = 2). "Driving token"
is the word whose presence best separates the two resulting sub-clusters,
and the two proportions are the fraction of narratives containing that
word in each sub-cluster, so 0.98 / 0.00 means the word is essentially present
in one sub-cluster and absent from the other. "Split silhouette"
scores how cleanly the two sub-clusters separate. Compare it against
0.48, the score of the top-level split under the same metric. Cluster A
splits cleanly, on recurrence phrasing. Cluster B does not split: its
0.21 is a weak data-completeness gradient on the missing-data sentinel,
which is why it is not plotted in Figure S5.*

| Parent cluster (n) | Splits into (n / n) | Driving token | Token present, sub 1 / sub 2 | Split silhouette (top level = 0.48) | Real split? |
| --- | --- | --- | ---: | ---: | :---: |
| A: no "episode" token (14,438) | recurrent + severity (11,425) / unspecified (3,013) | recurrent | 0.98 / 0.00 | 0.69 | Yes |
| B: single-episode (28,141) | sparse record (6,594) / populated record (21,547) | missing | 0.88 / 0.02 | 0.21 | No |

This layered reading reinforces rather than complicates the single-token
interpretation. At the top level the encoder keys on the recurrence token, and
the only genuine finer structure is a further split of cluster A on recurrence
phrasing, which is again a surface-lexical axis.
Where a candidate second split does not track clinical content
(cluster B), the silhouette correctly declines to support it, and the
apparent mode there reduces to how completely the record was filled in.
This is consistent with bge-small-en-v1.5 being the weakest discriminator
in the cross-embedder comparison (main-text Table 5) and serves as a
cautionary note that small sentence-transformer encoders can organize
their geometry around individual surface tokens rather than clinical
content. The analysis is descriptive, being k-means splits and binary token-presence
rates, and it is specific to this encoder. All
primary analyses use Qwen3-Embedding-8B.

