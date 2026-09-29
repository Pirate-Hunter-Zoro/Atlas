<!--
Section 19 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S5 Example Patient Narratives
-->

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
