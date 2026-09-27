<!-- chapter: predictions -->
## Where the student got to

Lecture on retrieval prediction and subgroups. The 2026-09-24 sitting is closed. It covered Benjamini-Hochberg (BH) by hand: the rising bars, and why a p-value that misses its own bar still counts when a larger one further down clears. That write-up compiled in homework/retrieval-and-subgroups. The α-sharpening exercise was skipped, so it is not in the write-up. The answer is on the closing card: α = 5 gives r̂ ≈ 0.88, against 0.60 at α = 1.

## What they got wrong

On 2026-09-25 they marked up the slide deck (writeups/deck-260925-0942). They could not see what "against the rest" meant, and the subgroup forest plots did not show it. The confusion was real: those plots show each group's own AUC, but BH tests a group's AUC minus the same model's AUC on everyone else. The deck now has contrast plots (ΔAUC, filled = survives BH), drawn by `plot_contrasts` in run_subgroups.py. When subgroups come up, teach the contrast as its own quantity, separate from the group AUC.

## What they got right

BH mechanics, including the step past a miss. Do not re-teach these. The deck brief also treats plain cosine KNN, the importance-weighted cosine and the max{s,0}^α clamp as settled.

## Next

Figure 4, the k sweep. The closing card named it, and the deck already explains it.

## How they work

- They would rather ink a document than type. The marks are terse questions ("we don't see that in the graph"), and a mark is a request to change the figure, not to reword the text.
- They cut implementation detail hard ("Don't care. Just say what we did").
- They want an interval on every number they see.
- They skip exercises when tired. Record the answer and move on; do not chase it.

## Loose ends

None of the code changes from the deck rounds are committed: run_subgroups.py, neighbor_count_sweep.py and plot_neighbor_sweep_figure.py. The results/ mirror holds the old Figure 4.
