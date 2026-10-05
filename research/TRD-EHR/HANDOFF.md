<!-- chapter:  -->
Thread knn-across-embedders (Paper 1). The owner's direction is applied to the text; the figures it needs are not made yet.

In the text now:
- Retrieval is nearest and random neighbours, each scored at every k from 1 to 34,063; no single k is the headline. ROC curves and confusion matrices are shown only at each arm's best k.
- Farthest-neighbour retrieval is gone from every document in paper1-trd-prediction/ except review/ and feedback/, which are records. It remains in research/TRD-EHR/README.md and in code (core.py, fusion_analysis.py, retriever.py, neighbor_scheme.py).
- Figure 4 is the primary encoder's panel; Figure 5 is the other three encoders' panels (A-C); Figure 6 is dimensions holding 90% of |coefficient| mass against best k, in the main text (owner's answer).
- Best-k ROC and confusion panels for all four encoders (owner's answer) are Figures S8-S9.
- parts/ is re-split. No PDF or .docx is rebuilt: the figures are not on this Mac.

Not made yet, all on the cluster: the three per-encoder sweep figures, the twelve best-k panels, and lr_dimensions_vs_best_k.png in results/cross_embedder_retrieval/. plot_neighbor_sweep_figure.py now falls back to classical_ml_results_*.json where an encoder has no per-patient predictions, which is why job 2110916 (bge-small) failed. The rerun is filed as its repair (--fixes 2026-10-02-knn-across-embedders-neighbor-count-sweep), then the other two encoders and Qwen3-8B with REDRAW=1, then plot_cross_embedder_retrieval.sbatch. The figures cross only once the owner marks the 23 thread exports aggregate.

The dimension counts (253, 271, 1,626, 236) and the L2 penalty of the other encoders' logistic regressions come from an earlier session's notes, not the evidence ledger; check them against the cluster's outputs when they land. If the bge-small rerun moves its best k, the panel file names and the text move with it (best_k_panels.json).

How this student works: they steer by inking the PDF, not by typing. Marks arrive with no text. Open every PNG; the same page marks can repeat across sessions.
