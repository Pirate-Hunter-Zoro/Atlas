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

**What does move.** 0.594 is plain cosine at k=50 and 0.625 is the weighted
metric at k=295, so the metric and the neighbourhood size change together and
neither number separates them. The sweep runs both metrics over the same k --
`--metrics`, plain cosine being the raw embedding L2-normalised with no
classifier in it -- and the plain curve is the control that says how much of the
gap was only k.

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
