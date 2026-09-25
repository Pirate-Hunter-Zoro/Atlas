<!-- chapter: predictions -->
## Where this got to

A lecture on retrieval-based prediction and the subgroup analysis. Settled, not to be re-taught: plain cosine KNN (k-nearest neighbours); the importance-weighted cosine (z-scores from the logistic regression pipeline's StandardScaler, fitted on the 34,063 pool patients, w_d = |beta_d| / sum|beta|); the risk line with the max{s, 0}^alpha clamp; Benjamini-Hochberg (BH).

## BH: what went wrong, what went right

Each subgroup contrast is one model's AUC inside a subgroup minus its AUC in the rest. There are 240 of them: 24 subgroup levels across 8 families, times 10 models. BH runs on two-sided bootstrap p-values. 60 are nominally significant and 24 survive, 19 of them recurrence contrasts.

They first used "rejected" backwards. That was a vocabulary slip, not a conceptual one. On the next check (p = .004, .030, .045, .047, .060) they correctly said only rank 1 is significant. They did not overcorrect. BH is Problem 1 in homework/retrieval-and-subgroups, built, with their handwriting filed.

## Skipped

The alpha-sharpening check was skipped. Two neighbours: A (s = .9, TRD) and B (s = .6, no TRD). At alpha = 1 the risk is .60. At alpha = 5 it is .590/(.590 + .078), about 0.88. The answer went on the board but nothing was filed. They ended the sitting with "I'm okay not doing this. We're done here."

## Teach next

Figure 4, the k sweep. Most of the weighted-versus-plain AUC gap (0.625 against 0.594) comes from k, not from the weighting. The paired metric effect is +0.0068 (95% CI -0.0006 to +0.0141). Retrieval's best AUC, 0.6249, sits below FEATURE XGBoost (0.6492) and EMBEDDED logistic regression (0.6571). The figure is the payoff of this component, and alpha is already on the board.

## How this student works

Answer any question on their page before assessing work. They check every number against memory, so quote only numbers that were run. They drop exercises when the pace drags. Keep checks to one quick computation and get to the figure fast. They want each request done whole.
