<!-- chapter: predictions -->
## Where this got to

A lecture on the importance-weighted cosine KNN (k-nearest neighbours) and the subgroup analysis. Settled and not to be re-taught: plain cosine; the weighted formula (standardise to z with the StandardScaler from the logistic regression's pipeline, fitted on the 34,063 pool patients, then w_d = |beta_d| / sum|beta|, weighted inner product, cosine); the risk line with the max{sim_w, 0}^alpha clamp.

They then asked about sorted p-values, which is Benjamini-Hochberg (BH), in `benjamini_hochberg` at scripts/pipeline/review/subgroups/core.py:369.

## Misreading, now corrected on the board

They thought the subgroup test asked whether the interval for ROC_ML - ROC_KNN excludes 0. It does not. Each contrast is one model's AUC inside a subgroup minus its AUC in the rest. There are 24 subgroup levels across 8 families, times 10 models (4 classifiers each on FEATURE and EMBEDDED, plus plain and weighted cosine KNN), giving 240 contrasts. BH runs on two-sided bootstrap p-values, not on whether the interval excludes 0. 60 are nominally significant and 24 survive, 19 of them recurrence contrasts. They had forgotten what the subgroups were.

## Open question

A BH worked example with q = .05 and sorted p-values .001, .025, .028, .035, .300. The bars are .01 to .05. Rank 2 misses its bar but rank 4 clears, so ranks 1-4 are rejected. The trap is stopping at the first miss. Bonferroni's bar of .01 rejects only rank 1.

## Teach next

Grade the BH answer. Then show how alpha = 5 sharpens the neighbours' votes, then the k sweep figure (Figure 4). Move fast: they drop exercises when the pace drags.

## Settled numbers

- The weighted AUC is 0.625 against plain cosine's 0.594. Most of the gap comes from k.
- The paired metric effect is +0.0068 (95% CI -0.0006 to +0.0141).
- Retrieval's best AUC, 0.6249, is below FEATURE XGBoost (0.6492) and EMBEDDED logistic regression (0.6571).

## How this student works

Answer the questions on their page before any exercise. They check every number against memory, so quote only numbers you have run. They want each request done whole.
