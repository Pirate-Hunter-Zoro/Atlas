<!--
TRD prediction from EHR-derived patient representations.
Target venue: JMIR Mental Health. Reporting follows TRIPOD+AI.
Source of truth is this Markdown; the .docx is built, not edited.

============================================================================
THE PAPER MAKES TWO POINTS. EVERYTHING IN IT SERVES ONE OF THEM.
============================================================================

Decided 2026-09-06. This is the rule that governs every other rule below, and
it is the test to apply to any proposed addition. The ladder that enforces it
is Paper-Writer's `gates/ladder.py`; the map it was gated against is
`reserve/point_claim_map.json` and the argument for it is
`review/two_points_rationale.md`.

  POINT 1. A generalized pretrained transformer embedding of a patient
  narrative does NOT significantly outperform a typed feature vector built
  from the same record. Best against best, +0.008 ROC AUC (95% CI -0.003 to
  +0.019).

  POINT 2. Nearest-neighbor retrieval over that embedding -- the digital-twin
  intuition, predicting a patient from their closest analogues -- captures
  real label-informative structure but loses decisively to trained models.
  Nearest 0.594 against random 0.499, and 0.594 against 0.657 for the trained classifier on the same embedding, with confidence intervals that do not overlap.

Every Results subsection is placed under one of the two, and the Discussion
takes them in order. A passage that serves neither does not belong in the main
text; the packet has a `reserve/` folder for finished work that is held back,
and using it is the normal outcome rather than a failure.

THE EMPHASIS THAT RUNS THROUGH BOTH, AND IS NOT A THIRD POINT. In both arms
the patient data were HAND-PICKED. Predictor selection ran once, before either
representation existed, and the narrative the encoder reads is a fixed template
over that same selection. So Point 1 compares two encodings of one hand-picked
record, and neither point is evidence about what a model would do with a raw
one.

This is stated because it is the most natural wrong conclusion to draw from a null result: that the
advantage of an embedder is skipping the feature engineering, that you throw the raw patient in and the model finds the
structure. It appears in the Abstract's objective, once in the Introduction as
a bounding fact on both questions, in the Methods where the representations are
built, in the Discussion, in Limitations, and in the Conclusions.

It was briefly written up as a third point on 2026-09-06 and that was wrong.
It is not a question the paper asks and it has no Results subsection, because
it is a scope condition on two answers rather than a third answer. Do not
promote it again.

WHAT LEFT THE PAPER IN THIS ROUND, AND WHY. The LLM clinical-similarity judge
was one of four neighbor-weighting strategies. It changed nothing under
nearest retrieval (0.5939 cosine against 0.5947 judge-weighted) and helped
only under random retrieval, which is a negative control nobody would deploy.
It cost a rubric, a prompt, a worked-example appendix, a sub-score audit and a
re-judging experiment, all of it in service of a null on a scheme that is
itself not competitive. It is now `reserve/llm_similarity_judge.md`, complete,
with its numbers. The one-sentence disclosure that survived the first cut has
now gone too: a paper that describes an analysis and then declines to report it
advertises work the reader cannot check, which is "data not shown" in a politer
phrase. Neighbor weighting in the paper is uniform and cosine, and nothing
mentions a third. DO NOT re-import the judge into the main text or supplement
without a reason that connects it to Point 1 or Point 2.

LIMITATIONS IS A SECTION AGAIN, restored 2026-09-06 on the user's explicit
instruction after being held out on 2026-09-03 to match the senior author's
supplied Discussion. It is the ninth item that matters most: a medication
change that happened for a reason other than the drug not working is
invisible to this study, and the label counts it identically. The section
carries its sources. `reserve/limitations_reserve.md` records the earlier
removal and the audit of where each item had been living meanwhile.

============================================================================
NAMING, AND OTHER RULES STILL IN FORCE
============================================================================

TWO REPRESENTATIONS, TWO NAMES. The FEATURE representation ("feature vector",
"typed feature vector", "feature-vector XGBoost") and the EMBEDDED
representation ("the embedding", "the embedded representation"). "Rule-based"
is NOT an alias for either and must not appear anywhere in the packet: a third
name for the feature vector reads as a third method, and a reviewer once asked
which of three methods an ablation had been run on. Where the point is that no
generative model participates in narrative construction, the word is
"deterministic", which is what that sentence actually means.

"FEATURE MATRIX" IS ALSO BANNED, removed from both documents on 2026-09-07.
It was the second name nobody had declared -- eleven uses across the packet,
past every gate, because only "rule-based" had ever been listed. The stacked
92-column object does not get a name of its own: the sentence about its width
says the FEATURE representation expanded to 92 columns, and every other use is
"the feature vector". Where a sentence needs a short second mention, it repeats
"the feature vector" rather than shortening to "the matrix".

THE EMBEDDING IS A "generalized pretrained transformer embedding", the senior
author's phrase, and that is its only name. "Neural embedding" and "neural
narrative embedding" appear nowhere. "pretrained" is unhyphenated throughout.

"Standard machine learning", not "classical machine learning".

TIME ZERO IS THE INDEX. "index date", "index prescription", "pre-index",
"post-index" everywhere. The word "anchor" survives in exactly one sense: a
QUERY anchor in the retrieval arm (anchor-neighbor pair, 8,516 test anchors).
The deterministic renderer still prints `MDD-to-anchor gap` in its own field
labels, and the narratives reproduced in the supplement are verbatim and are
NOT re-labeled; a sentence there says so.

THE INDEX IS NOT "the first adequate antidepressant exposure". It is the
earliest antidepressant prescription recorded on or after the first documented
depression diagnosis. No adequacy, dose, or duration criterion enters its
selection, which is why 14.7% of the cohort carries a pre-index course meeting
the 42-day adequacy threshold. Verified against
scripts/data_loading/load_patient_data.py and against the table itself.

THE OUTCOME IS A PROXY AND IS NEVER RE-DESCRIBED AS THE CONSENSUS DEFINITION.
It is stated in the wording of Forthman et al [2] -- three or more
antidepressant treatments within one year of the index -- with the
two-post-index-changes restatement kept as equivalent arithmetic rather than
as the primary phrasing.

METHODS DOES NOT GROW. The Methods section is the senior author's own
condensation (supplied 2026-09-02), taken as written. Everything it cuts was
relocated into Supplementary Methods M1-M13, not deleted, and eight passages
that survive nowhere else are held in `reserve/methods_reserve.md`. New
methodological detail goes in the M-section and is noted in the reserve
document.

THE ABLATION SLATE IS SIX SPECIFICATIONS, treatment exposure included, and all
six are written up identically: a listing in Methods, a row in the table and
the figure, a rank in the Results paragraph. Treatment contraindications is a
PRESCRIBING-SAFETY concept, so the negligible-delta group is "the two
sociodemographic concepts, plus treatment contraindications" and never "the
sociodemographic permutations". General medical comorbidity is a separate
narrative section that was never permuted. The treatment-exposure section is
pre-index exposure only and is NOT label leakage; do not re-describe it that
way.

THE STUDY POPULATION IS CASE-ENRICHED BY DESIGN, and that is written up as the
study design in Methods rather than as a limitation. Every patient with a
problem-list depression code was retained and unflagged patients were added at
about 4:1. The one interpretive consequence stated is that prevalence-type
figures describe this cohort and not the source population; the representation
comparison is untouched, both arms using the same patients on the same split.
Do not describe 501,718 as a "source population" in the sense of a census. The
provenance is an internal LIBR working document and must NEVER be cited.

============================================================================
THE FINAL-REVIEW ROUND, 2026-09-07
============================================================================

A last pass over the manuscript and the supplement before the senior author
read them, run against Paper-Writer's gates and then by hand. What it found,
because the same defects will be reachable again:

  THE METHODS HEADING HAD STOPPED EXISTING. A missing newline left `# Methods`
  inside the last sentence of the Introduction, so pandoc printed four literal
  characters and the built .docx had no Methods heading anywhere. The splitter
  had always read it correctly, so parts/manuscript/04-methods.md was right and
  only the assembled document -- the artifact -- was wrong. Paper-Writer's
  `gates/venue.py` now refuses a heading marker that sits inside a line, and
  separately checks the five IMRaD headings.

  THE REFERENCES WERE NOT IN ORDER OF FIRST APPEARANCE, and this comment block
  claimed they were. See the map in the comment above the reference list.
  `gates/citations.py` now checks the order.

  "FEATURE MATRIX" WAS AN UNDECLARED THIRD NAME. Eleven uses across the two
  documents, past every gate, because the lock had only ever banned
  "rule-based". Removed; see the naming block above.

  A CAPTION POINTED AT A DOCUMENT THAT DOES NOT EXIST. Table 1's caption read
  "Full table in supporting material", which resolves to nothing and
  contradicted its own body sentence two lines above. `gates/crossrefs.py` now
  refuses a pointer that names no target.

  THE RESULTS CLAIMED AN INTERACTION TEST NOBODY RAN. "Classifier-matched
  contrasts revealed a significant interaction between representation and
  learner", against a Methods section describing only paired bootstrap
  intervals. Now stated as what was computed, matching the Abstract's wording.

  SUPPLEMENT S1 CONTRADICTED ITSELF. S1.1 concluded the embedded signal is
  concentrated in a sparse subset and S1.3 called that "the same
  broadly-distributed-signal conclusion". Both halves are true and they are not
  the same claim: the raw signal is diffuse and the elasticnet penalty is what
  compresses it. S1.3 now says so.

  SUPPLEMENT S8 ADVERTISED AN UNREPORTED TEST. "Whether this imbalance carries
  the head-to-head result was tested rather than conceded" -- and the test is
  reserve/matched_input_parity.md, which is not in the packet. Removed; the
  table is offered as what makes the bound checkable, which is what it is.

  A POINTER AIMED AT THE WRONG SECTION. The Results sent a reader to Supplement
  S8, the field-level crosswalk, for the full stratified subgroup results, which
  are Supplement S7. Nothing can catch this but reading it.

  MIXED BRITISH AND AMERICAN SPELLING, 45 instances, the worst of them 36
  "Neighbour-weighted" cells in Supplement S7's three tables against
  "neighbor-weighted" everywhere else in both documents. American throughout
  now.

Everything else the round changed is sentence surgery: eleven sentences split
for length, four paragraphs broken where they carried two claims, and two
supplementary paragraphs reordered so they close on their claim rather than on
a cross-reference. No number moved. The evidence ledger was not touched.

============================================================================
THE FIELD-INVENTORY ROUND, 2026-09-11
============================================================================

ONE NOUN, ONE SENSE. "Field inventory" meant two different things twenty-five
lines apart in Methods, *Predictors and patient representations*. The bolded
paragraph said both representations were built from the SAME curated field
inventory, meaning the fields predictor selection chose. The paragraph below it
said they do NOT receive an identical field inventory, meaning the information
those chosen fields carry once encoded. Both sentences were true and the reader
could not know that, so the second paragraph no longer uses the phrase at all:
selection was identical, and what differed was the ENCODING of some selected
fields. Supplement S8's opening sentence carried the same collision on "fields"
and now says "the same information". Paper-Writer's `gates/polarity.py` was
written from this and reports a noun the document calls the same in one place
and not the same in another.

The same round rewrote *Participants, index date, and temporal windows*, which
a reader could not follow. Three defects, all repaired:

  A "THEREFORE" WITH NO ANTECEDENT. "Prior antidepressant exposure was retained
  as a predictor. The index prescription was therefore the first antidepressant
  linked to a documented depression diagnosis..." The conclusion follows from
  the absence of any adequacy criterion in index selection, not from the
  retention of prior exposure as a predictor. What the index IS and IS NOT is
  now its own paragraph, opening on the denial and closing on the predictor.

  THE POINT OF THE DESIGN WAS NEVER STATED. The old paragraph listed the
  lookback window and the outcome window and never said the thing that makes
  the design valid: they never overlap. That is now the paragraph's closing
  sentence, and the forward-looking-selection claim ("nothing in that selection
  rule looks forward") is stated before the prediction point is named rather
  than welded to it.

  TWO PARAGRAPHS CLOSED ON SIGNPOSTS. "Figure 1 summarizes the temporal design.
  Full index-selection rules are given in Supplement M2." Both pointers moved
  under the claims they support. The same defect was live in the paragraph above
  the bolded one in *Predictors* -- pre-existing, caught by
  `gates/paragraphs.py` when the section was re-measured -- and the last two
  sentences there were swapped.

No number moved and the evidence ledger was not touched. Two sections are
longer than the author's condensation left them: *Participants* by 57 words and
*Predictors* by 40. Every one of those words is a sentence boundary or a
restatement of a fact the section already carried. No new methodological detail
entered, which is what METHODS DOES NOT GROW protects.

============================================================================
NUMBERS, FIGURES, AND THE BUILD
============================================================================

All performance numbers are from the current pipeline run (42,579-patient
cohort, data version DV260629v1-PV260710v1, primary encoder
Qwen3-Embedding-8B). Every figure in this file exists on disk under
`../results/` or `../notebooks/figures/`; the neighbor-weighted ROC panel was
repointed from the judge-weighted file to the cosine-weighted one in this
round, and no number moved as a result.

FIGURE GEOMETRY. Every panel is wide and short and stays at the full 6in text
width. A 6in-wide panel taller than about half the 9in text column cannot
share a page with its companion, so Word pushes the second panel overleaf.
Geometry comes from PANEL_FIGSIZE in scripts/shared/plots.py; do not set panel
widths below 6in in this file to fix a gap.

REFERENCES are numbered by order of first appearance in the text, counting
the abstract, Vancouver style. The list is 1-30, contiguous, every entry
cited, and the order was actually verified on 2026-09-07 rather than asserted
-- it had never held. Two references left with the judge in an earlier round
and the whole list was remapped in that verification pass, so a reference
number quoted in review/ or reserve/ will not match this list. The map is in
the comment block above the list itself; read it before chasing a number.
Bibliographic details were verified against PubMed and publisher records. Two
of the added references are not open access, every discrimination figure
quoted from them is confirmed against the published abstracts, and reprint
requests are drafted.

HISTORY. The round-by-round decision record that used to live in this comment
block is `review/manuscript_header_through_2026-09-03.md`, preserved verbatim.
Read it when the question is why a rule exists rather than what it is. The
senior-author review rounds themselves are `review/MP_review_latest.md` and
`review/round_2026-09-02.md`.
-->

# Title page
<!-- TRIPOD+AI 1 (title), 2 (abstract on next page) -->

**Title.** Narrative Embeddings Do Not Outperform Typed Features for a Treatment-Switch Proxy of Treatment-Resistant Depression: Retrospective Cohort Study

**Short title.** Embeddings and Typed Features for TRD Prediction

**Authors.** Mikey Ferguson, BS^1^; Martin Paulus,
MD^1^; Rayus Kuplicki, PhD^1^; Katherine L. Forthman,
MS^1^; Dale Peasley, MS^1^; Sandip Sen,
PhD^2^.

**Affiliations.**

^1^ Laureate Institute for Brain Research, Tulsa, OK, United States

^2^ The University of Tulsa, Tulsa, OK, United States

**ORCIDs.**

| Author | ORCID iD |
| --- | --- |
| Mikey Ferguson | 0009-0005-1365-5609 |
| Martin Paulus | 0000-0002-0825-3606 |
| Rayus Kuplicki | 0000-0003-2954-6421 |
| Katherine L. Forthman | 0000-0002-8695-8388 |
| Dale Peasley | 0009-0003-7696-595X |
| Sandip Sen | 0000-0001-6107-4095 |

**Corresponding author.**

Mikey Ferguson, BS
Laureate Institute for Brain Research
6655 South Yale Avenue, Tulsa, OK 74136, United States
Email: mferguson@laureateinstitute.org
ORCID: 0009-0005-1365-5609

# Abstract
<!-- TRIPOD+AI 2 (structured abstract); JMIR structured format -->

**Background.** As many as 1 in 3 patients with major depressive disorder (MDD)
progress to treatment-resistant depression (TRD) after failing successive
antidepressant trials [1]. An electronic health record (EHR) can be given to a
model as a typed feature vector, or written out as text and encoded by a
pretrained transformer, and the two have not been compared. A third approach
predicts a patient from the outcomes of their closest analogues, the premise
behind clinical digital twins.

**Objective.** Two questions on one cohort. Whether a generalized pretrained
transformer embedding of a patient narrative outperforms a typed feature vector
for predicting a treatment-switch–defined EHR proxy for incident TRD, and
whether nearest-neighbor retrieval over that embedding predicts as well as a
trained classifier.

**Methods.** Retrospective cohort of 42,579 adults with unipolar MDD from one
community health system. Following Forthman et al [2], TRD was 3 or more
antidepressant treatments within 1 year of the index date, the earliest
antidepressant prescription after a documented depression diagnosis; predictors
came only from the 730 days before it. Two representations were built from the
same hand-picked fields: a typed feature vector, and a Markdown narrative
written by fixed rules with no generative model, encoded by a pretrained
sentence-transformer (4 encoders; primary `Qwen3-Embedding-8B`). Four
classifiers were tuned by cross-validated grid search and scored on one held-
out stratified 20% split (8,516 patients, 1,491 TRD-positive). A retrieval
predictor scored each patient as the weighted mean TRD rate of 50 retrieved
training patients under 4 retrieval schemes. A semantic-feature ablation
shuffled each narrative concept across patients in turn to locate the embedded
signal. Reporting follows TRIPOD+AI [3].

**Results.** The embedding did not outperform the feature vector: ROC
AUC 0.657 (95% CI 0.643–0.672) against 0.649 (0.634–0.664), paired
difference +0.008 (−0.003 to +0.019). Holding the classifier fixed, it
helped logistic regression (+0.028) and hurt all 3 tree ensembles
(−0.013 to −0.022). Discrimination stayed within 0.012 across 4
encoders. The ablation localized the signal to psychiatric history,
medication burden and prior treatment exposure rather than to
sociodemographic fields. Retrieval was informative, not competitive:
nearest 0.594 (0.578–0.610) against random 0.499 on all 4 encoders, yet
0.063 short of the trained classifier on intervals that do not overlap.

**Conclusions.** Embedding matched, but did not exceed, a feature vector built
from the same fields, and retrieval over that embedding lost to a fitted model.
Both arms encode the same hand-picked inventory, so neither result shows that
embedding removes the feature engineering. Discrimination near 0.65 is too
modest for clinical use, and the outcome is a treatment-switch phenotype rather
than verified non-response.

**Keywords.** treatment-resistant depression; major depressive disorder;
electronic health records; clinical prediction model; machine learning; text
embeddings; nearest-neighbor retrieval; feature engineering; TRIPOD+AI.

# Introduction
<!-- TRIPOD+AI 3a (background and rationale), 3b (objectives) -->

Major depressive disorder is among the most prevalent and disabling
medical conditions, and antidepressant pharmacotherapy is its
first-line treatment. A substantial minority of patients fail to achieve
remission despite successive adequate trials. These patients are
described as having treatment-resistant depression (TRD), most commonly
operationalized as the failure of at least two antidepressant trials of
adequate dose and duration [4]. The sequential-treatment evidence base,
anchored by the STAR\*D program, established that remission rates fall
sharply with each successive treatment step. Patients who move into a
third or fourth step face a markedly lower probability of recovery [5].
TRD accordingly accounts for a disproportionate share of the clinical
morbidity, functional impairment, and health-care cost attributable to
depression [1].

Escalation options become both more necessary and less likely to succeed
as resistance develops. There is therefore longstanding interest in
identifying, as early as possible, which patients are at high risk of
progressing to TRD. If such patients could be flagged at the point of
their index antidepressant prescription, clinicians could in principle
monitor them more closely and escalate sooner.

An electronic health record (EHR) does not say whether a patient got better,
and rarely says whether a drug was given long enough at a high enough dose to
count as a fair trial. What it does record is which antidepressants were
prescribed and when. So studies define TRD from the prescription sequence
itself, which is what makes a cohort of tens of thousands possible at all. A
sequence is not proof of failure. A patient may be switched because the drug
did not work, or because it was not tolerated, or because they stopped taking
it. And the rule is not fixed: research groups count treatments, minimum
durations, switches and augmentations differently, and changing the rule
changes both how many patients count as TRD and which ones [6-8].

Others have already tried to predict TRD from what an EHR records, and the
numbers they report vary far more than the methods do. One study of 35,246
adults reported a ROC AUC of 0.83 [9]. A model that was validated on a second
health system reached 0.652 [10]. Adding clinical notes to structured fields
reached 0.728 at a single site [11]. And in a three-system study, figures of
0.58 to 0.64 inside the site that built the model fell to 0.51 to 0.58 when it
was tested elsewhere [12]. The spread comes from how each study defined TRD,
how far ahead it predicted, and whether it was ever tested outside the site it
was built in, so there is no single figure to beat. Two things survive the
variation. Structured EHR fields carry real signal, and the sharpest drops come
at the point where a model meets a health system it was not built on
[8,10-12].

Two questions about how to use such a record motivate this study. The first is representational. Predicting clinical
outcomes with large, purpose-built EHR foundation models requires data and
compute at scales most groups cannot reach [13,14]. Serializing an EHR into
text and applying general-purpose language-model embeddings is a
computationally efficient alternative that has proved competitive across
clinical prediction tasks [15]. It has not been compared directly against a
transparent, hand-crafted feature vector for TRD prediction. The comparison
matters because the two are not equally auditable. A feature vector can be
read, and a 4,096-dimensional embedding cannot, so a gain in discrimination is
the only thing that would pay for the loss of interpretability.

The second question concerns prediction by analogy. A recurring proposal in
precision psychiatry is that a patient's likely course can be read off the
recorded courses of the patients most similar to them, an idea usually
described as a clinical digital twin. An embedding makes that proposal directly
testable, because similarity in the embedding space is a defined quantity and
the neighbors it selects have observed outcomes. If the premise holds,
retrieving a patient's closest analogues and averaging their outcomes should
predict well. Whether it does, and how it compares with fitting a model to the
same representation, has not been established for TRD.

One thing is true of both questions and bounds both answers, so we state it
here rather than leaving it to be inferred. **The patient data were hand-picked in both arms.** Serializing a record
and embedding it is often read as a way to stop choosing features, and
that is not what happens here. Neither answer below is evidence about
what a model would do with a raw record, because neither arm was given
one.

Embedding a whole untailored record would be the interesting version of
that, and this study does not attempt it. The obstacle is input length
rather than principle.

This study evaluated whether EHR-derived patient data can predict this
prescription-sequence definition of TRD within one year, and addressed
the two objectives in order. To ensure methodological transparency and
facilitate rigorous appraisal, we report it in full accordance with the
TRIPOD+AI reporting guideline for clinical prediction models developed
with regression or machine-learning methods [3]. First, we compared a
transparent typed feature vector against generalized pretrained
transformer embeddings of patient narratives, evaluating both with four
standard classifiers on an identical cohort and held-out split. We
repeated that comparison across four encoders and located the embedded
signal with a semantic-feature ablation that permutes individual
clinical concepts. Second, we tested nearest-neighbor retrieval over the
same embedding against a random-retrieval control, and against the
trained classifiers themselves. Field by field, what each representation
receives is documented in Supplement S8.

# Methods

<!-- This is the senior author's own condensed Methods (supplied 2026-09-02 as
     JMIR_Methods_and_Supplement.docx), taken as written. Departures from his
     text are confined to cross-references, citation markers, the two facts his
     draft could not have known (the eligibility cascade moved to the supplement
     under his comment 115, the cohort table is Table 1 under comment 119), and
     the 2026-09-06 reduction of the neighbor-weighting slate to uniform and
     cosine. Everything his condensation drops is either in Supplement M1-M13 or
     recorded in reserve/methods_reserve.md. Do not grow this section; grow the
     M-section, and note the change in the reserve document. -->

## Study design and data source
<!-- TRIPOD+AI 4a (data source), 4b (study dates), 6a (setting) -->

We conducted a retrospective cohort study using a frozen, de-identified extract
from the Epic EHR of Saint Francis Health System, a community health system in
Tulsa, Oklahoma. The extract included person,
encounter, diagnosis, medication, procedure, laboratory/flowsheet, and
medication-to-RxNorm mapping data. Patient and encounter identifiers were
replaced with one-way hashes before transfer, and no direct identifiers or dates
of birth were provided.

The delivered extract was case enriched rather than a census of the health
system. All patients with a depression code on the problem list were retained,
together with a random sample of patients without that flag at an approximate
4:1 ratio. The extract contained 501,718 patients, including 100,420 (20.0%)
with and 401,298 (80.0%) without a problem-list depression flag. Eligibility for
the analytic cohort was determined from encounter-level diagnoses rather than
the problem-list sampling flag. Consequently, 12,530 of the 42,579 eligible
patients (29.4%) entered through the randomly sampled group. Cohort proportions
therefore describe this enriched sample and should not be interpreted as
health-system prevalence estimates. The head-to-head comparison of
representations is unaffected, both being derived from the same patients and
scored on the same held-out split.

All analyses used data version DV260629v1 and patient version PV260710v1. Source
files were cut on June 29, 2026, and analysis-ready tables were created on July
10, 2026. No subsequent data refresh entered the study. Patient index dates
spanned 2016-2024. The study used a random internal validation split from the
same source and period, not temporal or external validation. Additional
information on the source tables, setting, sampling frame, diagnosis code sets,
and data versions is provided in Supplement M1-M2.

## Participants, index date, and temporal windows
<!-- TRIPOD+AI 5a (eligibility), 5b (study dates), 6b, 6c (treatments) -->

Eligibility required a qualifying MDD diagnosis, an eligible antidepressant
index prescription, and that diagnosis recorded on or before that prescription.
Patients with a bipolar disorder or schizophrenia-spectrum diagnosis were
excluded. Each patient also needed at least 730 days of recorded EHR history
before the index prescription and at least 365 days of follow-up after it.
Those are the windows in which predictors and the outcome are measured. The
cascade and the rejection reason at each step are reported in Supplement M2
(Table M1). These criteria yielded 42,579 patients.

The index date was the start date of each patient's earliest antidepressant
prescription recorded on or after the first documented depression diagnosis.
Each patient contributed one index date. Nothing in that selection rule looks
forward. Dose, duration, response, and subsequent treatment changes play no
part in choosing the index prescription, so the prediction point is the
prescription date itself. Predictors were computed only from the 730-day
lookback window ending on the index date, which Figure 1 draws. Post-index data
entered in 2 places, confirming 365 days of follow-up and ascertaining the
outcome. The lookback window and the outcome window therefore never overlap.

The index prescription is not the patient's first antidepressant, and not their
first adequate trial. No adequacy, dose, or duration criterion enters its
selection, and Supplement M2 gives the rules in full. It is the first
antidepressant the record links to a documented depression diagnosis. Patients
with prior antidepressant exposure were therefore kept rather than excluded, and
that exposure was measured in the lookback window and retained as a
predictor.

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/time_zero_timeline.png){width=6in}

***Figure 1.** Time zero, the lookback window, and the outcome ascertainment
window. The index is the earliest antidepressant prescription recorded on or
after the patient's first documented depression diagnosis. Nothing that happens
after that date is used to choose it, so the prediction point is the
prescription date. Every predictor is measured inside the 730-day lookback
window. Recorded history often extends further back, with a median of 1,792
days, and its length is itself a predictor. Its content outside the lookback
window is never read. Post-index data enters in 2 places only: eligibility
requires at least 365 days of follow-up, and the outcome is ascertained over
those 365 days.*

## Outcome
<!-- TRIPOD+AI 6a (outcome definition), 6b (assessment) -->

The prediction target was a predefined EHR proxy for incident TRD, generated
upstream and used without modification. Consistent with the operational definition used by Forthman et al
[2], patients with MDD were classified as TRD positive if they received at
least 3 distinct antidepressant treatments during the 365 days after the index
date, including the index agent as the first treatment. Equivalently, the
outcome required at least 2 post-index antidepressant changes. A treatment was a
distinct antidepressant agent rather than a prescribing event. Augmentation
without replacement and restarting a previously used agent did not increment the
count, and augmentation enters the study as a pre-index predictor instead.

This outcome is a treatment-switch proxy rather than direct evidence of
inadequate response to 2 adequate trials [4,5]. Symptom response was not
systematically available, and dose and duration adequacy were not verified for
the counted treatments. Switching may therefore reflect nonresponse,
intolerance, adverse effects, cost, insurance constraints, fragmented care,
patient preference, or prescriber practice, and it depends on continuity of care
and access, which differ across demographic groups [16,17]. The label was not
validated against chart review or standardized symptom measures. These
inferential boundaries and proposed validation analyses are detailed in
Supplement M3, and their consequences for the study's claims in the Discussion,
*Limitations*.

## Predictors and patient representations
<!-- TRIPOD+AI 7a (predictor definition), 7b (assessment) -->

Predictors were specified a priori on clinical and prior-literature grounds
before model fitting or inspection of outcome associations. Domains included
depression characteristics, psychiatric and substance-use comorbidity, medical
comorbidity, prior antidepressant exposure and medication burden, prescribing
constraints, health care utilization, and sociodemographic and social-determinant
variables [18-21]. Selection rationale is given in Supplement M4 and the
complete inventory in Multimedia Appendix 1. Only structured EHR fields
available within the pre-index window were used.

**Both representations were built from the same curated field inventory, and
neither was built from a raw record.** Predictor selection happened once,
before either representation existed, and both then encoded that selection.
This bounds every comparison below: what is compared is two encodings of one
tailored record, not a tailored record against an untailored one. Each
patient's timeline-sliced record was converted independently into 2
representations. The typed feature representation (FEATURE) assigned explicit
data types to continuous variables, binary and multilabel indicators, and
nominal categorical variables. Continuous variables included age, utilization
and duration measures, medication burden, and counts of adequate antidepressant
trials, with an adequate trial defined as at least 42 days of continuous
exposure to an agent. After categorical expansion and exclusion of 3 vital-sign
variables for missingness, the FEATURE representation expanded to 92
columns.

For the embedded representation (EMBEDDED), the same pre-index record was
deterministically rendered as a human-readable Markdown narrative and encoded
as a fixed-length dense vector. The renderer walks a fixed template of section
headings and field labels, in a fixed order, over the fields named above.
Absent findings are printed explicitly and unrecorded ones as a literal token,
so every patient reaches the encoder through the same constant form. Narrative
construction used predefined rules and no generative model, ensuring that every
statement was traceable to the structured record. That guarantee is worth the loss of fluency, because a generated summary
introduces statements the record does not support at measured rates [22] and
here the narrative *is* the predictor. Four pretrained sentence-transformer
encoders were evaluated independently: `bge-small-en-v1.5` [23], `bge-en-icl`
[24], `Qwen3-Embedding-4B`, and `Qwen3-Embedding-8B` [25], with
`Qwen3-Embedding-8B` designated as the primary encoder.

Predictor selection was identical for the 2 representations, and both were built
from the same pre-index slice of the record. What differed was how some of those
selected fields were encoded. Supplement S8 is a field-level crosswalk that sets
the 2 encodings side by side across 28 source fields. For 17 fields the 2 sides
carry the same information. The remaining 11 are asymmetric, meaning that one
representation is told something the other is not.

The narrative holds more in 10 of those 11 fields. Some fields it renders have
no column in the feature vector at all. Others it prints as the raw Epic value
where the feature vector collapses that value into coarse categories.
Supplement M5 states the full encoding rules and Supplement S4 reproduces 2
example narratives. The eleventh field runs the other way, recorded history
length, which the narrative does not render. A head-to-head result therefore
compares 2 whole pipelines rather than data format alone, and the crosswalk is
what makes that bound checkable field by field.

## Missing data and sample partition
<!-- TRIPOD+AI 8 (sample size), 9 (missing data), 12a (partition) -->

No statistical imputation was performed. Mean body mass index and mean systolic
and diastolic blood pressure were excluded because of substantial and
outcome-associated missingness. Missing categorical values were retained as an
explicit category in FEATURE and as the literal token "Missing" in EMBEDDED. No
missing continuous values reached the estimators. Detailed missingness
frequencies and rationale are provided in Supplement M6.

We created one stratified 80:20 train-test split and used it for every
evaluation arm. The training set comprised 34,063 patients, including 5,964
TRD-positive patients (17.5%). The held-out test set comprised 8,516 patients,
including 1,491 TRD-positive patients (17.5%). Across 100 predictor rows, the
maximum absolute standardized mean difference between the 2 sets was 0.036. For
retrieval analyses, only training patients were placed in the searchable
neighbor pool. Test patients served solely as query anchors, which prevents
self-retrieval and any use of a test outcome as a neighbor label.
Events-per-variable calculations and further leakage safeguards appear in
Supplement M7-M8.

## Model development
<!-- TRIPOD+AI 10 (model development), 11 (analysis methods) -->

**Standard machine learning.** Logistic regression, random forest, gradient
boosting, and XGBoost classifiers were trained separately on each
representation. For FEATURE, a column transformer standardized continuous
variables, one-hot encoded categorical variables while ignoring unseen levels at
inference, and cast Boolean variables to integers. EMBEDDED was processed as an
all-numeric block. Preprocessing and estimation were combined within a single
pipeline and tuned using 5-fold cross-validated grid search in the training set,
optimizing area under the receiver operating characteristic curve (ROC AUC). On
every fold, fitted preprocessing parameters and category vocabularies were
estimated from that fold's training rows only. The best cross-validated
estimator was refit on the full training set and generated probabilities for the
untouched test set (Supplement M9).

**Neighbor-weighted retrieval prediction.** For EMBEDDED only, we also
estimated risk without fitting a model, as the weighted mean of TRD
labels among K = 50 retrieved training-set neighbors. This tests the
digital-twin premise directly: if a patient's course can be read from
the courses of their closest analogues, retrieval should predict well.
Retrieval schemes selected the nearest or the random training patients,
with random retrieval as the negative control. Weighting was uniform or
based on anchor-neighbor cosine similarity. Detailed equations, retrieval controls, and the evaluation grid are provided in Supplement M10 and M12.

**Semantic-feature ablation.** To estimate direct reliance of the embedded
pipeline on selected concepts, we permuted 1 narrative section or field at a
time across patients, re-embedded the perturbed narratives, and applied the
already-trained classifiers without retraining. Permutation preserved each
concept's marginal distribution while severing its patient-level association
with outcome. The tested concepts were psychiatric history, medication burden,
prior treatment exposure, treatment contraindications, race/ethnicity, and
social determinants of health. Change in ROC AUC relative to the unperturbed
model quantified direct-input reliance. This analysis was not designed to
establish fairness, rule out reconstruction of a permuted concept from
correlated fields, or evaluate subgroup calibration. Specifications, including
what each concept's permutation destroys, are provided in Supplement M11.

## Statistical analysis and performance metrics
<!-- TRIPOD+AI 11, 12 (evaluation) -->

Performance in the held-out test set was characterized using ROC AUC,
calibration slope and intercept, and sensitivity, specificity and the positive
and negative likelihood ratios at the threshold maximizing the Youden J
statistic. That threshold was selected and evaluated in the same test set, so operating-point
estimates are descriptive and optimistic rather than deployable clinical
thresholds. Calibration estimates apply to the case-enriched cohort's outcome
frequency and were not recalibrated to population prevalence.

An interval containing zero means no difference was detected, not that
the two representations are equivalent. No equivalence or noninferiority
margin was set in advance, so this paper makes no equivalence claim
anywhere.

Confidence intervals come from 1,000 nonparametric bootstrap resamples
of the test-set patients, detailed in Supplement M13. The subgroup
analysis computes 240 between-group contrasts, so its P values are
adjusted across that whole set by the Benjamini-Hochberg procedure,
controlling the false discovery rate at 5%.

Comparisons between two prediction vectors are paired. Each bootstrap
draw scores both prediction vectors on the same resampled patients
before their difference in ROC AUC is taken, which keeps the patient
draw out of the comparison. Classifier-matched contrasts hold the
learner fixed and vary only the representation. The
best-feature-versus-best-embedded comparison was chosen after the
results were in, so it is descriptive rather than a test. Retrieval
against the trained classifiers is reported as marginal rather than
paired intervals. Pairing would narrow those intervals, so reporting
them unpaired is the conservative choice.

## Reproducibility and software
<!-- TRIPOD+AI 13 (availability) -->

All random processes were seeded. Analyses were implemented in Python using
scikit-learn [26], XGBoost [27], and sentence-transformer encoders [28]. The
analysis code is publicly available [29].

# Results

<!-- ORDER IS LOAD-BEARING. Participant flow and cohort first, then everything
     bearing on Point 1 (the representation comparison), then everything
     bearing on Point 2 (retrieval), then the validity checks that support
     both. Do not re-insert a subsection ahead of the discrimination result;
     the previous draft opened Results on subgroup performance and confound
     checks, which buried the finding the paper is about. -->

The results are reported in the order of the two objectives. Participant flow
and cohort composition come first, then the comparison between the two
representations, then the retrieval predictor, and last the checks that bear on
both.

## Participant flow
<!-- TRIPOD+AI 13a (participant flow), 13b (characteristics) -->

Of the 501,718 patients in the delivered extract, 42,579 satisfied every
inclusion and exclusion criterion. Supplement M2 (Table M1) counts the
rejections at each stage of the hierarchical cascade. Those 42,579 are
the analysis cohort throughout, and 7,455 of them (17.5%) were
TRD-positive.

## Cohort characteristics

The cohort was middle-aged (median age 55 years, IQR 38–70),
predominantly female (72.5%), White/Caucasian (80.0%) and
English-preferring (98.9%). Table 1 gives every selected characteristic, overall and by TRD status,
and Supplement S9 gives within-subgroup TRD prevalence. The
characteristics most associated with TRD were a flagged suicidality
history, severe MDD coding, and a broad band of psychiatric and
substance-use comorbidity, which is the same profile the models later
rely on.

***Table 1.** Selected cohort characteristics by TRD status. Continuous
variables are median (IQR); categorical/boolean entries are n (%).
SMD = standardized mean difference (TRD-positive vs TRD-negative).*

| Characteristic | Level | Overall | TRD+ | TRD− | SMD |
| --- | --- | ---: | ---: | ---: | ---: |
| **Demographics** | | | | | |
| Age (years) | median (IQR) | 55 (38–70) | 51 (36–66) | 56 (39–71) | −0.193 |
| Age band | 18–29 | 5,513 (12.9%) | 1,135 (15.2%) | 4,378 (12.5%) | 0.080 |
| | 30–44 | 9,025 (21.2%) | 1,836 (24.6%) | 7,189 (20.5%) | 0.100 |
| | 45–64 | 13,268 (31.2%) | 2,445 (32.8%) | 10,823 (30.8%) | 0.043 |
| | 65+ | 14,773 (34.7%) | 2,039 (27.4%) | 12,734 (36.3%) | −0.192 |
| Sex | Female | 30,850 (72.5%) | 5,552 (74.5%) | 25,298 (72.0%) | 0.055 |
| Race/ethnicity | White/Caucasian | 34,079 (80.0%) | 5,942 (79.7%) | 28,137 (80.1%) | −0.010 |
| | Black/African American | 2,368 (5.6%) | 401 (5.4%) | 1,967 (5.6%) | −0.010 |
| | Am. Indian/Alaska Native | 2,033 (4.8%) | 394 (5.3%) | 1,639 (4.7%) | 0.028 |
| | Missing | 297 (0.7%) | 46 (0.6%) | 251 (0.7%) | −0.012 |
| **Depression phenotype** | | | | | |
| MDD recurrence | Recurrent | 11,213 (26.3%) | 2,189 (29.4%) | 9,024 (25.7%) | 0.082 |
| | Single episode | 28,206 (66.2%) | 4,721 (63.3%) | 23,485 (66.9%) | −0.074 |
| MDD severity | Severe | 2,286 (5.4%) | 720 (9.7%) | 1,566 (4.5%) | 0.204 |
| | Moderate | 7,233 (17.0%) | 1,300 (17.4%) | 5,933 (16.9%) | 0.014 |
| | Psychotic | 112 (0.3%) | 35 (0.5%) | 77 (0.2%) | 0.043 |
| | Unspecified | 28,951 (68.0%) | 4,803 (64.4%) | 24,148 (68.8%) | −0.092 |
| **Psychiatric and substance comorbidity** | | | | | |
| Suicidality flagged | True | 1,753 (4.1%) | 641 (8.6%) | 1,112 (3.2%) | 0.232 |
| Anxiety disorder | True | 22,401 (52.6%) | 4,499 (60.3%) | 17,902 (51.0%) | 0.190 |
| Substance use disorder (any) | True | 9,265 (21.8%) | 2,006 (26.9%) | 7,259 (20.7%) | 0.147 |
| Insomnia | True | 9,350 (22.0%) | 2,021 (27.1%) | 7,329 (20.9%) | 0.147 |
| PTSD | True | 1,541 (3.6%) | 450 (6.0%) | 1,091 (3.1%) | 0.141 |
| Alcohol use disorder | True | 1,875 (4.4%) | 501 (6.7%) | 1,374 (3.9%) | 0.125 |
| Opioid use disorder | True | 1,281 (3.0%) | 337 (4.5%) | 944 (2.7%) | 0.098 |
| Adjustment disorder | True | 2,918 (6.9%) | 663 (8.9%) | 2,255 (6.4%) | 0.093 |
| **Medical comorbidity** | | | | | |
| High cholesterol | True | 15,747 (37.0%) | 2,202 (29.5%) | 13,545 (38.6%) | −0.191 |
| Uncontrolled hypertension | True | 15,680 (36.8%) | 2,366 (31.7%) | 13,314 (37.9%) | −0.130 |
| **Treatment and utilization** | | | | | |
| Active med count | median (IQR) | 1 (0–2) | 1 (0–2) | 1 (0–2) | 0.084 |
| Encounter count | median (IQR) | 21 (8–46) | 17 (6–40) | 21 (8–47) | −0.140 |
| Pre-index history (days) | median (IQR) | 1,792 (1,216–2,546) | 1,629 (1,141–2,335) | 1,830 (1,239–2,587) | −0.198 |
| Any prior treatment exposure recorded | True | 10,230 (24.0%) | 1,793 (24.1%) | 8,437 (24.0%) | 0.001 |
| Prior adequate AD trial (any class) | True | 6,276 (14.7%) | 1,050 (14.1%) | 5,226 (14.9%) | −0.023 |
| Benzodiazepine days recorded | True | 4,724 (11.1%) | 989 (13.3%) | 3,735 (10.6%) | 0.081 |
| Hypnotic recorded | True | 1,661 (3.9%) | 292 (3.9%) | 1,369 (3.9%) | 0.001 |
| Augmentation therapy used | True | 422 (1.0%) | 108 (1.4%) | 314 (0.9%) | 0.052 |

## Model discrimination
<!-- TRIPOD+AI 13b. POINT 1, the primary result. -->

The embedding did not outperform the feature vector. Embedded logistic
regression achieved the highest discrimination on the embedded
representation (ROC AUC 0.657, 95% CI 0.643–0.672), and XGBoost led the
feature-vector models (0.649, 95% CI 0.634–0.664). All eight representation-by-classifier combinations appear in Figure 2A
and Table 2. The best embedded model scored 0.008 higher than the best
feature-vector model, on an interval from −0.003 to +0.019 that crosses
zero (Figure 2B). The comparison is paired: every bootstrap draw scores
both models on the same patients, so the interval measures the gap
between models rather than the luck of the draw. An embedded gain larger than +0.019 ROC AUC falls outside it.
Discrimination was modest throughout, from 0.623 at the lowest
configuration to 0.657 at the highest, against a 17.5% TRD-positive
rate.

Which representation won depended on the learner. Holding the classifier
fixed, the embedding helped logistic regression (+0.028, 95% CI +0.017 to
+0.039). It hurt all three tree ensembles: random forest by 0.022 (95% CI
0.011 to 0.033), gradient
boosting by 0.013 (0.001 to 0.026), and XGBoost by 0.013 (0.002 to
0.025). Tuning grids did not differ between representations, so this is
a property of the representation rather than of its tuning.

***Table 2.** Discrimination of the four classifiers on each
representation (held-out test set). 95% CIs are bootstrap percentile
intervals. FEATURE-side values are from the 92-column feature vector.*

| Representation | Classifier | ROC AUC (95% CI) |
| --- | --- | :---: |
| EMBEDDED | Logistic regression | 0.657 (0.643–0.672) |
| EMBEDDED | Random forest | 0.623 (0.608–0.639) |
| EMBEDDED | Gradient boosting | 0.632 (0.618–0.647) |
| EMBEDDED | XGBoost | 0.636 (0.621–0.651) |
| FEATURE | Logistic regression | 0.629 (0.613–0.644) |
| FEATURE | Random forest | 0.644 (0.630–0.659) |
| FEATURE | Gradient boosting | 0.645 (0.629–0.660) |
| FEATURE | XGBoost | 0.649 (0.634–0.664) |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/discrimination_forest_EMBEDDED_vs_FEATURE.png){width=6in}

***Figure 2.** Discrimination by representation and classifier (held-out
test set, n = 8,516; primary Qwen3-Embedding-8B encoder). **(A)** All
eight representation-by-classifier combinations, grouped with EMBEDDED
above FEATURE and in the same classifier order within each group, so the
two can be read row for row. Markers are ROC AUC point estimates, bars
are bootstrap percentile 95% confidence intervals, and the values are in
Table 2. **(B)** The paired difference in ROC AUC, EMBEDDED minus
FEATURE, with a paired bootstrap 95% interval. The solid line marks
zero. The four diamonds hold the classifier fixed and vary only the
representation; the star is the post-hoc
best-feature-versus-best-embedded contrast, embedded logistic regression
minus feature-vector XGBoost.*

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_xgboost_FEATURE.png){width=6in}

***Figure 3.** Receiver-operating-characteristic curves for the best
classifier on each representation (held-out test set; primary
Qwen3-Embedding-8B encoder). Shaded bands are bootstrap 95% confidence
intervals; point AUCs are given in Table 2.*

The two behaved alike at their Youden-J operating points (Figure 4).
Embedded logistic regression ran at slightly higher sensitivity than
feature-vector XGBoost (0.65 versus 0.62), flagging 964 of 1,491
held-out TRD patients against 917, and at slightly lower specificity
(0.58 versus 0.61), producing more false positives (2,932 versus 2,768).
Both thresholds fell near 0.17. They were chosen on the same patients
the models were scored on, so these figures describe the shape of each
ROC curve rather than performance at a prespecified threshold, and are
not candidate operating characteristics.

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/confusion_matrices/confusion_matrix_xgboost_FEATURE.png){width=6in}

***Figure 4.** Confusion matrices at the Youden-J optimal operating point
for the best classifier on each representation (held-out test set;
primary Qwen3-Embedding-8B encoder).*

## Model calibration

Neither representation was systematically better scaled than the other
(Table 3, Figure 5). On
the embedded representation, gradient boosting was the best-calibrated
model (slope 1.01, intercept 0.01). Logistic regression was mildly
under-confident (slope 1.27, the slope above 1 indicating probabilities
pulled toward the base rate), random forest similar (1.15), and XGBoost
mildly over-confident (slope 0.75). On the feature vector, XGBoost was
best-calibrated (slope 1.02, intercept 0.02) and random forest the worst
(slope 1.84). Each representation therefore contained both a
near-ideally calibrated model and a poorly calibrated one, and which
classifier occupied which position differed between them. No model
placed any test prediction above 0.9, as expected at this base rate.
Absolute-error metrics are in Supplement S3. Every one of these figures
is scaled to this cohort's 17.5% TRD rate, which the sampling design
chose, so none of them establishes calibration anywhere else.

***Table 3.** Calibration slope (ideal 1) and intercept (ideal 0) of the
four classifiers on each representation (held-out test set). Brier score
and weighted calibration error are reported in Supplement S3 (Table S3).*

| Representation | Classifier | Slope | Intercept |
| --- | --- | ---: | ---: |
| EMBEDDED | Logistic regression | 1.27 | −0.07 |
| EMBEDDED | Random forest | 1.15 | −0.02 |
| EMBEDDED | Gradient boosting | 1.01 | 0.01 |
| EMBEDDED | XGBoost | 0.75 | 0.07 |
| FEATURE | Logistic regression | 0.78 | 0.06 |
| FEATURE | Random forest | 1.84 | −0.15 |
| FEATURE | Gradient boosting | 0.87 | 0.04 |
| FEATURE | XGBoost | 1.02 | 0.02 |

**(A) Embedded logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png){width=6in}

**(B) Feature-vector XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png){width=6in}

***Figure 5.** Calibration curves for the best classifier on each
representation (held-out test set; primary Qwen3-Embedding-8B encoder).
The diagonal is perfect calibration. Deviations above it indicate
under-confidence and below it over-confidence. Per-classifier calibration
slope and intercept are given in Table 3.*

## What each representation reads

Only the feature vector can be read directly.
The embedded representation's 4,096 latent dimensions carry no
individual clinical meaning, so per-concept attribution on the embedded
side is addressed by the ablation below rather than by an importance
ranking. On the feature vector, the highest-weighted predictors
recapitulated the strongest univariate correlates of TRD in Table 1.
Severe MDD coding, a flagged suicidality history, insomnia,
obsessive–compulsive disorder, opioid use disorder, PTSD, and anxiety
disorder carried the largest positive logistic-regression weights.
Indicators such as missing smoking status, hyperlipidemia, longer
pre-index history, and male sex carried negative weights. Importances for
all four classifiers are shown in Figure 6. The tree ensembles concentrated on a similar set of psychiatric and
substance-use predictors at the top, with direction of effect recovered
by univariate correlation. The readable side of the null is therefore
reading recognizable psychiatric risk, which is what separates a tie
between two working models from a tie between two failing ones.

<!-- One panel per row at full text width: the previous 2x2 grid at 2.8in
     rendered the axis labels unreadably small. -->

**(A) Logistic regression**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_logistic_regression.png){width=6in}

**(B) Random forest**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_random_forest.png){width=6in}

**(C) Gradient boosting**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_gradient_boosting.png){width=6in}

**(D) XGBoost**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_xgboost.png){width=6in}

***Figure 6.** Feature importance on the feature-vector representation, one
panel per classifier. (A) Signed logistic-regression coefficients
(steelblue raises TRD risk, firebrick lowers it). (B) Random forest,
(C) gradient boosting, and (D) XGBoost importances, with
direction-of-effect recovered by univariate correlation. The
highest-ranked predictors mirror the largest TRD-stratified differences
in Table 1.*

The embedded model used far fewer dimensions than it was given.
Cross-validated elasticnet left 385 of the 4,096 with nonzero weight,
and roughly 179 of those carried 80% of the total coefficient magnitude
(roughly 236 carried 90%; Figure 7). Fewer than 5% of the available dimensions
therefore account for most of the fit, and model-agnostic correlation
and principal-component checks agree (Supplement S1).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/feature_importance/feature_importance_cumulative_EMBEDDED.png){width=6in}

***Figure 7.** Effective dimensionality of the embedded representation
(primary Qwen3-Embedding-8B encoder): cumulative built-in feature
importance for the four embedded classifiers. Each curve plots the
cumulative fraction of total importance mass against dimension rank, with
dimensions sorted by descending native importance, and the K₈₀ / K₉₀
knees are reported in the legend. Model-agnostic correlation and PCA-based checks are in Supplement S1.*

## Semantic-feature ablation

Permuting narrative concepts one at a time located the embedded signal in
psychiatric history, medication burden, and prior treatment exposure.
Psychiatric history produced the largest discrimination loss (logistic
regression, a ROC AUC change of −0.028, with the other three
classifiers between −0.024 and −0.027). Medication burden produced the second largest
(−0.003 to −0.027) and treatment exposure the third (−0.019 for logistic
regression, and +0.000 to −0.011 for the other three).
Permuting the two sociodemographic concepts, race/ethnicity and social
determinants of health, or the treatment-contraindication section
changed discrimination by no more than 0.005 under any classifier
(Table 4, Figure 8).

Paired-bootstrap intervals excluded zero for psychiatric history in all
four classifiers, medication burden in three, and treatment exposure in
two. Among the remaining concepts only one interval excluded zero,
treatment contraindications under XGBoost at −0.005 (−0.008 to −0.001),
and race and social determinants moved ROC AUC by less than 0.003
anywhere.

The domains the embedding relies on are the same domains that carry the
largest feature-vector weights. That convergence is the mechanism behind the null in Table 2: the two representations are reading the same
clinical content out of the same record, and the embedding reorganizes it
without adding to it.

***Table 4.** Semantic-feature ablation: change in ROC AUC versus the
frozen baseline when each narrative concept is permuted across donors
(embedded representation, primary Qwen3-Embedding-8B encoder). More
negative = larger reliance on that concept. Point estimates, ordered by descending logistic-regression loss to match
Figure 8. Paired-bootstrap intervals are quoted in the text.*

| Permuted concept | LR | RF | GB | XGB |
| --- | ---: | ---: | ---: | ---: |
| Psychiatric history | −0.028 | −0.027 | −0.024 | −0.027 |
| Medication burden | −0.027 | −0.003 | −0.014 | −0.017 |
| Treatment exposure | −0.019 | +0.000 | −0.006 | −0.011 |
| Treatment contraindications | −0.002 | +0.001 | −0.001 | −0.005 |
| Social determinants (SDOH) | −0.000 | +0.000 | +0.000 | +0.001 |
| Race/ethnicity | −0.000 | +0.000 | −0.003 | −0.000 |

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/ablation_roc_ci_EMBEDDED.png){width=6in}

***Figure 8.** Semantic-feature ablation, absolute-discrimination view
(embedded representation, primary Qwen3-Embedding-8B encoder). Each row
is a run: the unablated baseline on top, then the six permutation
specifications ordered by descending logistic-regression ROC AUC drop, the
same ordering reused across panels. There is one panel per classifier,
arranged two by two on a shared ROC AUC axis, with a reference line at the
baseline ROC AUC. Permuting psychiatric history, medication burden and
treatment exposure produces the largest discrimination loss, whereas the
remaining three concepts move ROC AUC comparatively little (deltas in
Table 4).*

## Robustness across encoders

The comparison did not depend on which encoder produced the embedding.
Across the four encoders the embedded logistic-regression model occupied
a 0.012-wide discrimination band (ROC AUC 0.645–0.657, Table 5 and
Figure 9A). Qwen3-Embedding-8B was highest (0.657, 95% CI 0.643–0.672),
with bge-en-icl and Qwen3-Embedding-4B tied just behind (both 0.655) and
bge-small-en-v1.5 lowest (0.645). Logistic regression was the
best-discriminating classifier on the embedded representation for every
encoder. Only bge-small-en-v1.5 scored below the best feature-vector
model. The other three scored just above it, and all four fall inside
that same band, which is narrower than every confidence interval in
Table 2. The choice of encoder therefore does not change
what Table 2 shows.

The ablation also reproduced across encoders (Figure 9B). Psychiatric
history and medication burden cost the most on all four, −0.027 to
−0.030 and −0.022 to −0.034 respectively. Every one of those intervals
excluded zero. The two sociodemographic permutations moved ROC AUC
little. The order of the two largest concepts held everywhere except in
bge-en-icl, where medication burden cost more than psychiatric history,
and it did so for all four classifiers there (embedded logistic
regression −0.034 versus −0.027).

***Table 5.** Embedded logistic-regression discrimination by encoder
(held-out test set). 95% CIs are bootstrap percentile intervals.
"Dimensions" is the encoder's output dimensionality, which is also the
number of predictor columns the classifier receives; EPV is events per
variable, 5,964 TRD-positive training patients divided by that column
count (Supplement M7). Note that EPV runs opposite to discrimination: the
encoder with the most favorable EPV is the least discriminating.*

| Encoder | Dimensions | EPV | ROC AUC (95% CI) |
| --- | ---: | ---: | :---: |
| bge-small-en-v1.5 | 384 | 15.5 | 0.645 (0.629–0.660) |
| bge-en-icl | 4,096 | 1.5 | 0.655 (0.641–0.670) |
| Qwen3-Embedding-4B | 2,560 | 2.3 | 0.655 (0.641–0.670) |
| Qwen3-Embedding-8B | 4,096 | 1.5 | 0.657 (0.643–0.672) |

![](../results/cross_embedder_robustness_EMBEDDED.png){width=6in}

***Figure 9.** Cross-embedder robustness: embedded logistic-regression
ROC AUC (A) and the two largest semantic-feature ablation deltas
(psychiatric history, medication burden; B) across all four encoders
(bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, Qwen3-Embedding-8B),
demonstrating that the principal conclusions hold beyond the
Qwen3-Embedding-8B encoder. Error bars are bootstrap (A) and
paired-bootstrap (B) 95% confidence intervals.*

## Prediction from retrieved neighbors
<!-- POINT 2. Table 6 is the two-by-two grid; Table 7 is the cross-encoder
     reproduction; Figure 10 is nearest against random. The similarity-judge
     weightings, and the farthest and subsampled schemes, were removed from
     this arm on 2026-09-06 and are held in reserve/. Do not re-add columns
     here. -->

Retrieval recovered real signal from the embedding geometry. Retrieving
the nearest neighbors discriminated at ROC AUC 0.594 (95% CI
0.578–0.610) under cosine weighting. Random retrieval landed at chance
(0.499, 95% CI 0.483–0.515). A space in which a patient's closest
analogues predict the outcome and randomly drawn patients do not is a
space that carries label information.

How neighbors were weighted mattered far less than which neighbors were
retrieved. Uniform and cosine weighting differed by at most 0.005 ROC
AUC within either retrieval scheme, against the gap from 0.594 to 0.499
between nearest and random retrieval (Table 6). Once the 50 retrieved
patients are already the most similar available, adjusting their
relative contributions has almost nothing left to do.

Retrieval nevertheless lost decisively to a model fitted on the same
embedding. The best retrieval configuration reached 0.594 (0.578–0.610)
against 0.657 (0.643–0.672) for embedded logistic regression, a
shortfall of 0.063 ROC AUC on intervals that do not overlap. The
comparison is unpaired and therefore conservative, since both predictors
score the same held-out patients. Retrieval also fell below every one of
the eight trained configurations in Table 2, including the weakest of
them at 0.623.

***Table 6.** Neighbor-weighted ROC AUC by retrieval scheme and
weighting strategy (embedded representation, primary Qwen3-Embedding-8B
encoder, held-out test set; K = 50 neighbors). 95% CIs are bootstrap
percentile intervals. Random retrieval is the negative control. For
comparison, embedded logistic regression on the same representation and
the same patients reaches 0.657 (0.643–0.672).*

| Retrieval scheme | Uniform (95% CI) | Cosine (95% CI) |
| --- | :---: | :---: |
| Nearest | 0.593 (0.578–0.609) | 0.594 (0.578–0.610) |
| Random | 0.495 (0.479–0.510) | 0.499 (0.483–0.515) |

**(A) Nearest retrieval**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_NEAREST_COSINE.png){width=6in}

**(B) Random retrieval**

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/roc_curves/roc_curve_RANDOM_COSINE.png){width=6in}

***Figure 10.** Neighbor-weighted ROC for the cosine-weighted predictor on
the embedded representation (held-out test set, n = 8,516, K = 50;
primary Qwen3-Embedding-8B encoder). (A) Nearest retrieval;
(B) random retrieval. The separation between the two panels is the
discriminative signal in the embedding geometry. Shaded bands are
bootstrap 95% confidence intervals and the dashed diagonal is chance.
The uniform weighting is in Table 6.*

Both halves of that result reproduced on every encoder (Table 7).
Nearest retrieval beat random retrieval by 0.083 to 0.095 ROC AUC on all
four, and on all four it fell short of that encoder's own trained
logistic regression by 0.061 to 0.065. The gap between retrieval and a
fitted model is therefore a property of the approach rather than of the
primary encoder.

***Table 7.** Neighbor-weighted retrieval against embedded logistic
regression, by encoder (cosine weighting, K = 50, held-out test set).
95% CIs are bootstrap percentile intervals. Random retrieval is the
negative control. The last column is that encoder's own model from Table
5, scored on the same patients.*

| Encoder | Nearest (95% CI) | Random (95% CI) | Embedded logistic regression (95% CI) |
| --- | :---: | :---: | :---: |
| bge-small-en-v1.5 | 0.580 (0.564–0.596) | 0.497 (0.482–0.513) | 0.645 (0.629–0.660) |
| bge-en-icl | 0.592 (0.577–0.607) | 0.498 (0.482–0.515) | 0.655 (0.641–0.670) |
| Qwen3-Embedding-4B | 0.594 (0.579–0.611) | 0.500 (0.484–0.516) | 0.655 (0.641–0.670) |
| Qwen3-Embedding-8B | 0.594 (0.578–0.610) | 0.499 (0.483–0.515) | 0.657 (0.643–0.672) |

## Validity checks

Three checks bear on both objectives, because an artifact in any of them
would undermine the comparison as much as the retrieval result. None of
the three found one.

**Train/test comparability.** The training and test sets were closely
matched on every predictor. Over 100 predictor rows the largest absolute
standardized mean difference was 0.036, none reached the conventional
0.1 threshold, and the maximum sat on a social-determinant flag recorded
for 22 training patients and no held-out patient. That is a small-cell
artifact rather than a distributional difference. No measured difference separates the evaluation sample from the
development sample, and neither is representative of a wider population,
because both halves inherit the extract's case enrichment. Supplement S6
tabulates the distributions in the form of Table 1.

**Data volume did not act as a confound.** Patients with richer records
could appear higher-risk for reasons that have nothing to do with
depression, so we correlated the TRD label with three volume and recency
proxies on the full untruncated data. All three associations were weak
and negative: pre-index history length (Spearman ρ = −0.073), encounter
count (ρ = −0.064), and MDD-to-index gap (ρ = −0.029). TRD-positive patients did not simply have more data (Figure 11A–C), and
discrimination is flat across quintiles of pre-index history length,
which is the stronger form of the same test (Supplement S5). Most patients were prescribed an antidepressant on the day of their MDD
diagnosis (n = 27,906). Their TRD rate was 18.4% against 15.9% for the
14,673 with a delayed prescription, both near the 17.5% base rate
(Figure 11D).

**(A) Pre-index history length**

![](../notebooks/figures/density_pre_anchor_history_days.png){width=6in}

**(B) MDD-to-index gap**

![](../notebooks/figures/density_mdd_to_anchor_days.png){width=6in}

**(C) Encounter count**

![](../notebooks/figures/density_num_encounters.png){width=6in}

**(D) TRD rate, same-day vs delayed prescription**

![](../notebooks/figures/trd_rate_by_delayed_mdd_to_anchor_days.png){width=6in}

***Figure 11.** Volume and recency confound checks on the full untruncated
data. (A–C) TRD-stratified distributions of the three proxies: (A)
pre-index history length; (B) MDD-to-index gap; (C) encounter count.
(D) TRD rate among patients with a same-day versus delayed
MDD-to-antidepressant prescription (dashed line = 17.5% cohort base
rate; bar labels are group n).*

**Subgroup performance.** Most of what separates subgroups here is how the depression is coded,
not who the patient is. The same models were scored again inside eight strata, with nothing
refit, giving 240 between-group contrasts across the three arms. At a conventional 5% threshold about twelve of those clear the bar by
chance alone, so P values were adjusted across the whole set by
Benjamini-Hochberg at a 5% false discovery rate. Fifty-eight contrasts exclude zero before that
adjustment and 24 survive it, 21 of them about MDD coding. Discrimination is higher where MDD is coded
recurrent or severe (+0.059 to +0.087 ROC AUC) and lower where it is
coded single-episode (−0.074 to −0.056), in all three arms. That is a
documentation effect as much as a phenotype one: the models do better
where the diagnosis is recorded specifically, and worse where it is left
unspecified, which is most of this cohort.

The sociodemographic strata gave three surviving contrasts, and all
three are consistent with thinner records supporting weaker prediction.
Discrimination is lower for patients aged 18–29 in the feature-vector
arm (−0.068, adjusted *P* = .04). It is also lower for never-married
patients in the embedded arm, where two of the four classifiers
survive, at −0.054 and −0.051 (adjusted *P* = .01). No sex contrast
came close: all ten include zero and none exceeds 0.012 ROC AUC.
Preferred language was not analyzed, because 98.9% of the cohort prefers
English.

The data neither establish nor rule out a race-associated performance
gap. All ten White-minus-non-White contrasts are positive
(+0.005 to +0.053) and five exclude zero before adjustment, but none
survives it (smallest adjusted *P* = .11). The minority stratum carries
302 outcome events against 1,181, which leaves its intervals roughly
twice as wide. Feature-vector calibration is worse among non-White
patients (slope 0.79 versus 0.98) while the embedded arm holds (0.95
versus 0.97). Supplement S7 has the full stratified results, and
Limitations takes up what a gap this wide can and cannot be read to
mean.

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

# Declarations

**Funding.** This work was funded by the William K. Warren Foundation. No
other funding agency in the public, commercial, or not-for-profit sectors
supported this research. M. Ferguson was supported by a graduate
assistantship from the Laureate Institute for Brain Research while
enrolled as a graduate student at The University of Tulsa. The funder had
no role in the design of the study, the analysis or interpretation of the
data, the writing of the manuscript, or the decision to submit it for
publication.

**Conflicts of interest.** None declared.

**Ethics and data handling.** This study is a secondary analysis of
de-identified data and is therefore not human-subjects research subject
to institutional review board approval; no IRB review, protocol number,
or waiver of informed consent applies. The analysis used a de-identified
EHR extract containing no direct patient identifiers, and no protected
health information was accessible to the investigators at any stage. All computation was performed on local institutional hardware, including the sentence-transformer embedding of the patient narratives. No patient data,
structured or narrative, was transmitted to any external, third-party,
or commercial service or application programming interface.

**Authors' contributions.** MF designed and implemented the analysis
pipeline, performed all modelling and statistical analysis, produced the
figures and tables, and wrote the manuscript. MP directed the project and
supervised its scientific design and interpretation. KLF prepared the
upstream clinical data, including the treatment-resistant depression
labels and the antidepressant index dates that define the cohort and the
outcome. RK, SS, and DP provided methodological feedback and guidance on
the analysis and its interpretation throughout. All authors reviewed and
approved the final manuscript.

**Patient and public involvement.** No patients or members of the public
were involved in the design, conduct, reporting, or dissemination of this
study.

**Protocol.** A study protocol was not prepared.

**Registration.** This study was not registered.

**Data availability.** The EHR data are not publicly shareable. The analysis
code is publicly available [29]. Fitted model objects are not distributed, as
they are derived from non-shareable patient data.

**Reporting.** This study is reported in accordance with the TRIPOD+AI
guideline for prediction-model studies [3]. The completed TRIPOD+AI
checklist is provided as a separate submission document.

# Abbreviations

<!-- Mandatory for JMIR, and checked by `gates/venue.py`. One row per abbreviation
     the manuscript actually uses more than once; the two representation names are
     included because the naming rule makes them terms of art in this paper rather
     than ordinary words. Keep this in step with the terminology lock. -->

**AUPRC:** area under the precision-recall curve.

**CI:** confidence interval.

**EHR:** electronic health record.

**EMBEDDED:** the embedded representation, a deterministic patient narrative encoded.
by a pretrained sentence-transformer

**EPV:** events per variable.

**FEATURE:** the typed feature representation, a typed vector built directly from.
coded EHR fields

**IQR:** interquartile range.

**MDD:** major depressive disorder.

**ROC AUC:** area under the receiver operating characteristic curve.

**SDOH:** social determinants of health.

**SMD:** standardized mean difference.

**TRD:** treatment-resistant depression.

**TRIPOD+AI:** Transparent Reporting of a multivariable prediction model for.
Individual Prognosis Or Diagnosis, artificial intelligence extension

**WCE:** weighted calibration error.

# References

<!--
References are numbered by order of first appearance in the text, counting
the abstract, and the numbering is CONTIGUOUS FROM 1 with every entry cited.
Vancouver style, first six authors then "et al." Bibliographic details
verified against PubMed / ACL Anthology / publisher records.

RENUMBERED THREE TIMES. Read this block before quoting a reference number out
of review/ or reserve/, because those documents record the numbers that were
in force when they were written and no attempt was made to rewrite history
there.

Passes one and two, both 2026-09-06, were REMOVALS. The previous ref 24
(Lee C et al, "How to correctly report LLM-as-a-judge evaluations") existed
only to pre-empt an objection to the similarity-judge weighting arm; the arm's
RESULTS left the main text and the reference left with them, so previous 25-31
became 24-30. Then the arm stopped being MENTIONED at all, because a paper
that describes an analysis and then declines to report it advertises work the
reader cannot check. Ref 15 (Sellergren et al, MedGemma technical report) was
cited only from those two sentences and left with them, so 16-31 became 15-30.
Both the judge results and their citation are complete in
reserve/llm_similarity_judge.md, which carries its own inline citations and no
numbered list.

Pass three, 2026-09-07, was the ORDER. The list had never actually been in
order of first appearance -- the Introduction cited [23-25] before [4] -- and
this block claimed it was. Every marker was remapped and the list reordered.
The map, old to new:

     1 ->  1     2 ->  4     3 ->  5     4 -> 18     5 -> 19     6 -> 20
     7 -> 21     8 -> 30     9 -> 15    10 ->  3    11 -> 28    12 -> 23
    13 -> 24    14 -> 25    15 -> 26    16 -> 27    17 -> 16    18 -> 17
    19 ->  2    20 -> 13    21 -> 14    22 -> 22    23 ->  6    24 ->  7
    25 ->  8    26 ->  9    27 -> 10    28 -> 11    29 -> 12    30 -> 29

Two markers stopped being single ranges because the pass broke their runs:
[4-8] is now [18-21,30] and [25,27-29] is now [8,10-12]. Both are correct
Vancouver. Ref 30 (Chekroud 2021) carries the last number because the group in
Discussion, *Comparison with prior work*, is the only place it is ever cited.
The same remap was applied to supplement.md and tripod_ai_checklist.md.

Refs 6-12 (Cepeda, Fabbri, Iveson, Liberman, Lage, Lee DY, Walsh) were added
2026-09-03 from the senior author's review, and were 24-30 before pass three.
VERIFIED against PubMed records and, where obtainable, the papers themselves.
Three had wrong fields as first entered and are corrected here (Cepeda's issue
and pages; Iveson's author list and volume/pages; Walsh's author list). EVERY
DISCRIMINATION FIGURE QUOTED FROM THEM IN THE DISCUSSION IS CONFIRMED:
Liberman AUC 0.83 over a 24-month follow-up in 35,246 eligible people; Lage
0.652 (95% CI 0.623-0.682) in the second health system with top-quintile lift
1.99; Lee DY 0.684 structured-only, 0.569 notes-only, 0.728 combined, 0.794
with MRI as the highest; Walsh 0.58-0.64 internal falling to 0.51-0.58
external. Five of the seven are held as PDFs; Lage and Lee DY are not open
access and have reprint requests drafted.

Ref 11 is Lee DY (multimodal TRD prediction), and it was ref 28 before pass
three and ref 29 before that. The removed LLM-as-a-judge reference was also a
"Lee". There is no longer any other Lee in the list.
-->

1. Al-Harbi KS. Treatment-resistant depression: therapeutic trends,
   challenges, and future directions. Patient Prefer Adherence.
   2012;6:369-388. doi:10.2147/PPA.S29716.

2. Forthman KL, Kuplicki R, Thompson WK, Nemeroff CB, Si Y, Fan CC, et al.
   Treatment resistant depression: socio-demographic characteristics,
   comorbidity and treatment patterns from the All of Us Research Program.
   J Affect Disord. 2025;390:119858. doi:10.1016/j.jad.2025.119858.

3. Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B,
   et al. TRIPOD+AI statement: updated guidance for reporting clinical
   prediction models that use regression or machine learning methods. BMJ.
   2024;385:e078378. doi:10.1136/bmj-2023-078378.

4. Gaynes BN, Lux L, Gartlehner G, Asher G, Forman-Hoffman V, Green J,
   et al. Defining treatment-resistant depression. Depress Anxiety.
   2020;37(2):134-145. doi:10.1002/da.22968.

5. Rush AJ, Trivedi MH, Wisniewski SR, Nierenberg AA, Stewart JW, Warden
   D, et al. Acute and longer-term outcomes in depressed outpatients
   requiring one or several treatment steps: a STAR\*D report. Am J
   Psychiatry. 2006;163(11):1905-1917. doi:10.1176/ajp.2006.163.11.1905.

6. Cepeda MS, Reps J, Fife D, Blacketer C, Stang P, Ryan P. Finding
   treatment-resistant depression in real-world data: how a data-driven
   approach compares with expert-based heuristics. Depress Anxiety.
   2018;35(3):220-228. doi:10.1002/da.22705.

7. Fabbri C, Hagenaars SP, John C, Williams AT, Shrine N, Moles L, et al.
   Genetic and clinical characteristics of treatment-resistant depression
   using primary care records in two UK cohorts. Mol Psychiatry.
   2021;26(7):3363-3373. doi:10.1038/s41380-021-01062-9.

8. Iveson MH, Ball EL, Lo CWH, Falis M, Lewis CM, Whalley HC. Treatment
   resistant depression in electronic health records: definitions matter.
   BMC Psychiatry. 2026;26(1):453. doi:10.1186/s12888-026-08085-y.

9. Liberman JN, Davis T, Pesa J, Chow W, Verbanac J, Heverly-Fitt S,
   et al. Predicting incident treatment-resistant depression: a model
   designed for health systems of care. J Manag Care Spec Pharm.
   2020;26(8):987-995. doi:10.18553/jmcp.2020.26.8.987.

10. Lage I, McCoy TH, Perlis RH, Doshi-Velez F. Efficiently identifying
    individuals at high risk for treatment resistance in major depressive
    disorder using electronic health records. J Affect Disord.
    2022;306:254-259. doi:10.1016/j.jad.2022.02.046.

11. Lee DY, Kim N, Park C, Gan S, Son SJ, Park RW, et al. Explainable
    multimodal prediction of treatment-resistance in patients with
    depression leveraging brain morphometry and natural language
    processing. Psychiatry Res. 2024;334:115817.
    doi:10.1016/j.psychres.2024.115817.

12. Walsh CG, Ripperger M, McCoy TH, Castro V, Hu Y, Kirchner HL, et al.
    Generalizability of risk models for treatment-resistant depression
    across three health systems. medRxiv. 2025. Preprint.
    doi:10.1101/2025.05.21.25328089.

13. Shmatko A, Jung AW, Gaurav K, Brunak S, Mortensen LH, Birney E, et al.
    Learning the natural history of human disease with generative
    transformers. Nature. 2025;647(8082):248-256.
    doi:10.1038/s41586-025-09529-3.

14. Waxler S, Blazek P, White D, Sneider D, Chung K, Nagarathnam M, et al.
    Generative medical event models improve with scale. arXiv.
    2025;arXiv:2508.12104. doi:10.48550/arXiv.2508.12104.

15. Hegselmann S, von Arnim G, Rheude T, Kronenberg N, Sontag D, Hindricks
    G, et al. Large language models are powerful electronic health record
    encoders. arXiv:2502.17403. 2025.

16. González HM, Vega WA, Williams DR, Tarraf W, West BT, Neighbors HW.
    Depression care in the United States: too little for too few. Arch Gen
    Psychiatry. 2010;67(1):37-46. doi:10.1001/archgenpsychiatry.2009.168.

17. Alegría M, Chatterji P, Wells K, Cao Z, Chen CN, Takeuchi D, et al.
    Disparity in depression treatment among racial and ethnic minority
    populations in the United States. Psychiatr Serv.
    2008;59(11):1264-1272. doi:10.1176/ps.2008.59.11.1264.

18. Perlis RH. A clinical risk stratification tool for predicting
    treatment resistance in major depressive disorder. Biol Psychiatry.
    2013;74(1):7-14. doi:10.1016/j.biopsych.2012.12.007.

19. Kautzky A, Baldinger-Melich P, Kranz GS, Vanicek T, Souery D,
    Montgomery S, et al. A new prediction model for evaluating
    treatment-resistant depression. J Clin Psychiatry. 2017;78(2):215-222.
    doi:10.4088/JCP.15m10381.

20. Sheu YH, Magdamo C, Miller M, Das S, Blacker D, Smoller JW.
    AI-assisted prediction of differential response to antidepressant
    classes using electronic health records. npj Digit Med. 2023;6:73.
    doi:10.1038/s41746-023-00817-8.

21. Chekroud AM, Zotti RJ, Shehzad Z, Gueorguieva R, Johnson MK, Trivedi
    MH, et al. Cross-trial prediction of treatment outcome in depression:
    a machine learning approach. Lancet Psychiatry. 2016;3(3):243-250.
    doi:10.1016/S2215-0366(15)00471-X.

22. Hegselmann S, Shen SZ, Gierse F, Agrawal M, Sontag D, Jiang X. A
    data-centric approach to generate faithful and high quality patient
    summaries with large language models. Proc Mach Learn Res.
    2024;248:339-379.

23. Xiao S, Liu Z, Zhang P, Muennighoff N, Lian D, Nie JY. C-Pack: packed
    resources for general Chinese embeddings. In: Proceedings of the 47th
    International ACM SIGIR Conference on Research and Development in
    Information Retrieval (SIGIR '24); 2024 Jul 14-18; Washington (DC).
    New York: ACM; 2024. p. 641-649. doi:10.1145/3626772.3657878.

24. Li C, Qin M, Xiao S, Chen J, Luo K, Shao Y, et al. Making text
    embedders few-shot learners. arXiv:2409.15700. 2024.

25. Zhang Y, Li M, Long D, Zhang X, Lin H, Yang B, et al. Qwen3 embedding:
    advancing text embedding and reranking through foundation models.
    arXiv:2506.05176. 2025.

26. Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O,
    et al. Scikit-learn: machine learning in Python. J Mach Learn Res.
    2011;12:2825-2830.

27. Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In:
    Proceedings of the 22nd ACM SIGKDD International Conference on
    Knowledge Discovery and Data Mining (KDD '16); 2016 Aug 13-17; San
    Francisco (CA). New York: ACM; 2016. p. 785-794.
    doi:10.1145/2939672.2939785.

28. Reimers N, Gurevych I. Sentence-BERT: sentence embeddings using
    Siamese BERT-networks. In: Proceedings of the 2019 Conference on
    Empirical Methods in Natural Language Processing and the 9th
    International Joint Conference on Natural Language Processing
    (EMNLP-IJCNLP); 2019 Nov; Hong Kong. Stroudsburg (PA): Association for
    Computational Linguistics; 2019. p. 3982-3992.
    doi:10.18653/v1/D19-1410.

29. Ferguson M. TRD-EHR: analysis code for treatment-resistant depression
    prediction from electronic health records. GitHub. 2026. URL:
    https://github.com/Pirate-Hunter-Zoro/TRD-EHR [accessed 2026-09-06]

30. Chekroud AM, Bondar J, Delgadillo J, Doherty G, Wasil A, Fokkema M,
    et al. The promise of machine learning in predicting treatment
    outcomes in psychiatry. World Psychiatry. 2021;20(2):154-170.
    doi:10.1002/wps.20882.

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
