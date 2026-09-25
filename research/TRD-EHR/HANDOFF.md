<!-- chapter: predictions -->
## Where this got to

Retrieval-based prediction and the subgroup analysis are taught. Settled, do not re-teach: plain cosine KNN; the importance-weighted cosine (z-scores from the logistic regression pipeline's StandardScaler, fitted on the 34,063 pool patients, w_d = |beta_d| / sum|beta|); the risk line with the max{s, 0}^alpha clamp; Benjamini-Hochberg (BH).

## Got wrong, then right

BH: they first used "rejected" backwards, reading it as "not significant". That was vocabulary, not concept. On the next check (p = .004, .030, .045, .047, .060) they correctly called only rank 1 significant, with no overcorrection. BH is Problem 1 in homework/retrieval-and-subgroups, with their handwriting filed.

## Skipped

The alpha-sharpening check: A (s = .9, TRD), B (s = .6, no TRD). Risk .60 at alpha = 1 and about 0.88 at alpha = 5. The answer is on the board; nothing was filed. They chose to stop.

## Teach next

Figure 4, the k sweep. It is the payoff of this component. Most of the gap between weighted 0.625 and published 0.594 is k, not the metric: the paired metric effect is +0.0068 (95% CI -0.0006 to +0.0141). Best retrieval (0.625) sits below FEATURE XGBoost (0.649) and EMBEDDED logistic regression (0.657). Alpha changes nothing on real data (0.625, 0.625, 0.624).

## Written outside the lesson

A slide deck of this component is at writeups/deck-260925-0942/deck-260925-0942.tex, compiled. latexmk is broken here (system Perl lacks Time::HiRes), so it was built with pdflatex twice.

## How this student works

Answer any question on their page before grading work. They check every number against memory, so quote only numbers that were run. They drop exercises when the pace drags. Keep checks to one quick computation and get to the figure fast. They want each request done whole.
