<!-- chapter: predictions -->
## Where this got to

The predictions arm has a second KNN beside the published one. Importance-weighted
metric plus a sweep of k from 1 to the whole 34,063-patient pool: committed as
c267ec57 and now pushed to origin/main. Five new files, nothing in the published
arm touched, no enum member added, so `knn_results.json` still means what it meant.

Numbers, all measured: ROC AUC 0.625 (95% CI 0.610-0.641) against plain cosine's
0.594. The curve climbs to roughly k=300 and is flat from there to the whole pool,
so the inherited k=50 cost more than the metric did. Sharpening is dead -- alpha
1, 2 and 5 give 0.625, 0.625, 0.624. Full suite re-run this session: 44 passed
before the new test file, 53 after.

## Settled, do not re-teach

The student's own recollection was right and is now confirmed against the fitted
model: 385 of 4096 coefficients non-zero, top 41 dimensions hold 31% of the
|beta| mass. The weighted-cosine formula has been named to them in full.

One stale number, code is not wrong: commit c267ec57's message says the top 1%
carries 30.5%, which is the figure for 40 dimensions. `concentration_summary`
rounds 40.96 up to 41 and reports 31.08%. No shipped artifact carries 30.5%.

## Teach next

What the 0.625-vs-0.594 gap is made of, because two things move between those
numbers and neither of them is a validity problem.

**Beta is not a confound.** It is fitted on the 34,063 pool patients, the 8,516
anchors are held out, and a supervised predictor fitted on train and scored on
test is the ordinary arrangement rather than a leak. An overfitted beta would
LOWER the held-out AUC, not raise it. The module docstring has this right and
claims only that the metric is supervised. Nothing needs re-fitting.

**What moved was k, and it is measured.** The sweep now runs both metrics over
the same k (`--metrics`; plain cosine is the raw embedding L2-normalised, no
classifier in it), and it reproduces the published arm exactly at its own
setting: plain cosine, alpha 5, k=50 gives 0.5939, which is `NEAREST_COSINE` in
`knn_results.json` to four decimals.

| | plain cosine | importance-weighted |
| --- | --- | --- |
| k = 50 | 0.5939 | 0.6038 |
| own best k | 0.6180 (k=757) | 0.6248 (k=295) |

So of the 0.031 between the published 0.594 and the weighted 0.625, roughly
0.024 is neighbourhood size and 0.007 is the metric. Paired over the 8,516
anchors, each arm at its own best k, the metric is worth **+0.0068 (95% CI
-0.0006 to +0.0141)** and the interval crosses zero.

**The supervised metric buys nothing, so nothing rests on defending it.** k=50
was the whole story. That result is unsupervised end to end and is the one to
write up: the inherited neighbourhood size cost more than the metric ever
returned. Sharpening stays dead in both arms -- alpha 1, 2 and 5 agree to three
decimals.

**And one real optimism, small.** A best k is the largest of 34,063 held-out
AUCs, so it is selected on the anchors. The curve is flat from k=261 to the whole
pool, which is why it costs little here, and `roc_auc_at_all_neighbors` is the
same curve read at a k nobody chose: 0.6237. Quote that where the selection
matters.

## How this student works

They send one long, fully specified request and want the whole of it -- implemented,
documented, submitted to slurm, results filed -- not one step at a time. They defer
the maths to you deliberately and then check the numbers you quote against their
own memory, so quote nothing you have not run.
