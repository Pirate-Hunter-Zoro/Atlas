<!--
Section 21 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S7 Record Length and Prediction
-->

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
