<!--
Section 19 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S6. The held-out set against the training set
-->

# Supplement S6. The held-out set against the training set

The main text reports the split's sizes and outcome counts (Methods,
*Missing data and sample partition*) and states that every per-predictor
standardized mean difference (SMD) is small. This
section shows the distributions behind that statement, because a claim about
comparability that is asserted rather than displayed cannot be checked by a
reader.

The split is the frozen stratified 80/20 split every evaluation in this paper
uses. Nothing was refit or re-split to produce this table. SMDs use the same
pooled-standard-deviation definition as main-text Table 1, so the two tables are directly
comparable. Over the 100 predictor rows the largest absolute SMD is **0.036**,
and no row reaches the conventional 0.1 threshold for a non-trivial imbalance.
The maximum sits on a social-determinant flag recorded for 22 training
patients and none of the held-out patients. That is a small-cell artifact
rather than a distributional difference, and the flag's prevalence is 0.1% in
the arm that has it.
The outcome rate matches by construction, the split having been stratified on
it, and is therefore not evidence of anything.

***Table S5.** Held-out patients against training patients on the
characteristics reported in main-text Table 1. Continuous variables are median
(IQR); categorical and boolean entries are n (%). SMD is training minus
held-out, in pooled standard deviations. Vital signs are shown because they
describe the cohort, but they are rendered only in the narrative
representation and are absent from the feature vector as published
(Supplement S8).*

| Characteristic | Training | Held-out | SMD |
| --- | ---: | ---: | ---: |
| **Demographics** | | | |
| Age (years) | 55 (38-70) | 55 (38-70) | -0.014 |
| Age band: 18-29 | 4,428 (13.0%) | 1,085 (12.7%) | +0.008 |
| Age band: 30-44 | 7,198 (21.1%) | 1,827 (21.5%) | -0.008 |
| Age band: 45-64 | 10,632 (31.2%) | 2,636 (31.0%) | +0.006 |
| Age band: 65+ | 11,805 (34.7%) | 2,968 (34.9%) | -0.004 |
| Sex: Female | 24,682 (72.5%) | 6,168 (72.4%) | +0.001 |
| Race: White/Caucasian | 27,244 (80.0%) | 6,835 (80.3%) | -0.007 |
| Race: Black/African American | 1,894 (5.6%) | 474 (5.6%) | -0.000 |
| Race: Am. Indian/Alaska Native | 1,637 (4.8%) | 396 (4.7%) | +0.007 |
| Race: Missing | 247 (0.7%) | 50 (0.6%) | +0.017 |
| Language: English only | 33,698 (98.9%) | 8,425 (98.9%) | -0.000 |
| **Depression phenotype** | | | |
| MDD recurrence: Recurrent | 9,036 (26.5%) | 2,177 (25.6%) | +0.022 |
| MDD severity: Severe | 1,818 (5.3%) | 468 (5.5%) | -0.007 |
| MDD severity: Moderate | 5,807 (17.0%) | 1,426 (16.7%) | +0.008 |
| **Psychiatric and substance comorbidity** | | | |
| Suicidality flagged | 1,392 (4.1%) | 361 (4.2%) | -0.008 |
| Anxiety disorder | 17,975 (52.8%) | 4,426 (52.0%) | +0.016 |
| Substance use disorder (any) | 7,472 (21.9%) | 1,793 (21.1%) | +0.021 |
| Insomnia | 7,452 (21.9%) | 1,898 (22.3%) | -0.010 |
| PTSD | 1,241 (3.6%) | 300 (3.5%) | +0.006 |
| Alcohol use disorder | 1,523 (4.5%) | 352 (4.1%) | +0.017 |
| **Medical comorbidity** | | | |
| High cholesterol | 12,591 (37.0%) | 3,156 (37.1%) | -0.002 |
| Uncontrolled hypertension | 12,544 (36.8%) | 3,136 (36.8%) | +0.000 |
| **Vital signs (narrative only)** | | | |
| BMI | 29 (25-35) | 29 (25-35) | -0.013 |
| Systolic BP | 126 (118-136) | 126 (118-136) | -0.010 |
| BMI: not recorded | 7,484 (22.0%) | 1,911 (22.4%) | -0.011 |
| **Treatment and utilization** | | | |
| Active med count | 1 (0-2) | 1 (0-2) | +0.008 |
| Encounter count | 21 (8-46) | 20 (8-47) | -0.001 |
| Pre-index history (days) | 1792 (1213-2547) | 1797 (1222-2541) | +0.004 |
| Prior adequate AD trial (any class) | 5,014 (14.7%) | 1,262 (14.8%) | -0.003 |
| Benzodiazepine days recorded | 3,775 (11.1%) | 949 (11.1%) | -0.002 |
| Hypnotic recorded | 1,319 (3.9%) | 342 (4.0%) | -0.007 |
| Augmentation therapy used | 326 (1.0%) | 96 (1.1%) | -0.017 |

**What this does and does not establish.** It establishes that no measured
difference separates the patients the models were scored on from the patients
they were trained on. The reported discrimination is therefore not an artifact
of an evaluation sample that differs on anything this table covers. It establishes nothing about
representativeness of any wider population. The delivered extract is
case-enriched by design (Methods, *Study design and data source*), and both halves of the
split inherit that enrichment equally. A table comparing two halves of a
selected cohort cannot detect the selection they share. The calibration
reported in this paper remains calibration to this cohort's own base rate, and
the limitation stands as written.
