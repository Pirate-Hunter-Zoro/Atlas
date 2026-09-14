<!--
Section 4 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Methods
-->

# Methods

<!-- This is the senior author's own condensed Methods (supplied 2026-09-02 as
     JMIR_Methods_and_Supplement.docx), taken as written. Departures from his
     text are confined to cross-references, citation markers, the two facts his
     draft could not have known (the eligibility cascade moved to the supplement
     under his comment 115, the cohort table is Table 1 under comment 119), and
     the 2026-09-06 reduction of the neighbor-weighting slate to uniform and
     cosine. Everything his condensation drops is either in Supplement M1-M13 or
     recorded in reserve/methods_reserve.md. Do not grow this section; grow the
     M-section, and note the change in the reserve document. -->

## Study design and data source
<!-- TRIPOD+AI 4a (data source), 4b (study dates), 6a (setting) -->

We conducted a retrospective cohort study using a frozen, de-identified extract
from the Epic EHR of Saint Francis Health System, a community health system in
Tulsa, Oklahoma. The extract included person,
encounter, diagnosis, medication, procedure, laboratory/flowsheet, and
medication-to-RxNorm mapping data. Patient and encounter identifiers were
replaced with one-way hashes before transfer, and no direct identifiers or dates
of birth were provided.

The delivered extract was case enriched rather than a census of the health
system. All patients with a depression code on the problem list were retained,
together with a random sample of patients without that flag at an approximate
4:1 ratio. The extract contained 501,718 patients, including 100,420 (20.0%)
with and 401,298 (80.0%) without a problem-list depression flag. Eligibility for
the analytic cohort was determined from encounter-level diagnoses rather than
the problem-list sampling flag. Consequently, 12,530 of the 42,579 eligible
patients (29.4%) entered through the randomly sampled group. Cohort proportions
therefore describe this enriched sample and should not be interpreted as
health-system prevalence estimates. The head-to-head comparison of
representations is unaffected, both being derived from the same patients and
scored on the same held-out split.

All analyses used data version DV260629v1 and patient version PV260710v1. Source
files were cut on June 29, 2026, and analysis-ready tables were created on July
10, 2026. No subsequent data refresh entered the study. Patient index dates
spanned 2016-2024. The study used a random internal validation split from the
same source and period, not temporal or external validation. Additional
information on the source tables, setting, sampling frame, diagnosis code sets,
and data versions is provided in Supplement M1-M2.

## Participants, index date, and temporal windows
<!-- TRIPOD+AI 5a (eligibility), 5b (study dates), 6b, 6c (treatments) -->

Patients were included if they had a qualifying MDD diagnosis, no bipolar
disorder or schizophrenia-spectrum diagnosis, an eligible
antidepressant index prescription, an MDD diagnosis on or before that
prescription, at least 730 days of pre-index EHR history, and at least 365 days
of post-index follow-up. These criteria yielded 42,579 patients. The eligibility
cascade and rejection reasons are reported in Supplement M2 (Table M1).

The index date was the start date of each patient's earliest antidepressant
prescription recorded on or after the first documented depression diagnosis.
Each patient contributed one index date. The prediction point coincided with the
prescription date, and index eligibility did not depend on subsequent dose,
duration, response, or treatment changes. Predictors were computed only from the
730-day lookback window ending on the index date. Post-index data were used only
to confirm 365 days of follow-up and to ascertain the outcome during that
period. Prior antidepressant exposure was retained as a predictor rather than
used as an exclusion criterion. The index prescription was therefore the first
antidepressant linked to a documented depression diagnosis in the available
record, not necessarily the patient's first lifetime exposure or first adequate
trial. Figure 1 summarizes the temporal design. Full index-selection rules are
given in Supplement M2.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/time_zero_timeline.png){width=6in}

***Figure 1.** Time zero, the lookback window, and the outcome ascertainment
window. The index is the earliest antidepressant prescription recorded on or
after the patient's first documented depression diagnosis; no property of it is
conditioned on post-index data, so the prediction point coincides with the
prescription date. Every predictor is measured inside the 730-day lookback
window. Recorded history frequently extends further back (median 1,792 days) and
its length is itself a predictor, but its content outside the lookback window is
never read. Post-index data enters in exactly two places: eligibility requires at
least 365 days of follow-up, and the outcome is ascertained over those 365 days.*

## Outcome
<!-- TRIPOD+AI 6a (outcome definition), 6b (assessment) -->

The prediction target was a predefined EHR proxy for incident TRD, generated
upstream and used without modification. Consistent with the operational definition used by Forthman et al
[2], patients with MDD were classified as TRD positive if they received at
least 3 distinct antidepressant treatments during the 365 days after the index
date, including the index agent as the first treatment. Equivalently, the
outcome required at least 2 post-index antidepressant changes. A treatment was a
distinct antidepressant agent rather than a prescribing event. Augmentation
without replacement and restarting a previously used agent did not increment the
count, and augmentation enters the study as a pre-index predictor instead.

This outcome is a treatment-switch proxy rather than direct evidence of
inadequate response to 2 adequate trials [4,5]. Symptom response was not
systematically available, and dose and duration adequacy were not verified for
the counted treatments. Switching may therefore reflect nonresponse,
intolerance, adverse effects, cost, insurance constraints, fragmented care,
patient preference, or prescriber practice, and it depends on continuity of care
and access, which differ across demographic groups [16,17]. The label was not
validated against chart review or standardized symptom measures. These
inferential boundaries and proposed validation analyses are detailed in
Supplement M3, and their consequences for the study's claims in the Discussion,
*Limitations*.

## Predictors and patient representations
<!-- TRIPOD+AI 7a (predictor definition), 7b (assessment) -->

Predictors were specified a priori on clinical and prior-literature grounds
before model fitting or inspection of outcome associations. Domains included
depression characteristics, psychiatric and substance-use comorbidity, medical
comorbidity, prior antidepressant exposure and medication burden, prescribing
constraints, health care utilization, and sociodemographic and social-determinant
variables [18-21]. Only structured EHR fields available within the pre-index window
were used. Selection rationale is given in Supplement M4 and the complete
inventory in Multimedia Appendix 1.

**Both representations were built from the same curated field inventory, and
neither was built from a raw record.** Predictor selection happened once,
before either representation existed, and both then encoded that selection.
This bounds every comparison below: what is compared is two encodings of one
tailored record, not a tailored record against an untailored one. Each
patient's timeline-sliced record was converted independently into 2
representations. The typed feature representation (FEATURE) assigned explicit
data types to continuous variables, binary and multilabel indicators, and
nominal categorical variables. Continuous variables included age, utilization
and duration measures, medication burden, and counts of adequate antidepressant
trials, with an adequate trial defined as at least 42 days of continuous
exposure to an agent. After categorical expansion and exclusion of 3 vital-sign
variables for missingness, the FEATURE representation expanded to 92
columns.

For the embedded representation (EMBEDDED), the same pre-index record was
deterministically rendered as a human-readable Markdown narrative and encoded
as a fixed-length dense vector. The renderer walks a fixed template of section
headings and field labels, in a fixed order, over the fields named above.
Absent findings are printed explicitly and unrecorded ones as a literal token,
so every patient reaches the encoder through the same constant form. Narrative
construction used predefined rules and no generative model, ensuring that every
statement was traceable to the structured record. That guarantee is worth the loss of fluency, because a generated summary
introduces statements the record does not support at measured rates [22] and
here the narrative *is* the predictor. Four pretrained sentence-transformer
encoders were evaluated independently: `bge-small-en-v1.5` [23], `bge-en-icl`
[24], `Qwen3-Embedding-4B`, and `Qwen3-Embedding-8B` [25], with
`Qwen3-Embedding-8B` designated as the primary encoder.

FEATURE and EMBEDDED do not receive an identical field inventory, so a
head-to-head comparison estimates the two complete pipelines rather than the
isolated effect of data format. Both were derived from the same temporal slice and the same selected
fields. Eleven of the crosswalk's twenty-eight rows are encoded
asymmetrically. In ten of the eleven the narrative receives information
the feature vector does not, either a field with no column or a value
the feature vector coarsens. Supplement S8 gives the crosswalk row by row, with each field's
encoding on both sides. Supplement M5 states the full encoding rules and
Supplement S4 reproduces two example narratives. The asymmetry is what bounds
the comparison, and the crosswalk is what makes that bound checkable.

## Missing data and sample partition
<!-- TRIPOD+AI 8 (sample size), 9 (missing data), 12a (partition) -->

No statistical imputation was performed. Mean body mass index and mean systolic
and diastolic blood pressure were excluded because of substantial and
outcome-associated missingness. Missing categorical values were retained as an
explicit category in FEATURE and as the literal token "Missing" in EMBEDDED. No
missing continuous values reached the estimators. Detailed missingness
frequencies and rationale are provided in Supplement M6.

We created one stratified 80:20 train-test split and used it for every
evaluation arm. The training set comprised 34,063 patients, including 5,964
TRD-positive patients (17.5%). The held-out test set comprised 8,516 patients,
including 1,491 TRD-positive patients (17.5%). Across 100 predictor rows, the
maximum absolute standardized mean difference between the 2 sets was 0.036. For
retrieval analyses, only training patients were placed in the searchable
neighbor pool. Test patients served solely as query anchors, which prevents
self-retrieval and any use of a test outcome as a neighbor label.
Events-per-variable calculations and further leakage safeguards appear in
Supplement M7-M8.

## Model development
<!-- TRIPOD+AI 10 (model development), 11 (analysis methods) -->

**Standard machine learning.** Logistic regression, random forest, gradient
boosting, and XGBoost classifiers were trained separately on each
representation. For FEATURE, a column transformer standardized continuous
variables, one-hot encoded categorical variables while ignoring unseen levels at
inference, and cast Boolean variables to integers. EMBEDDED was processed as an
all-numeric block. Preprocessing and estimation were combined within a single
pipeline and tuned using 5-fold cross-validated grid search in the training set,
optimizing area under the receiver operating characteristic curve (ROC AUC). On
every fold, fitted preprocessing parameters and category vocabularies were
estimated from that fold's training rows only. The best cross-validated
estimator was refit on the full training set and generated probabilities for the
untouched test set (Supplement M9).

**Neighbor-weighted retrieval prediction.** For EMBEDDED only, we also
estimated risk without fitting a model, as the weighted mean of TRD
labels among K = 50 retrieved training-set neighbors. This tests the
digital-twin premise directly: if a patient's course can be read from
the courses of their closest analogues, retrieval should predict well.
Retrieval schemes selected the nearest or the random training patients,
with random retrieval as the negative control. Weighting was uniform or
based on anchor-neighbor cosine similarity. Detailed equations, retrieval controls, and the evaluation grid are provided in Supplement M10 and M12.

**Semantic-feature ablation.** To estimate direct reliance of the embedded
pipeline on selected concepts, we permuted 1 narrative section or field at a
time across patients, re-embedded the perturbed narratives, and applied the
already-trained classifiers without retraining. Permutation preserved each
concept's marginal distribution while severing its patient-level association
with outcome. The tested concepts were psychiatric history, medication burden,
prior treatment exposure, treatment contraindications, race/ethnicity, and
social determinants of health. Change in ROC AUC relative to the unperturbed
model quantified direct-input reliance. This analysis was not designed to
establish fairness, rule out reconstruction of a permuted concept from
correlated fields, or evaluate subgroup calibration. Specifications, including
what each concept's permutation destroys, are provided in Supplement M11.

## Statistical analysis and performance metrics
<!-- TRIPOD+AI 11, 12 (evaluation) -->

Performance in the held-out test set was characterized using ROC AUC,
calibration slope and intercept, and sensitivity, specificity and the positive
and negative likelihood ratios at the threshold maximizing the Youden J
statistic. That threshold was selected and evaluated in the same test set, so operating-point
estimates are descriptive and optimistic rather than deployable clinical
thresholds. Calibration estimates apply to the case-enriched cohort's outcome
frequency and were not recalibrated to population prevalence.

An interval containing zero means no difference was detected, not that
the two representations are equivalent. No equivalence or noninferiority
margin was set in advance, so this paper makes no equivalence claim
anywhere.

Confidence intervals come from 1,000 nonparametric bootstrap resamples
of the test-set patients, detailed in Supplement M13. The subgroup
analysis computes 240 between-group contrasts, so its P values are
adjusted across that whole set by the Benjamini-Hochberg procedure,
controlling the false discovery rate at 5%.

Comparisons between two prediction vectors are paired. Each bootstrap
draw scores both prediction vectors on the same resampled patients
before their difference in ROC AUC is taken, which keeps the patient
draw out of the comparison. Classifier-matched contrasts hold the
learner fixed and vary only the representation. The
best-feature-versus-best-embedded comparison was chosen after the
results were in, so it is descriptive rather than a test. Retrieval
against the trained classifiers is reported as marginal rather than
paired intervals. Pairing would narrow those intervals, so reporting
them unpaired is the conservative choice.

## Reproducibility and software
<!-- TRIPOD+AI 13 (availability) -->

All random processes were seeded. Analyses were implemented in Python using
scikit-learn [26], XGBoost [27], and sentence-transformer encoders [28]. The
analysis code is publicly available [29].
