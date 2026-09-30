<!-- chapter: predictions -->
## Where the student got to

Lecture on retrieval prediction. The 2026-09-29 sitting was one doing turn, no student answer. Figure 4 has no k = 50 line. It has a random-neighbour arm with uniform weights, swept over every k up to 34,063, with a band from 1,000 seeded draws; the band covers 0.5 at every k. ROC, PR, calibration, decision-curve, ESS and confusion-matrix panels are drawn at each arm's best k by `best_k_panels.py`. Best k and ROC AUC: weighted 295, 0.625 (0.610–0.641); plain 757, 0.618 (0.602–0.634); random 32,720, 0.500 (0.484–0.515). The manuscript and supplement carry these numbers.

## What they got wrong

Nothing new this sitting. From 2026-09-25: they could not see "against the rest" in the subgroup forest plots. Those plots show each group's own AUC. BH (Benjamini-Hochberg) tests that AUC minus the same model's AUC on everyone else. The deck now has contrast plots for this. Teach the contrast as its own quantity.

## What they got right

BH mechanics, including the step past a miss. Plain cosine KNN, the importance-weighted cosine and the max{s,0}^α clamp are settled. Do not re-teach them.

## Next

After the job runs: Figure 4 with the random band. Why the random arm sits at 0.5 at every k, and why its "best k" is noise. The best k was chosen on the test patients, so every maximum is optimistic. Keep any exercise to one quick question.

## How they work

- They would rather ink a document than type. A mark is a request to change the figure, not to reword the text.
- They cut implementation detail hard ("Just say what we did").
- They want an interval on every number.
- They skip exercises when tired. Record the answer and move on.
