<!-- chapter:  -->
This was a build sitting on the KNN section of Paper 1 (thread knn-across-embedders). No exercises were posed or answered, so nothing needs re-teaching.

Where the work stands:
- The neighbour-count sweep has run on all four encoders: bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B and Qwen3-Embedding-8B.
- Every redrawn sweep figure (neighbor_count_sweep_manuscript.png, REDRAW=1) is in exports/, stamped 2026-10-06 02:05-02:15.
- Best k: bge-en-icl is 1,519 weighted and 413 plain cosine. Qwen3-4B is 684 and 493. Qwen3-8B is 295, 757 and 32,720 random. bge-small is 579 weighted. All match manuscript lines 293-295 and the Figure S8-S9 panel paths, so the text does not move.
- No report carried RELAY: lines.
- Uncommitted: threads.json, supplement.md and parts/supplement/17-s3-calibration.md.

Next: thread task 11. Rebuild parts/ and run scripts/rebuild-packet.sh --strict. First confirm that the twelve best-k panels and lr_dimensions_vs_best_k.png are on the Mac too, not only the sweep figures. Then do task 14: check the dimension counts (253, 271, 1,626, 236) against cross_embedder_retrieval.csv once the owner marks that file aggregate. Those counts come from session notes, not the evidence ledger.

Still open, owed to the owner:
- The dimension-count vs best-k scatter stays out of the write-up until it has been discussed with them. It has four points, and Qwen3-4B (1,626) is far from the rest.
- The S12.1 interval question for Martin.
- The fixed-seed S7 re-run (card 0007).
- The CSV question (card 0006).
- Thread task 6, the one learning task: why the ROC AUC curve against k has its shape. That covers the random arm at 1/2, k = 1, the climb in log k, the right edge, and why every best k is optimistic. Teach it when the student returns to learning. It is the only conceptual piece of this thread they have not worked.

How this student works:
- They steer by inking the PDF, not by typing. Marks arrive with no text, so open every PNG.
- Cluster reports arrive in batches of three; one card covers each batch.
- Check the export timestamps in exports/ yourself. A report alone does not prove the redrawn copy reached the Mac.
