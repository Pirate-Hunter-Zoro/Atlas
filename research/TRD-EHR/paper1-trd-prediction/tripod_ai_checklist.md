<!--
Completed TRIPOD+AI reporting checklist for the Paper 1 manuscript.

Kept as a SEPARATE submission document, not folded into supplement.md:
TRIPOD distributes it as a standalone form, JMIR uploads it as its own
file, and its 27 items would swamp the supplement and collide with the
supplement's S-numbering.

Item wording is verbatim from Collins GS, Moons KGM, Dhiman P, et al.
BMJ 2024;385:e078378 (checklist version 11-January-2024), transcribed
from formats/TripodAI.pdf.

The "Reported in" column gives manuscript SECTION names rather than page
numbers, because page numbers are not stable until the journal typesets.
Insert page numbers at proof if the journal requires them.

Every row points at the manuscript section that reports the item. The
ethics position for item 17 and the funder for item 18a were settled by
coauthor feedback 2026-08-17 and are now written into Declarations
(secondary analysis of de-identified data, not subject to IRB approval;
funded by the William K. Warren Foundation). Nothing on this checklist
remains owed by the authors.
-->

# Completed TRIPOD+AI checklist

**Manuscript.** Typed Feature Vectors, Generalized Pretrained Transformer
Embeddings of Deterministic Patient Narratives, and Nearest-Neighbor Retrieval
for Predicting a Treatment-Switch–Defined Electronic Health Record Proxy for
Treatment-Resistant Depression: Retrospective Cohort Study

**Study type.** Development of a multivariable prediction model with
internal validation by a single random split. There is no external
validation and no evaluation of a previously developed model, so items
marked *E* (evaluation only) are recorded as not applicable unless the
internal-validation split addresses them.

**Key.** D = development; E = evaluation; D;E = both. "Reported in"
refers to sections of the main manuscript unless prefixed *Supplement*.

## Title and abstract

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 1 | D;E | Identify the study as developing or evaluating the performance of a multivariable prediction model, the target population, and the outcome to be predicted | Title page. The title names the prediction task, the outcome (a treatment-switch–defined EHR proxy for treatment-resistant depression), the data source, and the study design; the target population (adults with unipolar MDD at their first antidepressant prescription following a documented depression diagnosis) is specified in the Abstract and in Methods, *Participants, index date, and temporal windows* |
| 2 | D;E | See TRIPOD+AI for Abstracts checklist | Abstract (structured: Background, Objective, Methods, Results, Conclusions) |

## Introduction

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 3a | D;E | Explain the healthcare context (including whether diagnostic or prognostic) and rationale for developing or evaluating the prediction model, including references to existing models | Introduction, paragraphs 1–2. Prognostic. Existing models cited [18-21] |
| 3b | D;E | Describe the target population and the intended purpose of the prediction model in the context of the care pathway, including its intended users | Introduction, paragraph 2 (flagging risk at the index antidepressant prescription so clinicians can monitor more closely and escalate sooner); Conclusions and Discussion, *Implications and future directions* (no clinical role is proposed: the discrimination is too modest for deployment in any form, and temporal and external validation, subgroup performance evidence, and a prospectively derived operating point are all prerequisites) |
| 3c | D;E | Describe any known health inequalities between sociodemographic groups | Methods, *Outcome*. Documented US disparities in depression treatment — Black and Mexican American adults meeting MDD criteria have lower odds of receiving any treatment and of receiving guideline-concordant treatment, at comparable symptom severity [2,17] — are stated as the reason a switching-derived label can encode unequal access as clinical signal (also Supplement M3). Revisited in Discussion, *Clinical interpretation*, which reads the outcome as a care-process phenotype and states that a model can reproduce inequities with protected attributes omitted. Addressed empirically in Supplement S11, Supplement S9 (subgroup discrimination and calibration), and the semantic-feature ablation |
| 4 | D;E | Specify the study objectives, including whether the study describes the development or validation of a prediction model (or both) | Introduction, final paragraph (three stated objectives). Development with internal validation |

## Methods

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 5a | D;E | Describe the sources of data separately for the development and evaluation datasets, the rationale for using these data, and representativeness of the data | Methods, *Study design and data source* (Supplement M1). Routine-care Epic EHR data from one service area of one community health system, delivered as six de-identified Caboodle/Clarity tables; development and evaluation samples are a single random partition of that one extract, whose version and cut dates are stated. Representativeness, including the single-centre constraint: Supplement M1 |
| 5b | D;E | Specify the dates of the collected participant data, including start and end of participant accrual; and, if applicable, end of follow-up | Methods, *Study design and data source* (index dates span 2016–2024); Methods, *Participants, index date, and temporal windows* and *Outcome* (minimum one year of post-index follow-up; one-year outcome window). Figure 1 shows the lookback window, time zero, and the ascertainment window on one axis |
| 6a | D;E | Specify key elements of the study setting (e.g., primary care, secondary care, general population) including the number and location of centres | Methods, *Study design and data source*, and Supplement M1, *Source data,
setting, and sampling frame*. Single centre: Saint Francis Health System, Tulsa, Oklahoma, United States — one community health system, covering inpatient, outpatient, observation, and emergency encounters within one administrative division of that system rather than a psychiatric specialty service line |
| 6b | D;E | Describe the eligibility criteria for study participants | Methods, *Participants, index date, and temporal windows* (six hierarchical filters); Results, *Participant flow*, Supplement M2, Table M1 |
| 6c | D;E | Give details of any treatments received, and how they were handled during model development or evaluation, if relevant | Methods, *Participants, index date, and temporal windows* (the index is the earliest antidepressant prescription on or after the first documented depression diagnosis; no adequacy criterion enters index selection, and prior adequate courses are handled as predictors rather than exclusions); Methods, *Predictors and patient representations* (per-agent adequate-trial counts, 42-day threshold; medication burden); Methods, *Model development*, **Semantic-feature ablation** (Supplement M11) (the treatment-exposure section is one of the six permuted concepts on the ablation slate; it reports pre-index exposure only and does not restate the outcome, and the reasoning is given there). Results, *Semantic-feature ablation* and Table 4 give its delta; Discussion, *Principal findings* interprets it |
| 7 | D;E | Describe any data pre-processing and quality checking, including whether this was similar across relevant sociodemographic groups | Methods, *Predictors and patient representations*; Methods, *Model development* (column transformer routed by each field's declared data type, fit within each cross-validation fold). Pre-processing is identical for all patients. Sociodemographic differences in data completeness are quantified in Methods, *Missing data and sample partition* (religion missingness by age band; outcome-associated vital-sign missingness) |
| 8a | D;E | Clearly define the outcome that is being predicted and the time horizon, including how and when assessed, the rationale for choosing this outcome, and whether the method of outcome assessment is consistent across sociodemographic groups | Methods, *Outcome*. Three or more antidepressant treatments within one year of the index date, the
index agent counting as the first (equivalently, two or more post-index
switches); augmentation and restarts excluded. This is the EHR-based operational definition of Forthman et al. [13], adopted unchanged. The label is computed algorithmically from prescription records and is therefore applied identically across sociodemographic groups. Rationale and its limits as a proxy: Methods, *Outcome*; Supplement M3,
*Outcome construction and inferential boundary*; and Discussion, *Limitations*,
which leads on the fact that the label counts switches and cannot see why one
happened |
| 8b | D;E | If outcome assessment requires subjective interpretation, describe the qualifications and demographic characteristics of the outcome assessors | Not applicable. The outcome is derived algorithmically from structured prescription records; no human assessor interprets it |
| 8c | D;E | Report any actions to blind assessment of the outcome to be predicted | Methods, *Outcome*. The label was computed in a separate upstream data-preparation stage, independently of and prior to the predictors used here; no predictor information enters the label |
| 9a | D | Describe the choice of initial predictors and any pre-selection of predictors before model building | Methods, *Predictors and patient representations*; Multimedia Appendix 1 (complete inventory). All pre-index fields were retained except the three vital signs -- each a mean over that patient's own pre-index encounters -- dropped for outcome-associated missingness (Methods, *Missing data and sample partition*). No outcome-driven pre-selection was performed |
| 9b | D;E | Clearly define all predictors, including how and when they were measured (and any actions to blind assessment of predictors for the outcome and other predictors) | Methods, *Predictors and patient representations*; Multimedia Appendix 1, Tables A1–A3. All predictors are derived solely from the pre-index window; no post-index information enters any predictor |
| 9c | D;E | If predictor measurement requires subjective interpretation, describe the qualifications and demographic characteristics of the predictor assessors | Not applicable. All predictors are derived deterministically from structured EHR fields; the narrative rendering is deterministic, with no generative model and no human judgement involved (Methods, *Predictors and patient representations*) |
| 10 | D;E | Explain how the study size was arrived at (separately for development and evaluation), and justify that the study size was sufficient to answer the research question. Include details of any sample size calculation | Methods, *Missing data and sample partition* (Supplement M7). No a-priori calculation; cohort size fixed by the eligibility filters. Events per variable reported per representation and per encoder, against the conventional threshold of 10 (Table 5) |
| 11 | D;E | Describe how missing data were handled. Provide reasons for omitting any data | Methods, *Missing data and sample partition* (Supplement M6). No imputation anywhere. Three vital-sign columns dropped because their recording is associated with the outcome, which rules out missingness completely at random without identifying the mechanism; categorical missingness retained as an explicit level. Supplement M6 records that a matched no-vitals / vitals-plus-indicators / within-fold-imputation comparison is not reported in the packet, and Supplement S10 that the narrative continued to render the dropped vital signs. Supplement S10 is the field-level crosswalk of every field's encoding, rendering and missing-value rule in both representations. A re-run in which the feature matrix receives the vitals with an explicit missingness indicator per block and within-fold median imputation leaves the primary comparison a null; it is not reported here and is available from the corresponding author. A second re-run removing religion from both representations — the column from FEATURE and the field from the rendered narrative, which removes the unrecorded level along with the recorded values, and therefore tests the differential missingness rather than only the field — leaves discrimination unchanged in both, with every paired interval including zero; it is likewise not reported here and is available from the corresponding author |
| 12a | D | Describe how the data were used in the analysis, including whether the data were partitioned, considering any sample size requirements | Methods, *Missing data and sample partition* (Supplement M8) (single stratified 80/20 split shared across all evaluation arms); Results, *Validity checks* |
| 12b | D | Depending on the type of model, describe how predictors were handled in the analyses (functional form, rescaling, transformation, or any standardisation) | Methods, *Model development*. Numeric block standardized; categorical block one-hot encoded with binary categories collapsed; boolean block cast to integer; the embedded representation is a single all-numeric block |
| 12c | D | Specify the type of model, rationale, all model-building steps, including any hyperparameter tuning, and method for internal validation | Methods, *Model development* (four classifiers per representation; five-fold cross-validated grid search optimizing ROC AUC; refit best estimator). Internal validation is the held-out 20% split (Methods, *Missing data and sample partition* (Supplement M8)) |
| 12d | D;E | Describe if and how any heterogeneity in estimates of model parameter values and model performance was handled and quantified across clusters | Not applicable. Data come from a single source with no modelled cluster structure; no clustered or multi-centre analysis was performed |
| 12e | D;E | Specify all measures and plots used (and their rationale) to evaluate model performance and, if relevant, to compare multiple models | Methods, *Statistical analysis and performance metrics* (discrimination, calibration, operating point, bootstrap uncertainty). Comparisons between models scored on the same patients — the ablation and the representation head-to-head (Figure 2B) in the main text, and the retrieval fusions in Supplement S6 — use a paired bootstrap on the difference in AUC, with the rationale given in the same subsection. Rationale for the complementary precision–recall view under class imbalance: Supplement S2. Absolute calibration error: Supplement S3 |
| 12f | E | Describe any model updating arising from the model evaluation, either overall or for particular sociodemographic groups or settings | Not applicable. No recalibration or model updating was performed after evaluation |
| 12g | E | For model evaluation, describe how the model predictions were calculated | Methods, *Model development* (classifier predicted probabilities) and the neighbor-weighted prediction formula given explicitly; Methods, *Reproducibility and software*; Declarations, *Data availability* (analysis code) |
| 13 | D;E | If class imbalance methods were used, state why and how this was done, and any subsequent methods to recalibrate the model or the model predictions | No class-imbalance method was used. The natural 17.5% positive rate was deliberately preserved in both partitions (Methods, *Missing data and sample partition* (Supplement M8)), and no resampling, class weighting, or post-hoc recalibration was applied. The consequences for interpretation are reported via precision–recall analysis (Supplement S2) and calibration (Table 3, Supplement S3) |
| 14 | D;E | Describe any approaches that were used to address model fairness and their rationale | No fairness assessment was performed, and this is stated as such. Methods, *Model development*, **Semantic-feature ablation** (Supplement M11) defines the analysis as one of direct-input reliance — race/ethnicity and social-determinant concepts are permuted to test whether the fitted models rely on those inputs — and names the three questions it cannot answer (indirect encoding through correlated clinical content, equity of the outcome label itself, and subgroup discrimination and calibration). Supplement S11 reports subgroup outcome rates and flags strata below 20 patients as not estimable. Subgroup *performance* is reported: Results, *Validity checks* and Supplement S9 give ROC AUC, calibration slope and calibration-in-the-large with uncertainty across six sociodemographic strata (sex, race, age band, marital status, smoking status, religion) and two clinical ones (MDD recurrence, severity), for all three prediction arms, with sparse strata and a level-by-level race breakdown declared not estimable. 240 contrasts, each carrying a bootstrap P value adjusted across the whole set by Benjamini-Hochberg; 58 exclude zero unadjusted and 24 survive correction. Sex shows no difference anywhere (max 0.012 ROC AUC). Race is directionally consistent, with all ten contrasts positive and five excluding zero unadjusted, but no race contrast survives adjustment (smallest adjusted P = .11), and non-White calibration is worse in the feature-vector arm (slope 0.79 vs 0.98). What survives is clinical: 21 of the 24 concern MDD recurrence and severity coding. Results, *Validity checks*, states that this cohort neither establishes nor excludes a race-associated gap and that the limit is power (302 minority events against 1,181); Discussion, *Principal findings* and *Clinical interpretation*, state that this is not a fairness result and why |
| 15 | D | Specify the output of the prediction model. Provide details and rationale for any classification and how the thresholds were identified | Methods, *Statistical analysis and performance metrics*. The model outputs a predicted probability of the treatment-switch–defined TRD proxy; a binary classification is additionally reported at the threshold maximizing Youden's J on the held-out test set, with the resulting operating characteristics in Figure 4 and Results, *Model discrimination*. Because that threshold is selected on the same patients the models are scored on, the reported sensitivity and specificity are optimistic and are presented as descriptive of the ROC curve rather than as candidate operating characteristics; no deployable threshold is proposed (Methods, *Statistical analysis and performance metrics*; Discussion, *Implications and future directions*) |
| 16 | D;E | Identify any differences between the development and evaluation data in healthcare setting, eligibility criteria, outcome, and predictors | Methods, *Missing data and sample partition* (Supplement M8). None: both partitions are a single random stratified split of one cohort, with identical setting, eligibility, outcome, and predictors. Empirical comparability is confirmed by per-predictor standardized mean differences (Results, *Validity checks*; maximum absolute SMD ≈ 0.04) |
| 17 | D;E | Name the institutional research board or ethics committee that approved the study and describe the participant-informed consent or the ethics committee waiver of informed consent | Declarations, *Ethics and data handling*. Not applicable: the study is a secondary analysis of de-identified data and is therefore not human-subjects research subject to institutional review board approval, so there is no reviewing body, protocol number, or consent waiver to report |

## Open science

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 18a | D;E | Give the source of funding and the role of the funders for the present study | Declarations, *Funding*. Funded by the William K. Warren Foundation, with no other funder; the funder had no role in study design, analysis, interpretation, writing, or the decision to submit |
| 18b | D;E | Declare any conflicts of interest and financial disclosures for all authors | Declarations, *Conflicts of interest*. None declared |
| 18c | D;E | Indicate where the study protocol can be accessed or state that a protocol was not prepared | Declarations, *Protocol*. A protocol was not prepared |
| 18d | D;E | Provide registration information for the study, including register name and registration number, or state that the study was not registered | Declarations, *Registration*. The study was not registered |
| 18e | D;E | Provide details of the availability of the study data | Declarations, *Data availability*. The EHR data are not publicly shareable |
| 18f | D;E | Provide details of the availability of the analytical code | Declarations, *Data availability*; Methods, *Reproducibility and software*. Analysis code is public at https://github.com/Pirate-Hunter-Zoro/TRD-EHR |

## Patient and public involvement

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 19 | D;E | Provide details of any patient and public involvement during the design, conduct, reporting, interpretation, or dissemination of the study or state no involvement | Declarations, *Patient and public involvement*. No involvement |

## Results

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 20a | D;E | Describe the flow of participants through the study, including the number of participants with and without the outcome and, if applicable, a summary of the follow-up time | Results, *Participant flow*, Supplement M2, Table M1 (501,718 → 42,579; 7,455 TRD-positive, 17.5%). Minimum follow-up of one year is imposed by eligibility (Methods, *Participants, index date, and temporal windows*) |
| 20b | D;E | Report the characteristics overall and, where applicable, for each data source or setting, including the key dates, key predictors, treatments received, sample size, number of outcome events, follow-up time, and amount of missing data. Report any differences across key demographic groups | Results, *Cohort characteristics*, Table 1 (overall and stratified by TRD status, with standardized mean differences); Supplement S11 (differences across sex, age band, and social-determinant strata); Methods, *Missing data and sample partition* (amount and pattern of missingness) |
| 20c | E | For model evaluation, show a comparison with the development data of the distribution of important predictors | Results, *Validity checks* and Supplement S8, Table S8, which shows the distributions themselves in the same form as Table 1. Per-predictor standardized mean differences between the training and test partitions: maximum absolute value 0.036 over 100 rows, none reaching 0.1 |
| 21 | D;E | Specify the number of participants and outcome events in each analysis | Methods, *Missing data and sample partition* (Supplement M7, M8); Results, *Validity checks*. Training 34,063 (5,964 events); test 8,516 (1,491 events). Per-subgroup counts and events are in Supplement S9, Table S9 |
| 22 | D | Provide details of the full prediction model to allow predictions in new individuals and to enable third-party evaluation and implementation, including any restrictions to access or re-use | **Partially reported.** The complete analysis code, including the model specification and fitting procedure, is public (Declarations, *Data availability*), and the neighbor-weighted predictor is given in closed form in Methods. Fitted model objects and coefficients are not distributed because they derive from non-shareable patient data; this restriction is stated in Declarations, *Data availability* |
| 23a | D;E | Report model performance estimates with confidence intervals, including for any key subgroups. Consider plots to aid presentation | Results, *Model discrimination* (Table 2, Figures 2–4), *Model calibration* (Table 3, Figure 5), *Prediction from retrieved neighbors* (Tables 6 and 7, Figure 10), *Robustness across encoders* (Table 5, Figure 9); Supplement S2 and S3. Subgroup-stratified performance is reported in Results, *Validity checks* and Supplement S9 (Tables S9-S11); Supplement S11 documents the small-cell ceiling on the sparsest strata |
| 23b | D;E | If examined, report results of any heterogeneity in model performance across clusters | Not applicable. Not examined; see item 12d |
| 24 | E | Report the results from any model updating, including the updated model and subsequent performance | Not applicable. No model updating was performed; see item 12f |

## Discussion

| Item | D/E | Checklist item | Reported in |
| :---: | :---: | --- | --- |
| 25 | D;E | Give an overall interpretation of the main results, including issues of fairness in the context of the objectives and previous studies | Discussion, *Principal findings* and *Clinical interpretation*. Fairness is interpreted via the semantic-feature ablation; the discrimination ceiling is situated against prior EHR- and trial-based work [18-21,30] |
| 26 | D;E | Discuss any limitations of the study and their effects on any biases, statistical uncertainty, and generalizability | Discussion, *Limitations*, which states ten in order of how much they bound the conclusions. The first is the binding one: the outcome counts antidepressant switches and cannot see why a switch happened, so intolerance, cost, non-adherence and prescriber preference are counted identically with non-response, and the label is not validated against chart review or symptom measures [2,4,5,7-9,17]. The others cover internal-only validation and the reported discrimination as an
upper bound [29]; that no raw record was ever embedded, both representations
encoding the same curated field inventory chosen before either existed, so the
engineering was relocated rather than removed and nothing here bounds how an
untailored encoding would perform; the unequal field inventories that bound the
parity claim (Supplement S10); the single form in which retrieval was tested; absence of an advantage not being equivalence; dropped rather than modelled missing data (Supplement M6); the absence of any fairness evidence [2,17]; the single-centre cohort; one-concept-at-a-time ablation; and an optimistic operating point with cohort-specific calibration. The section is also carried by Methods, *Study design and data source*, *Outcome*, *Predictors and patient representations*, *Missing data and sample partition* and *Statistical analysis and performance metrics*, and by Supplement M1, M3, M6, M7 and S10 |
| 27a | D | Describe how poor quality or unavailable input data should be assessed and handled when implementing the prediction model | **Not reported.** Missing-data handling is specified for model development (Methods, *Missing data and sample partition*) but no implementation-time guidance is given, consistent with the study not proposing the model for deployment (Conclusions) |
| 27b | D | Specify whether users will be required to interact in the handling of the input data or use of the model, and what level of expertise is required of users | Not applicable. The study concludes that the absolute discrimination is too modest for standalone clinical deployment (Conclusions), and no user-facing implementation is proposed |
| 27c | D;E | Discuss any next steps for future research, with a specific view
to applicability and generalizability of the model | Discussion, *Implications
and future directions* — the experiment this study could not run, an untailored
encoding of a whole record against the curated narrative on the same patients,
together with the input-length constraint that blocks it and the design
decisions each way round it reintroduces; — causal-forest / heterogeneous-treatment-effect modelling of next-step strategy choice; joint perturbation of concepts drawn from the same pre-index window, which single-concept ablation cannot separate; and fusion across differing representations or encoder geometries, which the single-geometry nearest–farthest null does not bear on (that fusion is tested and closed in Supplement S6). Discussion, *Implications and future directions* (external and temporal validation; validation of the outcome label against chart-reviewed non-response) |

---

*From: Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement:
updated guidance for reporting clinical prediction models that use
regression or machine learning methods. BMJ 2024;385:e078378.
doi:10.1136/bmj-2023-078378. Checklist version 11-January-2024.*
