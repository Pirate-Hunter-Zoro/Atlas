<!--
Section 17 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S4. Example patient narratives
-->

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
