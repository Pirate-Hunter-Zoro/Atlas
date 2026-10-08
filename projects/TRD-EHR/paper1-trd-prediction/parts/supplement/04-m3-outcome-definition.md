<!--
Section 4 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M3 Outcome Definition
-->

# M3 Outcome Definition

The binary outcome was generated in the upstream R data-preparation pipeline independently of the predictors and supplied to the modeling workflow as a fixed label. TRD was assigned when a patient with MDD received at least three distinct antidepressant treatments within 365 days of the index date, the index agent counting as the first. Patients with fewer than three treatments were classified TRD-negative.

A treatment is a distinct antidepressant agent rather than an order or prescribing event. Addition of a second agent while the current antidepressant continues is augmentation and does not advance the outcome count; restarting a previously used agent also does not advance it. Augmentation is available as a pre-index predictor where its definition is met.

The follow-up requirement provided a 365-day observation window for outcome ascertainment. It did not ensure complete capture of care, including treatment outside the health system; a negative label therefore indicates that the qualifying sequence was not observed.

The label does not establish inadequate response to at least 2 trials of adequate dose and duration \[1,2\]. Standardized symptom response was unavailable, and adequacy was not verified for counted post-index treatments. Switching could reflect nonresponse, intolerance, cost, formulary restrictions, preference, or clinical practice. It also depends on continuity and access, which differ across demographic groups \[3,4\]. Chart adjudication and symptom trajectories are needed to validate the label, together with sensitivity analyses requiring documented adequate courses.
