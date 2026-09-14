<!--
Matched-input representation parity: the reserve report.

STATUS: COMPLETE, AND NOT PART OF THE SUBMITTED PACKET. All three arms
reported by 2026-08-30 and the decision is on the record: the head-to-head null
survives matched inputs, so the published comparison stands and no full pipeline
pass is required. The document is held back deliberately. The senior author's
judgement is that a reviewer is unlikely to press the field-mismatch point, and
the manuscript still discloses the mismatch (Methods, *Predictors and patient
representations*) with the field-level crosswalk in Supplement S11. If a reviewer does press it, this is
the document that answers them, and it is complete enough to be handed over as
written.

Naming: the two representations are the FEATURE representation ("feature
vector") and the EMBEDDED representation ("the embedding"). "Rule-based" is not
an alias for either; see the NAMING block in ../manuscript.md.

Every number here is read from results/review/parity/parity_summary.{csv,json}
and the per-arm metrics.json files. Nothing is typed from memory.
-->

# Matched-input representation parity

**A reserve analysis for the TRD-prediction manuscript. Not submitted.**

**Result in one line.** Closing the two largest field asymmetries between the two
representations leaves the primary comparison a null — best-versus-best +0.007
(95% CI −0.004 to +0.016) on matched inputs against +0.008 as published — so the
field mismatch does not carry the published finding.

## 1. The question this answers

The paper's primary comparison sets a generalized pretrained transformer
embedding of a deterministic
clinical narrative against a typed feature vector, on the same patients, with
the same split. On the primary encoder the head-to-head contrast is embedded
logistic regression 0.657 against feature-vector XGBoost 0.649: a paired
difference of +0.008 (95% CI −0.003 to +0.019), reported as no evidence of
superior discrimination.

The two representations are not, however, fed the same fields. The field-level
crosswalk (Supplement S11) finds eleven asymmetries, ten of which favour the
narrative. The largest are three within-patient mean vital signs that the
narrative renders and the feature matrix drops at load time, and — running the
other way — recorded pre-index history length, which the feature matrix carries
and the narrative never rendered.

That imbalance is roughly the size of the effect under test. So the head-to-head
comparison is, strictly, a comparison of two encodings *and* of the fields each
encoding happens to carry, and the obvious objection is that the published
result is an artifact of the inventory rather than of the representation.

**This analysis closes the two largest asymmetries and asks whether the primary
comparison survives.** It is a decision procedure, not a second study: its job
is to establish whether the expensive version — a full pipeline pass — is
needed.

## 2. Design

### 2.1 What was changed

Two changes, one per representation.

- **The feature matrix receives the vital signs.** The three within-patient mean
  vital signs are restored (BMI, mean systolic and mean diastolic blood
  pressure), each vital block carrying an explicit boolean missingness indicator,
  and the numeric branch of the preprocessing pipeline gains a median imputer
  fitted inside each cross-validation fold rather than over the whole cohort. The
  indicator is what keeps this from being a silent imputation: 22.1% of patients
  have no recorded BMI and 21.8% no recorded blood pressure, and the association
  between vital-sign missingness and the outcome is precisely what the paper's
  missing-data limitation is about, so the fact of an absent measurement has to
  stay available to the model. The design matrix goes from 59 columns to 64.
- **The narrative renders recorded history length.** `pre_anchor_history_days` is
  added to the narrative's cohort-and-index header. It is the one field the
  feature matrix had and the narrative did not.

### 2.2 What was deliberately not changed

The remaining nine asymmetries are left in place, and the reason is scope rather
than oversight. Removing the index date, the sexual-orientation
field, the raw sociodemographic tokens or the named medication ingredients from
the narrative would mean either deleting information from one representation or
adding columns to the other. Every such change alters the narrative text, which
invalidates every embedding, neighbour set and cached judgement downstream of
it. The two changes made here are the two that can be attributed cleanly.

Three further restrictions keep this a decision procedure. Two classifiers are
fitted rather than four — logistic regression and XGBoost, respectively the best
embedded and the best feature-vector model, so the pair carries both the
head-to-head contrast and the classifier-by-representation interaction. One
encoder is used, the primary `Qwen3-Embedding-8B`, not all four. The
neighbour-weighted arm is re-run with cosine and uniform weighting only, with no
LLM judging, and the ablation slate is not re-scored.

Hyperparameter grids, the 80/20 stratified split, the seed and the bootstrap
procedure are all the published ones. Every comparison is a **paired** bootstrap
against the published prediction vector on the same held-out patients, which is
the appropriate test because both vectors rank the same people; the paired
intervals run roughly a third the width of the marginal ones.

### 2.3 A reproducibility defect, and the control arm it forced

Re-rendering the narratives revealed that the published narrative text is not
byte-reproducible. The renderer emitted its flag lists — psychiatric and general
medical comorbidities, prescribing-safety flags, and the per-class prior-trial
counts — by iterating Python sets, whose iteration order varies between
processes. Re-running the renderer on identical input therefore produced
identically *informative* but differently *ordered* text. The renderer sorts as
of this revision, which makes future renders deterministic; it does not
reconstruct the exact strings that were embedded and judged, which are the ones
on disk.

This bears on no published number: each published narrative was rendered once,
and every embedding, neighbour set and judgement was computed from the text that
was actually written. It does mean a re-render cannot serve as a byte-level
control. So the comparison carries three arms, not two:

| Arm | What it is |
| --- | --- |
| `feature_vitals` | the feature matrix with the vitals and their missingness indicators |
| `narrative_control` | the narrative re-rendered in sorted order, **no content change** |
| `narrative_parity` | the narrative re-rendered with `pre_anchor_history_days` added |

The control arm measures what re-rendering alone costs, so the parity arm's
delta is attributable to the added field rather than to the reshuffle. It also
answers a question the paper otherwise could not: how stable the embedded arm is
to a rebuild of its own inputs.

### 2.4 The decision rule

Fixed on 2026-08-28, before any arm reported, and recorded in the project task
list at that time:

> If no paired interval on the **head-to-head** contrast excludes zero, the
> published comparison stands as reported and this analysis is the evidence that
> the field mismatch does not carry it. If one does, the full pipeline pass —
> re-render, re-embed all four encoders, re-tune every classifier, re-score the
> ablation slate — becomes unavoidable, because the donor pairings and the frozen
> baselines all sit downstream of the narrative text.

The trigger is the head-to-head contrast specifically, and it is worth saying
why, because the within-representation contrasts below are not nulls and it
would be easy to read them as triggering. Adding an informative field to an arm
*should* move that arm; a manipulation that moved nothing would mean the
manipulation failed. What the paper claims is about the *comparison* between the
arms, and that is the quantity the rule names. The rule's own justification says
the same thing from the other side: what a full pass would have to rebuild is
everything downstream of the *narrative text*, which no feature-arm result can
require.

## 3. Results

### 3.1 The feature arm gains, and the gain is real but classifier-specific

Adding the vitals with missingness indicators to the feature matrix, against the
published feature arm, on the same held-out patients:

| Model | Published ROC AUC | With vitals | Paired Δ | 95% CI | Excludes zero |
| --- | --- | --- | --- | --- | --- |
| Logistic regression | 0.629 | 0.643 | **+0.014** | +0.009 to +0.020 | **yes** |
| XGBoost | 0.649 | 0.651 | +0.002 | −0.002 to +0.006 | no |

Three things about this table.

**The tuning did not move.** Both parity models selected exactly the
hyperparameters their published counterparts selected — elasticnet at C = 0.1
with an L1 ratio of 0.5 for logistic regression, and 300 trees at learning rate
0.01, depth 5, subsample 0.5 for XGBoost. The gain is attributable to the added
columns rather than to landing on a different point in the grid.

**Calibration improves more than discrimination does.** The feature arm's
logistic-regression calibration slope moves from 0.779 to 0.922 and its
intercept from 0.058 to 0.018; Brier falls from 0.1391 to 0.1382. A slope that
far below one is systematic overconfidence, and restoring the vitals removes
most of it.

**Only the linear model gains.** XGBoost is unmoved. This is the same
representation-by-classifier pattern the paper already reports from the other
direction: the tree ensemble was already extracting from 59 columns most of what
three more contain, while the regularized linear model could use them.

This closes two-thirds of the three-way missing-data comparison that the packet
does not report. (The sentence saying it should was in the Limitations section,
which came out of the Discussion on 2026-09-03; see `limitations_reserve.md`.) The published arm is the
"no vitals" arm and this is the "vitals plus explicit indicators, imputed within
fold" arm. The third — vitals imputed *without* indicators, which would isolate
what the indicator itself contributes — was not run.

### 3.2 The neighbour arm is a clean null, and it bounds the rebuild noise

Nearest-retrieval KNN, each narrative arm against the published run, paired on
the same held-out anchors:

| Arm | Weighting | Published | Arm | Paired Δ | 95% CI | Excludes zero |
| --- | --- | --- | --- | --- | --- | --- |
| Control (re-render only) | uniform | 0.5934 | 0.5976 | +0.0042 | −0.0063 to +0.0132 | no |
| Control (re-render only) | cosine | 0.5939 | 0.5978 | +0.0039 | −0.0059 to +0.0124 | no |
| Parity (+ history length) | uniform | 0.5934 | 0.5925 | −0.0009 | −0.0120 to +0.0090 | no |
| Parity (+ history length) | cosine | 0.5939 | 0.5933 | −0.0007 | −0.0112 to +0.0088 | no |

The negative controls hold in both arms: random retrieval sits at 0.496–0.500
against the published 0.495–0.499, so the retrieval geometry is behaving as it
did.

Two readings, and the second is the one worth keeping.

**Adding recorded history length does nothing to the neighbour arm.** Both
intervals straddle zero and both point estimates are under a thousandth of an
AUC point.

**The control arm is the more informative row.** Re-rendering the narratives
with no content change at all moves nearest-retrieval discrimination by about
+0.004 — larger, in point estimate, than the field the analysis was built to
test, and in the opposite direction. That is the scale of the arm's sensitivity
to a rebuild of its own inputs, and it is not something the paper previously had
a number for. It is also why the control arm was not padding: without it, the
parity arm's −0.001 would have been read as "the field costs nothing" when the
honest statement is that a difference this size is below the noise floor of
re-rendering at all.

### 3.3 The head-to-head comparison survives, and the interaction survives with it

The embedded arms against the feature arm, both on matched inputs, paired on the
same held-out patients. The published contrast is shown beside each for
comparison.

| Contrast | Arm | Matched Δ | 95% CI | Excludes zero | Published Δ |
| --- | --- | --- | --- | --- | --- |
| **Best vs best** (embedded LR vs feature XGBoost) | control | **+0.0087** | −0.0018 to +0.0188 | **no** | +0.0079 |
| **Best vs best** | parity | **+0.0069** | −0.0035 to +0.0164 | **no** | +0.0079 |
| Logistic regression, classifier fixed | control | +0.0168 | +0.0061 to +0.0267 | yes | +0.0283 |
| Logistic regression, classifier fixed | parity | +0.0150 | +0.0045 to +0.0247 | yes | +0.0283 |
| XGBoost, classifier fixed | control | −0.0137 | −0.0250 to −0.0033 | yes | −0.0135 |
| XGBoost, classifier fixed | parity | −0.0135 | −0.0243 to −0.0037 | yes | −0.0135 |

**The headline null holds, and it holds slightly more comfortably than it did.**
Neither best-versus-best interval excludes zero. In the parity arm — the one with
both asymmetries closed — the point estimate falls from +0.008 to +0.007 and the
interval tightens marginally. **The published comparison stands as reported, and
the field mismatch does not carry it.** By the rule fixed before any arm
reported, no full pipeline pass is required.

**The classifier-by-representation interaction survives, but the positive half of
it is roughly halved.** Holding the classifier fixed, the embedding remains
significantly better for logistic regression and significantly worse for
XGBoost — the two-effects-of-opposite-sign structure the paper reports is intact,
and it is what continues to produce a null at best-versus-best. But the logistic-
regression contrast falls from +0.028 to +0.015 once the feature arm has its
vitals, which is most of the way to the boundary while still clearing it. That is
the predicted direction and very close to the predicted magnitude: closing the
gap lifts the feature arm, and the arm the embedding was beating is the one that
gained. The XGBoost half is unmoved at −0.0135, identical to the published value
to four decimals.

**Re-rendering costs the classifier arms nothing**, unlike the neighbour arm.
Every within-representation contrast against the published embedded arm is null:
the control arm moves logistic regression +0.0029 (−0.0014 to +0.0072) and
XGBoost +0.0020 (−0.0045 to +0.0082); the parity arm moves them +0.0011 (−0.0037
to +0.0056) and +0.0021 (−0.0042 to +0.0087). So the embedded representation's
discrimination is stable to a rebuild of its own inputs when it is read by a
fitted classifier, and mildly unstable when it is read by nearest-neighbour
retrieval (§3.2) — which makes sense, since retrieval consumes the geometry
directly while a fitted model re-optimizes against whatever geometry it is given.

**One thing that is *not* stable, and the paper makes a claim about it.** The
discrimination is reproducible; the *selected model* is not. The published
embedded logistic regression chose an elasticnet penalty (C = 0.01, L1 ratio
0.25) and is sparse — the manuscript reports that only 385 of the 4,096
dimensions carry nonzero weight. Both re-rendered arms instead chose plain L2 at
C = 0.001, a dense ridge fit, and XGBoost moved from depth 8 to depth 5. Nothing
about the reported discrimination changes: the two penalties land within 0.003
AUC of each other and the interval on that difference includes zero. But it means
the sparsity result is a property of the fit obtained on the published narratives
rather than a stable property of the representation, and a rebuild carrying the
same information can select a dense solution that discriminates just as well.
Read the sparsity claim as descriptive of the published model, which is what it
says, and not as evidence that the predictive structure in the embedding is
*necessarily* concentrated in a few hundred dimensions.

## 4. What this establishes, and what it does not

**Establishes.** That the two largest field asymmetries were closed and measured
rather than conceded, and that the primary comparison is unchanged by closing
them: the best-versus-best contrast remains a null, at +0.007 with both changes
in place against +0.008 as published. That the feature vector's missing vitals
were worth about 0.014 AUC to a linear model and nothing to a tree ensemble, most
of it showing up as calibration rather than discrimination. That recorded history
length is worth nothing measurable to either the narrative's neighbour arm or its
classifier arms. That the classifier-by-representation interaction is real enough
to survive the manipulation, though its positive half halves. And two stability
facts the paper did not previously have: re-rendering the narratives moves the
neighbour arm by about as much as the field under test does, while leaving the
fitted classifiers untouched, and the *selected* embedded model is not stable
across a rebuild even where its discrimination is.

**Does not establish.** That the representations are now matched — nine
asymmetries remain, all favouring the narrative, and closing them would require
invalidating every embedding and cached judgement in the study. That the result
generalizes across encoders: one encoder was used. That the ablation slate is
unaffected: it was not re-scored, and it sits downstream of the narrative text.
And it says nothing about the four classifiers not fitted here — in particular,
the random-forest and gradient-boosting halves of the published interaction were
not re-tested.

## 5. Provenance

Every number quoted above is tracked alongside this document in
`parity_results/`, which is the only version-controlled copy: `TRD-EHR/results/`
is gitignored in its own repository, and the `results` symlink at the root of
this one is gitignored here as well, so neither repo's history otherwise carries
the numbers. That directory's README says what it holds and what it does not.

The live originals, and everything too large to track:

| Artifact | Path |
| --- | --- |
| Summary table and decision | `results/review/parity/parity_summary.{csv,json}` |
| Per-arm metrics | `results/review/parity/<arm>/metrics.json` |
| Per-patient held-out probabilities | `results/review/parity/<arm>/test_predictions.parquet` |
| Neighbour results | `results/review/parity/<arm>/knn_results.json`, `summary_predictions.csv` |
| Design and drivers | `scripts/pipeline/review/parity/` |
| Job scripts | `slurm_jobs/review/parity_*.sbatch` |

Paths in that table are relative to the `TRD-EHR` repository, whose `results/`
tree is itself a mirror of `ARTIFACTS_DIR/review/parity/`. The narratives,
embedding databases and trained model objects are excluded from the mirror by
size and exist only under `ARTIFACTS_DIR`. Regenerate the summary with
`python -m scripts.pipeline.review.parity.summarize`, then re-copy
`parity_results/`.

## 6. Run history

The three arms were submitted 2026-08-28. The feature arm completed the same
evening. Both narrative arms — a four-stage chain of render, embed, neighbours,
fit — were killed at the twelve-hour wall on 2026-08-29 at 04:56, part-way
through the embedded logistic-regression grid search, with everything upstream
of the fit complete on disk. The recovery job ran the fit alone and both arms
completed on 2026-08-30; the embedded logistic-regression grid took 6.0 hours per
arm even at the wider allocation, against 4.9 in the published run.

Two causes, both recorded because they are the kind that recur. The submitted
copy of the job ran the neighbour stage *before* the classifier fit, so the stage
the decision rests on received whatever time the cheaper corroboration left it;
the job script has since been reordered to fit first. And it requested 16 CPUs
while `GridSearchCV` runs 16 worker processes, leaving each worker's BLAS a
single core on a fully subscribed allocation — the published run fitted the same
grid on the same matrix in 4.9 hours with 48 CPUs. The recovery job
(`parity_narrative_fit.sbatch`) runs the fit stage standalone against the
surviving embeddings, at 48 CPUs, with no GPU and no re-render.
