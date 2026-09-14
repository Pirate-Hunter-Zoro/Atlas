<!--
Section 11 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M11. Semantic-feature ablation specifications
-->

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
