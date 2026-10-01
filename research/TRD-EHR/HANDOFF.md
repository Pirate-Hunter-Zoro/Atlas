<!-- chapter: predictions -->
Where they got to: the neighbour-count sweep lesson (planning/TRD-EHR_TODO.txt, L1-L5) has opened and nothing has been answered. One card is on the board. It shows the manuscript sweep figure (results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/neighbor_count_sweep_manuscript.png), lists L1-L5, and poses L1's first micro-check. That check is still open. Pool p1-p4, only p1 TRD, k=4 (the whole pool, uniform weights). Ask for s_A, s_B and the AUC. Expected answer: s_A = s_B = 1/4, every pair ties, AUC = 1/2.

Got wrong: nothing yet. No answers on record.

Got right: nothing yet. Nothing is settled, so nothing is protected from re-teaching.

Next thing to teach: re-pose that same k=4 micro-check. It is the cheapest way into L1, because ties alone give AUC 1/2. Then do the k=1 random case. The random neighbour is drawn independently of the anchor's label, so s_A and s_B have the same distribution, giving AUC 1/2 in expectation. Then re-pose L1 in full with its definitions list. Bind a homework file (board hw list / new) on the first agreed answer.

Before L4, verify from the embeddings what share of weighted-cosine similarities are non-positive and so get weight zero. Only 385 of 4096 dimensions have nonzero importance. This is unverified, so do not teach the flat right edge until it is checked.

Figures from the sweep: risk = sum of w*y over sum of w on the k nearest, with w = max(cos, 0)^alpha and alpha = 1. Pool 34,063; test 8,516; prevalence 0.175. Code: scripts/pipeline/predictions/neighbor_count_sweep.py.

How they work: the direction (set 2026-09-30) asks for the figure to be shown repeatedly. Show it again on any card whose question is about a feature of the curve.
