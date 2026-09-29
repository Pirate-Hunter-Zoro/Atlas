<!--
Section 7 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M6 Missing Data
-->

# M6 Missing Data

No statistical imputation was performed. Mean body mass index and mean systolic and diastolic blood pressure were present in the intermediate feature file but removed from the FEATURE matrix at load time. Each value is the within-patient mean across that patient's own pre-index encounters, not a mean across patients. Mean body mass index was missing for 22.1% of patients, and at least one vital sign was absent for 21.0%. Body mass index was missing for 28.8% of TRD-positive and 20.6% of TRD-negative patients, an approximately 8-percentage-point difference.

Outcome-associated missingness argues against missing completely at random but does not establish missing not at random. The primary FEATURE analysis excluded the vital signs without imputation or continuous missingness indicators. A sensitivity analysis retaining them with missingness indicators and within-fold median imputation was reported to leave the best-model comparison nonsignificant. Quantitative results are not included here and are available from the corresponding author.

FEATURE encoded missing categorical values as separate levels. Narratives generally used "Missing," with field-specific exceptions documented in section S10. Marital and smoking status were less than 0.5% missing. Religion was missing in 29.4% overall, ranging from 43.8% at ages 18--29 to 17.5% at age 65 or older. A sensitivity analysis removing religion from both pipelines was reported to yield paired discrimination CIs including zero; quantitative results are available from the corresponding author.
