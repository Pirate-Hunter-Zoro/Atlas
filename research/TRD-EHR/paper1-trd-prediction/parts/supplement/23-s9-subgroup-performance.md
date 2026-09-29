<!--
Section 23 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S9 Subgroup Performance
-->

# S9 Subgroup Performance

Subgroup analyses address performance differences, a question distinct from direct-input reliance under permutation. They do not establish fairness of the outcome label or of a proposed clinical decision.

## S9 1 Design

Held-out predicted probabilities were partitioned by subgroup without refitting models. Discrimination and calibration were recalculated within each group.

The analysis included 4 FEATURE classifiers, 4 EMBEDDED classifiers, and 4 neighbor configurations: nearest retrieval under plain cosine similarity (k = 50) and under importance-weighted similarity (best k, 295), and the random and farthest controls. Between-group contrasts included the 2 nearest-neighbor configurations and excluded the controls.

Strata comprised sex, recorded race, age, marital status, smoking, religion, MDD recurrence, and severity. Race was aggregated as White versus other recorded categories because of small subgroup counts; this masks potentially important heterogeneity. Preferred language was not contrasted because 98.9% preferred English. A subgroup was treated as not estimable when its smaller outcome class contained fewer than 20 patients.

Within-group CIs used percentile bootstrap resampling. Contrasts between disjoint groups used independent resampling of each group. Two-sided bootstrap P values were adjusted across 240 contrasts with the Benjamini--Hochberg procedure.

The individual-level calibration slope was estimated by logistic regression of outcome on logit predicted risk. Mean predicted risk minus observed outcome frequency was also reported; the original table label "calibration-in-the-large" is retained as "mean risk difference" to identify the quantity actually calculated. This is not a logistic calibration intercept. Both differ from the binned-curve parameters in section S3.

## S9 2 Sociodemographic strata

Table S10. Discrimination and calibration by sociodemographic stratum, one representative model per arm, held-out test set. Groups are not disjoint across families: every patient with a recorded sex appears in one sex row and every patient with a recorded race in one race row.

| **Group** | **n** | **Events** | **Arm** | **ROC AUC (95% CI)** | **Brier** | **Logistic slope** | **Mean risk difference** |
| ------------------------------ | ------: | ------: | ------ | --------------------: | ------: | --------: | ---------: |
| All held-out patients | 8,516 | 1,491 | E LR | 0.657 (0.643--0.672) | 0.137 | 0.97 | +0.000 |
| All held-out patients | 8,516 | 1,491 | F LR | 0.629 (0.613--0.644) | 0.139 | 0.95 | -0.000 |
| All held-out patients | 8,516 | 1,491 | N WTD | 0.625 (0.610--0.641) | 0.140 | 1.15 | -0.004 |
| Male | 2,347 | 386 | E LR | 0.653 (0.622--0.682) | 0.131 | 0.94 | -0.003 |
| Male | 2,347 | 386 | F LR | 0.626 (0.595--0.655) | 0.133 | 0.86 | -0.003 |
| Male | 2,347 | 386 | N WTD | 0.625 (0.595--0.653) | 0.133 | 1.04 | -0.001 |
| Female | 6,168 | 1,105 | E LR | 0.658 (0.641--0.675) | 0.139 | 0.98 | +0.002 |
| Female | 6,168 | 1,105 | F LR | 0.630 (0.612--0.648) | 0.141 | 0.99 | +0.001 |
| Female | 6,168 | 1,105 | N WTD | 0.624 (0.607--0.642) | 0.142 | 1.20 | -0.005 |
| White/Caucasian | 6,835 | 1,181 | E LR | 0.657 (0.640--0.674) | 0.136 | 0.97 | +0.002 |
| White/Caucasian | 6,835 | 1,181 | F LR | 0.633 (0.615--0.652) | 0.137 | 0.98 | +0.001 |
| White/Caucasian | 6,835 | 1,181 | N WTD | 0.633 (0.615--0.650) | 0.138 | 1.22 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | E LR | 0.652 (0.620--0.684) | 0.144 | 0.95 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | F LR | 0.608 (0.573--0.643) | 0.147 | 0.79 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | N WTD | 0.587 (0.553--0.620) | 0.148 | 0.85 | -0.004 |
| Race not recorded | 50 | 8 | E LR | not estimable | — | — | — |
| Race not recorded | 50 | 8 | F LR | not estimable | — | — | — |
| Race not recorded | 50 | 8 | N WTD | not estimable | — | — | — |
| Age band: 18-29 | 1,085 | 218 | E LR | 0.611 (0.568--0.654) | 0.156 | 0.78 | +0.003 |
| Age band: 18-29 | 1,085 | 218 | F LR | 0.570 (0.524--0.615) | 0.160 | 0.60 | +0.012 |
| Age band: 18-29 | 1,085 | 218 | N WTD | 0.578 (0.535--0.620) | 0.158 | 0.81 | -0.007 |
| Age band: 30-44 | 1,827 | 372 | E LR | 0.653 (0.621--0.682) | 0.154 | 0.95 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | F LR | 0.636 (0.605--0.667) | 0.155 | 1.00 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | N WTD | 0.610 (0.578--0.642) | 0.158 | 1.08 | -0.015 |
| Age band: 45-64 | 2,636 | 473 | E LR | 0.652 (0.623--0.679) | 0.140 | 0.98 | +0.007 |
| Age band: 45-64 | 2,636 | 473 | F LR | 0.607 (0.580--0.636) | 0.143 | 0.88 | -0.001 |
| Age band: 45-64 | 2,636 | 473 | N WTD | 0.624 (0.594--0.651) | 0.142 | 1.16 | -0.002 |
| Age band: 65+ | 2,968 | 428 | E LR | 0.658 (0.630--0.682) | 0.117 | 1.10 | -0.005 |
| Age band: 65+ | 2,968 | 428 | F LR | 0.641 (0.614--0.669) | 0.119 | 1.18 | -0.003 |
| Age band: 65+ | 2,968 | 428 | N WTD | 0.624 (0.595--0.651) | 0.119 | 1.28 | +0.003 |
| Marital status: Divorced | 882 | 211 | E LR | 0.640 (0.593--0.681) | 0.173 | 0.90 | -0.046 |
| Marital status: Divorced | 882 | 211 | F LR | 0.607 (0.563--0.649) | 0.177 | 0.85 | -0.049 |
| Marital status: Divorced | 882 | 211 | N WTD | 0.607 (0.561--0.646) | 0.179 | 1.07 | -0.061 |
| Marital status: Never Married | 2,364 | 438 | E LR | 0.634 (0.609--0.661) | 0.145 | 0.85 | +0.013 |
| Marital status: Never Married | 2,364 | 438 | F LR | 0.598 (0.569--0.627) | 0.149 | 0.72 | +0.016 |
| Marital status: Never Married | 2,364 | 438 | N WTD | 0.590 (0.562--0.619) | 0.149 | 0.85 | +0.002 |
| Marital status: Now Married | 4,251 | 694 | E LR | 0.670 (0.650--0.690) | 0.129 | 1.05 | -0.001 |
| Marital status: Now Married | 4,251 | 694 | F LR | 0.644 (0.623--0.666) | 0.131 | 1.10 | -0.002 |
| Marital status: Now Married | 4,251 | 694 | N WTD | 0.640 (0.619--0.663) | 0.131 | 1.31 | +0.002 |
| Marital status: Separated | 99 | 21 | E LR | 0.518 (0.364--0.673) | 0.171 | 0.08 | +0.001 |
| Marital status: Separated | 99 | 21 | F LR | 0.518 (0.357--0.687) | 0.169 | 0.30 | -0.003 |
| Marital status: Separated | 99 | 21 | N WTD | 0.581 (0.418--0.741) | 0.162 | 0.73 | -0.018 |
| Marital status: Widowed | 891 | 120 | E LR | 0.654 (0.597--0.708) | 0.111 | 1.09 | +0.022 |
| Marital status: Widowed | 891 | 120 | F LR | 0.625 (0.572--0.678) | 0.112 | 1.17 | +0.017 |
| Marital status: Widowed | 891 | 120 | N WTD | 0.623 (0.565--0.678) | 0.113 | 1.22 | +0.015 |
| Smoking status: Current Smoker | 1,126 | 243 | E LR | 0.667 (0.631--0.706) | 0.158 | 1.01 | -0.009 |
| Smoking status: Current Smoker | 1,126 | 243 | F LR | 0.617 (0.575--0.660) | 0.162 | 0.87 | -0.011 |
| Smoking status: Current Smoker | 1,126 | 243 | N WTD | 0.609 (0.569--0.649) | 0.163 | 1.12 | -0.020 |
| Smoking status: Former Smoker | 2,532 | 443 | E LR | 0.663 (0.636--0.690) | 0.137 | 0.98 | +0.003 |
| Smoking status: Former Smoker | 2,532 | 443 | F LR | 0.633 (0.603--0.660) | 0.140 | 0.89 | +0.001 |
| Smoking status: Former Smoker | 2,532 | 443 | N WTD | 0.632 (0.603--0.659) | 0.139 | 1.16 | -0.005 |
| Smoking status: Never Smoker | 4,788 | 793 | E LR | 0.646 (0.623--0.665) | 0.132 | 0.93 | +0.001 |
| Smoking status: Never Smoker | 4,788 | 793 | F LR | 0.625 (0.603--0.645) | 0.133 | 0.99 | +0.002 |
| Smoking status: Never Smoker | 4,788 | 793 | N WTD | 0.618 (0.596--0.638) | 0.134 | 1.13 | +0.001 |
| Religion: Catholic | 608 | 93 | E LR | 0.695 (0.634--0.754) | 0.120 | 1.29 | +0.009 |
| Religion: Catholic | 608 | 93 | F LR | 0.648 (0.587--0.710) | 0.124 | 1.06 | +0.002 |
| Religion: Catholic | 608 | 93 | N WTD | 0.658 (0.598--0.713) | 0.124 | 1.52 | +0.011 |
| Religion: Non-Christian | 50 | 16 | E LR | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | F LR | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | N WTD | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | E LR | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | F LR | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | N WTD | not estimable | — | — | — |
| Religion: Other/Unknown | 759 | 145 | E LR | 0.615 (0.565--0.664) | 0.151 | 0.72 | -0.013 |
| Religion: Other/Unknown | 759 | 145 | F LR | 0.589 (0.537--0.642) | 0.153 | 0.66 | -0.010 |
| Religion: Other/Unknown | 759 | 145 | N WTD | 0.594 (0.543--0.643) | 0.151 | 0.93 | -0.014 |
| Religion: Protestant | 4,654 | 793 | E LR | 0.665 (0.644--0.685) | 0.134 | 1.00 | +0.003 |
| Religion: Protestant | 4,654 | 793 | F LR | 0.642 (0.620--0.662) | 0.135 | 1.05 | +0.002 |
| Religion: Protestant | 4,654 | 793 | N WTD | 0.632 (0.609--0.653) | 0.136 | 1.19 | -0.003 |

E LR: embedded logistic regression; F LR: feature-vector logistic regression; N WTD: importance-weighted nearest-neighbor prediction (k = 295). Events denotes positive TRD proxy outcomes. Mean risk difference is mean predicted probability minus observed frequency.

## S9 3 Clinical strata

Table S11. Discrimination and calibration by recorded depression phenotype, one representative model per arm.

| **Group** | **n** | **Events** | **Arm** | **ROC AUC (95% CI)** | **Brier** | **Logistic slope** | **Mean risk difference** |
| ------------------------------ | ------: | ------: | ------ | --------------------: | ------: | --------: | ---------: |
| MDD severity: Mild | 633 | 105 | E LR | 0.683 (0.624--0.742) | 0.130 | 1.39 | -0.020 |
| MDD severity: Mild | 633 | 105 | F LR | 0.607 (0.547--0.667) | 0.135 | 0.86 | -0.018 |
| MDD severity: Mild | 633 | 105 | N WTD | 0.607 (0.547--0.668) | 0.137 | 1.30 | -0.020 |
| MDD severity: Moderate | 1,426 | 255 | E LR | 0.652 (0.618--0.687) | 0.142 | 0.98 | +0.003 |
| MDD severity: Moderate | 1,426 | 255 | F LR | 0.634 (0.599--0.670) | 0.142 | 1.06 | +0.001 |
| MDD severity: Moderate | 1,426 | 255 | N WTD | 0.631 (0.593--0.666) | 0.143 | 1.58 | -0.005 |
| MDD severity: Psychotic | 18 | 8 | E LR | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | F LR | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | N WTD | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | E LR | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | F LR | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | N WTD | not estimable | — | — | — |
| MDD severity: Severe | 468 | 137 | E LR | 0.700 (0.648--0.749) | 0.187 | 1.21 | +0.029 |
| MDD severity: Severe | 468 | 137 | F LR | 0.636 (0.578--0.690) | 0.197 | 0.88 | +0.029 |
| MDD severity: Severe | 468 | 137 | N WTD | 0.678 (0.622--0.730) | 0.193 | 1.86 | +0.014 |
| MDD severity: Unspecified | 5,828 | 967 | E LR | 0.641 (0.621--0.660) | 0.133 | 0.94 | -0.000 |
| MDD severity: Unspecified | 5,828 | 967 | F LR | 0.615 (0.595--0.634) | 0.134 | 0.98 | -0.001 |
| MDD severity: Unspecified | 5,828 | 967 | N WTD | 0.609 (0.590--0.628) | 0.135 | 1.14 | -0.003 |
| MDD recurrence: | 32 | 7 | E LR | not estimable | — | — | — |
| MDD recurrence: | 32 | 7 | F LR | not estimable | — | — | — |
| MDD recurrence: | 32 | 7 | N WTD | not estimable | — | — | — |
| MDD recurrence: Dysthymia | 584 | 97 | E LR | 0.690 (0.638--0.748) | 0.130 | 1.33 | +0.008 |
| MDD recurrence: Dysthymia | 584 | 97 | F LR | 0.627 (0.565--0.687) | 0.134 | 1.13 | +0.010 |
| MDD recurrence: Dysthymia | 584 | 97 | N WTD | 0.628 (0.567--0.688) | 0.135 | 2.22 | +0.003 |
| MDD recurrence: Recurrent | 2,177 | 433 | E LR | 0.698 (0.671--0.726) | 0.146 | 1.09 | -0.000 |
| MDD recurrence: Recurrent | 2,177 | 433 | F LR | 0.676 (0.648--0.703) | 0.148 | 1.07 | -0.002 |
| MDD recurrence: Recurrent | 2,177 | 433 | N WTD | 0.666 (0.639--0.693) | 0.150 | 1.26 | -0.005 |
| MDD recurrence: Single Episode | 5,723 | 954 | E LR | 0.633 (0.612--0.652) | 0.134 | 0.86 | +0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | F LR | 0.605 (0.584--0.626) | 0.136 | 0.83 | -0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | N WTD | 0.603 (0.584--0.623) | 0.136 | 1.03 | -0.004 |

E LR: embedded logistic regression; F LR: feature-vector logistic regression; N WTD: importance-weighted nearest-neighbor prediction (k = 295). Events denotes positive TRD proxy outcomes. Mean risk difference is mean predicted probability minus observed frequency.

## S9 4 Adjusted Subgroup Comparisons

Of 240 contrasts, 60 had unadjusted CIs excluding zero and 24 survived Benjamini--Hochberg adjustment (Table S12).

Table S12. Contrasts surviving Benjamini-Hochberg adjustment across all 240 reported comparisons, grouped by contrast and arm. "Models surviving" counts how many of that arm's contrasted models cleared the threshold.

| **Contrast** | **Arm** | **Models surviving** | **ΔROC AUC range** | **Smallest P (BH)** |
| -------------------------------------- | ----------------- | --------- | ---------------- | --------- |
| Age: 18-29 vs rest | Feature vector | 1 of 4 | -0.068 | 0.040 |
| MDD recurrence: Recurrent vs rest | Embedded | 4 of 4 | +0.059 to +0.072 | 0.014 |
| MDD recurrence: Recurrent vs rest | Feature vector | 4 of 4 | +0.060 to +0.068 | 0.014 |
| MDD recurrence: Recurrent vs rest | Nearest neighbors | 2 of 2 | +0.060 to +0.076 | 0.014 |
| MDD recurrence: Single Episode vs rest | Embedded | 4 of 4 | -0.071 to -0.065 | 0.014 |
| MDD recurrence: Single Episode vs rest | Feature vector | 3 of 4 | -0.064 to -0.056 | 0.025 |
| MDD recurrence: Single Episode vs rest | Nearest neighbors | 2 of 2 | -0.074 to -0.058 | 0.014 |
| MDD severity: Severe vs rest | Nearest neighbors | 1 of 2 | +0.087 | 0.040 |
| Marital status: Never Married vs rest | Embedded | 2 of 4 | -0.054 to -0.051 | 0.014 |
| Marital status: Never Married vs rest | Nearest neighbors | 1 of 2 | -0.047 | 0.040 |

All 10 male-minus-female AUC contrasts included zero; the largest absolute point difference was 0.012. This does not establish equivalent performance.

All 10 White-minus-non-White AUC contrasts were positive (0.005--0.052); 5 excluded zero before adjustment, but none survived adjustment (minimum adjusted P=.11). For FEATURE logistic regression, calibration slopes were 0.98 in White patients and 0.79 in patients with other recorded racial categories.

The other-recorded-race stratum had 302 events, compared with 1,181 among White patients, and wider CIs. The direction is consistent across related models, but these are correlated comparisons rather than independent replications. The data leave racial differences unresolved.

Nineteen of the 24 adjusted contrasts involved recurrence. Recurrent coding was associated with higher discrimination in all 10 contrasted models (differences 0.059--0.076), and single-episode coding with lower discrimination (−0.074 to −0.054), which survived adjustment in 9. In plain-cosine nearest-neighbor prediction, severe coding was associated with higher discrimination (+0.087; adjusted P=.04).

The remaining 4 adjusted contrasts indicated lower discrimination among never-married patients in 2 EMBEDDED classifiers (−0.054 to −0.051; minimum adjusted P=.014) and in importance-weighted retrieval (−0.047; adjusted P=.04), and at ages 18--29 in FEATURE XGBoost (−0.068; adjusted P=.04). Their causes were not established.

![](../results/review/subgroups/subgroup_forest.png){width=5.6in}

Figure S11. Subgroup discrimination across sociodemographic strata, one representative model per arm, with 95% bootstrap confidence intervals. The dotted line marks chance. Strata declared not estimable are omitted.
