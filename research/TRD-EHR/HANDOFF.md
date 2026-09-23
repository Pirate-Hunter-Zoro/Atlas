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

## The index dates are 2013 to 2025, and both drafts say otherwise

Measured from the pipeline's own definition -- the earliest `MedStartInstant` per
patient in `post_mdd_ad_index.csv`, which is what `load_patient_data` takes as the
anchor -- over all 42,579 cohort patients, every one of whom matched:

    earliest index date   2013-09-05
    latest index date     2025-08-14

    2013     1   2016  1941   2019  4893   2022  5224   2025  1566
    2014   148   2017  3552   2020  5112   2023  5219
    2015   194   2018  4077   2021  5612   2024  5040

The packet says "Patient index dates spanned 2016-2024" in Methods and again in
Limitations, and derives "a nine-year window" from it. The senior author's rewrite says
2016-2025. All three are wrong: 343 patients sit before 2016 and 1,566 in 2025, and the
window is twelve years. Fix the two sentences and the derived phrase together.

Paper-Writer's numbers gate cannot catch this. `gates/numbers.py` skips four-digit years
on purpose -- "2024 is a date, not a finding" -- which is right everywhere except here,
where the year IS the finding.

## The retrieval slate, settled

Two arms, cosine weighting throughout, and the similarity that ranks is the similarity
that weights:

  * **importance-weighted cosine KNN** -- the arm.
  * **plain cosine KNN** -- the baseline, and the published `NEAREST_COSINE`.

Out: uniform weighting, the MedGemma clinical-similarity judge, combined weighting,
subsampled retrieval. Random and farthest stay as negative controls in the supplement.
The judge staying in reserve kills the two references the rewrite resurrected and its
four-weighting Methods sentence.

**Point 2 needs no chosen k.** The maximum of the retrieval curve over every k from 1 to
the whole 34,063-patient pool, under either metric and any sharpening, is 0.6249 --
below FEATURE XGBoost at 0.6492 and EMBEDDED logistic regression at 0.6571. Paired over
the 8,516 anchors, weighted KNN loses by 0.0244 (95% CI -0.0366 to -0.0110) and 0.0323
(-0.0432 to -0.0212); neither interval crosses zero. Quoting the maximum hands retrieval
the best k with hindsight and it still loses, which is the conservative direction.

Subgroups are re-run on this slate: 240 contrasts, 60 nominally significant, 24 surviving
Benjamini-Hochberg -- 19 MDD recurrence, 3 marital status, 1 severity, 1 age band,
smallest adjusted P = .014. The earlier `reported_set` block also held 240 and was a
different slate (uniform plus cosine), so none of its adjusted P-values carry over.

## Still to write

Nothing of the manuscript has been drafted against any of the above. The decisions are
taken and the numbers are measured; the prose is not written. Follow the senior author's
supplement numbering, which means his S1 -- the similarity judge -- has to go or be
re-cast, because the slate above cut it from the main text.
