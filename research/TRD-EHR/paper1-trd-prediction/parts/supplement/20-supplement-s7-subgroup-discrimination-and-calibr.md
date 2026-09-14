<!--
Section 20 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S7. Subgroup discrimination and calibration
-->

# Supplement S7. Subgroup discrimination and calibration

This paper makes no fairness claim (Methods, *Model development*,
**Semantic-feature ablation**, Discussion, *Limitations*). The permutation
slate it reports measures how much a model's discrimination depends on a
concept being present in its input, which is a different question from whether
performance is even across groups. This section reports the subgroup evidence
itself.

## S7.1 Design

**Nothing was refit.** The per-patient held-out predicted probabilities the
pipeline persists were partitioned by stratum, and discrimination and
calibration were recomputed inside each group. Subsetting a per-patient
prediction vector is arithmetically identical to scoring that model on the
subset, so no published number can drift. Refitting within a subgroup would
answer a different question, namely how a model trained only on one group
predicts that group, and would break comparability with everything else
reported.

**All three prediction arms are covered.** The embedded and feature-vector
arms contribute their four classifiers each, and the neighbor-weighted arm
contributes its two reported nearest-retrieval weightings, uniform and cosine.
Only nearest-retrieval configurations are contrasted across groups. Whether a
deliberately uninformative retrieval scheme is evenly uninformative across
subgroups is not a fairness question, and including the negative controls would
inflate the multiplicity burden on the contrasts that are.

**Strata.** Six sociodemographic families (sex, race, age band, marital status,
smoking status, religion) and two clinical ones (MDD recurrence and severity).
Race is collapsed to majority against recorded minority because a
level-by-level breakdown is not estimable at 80.0% White/Caucasian. Preferred
language is absent by necessity rather than choice: 98.9% of the cohort prefers
English, leaving one estimable level and therefore no contrast. A group whose
smaller class holds fewer than 20 outcome events is declared not estimable
rather than reported.

**Intervals and multiplicity.** Within-group intervals are percentile
bootstraps over that group's own patients. Between-group intervals are
*unpaired* bootstraps, because two subgroups are disjoint patient sets and each
must be resampled independently, unlike the paired test used for the
representation contrasts in main-text Figure 2. Two hundred forty contrasts
were computed. At that number, nominally significant results arise from
sampling alone, so each contrast carries a two-sided bootstrap *P* value taken
from the same draws, adjusted across the entire reported set by Benjamini-Hochberg,
controlling the false discovery rate at 5%. The adjusted value is what
we interpret. The reported set is the 240 contrasts this paper describes, not
the 288 the analysis ran. The two neighbor weightings that left the paper took
48 contrasts with them. A Benjamini-Hochberg threshold depends on how many
tests it ranks, so dropping them changes every adjusted value.

Calibration slope is the coefficient of a logistic regression of the outcome on
the logit of predicted risk (1.0 is perfect). Calibration-in-the-large is mean
predicted risk minus observed rate (0.0 is perfect). Both are computed directly
rather than from the binned calibration surface used in main-text Table 3,
because a bin-mean fit over a few thousand patients describes the bin grid more
than it describes the model.

## S7.2 Sociodemographic strata

***Table S6.** Discrimination and calibration by sociodemographic stratum, one
representative model per arm, held-out test set. Groups are not disjoint across
families: every patient with a recorded sex appears in one sex row and every
patient with a recorded race in one race row.*

| Group | n | TRD+ | Arm | ROC AUC (95% CI) | Brier | Calibration slope | Calibration-in-the-large |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| All held-out patients | 8,516 | 1,491 | Embedded (logistic regression) | 0.657 (0.643–0.672) | 0.137 | 0.97 | +0.000 |
| All held-out patients | 8,516 | 1,491 | Feature vector (logistic regression) | 0.629 (0.613–0.644) | 0.139 | 0.95 | -0.000 |
| All held-out patients | 8,516 | 1,491 | Neighbor-weighted (nearest, cosine) | 0.594 (0.578–0.610) | 0.142 | 0.56 | -0.007 |
| Male | 2,347 | 386 | Embedded (logistic regression) | 0.653 (0.622–0.682) | 0.131 | 0.94 | -0.003 |
| Male | 2,347 | 386 | Feature vector (logistic regression) | 0.626 (0.595–0.655) | 0.133 | 0.86 | -0.003 |
| Male | 2,347 | 386 | Neighbor-weighted (nearest, cosine) | 0.595 (0.563–0.627) | 0.135 | 0.58 | -0.005 |
| Female | 6,168 | 1,105 | Embedded (logistic regression) | 0.658 (0.641–0.675) | 0.139 | 0.98 | +0.002 |
| Female | 6,168 | 1,105 | Feature vector (logistic regression) | 0.630 (0.612–0.648) | 0.141 | 0.99 | +0.001 |
| Female | 6,168 | 1,105 | Neighbor-weighted (nearest, cosine) | 0.592 (0.574–0.611) | 0.145 | 0.55 | -0.008 |
| White/Caucasian | 6,835 | 1,181 | Embedded (logistic regression) | 0.657 (0.640–0.674) | 0.136 | 0.97 | +0.002 |
| White/Caucasian | 6,835 | 1,181 | Feature vector (logistic regression) | 0.633 (0.615–0.652) | 0.137 | 0.98 | +0.001 |
| White/Caucasian | 6,835 | 1,181 | Neighbor-weighted (nearest, cosine) | 0.604 (0.585–0.622) | 0.140 | 0.61 | -0.007 |
| Non-White (recorded) | 1,631 | 302 | Embedded (logistic regression) | 0.652 (0.620–0.684) | 0.144 | 0.95 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | Feature vector (logistic regression) | 0.608 (0.573–0.643) | 0.147 | 0.79 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | Neighbor-weighted (nearest, cosine) | 0.551 (0.515–0.588) | 0.152 | 0.37 | -0.006 |
| Race not recorded | 50 | 8 | Embedded (logistic regression) | not estimable | — | — | — |
| Race not recorded | 50 | 8 | Feature vector (logistic regression) | not estimable | — | — | — |
| Race not recorded | 50 | 8 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| Age band: 18-29 | 1,085 | 218 | Embedded (logistic regression) | 0.611 (0.568–0.654) | 0.156 | 0.78 | +0.003 |
| Age band: 18-29 | 1,085 | 218 | Feature vector (logistic regression) | 0.570 (0.524–0.615) | 0.160 | 0.60 | +0.012 |
| Age band: 18-29 | 1,085 | 218 | Neighbor-weighted (nearest, cosine) | 0.546 (0.503–0.589) | 0.162 | 0.36 | -0.004 |
| Age band: 30-44 | 1,827 | 372 | Embedded (logistic regression) | 0.653 (0.621–0.682) | 0.154 | 0.95 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | Feature vector (logistic regression) | 0.636 (0.605–0.667) | 0.155 | 1.00 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | Neighbor-weighted (nearest, cosine) | 0.598 (0.566–0.629) | 0.159 | 0.64 | -0.017 |
| Age band: 45-64 | 2,636 | 473 | Embedded (logistic regression) | 0.652 (0.623–0.679) | 0.140 | 0.98 | +0.007 |
| Age band: 45-64 | 2,636 | 473 | Feature vector (logistic regression) | 0.607 (0.580–0.636) | 0.143 | 0.88 | -0.001 |
| Age band: 45-64 | 2,636 | 473 | Neighbor-weighted (nearest, cosine) | 0.592 (0.564–0.622) | 0.145 | 0.62 | -0.005 |
| Age band: 65+ | 2,968 | 428 | Embedded (logistic regression) | 0.658 (0.630–0.682) | 0.117 | 1.10 | -0.005 |
| Age band: 65+ | 2,968 | 428 | Feature vector (logistic regression) | 0.641 (0.614–0.669) | 0.119 | 1.18 | -0.003 |
| Age band: 65+ | 2,968 | 428 | Neighbor-weighted (nearest, cosine) | 0.576 (0.546–0.608) | 0.122 | 0.40 | -0.005 |
| Marital status: Divorced | 882 | 211 | Embedded (logistic regression) | 0.640 (0.593–0.681) | 0.173 | 0.90 | -0.046 |
| Marital status: Divorced | 882 | 211 | Feature vector (logistic regression) | 0.607 (0.563–0.649) | 0.177 | 0.85 | -0.049 |
| Marital status: Divorced | 882 | 211 | Neighbor-weighted (nearest, cosine) | 0.589 (0.542–0.631) | 0.181 | 0.39 | -0.065 |
| Marital status: Never Married | 2,364 | 438 | Embedded (logistic regression) | 0.634 (0.609–0.661) | 0.145 | 0.85 | +0.013 |
| Marital status: Never Married | 2,364 | 438 | Feature vector (logistic regression) | 0.598 (0.569–0.627) | 0.149 | 0.72 | +0.016 |
| Marital status: Never Married | 2,364 | 438 | Neighbor-weighted (nearest, cosine) | 0.572 (0.543–0.602) | 0.151 | 0.47 | +0.001 |
| Marital status: Now Married | 4,251 | 694 | Embedded (logistic regression) | 0.670 (0.650–0.690) | 0.129 | 1.05 | -0.001 |
| Marital status: Now Married | 4,251 | 694 | Feature vector (logistic regression) | 0.644 (0.623–0.666) | 0.131 | 1.10 | -0.002 |
| Marital status: Now Married | 4,251 | 694 | Neighbor-weighted (nearest, cosine) | 0.606 (0.583–0.631) | 0.134 | 0.67 | -0.002 |
| Marital status: Separated | 99 | 21 | Embedded (logistic regression) | 0.518 (0.364–0.673) | 0.171 | 0.08 | +0.001 |
| Marital status: Separated | 99 | 21 | Feature vector (logistic regression) | 0.518 (0.357–0.687) | 0.169 | 0.30 | -0.003 |
| Marital status: Separated | 99 | 21 | Neighbor-weighted (nearest, cosine) | 0.565 (0.407–0.723) | 0.164 | 0.44 | -0.007 |
| Marital status: Widowed | 891 | 120 | Embedded (logistic regression) | 0.654 (0.597–0.708) | 0.111 | 1.09 | +0.022 |
| Marital status: Widowed | 891 | 120 | Feature vector (logistic regression) | 0.625 (0.572–0.678) | 0.112 | 1.17 | +0.017 |
| Marital status: Widowed | 891 | 120 | Neighbor-weighted (nearest, cosine) | 0.554 (0.492–0.606) | 0.117 | 0.33 | +0.006 |
| Smoking status: Current Smoker | 1,126 | 243 | Embedded (logistic regression) | 0.667 (0.631–0.706) | 0.158 | 1.01 | -0.009 |
| Smoking status: Current Smoker | 1,126 | 243 | Feature vector (logistic regression) | 0.617 (0.575–0.660) | 0.162 | 0.87 | -0.011 |
| Smoking status: Current Smoker | 1,126 | 243 | Neighbor-weighted (nearest, cosine) | 0.613 (0.573–0.652) | 0.164 | 0.75 | -0.020 |
| Smoking status: Former Smoker | 2,532 | 443 | Embedded (logistic regression) | 0.663 (0.636–0.690) | 0.137 | 0.98 | +0.003 |
| Smoking status: Former Smoker | 2,532 | 443 | Feature vector (logistic regression) | 0.633 (0.603–0.660) | 0.140 | 0.89 | +0.001 |
| Smoking status: Former Smoker | 2,532 | 443 | Neighbor-weighted (nearest, cosine) | 0.578 (0.547–0.607) | 0.143 | 0.50 | -0.010 |
| Smoking status: Never Smoker | 4,788 | 793 | Embedded (logistic regression) | 0.646 (0.623–0.665) | 0.132 | 0.93 | +0.001 |
| Smoking status: Never Smoker | 4,788 | 793 | Feature vector (logistic regression) | 0.625 (0.603–0.645) | 0.133 | 0.99 | +0.002 |
| Smoking status: Never Smoker | 4,788 | 793 | Neighbor-weighted (nearest, cosine) | 0.589 (0.566–0.610) | 0.136 | 0.51 | -0.003 |
| Religion: Catholic | 608 | 93 | Embedded (logistic regression) | 0.695 (0.634–0.754) | 0.120 | 1.29 | +0.009 |
| Religion: Catholic | 608 | 93 | Feature vector (logistic regression) | 0.648 (0.587–0.710) | 0.124 | 1.06 | +0.002 |
| Religion: Catholic | 608 | 93 | Neighbor-weighted (nearest, cosine) | 0.611 (0.547–0.676) | 0.126 | 0.75 | +0.009 |
| Religion: Non-Christian | 50 | 16 | Embedded (logistic regression) | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | Feature vector (logistic regression) | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Embedded (logistic regression) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Feature vector (logistic regression) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| Religion: Other/Unknown | 759 | 145 | Embedded (logistic regression) | 0.615 (0.565–0.664) | 0.151 | 0.72 | -0.013 |
| Religion: Other/Unknown | 759 | 145 | Feature vector (logistic regression) | 0.589 (0.537–0.642) | 0.153 | 0.66 | -0.010 |
| Religion: Other/Unknown | 759 | 145 | Neighbor-weighted (nearest, cosine) | 0.549 (0.499–0.602) | 0.154 | 0.39 | -0.016 |
| Religion: Protestant | 4,654 | 793 | Embedded (logistic regression) | 0.665 (0.644–0.685) | 0.134 | 1.00 | +0.003 |
| Religion: Protestant | 4,654 | 793 | Feature vector (logistic regression) | 0.642 (0.620–0.662) | 0.135 | 1.05 | +0.002 |
| Religion: Protestant | 4,654 | 793 | Neighbor-weighted (nearest, cosine) | 0.599 (0.577–0.622) | 0.139 | 0.60 | -0.007 |

## S7.3 Clinical strata

***Table S7.** Discrimination and calibration by recorded depression
phenotype, one representative model per arm.*

| Group | n | TRD+ | Arm | ROC AUC (95% CI) | Brier | Calibration slope | Calibration-in-the-large |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| MDD severity: Mild | 633 | 105 | Embedded (logistic regression) | 0.683 (0.624–0.742) | 0.130 | 1.39 | -0.020 |
| MDD severity: Mild | 633 | 105 | Feature vector (logistic regression) | 0.607 (0.547–0.667) | 0.135 | 0.86 | -0.018 |
| MDD severity: Mild | 633 | 105 | Neighbor-weighted (nearest, cosine) | 0.531 (0.475–0.594) | 0.140 | 0.28 | -0.020 |
| MDD severity: Moderate | 1,426 | 255 | Embedded (logistic regression) | 0.652 (0.618–0.687) | 0.142 | 0.98 | +0.003 |
| MDD severity: Moderate | 1,426 | 255 | Feature vector (logistic regression) | 0.634 (0.599–0.670) | 0.142 | 1.06 | +0.001 |
| MDD severity: Moderate | 1,426 | 255 | Neighbor-weighted (nearest, cosine) | 0.587 (0.548–0.624) | 0.146 | 0.58 | -0.003 |
| MDD severity: Psychotic | 18 | 8 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| MDD severity: Severe | 468 | 137 | Embedded (logistic regression) | 0.700 (0.648–0.749) | 0.187 | 1.21 | +0.029 |
| MDD severity: Severe | 468 | 137 | Feature vector (logistic regression) | 0.636 (0.578–0.690) | 0.197 | 0.88 | +0.029 |
| MDD severity: Severe | 468 | 137 | Neighbor-weighted (nearest, cosine) | 0.665 (0.611–0.718) | 0.194 | 1.10 | +0.012 |
| MDD severity: Unspecified | 5,828 | 967 | Embedded (logistic regression) | 0.641 (0.621–0.660) | 0.133 | 0.94 | -0.000 |
| MDD severity: Unspecified | 5,828 | 967 | Feature vector (logistic regression) | 0.615 (0.595–0.634) | 0.134 | 0.98 | -0.001 |
| MDD severity: Unspecified | 5,828 | 967 | Neighbor-weighted (nearest, cosine) | 0.578 (0.559–0.598) | 0.137 | 0.45 | -0.008 |
| MDD recurrence: (unrecorded) | 32 | 7 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD recurrence: (unrecorded) | 32 | 7 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD recurrence: (unrecorded) | 32 | 7 | Neighbor-weighted (nearest, cosine) | not estimable | — | — | — |
| MDD recurrence: Dysthymia | 584 | 97 | Embedded (logistic regression) | 0.690 (0.638–0.748) | 0.130 | 1.33 | +0.008 |
| MDD recurrence: Dysthymia | 584 | 97 | Feature vector (logistic regression) | 0.627 (0.565–0.687) | 0.134 | 1.13 | +0.010 |
| MDD recurrence: Dysthymia | 584 | 97 | Neighbor-weighted (nearest, cosine) | 0.592 (0.531–0.655) | 0.136 | 0.74 | +0.002 |
| MDD recurrence: Recurrent | 2,177 | 433 | Embedded (logistic regression) | 0.698 (0.671–0.726) | 0.146 | 1.09 | -0.000 |
| MDD recurrence: Recurrent | 2,177 | 433 | Feature vector (logistic regression) | 0.676 (0.648–0.703) | 0.148 | 1.07 | -0.002 |
| MDD recurrence: Recurrent | 2,177 | 433 | Neighbor-weighted (nearest, cosine) | 0.645 (0.616–0.674) | 0.152 | 0.82 | -0.005 |
| MDD recurrence: Single Episode | 5,723 | 954 | Embedded (logistic regression) | 0.633 (0.612–0.652) | 0.134 | 0.86 | +0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | Feature vector (logistic regression) | 0.605 (0.584–0.626) | 0.136 | 0.83 | -0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | Neighbor-weighted (nearest, cosine) | 0.565 (0.545–0.585) | 0.139 | 0.36 | -0.009 |

## S7.4 What survives correction

Fifty-eight of the 240 contrasts exclude zero unadjusted, and **24 survive
Benjamini-Hochberg adjustment**. They are not the ones the analysis was
commissioned to look for.

***Table S8.** Contrasts surviving Benjamini-Hochberg adjustment across all
240 reported comparisons, grouped by contrast and arm. "Models surviving"
counts how many of that arm's contrasted models cleared the threshold, out of
four for the two classifier arms and two for the neighbor-weighted arm.*

| Contrast | Arm | Models surviving | ΔROC AUC range | smallest p (BH) |
| --- | --- | ---: | ---: | ---: |
| Age: 18-29 vs rest | Feature vector | 1 of 4 | -0.068 | 0.0400 |
| Marital status: Never Married vs rest | Embedded | 2 of 4 | -0.054 to -0.051 | 0.0133 |
| MDD recurrence: Recurrent vs rest | Embedded | 4 of 4 | +0.059 to +0.072 | 0.0133 |
| MDD recurrence: Recurrent vs rest | Feature vector | 4 of 4 | +0.060 to +0.068 | 0.0133 |
| MDD recurrence: Recurrent vs rest | Neighbor-weighted | 2 of 2 | +0.076 | 0.0133 |
| MDD recurrence: Single Episode vs rest | Embedded | 4 of 4 | -0.071 to -0.065 | 0.0133 |
| MDD recurrence: Single Episode vs rest | Feature vector | 3 of 4 | -0.064 to -0.056 | 0.0253 |
| MDD recurrence: Single Episode vs rest | Neighbor-weighted | 2 of 2 | -0.074 to -0.073 | 0.0133 |
| MDD severity: Severe vs rest | Neighbor-weighted | 2 of 2 | +0.087 | 0.0400 |

**Sex: no difference anywhere.** All ten male-minus-female contrasts include
zero, across every arm and model, and the largest absolute difference is 0.012
ROC AUC. Nothing here needs qualification.

**Race: consistent in direction, not significant after correction.** All ten
White-minus-non-White contrasts are positive, from +0.005 to +0.053 ROC AUC,
and five exclude zero unadjusted, including both neighbor-weighted
configurations, which is a structurally different predictor reproducing the
same sign. None survives adjustment, and the smallest adjusted *P* is .11.
Calibration moves the same way in the feature-vector arm, where the slope among
non-White patients is 0.79 against 0.98 among White patients, while the
embedded arm holds at 0.95 against 0.97.

The correct reading is neither "no difference" nor "a gap of 0.04". This cohort
lacks the power to settle it. The minority stratum carries 302 outcome events
against 1,181, so its intervals are roughly twice as wide, and a real
difference of the size observed could as easily have gone undetected. What the
data do show is a sign that is consistent across ten contrasts and three
independent predictor families, which is not the shape sampling noise usually
takes, and a calibration deficit concentrated in one representation. Both are
reported for that reason, and neither is claimed as established.

**What does survive is how the depression is coded.** Twenty-one of the 24
surviving contrasts concern MDD recurrence and severity. Discrimination is
higher among patients coded with recurrent MDD (+0.059 to +0.076 against the
rest) and lower among those coded single-episode (-0.074 to -0.056), in every
arm. Severity behaves the same way in the neighbor-weighted arm, where
discrimination is higher among patients coded severe (+0.087). The pattern is coherent and is as much about documentation as about phenotype.
The models discriminate better where the diagnosis is recorded specifically and
worse where the coding is left unspecified, which is the majority of this
cohort. Of the 8,516 held-out patients, 5,828 are coded unspecified severity.

**Two sociodemographic contrasts survive**, and both point the same way as the
documentation story. Discrimination is lower among patients aged 18-29 than
among the rest in the feature-vector arm (-0.068 under XGBoost, adjusted *P* =
.04). It is lower among never-married patients in the embedded arm, where two
of the four classifiers survive, at -0.054 and -0.051 (adjusted *P* = .01). Younger and never-married patients accumulate
less recorded history, which is consistent with thinner records supporting
weaker prediction, though this analysis cannot separate that explanation from
any other.

![](../results/review/subgroups/subgroup_forest.png){width=6in}

***Figure S4.** Subgroup discrimination across sociodemographic strata, one
representative model per arm, with 95% bootstrap confidence intervals. The
dotted line marks chance. Strata declared not estimable are omitted.*
