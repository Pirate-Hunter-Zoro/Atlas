<!--
The rationale for the 2026-09-06 refocus onto two points.

WHAT THIS IS. The account of why the manuscript was rebuilt around points instead of
objectives, why the hand-picking emphasis is NOT a third point, what came out, what
went back in, and what is now waiting on the senior author. It is written to be read
by him, so it argues rather than merely records, and it is short enough to read in one
sitting.

HOW THIS ROUND WAS GATED. The point-and-claim map was written first and run through
Paper-Writer's `gates/ladder.py` before a word of prose moved: 2 points, 20 claims,
every claim serving a point or declaring a role, no orphans. The gate output is quoted
in section 5b, and the map itself is `../reserve/point_claim_map.json`.

WHERE THE MECHANICS ARE. `round_2026-09-02.md` is the previous round item by item.
`manuscript_header_through_2026-09-03.md` is the decision history that used to sit at
the top of manuscript.md. `../reserve/llm_similarity_judge.md` is the analysis that
came out, complete. `../reserve/limitations_reserve.md` records the removal that this
round reversed.

Internal. Not part of the submitted packet.
-->

# Why the paper makes two points

**Internal note, 2026-09-06. Not submitted.**

## The short version

The paper had three objectives and no spine. The objectives were three things the
analysis had done rather than three things the paper argues. It now makes two points,
and every section is placed under one of them.

> **Point 1.** A generalized pretrained transformer embedding of a patient narrative
> does not significantly outperform a typed feature vector built from the same record.
> Best against best, +0.008 ROC AUC (95% CI −0.003 to +0.019).
>
> **Point 2.** Nearest-neighbor retrieval over that embedding, the clinical
> digital-twin premise, captures real label-informative structure and still loses
> decisively to a trained model. Nearest 0.594 against random 0.499 and farthest
> 0.432, and 0.594 against 0.657 for a classifier fitted on the same embedding, on
> intervals that do not overlap.

One thing is true of both points and bounds both answers, and it is emphasis rather
than a third point: **in both arms the patient data were hand-picked.** Section 0 is
why that is emphasis and not a point.

Three things follow from adopting the two. The LLM clinical-similarity judge left the
packet. Limitations came back as a section. And the whole manuscript was rewritten to
sentences a reader gets on one pass.

Nothing was deleted. Everything that came out is complete, held in `reserve/`, and
named below.

## 0. The hand-picking emphasis, and why it is not a third point

**A reader can finish this paper believing something it never showed.** The belief is
that the advantage of an embedder is skipping the feature engineering: you throw the
raw patient in, the model puts them somewhere useful, and the parity result proves it
works. Every part of that is wrong here, and it is the most natural wrong conclusion
to draw from a null.

What actually happened is that predictor selection ran once, before either
representation existed, and both representations then encoded the same selection. The
narrative is a fixed template of section headings and field labels walked over that
inventory. So Point 1 compares two encodings of one hand-picked record, and Point 2
describes the geometry of one. The engineering was relocated from designing a feature
vector to designing a narrative template. It was not removed.

**This was briefly written up as a third point on 2026-09-06, and that was wrong.** It
is not a question the paper asks, it has no Results subsection, and calling it a point
made the Introduction promise three answers where the study has two. It is a scope
condition on both answers. It now appears as a bounding fact in the Abstract's
objective, once in the Introduction after the two questions, in the Methods where the
representations are built, in the Discussion, in Limitations, and in the Conclusions.
The manuscript's header comment says not to promote it again.

**It also makes a real question askable, which is why it earns emphasis rather than
one line.** If a whole untailored record could be embedded, would that space predict?
Nobody knows, and this study cannot say. The obstacle is length rather than principle.
Predictors here come from a fixed 730-day window, whereas recorded history reaches a
median of 1,792 days and a maximum of 5,288 across a median of 21 encounters, and an
encoder accepts a bounded input.

That constraint is a property of the tooling and will move. The Implications section
names three ways round it. A hierarchical scheme that embeds encounters and then
embeds their sequence. A long-context encoder. Or a retrieval step that chooses which
parts of a record to encode. Each reintroduces a design decision, and that is itself
worth reporting: there may be no version of this that involves no choices at all.

**One caveat on the length argument, and it is mine rather than the paper's.** The
numbers above are days of history and counts of encounters. They are not tokens. A
21-encounter record might serialize to a few thousand tokens, which several encoders
handle without complaint, so those figures establish that a record is long and not
that it is too long. The rendered narratives in Supplement S5 are 184 words each,
which is the only measured side of the comparison. If the real constraint is known, whether that is a
context-window limit, a batch size or an out-of-memory failure, it should replace the
proxy. Otherwise the honest version is "we did not attempt it" with the length
argument dropped.

**The evidence for the emphasis is the crosswalk**, Supplement S10, which was
previously framed only as a limitation on the parity claim. It now does two jobs and
says so: it bounds Point 1, and it is the row-by-row record that neither arm was
handed a raw record. A reader who doubts the scope statement can check it in the
second column.

## 1. Why points and not objectives

The previous draft opened its Introduction on three objectives: compare the two
representations, test the embeddings across encoders and probe their geometry,
and localize the signal with an ablation. Those are three things the analysis
did. They are not three things the paper argues, and the coincidence that there
were also three of them is worth naming: the count was right and the content
was wrong.

The second and third are support, not findings. The encoder sweep exists to show
that the parity in Point 1 is not an artifact of one encoder. The ablation exists
to show that both representations are reading the same clinical content, which is
the mechanism behind that parity. Presented as objectives in their own right they
read as three loosely related analyses, and a reader who stops after the Results
cannot say what the paper claims.

Retrieval was the genuinely separate question and it was buried. The reason the
retrieval arm exists is the digital-twin idea: that a patient's likely course can
be read off the recorded courses of the patients most similar to them. That is a
real proposal in precision psychiatry, an embedding makes it directly testable,
and this study tests it and finds it wanting. In the previous draft that
motivation appeared nowhere. The arm was introduced as an examination of
"representation geometry", which is what it measures rather than why anyone would
care.

So the Introduction now poses two questions and the paper answers them in
order. The encoder sweep and the ablation sit under Point 1 as what makes it
credible. The digital-twin premise is named in the Introduction, tested in the
Results, and answered in the Discussion. The hand-picking emphasis is stated
once after the two questions and recalled where it bites, and it has no Results
subsection because it is a scope condition rather than an answer.

## 2. What came out, and why

**The LLM clinical-similarity judge.** It was one of four neighbor-weighting
strategies. Under nearest retrieval, the only retrieval scheme anyone would
consider using, it moved discrimination from 0.5939 to 0.5947. It helped only
under random and subsampled retrieval, which are negative controls.

Against that it cost a rubric, two verbatim prompts, four worked examples, a
sub-score audit over a systematic sample of 1.71 million cached judgements, and a
5,000-pair re-judging experiment under a corrected rubric. That is a large amount
of a reader's attention spent on a null result about a weighting scheme layered
on top of a retrieval predictor that is itself not competitive. It was the single
most distracting block in the packet and it served neither point.

It is now `reserve/llm_similarity_judge.md`, complete, with the full four-by-four
grid, every number, and a section recording the one subgroup contrast whose
significance depends on including the judge weightings. The Methods discloses in
one sentence that the two judge-derived weightings were evaluated, that they added
no discrimination under nearest retrieval, and that the analysis is available from
the corresponding author. That is the same disclosure pattern already used for the
matched-input parity re-run and the religion sensitivity analysis.

Neighbor weighting in the paper is now uniform and cosine. The manuscript states
the mechanical reason they agree: within a nearest-neighbor set the similarities
are all high and all close together, so the weights are nearly uniform whatever
the formula.

**One reference left with it.** The LLM-as-a-judge reporting reference existed
only to pre-empt an objection to the judge arm. References 25–31 are now 24–30.
Everything else in the list is unchanged.

## 3. What went back in

**Limitations is a section again**, restored on the user's instruction after being
held out on 2026-09-03 to match the supplied Discussion.

The reason is the first item, and it is the reason the section needed a heading
rather than nine sentences distributed across the paper. The outcome counts
antidepressant switches. Nothing in the record says whether a change followed a
genuine failure to respond. A patient is switched because the drug did not work,
or because it caused intolerable side effects, or because it was unaffordable, or
because they stopped taking it, or because their prescriber prefers switching to
augmenting. All of these increment the count identically and this study cannot
distinguish them. That single fact bounds both of the paper's points, and a
reviewer who goes looking for the heading now finds it.

Every item carries its sources: the consensus TRD definition [2,3], the
documented US disparities in depression treatment that make switching
access-dependent [18,19], the definitions-matter literature [24-26], and the
three-health-system transportability result [30].

The section has ten items rather than the previous nine. The new one is on
retrieval, because retrieval is now one of the two points and its own boundaries
have to be stated: similarity was geometric cosine similarity over an
unsupervised embedding, the neighborhood was fixed at 50, and the neighbor pool
was one cohort. A supervised or metric-learned similarity is untested and might
do better. What the analysis supports is narrower and still substantive.

Both sentences that the 2026-09-03 removal had lost entirely are back: that
dropping the vital signs is arguably the wrong handling for a prediction problem,
and that the reported discrimination is an upper bound on later or external data.

## 4. What the Results now look like

The order changed, and the order was doing damage. The previous draft opened
Results on subgroup performance and confound checks, so a reader met 288
significance contrasts before meeting the finding the paper is about.

| | Previous | Now |
| --- | --- | --- |
| Opens on | Participant flow, cohort, subgroup performance, train/test, confounds | Participant flow, cohort, then the representation comparison |
| Retrieval | One subsection, sixth of nine | Its own block with a cross-encoder table, after Point 1 |
| Validity checks | Three separate subsections, before the main result | One subsection, after both points |
| Main-text tables | 6 | 7 |
| Main-text figures | 12 | 11 |

**One table was added and it is a real result the previous draft did not report.**
Table 7 puts nearest retrieval, random retrieval, and the trained classifier side
by side for all four encoders. Nearest beats random by 0.083 to 0.095 ROC AUC on
every encoder, and falls short of that encoder's own trained model by 0.061 to
0.065 on every encoder. Point 2 was a single-encoder observation before; it is now
a reproduced one. The numbers were already in the results tree and were reported
only as a sentence in the supplement's evaluation-coverage section.

**One figure was dropped**, the confusion matrices for the neighbor-weighted
predictor. No number left with it; the operating characteristics were already in
the table, and the retrieval predictor is not one anybody would set a threshold
on.

**The subgroup analysis was re-corrected over the contrasts the paper reports.**
Dropping two of the four neighbor weightings takes the contrast set from 288 to
240, and Benjamini-Hochberg was recomputed over the 240. Fifty-eight exclude zero
unadjusted and 24 survive, against 72 and 35 before. The reading is unchanged and
slightly cleaner: 21 of the 24 concern how the depression is coded, sex shows no
difference anywhere, and the race contrasts stay directionally positive without
surviving correction. One contrast changes status, and it is recorded in the
reserve document rather than quietly dropped.

## 5. The prose

The verdict from the 2026-09-04 follow-up was that the writing is too dense and
reads as machine-written. That was correct and it was measurable. The submitted
body text ran a mean of 26.2 words per sentence against a readable 18 to 20, with
23% of sentences over 35 words, 74 semicolons and 34 em-dashes.

Both documents were rewritten against that, and both now measure clean:

| | Manuscript | Supplement |
| --- | ---: | ---: |
| Mean words per sentence | 18.9 | 18.3 |
| Longest sentence | 54 | 43 |
| Share over 35 words | 1.9% | 4.4% |
| Semicolons per 1,000 words | 0.7 | 0.3 |
| Clause-joining dashes per 1,000 words | 0 | 0 |

No number moved and no claim changed. The rewriting is splitting, not cutting.

**One thing to flag, because it touches the supplied text.** The Methods is the
senior author's own condensation and the rule has been not to grow it. It was not
grown, and no number in it moved. It was nevertheless edited, and the honest
accounting is this. Twenty-six of its sentences became forty-two. Most of that is
splitting: a semicolon becomes a full stop, a two-clause sentence becomes two.
Three abbreviation redefinitions came out because the Introduction already
defines them. One paragraph was rewritten rather than split, the
neighbor-weighted retrieval paragraph, because the judge weightings left it and
the digital-twin framing went in. And *Statistical analysis* gained one sentence,
saying that the retrieval-against-classifier comparison is reported as marginal
intervals rather than as a paired test, which is the conservative choice.

If he would rather have his sentences back exactly as written, that is a
five-minute revert and the previous text is in git.

## 5b. What the ladder gate said

This is the first packet gated by Paper-Writer's support ladder rather than by a
person reading for coherence. The point-and-claim map was written first and run
through `gates/ladder.py` before any prose moved:

```
points: 2
claims: 20
per point:  p.1 -> 14 claims,  p.2 -> 10   (six serve both)
roles:      setup 2, reporting 1   (3 of 20 = 15%, ceiling 34%)
orphans:    none
planned words serving no point: 0 of 10,770   (ceiling 30%)
```

Three of those lines are worth reading rather than skimming.

**`orphans: none`** means every one of the twenty claims either serves a point or
declares why it is in the paper without serving one. The gate refuses a claim
that does neither, and the honest fix is usually to drop it.

**`0 of 10,770` unladdered words** is the check that would have caught the
similarity-judge supplement in the previous round. It measures how much of the
paper's planned length sits in sections whose claims serve none of its points,
and a graph check cannot see that. A determined writer satisfies a graph check
by attaching claims loosely. Length cannot be argued with.

**The one thing the gate genuinely caught.** Collapsing the map from three
points back to two left claim c.9 still flagged as a headline claim, and it now
served two points at once. A claim that states a point states one, so the gate
refused the map until the flag came off. That is the first time the ladder has
rejected anything, and it was rejecting my own edit rather than a model's
output.

**And one thing this section should not be read as claiming.** The map
otherwise passed on the first run, because it was written by someone who
already knew what the gate checks. That makes this a weak test of the gate and
a reasonable test of the map: it proves the ladder holds, not that the ladder
would have caught a writer who was not trying to satisfy it. The honest verdict
waits for a run where a model writes the map without that knowledge.

## 6. What is waiting on him

Four things, in the order they cost.

**1. The title now names retrieval.** It reads *Typed Feature Vectors,
Generalized Pretrained Transformer Embeddings, and Nearest-Neighbor Retrieval for
Predicting a Treatment-Switch–Defined Electronic Health Record Proxy for
Treatment-Resistant Depression: Retrospective Cohort Study*. His required phrase
is intact. A paper making two points should name both, but the title is his call
and it propagates to the cover letter and the checklist.

**2. Limitations is back and his Discussion has none.** This reverses a decision
taken to match his draft. The argument for reversing it is section 3 above. If he
prefers the section out, the two sentences named there should go into Methods and
into *Implications and future directions* rather than being lost again.

**3. The judge is in reserve.** If he considers the LLM-similarity arm part of the
contribution rather than a distraction, it comes back as a supplement section by
a paste. The case for holding it back is that it changes nothing where retrieval
works, and the case against is that a reviewer might want to see that a clinically
informed similarity was tried.

**4. The take-home he asked about, still unanswered.** His 2026-09-04 note said
"embedders are useful to match the standards other people have done". That reads
as an instruction to lead the Discussion on parity with the published literature (Lage
0.652, Lee 0.684, Walsh 0.51–0.64 externally, ours 0.657) rather than on parity
between our two representations. The Discussion currently leads on the latter and
makes the literature comparison in its own subsection. If he meant the former, it
is a reordering of two paragraphs, not a rewrite. This was raised in the previous
round and has not been answered.

## 7. Three word changes still staged

From the 2026-09-04 follow-up, unchanged and still not applied, because each one
touches text he is rewriting:

- *deterministic* to *algorithmic*, 18 places, which also needs the naming rule
  rewritten in the same edit since "deterministic" is the sanctioned word there.
- *patient* to *participant*, about 261 places, which must not touch the title,
  the verbatim narratives in Supplement S5, or wording quoted from prior studies.
- *trained classifier* to *machine learning model*, 4 places, two of which
  destroy a real contrast: the phrase exists to distinguish the fitted models
  from the neighbor-weighted predictor, and that distinction is now Point 2.

The third one matters more than it did a week ago. Point 2 is a comparison
between a fitted model and a predictor that fits nothing, and it needs two names.
