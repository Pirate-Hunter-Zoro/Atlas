<!--
The 2026-09-02 review round, in brief.

WHAT THIS IS. The short, plain-language version of what the senior author asked
for on 2026-09-02 and what was done about each item — one screen per section, no
argument, no numbers that are not needed to see whether a request was met. It is
for a reader who wants to know the state of the revision in five minutes.

THE THREE DOCUMENTS AND WHICH IS WHICH, so none of them gets read for the wrong
thing:
  MP_review_latest.md     what he sent, verbatim. The record.
  round_2026-09-02_brief.md  this file. What was asked, what was done.
  round_2026-09-02.md     the full item-by-item account, with the reasoning,
                          the word counts, the verification tables, and the
                          arguments that exist nowhere else.
When this file and the long one disagree, the long one is right and this one is
stale.

Not part of the submitted packet.
-->

# The 2026-09-02 revision, in brief

**Internal. Not submitted.** The full account with all reasoning is
`round_2026-09-02.md`; the verbatim record of what was sent is
`MP_review_latest.md`.

## What arrived

Four things, on 2026-09-02: a tracked-changes manuscript carrying 64 insertions,
75 deletions and 9 comments; a replacement Methods section with its own
supplementary appendix; a replacement Discussion carrying new literature; and a
covering email. All of it was applied on 2026-09-03.

The email's substance was one sentence — *you need to make many sections more
concise* — plus notice that the Methods and Discussion documents were coming.

## The nine comments, and what happened to each

| # | What he asked for | What was done | Status |
| --- | --- | --- | --- |
| 35 | Doubted "deterministic" — thought a GPT wrote the narratives | Answered in the text, not argued. No generative model builds a narrative; a fixed renderer walks the record. The Abstract now says so in plain words, and his own Methods says the same in his | Done |
| 50 | Replacement Introduction plus seven new references | Taken as written. All seven references verified against PubMed; three had wrong fields as first entered and were corrected. Every performance figure quoted from them was checked against the source | Done |
| 84 | Methods is 6,000 words, cut it to about 2,000 | His supplied Methods **is** the Methods now, at 1,851 words. Nothing was deleted — what came out went to a new Supplementary Methods block, and eight passages that survive nowhere in the packet are held in `../reserve/methods_reserve.md` | Done |
| 115 | Move the participant-flow table to the supplement | Moved, beside the eligibility cascade it belongs to. Results keeps the two numbers a reader needs and points at it | Done |
| 117 | Cohort characteristics should be one sentence referring to the table | Done, and it is literally one sentence. It replaces a 1,017-word paragraph | Done |
| 119 | Cohort characteristics should be Table 1 | Renumbered, and every table after it moved up. One table was dropped outright rather than renumbered, its two numbers now stated in Methods | Done |
| 136 | Move subgroup outcome prevalence to the supplement | Moved in full. Subgroup *performance* — a different analysis, and the one that answers his previous round — stays in Results | Done |
| 172 | Cannot read the labels on the ablation figure | Fixed, and it was a real defect: the figure was drawn far too wide, so it shrank 3.3× on the page and its labels landed at about 4.5pt. Redrawn as a 2×2 grid with labels on every panel. No number changed | Done |
| 176 | A revised Discussion was coming | Taken as written, including its new *Comparison with prior work* section | Done |

Eight of the nine were preferences about structure and length. One — the
unreadable figure — was a defect, and it was the only comment that named
something wrong rather than something he wanted differently.

## What the packet looks like now

| | Before | After |
| --- | ---: | ---: |
| Manuscript | 17,221 words | 11,149 |
| Methods | 6,057 | 1,851 |
| Discussion | 2,925 | 1,903 |
| Results | 5,104 | 4,200 |
| Main-text tables | 8 | 6 |
| References | 24 | 31 |
| Figures | 12 | 12 |

The manuscript is 35% shorter. **Nothing was deleted to achieve that.** Material
either moved into the Supplementary Methods, which is submitted, or into one of
four reserve documents held in this folder and deliberately not submitted, each
of which says why it is held back and what question would call it out.

Two naming decisions were taken across the whole packet because his documents
took them: time zero is the **index** date rather than the anchor, and the
embedding is a **generalized pretrained transformer embedding** — in the title
too. One of his inserted clauses was *not* taken: his Abstract glossed the index
as the first antidepressant in the record, which is the description corrected in
the previous round. The Abstract states the correct definition.

## The analysis his supplement asked for

His supplied supplementary methods wanted one sensitivity analysis: does the
result depend on religion being kept, given how often it is unrecorded?

**The real question was the missingness, not the field.** Religion is unrecorded
for 29.4% of patients, and unevenly — 43.8% of 18-to-29-year-olds against 17.5%
of those 65 or older. Both representations make that blank readable, one as its
own category and one as the printed word *Missing*, so a model could lean on the
silence as an age proxy without ever using a recorded religion. Permuting the
field, which the existing ablation slate does, cannot detect that: it shuffles
recorded values among the patients who have one and leaves every blank exactly
where it was. Only removing the field takes both away.

So the field was removed from both representations — the column out of the
feature matrix, the line out of the narrative, which was then re-rendered and
re-embedded — and each stripped arm was scored against its own comparator on the
same held-out patients.

**Every contrast is a null.** Discrimination moves by at most three
thousandths of an AUC point anywhere, and every confidence interval includes
zero. The field is not carrying the result, and neither is the shape of its
silence.

Two things about how that was done are worth a sentence each, because both were
decided before the numbers existed:

- **The threshold was fixed in advance**, in writing, in the project task list:
  a null and the finding stays out of the paper as reassurance; anything moving
  and it goes *in* as a finding, with Limitations gaining a clause. Every
  threshold is defensible after the fact, so it was set before.
- **The comparator was chosen to be honest rather than flattering.** The stripped
  narrative arm was scored against an earlier re-render that changed no content at
  all, not against the published run — because a bare re-render moves the
  embedding slightly on its own, and scoring against the published run instead
  would have returned a point estimate three times larger that came within a
  thousandth of looking significant. The comparator is what kept a null from
  being written up as a near-miss.

**Where it went.** The write-up is `../reserve/religion_sensitivity.md`, with its numbers
tracked beside it in `../reserve/religion_results/`, held out of the packet on
the same reasoning as the matched-input parity report. In the submission itself
it is two clauses: Supplement M6 no longer says no such analysis was performed
and states the null instead, and the TRIPOD checklist's missing-data row carries
it beside the other re-run. Nothing else in the packet moved.

## The follow-up of 2026-09-04, which is staged and not done

A second round arrived verbally on 2026-09-04. It is recorded in
`MP_review_latest.md` and costed item by item in `round_2026-09-02.md`. **None of
it is applied**, because he is sending more rewritten sections and every item
would otherwise be done twice.

**The verdict on the prose.** Too dense. Correct — no number and no claim was
disputed — but it reads as machine-written, and a sentence has to be read three
times. This is measurable rather than a taste: the body text runs a mean of 26.2
words per sentence against a readable 18-20, 23% of sentences are over 35 words,
and it carries 74 semicolons and 34 em-dashes, nearly every one of which fuses a
second claim into a sentence that already had one. Worth raising with him: his
own comment 84 cut Methods from 6,057 words to 1,851, and compression is what
causes density. Shorter and clearer are not the same instruction.

**Three word changes**, all waiting on his documents: deterministic to
algorithmic (18 places), patient to participant (about 261), trained classifier
to machine learning model (4). The first needs the `manuscript.md` naming rule
rewritten in the same edit, since "deterministic" is the sanctioned word there;
the second must not touch the title, the verbatim narratives in Supplement S6,
or wording quoted from prior studies; the third destroys a real contrast in two
of its four uses, where the phrase exists to distinguish the fitted models from
the neighbor-weighted predictor.

**Two sections move to reserve, and are not cut.** The cosine-similarity
bimodality (Supplement S5) and the fusion analysis (Supplement S7). Both are
supplement-only already, so the packet loses two sections and gains two reserve
documents; the work is the renumbering that follows and the five live
cross-references into them.

**One thing to confirm before acting.** His note on the Discussion's take-home —
"embedders are useful to match the standards other people have done" — reads as
an instruction to lead on parity with the published literature (Lage 0.652, Lee
0.684, Walsh 0.51-0.64 externally, ours 0.657) rather than on parity between the
two representations. That is a better story than the section now tells, and it is
his Discussion, so ask.

## What is left

**Nothing analytical and nothing mechanical**, and nothing that is not waiting on
him. All three review rounds are
closed, every analysis any of them asked for has reported, all four packet
documents build clean, and no placeholder marker remains anywhere.

All three review rounds are closed, every analysis any of them asked for has
reported, all four packet documents build clean, and no placeholder marker
remains anywhere. The 2026-09-04 follow-up above is staged and waits on his
rewritten sections.

Six questions want the authors' judgement rather than anyone's work, and they are
the list for the covering note:

1. The sampling-frame framing — the extract is case-enriched by design, and how
   forcefully to say so is a choice.
2. Whether the classifier-by-representation interaction deserves more than the
   two paragraphs it gets.
3. Whether the fusion analysis should have stayed in the main text at all. He
   asked for it to move *into* Results; it has since moved out to the supplement
   entirely.
4. Whether the retrieval and judge arm belongs in the supplement.
5. Whether the sparsity sentence — 385 of 4,096 dimensions carrying weight —
   should carry a clause, now that a re-render has been shown to select a dense
   solution that discriminates just as well.
6. **Limitations: in or out.** This is the only one of the six with a cost rather
   than a preference attached, and it is the one to raise with him.

On that last one: his Discussion has no Limitations section, so the packet has
none. Seven of the nine disclosures still exist somewhere in the submission —
his own Methods absorbed several, the Supplementary Methods carry others, and his
Discussion argues fairness and the outcome proxy at length in his own words. Two
are nowhere in the packet, and both are one sentence: that dropping the vital
signs is arguably the wrong handling for a prediction problem, where an
informative pattern of missingness is usable signal rather than a nuisance; and
that the reported discrimination should be read as an upper bound on what the
same models would manage on later data or in another system. The reporting
checklist's limitations row now points at scattered places instead of a heading,
which is true and weaker than a section with the word on it — a reviewer looking
for the heading will not find one. `../reserve/limitations_reserve.md` holds the section
intact either way, so this is reversible in an afternoon.

Two loose ends that block nothing: two of the new references are not open access,
so reprint requests are drafted, though every figure quoted from them is already
confirmed from the published abstracts; and two citation fields want a check at
proof stage.
