<!--
RESERVE DRAFT — not the submitted manuscript.

This is a PROSE redraft of manuscript.md. Every claim, every number and every citation
is carried over unchanged; what changed is the sentences. The science was not in
question. The prose was: the submitted draft's body ran a mean of 28.8 words per
sentence with 28% of sentences past 35 words, 22 of them past 55, and the longest at
133. Reviewers had already said the paper was hard to follow.

Produced with Paper-Writer (../../../Paper-Writer). Every section below passes its
deterministic gates: sentence density, paragraph shape, terminology lock, evidence-backed
numbers, and citation resolution. The evidence ledger holding every quotable figure is
reserve/evidence_ledger.json, built from results/ and notebooks/figures/.

WHAT THE GATES SAY ABOUT THIS DRAFT vs THE SUBMITTED ONE
                       submitted    this draft
  mean words/sentence       28.8          16.5
  share over 35 words        28%          2%
  longest sentence           133          47
  semicolons per 1,000       9.5          0.2
  em-dashes per 1,000        7.2          0.0

Generated 2026-09-05. Keep in reserve pending reviewer feedback.
-->

# Abstract

**Background.** As many as 1 in 3 patients with major depressive disorder (MDD) fail
successive antidepressant trials and progress to treatment-resistant depression (TRD)
[1]. That group carries a disproportionate share of the clinical and economic burden of
depression. Identifying those patients at the point of first treatment could support a
decision to escalate sooner. Two things are unsettled. Whether the structural elements
of an electronic health record (EHR) carry enough signal to do so at all. And whether a
pretrained transformer encoder extracts more of that signal than a transparent set of
coded fields does.

**Objective.** To measure how well EHR-derived patient representations predict a
treatment-switch-defined proxy for incident TRD at a patient's index antidepressant
prescription. We compare a typed feature representation against a pretrained
transformer embedding of the same record.

**Methods.** We assembled a retrospective cohort of 42,579 adults with unipolar MDD from
one community health system, excluding bipolar and schizophrenia-spectrum diagnoses.
TRD was operationalised as three or more antidepressant treatments within one year of
the index date, following Forthman et al [20]. The index date is the earliest
antidepressant prescription recorded on or after a patient's first documented
depression diagnosis. No property of the index depends on post-index data. Each record
was truncated at the index date and rendered two ways. The feature representation is a
typed vector of coded fields. The embedded representation is a Markdown narrative
written by fixed rules, with no generative model involved, encoded by a pretrained
sentence-transformer. Four encoders were evaluated and `Qwen3-Embedding-8B` is primary.
Four classifiers were tuned by cross-validated grid search on each representation:
logistic regression, random forest, gradient boosting, and XGBoost. All were evaluated
once, on a held-out stratified 20% split of 8,516 patients containing 1,491
TRD-positive cases. We also fitted a neighbour-weighted predictor on the embeddings.
To locate the signal, we permuted individual narrative concepts and re-scored. We
report discrimination, calibration, and a descriptive operating point with bootstrap
confidence intervals. The study follows TRIPOD+AI [10].

**Results.** Discrimination was modest, and neither representation was better than the
other. The best embedded model was logistic regression at ROC AUC 0.657 (95% CI
0.643-0.672). The best feature model was XGBoost at 0.649 (0.634-0.664). Their paired
difference was +0.008 (95% CI -0.003 to +0.019), an interval that includes zero. Holding
the classifier fixed tells a sharper story. The embedding helped logistic regression by
+0.028 (0.017 to 0.039) and hurt every tree ensemble, by -0.013 to -0.022. Representation
and learner are therefore not separable choices. Logistic regression was the strongest
embedded classifier under all four encoders, across a narrow band of 0.645 to 0.657,
and the smallest encoder trailed the largest by 0.013 despite using a tenth as many
dimensions. The fitted model was sparse: 385 of 4,096 coefficients were non-zero. The
neighbour-weighted predictor confirmed that the embedding space is organised around the
outcome. Nearest-neighbour retrieval reached 0.593, random retrieval 0.494 to 0.517, and
farthest-neighbour retrieval inverted to 0.434. All three stayed below the trained
classifiers. Permutation localised the signal to three concepts. Psychiatric history
cost -0.028 (-0.039 to -0.017), medication burden -0.027 (-0.037 to -0.018), and prior
treatment exposure -0.019 (-0.027 to -0.011). Permuting race, social determinants, or
treatment contraindications cost nothing measurable.

**Conclusions.** Structured EHR data carry a modest, real signal for a
treatment-switch-defined TRD proxy at the index antidepressant prescription. A
pretrained transformer embedding of a deterministic narrative matched a transparent
feature representation and did not beat it. Neither model's predictions depended on its
race or social-determinant inputs, though we did not assess whether the outcome label
itself is equitable, so no fairness conclusion follows. At ROC AUC near 0.65 the models
are too weak for clinical use. Temporal and external validation would both be required
before any clinical role could be considered.

# Introduction

Major depressive disorder is among the most prevalent and disabling medical conditions,
and antidepressant pharmacotherapy is its first-line treatment. A substantial minority
of patients never reach remission despite successive adequate trials. Those patients are
described as having treatment-resistant depression, most commonly operationalised as
failure of at least two antidepressant trials at adequate dose and duration [2]. The
sequential-treatment literature anchored by STAR\*D established why that matters:
remission rates fall sharply at each successive step, so a patient entering a third or
fourth step faces a markedly lower chance of recovery [3]. TRD accordingly accounts for
a disproportionate share of the morbidity, functional impairment and cost attributable
to depression [1].

The escalation options all become less likely to work as resistance develops.
Augmentation, combination, switching class, and neuromodulation are each more necessary
and less effective the later they arrive. That asymmetry is the reason for a long
interest in identifying high-risk patients early. A patient flagged at their index
antidepressant prescription could in principle be monitored more closely and escalated
sooner, which is the clinical use such a model would have.

An electronic health record (EHR) rarely records standardised symptom change or treatment
adequacy. Studies therefore operationalise TRD from observable medication trajectories
instead. These computable phenotypes make large-scale analysis possible, and they are
not the same thing as symptom-confirmed non-response. Varying the operational rules
materially changes both TRD prevalence and cohort composition [25-27]. Any result
obtained against such a label is a result about the label as much as about the illness.

Structural EHR elements do encode illness burden and care pathway. Early models built
from demographics, utilisation and history reported high internal discrimination, at
ROC AUC 0.83 [28]. Independent external validation of that class of model is more
conservative, at 0.652 [29]. Adding clinical notes raises performance to 0.728, and
adding neuroimaging raises it further [30]. Tabular data are informative, in other
words, and they benefit from multimodal integration. A multi-system evaluation
nevertheless found poor external generalisation, at ROC AUC 0.51 to 0.58 [31].

That gap between internal and external performance points at a specific methodological
vulnerability. A model can reconstruct the operationalised treatment-history label
rather than identify a distinct liability to resistance, and it will do so whenever
temporal separation between the prediction index and the forecast window is not
enforced [25,27,28,31]. Structural EHR features are therefore candidates for risk
stratification rather than deployable tools. A credible model has to enforce that
separation, evaluate transportability, test whether structural features beat simpler
medication rules, and keep the distinction between a computable proxy and verified
non-response visible throughout [27,29-31].

Two considerations motivate this study. The first is the representational capacity of
generalised pretrained transformer embeddings. Purpose-built EHR foundation models
demand data and compute at a scale most groups cannot reach [21,22]. Serialising a
record into text and embedding it with a general-purpose language model is a cheap
alternative, and it has proved competitive across clinical prediction tasks [9]. It has
not been compared directly against a transparent feature representation for TRD
prediction. Nor has anyone asked whether its predictive signal rests on clinically
appropriate content. The second consideration is appraisal. We report this study in full
accordance with TRIPOD+AI, the reporting guideline for prediction models developed with
regression or machine-learning methods [10].

This study asked whether EHR-derived patient data predict an EHR-operationalised
definition of TRD within one year. It addressed three objectives in sequence. First, we
compared a typed feature representation against an embedded representation of the same
records, evaluating both with four standard classifiers on one cohort and one held-out
split. Second, we tested how far that comparison depends on the encoder, using four
sentence-transformers, and examined the geometry of the resulting space with a
neighbour-weighted predictor. Third, we located the predictive signal by permuting
individual clinical concepts and re-scoring. That third objective is the one that
establishes clinical plausibility: it asks whether the models rely on coherent clinical
content rather than on sociodemographic variables. Passing it is necessary for equitable
performance and it is not sufficient.

# Methods

## Study design and data source

We conducted a retrospective cohort study on a frozen, de-identified extract from the
Epic EHR of Saint Francis Health System, a community health system in Tulsa, Oklahoma.
The extract carried person, encounter, diagnosis, medication, procedure,
laboratory and flowsheet, and medication-to-RxNorm mapping tables. Patient and encounter
identifiers were replaced with one-way hashes before transfer. No direct identifiers and
no dates of birth were provided.

The extract is case-enriched rather than a census, and that shapes what its proportions
mean. Every patient with a depression code on the problem list was retained, alongside a
random sample of unflagged patients at roughly 4:1. The extract held 501,718 patients:
100,420 (20.0%) with a problem-list depression flag and 401,298 (80.0%) without.
Eligibility for the analytic cohort was decided from encounter-level diagnoses rather
than from that sampling flag, so 12,530 of the 42,579 eligible patients (29.4%) entered
through the random arm. Cohort proportions therefore describe this enriched sample and
are not health-system prevalence estimates. The head-to-head comparison is unaffected,
because both representations come from the same patients and are scored on the same
held-out split.

All analyses used data version DV260629v1 and patient version PV260710v1. Source files
were cut on June 29, 2026 and analysis-ready tables were built on July 10, 2026. No
later refresh entered the study. Index dates span 2016 to 2024. This is a random
internal validation split from one source and one period, which is neither temporal nor
external validation. Supplement M1-M2 gives the source tables, setting, sampling frame,
diagnosis code sets and data versions.

## Participants, index date, and temporal windows

Patients entered the cohort on six criteria. They needed a qualifying MDD diagnosis, no
bipolar or schizophrenia-spectrum diagnosis, an eligible antidepressant index
prescription, an MDD diagnosis on or before that prescription, at least 730 days of
pre-index history, and at least 365 days of post-index follow-up. Those criteria yielded
42,579 patients. Supplement M2 reports the full cascade and every rejection reason.

The index date is the start date of the earliest antidepressant prescription recorded on
or after a patient's first documented depression diagnosis. Each patient contributes one.
The prediction point coincides with the prescription date, and index eligibility depends
on no subsequent dose, duration, response or treatment change. Predictors were computed
only inside the 730-day lookback window ending at the index date. Post-index data enters
in exactly two places: confirming 365 days of follow-up, and ascertaining the outcome
across those days. Prior antidepressant exposure was kept as a predictor rather than used
as an exclusion, so the index prescription is the first antidepressant linked to a
documented depression diagnosis in the available record. It is not necessarily a
patient's first lifetime exposure or first adequate trial. Figure 1 shows the temporal
design and Supplement M2 gives the index-selection rules.

## Outcome

The prediction target is a predefined EHR proxy for incident TRD, generated upstream and
used without modification. Following the operational definition of Forthman et al [20],
a patient with MDD is TRD-positive if they received at least 3 distinct antidepressant
treatments during the 365 days after the index date, counting the index agent as the
first. That is equivalent to requiring at least 2 post-index changes. A treatment is a
distinct agent rather than a prescribing event. Augmentation without replacement does not
increment the count, and neither does restarting a previously used agent. Augmentation
instead enters the study as a pre-index predictor.

This is a treatment-switch proxy and not direct evidence of inadequate response to 2
adequate trials [2,3]. Symptom response was not systematically available, and neither
dose nor duration adequacy was verified for the counted treatments. A switch may reflect
non-response. It may equally reflect intolerance, adverse effects, cost, insurance
constraints, fragmented care, patient preference or prescriber habit. It also depends on
continuity of care and access, both of which differ across demographic groups [18,19].
The label was never validated against chart review or a standardised symptom measure.
Supplement M3 sets out these inferential boundaries and the validation analyses we
propose.

## Predictors and patient representations

Predictors were specified a priori, on clinical and prior-literature grounds, before any
model was fitted and before any outcome association was inspected. The domains are
depression characteristics, psychiatric and substance-use comorbidity, medical
comorbidity, prior antidepressant exposure and medication burden, prescribing
constraints, health-care utilisation, and sociodemographic and social-determinant
variables [4-7]. Only structured EHR fields available inside the pre-index window were
used. Supplement M4 gives the selection rationale and Multimedia Appendix 1 the complete
inventory.

Each patient's timeline-sliced record was converted independently into two
representations. The feature representation assigns explicit data types to continuous
variables, to binary and multilabel indicators, and to nominal categorical variables.
Its continuous variables include age, utilisation and duration measures, medication
burden, and counts of adequate antidepressant trials, where an adequate trial is at
least 42 days of continuous exposure to one agent. After categorical expansion, and
after excluding 3 vital-sign variables for missingness, the feature matrix holds 92
columns.

The embedded representation renders the same pre-index record as a human-readable
Markdown narrative and encodes it as a fixed-length dense vector. Narrative construction
uses predefined rules and no generative model, so every statement is traceable to the
structured record. That guarantee costs fluency and is worth it, because a generated
summary introduces statements the record does not support at measured rates [23] and
here the narrative is the predictor. Four pretrained sentence-transformer encoders were
evaluated independently: `bge-small-en-v1.5` [12], `bge-en-icl` [13],
`Qwen3-Embedding-4B`, and `Qwen3-Embedding-8B` [14]. `Qwen3-Embedding-8B` is the primary
encoder. The two representations come from the same temporal slice and do not hold
identical field inventories, so a head-to-head comparison estimates the performance of
two complete pipelines rather than the isolated effect of data format. Supplement S11 is
the field-level crosswalk, Supplement M5 the encoding rules, and Supplement S6 two
example narratives.

## Missing data and sample partition

No statistical imputation was performed. Mean body mass index and mean systolic and
diastolic blood pressure were excluded for substantial, outcome-associated missingness.
Missing categorical values were kept as an explicit category in the feature
representation and as the literal token "Missing" in the embedded representation. No
missing continuous value reached an estimator. Supplement M6 gives the missingness
frequencies and the rationale.

We created one stratified 80:20 train-test split and used it for every evaluation arm.
The training set holds 34,063 patients, of whom 5,964 are TRD-positive (17.5%). The
held-out test set holds 8,516 patients, of whom 1,491 are TRD-positive (17.5%). Across
100 predictor rows the largest absolute standardized mean difference between the two
sets is 0.036. For the retrieval analyses only training patients entered the searchable
neighbour pool, and test patients served solely as query anchors. That prevents both
self-retrieval and the use of any test outcome as a neighbour label. Supplement M7-M8
covers events-per-variable and the remaining leakage safeguards.

## Model development

Logistic regression, random forest, gradient boosting and XGBoost were trained
separately on each representation. For the feature representation a column transformer
standardised continuous variables, one-hot encoded categorical variables while ignoring
unseen levels at inference, and cast Booleans to integers. The embedded representation
was processed as an all-numeric block. Preprocessing and estimation sat inside one
pipeline and were tuned by 5-fold cross-validated grid search on the training set,
optimising ROC AUC. On every fold, fitted preprocessing parameters and category
vocabularies came from that fold's training rows alone. The best cross-validated
estimator was refit on the full training set and produced probabilities for the untouched
test set. Supplement M9 gives the grids.

We also estimated risk on the embedded representation as a weighted mean of TRD labels
among retrieved training-set neighbours. Weighting was uniform, by cosine similarity, by
an outcome-blind clinical-similarity score from `MedGemma-27B` [15], or by the harmonic
mean of the last two. Retrieval schemes selected the nearest, farthest, or random
neighbours, or the nearest within a randomly subsampled candidate pool. The judge
compared deterministic narratives under a fixed 6-domain rubric and returned a structured
0-100 similarity score, rescaled to 0-1. It never received or predicted patient outcomes.
No human-rated pairs exist to calibrate it, so no judge-derived quantity is reported as
an accuracy claim [24]. Supplement M10 gives the equations, prompts and retrieval
controls, and Supplement S1 the verbatim rubric.

The semantic-feature ablation estimates how far the embedded pipeline relies directly on
a given concept. We permuted one narrative section or field at a time across patients,
re-embedded the perturbed narratives, and applied the already-trained classifiers without
retraining. Permutation preserves each concept's marginal distribution and severs its
patient-level association with the outcome. The tested concepts are psychiatric history,
medication burden, prior treatment exposure, treatment contraindications, race and
ethnicity, and social determinants of health. The change in ROC AUC against the
unperturbed model quantifies direct-input reliance. This analysis does not establish
fairness, does not rule out reconstruction of a permuted concept from correlated fields,
and does not evaluate subgroup calibration. Supplement M11 records what each
permutation destroys and Supplement M12 the coverage of every arm.

## Statistical analysis and performance metrics

Test-set performance is characterised by ROC AUC, by calibration slope and intercept, and
by sensitivity, specificity and likelihood ratios at the threshold maximising Youden's J.
That threshold was chosen and evaluated in the same test set, so the operating-point
estimates are descriptive and optimistic rather than deployable. Calibration estimates
apply to this case-enriched cohort's outcome frequency and were not recalibrated to
population prevalence.

Confidence intervals come from nonparametric bootstrap resampling of test-set patients.
Differences in ROC AUC, both between unperturbed and ablated models and between the two
representations, were evaluated by paired bootstrap: each draw used the same resampled
patients for both prediction vectors before the difference was computed.
Classifier-matched contrasts hold the learner fixed and vary the representation. The
best-versus-best comparison is post hoc and is treated as descriptive. We prespecified no
equivalence or non-inferiority margin, so an interval containing zero is read as absence
of evidence for superiority rather than as evidence of equivalence. Supplement M13 gives
the remaining detail.

## Reproducibility and software

All random processes were seeded. Analyses were implemented in Python with scikit-learn
[16], XGBoost [17], and sentence-transformer encoders [11]. Analysis code is available at
[https://github.com/Pirate-Hunter-Zoro/TRD-EHR](https://github.com/Pirate-Hunter-Zoro/TRD-EHR).

# Results

## Participant flow and cohort characteristics

The eligibility cascade reduced 501,718 extracted patients to 42,579 analysed ones. The
MDD requirement removed the largest block, leaving 144,110. Excluding bipolar and
schizophrenia-spectrum diagnoses left 124,188, and requiring an antidepressant index
left 107,636. Requiring the MDD diagnosis to precede that index left 103,458. The two
window requirements were the next largest losses: 730 days of pre-index history left
54,215, and 365 days of post-index follow-up left the final 42,579. Supplement M2 gives
the cascade in full.

Of those 42,579 patients, 7,455 met the TRD proxy, a rate of 17.5%. The cohort is
predominantly female, at 30,850 women against 11,728 men. TRD rates differ modestly by
sex, at 18.0% in women and 16.2% in men. Median age is 55 years and TRD-positive
patients are younger, with a mean of 51.4 years against 55.1 in TRD-negative patients.
Table 1 gives the full cohort description.

The training and test sets are comparable on every measured predictor. Across 100
predictor rows the largest absolute standardized mean difference between them is 0.036,
well inside any conventional imbalance threshold. That comparability is a property of
the stratified split rather than a finding, and it is reported so a reader can rule out
allocation imbalance as an explanation for anything below.

## Discrimination

Neither representation discriminated better than the other. The best embedded model was
logistic regression, at ROC AUC 0.657 (95% CI 0.643-0.672). The best feature model was
XGBoost, at 0.649 (0.634-0.664). Their paired difference was +0.008 (95% CI -0.003 to
+0.019). That interval contains zero, so the comparison provides no evidence that either
pipeline is superior. It is also not evidence of equivalence, because no equivalence
margin was prespecified.

Holding the classifier fixed produces a sharper and more interesting picture than the
headline comparison does. The embedding helped logistic regression substantially, by
+0.028 (0.017 to 0.039). It hurt every tree ensemble: random forest by -0.022
(-0.033 to -0.011), gradient boosting by -0.013 (-0.026 to -0.001), and XGBoost by
-0.013 (-0.025 to -0.002). Every one of those four intervals excludes zero. Representation
and learner are therefore not separable choices, and reporting either one alone would
misdescribe the result.

That pattern is what a 4,096-dimensional dense block does to two different model
families. A regularised linear model handles that geometry well, and axis-aligned trees
splitting on individual embedding dimensions handle it badly. The practical implication
runs the other way from the usual intuition: the embedded representation does not need a
more powerful learner, it needs a simpler one.

Absolute discrimination is modest under every combination. Across the eight
representation-by-classifier cells the range runs from 0.623 to 0.657. Discrimination
near 0.65 places these models well below the internal figures reported for structured-EHR
TRD models, at 0.83 [28], and close to the external-validation figure of 0.652 [29].

## Calibration and operating characteristics

Calibration was adequate for the best embedded model and did not distinguish the
representations. Embedded logistic regression had a calibration slope of 1.272 and an
intercept of -0.069, indicating slight under-dispersion of predicted risk. Its weighted
calibration error was 0.010 and its Brier score 0.137. The best feature model reached a
Brier score of 0.138. Table 3 gives slope and intercept for every classifier and
Supplement S4 the full calibration metrics.

Precision-recall performance tracks discrimination and is the more informative view at
this outcome frequency. Embedded logistic regression reached AUPRC 0.302 against a
positive rate of 17.5%, and the best feature model reached 0.298. Both represent a real
but small improvement over the prevalence baseline.

## Encoder robustness

The comparison does not depend on which encoder produced the embedding. Logistic
regression was the strongest embedded classifier under all four, and the best embedded
ROC AUC spans a narrow band from 0.645 to 0.657. `Qwen3-Embedding-8B` led at 0.657,
followed by `bge-en-icl` at 0.655, `Qwen3-Embedding-4B` at 0.655, and `bge-small-en-v1.5`
at 0.645.

Encoder scale bought almost nothing. The smallest encoder produces 384 dimensions and the
largest produces 4,096, a factor of more than ten, and the resulting discrimination
differs by 0.013. Whatever signal the narrative carries is evidently accessible to a
small general-purpose encoder, which matters for anyone deciding what to run this
pipeline on.

## Where the signal is

The fitted embedded model is sparse rather than diffuse. L1-penalised logistic regression
retained 385 non-zero coefficients out of 4,096, so roughly one dimension in eleven
carries the model's weight. A representation that spread its signal evenly across four
thousand dimensions would be far harder to interrogate than this one turned out to be.

Permutation localised that signal to three clinical concepts. Permuting psychiatric
history cost -0.028 in ROC AUC (95% CI -0.039 to -0.017). Permuting medication burden
cost -0.027 (-0.037 to -0.018), and permuting prior treatment exposure cost -0.019
(-0.027 to -0.011). All three intervals exclude zero. These are the three concepts a
clinician would expect to matter for treatment resistance, which is the result the
analysis was designed to be able to fail.

Three other concepts cost nothing measurable. Permuting treatment contraindications cost
-0.002 (-0.004 to +0.001), permuting social determinants cost -0.000 (-0.001 to +0.000),
and permuting race and ethnicity cost -0.000 (-0.002 to +0.002). Every one of those
intervals contains zero. The model's predictions therefore do not depend on its race or
social-determinant inputs in any measurable way.

That last finding needs its boundary stated with it. The ablation permutes an input and
re-scores; it does not rule out reconstruction of a permuted concept from correlated
fields, it does not evaluate subgroup calibration, and it says nothing about whether the
outcome label is itself equitable. It establishes that the model does not read these
fields directly. It does not establish that the model is fair.

## Neighbour-weighted prediction

The embedding space is organised around the outcome, and weakly. A neighbour-weighted
predictor using nearest-neighbour retrieval reached ROC AUC 0.593. Random retrieval
reached 0.494 to 0.517 depending on the weighting, which is chance. Farthest-neighbour
retrieval inverted to 0.434, below chance, which is what a genuine outcome gradient
predicts and what a spurious one would not produce.

Retrieval scheme dominated weighting strategy throughout. The four weightings within
nearest-neighbour retrieval span 0.593 to 0.595, a range narrower than the difference
between any two retrieval schemes. The clinical-similarity judge therefore bought nothing
over plain cosine distance on this task, and no judge-derived quantity is reported as an
accuracy claim.

Every neighbour-weighted variant stayed below the trained classifiers. Retrieval confirms
that similar records carry similar outcomes and it is not a competitive predictor, so the
trained models are extracting something retrieval alone does not reach.

# Discussion

## Principal findings

EHR-derived patient representations carried modest but measurable signal for a
treatment-switch proxy for subsequent TRD, measured at the index antidepressant
prescription. An embedded representation classified by logistic regression discriminated
essentially as well as the best feature model, at ROC AUC 0.657 against 0.649. Both
representations scored the same held-out patients, so the paired bootstrap is the
relevant comparison, and it gave a difference of +0.008 (95% CI -0.003 to +0.019). The
result supports parity rather than superiority.

Parity here should not be read as evidence that narrative embedding added clinical
information. Both representations were generated from the same pre-index structured
record, so there was no new information available to either. What the result shows is
narrower and still useful: a general-purpose encoder can reorganise the available
structural signal into a dense space without materially degrading discrimination. That
is a claim about representation, not about content.

Representation and learner turned out to be interacting choices rather than separable
components. Logistic regression was the strongest embedded classifier under all four
encoders and the best model overall under the primary one. The classifier-matched
contrasts show why that matters: the embedding beat the feature representation with
logistic regression by +0.028 and lost to it with all three tree ensembles, by -0.013 to
-0.022. Dense latent coordinates suit a regularised linear combination. One-coordinate
tree splits no longer operate on individually meaningful clinical variables, which is
what those coordinates stop being.

We are careful about how far that reads. The pattern is consistent with a decision
boundary a regularised linear model captures efficiently. It does not establish that the
latent clinical structure is intrinsically linear, because differences in
regularisation, dimensionality and inductive bias all offer alternative explanations for
the same ordering.

The fitted model used a restricted portion of its nominal input space. It assigned
non-zero coefficients to 385 of 4,096 dimensions, and roughly 80% of the total absolute
coefficient mass fell inside 179 of them. Fewer than 5% of the available latent
dimensions therefore carry most of the fitted magnitude. That concentration narrows the
gap between nominal input dimension and fitted model complexity, and it makes the
events-per-variable concern less severe than a raw count of 4,096 inputs implies. It
does not remove the concern. The selected directions may be unstable across resamples or
sites, and coefficient magnitude confers neither semantic interpretability nor evidence
that these directions track distinct clinical processes.

## Clinical interpretation

The ablation localised direct-input reliance to psychiatric history, medication burden,
and prior treatment exposure. Those are the three concepts a clinician would nominate in
advance, and the analysis was constructed so that it could have returned a different
answer. Permuting race and ethnicity or recorded social determinants produced no
measurable loss of discrimination.

The claim that supports is deliberately narrow. Under the tested perturbations, the
fitted embedded pipeline did not rely materially on these direct sociodemographic inputs
for overall discrimination. That is not a fairness result and should not be reported as
one. The analysis does not determine whether demographic information is indirectly
recoverable from diagnosis, medication or utilisation patterns. It does not determine
whether access-dependent treatment switching produces inequitable labels. Those are
different questions and they need different designs.

The neighbour-weighted predictor was informative about geometry rather than competitive
as a model. Nearest-neighbour retrieval discriminated markedly better than random
retrieval, which demonstrates that proximity in the embedding is associated with TRD
risk. Retrieval choice mattered far more than weighting choice throughout. Every variant
stayed below the trained classifiers, at roughly 0.59 against roughly 0.66, so we read
retrieval as evidence of label-informative local geometry rather than as a prediction
method worth deploying.

## Comparison with prior work

Clinical-trial, registry and EHR studies have generally shown only modest separation for
treatment resistance or antidepressant response [4-8]. The structural-EHR literature
nonetheless argues against treating ROC AUC near 0.65 as a universal ceiling. Reported
discrimination varies with the phenotype definition, the prediction horizon, how close
the predictors sit to the treatment trajectory, which modalities are available, and
whether evaluation is internal or external.

The high end of that range comes with a caveat about what was predicted from. Liberman
and colleagues linked claims and EHR data from 35,246 adults initiating antidepressant
treatment and reported ROC AUC 0.83 for incident TRD over 24 months [28]. Their
predictors included psychiatric visits, nurse contacts, prescription volume,
antidepressants attempted, anticonvulsant use, suicidality, insomnia, hypertension, and
time from diagnosis to treatment. Those features combine illness burden with the
structure and intensity of care itself.

Externally validated estimates sit much lower. Lage and colleagues reported ROC AUC
0.652 (95% CI 0.623-0.682) with a top-quintile lift of 1.99 [29]. A smaller single-site
multimodal study found structured EHR data alone reaching 0.684, clinical notes alone
0.569, and the two combined 0.728, with imaging adding more [30]. Structural data
evidently contain meaningful signal, and genuinely incremental modalities can complement
it. Neither result establishes that converting the same structural content into text
adds information.

Transportability looks like the more consequential constraint. In a three-health-system
study, internal ROC AUCs of 0.58 to 0.64 fell to 0.51 to 0.58 under external validation,
precision-recall performance was low, and patient-level risk estimates agreed poorly
across sites [31]. Against that background the figure reported here is most comparable
to the externally validated and single-site structural estimates. Our figure is evidence neither of a new
ceiling nor of an improvement. Higher performance elsewhere may
reflect richer or more proximal care-process variables, different windows and outcome
rules, or internal rather than external evaluation.

The contribution of this study is therefore representational and analytic rather than a
new level of discrimination. Inside a like-for-like comparison using the same patients,
the same temporal cutoff, the same source record, the same outcome and the same held-out
split, a general-purpose transformer embedding preserved the clinically coherent signal
available to a transparent feature representation. The learner interaction, the sparse
concentration of coefficient mass, the ablation and the retrieval analyses each
characterise how that signal is organised. None of them shows that the embedding
captures a biological liability to treatment resistance, or that it improves a clinical
decision over a simpler structural model.

## Limitations

The outcome is the first limitation and the largest. It is a treatment-switch proxy, not
verified inadequate response to adequate trials. Dose and duration adequacy were not
confirmed for the counted treatments, and symptom measures were not systematically
available. A switch may reflect intolerance, cost, insurance constraints, fragmented
care, preference or prescriber habit as readily as non-response. Because switching
depends on continuity of care and access, which differ across groups [18,19], the label
may itself be inequitably distributed. We did not assess that, so no fairness conclusion
follows from the ablation result above.

The design is internal validation from one health system and one period. Index dates
span 2016 to 2024 and the split is random rather than temporal. Nothing here therefore
speaks to transportability, which is where this class of model degrades most [31]. The cohort is also case-enriched by construction, so its
proportions are not health-system prevalence and the calibration estimates apply to this
sample's outcome frequency rather than to a population.

Two smaller limitations affect specific claims. The operating point was chosen and
evaluated in the same test set, so its sensitivity and specificity are optimistic and
descriptive rather than deployable. And the two representations were derived from the
same temporal slice without identical field inventories, so the head-to-head comparison
estimates two complete pipelines rather than the isolated effect of data format.

## Implications for validation and clinical use

Discrimination near 0.65 does not justify clinical deployment. The next evaluation should
prioritise temporal and multisite external validation with the entire representation and
preprocessing pipeline frozen. Reporting should include calibration-in-the-large,
calibration slope, precision-recall measures at the target prevalence, subgroup
calibration and error rates, and decision-curve analysis at clinically credible
intervention thresholds. Because this cohort was case-enriched, calibration has to be
re-estimated in a sampling-representative population before any absolute risk estimate is
read clinically.

Incremental value should be tested against parsimonious baselines rather than only
against alternative architectures. The relevant comparators are outcome prevalence, age
and coded severity, prior medication history, and a compact set of psychiatric-comorbidity
and utilisation variables. A representation that does not beat those is not worth its
complexity, whatever it does against another neural model.

## Conclusions

An embedded representation and a feature representation extracted comparable predictive
signal from the same pre-index EHR record, and only when each was paired with a learner
suited to its geometry. The embedding's contribution was not higher discrimination. It
was the preservation and reorganisation of clinically coherent structural information in
a dense latent space, which is a smaller claim than it is often given credit for.

Set against prior structural-EHR work, discrimination near 0.65 is credible and
insufficient for clinical use. Four questions decide whether this line of work goes
anywhere. Whether the signal transports across health systems. Whether it adds value over
parsimonious care-history baselines. Whether it stays calibrated across subgroups. And
whether it predicts symptom-verified inadequate response rather than an access-dependent
and practice-dependent treatment trajectory.
