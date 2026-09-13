<!--
Section 10 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Multimedia Appendix 1. FEATURE predictor inventory
-->

# Multimedia Appendix 1. FEATURE predictor inventory

The FEATURE representation comprises 59 source fields (the
three within-patient mean vital signs having been dropped at load time;
see *Missing data and sample partition*). Quantitative and boolean fields
map one-to-one to model columns. The eight categorical fields are one-hot
encoded (`drop='if_binary'` for the single binary field, all levels
retained otherwise), and five of them carry an additional automatic
"Missing" level for patients with no recorded value. The resulting design
matrix has 92 columns (15 quantitative + 36 boolean + 41 one-hot levels).
Display names are those used in the feature-importance figures.

***Table A1.** Quantitative predictors (15; continuous, standardized).*

| Predictor |
| --- |
| MDD history before index (days) |
| History length (days) |
| Encounter count |
| ED visits (count) |
| Inpatient days before index |
| Age (years) |
| Medications active at index |
| Anti-inflammatories active at index |
| Sleep meds active at index |
| Anxiolytic days before index |
| Bupropion trials (6+ wk) |
| Mirtazapine trials (6+ wk) |
| SNRI trials (6+ wk) |
| SSRI trials (6+ wk) |
| Vortioxetine trials (6+ wk) |

***Table A2.** Boolean predictors (36; cast to 0/1), grouped by block.*

| Block | Predictors |
| --- | --- |
| Clinical flags (3) | MDD in history; Suicidality; Augmentation therapy |
| Psychiatric comorbidities (8) | Adjustment disorder; Anxiety disorder; Dysthymia (chronic depression); Insomnia; OCD; PTSD; Social anxiety disorder; Substance use disorder (any) |
| Medical comorbidities (4) | Chronic pain; Diabetes; High cholesterol; Thyroid disorder |
| Prescribing-constraint / safety (2) | Seizure disorder; Uncontrolled hypertension |
| Substance use disorders (10) | Alcohol; Cannabis; Cocaine; Hallucinogen; Inhalant; Nicotine; Opioid; Other stimulant; Other substance; Sedative/hypnotic |
| Social determinants of health (9) | Education or literacy issue; Employment issue; Housing or financial issue; Legal or criminal issue; Occupational hazard exposure; Family/support group issue; Psychosocial circumstances; Social environment issue; Upbringing issue |

***Table A3.** Categorical predictors (8 fields → 41 one-hot columns).
"Missing" indicates an automatic one-hot level for unrecorded values.*

| Field | One-hot columns | Levels |
| --- | :---: | --- |
| Sex | 1 | Male (Female = reference, dropped) |
| Preferred language | 6 | Asian/Pacific Islander; English; Other; Other Indo-European; Spanish; Missing |
| Marital status | 6 | Divorced; Never married; Married; Separated; Widowed; Missing |
| Religion | 6 | Catholic; Non-Christian; Orthodox; Other/Unknown; Protestant; Missing |
| Smoking status | 4 | Current; Former; Never; Missing |
| Race/ethnicity | 8 | American Indian/Alaska Native; Asian; Black/African American; Hispanic/Latino; Multi-race; Native Hawaiian/Pacific Islander; White/Caucasian; Missing |
| MDD recurrence | 4 | Unspecified; Single episode; Recurrent; Dysthymia (chronic depression) |
| MDD severity | 6 | Unspecified; Mild; Moderate; Severe; Psychotic; Remission |
