<!--
Methods reserve: everything the condensed Methods no longer says in the main text.

STATUS: HELD IN THIS FOLDER, NOT PART OF THE SUBMITTED PACKET. The packet is
four documents — manuscript, supplement, TRIPOD+AI checklist, cover letter — and
this is not one of them.

WHY IT EXISTS. The senior author's review of 2026-09-02 (comment 84) called the
Methods section verbose at ~4,600 words and supplied a ~1,600-word replacement,
which the manuscript now carries essentially as written. Almost everything the
condensation removed was RELOCATED into the Supplementary Methods (Supplement
M1-M13) rather than deleted, and those sections are submitted. This document
covers the remainder: passages that survive nowhere in the packet, and passages
that survive only in the supplement where a reader of the main text alone will
not meet them. Each is reproduced verbatim, so restoring one is a paste rather
than a rewrite.

HOW TO USE IT. If a reviewer asks a question this answers, the answer is already
written. Paste the passage back into the named Methods subsection, or into its
M-section if the supplement is the better home, and delete the entry here.

MAINTENANCE RULE. The Methods section does not grow. When something new has to
be said, it goes in the M-section and, if it was ever in the main text, its
removal is recorded here. See the header comment at the top of Methods.

Naming: the two representations are the FEATURE representation ("feature
vector") and the EMBEDDED representation ("the embedding"). Time zero is the
INDEX, never the anchor, except for a retrieval query anchor.
-->

# Methods reserve

**Material removed from the main-text Methods in the 2026-09-02 condensation.
Held for reference. Not submitted.**

**In one line.** Methods went from 2,637 words to 1,851 (1,749 of prose plus the
104-word Figure 1 caption); of the ~790 words removed, all but the eight
passages below are still submitted inside Supplement M1-M13.

## 1. What was actually lost, and what merely moved

The condensation had three different effects, and only the third is a loss.

**Moved and still submitted.** The bulk of it. Source tables, extract-level
filters and ICD code lists; the eligibility cascade; the outcome's inferential
boundary; predictor-selection rationale; missingness frequencies and the
religion age-gradient; the events-per-variable derivation; leakage safeguards;
the retrieval equations, rubric and grid; the six ablation concept definitions;
evaluation coverage; and the bootstrap machinery. All of it is Supplement
M1-M13, which is part of the submission. A reader who wants the detail has it.

**Compressed but preserved.** A claim that used to take a paragraph and now
takes a clause. These are not recorded here — the claim survives, and the
supplement carries the argument.

**Dropped from the packet entirely.** Eight passages, below. None of them
carries a number, and none is load-bearing for a reported result; each is an
argument, a piece of provenance, or a pre-emption of an objection. That is why
they were affordable to cut and why they are worth keeping to hand.

## 2. The eight passages

### 2.1 Setting: why this is a general population, not a psychiatric one

*Was in:* Methods, *Source of data and study design* → **Setting**.
*Now in:* Supplement M1, final paragraph, in shorter form.
*A reviewer asks this when:* they want to know whether the cohort is a specialty
sample, which bears directly on the 17.5% outcome rate.

> The cohort is therefore a general health-system population rather than a
> psychiatric specialty sample: patients enter it by receiving an antidepressant
> somewhere in routine care, not by being referred to psychiatry, and the
> antidepressant index prescription may be written in any of those settings. This
> is a single-centre study in one metropolitan area, which bears directly on the
> demographic composition reported below and on generalizability.

### 2.2 Why the problem list and the encounter diagnoses disagree

*Was in:* Methods, *Source of data and study design* → **Study population**.
*Now in:* Supplement M1, in full.
*A reviewer asks this when:* they cannot see how 29.4% of an analysis cohort
drawn from a depression-flagged extract came through the unflagged arm.

> The flag used to build the extract and the eligibility criteria applied below
> read different parts of the record. The flag was computed from the patient's
> *problem list*, the curated summary of conditions carried on their chart.
> Eligibility here is assessed from diagnosis codes recorded at individual
> *encounters*. A depression code entered at a visit is a documented diagnosis
> whether or not it was ever added to the problem list, and in routine care the
> problem list is frequently not updated, so the two sets overlap without either
> containing the other.

### 2.3 The index-selection algorithm, stated as an algorithm

*Was in:* Methods, *Participants and eligibility* → **Anchor selection**.
*Now in:* Supplement M2, in full, including the 57.9% same-day figure.
*A reviewer asks this when:* they suspect the index date reads post-index data —
which is exactly what the 2026-08-28 round asked, and the answer is no.

> The upstream data-preparation stage assembles, for every patient, the set of
> antidepressant medication orders starting on or after that first
> depression-diagnosis date; the index is the start date of the earliest such
> order, one per patient. Every patient in the analysis cohort therefore has
> exactly one index date, and 57.9% of the candidate orders in that upstream
> table begin on the same day as the first recorded depression diagnosis.
>
> No property of the index is conditioned on data recorded after the index date.
> In particular, adequacy of dose or duration is *not* required of the index
> exposure, so the index is fully observable at the moment the prescription is
> written and the prediction point coincides with it. Post-index information
> enters the study in exactly two places, both concerning eligibility and outcome
> rather than prediction.

### 2.4 The prior-exposure prevalences, in the main text

*Was in:* Methods, *Participants and eligibility*.
*Now in:* Supplement M2, and the numbers themselves are Table 1.
*A reviewer asks this when:* they read "not necessarily the patient's first
lifetime exposure" and want to know how often that actually happens.

> Because the index is tied to the first *documented depression diagnosis*, a
> patient may carry antidepressant courses that began before that diagnosis was
> recorded: 24.0% of the cohort has some recorded pre-index antidepressant
> exposure and 14.7% has at least one pre-index course meeting the 42-day
> adequacy threshold used for the trial-count predictors.

### 2.5 Predictor selection: what rules out a data-driven screen

*Was in:* Methods, *Predictors and patient representations* → **Predictor
selection**.
*Now in:* Supplement M4, first paragraph.
*A reviewer asks this when:* they suspect the predictor set was tuned against
the outcome, which would inflate every reported number.

> No predictor was kept or discarded on the strength of its measured association
> with TRD, and no automated selection step ran at any stage. The predictor list
> was therefore settled before any patient's outcome was consulted, which is what
> rules out the reported performance having been inflated by a selection step
> that had already seen the data it was later scored on.

### 2.6 Why sociodemographic fields were deliberately kept

*Was in:* Methods, *Predictors and patient representations* → **Predictor
selection**.
*Now in:* Supplement M4, third paragraph.
*A reviewer asks this when:* they ask why a model that makes no fairness claim
was given race and social-determinant inputs at all.

> Sociodemographic and social-determinant fields were retained so that the
> semantic-feature ablation could test directly whether the models lean on them,
> rather than leaving that question unanswerable by construction.

### 2.7 The frozen-classifier argument for the ablation

*Was in:* Methods, *Semantic-feature ablation*.
*Now in:* Supplement M11, first paragraph, in shorter form.
*A reviewer asks this when:* they ask why the ablated models were not retrained,
which looks like an oversight until the reason is stated.

> Holding the classifiers *frozen* is deliberate: it answers the
> input-perturbation question "does the embedder's encoding of concept *X* drive
> predictions?" rather than "could a retrained model find a substitute signal and
> route around the ablation?" — a retrained baseline would mask the very
> dependence we set out to measure.

### 2.8 The subsampled retrieval scheme, and what it does not assume

*Was in:* Methods, *Model development* → **Neighbor-weighted retrieval
prediction**.
*Now in:* Supplement M10, final paragraph, in shorter form.
*A reviewer asks this when:* they read "subsampled" and take it as an assumption
that hub vectors exist in this embedding.

> Its *motivation* is to inject diversity into the neighborhood and dilute the
> influence of geometric "hub" vectors — patients who, if present in the
> embedding, would fall among the nearest neighbors of almost every anchor and be
> returned repeatedly by a pure nearest search. The scheme was designed to test
> whether discrimination survives when the very closest, and potentially
> redundant, neighbors are replaced by merely similar ones; whether such hubs
> actually distort this particular cohort is an empirical question the scheme
> probes rather than a mechanism we assume. In the event, subsampled retrieval
> landed between random and nearest and stayed below nearest, so no strong hub
> effect was needed to account for the results.

## 3. TRIPOD+AI coverage after the cut

No checklist item lost its home. Every row of the completed checklist that used
to point at a Methods subsection now points at that subsection, at its M-section,
or at both, and the checklist was updated in the same pass as the condensation.
The items that moved furthest are the ones whose whole substance is now
supplementary:

| Item | Was | Is |
| --- | --- | --- |
| 5a (data sources, representativeness) | Methods, *Source of data and study design* incl. *Setting* | Methods, *Study design and data source*; Supplement M1 |
| 6b (eligibility) | Methods + Results, Table 1 | Methods; Supplement M2, Table M1 |
| 9a (predictor pre-selection) | Methods, **Predictor selection** | Methods; Supplement M4 |
| 10 (study size, EPV) | Methods, *Sample size and events per variable* | Supplement M7; Table 6 caption |
| 11 (missing data) | Methods, *Missing data* | Methods; Supplement M6 |
| 12a (partition) | Methods, *Train/test split* | Methods; Supplement M8 |

The one thing a main-text-only reader now loses is the derivation of
events per variable. The term is still defined where it is used, in the Table 6
caption, and the full derivation is Supplement M7.

## 4. What this document is not

It is not a second Methods section and must never be cited from the manuscript.
It is not a record of the analyses themselves — the matched-input parity result
has its own reserve report (`matched_input_parity.md`) and the religion
sensitivity analysis will have its own. And it is not a place to put new
material: anything new goes in an M-section, and only text that has been
*removed* from the packet is recorded here.
