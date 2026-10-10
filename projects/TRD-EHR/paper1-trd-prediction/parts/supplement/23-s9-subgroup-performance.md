<!--
Section 23 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S9 Subgroup Performance
-->

# S9 Subgroup Performance

Subgroup analyses address performance differences, a question distinct from direct-input reliance under permutation. They do not establish fairness of the outcome label or of a proposed clinical decision.

## S9.1 Design

Held-out predicted probabilities were partitioned by subgroup without refitting models. Discrimination and calibration were recalculated within each group.

The analysis included 4 FEATURE classifiers, 4 EMBEDDED classifiers, and 3 neighbor configurations for Qwen3-Embedding-8B, each at its own best k from section S6: nearest retrieval under plain cosine similarity (k = 757) and under logistic-regression-weighted similarity (k = 295), and uniform random retrieval (k = 32,720) as a control. Between-group contrasts included the 2 nearest-neighbor configurations and excluded the control. The best k was chosen on all test patients, not within each subgroup.

Strata comprised sex, recorded race, age, marital status, smoking, religion, MDD recurrence, and severity. Race was aggregated as White versus other recorded categories because of small subgroup counts; this masks potentially important heterogeneity. Preferred language was not contrasted because 98.9% (95% CI 98.7--99.1) of held-out patients preferred English. A subgroup was treated as not estimable when its smaller outcome class contained fewer than 20 patients.

Within-group CIs used percentile bootstrap resampling, and every within-group metric (ROC AUC, Brier score, logistic slope, mean risk difference) carries one, cut from the same resamples. Contrasts between disjoint groups used independent resampling of each group. Two-sided bootstrap P values were adjusted across 240 contrasts with the Benjamini--Hochberg procedure.

The individual-level calibration slope was estimated by logistic regression of outcome on logit predicted risk. Mean predicted risk minus observed outcome frequency was also reported, labeled "mean risk difference" rather than "calibration-in-the-large" to identify the quantity actually calculated. This is not a logistic calibration intercept. Both differ from the binned-curve parameters in section S3.

## S9.2 Sociodemographic strata

Table S10 gives discrimination and calibration within each sociodemographic stratum, and Figure S13 plots the discrimination.

Table S10. Discrimination and calibration by sociodemographic stratum, one representative model per arm (embedded logistic regression, feature-vector XGBoost, and logistic-regression-weighted retrieval at k = 295, the leading model of each), Qwen3-Embedding-8B, held-out test set. Groups are not disjoint across families: every patient with a recorded sex appears in one sex row and every patient with a recorded race in one race row.

| **Group** | **n** | **Events** | **Arm** | **ROC AUC (95% CI)** | **Brier (95% CI)** | **Logistic slope (95% CI)** | **Mean risk difference (95% CI)** |
| -------------------- | ---------: | -----------: | -------- | ---------------- | ---------------- | -------------- | ------------------ |
| All held-out patients | 8,516 | 1,491 | E LR | 0.657 (0.643--0.672) | 0.137 (0.132--0.142) | 0.97 (0.88--1.06) | +0.000 (−0.007 to +0.008) |
| All held-out patients | 8,516 | 1,491 | F XGB | 0.649 (0.634--0.664) | 0.138 (0.132--0.143) | 1.25 (1.13--1.37) | +0.000 (−0.008 to +0.008) |
| All held-out patients | 8,516 | 1,491 | N WTD | 0.625 (0.610--0.641) | 0.140 (0.134--0.145) | 1.15 (1.01--1.29) | −0.004 (−0.012 to +0.005) |
| Male | 2,347 | 386 | E LR | 0.653 (0.622--0.682) | 0.131 (0.121--0.140) | 0.94 (0.76--1.13) | −0.003 (−0.017 to +0.012) |
| Male | 2,347 | 386 | F XGB | 0.654 (0.624--0.683) | 0.131 (0.122--0.140) | 1.18 (0.96--1.42) | +0.006 (−0.007 to +0.021) |
| Male | 2,347 | 386 | N WTD | 0.625 (0.595--0.653) | 0.133 (0.124--0.142) | 1.04 (0.78--1.28) | −0.001 (−0.014 to +0.013) |
| Female | 6,168 | 1,105 | E LR | 0.658 (0.641--0.675) | 0.139 (0.134--0.145) | 0.98 (0.87--1.09) | +0.002 (−0.007 to +0.011) |
| Female | 6,168 | 1,105 | F XGB | 0.647 (0.630--0.664) | 0.140 (0.134--0.146) | 1.27 (1.14--1.42) | −0.002 (−0.011 to +0.007) |
| Female | 6,168 | 1,105 | N WTD | 0.624 (0.607--0.642) | 0.142 (0.136--0.148) | 1.20 (1.04--1.37) | −0.005 (−0.013 to +0.004) |
| White/Caucasian | 6,835 | 1,181 | E LR | 0.657 (0.640--0.674) | 0.136 (0.130--0.141) | 0.97 (0.87--1.08) | +0.002 (−0.007 to +0.010) |
| White/Caucasian | 6,835 | 1,181 | F XGB | 0.656 (0.639--0.673) | 0.136 (0.130--0.141) | 1.28 (1.14--1.44) | −0.000 (−0.009 to +0.008) |
| White/Caucasian | 6,835 | 1,181 | N WTD | 0.633 (0.615--0.650) | 0.138 (0.132--0.143) | 1.22 (1.06--1.38) | −0.004 (−0.013 to +0.005) |
| Non-White (recorded) | 1,631 | 302 | E LR | 0.652 (0.620--0.684) | 0.144 (0.133--0.155) | 0.95 (0.74--1.16) | −0.004 (−0.023 to +0.013) |
| Non-White (recorded) | 1,631 | 302 | F XGB | 0.616 (0.579--0.650) | 0.146 (0.136--0.158) | 1.07 (0.75--1.36) | +0.000 (−0.019 to +0.017) |
| Non-White (recorded) | 1,631 | 302 | N WTD | 0.587 (0.553--0.620) | 0.148 (0.138--0.161) | 0.85 (0.53--1.15) | −0.004 (−0.024 to +0.013) |
| Race not recorded | 50 | 8 | E LR | not estimable | — | — | — |
| Race not recorded | 50 | 8 | F XGB | not estimable | — | — | — |
| Race not recorded | 50 | 8 | N WTD | not estimable | — | — | — |
| Age band: 18-29 | 1,085 | 218 | E LR | 0.611 (0.568--0.654) | 0.156 (0.142--0.171) | 0.78 (0.49--1.07) | +0.003 (−0.022 to +0.026) |
| Age band: 18-29 | 1,085 | 218 | F XGB | 0.588 (0.544--0.628) | 0.157 (0.144--0.172) | 0.96 (0.50--1.39) | +0.001 (−0.025 to +0.024) |
| Age band: 18-29 | 1,085 | 218 | N WTD | 0.578 (0.535--0.620) | 0.158 (0.144--0.174) | 0.81 (0.40--1.24) | −0.007 (−0.033 to +0.016) |
| Age band: 30-44 | 1,827 | 372 | E LR | 0.653 (0.621--0.682) | 0.154 (0.144--0.165) | 0.95 (0.76--1.14) | −0.002 (−0.021 to +0.016) |
| Age band: 30-44 | 1,827 | 372 | F XGB | 0.649 (0.617--0.681) | 0.154 (0.144--0.166) | 1.35 (1.08--1.66) | −0.004 (−0.023 to +0.014) |
| Age band: 30-44 | 1,827 | 372 | N WTD | 0.610 (0.578--0.642) | 0.158 (0.147--0.170) | 1.08 (0.78--1.36) | −0.015 (−0.035 to +0.002) |
| Age band: 45-64 | 2,636 | 473 | E LR | 0.652 (0.623--0.679) | 0.140 (0.130--0.148) | 0.98 (0.81--1.15) | +0.007 (−0.006 to +0.022) |
| Age band: 45-64 | 2,636 | 473 | F XGB | 0.642 (0.614--0.671) | 0.140 (0.131--0.149) | 1.24 (1.01--1.48) | +0.005 (−0.008 to +0.020) |
| Age band: 45-64 | 2,636 | 473 | N WTD | 0.624 (0.594--0.651) | 0.142 (0.133--0.151) | 1.16 (0.91--1.42) | −0.002 (−0.015 to +0.013) |
| Age band: 65+ | 2,968 | 428 | E LR | 0.658 (0.630--0.682) | 0.117 (0.108--0.126) | 1.10 (0.92--1.28) | −0.005 (−0.017 to +0.008) |
| Age band: 65+ | 2,968 | 428 | F XGB | 0.660 (0.631--0.687) | 0.118 (0.109--0.126) | 1.42 (1.19--1.66) | −0.002 (−0.015 to +0.011) |
| Age band: 65+ | 2,968 | 428 | N WTD | 0.624 (0.595--0.651) | 0.119 (0.111--0.128) | 1.28 (1.02--1.54) | +0.003 (−0.010 to +0.016) |
| Marital status: Divorced | 882 | 211 | E LR | 0.640 (0.593--0.681) | 0.173 (0.156--0.191) | 0.90 (0.64--1.14) | −0.046 (−0.074 to −0.018) |
| Marital status: Divorced | 882 | 211 | F XGB | 0.633 (0.590--0.673) | 0.175 (0.158--0.193) | 1.12 (0.79--1.45) | −0.053 (−0.082 to −0.026) |
| Marital status: Divorced | 882 | 211 | N WTD | 0.607 (0.561--0.646) | 0.179 (0.161--0.197) | 1.07 (0.69--1.42) | −0.061 (−0.089 to −0.034) |
| Marital status: Never Married | 2,364 | 438 | E LR | 0.634 (0.609--0.661) | 0.145 (0.137--0.155) | 0.85 (0.69--1.02) | +0.013 (−0.003 to +0.028) |
| Marital status: Never Married | 2,364 | 438 | F XGB | 0.620 (0.595--0.649) | 0.146 (0.137--0.156) | 1.12 (0.88--1.37) | +0.011 (−0.005 to +0.026) |
| Marital status: Never Married | 2,364 | 438 | N WTD | 0.590 (0.562--0.619) | 0.149 (0.139--0.159) | 0.85 (0.61--1.12) | +0.002 (−0.014 to +0.016) |
| Marital status: Now Married | 4,251 | 694 | E LR | 0.670 (0.650--0.690) | 0.129 (0.122--0.136) | 1.05 (0.92--1.19) | −0.001 (−0.012 to +0.009) |
| Marital status: Now Married | 4,251 | 694 | F XGB | 0.660 (0.639--0.681) | 0.130 (0.123--0.136) | 1.35 (1.17--1.54) | +0.002 (−0.009 to +0.012) |
| Marital status: Now Married | 4,251 | 694 | N WTD | 0.640 (0.619--0.663) | 0.131 (0.125--0.138) | 1.31 (1.12--1.52) | +0.002 (−0.009 to +0.013) |
| Marital status: Separated | 99 | 21 | E LR | 0.518 (0.364--0.673) | 0.171 (0.123--0.224) | 0.08 (−1.14 to 1.24) | +0.001 (−0.088 to +0.082) |
| Marital status: Separated | 99 | 21 | F XGB | 0.609 (0.442--0.764) | 0.164 (0.115--0.214) | 0.72 (−0.56 to 2.60) | −0.006 (−0.094 to +0.071) |
| Marital status: Separated | 99 | 21 | N WTD | 0.581 (0.418--0.741) | 0.162 (0.112--0.215) | 0.73 (−0.74 to 2.45) | −0.018 (−0.103 to +0.060) |
| Marital status: Widowed | 891 | 120 | E LR | 0.654 (0.597--0.708) | 0.111 (0.097--0.125) | 1.09 (0.73--1.45) | +0.022 (+0.000 to +0.043) |
| Marital status: Widowed | 891 | 120 | F XGB | 0.643 (0.587--0.693) | 0.112 (0.097--0.127) | 1.31 (0.87--1.74) | +0.017 (−0.004 to +0.039) |
| Marital status: Widowed | 891 | 120 | N WTD | 0.623 (0.565--0.678) | 0.113 (0.098--0.128) | 1.22 (0.70--1.76) | +0.015 (−0.007 to +0.038) |
| Smoking status: Current Smoker | 1,126 | 243 | E LR | 0.667 (0.631--0.706) | 0.158 (0.144--0.172) | 1.01 (0.80--1.27) | −0.009 (−0.032 to +0.014) |
| Smoking status: Current Smoker | 1,126 | 243 | F XGB | 0.658 (0.620--0.698) | 0.161 (0.146--0.174) | 1.25 (0.95--1.58) | −0.014 (−0.037 to +0.010) |
| Smoking status: Current Smoker | 1,126 | 243 | N WTD | 0.609 (0.569--0.649) | 0.163 (0.149--0.177) | 1.12 (0.79--1.49) | −0.020 (−0.043 to +0.004) |
| Smoking status: Former Smoker | 2,532 | 443 | E LR | 0.663 (0.636--0.690) | 0.137 (0.128--0.146) | 0.98 (0.82--1.15) | +0.003 (−0.012 to +0.017) |
| Smoking status: Former Smoker | 2,532 | 443 | F XGB | 0.654 (0.627--0.683) | 0.138 (0.128--0.147) | 1.22 (1.00--1.44) | −0.003 (−0.018 to +0.011) |
| Smoking status: Former Smoker | 2,532 | 443 | N WTD | 0.632 (0.603--0.659) | 0.139 (0.130--0.149) | 1.16 (0.92--1.39) | −0.005 (−0.020 to +0.009) |
| Smoking status: Never Smoker | 4,788 | 793 | E LR | 0.646 (0.623--0.665) | 0.132 (0.126--0.139) | 0.93 (0.80--1.05) | +0.001 (−0.009 to +0.011) |
| Smoking status: Never Smoker | 4,788 | 793 | F XGB | 0.639 (0.616--0.660) | 0.132 (0.126--0.139) | 1.26 (1.06--1.44) | +0.005 (−0.005 to +0.015) |
| Smoking status: Never Smoker | 4,788 | 793 | N WTD | 0.618 (0.596--0.638) | 0.134 (0.128--0.141) | 1.13 (0.92--1.30) | +0.001 (−0.009 to +0.011) |
| Religion: Catholic | 608 | 93 | E LR | 0.695 (0.634--0.754) | 0.120 (0.104--0.139) | 1.29 (0.88--1.77) | +0.009 (−0.018 to +0.034) |
| Religion: Catholic | 608 | 93 | F XGB | 0.681 (0.619--0.737) | 0.122 (0.105--0.140) | 1.52 (1.02--2.07) | +0.011 (−0.018 to +0.036) |
| Religion: Catholic | 608 | 93 | N WTD | 0.658 (0.598--0.713) | 0.124 (0.107--0.143) | 1.52 (0.98--2.08) | +0.011 (−0.017 to +0.037) |
| Religion: Non-Christian | 50 | 16 | E LR | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | F XGB | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | N WTD | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | E LR | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | F XGB | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | N WTD | not estimable | — | — | — |
| Religion: Other/Unknown | 759 | 145 | E LR | 0.615 (0.565--0.664) | 0.151 (0.135--0.169) | 0.72 (0.42--1.04) | −0.013 (−0.041 to +0.013) |
| Religion: Other/Unknown | 759 | 145 | F XGB | 0.607 (0.556--0.659) | 0.151 (0.135--0.169) | 0.92 (0.50--1.35) | −0.011 (−0.038 to +0.015) |
| Religion: Other/Unknown | 759 | 145 | N WTD | 0.594 (0.543--0.643) | 0.151 (0.135--0.168) | 0.93 (0.49--1.40) | −0.014 (−0.042 to +0.012) |
| Religion: Protestant | 4,654 | 793 | E LR | 0.665 (0.644--0.685) | 0.134 (0.127--0.140) | 1.00 (0.87--1.13) | +0.003 (−0.007 to +0.013) |
| Religion: Protestant | 4,654 | 793 | F XGB | 0.662 (0.641--0.682) | 0.134 (0.127--0.141) | 1.33 (1.16--1.51) | −0.001 (−0.010 to +0.009) |
| Religion: Protestant | 4,654 | 793 | N WTD | 0.632 (0.609--0.653) | 0.136 (0.130--0.143) | 1.19 (0.99--1.40) | −0.003 (−0.012 to +0.007) |

E LR: embedded logistic regression; F XGB: feature-vector XGBoost; N WTD: logistic-regression-weighted nearest-neighbor prediction (k = 295). Events denotes positive TRD proxy outcomes. Mean risk difference is mean predicted probability minus observed frequency.

## S9.3 Clinical strata

Table S11. Discrimination and calibration by recorded depression phenotype, one representative model per arm (embedded logistic regression, feature-vector XGBoost, and logistic-regression-weighted retrieval at k = 295, the leading model of each), Qwen3-Embedding-8B.

| **Group** | **n** | **Events** | **Arm** | **ROC AUC (95% CI)** | **Brier (95% CI)** | **Logistic slope (95% CI)** | **Mean risk difference (95% CI)** |
| -------------------- | ---------: | -----------: | -------- | ---------------- | ---------------- | -------------- | ------------------ |
| MDD severity: Mild | 633 | 105 | E LR | 0.683 (0.624--0.742) | 0.130 (0.111--0.149) | 1.39 (0.96--1.88) | −0.020 (−0.049 to +0.007) |
| MDD severity: Mild | 633 | 105 | F XGB | 0.640 (0.581--0.702) | 0.133 (0.115--0.152) | 1.34 (0.73--1.97) | −0.007 (−0.036 to +0.020) |
| MDD severity: Mild | 633 | 105 | N WTD | 0.607 (0.547--0.668) | 0.137 (0.117--0.157) | 1.30 (0.54--2.12) | −0.020 (−0.049 to +0.008) |
| MDD severity: Moderate | 1,426 | 255 | E LR | 0.652 (0.618--0.687) | 0.142 (0.131--0.155) | 0.98 (0.74--1.24) | +0.003 (−0.018 to +0.021) |
| MDD severity: Moderate | 1,426 | 255 | F XGB | 0.655 (0.620--0.691) | 0.141 (0.129--0.154) | 1.45 (1.10--1.84) | −0.007 (−0.028 to +0.011) |
| MDD severity: Moderate | 1,426 | 255 | N WTD | 0.631 (0.593--0.666) | 0.143 (0.132--0.157) | 1.58 (1.10--2.09) | −0.005 (−0.026 to +0.013) |
| MDD severity: Psychotic | 18 | 8 | E LR | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | F XGB | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | N WTD | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | E LR | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | F XGB | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | N WTD | not estimable | — | — | — |
| MDD severity: Severe | 468 | 137 | E LR | 0.700 (0.648--0.749) | 0.187 (0.171--0.201) | 1.21 (0.88--1.56) | +0.029 (−0.007 to +0.070) |
| MDD severity: Severe | 468 | 137 | F XGB | 0.682 (0.621--0.734) | 0.188 (0.172--0.204) | 1.41 (0.97--1.93) | +0.007 (−0.028 to +0.049) |
| MDD severity: Severe | 468 | 137 | N WTD | 0.678 (0.622--0.730) | 0.193 (0.178--0.208) | 1.86 (1.27--2.50) | +0.014 (−0.021 to +0.055) |
| MDD severity: Unspecified | 5,828 | 967 | E LR | 0.641 (0.621--0.660) | 0.133 (0.127--0.139) | 0.94 (0.81--1.07) | −0.000 (−0.010 to +0.009) |
| MDD severity: Unspecified | 5,828 | 967 | F XGB | 0.635 (0.617--0.654) | 0.134 (0.127--0.140) | 1.27 (1.10--1.43) | +0.002 (−0.008 to +0.011) |
| MDD severity: Unspecified | 5,828 | 967 | N WTD | 0.609 (0.590--0.628) | 0.135 (0.129--0.142) | 1.14 (0.94--1.35) | −0.003 (−0.013 to +0.006) |
| MDD recurrence: Unspecified | 32 | 7 | E LR | not estimable | — | — | — |
| MDD recurrence: Unspecified | 32 | 7 | F XGB | not estimable | — | — | — |
| MDD recurrence: Unspecified | 32 | 7 | N WTD | not estimable | — | — | — |
| MDD recurrence: Dysthymia | 584 | 97 | E LR | 0.690 (0.638--0.748) | 0.130 (0.113--0.149) | 1.33 (0.92--1.86) | +0.008 (−0.022 to +0.037) |
| MDD recurrence: Dysthymia | 584 | 97 | F XGB | 0.650 (0.593--0.707) | 0.134 (0.116--0.153) | 1.39 (0.82--2.01) | +0.012 (−0.019 to +0.040) |
| MDD recurrence: Dysthymia | 584 | 97 | N WTD | 0.628 (0.567--0.688) | 0.135 (0.116--0.156) | 2.22 (1.18--3.50) | +0.003 (−0.028 to +0.032) |
| MDD recurrence: Recurrent | 2,177 | 433 | E LR | 0.698 (0.671--0.726) | 0.146 (0.136--0.156) | 1.09 (0.94--1.26) | −0.000 (−0.017 to +0.015) |
| MDD recurrence: Recurrent | 2,177 | 433 | F XGB | 0.693 (0.665--0.720) | 0.146 (0.137--0.156) | 1.38 (1.18--1.59) | −0.006 (−0.022 to +0.009) |
| MDD recurrence: Recurrent | 2,177 | 433 | N WTD | 0.666 (0.639--0.693) | 0.150 (0.140--0.160) | 1.26 (1.07--1.48) | −0.005 (−0.021 to +0.011) |
| MDD recurrence: Single Episode | 5,723 | 954 | E LR | 0.633 (0.612--0.652) | 0.134 (0.128--0.141) | 0.86 (0.73--0.99) | +0.000 (−0.010 to +0.010) |
| MDD recurrence: Single Episode | 5,723 | 954 | F XGB | 0.627 (0.607--0.647) | 0.135 (0.129--0.141) | 1.14 (0.97--1.31) | +0.001 (−0.009 to +0.011) |
| MDD recurrence: Single Episode | 5,723 | 954 | N WTD | 0.603 (0.584--0.623) | 0.136 (0.130--0.143) | 1.03 (0.83--1.22) | −0.004 (−0.014 to +0.006) |

E LR: embedded logistic regression; F XGB: feature-vector XGBoost; N WTD: logistic-regression-weighted nearest-neighbor prediction (k = 295). Events denotes positive TRD proxy outcomes. Mean risk difference is mean predicted probability minus observed frequency. MDD recurrence: Unspecified is the 32 test patients with no recurrence code recorded; every one of them is also coded Unspecified severity.

## S9.4 Adjusted Subgroup Comparisons

Of 240 contrasts, 58 had unadjusted CIs excluding zero and 23 survived Benjamini--Hochberg adjustment (Table S12; each surviving model is drawn in manuscript Figure 5).

Table S12. Contrasts surviving Benjamini-Hochberg adjustment across all 240 reported comparisons, grouped by contrast and arm. "Models surviving" counts how many of that arm's contrasted models cleared the threshold.

| **Contrast** | **Arm** | **Models surviving** | **ΔROC AUC range** | **Smallest P (BH)** |
| -------------------------------------- | ----------------- | --------- | ---------------- | --------- |
| Age: 18-29 vs rest | Feature vector | 1 of 4 | −0.068 (95% CI −0.117 to −0.022) | 0.042 |
| MDD recurrence: Recurrent vs rest | Embedded | 4 of 4 | +0.059 (95% CI +0.030 to +0.089) to +0.072 (95% CI +0.041 to +0.104) | 0.015 |
| MDD recurrence: Recurrent vs rest | Feature vector | 4 of 4 | +0.060 (95% CI +0.027 to +0.091) to +0.068 (95% CI +0.037 to +0.100) | 0.015 |
| MDD recurrence: Recurrent vs rest | Nearest neighbors | 2 of 2 | +0.053 (95% CI +0.022 to +0.085) to +0.060 (95% CI +0.028 to +0.091) | 0.015 |
| MDD recurrence: Single Episode vs rest | Embedded | 4 of 4 | −0.071 (95% CI −0.105 to −0.039) to −0.065 (95% CI −0.096 to −0.035) | 0.015 |
| MDD recurrence: Single Episode vs rest | Feature vector | 3 of 4 | −0.064 (95% CI −0.098 to −0.030) to −0.056 (95% CI −0.088 to −0.024) | 0.027 |
| MDD recurrence: Single Episode vs rest | Nearest neighbors | 2 of 2 | −0.058 (95% CI −0.090 to −0.026) to −0.047 (95% CI −0.079 to −0.014) | 0.027 |
| Marital status: Never Married vs rest | Embedded | 2 of 4 | −0.054 (95% CI −0.090 to −0.019) to −0.051 (95% CI −0.086 to −0.016) | 0.015 |
| Marital status: Never Married vs rest | Nearest neighbors | 1 of 2 | −0.047 (95% CI −0.080 to −0.012) | 0.042 |

Ranges run from the smallest to the largest surviving point estimate, each with its own 95% CI; a single-model row shows that model's estimate and CI. Every surviving contrast's 95% CI excludes zero.

All 10 male-minus-female AUC contrasts included zero; the largest absolute difference was +0.012 (95% CI −0.021 to +0.046), for FEATURE gradient boosting. This does not establish equivalent performance.

All 10 White-minus-non-White AUC contrasts were positive, from +0.005 (95% CI −0.031 to +0.042) to +0.046 (95% CI +0.006 to +0.087); 5 excluded zero before adjustment, but none survived adjustment (minimum adjusted P=.15). For the 2 leading models, calibration slopes in White patients and in patients with other recorded racial categories were 0.97 (95% CI 0.87--1.08) and 0.95 (95% CI 0.74--1.16) for embedded logistic regression, and 1.28 (95% CI 1.14--1.44) and 1.07 (95% CI 0.75--1.36) for feature-vector XGBoost.

The other-recorded-race stratum had 302 events, compared with 1,181 among White patients, and wider CIs. The direction is consistent across related models, but these are correlated comparisons rather than independent replications. The data leave racial differences unresolved.

Nineteen of the 23 adjusted contrasts involved recurrence. Recurrent coding was associated with higher discrimination in all 10 contrasted models, from +0.053 (95% CI +0.022 to +0.085) to +0.072 (95% CI +0.041 to +0.104). Single-episode coding was associated with lower discrimination, from −0.071 (95% CI −0.105 to −0.039) to −0.047 (95% CI −0.079 to −0.014), which survived adjustment in 9. Severe coding did not survive adjustment in either retrieval arm at its best k (plain cosine +0.053, 95% CI −0.008 to +0.104, adjusted P=.26; logistic-regression-weighted +0.064, 95% CI +0.005 to +0.118, adjusted P=.18).

The remaining 4 adjusted contrasts indicated lower discrimination among never-married patients in 2 EMBEDDED classifiers, from −0.054 (95% CI −0.090 to −0.019) to −0.051 (95% CI −0.086 to −0.016; minimum adjusted P=.015), and in logistic-regression-weighted retrieval, −0.047 (95% CI −0.080 to −0.012; adjusted P=.04), and at ages 18--29 in FEATURE XGBoost, −0.068 (95% CI −0.117 to −0.022; adjusted P=.04). Their causes were not established.

![](../results/review/subgroups/subgroup_forest.png){width=5.6in}

Figure S13. Subgroup discrimination across sociodemographic strata, one representative model per arm (embedded logistic regression, feature-vector XGBoost, and logistic-regression-weighted retrieval at k = 295, the leading model of each), Qwen3-Embedding-8B, with 95% bootstrap confidence intervals. The dotted line marks chance. Strata declared not estimable are omitted.
