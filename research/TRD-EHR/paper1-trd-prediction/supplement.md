<!--
Supplementary material for the TRD prediction manuscript (manuscript.md).
Convert alongside the main text at submission: pandoc supplement.md -o supplement.docx.

WHAT LEFT THIS PACKET, all on 2026-09-06. Each is complete and unretracted in
reserve/; none was withdrawn for being wrong.

  * The LLM clinical-similarity judge, when the neighbor-weighting slate was cut
    to uniform and cosine.            reserve/llm_similarity_judge.md
  * The nearest-farthest retrieval fusion, with the farthest and subsampled
    retrieval schemes.                reserve/nearest_farthest_fusion.md
  * The encoder similarity geometry, a bimodality artifact in the weakest of the
    four encoders.                    reserve/encoder_similarity_geometry.md

None of the three served a point the paper makes.

THE FINAL-REVIEW ROUND, 2026-09-07. Six defects in this document, recorded
because the same ones will be reachable again. "Feature matrix" was an
undeclared third name for the feature vector, seven uses. S1.3 called S1.1's
"concentrated in a sparse subset" conclusion "the same broadly-distributed-
signal conclusion", which is the opposite claim; both halves are true and S1.3
now says which is which. S8 asserted that the field asymmetry "was tested
rather than conceded" and the test is reserve/matched_input_parity.md, not in
this packet. S9 defined the small-cell rule as "fewer than 20 patients" where
S7.1 defines it as fewer than 20 outcome events. S7.4 reported two
never-married deltas without saying they are two of four classifiers. And 38
spellings were British, 36 of them "Neighbour-weighted" cells in S7's tables
against "neighbor-weighted" everywhere else. The manuscript's header comment
carries the full account of the round.

CURRENT NUMBERING, after all of it: Supplements M1-M13 and S1-S9, Tables S1-S9,
Figures S1-S4. All contiguous, every reference resolves. Deliberately stated as
the current state rather than as a chain of "was X, now Y" — three renumbering
passes rewrote the numbers inside the previous version of this note and left it
describing a history that never happened.

Naming: the two representations are the FEATURE representation ("feature
vector", "typed feature vector", "feature-vector XGBoost") and the EMBEDDED
representation. "Rule-based" is not an alias for either, and neither is
"feature matrix", which was removed from this document on 2026-09-07 -- seven
uses, all of them a second name for the feature vector. See the naming block in
manuscript.md for the full rule.
-->

*Supplements M1-M13 are the **Supplementary Methods**: they carry the
methodological detail condensed out of the main text. Every statement in
them is a fuller form of something the Methods section states or points
at, and nothing reported in the main text depends on material that
appears only there. Supplements S1-S9 are supporting analyses and
extended results.*

# Supplement M1. Source data, setting, and sampling frame

The study used a single de-identified extract from the Epic EHR of Saint
Francis Health System. Seven files were delivered: person, encounter,
diagnosis, medication, procedure, and laboratory/flowsheet tables together
with a medication-to-RxNorm mapping table. The clinical tables originated
from the Caboodle enterprise data warehouse. The RxNorm mapping originated
from the Clarity reporting database. Body mass index and systolic and
diastolic blood pressure were obtained from the laboratory/flowsheet table.
Each table was delivered as a flat file after patient and encounter keys had
been replaced by one-way MD5 hashes, and was transferred by secure file
transfer protocol. No names, medical record numbers, direct identifiers, or
dates of birth were included.

The delivering data team restricted the person table to one administrative
division of the health system and to patients who were current, valid,
non-test, non-historical, not recorded as deceased, and aged 18-110 years at
extraction. Eligible source encounters were completed on or before the
extraction date, had at least one associated diagnosis, and had an
inpatient, outpatient, observation, or emergency patient class.

Investigators prespecified the diagnosis code lists. Depression comprised
ICD-9 codes 296.2, 296.3, 300.4, and 311 or ICD-10 codes F32.\*, F33.\*, and
F34.1. Bipolar disorder comprised ICD-9 codes 296.0 and 296.4-296.8 or
ICD-10 codes F30.\* and F31.\*. Schizophrenia-spectrum disorders comprised
ICD-9 codes 295.\* and 298.\* or ICD-10 codes F20.\*, F23.\*, F25.\*, F28.\*,
and F29.\*.

The extract was assembled as a case-enriched sample. All patients with a
depression diagnosis on the problem list were retained, and a random sample
of patients without that flag was added at an approximate 4:1
unflagged-to-flagged ratio. The remaining tables were then linked to the
person table. The delivered extract included 501,718 patients: 100,420
(20.0%) with and 401,298 (80.0%) without a problem-list depression flag.

Sampling used the problem list, whereas study eligibility used diagnoses
recorded at individual encounters. A depression code entered at a visit is a
documented diagnosis whether or not it was ever added to the problem list. In
routine care the problem list is frequently not updated, so the two sets
overlap without either containing the other. Of the 42,579
analysis-cohort patients, 12,530 (29.4%) qualified through an encounter-level
depression diagnosis despite lacking the problem-list flag and therefore
entered through the randomly sampled group. The analysis cohort is
consequently a sample, not an enumeration, of the health system's patients
with depression, and cohort TRD and subgroup proportions are not population
prevalence estimates. The paired comparison between representations remains
internally valid because both were evaluated in the same patients on the
same held-out split.

The setting is a single community health system in Tulsa, Oklahoma, serving
inpatient, outpatient, observation, and emergency care. Patients enter the
cohort through routine antidepressant prescribing across those settings
rather than through psychiatric specialty referral, and the index
prescription may be written in any of them.

# Supplement M2. Eligibility cascade, index selection, and temporal design

Eligibility was applied hierarchically from the full delivered extract.
Patients were required to have all six of the following. 1. A qualifying MDD
diagnosis. 2. No bipolar-disorder diagnosis and no schizophrenia-spectrum
diagnosis, so that the cohort is unipolar depression. 3. An eligible
antidepressant index prescription. 4. An MDD diagnosis recorded on or before
the index date. 5. At least 730 days of pre-index history. 6. At least 365 days
of post-index follow-up. Patients failing the chronological or observation
prerequisites were assigned explicit rejection reasons for attrition
accounting.

***Table M1.** Participant flow through the hierarchical eligibility filters.
Each row applies one additional filter to the survivors of the row above. The
first row is the delivered extract, a case-enriched sample by design
(Supplement M1).*

| Stage | Remaining | Rejected at stage |
| --- | ---: | ---: |
| Delivered extract (4:1 case-enriched) | 501,718 | — |
| MDD-diagnosed | 144,110 | 357,608 |
| Not bipolar AND not schizophrenia-spectrum | 124,188 | 19,922 |
| Has antidepressant index prescription | 107,636 | 16,552 |
| Has MDD before index | 103,458 | 4,178 |
| ≥2 years pre-index history | 54,215 | 49,243 |
| ≥1 year post-index follow-up (final cohort) | 42,579 | 11,636 |

Upstream data preparation assembled, for each patient, all antidepressant
medication orders beginning on or after the date of the first documented
depression diagnosis. The earliest start date in that set defined the index
date, one per patient. Among candidate index orders, 57.9% begin on the same
date as the first recorded depression diagnosis.

No post-index property was used to qualify the index exposure. Dose adequacy,
exposure duration, subsequent response, and treatment changes were not
considered, so the prediction point is the moment the prescription is
written. Post-index data entered only through the requirement for at least
365 days of follow-up and outcome ascertainment during those 365 days.
Predictors used only information within the 730 days ending on the index
date. Although recorded history extends further back for many patients
(median 1,792 days), clinical content outside the fixed lookback window was
not read. Total recorded history length was itself retained as a predictor.

Antidepressant exposure before the index date did not exclude a patient.
The index is tied to the first documented depression diagnosis rather than to
the first antidepressant exposure. Consequently 24.0% of the cohort had some
recorded pre-index antidepressant exposure, and 14.7% had at least one pre-
index course meeting the 42-day threshold used for the adequate-trial
predictors. The index is therefore best described as the first antidepressant
prescription after a documented depression diagnosis, and not as the first
antidepressant treatment or first adequate trial.

# Supplement M3. Outcome construction and inferential boundary

The binary outcome was generated in the upstream R data-preparation pipeline
independently of the predictors and supplied to the modeling workflow as a
fixed label. TRD was assigned when a patient with MDD received at least three
distinct antidepressant treatments within 365 days of the index date, the
index agent counting as the first. Patients with fewer than three treatments
were classified TRD-negative.

A treatment is a distinct antidepressant agent rather than an order or
prescribing event. Addition of a second agent while the current
antidepressant continues is augmentation and does not advance the outcome
count. Restarting a previously used agent also does not advance it.
Augmentation is available as a pre-index predictor where its definition is
met.

The 365-day follow-up requirement ensures that every patient has the
observation window needed to determine the label, so a negative label
reflects an absence of further antidepressant treatments rather than an
absence of observation. It does not guarantee that care delivered outside
the health system was captured.

The label approximates, but does not establish, the consensus
characterization of TRD as inadequate response to at least two antidepressant
trials of adequate dose and duration [4,5]. Non-response is inferred from
switching rather than measured, because standardized symptom severity is not
systematically recorded in this extract. Dose and duration adequacy were not
verified for the counted post-index treatments. Changes attributable to
intolerance, adverse effects, cost, formulary restriction, fragmented care,
patient preference, or prescriber practice are therefore counted in the same
way as changes attributable to non-response. Switching also depends on
continuity, access, insurance, and clinical practice, which may differ across
demographic groups [16,17], so the target can encode health-care process and
inequity in addition to pharmacologic non-response. The label was not
validated against chart review or a symptom-severity criterion. Future
validation should compare it with adjudicated treatment histories and symptom
trajectories, and should test a higher-specificity outcome requiring
documented adequate courses.

# Supplement M4. Predictor selection and the typed feature representation

The candidate predictor set was specified before model fitting and before
predictor-outcome associations were examined. The approach followed manual
clinical and literature-based selection, as in the treatment-resistance model
of Perlis [18], rather than univariate screening or automated selection. No
variable was retained or removed because of its observed association with
TRD, and no automated selection step ran at any stage.

The selected domains reflect prior treatment-resistance and
antidepressant-response research: depression severity and recurrence;
psychiatric and substance-use comorbidity, medical comorbidity, prior
antidepressant exposure and medication burden, health-care utilization, and
sociodemographic characteristics [18,19]. Unlike clinical-trial studies that
use scheduled symptom scales and structured interviews, this study is
restricted to structured fields recorded in routine EHR care, so depression
severity enters as diagnostic coding rather than as a rating-scale score.
Prior EHR prediction studies informed the feasible domains [20,21].

Prescribing-constraint flags were retained because they describe whether
escalation options may be limited. Sociodemographic and social-determinant
fields were retained so that their direct contribution could be tested by the
semantic-feature ablation rather than rendered unobservable by design. The
only prespecified fields later removed were body mass index and systolic and
diastolic blood pressure, for the missingness reasons in Supplement M6 rather
than because of any association with the outcome.

FEATURE assigns an explicit type to every field. Quantitative counts and
durations are continuous, including encounter count, pre-index history
length, age, per-agent adequate-trial counts, and medication burden. Single
binary flags and multi-label indicator sets are boolean, including
psychiatric and medical comorbidity, prescribing constraints, substance-use
categories, and social-determinant categories. Single-valued nominal
variables are categorical, including sex, preferred language, marital status,
religion, smoking status, race/ethnicity, MDD recurrence, and coded MDD
severity. An adequate prior antidepressant trial requires at least 42 days of
continuous exposure to an agent. The complete predictor inventory, with each
field's type and encoded form, is Multimedia Appendix 1.

# Supplement M5. Deterministic narrative and embedded representation

The same pre-index record was rendered deterministically into a human-readable
Markdown narrative, and two examples are reproduced in Supplement S4.
Rendering is rule-driven and reproducible: no generative language model
participates in construction. This choice prioritizes traceability over
fluency, because an unsupported generated statement would silently alter the
patient's model input [22].

**What the renderer is given, and what it is not.** It walks a fixed template
of section headings and field labels, in a fixed order, over the field
inventory selected in Supplement M4. That is the same inventory the feature
vector receives. Absent findings are printed explicitly and unrecorded ones as
a literal token, so every patient reaches the encoder through the same constant
form and the narrative's length varies only with how much of that inventory is
populated. The renderer never reads the record outside the 730-day lookback
window, and it never reads a field that predictor selection did not choose. An
untailored encoding of a whole record is therefore a different experiment and
not a variant of this one. The main text states why it was not attempted
(Methods, *Predictors and patient representations*).

Each narrative was mapped to a fixed-length vector with a pretrained
sentence-transformer encoder [28]. The four independently evaluated encoders
were `bge-small-en-v1.5` [23], `bge-en-icl` [24], `Qwen3-Embedding-4B`, and
`Qwen3-Embedding-8B` [25]. This serialization-and-encoding strategy follows
evidence that general-purpose language-model embeddings of serialized EHR
records can perform competitively with purpose-built EHR foundation models
across prediction tasks [15].

FEATURE and EMBEDDED use the same timeline-sliced source record but not an
identical set of rendered fields. The field-level crosswalk in Supplement S8
gives, for every source field, its FEATURE encoding, narrative rendering,
missing-value rule, and temporal availability. Because the field inventories
differ, the comparison is between complete representation pipelines and is
not a controlled comparison of numeric versus language encoding of identical
information.

# Supplement M6. Missing-data handling

No statistical imputation was performed. Mean body mass index and mean
systolic and diastolic blood pressure were present in the intermediate
feature file but removed from the FEATURE representation at load time. Each value is
the within-patient mean across that patient's own pre-index encounters, not a
mean across patients. Mean body mass index was missing for 22.1% of patients,
and at least one vital sign was absent for 21.0%. Body mass index was missing
for 28.8% of TRD-positive and 20.6% of TRD-negative patients, an approximately
8-percentage-point difference.

That association rules out missing completely at random but does not
establish missing not at random, which cannot be identified from observed
data: missingness may depend on health-system contact that the recorded
predictors capture only partly. The variables were removed because no
defensible imputation model was available from the observed predictors alone.
No missingness indicators were created for the continuous block, and no NaN
values reached an estimator. Their removal is stated in the main text, Methods, *Missing data and
sample partition*.

Missing categorical values were encoded as a separate level by the FEATURE
one-hot encoder and as the literal token "Missing" in EMBEDDED. Marital and
smoking status are nearly complete (<0.5% missing). Religion is missing for
29.4% overall and shows a monotone age gradient, from 43.8% at ages 18-29 to
17.5% at ages 65 or older, so the missing-category level itself may carry
age-related information. Religion was retained with that indicator level, so the models can use
the fact of an unrecorded value as well as the recorded ones.

# Supplement M7. Sample size and events per variable

No formal a-priori sample-size calculation was performed, because cohort size
was fixed by the eligibility cascade. Model dimensionality is summarized as
events per variable (EPV), the number of TRD-positive patients in the
training set divided by the number of encoded input columns. The numerator is
5,964 events rather than the total training sample of 34,063, because what
limits how precisely a coefficient can be estimated is the size of the
minority class. The denominator is the matrix dimension actually supplied to
the estimator.

FEATURE contains 92 encoded columns, giving EPV = 5,964/92 ≈ 64.8. EMBEDDED
dimensionality is encoder-specific: `bge-small-en-v1.5` has 384 dimensions
(EPV ≈ 15.5), `Qwen3-Embedding-4B` has 2,560 (EPV ≈ 2.3), and `bge-en-icl`
and `Qwen3-Embedding-8B` each have 4,096 (EPV ≈ 1.5). Only the smallest
encoder exceeds the conventional threshold of 10 events per variable.

EPV was developed for lower-dimensional regression and is not a complete
adequacy criterion for high-dimensional regularized learners. The three
larger encoders are therefore interpreted as high-dimensional regularized
models rather than as the low-dimensional regressions for which EPV was
devised. The low ratios nevertheless emphasize overfitting risk. EPV does not
account for the discrimination ranking: `bge-small-en-v1.5` has the most
favorable ratio and is the weakest encoder.

# Supplement M8. Train/test split, comparability, and leakage safeguards

One stratified 80:20 train/test split was generated once and reused for all
models, representations, encoders, and ablations. The training set includes
34,063 patients (5,964 TRD-positive, 17.5%) and the test set 8,516 (1,491
TRD-positive, 17.5%). Standardized mean differences were calculated for every
predictor as the train-minus-test mean difference divided by the pooled
standard deviation. Across 100 predictor rows the largest absolute SMD is
0.036 and none reaches 0.10, and the distributions themselves are Supplement
S6. The largest SMD arises from a rare social-determinant flag present in 22
training patients and no test patient. Outcome frequency is matched by
stratification rather than by observation.

All data-dependent preprocessing occurred inside the cross-validation
pipeline. On each fold, numeric scaling parameters and categorical levels were
learned only from that fold's training rows and then applied to its validation
rows. The final pipeline was fitted on the full training set and evaluated
once on the test set.

In the retrieval analyses all test identifiers were removed from the
searchable index. Each test patient was a query anchor, but every neighbor and
neighbor outcome came from the training set, which prevents self-retrieval,
test-to-test outcome propagation, and any direct use of a test label in
prediction. Train/test comparability supports internal evaluation but does not
establish transportability, because both partitions inherit the same
case-enriched sampling frame.

# Supplement M9. Standard machine-learning pipeline

Four classifiers were fitted to each representation: logistic regression,
random forest, gradient boosting, and XGBoost. For FEATURE, the column
transformer standardized the numeric block, one-hot encoded categorical
variables with binary categories collapsed and unknown inference-time levels
ignored, and cast boolean indicators to integer without further
transformation. EMBEDDED entered through the numeric branch only.

Each classifier and its preprocessing transformer were wrapped in a single
scikit-learn pipeline. Hyperparameters were selected by five-fold grid search
on the training set using ROC AUC as the optimization criterion. The best
configuration was refitted on all training patients and generated held-out
probabilities. The standardizer and the one-hot encoder both estimate their
parameters from data, so fitting either outside the cross-validation loop
would let held-out rows inform their own transformation. Bundling them with
the estimator prevents this. With no imputation anywhere in the pipeline,
these are the only two fitted preprocessing steps, so the cross-validated
estimates carry no preprocessing leakage. Tuning grids are keyed by classifier
only and are identical across representations.

# Supplement M10. Neighbor-weighted retrieval prediction

For EMBEDDED only, the predicted TRD probability for query patient q was the
weighted mean of binary TRD labels among K = 50 retrieved training neighbors:

$$\hat{P}(\mathrm{TRD} \mid q) = \frac{\sum_{i=1}^{K} w_i\, y_i}{\sum_{i=1}^{K} w_i},$$

where $y_i \in \{0,1\}$ is neighbor $i$'s TRD label and $w_i$ its non-negative
weight. No model is fitted anywhere in this arm. The predictor is the observed
outcome rate of a retrieved set of real patients. That is what makes it a
direct test of the premise that a patient's course can be read from the
courses of their closest analogues.

Two weighting strategies are reported. Under uniform weighting all weights are
equal and the prediction is the raw TRD rate of the retrieved set. Under
cosine weighting each neighbor is weighted by its cosine similarity to the
anchor.
Neighborhood concentration was summarized by the effective sample size,

$$\mathrm{ESS} = \frac{\left(\sum_{i=1}^{K} w_i\right)^2}{\sum_{i=1}^{K} w_i^2},$$

which equals $K$ under uniform weighting and falls as weight concentrates on
fewer neighbors. Cosine weighting leaves it essentially unchanged, at a mean ESS of 49.98
against 50.00 under nearest retrieval. That is the mechanical reason the two
weightings return nearly identical discrimination. Within a nearest-neighbor
set the similarities are all high and all close together, so the weights are
nearly uniform whatever the formula.

Two retrieval schemes were evaluated. *Nearest* selects the K training
patients of highest cosine similarity. *Random* draws K training
patients uniformly, as a negative control. This arm is embedding-only,
because cosine similarity is not well defined over mixed categorical and
numeric features.

All test identifiers were removed from the searchable index. Each test patient
was a query anchor, and every neighbor and neighbor outcome came from the
training set, which prevents self-retrieval, test-to-test outcome propagation,
and any direct use of a test label in prediction.

# Supplement M11. Semantic-feature ablation specifications

The ablation measures direct-input reliance. For each target concept, patient
values were reassigned through a random one-to-one cohort-wide donor
permutation, which retains the same marginal set of values while severing the
association between each patient's concept value and their outcome.
Section-level ablations exchange a complete narrative section. Field-level
ablations exchange only the specified field. Perturbed narratives were
re-embedded, but the baseline classifiers were kept frozen, so the resulting
change in ROC AUC answers whether the fitted embedding pipeline relies on that
input, not whether a newly trained model could substitute correlated
information. Like every other predictor, all six concepts are measured at or
before the index date, and permuting one leaves the remainder of the narrative
untouched.

**Psychiatric history** (section). Present/absent indicators for anxiety
disorder, social anxiety disorder, obsessive-compulsive disorder,
posttraumatic stress disorder, adjustment disorder, dysthymia, insomnia, and
any substance-use disorder, any suicidal-ideation or suicide-attempt code in
the two-year lookback, and named substance categories including alcohol,
cannabis, cocaine, nicotine, opioid, and sedative/hypnotic disorders. It
carries documented diagnoses rather than treatments.

**Medication burden** (section). The count and names of distinct active drug
ingredients at the index date across all therapeutic classes, and the count
and names of distinct non-steroidal anti-inflammatory ingredients prescribed
for at least seven days. It stands in for overall medical complexity and pill
burden, not psychiatric treatment specifically.

**Treatment exposure** (section). Four things. Pre-index counts of adequate trials for selective serotonin
reuptake inhibitors, serotonin-norepinephrine reuptake inhibitors, bupropion,
mirtazapine, and vortioxetine, each requiring at least 42 continuous days on
the agent. Total benzodiazepine days covered during the lookback. Hypnotic
agents prescribed for at least seven days. And augmentation, defined as overlap
of an antidepressant with lithium, an antipsychotic, or buspirone for at least
14 days. It is distinct from
all-class medication burden and from the post-index agents used to construct
the outcome.

**Treatment contraindications** (section). Seizure disorder, which weighs
against bupropion, and uncontrolled hypertension, which weighs against
serotonin-norepinephrine reuptake inhibitors. The concept is constraint on
escalation options rather than general medical comorbidity, which the
narrative reports in a separate section that was not permuted.

**Race/ethnicity** (field). The recorded race/ethnicity category, including an
explicit unrecorded level, permuted within an otherwise unchanged
sociodemographic section. Sex, age, preferred language, marital status,
religion, and smoking status were not altered in this ablation.

**Social determinants of health** (field). ICD-10 Z-code categories recorded
during the lookback: education/literacy, employment, occupational exposure,
housing/economic circumstances, social environment, upbringing, primary
support group/family circumstances, psychosocial circumstances, and
legal/criminal circumstances. The narrative renders "None Recorded" when no
qualifying code is present. Only this field was permuted.

The ablation does not determine whether outcome labeling or care processes are
equitable, whether a permuted attribute can be reconstructed from correlated
inputs, or whether discrimination and calibration differ across subgroups. A
negligible race/ethnicity delta, for example, would not exclude the presence
of sociodemographic information in utilization, diagnosis, or treatment
patterns.

# Supplement M12. Evaluation coverage

Standard machine learning, the cross-encoder comparison, and the semantic
ablation all ran on the complete 42,579-patient cohort. All three scored the
shared 8,516-patient test set, with `Qwen3-Embedding-8B` as the primary
encoder.

Retrieval used nearest and random schemes crossed with uniform and
cosine weighting, on all four encoders. The retrieval scheme dominated
the weighting strategy throughout: the two weightings were nearly
indistinguishable under both schemes, while nearest and random separated
cleanly (main text, Table 6). That is what establishes that the
nearest-versus-random ordering and the shortfall against a trained
classifier both generalize across encoders (main text, Table 7).

# Supplement M13. Metrics and uncertainty

Discrimination was measured by ROC AUC. Calibration was summarized by
intercept and slope, with ideal values of 0 and 1. The extract was case-enriched, so the average predicted risk is anchored
to this cohort's own TRD frequency. Carrying the models to a population
with a different rate would require rescaling the probabilities to it.

Continuous probabilities were dichotomized at the test-set threshold
maximizing Youden's J, and sensitivity, specificity, and positive and negative
likelihood ratios were calculated from the resulting confusion matrix.
Selecting and evaluating the threshold in the same test set produces
optimistic operating characteristics. These estimates characterize the ROC
curve and are not proposed for deployment. A clinical threshold would have to
be selected entirely within development data and evaluated in a separate
temporal or external cohort.

Metric confidence intervals were estimated from 1,000 bootstrap
resamples of the test-set patients, drawn with replacement. For ablation contrasts, the same patient resample was applied to the baseline
and perturbed prediction vectors and the ROC AUC difference recomputed. The
point estimate is the full-sample difference, and the 2.5th and 97.5th
percentiles of the bootstrap distribution form the 95% confidence interval. Paired resampling preserves within-patient correlation
and avoids overstating the uncertainty of a difference.

Representation contrasts used the same paired bootstrap.
Classifier-matched comparisons held the learner constant and varied only
FEATURE versus EMBEDDED. The best-feature-versus-best-embedded contrast
compares each representation's strongest classifier, but that classifier
was identified post hoc on the test set, so the contrast is interpreted
descriptively. One resample matrix was reused across all contrasts to
keep them mutually comparable.

No equivalence or noninferiority margin was prespecified. A paired confidence
interval containing zero indicates that superiority was not established at the
precision achieved. It does not establish equivalence.

# Supplement S1. Effective dimensionality of the embedded representation

Individual embedding dimensions carry no clinical meaning. Per-feature
interpretability, available for the feature vector in main-text Figure 6,
therefore does not transfer to the 4,096-dimensional embedded representation. Instead we
characterize *how many* latent dimensions carry the predictive signal, using
three complementary views. All figures are for the primary
`Qwen3-Embedding-8B` encoder on the held-out test set.

## S1.1 Sparsity and cumulative built-in importance

The best logistic-regression fit used an elasticnet penalty (`l1_ratio` 0.25,
`C` 0.01) that zeroed most coefficients. Only 385 of the 4,096 dimensions carry
nonzero weight, so the signal is concentrated in a sparse subset of them. We then ranked dimensions by each fitted classifier's native importance, using
`|coef|` for logistic regression and `feature_importances_` for the tree
ensembles, and accumulated the importance mass. That confirms the
concentration. For logistic regression, 80% of the coefficient magnitude falls
in roughly 179 of the 4,096 dimensions and 90% in roughly 236 (main-text Figure
7). TRD-relevant information is therefore carried by a modest subset of
embedding dimensions rather than spread across the space.

## S1.2 Cumulative univariate correlation

An importance ranking is model-specific. As a model-agnostic check we ranked
dimensions by the absolute Spearman correlation between each dimension and the
outcome, |ρ(dim, y)|, and overlaid that baseline against per-classifier curves
ranking dimensions by |ρ(dim, risk score)| (Figure S1). Divergence between the model-agnostic baseline and a classifier's curve would
flag dimensions the classifier weights through regularization or interactions
that a univariate ranking cannot see. The model-agnostic correlation curve
remained diffuse, with many dimensions each weakly correlated with the outcome.
The elasticnet logistic-regression curve was far more concentrated, the
regularization having selected a compact predictive subset from a broadly
informative space. Only |ρ| is used, because the sign of a correlation on an unnamed latent
dimension is not interpretable.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png){width=6in}

***Figure S1.** Cumulative absolute univariate (Spearman) correlation. One
model-agnostic baseline curve ranks dimensions by |ρ(dim, outcome)|. The four
per-classifier curves rank by |ρ(dim, predicted risk)|. Cumulative fraction of
total |ρ| mass versus rank, with K₈₀ / K₉₀ knees in the legend.*

## S1.3 PCA-K discrimination sweep

To locate the geometric plateau, each classifier was retrained on the top
K ∈ {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024} principal components of the
embedding and its held-out ROC AUC plotted against K (Figure S2).
Discrimination rose steeply over the first handful of components and then
plateaued, with no single low-dimensional projection recovering the full-rank
performance. That matches the diffuse model-agnostic curve in S1.2. The
compact subset in S1.1 is what the elasticnet penalty selects out of a broadly
informative space, not a low-dimensional subspace the signal already occupies.

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

# Supplement S2. Precision–recall performance

The main text reports discrimination as ROC AUC. Under the cohort's ~5:1 class
imbalance (17.5% TRD-positive), ROC AUC can flatter apparent performance
because the true-negative-dominated specificity term stays high regardless of
how the positive class is ranked. The area under the precision–recall curve
(AUPRC) is the complementary view: its no-skill baseline is the positive rate
itself (0.175), not 0.5, and it exposes the precision cost of capturing TRD
cases. We report it here rather than in the main text.

AUPRC tracked ROC AUC closely and remained modest for every model (Table S1):
at this base rate, capturing high recall on the TRD proxy necessarily forces
low precision. No clinical role is inferred from these values. The main text's
Discussion, *Implications and future directions*, records that temporal
and external validation are prerequisites
for any such claim.

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

***Figure S3.** Precision–recall curves for the best classifier on each
representation (held-out test set; primary `Qwen3-Embedding-8B` encoder).
(A) Embedded logistic regression; (B) feature-vector XGBoost. The horizontal
reference is the no-skill baseline (0.175, the positive rate).*

# Supplement S3. Calibration absolute-error metrics

The main text reports calibration shape via the calibration slope and intercept
(main-text Table 3) and the calibration curves (main-text Figure 5). Here we report the two
absolute-error summaries: the Brier score and a weighted calibration error
(WCE), both lower-is-better (Table S3). Brier scores were uniformly near 0.137–0.140 across all eight models, dominated
by the base rate of 17.5% positive. The WCE separated the models more. Gradient
boosting on the embedded representation was lowest (0.004) and logistic
regression on the feature vector next (0.005), consistent with their near-ideal
slopes in main-text Table 3.

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

# Supplement S4. Example patient narratives

The EMBEDDED representation encodes a deterministically rendered Markdown
narrative of each patient's pre-index window (Methods). To make the encoder's
input concrete, we reproduce two representative narratives below, one
TRD-positive and one TRD-negative. Both were extracted by
`scripts/pipeline/neighbors/narrative_audit.py`, which takes the first patient
by sorted de-identified hash in each outcome class (output written to
`results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/narrative_audit/`).
Each narrative contains only structured EHR-derived fields, with no free text,
names, or direct identifiers. The section headers and field order are fixed
across all patients. Absent findings are rendered explicitly ("Absent") and
unrecorded values as "Missing", so every patient is presented to the encoder
through the same constant template.

The renderer's own field labels predate the manuscript's terminology: where the
narrative prints `MDD-to-anchor gap` and `Baseline window`, the manuscript says
the MDD-to-index gap and the lookback window. The narratives are reproduced
exactly as the encoder received them and are not re-labeled here.

Three things visible in these examples are not matched by the feature vector.
All three are recorded as a limitation of the head-to-head comparison (main
text, Methods, *Predictors and patient representations*, and Supplement S8).
The `PHYSICAL HEALTH` section renders the within-patient mean vital signs that
were dropped from the feature vector at load time (main text, *Missing data and
sample partition*). The `SOCIODEMOGRAPHICS / ACCESS` line renders a recorded
sexual-orientation field that is absent from the feature inventory entirely,
and it renders an unrecorded value there as the literal token `nan` rather than
as `Missing`. The `COHORT & INDEX` line renders the index date, for which the
feature vector has no column. The `MEDICATION BURDEN` and
`TREATMENT EXPOSURE` sections also name individual ingredients where the
feature vector carries only their counts, while pre-index history length is a
feature-vector column that the narrative does not render.

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

# Supplement S5. Discrimination stratified by length of pre-index history

The main text tests the volume and recency confound by correlating the TRD
label with three proxies for how much data a patient has, and finds all three
associations weak and negative (Results, *Validity checks*; Figure 11). That
test asks whether the *outcome* tracks data volume. This section asks the
stronger question: whether *discrimination* tracks it, which is what one would
expect if the predictor were partly reading data volume rather than clinical
content.

The held-out test set was divided into quintiles of pre-index history length
and the neighbor-weighted predictor was scored within each quintile. The
nearest-retrieval, cosine-weighted arm is reported in Table S4. The pattern is
the same under uniform weighting.

***Table S4.** Neighbor-weighted discrimination by quintile of pre-index
history length (nearest retrieval, cosine weighting, embedded representation,
held-out test set). Quintile bounds are in days of pre-index history.*

| Pre-index history (days) | Patients | ROC AUC |
| --- | ---: | ---: |
| 731–1,110 | 1,706 | 0.580 |
| 1,110–1,554 | 1,704 | 0.598 |
| 1,554–2,066 | 1,701 | 0.582 |
| 2,066–2,733 | 1,704 | 0.610 |
| 2,733–5,288 | 1,701 | 0.578 |

Discrimination is flat across the range. The spread between the best and worst
quintile is 0.032 ROC AUC with no monotone trend, across a span of history
length that varies more than fourfold from the shortest quintile to the
longest. Had the predictor been exploiting record volume, discrimination should
have risen with it. It does not.

Two limits on this analysis. It covers the neighbor-weighted arm only, not the
trained classifiers that carry the main comparison, because the stratification
was computed over the neighbor predictions. And each quintile holds roughly
1,700 patients, so the per-quintile estimates are individually imprecise. The
claim rests on the absence of a trend rather than on any single value. A
parallel stratification by embedding-neighborhood density was computed but is
not reported, because the density distribution is concentrated enough that
three of its five bins were empty, leaving too little coverage to interpret.

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

# Supplement S8. Field-level crosswalk of the two representations

The head-to-head comparison in this paper is between two encodings of one
record, so it is only a comparison of encodings to the extent that both
encodings carry the same information. This section is the field-by-field
accounting, and it does two jobs. **It bounds the null**, because the two representations do not render an
identical inventory: 11 of the 28 rows below are asymmetric,
and in 10 of them the narrative receives information the feature vector
does not. **And it is the evidence for a scope condition the main text states in its own
voice** (Methods, *Predictors and patient representations*; Discussion,
*Principal findings*). Every row here traces to a field that predictor
selection chose before either representation existed. The patient data were
hand-picked in both arms, and neither was handed a raw record. A reader who takes the null to mean that the embedding found structure
without being told where to look can check that against this table, row by row, and the
answer is in the second column.

***Table S9.** Field-level crosswalk. **Asymmetric** marks a row where the two
representations do not receive the same information. Missing-value rules are as
implemented, not as intended.*

| Source field | Feature-vector encoding | Narrative rendering | Missing-value rule | Match |
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

**What the crosswalk shows.** The imbalance is not symmetric, and it is
larger than a count of rows suggests. Eleven rows are asymmetric, and in
ten of them the narrative receives information the feature vector does
not. Two are fields it renders and the feature vector has no column for,
the index date and sexual orientation. One is the row of vital signs
dropped at load. Four are sociodemographic fields where the feature
vector collapses raw Epic values into coarse categories and the
narrative prints the raw token. Three are medication blocks where the
feature vector carries a count and the narrative names the ingredients.
The eleventh
runs the other way: recorded history length, which the narrative did not
render.

Two rules are worth stating because they are easy to assume wrongly. Missingness
is *not* silently imputed on the categorical side of the feature vector: an
absent value becomes its own one-hot level, so the model can use the fact of a
missing record. And the vital signs were dropped rather than imputed, so the published feature
arm never saw them in any form. The reason is mechanical rather than
principled: a numeric column carrying nulls cannot pass through the pipeline's
scaler.

The main text states the imbalance as a bound on the comparison (Methods,
*Predictors and patient representations*). This table is what makes that bound
checkable, row by row.

# Supplement S9. Subgroup outcome prevalence

This section reports the *within-subgroup prevalence* of TRD, meaning the
number of TRD-positive patients divided by the total patients in that subgroup. Main-text Table 1 gives column percentages conditioned on TRD status, not row
percentages, so the prevalences below were computed from the raw subgroup
counts. For instance, the TRD prevalence for the 18-29 age band is 20.6%
(1,135 TRD-positive patients out of 5,513).

TRD prevalence varied modestly across subgroups. By sex it was 18.0% (female)
versus 16.2% (male). By age band it followed a clear gradient: the two youngest bands were highest and nearly tied, at 20.6% in 18-29-year-
olds (1,135/5,513) and 20.3% in 30-44-year-olds (1,836/9,025). Prevalence then
fell through 18.4% at 45-64 (2,445/13,268) to 13.8% in those aged 65 or older
(2,039/14,773). Several small social-determinant strata showed elevated but
imprecise prevalence (upbringing-related issue 33.0%, legal/criminal issue
26.1%, employment issue 24.0%, family/support-group issue 22.9%). Patients
with missing race/ethnicity (n = 297) did not show elevated prevalence (15.5%
against the 17.5% base rate). Strata this small are why the subgroup performance analysis in Supplement S7
declares some groups not estimable. One example is a psychosocial-circumstances
flag, with n = 12.
