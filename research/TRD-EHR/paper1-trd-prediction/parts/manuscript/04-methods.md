<!--
Section 4 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Methods
-->

# Methods

## Study Design and Data Source

We conducted a retrospective cohort study using a frozen, deidentified Epic EHR extract from Saint Francis Health System in Tulsa, Oklahoma. The extract contained 501,718 patients and included diagnoses, encounters, medications, procedures, and laboratory data. The extract combined 2 groups: every patient with a depression flag on the problem list (100,420, 20.0%) and a random sample of patients without that flag (401,298, 80.0%). Eligibility was then decided from diagnoses recorded at encounters, not from the flag. Some patients in the random sample therefore qualified: 12,530 of the 42,579 eligible patients (29.4%, 95% CI 29.0--29.9) had no depression flag. Because every flagged patient was kept, the sample over-represents depression, and its outcome frequency is not the health system's.

We used data version DV260629v1 and patient version PV260710v1, extracted on June 29, 2026, and processed on July 10, 2026. Index dates spanned 2013--2025. Evaluation used a random internal split from the same source and period. Source definitions and sampling details are provided in Multimedia Appendix 1, sections M1--M2. We used TRIPOD+AI to guide reporting \[19\].

## Participants and Prediction Time

Eligible patients met the study's coded depression definition, had no bipolar or schizophrenia-spectrum diagnosis, had an antidepressant index prescription on or after a documented depression diagnosis, and had at least 730 days of prior history and 365 days of subsequent follow-up. The depression code set included major depressive disorder (MDD), dysthymia, and unspecified depression. The final cohort included 42,579 patients; the eligibility cascade and code lists appear in Multimedia Appendix 1, sections M1--M2.

The index was the earliest recorded antidepressant prescription on or after the first documented depression diagnosis. It was not necessarily the first lifetime exposure: prior antidepressant use was retained as a predictor. The index was chosen without looking at anything after it, such as later dose, duration, response, or switching. Clinical content was restricted to the 730-day window ending on the index date; total recorded pre-index history length was an additional duration variable. Post-index information established follow-up eligibility and the outcome (Figure 1).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/time_zero_timeline.png){width=6in}

***Figure 1.** Prediction time and observation windows. The index is the earliest antidepressant prescription on or after the first recorded depression diagnosis. Clinical content comes from the preceding 730 days through the index date. Total recorded pre-index history length is a separate duration predictor and can exceed this window. The subsequent 365 days establish follow-up eligibility and the treatment-switching outcome. For 25,645 of the 42,579 patients (60.2%, 95% CI 59.8--60.7), the index prescription was written on the same day as the first depression diagnosis. EHR: electronic health record; MDD: major depressive disorder; TRD: treatment-resistant depression proxy.*

## Outcome

The prespecified outcome was a treatment-switching proxy for TRD, generated upstream and supplied as a fixed label \[20\]. Patients were positive if they received at least 3 distinct antidepressant treatments within 365 days, counting the index agent first. This required at least 2 subsequent changes to distinct agents. Augmentation without replacement and restarting a previously used agent did not increase the count.

The outcome did not verify inadequate response to 2 adequate trials. No symptom rating scale, such as the PHQ-9, was available to show whether a patient improved. We also could not tell whether each counted treatment was given at an adequate dose for long enough. Switching could reflect nonresponse, intolerance, preference, access, or prescribing practice. Switching also depends on access to care, and in the United States access to depression treatment differs by race and ethnicity. A patient with poor access has fewer chances to switch, so is less likely to be labeled positive, whatever their illness. The label was not checked against charts or symptom scores (Multimedia Appendix 1, section M3). We therefore call the outcome a "TRD proxy" rather than TRD.

## Patient Representations and Missing Data

Predictor domains were selected before model fitting or examination of outcome associations. They included depression coding, psychiatric and medical comorbidity, prior treatment, medication burden, utilization, prescribing constraints, and sociodemographic characteristics \[4-7\]. The structured representation (FEATURE) comprised 92 encoded columns. Continuous variables were standardized, categorical variables were one-hot encoded, and binary variables were coded as 0 or 1. A prior antidepressant trial was counted when the patient was on the drug for at least 42 continuous days. The rule counts time on the drug only, not dose.

For the embedded representation (EMBEDDED), fixed rules converted structured fields into Markdown narratives. No generative model wrote the narratives, preserving traceability to the source fields \[21\]. We evaluated bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, and Qwen3-Embedding-8B; the last was the primary encoder \[22-25\].

The pipelines differed in information content. Narratives retained vital signs, individual medication names, index dates, sexual orientation, and finer sociodemographic categories; FEATURE included total recorded history length, which the narratives omitted. Missing vital signs were excluded from FEATURE, and no statistical imputation was used in the primary analysis. Missing categorical information was represented explicitly, although some narrative fields retained raw missing-value tokens. Encoding rules, the predictor inventory, example narratives, and the field crosswalk are provided in Multimedia Appendix 1, sections M4--M6, S5, and S10.

## Model Development and Evaluation

All models used one stratified 80:20 split: 34,063 training patients, including 5,964 outcome-positive patients, and 8,516 test patients, including 1,491 outcome-positive patients. We fitted logistic regression, random forest, gradient boosting, and XGBoost to each representation. Five-fold cross-validated grid search optimized ROC AUC within the training set. No resampling, class weighting, or other class-imbalance method was used. Scaling and category encoding were fitted within each training fold; the selected pipeline was then refitted on all training patients and applied to the test set. Each classifier searched the same hyperparameter grid for both representations, and the best setting was chosen separately for each, so the selected hyperparameters could differ (Multimedia Appendix 1, sections M7--M9).

We assessed ROC AUC, area under the precision--recall curve (AUPRC), Brier score, and calibration. All calibration estimates concern this enriched cohort.

95% CIs came from resampling the test patients with replacement (the bootstrap). A difference between 2 models used the same resampled patients for both, which is called a paired bootstrap. We compared the representations in 2 ways. First, each classifier on embeddings was compared with the same classifier on feature vectors. Second, the best embedded model was compared with the best feature-vector model. Those 2 models were picked after seeing their test results, so the second comparison was not planned in advance. We set no margin for calling 2 models equivalent, so an interval that includes zero means no difference was found, not that the models are the same. Sensitivity and specificity at the threshold that maximized their sum in the test patients are given in Multimedia Appendix 1, section S12, as descriptions only.

## Supporting Analyses

We examined embedded-model reliance on 6 concepts by permuting one narrative section or field across patients, re-embedding the narratives, and applying the original classifiers without retraining. The concepts were psychiatric history, medication burden, prior treatment exposure, prescribing contraindications, race/ethnicity, and social determinants of health. Change in ROC AUC measures reliance under the specified perturbation; it does not identify causal mechanisms or establish fairness.

We also predicted each test patient's outcome from its nearest training-set neighbors. Test patients served only as queries. The risk score was the similarity-weighted mean outcome of the k most similar training patients (Equation 2). Similarity was measured in 2 ways. Plain cosine similarity used the raw embeddings. Logistic-regression-weighted cosine similarity first standardized each embedding dimension with the embedded logistic regression's own scaler. It then weighted each dimension by its share of that model's absolute coefficients (Equation 1). The coefficients were fitted on training patients only, so no test outcome entered a risk score.

$$\mathrm{sim}_w(x,y)=\frac{\sum_d w_d\,z_d(x)\,z_d(y)}{\sqrt{\sum_d w_d\,z_d(x)^2}\,\sqrt{\sum_d w_d\,z_d(y)^2}},\qquad w_d=\frac{|\beta_d|}{\sum_e |\beta_e|}\qquad(1)$$

$$\hat{r}(x)=\frac{\sum_{i\in N_k(x)} s_i^{\alpha}\,y_i}{\sum_{i\in N_k(x)} s_i^{\alpha}},\qquad s_i=\max\{\mathrm{sim}(x,i),0\}\qquad(2)$$

Here $z_d$ is dimension $d$ after standardization, $\beta_d$ is its logistic-regression coefficient, $N_k(x)$ is the set of the $k$ most similar training patients, $y_i$ is a neighbor's outcome, and $\alpha$ is a sharpening exponent. Plain cosine similarity is Equation 1 with raw embeddings and equal weights. Neighbors were chosen in 2 ways, nearest and random. Random retrieval averaged the outcomes of k training patients drawn at random, with equal weights, in 1,000 seeded draws; its interval is the 2.5th to 97.5th percentile across draws. Both were scored at every k from 1 to all 34,063 training patients, nearest retrieval under α = 1, 2, and 5. Each retrieval arm, the 2 nearest-neighbor metrics and random retrieval, therefore yields a curve over k, not a value at one k. Where a single value is reported, including the ROC curves and confusion matrices, it is at the arm's best k, the k with the highest ROC AUC in the test patients. Because that k was chosen on the test patients, these values are optimistic. Details appear in Multimedia Appendix 1, sections M10--M12 and S6.

Additional analyses examined encoder robustness, model dimensionality, record length, and subgroup performance. Subgroup comparisons used held-out predictions without refitting and Benjamini--Hochberg adjustment across 240 contrasts. Full methods and results appear in Multimedia Appendix 1. All random processes were seeded; analyses used Python, scikit-learn, XGBoost, and sentence-transformers \[22,26,27\].

## Ethical Considerations

We analyzed deidentified secondary records without direct identifiers. No institutional review board review or consent waiver was obtained because the study was considered not to involve human participants. All analytic computation, including embedding, ran on local institutional hardware; patient-level analytic data were not transmitted to external services. No patients or members of the public participated in the design, conduct, or reporting of the study.
