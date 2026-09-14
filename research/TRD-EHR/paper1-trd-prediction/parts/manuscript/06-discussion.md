<!--
Section 6 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Discussion
-->

# Discussion

## Principal findings

**The embedding did not beat the feature vector.** Embedded logistic
regression reached 0.657 against 0.649 for the best feature-vector
model. Both scored the same held-out patients, so the paired comparison
is the one that counts: +0.008, on an interval from −0.003 to +0.019.
Neither representation is better than the other. Both were built from
the same hand-picked record, which Supplement S8 lists field by field,
so this says nothing about whether narrative adds clinical information.
It says an embedding can reorganize the same signal without losing
discrimination, and it says nothing about what an encoder would find in
a raw record.

Three results point the same way. The ablation traces the embedded
model's reliance to psychiatric history, medication burden and prior
treatment exposure, which are the domains carrying the largest
feature-vector weights. The embedded model uses 385 of 4,096 dimensions,
with 80% of the coefficient magnitude in roughly 179 of them. And
discrimination stays within 0.012 across four encoders.

**It is an interaction, not a tie.** The embedding beat the feature
vector with logistic regression (+0.028) and lost to all three tree
ensembles (−0.013 to −0.022). Dense coordinates suit a regularized
linear model. Trees split one coordinate at a time, and those
coordinates mean nothing on their own. A study comparing representations
under a single learner could report either result, depending on which
learner it picked.

**Retrieval works, and loses.** Nearest retrieval discriminated far
better than random on every encoder, so proximity in the embedding
tracks TRD risk. It still fell 0.063 short of a model fitted to the same
embedding, on intervals that do not overlap, and below all eight trained
configurations. Averaging the outcomes of a patient's 50 closest
analogues is a worse use of the representation than fitting a model to
it.

Two things cause that gap. A fitted model can ignore the dimensions
carrying no outcome signal, which is what selecting 385 of 4,096 does,
whereas cosine similarity weights all 4,096 equally. And 50 neighbors
is a noisy way to estimate a rate near 0.175, however well they are
chosen. The first points toward a similarity learned against the
outcome. The second is a variance cost retrieval always pays.

## Clinical interpretation

The strongest feature-vector predictors are the ones a clinician would
expect: a history of suicidality, severe MDD coding, and broad
psychiatric and substance-use comorbidity. The ablation lands on the
same domains. That is reassuring for face validity and nothing more,
because every one of those predictors can equally reflect how much treatment a patient was able to get. That matters because the outcome is a treatment trajectory, not a
verified failure to respond. Definitions of EHR-defined TRD differ in
what they count, and the choice changes both how common it looks and who
ends up in the group [6-8].

The temporal design is a real strength. Every predictor was fixed before
the index prescription and the treatment sequence defining the outcome
came afterward. That is what stops a model from reconstructing the
outcome rule out of data recorded alongside it, which is the mechanism
suspected behind the sharp external-validation drops reported elsewhere
[12].

The sociodemographic ablation needs the same reading. It shows the
models did not need the recorded race/ethnicity and social-determinant
fields to reach their ROC AUC. It does not show the prediction pathway
is demographically neutral. Utilization and treatment variables can
carry differential access, and the chance to receive several medication
changes is itself socially patterned.

## Comparison with prior work

Reported discrimination for treatment resistance varies widely, and 0.65
is not a ceiling [18-21,30]. What moves it is the phenotype definition, the
prediction horizon, how close the predictors sit to the treatment
trajectory, and whether validation is internal or external. Liberman and colleagues
reached 0.83 over 24 months
in 35,246 adults, on predictors that mix illness burden with the
intensity of care received [9]. Lage and colleagues reported 0.652 (95%
CI 0.623–0.682) under external validation, with a top-quintile lift of
1.99 [10]. A single-site multimodal study reported 0.684 from structured
data, 0.569 from notes and 0.728 from the two combined, with MRI highest
[11].

Transportability is the harder constraint. Across three health systems,
internal ROC AUCs of 0.58–0.64 fell to 0.51–0.58 under external
validation, and patient-level risk estimates agreed poorly between sites [12]. The 0.65 reported here sits with the externally validated and
single-site structural estimates. It is neither a new ceiling nor an
improvement on any of them [9-12]. What this study contributes is the
controlled comparison: the same patients, cutoff, source record, outcome
and held-out split. Within it, the embedding preserved the signal a
transparent feature vector already carried, and did not exceed it.

## Limitations

<!-- RESTORED 2026-09-06. This section was removed on 2026-09-03 to match the
     senior author's supplied Discussion, which has none, and was held whole in
     reserve/limitations_reserve.md. It is back on the user's explicit
     instruction. It gained one item the earlier version did not have, on the
     retrieval arm, because retrieval is now one of the paper's two main
     points and its own boundaries have to be stated. Every item carries its
     sources. Do not remove this section again without recording the decision
     in the reserve document. -->

**The outcome counts switches, and cannot see why a switch happened.**
This is the binding limitation on everything above. The label is
assigned when a patient receives three or more distinct antidepressant
treatments within a year [2], and nothing in the record says whether
the change followed a genuine failure to respond. A patient is switched because the
drug did not work, or because it caused intolerable side effects, or
because it was unaffordable, or because they stopped taking it, or
because their prescriber prefers switching to augmenting. All of these increment the count identically,
and this study cannot distinguish them. Symptom response was not systematically recorded, and dose and duration
adequacy were not verified for the counted treatments. The target therefore
approximates rather than establishes the consensus characterization of TRD as
inadequate response to at least two adequate trials [4,5].

Switching also
depends on continuity of care, insurance, and access. Those differ across
demographic groups in the delivery of depression treatment in the United States
[16,17], so the label can encode health-care process alongside pharmacologic
non-response. Changing the operational rules materially alters both prevalence
and cohort composition [6-8].

The proxy is wrong in two directions. It counts patients who changed
drugs for reasons that have nothing to do with whether the drug worked,
such as a change in insurance or a break in care. It misses patients who
stayed on one inadequate drug and never switched, and that is the group
a clinician would worry about most. This study cannot see them at all.
Both arms predict the same imperfect label, so the head-to-head
comparison is not biased by it. What it costs is the meaning of the
absolute number, which is discrimination against the proxy rather than
against TRD. Two things would sharpen the target and neither was done
here: checking the label against chart review, and building a stricter
label that requires documented adequate courses after the index date.

**Validation is internal, and the reported discrimination is an upper
bound.** This is a single random split of one health system's records
spanning 2016–2024. There is no temporal split and no external cohort,
so nothing here speaks to transportability across time or site. The
study also cannot detect the coding, documentation, and prescribing
drift that accumulates over a nine-year window, because a random split
distributes any such drift evenly across both sides and hides it.
Reported discrimination should therefore be read as an upper bound on
what the same models would achieve on later data or in another system.
The drop seen elsewhere under external validation is substantial [12]. By construction the embedded representation also runs below the
conventional events-per-variable threshold of 10 on three of the four
encoders (EPV ≈ 1.5–2.3), whereas the feature-vector model comfortably
exceeds it at ≈65.

**Retrieval was tested in one form.** The retrieval result bounds the
digital-twin premise as implemented here, not the premise in general.
Similarity was geometric cosine similarity over an unsupervised
embedding, the neighborhood was fixed at 50 patients, and the neighbor
pool was the training half of a single cohort. A supervised or
metric-learned similarity, a different neighborhood size, a
prevalence-recalibrated local estimate, or a neighbor pool drawn from
several health systems could each perform differently, and none was
tested. What the present analysis supports is narrower and still substantive. On
this cohort, an unsupervised embedding whose geometry demonstrably
tracks the outcome still yields a retrieval predictor that a fitted
model beats decisively.

**Absence of an advantage is not equivalence.** No equivalence or
noninferiority margin was prespecified. The correct statement is that
this study found no evidence of superior internal discrimination for the
embedding, bounded above by +0.019 ROC AUC, the upper end of the paired
interval. It is not that the two representations are equivalent.

What the embedding does offer is that it cost no discrimination, needed
no explicit feature vector, and held across encoders. That is not a free
lunch. It still depends on
the hand-built deterministic narrative, which required the same parsing
and structuring of the raw record. The engineering effort
is relocated from designing a feature vector to designing a narrative
template rather than eliminated.

**Missing data were dropped rather than modeled.** The three vital-sign columns were removed rather than imputed, because
whether a vital sign was recorded is itself associated with the outcome.
That rules out missingness completely at random without identifying the
mechanism, so dropping the columns is conservative rather than
justified. It costs three genuinely clinical predictors. It also
discards signal the rest of the pipeline keeps: an absent categorical
value becomes its own level in the feature vector, so a model can use
the fact that a record is missing. Missingness in religion and
race/ethnicity is likewise associated with the outcome, and Supplement
M6 has the frequencies and the retained-category rules. The vitals are
the one place this paper throws that signal away.

**This study reports no fairness evidence.** The ablation establishes
only that neither model's predictions rely on the race/ethnicity and
social-determinant fields supplied directly to it. Three questions
remain open. Sociodemographic information may still reach the models
indirectly through correlated psychiatric, medication, or utilization
content. The outcome label is derived from prescribing behavior and may
itself be inequitably distributed, given documented racial and ethnic
disparities in the delivery of depression treatment [16,17]. And age,
sex, preferred language, marital status, religion, and smoking status
remain in both representations and were never permuted. The subgroup
evidence does not return a uniform null: sex shows no difference
anywhere, whereas the White-minus-non-White contrasts are directionally
positive throughout without surviving correction, and non-White
calibration is materially worse in the feature-vector arm.

This cohort cannot settle whether there is a race-associated gap, in
either direction. The reason is sample size: the non-White stratum
carries 302 TRD events against 1,181, so every contrast involving it has
an interval about twice as wide. Individual race categories carry too
few events to estimate at all, which is why the analysis compares White
against everyone else. The groups where a disparity would be most likely
to appear are the ones that disappear into that single comparison.

**The cohort is one community health system.** It skews middle-aged and
older (34.7% aged 65 or over), predominantly female (72.5%),
overwhelmingly White (80.0%) and English-preferring (98.9%). Both the
single-center design and that demographic profile limit transfer to more
diverse or non-English-preferring populations and to health systems
whose case mix or prescribing culture differs. Because the index
prescription can be written anywhere in the system rather than in
specialty psychiatric care, the cohort is also weighted toward routine
rather than referred management.

**The ablation perturbs one concept at a time.** It therefore cannot
disentangle co-correlated clinical content without joint perturbation,
and prior treatment exposure and medication burden are the two concepts
most likely to share contribution. It also cannot rule out
reconstruction of a permuted concept from correlated fields left intact.

**The operating point and the calibration are both optimistic.** The
Youden-J threshold was selected on the same held-out patients the models
were then scored on, so the reported sensitivity and specificity are not
candidate operating characteristics. Calibration was measured inside a case-enriched sample. Its 17.5% TRD
rate was chosen by the sampling design and is not what a clinic would
see, so a predicted risk from these models is a risk relative to this
cohort. Applying them anywhere else would need the probabilities
rescaled to that population's own rate.

## Implications and future directions

At 0.65, none of this is ready for the clinic. The next study should
validate externally, across sites and forward in time, with the whole
pipeline frozen, and should report calibration and decision-curve
analysis rather than discrimination alone. This cohort was
case-enriched, so absolute risks need rescaling before they mean
anything clinically.

Incremental value should be tested against simple baselines, not only
against other architectures. The comparators that matter are outcome
prevalence, age and coded severity, prior medication history, and a
compact set of comorbidity and utilization variables. An embedding earns
its place only if it improves transportability, calibration or net
benefit beyond those.

Three experiments follow from what is reported here. Embed an untailored
record, which tests whether an encoder finds TRD-relevant structure
without being told where to look. The obstacle there is input length: predictors here come from a fixed
730-day window, whereas recorded history reaches a median of 1,792 days
and a maximum of 5,288 across a median of 21 encounters. Every way
around that reintroduces a design decision, which is itself worth
reporting. Learn a similarity against the outcome, or draw
neighbors from several health systems, and see whether retrieval closes
the 0.063 gap. And validate the target itself, by chart adjudication and
symptom measurement, to find out how often a treatment switch means a treatment failed. Until that is done, the defensible use is research-stage cohort enrichment, not treatment selection.

One thing retrieval offers that a fitted model does not is that its
neighbors are real patients with observed courses. Whether that is
worth 0.063 ROC AUC is a question about clinical workflow rather than
discrimination, and it needs a different study. The feature vector's
explicit treatment-exposure variables also make a different question
tractable: which patients benefit from which next step, rather than who
becomes resistant. That is ongoing work.

## Conclusions

Writing a structured EHR out as text and embedding it with a general-purpose
transformer extracted the same predictive signal as a typed feature vector
built from the same record, and no more of it. The embedding's contribution was
reorganization rather than discrimination, and its apparent advantage or
disadvantage depended entirely on which classifier was applied to it.

Predicting a patient from the recorded outcomes of their nearest neighbors
recovered part of that signal and still lost decisively to a model fitted on
the same embedding, on every encoder tested. The digital-twin premise in its
unsupervised geometric form is therefore not competitive here.

Both results rest on hand-picked patient data. Predictor selection ran once and
served both arms, so the engineering was relocated rather than removed, and
neither result is evidence about what a model would do with a raw record.
Embedding a whole untailored history was not attempted because record length
stands in the way, and that experiment remains the interesting one.

Nothing here is close to clinical utility at a ROC AUC near 0.65, and
the outcome is a treatment-switch pattern whose relationship to verified
non-response is untested. Three things would decide whether any of it
matters. The first is whether the signal survives in another health
system. The second is whether it beats a simple baseline built from care
history alone. The third is whether it finds patients whose symptoms
were measured and did not improve, rather than patients whose path
through the system was shaped by insurance, access and prescribing
habit.
