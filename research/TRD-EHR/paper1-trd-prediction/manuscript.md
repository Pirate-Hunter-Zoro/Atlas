<!--
TRD prediction from EHR-derived patient representations.
Target venue: JMIR Mental Health. Reporting follows TRIPOD+AI.
Source of truth is this Markdown; the .docx and .pdf are built, not edited.

THE TEXT IS THE SENIOR AUTHOR'S. This document is Martin Paulus's revision
(review/feedback/2026-09-21/manuscript_revised.docx), converted, with the
retrieval direction applied on top. Keep his wording outside the passages
below; a change to his prose is a question for him, not an edit.

THE PAPER MAKES TWO POINTS.
  1. The embedding does not significantly outperform the feature vector:
     best against best, +0.008 ROC AUC (95% CI -0.003 to 0.019).
  2. Nearest-neighbor retrieval over the embedding carries real signal and
     still loses to a trained classifier at every k from 1 to 34,063. Best
     retrieval 0.625 against 0.649 and 0.657; paired intervals exclude zero.

THE RETRIEVAL SLATE IS TWO ARMS: plain cosine (the k = 50 baseline) and
importance-weighted cosine (Equations 1-2). Random and farthest are negative
controls. The LLM clinical-similarity judge, uniform and combined weighting,
and subsampled retrieval are out of the main text and the supplement; the
judge is complete in reserve/llm_similarity_judge.md. Every retrieval number
is in results/.../neighbor_count_sweep/{sweep_summary,retrieval_paired_deltas}.json,
drawn by scripts/pipeline/predictions/plot_neighbor_sweep_figure.py.

INDEX DATES ARE 2013-2025, measured over all 42,579 patients. Paper-Writer's
numbers gate skips four-digit years, so nothing catches this but reading.

SUBGROUPS are 240 contrasts over the two-arm slate, 24 surviving BH, from
results/review/subgroups/subgroup_summary.json.

SUPPLEMENT POINTERS follow supplement.md, which is the senior author's
supplement with his judge section removed: sections S1-S12, Tables S1-S15,
Figures S1-S15.
-->

# Title page

**Title.** Feature Vectors and Narrative Embeddings for Predicting a Treatment Switching Proxy for Treatment Resistant Depression: Retrospective Cohort Study

Mikey Ferguson, BS¹; Martin Paulus, MD¹; Rayus Kuplicki, PhD¹; Katherine L. Forthman, MS¹; Dale Peasley, MS¹; Sandip Sen, PhD²

¹ Laureate Institute for Brain Research, Tulsa, Oklahoma, United States\
² The University of Tulsa, Tulsa, Oklahoma, United States

## Corresponding Author

Mikey Ferguson, BS\
Laureate Institute for Brain Research\
6655 South Yale Avenue, Tulsa, OK 74136, United States\
Email: mferguson\@laureateinstitute.org\
ORCID: 0009-0005-1365-5609

## Author ORCIDs

Mikey Ferguson 0009-0005-1365-5609

Martin Paulus 0000-0002-0825-3606

Rayus Kuplicki 0000-0003-2954-6421

Katherine L. Forthman 0000-0002-8695-8388

Dale Peasley 0009-0003-7696-595X

Sandip Sen 0000-0001-6107-4095

# Abstract

**Background:** Electronic health records (EHRs) have been shown to support prediction of subsequent antidepressant switching, an imperfect proxy for treatment-resistant depression (TRD). However, it is unclear whether general-purpose narrative embeddings improve prediction beyond structured feature vectors.

**Objective:** We compared structured feature vectors with pretrained embeddings of rule-based patient narratives for predicting a treatment-switching proxy for TRD at the index antidepressant prescription.

**Methods:** This retrospective study included 42,579 patients with depression from one community health system. The outcome required at least 3 distinct antidepressant treatments, including the index agent, within 365 days. Clinical predictors were derived from a 730-day lookback window. We evaluated 4 classifiers on each representation using a shared 80:20 training and test split, with preprocessing and tuning confined to training data. Four embedding encoders were evaluated; Qwen3-Embedding-8B was primary. The pipelines used the same source records. We assessed discrimination, calibration, and paired bootstrap differences, and used concept permutation and neighbor retrieval to examine the predictive signal.

**Results:** The outcome occurred in 7,455 patients (17.5%). In 8,516 test patients, embedded logistic regression achieved a receiver operating characteristic area under the curve (ROC AUC) of 0.657 (95% CI 0.643--0.672), compared with 0.649 (95% CI 0.634--0.664) for feature-vector XGBoost. The post hoc difference between these leading models was 0.008 (95% CI −0.003 to 0.019). Embeddings improved logistic regression by 0.028 ROC AUC but reduced discrimination for the 3 tree ensembles by 0.013--0.022. Embedded logistic regression achieved ROC AUCs of 0.645--0.657 across encoders. Permuting psychiatric history produced the largest discrimination loss for the primary encoder (0.024--0.028 across classifiers); medication burden and prior treatment exposure also contributed. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003. Nearest-neighbor retrieval over the embedding stayed below both leading classifiers at every neighborhood size tested; its best ROC AUC was 0.625 (95% CI 0.610--0.641).

**Conclusions:** Narrative embeddings did not demonstrate superior discrimination over the strongest structured feature model for this treatment-switching proxy. Performance depended on the classifier, and neither pipeline established clinical utility. These findings support structured features as a practical benchmark and prioritize validation of the outcome, transportability, and clinical value before deployment.

Keywords: treatment-resistant depression; depression; electronic health records; machine learning; clinical prediction; text embeddings; antidepressants

# Introduction

Treatment-resistant depression (TRD) is commonly defined as inadequate response to at least 2 antidepressant trials of adequate dose and duration \[1\]. The probability of remission declines with successive treatment steps \[2\], and persistent depression carries substantial clinical and economic burden \[3\]. Identifying patients likely to experience a difficult treatment course could inform monitoring and follow-up. Clinical prediction studies suggest that relevant information is available, but reliable individual prediction remains challenging \[4-8\].

Electronic health records (EHRs) offer longitudinal information on diagnoses, prescribing, and health care use. They rarely establish why a medication was changed or whether an adequate trial failed. Consequently, EHR studies often define TRD through treatment sequences. These definitions identify observable care trajectories, and changes in the rules alter both outcome frequency and cohort composition \[9-11\]. A model predicting repeated switching therefore requires a more limited interpretation than one predicting symptom-confirmed treatment resistance.

Prior EHR models have reported widely varying discrimination. Internal performance as high as a receiver operating characteristic area under the curve (ROC AUC) of 0.83 contrasts with an externally validated estimate of 0.652 and cross-system estimates of 0.51--0.58 \[12-14\]. Combining structured records with clinical notes has improved performance in a smaller study \[15\]. These findings make the source and representation of information, the prediction time, and the validation setting central to interpreting any apparent advance.

General-purpose text encoders provide one way to represent an EHR without training a large clinical foundation model \[16-18\]. Structured fields can be converted into a patient narrative and then encoded as a numerical embedding for prediction. The practical question is whether this additional processing improves on a transparent feature vector. A narrative created from the same structured records adds no new measurement, although the encoding may organize existing information differently.

We asked whether pretrained embeddings of rule-based patient narratives improve prediction of a treatment-switching proxy for TRD beyond structured feature vectors at the index antidepressant prescription. We compared the pipelines in the same patients, using a common temporal design and test set. Secondary analyses examined whether performance depended on the classifier or encoder, which clinical domains contributed, and whether embedding similarity supported prediction. The comparison concerns complete representation pipelines because their field inventories were not identical.

# Methods

## Study Design and Data Source

We conducted a retrospective cohort study using a frozen, deidentified Epic EHR extract from Saint Francis Health System in Tulsa, Oklahoma. The extract contained 501,718 patients and included diagnoses, encounters, medications, procedures, and laboratory data. Patients with a problem-list depression flag were retained, together with a random sample without that flag. The resulting sample was enriched for depression and does not represent health-system prevalence. Encounter-level diagnoses determined study eligibility; 12,530 eligible patients (29.4%) entered through the randomly sampled group.

We used data version DV260629v1 and patient version PV260710v1, extracted on June 29, 2026, and processed on July 10, 2026. Index dates spanned 2013--2025. Evaluation used a random internal split from the same source and period. Source definitions and sampling details are provided in Multimedia Appendix 1, sections M1--M2. We used TRIPOD+AI to guide reporting \[19\].

## Participants and Prediction Time

Eligible patients met the study's coded depression definition, had no bipolar or schizophrenia-spectrum diagnosis, had an antidepressant index prescription on or after a documented depression diagnosis, and had at least 730 days of prior history and 365 days of subsequent follow-up. The depression code set included major depressive disorder (MDD), dysthymia, and unspecified depression. The final cohort included 42,579 patients; the eligibility cascade and code lists appear in Multimedia Appendix 1, sections M1--M2.

The index was the earliest recorded antidepressant prescription on or after the first documented depression diagnosis. It was not necessarily the first lifetime exposure: prior antidepressant use was retained as a predictor. Index selection did not require subsequent dose adequacy, duration, response, or treatment change. Clinical content was restricted to the 730-day window ending on the index date; total recorded pre-index history length was an additional duration variable. Post-index information established follow-up eligibility and the outcome (Figure 1).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/time_zero_timeline.png){width=6in}

***Figure 1.** Prediction time and observation windows. The index is the earliest antidepressant prescription on or after the first recorded depression diagnosis. Clinical content comes from the preceding 730 days through the index date. Total recorded pre-index history length is a separate duration predictor and can exceed this window. The subsequent 365 days establish follow-up eligibility and the treatment-switching outcome. The 57.9% annotation describes candidate index orders, not the final cohort. EHR: electronic health record; MDD: major depressive disorder; TRD: treatment-resistant depression proxy.*

## Outcome

The prespecified outcome was a treatment-switching proxy for TRD, generated upstream and supplied as a fixed label \[20\]. Patients were positive if they received at least 3 distinct antidepressant treatments within 365 days, counting the index agent first. This required at least 2 subsequent changes to distinct agents. Augmentation without replacement and restarting a previously used agent did not increase the count.

The outcome did not verify inadequate response to 2 adequate trials. Standardized symptom response was unavailable, and dose and duration adequacy were not established for the counted treatments. Switching could reflect nonresponse, intolerance, preference, access, or prescribing practice. The label was not validated by chart review or symptom measures (Multimedia Appendix 1, section M3). We use "TRD proxy" throughout to distinguish this outcome from clinically confirmed resistance.

## Patient Representations and Missing Data

Predictor domains were selected before model fitting or examination of outcome associations. They included depression coding, psychiatric and medical comorbidity, prior treatment, medication burden, utilization, prescribing constraints, and sociodemographic characteristics \[4-7\]. The structured representation (FEATURE) comprised 92 encoded columns. Continuous variables were standardized, categorical variables were one-hot encoded, and binary variables were coded as 0 or 1. Prior antidepressant trial counts required at least 42 days of continuous exposure; this duration rule did not establish adequate dose.

For the embedded representation (EMBEDDED), fixed rules converted structured fields into Markdown narratives. No generative model wrote the narratives, preserving traceability to the source fields \[21\]. We evaluated bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, and Qwen3-Embedding-8B; the last was the primary encoder \[22-25\].

The pipelines differed in information content. Narratives retained vital signs, individual medication names, index dates, sexual orientation, and finer sociodemographic categories; FEATURE included total recorded history length, which the narratives omitted. Missing vital signs were excluded from FEATURE, and no statistical imputation was used in the primary analysis. Missing categorical information was represented explicitly, although some narrative fields retained raw missing-value tokens. Encoding rules, the predictor inventory, example narratives, and the field crosswalk are provided in Multimedia Appendix 1, sections M4--M6, S5, and S10.

## Model Development and Evaluation

All models used one stratified 80:20 split: 34,063 training patients, including 5,964 outcome-positive patients, and 8,516 test patients, including 1,491 outcome-positive patients. We fitted logistic regression, random forest, gradient boosting, and XGBoost to each representation. Five-fold cross-validated grid search optimized ROC AUC within the training set. Scaling and category encoding were fitted within each training fold; the selected pipeline was then refitted on all training patients and applied to the test set. Tuning grids were identical across representations for each classifier (Multimedia Appendix 1, sections M7--M9).

We assessed ROC AUC, area under the precision--recall curve (AUPRC), Brier score, and calibration. The supplementary calibration-curve summaries use slopes and intercepts fitted to binned probabilities; the subgroup analyses separately report logistic calibration slopes based on individual predicted probabilities. These quantities are distinguished because they are not interchangeable. All calibration estimates concern this enriched cohort.

Nonparametric bootstrap resampling of test patients provided 95% CIs. Paired resampling estimated differences between representations and between original and perturbed predictions. Classifier-matched contrasts held the learner fixed. The comparison of the best model for each representation was post hoc because the leading models were identified from test performance. No equivalence margin was prespecified; a CI containing zero does not establish equivalence. Sensitivity and specificity at test-selected Youden J thresholds are reported only as descriptive analyses in Multimedia Appendix 1, section S12.

## Supporting Analyses

We examined embedded-model reliance on 6 concepts by permuting one narrative section or field across patients, re-embedding the narratives, and applying the original classifiers without retraining. The concepts were psychiatric history, medication burden, prior treatment exposure, prescribing contraindications, race/ethnicity, and social determinants of health. Change in ROC AUC measures reliance under the specified perturbation; it does not identify causal mechanisms or establish fairness.

We also predicted each test patient's outcome from its nearest training-set neighbors. Test patients served only as queries. The risk score was the similarity-weighted mean outcome of the k most similar training patients (Equation 2). Similarity was measured in 2 ways. Plain cosine similarity used the raw embeddings. Importance-weighted cosine similarity first standardized each embedding dimension with the embedded logistic regression's own scaler. It then weighted each dimension by its share of that model's absolute coefficients (Equation 1). The coefficients were fitted on training patients only, so no test outcome entered a risk score.

$$\mathrm{sim}_w(x,y)=\frac{\sum_d w_d\,z_d(x)\,z_d(y)}{\sqrt{\sum_d w_d\,z_d(x)^2}\,\sqrt{\sum_d w_d\,z_d(y)^2}},\qquad w_d=\frac{|\beta_d|}{\sum_e |\beta_e|}\qquad(1)$$

$$\hat{r}(x)=\frac{\sum_{i\in N_k(x)} s_i^{\alpha}\,y_i}{\sum_{i\in N_k(x)} s_i^{\alpha}},\qquad s_i=\max\{\mathrm{sim}(x,i),0\}\qquad(2)$$

Here $z_d$ is dimension $d$ after standardization, $\beta_d$ is its logistic-regression coefficient, $N_k(x)$ is the set of the $k$ most similar training patients, $y_i$ is a neighbor's outcome, and $\alpha$ is a sharpening exponent. Plain cosine similarity is Equation 1 with raw embeddings and equal weights. The primary analysis used k = 50 and α = 5. A sweep evaluated every k from 1 to all 34,063 training patients, under α = 1, 2, and 5. Random and farthest retrieval served as negative controls. Details appear in Multimedia Appendix 1, sections M10--M12 and S6.

Additional analyses examined encoder robustness, model dimensionality, record length, and subgroup performance. Subgroup comparisons used held-out predictions without refitting and Benjamini--Hochberg adjustment across 240 contrasts. Full methods and results appear in Multimedia Appendix 1. All random processes were seeded; analyses used Python, scikit-learn, XGBoost, and sentence-transformers \[22,26,27\].

## Ethical Considerations

We analyzed deidentified secondary records without direct identifiers. No institutional review board review or consent waiver was obtained because the study was considered not to involve human participants. All analytic computation, including embedding, ran on local institutional hardware; patient-level analytic data were not transmitted to external services. No patients or members of the public participated in the design, conduct, or reporting of the study.

# Results

## Cohort Characteristics

Of 501,718 patients in the extract, 42,579 met eligibility criteria and 7,455 (17.5%) met the TRD proxy definition. Median age was 55 years (IQR 38--70); 72.5% were female, 80.0% were recorded as White/Caucasian, and 98.9% preferred English. Outcome-positive patients more often had coded suicidality, severe depression, anxiety, insomnia, and substance use disorders (Table 1). Expanded characteristics and subgroup outcome frequencies are in Multimedia Appendix 1, section S11.

***Table 1.** Selected cohort characteristics by TRD proxy status. Values are median (IQR) or n (%). SMD is the standardized mean difference between positive and negative groups. MDD: major depressive disorder; PTSD: posttraumatic stress disorder. Expanded characteristics appear in Multimedia Appendix 1, Table S14.*

  --------------------------------------------------------------------------------------------------------------------
  Characteristic                         Overall\               TRD\                   Non-TRD\               SMD
                                         N=42,579               n=7,455                n=35,124               
  -------------------------------------- ---------------------- ---------------------- ---------------------- --------
  Age (years)                            55 (38--70)            51 (36--66)            56 (39--71)            −0.193

  Female                                 30,850 (72.5%)         5,552 (74.5%)          25,298 (72.0%)         0.055

  White/Caucasian                        34,079 (80.0%)         5,942 (79.7%)          28,137 (80.1%)         −0.010

  Recurrent MDD                          11,213 (26.3%)         2,189 (29.4%)          9,024 (25.7%)          0.082

  Severe MDD                             2,286 (5.4%)           720 (9.7%)             1,566 (4.5%)           0.204

  Unspecified MDD severity               28,951 (68.0%)         4,803 (64.4%)          24,148 (68.8%)         −0.092

  Suicidality flagged                    1,753 (4.1%)           641 (8.6%)             1,112 (3.2%)           0.232

  Anxiety disorder                       22,401 (52.6%)         4,499 (60.3%)          17,902 (51.0%)         0.190

  Substance use disorder (any)           9,265 (21.8%)          2,006 (26.9%)          7,259 (20.7%)          0.147

  Insomnia                               9,350 (22.0%)          2,021 (27.1%)          7,329 (20.9%)          0.147

  PTSD                                   1,541 (3.6%)           450 (6.0%)             1,091 (3.1%)           0.141

  Active medication count                1 (0--2)               1 (0--2)               1 (0--2)               0.084

  Encounter count                        21 (8--46)             17 (6--40)             21 (8--47)             −0.140

  Pre-index history (days)               1,792 (1,216--2,546)   1,629 (1,141--2,335)   1,830 (1,239--2,587)   −0.198

  Any prior antidepressant exposure      10,230 (24.0%)         1,793 (24.1%)          8,437 (24.0%)          0.001

  Prior antidepressant course ≥42 days   6,276 (14.7%)          1,050 (14.1%)          5,226 (14.9%)          −0.023
  --------------------------------------------------------------------------------------------------------------------

Training and test characteristics were closely balanced (maximum absolute standardized mean difference 0.036). Weak negative correlations linked the outcome to history length, encounter count, and time from depression diagnosis to the index prescription. These descriptive checks do not exclude effects of observation or care access (Multimedia Appendix 1, sections S7--S8).

## Discrimination and Calibration

Embedded logistic regression had the highest ROC AUC, 0.657 (95% CI 0.643--0.672), followed by feature-vector XGBoost at 0.649 (95% CI 0.634--0.664). Their paired difference was 0.008 (95% CI −0.003 to 0.019). This post hoc comparison did not demonstrate superior discrimination for embeddings (Table 2; Figure 2).

***Table 2.** Discrimination and Brier score in 8,516 test patients for all primary model combinations. AUPRC: area under the precision--recall curve; ROC AUC: area under the receiver operating characteristic curve. The positive-rate reference for AUPRC is 0.175. EMBEDDED uses Qwen3-Embedding-8B; FEATURE uses 92 structured columns.*

  Representation   Classifier            ROC AUC (95% CI)       AUPRC   Brier score
  ---------------- --------------------- ---------------------- ------- -------------
  EMBEDDED         Logistic regression   0.657 (0.643--0.672)   0.302   0.137
  EMBEDDED         Random forest         0.623 (0.608--0.639)   0.270   0.140
  EMBEDDED         Gradient boosting     0.632 (0.618--0.647)   0.276   0.139
  EMBEDDED         XGBoost               0.636 (0.621--0.651)   0.278   0.139
  FEATURE          Logistic regression   0.629 (0.613--0.644)   0.278   0.139
  FEATURE          Random forest         0.644 (0.630--0.659)   0.293   0.139
  FEATURE          Gradient boosting     0.645 (0.629--0.660)   0.288   0.138
  FEATURE          XGBoost               0.649 (0.634--0.664)   0.298   0.138

The direction of the representation difference depended on the classifier. Embeddings improved logistic regression by 0.028 ROC AUC (95% CI 0.017--0.039), but reduced performance for random forest by 0.022 (95% CI 0.011--0.033), gradient boosting by 0.013 (95% CI 0.001--0.026), and XGBoost by 0.013 (95% CI 0.002--0.025).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/discrimination_forest_EMBEDDED_vs_FEATURE.png){width=6in}

***Figure 2.** Discrimination by representation and classifier. A: ROC AUC with bootstrap 95% CIs for all primary models. B: paired differences, EMBEDDED minus FEATURE, with 95% CIs. Diamonds hold the classifier fixed; the star compares embedded logistic regression with feature-vector XGBoost, selected post hoc. An interval crossing zero does not demonstrate superiority or establish equivalence.*

AUPRC was 0.302 for embedded logistic regression and 0.298 for feature-vector XGBoost, compared with the cohort's positive-rate reference of 0.175. Brier scores were 0.137 and 0.138, respectively. Calibration varied by model and method of assessment; the individual-level logistic calibration slope for embedded logistic regression was 0.97. Full calibration summaries, precision--recall curves, and descriptive operating points appear in Multimedia Appendix 1, sections S2--S3, S9, and S12.

## Clinical Contributions and Encoder Robustness

For the primary encoder, permuting psychiatric history reduced ROC AUC by 0.024--0.028 across classifiers, with all paired CIs excluding zero. For embedded logistic regression, medication burden and prior treatment exposure reduced ROC AUC by 0.027 and 0.019, respectively. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003 (Table 3). These results describe direct input reliance under the tested perturbations.

***Table 3.** Change in ROC AUC after permuting each narrative concept and applying the frozen primary models. Negative values indicate reduced discrimination. LR: logistic regression; RF: random forest; GB: gradient boosting; XGB: XGBoost; SDOH: social determinants of health. Values are point differences; psychiatric-history paired CIs excluded zero for all 4 classifiers.*

  Permuted concept              LR       RF       GB       XGB
  ----------------------------- -------- -------- -------- --------
  Psychiatric history           −0.028   −0.027   −0.024   −0.027
  Medication burden             −0.027   −0.003   −0.014   −0.017
  Treatment exposure            −0.019   +0.000   −0.006   −0.011
  Treatment contraindications   −0.002   +0.001   −0.001   −0.005
  Social determinants (SDOH)    −0.000   +0.000   +0.000   +0.001
  Race/ethnicity                −0.000   +0.000   −0.003   −0.000

Logistic regression was the strongest embedded classifier for all 4 encoders, with ROC AUCs ranging from 0.645 to 0.657. Psychiatric history and medication burden remained the largest contributors across encoders: permutation reduced logistic-regression ROC AUC by 0.027--0.030 and 0.022--0.034, respectively (Figure 3). Feature-vector coefficient rankings also emphasized psychiatric burden, including suicidality, severe depression coding, insomnia, and anxiety. Detailed importance, dimensionality, and encoder analyses are in Multimedia Appendix 1, sections S1, S4, and S12.

![](../results/cross_embedder_robustness_EMBEDDED.png){width=6in}

***Figure 3.** Encoder robustness for embedded logistic regression. A: ROC AUC with bootstrap 95% CIs. B: change in ROC AUC after permutation of psychiatric history or medication burden, with paired bootstrap 95% CIs. Encoders are bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, and Qwen3-Embedding-8B. Complete encoder estimates appear in Multimedia Appendix 1, Table S15.*

## Retrieval and Subgroup Performance

At k = 50, plain cosine retrieval achieved an ROC AUC of 0.594 (95% CI 0.578--0.610). Random retrieval yielded 0.499 and farthest retrieval 0.432. Neighborhood size mattered more than the similarity metric (Figure 4). Discrimination rose with k and was flat from roughly 300 neighbors onward. At its best k, importance-weighted retrieval reached 0.625 (95% CI 0.610--0.641) and plain cosine 0.618 (95% CI 0.602--0.634). The paired difference between the 2 metrics was 0.007 (95% CI −0.001 to 0.014). The best retrieval result over every k and exponent was still lower than feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and lower than embedded logistic regression by 0.032 (95% CI 0.022--0.043). Because the best k was chosen on test patients, these maxima are optimistic. Using all 34,063 training patients as neighbors, with no k chosen, gave 0.624 (Multimedia Appendix 1, section S6).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/neighbor_count_sweep_manuscript.png){width=6in}

***Figure 4.** Retrieval discrimination by neighborhood size. ROC AUC in 8,516 test patients for importance-weighted and plain cosine retrieval at every k from 1 to 34,063, with bootstrap 95% bands. Points mark each metric's best k. The vertical line marks k = 50, the primary analysis. Horizontal lines mark the 2 leading trained classifiers. Curves use α = 1; the maxima under α = 1, 2, and 5 agreed within 0.002.*

Of 240 subgroup contrasts, 24 survived multiplicity adjustment; 19 involved depression recurrence. Discrimination was higher with recurrent coding in all 10 models contrasted and lower with single-episode coding in 9. Performance was lower among never-married patients for 2 embedded classifiers and importance-weighted retrieval, and among patients aged 18--29 for feature-vector XGBoost. Plain cosine retrieval discriminated better in patients with severe coding. Sex contrasts did not show clear differences. White-minus-non-White ROC AUC differences were consistently positive (0.005--0.052), but none survived adjustment. For feature-vector logistic regression, individual-level calibration slopes were 0.98 in White patients and 0.79 in patients with other recorded racial categories. These findings do not establish equitable performance (Multimedia Appendix 1, section S9).

# Discussion

## Principal Findings

We asked whether pretrained narrative embeddings improve prediction of a treatment-switching proxy for TRD beyond structured feature vectors. In this cohort, they did not demonstrate superior discrimination over the strongest feature-vector model. The leading models achieved ROC AUCs of 0.657 and 0.649, with a paired difference of 0.008 (95% CI −0.003 to 0.019). This finding supports structured features as a practical benchmark; it does not establish equivalence or isolate the effect of encoding identical information.

The choice of classifier changed the result. Embeddings improved logistic regression but reduced discrimination for each tree ensemble, and logistic regression led the embedded models across all encoders. This pattern is consistent with regularized linear models accommodating distributed embedding information more effectively under the tested settings. Differences in dimensionality, regularization, and tuning may also contribute. The analysis supports evaluating the representation and classifier together, without attributing the pattern to an intrinsic property of clinical information.

The predictive signal was concentrated in familiar aspects of clinical history. Psychiatric comorbidity, medication burden, and prior treatment contributed most to embedded discrimination, while feature-vector models highlighted related markers of illness complexity. Nearest-neighbor analyses showed that embedding proximity was associated with the outcome. Retrieval still fell short of the trained classifiers at every neighborhood size, and the number of neighbors mattered more than how similarity was weighted. Taken together, these findings suggest that embeddings reorganized useful information already recorded in the EHR; they do not demonstrate a new measure of treatment resistance.

## Comparison With Prior Work

Our discrimination estimates fall within the range reported for structured EHR models, but differences in outcome definition and validation preclude direct performance rankings. Liberman and colleagues reported an internally evaluated ROC AUC of 0.83 over 24 months \[12\], whereas Lage and colleagues reported an externally validated ROC AUC of 0.652 \[13\]. A smaller multimodal study achieved 0.684 with structured EHR data and 0.728 after adding clinical notes \[15\]. In a 3-system study, internal ROC AUCs of 0.58--0.64 declined to 0.51--0.58 under external validation \[14\].

The present contribution is the direct comparison of practical representation pipelines under a shared cohort, prediction time, and test split. It does not set a performance ceiling for EHR prediction. Adding independently informative measurements may improve prediction, as may better outcome ascertainment. Re-encoding existing records should therefore be judged by incremental performance, reproducibility, and implementation burden rather than model size alone.

## Clinical Interpretation and Limitations

The main limitation is the target. Repeated antidepressant switching can reflect inadequate response, but also tolerability, preference, clinician behavior, and access. The study did not verify failed adequate trials or symptom trajectories, and the index prescription was not necessarily a patient's first antidepressant exposure. The results therefore need to be seen as focused on subsequent treatment switching in patients with recorded depression, not necessarily confirmed incident TRD. Future investigations with access to unstructured elements of the EHR record may need to examine more variation across EHR definitions since they may have considerable effects on what the label represents \[9-11\].

There are several noteworthy limitations. Temporal separation of predictors and outcome reduces direct leakage from future treatment history. However, it does not necessarily remove selection or observation bias. Eligibility required subsequent follow-up, the source extract excluded patients recorded as deceased at extraction, and care outside the system could be missed. The single-system, depression-enriched sample and random internal validation also limit transportability and the interpretation of absolute risk.

The minimal change after race/ethnicity or social-determinant permutation is useful but does not establish fairness. These fields may be incompletely recorded, related information may remain in other predictors, and the outcome depends on access to treatment \[28,29\]. The subgroup analyses were limited by small event counts and broad racial aggregation, with unresolved differences in discrimination and calibration. Similarly, concept permutation measures sensitivity to altered inputs rather than a causal contribution; correlated fields and implausible combinations after permutation limit attribution.


## Implications and Next Steps

The current findings are useful, but the results do not support clinical deployment. The next steps are to validate the switching phenotype against treatment histories and symptom change, then evaluate frozen pipelines in temporal and external cohorts. Evaluation should compare embeddings with compact psychiatric-history, medication, and utilization baselines and report precision--recall performance, individual-level calibration, subgroup errors, and decision-analytic net benefit at prespecified thresholds. However, for an embedding pipeline to justify its added complexity, it should improve prediction, transportability, or clinical workflow beyond a simpler model. It is also possible that a more clinically informative prediction target may be as impactful for future investigations as a more elaborate representation of the case embedding.

## Conclusions

At the index antidepressant prescription, structured feature vectors and narrative embeddings provided modest discrimination for a subsequent treatment-switching proxy for TRD, without demonstrated superiority of the strongest embedded model. Performance depended on the classifier. Progress toward clinical use requires better validation of the outcome and evidence that prediction improves decisions across patients and health systems.

# Acknowledgments

ChatGPT (OpenAI) assisted with language editing and organization of the manuscript and supplement. The authors are responsible for the final content.

# Funding

This work was funded by the William K. Warren Foundation. No other funding agency in the public, commercial, or not-for-profit sectors supported this research. M. Ferguson was supported by a graduate assistantship from the Laureate Institute for Brain Research while enrolled as a graduate student at The University of Tulsa. The funder had no role in the design of the study, the analysis or interpretation of the data, the writing of the manuscript, or the decision to submit it for publication.

# Conflicts of Interest

None declared.

# Data Availability

The EHR data cannot be shared publicly. Analysis code is available at https://github.com/Pirate-Hunter-Zoro/TRD-EHR. Fitted model objects are not distributed because they are derived from nonshareable patient data.

# Authors Contributions

MF designed and implemented the analysis pipeline, performed all modeling and statistical analysis, produced the figures and tables, and wrote the manuscript. MP directed the project and supervised its scientific design and interpretation. KLF prepared the upstream clinical data, including the treatment-resistant depression labels and the antidepressant index dates that define the cohort and the outcome. RK, SS, and DP provided methodological feedback and guidance on the analysis and its interpretation throughout. All authors reviewed and approved the final manuscript.

# Protocol and Registration

No study protocol was prepared, and the study was not registered. The completed TRIPOD+AI checklist is provided as a separate submission document \[19\].

# Abbreviations

AUPRC: area under the precision--recall curve

EHR: electronic health record

MDD: major depressive disorder

ROC AUC: area under the receiver operating characteristic curve

TRD: treatment-resistant depression

TRIPOD+AI: Transparent Reporting of a Multivariable Prediction Model for Individual Prognosis or Diagnosis plus Artificial Intelligence

# Multimedia Appendix 1

Supplementary methods, predictor inventory, supporting analyses, and extended results for the comparison of structured feature vectors and narrative embeddings.

# References

1\. Gaynes BN, Lux L, Gartlehner G, Asher G, Forman-Hoffman V, Green J, et al. Defining treatment-resistant depression. Depress Anxiety. 2020;37(2):134-145. doi:10.1002/da.22968.

2\. Rush AJ, Trivedi MH, Wisniewski SR, Nierenberg AA, Stewart JW, Warden D, et al. Acute and longer-term outcomes in depressed outpatients requiring one or several treatment steps: a STAR\*D report. Am J Psychiatry. 2006;163(11):1905-1917. doi:10.1176/ajp.2006.163.11.1905.

3\. Al-Harbi KS. Treatment-resistant depression: therapeutic trends, challenges, and future directions. Patient Prefer Adherence. 2012;6:369-388. doi:10.2147/PPA.S29715.

4\. Perlis RH. A clinical risk stratification tool for predicting treatment resistance in major depressive disorder. Biol Psychiatry. 2013;74(1):7-14. doi:10.1016/j.biopsych.2012.12.007.

5\. Kautzky A, Baldinger-Melich P, Kranz GS, Vanicek T, Souery D, Montgomery S, et al. A new prediction model for evaluating treatment-resistant depression. J Clin Psychiatry. 2017;78(2):215-222. doi:10.4088/JCP.15m10381.

6\. Sheu YH, Magdamo C, Miller M, Das S, Blacker D, Smoller JW. AI-assisted prediction of differential response to antidepressant classes using electronic health records. npj Digit Med. 2023;6:73. doi:10.1038/s41746-023-00817-8.

7\. Chekroud AM, Zotti RJ, Shehzad Z, Gueorguieva R, Johnson MK, Trivedi MH, et al. Cross-trial prediction of treatment outcome in depression: a machine learning approach. Lancet Psychiatry. 2016;3(3):243-250. doi:10.1016/S2214-0366(15)00471-X.

8\. Chekroud AM, Bondar J, Delgadillo J, Doherty G, Wasil A, Fokkema M, et al. The promise of machine learning in predicting treatment outcomes in psychiatry. World Psychiatry. 2021;20(2):154-170. doi:10.1002/wps.20882.

9\. Cepeda MS, Reps J, Fife D, Blacketer C, Stang P, Ryan P. Finding treatment-resistant depression in real-world data: how a data-driven approach compares with expert-based heuristics. Depress Anxiety. 2018;35(3):220-228. doi:10.1002/da.22705.

10\. Fabbri C, Hagenaars SP, John C, Williams AT, Shrine N, Moles L, et al. Genetic and clinical characteristics of treatment-resistant depression using primary care records in two UK cohorts. Mol Psychiatry. 2021;26(7):3363-3373. doi:10.1038/s41380-021-01062-9.

11\. Iveson MH, Ball EL, Lo CWH, Falis M, Lewis CM, Whalley HC. Treatment resistant depression in electronic health records: definitions matter. BMC Psychiatry. 2026;26(1):453. doi:10.1186/s12888-026-08085-y.

12\. Liberman JN, Davis T, Pesa J, Chow W, Verbanac J, Heverly-Fitt S, et al. Predicting incident treatment-resistant depression: a model designed for health systems of care. J Manag Care Spec Pharm. 2020;26(8):987-995. doi:10.18553/jmcp.2020.26.8.987.

13\. Lage I, McCoy TH, Perlis RH, Doshi-Velez F. Efficiently identifying individuals at high risk for treatment resistance in major depressive disorder using electronic health records. J Affect Disord. 2022;306:254-259. doi:10.1016/j.jad.2022.02.046.

14\. Walsh CG, Ripperger M, McCoy TH, Castro V, Hu Y, Kirchner HL, et al. Generalizability of risk models for treatment-resistant depression across three health systems. medRxiv. 2025. Preprint. doi:10.1101/2025.05.21.25328089.

15\. Lee DY, Kim N, Park C, Gan S, Son SJ, Park RW, et al. Explainable multimodal prediction of treatment-resistance in patients with depression leveraging brain morphometry and natural language processing. Psychiatry Res. 2024;334:115817. doi:10.1016/j.psychres.2024.115817.

16\. Hegselmann S, von Arnim G, Rheude T, Kronenberg N, Sontag D, Hindricks G, et al. Large language models are powerful electronic health record encoders. arXiv:2502.17403. 2025.

17\. Shmatko A, Jung AW, Gaurav K, Brunak S, Mortensen LH, Birney E, et al. Learning the natural history of human disease with generative transformers. Nature. 2025;647(8082):248-256. doi:10.1038/s41586-025-09529-3.

18\. Waxler S, Blazek P, White D, Sneider D, Chung K, Nagarathnam M, et al. Generative medical event models improve with scale. arXiv. 2025;arXiv:2508.12104. doi:10.48550/arXiv.2508.12104.

19\. Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ. 2024;385:e078378. doi:10.1136/bmj-2023-078378.

20\. Forthman KL, Kuplicki R, Thompson WK, Nemeroff CB, Si Y, Fan CC, et al. Treatment resistant depression: socio-demographic characteristics, comorbidity and treatment patterns from the All of Us Research Program. J Affect Disord. 2025;390:119858. doi:10.1016/j.jad.2025.119858.

21\. Hegselmann S, Shen SZ, Gierse F, Agrawal M, Sontag D, Jiang X. A data-centric approach to generate faithful and high quality patient summaries with large language models. Proc Mach Learn Res. 2024;248:339-379.

22\. Reimers N, Gurevych I. Sentence-BERT: sentence embeddings using Siamese BERT-networks. In: Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP); 2019 Nov; Hong Kong. Stroudsburg (PA): Association for Computational Linguistics; 2019. p. 3982-3992. doi:10.18653/v1/D19-1410.

23\. Xiao S, Liu Z, Zhang P, Muennighoff N, Lian D, Nie JY. C-Pack: packed resources for general Chinese embeddings. In: Proceedings of the 47th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR '24); 2024 Jul 14-18; Washington (DC). New York: ACM; 2024. p. 641-649. doi:10.1145/3626772.3657878.

24\. Li C, Qin M, Xiao S, Chen J, Luo K, Shao Y, et al. Making text embedders few-shot learners. arXiv:2409.15700. 2024.

25\. Zhang Y, Li M, Long D, Zhang X, Lin H, Yang B, et al. Qwen3 embedding: advancing text embedding and reranking through foundation models. arXiv:2506.05176. 2025.

26\. Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O, et al. Scikit-learn: machine learning in Python. J Mach Learn Res. 2011;12:2825-2830.

27\. Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16); 2016 Aug 13-17; San Francisco (CA). New York: ACM; 2016. p. 785-794. doi:10.1145/2939672.2939785.

28\. González HM, Vega WA, Williams DR, Tarraf W, West BT, Neighbors HW. Depression care in the United States: too little for too few. Arch Gen Psychiatry. 2010;67(1):37-46. doi:10.1001/archgenpsychiatry.2009.168.

29\. Alegría M, Chatterji P, Wells K, Cao Z, Chen CN, Takeuchi D, et al. Disparity in depression treatment among racial and ethnic minority populations in the United States. Psychiatr Serv. 2008;59(11):1264-1272. doi:10.1176/ps.2008.59.11.1264.
