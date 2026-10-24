# MP review round of 2026-09-02 (verbatim record)

Delivered as `feedback/`: a tracked-changes manuscript
(`manuscript_09.02.2026.docx`, 64 insertions, 75 deletions, 9 comments), two
supplied replacement documents (`JMIR_Methods_and_Supplement.docx`,
`Integrated_TRD_EHR_Discussion.docx`), and a covering email.

## The email

> Hi Mikey
>
> I edited the manuscript and made substantial revisions and suggestions, I
> also added more literature and changed the discussion. Overall, this is
> coming along very well. You need to make many sections more concise (and I
> gave examples). I have also added a revised methods section and a revised
> discussion section,
>
> Martin

## The nine comments

**[35] Abstract, on "deterministic" (Methods).** "I am not sure what you mean
by that term, you had the GPT generate it, I don't think that counts as
deterministic."

**[50] Introduction.** A block of replacement text plus seven references
(Cepeda 2017, Fabbri 2021, Iveson 2026, Liberman 2020, Lage 2022, Lee 2024,
Walsh 2025).

**[84] Methods heading.** "Your methods section is VERY verbose, 6000 words,
you need to cut this down to about 2000, I will provide you with a document as
a suggestion.."

**[115] Table 1 (participant flow).** "This table should go into a supplement"

**[117] Cohort characteristics paragraph.** "This should be one sentence and
referring to the table, the goal of this manuscript is NOT to go into detail of
the characteristics of TRD"

**[119] Table 2 (cohort characteristics).** "This should be Table 1"

**[136] Subgroup outcome prevalence section.** "This goes into the supplement"

**[172] Figure 11 (ablation forest plot).** "You cannot read the labels of this
figure"

**[176] Discussion heading.** "I will send you a revised discussion section
that includes the most recent literature (which I also cited in the intro),"

## The tracked changes

Terminology, applied throughout: "neural embedding" → "generalized pre-trained
transformer embedding"; "classical machine learning" → "standard machine
learning"; "anchor" → "index" (his Methods and Discussion documents both use
index date / pre-index / post-index throughout).

Condensed rewrites supplied inline for the Abstract, the Introduction, Results
*Subgroup performance*, and Results *Model discrimination*. The remaining edits
are word-level.

One inserted clause was **not** taken: his Abstract insertion glossed the
anchor as "the first instance of antidepressant treatment in the EHR". It is
not — that is the description corrected in the 2026-08-28 round. The index is
the earliest antidepressant prescription recorded on or after the first
documented depression diagnosis, and 24.0% of the cohort carries earlier
antidepressant exposure. The Abstract states the correct definition.

## The follow-up conversation of 2026-09-04

Verbal, and not in the tracked-changes file. Recorded from notes rather than
quoted, except where marked. It has two halves: a verdict on the prose, and six
instructions. **None of it is applied**, for the reason at the bottom.

### The verdict on the writing

The manuscript is too dense. It is correct — he disputed no number and no claim —
but it reads as machine-written, and a sentence has to be read three times before
it gives up its meaning. He asked for the draft to be produced with AI in the
first place, so this is a judgement about the register, not about the method.

He is describing something measurable rather than a matter of taste. Across the
body text, abstract through conclusions, with tables and captions excluded: 311
sentences, mean 26.2 words, median 24, and 23% of them longer than 35 words, the
longest at 86; 74 semicolons, 34 em-dashes, 191 parentheses. Readable scientific
prose sits nearer a median of 18. Nearly every one of those semicolons and
em-dashes is a second or third claim fused into a sentence that already carried
one, which is the mechanism behind reading it three times.

Note what this collides with. Comment 84 cut Methods from 6,057 words to 1,851,
and compression is exactly what produces density. The two requests pull against
each other, and the resolution is fewer claims with more room each — not the same
claims in fewer words.

### Three word changes

| From | To |
| --- | --- |
| deterministic | algorithmic |
| patient | participant |
| trained classifier | machine learning model |

The first follows comment [35]. The reason he gave there — "you had the GPT
generate it" — is wrong on the facts: fixed rules write the narrative, no
generative model participates in its construction, and that is precisely what
"deterministic" was carrying. Concede the word; keep the fact in a clause.

### Two sections leave the packet, both held in reserve

- **The cosine-similarity distribution and its bimodal mode** — Supplement S5,
  the bge-small-en-v1.5 artifact. "Not relevant enough." **Reserved, not cut.**
- **The fusion analysis** — Supplement S7. The same judgement, offered
  unprompted: "honestly neither is the fusion analysis." Also to reserve.

### The Discussion's take-home

"Embedders are useful to match the standards other people have done." Read as:
the point worth leading with is that a general-purpose embedder reaches the
discrimination band the published literature already reports — Lage 0.652, Lee
0.684, Walsh 0.51-0.64 externally, ours 0.657 — without a purpose-built EHR
foundation model. That fits the *Comparison with prior work* section he supplied
and the seven references he added with it. **Confirm before acting on it.** It
reframes *Principal findings* from "the two representations tie" to "the cheap
route reaches the field's standard", which is a different emphasis for the paper.

### Why none of it is applied yet

More rewritten sections are coming. Running the terminology sweep now means
running it twice, once over our text and once over his, so the whole set waits on
his documents. The cost of each item, the exclusions each one needs, and where
every entry lands are in `round_2026-09-02.md`.
