<!-- Cut from the supplement on 2026-09-06. It was a null result about a
     weighting scheme layered on a retrieval predictor the paper had already
     reported as not competitive, so it served no point the paper makes.
     The results themselves stand; nothing here was retracted. -->

# Supplement S6. Nearest–farthest retrieval fusion

The main text observes that the farthest-neighbor predictor is not merely poor
but *informatively* poor. Its ROC AUC of 0.434 (main-text Table 6) falls below
chance, and its ROC curve bows beneath the chance diagonal rather than tracking
it (Figure S6B below). Inverting the predictor therefore recovers a
discrimination of ≈0.57. Dissimilarity in the embedding therefore carries exploitable signal of
its own. This section reports a direct test of whether that signal is *additive*, that
is, whether fusing each patient's nearest-neighborhood risk with their inverted
farthest-neighborhood risk improves on nearest retrieval alone. The test is
reported here in full rather than in the main text, where it is referred to
once from Results, *Prediction from retrieved neighbors*.

Figure S6 shows the two scores that enter that test, each under the uniform
weighting used throughout this section. Nearest retrieval reaches 0.593 and
farthest retrieval 0.434 (main-text Table 6). The farthest curve does not
wander around the chance diagonal the way an uninformative score would. It
sits beneath the diagonal across the entire range, displaced from it by about
as much as the nearest curve is displaced above it. Inverting it gives
1 − 0.434 = 0.566, within 0.03 of nearest retrieval's own 0.593. The farthest neighbors therefore carry real predictive power once their
direction is corrected. That is what makes the fusion question worth asking
rather than a formality. The remainder of this section tests whether that power
is *additional* to what nearest retrieval already supplies.

**(A) Nearest retrieval (ROC AUC 0.593)**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_UNIFORM.png){width=6in}

**(B) Farthest retrieval (ROC AUC 0.434)**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_FARTHEST_UNIFORM.png){width=6in}

***Figure S6.** The two component scores entering the fusion: neighbor-weighted
ROC for (A) nearest and (B) farthest retrieval under uniform weighting
(embedded representation, held-out test set, n = 8,516, K = 50; primary
`Qwen3-Embedding-8B` encoder). Shaded bands are bootstrap 95% intervals and the
dashed diagonal is chance. Uniform weighting is shown because it is the
weighting fused here. Under cosine weighting the same contrast gives 0.594 and
0.432 (main-text Table 6).*

## S6.1 Design

The analysis is post hoc and reuses the row-level predictions already written by
the neighbor-weighted pipeline, and no new retrieval was performed. It is restricted to the primary `Qwen3-Embedding-8B` encoder, the only
configuration for which farthest-scheme scores were computed, and to the 8,516
held-out test anchors (1,491 TRD-positive).

All scores use **uniform** weighting. Under uniform weighting the predicted risk
is the raw TRD rate of the K = 50 geometrically selected neighbors, with no
similarity opinion layered on top, so the retrieval geometry under test is the
only thing shaping the score. That is the right choice on the farthest scheme in
particular, where any similarity weighting is self-contradictory: the scheme
selects the most clinically dissimilar patients and a similarity weight then
pulls them back toward similarity, corrupting the meaning of the inverted term.
Whatever weighting is fused, the nearest-alone baseline uses the same one.

Writing *p*~near~ and *p*~far~ for a patient's nearest- and
farthest-neighborhood predicted risk, three fusions were compared against
*p*~near~ alone:

**Variant (a)** is a parameter-free equal average of *p*~near~ and (1 −
*p*~far~).

**Variant (b)** is a convex blend α·*p*~near~ + (1 − α)·(1 − *p*~far~), with α
chosen from a grid of 21 equally spaced values on [0, 1] by maximizing ROC AUC.

**Variant (c)** is a logistic stack on the raw pair (*p*~near~, *p*~far~). It
fits a coefficient on each term plus an intercept, so it is free both to learn
the sign on *p*~far~ rather than being told to invert it, and to place weights
that do not sum to one.

### Estimation and reporting for the tuned variants

Variants (b) and (c) each estimate parameters from data, which forces a
distinction between the parameters one would *deploy* and the performance one may
*report*. Both variants are handled identically, on a single stratified 5-fold
partition of the 8,516 anchors shared between them, so fold luck cannot confound
their comparison.

**Reported performance is computed out of fold.** Within each fold, α (variant b)
or the logistic coefficients and intercept (variant c) are estimated on the four
training folds alone and applied only to the corresponding held-out fold. Every
patient's fused score therefore comes from parameters fitted without that
patient, and the ROC AUC in Table S6 is computed once over the pooled held-out
predictions rather than as an average of per-fold AUCs. Scoring a tuned parameter on the same data used to choose it is optimistically
biased, and the magnitude here is not negligible. The single α maximizing ROC AUC
across all 8,516 anchors attains 0.600 in sample against the 0.594 obtained out
of fold. That inflation is roughly the size of the entire effect under test,
and enough on its own to manufacture an apparent gain over the nearest-alone
baseline. Embedding every
fitted step inside the resampling loop, rather than reporting the score of an
already-tuned parameter, follows Varma and Simon (*BMC Bioinformatics*
2006;7:91). They show that a cross-validation error computed for a classifier
"that has itself been tuned using CV gives a significantly biased estimate of the
true error."

**Deployable parameters are estimated separately, on all 8,516 anchors**: α = 0.65
for variant (b), and coefficients +3.49 on *p*~near~ and −2.00 on *p*~far~ with an
intercept of −1.80 for variant (c). These are the values that would be applied to
a new patient. The intercept is not incidental: the two coefficients alone fix the
ranking, and so the discrimination reported for variant (c), but the intercept
sets the level of the predicted probabilities and is therefore what its
calibration advantage in Table S6 rests on. The out-of-fold ROC AUC is an estimate *of* this fitted model. The cross-validated
error estimates the true error of the model that the same procedure returns
when trained on the whole dataset. Two caveats attach. First, the out-of-fold estimate is mildly conservative, because each fold's
parameters are chosen on four-fifths of the anchors rather than all of them.
This bias is second-order at this sample size and runs opposite to the
selection bias it removes, so the reported figure should not be read as a lower
bound with the in-sample value as the truth.
Second, these deployment parameters are themselves selected on the held-out test
anchors and are accordingly *not* independently validated. They are reported for
transparency, and nothing in the conclusion of this section rests on them, the
result being null.

The verdict statistic is a **paired** bootstrap on the difference in ROC AUC.
A single 1,000 × 8,516 matrix of resampled patient indices is drawn once and
applied to the baseline and the variant alike, so every draw perturbs both
scores on the same patients. The reported interval spans the 2.5th to 97.5th
percentiles of the resulting difference distribution. Pairing is essential here:
*p*~near~ and (1 − *p*~far~) are positively correlated by construction, and
comparing their marginal confidence intervals for overlap is a substantially
weaker test.

## S6.2 Results

No fusion improved discrimination (Table S6). All three point gains were under 0.006 ROC AUC, and every 95% interval on the
paired difference included zero. That includes the largest, variant (c) at
+0.0059 (−0.0008 to +0.0122). The four ROC
curves are visually indistinguishable (Figure S7).

***Table S6.** Nearest-alone baseline versus three nearest–farthest fusions
(uniform weighting, embedded representation, held-out test set, n = 8,516;
primary `Qwen3-Embedding-8B` encoder). Δ is the difference in ROC AUC against
the nearest-alone baseline with a paired bootstrap 95% interval. WCE = weighted
calibration error. Lower is better for Brier and WCE. Farthest retrieval alone
scores 0.434 (main-text Table 6).*

| Score | ROC AUC (95% CI) | Δ vs nearest alone (95% CI) | AUPRC | Brier | WCE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nearest alone | 0.593 (0.578–0.609) | — | 0.253 | 0.142 | 0.026 |
| (a) Equal average | 0.599 (0.583–0.615) | +0.0051 (−0.0054 to +0.0149) | 0.254 | 0.241 | 0.316 |
| (b) CV-tuned blend | 0.594 (0.579–0.610) | +0.0004 (−0.0081 to +0.0087) | 0.249 | 0.187 | 0.213 |
| (c) Logistic stack | 0.599 (0.584–0.615) | +0.0059 (−0.0008 to +0.0122) | 0.256 | 0.141 | 0.003 |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_fusion_overlay.png){width=6in}

***Figure S7.** ROC curves for the nearest-alone baseline and the three fusion
variants (uniform weighting, embedded representation, held-out test set; primary
`Qwen3-Embedding-8B` encoder). The four curves are visually indistinguishable.
Legend values are ROC AUC with the bootstrap 95% interval. The dashed diagonal
is chance.*

This null is not a power failure. The paired intervals are roughly ±0.006 wide,
about three times tighter than the ±0.016 marginal intervals on the individual
AUCs, so it is the *stronger* test that returns the null rather than an
underpowered one that cannot distinguish the scores.

Two secondary observations are worth recording. First, the logistic stack
recovered the inversion unprompted: it assigned a coefficient of +3.49 to
*p*~near~ and −2.00 to the raw *p*~far~, independently rediscovering that
farthest-neighborhood risk runs backwards. The inverted signal is therefore real, and its direction is learnable from the
data alone. But it is the same geometry restated, which is why restating it
adds nothing. The two tuned variants also
agree on the mixing direction despite optimizing different objectives:
normalizing the stack's coefficients gives 3.49 / (3.49 + 2.00) = 0.64, against
the blend's deployable α = 0.65 and per-fold range of 0.60–0.70. A rank-based
grid search on ROC AUC and a likelihood-based logistic fit independently converge on
the same weighting, which is stronger evidence that the direction is a property
of the data than either result alone. Second, tuning did not help:
the cross-validated blend (b) placed last of the three, below the parameter-free
average, despite stable per-fold weights (α = 0.60–0.70). Pooling out-of-fold
scores produced under five slightly different weightings appears to cost more
than the tuning gains.

Calibration separates the variants even though discrimination does not. The parameter-free fusion (a) and the tuned blend (b) markedly degrade
calibration relative to nearest alone. Brier rises from 0.142 to 0.241 and
0.187 respectively, and weighted calibration error from 0.026 to 0.316 and
0.213. The cause is that (1 − *p*~far~) is not itself calibrated to the
patient's risk. It is
anti-correlated with the outcome by construction, which makes it informative for
*ranking* while leaving its scale arbitrary, so averaging it into a
reasonably calibrated *p*~near~ preserves ordering but distorts the scale. The resulting score is still a risk estimate in the sense of being a number in
[0, 1], just a poorly calibrated one, which is why the remedy is recalibration
rather than abandonment. Both also compress the predicted range so severely
that no patient receives a risk below 0.1, against 14.5% of patients under
nearest alone. The
logistic stack (c) does not share this defect: being fit to the outcome, it
slightly improves on the baseline in both Brier (0.141) and weighted calibration
error (0.003). Variants (a) and (b) should accordingly be treated as ranking
scores only, absent an explicit out-of-fold recalibration step. Variant (c)
requires no such caveat.

## S6.3 Interpretation

The fusion hypothesis is rejected on this cohort. The farthest-retrieval signal is real, and the direction of its inversion is
recoverable from the data without being specified in advance. It is not
additive to nearest retrieval. The likely reason is that both are readings of
the same embedding geometry over the same patients, so the inverted farthest
score largely restates information the nearest score already carries. Fusion across *different* representations, or
across encoders whose geometries disagree, is a materially different proposition
and remains untested.

This analysis is exploratory, single-encoder, and conducted post hoc on the
held-out test set. It is reported for completeness and to close a question the
main text raises, not as a confirmatory result.

