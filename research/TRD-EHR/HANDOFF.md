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

The supervised confound, and only this. Beta is fitted on the pool patients, so
0.625 is a supervised metric beaten against an unsupervised one; the anchors are
held out, so nothing leaks, but the comparison is not two retrieval tricks. Until
beta is fitted inside the training fold alone, every claim resting on that
0.625-vs-0.594 gap is soft. It is already flagged in the module docstring and the
README.

## How this student works

They send one long, fully specified request and want the whole of it -- implemented,
documented, submitted to slurm, results filed -- not one step at a time. They defer
the maths to you deliberately and then check the numbers you quote against their
own memory, so quote nothing you have not run.
