Thread knn-across-embedders (Paper 1): built and committed. Stance was do.

- L1 worry resolved: the grid search fitted L2 for bge-small (C 0.01) and Qwen3-4B (C 0.001), so every coefficient is non-zero by design. The dimension count compared across encoders is the fewest holding 90% of |coefficient| mass: 253, 271, 1,626, 236 (bge-small, bge-en-icl, Qwen3-4B, Qwen3-8B).
- Manuscript has "## Nearest-Neighbor Retrieval Across Encoders" and Figure 5 (results/cross_embedder_retrieval/cross_embedder_sweep.png). Numbers: results/cross_embedder_retrieval/cross_embedder_retrieval.csv and each encoder's sweep_intervals.csv. Packet rebuilt.
- Not in the paper, waiting on the owner: results/cross_embedder_retrieval/lr_dimensions_vs_best_k.png. Four points, and Qwen3-4B (L2, 1,626) is the only one far from ~250, so it shows no trend yet.
- No paired retrieval-minus-classifier contrast exists for the three non-primary encoders. Their per-patient classifier test predictions are not on disk.
- parts/ was not re-split after this edit.
