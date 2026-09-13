<!--
Section 2 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M2. Eligibility cascade, index selection, and temporal design
-->

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
