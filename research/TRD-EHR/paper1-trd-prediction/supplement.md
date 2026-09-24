<!--
Multimedia Appendix 1 for the TRD prediction manuscript.
Source of truth is this Markdown; the .docx and .pdf are built, not edited.

THE TEXT IS THE SENIOR AUTHOR'S (review/feedback/2026-09-21/supplement_revised.docx),
converted, with the retrieval direction applied. Keep his wording elsewhere.

WHAT IS NOT IN IT, and must not come back without a reason tied to one of the
paper's two points: the LLM clinical-similarity judge (complete in
reserve/llm_similarity_judge.md), uniform and combined weighting, subsampled
retrieval, and the nearest-farthest fusion, which rested on uniform weighting.

RETRIEVAL is two arms, plain cosine (k = 50, the primary setting) and
importance-weighted cosine (M10), with random and farthest as controls. The
subgroup tables' retrieval row is importance-weighted at k = 295, drawn by
scripts/pipeline/review/subgroups/run_subgroups.py (--replot redraws the
tables and forest plot from the saved CSVs).
-->

# Contents

M1--M13 Detailed methods and predictor inventory\
S1 Embedding dimensionality\
S2--S3 Precision--recall performance and calibration\
S4--S5 Similarity geometry and example narratives\
S6 Neighbor prediction\
S7--S8 Record length and sample comparability\
S9--S11 Subgroup performance, field crosswalk, and cohort characteristics\
S12 Additional model diagnostics and encoder estimates

This appendix provides detailed methods, supporting analyses, and results for the comparison of structured feature vectors and narrative embeddings. Sections M1--M13 describe the methods and predictor inventory; sections S1--S12 report supporting analyses and extended results. TRD denotes the treatment-switching proxy defined in section M3, not symptom-confirmed treatment-resistant depression. FEATURE and EMBEDDED identify the structured and narrative pipelines, respectively.

# M1 Source Data and Sampling

The study used a single de-identified extract from the Epic EHR of Saint Francis Health System. Seven files were delivered: person, encounter, diagnosis, medication, procedure, and laboratory/flowsheet tables together with a medication-to-RxNorm mapping table. The clinical tables originated from the Caboodle enterprise data warehouse; the RxNorm mapping originated from the Clarity reporting database. Body mass index and systolic and diastolic blood pressure were obtained from the laboratory/flowsheet table. Each table was delivered as a flat file after patient and encounter keys had been replaced by one-way MD5 hashes, and was transferred by secure file transfer protocol. No names, medical record numbers, direct identifiers, or dates of birth were included.

The delivering data team restricted the person table to one administrative division of the health system and to patients who were current, valid, non-test, non-historical, not recorded as deceased, and aged 18-110 years at extraction. Eligible source encounters were completed on or before the extraction date, had at least one associated diagnosis, and had an inpatient, outpatient, observation, or emergency patient class.

Investigators prespecified the diagnosis code lists. Depression comprised ICD-9 codes 296.2, 296.3, 300.4, and 311 or ICD-10 codes F32.\*, F33.\*, and F34.1. Bipolar disorder comprised ICD-9 codes 296.0 and 296.4-296.8 or ICD-10 codes F30.\* and F31.\*. Schizophrenia-spectrum disorders comprised ICD-9 codes 295.\* and 298.\* or ICD-10 codes F20.\*, F23.\*, F25.\*, F28.\*, and F29.\*.

The extract was assembled as a case-enriched sample. All patients with a depression diagnosis on the problem list were retained, and a random sample of patients without that flag was added at an approximate 4:1 unflagged-to-flagged ratio; the remaining tables were then linked to the person table. The delivered extract included 501,718 patients: 100,420 (20.0%) with and 401,298 (80.0%) without a problem-list depression flag.

Sampling used problem-list flags, whereas eligibility used encounter diagnoses. Of 42,579 eligible patients, 12,530 (29.4%) lacked the problem-list flag and entered through the randomly sampled group. The analytic cohort therefore does not enumerate all patients with depression in the health system. Its outcome and subgroup frequencies are sample descriptions, not population prevalence estimates. Both representations were evaluated in the same sampled patients.

The setting is a single community health system in Tulsa, Oklahoma, serving inpatient, outpatient, observation, and emergency care. Patients enter the cohort through routine antidepressant prescribing across those settings rather than through psychiatric specialty referral, and the index prescription may be written in any of them.

Analyses used data version DV260629v1 and patient version PV260710v1. Source files were extracted June 29, 2026; analysis-ready tables were created July 10, 2026. No later refresh entered the study.

# M2 Eligibility and Temporal Design

Eligibility was applied hierarchically from the full delivered extract. Patients were required to have: (1) a qualifying MDD diagnosis; (2) no bipolar-disorder diagnosis and no schizophrenia-spectrum diagnosis, to isolate unipolar depression; (3) an eligible antidepressant index prescription; (4) an MDD diagnosis recorded on or before the index date; (5) at least 730 days of pre-index history; and (6) at least 365 days of post-index follow-up. Patients failing the chronological or observation prerequisites were assigned explicit rejection reasons for attrition accounting.

Table M1. Participant flow through the hierarchical eligibility filters. Each row applies one additional filter to the survivors of the row above. The first row is the delivered extract, a case-enriched sample by design (Supplement M1).

  **Stage**                                     **Remaining**   **Rejected at stage**
  --------------------------------------------- --------------- -----------------------
  Delivered extract (4:1 case-enriched)         501,718         ---
  MDD-diagnosed                                 144,110         357,608
  Not bipolar AND not schizophrenia-spectrum    124,188         19,922
  Has antidepressant index prescription         107,636         16,552
  Has MDD before index                          103,458         4,178
  ≥2 years pre-index history                    54,215          49,243
  ≥1 year post-index follow-up (final cohort)   42,579          11,636

Upstream data preparation assembled, for each patient, all antidepressant medication orders beginning on or after the date of the first documented depression diagnosis. The earliest start date in that set defined the index date, one per patient. Among candidate index orders, 57.9% begin on the same date as the first recorded depression diagnosis.

Index selection did not depend on subsequent dose, exposure duration, response, or switching. Post-index information was used to establish 365 days of follow-up and ascertain the outcome. Clinical content was restricted to the 730-day window ending on the index date. Total recorded pre-index history length (median 1,792 days) was retained separately as a duration variable, although clinical content outside the fixed window was not used.

Prior antidepressant exposure did not exclude patients: 24.0% had some recorded pre-index exposure and 14.7% had a course meeting the 42-day duration threshold. The index was the first recorded prescription on or after a documented depression diagnosis, not necessarily the first lifetime exposure or first adequate trial.

# M3 Outcome Definition

The binary outcome was generated in the upstream R data-preparation pipeline independently of the predictors and supplied to the modeling workflow as a fixed label. TRD was assigned when a patient with MDD received at least three distinct antidepressant treatments within 365 days of the index date, the index agent counting as the first. Patients with fewer than three treatments were classified TRD-negative.

A treatment is a distinct antidepressant agent rather than an order or prescribing event. Addition of a second agent while the current antidepressant continues is augmentation and does not advance the outcome count; restarting a previously used agent also does not advance it. Augmentation is available as a pre-index predictor where its definition is met.

The follow-up requirement provided a 365-day observation window for outcome ascertainment. It did not ensure complete capture of care, including treatment outside the health system; a negative label therefore indicates that the qualifying sequence was not observed.

The label does not establish inadequate response to at least 2 trials of adequate dose and duration \[1,2\]. Standardized symptom response was unavailable, and adequacy was not verified for counted post-index treatments. Switching could reflect nonresponse, intolerance, cost, formulary restrictions, preference, or clinical practice. It also depends on continuity and access, which differ across demographic groups \[3,4\]. Chart adjudication and symptom trajectories are needed to validate the label, together with sensitivity analyses requiring documented adequate courses.

# M4 Predictors and Structured Representation

Predictor domains were selected clinically and from prior literature before model fitting or inspection of outcome associations \[5\]. No univariate screening or automated selection determined the source-field inventory; subsequent model regularization operated on the encoded predictors.

Domains included depression severity and recurrence, psychiatric and substance-use comorbidity, medical comorbidity, prior treatment, medication burden, utilization, and sociodemographic characteristics \[5-8\]. Severity was represented by diagnosis codes because standardized symptom scales were not available.

Prescribing-constraint flags described potential limits on treatment options. Sociodemographic and social-determinant fields were retained to evaluate their direct contribution by permutation. Body mass index and blood pressure were subsequently removed from FEATURE because of missingness (section M6).

FEATURE assigns explicit types to counts and durations, binary indicators, and nominal categories. Prior antidepressant trial counts required at least 42 continuous days of exposure; adequate dose was not established by this rule. Tables M2--M4 provide the 59 retained source fields and their expansion to 92 model columns.

After removal of 3 vital-sign fields, the inventory comprised 15 quantitative, 36 binary, and 8 categorical source fields. Categorical expansion produced 41 columns, for a total of 92. Display labels are those used in the original analyses.

Table M2. Quantitative predictors.

  **Predictor**
  -------------------------------------
  MDD history before index (days)
  History length (days)
  Encounter count
  ED visits (count)
  Inpatient days before index
  Age (years)
  Medications active at index
  Anti-inflammatories active at index
  Sleep meds active at index
  Anxiolytic days before index
  Bupropion trials (6+ wk)
  Mirtazapine trials (6+ wk)
  SNRI trials (6+ wk)
  SSRI trials (6+ wk)
  Vortioxetine trials (6+ wk)

Table M3. Binary predictors by domain.

  **Block**                             **Predictors**
  ------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Clinical flags (3)                    MDD in history; Suicidality; Augmentation therapy
  Psychiatric comorbidities (8)         Adjustment disorder; Anxiety disorder; Dysthymia (chronic depression); Insomnia; OCD; PTSD; Social anxiety disorder; Substance use disorder (any)
  Medical comorbidities (4)             Chronic pain; Diabetes; High cholesterol; Thyroid disorder
  Prescribing-constraint / safety (2)   Seizure disorder; Uncontrolled hypertension
  Substance use disorders (10)          Alcohol; Cannabis; Cocaine; Hallucinogen; Inhalant; Nicotine; Opioid; Other stimulant; Other substance; Sedative/hypnotic
  Social determinants of health (9)     Education or literacy issue; Employment issue; Housing or financial issue; Legal or criminal issue; Occupational hazard exposure; Family/support group issue; Psychosocial circumstances; Social environment issue; Upbringing issue

Table M4. Categorical fields and encoded levels.

  **Field**            **One-hot columns**   **Levels**
  -------------------- --------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------
  Sex                  1                     Male (Female = reference, dropped)
  Preferred language   6                     Asian/Pacific Islander; English; Other; Other Indo-European; Spanish; Missing
  Marital status       6                     Divorced; Never married; Married; Separated; Widowed; Missing
  Religion             6                     Catholic; Non-Christian; Orthodox; Other/Unknown; Protestant; Missing
  Smoking status       4                     Current; Former; Never; Missing
  Race/ethnicity       8                     American Indian/Alaska Native; Asian; Black/African American; Hispanic/Latino; Multi-race; Native Hawaiian/Pacific Islander; White/Caucasian; Missing
  MDD recurrence       4                     Unspecified; Single episode; Recurrent; Dysthymia (chronic depression)
  MDD severity         6                     Unspecified; Mild; Moderate; Severe; Psychotic; Remission

# M5 Deterministic Narratives and Embeddings

Fixed rules rendered the pre-index structured record as a Markdown narrative. No generative model wrote the summaries, preserving traceability and avoiding unsupported generated content \[9\]. Example inputs appear in section S5.

Each narrative was mapped to a fixed-length vector with a pretrained sentence-transformer encoder \[10\]. The four independently evaluated encoders were bge-small-en-v1.5 \[11\], bge-en-icl \[12\], Qwen3-Embedding-4B, and Qwen3-Embedding-8B \[13\]. This serialization-and-encoding strategy follows evidence that general-purpose language-model embeddings of serialized EHR records can perform competitively with purpose-built EHR foundation models across prediction tasks \[14\].

The pipelines share a source record and temporal cutoff but differ in field content. Section S10 documents these differences. Accordingly, the primary comparison evaluates complete pipelines rather than the isolated effect of numeric versus language encoding.

# M6 Missing Data

No statistical imputation was performed. Mean body mass index and mean systolic and diastolic blood pressure were present in the intermediate feature file but removed from the FEATURE matrix at load time. Each value is the within-patient mean across that patient's own pre-index encounters, not a mean across patients. Mean body mass index was missing for 22.1% of patients, and at least one vital sign was absent for 21.0%. Body mass index was missing for 28.8% of TRD-positive and 20.6% of TRD-negative patients, an approximately 8-percentage-point difference.

Outcome-associated missingness argues against missing completely at random but does not establish missing not at random. The primary FEATURE analysis excluded the vital signs without imputation or continuous missingness indicators. A sensitivity analysis retaining them with missingness indicators and within-fold median imputation was reported to leave the best-model comparison nonsignificant. Quantitative results are not included here and are available from the corresponding author.

FEATURE encoded missing categorical values as separate levels. Narratives generally used "Missing," with field-specific exceptions documented in section S10. Marital and smoking status were less than 0.5% missing. Religion was missing in 29.4% overall, ranging from 43.8% at ages 18--29 to 17.5% at age 65 or older. A sensitivity analysis removing religion from both pipelines was reported to yield paired discrimination CIs including zero; quantitative results are available from the corresponding author.

# M7 Sample Size and Model Dimensionality

Cohort size was determined by eligibility rather than a formal sample-size calculation. Events per variable (EPV) was calculated as 5,964 outcome-positive training patients divided by the number of encoded input columns.

FEATURE contains 92 encoded columns, giving EPV = 5,964/92 ≈ 64.8. EMBEDDED dimensionality is encoder-specific: bge-small-en-v1.5 has 384 dimensions (EPV ≈ 15.5), Qwen3-Embedding-4B has 2,560 (EPV ≈ 2.3), and bge-en-icl and Qwen3-Embedding-8B each have 4,096 (EPV ≈ 1.5). Only the smallest encoder exceeds the conventional threshold of 10.

EPV is a descriptive ratio, not a sufficient sample-size criterion for high-dimensional regularized models. The larger encoders nevertheless have many inputs relative to outcome events, reinforcing the need for independent validation. Sparsity in a fitted model does not establish stability of the selected dimensions.

# M8 Training and Test Split

All models used the same stratified split: 34,063 training patients (5,964 positive) and 8,516 test patients (1,491 positive). Across 100 predictor rows, the largest absolute standardized mean difference was 0.036. The largest imbalance concerned a rare social-determinant flag present in 22 training patients and no test patient. Outcome frequencies matched by design. Selected distributions are in section S8.

Scaling parameters and category levels were estimated within each cross-validation training fold. The selected pipeline was then refitted on all training patients and applied to the test set; exploratory analyses subsequently reused these held-out predictions.

The retrieval index contained training patients only. Test patients served as query anchors, with no self-retrieval or test-patient labels used to predict another test patient. Internal balance does not establish transportability because both partitions share the same sampling frame.

# M9 Model Development

Four classifiers were fitted to each representation: logistic regression, random forest, gradient boosting, and XGBoost. For FEATURE, the column transformer standardized the numeric block, one-hot encoded categorical variables with binary categories collapsed and unknown inference-time levels ignored, and cast boolean indicators to integer without further transformation. EMBEDDED entered through the numeric branch only.

Each classifier and its preprocessing steps formed a single scikit-learn pipeline. Five-fold grid search optimized training-set ROC AUC, after which the selected pipeline was refitted on all training patients. Scaling and category encoding were fitted within each fold. Classifier-specific tuning grids were identical across representations.

# M10 Neighbor Prediction

For EMBEDDED only, the predicted TRD probability for query patient q was the similarity-weighted mean of binary TRD labels among its k retrieved training neighbors:

$$\widehat{P}(TRD \mid q) = \frac{\sum_{i = 1}^{k}w_{i}\, y_{i}}{\sum_{i = 1}^{k}w_{i}}, \qquad w_{i} = \max\{s_{i}, 0\}^{\alpha},$$

where $y_{i} \in \{ 0,1\}$ is neighbor $i$'s TRD label, $s_{i}$ its similarity to q, and $\alpha$ a sharpening exponent. Neighborhood concentration was summarized by the effective sample size,

$$ESS = \frac{\left( \sum_{i = 1}^{k}w_{i} \right)^{2}}{\sum_{i = 1}^{k}w_{i}^{2}},$$

which equals $k$ when all weights are equal and falls as weight concentrates on fewer neighbors.

Two similarity metrics were compared. Plain cosine similarity used the raw embeddings. Importance-weighted cosine similarity standardized each dimension with the embedded logistic regression's own scaler, $z_{d} = (x_{d} - \mu_{d})/\sigma_{d}$, and weighted dimension $d$ by its share of that model's absolute coefficients:

$$\mathrm{sim}_{w}(x,y) = \frac{\sum_{d}w_{d}\, z_{d}(x)\, z_{d}(y)}{\sqrt{\sum_{d}w_{d}\, z_{d}(x)^{2}}\,\sqrt{\sum_{d}w_{d}\, z_{d}(y)^{2}}}, \qquad w_{d} = \frac{|\beta_{d}|}{\sum_{e}|\beta_{e}|}.$$

The coefficients came from the model fitted on training patients, so no test outcome entered a risk score. The metric is supervised, whereas plain cosine similarity is not. Of 4,096 dimensions, 385 had non-zero coefficients, and the top 41 (1%) carried 31% of the absolute coefficient mass.

The primary analysis used plain cosine similarity with k = 50 and $\alpha$ = 5. A sweep evaluated every k from 1 to all 34,063 training patients for both metrics, under $\alpha$ = 1, 2, and 5. Nearest retrieval selected the k most similar training patients. Farthest retrieval, which selected the least similar, and random retrieval served as negative controls at k = 50. These analyses were restricted to embeddings; no mixed-data similarity metric was specified for FEATURE.

# M11 Concept Permutation

Each concept was reassigned through a one-to-one donor permutation across patients. Section permutations exchanged complete sections; field permutations changed only the specified field. Narratives were then re-embedded and scored by frozen classifiers. The analysis estimates reliance on the perturbed input, conditional on the remaining fields. It does not show whether retraining could recover performance from correlated information.

Psychiatric history (section). Present/absent indicators for anxiety disorder, social anxiety disorder, obsessive-compulsive disorder, posttraumatic stress disorder, adjustment disorder, dysthymia, insomnia, and any substance-use disorder; any suicidal-ideation or suicide-attempt code in the two-year lookback; and named substance categories including alcohol, cannabis, cocaine, nicotine, opioid, and sedative/hypnotic disorders. It carries documented diagnoses rather than treatments.

Medication burden (section). The count and names of distinct active drug ingredients at the index date across all therapeutic classes, and the count and names of distinct non-steroidal anti-inflammatory ingredients prescribed for at least seven days. It stands in for overall medical complexity and pill burden, not psychiatric treatment specifically.

Treatment exposure (section). Pre-index counts of adequate trials for selective serotonin reuptake inhibitors, serotonin-norepinephrine reuptake inhibitors, bupropion, mirtazapine, and vortioxetine, each requiring at least 42 continuous days on the agent; total benzodiazepine days covered during the lookback; hypnotic agents prescribed for at least seven days; and augmentation, defined as overlap of an antidepressant with lithium, an antipsychotic, or buspirone for at least 14 days. It is distinct from all-class medication burden and from the post-index agents used to construct the outcome.

Treatment contraindications (section). Seizure disorder, which weighs against bupropion, and uncontrolled hypertension, which weighs against serotonin-norepinephrine reuptake inhibitors. The concept is constraint on escalation options rather than general medical comorbidity, which the narrative reports in a separate section that was not permuted.

Race/ethnicity (field). The recorded race/ethnicity category, including an explicit unrecorded level, permuted within an otherwise unchanged sociodemographic section. Sex, age, preferred language, marital status, religion, and smoking status were not altered in this ablation.

Social determinants of health (field). ICD-10 Z-code categories recorded during the lookback: education/literacy, employment, occupational exposure, housing/economic circumstances, social environment, upbringing, primary support group/family circumstances, psychosocial circumstances, and legal/criminal circumstances. The narrative renders "None Recorded" when no qualifying code is present. Only this field was permuted.

Permutation does not establish equitable labeling or performance. Correlated diagnosis, medication, and utilization fields may retain demographic information, and sparse recording may limit the contribution of an explicitly permuted field.

# M12 Evaluation Coverage

Standard classifiers, encoder comparisons, and concept permutations used the full cohort and common test split. The primary Qwen3-Embedding-8B encoder received both similarity metrics, the negative controls, and the neighborhood-size sweep. Other encoders were evaluated with nearest and random retrieval under plain cosine similarity at k = 50, so the importance-weighted metric and the sweep describe the primary encoder only.

# M13 Performance Metrics and Uncertainty

Discrimination was summarized by ROC AUC and AUPRC. The original overall calibration summaries fit a line to binned observed and predicted probabilities. These binned slopes and intercepts are retained in section S3 and are not conventional individual-level logistic calibration parameters. Section S9 separately reports logistic calibration slopes and mean predicted minus observed risk. All estimates describe the enriched sample.

Sensitivity, specificity, and likelihood ratios were calculated at the test-set threshold maximizing Youden J. Selecting and evaluating a threshold in the same patients introduces optimism. These operating points are descriptive; a clinical threshold would require selection in development data and evaluation in an independent cohort.

Bootstrap resampling drew test patients with replacement. Paired contrasts applied identical resampled patient indices to both prediction vectors and recalculated their ROC AUC difference. The 2.5th and 97.5th percentiles formed the 95% CI.

Classifier-matched comparisons varied the representation while holding the learner fixed. The best-model comparison selected the leading classifier for each representation from test performance and is therefore post hoc. A common resampling matrix was used across contrasts.

No equivalence or noninferiority margin was prespecified. A paired confidence interval containing zero indicates that superiority was not established at the precision achieved; it does not establish equivalence.

# S1 Embedding Dimensionality

Latent embedding coordinates do not have individual clinical interpretations. We therefore examined fitted sparsity, cumulative correlations, and performance after principal component reduction for Qwen3-Embedding-8B. These exploratory analyses describe the fitted representation rather than identify distinct clinical mechanisms.

## S1 1 Sparsity and cumulative built in importance

The selected logistic regression used elastic-net regularization (l1_ratio=0.25; C=0.01). It assigned nonzero coefficients to 385 of 4,096 dimensions; approximately 80% of total absolute coefficient magnitude fell in 179 dimensions and 90% in 236 (Figure S1). These are model-specific measures of coefficient concentration, not estimates of intrinsic dimensionality or independent predictive information.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_cumulative_EMBEDDED.png){width=5.8in}

Figure S1. Cumulative built-in importance across embedding dimensions, ranked within each classifier. For logistic regression, importance is absolute coefficient magnitude; tree models use native feature importance. K80 and K90 identify the numbers of coordinates accounting for 80% and 90% of that model-specific total.

## S1 2 Cumulative univariate correlation

We ranked coordinates by absolute Spearman correlation with the outcome and, separately, with each classifier's predicted risk (Figure S2). The cumulative curves were broadly distributed. A sparse coefficient vector and diffuse marginal correlations can coexist because embedding coordinates are correlated; neither identifies unique clinical factors.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_correlation_cumulative_EMBEDDED.png){width=5.8in}

Figure S2. Cumulative absolute univariate (Spearman) correlation. One model-agnostic baseline curve ranks dimensions by \|ρ(dim, outcome)\|; the four per-classifier curves rank by \|ρ(dim, predicted risk)\|. Cumulative fraction of total \|ρ\| mass versus rank, with K₈₀ / K₉₀ knees in the legend.

## S1 3 PCA K discrimination sweep

Each classifier was retrained on the top K principal components, with K in {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024}. Held-out ROC AUC generally improved as components were added, with model-specific plateaus and some deterioration at larger K (Figure S3). These curves do not identify a unique effective dimension, and choosing K from them would require further independent evaluation.

A Logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_logistic_regression_EMBEDDED.png){width=5.8in}

B Random forest

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_random_forest_EMBEDDED.png){width=5.8in}

Figure S3. Continued on the next page.

C Gradient boosting

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_gradient_boosting_EMBEDDED.png){width=5.8in}

D XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_pca_sweep_xgboost_EMBEDDED.png){width=5.8in}

Figure S3. ROC AUC by retained principal components for logistic regression (A), random forest (B), gradient boosting (C), and XGBoost (D). The number of components is shown on a logarithmic scale. These are exploratory comparisons on the shared test set.

# S2 Precision Recall Performance

AUPRC complements ROC AUC by describing precision across recall levels. Its no-skill reference is the cohort's positive fraction, 0.175. Because it depends on outcome frequency, AUPRC should not be compared across populations without accounting for prevalence.

AUPRC remained modest across models (Tables S1--S2; Figure S4). The leading embedded and feature models achieved 0.302 and 0.298, respectively. These values are also summarized in Table 2.

Table S1. AUPRC of the four classifiers on each representation (held-out test set). No-skill baseline = 0.175 (the positive rate).

  **Representation**   **Classifier**        **AUPRC**
  -------------------- --------------------- -----------
  EMBEDDED             Logistic regression   0.302
  EMBEDDED             Random forest         0.270
  EMBEDDED             Gradient boosting     0.276
  EMBEDDED             XGBoost               0.278
  FEATURE              Logistic regression   0.278
  FEATURE              Random forest         0.293
  FEATURE              Gradient boosting     0.288
  FEATURE              XGBoost               0.298

Table S2. Embedded logistic-regression AUPRC by encoder (held-out test set). No-skill baseline = 0.175.

  **Encoder**          **AUPRC**
  -------------------- -----------
  bge-small-en-v1.5    0.281
  bge-en-icl           0.297
  Qwen3-Embedding-4B   0.297
  Qwen3-Embedding-8B   0.302

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/pr_curves/pr_curve_xgboost_FEATURE.png){width=5.8in}

Figure S4. Precision--recall curves for the best classifier on each representation (held-out test set; primary Qwen3-Embedding-8B encoder). (A) Embedded logistic regression; (B) feature-vector XGBoost. The no-skill AUPRC reference is 0.175, the positive rate.

# S3 Calibration

Table S3 reports Brier score and weighted calibration error (WCE), for which lower values are better. Scores ranged from 0.137 to 0.140 and 0.004 to 0.018, respectively. The binned calibration slopes and intercepts originally reported in the manuscript are retained below, separately from the individual-level logistic slopes in section S9. Binned slopes should not be interpreted as conventional logistic calibration slopes.

Table S3. Brier score and weighted calibration error for all 8 primary representation--classifier combinations. Both metrics describe the cohort's observed outcome frequency.

  **Representation**   **Classifier**        **Brier**   **WCE**
  -------------------- --------------------- ----------- ---------
  EMBEDDED             Logistic regression   0.137       0.010
  EMBEDDED             Random forest         0.140       0.006
  EMBEDDED             Gradient boosting     0.139       0.004
  EMBEDDED             XGBoost               0.139       0.013
  FEATURE              Logistic regression   0.139       0.005
  FEATURE              Random forest         0.139       0.018
  FEATURE              Gradient boosting     0.138       0.010
  FEATURE              XGBoost               0.138       0.012

Table S4. Slopes and intercepts fitted to the binned calibration curves. These descriptive values are retained from the original overall calibration analysis and are not individual-level logistic calibration parameters. See section S9 for the latter.

  **Representation**   **Classifier**        **Binned slope**   **Binned intercept**
  -------------------- --------------------- ------------------ ----------------------
  EMBEDDED             Logistic regression   1.27               −0.07
  EMBEDDED             Random forest         1.15               −0.02
  EMBEDDED             Gradient boosting     1.01               0.01
  EMBEDDED             XGBoost               0.75               0.07
  FEATURE              Logistic regression   0.78               0.06
  FEATURE              Random forest         1.84               −0.15
  FEATURE              Gradient boosting     0.87               0.04
  FEATURE              XGBoost               1.02               0.02

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png){width=5.8in}

Figure S5. Calibration curves for embedded logistic regression (A) and feature-vector XGBoost (B). The diagonal indicates agreement between predicted and observed outcome frequency; points above it indicate underprediction in that bin, and points below indicate overprediction. The sample is enriched for depression.

# S4 Encoder Similarity Geometry

Figure S6 compares cosine similarities for random patient pairs and nearest-neighbor pairs. The 3 larger encoders produced broadly unimodal random-pair distributions. bge-small-en-v1.5 showed multiple modes at high similarity values, prompting a descriptive analysis of the corresponding narrative wording.

A bge-small-en-v1.5

![](../results/bge-small-en-v1.5/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

B bge-en-icl

![](../results/bge-en-icl/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

Figure S6. Continued on the next page.

C Qwen3-Embedding-4B

![](../results/Qwen-Qwen3-Embedding-4B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

D Qwen3-Embedding-8B

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/cosine_score_random_vs_neighbor.png){width=5.8in}

Figure S6. Cosine similarity for random pairs (red) and nearest-neighbor pairs (green) for bge-small-en-v1.5 (A), bge-en-icl (B), Qwen3-Embedding-4B (C), and Qwen3-Embedding-8B (D). Axis ranges differ across encoders. The smallest encoder shows a multimodal random-pair distribution.

K-means clustering of L2-normalized bge-small embeddings (k=2) separated 42,579 patients into groups of 14,438 and 28,141. The partition closely tracked whether the narrative contained the token "episode" (Table S5).

The token occurs in "Single Episode" but not "Recurrent" or "Dysthymia." Thus, the partition should not be described simply as recurrent versus nonrecurrent depression.

Cluster B (n=28,141) largely comprised narratives containing "episode"; the full cohort contained 28,206 patients coded single episode.

Cluster A (n=14,438) largely lacked "episode" and included both recurrent and other depression codes. The full cohort contained 11,213 recurrent-coded patients.

Table S5. Fraction of narratives containing selected tokens within each top-level k-means cluster. Cluster A has 14,438 patients and cluster B has 28,141. "Single" may also denote marital status.

  **Token**     **P(present \| cluster A)**   **P(present \| cluster B)**   **\|Δ\|**
  ------------- ----------------------------- ----------------------------- -----------
  episode       0.00                          1.00                          1.00
  recurrent     0.78                          0.00                          0.78
  single        0.30                          1.00                          0.70
  unspecified   0.39                          0.83                          0.45
  moderate      0.32                          0.09                          0.23

Figure S7 stratifies pairwise similarities by token agreement. Blue denotes pairs agreeing on token presence, red denotes disagreement, and gray denotes all pairs.

Across the cohort, pairs agreeing on "episode" had higher similarities than pairs differing on that token (Figure S7A). This association links the observed modes to diagnostic wording but does not isolate a causal token effect from correlated clinical information.

Within cluster A, the same comparison using "recurrent" again separated similarity distributions (Figure S7B). The nested k-means subgroups contained 11,425 and 3,013 patients; these cluster sizes should not be equated with diagnosis-code counts.

Within cluster B, similarity distributions showed little separation by the "Missing" token. Nested cluster results are summarized in Table S6.

A All patients

![](../notebooks/figures/bge_small_recurrence_bimodality.png){width=5.8in}

B Cluster A

![](../notebooks/figures/bge_small_cluster0_subsplit.png){width=5.8in}

Figure S7. Pairwise similarity by agreement on "episode" across the cohort (A) and on "recurrent" within cluster A (B). Blue denotes token agreement, red disagreement, and gray all pairs. The analysis is descriptive and does not establish that wording alone causes the separation.

We re-ran k-means (k=2) within each parent cluster and described separation using the cosine silhouette in a seeded 5,000-patient subsample. The top-level silhouette was 0.48.

Silhouette values summarize within- versus between-cluster similarity and are descriptive, not hypothesis tests. They do not by themselves establish discrete biological or clinical subgroups.

Cluster A had a nested silhouette of 0.69. The larger subgroup (n=11,425) contained "recurrent" in 98% of narratives, whereas the smaller subgroup (n=3,013) contained "unspecified" in all narratives. Cluster B had weaker separation (silhouette 0.21); "Missing" appeared in 88% versus 2% of its subgroups. Medication tokens also differed, consistent with differences in record content.

Table S6. Nested k-means results within each parent cluster. Token proportions describe presence in the 2 subgroups. The top-level cosine silhouette was 0.48; higher values indicate greater geometric separation, without establishing clinical validity.

  **Parent cluster (n)**           **Splits into (n / n)**                               **Driving token**   **Token present, sub 1 / sub 2**   **Split silhouette (top level = 0.48)**   **Separation**
  -------------------------------- ----------------------------------------------------- ------------------- ---------------------------------- ----------------------------------------- ----------------
  A: no "episode" token (14,438)   recurrent + severity (11,425) / unspecified (3,013)   recurrent           0.98 / 0.00                        0.69                                      Stronger
  B: single-episode (28,141)       sparse record (6,594) / populated record (21,547)     missing             0.88 / 0.02                        0.21                                      Weaker

These findings show sensitivity of the smallest encoder's geometry to diagnostic wording and missing-value tokens. They may help explain its retrieval behavior, but do not establish why its discrimination was lower (Table S15). Primary analyses used Qwen3-Embedding-8B.

# S5 Example Patient Narratives

Two deterministic narratives are reproduced verbatim, one from each outcome class. They were selected as the first patient by sorted deidentified hash within each class using scripts/pipeline/neighbors/narrative_audit.py. Inputs contained structured EHR fields only. Fixed section order, explicit absence labels, and missing-value tokens formed the template.

The original renderer uses "anchor" for the index and "Baseline window" for the lookback window. These labels are preserved because they show the actual encoder input.

The examples show field asymmetries documented in section S10: narratives include vital signs, sexual orientation, index dates, raw sociodemographic values, and medication names. FEATURE omits some of these fields or uses coarser encodings, but includes total recorded history length. A missing sexual-orientation value appears as the literal token nan.

TRD-positive example.

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

TRD-negative example.

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

# S6 Neighbor Prediction

Retrieval over the embedding carried outcome information but did not reach the trained classifiers. At k = 50 under plain cosine similarity, nearest retrieval achieved an ROC AUC of 0.594, against 0.499 for random and 0.432 for farthest retrieval (Table S7). Mean effective sample size was 50.0 for nearest and 48.9 for random retrieval, so cosine weights were close to equal within a neighborhood of 50.

Neighborhood size mattered more than the metric. Both curves rose to a plateau from about 300 neighbors (manuscript Figure 4). Each metric at its own best k differed by 0.007 (95% CI −0.001 to 0.014). The best k was selected on test patients, so those maxima are optimistic. Using every training patient as a neighbor involves no selection and gave 0.624 for the importance-weighted metric and 0.608 for plain cosine. The sharpening exponent changed the maxima by at most 0.002.

The best retrieval result over every k and exponent, 0.625, remained below feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and below embedded logistic regression by 0.032 (95% CI 0.022--0.043), from paired bootstrap resampling of the 8,516 test patients.

Table S7. Neighbor-prediction ROC AUC for the primary encoder by retrieval scheme, similarity metric, and neighborhood size. Rows at k = 50 use $\alpha$ = 5, the primary setting; rows from the sweep use $\alpha$ = 1. Best k is the test-selected maximum and is optimistic.

| **Retrieval** | **Similarity** | **Neighbors (k)** | **ROC AUC (95% CI)** |
| ---------- | -------------------- | ------------------ | ---------------------- |
| Nearest | Plain cosine | 50 (primary) | 0.594 (0.578--0.610) |
| Nearest | Importance-weighted | 50 | 0.602 (0.587--0.619) |
| Nearest | Plain cosine | best, 757 | 0.618 (0.602--0.634) |
| Nearest | Importance-weighted | best, 295 | 0.625 (0.610--0.641) |
| Nearest | Plain cosine | all, 34,063 | 0.608 (0.592--0.624) |
| Nearest | Importance-weighted | all, 34,063 | 0.624 (0.607--0.639) |
| Random | Plain cosine | 50 | 0.499 (0.483--0.515) |
| Farthest | Plain cosine | 50 | 0.432 (0.416--0.449) |

A Nearest retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_COSINE.png){width=5.8in}

B Random retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_RANDOM_COSINE.png){width=5.8in}

Figure S8. ROC curves for plain-cosine nearest (A) and random (B) retrieval at k = 50. Shaded bands are bootstrap 95% CIs. ROC: receiver operating characteristic.

A Nearest retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_NEAREST_COSINE.png){width=5.8in}

B Random retrieval

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_RANDOM_COSINE.png){width=5.8in}

Figure S9. Confusion matrices for plain-cosine nearest (A) and random (B) retrieval at k = 50, at test-selected Youden J thresholds. These operating points were selected and evaluated in the same patients and are descriptive.

# S7 Record Length and Prediction

We examined record volume descriptively by correlating the outcome with history length, encounter count, and the diagnosis-to-index interval, then assessed neighbor-prediction discrimination across history-length quintiles.

Using the full recorded history, outcome correlations were small: Spearman ρ=−0.073 for pre-index history length, −0.064 for encounter count, and −0.029 for diagnosis-to-index interval. Same-day diagnosis and prescribing occurred in 27,906 patients with outcome frequency 18.4%, compared with 14,673 patients and 15.9% for delayed prescribing. These weak marginal relationships do not rule out care-process contributions to prediction.

A Pre-index history length

![](../notebooks/figures/density_pre_anchor_history_days.png){width=5.7in}

B Diagnosis-to-index interval

![](../notebooks/figures/density_mdd_to_anchor_days.png){width=5.7in}

Figure S10. Continued on the next page.

C Encounter count

![](../notebooks/figures/density_num_encounters.png){width=5.7in}

D Outcome frequency by prescription timing

![](../notebooks/figures/trd_rate_by_delayed_mdd_to_anchor_days.png){width=5.7in}

Figure S10. Record length, diagnosis-to-index interval, encounter count, and outcome frequency by prescription timing. A--C show outcome-stratified distributions; axes are truncated as labeled in the original plots. D compares same-day and delayed prescribing, with group counts above bars and the 17.5% cohort reference as a dashed line.

The held-out test set was divided into quintiles of pre-index history length and the neighbor-weighted predictor was scored within each quintile. The primary retrieval arm, nearest retrieval at k = 50 under plain cosine similarity, is reported in Table S8.

Table S8. Neighbor-weighted discrimination by quintile of pre-index history length (nearest retrieval, plain cosine similarity, k = 50, embedded representation, held-out test set). Quintile bounds are in days of pre-index history.

  **Pre-index history (days)**   **Patients**   **ROC AUC**
  ------------------------------ -------------- -------------
  731--1,110                     1,706          0.580
  1,110--1,554                   1,704          0.598
  1,554--2,066                   1,701          0.582
  2,066--2,733                   1,704          0.610
  2,733--5,288                   1,701          0.578

AUC ranged from 0.578 to 0.610 across quintiles without a monotonic trend. This does not establish independence from record volume; differing case mix and imprecision within strata limit interpretation.

The stratification covers neighbor prediction only, not the trained classifiers. Each quintile contained about 1,700 patients. An analysis by embedding-neighborhood density was not interpretable because 3 of 5 bins were empty.

# S8 Training and Test Characteristics

Table S9 compares selected characteristics in the shared training and test split.

Across 100 predictor rows, maximum absolute SMD was 0.036. The largest value involved a social-determinant flag present in 22 training patients and no test patient. Outcome rates match because the split was stratified.

Table S9. Held-out patients against training patients on the characteristics reported in Table 1. Continuous variables are median (IQR); categorical and boolean entries are n (%). SMD is training minus held-out, in pooled standard deviations. Vital signs are shown because they describe the cohort, but they are rendered only in the narrative representation and are absent from the feature matrix as published (Supplement S10).

  **Characteristic**                      **Training**       **Held-out**       **SMD**
  --------------------------------------- ------------------ ------------------ ---------
  Demographics                                                                  
  Age (years)                             55 (38-70)         55 (38-70)         -0.014
  Age band: 18-29                         4,428 (13.0%)      1,085 (12.7%)      +0.008
  Age band: 30-44                         7,198 (21.1%)      1,827 (21.5%)      -0.008
  Age band: 45-64                         10,632 (31.2%)     2,636 (31.0%)      +0.006
  Age band: 65+                           11,805 (34.7%)     2,968 (34.9%)      -0.004
  Sex: Female                             24,682 (72.5%)     6,168 (72.4%)      +0.001
  Race: White/Caucasian                   27,244 (80.0%)     6,835 (80.3%)      -0.007
  Race: Black/African American            1,894 (5.6%)       474 (5.6%)         -0.000
  Race: Am. Indian/Alaska Native          1,637 (4.8%)       396 (4.7%)         +0.007
  Race: Missing                           247 (0.7%)         50 (0.6%)          +0.017
  Language: English only                  33,698 (98.9%)     8,425 (98.9%)      -0.000
  Depression phenotype                                                          
  MDD recurrence: Recurrent               9,036 (26.5%)      2,177 (25.6%)      +0.022
  MDD severity: Severe                    1,818 (5.3%)       468 (5.5%)         -0.007
  MDD severity: Moderate                  5,807 (17.0%)      1,426 (16.7%)      +0.008
  Psychiatric and substance comorbidity                                         
  Suicidality flagged                     1,392 (4.1%)       361 (4.2%)         -0.008
  Anxiety disorder                        17,975 (52.8%)     4,426 (52.0%)      +0.016
  Substance use disorder (any)            7,472 (21.9%)      1,793 (21.1%)      +0.021
  Insomnia                                7,452 (21.9%)      1,898 (22.3%)      -0.010
  PTSD                                    1,241 (3.6%)       300 (3.5%)         +0.006
  Alcohol use disorder                    1,523 (4.5%)       352 (4.1%)         +0.017
  Medical comorbidity                                                           
  High cholesterol                        12,591 (37.0%)     3,156 (37.1%)      -0.002
  Uncontrolled hypertension               12,544 (36.8%)     3,136 (36.8%)      +0.000
  Vital signs (narrative only)                                                  
  BMI                                     29 (25-35)         29 (25-35)         -0.013
  Systolic BP                             126 (118-136)      126 (118-136)      -0.010
  BMI: not recorded                       7,484 (22.0%)      1,911 (22.4%)      -0.011
  Treatment and utilization                                                     
  Active med count                        1 (0-2)            1 (0-2)            +0.008
  Encounter count                         21 (8-46)          20 (8-47)          -0.001
  Pre-index history (days)                1792 (1213-2547)   1797 (1222-2541)   +0.004
  Prior adequate AD trial (any class)     5,014 (14.7%)      1,262 (14.8%)      -0.003
  Benzodiazepine days recorded            3,775 (11.1%)      949 (11.1%)        -0.002
  Hypnotic recorded                       1,319 (3.9%)       342 (4.0%)         -0.007
  Augmentation therapy used               326 (1.0%)         96 (1.1%)          -0.017

The measured balance supports internal comparability. It does not establish distributional identity or representativeness of the health system, because both partitions inherit the same sampling design.

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

# S10 Representation Field Crosswalk

Table S13 documents how the pipelines encode each source field, based on scripts/data_loading/feature_vector.py and scripts/data_loading/deterministic_narrative.py. It distinguishes shared information from differences in field content and resolution.

Fields were available by the index date. Clinical content used the 730-day lookback, while recorded history length summarized the longer pre-index record and index date identified the prediction date. Neither representation used post-index clinical data.

Table S13. Field-level crosswalk. Asymmetric marks a row where the two representations do not receive the same information. Missing-value rules are as implemented, not as intended.

  **Source field**                        **Feature-matrix encoding**              **Narrative rendering**                           **Missing-value rule**                                                                   **Parity**
  --------------------------------------- ---------------------------------------- ------------------------------------------------- ---------------------------------------------------------------------------------------- ----------------------------------
  MDD recurrence, severity                two categorical columns                  Condition: MDD (recurrence, severity)             empty string is a level in both                                                          matched
  Index date                              no column                                Index date: YYYY-MM-DD                            never missing                                                                            asymmetric
  Lookback window width                   no column (constant)                     Baseline window: −730\...0 days                   never missing                                                                            matched (carries no information)
  MDD-to-index gap                        mdd_to_anchor_days, float                MDD-to-anchor gap: N days                         never missing                                                                            matched
  Encounter count in window               num_encounters, float                    Encounters in window: N                           never missing                                                                            matched
  MDD inside lookback window              mdd_within_window, boolean               MDD within window: Present/Absent                 never missing                                                                            matched
  Recorded pre-index history length       pre_anchor_history_days, float           not rendered                                      never missing                                                                            asymmetric
  Age                                     AgeInYears, float                        AgeInYears: N                                     never missing                                                                            matched
  Sex                                     categorical                              Sex: X                                            absent value becomes its own one-hot level; narrative prints the raw token               matched
  Race / ethnicity                        categorical, seven levels                Race_Ethnicity: X                                 own one-hot level; narrative prints raw token                                            matched
  Preferred language                      categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Marital status                          categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Religion                                categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Smoking status                          categorical, collapsed to three levels   raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Sexual orientation                      no column                                SexualOrientation: X                              rendered as the literal token nan when recorded-but-empty                                asymmetric
  Social determinants of health           nine boolean columns                     SDOH: list of present categories only             absence is an explicit False in the matrix, an omission from the list in the narrative   matched in content
  BMI, systolic BP, diastolic BP          dropped at load                          BMI: N \\\| BP (mean): S/D, or Missing            dropped, so no rule; narrative prints Missing                                            asymmetric
  Psychiatric comorbidity (8 flags)       eight boolean columns                    ARM: Present/Absent for all eight                 never missing                                                                            matched
  Suicidality flag                        boolean                                  SUICIDE FLAG (2y): Present/Absent                 never missing                                                                            matched
  Substance-use specifics (10)            ten boolean columns                      names of present substances only                  absence explicit in matrix, omitted in narrative                                         matched in content
  General medical comorbidity (4)         four boolean columns                     ARM: Present/Absent for all four                  never missing                                                                            matched
  Prior adequate AD trials                five trials\_\<class\> counts            Prior adequate AD trials: CLASS: n for all five   never missing                                                                            matched
  Benzodiazepine days                     benzo_days_coverage, float               Benzodiazepine days (2y): N                       never missing                                                                            matched
  Hypnotics                               hypnotics_burden, count only             count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  Active medications                      polypharmacy_count, count only           count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  NSAIDs                                  nsaid_count, count only                  count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  Psychiatric inpatient days, ED visits   two float columns                        Psych inpatient days: N \\\| ED psych visits: N   never missing                                                                            matched
  Prescribing-safety comorbidity (2)      two boolean columns                      ARM: Present/Absent                               never missing                                                                            matched

Eleven rows are asymmetric. Ten provide additional or finer information to the narrative, including index date, sexual orientation, vital signs, 4 sociodemographic categories, and 3 medication blocks. Recorded history length is available only to FEATURE. The primary comparison therefore cannot isolate encoding from information content.

FEATURE retains categorical missingness as explicit levels. Its primary vital-sign fields were dropped rather than imputed; narratives retained measured values or missing-value tokens. The raw sexual-orientation token nan is a further implementation-specific exception to the general missing-value convention.

A sensitivity analysis added vital signs to FEATURE using missingness indicators and within-fold median imputation and added recorded history length to the narratives. The best-model contrast was reported to remain nonsignificant. These changes address selected asymmetries, not all differences listed above. Quantitative results are not included here and are available from the corresponding author.

# S11 Cohort Characteristics and Outcome Frequency

Within-subgroup outcome frequency divides positive patients by all patients in that subgroup. This differs from the outcome-conditioned column percentages in the cohort table below. All frequencies describe the enriched analytic sample.

Outcome frequency was 18.0% among female and 16.2% among male patients. It declined across age groups: 20.6% at 18--29 years (1,135/5,513), 20.3% at 30--44 (1,836/9,025), 18.4% at 45--64 (2,445/13,268), and 13.8% at 65 or older (2,039/14,773). Selected social-determinant strata had higher frequencies: upbringing-related issues, 33.0%; legal issues, 26.1%; employment issues, 24.0%; and family or support-group issues, 22.9%. Small counts limit these comparisons. Missing race/ethnicity was associated with a frequency of 15.5% (46/297), versus 17.5% overall.

Table S14. Expanded cohort characteristics by TRD proxy status. Values are median (IQR) or n (%); percentages within outcome columns use the corresponding outcome-group denominator. SMD: standardized mean difference; AD: antidepressant; ED: emergency department; MDD: major depressive disorder; PTSD: posttraumatic stress disorder. Total N=42,579; positive n=7,455; negative n=35,124.

  **Characteristic**                      **Level**                  **Overall**            **TRD+**               **TRD−**               **SMD**
  --------------------------------------- -------------------------- ---------------------- ---------------------- ---------------------- ---------
  Demographics                                                                                                                            
  Age (years)                             median (IQR)               55 (38--70)            51 (36--66)            56 (39--71)            −0.193
  Age band                                18--29                     5,513 (12.9%)          1,135 (15.2%)          4,378 (12.5%)          0.080
                                          30--44                     9,025 (21.2%)          1,836 (24.6%)          7,189 (20.5%)          0.100
                                          45--64                     13,268 (31.2%)         2,445 (32.8%)          10,823 (30.8%)         0.043
                                          65+                        14,773 (34.7%)         2,039 (27.4%)          12,734 (36.3%)         −0.192
  Sex                                     Female                     30,850 (72.5%)         5,552 (74.5%)          25,298 (72.0%)         0.055
  Race/ethnicity                          White/Caucasian            34,079 (80.0%)         5,942 (79.7%)          28,137 (80.1%)         −0.010
                                          Black/African American     2,368 (5.6%)           401 (5.4%)             1,967 (5.6%)           −0.010
                                          Am. Indian/Alaska Native   2,033 (4.8%)           394 (5.3%)             1,639 (4.7%)           0.028
                                          Missing                    297 (0.7%)             46 (0.6%)              251 (0.7%)             −0.012
  Depression phenotype                                                                                                                    
  MDD recurrence                          Recurrent                  11,213 (26.3%)         2,189 (29.4%)          9,024 (25.7%)          0.082
                                          Single episode             28,206 (66.2%)         4,721 (63.3%)          23,485 (66.9%)         −0.074
  MDD severity                            Severe                     2,286 (5.4%)           720 (9.7%)             1,566 (4.5%)           0.204
                                          Moderate                   7,233 (17.0%)          1,300 (17.4%)          5,933 (16.9%)          0.014
                                          Psychotic                  112 (0.3%)             35 (0.5%)              77 (0.2%)              0.043
                                          Unspecified                28,951 (68.0%)         4,803 (64.4%)          24,148 (68.8%)         −0.092
  Psychiatric and substance comorbidity                                                                                                   
  Suicidality flagged                     True                       1,753 (4.1%)           641 (8.6%)             1,112 (3.2%)           0.232
  Anxiety disorder                        True                       22,401 (52.6%)         4,499 (60.3%)          17,902 (51.0%)         0.190
  Substance use disorder (any)            True                       9,265 (21.8%)          2,006 (26.9%)          7,259 (20.7%)          0.147
  Insomnia                                True                       9,350 (22.0%)          2,021 (27.1%)          7,329 (20.9%)          0.147
  PTSD                                    True                       1,541 (3.6%)           450 (6.0%)             1,091 (3.1%)           0.141
  Alcohol use disorder                    True                       1,875 (4.4%)           501 (6.7%)             1,374 (3.9%)           0.125
  Opioid use disorder                     True                       1,281 (3.0%)           337 (4.5%)             944 (2.7%)             0.098
  Adjustment disorder                     True                       2,918 (6.9%)           663 (8.9%)             2,255 (6.4%)           0.093
  Medical comorbidity                                                                                                                     
  High cholesterol                        True                       15,747 (37.0%)         2,202 (29.5%)          13,545 (38.6%)         −0.191
  Uncontrolled hypertension               True                       15,680 (36.8%)         2,366 (31.7%)          13,314 (37.9%)         −0.130
  Treatment and utilization                                                                                                               
  Active med count                        median (IQR)               1 (0--2)               1 (0--2)               1 (0--2)               0.084
  Encounter count                         median (IQR)               21 (8--46)             17 (6--40)             21 (8--47)             −0.140
  Pre-index history (days)                median (IQR)               1,792 (1,216--2,546)   1,629 (1,141--2,335)   1,830 (1,239--2,587)   −0.198
  Any prior treatment exposure recorded   True                       10,230 (24.0%)         1,793 (24.1%)          8,437 (24.0%)          0.001
  Prior adequate AD trial (any class)     True                       6,276 (14.7%)          1,050 (14.1%)          5,226 (14.9%)          −0.023
  Benzodiazepine days recorded            True                       4,724 (11.1%)          989 (13.3%)            3,735 (10.6%)          0.081
  Hypnotic recorded                       True                       1,661 (3.9%)           292 (3.9%)             1,369 (3.9%)           0.001
  Augmentation therapy used               True                       422 (1.0%)             108 (1.4%)             314 (0.9%)             0.052

# S12 Additional Model Diagnostics and Encoder Estimates

## S12 1 Primary ROC Curves and Descriptive Operating Points

The primary ROC curves are shown in Figure S12. At test-selected Youden J thresholds of 0.165 and 0.173, embedded logistic regression and feature-vector XGBoost had sensitivity 0.65 and 0.62 and specificity 0.58 and 0.61. They identified 964 and 917 of 1,491 positive patients, with 2,932 and 2,768 false positives, respectively (Figure S13). These thresholds were chosen and evaluated in the same test patients; the estimates are optimistic descriptions and are not deployment thresholds.

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_xgboost_FEATURE.png){width=5.8in}

Figure S12. Primary ROC curves for embedded logistic regression (A) and feature-vector XGBoost (B). Shaded bands are bootstrap 95% CIs. ROC AUCs are reported in main-text Table 2.

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_xgboost_FEATURE.png){width=5.8in}

Figure S13. Confusion matrices at test-selected Youden J thresholds for embedded logistic regression (A) and feature-vector XGBoost (B). TRD refers to the treatment-switching proxy.

## S12 2 Structured Feature Importance

Positive logistic-regression coefficients included severe depression coding, suicidality, insomnia, obsessive-compulsive disorder, opioid use disorder, posttraumatic stress disorder, and anxiety. Negative coefficients included missing smoking status, hyperlipidemia, longer pre-index history, and male sex. Tree importance rankings varied and also emphasized record length, age, utilization, and psychiatric burden (Figure S14). For trees, plotted colors derive from univariate correlations and do not give the direction of the fitted model's conditional effect. None of these rankings supports causal interpretation.

A Logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_logistic_regression.png){width=5.7in}

B Random forest

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_random_forest.png){width=5.7in}

Figure S14. Continued on the next page.

C Gradient boosting

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_gradient_boosting.png){width=5.7in}

D XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_xgboost.png){width=5.7in}

Figure S14. Structured feature importance for logistic regression (A), random forest (B), gradient boosting (C), and XGBoost (D). Logistic-regression bars show signed coefficients. Tree bars show native importance; colors reflect univariate associations, not conditional model effects or causal directions.

## S12 3 Concept Permutation and Encoder Comparison

In the primary encoder, psychiatric-history permutation reduced AUC by 0.024--0.028 across classifiers; all paired CIs excluded zero. Medication burden reduced AUC by 0.003--0.027, with CIs excluding zero for 3 classifiers. Prior treatment reduced embedded logistic-regression AUC by 0.019 and the other models by 0.000--0.011, with CIs excluding zero for logistic regression and XGBoost. Among the remaining concepts, only the XGBoost contraindication contrast excluded zero (−0.005; 95% CI −0.008 to −0.001). Main-text Table 3 gives point differences; Figure S15 gives each model's absolute AUC.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/ablation_roc_ci_EMBEDDED.png){width=6.6in}

Figure S15. Absolute ROC AUC after concept permutation for each primary embedded classifier. Each panel includes the unperturbed baseline and 6 permutations. Bars are each run's bootstrap 95% CIs, rather than paired CIs for the differences. SDOH: social determinants of health.

Embedded logistic regression had the highest AUC for every encoder. Across encoders, psychiatric-history permutation reduced its AUC by 0.027--0.030 and medication-burden permutation by 0.022--0.034, with all paired CIs excluding zero. Medication burden exceeded psychiatric history in bge-en-icl (−0.034 versus −0.027); psychiatric history had the larger effect in the other 3 encoders. The ordering applies to these tested concepts and does not establish unique or causal contributions.

Table S15. Embedded logistic-regression discrimination by encoder. EPV is 5,964 positive training outcomes divided by input dimension and is descriptive for these regularized models.

  **Encoder**          **Dimensions**   **EPV**   **ROC AUC (95% CI)**
  -------------------- ---------------- --------- ----------------------
  bge-small-en-v1.5    384              15.5      0.645 (0.629--0.660)
  bge-en-icl           4,096            1.5       0.655 (0.641--0.670)
  Qwen3-Embedding-4B   2,560            2.3       0.655 (0.641--0.670)
  Qwen3-Embedding-8B   4,096            1.5       0.657 (0.643--0.672)

# References

1\. Gaynes BN, Lux L, Gartlehner G, Asher G, Forman-Hoffman V, Green J, et al. Defining treatment-resistant depression. Depress Anxiety. 2020;37(2):134-145. doi:10.1002/da.22968.

2\. Rush AJ, Trivedi MH, Wisniewski SR, Nierenberg AA, Stewart JW, Warden D, et al. Acute and longer-term outcomes in depressed outpatients requiring one or several treatment steps: a STAR\*D report. Am J Psychiatry. 2006;163(11):1905-1917. doi:10.1176/ajp.2006.163.11.1905.

3\. González HM, Vega WA, Williams DR, Tarraf W, West BT, Neighbors HW. Depression care in the United States: too little for too few. Arch Gen Psychiatry. 2010;67(1):37-46. doi:10.1001/archgenpsychiatry.2009.168.

4\. Alegría M, Chatterji P, Wells K, Cao Z, Chen CN, Takeuchi D, et al. Disparity in depression treatment among racial and ethnic minority populations in the United States. Psychiatr Serv. 2008;59(11):1264-1272. doi:10.1176/ps.2008.59.11.1264.

5\. Perlis RH. A clinical risk stratification tool for predicting treatment resistance in major depressive disorder. Biol Psychiatry. 2013;74(1):7-14. doi:10.1016/j.biopsych.2012.12.007.

6\. Kautzky A, Baldinger-Melich P, Kranz GS, Vanicek T, Souery D, Montgomery S, et al. A new prediction model for evaluating treatment-resistant depression. J Clin Psychiatry. 2017;78(2):215-222. doi:10.4088/JCP.15m10381.

7\. Sheu YH, Magdamo C, Miller M, Das S, Blacker D, Smoller JW. AI-assisted prediction of differential response to antidepressant classes using electronic health records. npj Digit Med. 2023;6:73. doi:10.1038/s41746-023-00817-8.

8\. Chekroud AM, Zotti RJ, Shehzad Z, Gueorguieva R, Johnson MK, Trivedi MH, et al. Cross-trial prediction of treatment outcome in depression: a machine learning approach. Lancet Psychiatry. 2016;3(3):243-250. doi:10.1016/S2214-0366(15)00471-X.

9\. Hegselmann S, Shen SZ, Gierse F, Agrawal M, Sontag D, Jiang X. A data-centric approach to generate faithful and high quality patient summaries with large language models. Proc Mach Learn Res. 2024;248:339-379.

10\. Reimers N, Gurevych I. Sentence-BERT: sentence embeddings using Siamese BERT-networks. In: Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP); 2019 Nov; Hong Kong. Stroudsburg (PA): Association for Computational Linguistics; 2019. p. 3982-3992. doi:10.18653/v1/D19-1410.

11\. Xiao S, Liu Z, Zhang P, Muennighoff N, Lian D, Nie JY. C-Pack: packed resources for general Chinese embeddings. In: Proceedings of the 47th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '24); 2024 Jul 14-18; Washington (DC). New York: ACM; 2024. p. 641-649. doi:10.1145/3626772.3657878.

12\. Li C, Qin M, Xiao S, Chen J, Luo K, Shao Y, et al. Making text embedders few-shot learners. arXiv:2409.15700. 2024.

13\. Zhang Y, Li M, Long D, Zhang X, Lin H, Yang B, et al. Qwen3 embedding: advancing text embedding and reranking through foundation models. arXiv:2506.05176. 2025.

14\. Hegselmann S, von Arnim G, Rheude T, Kronenberg N, Sontag D, Hindricks G, et al. Large language models are powerful electronic health record encoders. arXiv:2502.17403. 2025.

15\. Varma S, Simon R. Bias in error estimation when using cross-validation for model selection. BMC Bioinformatics. 2006;7:91. doi:10.1186/1471-2105-7-91.
