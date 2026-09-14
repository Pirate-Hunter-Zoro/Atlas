<!--
Section 6 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M6. Missing-data handling
-->

# Supplement M6. Missing-data handling

No statistical imputation was performed. Mean body mass index and mean
systolic and diastolic blood pressure were present in the intermediate
feature file but removed from the FEATURE representation at load time. Each value is
the within-patient mean across that patient's own pre-index encounters, not a
mean across patients. Mean body mass index was missing for 22.1% of patients,
and at least one vital sign was absent for 21.0%. Body mass index was missing
for 28.8% of TRD-positive and 20.6% of TRD-negative patients, an approximately
8-percentage-point difference.

That association rules out missing completely at random but does not
establish missing not at random, which cannot be identified from observed
data: missingness may depend on health-system contact that the recorded
predictors capture only partly. The variables were removed because no
defensible imputation model was available from the observed predictors alone.
No missingness indicators were created for the continuous block, and no NaN
values reached an estimator. Their removal is stated in the main text, Methods, *Missing data and
sample partition*.

Missing categorical values were encoded as a separate level by the FEATURE
one-hot encoder and as the literal token "Missing" in EMBEDDED. Marital and
smoking status are nearly complete (<0.5% missing). Religion is missing for
29.4% overall and shows a monotone age gradient, from 43.8% at ages 18-29 to
17.5% at ages 65 or older, so the missing-category level itself may carry
age-related information. Religion was retained with that indicator level, so the models can use
the fact of an unrecorded value as well as the recorded ones.
