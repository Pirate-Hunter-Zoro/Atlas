<!--
The LLM clinical-similarity judge: the reserve report.

STATUS: COMPLETE, AND NOT PART OF THE SUBMITTED PACKET, as of 2026-09-06.
Every number here was produced by the published pipeline run and none of it is
provisional. It is held back because it does not serve either of the paper's
two points, not because it is unfinished.

WHY IT CAME OUT. The judge was one of four neighbor-weighting strategies in the
retrieval arm. Under nearest retrieval -- the only retrieval scheme anyone
would consider using -- it moved discrimination from 0.5939 (cosine) to 0.5947,
a difference of eight ten-thousandths of an ROC AUC point. It helped only under
random and subsampled retrieval, which are negative controls. Against that, it
cost the packet a rubric, two verbatim prompts, four worked examples, a
sub-score audit over a 1-in-57 systematic sample of 1.71 million cached
judgements, and a 5,000-pair re-judging experiment under a corrected rubric.
That is a large amount of a reader's attention spent on a null result about a
weighting scheme layered on top of a retrieval predictor that is itself not
competitive with a trained model.

The paper's Methods discloses in one sentence that the two judge-derived
weightings were evaluated, that they added no discrimination under nearest
retrieval, and that the analysis is available from the corresponding author.
This is that analysis.

WHAT THE PAPER STILL SAYS ABOUT IT. Neighbor weighting in the submitted paper
is uniform and cosine only (main text, Table 6). The subgroup analysis
(Supplement S9) contrasts the two reported weightings; the two judge-derived
weightings were computed and are recorded in section 3 below, along with the
one subgroup contrast whose Benjamini-Hochberg survival depends on including
them.

WHAT WOULD BRING IT BACK. A reviewer asking whether a clinically informed
similarity measure would rescue retrieval. The answer here is that this one
does not, and section 1 is the evidence.

Naming: the two representations are the FEATURE representation ("feature
vector") and the EMBEDDED representation ("the embedding"). "Rule-based" is not
an alias for either; see the naming block in ../manuscript.md.
-->

# The LLM clinical-similarity judge

**A reserve analysis for the TRD-prediction manuscript. Not submitted.**

**Result in one line.** Weighting retrieved neighbors by an outcome-blind
`MedGemma-27B` clinical-similarity score does not improve nearest-neighbor
prediction over plain cosine weighting (ROC AUC 0.5947 against 0.5939), and
helps only under retrieval schemes that are deliberately uninformative.

## 1. The result the paper rests on

The full four-by-four grid of retrieval scheme against weighting strategy, on
the primary `Qwen3-Embedding-8B` encoder and the 8,516 held-out anchors, is
below. The two right-hand columns are the judge-derived weightings. The two
left-hand columns are what the submitted paper reports (main text, Table 6).

***Table R1.** Neighbor-weighted ROC AUC by retrieval scheme and weighting
strategy (embedded representation, held-out test set; K = 50 neighbors).
"LLM" weights each neighbor by the judge's overall similarity score;
"combined" by the harmonic mean of cosine and judge similarity. For reference,
embedded logistic regression on the same patients reaches 0.657.*

| Retrieval scheme | Uniform | Cosine | LLM | Combined |
| --- | ---: | ---: | ---: | ---: |
| Nearest | 0.5934 | 0.5939 | 0.5947 | 0.5955 |
| Subsampled | 0.5428 | 0.5439 | 0.5541 | 0.5522 |
| Random | 0.4945 | 0.4989 | 0.5170 | 0.5117 |
| Farthest | 0.4341 | 0.4321 | 0.4358 | 0.4338 |

Three things follow, and the first is the one that decided the section's fate.

**Where retrieval already works, the judge adds nothing.** Under nearest
retrieval the four weightings span 0.5934 to 0.5955, a range of 0.002 ROC AUC
against bootstrap intervals roughly 0.032 wide. When the 50 retrieved patients
are already the most similar available, there is almost nothing left for a
similarity opinion to re-order.

**Where retrieval does not work, the judge helps.** Under random retrieval the
judge lifts ROC AUC from 0.4945 to 0.5170, and under subsampled retrieval from
0.5428 to 0.5541. It is concentrating weight on the few clinically congruent
patients a non-targeted draw happens to include. Consistent with that, the
judge's effective sample size falls below the uniform value (nearest mean ESS
40.6 against 50.0), so it is genuinely reweighting rather than passing the
neighborhood through unchanged.

**Neither case is a use case.** Random and subsampled retrieval are negative
controls. Improving a predictor one would never deploy, on a scheme that
remains below the one that is not improved, does not bear on either of the
paper's two points.

## 2. The judge itself

What follows is the supplement section as it stood in the packet through the
build of 2026-09-03, reproduced without change. Section numbering (S1.1 to
S1.6) and its internal figure number (Figure S8) are as they were then, and do
not correspond to the submitted supplement's current numbering.

# Supplement S1. LLM clinical-similarity judge

## S1.1 Task

In the neighbor-weighted prediction arm, the LLM weighting strategy used a
large language model (`MedGemma-27B`) as a clinical-similarity judge. For each
anchor–neighbor pair the judge received the two patients' deterministic
narratives and returned a structured JSON score. Only the integer
`overall_similarity` field (0–100), rescaled to the unit interval, was used as
the neighbor weight; the per-dimension sub-scores and free-text lists were
retained for auditing only and did not enter the prediction. The judge was run
with cached results (each unordered pair scored once and stored), so repeated
runs are deterministic with respect to the cache.

## S1.2 System prompt (verbatim)

```text
You are a clinical similarity scorer for major depressive disorder (MDD).
Compare two patient narratives that contain only structured EHR data from a fixed baseline window.

Judge similarity ONLY on factors that affect antidepressant response/tolerability.
Treat "Missing" as unknown (neutral). Treat "Absent" as truly absent. Do not infer beyond text.

Weight these dimensions when scoring (sum=100):
1. Baseline symptom phenotype (PHQ-9 subitems): 25 points
2. Psychiatric comorbidity & threat/anxiety/trauma & SUD/suicidality: 20 points
3. Medical/metabolic & pain/NSAIDs: 20 points
4. Treatment exposure & medication burden (polypharmacy, prior adequate trials, 3y complexity): 20 points
5. Social/functional access (no-show, marital/employment/SDOH): 10 points
6. Safety flags (contraindications): 5 points

Return JSON only.
Do not repeat items in lists.
Do NOT provide explanations, reasoning, or calculations. Output raw JSON only.
```

## S1.3 User prompt and output schema (verbatim)

The two narratives are injected at `{narrative_a}` and `{narrative_b}`.

```text
INDEX PATIENT:
{narrative_a}

CANDIDATE PATIENT:
{narrative_b}

Limit "top_similarity_drivers" and "key_mismatches" to at most 5 items each. Return this JSON:
{
    "overall_similarity": 0-100,
    "phenotype": 0-100,
    "psych_comorbidity": 0-100,
    "metabolic_pain": 0-100,
    "treatment_burden": 0-100,
    "social_functional": 0-100,
    "safety": 0-100,
    "top_similarity_drivers": ["driver 1", "...up to 5"],
    "key_mismatches": ["mismatch 1", "...up to 5"]
}

Scoring rules:
- Same band (e.g., NSAID 0 vs 1) = small penalty; different band (0 vs >=2) = large penalty.
- Reward matches on polypharmacy, pain/NSAIDs, anxiety/fatigue most.
- If a dimension has 'Missing' data, strictly output the value 0 for that score.
```

## S1.4 Worked examples

The examples below are drawn from the extremes of the judged distribution
across the primary `Qwen3-Embedding-8B` encoder's neighborhoods: the five
lowest- and five highest-scoring anchor–neighbor pairs, extracted by
`scripts/pipeline/neighbors/llm_similarity_audit.py` and written in full to
`results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/llm_audit/judgement_{id_a}_{id_b}.txt`.
On the current run the five lowest all scored 25 and the five highest scored
98–100. Two of each are reproduced here in full; the remaining responses are
shown as JSON only.

Neither band admits a meaningful internal ranking, so the examples are labelled
as *low* and *top-band* rather than as "lowest", "second-lowest" and so on. At
the bottom, all five pairs are tied at exactly 25; at the top, the five are
effectively tied at the ceiling (98–100). The score-98 pair is reproduced in
full because it is the cleanest near-duplicate, and a score-100 pair follows to
illustrate a sub-score artifact (S1.5) — a choice of illustration, not an
ordering.

### Low-similarity example (score 25) — dissimilar patients

> **Narrative A** — MDD (Single Episode, Unspecified); Female, 55, Divorced,
> Spanish-preferring, never-smoker; no psychiatric comorbidity, no suicidality;
> no medical comorbidity; 0 prior adequate AD trials; 0 active meds; no safety
> flags.
>
> **Narrative B** — MDD (Recurrent, Moderate); Male, 77, Married, heavy smoker;
> anxiety, substance-use disorder (alcohol, nicotine), and insomnia present;
> chronic pain, hyperlipidemia, thyroid disease; 2 prior SNRI trials, 346
> benzodiazepine days, augmentation present; 3 active meds (buspirone,
> diazepam, duloxetine).

```json
{
    "overall_similarity": 25,
    "phenotype": 0,
    "psych_comorbidity": 25,
    "metabolic_pain": 0,
    "treatment_burden": 25,
    "social_functional": 0,
    "safety": 100,
    "top_similarity_drivers": [
        "Absent suicide flag",
        "Absent epilepsy",
        "Absent uncontrolled hypertension",
        "Absent psych inpatient days",
        "Absent ED psych visits"
    ],
    "key_mismatches": [
        "Presence of SUD/Anxiety/Insomnia in Index",
        "Prior SNRI exposure in Index",
        "Active medications at baseline in Index"
    ]
}
```

### Top-band example (score 98) — near-duplicate patients

> **Narrative A** — MDD (Single Episode, Unspecified); Female, 68, Married,
> never-smoker; anxiety present, no other psychiatric or medical comorbidity;
> 0 prior adequate AD trials; 0 active meds; uncontrolled hypertension; BMI and
> blood pressure missing.
>
> **Narrative B** — Identical on every clinical field; differs only in recorded
> religion (Missing vs Non-Denominational) and index timing (MDD-to-anchor gap
> 40 vs 0 days).

```json
{
    "overall_similarity": 98,
    "phenotype": 100,
    "psych_comorbidity": 100,
    "metabolic_pain": 100,
    "treatment_burden": 100,
    "social_functional": 100,
    "safety": 100,
    "top_similarity_drivers": [
        "Age 68",
        "Female",
        "Married",
        "Anxiety Present",
        "No Prior AD Trials"
    ],
    "key_mismatches": []
}
```

### Additional responses (JSON only)

A second low-similarity example (score 25) — index patient with severe
recurrent MDD and anxiety/adjustment/PTSD/SUD versus a candidate with
dysthymia and no comorbidity:

```json
{
    "overall_similarity": 25,
    "phenotype": 0,
    "psych_comorbidity": 25,
    "metabolic_pain": 25,
    "treatment_burden": 25,
    "social_functional": 0,
    "safety": 100,
    "top_similarity_drivers": [
        "Absent Epilepsy",
        "Absent Uncontrolled HTN",
        "Absent NSAID burden",
        "Absent Benzodiazepine use",
        "Absent Hypnotic use"
    ],
    "key_mismatches": [
        "Age difference (55 vs 84)",
        "Comorbidity presence (Anxiety, PTSD, SUD, Chronic Pain vs Absent)",
        "Treatment burden (Active meds 2 vs 0)"
    ]
}
```

A second top-band pair (score 100) — two demographically and clinically identical
patients (both female, 32, single, no comorbidity, no prior trials), with the
overall score of 100 assigned despite a `phenotype` sub-score of 0:

```json
{
    "overall_similarity": 100,
    "phenotype": 0,
    "psych_comorbidity": 100,
    "metabolic_pain": 100,
    "treatment_burden": 100,
    "social_functional": 100,
    "safety": 100,
    "top_similarity_drivers": [
        "No prior adequate AD trials",
        "No benzodiazepine use",
        "No substance abuse",
        "No chronic pain",
        "No medical comorbidities"
    ],
    "key_mismatches": []
}
```

## S1.5 Interpretation and caveats

The judge's **overall** similarity behaved sensibly at the extremes — near-
duplicate patients scored 98, clinically dissimilar patients scored 25 — and
the population of ~1.71 million cached judgements spans 25–100 (median 55,
modal 45–65), so the score is graded rather than degenerate.

Parts of the rubric name evidence the narratives do not contain, and the
prompt is reproduced above exactly as it was run rather than corrected.
Dimension 1 is headed "Baseline symptom phenotype (PHQ-9 subitems)", and no
PHQ-9 item — indeed no symptom-severity instrument of any kind — is recorded in
this extract or rendered in any narrative (manuscript, Methods, *Outcome*).
Dimension 5 names no-show behaviour, which is not a field in the
narrative template, although the marital, employment, and social-determinant
cues named beside it are. Dimension 4 refers to "3y complexity" where the
lookback window is two years. Dimensions 2, 3, and 6, carrying 45 of the
rubric's 100 points, are fully supported by the template.

The judge did not treat the unsupported dimension as empty. Across a systematic
1-in-57 sample of the 1,710,849 cached judgements, the `phenotype` sub-score is
0 for 31.4% of pairs and takes 15 distinct values with a median of 60 over the
remainder, correlating 0.58 with `overall_similarity` — so rather than following
the instruction to output 0 for a dimension whose data are Missing, the model
scored baseline phenotype from the evidence actually present, the narrative's
MDD recurrence and severity coding and its psychiatric flags. The mislabel is in
the rubric's wording, not in the resulting behaviour. For comparison, the
sub-scores on the three fully supported dimensions are 0 for 0.0%, 1.0%, and
14.7% of pairs respectively.

None of this propagates into a reported number. Only `overall_similarity` enters
the neighbor weighting, and that weighting is itself scored against observed
outcomes the judge never sees, so a judgement made on thin evidence can only
degrade the discrimination reported above. What the mislabel does bound
is the generality of that null: the finding is that *this* rubric
added no discrimination over plain cosine weighting under nearest retrieval, not
that LLM clinical-similarity judging in general cannot. Against that, the same
rubric did lift discrimination where retrieval was uninformative (0.495 to 0.517
under random retrieval, 0.543 to 0.554 under subsampled), so it carries
clinical signal despite the mislabelled dimension.

The **per-dimension sub-scores are not a decomposition of the overall score**
and should be read as illustrative only:

- The `overall_similarity` is a holistic judgment, **not an aggregation of the
  six sub-scores**: both low-similarity pairs score `safety` 100
  — both patients simply lack the safety flags — yet an `overall` of 25, and
  a second top-band pair scores `phenotype` 0 yet an `overall` of 100.
- The free-text `top_similarity_drivers` and `key_mismatches` lists are
  unvalidated descriptive annotations: they were broadly accurate in the
  sampled extremes but are not audited at scale and do not enter the
  prediction.

Because only `overall_similarity` enters the neighbor weighting, these
sub-score artifacts do not propagate into the predictions; they are reported
here for transparency. Consistent with section 1 above, the weighting
strategy was second-order to the retrieval scheme: where the nearest neighbors
were already maximally similar, LLM weighting added no discrimination over
cosine weighting (both ROC AUC ≈ 0.59), and it lifted discrimination only
under random or subsampled retrieval, where the overall similarity score could
recover the few congruent neighbors a non-targeted draw happened to include —
behavior attributable to the retrieval geometry rather than to any deficiency
in the overall similarity score.

## S1.6 Re-judging under a corrected rubric

Measuring what the model did with the mislabelled dimension is not the same test
as asking what it would do without it, so the rubric was corrected and a sample
of cached pairs was re-judged under it.

**The change.** Exactly one: dimension 1, "Baseline symptom phenotype (PHQ-9
subitems)", is removed, and the surviving five dimensions are rescaled from
20/20/20/10/5 to 27/27/27/13/6 so the weights still sum to 100. The `phenotype`
field is dropped from the response schema. Nothing else differs — not the system
prompt's framing, not the scoring rules, not the output contract — which is what
makes the comparison a test of one change. The rubric's two other wording faults
(dimension 5's no-show reference, dimension 4's three-year window) are
deliberately left in place; correcting all three at once would have made the
comparison a test of three changes and left no way to attribute a divergence.

**The design.** A uniform random sample of 5,000 pairs was drawn from the
1,710,849 cached judgements — the sample is a function of the pipeline seed and
the cache contents, not of when the job ran — and re-judged under the corrected
rubric with a single model instance, the same model at the same temperature. New
judgements are written to their own database with its own table, so the published
cache is not touched. Agreement is reported two ways: on `overall_similarity`
itself, and on the derived neighbour weight, `(score/100)` raised to the
weighting exponent, because that is the quantity the neighbour-weighted arm
actually consumes and a monotone but non-affine shift in level moves it even when
the ranking is intact.

**The decision rule, fixed in advance.** Close agreement means the cached
judgements stand and this supplement records that no PHQ-9 item exists in the
extract. Material divergence means the full cache is re-judged and the corrected
rubric replaces the one printed in S1.2–S1.3, since that would then be the
rubric the paper used.

**The result: the cached judgements stand.** Across the 5,000 re-judged pairs the
corrected rubric agrees with the cached one at Pearson *r* = 0.929 and Spearman
ρ = 0.923, and the agreement is slightly *higher* on the derived neighbour weight
(*r* = 0.932) than on the raw score, so the quantity the predictor consumes is
not more sensitive to the change than the score it is built from. The median
absolute difference is **0 points** — most pairs receive the identical score —
the mean absolute difference is 3.2 points on a 0–100 scale, 69.0% of pairs fall
within 5 points and 99.1% within 10.

The change is small, systematic, and in the direction the rubric edit predicts.
Mean overall similarity falls from 56.6 to 55.4, a shift of −1.1 points, and the
spread widens slightly (SD 13.6 to 14.5). Removing a dimension the model had been
scoring generously — its mean `phenotype` sub-score across these pairs is 50.1 —
lowers the aggregate a little and lets the surviving dimensions separate pairs a
little more. Nothing about the ranking of neighbours moves materially, which is
what the weighting depends on.

Two incidental confirmations. The `phenotype` sub-score is 0 for 30.5% of these
5,000 pairs, reproducing the 31.4% measured independently on the systematic
1-in-57 sample in S1.5 and confirming that the model was scoring that dimension
from the evidence actually present rather than obeying the "output 0 if Missing"
rule. And the re-judging run recorded no parse or schema failure across 5,000
requests under the modified response contract.

**Decision.** The pre-specified rule is met on the agreement side, so the
1,710,849-judgement cache stands unchanged, the rubric printed in S1.2–S1.3
remains the one this paper used, and no result reported anywhere in the paper is
revised. What this adds to S1.5 is that the mislabelled dimension is not merely
harmless in principle — it is measurably close to inert in practice: correcting
it moves a typical neighbour's similarity score by about one point and leaves the
ordering intact.

***Figure S8.** Cached against corrected judgements over 5,000 randomly sampled
pairs. Left: joint distribution of overall similarity under the two rubrics, with
the identity line. Right: the distribution of their difference, corrected minus
cached.*

![](../../results/review/judge_prompt/judge_prompt_agreement.png){width=6in}


## 3. What the judge changes in the subgroup analysis

The subgroup analysis (submitted Supplement S9) contrasts discrimination
across strata for the embedded arm's four classifiers, the feature-vector
arm's four, and the neighbor-weighted arm's nearest-retrieval weightings. With
the judge in, that is 12 models and 288 contrasts; with it out, 10 models and
240. The Benjamini-Hochberg correction is applied across whichever set is
reported, so the submitted supplement corrects across 240.

The substantive reading is unchanged either way: the surviving contrasts are
overwhelmingly about how the depression is coded, sex shows no difference
anywhere, and the White-minus-non-White contrasts are directionally positive
throughout without surviving correction.

Two bookkeeping differences are worth recording so that a reader comparing this
document against the submitted supplement is not confused.

**Counts.** Over the 288-contrast set, 72 exclude zero unadjusted and 35
survive adjustment. Over the 240-contrast reported set, 58 exclude zero and 24
survive.

**One contrast depends on the judge.** Discrimination is lower among patients
with unspecified MDD severity than among the rest in the neighbor-weighted arm.
That contrast survives adjustment under judge weighting (−0.051, adjusted
*P* = .013) and under combined weighting (−0.047, adjusted *P* = .023), and
does not survive under either reported weighting (uniform −0.040, adjusted
*P* = .077; cosine −0.041, adjusted *P* = .064). The point estimates agree in
sign and are close in size across all four, so this is a threshold crossing
rather than a disagreement between weightings. It is the only contrast in the
whole set whose survival turns on which weightings are reported.

**Two others shift in count without shifting in conclusion.** The
age-18-to-29 contrast in the feature-vector arm survives in three of four
classifiers over the 288-contrast set and one of four over the 240-contrast
set, and the single-episode contrast in the feature-vector arm in four of four
against three of four. Both remain in the surviving set in both cases, with
the same sign and effectively the same effect size. The difference is the size
of the multiplicity denominator, not the evidence.

## 4. Where the numbers live

| Quantity | File |
| --- | --- |
| The four-by-four retrieval grid, with intervals and effective sample sizes | `../../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/knn_results.json` |
| Cached pairwise judgements | the judgement cache written by the neighbor pipeline |
| Worked-example judgements | `../../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/llm_audit/` |
| Re-judging under the corrected rubric | `../../results/review/judge_prompt/judge_prompt_agreement.{json,png}`, `judge_prompt_pairs.csv` |
| Subgroup contrasts, all 288 | `../../results/review/subgroups/subgroup_contrasts.csv` |

The `results` tree is gitignored, so a clone of this repository carries this
prose and none of the numbers. Regenerating them means re-running the neighbor
pipeline on the primary encoder.
