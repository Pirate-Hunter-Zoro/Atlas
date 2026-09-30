<!-- chapter: predictions -->
## Where the student got to

Lecture on retrieval prediction. The 2026-09-29 sitting was one doing turn, no student answer. Figure 4 has no k = 50 line. It has a random-neighbour arm with uniform weights, swept over every k up to 34,063, with a band from 1,000 seeded draws; the band covers 0.5 at every k. ROC, PR, calibration, decision-curve, ESS and confusion-matrix panels are drawn at each arm's best k by `best_k_panels.py`. Best k and ROC AUC: weighted 295, 0.625 (0.610–0.641); plain 757, 0.618 (0.602–0.634); random 32,720, 0.500 (2.5th–97.5th percentile across draws 0.484–0.515). Best k is the k with the highest test AUC, the smallest on a tie; for random it is the highest mean across draws. No retrieval number in the paper is read at k = 50 except farthest. Table S8 and the S9 subgroups are at best k too (23 of 240 contrasts survive BH). Their 16 ink marks on pages 1–7, and the paper reviewer's ten findings on that round, are answered in `review/round_2026-09-29.md`. Every number in the packet carries an interval; the classifier AUPRC, Brier and calibration intervals come from `scripts/pipeline/review/metric_intervals.py`. The sweep's artifacts are in `results/<encoder>/<judge>/neighbor_count_sweep/`. To regenerate, submit `slurm_jobs/quick_runs/neighbor_count_sweep.sbatch`, then `slurm_jobs/review/{history_quintiles,subgroup_performance,metric_intervals}.sbatch`; README 5c–5d has the detail.

## What they got wrong

Nothing new this sitting. From 2026-09-25: they could not see "against the rest" in the subgroup forest plots. Those plots show each group's own AUC. BH (Benjamini-Hochberg) tests that AUC minus the same model's AUC on everyone else. The deck now has contrast plots for this. Teach the contrast as its own quantity.

## What they got right

BH mechanics, including the step past a miss. Plain cosine KNN, the importance-weighted cosine and the max{s,0}^α clamp are settled. Do not re-teach them.

## Next

Figure 4, which is drawn: why the random arm sits at 0.5 at every k, and why its "best k" is noise. Then the optimism of every best k, chosen on the same test patients it is scored on. Keep any exercise to one quick question.

## How they work

- They would rather ink a document than type. A mark is a request to change the figure, not to reword the text.
- They cut implementation detail hard ("Just say what we did").
- They want an interval on every number.
- They skip exercises when tired. Record the answer and move on.
