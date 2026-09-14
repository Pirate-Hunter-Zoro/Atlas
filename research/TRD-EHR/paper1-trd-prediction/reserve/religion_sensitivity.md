<!--
Religion retention-versus-removal sensitivity: the reserve report.

STATUS: COMPLETE, AND NOT PART OF THE SUBMITTED PACKET. Both arms reported by
2026-09-03 and the decision is on the record: every deciding interval includes
zero, so the field does not carry the published result and nothing in the packet
changes except one sentence in Supplement M6. The document is held back on the
matched-input-parity precedent — a null on a one-off "does this change anything"
analysis is reassurance rather than a finding, and reassurance belongs in the
reserve folder where it can be handed over if a reviewer asks for it.

The decision rule was fixed on 2026-09-03, in planning/TRD-EHR_TODO.txt, BEFORE
the embedded arm's numbers existed, and it said the opposite thing about a
positive: had any deciding interval excluded zero, the result would have gone
INTO the packet — Supplement M6 stating the delta and Limitations, *Missing
data* gaining a clause. It did not, so it did not.

Naming: the two representations are the FEATURE representation ("feature
vector") and the EMBEDDED representation ("the embedding"). "Rule-based" is not
an alias for either; see the NAMING block in ../manuscript.md.

Every number here is read from results/review/religion/religion_summary.{csv,json},
the per-arm metrics.json files, and — for the published and control baselines —
results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/classical_ml_results_*.json
and results/review/parity/narrative_control/metrics.json. Nothing is typed from
memory.
-->

# Religion: retention against removal

**A reserve analysis for the TRD-prediction manuscript. Not submitted.**

**Result in one line.** Removing religion from both representations changes
discrimination in neither — the deciding paired contrasts are +0.0013 (95% CI
−0.0017 to +0.0039) and −0.0031 (−0.0083 to +0.0024) for the embedded arm and
+0.0001 and +0.0002 for the feature arm, all four intervals inside ±0.009 — so
the published result does not depend on the field or on the shape of its
missingness.

## 1. The question this answers

The supplied supplementary methods asked for a sensitivity analysis comparing
retention of religion against its removal. The question is really about the
*missingness*, not the field.

Religion is unrecorded for 29.4% of the cohort, and the absence is not uniform:
43.8% of patients aged 18–29 have no recorded religion against 17.5% of those
aged 65 or older (Supplement M6). Both representations make that absence
readable — the FEATURE one-hot encoder gives "unrecorded" a level of its own,
and the narrative prints the literal token `Missing` — so a model can use the
field's *absence* as an age proxy without ever using the field's content. A
sociodemographic field that is missing differentially by age is a route by which
age enters a model twice, once as itself and once as a pattern of silence.

**Removing is not permuting**, which is why the six-concept ablation slate does
not answer this. A permutation destroys the link between a patient and their own
value while leaving the pattern of who has one intact; the sociodemographic
permutation (Supplement M11) therefore scrambles recorded religions among the
patients who have one and leaves every `Missing` token exactly where it was. Only
a removal takes both the content and the pattern away.

**This analysis removes the field from both representations and asks whether the
published discrimination survives.** Like the matched-input parity round, it is a
decision procedure rather than a second study: its job is to say whether the
field is load-bearing, and if it is not, to say so once and get out of the way.

## 2. Design

### 2.1 What was changed

One change per representation, and nothing else.

- **The feature matrix loses the Religion column.** The published design matrix
  goes from 59 columns to 58, everything else byte-identical: the same rows, the
  same split, the same seed, the same preprocessing, the same grid. Because the
  column is categorical, what is removed is the whole one-hot block including its
  unrecorded level — the pattern of silence goes out with the content, which is
  the point.
- **The narrative drops the Religion field from its sociodemographics line**, and
  the 42,579 re-rendered narratives are re-embedded with the primary encoder
  `Qwen3-Embedding-8B`. The renderer's check on 200 sampled narratives confirmed
  no Religion field survived the render.

Both changes are opt-in flags — `NARRATIVE_DROP_RELIGION` for the renderer and a
`drop_religion` keyword on the feature-matrix loader — defaulting to off, so the
published artifacts remain reproducible from the published code path. Both were
verified before submission.

### 2.2 What was deliberately not changed

The same reduction the parity round used, for the same reason: two classifiers
rather than four (logistic regression and XGBoost, respectively the best embedded
and the best feature-vector model, so the pair carries both the head-to-head
contrast and the classifier-by-representation interaction), one encoder rather
than four, no neighbour-weighted arm, and no re-score of the ablation slate.
Hyperparameter grids, the 80/20 stratified split, the seed and the bootstrap are
the published ones, and every contrast is a **paired** bootstrap over 1,000
resamples of the same 8,516 held-out patients, which is the right test because
both score vectors rank the same people.

### 2.3 The comparator, which is the whole reason this was affordable

The embedded arm is scored against the **parity round's `narrative_control`**,
not against the published embedded arm.

`narrative_control` is a re-render with no content change, already rendered and
already embedded from the parity round. It exists because the published narrative
text is not byte-reproducible: the renderer once emitted its flag lists by
iterating Python sets, so a re-run produced identically informative but
differently ordered text (§2.3 of `matched_input_parity.md`). A re-render
therefore moves the embedded arm on its own, by up to +0.003 AUC for the fitted
classifiers, and by considerably more than that in calibration (§3.4). Scoring
the religion-free arm against the control puts both arms on the far side of the
same rebuild, so the difference between them is attributable to the removed field
rather than to the reshuffle — and it cost nothing, because the control was
already on disk.

The contrast against the published embedded arm is reported too (§3.3), as
corroboration. It carries the re-render inside it and is the weaker of the two.

The feature arm needs no such device: nothing was re-rendered, so its comparator
is the published feature arm directly.

### 2.4 The decision rule

Fixed 2026-09-03 and recorded in the project task list, before the embedded arm's
numbers existed. The feature arm had already reported; the deciding arm had not.

> The contrast that decides it is `narrative_no_religion` against the parity
> round's `narrative_control`, paired bootstrap, per classifier — not against the
> published embedded arm, which carries the re-render inside it.
>
> If every deciding interval includes zero, the field does not carry the
> published result. Nothing in the packet changes except the one sentence in
> Supplement M6, and this report records the null and is held back exactly as
> `matched_input_parity.md` is.
>
> If any deciding interval excludes zero, religion is load-bearing for a
> representation, which is a finding rather than a reassurance, and it goes *in*
> the packet — Supplement M6 stating the delta and Limitations, **Missing data**
> gaining a clause. Do not bury a positive in a reserve document.
>
> Either way, note whether the two classifiers picked the same hyperparameters
> their comparators picked, because a null attributable to a different point in
> the grid is not a null about the field.

## 3. Results

### 3.1 The feature arm is a precise null

The published feature matrix minus the Religion column, against the published
feature arm, on the same held-out patients:

| Model | Published ROC AUC | Without religion | Paired Δ | 95% CI | Excludes zero |
| --- | --- | --- | --- | --- | --- |
| Logistic regression | 0.6288 | 0.6290 | +0.0001 | −0.0011 to +0.0015 | no |
| XGBoost | 0.6492 | 0.6494 | +0.0002 | −0.0005 to +0.0009 | no |

Both point estimates are under two ten-thousandths of an AUC point and both
intervals fit inside ±0.0015 — two to seven times tighter than the intervals the
embedded arm returns below, because nothing here was rebuilt and the only thing
separating the two prediction vectors is one column.

**The tuning did not move.** Both models selected exactly the hyperparameters
their published counterparts selected — elasticnet at C = 0.1 with an L1 ratio of
0.5 for logistic regression, and 300 trees at learning rate 0.01, depth 5,
subsample 0.5 for XGBoost. The null is the dropped column and not a different
point in the grid.

### 3.2 The embedded arm is the deciding contrast, and it is also a null

The religion-free narratives, re-embedded, against the parity round's
`narrative_control` — both arms re-rendered, one of them without the field:

| Model | Control ROC AUC | Without religion | Paired Δ | 95% CI | Excludes zero |
| --- | --- | --- | --- | --- | --- |
| Logistic regression | 0.6600 | 0.6613 | +0.0013 | −0.0017 to +0.0039 | no |
| XGBoost | 0.6377 | 0.6346 | −0.0031 | −0.0083 to +0.0024 | no |

Neither interval excludes zero. By the rule fixed before these numbers existed,
**the field does not carry the published result**, and the packet changes by one
sentence.

Two things qualify the table without changing its verdict.

**The two point estimates disagree in sign**, +0.0013 for the linear model and
−0.0031 for the tree ensemble. Both are well inside their own intervals and
neither is separable from zero, so the disagreement is noise rather than a
miniature of the classifier-by-representation interaction the paper reports. It
is worth naming only because a reader who wanted the field to matter could quote
either number alone.

**One of the two carries a hyperparameter change and the other does not.**
Logistic regression selected exactly what the control selected — plain L2 at
C = 0.001. XGBoost moved from depth 5 to depth 8. That instability is already on
the record and it is not about religion: the parity round found the *published*
embedded XGBoost at depth 8 and both of its own re-rendered arms at depth 5, so
the depth choice flips across a rebuild of the narratives on its own. The
religion-free arm landing back on depth 8 is that same coin coming up the other
way. The consequence is narrow — the XGBoost row of this table is the one
contrast whose point estimate is not cleanly attributable to the removed field —
and it is moot, because the interval includes zero either way.

### 3.3 The corroborating contrast agrees

The same arm against the *published* embedded arm, which carries the re-render
inside it:

| Model | Published ROC AUC | Without religion | Paired Δ | 95% CI | Excludes zero |
| --- | --- | --- | --- | --- | --- |
| Logistic regression | 0.6571 | 0.6613 | +0.0042 | −0.0006 to +0.0087 | no |
| XGBoost | 0.6357 | 0.6346 | −0.0011 | −0.0081 to +0.0060 | no |

Both null, and the logistic-regression row shows exactly why this is the weaker
comparison: its point estimate is three times the deciding one and its interval
comes within a thousandth of excluding zero, because most of what it measures is
the +0.0029 the parity round attributed to re-rendering alone. Had this been the
deciding contrast, a null would have been reported as a near-miss. The comparator
choice in §2.3 is what keeps that from happening.

### 3.4 Calibration moved more than ranking did, and it is not a finding

The task list flagged one thing to chase: in the feature arm, removing the
column moved calibration further than it moved discrimination. It did, and the
embedded arm was supposed to say whether the pattern held. It does not.

| Arm | Model | Comparator slope | Without religion | Comparator Brier | Without religion |
| --- | --- | --- | --- | --- | --- |
| Feature (vs published) | Logistic regression | 0.778 | 0.935 | 0.1391 | 0.1391 |
| Feature (vs published) | XGBoost | 1.016 | 1.094 | 0.1376 | 0.1376 |
| Embedded (vs control) | Logistic regression | 1.066 | 1.077 | 0.1367 | 0.1366 |
| Embedded (vs control) | XGBoost | 1.636 | 1.187 | 0.1387 | 0.1391 |

**The feature arm's observation is real and attributable.** Nothing was
re-rendered, both models kept the published hyperparameters, and one column left:
the linear model's calibration slope moves 0.778 → 0.935, most of the way out of
systematic overconfidence, with its intercept falling 0.058 → 0.014. What removing
a one-hot block whose largest level is "unrecorded" appears to do is stop the
linear model spending coefficient on a level that is a demographic proxy rather
than a risk factor.

**It cannot be elevated past an observation, for three reasons.** The sign is
inconsistent within the same arm — XGBoost moves 1.016 → 1.094, *away* from one.
Brier moves by at most 0.0004 anywhere in the table and not at all in the two
feature-arm cells, so no total accuracy is gained: what moved is the distribution
of the same error, not its size. And the embedded arm cannot corroborate anything,
because its own noise floor is larger than the effect: re-rendering with no
content change at all moved the embedded XGBoost slope from 0.750 to 1.636 and the
embedded logistic regression from 1.272 to 1.066, so the −0.449 that removing
religion then contributes to XGBoost is about half what the rebuild did by itself,
in the opposite direction.

The honest statement is the one the numbers support: religion's removal is
neutral for discrimination in both representations, and the only calibration
change large enough to notice is in the one arm that was not rebuilt, where it
improves a linear model that the paper does not report as its primary embedded
result. Nothing in the packet says otherwise, and nothing in the packet needs to.

## 4. What this establishes, and what it does not

**Establishes.** That religion's retention was measured against its removal
rather than argued about, in both representations, on the same held-out patients,
against a rule fixed before the deciding numbers existed. That the field is not
load-bearing: no interval on any of the six contrasts excludes zero, the deciding
pair sit at +0.0013 and −0.0031, and the feature arm's pair are inside ±0.0015
with the published hyperparameters intact. That the differential missingness —
29.4% overall, 43.8% at ages 18–29 against 17.5% at 65 or older — is therefore
not a route by which age is doing undisclosed work in either model, because
taking away both the content and the pattern of silence changes neither model's
ranking. And, incidentally, that the comparator device matters: the same arm
scored against the published embedded run instead of the control returns a point
estimate three times larger and an interval within a thousandth of excluding
zero.

**Does not establish.** That the *other* differentially missing fields are
neutral — this is one field, chosen because the review asked for it. That the
result holds across encoders: one encoder was used. That it holds for the
neighbour-weighted arm, which was not run, and where retrieval consumes the
embedding geometry directly rather than re-optimizing against it — the parity
round found that arm to be the one sensitive to a rebuild, so it is the arm where
a removal would be hardest to attribute. That the ablation slate is unaffected:
it was not re-scored, and it sits downstream of the narrative text. That the
random-forest and gradient-boosting halves of the published interaction are
unmoved: they were not fitted. And nothing about calibration, for the reasons in
§3.4.

## 5. Provenance

Every number quoted above is tracked alongside this document in
`religion_results/`, which is the only version-controlled copy: `TRD-EHR/results/`
is gitignored in its own repository, and the `results` symlink at the root of this
one is gitignored here as well, so neither repo's history otherwise carries the
numbers. That directory's README says what it holds and what it does not.

The live originals, and everything too large to track:

| Artifact | Path |
| --- | --- |
| Summary table and verdict | `results/review/religion/religion_summary.{csv,json}` |
| Per-arm deltas | `results/review/religion/{feature,embedded}_arm_deltas.csv` |
| Per-arm metrics | `results/review/religion/<arm>/metrics.json` |
| Per-patient held-out probabilities | `results/review/religion/<arm>/test_predictions.parquet` |
| Published baselines | `results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/classical_ml_results_{FEATURE,EMBEDDED}.json` |
| Control-arm baseline | `results/review/parity/narrative_control/metrics.json` |
| Design and drivers | `scripts/pipeline/review/religion/` |
| Job scripts | `slurm_jobs/review/religion_*.sbatch` |

Paths in that table are relative to the `TRD-EHR` repository, whose `results/`
tree is itself a mirror of `ARTIFACTS_DIR`. The religion-free narratives, the
embedding database and the trained model objects are excluded from the mirror by
size and exist only under `ARTIFACTS_DIR`. Regenerate the summary with
`python -m scripts.pipeline.review.religion.summarize`, then re-copy
`religion_results/`.

## 6. Run history

Three jobs, submitted together on 2026-09-03, the third on an `afterok`
dependency, and all three completed the same day without a failure or a
resubmission.

| Job | What it did | Reported |
| --- | --- | --- |
| 2069433 `religion_feature` | the 58-column feature arm, both classifiers | 11:30, same day |
| 2069434 `religion_embed` | render 42,579 religion-free narratives, embed them | 15:53 |
| 2069435 `religion_fit` | both classifiers on the religion-free embeddings, then the summary | 22:36 |

The feature arm is cheap — 868 s for the logistic-regression grid and 18 s for
XGBoost. The embedded fit is not: 20,086 s (5.6 hours) for the logistic-regression
grid and 4,038 s (1.1 hours) for XGBoost, inside an 8.5-hour wall at 48 CPUs and
192 GB.

Both lessons from the parity round's twelve-hour kill were applied at submission
rather than after another failure. The fit stage runs as its own job against
embeddings already on disk, so nothing the decision rests on shares an allocation
with anything cheaper. And it asks for 48 CPUs rather than 16, because the grid
search runs 16 worker processes and starving each worker's BLAS to a single core
is what turned a 4.9-hour published fit into a wall-clock kill the first time.
