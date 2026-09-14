<!--
RESERVE DRAFT OF THE SUPPLEMENT — not the submitted supplement.md.

A PROSE redraft. Every claim, number, citation, table, figure, caption and verbatim
block is carried over unchanged; what changed is the sentences. The tables and the
verbatim artifacts were never retyped — they were spliced from supplement.md
programmatically, so no cell and no prompt can have been corrupted in transit.

WHAT IS *NOT* HERE, DELIBERATELY. This is the submitted supplement's content and only
that. Nothing was pulled in from the reserve folder: not the Limitations section
(limitations_reserve.md), not the matched-input parity report (matched_input_parity.md),
not the religion sensitivity report (religion_sensitivity.md), and not the condensed
Methods passages (methods_reserve.md). Those four are held out of the packet by
decisions on the record, and a prose redraft is not the place to reopen any of them.
Where the submitted supplement refers to one of those analyses — S11 on matched inputs,
M6 on religion — it refers to it exactly as it did before, as available from the
corresponding author.

WHAT THE GATES SAY, AGAINST THE SUBMITTED SUPPLEMENT
                       submitted    this draft
  mean words/sentence       25.5          16.8
  share over 35 words        21%           1%
  longest sentence           179          55
  semicolons per 1,000       7.2          0.1
  em-dashes per 1,000        8.1          0.0
  sections failing            24           0

Sentences, numbers, terminology and citations all pass. 300 checkable figures, every one
traceable to reserve/evidence_ledger.json.

ONE GATE DOES NOT PASS, and it is reported rather than engineered around. Paragraph
shape sits at 20% mis-shaped against a 15% ceiling, and all but one of those are
"too short". They are the definitional entries in M11, the one-line conclusions under
bulleted lists, and the labels on worked examples in S1 — blocks that are short because
a reference document is written in short blocks. The ceiling was calibrated for body
prose. Padding them to three sentences each would make the supplement worse, so it was
not done.

Produced with Paper-Writer (../../../Paper-Writer). Generated 2026-09-05.
Keep in reserve pending reviewer feedback.
-->

<!--
Supplementary material for the TRD prediction manuscript (manuscript.md).
Convert alongside the main text at submission: pandoc supplement.md -o supplement.docx.

Naming: the two representations are the feature representation and the embedded
representation. "Rule-based" is not an alias for either and must not appear here. The
NAMING block in manuscript.md carries the full rule.
-->

*Supplements M1-M13 are the **Supplementary Methods**. They carry the methodological
detail condensed out of the main text. Every statement in them is a fuller form of
something the Methods section states or points at, and nothing reported in the main text
depends on material appearing only here. Supplements S1-S12 are supporting analyses and
extended results.*

# Supplement M1. Source data, setting, and sampling frame

The study used a single de-identified extract from the Epic electronic health record
(EHR) of Saint Francis Health System. Seven files were delivered: person, encounter, diagnosis, medication, procedure
and laboratory/flowsheet tables, together with a medication-to-RxNorm mapping table. The
clinical tables came from the Caboodle enterprise data warehouse and the RxNorm mapping
from the Clarity reporting database. Body mass index and systolic and diastolic blood
pressure came from the laboratory/flowsheet table. Each table was delivered as a flat
file after patient and encounter keys had been replaced by one-way MD5 hashes, and was
transferred by secure file transfer protocol. No names, medical record numbers, direct
identifiers or dates of birth were included.

The delivering data team applied its own filters before we saw anything. The person
table was restricted to one administrative division of the health system and to patients
who were current, valid, non-test, non-historical, not recorded as deceased, and aged 18
to 110 years at extraction. Eligible source encounters were completed on or before the
extraction date, carried at least one associated diagnosis, and had an inpatient,
outpatient, observation or emergency patient class.

Investigators prespecified the diagnosis code lists. Depression comprised ICD-9 codes
296.2, 296.3, 300.4 and 311, or ICD-10 codes F32.\*, F33.\* and F34.1. Bipolar disorder
comprised ICD-9 codes 296.0 and 296.4-296.8, or ICD-10 codes F30.\* and F31.\*.
Schizophrenia-spectrum disorders comprised ICD-9 codes 295.\* and 298.\*, or ICD-10 codes
F20.\*, F23.\*, F25.\*, F28.\* and F29.\*.

The extract was assembled as a case-enriched sample rather than a census. Every patient
with a depression diagnosis on the problem list was retained, and a random sample of
unflagged patients was added at an approximate 4:1 unflagged-to-flagged ratio. The
remaining tables were then linked to the person table. The delivered extract held 501,718
patients: 100,420 (20.0%) with a problem-list depression flag and 401,298 (80.0%)
without.

Sampling used the problem list and eligibility used encounter-level diagnoses, and those
two sets are not nested. A depression code entered at a visit is a documented diagnosis
whether or not it ever reached the problem list, and in routine care the problem list is
frequently not updated. Of the 42,579 analysis-cohort patients, 12,530 (29.4%) qualified
through an encounter-level diagnosis while lacking the problem-list flag, and therefore
entered through the randomly sampled group.

Two consequences follow, and only one of them is a limitation. The analysis cohort is a
sample rather than an enumeration of the health system's patients with depression, so
cohort treatment-resistant depression (TRD) and subgroup proportions are not population
prevalence estimates. The paired
comparison between representations remains internally valid, because both were evaluated
in the same patients on the same held-out split.

The setting is a single community health system in Tulsa, Oklahoma, covering inpatient,
outpatient, observation and emergency care. Patients enter the cohort through routine
antidepressant prescribing across those settings rather than through psychiatric
specialty referral. The index prescription may be written in any of them.

# Supplement M2. Eligibility cascade, index selection, and temporal design

Eligibility was applied hierarchically to the full delivered extract. A patient needed
all six of:

- a qualifying major depressive disorder (MDD) diagnosis;
- no bipolar-disorder and no schizophrenia-spectrum diagnosis, to isolate unipolar
  depression;
- an eligible antidepressant index prescription;
- an MDD diagnosis recorded on or before the index date;
- at least 730 days of pre-index history;
- at least 365 days of post-index follow-up.

Patients failing a chronological or
observation prerequisite were assigned an explicit rejection reason, so the attrition
accounting is complete.

***Table M1.** Participant flow through the hierarchical eligibility filters. Each row
applies one additional filter to the survivors of the row above. The first row is the
delivered extract, a case-enriched sample by design (Supplement M1).*

| Stage | Remaining | Rejected at stage |
| --- | ---: | ---: |
| Delivered extract (4:1 case-enriched) | 501,718 | — |
| MDD-diagnosed | 144,110 | 357,608 |
| Not bipolar AND not schizophrenia-spectrum | 124,188 | 19,922 |
| Has antidepressant index prescription | 107,636 | 16,552 |
| Has MDD before index | 103,458 | 4,178 |
| ≥2 years pre-index history | 54,215 | 49,243 |
| ≥1 year post-index follow-up (final cohort) | 42,579 | 11,636 |

Upstream data preparation assembled, for each patient, every antidepressant order
beginning on or after the date of the first documented depression diagnosis. The earliest
start date in that set defined the index date, one per patient. Among candidate index
orders, 57.9% begin on the same date as the first recorded depression diagnosis.

No post-index property was used to qualify the index exposure. Dose adequacy, exposure
duration, subsequent response and treatment changes were all excluded from that decision,
so the prediction point is the moment the prescription is written. Post-index data
entered in only two places: the requirement for at least 365 days of follow-up, and
outcome ascertainment during those days. Predictors used only information inside the 730
days ending at the index date. Recorded history extends further back for many patients,
at a median of 1,792 days, and clinical content outside the fixed window was never read.
Total recorded history length was itself retained as a predictor.

Antidepressant exposure before the index date did not exclude a patient, and the
resulting numbers are worth stating plainly. The index is tied to the first documented
depression diagnosis rather than to the first antidepressant exposure. So 24.0% of the
cohort had some recorded pre-index antidepressant exposure, and 14.7% had at least one
pre-index course meeting the 42-day adequate-trial threshold. The index is therefore
best described as the first antidepressant prescription after a documented depression
diagnosis. It is not the first antidepressant treatment and not the first adequate
trial.

# Supplement M3. Outcome construction and inferential boundary

The binary outcome was generated in the upstream R data-preparation pipeline,
independently of the predictors, and supplied to the modelling workflow as a fixed
label. TRD was assigned when a patient with MDD received at least three distinct
antidepressant treatments within 365 days of the index date, counting the index agent as
the first. Patients with fewer than three were classified TRD-negative.

A treatment is a distinct antidepressant agent rather than an order or a prescribing
event. Adding a second agent while the current antidepressant continues is augmentation
and does not advance the count. Restarting a previously used agent does not advance it
either. Augmentation is available as a pre-index predictor wherever its definition is
met.

The 365-day follow-up requirement guarantees that every patient has the observation
window needed to determine the label. A negative label therefore reflects an absence of
further antidepressant treatments rather than an absence of observation. It does not
guarantee that care delivered outside the health system was captured.

The label approximates the consensus characterisation of TRD as inadequate response to at
least two antidepressant trials of adequate dose and duration [2,3]. It does not
establish it. Non-response is inferred from switching rather than measured, because
standardised symptom severity is not systematically recorded in this extract, and dose
and duration adequacy were not verified for the counted post-index treatments. A change
attributable to intolerance, adverse effects, cost, formulary restriction, fragmented
care, patient preference or prescriber practice is counted exactly as a change
attributable to non-response.

Switching also depends on continuity, access, insurance and clinical practice, all of
which may differ across demographic groups [18,19]. The target can therefore encode
health-care process and inequity alongside pharmacologic non-response. The label was
never validated against chart review or a symptom-severity criterion. Future validation
should compare it with adjudicated treatment histories and symptom trajectories, and
should test a higher-specificity outcome requiring documented adequate courses.

# Supplement M4. Predictor selection and the typed feature representation

The candidate predictor set was specified before model fitting and before any
predictor-outcome association was examined. Selection was manual, on clinical and
literature grounds, as in the treatment-resistance model of Perlis [4], rather than by
univariate screening or an automated procedure. No variable was retained or removed
because of its observed association with TRD, and no automated selection step ran at any
stage.

The selected domains follow prior treatment-resistance and antidepressant-response
research [4,5]:

- depression severity and recurrence;
- psychiatric and substance-use comorbidity;
- medical comorbidity;
- prior antidepressant exposure and medication burden;
- health-care utilisation;
- sociodemographic characteristics.

One difference from
clinical-trial studies is structural rather than incidental. Those studies use scheduled
symptom scales and structured interviews, and this one is restricted to structured fields
recorded in routine care, so depression severity enters as diagnostic coding rather than
as a rating-scale score. Prior EHR prediction studies informed which domains were
feasible at all [6,7].

Two retention decisions are worth stating because they look like oversights and are not.
Prescribing-constraint flags were kept because they describe whether escalation options
may be limited, which is the clinical question the model sits next to. Sociodemographic
and social-determinant fields were kept so that their direct contribution could be tested
by the semantic-feature ablation, rather than being rendered unobservable by design. The
only prespecified fields later removed were body mass index and systolic and diastolic
blood pressure, for the missingness reasons in Supplement M6 and not for any association
with the outcome.

The feature representation assigns an explicit type to every field. Quantitative counts
and durations are continuous, covering encounter count, pre-index history length, age,
per-agent adequate-trial counts and medication burden. Single binary flags and
multi-label indicator sets are boolean, covering psychiatric and medical comorbidity,
prescribing constraints, substance-use categories and social-determinant categories.
Single-valued nominal variables are categorical, covering sex, preferred language,
marital status, religion, smoking status, race and ethnicity, MDD recurrence and coded
MDD severity. An adequate prior
antidepressant trial requires at least 42 days of continuous exposure to an agent. The
complete inventory, with each field's type and encoded form, is Multimedia Appendix 1.

# Supplement M5. Deterministic narrative and embedded representation

The same pre-index record was rendered deterministically into a human-readable Markdown
narrative. Rendering is rule-driven and reproducible, and no generative language model
participates in construction. That choice prioritises traceability over fluency, because
an unsupported generated statement would silently alter the patient's model input [23].
Example narratives are reproduced in Supplement S6.

Each narrative was mapped to a fixed-length vector by a pretrained sentence-transformer
encoder [11]. The four independently evaluated encoders were `bge-small-en-v1.5` [12],
`bge-en-icl` [13], `Qwen3-Embedding-4B`, and `Qwen3-Embedding-8B` [14]. This
serialisation-and-encoding strategy follows evidence that general-purpose language-model
embeddings of serialised EHR records perform competitively with purpose-built EHR
foundation models across prediction tasks [9].

The two representations use the same timeline-sliced source record and not an identical
set of rendered fields. Supplement S11 gives, for every source field, its feature
encoding, its narrative rendering, its missing-value rule and its temporal availability.
Because the inventories differ, the comparison is between two complete representation
pipelines. It is not a controlled comparison of numeric against language encoding of
identical information.

# Supplement M6. Missing-data handling

No statistical imputation was performed. Mean body mass index and mean systolic and
diastolic blood pressure were present in the intermediate feature file and removed from
the feature matrix at load time. Each value is the within-patient mean across that
patient's own pre-index encounters rather than a mean across patients.

The missingness was both substantial and outcome-associated. Mean body mass index was
missing for 22.1% of patients and at least one vital sign was absent for 21.0%. Body mass
index was missing for 28.8% of TRD-positive against 20.6% of TRD-negative patients, a gap
of roughly 8 percentage points.

That association rules out missing completely at random. It does not establish missing
not at random, which cannot be identified from observed data, because missingness may
depend on health-system contact that the recorded predictors capture only partly. The
variables were removed because no defensible imputation model was available from the
observed predictors alone. No missingness indicators were created for the continuous
block and no NaN value reached an estimator. A matched re-run retaining these variables
with explicit missingness indicators and within-fold median imputation leaves the
head-to-head result a null, and is available from the corresponding author.

Missing categorical values were handled differently and were kept. The feature one-hot
encoder gave them a separate level and the narrative rendered the literal token
"Missing". Marital and smoking status are nearly complete, under 0.5% missing. Religion
is missing for 29.4% overall and shows a monotone age gradient, from 43.8% at ages 18-29
to 17.5% at ages 65 or older, so the missing-category level may itself carry age-related
information. Religion was retained with that indicator level. A matched re-run removed the field from
both representations, taking the column out of the feature matrix and the field out of
the rendered narrative. That removes the unrecorded level along with the recorded values.
Discrimination is unchanged in both, every paired interval includes zero, and the re-run
is available from the corresponding author.

# Supplement M7. Sample size and events per variable

No formal a-priori sample-size calculation was performed, because cohort size was fixed
by the eligibility cascade. Model dimensionality is summarised as events per variable:
the number of TRD-positive patients in the training set divided by the number of encoded
input columns. The numerator is 5,964 events rather than the full training sample of
34,063, because what limits the precision of a coefficient is the size of the minority
class. The denominator is the matrix dimension actually supplied to the estimator.

The resulting ratios differ by an order of magnitude across representations. The feature
matrix holds 92 encoded columns, giving 5,964/92, or about 64.8. Embedded dimensionality
is encoder-specific: `bge-small-en-v1.5` has 384 dimensions and a ratio near 15.5,
`Qwen3-Embedding-4B` has 2,560 and a ratio near 2.3, and `bge-en-icl` and
`Qwen3-Embedding-8B` each have 4,096 and a ratio near 1.5. Only the smallest encoder
clears the conventional threshold of 10.

Two qualifications belong with those numbers. Events per variable was developed for
lower-dimensional regression and is not a complete adequacy criterion for a
high-dimensional regularised learner. The three larger encoders are therefore
interpreted as regularised high-dimensional models rather than as the regressions the
measure was devised for. The low ratios nevertheless mark real overfitting risk, and
they do not explain the discrimination ranking: `bge-small-en-v1.5` has the most
favourable ratio and is the weakest encoder.

# Supplement M8. Train/test split, comparability, and leakage safeguards

One stratified 80:20 train/test split was generated once and reused for every model,
representation, encoder and ablation. The training set holds 34,063 patients, of whom
5,964 are TRD-positive (17.5%), and the test set 8,516, of whom 1,491 are TRD-positive
(17.5%). Standardized mean differences were computed for every predictor as the
train-minus-test mean difference over the pooled standard deviation. Across 100 predictor
rows the largest absolute value is 0.036 and none reaches 0.10. The largest arises from a
rare social-determinant flag present in 22 training patients and no test patient. Outcome
frequency is matched by stratification rather than by observation. The distributions
themselves are Supplement S9.

All data-dependent preprocessing happened inside the cross-validation pipeline. On each
fold, numeric scaling parameters and categorical levels were learned only from that
fold's training rows and then applied to its validation rows. The final pipeline was
fitted on the full training set and evaluated once on the test set.

The retrieval analyses required their own safeguard. All test identifiers were removed
from the searchable index, so each test patient was a query anchor while every neighbour
and every neighbour outcome came from the training set. That prevents self-retrieval,
test-to-test outcome propagation, and any direct use of a test label in prediction.
Train/test comparability supports internal evaluation and says nothing about
transportability, because both partitions inherit the same case-enriched sampling frame.

# Supplement M9. Standard machine-learning pipeline

Four classifiers were fitted to each representation: logistic regression, random forest,
gradient boosting and XGBoost. For the feature representation the column transformer
standardised the numeric block, one-hot encoded categorical variables with binary
categories collapsed and unknown inference-time levels ignored, and cast boolean
indicators to integer without further transformation. The embedded representation entered
through the numeric branch only.

Each classifier and its preprocessing transformer were wrapped in one scikit-learn
pipeline. Hyperparameters were selected by five-fold grid search on the training set,
optimising ROC AUC. The best configuration was refitted on all training patients and
generated held-out probabilities.

Bundling the transformer with the estimator is what makes the cross-validated estimates
trustworthy. The standardizer and the one-hot encoder both estimate parameters from data,
so fitting either outside the loop would let held-out rows inform their own
transformation. With no imputation anywhere in the pipeline, those two are the only
fitted preprocessing steps, so the cross-validated estimates carry no preprocessing
leakage. Tuning grids are keyed by classifier alone and are identical across
representations.

# Supplement M10. Neighbor-weighted retrieval prediction

The retrieval predictor was fitted on the embedded representation only. For query
patient q, the predicted TRD probability is the weighted mean of binary TRD labels among
K = 50 retrieved training neighbours:

$$\hat{P}(\mathrm{TRD} \mid q) = \frac{\sum_{i=1}^{K} w_i\, y_i}{\sum_{i=1}^{K} w_i},$$

where $y_i \in \{0,1\}$ is neighbour $i$'s TRD label and $w_i$ its non-negative weight.
Neighbourhood concentration was summarised by the effective sample size,

$$\mathrm{ESS} = \frac{\left(\sum_{i=1}^{K} w_i\right)^2}{\sum_{i=1}^{K} w_i^2},$$

which equals $K$ under uniform weighting and falls as weight concentrates on fewer
neighbours. Four weighting strategies were tested: uniform, cosine similarity between
anchor and neighbour, language-model similarity, and the harmonic mean of the last two.

`MedGemma-27B` [15] served as an outcome-blind similarity judge. It compared each pair of
deterministic narratives against a fixed six-dimension rubric and returned structured
JSON carrying an overall score from 0 to 100, rescaled to the unit interval. The judge
never received neighbour outcomes and never classified TRD. Its score changed only how
much a retrieved neighbour contributed to the weighted mean.

The judge's accuracy is unmeasured, and the design bounds what that costs. No human-rated
anchor-neighbour pairs were available to estimate its sensitivity, specificity or
calibration [24], so no accuracy claim and no corrected descriptive quantity is derived
from its assessments. An incorrect judgement could mis-weight a neighbour and reduce
performance. It could not create a direct outcome-information pathway, because the judge
never observed an outcome. The fixed prompt, rubric, JSON schema and worked examples are
Supplement S1.

Four retrieval schemes were evaluated. *Nearest* selects the K training patients of
highest cosine similarity. *Farthest* selects those of lowest similarity, as a negative
control. *Random* draws K training patients uniformly. *Subsampled* first draws a large
random candidate pool and then keeps the K most similar within it. That last scheme
tests whether discrimination survives when the closest and potentially redundant
neighbours are replaced by less extreme but still similar ones, and it does not assume
geometric hub vectors are present. This arm is embedding-only, because cosine similarity
is not well defined over mixed categorical and numeric features.

# Supplement M11. Semantic-feature ablation specifications

The ablation measures direct-input reliance and nothing wider. For each target concept,
patient values were reassigned through a random one-to-one cohort-wide donor permutation,
which retains the same marginal set of values while severing the association between a
patient's concept value and their outcome. Section-level ablations exchange a complete
narrative section and field-level ablations exchange only the named field. Perturbed
narratives were re-embedded and the baseline classifiers were kept frozen, so the change
in ROC AUC answers whether the fitted pipeline relies on that input. It does not answer
whether a newly trained model could substitute correlated information. Like every other
predictor, all six concepts are measured at or before the index date, and permuting one
leaves the rest of the narrative untouched.

**Psychiatric history** (section). Three groups of content:

- present-or-absent indicators for anxiety disorder, social anxiety disorder,
  obsessive-compulsive disorder, posttraumatic stress disorder, adjustment disorder,
  dysthymia, insomnia and any substance-use disorder;
- any suicidal-ideation or suicide-attempt code in the two-year lookback;
- named substance categories, including alcohol, cannabis, cocaine, nicotine, opioid and
  sedative or hypnotic disorders.

It carries documented diagnoses rather than treatments.

**Medication burden** (section). The count and names of distinct active drug ingredients
at the index date across all therapeutic classes, and the count and names of distinct
non-steroidal anti-inflammatory ingredients prescribed for at least seven days. It stands
in for overall medical complexity and pill burden rather than for psychiatric treatment.

**Treatment exposure** (section). Four groups of content:

- pre-index counts of adequate trials for selective serotonin reuptake inhibitors,
  serotonin-norepinephrine reuptake inhibitors, bupropion, mirtazapine and vortioxetine,
  each requiring at least 42 continuous days on the agent;
- total benzodiazepine days covered during the lookback;
- hypnotic agents prescribed for at least seven days;
- augmentation, defined as an antidepressant overlapping lithium, an antipsychotic or
  buspirone for at least 14 days.

It is distinct from all-class medication
burden and from the post-index agents used to construct the outcome.

**Treatment contraindications** (section). Seizure disorder, which weighs against
bupropion, and uncontrolled hypertension, which weighs against
serotonin-norepinephrine reuptake inhibitors. The concept is constraint on escalation
options rather than general medical comorbidity, which the narrative reports in a
separate section that was not permuted.

**Race/ethnicity** (field). The recorded category, including an explicit unrecorded
level, permuted inside an otherwise unchanged sociodemographic section. Sex, age,
preferred language, marital status, religion and smoking status were not altered.

**Social determinants of health** (field). ICD-10 Z-code categories recorded during the
lookback: education or literacy, employment, occupational exposure, housing and economic
circumstances, social environment, upbringing, primary support group and family
circumstances, psychosocial circumstances, and legal or criminal circumstances. The
narrative renders "None Recorded" when no qualifying code is present, and only this field
was permuted.

Three questions this design cannot answer are worth naming, because a reader may expect
it to. It does not determine whether outcome labelling or care processes are equitable.
It does not determine whether a permuted attribute can be reconstructed from correlated
inputs. It does not determine whether discrimination and calibration differ across
subgroups. A negligible race and ethnicity delta, for instance, would not exclude
sociodemographic information carried in utilisation, diagnosis or treatment patterns.

# Supplement M12. Evaluation coverage

Standard machine learning, the cross-encoder comparison and the semantic ablation all
used the complete 42,579-patient cohort and the shared 8,516-patient test set, with
`Qwen3-Embedding-8B` as the primary encoder and `MedGemma-27B` as the similarity judge.
The retrieval analyses used the full four-by-four grid for the primary encoder.

On that encoder the retrieval scheme dominated the weighting strategy. The weightings
were nearly indistinguishable under nearest retrieval, and the judge added value only
where retrieval was already uninformative. The farthest and subsampled schemes were
therefore not rerun for the other encoders, and neither were the language-model and
combined weightings. The three remaining encoders were evaluated on a reduced grid:
nearest and random retrieval crossed with uniform and cosine weighting. That is enough
to establish whether the nearest-versus-random ordering generalises.

# Supplement M13. Metrics and uncertainty

Discrimination was measured by ROC AUC. Calibration was summarised by intercept and
slope, with ideal values of 0 and 1. The extract was case-enriched, so calibration in
the large pertains to this cohort's observed TRD frequency. It does not transport to a
sampling-representative population without recalibration.

Continuous probabilities were dichotomised at the test-set threshold maximising Youden's
J, and sensitivity, specificity and positive and negative likelihood ratios were computed
from the resulting confusion matrix. Selecting and evaluating a threshold in the same
test set produces optimistic operating characteristics, so these estimates characterise
the ROC curve rather than propose a deployment threshold. A clinical threshold would have
to be selected entirely within development data and evaluated in a separate temporal or
external cohort.

Metric confidence intervals were estimated by resampling test-set patients with
replacement. For ablation contrasts the same patient resample was applied to the baseline
and perturbed prediction vectors before the ROC AUC difference was recomputed. The point
estimate is the full-sample difference and the 2.5th and 97.5th percentiles of the
bootstrap distribution form the 95% interval. Paired resampling preserves within-patient
correlation and avoids overstating the uncertainty of a difference.

Representation contrasts used the same paired bootstrap. Classifier-matched comparisons
held the learner constant and varied only the representation. The best-versus-best
contrast compares each representation's strongest classifier, and that classifier was
identified post hoc on the test set, so the contrast is interpreted descriptively. One
resample matrix was reused across all contrasts to keep them mutually comparable.

No equivalence or non-inferiority margin was prespecified. A paired interval containing
zero indicates that superiority was not established at the precision achieved. It does
not establish equivalence.

# Supplement S1. LLM clinical-similarity judge

## S1.1 Task

In the neighbour-weighted prediction arm, the language-model weighting strategy used
`MedGemma-27B` as a clinical-similarity judge. For each anchor-neighbour pair the judge
received the two patients' deterministic narratives and returned a structured JSON
score. Only the integer `overall_similarity` field, from 0 to 100 and rescaled to the
unit interval, was used as the neighbour weight. The per-dimension sub-scores and
free-text lists were retained for auditing and never entered the prediction. The judge
ran against a cache, with each unordered pair scored once and stored, so repeated runs
are deterministic with respect to that cache.

## S1.2 System prompt (verbatim)

```text
You are a clinical similarity scorer for major depressive disorder (MDD).
Compare two patient narratives that contain only structured EHR data from a fixed baseline window.

Judge similarity ONLY on factors that affect antidepressant response/tolerability.
Treat "Missing" as unknown (neutral). Treat "Absent" as truly absent. Do not infer beyond text.

Weight these dimensions when scoring (sum=100):
1. Baseline symptom phenotype (PHQ-9 subitems): 25 points
2. Psychiatric comorbidity & threat/anxiety/trauma & SUD/suicidality: 20 points
3. Medical/metabolic & pain/NSAIDs: 20 points
4. Treatment exposure & medication burden (polypharmacy, prior adequate trials, 3y complexity): 20 points
5. Social/functional access (no-show, marital/employment/SDOH): 10 points
6. Safety flags (contraindications): 5 points

Return JSON only.
Do not repeat items in lists.
Do NOT provide explanations, reasoning, or calculations. Output raw JSON only.
```

## S1.3 User prompt and output schema (verbatim)

The two narratives are injected at `{narrative_a}` and `{narrative_b}`.

```text
INDEX PATIENT:
{narrative_a}

CANDIDATE PATIENT:
{narrative_b}

Limit "top_similarity_drivers" and "key_mismatches" to at most 5 items each. Return this JSON:
{
    "overall_similarity": 0-100,
    "phenotype": 0-100,
    "psych_comorbidity": 0-100,
    "metabolic_pain": 0-100,
    "treatment_burden": 0-100,
    "social_functional": 0-100,
    "safety": 0-100,
    "top_similarity_drivers": ["driver 1", "...up to 5"],
    "key_mismatches": ["mismatch 1", "...up to 5"]
}

Scoring rules:
- Same band (e.g., NSAID 0 vs 1) = small penalty; different band (0 vs >=2) = large penalty.
- Reward matches on polypharmacy, pain/NSAIDs, anxiety/fatigue most.
- If a dimension has 'Missing' data, strictly output the value 0 for that score.
```

## S1.4 Worked examples

The examples below come from the extremes of the judged distribution across the
primary `Qwen3-Embedding-8B` encoder's neighbourhoods. They are the five lowest- and
five highest-scoring anchor-neighbour pairs, extracted by
`scripts/pipeline/neighbors/llm_similarity_audit.py` and written in full to
`results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/llm_audit/judgement_{id_a}_{id_b}.txt`.
On the current run the five lowest all scored 25 and the five highest scored 98 to 100.
Two of each are reproduced here in full and the remaining responses are shown as JSON
only.

Neither band admits a meaningful internal ranking, so the examples are labelled *low*
and *top-band* rather than "lowest" and "second-lowest". At the bottom all five pairs
are tied at exactly 25. At the top the five are effectively tied at the ceiling. The
score-98 pair is reproduced in full because it is the cleanest near-duplicate, and a
score-100 pair follows to illustrate a sub-score artifact described in S1.5. That is a
choice of illustration rather than an ordering.

### Low-similarity example (score 25) — dissimilar patients

> **Narrative A** — MDD (Single Episode, Unspecified); Female, 55, Divorced,
> Spanish-preferring, never-smoker; no psychiatric comorbidity, no suicidality;
> no medical comorbidity; 0 prior adequate AD trials; 0 active meds; no safety
> flags.
>
> **Narrative B** — MDD (Recurrent, Moderate); Male, 77, Married, heavy smoker;
> anxiety, substance-use disorder (alcohol, nicotine), and insomnia present;
> chronic pain, hyperlipidemia, thyroid disease; 2 prior SNRI trials, 346
> benzodiazepine days, augmentation present; 3 active meds (buspirone,
> diazepam, duloxetine).

```json
{
    "overall_similarity": 25,
    "phenotype": 0,
    "psych_comorbidity": 25,
    "metabolic_pain": 0,
    "treatment_burden": 25,
    "social_functional": 0,
    "safety": 100,
    "top_similarity_drivers": [
        "Absent suicide flag",
        "Absent epilepsy",
        "Absent uncontrolled hypertension",
        "Absent psych inpatient days",
        "Absent ED psych visits"
    ],
    "key_mismatches": [
        "Presence of SUD/Anxiety/Insomnia in Index",
        "Prior SNRI exposure in Index",
        "Active medications at baseline in Index"
    ]
}
```

### Top-band example (score 98) — near-duplicate patients

> **Narrative A** — MDD (Single Episode, Unspecified); Female, 68, Married,
> never-smoker; anxiety present, no other psychiatric or medical comorbidity;
> 0 prior adequate AD trials; 0 active meds; uncontrolled hypertension; BMI and
> blood pressure missing.
>
> **Narrative B** — Identical on every clinical field; differs only in recorded
> religion (Missing vs Non-Denominational) and index timing (MDD-to-anchor gap
> 40 vs 0 days).

```json
{
    "overall_similarity": 98,
    "phenotype": 100,
    "psych_comorbidity": 100,
    "metabolic_pain": 100,
    "treatment_burden": 100,
    "social_functional": 100,
    "safety": 100,
    "top_similarity_drivers": [
        "Age 68",
        "Female",
        "Married",
        "Anxiety Present",
        "No Prior AD Trials"
    ],
    "key_mismatches": []
}
```

### Additional responses (JSON only)

A second low-similarity example, scored 25. The index patient has severe recurrent MDD
with anxiety, adjustment disorder, PTSD and a substance-use disorder. The candidate has
dysthymia and no comorbidity.

```json
{
    "overall_similarity": 25,
    "phenotype": 0,
    "psych_comorbidity": 25,
    "metabolic_pain": 25,
    "treatment_burden": 25,
    "social_functional": 0,
    "safety": 100,
    "top_similarity_drivers": [
        "Absent Epilepsy",
        "Absent Uncontrolled HTN",
        "Absent NSAID burden",
        "Absent Benzodiazepine use",
        "Absent Hypnotic use"
    ],
    "key_mismatches": [
        "Age difference (55 vs 84)",
        "Comorbidity presence (Anxiety, PTSD, SUD, Chronic Pain vs Absent)",
        "Treatment burden (Active meds 2 vs 0)"
    ]
}
```

A second top-band pair, scored 100. The two patients are demographically and clinically
identical: both female, 32, single, with no comorbidity and no prior trials. The overall
score of 100 was assigned despite a `phenotype` sub-score of 0.

```json
{
    "overall_similarity": 100,
    "phenotype": 0,
    "psych_comorbidity": 100,
    "metabolic_pain": 100,
    "treatment_burden": 100,
    "social_functional": 100,
    "safety": 100,
    "top_similarity_drivers": [
        "No prior adequate AD trials",
        "No benzodiazepine use",
        "No substance abuse",
        "No chronic pain",
        "No medical comorbidities"
    ],
    "key_mismatches": []
}
```

## S1.5 Interpretation and caveats

The judge's **overall** similarity behaved sensibly at the extremes. Near-duplicate
patients scored 98 and clinically dissimilar patients scored 25. The roughly 1.71
million cached judgements span 25 to 100, with a median of 55 and a modal band of 45 to
65, so the score is graded rather than degenerate.

Parts of the rubric name evidence the narratives do not contain, and the prompt is
reproduced above exactly as it was run rather than corrected. Dimension 1 is headed
"Baseline symptom phenotype (PHQ-9 subitems)", and no PHQ-9 item is recorded in this
extract or rendered in any narrative. Neither is any other symptom-severity instrument.
Dimension 5 names no-show behaviour, which is not a field in the narrative template,
although the marital, employment and social-determinant cues named beside it are.
Dimension 4 refers to "3y complexity" where the lookback window is two years. Dimensions
2, 3 and 6 carry 45 of the rubric's 100 points and are fully supported by the
template.

The judge did not treat the unsupported dimension as empty. Across a systematic 1-in-57
sample of the 1,710,849 cached judgements, the `phenotype` sub-score is 0 for 31.4% of
pairs. Over the remainder it takes 15 distinct values with a median of 60 and correlates
0.58 with `overall_similarity`. The model was therefore not following the instruction to
output 0 for a dimension whose data are missing. It was scoring baseline phenotype from
the evidence actually present: the narrative's MDD recurrence and severity coding and
its psychiatric flags. The mislabel is in the rubric's wording rather than in the
resulting behaviour. For comparison, the sub-scores on the three fully supported
dimensions are 0 for 0.0%, 1.0% and 14.7% of pairs.

None of this propagates into a reported number. Only `overall_similarity` enters the
neighbour weighting, and that weighting is itself scored against observed outcomes the
judge never sees. A judgement made on thin evidence can therefore only degrade the
discrimination the main text reports.

What the mislabel does bound is the generality of the main text's null. The finding is
that *this* rubric added no discrimination over plain cosine weighting under nearest
retrieval. It is not that language-model clinical similarity judging cannot. Against
that, the same rubric did lift discrimination where retrieval was uninformative, from
0.495 to 0.517 under random retrieval and from 0.543 to 0.554 under subsampled
retrieval, so it carries clinical signal despite the mislabelled dimension.

The **per-dimension sub-scores are not a decomposition of the overall score**
and should be read as illustrative only:

- The `overall_similarity` is a holistic judgment and **not an aggregation of the six
  sub-scores**. Both low-similarity pairs score `safety` 100, because both patients
  simply lack the safety flags, and both still carry an `overall` of 25. A second
  top-band pair scores `phenotype` 0 and carries an `overall` of 100.
- The free-text `top_similarity_drivers` and `key_mismatches` lists are unvalidated
  descriptive annotations. They were broadly accurate in the sampled extremes, they are
  not audited at scale, and they do not enter the prediction.

Because only `overall_similarity` enters the neighbour weighting, these sub-score
artifacts do not propagate into the predictions. They are reported so that a reader of
the cached JSON is not misled into treating the six dimensions as a decomposition.

## S1.6 Re-judging under a corrected rubric

Measuring what the model did with the mislabelled dimension is not the same test as
asking whether correcting the rubric would change the cached scores. S1.6 runs that
second test.

**The change.** Exactly one. Dimension 1, "Baseline symptom phenotype (PHQ-9
subitems)", was re-headed to name the evidence the narratives actually carry: MDD
recurrence and severity coding, and psychiatric comorbidity flags. Its weight and every
other dimension were left untouched. The instruction to output 0 for a dimension whose
data are missing was also left in place. The question is whether the model's behaviour
changes when a dimension is correctly described, not whether it obeys that
instruction.

**The design.** A uniform random sample of 5,000 pairs was drawn from the 1,710,849
cached judgements and re-judged under the corrected rubric, with the same model, the
same decoding settings and the same seed. Each pair therefore has two scores: the cached
one and the re-judged one. The comparison is paired.

**The decision rule, fixed in advance.** Close agreement means the cached judgements
stand and the mislabel is cosmetic. Substantial disagreement means the cache would have
to be regenerated and every retrieval result recomputed.

**The result: the cached judgements stand.** Across the 5,000 re-judged pairs the two
scores agree closely. The correlation is high, the median absolute difference is small,
and the rank ordering that the neighbour weighting actually depends on is essentially
unchanged.

The change is small, systematic, and in the direction the rubric edit predicts. Scores
move slightly, and they move consistently rather than randomly, which is what a
correctly re-described dimension should produce. A random scatter would have suggested
the judge was not reading the dimension heading at all.

Two incidental confirmations fall out of the same run. The `phenotype` sub-score is 0
for 30.5% of these pairs under the corrected rubric, against 31.4% in the systematic
sample under the original, so the model was already scoring the dimension from available
evidence. And the free-text driver lists remain broadly accurate on inspection, which is
the same unaudited impression recorded in S1.5.

**Decision.** The pre-specified rule is met on the agreement side, so the 1,710,849
cached judgements stand and no retrieval result was recomputed. The rubric is reported
as it was run, with this section as the record of why that is defensible rather than
merely convenient.

***Figure S8.** Cached against corrected judgements over 5,000 randomly sampled
pairs. Left: joint distribution of overall similarity under the two rubrics, with
the identity line. Right: the distribution of their difference, corrected minus
cached.*

![](../results/review/judge_prompt/judge_prompt_agreement.png){width=6in}

# Supplement S2. Effective dimensionality of the embedded representation

Individual embedding dimensions carry no clinical meaning, so the per-feature
interpretability available for the feature representation in main-text Figure 7 does not
transfer to a 4,096-dimensional embedded representation. What can be characterised
instead is *how many* latent dimensions carry the predictive signal. Three complementary
views are reported, all for the primary `Qwen3-Embedding-8B` encoder on the held-out
test set.

## S2.1 Sparsity and cumulative built-in importance

The best logistic-regression fit used an elasticnet penalty, with `l1_ratio` 0.25 and
`C` 0.01, that zeroed most coefficients. Only 385 of the 4,096 dimensions carry non-zero
weight, so the signal is concentrated in a sparse subset. Ranking dimensions by each
fitted classifier's native importance and accumulating the mass confirms that
concentration. For logistic regression, 80% of the coefficient magnitude falls in
roughly 179 of the 4,096 dimensions and 90% in roughly 236, as main-text Figure 8 shows.
TRD-relevant information is therefore carried by a modest subset of embedding dimensions
rather than spread across the space.

## S2.2 Cumulative univariate correlation

An importance ranking is model-specific. As a model-agnostic check we ranked dimensions
by the absolute Spearman correlation between each dimension and the outcome, and
overlaid that against per-classifier curves ranking by the correlation between each
dimension and the predicted risk. Divergence between the two would flag dimensions a
classifier weights through regularisation or interactions that a univariate ranking
cannot see.

The model-agnostic curve remained diffuse, with many dimensions each weakly correlated
with the outcome. The elasticnet logistic-regression curve was far more concentrated, so
the regularisation is selecting a compact predictive subset from a broadly informative
space. Only the absolute correlation is used, because the sign of a correlation on an
unnamed latent dimension is not interpretable.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png){width=6in}

***Figure S1.** Cumulative absolute univariate (Spearman) correlation. One
model-agnostic baseline curve ranks dimensions by the correlation between each dimension
and the outcome. The four per-classifier curves rank by the correlation between each
dimension and the predicted risk. The plot shows cumulative fraction of total
correlation mass against rank, with the K₈₀ and K₉₀ knees in the legend.*

## S2.3 PCA-K discrimination sweep

To locate the geometric plateau, each classifier was retrained on the top K principal
components of the embedding and its held-out ROC AUC plotted against K. The sweep ran K
over 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 and 1024. Discrimination rose steeply over
the first handful of components and then plateaued. No single low-dimensional projection
recovered full-rank performance, which is the same broadly-distributed-signal conclusion
the cumulative-importance and correlation curves reach.

**(A) Logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_logistic_regression_EMBEDDED.png){width=6in}

**(B) Random forest**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_random_forest_EMBEDDED.png){width=6in}

**(C) Gradient boosting**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_gradient_boosting_EMBEDDED.png){width=6in}

**(D) XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_xgboost_EMBEDDED.png){width=6in}

***Figure S2.** ROC AUC versus number of retained principal components, one
panel per classifier: (A) logistic regression, (B) random forest,
(C) gradient boosting, (D) XGBoost. The plateau marks the effective number of
principal directions beyond which added components do not improve
discrimination.*

# Supplement S3. Precision–recall performance

The main text reports discrimination as ROC AUC, and under this cohort's roughly 5:1
class imbalance that measure can flatter apparent performance. With 17.5% of patients
TRD-positive, the true-negative-dominated specificity term stays high however well or
badly the positive class is ranked. The area under the precision-recall curve is the
complementary view, because its no-skill baseline is the positive rate itself rather
than 0.5. It exposes the precision cost of capturing TRD cases, which is the quantity a
clinician would actually feel.

Precision-recall performance tracked discrimination closely and stayed modest for every
model in the comparison. At this base rate, high recall on the TRD proxy necessarily
forces low precision, and no combination of representation and classifier escaped that
trade. No clinical role is inferred from these values, and the main text's Discussion
records that temporal and external validation are prerequisites for any such claim.

***Table S1.** AUPRC of the four classifiers on each representation (held-out
test set). No-skill baseline = 0.175 (the positive rate).*

| Representation | Classifier | AUPRC |
| --- | --- | ---: |
| EMBEDDED | Logistic regression | 0.302 |
| EMBEDDED | Random forest | 0.270 |
| EMBEDDED | Gradient boosting | 0.276 |
| EMBEDDED | XGBoost | 0.278 |
| FEATURE | Logistic regression | 0.278 |
| FEATURE | Random forest | 0.293 |
| FEATURE | Gradient boosting | 0.288 |
| FEATURE | XGBoost | 0.298 |

***Table S2.** Embedded logistic-regression AUPRC by encoder (held-out test
set). No-skill baseline = 0.175.*

| Encoder | AUPRC |
| --- | ---: |
| bge-small-en-v1.5 | 0.281 |
| bge-en-icl | 0.297 |
| Qwen3-Embedding-4B | 0.297 |
| Qwen3-Embedding-8B | 0.302 |

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png){width=6in}

***Figure S3.** Precision-recall curves for the best classifier on each representation,
on the held-out test set with the primary `Qwen3-Embedding-8B` encoder. Panel A is
embedded logistic regression and panel B feature-representation XGBoost. The horizontal
reference is the no-skill baseline of 0.175, the positive rate.*

# Supplement S4. Calibration absolute-error metrics

The main text reports calibration shape in two places: the slope and intercept in its
Table 3, and the calibration curves in its Figure 6. The two absolute-error summaries
are reported here instead. They are the Brier score and a weighted calibration error,
and lower is better for both.

Brier scores sat uniformly near 0.137 to 0.140 across all eight models, dominated by the
17.5% base rate. The weighted calibration error separated the models more clearly.
Gradient boosting on the embedded representation was lowest at 0.004, with logistic
regression on the feature representation next at 0.005. Both are consistent with the
near-ideal slopes those two models carry in main-text Table 3.

***Table S3.** Brier score and weighted calibration error (WCE) of the four
classifiers on each representation (held-out test set). Lower is better for
both. Calibration slope and intercept are in main-text Table 3.*

| Representation | Classifier | Brier | WCE |
| --- | --- | ---: | ---: |
| EMBEDDED | Logistic regression | 0.137 | 0.010 |
| EMBEDDED | Random forest | 0.140 | 0.006 |
| EMBEDDED | Gradient boosting | 0.139 | 0.004 |
| EMBEDDED | XGBoost | 0.139 | 0.013 |
| FEATURE | Logistic regression | 0.139 | 0.005 |
| FEATURE | Random forest | 0.139 | 0.018 |
| FEATURE | Gradient boosting | 0.138 | 0.010 |
| FEATURE | XGBoost | 0.138 | 0.012 |

# Supplement S5. Encoder similarity geometry: a bimodality artifact in bge-small-en-v1.5

A complementary view of how each encoder organises the cohort is the distribution of
cosine similarities between patient embeddings. Figure S4 contrasts, for each encoder,
the similarities of random patient pairs against those of nearest-neighbour pairs, where
the random-pair histogram is the encoder's overall similarity distribution.

Three of the four encoders produce smooth, unimodal random-pair distributions:
bge-en-icl, Qwen3-Embedding-4B and Qwen3-Embedding-8B. The smallest encoder is the
exception. Its random-pair distribution is distinctly multimodal, with a sharp primary
peak near 0.99 and a separated secondary mode near 0.98. That says the cohort splits
into two internally similar groups rather than spreading along one continuum.

**(A) bge-small-en-v1.5**

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(B) bge-en-icl**

![](../results/bge-en-icl/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(C) Qwen3-Embedding-4B**

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

**(D) Qwen3-Embedding-8B**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=6in}

***Figure S4.** Random-pair (red) versus nearest-neighbor-pair (green)
cosine similarities for each encoder (full cohort). (A) bge-small-en-v1.5,
(B) bge-en-icl, (C) Qwen3-Embedding-4B, (D) Qwen3-Embedding-8B. The red
random-pair histogram is the encoder's overall similarity distribution:
it is multimodal only for bge-small-en-v1.5 (A) and smoothly unimodal for
the other three. In every panel the neighbor-pair similarities (green)
sit above the bulk of the random-pair mass, confirming that
nearest-neighbor retrieval selects genuinely more similar patients. Axis
ranges differ per panel because the encoders occupy different absolute
similarity bands.*

To identify the split we clustered the L2-normalised bge-small embeddings into two
groups with k-means, which partitioned the 42,579 patients into 14,438 and 28,141. The
partition coincides almost perfectly with a single surface lexical feature. The literal
token "episode" appears in essentially every narrative of the larger cluster and almost
none of the smaller, and the related MDD recurrence and severity wording follows the
same split.

What each cluster is deserves stating precisely, because the two are *not* simply
recurrent against non-recurrent. The narrative renders each patient's MDD coding
verbatim, as `MDD (Single Episode, Unspecified)` or `MDD (Recurrent, Moderate)`, and
only the single-episode wording contains the word "episode". So:

- **Cluster B (28,141)** holds narratives that contain "episode", the single-episode
  patients, of whom there are 28,206 in the cohort.
- **Cluster A (14,438)** holds narratives that do not. It is a mixture of the 11,213
  patients coded `Recurrent` and the roughly 3,200 coded `Unspecified` or `Dysthymia`,
  neither of which uses the word "episode".

Cluster A is therefore best described as carrying no *episode* token rather than as
being all recurrent. Roughly one patient in five inside it is not coded recurrent at
all. That distinction is what the second-order analysis below turns on.

***Table S4.** Surface tokens that most strongly separate the two k-means clusters of
bge-small-en-v1.5 embeddings. Values are the fraction of narratives in each cluster
containing the token, as binary presence. Cluster A holds 14,438 patients whose
narratives carry no "episode" token, which is the recurrent-coded group plus
unspecified and dysthymia. Cluster B holds 28,141 single-episode narratives. The token
"single" is elevated in both clusters because it also occurs as a marital status.*

| Token | P(present \| cluster A) | P(present \| cluster B) | \|Δ\| |
| --- | ---: | ---: | ---: |
| episode | 0.00 | 1.00 | 1.00 |
| recurrent | 0.78 | 0.00 | 0.78 |
| single | 0.30 | 1.00 | 0.70 |
| unspecified | 0.39 | 0.83 | 0.45 |
| moderate | 0.32 | 0.09 | 0.23 |

Figure S5 makes that mechanism visible. Both panels are histograms of *pairs of
patients* rather than of patients. For every pair in the set shown we compute the cosine
similarity between the two embeddings and ask one yes-or-no question about the two
narratives: do they agree on a particular word? Pairs that agree are drawn in blue and
pairs that disagree in red, with the grey histogram behind them showing every pair in
the set. If a single word were driving the geometry, blue and red would sit at visibly
different similarities. If it were not, they would lie on top of each other.

Panel A asks this of all 42,579 patients, using the word "episode": do both narratives
contain it, or does neither? Blue is agreement, meaning both single-episode or both
non-single-episode, and red is disagreement. The blue pairs pile up at about 0.99 and
the red pairs at about 0.97. The two modes of Figure S4A are therefore exactly these two
groups. The encoder places two patients about 0.02 further apart when their MDD coding
is phrased differently, whatever else is in their records.

Panel B asks the question again inside cluster A alone, using the word "recurrent". A
second question is needed because every narrative in cluster A lacks "episode", which
makes panel A's question uninformative there. "Recurrent" is a genuine question because
cluster A is not uniformly recurrent: 11,425 of its members are coded `Recurrent` and
3,013 are coded `Unspecified`. Blue pairs again separate from red pairs, so cluster A
carries a real second split, once more on wording rather than on clinical content.

Cluster B was tested the same way and is not plotted. Its only candidate second-order
token is the narrative's `Missing` sentinel, and there the blue and red histograms lie
almost exactly on top of each other. There is no second split to show. Those numbers are
in Table S5.

**(A) All 42,579 patients, split by the "episode" token**

![](../notebooks/figures/bge_small_recurrence_bimodality.png){width=5.5in}

**(B) Cluster A only (n = 14,438), split by the "recurrent" token**

![](../notebooks/figures/bge_small_cluster0_subsplit.png){width=5.5in}

***Figure S5.** Pairwise cosine-similarity distributions for bge-small-en-v1.5,
decomposed by whether the two patients in a pair use the same wording for one token.
Blue is same, red is different, and grey is all pairs in the set shown. **(A)** All
42,579 patients, split on the "episode" token. Same-wording pairs form the upper mode
near 0.99 and differing-wording pairs the lower mode near 0.97, so the bimodality in
Figure S4A is driven by recurrence phrasing rather than by holistic clinical similarity.
**(B)** Cluster A only, the 14,438 patients whose narratives lack "episode", split on
the "recurrent" token. The two colours again separate, so this cluster is itself
genuinely divided, once more along a surface-lexical axis. Cluster B admits no
comparable second split and is not plotted.*

The lowest-capacity encoder therefore organises its geometry around the presence or
absence of one recurrence-phrasing token rather than around holistic clinical content.
That lexical split produces the second mode of Figure S4A. The higher-capacity encoders
show no such artifact.

On visual inspection each of the two parent clusters looks as though it might contain
two further sub-modes. Table S5 tests whether those apparent sub-modes are real. The
test is the same one run twice: take a parent cluster on its own, re-run k-means inside
it, ask how clean the resulting two-way split is, and then ask which word the split
tracks.

Cleanliness is measured by the cosine silhouette, on a 5,000-point subsample with a
fixed seed. It scores from −1 to 1 and asks, for each patient, whether it sits closer to
its own sub-cluster than to the other one. Higher means better separated. The number is
only interpretable by comparison, so the reference point is the top-level split of Table
S4, which scores 0.48 under the same metric. A within-cluster split scoring well above
0.48 is more clearly separated than the split it came from. One scoring well below is
not really a split at all.

The two parents give opposite answers. Cluster A subdivides **more** cleanly than the
parent split itself, at a silhouette of 0.69. It separates into an explicitly recurrent
subgroup of 11,425 patients, carrying the token "recurrent" in 98% along with the
severity words moderate, mild and severe. The other side is a smaller
unspecified-recurrence subgroup of 3,013, carrying "unspecified" in 100% and no severity
wording. That smaller subgroup is the same group of about 3,000 patients, 7% of the
cohort, that a flat three-cluster solution peels off.

Cluster B does **not** meaningfully subdivide. Its silhouette is 0.21, well below the
parent 0.48. What little structure it has is keyed on the narrative's `Missing`
sentinel, present in 88% of one putative subgroup and 2% of the other, which is a
data-completeness gradient rather than a clinical contrast. Consistent with that
reading, the better-populated side additionally carries named SSRIs, at 0.24 for
citalopram, 0.16 for escitalopram and 0.17 for sertraline, simply because those patients
have more recorded medication.

***Table S5.** Do the two clusters of Table S4 split again? Each parent cluster was
re-clustered on its own with k-means. "Driving token" is the word whose presence best
separates the two resulting sub-clusters. The two proportions are the fraction of
narratives containing that word in each sub-cluster, so 0.98 against 0.00 means the word
is essentially present in one sub-cluster and absent from the other. "Split silhouette"
scores how cleanly the two sub-clusters separate, and should be compared against 0.48,
the score of the top-level split under the same metric. Cluster A splits cleanly, on
recurrence phrasing. Cluster B does not split: its 0.21 is a weak data-completeness
gradient on the missing-data sentinel, which is why it is not plotted in Figure S5.*

| Parent cluster (n) | Splits into (n / n) | Driving token | Token present, sub 1 / sub 2 | Split silhouette (top level = 0.48) | Real split? |
| --- | --- | --- | ---: | ---: | :---: |
| A: no "episode" token (14,438) | recurrent + severity (11,425) / unspecified (3,013) | recurrent | 0.98 / 0.00 | 0.69 | Yes |
| B: single-episode (28,141) | sparse record (6,594) / populated record (21,547) | missing | 0.88 / 0.02 | 0.21 | No |

This layered reading reinforces the single-token interpretation rather than
complicating it. At the top level the encoder keys on the recurrence token, and the only
genuine finer structure is a further split of cluster A on recurrence phrasing, which is
again a surface-lexical axis. Where a candidate second split does not track clinical
content, as in cluster B, the silhouette correctly declines to support it and the
apparent mode reduces to how completely the record was filled in.

Two things follow. The result is consistent with bge-small-en-v1.5 being the weakest
discriminator in the cross-embedder comparison of main-text Table 6. And it is a
cautionary note that a small sentence-transformer can organise its geometry around
individual surface tokens rather than around clinical content. The analysis is
descriptive, resting on k-means splits and binary token-presence rates, and it is
specific to this encoder. All primary analyses use Qwen3-Embedding-8B.

# Supplement S6. Example patient narratives

The embedded representation encodes a deterministically rendered Markdown narrative of
each patient's pre-index window. To make the encoder's input concrete, two representative
narratives are reproduced below, one TRD-positive and one TRD-negative. They were
extracted by `scripts/pipeline/neighbors/narrative_audit.py` as the first patient by
sorted de-identified hash in each outcome class, with output written to
`results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/narrative_audit/`. Each
narrative contains only structured EHR-derived fields, with no free text, names or direct
identifiers. Section headers and field order are fixed across all patients, absent
findings are rendered explicitly as "Absent" and unrecorded values as "Missing", so every
patient reaches the encoder through the same constant template.

The renderer's own field labels predate the manuscript's terminology: where the
narrative prints `MDD-to-anchor gap` and `Baseline window`, the manuscript says
the MDD-to-index gap and the lookback window. The narratives are reproduced
exactly as the encoder received them and are not re-labelled here.

Three things visible in these examples are not matched by the feature representation,
and all three are recorded as a limitation of the head-to-head comparison in the main
text and in Supplement S11:

- the `PHYSICAL HEALTH` section renders the within-patient mean vital signs that were
  dropped from the feature matrix at load time;
- the `SOCIODEMOGRAPHICS / ACCESS` line renders a recorded sexual-orientation field that
  is absent from the feature inventory entirely, and renders an unrecorded value there as
  the literal token `nan` rather than as `Missing`;
- the `COHORT & INDEX` line renders the index date, for which the feature representation
  has no column.

The `MEDICATION BURDEN` and `TREATMENT EXPOSURE` sections also name individual
ingredients where the feature representation carries only their counts. The imbalance
runs the other way once: pre-index history length is a feature-representation column that
the narrative does not render.

**TRD-positive example.**

```text
### COHORT & INDEX
Condition: MDD (Dysthymia, Unspecified) | Index date: 2022-10-06 | Baseline window: -730...0 days | MDD-to-anchor gap: 57 days | Encounters in window: 34 | MDD within window: Present

### SOCIODEMOGRAPHICS / ACCESS
Sex: Male | PreferredLanguage: English | AgeInYears: 37 | SexualOrientation: nan | MaritalStatus: Married | Religion: Baptist | SmokingStatus: Never | Race_Ethnicity: American Indian or Alaska Native
SDOH: None Recorded

### PHYSICAL HEALTH
BMI: 29.8 | BP (mean): 140/88

### PSYCH HISTORY
SOCIAL_ANXIETY: Absent | OCD: Absent | ANXIETY: Present | ADJUSTMENT_DISORDER: Absent | PTSD: Absent | DYSTHYMIA: Present | SUD: Present | INSOMNIA: Present
SUICIDE FLAG (2y): Absent
SUBSTANCE ABUSE: Nicotine

### MEDICAL COMORBIDITY
CHRONIC_PAIN: Absent | HYPERLIPIDEMIA: Absent | THYROID: Absent | DIABETES: Present

### TREATMENT EXPOSURE
Prior adequate AD trials: MIRTAZAPINE: 0 | SSRI: 1 | VORTIOXETINE: 0 | BUPROPION: 0 | SNRI: 0
Benzodiazepine days (2y): 0
Hypnotics: eszopiclone
Augmentation: Absent

### MEDICATION BURDEN
Active meds at baseline: 0 (Absent)
NSAID burden: 0 (Absent)

### UTILIZATION
Psych inpatient days: 0 (2y) | ED psych visits: 0 (2y)

### SAFETY
UNCONTROLLED_HTN: Present | EPILEPSY: Absent
```

---

**TRD-negative example.**

```text
### COHORT & INDEX
Condition: MDD (Recurrent, Moderate) | Index date: 2025-05-09 | Baseline window: -730...0 days | MDD-to-anchor gap: 0 days | Encounters in window: 2 | MDD within window: Present

### SOCIODEMOGRAPHICS / ACCESS
Sex: Female | PreferredLanguage: English | AgeInYears: 52 | SexualOrientation: nan | MaritalStatus: Single | Religion: Baptist | SmokingStatus: Every Day | Race_Ethnicity: White or Caucasian
SDOH: None Recorded

### PHYSICAL HEALTH
BMI: 35.6 | BP (mean): 138/86

### PSYCH HISTORY
SOCIAL_ANXIETY: Absent | OCD: Absent | ANXIETY: Present | ADJUSTMENT_DISORDER: Absent | PTSD: Absent | DYSTHYMIA: Absent | SUD: Present | INSOMNIA: Absent
SUICIDE FLAG (2y): Absent
SUBSTANCE ABUSE: Nicotine

### MEDICAL COMORBIDITY
CHRONIC_PAIN: Absent | HYPERLIPIDEMIA: Absent | THYROID: Absent | DIABETES: Absent

### TREATMENT EXPOSURE
Prior adequate AD trials: MIRTAZAPINE: 0 | SSRI: 0 | VORTIOXETINE: 0 | BUPROPION: 0 | SNRI: 0
Benzodiazepine days (2y): 0
Hypnotics: Absent
Augmentation: Absent

### MEDICATION BURDEN
Active meds at baseline: 0 (Absent)
NSAID burden: 0 (Absent)

### UTILIZATION
Psych inpatient days: 0 (2y) | ED psych visits: 0 (2y)

### SAFETY
UNCONTROLLED_HTN: Present | EPILEPSY: Absent
```

# Supplement S7. Nearest–farthest retrieval fusion

The main text observes that the farthest-neighbour predictor is not merely poor but
*informatively* poor. Its ROC AUC of 0.434 falls below chance, and its ROC curve bows
beneath the chance diagonal rather than tracking it, so inverting the predictor recovers
a discrimination of about 0.57. Dissimilarity in the embedding therefore carries
exploitable signal of its own. This section tests directly whether that signal is
*additive*: whether fusing each patient's nearest-neighbourhood risk with their inverted
farthest-neighbourhood risk improves on nearest retrieval alone. The test is reported in
full here and referred to once from the main text's Results.

Figure S6 shows the two scores that enter that test, each under the uniform weighting
used throughout this section. Nearest retrieval reaches 0.593 and farthest retrieval
0.434. The farthest curve does not wander around the chance diagonal the way an
uninformative score would. It sits beneath the diagonal across the entire range,
displaced from it by about as much as the nearest curve is displaced above it. Inverting
it gives 0.566, within 0.03 of nearest retrieval's own 0.593. The farthest neighbours
therefore carry real predictive power once their direction is corrected, which is what
makes the fusion question worth asking rather than a formality.

**(A) Nearest retrieval (ROC AUC 0.593)**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_UNIFORM.png){width=6in}

**(B) Farthest retrieval (ROC AUC 0.434)**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_FARTHEST_UNIFORM.png){width=6in}

***Figure S6.** The two component scores entering the fusion. Neighbour-weighted ROC for
panel A nearest and panel B farthest retrieval, under uniform weighting, on the embedded
representation and the held-out test set of 8,516 patients at K = 50, with the primary
`Qwen3-Embedding-8B` encoder. Shaded bands are bootstrap 95% intervals and the dashed
diagonal is chance. Uniform weighting is shown because it is the weighting fused here.
Under judge weighting the same contrast gives 0.595 and 0.436.*

## S7.1 Design

The analysis is post hoc and reuses the row-level predictions the neighbour-weighted
pipeline already wrote. No new retrieval and no new judge calls were performed. It is
restricted to the primary `Qwen3-Embedding-8B` encoder, the only configuration for which
farthest-scheme scores were computed, and to the 8,516 held-out test anchors of whom
1,491 are TRD-positive.

All scores use **uniform** weighting. The predicted risk is then the raw TRD rate of the
K = 50 geometrically selected neighbours, with no similarity opinion layered on top, so
the retrieval geometry under test is the only thing shaping the score.

Language-model weighting was rejected here as self-contradictory on the farthest scheme.
It selects the most clinically dissimilar patients and then reweights them back toward
similarity, which corrupts the meaning of the inverted term. Whatever weighting is
fused, the nearest-alone baseline uses the same one.

Writing *p*~near~ and *p*~far~ for a patient's nearest- and
farthest-neighborhood predicted risk, three fusions were compared against
*p*~near~ alone:

**Variant (a)** is a parameter-free equal average of *p*~near~ and (1 − *p*~far~).

**Variant (b)** is a convex blend α·*p*~near~ + (1 − α)·(1 − *p*~far~), with α chosen
from a grid of 21 equally spaced values on [0, 1] by maximising ROC AUC.

**Variant (c)** is a logistic stack on the raw pair (*p*~near~, *p*~far~). It fits a
coefficient on each term plus an intercept. It is therefore free to learn the sign on
*p*~far~ rather than being told to invert it, and free to place weights that do not sum
to one.

### Estimation and reporting for the tuned variants

Variants (b) and (c) each estimate parameters from data, which forces a distinction
between the parameters one would *deploy* and the performance one may *report*. Both are
handled identically, on a single stratified 5-fold partition of the 8,516 anchors shared
between them, so fold luck cannot confound their comparison.

**Reported performance is computed out of fold.** Within each fold, α for variant (b)
or the logistic coefficients and intercept for variant (c) are estimated on the four
training folds alone and applied only to the held-out fold. Every patient's fused score
therefore comes from parameters fitted without that patient, and the ROC AUC in Table S6 is
computed once over the pooled held-out predictions rather than averaged across per-fold
AUCs.

Scoring a tuned parameter on the same data used to choose it is optimistically biased,
and the magnitude here is not negligible. The single α maximising ROC AUC across all 8,516
anchors attains 0.600 in sample, against the 0.594 obtained out of fold. That inflation
is roughly the size of the entire effect under test. It is enough on its own to
manufacture an apparent gain over the baseline.

Embedding every fitted step inside the resampling loop follows Varma and Simon (*BMC
Bioinformatics* 2006;7:91). They show that a cross-validation error computed for a
classifier "that has itself been tuned using CV gives a significantly biased estimate of
the true error".

**Deployable parameters are estimated separately, on all 8,516 anchors.** They are
α = 0.65 for variant (b), and coefficients of +3.49 on *p*~near~ and −2.00 on *p*~far~
with an intercept of −1.80 for variant (c). These are the values that would be applied to
a new patient.

The intercept is not incidental. The two coefficients alone fix the ranking, and
therefore the discrimination reported for variant (c). The intercept sets the level of
the predicted probabilities, and that is what its calibration advantage in Table S6
rests on. The out-of-fold ROC AUC is an estimate *of* this fitted model, because a
cross-validated error estimates the true error of the model the same procedure returns
when trained on the whole dataset.

Two caveats attach to that. The out-of-fold estimate is mildly conservative, because
each fold's parameters are chosen on four-fifths of the anchors rather than all of them.
That bias is second-order at this sample size and runs opposite to the selection bias it
removes, so the reported figure should not be read as a lower bound with the in-sample
value as the truth. And these deployment parameters are themselves selected on the
held-out test anchors, so they are *not* independently validated. They are reported for
transparency, and nothing in this section's conclusion rests on them, the result being
null.

The verdict statistic is a **paired** bootstrap on the difference in ROC AUC. A single
1,000 by 8,516 matrix of resampled patient indices is drawn once and applied to the
baseline and the variant alike, so every draw perturbs both scores on the same patients.
The reported interval spans the 2.5th to 97.5th percentiles of the resulting difference
distribution. Pairing is essential here, because *p*~near~ and (1 − *p*~far~) are
positively correlated by construction and comparing their marginal intervals for overlap
is a substantially weaker test.

## S7.2 Results

No fusion improved discrimination. All three point gains were under 0.006 ROC AUC and
every 95% interval on the paired difference included zero, the largest being variant (c)
at +0.0059 (−0.0008 to +0.0122). The four ROC curves are visually indistinguishable.

***Table S6.** Nearest-alone baseline against three nearest-to-farthest fusions, under
uniform weighting on the embedded representation and the held-out test set of 8,516
patients, with the primary `Qwen3-Embedding-8B` encoder. Δ is the difference in ROC AUC
against the nearest-alone baseline, with a paired bootstrap 95% interval. WCE is
weighted calibration error, and lower is better for both it and Brier. Farthest
retrieval alone scores 0.434.*

| Score | ROC AUC (95% CI) | Δ vs nearest alone (95% CI) | AUPRC | Brier | WCE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nearest alone | 0.593 (0.578–0.609) | — | 0.253 | 0.142 | 0.026 |
| (a) Equal average | 0.599 (0.583–0.615) | +0.0051 (−0.0054 to +0.0149) | 0.254 | 0.241 | 0.316 |
| (b) CV-tuned blend | 0.594 (0.579–0.610) | +0.0004 (−0.0081 to +0.0087) | 0.249 | 0.187 | 0.213 |
| (c) Logistic stack | 0.599 (0.584–0.615) | +0.0059 (−0.0008 to +0.0122) | 0.256 | 0.141 | 0.003 |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_fusion_overlay.png){width=6in}

***Figure S7.** ROC curves for the nearest-alone baseline and the three fusion variants,
under uniform weighting on the embedded representation and the held-out test set, with
the primary `Qwen3-Embedding-8B` encoder. The four curves are visually
indistinguishable. Legend values are ROC AUC with the bootstrap 95% interval, and the
dashed diagonal is chance.*

This null is not a power failure. The paired intervals are roughly ±0.006 wide, about
three times tighter than the ±0.016 marginal intervals on the individual AUCs. It is
therefore the *stronger* test that returns the null, rather than an underpowered one that
cannot distinguish the scores.

Two secondary observations are worth recording.

The logistic stack recovered the inversion unprompted. It assigned +3.49 to *p*~near~ and
−2.00 to the raw *p*~far~, independently rediscovering that farthest-neighbourhood risk
runs backwards. The inverted signal is therefore real and its direction is learnable from
the data alone. It is also the same geometry restated, which is why restating it adds
nothing. The two tuned variants agree on the mixing direction despite optimising
different objectives: normalising the stack's coefficients gives 0.64, against the
blend's deployable α = 0.65 and per-fold range of 0.60 to 0.70. A rank-based grid search
on ROC AUC and a likelihood-based logistic fit converge on the same weighting, which is
stronger evidence that the direction is a property of the data than either result alone.

Tuning did not help. The cross-validated blend placed last of the three, below the
parameter-free average, despite stable per-fold weights. Pooling out-of-fold scores
produced under five slightly different weightings appears to cost more than the tuning
gains.

Calibration separates the variants even though discrimination does not. The
parameter-free fusion and the tuned blend both degrade it markedly against nearest alone.
Brier rises from 0.142 to 0.241 and 0.187 respectively, and weighted calibration error
from 0.026 to 0.316 and 0.213.

The mechanism is that (1 − *p*~far~) is not itself calibrated to the patient's risk. It
is anti-correlated with the outcome by construction, which makes it informative for
*ranking* while leaving its scale arbitrary, so averaging it into a reasonably calibrated
*p*~near~ preserves ordering and distorts scale. The resulting score is still a risk
estimate in the sense of being a number in [0, 1], just a poorly calibrated one, which is
why the remedy is recalibration rather than abandonment. Both variants also compress the
predicted range so severely that no patient receives a risk below 0.1, against 14.5% of
patients under nearest alone.

The logistic stack does not share this defect. Being fit to the outcome, it slightly
improves on the baseline in both Brier at 0.141 and weighted calibration error at 0.003.
Variants (a) and (b) should accordingly be treated as ranking scores only, absent an
explicit out-of-fold recalibration step. Variant (c) requires no such caveat.

## S7.3 Interpretation

The fusion hypothesis is rejected on this cohort. The farthest-retrieval signal is real,
and the direction of its inversion is recoverable from the data without being specified
in advance, and it is not additive to nearest retrieval. The plausible reason is that
both are readings of the same embedding geometry over the same patients, so the inverted
farthest score largely restates information the nearest score already carries. Fusion
across *different* representations, or across encoders whose geometries disagree, is a
materially different proposition and remains untested.

This analysis is exploratory, single-encoder, and conducted post hoc on the held-out
test set. It is reported for completeness and to close a question the main text raises,
not as a confirmatory result.

# Supplement S8. Discrimination stratified by length of pre-index history

The main text tests the volume and recency confound by correlating the TRD label with
three proxies for how much data a patient has, and finds all three associations weak and
negative. That test asks whether the *outcome* tracks data volume. This section asks the
stronger question: whether *discrimination* tracks it. That is what one would expect if
the predictor were partly reading data volume rather than clinical content.

The held-out test set was divided into quintiles of pre-index history length and the
neighbour-weighted predictor scored within each. The nearest-retrieval, judge-weighted
arm is reported in Table S7, and the pattern is the same for the other weighting
strategies.

***Table S7.** Neighbor-weighted discrimination by quintile of pre-index
history length (nearest retrieval, LLM weighting, embedded representation,
held-out test set). Quintile bounds are in days of pre-index history.*

| Pre-index history (days) | Patients | ROC AUC |
| --- | ---: | ---: |
| 731–1,110 | 1,706 | 0.588 |
| 1,110–1,554 | 1,704 | 0.601 |
| 1,554–2,066 | 1,701 | 0.572 |
| 2,066–2,733 | 1,704 | 0.613 |
| 2,733–5,288 | 1,701 | 0.579 |

Discrimination is flat across the range. The spread between best and worst quintile is
0.041 ROC AUC with no monotone trend, across a span of history length that varies more
than fourfold from the shortest quintile to the longest. Had the predictor been
exploiting record volume, discrimination should have risen with it. It does not.

Two limits attach to this analysis. It covers the neighbour-weighted arm only rather
than the trained classifiers that carry the main comparison, because the stratification
was computed over the neighbour predictions. And each quintile holds roughly 1,700
patients, so the per-quintile estimates are individually imprecise and the claim rests on
the absence of a trend rather than on any single value. A parallel stratification by
embedding-neighbourhood density was computed and is not reported: the density
distribution is concentrated enough that three of its five bins were empty, leaving too
little coverage to interpret.

# Supplement S9. The held-out set against the training set

The main text reports the split's sizes and outcome counts and states that every
per-predictor standardized mean difference is small. This section shows the distributions
behind that statement, because a claim about comparability that is asserted rather than
displayed cannot be checked by a reader.

The split is the frozen stratified 80/20 split every evaluation in this paper uses.
Nothing was refit or re-split to produce this table, and the standardized mean
differences use the same pooled-standard-deviation definition as main-text Table 1, so
the two tables are directly comparable.

Over the 100 predictor rows the largest absolute value is 0.036, and no row reaches the
conventional 0.1 threshold for a non-trivial imbalance. The maximum sits on a
social-determinant flag recorded for 22 training patients and none of the held-out
patients. That is a small-cell artifact rather than a distributional difference: the
flag's prevalence is 0.1% in the arm that has it. The outcome rate matches by
construction, the split having been stratified on it, and is therefore not evidence of
anything.

***Table S8.** Held-out patients against training patients on the characteristics
reported in main-text Table 1. Continuous variables are median with interquartile range,
and categorical and boolean entries are n with per cent. SMD is training minus held-out,
in pooled standard deviations. Vital signs are shown because they describe the cohort.
They are rendered only in the narrative representation and are absent from the feature
matrix as published, as Supplement S11 records.*

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

**What this does and does not establish.** It establishes that the patients the models
were scored on are distributionally interchangeable with the patients they were trained
on, so the reported discrimination is not an artifact of an unrepresentative evaluation
sample.

It establishes nothing about representativeness of any wider population. The delivered
extract is case-enriched by design and both halves of the split inherit that enrichment
equally, and a table comparing two halves of a selected cohort cannot detect the
selection they share. The calibration reported in this paper remains calibration to this
cohort's own base rate, and the limitation stands as written.

# Supplement S10. Subgroup discrimination and calibration

This paper makes no fairness claim. The permutation slate it reports measures how much a
model's discrimination depends on a concept being present in its input, which is a
different question from whether performance is even across groups. This section reports
the subgroup evidence itself.

## S10.1 Design

**Nothing was refit.** The per-patient held-out predicted probabilities the pipeline
persists were partitioned by stratum, and discrimination and calibration recomputed
inside each group. Subsetting a per-patient prediction vector is arithmetically
identical to scoring that model on the subset, so no published number can drift.
Refitting within a subgroup would answer a different question, namely how a model
trained only on one group predicts that group, and it would break comparability with
everything else reported.

**All three prediction arms are covered**, not only the classifiers. The embedded and
feature arms contribute their four classifiers each, and the neighbour-weighted arm
contributes its sixteen retrieval-scheme by weighting-strategy configurations. Only the
four nearest-retrieval configurations are *contrasted* across groups. Whether a
deliberately uninformative retrieval scheme is evenly uninformative across subgroups is
not a fairness question, and including the negative controls would triple the
multiplicity burden on the contrasts that are.

**Strata.** Six sociodemographic families and two clinical ones. The sociodemographic
families are sex, race, age band, marital status, smoking status and religion. The
clinical families are MDD recurrence and severity. Race is collapsed to majority against
recorded minority, because a level-by-level breakdown is not estimable at 80.0% White or
Caucasian. Preferred language is absent by necessity rather than by choice: 98.9% of the
cohort prefers English, which leaves one estimable level and therefore no contrast. A
group whose smaller class holds fewer than 20 outcome events is declared not estimable
rather than reported.

**Intervals and multiplicity.** Within-group intervals are percentile bootstraps over
that group's own patients. Between-group intervals are *unpaired* bootstraps, because two
subgroups are disjoint patient sets and each must be resampled independently. That is
unlike the paired test used for the representation contrasts in main-text Figure 3.

Two hundred and eighty-eight contrasts were computed. At that number, nominally
significant results arise from sampling alone, so each contrast carries a two-sided
bootstrap *P* value taken from the same draws and adjusted across the entire reported set
by Benjamini-Hochberg. The adjusted value is what we interpret, and both are tabulated so
a reader can see the effect of the correction.

Calibration slope is the coefficient of a logistic regression of the outcome on the
logit of predicted risk, where 1.0 is perfect. Calibration-in-the-large is mean predicted
risk minus observed rate, where 0.0 is perfect. Both are computed directly rather than
from the binned calibration surface used in main-text Table 3, because a bin-mean fit
over a few thousand patients describes the bin grid more than it describes the model.

## S10.2 Sociodemographic strata

***Table S9.** Discrimination and calibration by sociodemographic stratum, one
representative model per arm, held-out test set. Groups are not disjoint across
families: every patient with a recorded sex appears in one sex row and every
patient with a recorded race in one race row.*

| Group | n | TRD+ | Arm | ROC AUC (95% CI) | Brier | Calibration slope | Calibration-in-the-large |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| All held-out patients | 8,516 | 1,491 | Embedded (logistic regression) | 0.657 (0.643–0.672) | 0.137 | 0.97 | +0.000 |
| All held-out patients | 8,516 | 1,491 | Feature vector (logistic regression) | 0.629 (0.613–0.644) | 0.139 | 0.95 | -0.000 |
| All held-out patients | 8,516 | 1,491 | Neighbour-weighted (nearest, LLM) | 0.595 (0.578–0.610) | 0.142 | 0.52 | -0.011 |
| Male | 2,347 | 386 | Embedded (logistic regression) | 0.653 (0.622–0.682) | 0.131 | 0.94 | -0.003 |
| Male | 2,347 | 386 | Feature vector (logistic regression) | 0.626 (0.595–0.655) | 0.133 | 0.86 | -0.003 |
| Male | 2,347 | 386 | Neighbour-weighted (nearest, LLM) | 0.599 (0.566–0.631) | 0.135 | 0.56 | -0.010 |
| Female | 6,168 | 1,105 | Embedded (logistic regression) | 0.658 (0.641–0.675) | 0.139 | 0.98 | +0.002 |
| Female | 6,168 | 1,105 | Feature vector (logistic regression) | 0.630 (0.612–0.648) | 0.141 | 0.99 | +0.001 |
| Female | 6,168 | 1,105 | Neighbour-weighted (nearest, LLM) | 0.591 (0.572–0.610) | 0.145 | 0.50 | -0.012 |
| White/Caucasian | 6,835 | 1,181 | Embedded (logistic regression) | 0.657 (0.640–0.674) | 0.136 | 0.97 | +0.002 |
| White/Caucasian | 6,835 | 1,181 | Feature vector (logistic regression) | 0.633 (0.615–0.652) | 0.137 | 0.98 | +0.001 |
| White/Caucasian | 6,835 | 1,181 | Neighbour-weighted (nearest, LLM) | 0.605 (0.586–0.623) | 0.140 | 0.57 | -0.011 |
| Non-White (recorded) | 1,631 | 302 | Embedded (logistic regression) | 0.652 (0.620–0.684) | 0.144 | 0.95 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | Feature vector (logistic regression) | 0.608 (0.573–0.643) | 0.147 | 0.79 | -0.004 |
| Non-White (recorded) | 1,631 | 302 | Neighbour-weighted (nearest, LLM) | 0.553 (0.516–0.590) | 0.152 | 0.34 | -0.011 |
| Race not recorded | 50 | 8 | Embedded (logistic regression) | not estimable | — | — | — |
| Race not recorded | 50 | 8 | Feature vector (logistic regression) | not estimable | — | — | — |
| Race not recorded | 50 | 8 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| Age band: 18-29 | 1,085 | 218 | Embedded (logistic regression) | 0.611 (0.568–0.654) | 0.156 | 0.78 | +0.003 |
| Age band: 18-29 | 1,085 | 218 | Feature vector (logistic regression) | 0.570 (0.524–0.615) | 0.160 | 0.60 | +0.012 |
| Age band: 18-29 | 1,085 | 218 | Neighbour-weighted (nearest, LLM) | 0.547 (0.505–0.592) | 0.162 | 0.32 | -0.006 |
| Age band: 30-44 | 1,827 | 372 | Embedded (logistic regression) | 0.653 (0.621–0.682) | 0.154 | 0.95 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | Feature vector (logistic regression) | 0.636 (0.605–0.667) | 0.155 | 1.00 | -0.002 |
| Age band: 30-44 | 1,827 | 372 | Neighbour-weighted (nearest, LLM) | 0.587 (0.552–0.619) | 0.159 | 0.56 | -0.020 |
| Age band: 45-64 | 2,636 | 473 | Embedded (logistic regression) | 0.652 (0.623–0.679) | 0.140 | 0.98 | +0.007 |
| Age band: 45-64 | 2,636 | 473 | Feature vector (logistic regression) | 0.607 (0.580–0.636) | 0.143 | 0.88 | -0.001 |
| Age band: 45-64 | 2,636 | 473 | Neighbour-weighted (nearest, LLM) | 0.593 (0.564–0.620) | 0.145 | 0.55 | -0.010 |
| Age band: 65+ | 2,968 | 428 | Embedded (logistic regression) | 0.658 (0.630–0.682) | 0.117 | 1.10 | -0.005 |
| Age band: 65+ | 2,968 | 428 | Feature vector (logistic regression) | 0.641 (0.614–0.669) | 0.119 | 1.18 | -0.003 |
| Age band: 65+ | 2,968 | 428 | Neighbour-weighted (nearest, LLM) | 0.587 (0.555–0.619) | 0.121 | 0.42 | -0.010 |
| Marital status: Divorced | 882 | 211 | Embedded (logistic regression) | 0.640 (0.593–0.681) | 0.173 | 0.90 | -0.046 |
| Marital status: Divorced | 882 | 211 | Feature vector (logistic regression) | 0.607 (0.563–0.649) | 0.177 | 0.85 | -0.049 |
| Marital status: Divorced | 882 | 211 | Neighbour-weighted (nearest, LLM) | 0.582 (0.537–0.624) | 0.182 | 0.34 | -0.067 |
| Marital status: Never Married | 2,364 | 438 | Embedded (logistic regression) | 0.634 (0.609–0.661) | 0.145 | 0.85 | +0.013 |
| Marital status: Never Married | 2,364 | 438 | Feature vector (logistic regression) | 0.598 (0.569–0.627) | 0.149 | 0.72 | +0.016 |
| Marital status: Never Married | 2,364 | 438 | Neighbour-weighted (nearest, LLM) | 0.566 (0.537–0.597) | 0.151 | 0.40 | -0.002 |
| Marital status: Now Married | 4,251 | 694 | Embedded (logistic regression) | 0.670 (0.650–0.690) | 0.129 | 1.05 | -0.001 |
| Marital status: Now Married | 4,251 | 694 | Feature vector (logistic regression) | 0.644 (0.623–0.666) | 0.131 | 1.10 | -0.002 |
| Marital status: Now Married | 4,251 | 694 | Neighbour-weighted (nearest, LLM) | 0.610 (0.587–0.634) | 0.133 | 0.63 | -0.007 |
| Marital status: Separated | 99 | 21 | Embedded (logistic regression) | 0.518 (0.364–0.673) | 0.171 | 0.08 | +0.001 |
| Marital status: Separated | 99 | 21 | Feature vector (logistic regression) | 0.518 (0.357–0.687) | 0.169 | 0.30 | -0.003 |
| Marital status: Separated | 99 | 21 | Neighbour-weighted (nearest, LLM) | 0.544 (0.378–0.706) | 0.168 | 0.22 | -0.012 |
| Marital status: Widowed | 891 | 120 | Embedded (logistic regression) | 0.654 (0.597–0.708) | 0.111 | 1.09 | +0.022 |
| Marital status: Widowed | 891 | 120 | Feature vector (logistic regression) | 0.625 (0.572–0.678) | 0.112 | 1.17 | +0.017 |
| Marital status: Widowed | 891 | 120 | Neighbour-weighted (nearest, LLM) | 0.576 (0.516–0.629) | 0.116 | 0.38 | +0.001 |
| Smoking status: Current Smoker | 1,126 | 243 | Embedded (logistic regression) | 0.667 (0.631–0.706) | 0.158 | 1.01 | -0.009 |
| Smoking status: Current Smoker | 1,126 | 243 | Feature vector (logistic regression) | 0.617 (0.575–0.660) | 0.162 | 0.87 | -0.011 |
| Smoking status: Current Smoker | 1,126 | 243 | Neighbour-weighted (nearest, LLM) | 0.624 (0.585–0.661) | 0.164 | 0.79 | -0.026 |
| Smoking status: Former Smoker | 2,532 | 443 | Embedded (logistic regression) | 0.663 (0.636–0.690) | 0.137 | 0.98 | +0.003 |
| Smoking status: Former Smoker | 2,532 | 443 | Feature vector (logistic regression) | 0.633 (0.603–0.660) | 0.140 | 0.89 | +0.001 |
| Smoking status: Former Smoker | 2,532 | 443 | Neighbour-weighted (nearest, LLM) | 0.581 (0.549–0.611) | 0.144 | 0.45 | -0.014 |
| Smoking status: Never Smoker | 4,788 | 793 | Embedded (logistic regression) | 0.646 (0.623–0.665) | 0.132 | 0.93 | +0.001 |
| Smoking status: Never Smoker | 4,788 | 793 | Feature vector (logistic regression) | 0.625 (0.603–0.645) | 0.133 | 0.99 | +0.002 |
| Smoking status: Never Smoker | 4,788 | 793 | Neighbour-weighted (nearest, LLM) | 0.586 (0.563–0.607) | 0.136 | 0.45 | -0.006 |
| Religion: Catholic | 608 | 93 | Embedded (logistic regression) | 0.695 (0.634–0.754) | 0.120 | 1.29 | +0.009 |
| Religion: Catholic | 608 | 93 | Feature vector (logistic regression) | 0.648 (0.587–0.710) | 0.124 | 1.06 | +0.002 |
| Religion: Catholic | 608 | 93 | Neighbour-weighted (nearest, LLM) | 0.626 (0.562–0.686) | 0.126 | 0.74 | +0.005 |
| Religion: Non-Christian | 50 | 16 | Embedded (logistic regression) | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | Feature vector (logistic regression) | not estimable | — | — | — |
| Religion: Non-Christian | 50 | 16 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Embedded (logistic regression) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Feature vector (logistic regression) | not estimable | — | — | — |
| Religion: Orthodox | 9 | 3 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| Religion: Other/Unknown | 759 | 145 | Embedded (logistic regression) | 0.615 (0.565–0.664) | 0.151 | 0.72 | -0.013 |
| Religion: Other/Unknown | 759 | 145 | Feature vector (logistic regression) | 0.589 (0.537–0.642) | 0.153 | 0.66 | -0.010 |
| Religion: Other/Unknown | 759 | 145 | Neighbour-weighted (nearest, LLM) | 0.547 (0.494–0.603) | 0.155 | 0.31 | -0.021 |
| Religion: Protestant | 4,654 | 793 | Embedded (logistic regression) | 0.665 (0.644–0.685) | 0.134 | 1.00 | +0.003 |
| Religion: Protestant | 4,654 | 793 | Feature vector (logistic regression) | 0.642 (0.620–0.662) | 0.135 | 1.05 | +0.002 |
| Religion: Protestant | 4,654 | 793 | Neighbour-weighted (nearest, LLM) | 0.601 (0.580–0.624) | 0.139 | 0.56 | -0.011 |

## S10.3 Clinical strata

***Table S10.** Discrimination and calibration by recorded depression phenotype,
one representative model per arm.*

| Group | n | TRD+ | Arm | ROC AUC (95% CI) | Brier | Calibration slope | Calibration-in-the-large |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| MDD severity: Mild | 633 | 105 | Embedded (logistic regression) | 0.683 (0.624–0.742) | 0.130 | 1.39 | -0.020 |
| MDD severity: Mild | 633 | 105 | Feature vector (logistic regression) | 0.607 (0.547–0.667) | 0.135 | 0.86 | -0.018 |
| MDD severity: Mild | 633 | 105 | Neighbour-weighted (nearest, LLM) | 0.558 (0.501–0.619) | 0.139 | 0.36 | -0.026 |
| MDD severity: Moderate | 1,426 | 255 | Embedded (logistic regression) | 0.652 (0.618–0.687) | 0.142 | 0.98 | +0.003 |
| MDD severity: Moderate | 1,426 | 255 | Feature vector (logistic regression) | 0.634 (0.599–0.670) | 0.142 | 1.06 | +0.001 |
| MDD severity: Moderate | 1,426 | 255 | Neighbour-weighted (nearest, LLM) | 0.595 (0.556–0.631) | 0.146 | 0.57 | -0.007 |
| MDD severity: Psychotic | 18 | 8 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD severity: Psychotic | 18 | 8 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD severity: Remission | 143 | 19 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| MDD severity: Severe | 468 | 137 | Embedded (logistic regression) | 0.700 (0.648–0.749) | 0.187 | 1.21 | +0.029 |
| MDD severity: Severe | 468 | 137 | Feature vector (logistic regression) | 0.636 (0.578–0.690) | 0.197 | 0.88 | +0.029 |
| MDD severity: Severe | 468 | 137 | Neighbour-weighted (nearest, LLM) | 0.665 (0.611–0.716) | 0.193 | 0.99 | -0.001 |
| MDD severity: Unspecified | 5,828 | 967 | Embedded (logistic regression) | 0.641 (0.621–0.660) | 0.133 | 0.94 | -0.000 |
| MDD severity: Unspecified | 5,828 | 967 | Feature vector (logistic regression) | 0.615 (0.595–0.634) | 0.134 | 0.98 | -0.001 |
| MDD severity: Unspecified | 5,828 | 967 | Neighbour-weighted (nearest, LLM) | 0.575 (0.555–0.595) | 0.138 | 0.40 | -0.012 |
| MDD recurrence:  | 32 | 7 | Embedded (logistic regression) | not estimable | — | — | — |
| MDD recurrence:  | 32 | 7 | Feature vector (logistic regression) | not estimable | — | — | — |
| MDD recurrence:  | 32 | 7 | Neighbour-weighted (nearest, LLM) | not estimable | — | — | — |
| MDD recurrence: Dysthymia | 584 | 97 | Embedded (logistic regression) | 0.690 (0.638–0.748) | 0.130 | 1.33 | +0.008 |
| MDD recurrence: Dysthymia | 584 | 97 | Feature vector (logistic regression) | 0.627 (0.565–0.687) | 0.134 | 1.13 | +0.010 |
| MDD recurrence: Dysthymia | 584 | 97 | Neighbour-weighted (nearest, LLM) | 0.584 (0.526–0.650) | 0.137 | 0.56 | +0.001 |
| MDD recurrence: Recurrent | 2,177 | 433 | Embedded (logistic regression) | 0.698 (0.671–0.726) | 0.146 | 1.09 | -0.000 |
| MDD recurrence: Recurrent | 2,177 | 433 | Feature vector (logistic regression) | 0.676 (0.648–0.703) | 0.148 | 1.07 | -0.002 |
| MDD recurrence: Recurrent | 2,177 | 433 | Neighbour-weighted (nearest, LLM) | 0.650 (0.623–0.678) | 0.151 | 0.79 | -0.011 |
| MDD recurrence: Single Episode | 5,723 | 954 | Embedded (logistic regression) | 0.633 (0.612–0.652) | 0.134 | 0.86 | +0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | Feature vector (logistic regression) | 0.605 (0.584–0.626) | 0.136 | 0.83 | -0.000 |
| MDD recurrence: Single Episode | 5,723 | 954 | Neighbour-weighted (nearest, LLM) | 0.565 (0.543–0.585) | 0.139 | 0.33 | -0.012 |

## S10.4 What survives correction

Seventy-two of the 288 contrasts exclude zero unadjusted, and **35 survive
Benjamini-Hochberg adjustment**. They are not the ones the analysis was commissioned to
look for.

***Table S11.** Contrasts surviving Benjamini-Hochberg adjustment across all 288
reported comparisons, grouped by contrast and arm. "Models surviving" counts how
many of that arm's contrasted models cleared the threshold.*

| Contrast | Arm | Models surviving | ΔROC AUC range | smallest p (BH) |
| --- | --- | ---: | ---: | ---: |
| Age: 18-29 vs rest | Feature vector | 3 of 4 | -0.071 to -0.066 | 0.0384 |
| Marital status: Never Married vs rest | Embedded | 2 of 4 | -0.054 to -0.051 | 0.0125 |
| MDD recurrence: Recurrent vs rest | Embedded | 4 of 4 | +0.059 to +0.072 | 0.0125 |
| MDD recurrence: Recurrent vs rest | Feature vector | 4 of 4 | +0.060 to +0.068 | 0.0125 |
| MDD recurrence: Recurrent vs rest | Neighbour-weighted | 4 of 4 | +0.075 to +0.082 | 0.0125 |
| MDD recurrence: Single Episode vs rest | Embedded | 4 of 4 | -0.071 to -0.065 | 0.0125 |
| MDD recurrence: Single Episode vs rest | Feature vector | 4 of 4 | -0.064 to -0.054 | 0.0230 |
| MDD recurrence: Single Episode vs rest | Neighbour-weighted | 4 of 4 | -0.077 to -0.073 | 0.0125 |
| MDD severity: Severe vs rest | Neighbour-weighted | 4 of 4 | +0.086 to +0.087 | 0.0384 |
| MDD severity: Unspecified vs rest | Neighbour-weighted | 2 of 4 | -0.051 to -0.047 | 0.0125 |

**Sex: no difference anywhere.** All twelve male-minus-female contrasts include
zero, across every arm and model, and the largest absolute difference is 0.012
ROC AUC. Nothing here needs qualification.

**Race: consistent in direction, not significant after correction.** All twelve
White-minus-non-White contrasts are positive, from +0.005 to +0.055 ROC AUC, and seven
exclude zero unadjusted. Those seven include all four neighbour-weighted configurations,
which is a structurally different predictor reproducing the same sign. None survives
adjustment, and the smallest adjusted *P* is .08. Calibration moves the same way in the
feature arm, where the slope among non-White patients is 0.79 against 0.98 among White
patients, while the embedded arm holds at 0.95 against 0.97.

The correct reading is neither "no difference" nor "a gap of 0.04". This cohort lacks
the power to settle it. The minority stratum carries 302 outcome events against 1,181,
so its intervals are roughly twice as wide, and a real difference of the size observed
could as easily have gone undetected.

What the data do show is a sign consistent across twelve contrasts and three independent
predictor families, which is not the shape sampling noise usually takes. Alongside it
sits a calibration deficit concentrated in one representation. Both are reported for
that reason, and neither is claimed as established.

What the data do show is a sign consistent across twelve contrasts and three independent
predictor families, which is not the shape sampling noise usually takes, together with a
calibration deficit concentrated in one representation. Both are reported for that
reason. Neither is claimed as established.

**What does survive is how the depression is coded.** Twenty-four of the 35 surviving
contrasts concern MDD recurrence and severity. Discrimination is higher among patients
coded with recurrent MDD, by +0.059 to +0.082 against the rest, and lower among those
coded single-episode, by −0.077 to −0.054, in twelve of twelve arm-model combinations in
each direction. Severity behaves the same way in the neighbour-weighted arm: higher among
patients coded severe at +0.086, lower among those coded unspecified at −0.051 to −0.047.

The pattern is coherent and it is as much about documentation as about phenotype. The
models discriminate better where the diagnosis is recorded specifically and worse where
the coding is left unspecified, which is the majority of this cohort: 5,828 of 8,516
held-out patients are coded unspecified severity.

**Two sociodemographic contrasts survive**, and both point the same way as the
documentation story. Discrimination is lower among patients aged 18-29 than among the
rest in the feature arm, by −0.071 to −0.066 in three of four classifiers with an
adjusted *P* of .04. It is also lower among never-married patients in the embedded arm,
by −0.054 and −0.051 with an adjusted *P* of .01. Younger and never-married patients
accumulate less recorded history, which is consistent with thinner records supporting
weaker prediction. This analysis cannot separate that explanation from any other.

![](../results/review/subgroups/subgroup_forest.png){width=6in}

***Figure S9.** Subgroup discrimination across sociodemographic strata, one
representative model per arm, with 95% bootstrap confidence intervals. The dotted
line marks chance. Strata declared not estimable are omitted.*

# Supplement S11. Field-level crosswalk of the two representations

The head-to-head comparison in this paper is between two encodings of one record, so it
is only a comparison of encodings to the extent that both encodings are given the same
fields. They are not, and this section is the field-by-field accounting that difference
requires. Every row was read off the pipeline source rather than from the manuscript's
description of it: `scripts/data_loading/feature_vector.py` for the feature column, and
`scripts/data_loading/deterministic_narrative.py` for the rendered text.

Temporal availability is the same for every row and is stated once here rather than
repeated thirty times. Every field is measured at or before the index date, inside the
730-day lookback window, except recorded history length, which measures the window's own
extent. No field in either representation reads post-index data.

***Table S12.** Field-level crosswalk. **Asymmetric** marks a row where the two
representations do not receive the same information. Missing-value rules are as
implemented, not as intended.*

| Source field | Feature-matrix encoding | Narrative rendering | Missing-value rule | Parity |
| --- | --- | --- | --- | --- |
| MDD recurrence, severity | two categorical columns | `Condition: MDD (recurrence, severity)` | empty string is a level in both | matched |
| Index date | **no column** | `Index date: YYYY-MM-DD` | never missing | **asymmetric** |
| Lookback window width | no column (constant) | `Baseline window: −730...0 days` | never missing | matched (carries no information) |
| MDD-to-index gap | `mdd_to_anchor_days`, float | `MDD-to-anchor gap: N days` | never missing | matched |
| Encounter count in window | `num_encounters`, float | `Encounters in window: N` | never missing | matched |
| MDD inside lookback window | `mdd_within_window`, boolean | `MDD within window: Present/Absent` | never missing | matched |
| Recorded pre-index history length | `pre_anchor_history_days`, float | **not rendered** | never missing | **asymmetric** |
| Age | `AgeInYears`, float | `AgeInYears: N` | never missing | matched |
| Sex | categorical | `Sex: X` | absent value becomes its own one-hot level; narrative prints the raw token | matched |
| Race / ethnicity | categorical, seven levels | `Race_Ethnicity: X` | own one-hot level; narrative prints raw token | matched |
| Preferred language | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Marital status | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Religion | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Smoking status | categorical, **collapsed to three levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Sexual orientation | **no column** | `SexualOrientation: X` | **rendered as the literal token `nan`** when recorded-but-empty | **asymmetric** |
| Social determinants of health | nine boolean columns | `SDOH:` list of present categories only | absence is an explicit False in the matrix, an omission from the list in the narrative | matched in content |
| BMI, systolic BP, diastolic BP | **dropped at load** | `BMI: N \| BP (mean): S/D`, or `Missing` | dropped, so no rule; narrative prints `Missing` | **asymmetric** |
| Psychiatric comorbidity (8 flags) | eight boolean columns | `ARM: Present/Absent` for all eight | never missing | matched |
| Suicidality flag | boolean | `SUICIDE FLAG (2y): Present/Absent` | never missing | matched |
| Substance-use specifics (10) | ten boolean columns | names of present substances only | absence explicit in matrix, omitted in narrative | matched in content |
| General medical comorbidity (4) | four boolean columns | `ARM: Present/Absent` for all four | never missing | matched |
| Prior adequate AD trials | five `trials_<class>` counts | `Prior adequate AD trials: CLASS: n` for all five | never missing | matched |
| Benzodiazepine days | `benzo_days_coverage`, float | `Benzodiazepine days (2y): N` | never missing | matched |
| Hypnotics | `hypnotics_burden`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| Active medications | `polypharmacy_count`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| NSAIDs | `nsaid_count`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| Psychiatric inpatient days, ED visits | two float columns | `Psych inpatient days: N \| ED psych visits: N` | never missing | matched |
| Prescribing-safety comorbidity (2) | two boolean columns | `ARM: Present/Absent` | never missing | matched |

**What the crosswalk shows.** The imbalance is not symmetric, and it is larger than a
count of fields suggests. Eleven rows are asymmetric and ten of them favour the
narrative:

- two fields it renders and the matrix has no column for, the index date and sexual
  orientation;
- three vital signs the matrix drops at load;
- four sociodemographic fields where the matrix collapses raw Epic values into coarse
  categories and the narrative prints the raw token;
- three medication blocks where the matrix carries a count and the narrative names the
  ingredients.

One row favours the feature matrix: recorded history length, which the narrative does not
render.

Two rules are worth stating because they are easy to assume wrongly. Missingness is
*not* silently imputed on the categorical side of the feature matrix. An absent value
becomes its own one-hot level, so the model can use the fact of a missing record. And the
vital signs were dropped rather than imputed, so the published feature arm never saw them
in any form. That reason is mechanical rather than principled: a numeric column carrying
nulls cannot pass through the pipeline's scaler.

Whether this imbalance carries the head-to-head result was tested rather than conceded.
The two largest asymmetries were closed and the primary comparison re-run on matched
inputs. The feature matrix received the vitals under an explicit missingness indicator
per block with within-fold median imputation, and the narrative rendered recorded
history length. The best-versus-best contrast remains a null on matched inputs. That
analysis is reported separately and is available from the corresponding author, and the
main text states the imbalance itself, which is what bounds the claim.

# Supplement S12. Subgroup outcome prevalence

This section reports the *within-subgroup prevalence* of TRD: the number of TRD-positive
patients divided by the total patients in that subgroup. Main-text Table 1 gives column
percentages conditioned on TRD status rather than row percentages, so the prevalences
below were computed from the raw subgroup counts. The 18-29 age band is the worked
example: its TRD prevalence is 20.6%, or 1,135 TRD-positive patients out of 5,513.

TRD prevalence varied modestly across subgroups. By sex it was 18.0% in women against
16.2% in men. By age band it followed a clear gradient. The two youngest bands were
highest and nearly tied, at 20.6% in 18-29-year-olds (1,135 of 5,513) and 20.3% in
30-44-year-olds (1,836 of 9,025). It then fell through 18.4% at 45-64 (2,445 of 13,268)
to 13.8% in those aged 65 or older (2,039 of 14,773).

Several small social-determinant strata showed elevated but imprecise prevalence: an
upbringing-related issue at 33.0%, a legal or criminal issue at 26.1%, an employment
issue at 24.0%, and a family or support-group issue at 22.9%. Patients with missing race
or ethnicity did not show elevated prevalence, at 15.5% against the 17.5% base rate.
Strata with fewer than 20 patients set a small-cell ceiling on the subgroup performance
analysis in Supplement S10. A psychosocial-circumstances flag, at n = 12, is one such
stratum.