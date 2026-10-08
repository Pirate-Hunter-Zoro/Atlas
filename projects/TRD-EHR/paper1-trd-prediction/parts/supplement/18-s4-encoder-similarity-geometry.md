<!--
Section 18 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S4 Encoder Similarity Geometry
-->

# S4 Encoder Similarity Geometry

Figure S6 compares cosine similarities for random patient pairs and nearest-neighbor pairs. The 3 larger encoders produced broadly unimodal random-pair distributions. bge-small-en-v1.5 showed multiple modes at high similarity values, prompting a descriptive analysis of the corresponding narrative wording.

A bge-small-en-v1.5

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

B bge-en-icl

![](../results/bge-en-icl/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

C Qwen3-Embedding-4B

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

D Qwen3-Embedding-8B

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

Figure S6. Cosine similarity for random pairs (red) and nearest-neighbor pairs (green) for bge-small-en-v1.5 (A), bge-en-icl (B), Qwen3-Embedding-4B (C), and Qwen3-Embedding-8B (D). Axis ranges differ across encoders. The smallest encoder shows a multimodal random-pair distribution.

K-means clustering of L2-normalized bge-small embeddings (k=2) separated 42,579 patients into groups of 14,438 and 28,141. The partition closely tracked whether the narrative contained the token "episode" (Table S5).

The token occurs in "Single Episode" but not "Recurrent" or "Dysthymia." Thus, the partition should not be described simply as recurrent versus nonrecurrent depression.

Cluster B (n=28,141) largely comprised narratives containing "episode"; the full cohort contained 28,206 patients coded single episode.

Cluster A (n=14,438) largely lacked "episode" and included both recurrent and other depression codes. The full cohort contained 11,213 recurrent-coded patients.

Table S5. Fraction of narratives containing selected tokens within each top-level k-means cluster. Cluster A has 14,438 patients and cluster B has 28,141. "Single" may also denote marital status.

  **Token**     **P(present \| cluster A)**   **P(present \| cluster B)**   **\|Δ\|**
  ------------- ----------------------------- ----------------------------- -----------
  episode       0.00                          1.00                          1.00
  recurrent     0.78                          0.00                          0.78
  single        0.30                          1.00                          0.70
  unspecified   0.39                          0.83                          0.45
  moderate      0.32                          0.09                          0.23

Figure S7 stratifies pairwise similarities by token agreement. Blue denotes pairs agreeing on token presence, red denotes disagreement, and gray denotes all pairs.

Across the cohort, pairs agreeing on "episode" had higher similarities than pairs differing on that token (Figure S7A). This association links the observed modes to diagnostic wording but does not isolate a causal token effect from correlated clinical information.

Within cluster A, the same comparison using "recurrent" again separated similarity distributions (Figure S7B). The nested k-means subgroups contained 11,425 and 3,013 patients; these cluster sizes should not be equated with diagnosis-code counts.

Within cluster B, similarity distributions showed little separation by the "Missing" token. Nested cluster results are summarized in Table S6.

A All patients

![](../results/notebook_figures/bge_small_recurrence_bimodality.png){width=5.8in}

B Cluster A

![](../results/notebook_figures/bge_small_cluster0_subsplit.png){width=5.8in}

Figure S7. Pairwise similarity by agreement on "episode" across the cohort (A) and on "recurrent" within cluster A (B). Blue denotes token agreement, red disagreement, and gray all pairs. The analysis is descriptive and does not establish that wording alone causes the separation.

We re-ran k-means (k=2) within each parent cluster and described separation using the cosine silhouette in a seeded 5,000-patient subsample. The top-level silhouette was 0.48.

Silhouette values summarize within- versus between-cluster similarity and are descriptive, not hypothesis tests. They do not by themselves establish discrete biological or clinical subgroups.

Cluster A had a nested silhouette of 0.69. The larger subgroup (n=11,425) contained "recurrent" in 98% of narratives, whereas the smaller subgroup (n=3,013) contained "unspecified" in all narratives. Cluster B had weaker separation (silhouette 0.21); "Missing" appeared in 88% versus 2% of its subgroups. Medication tokens also differed, consistent with differences in record content.

Table S6. Nested k-means results within each parent cluster. Token proportions describe presence in the 2 subgroups. The top-level cosine silhouette was 0.48; higher values indicate greater geometric separation, without establishing clinical validity.

  **Parent cluster (n)**           **Splits into (n / n)**                               **Driving token**   **Token present, sub 1 / sub 2**   **Split silhouette (top level = 0.48)**   **Separation**
  -------------------------------- ----------------------------------------------------- ------------------- ---------------------------------- ----------------------------------------- ----------------
  A: no "episode" token (14,438)   recurrent + severity (11,425) / unspecified (3,013)   recurrent           0.98 / 0.00                        0.69                                      Stronger
  B: single-episode (28,141)       sparse record (6,594) / populated record (21,547)     missing             0.88 / 0.02                        0.21                                      Weaker

These findings show sensitivity of the smallest encoder's geometry to diagnostic wording and missing-value tokens. They may help explain its retrieval behavior, but do not establish why its discrimination was lower (Table S15). Primary analyses used Qwen3-Embedding-8B.
