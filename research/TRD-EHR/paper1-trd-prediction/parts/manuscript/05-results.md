<!--
Section 5 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Results
-->

# Results

<!-- ORDER IS LOAD-BEARING. Participant flow and cohort first, then everything
     bearing on Point 1 (the representation comparison), then everything
     bearing on Point 2 (retrieval), then the validity checks that support
     both. Do not re-insert a subsection ahead of the discrimination result;
     the previous draft opened Results on subgroup performance and confound
     checks, which buried the finding the paper is about. -->

The results are reported in the order of the two objectives. Participant flow
and cohort composition come first, then the comparison between the two
representations, then the retrieval predictor, and last the checks that bear on
both.

## Participant flow
<!-- TRIPOD+AI 13a (participant flow), 13b (characteristics) -->

Of the 501,718 patients in the delivered extract, 42,579 satisfied every
inclusion and exclusion criterion. Supplement M2 (Table M1) counts the
rejections at each stage of the hierarchical cascade. Those 42,579 are
the analysis cohort throughout, and 7,455 of them (17.5%) were
TRD-positive.

## Cohort characteristics

The cohort was middle-aged (median age 55 years, IQR 38–70),
predominantly female (72.5%), White/Caucasian (80.0%) and
English-preferring (98.9%). Table 1 gives every selected characteristic, overall and by TRD status,
and Supplement S9 gives within-subgroup TRD prevalence. The
characteristics most associated with TRD were a flagged suicidality
history, severe MDD coding, and a broad band of psychiatric and
substance-use comorbidity, which is the same profile the models later
rely on.

***Table 1.** Selected cohort characteristics by TRD status. Continuous
variables are median (IQR); categorical/boolean entries are n (%).
SMD = standardized mean difference (TRD-positive vs TRD-negative).*

| Characteristic | Level | Overall | TRD+ | TRD− | SMD |
| --- | --- | ---: | ---: | ---: | ---: |
| **Demographics** | | | | | |
| Age (years) | median (IQR) | 55 (38–70) | 51 (36–66) | 56 (39–71) | −0.193 |
| Age band | 18–29 | 5,513 (12.9%) | 1,135 (15.2%) | 4,378 (12.5%) | 0.080 |
| | 30–44 | 9,025 (21.2%) | 1,836 (24.6%) | 7,189 (20.5%) | 0.100 |
| | 45–64 | 13,268 (31.2%) | 2,445 (32.8%) | 10,823 (30.8%) | 0.043 |
| | 65+ | 14,773 (34.7%) | 2,039 (27.4%) | 12,734 (36.3%) | −0.192 |
| Sex | Female | 30,850 (72.5%) | 5,552 (74.5%) | 25,298 (72.0%) | 0.055 |
| Race/ethnicity | White/Caucasian | 34,079 (80.0%) | 5,942 (79.7%) | 28,137 (80.1%) | −0.010 |
| | Black/African American | 2,368 (5.6%) | 401 (5.4%) | 1,967 (5.6%) | −0.010 |
| | Am. Indian/Alaska Native | 2,033 (4.8%) | 394 (5.3%) | 1,639 (4.7%) | 0.028 |
| | Missing | 297 (0.7%) | 46 (0.6%) | 251 (0.7%) | −0.012 |
| **Depression phenotype** | | | | | |
| MDD recurrence | Recurrent | 11,213 (26.3%) | 2,189 (29.4%) | 9,024 (25.7%) | 0.082 |
| | Single episode | 28,206 (66.2%) | 4,721 (63.3%) | 23,485 (66.9%) | −0.074 |
| MDD severity | Severe | 2,286 (5.4%) | 720 (9.7%) | 1,566 (4.5%) | 0.204 |
| | Moderate | 7,233 (17.0%) | 1,300 (17.4%) | 5,933 (16.9%) | 0.014 |
| | Psychotic | 112 (0.3%) | 35 (0.5%) | 77 (0.2%) | 0.043 |
| | Unspecified | 28,951 (68.0%) | 4,803 (64.4%) | 24,148 (68.8%) | −0.092 |
| **Psychiatric and substance comorbidity** | | | | | |
| Suicidality flagged | True | 1,753 (4.1%) | 641 (8.6%) | 1,112 (3.2%) | 0.232 |
| Anxiety disorder | True | 22,401 (52.6%) | 4,499 (60.3%) | 17,902 (51.0%) | 0.190 |
| Substance use disorder (any) | True | 9,265 (21.8%) | 2,006 (26.9%) | 7,259 (20.7%) | 0.147 |
| Insomnia | True | 9,350 (22.0%) | 2,021 (27.1%) | 7,329 (20.9%) | 0.147 |
| PTSD | True | 1,541 (3.6%) | 450 (6.0%) | 1,091 (3.1%) | 0.141 |
| Alcohol use disorder | True | 1,875 (4.4%) | 501 (6.7%) | 1,374 (3.9%) | 0.125 |
| Opioid use disorder | True | 1,281 (3.0%) | 337 (4.5%) | 944 (2.7%) | 0.098 |
| Adjustment disorder | True | 2,918 (6.9%) | 663 (8.9%) | 2,255 (6.4%) | 0.093 |
| **Medical comorbidity** | | | | | |
| High cholesterol | True | 15,747 (37.0%) | 2,202 (29.5%) | 13,545 (38.6%) | −0.191 |
| Uncontrolled hypertension | True | 15,680 (36.8%) | 2,366 (31.7%) | 13,314 (37.9%) | −0.130 |
| **Treatment and utilization** | | | | | |
| Active med count | median (IQR) | 1 (0–2) | 1 (0–2) | 1 (0–2) | 0.084 |
| Encounter count | median (IQR) | 21 (8–46) | 17 (6–40) | 21 (8–47) | −0.140 |
| Pre-index history (days) | median (IQR) | 1,792 (1,216–2,546) | 1,629 (1,141–2,335) | 1,830 (1,239–2,587) | −0.198 |
| Any prior treatment exposure recorded | True | 10,230 (24.0%) | 1,793 (24.1%) | 8,437 (24.0%) | 0.001 |
| Prior adequate AD trial (any class) | True | 6,276 (14.7%) | 1,050 (14.1%) | 5,226 (14.9%) | −0.023 |
| Benzodiazepine days recorded | True | 4,724 (11.1%) | 989 (13.3%) | 3,735 (10.6%) | 0.081 |
| Hypnotic recorded | True | 1,661 (3.9%) | 292 (3.9%) | 1,369 (3.9%) | 0.001 |
| Augmentation therapy used | True | 422 (1.0%) | 108 (1.4%) | 314 (0.9%) | 0.052 |

## Model discrimination
<!-- TRIPOD+AI 13b. POINT 1, the primary result. -->

The embedding did not outperform the feature vector. Embedded logistic
regression achieved the highest discrimination on the embedded
representation (ROC AUC 0.657, 95% CI 0.643–0.672), and XGBoost led the
feature-vector models (0.649, 95% CI 0.634–0.664). All eight representation-by-classifier combinations appear in Figure 2A
and Table 2. The best embedded model scored 0.008 higher than the best
feature-vector model, on an interval from −0.003 to +0.019 that crosses
zero (Figure 2B). The comparison is paired: every bootstrap draw scores
both models on the same patients, so the interval measures the gap
between models rather than the luck of the draw. An embedded gain larger than +0.019 ROC AUC falls outside it.
Discrimination was modest throughout, from 0.623 at the lowest
configuration to 0.657 at the highest, against a 17.5% TRD-positive
rate.

Which representation won depended on the learner. Holding the classifier
fixed, the embedding helped logistic regression (+0.028, 95% CI +0.017 to
+0.039). It hurt all three tree ensembles: random forest by 0.022 (95% CI
0.011 to 0.033), gradient
boosting by 0.013 (0.001 to 0.026), and XGBoost by 0.013 (0.002 to
0.025). Tuning grids did not differ between representations, so this is
a property of the representation rather than of its tuning.

***Table 2.** Discrimination of the four classifiers on each
representation (held-out test set). 95% CIs are bootstrap percentile
intervals. FEATURE-side values are from the 92-column feature vector.*

| Representation | Classifier | ROC AUC (95% CI) |
| --- | --- | :---: |
| EMBEDDED | Logistic regression | 0.657 (0.643–0.672) |
| EMBEDDED | Random forest | 0.623 (0.608–0.639) |
| EMBEDDED | Gradient boosting | 0.632 (0.618–0.647) |
| EMBEDDED | XGBoost | 0.636 (0.621–0.651) |
| FEATURE | Logistic regression | 0.629 (0.613–0.644) |
| FEATURE | Random forest | 0.644 (0.630–0.659) |
| FEATURE | Gradient boosting | 0.645 (0.629–0.660) |
| FEATURE | XGBoost | 0.649 (0.634–0.664) |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/discrimination_forest_EMBEDDED_vs_FEATURE.png){width=6in}

***Figure 2.** Discrimination by representation and classifier (held-out
test set, n = 8,516; primary Qwen3-Embedding-8B encoder). **(A)** All
eight representation-by-classifier combinations, grouped with EMBEDDED
above FEATURE and in the same classifier order within each group, so the
two can be read row for row. Markers are ROC AUC point estimates, bars
are bootstrap percentile 95% confidence intervals, and the values are in
Table 2. **(B)** The paired difference in ROC AUC, EMBEDDED minus
FEATURE, with a paired bootstrap 95% interval. The solid line marks
zero. The four diamonds hold the classifier fixed and vary only the
representation; the star is the post-hoc
best-feature-versus-best-embedded contrast, embedded logistic regression
minus feature-vector XGBoost.*

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_xgboost_FEATURE.png){width=6in}

***Figure 3.** Receiver-operating-characteristic curves for the best
classifier on each representation (held-out test set; primary
Qwen3-Embedding-8B encoder). Shaded bands are bootstrap 95% confidence
intervals; point AUCs are given in Table 2.*

The two behaved alike at their Youden-J operating points (Figure 4).
Embedded logistic regression ran at slightly higher sensitivity than
feature-vector XGBoost (0.65 versus 0.62), flagging 964 of 1,491
held-out TRD patients against 917, and at slightly lower specificity
(0.58 versus 0.61), producing more false positives (2,932 versus 2,768).
Both thresholds fell near 0.17. They were chosen on the same patients
the models were scored on, so these figures describe the shape of each
ROC curve rather than performance at a prespecified threshold, and are
not candidate operating characteristics.

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_xgboost_FEATURE.png){width=6in}

***Figure 4.** Confusion matrices at the Youden-J optimal operating point
for the best classifier on each representation (held-out test set;
primary Qwen3-Embedding-8B encoder).*

## Model calibration

Neither representation was systematically better scaled than the other
(Table 3, Figure 5). On
the embedded representation, gradient boosting was the best-calibrated
model (slope 1.01, intercept 0.01). Logistic regression was mildly
under-confident (slope 1.27, the slope above 1 indicating probabilities
pulled toward the base rate), random forest similar (1.15), and XGBoost
mildly over-confident (slope 0.75). On the feature vector, XGBoost was
best-calibrated (slope 1.02, intercept 0.02) and random forest the worst
(slope 1.84). Each representation therefore contained both a
near-ideally calibrated model and a poorly calibrated one, and which
classifier occupied which position differed between them. No model
placed any test prediction above 0.9, as expected at this base rate.
Absolute-error metrics are in Supplement S3. Every one of these figures
is scaled to this cohort's 17.5% TRD rate, which the sampling design
chose, so none of them establishes calibration anywhere else.

***Table 3.** Calibration slope (ideal 1) and intercept (ideal 0) of the
four classifiers on each representation (held-out test set). Brier score
and weighted calibration error are reported in Supplement S3 (Table S3).*

| Representation | Classifier | Slope | Intercept |
| --- | --- | ---: | ---: |
| EMBEDDED | Logistic regression | 1.27 | −0.07 |
| EMBEDDED | Random forest | 1.15 | −0.02 |
| EMBEDDED | Gradient boosting | 1.01 | 0.01 |
| EMBEDDED | XGBoost | 0.75 | 0.07 |
| FEATURE | Logistic regression | 0.78 | 0.06 |
| FEATURE | Random forest | 1.84 | −0.15 |
| FEATURE | Gradient boosting | 0.87 | 0.04 |
| FEATURE | XGBoost | 1.02 | 0.02 |

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png){width=6in}

***Figure 5.** Calibration curves for the best classifier on each
representation (held-out test set; primary Qwen3-Embedding-8B encoder).
The diagonal is perfect calibration. Deviations above it indicate
under-confidence and below it over-confidence. Per-classifier calibration
slope and intercept are given in Table 3.*

## What each representation reads

Only the feature vector can be read directly.
The embedded representation's 4,096 latent dimensions carry no
individual clinical meaning, so per-concept attribution on the embedded
side is addressed by the ablation below rather than by an importance
ranking. On the feature vector, the highest-weighted predictors
recapitulated the strongest univariate correlates of TRD in Table 1.
Severe MDD coding, a flagged suicidality history, insomnia,
obsessive–compulsive disorder, opioid use disorder, PTSD, and anxiety
disorder carried the largest positive logistic-regression weights.
Indicators such as missing smoking status, hyperlipidemia, longer
pre-index history, and male sex carried negative weights. Importances for
all four classifiers are shown in Figure 6. The tree ensembles concentrated on a similar set of psychiatric and
substance-use predictors at the top, with direction of effect recovered
by univariate correlation. The readable side of the null is therefore
reading recognizable psychiatric risk, which is what separates a tie
between two working models from a tie between two failing ones.

<!-- One panel per row at full text width: the previous 2x2 grid at 2.8in
     rendered the axis labels unreadably small. -->

**(A) Logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_logistic_regression.png){width=6in}

**(B) Random forest**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_random_forest.png){width=6in}

**(C) Gradient boosting**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_gradient_boosting.png){width=6in}

**(D) XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_xgboost.png){width=6in}

***Figure 6.** Feature importance on the feature-vector representation, one
panel per classifier. (A) Signed logistic-regression coefficients
(steelblue raises TRD risk, firebrick lowers it). (B) Random forest,
(C) gradient boosting, and (D) XGBoost importances, with
direction-of-effect recovered by univariate correlation. The
highest-ranked predictors mirror the largest TRD-stratified differences
in Table 1.*

The embedded model used far fewer dimensions than it was given.
Cross-validated elasticnet left 385 of the 4,096 with nonzero weight,
and roughly 179 of those carried 80% of the total coefficient magnitude
(roughly 236 carried 90%; Figure 7). Fewer than 5% of the available dimensions
therefore account for most of the fit, and model-agnostic correlation
and principal-component checks agree (Supplement S1).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_cumulative_EMBEDDED.png){width=6in}

***Figure 7.** Effective dimensionality of the embedded representation
(primary Qwen3-Embedding-8B encoder): cumulative built-in feature
importance for the four embedded classifiers. Each curve plots the
cumulative fraction of total importance mass against dimension rank, with
dimensions sorted by descending native importance, and the K₈₀ / K₉₀
knees are reported in the legend. Model-agnostic correlation and PCA-based checks are in Supplement S1.*

## Semantic-feature ablation

Permuting narrative concepts one at a time located the embedded signal in
psychiatric history, medication burden, and prior treatment exposure.
Psychiatric history produced the largest discrimination loss (logistic
regression, a ROC AUC change of −0.028, with the other three
classifiers between −0.024 and −0.027). Medication burden produced the second largest
(−0.003 to −0.027) and treatment exposure the third (−0.019 for logistic
regression, and +0.000 to −0.011 for the other three).
Permuting the two sociodemographic concepts, race/ethnicity and social
determinants of health, or the treatment-contraindication section
changed discrimination by no more than 0.005 under any classifier
(Table 4, Figure 8).

Paired-bootstrap intervals excluded zero for psychiatric history in all
four classifiers, medication burden in three, and treatment exposure in
two. Among the remaining concepts only one interval excluded zero,
treatment contraindications under XGBoost at −0.005 (−0.008 to −0.001),
and race and social determinants moved ROC AUC by less than 0.003
anywhere.

The domains the embedding relies on are the same domains that carry the
largest feature-vector weights. That convergence is the mechanism behind the null in Table 2: the two representations are reading the same
clinical content out of the same record, and the embedding reorganizes it
without adding to it.

***Table 4.** Semantic-feature ablation: change in ROC AUC versus the
frozen baseline when each narrative concept is permuted across donors
(embedded representation, primary Qwen3-Embedding-8B encoder). More
negative = larger reliance on that concept. Point estimates, ordered by descending logistic-regression loss to match
Figure 8. Paired-bootstrap intervals are quoted in the text.*

| Permuted concept | LR | RF | GB | XGB |
| --- | ---: | ---: | ---: | ---: |
| Psychiatric history | −0.028 | −0.027 | −0.024 | −0.027 |
| Medication burden | −0.027 | −0.003 | −0.014 | −0.017 |
| Treatment exposure | −0.019 | +0.000 | −0.006 | −0.011 |
| Treatment contraindications | −0.002 | +0.001 | −0.001 | −0.005 |
| Social determinants (SDOH) | −0.000 | +0.000 | +0.000 | +0.001 |
| Race/ethnicity | −0.000 | +0.000 | −0.003 | −0.000 |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/ablation_roc_ci_EMBEDDED.png){width=6in}

***Figure 8.** Semantic-feature ablation, absolute-discrimination view
(embedded representation, primary Qwen3-Embedding-8B encoder). Each row
is a run: the unablated baseline on top, then the six permutation
specifications ordered by descending logistic-regression ROC AUC drop, the
same ordering reused across panels. There is one panel per classifier,
arranged two by two on a shared ROC AUC axis, with a reference line at the
baseline ROC AUC. Permuting psychiatric history, medication burden and
treatment exposure produces the largest discrimination loss, whereas the
remaining three concepts move ROC AUC comparatively little (deltas in
Table 4).*

## Robustness across encoders

The comparison did not depend on which encoder produced the embedding.
Across the four encoders the embedded logistic-regression model occupied
a 0.012-wide discrimination band (ROC AUC 0.645–0.657, Table 5 and
Figure 9A). Qwen3-Embedding-8B was highest (0.657, 95% CI 0.643–0.672),
with bge-en-icl and Qwen3-Embedding-4B tied just behind (both 0.655) and
bge-small-en-v1.5 lowest (0.645). Logistic regression was the
best-discriminating classifier on the embedded representation for every
encoder. Only bge-small-en-v1.5 scored below the best feature-vector
model. The other three scored just above it, and all four fall inside
that same band, which is narrower than every confidence interval in
Table 2. The choice of encoder therefore does not change
what Table 2 shows.

The ablation also reproduced across encoders (Figure 9B). Psychiatric
history and medication burden cost the most on all four, −0.027 to
−0.030 and −0.022 to −0.034 respectively. Every one of those intervals
excluded zero. The two sociodemographic permutations moved ROC AUC
little. The order of the two largest concepts held everywhere except in
bge-en-icl, where medication burden cost more than psychiatric history,
and it did so for all four classifiers there (embedded logistic
regression −0.034 versus −0.027).

***Table 5.** Embedded logistic-regression discrimination by encoder
(held-out test set). 95% CIs are bootstrap percentile intervals.
"Dimensions" is the encoder's output dimensionality, which is also the
number of predictor columns the classifier receives; EPV is events per
variable, 5,964 TRD-positive training patients divided by that column
count (Supplement M7). Note that EPV runs opposite to discrimination: the
encoder with the most favorable EPV is the least discriminating.*

| Encoder | Dimensions | EPV | ROC AUC (95% CI) |
| --- | ---: | ---: | :---: |
| bge-small-en-v1.5 | 384 | 15.5 | 0.645 (0.629–0.660) |
| bge-en-icl | 4,096 | 1.5 | 0.655 (0.641–0.670) |
| Qwen3-Embedding-4B | 2,560 | 2.3 | 0.655 (0.641–0.670) |
| Qwen3-Embedding-8B | 4,096 | 1.5 | 0.657 (0.643–0.672) |

![](../results/cross_embedder_robustness_EMBEDDED.png){width=6in}

***Figure 9.** Cross-embedder robustness: embedded logistic-regression
ROC AUC (A) and the two largest semantic-feature ablation deltas
(psychiatric history, medication burden; B) across all four encoders
(bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, Qwen3-Embedding-8B),
demonstrating that the principal conclusions hold beyond the
Qwen3-Embedding-8B encoder. Error bars are bootstrap (A) and
paired-bootstrap (B) 95% confidence intervals.*

## Prediction from retrieved neighbors
<!-- POINT 2. Table 6 is the two-by-two grid; Table 7 is the cross-encoder
     reproduction; Figure 10 is nearest against random. The similarity-judge
     weightings, and the farthest and subsampled schemes, were removed from
     this arm on 2026-09-06 and are held in reserve/. Do not re-add columns
     here. -->

Retrieval recovered real signal from the embedding geometry. Retrieving
the nearest neighbors discriminated at ROC AUC 0.594 (95% CI
0.578–0.610) under cosine weighting. Random retrieval landed at chance
(0.499, 95% CI 0.483–0.515). A space in which a patient's closest
analogues predict the outcome and randomly drawn patients do not is a
space that carries label information.

How neighbors were weighted mattered far less than which neighbors were
retrieved. Uniform and cosine weighting differed by at most 0.005 ROC
AUC within either retrieval scheme, against the gap from 0.594 to 0.499
between nearest and random retrieval (Table 6). Once the 50 retrieved
patients are already the most similar available, adjusting their
relative contributions has almost nothing left to do.

Retrieval nevertheless lost decisively to a model fitted on the same
embedding. The best retrieval configuration reached 0.594 (0.578–0.610)
against 0.657 (0.643–0.672) for embedded logistic regression, a
shortfall of 0.063 ROC AUC on intervals that do not overlap. The
comparison is unpaired and therefore conservative, since both predictors
score the same held-out patients. Retrieval also fell below every one of
the eight trained configurations in Table 2, including the weakest of
them at 0.623.

***Table 6.** Neighbor-weighted ROC AUC by retrieval scheme and
weighting strategy (embedded representation, primary Qwen3-Embedding-8B
encoder, held-out test set; K = 50 neighbors). 95% CIs are bootstrap
percentile intervals. Random retrieval is the negative control. For
comparison, embedded logistic regression on the same representation and
the same patients reaches 0.657 (0.643–0.672).*

| Retrieval scheme | Uniform (95% CI) | Cosine (95% CI) |
| --- | :---: | :---: |
| Nearest | 0.593 (0.578–0.609) | 0.594 (0.578–0.610) |
| Random | 0.495 (0.479–0.510) | 0.499 (0.483–0.515) |

**(A) Nearest retrieval**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_COSINE.png){width=6in}

**(B) Random retrieval**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_RANDOM_COSINE.png){width=6in}

***Figure 10.** Neighbor-weighted ROC for the cosine-weighted predictor on
the embedded representation (held-out test set, n = 8,516, K = 50;
primary Qwen3-Embedding-8B encoder). (A) Nearest retrieval;
(B) random retrieval. The separation between the two panels is the
discriminative signal in the embedding geometry. Shaded bands are
bootstrap 95% confidence intervals and the dashed diagonal is chance.
The uniform weighting is in Table 6.*

Both halves of that result reproduced on every encoder (Table 7).
Nearest retrieval beat random retrieval by 0.083 to 0.095 ROC AUC on all
four, and on all four it fell short of that encoder's own trained
logistic regression by 0.061 to 0.065. The gap between retrieval and a
fitted model is therefore a property of the approach rather than of the
primary encoder.

***Table 7.** Neighbor-weighted retrieval against embedded logistic
regression, by encoder (cosine weighting, K = 50, held-out test set).
95% CIs are bootstrap percentile intervals. Random retrieval is the
negative control. The last column is that encoder's own model from Table
5, scored on the same patients.*

| Encoder | Nearest (95% CI) | Random (95% CI) | Embedded logistic regression (95% CI) |
| --- | :---: | :---: | :---: |
| bge-small-en-v1.5 | 0.580 (0.564–0.596) | 0.497 (0.482–0.513) | 0.645 (0.629–0.660) |
| bge-en-icl | 0.592 (0.577–0.607) | 0.498 (0.482–0.515) | 0.655 (0.641–0.670) |
| Qwen3-Embedding-4B | 0.594 (0.579–0.611) | 0.500 (0.484–0.516) | 0.655 (0.641–0.670) |
| Qwen3-Embedding-8B | 0.594 (0.578–0.610) | 0.499 (0.483–0.515) | 0.657 (0.643–0.672) |

## Validity checks

Three checks bear on both objectives, because an artifact in any of them
would undermine the comparison as much as the retrieval result. None of
the three found one.

**Train/test comparability.** The training and test sets were closely
matched on every predictor. Over 100 predictor rows the largest absolute
standardized mean difference was 0.036, none reached the conventional
0.1 threshold, and the maximum sat on a social-determinant flag recorded
for 22 training patients and no held-out patient. That is a small-cell
artifact rather than a distributional difference. No measured difference separates the evaluation sample from the
development sample, and neither is representative of a wider population,
because both halves inherit the extract's case enrichment. Supplement S6
tabulates the distributions in the form of Table 1.

**Data volume did not act as a confound.** Patients with richer records
could appear higher-risk for reasons that have nothing to do with
depression, so we correlated the TRD label with three volume and recency
proxies on the full untruncated data. All three associations were weak
and negative: pre-index history length (Spearman ρ = −0.073), encounter
count (ρ = −0.064), and MDD-to-index gap (ρ = −0.029). TRD-positive patients did not simply have more data (Figure 11A–C), and
discrimination is flat across quintiles of pre-index history length,
which is the stronger form of the same test (Supplement S5). Most patients were prescribed an antidepressant on the day of their MDD
diagnosis (n = 27,906). Their TRD rate was 18.4% against 15.9% for the
14,673 with a delayed prescription, both near the 17.5% base rate
(Figure 11D).

**(A) Pre-index history length**

![](../notebooks/figures/density_pre_anchor_history_days.png){width=6in}

**(B) MDD-to-index gap**

![](../notebooks/figures/density_mdd_to_anchor_days.png){width=6in}

**(C) Encounter count**

![](../notebooks/figures/density_num_encounters.png){width=6in}

**(D) TRD rate, same-day vs delayed prescription**

![](../notebooks/figures/trd_rate_by_delayed_mdd_to_anchor_days.png){width=6in}

***Figure 11.** Volume and recency confound checks on the full untruncated
data. (A–C) TRD-stratified distributions of the three proxies: (A)
pre-index history length; (B) MDD-to-index gap; (C) encounter count.
(D) TRD rate among patients with a same-day versus delayed
MDD-to-antidepressant prescription (dashed line = 17.5% cohort base
rate; bar labels are group n).*

**Subgroup performance.** Most of what separates subgroups here is how the depression is coded,
not who the patient is. The same models were scored again inside eight strata, with nothing
refit, giving 240 between-group contrasts across the three arms. At a conventional 5% threshold about twelve of those clear the bar by
chance alone, so P values were adjusted across the whole set by
Benjamini-Hochberg at a 5% false discovery rate. Fifty-eight contrasts exclude zero before that
adjustment and 24 survive it, 21 of them about MDD coding. Discrimination is higher where MDD is coded
recurrent or severe (+0.059 to +0.087 ROC AUC) and lower where it is
coded single-episode (−0.074 to −0.056), in all three arms. That is a
documentation effect as much as a phenotype one: the models do better
where the diagnosis is recorded specifically, and worse where it is left
unspecified, which is most of this cohort.

The sociodemographic strata gave three surviving contrasts, and all
three are consistent with thinner records supporting weaker prediction.
Discrimination is lower for patients aged 18–29 in the feature-vector
arm (−0.068, adjusted *P* = .04). It is also lower for never-married
patients in the embedded arm, where two of the four classifiers
survive, at −0.054 and −0.051 (adjusted *P* = .01). No sex contrast
came close: all ten include zero and none exceeds 0.012 ROC AUC.
Preferred language was not analyzed, because 98.9% of the cohort prefers
English.

The data neither establish nor rule out a race-associated performance
gap. All ten White-minus-non-White contrasts are positive
(+0.005 to +0.053) and five exclude zero before adjustment, but none
survives it (smallest adjusted *P* = .11). The minority stratum carries
302 outcome events against 1,181, which leaves its intervals roughly
twice as wide. Feature-vector calibration is worse among non-White
patients (slope 0.79 versus 0.98) while the embedded arm holds (0.95
versus 0.97). Supplement S7 has the full stratified results, and
Limitations takes up what a gap this wide can and cannot be read to
mean.
