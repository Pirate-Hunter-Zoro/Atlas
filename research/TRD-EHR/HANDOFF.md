<!-- chapter: predictions -->
## Where the student got to

Lecture on retrieval prediction. The 2026-09-28 sitting opened and closed on one doing turn, with no student answer. Figure 4 (the k sweep: ROC AUC against number of neighbours) was stale in `results/`, the mirror the manuscript links. The cause was `slurm_jobs/quick_runs/neighbor_count_sweep.sbatch`, which never drew the manuscript figure. The job now runs `plot_neighbor_sweep_figure` after the sweep. `REDRAW=1` redraws from the saved CSVs in about a minute. The mirror is current, and it is byte-identical to the artifact. Committed as d43bf0e4. Its numbers match the manuscript Results paragraph: the best retrieval AUC is 0.625 (0.610–0.641).

## What they got wrong

Nothing new this sitting. From 2026-09-25: they could not see "against the rest" in the subgroup forest plots. Those plots show each group's own AUC. BH (Benjamini-Hochberg) tests that AUC minus the same model's AUC on everyone else. The deck now has contrast plots for this. Teach the contrast as its own quantity.

## What they got right

BH mechanics, including the step past a miss. Plain cosine KNN, the importance-weighted cosine and the max{s,0}^α clamp are settled. Do not re-teach them.

## Next

Figure 4 content: why AUC rises with k and is flat from about 300 neighbours. The best k was chosen on the test patients, so those maxima are optimistic. Keep any exercise to one quick question.

## How they work

- They would rather ink a document than type. A mark is a request to change the figure, not to reword the text.
- They cut implementation detail hard ("Just say what we did").
- They want an interval on every number.
- They skip exercises when tired. Record the answer and move on.

## Loose ends

The manuscript .docx and .pdf still embed the old Figure 4 until the packet is rebuilt (plan step 5, `scripts/rebuild-packet.sh`). The paper1-trd-prediction/ documents carry uncommitted edits by the student, so the rebuild was left for them to approve.
