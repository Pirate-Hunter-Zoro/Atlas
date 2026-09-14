<!--
Section 3 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M3. Outcome construction and inferential boundary
-->

# Supplement M3. Outcome construction and inferential boundary

The binary outcome was generated in the upstream R data-preparation pipeline
independently of the predictors and supplied to the modeling workflow as a
fixed label. TRD was assigned when a patient with MDD received at least three
distinct antidepressant treatments within 365 days of the index date, the
index agent counting as the first. Patients with fewer than three treatments
were classified TRD-negative.

A treatment is a distinct antidepressant agent rather than an order or
prescribing event. Addition of a second agent while the current
antidepressant continues is augmentation and does not advance the outcome
count. Restarting a previously used agent also does not advance it.
Augmentation is available as a pre-index predictor where its definition is
met.

The 365-day follow-up requirement ensures that every patient has the
observation window needed to determine the label, so a negative label
reflects an absence of further antidepressant treatments rather than an
absence of observation. It does not guarantee that care delivered outside
the health system was captured.

The label approximates, but does not establish, the consensus
characterization of TRD as inadequate response to at least two antidepressant
trials of adequate dose and duration [4,5]. Non-response is inferred from
switching rather than measured, because standardized symptom severity is not
systematically recorded in this extract. Dose and duration adequacy were not
verified for the counted post-index treatments. Changes attributable to
intolerance, adverse effects, cost, formulary restriction, fragmented care,
patient preference, or prescriber practice are therefore counted in the same
way as changes attributable to non-response. Switching also depends on
continuity, access, insurance, and clinical practice, which may differ across
demographic groups [16,17], so the target can encode health-care process and
inequity in addition to pharmacologic non-response. The label was not
validated against chart review or a symptom-severity criterion. Future
validation should compare it with adjudicated treatment histories and symptom
trajectories, and should test a higher-specificity outcome requiring
documented adequate courses.
