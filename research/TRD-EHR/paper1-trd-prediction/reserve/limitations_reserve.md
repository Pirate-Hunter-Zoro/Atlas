<!--
Limitations: the section, held out of the packet.

STATUS: SUPERSEDED 2026-09-06. LIMITATIONS IS BACK IN THE MANUSCRIPT.

The section was removed on 2026-09-03 to match the senior author's supplied
Discussion, which has none. It was restored on 2026-09-06 on the user's explicit
instruction, as part of the refocus onto the paper's two main points, because the
first limitation -- that a medication change made for a reason other than the
drug not working is invisible to this study -- is the binding constraint on both
of them and needed a heading a reviewer could find.

What is in the manuscript now is NOT this text verbatim. It was rewritten to the
one-read prose contract and it gained a tenth item, on the single form in which
retrieval was tested, because retrieval is now one of the paper's two points and
its own boundaries have to be stated. Both sentences recorded in section 3 below
as having left the packet are back in it.

This file is kept as the record of the removal and of the audit in section 2,
which is still the right place to look for where each limitation ALSO lives
outside the Discussion. Read section 4 as the earlier draft of the section, not
as what is submitted.

WHY THIS IS LESS DRASTIC THAN IT SOUNDS, AND EXACTLY HOW MUCH LESS. Nine named
items came out. Seven of them say something the packet still says somewhere
else -- his Methods absorbed several of them wholesale, the Supplementary
Methods carry the rest, and his own Discussion makes the fairness and
outcome-proxy arguments in its own words. Section 2 below is that audit, item by
item, with where each one now lives. TWO things left the packet and are
nowhere in it; they are section 3, and they are the two worth raising.

WHAT IT COSTS ON THE CHECKLIST. TRIPOD+AI item 26 asks for a discussion of
limitations. The checklist row now points at the places that carry them --
Discussion *Clinical interpretation*, *Comparison with prior work* and
*Implications for validation and clinical use*, plus Methods and Supplement
M1-M13 -- which is true, and is a weaker answer than a section with the word
Limitations on it. A reviewer who looks for the heading will not find one.

HOW TO PUT IT BACK. Paste section 4 in as `## Limitations`, between
*Comparison with prior work* and *Implications for validation and clinical use*.
Then restore the cross-references listed in section 5, which were repointed at
other homes when the section came out.

Naming: the two representations are the FEATURE representation ("feature
vector") and the EMBEDDED representation ("the embedding", "the generalized
pretrained transformer embedding"). Time zero is the INDEX, never the anchor.
-->

# Limitations

**The record of a removal that was reversed. Not submitted.**

**In one line.** Nine named items came out of the Discussion on 2026-09-03 to
match the supplied draft, which has none. The section is back in the manuscript
as of 2026-09-06, rewritten and with a tenth item added, so what follows is the
audit of where each limitation also lives and the earlier text of the section
rather than the submitted wording.

## 1. Why it is out

The senior author's Discussion of 2026-09-02 was taken as written, and it has no
Limitations section. Keeping one alongside it would have been arguing with the
draft rather than applying it. The judgement is the authors' and will be raised
with him directly; until then the section lives here.

## 2. What survives the removal, and where

Seven of the nine say something the packet still says. Checked against the
manuscript and supplement as built on 2026-09-03, not from memory.

| Item | Still said in |
| --- | --- |
| **Representativeness** | Methods, *Study design and data source* (one community health system, Tulsa); Supplement M1, which carries the setting and the single-centre constraint |
| **Outcome definition** | Methods, *Outcome* (treatment-switch proxy, adequacy unverified, not validated against chart review); Supplement M3; Discussion, *Clinical interpretation*, which makes the same argument at length |
| **Missing data** | Methods, *Missing data and sample partition*; Supplement M6 (frequencies, the religion age gradient, why no imputation model was defensible) |
| **Validation** | Methods, *Study design and data source* (internal validation by random split, not temporal or external); Supplement M7 for the events-per-variable shortfall; Discussion, *Implications for validation and clinical use* |
| **Ablation scope** | Methods, *Model development*, **Semantic-feature ablation** (the three questions it cannot answer); Discussion, *Implications*, which names joint perturbation as the open question |
| **No representational advantage** | Methods, *Statistical analysis and performance metrics* (no equivalence or noninferiority margin prespecified); Discussion, *Principal findings* (parity, not superiority) |
| **Fairness** | Discussion, *Principal findings* ("This is not a fairness result") and *Clinical interpretation* (a care-process phenotype can reproduce inequities with protected attributes omitted); Results, *Subgroup performance* and Supplement S10 for the evidence itself |
| **Operating point and calibration** | Methods, *Statistical analysis and performance metrics*, which states both the optimism and the case-enriched calibration outright |
| **Representation parity** | Methods, *Predictors and patient representations* (field inventories are not identical, so the comparison is between complete pipelines); Supplement S11, the field-level crosswalk |

## 3. What actually left the packet

Two sentences, and nothing else in the packet stands in for them. They are the
two to raise.

**The missingness handling may be the wrong one for a prediction problem.** The
packet says the vital signs were dropped because their recording is associated
with the outcome, and that this rules out missingness completely at random
without identifying a mechanism. It no longer says the self-critical half:

> It is also arguably the wrong handling for a prediction problem, where an
> informative pattern of missingness is usable signal rather than a nuisance:
> the missingness in fields such as religion and race/ethnicity is likewise
> associated with TRD.

**The reported discrimination is an upper bound.** The packet says the study is
an internal validation by a single random split and that transportability is
untested. It no longer draws the conclusion:

> Reported discrimination should be read as an upper bound on what the same
> models would achieve on later data or in another system.

Both are one sentence. If the section stays out, the cheapest repair is to put
these two back into Methods and into *Implications for validation and clinical
use* respectively, where they would sit without reintroducing a heading.

## 4. The section, verbatim

Paste this back as `## Limitations`, between *Comparison with prior work* and
*Implications for validation and clinical use*.

### Limitations (as it stood)

**Representativeness.** This is a single-centre study drawn from one
community health system in a single metropolitan area, and the cohort
skews middle-aged and older (mean age 54.4; 34.7% aged ≥65),
predominantly female (72.5%), overwhelmingly White (80.0%) and
English-preferring (98.9%). Both the single-centre design and that
demographic profile limit transfer to more diverse or non-English-
preferring populations and to health systems whose case mix or
prescribing culture differs. Because the index prescription can be
written anywhere in the system rather than in specialty psychiatric
care, the cohort is also weighted toward routine rather than referred
management.

**Outcome definition.** The target is a treatment-switch proxy rather
than a measured treatment response. It will over-count patients who
cycled through agents for reasons unrelated to efficacy and under-count
patients who remained on a single inadequate agent without ever
switching — the latter arguably the more clinically concerning group,
and one this study cannot see at all. Because the same proxy defines the
outcome in both study arms it does not bias the head-to-head comparison,
but it bounds what the absolute discrimination means. Two things would
sharpen it and neither is done here: validation of the label against
chart-reviewed or symptom-scale-confirmed non-response, and a
higher-specificity label requiring documented post-index adequate
courses and clinically plausible intervals between switches.

**Missing data.** The three vital-sign columns were dropped rather than
imputed because their recording is associated with the outcome being
predicted. That association rules out missingness completely at random
but does not identify the mechanism, so dropping the columns is a
conservative handling rather than a mechanism-justified one, and it
costs three genuinely clinical predictors. It is also arguably the wrong
handling for a prediction problem, where an informative pattern of
missingness is usable signal; the missingness in fields such as religion
and race/ethnicity is likewise associated with TRD.

**Validation.** This is internal validation by a single random split of
one health system's records spanning 2016–2024. There is no temporal
split and no external cohort, so nothing here speaks to transportability
across time or site, and the study cannot detect the coding,
documentation, and prescribing drift that accumulates over a nine-year
window — a random split distributes any such drift evenly across both
sides and hides it. Reported discrimination should be read as an upper
bound on what the same models would achieve on later data or in another
system. The embedded representation also runs below the conventional
events-per-variable threshold by construction on three of the four
encoders (EPV ≈ 1.5–2.3); the feature-vector model comfortably exceeds
it at ≈65.

**Ablation scope.** The ablation isolates one named concept at a time
and cannot disentangle co-correlated clinical features without joint
perturbation.

**No representational advantage.** The embedding held no significant
advantage over the transparent feature vector on the primary encoder.
Its appeal is therefore parity without an explicit feature vector, plus
stability across encoders — but this is not a free lunch: the embedding
still depends on the hand-built deterministic narrative, which required
the same parsing and structuring of the raw record. The engineering
effort is relocated from designing a feature vector to designing a
narrative template, not eliminated. Because no equivalence or
noninferiority margin was prespecified, the correct statement is that
this study found no evidence of superior internal discrimination for the
embedding, bounded at roughly 0.02 AUC by the interval's own width, and
not that the two representations are equivalent.

**Fairness.** This study reports no fairness evidence. The ablation
establishes only that neither model's predictions rely on the
race/ethnicity and social-determinant fields supplied directly to it,
and it leaves three questions open: sociodemographic information may
still reach the models indirectly through correlated psychiatric,
medication, or utilization content; the outcome label is derived from
prescribing behaviour and so may itself be inequitably distributed,
given documented racial and ethnic disparities in the delivery of
depression treatment in the United States [18,19]; and age, sex,
preferred language, marital status, religion, and smoking status remain
in both representations and were never permuted. Subgroup discrimination
and calibration are reported (Results, *Subgroup performance*;
Supplement S10) and do not return a uniform null: sex shows no
difference anywhere, whereas the White-minus-non-White contrasts are
directionally positive throughout without surviving correction, and
non-White calibration is materially worse in the feature-vector arm.
This cohort therefore neither establishes a race-associated performance
gap nor excludes one, and the reason is power rather than ambiguity. A
level-by-level race breakdown is not estimable here, so the groups that
matter most are the ones this cohort cannot resolve; a full fairness
assessment needs a cohort whose minority strata are large enough to
estimate.

**Operating point and calibration.** The Youden-J threshold was selected
on the same held-out patients the models were then scored on, so the
reported sensitivity and specificity are optimistic and are not
candidate operating characteristics. Calibration is likewise measured
inside a case-enriched sample whose 17.5% TRD rate is a design property
rather than a population prevalence, so calibration in the large is
calibration to this cohort and does not transfer.

**Representation parity.** The two representations are built from the
same timeline-sliced record but do not receive an identical field
inventory, so the head-to-head comparison is a comparison of encodings
and of the fields each encoding happens to carry. The field-level
crosswalk is Supplement S11: eleven fields are asymmetric and ten of
them favour the narrative — the index date and a recorded
sexual-orientation field, which the feature matrix has no column for;
the three within-patient mean vital signs, dropped from the matrix but
still rendered; four sociodemographic fields where the matrix collapses
raw values into coarse categories and the narrative prints the raw
value; and three medication blocks where the matrix carries a count and
the narrative names the ingredients. One field favours the feature
matrix: pre-index history length, which the narrative does not render.
Because the deltas involved (≈0.008 AUC on the head-to-head contrast)
are the size of the effect under test, this bounds the parity claim
rather than merely qualifying it, and the direction is predictable:
closing the gap should raise the feature arm relative to the embedded
one. A re-run of the primary comparison with the two largest asymmetries
closed leaves the best-versus-best contrast a null; that analysis is
available from the corresponding author.

## 5. The cross-references that were repointed

Restoring the section means restoring these, which were sent to other homes when
it came out. Each is listed as it now reads.

| File | Now points at | Pointed at |
| --- | --- | --- |
| `../manuscript.md`, Discussion *Principal findings* | Results, *Subgroup performance* | *Limitations* |
| `../supplement.md` M6 | Methods, *Missing data and sample partition* | main text, *Limitations* |
| `../supplement.md` S3 | Discussion, *Implications for validation and clinical use* | *Limitations* |
| `../supplement.md` S6 | Methods, *Predictors and patient representations*; Supplement S11 | *Limitations*, **Representation parity** |
| `../supplement.md` S10 | Discussion, *Principal findings* | *Limitations*, **Fairness** |
| `../supplement.md` S11 | Methods, *Predictors and patient representations* | *Limitations*, **Representation parity** |
| `../tripod_ai_checklist.md` items 3b, 3c, 5a, 11, 14, 15, 26, 27c | the sections named in each row | *Limitations* and its named items |
| `matched_input_parity.md` | Methods, *Predictors and patient representations* | Limitations, **Representation parity** |
