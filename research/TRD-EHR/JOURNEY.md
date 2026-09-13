# TRD-EHR — the research journey

A plain-language narrative of this project: where it started, what we tried, what broke, what we
learned, and where it now stands. Written for a reader who wants the story and the current state
without reading the codebase.

`README.md` documents the pipeline architecture and carries no results. This file is its other
half — the narrative, the findings, and the reasoning behind them. Both live in this repository
now; until 2026-09-13 the narrative sat in a separate `Research-Journey` hub, which was retired so
that each project's writing, planning and documents live with the project they belong to.

One EHR pipeline, one shared data substrate, two papers:

- **Paper 1 — TRD prediction:** *Will this patient become treatment-resistant?*
- **Paper 2 — Counterfactual antidepressant selection:** *Which antidepressant class should this
  patient receive?*

Both sit on the same foundation, so the journey starts there (§0).

The two sibling projects keep journeys of the same shape: `~/PSYCH-ASR/JOURNEY.md` for the
spoken-psychotherapy feasibility work, and `~/libr-local-llm/JOURNEY.md` for the local LLM
inference this project's similarity judge runs on.

---

## The documents

> **Documentation convention.** `README.md` documents **pipeline architecture only** — module
> structure, data shapes, config, orchestration, engineering rationale. It must **never** carry
> empirical results or findings: no AUC/ATE/R²/Qini/ρ/p-value estimates, no prevalences,
> missingness rates, effect sizes, or outcome ratios, and no "we found X" verdicts. All numbers
> and findings belong in the manuscript and its supplement — the single source of truth — so they
> are never stated twice and never drift. This file is the exception that proves it: a narrative,
> not a specification, and it restates the paper's numbers on purpose. Hyperparameters,
> dimensions, seeds, wall-clock, resource asks, and method thresholds are architecture, not
> results, and are fine in the README. When in doubt: "would this number appear in the paper?" If
> yes, it does not go in the README.

| Folder | Contents |
| ------ | -------- |
| `paper1-trd-prediction/` | Paper 1, organized so that the top level *is* the submitted packet and nothing else is: `manuscript`, `supplement`, `tripod_ai_checklist` and `cover_letter`, each as Markdown source plus a built `.docx`. Beside them, three folders and a `README.md` that indexes them — `reserve/`, four finished documents deliberately held back (`methods_reserve.md`, `limitations_reserve.md`, `matched_input_parity.md`, `religion_sensitivity.md`), the two analysis reports carrying their numeric artifacts in `parity_results/` and `religion_results/` because both `results` trees are gitignored; `review/`, the internal account of the senior-author rounds (`MP_review_latest.md` verbatim, `round_2026-09-02_brief.md` for the five-minute version, `round_2026-09-02.md` for the item-by-item one, and `feedback/` holding the documents he supplied); and `references/`, the citation library — 26 of the 31 cited papers held as PDFs under a library index of its own (the prefixes are not manuscript reference numbers; `CITATION_MAP.md` is the authority on which is which), plus the SFHS extract query documentation as a data-provenance source, a role-grouped manifest, and drafted reprint-request emails for the four papers still paywalled |
| `paper2-counterfactual/` | Paper 2 design outline, the econometric identification strategy, the causal-validation summary, my own project notes, and its own `references/` citation library (20 of 22 papers + the source textbook, a role-grouped manifest, and drafted reprint-request emails) |
| `planning/` | Mentor specifications (`NextSteps.pdf`, `CRF_AnalysesConsiderations_07.08.2026.docx`) and this project's live task list, `TRD-EHR_TODO.txt` |
| `formats/` | Journal template (JMIR) and reporting-standard guideline (TRIPOD+AI) |

**The two citation libraries are on disk but not in git.** This repository is public and the
`references/` PDFs are other authors' published papers, so `.gitignore` keeps them out. What *is*
tracked is everything describing them — each library's `README.md`, `CITATION_MAP.md` (the
authority on which prefix is which reference number), the role-grouped manifests, the drafted
reprint-request emails, and the SFHS data-provenance note. A fresh clone therefore arrives with
the bibliography described but not carried.

### Editing a document and rebuilding it

The Markdown is the source. Every `.docx` in this repository is built from it, so editing
the `.docx` is how the two stop agreeing — and the `.docx` is the one that gets sent.

Open the `.md`, make the edit, and from anywhere in this repository:

```bash
rebuild
```

That rebuilds every document whose Markdown is newer than its `.docx` and leaves the rest
alone, so an edit to one section costs one conversion rather than fifty-five. Then commit
as usual, or `scripts/save-and-push.sh`.

`rebuild` is a shell function from the sibling Paper-Writer repository, defined in
`Paper-Writer/config/rebuild-alias.sh` and sourced from `~/.bashrc`. Arguments pass
through: `rebuild --list` says what it would do without doing it, `rebuild --all` forces
everything, and `rebuild paper1-trd-prediction/manuscript.md` does one document. The
script underneath is `Paper-Writer/scripts/rebuild-docs.sh` and is fine to call directly.

**It skips the READMEs.** A `README.md` describes the folder it sits in and nobody submits
it, so the walk passes over it and its kin; the list is `SKIP_NAMES` at the top of the
script. Every run says how many it walked past, so the policy is visible rather than
silent. Everything else under the tree is paper prose and gets a `.docx`.

**It fails if a figure went missing.** Pandoc reports an image it could not find as a
warning and exits 0, which is how a section under `parts/manuscript/` can build cleanly and
arrive with all twenty of its figures absent — those paths (`../results/roc.png`) are
written relative to the *paper* folder, not to the part. Each built `.docx` is opened and
its images counted against the ones its Markdown asks for, and a document that came up
short is named and fails the run.

**And it checks that the figures will fit.** A figure with no explicit `{width=...in}` is
imported by pandoc at full page width and pushes the text off its own page. A row of
panels wider than the printable column — 6.00in, measured from the JMIR template — is not
refused by Word but silently shrunk, until the panels stop lining up with the labels above
them. Both are named with their line number. They warn rather than fail, because a figure
that has always been too wide is not a reason to refuse to rebuild the paper today; add
`--strict` on the run before a submission and they fail it.

---

## 0. The shared foundation

Everything downstream depends on turning raw EHR exports into a clean, time-anchored patient cohort
and two parallel representations of each patient.

- **Cohort.** We study major depressive disorder without bipolar or schizophrenia — formally the
  set difference MDD − (BD ∪ SCH). Cohort construction yields **124,188** patients; after enforcing
  a sufficient post-index follow-up window (so treatment-resistance can actually be observed), the
  analyzable cohort is **42,579** (~34% retention). This attrition is *not* treatment-neutral — it
  favors SSRI initiators — which is logged as a limitation.
- **Time anchoring.** Every patient is sliced to a pre-index history window and a post-index
  follow-up window. Every feature is measured at or before the index date, which is what keeps the
  later causal work free of the classic "conditioning on the future" trap.
- **Two representations, built in parallel:**
  1. **Deterministic narratives → neural embeddings.** Each patient's structured record is rendered
     into a human-readable clinical narrative by fixed rules, then embedded by a sentence-transformer
     model into a high-dimensional vector. Missingness is encoded explicitly in the narrative.
  2. **Typed feature vectors.** A parallel path builds a structured table of ~60 typed features
     (counts, flags, categories) straight from the JSON, bypassing text entirely — the classical-ML
     baseline (`feature_vectors.parquet`, 42,579 × 62).
- **LLM clinical-similarity judge.** On the embedding side, for a given patient we retrieve nearby
  patients and ask a language model to score how clinically similar each retrieved pair is, under a
  rigid structured-output schema. Those judgments are cached durably.
- **One shared train/test split** (stratified 80/20) underlies every evaluation, so all methods are
  compared on identical held-out patients, with test patients barred from each other's neighbor
  pools to prevent leakage.

---

## 1. Paper 1 — TRD prediction

### The question

Given a patient's pre-index record, predict whether they will go on to become treatment-resistant.

### What we built

An **asymmetric evaluation matrix** deliberately pitting two philosophies against each other:

| Method | Feature vectors | Embedded vectors |
| ------ | --------------- | ---------------- |
| **Classical ML** (LR, RF, Gradient Boosting, XGBoost) | ✔ | ✔ |
| **Neighbor-weighted KNN + LLM similarity** | — (cosine is ill-defined on mixed categorical/numeric data) | ✔ |

The KNN arm is the novel one: instead of training a classifier, it predicts a patient's risk as a
similarity-weighted vote of their neighbors' outcomes, with four weighting schemes (uniform, raw
cosine, LLM-judged similarity, and a harmonic-mean combination) and four retrieval schemes
(nearest, farthest, random, subsampled). The farthest/random schemes exist as negative baselines —
to prove any signal is real and not an artifact of the geometry.

### What we found

New-cohort results have now been regenerated for **all four encoders**; the primary is
**Qwen3-Embedding-8B** (the full LLM-judged retrieval grid was run on it), and the manuscript and
supplement are fully re-synced to these numbers:

- **Discrimination ≈ 0.66, and the two representations are statistically tied.** On the primary
  Qwen3-Embedding-8B, logistic regression is best at ROC **0.657** (95% CI 0.643–0.672); random
  forest, gradient boosting, and XGBoost sit at 0.62–0.64. The four encoders span a narrow
  0.645–0.657 band. Embedded logistic regression edges the best feature-vector model (XGBoost,
  0.649) in point estimate, but a **paired** bootstrap on that difference — added 2026-08-21, and
  the right test, since both representations score the same held-out patients — returns **+0.008
  (95% CI −0.003 to +0.019)**. The embedding does *not* significantly outperform the
  feature vector, and because the paired interval is about a third the width of the marginal ones,
  that is an absence of advantage rather than an absence of power. The embedded fit is sparse — an
  elasticnet penalty keeps only 385 of the 4,096 dimensions.
- **The tie conceals an interaction — a new result, and the most interesting thing to come out of
  the figure work.** Holding the classifier fixed and varying only the representation, the embedding
  is significantly *better* for logistic regression (+0.028, CI +0.017 to +0.039) and significantly
  *worse* for all three tree ensembles (−0.013 to −0.022, every interval excluding zero). Two
  effects of comparable magnitude and opposite sign, which is precisely why best-versus-best lands
  on a null. A dense 4,096-dimensional embedding suits a regularized linear model and starves
  axis-aligned recursive partitioning, which has no privileged coordinates left to split on. The
  practical consequence for the paper: a representation's value cannot be reported without naming
  the classifier it was paired with. It also reaches the pre-existing "the predictive structure in
  the embedding is approximately linear" claim by a second and more direct route.
- **A clean semantic-ablation result, and the slate is now complete.** Scrambling the
  *psychiatric-history* content of each patient's narrative drops ROC by ≈0.030, and scrambling
  *medication-burden* content by ≈0.025 — while scrambling race, social-determinant, and
  treatment-contraindication content changes nothing (≈0.000). The embedding's predictive signal is
  real and sits in the clinically sensible places, not in demographics. **One concept had never been
  ablated, and the reason given for that was wrong** — caught 2026-08-21. The narrative's
  treatment-exposure section was left off the slate, and Methods claimed it "partly restates the
  information used to construct the outcome label itself". It does not: the label counts
  antidepressant treatments in the post-anchor year, no predictor touches post-anchor data, and that
  section reports pre-anchor exposure only. Permuting it would have leaked nothing. The real reason
  it had been skipped was scoping — the original slate was drawn to ask whether the signal sits in
  clinical content or in sociodemographic proxies, and prior antidepressant exposure was never the
  concept in doubt — which is a reason to run it rather than a reason to argue about it, so it was
  run.
- **The sixth ablation landed 2026-08-22, and the prediction it was supposed to confirm was
  wrong.** The paper expected prior treatment exposure to be the largest delta on the slate, on the
  reasoning that it is the closest pre-anchor analogue of the outcome's own counting rule. It is
  **third**, behind psychiatric history and medication burden: ΔROC AUC −0.019 (95% CI −0.027 to
  −0.011) for logistic regression and −0.011 (−0.020 to −0.003) for XGBoost, with the random-forest
  and gradient-boosting intervals including zero. The explanation is measured rather than argued,
  and it falls straight out of the cohort definition: because the anchor *is* the patient's first
  adequate antidepressant exposure, the treatment-exposure section is **empty for three patients in
  four** and the content that does appear does not separate the outcome groups at all (SMD 0.001).
  A permutation can only destroy variance that exists. **None of that reasoning is in the
  manuscript**, deliberately — the concept is written up exactly like the other five, getting a
  listing in Methods, a row in Table 7 and Figure 10, its rank in Results, and a mention in the
  one-sentence Discussion summary, and nothing more. Three attempts at framing it as something
  special were written and then cut on 2026-08-21/22: a post-hoc hedge, a dedicated Discussion
  paragraph explaining why the delta was smaller than expected, and a mention in Limitations item 5.
  What survived is the plain descriptive fact, as five ordinary rows in Table 2 (any exposure 24.0%,
  prior adequate trial 14.7%); the augmentation row among them reproduces its previously published
  values exactly, which is what validates the other four. The paper presents all six concepts as **one slate** — treatment
  exposure was scored later than the other five, and that ordering is deliberately absent from the
  text, because it is one more attribution result on the same frozen design rather than a post-hoc
  addendum needing a hedge. Adding it disturbed nothing already published: the other five specs were
  re-scored in the same run and came back **identical on every ROC AUC and confidence interval**
  (only Brier moved, at the eleventh decimal). Writing it up also caught a small over-claim in the
  previously published Results paragraph: "none of the sociodemographic permutations produced an
  interval excluding zero" was false — treatment contraindications under XGBoost does, at −0.005
  (−0.008 to −0.001). The paragraph's conclusion is unaffected; the sentence now states its
  exception.
- **KNN neighbor validity check.** Real *nearest* neighbors predict TRD at ROC ≈0.59 while *random*
  neighbors sit near chance (≈0.50) and *farthest* neighbors invert below it (≈0.43) — confirming the
  embedding neighborhood, not an artifact, drives the prediction. The **LLM-weighted** KNN arm is now
  complete: the retrieval scheme dominates the weighting, and the judge adds discrimination only where
  retrieval is already uninformative. The nearest/farthest **fusion predictor** is **closed, and the
  answer is no** (Supplement S7, and *only* the supplement as of 2026-08-21 — the main-text
  Results subsection, its figure, and the matching Discussion subsection were all cut, on the
  grounds that a closed null on a post-hoc secondary analysis does not earn main-text space; one
  pointer sentence in Results is all that remains). Three fusions of nearest with inverted-farthest risk — a
  parameter-free average, a cross-validated convex blend, and an out-of-fold logistic stack — all
  land within 0.006 ROC AUC of the 0.593 nearest-alone baseline, and every 95% interval on the
  *paired* AUC difference includes zero. Those paired intervals are about three times tighter than
  the marginal ones, so the null survives the stronger test rather than reflecting thin power. Two
  details worth keeping: the logistic stack rediscovered the inversion on its own (a negative
  coefficient on raw p_far, never told to invert it), which confirms the farthest signal is real
  while showing it is not *independent* of nearest retrieval — both read the same geometry; and the
  two unfitted variants wreck calibration (Brier 0.142 → 0.241 and 0.187), so they are ranking scores
  only, whereas the fitted stack stays well calibrated. The two tuned variants keep the reported
  score and the shippable parameters strictly apart: every patient's fused score comes from weights
  fitted without that patient, while the weights one would actually deploy come from a separate fit
  over all rows. That separation is what makes the null trustworthy rather than pedantic — the single
  best-fitting blend weight scores 0.600 on the rows that chose it against 0.594 out of fold, an
  inflation the size of the entire effect under test, which is exactly how a null of this kind gets
  mistakenly written up as a win (Varma & Simon 2006; it left the numbered reference list on 2026-08-21 when the fusion paragraphs moved out of the main text, and Supplement S7 now cites it inline in full, which shifted refs 21-25 down to 20-24). Fusing across *different*
  representations or disagreeing encoders is the untested and more promising version of the idea.
- Diagnostics carried throughout: calibration, effective sample size, neighbor "homophily" (does the
  LLM retrieve clinically-congruent neighbors better than cosine?), and confounding checks (is the
  model secretly using data *volume* as a proxy for risk?).

### The engineering journey (where the real time went)

Two multi-week ordeals worth recording:

1. **The data overhaul (July 2026).** The prepped data was re-versioned (DV260629v1-PV260710v1) and
   the entire pipeline had to be re-run. The first attempt died on a storage-quota error because the
   overhaul inflated per-patient JSON size. The fix was to make the ETL **cohort-scoped** — build
   JSONs only for the ~25% of the source population in the study cohort — which shrank the on-disk
   footprint ~4× and fit back inside quota.
2. **Scaling the LLM judging.** Scoring similarity for every held-out patient means **851,600
   judgments per compute task** (4,258 anchors × 4 schemes × 50 neighbors). This went through several
   failure modes before it was stable: a deadlock (an unbounded network timeout leaking concurrency
   slots); a "database is locked" crash from two parallel tasks writing one SQLite file on network
   storage, solved by **sharding** — each task writes its own database, and a reduce step merges them
   into a canonical cache; and finally a subtler reader-writer lock — a per-judgment SQLite commit run
   directly on the async event loop, which let any competing reader or network-filesystem latency stall
   the loop and, being uncaught, crash days of work. That was fixed by moving writes to a **single
   dedicated writer thread** that commits in batches off the event loop, with a lock-wait timeout so
   contention waits instead of failing. Concurrency was then tuned (32 → 64) once profiling showed the
   GPU had headroom, halving a ~7-day run.

### Status

- Pipeline: **complete**, including the two plotting jobs from the 2026-08-20 review, both of
  which landed the same day. `TRD-EHR` gained `plot_discrimination_forest.py`, which builds the
  new Figure 2 straight from the saved metrics JSONs so it can never drift from Table 4, and
  `redraw_feature_importance.py`, which re-renders the feature-importance panels from the saved
  importance summary without refitting anything. The panels are now sized against their 6in
  display width rather than downscaled into illegibility. Both are wired into the analysis
  sbatch chain, with a standalone `plot_manuscript_figures.sbatch` for figure-only re-runs. The
  manuscript packet builds clean, with 23 embedded images carrying its 12 numbered figures.
- **Figure 2 revised 2026-08-21, and it changed a claim rather than a picture.** Two edits. The
  dashed best-feature-vector-model reference line came out **on Rayus Kuplicki's suggestion** —
  he read it as contributing little, and it turned out to be worse than that: its only job was
  to support an eyeball test of whether an embedded interval crossed it, which is the weakest form of the comparison and
  one this same manuscript already argues against in the fusion supplement. In its place, a second
  panel carrying the **paired** bootstrap difference between representations — five contrasts, four
  holding the classifier fixed and one post-hoc best-versus-best. Doing the test properly is what
  produced both bullets under *What we found* above: the headline null is now stated outright
  instead of implied, and the classifier-by-representation interaction is new. Supporting work:
  `classical_ml.py` now persists per-patient held-out probabilities
  (`test_predictions_{EMBEDDED,FEATURE}.parquet`), which is what any paired test needs and what the
  metrics JSONs structurally cannot provide; both files are row-ordered on `sorted(test_ids)`, so
  the plotting script compares them row-for-row and raises rather than proceeding if that alignment
  ever breaks. The tables were backfilled from the joblib model cache without refitting anything,
  and the reproduced AUCs match all eight published values exactly. Text updated in Results,
  Discussion, Limitations item 6, both halves of the Abstract, Conclusions, and TRIPOD item 12e.
- **Figure geometry solved 2026-08-21, and the fix was in the plots rather than in the
  manuscript.** Enlarging the panels for Paulus' comment 8 traded illegible figures for
  half-empty pages, and the cause was geometric, not editorial: Word cannot flow text past an
  image, so a 6in-wide panel standing taller than about half the 9in text column cannot share a
  page with the panel below it and strands the remainder. The tall ones were the confusion
  matrices at 6.21in (their metrics block hung off the bottom of the axes with `figtext`, and
  `bbox_inches='tight'` then grew the canvas to contain it), the forest plot at 5.88in (its axes
  were spanning 41% of their own canvas, the rest margin), and the feature-importance panels at
  5.44in. Rather than shrink anything on the page, the panels were **redrawn wide and short at
  the same full 6in width** — `PANEL_FIGSIZE` in `scripts/shared/plots.py`, with font sizes raised
  to pay for the deeper downscale, so type lands where it did before or larger. Every panel now
  stands 1.80–3.75in, so two fit per page. The redraw is a restyle and not a re-estimate: a new
  `redraw_manuscript_panels.py` reads the per-patient predictions the pipeline already wrote
  (`test_predictions_*.parquet`, `summary_predictions.csv`), calls the pipeline's own plotting
  helpers, and checks each recomputed ROC AUC against the recorded value — **all 24 matched, and
  so did every bootstrap band**, the band being seeded on `SEED` and indexed by row count alone.
  `fusion_analysis.py` was re-run the same way and reproduced `fusion_comparison.csv` and
  `fusion_fit_parameters.json` byte for byte. Two incidental fixes rode along: the confusion
  matrices print their metrics block beside the matrix rather than beneath it, and quote the
  operating threshold to three decimals instead of sixteen. Measured on the rebuilt `.docx`, the
  worst image-forced gap fell from ~6.2in to 2.70in; the residual is a floor set by having one
  full-width panel per row, since a stranded hole can be almost as tall as a panel. Going lower
  means either letterboxing the panels enough to tile three per page or putting pairs side by
  side, which is what comment 8 rejected in the first place.
- **The last ablation is wired in, run, and written up (submitted 2026-08-21, landed 2026-08-22).**
  Adding the concept to the slate
  was one registry entry, because the ablation machinery is registry-driven end to end — the
  narrative builder, the embedding forge, and the scorer all iterate the same list. Three things
  had to be true for it to be that cheap, and two of them already were. The narrative driver
  skips any per-spec file that exists, so only the new concept's 42,579 narratives get written.
  Donor pairings are seeded on the *spec id*, so the five published specs are not re-shuffled.
  The third was not true: the registry has to be **append-only**, because a spec's *position*
  feeds both the Slurm array index and the per-spec bootstrap seed, so inserting one ahead of the
  published five would have moved their already-published intervals. That invariant now has a
  test file of its own, along with checks that every spec targets a bundle the renderer actually
  reaches — a spec aimed at an ignored bundle would emit a narrative identical to the baseline,
  and so a delta of exactly zero that reads as a null result rather than as broken plumbing.
  Adding the sixth spec also found the one genuine chokepoint the README had claimed did not
  exist: the per-classifier ROC overlay figure had its panel count hardcoded at five, so a sixth
  spec indexed off the end. Two new chained jobs do the backfill — embed the named spec on a GPU
  (~3h), then rescore the whole slate on CPU against the frozen classifiers — and both preflight
  their inputs rather than running against a half-built baseline. Rescoring the whole slate is
  unavoidable, since the summary table and the delta figures are written whole; it is also the
  check that matters, because the five published rows must come back identical, and the pre-run
  summary was snapshotted before submitting so they can be diffed. That diff was run 2026-08-22
  and is clean: every published ROC AUC and every confidence-interval bound is bit-identical, and
  the only movement anywhere in the table is the four logistic-regression Brier scores at the
  eleventh decimal place — floating-point summation order over 8,516 rows, invisible at the three
  decimals the paper reports. The snapshot has since been deleted and the append-only test's
  guarded list extended to cover the sixth spec, whose position is now load-bearing like the
  others'.
- The **2026-08-21 markup round** (handwritten annotations on the built PDFs) is applied in full,
  and three of its items were corrections rather than clarifications: the ablation-exclusion
  error described under *What we found*, "cohort-averaged" vital signs (they are means over each
  patient's *own* pre-anchor encounters, not means over patients), and a train/test balance
  paragraph that never said whether it was computed over predictors or over the outcome (it is
  the predictors; the TRD rate matches by construction, the split being stratified). The
  fusion analysis left the main text; `dtypes` became "data type" in prose; the
  "penalizes axis-aligned recursive partitioning" phrasing was reworded because it read as
  though a tuning hyperparameter were involved, when `HYPERPARAMETERS` in `classical_ml.py` is
  keyed by classifier only and the grids are identical across representations. Two stale
  checklist rows surfaced while syncing terminology and were fixed: item 6c still carried the
  wrong ablation justification, and item 6b still claimed the extract covers "the whole system",
  which is the same inaccuracy Paulus' comment 30 removed from the Setting paragraph.
- **The paper compares two things, so it now uses two names for them (2026-08-23).** The feature
  vector had been carrying a second name — "the rule-based feature vector" — in the title, in
  Methods, in three figure panel labels, and in the Discussion, alongside a third stray alias
  ("engineered feature vector"). A second name for one of two compared objects reads as a third
  method, so both are gone: there is the **feature vector** and there is the **embedding**, and
  nothing else. The **title changed with it** — *Typed Feature Vectors Versus Neural Narrative
  Embeddings …* — which propagates to the cover letter and the checklist, since both quote it. One usage was not an alias at all and was retained under a better
  word: the sentences arguing that no generative model writes the narratives now say
  "deterministic", which is the actual claim and is already the word used elsewhere in Methods.
  No number, model, or result is affected. The rule is recorded in the `manuscript.md` header
  comment and in the task list so it does not creep back.
- **The ablation slate now says what it ablates (2026-08-23).** Methods had named its six
  permutations and left the reader to guess what each concept contained — which makes the
  headline attribution result unreadable, since the whole finding is *which* concept carries the
  signal, and nobody could tell medication burden from treatment exposure. Each of the six is now
  defined by the narrative content its permutation destroys: the eight comorbidity flags,
  suicidality flag and named substances in psychiatric history; every drug ingredient active at
  the anchor regardless of indication, plus NSAIDs, in medication burden; per-class adequate-trial
  counts, benzodiazepine days, hypnotics and the augmentation flag in treatment exposure; the two
  prescribing constraints (seizure disorder against bupropion, uncontrolled hypertension against
  SNRIs) in treatment contraindications; and the two sociodemographic fields. Writing them out
  caught a wording error that had been in the paper since the slate was first reported: treatment
  contraindications was grouped with race and social determinants under "sociodemographic
  variables", which it is not — it is a prescribing-safety concept, and general medical
  comorbidity is a separate narrative section that was never permuted at all. Three sentences in
  Results and two figure captions were corrected; no delta moved.
- Analysis: **complete** — every planned investigation landed by 2026-08-07 (the full re-run on the
  new cohort, all four encoders for the cross-embedder robustness figure, the bge-small
  within-cluster substructure analysis (Supplement S5), and the nearest+farthest fusion follow-up
  (Supplement S7, a confirmed null)), and the one analysis that came back onto the list on
  2026-08-21 — permuting the narrative's treatment-exposure section, the concept the ablation slate
  never covered — **landed and was written up 2026-08-22**. Nothing from the paper's *own* design is
  outstanding; what analysis remains is review-driven and listed with the 2026-08-28 round below.
  Limitations item 5 no longer records a gap in coverage; it records the single-concept limit
  that applies to the whole slate, now pointed at the two concepts that share the pre-anchor window
  (treatment exposure and medication burden) and so cannot be separated without joint perturbation.
- Manuscript: **in senior-author revision** as of 2026-08-20. It was submission-ready on
  2026-08-14 with coauthor feedback incorporated 2026-08-17; Martin Paulus then returned a
  full tracked-changes review (82 insertions, 26 deletions, 11 comments) on 2026-08-20, and
  that round is now applied — see the sub-list below. Body, front matter, in-text citations,
  and the reference list are drafted and reviewed with every number re-synced to the new
  cohort; title, affiliations, ORCIDs, corresponding author, and the operational TRD
  definition were supplied by the authors 2026-08-05. The packet is four documents — manuscript,
  supplement, TRIPOD+AI checklist, cover letter — built and rebuilding clean; the
  response-to-comments memo was retired on 2026-08-30, having answered the previous revision
  round, and is recoverable from git history. All four were rebuilt 2026-08-30, when the heading styles in the shared
  JMIR reference template were opened up so sections breathe on the page — 36pt above a
  top-level heading against 10pt below it, 20/7 for subsections, on the principle that the
  space above a heading should be two to three times the space below so the heading binds to
  the text it introduces. Panel heights are untouched, so the page geometry solved on
  2026-08-21 still holds: the tallest panel is 3.75in against the 4.50in
  pair-on-a-page threshold. A second review round of nine items arrived 2026-08-28 and its
  **analysis is now closed** — see the sub-list below. A third round arrived 2026-09-02 and is
  applied — see the sub-list below. What is left wants the authors'
  judgement rather than our work: the sampling-frame framing, whether the
  classifier-by-representation interaction deserves more than its two paragraphs, whether the
  fusion analysis should have stayed in the main text, and whether the retrieval and judge arm
  belongs in the supplement at all.
- **The review round of 2026-08-28 corrected the paper's index event, and that is the round's
  real result.** The paper had called its anchor "the first adequate antidepressant exposure" in
  the title, the abstract, the introduction, Methods and the Discussion. It is not. The anchor is
  a patient's **earliest antidepressant prescription recorded on or after their first documented
  depression diagnosis**, and no adequacy, dose, or duration criterion enters its selection —
  checked against the pipeline, which sorts the upstream index table by prescription start and
  keeps the earliest row per patient, and against the table itself, where every candidate order
  starts on or after the first depression-diagnosis date (minimum gap zero days, 57.9% on the same
  day). Two things fall out. The reviewer's sharpest objection — that prediction cannot happen at
  the prescription date if adequacy requires observing 42 future days — **does not apply**, because
  nothing about the anchor reads post-anchor data; post-anchor information enters only as the
  follow-up requirement and the outcome window. And the apparent contradiction of listing prior
  adequate trials as predictors of a "first adequate exposure" dissolves: the anchor is indexed to
  the first *documented diagnosis*, so 14.7% of patients can and do carry an earlier adequate
  course. Methods now carries the exact algorithmic definition — anchor selection, required future
  information, lookback, prior-trial handling, outcome ascertainment — and the old phrase appears
  nowhere.
- **The rest of that round is claim discipline, and it cost the paper four claims.** Applied in
  full: the target is named as a **treatment-switch–defined EHR proxy** in the title, the abstract
  and at first mention of every result (the title changed with it, propagated to the cover letter
  and checklist); "statistically equivalent" is gone, replaced by "no evidence of
  superior discrimination", with Methods stating outright that no equivalence margin was ever
  prespecified; the **fairness claim is withdrawn** — the ablation is recast as a *direct-input
  reliance* analysis, the three questions it cannot answer are stated where it is defined, a new
  Limitations item says the study reports no fairness evidence, and TRIPOD item 14 now records
  that no fairness assessment was performed; and every "component of risk stratification" claim is
  out of the abstract, conclusions, keywords, checklist and supplement, replaced by the statement
  that temporal and external validation, subgroup evidence, and a prospectively derived operating
  point are all prerequisites. Two further items were softenings the data required rather than
  requests: the Youden threshold is chosen on the same held-out patients the models are scored on,
  so its sensitivity and specificity are now descriptive of the ROC curve and explicitly not
  candidate operating characteristics, and calibration is stated as calibration to a case-enriched
  cohort's own base rate; and the missing-not-at-random argument is weakened to what the data
  support — the outcome association rules out missingness *completely* at random and identifies no
  mechanism beyond that.
- **Two disclosures were added rather than fixed, and one of them bounds the headline claim.** The
  two representations do not receive an identical field inventory: the narrative renders the three
  within-patient mean vital signs that were dropped from the feature matrix at load time, a
  recorded sexual-orientation field absent from the feature inventory entirely (rendered as the
  literal token `nan` when unrecorded), and the anchor's calendar date, for which the feature
  vector has no column; it also names individual medication ingredients where the feature vector
  carries only counts, while pre-anchor history length is a feature-vector column the narrative
  never renders. That mismatch is the size of the effect under test — ≈0.008 AUC on the
  head-to-head contrast — so it bounds the parity claim rather than qualifying it, and it is now a
  Limitations item with the offending fields pointed at in Supplement S6. Separately, the LLM judge's
  rubric names evidence the narratives do not contain: PHQ-9 subitems, of which this extract
  records none; no-show behaviour, which is not a narrative field; and a three-year window where
  the lookback is two years. The prompt is reproduced as it was run and is not edited. **Nothing
  reported is inflated by the mismatch, and that was measured rather than
  assumed**: over a systematic 1-in-57 sample the phenotype sub-score is zero for only 31.4% of
  pairs, takes 15 distinct values with a median of 60 otherwise, and correlates 0.58 with the
  overall score — so the model ignored the PHQ-9 framing and scored baseline phenotype from the MDD
  recurrence and severity coding and psychiatric flags that *are* present, rather than obeying the
  prompt's "output 0 if Missing" rule. The mislabel is in the rubric's wording, not in the
  behaviour, and only the overall similarity score becomes a neighbour weight — that weighting is
  scored against outcomes the judge never sees, so a thin judgement can only lower the
  discrimination reported. The one genuine cost is the reach of the
  null — the finding is that *this* rubric added nothing over plain cosine under nearest retrieval,
  not that LLM similarity judging cannot, and the same rubric did lift discrimination where
  retrieval was uninformative (0.495 to 0.517 random, 0.543 to 0.554 subsampled). Whether the
  1.71-million-judgement cache survives is a separate question from whether it inflated anything,
  and it is decided by the prompt-correction check below rather than by the measurement above.
- **The open work from that round is deliberately smaller than the round asked for, and all
  of its analysis is now closed.** The governing scope is the authors' own annotations on
  the review rather than the reviewer's wording: three items were cut down, two declined
  outright, one enlarged. What remains is the authors' judgement and sending the packet
  back.
  - **The held-out set is representative of the training set, and the paper now shows it
    rather than asserting it.** Over 100 predictor rows the largest absolute standardized
    mean difference between the two halves of the split is 0.036 and none reaches 0.1; the
    maximum sits on a social-determinant flag held by 22 training patients and no held-out
    patient, which is a small-cell artifact. The distributions are Supplement S9, in the
    same form as the cohort table. The main text now also says what this does *not*
    establish: both halves inherit the delivered extract's case enrichment equally, so a
    comparison between two halves of a selected cohort cannot detect the selection they
    share, and calibration remains calibration to this cohort's own base rate.
  - **Subgroup performance contradicted the plan twice, and the second time it
    corrected the first.** The analysis refits nothing — the per-patient held-out
    probabilities are partitioned by stratum, which is the right design, since the
    question is how the published models behave on subpopulations they were already
    scored on. The plan was logistic regression on four groups, expecting no
    significant difference. What was actually run covers **three prediction arms**
    (embedded, feature vector, neighbour-weighted), **eight stratum families** and
    all four classifiers, producing 288 contrasts, each carrying a bootstrap p-value
    adjusted across the whole set by Benjamini–Hochberg. Seventy-two exclude zero
    unadjusted; **35 survive correction**. Sex is a clean null: twelve contrasts,
    none excluding zero, none above 0.012 AUC. Race is *not* what an interim reading
    suggested — all twelve White-minus-non-White contrasts are positive and seven
    exclude zero unadjusted, including all four neighbour-weighted configurations,
    but **none survives adjustment** (smallest adjusted p = .08), and non-White
    calibration is worse in the feature arm (slope 0.79 against 0.98). It is
    reported as neither settled nor dismissed: the limit is power, at 302 minority
    outcome events against 1,181. **What survives is clinical.** Twenty-four of the
    35 concern how the depression is coded — recurrent coding discriminates better
    (+0.059 to +0.082), single-episode and unspecified worse (−0.077 to −0.047) — in
    twelve of twelve arm-model combinations each way. The models do better where the
    diagnosis is recorded specifically and worse where it is left unspecified, which
    describes most of this cohort. Two sociodemographic contrasts also survive: age
    18–29 in the feature arm and never-married patients in the embedded arm, both
    consistent with thinner records supporting weaker prediction. The scoped-down
    version of this analysis would have reported a race gap that does not hold at
    this evidence level and missed the finding that does.
  - **The field-level crosswalk found more asymmetry than the disclosure described.**
    Eleven fields differ between the representations and ten of the eleven favour the
    narrative. Two were not on the original list: four sociodemographic fields — preferred
    language, marital status, religion, smoking status — are collapsed into coarse
    categories in the feature matrix while the narrative prints the raw recorded value, so
    the narrative carries strictly finer resolution on them; and missingness on the
    categorical side of the feature matrix is *not* dropped, since an absent value becomes
    its own one-hot level. Both were read off the pipeline source rather than from the
    manuscript's description of it, which is how the first went unnoticed. The crosswalk is
    Supplement S11.
  - **Time zero now has a figure**, added as Figure 1 — which renumbered the previous
    Figures 1–11 to 2–12 across four documents. Its window widths and the annotated median
    history length are read from the pipeline rather than typed.
  - **The matched-input re-run is done, it is a null, and it does not go in the paper.** Not
    the full pipeline pass: the feature matrix receives the vitals with an explicit
    missingness indicator per block and within-fold median imputation, the narrative
    receives recorded history length, and the comparison uses two classifiers rather than
    four, one encoder rather than four, cosine and uniform neighbour weighting with no LLM
    judging, and no ablation re-score. Its only job was to decide whether the expensive
    version is needed, against a rule fixed before the numbers existed. **It is not.** On
    matched inputs the best-versus-best contrast is +0.007 (95% CI −0.004 to +0.016)
    against +0.008 as published — still a null, point estimate slightly smaller, interval
    slightly tighter. The published comparison stands and the field mismatch does not carry
    it. On the authors' instruction the result is held in reserve: written up in full as
    `paper1-trd-prediction/reserve/matched_input_parity.md` with its numbers tracked beside it,
    kept out of the submitted packet, and produced only if a reviewer presses the field
    mismatch, which Paulus does not expect. Supplement S12 was removed accordingly and the
    four places that pointed at it now state the result in a clause. What the packet
    carries is the *disclosure*: Limitations item 9 and the Supplement S11 crosswalk.
  - **The feature arm gains, and the arm the embedding was beating is the one that
    gained.** Restoring the vitals moves feature-arm logistic regression from 0.629 to
    0.643 — paired +0.014 (+0.009 to +0.020) — while XGBoost is unmoved at 0.649 → 0.651.
    Both models selected exactly the hyperparameters their published counterparts selected,
    so the gain is the three columns rather than a different point in the grid, and the
    larger change is to calibration: the linear model's slope goes 0.779 → 0.922, most of
    the way out of systematic overconfidence. The consequence for the paper is the one the
    crosswalk predicted and it is counterintuitive: **the headline null gets safer while
    the one contrast that reached significance is halved.** The classifier-fixed
    logistic-regression contrast falls from +0.028 to +0.015. It still excludes zero, so
    the classifier-by-representation interaction survives — the embedding is still
    significantly better for logistic regression and significantly worse for XGBoost, which
    is exactly why best-versus-best is a null — but the positive half of that interaction
    is half the size once the two representations are fed comparably. The XGBoost half is
    unchanged at −0.0135.
  - **Two stability facts came out of the control arm that the study did not have.**
    Re-rendering the narratives with *no content change at all* leaves every fitted
    classifier where it was — all four contrasts null, the largest +0.003 — but moves
    nearest-retrieval KNN by +0.004, larger in point estimate than the field under test and
    in the opposite direction. Retrieval consumes the embedding geometry directly while a
    fitted model re-optimizes against whatever geometry it is handed, which is why one
    notices the rebuild and the other does not. The second fact is sharper: **the selected
    model is not stable even where its discrimination is.** The published embedded logistic
    regression chose a sparse elasticnet penalty and the manuscript reports that only 385
    of 4,096 dimensions carry nonzero weight; both re-rendered arms chose a dense L2, and
    the two land within 0.003 AUC of each other. The sparsity figure is descriptive of the
    published fit, which is what the manuscript says — but it is not evidence that the
    predictive structure must be concentrated in a few hundred dimensions, and it is worth
    deciding whether the paper should say so.
  - **The half that decided it had to be re-run, and both reasons it died are the reusable
    kind.** The two narrative arms are four-stage chains — render, embed, neighbours, fit —
    and both were killed at the twelve-hour wall part-way through the embedded
    logistic-regression grid search, with everything upstream complete on disk. First
    cause: the submitted copy ran the neighbour stage *before* the classifier fit, so the
    stage the whole decision rests on received whatever time the cheaper corroboration left
    it, 5.9 hours of twelve. Order the stages by what the result depends on, not by the
    order they were written. Second: it asked for 16 CPUs while the grid search runs 16
    worker processes, leaving each worker's BLAS one core on a fully subscribed allocation;
    the published run fitted the same grid on the same matrix in 4.9 hours with 48. The
    recovery job ran the fit standalone against the surviving embeddings, so nothing was
    re-rendered or re-embedded — only possible because every stage wrote its artifact to
    disk before the next one started. It landed 2026-08-30, at 6.0 hours per arm for the
    logistic-regression grid even at the wider allocation.
  - **A reproducibility defect surfaced while building that re-run, and it is ours.** The
    narrative renderer emitted its comorbidity, prescribing-safety and prior-trial flag
    lists by iterating Python sets, whose order varies between processes, so re-running the
    renderer on identical input produced identically informative but differently *ordered*
    text. The published narratives are therefore not byte-reproducible. No published number
    is affected — each narrative was rendered once and every embedding, neighbour set and
    judgement was computed from the text actually written — but a re-render cannot serve as
    a byte-level control, so the parity comparison carries a control arm re-rendered with no
    content change. That arm also answers something the paper never had an answer for: how
    stable the embedded arm is to a rebuild of its own inputs. The renderer sorts now.
  - **The judge rubric is corrected and re-tested rather than only measured.** Measuring
    what the model did with the mislabelled PHQ-9 dimension is not the same test as asking
    what it does without it, so the dimension is removed, the surviving five rescaled from
    20/20/20/10/5 to 27/27/27/13/6, and 5,000 cached pairs are being re-judged under the
    corrected rubric with one model instance. Exactly one thing changes, which is what makes
    the correlation attributable; new judgements go to their own database so the published
    cache is untouched. The decision rule is fixed: close agreement and the cache stands,
    material divergence and the full 1.71M are re-judged with the corrected prompt replacing
    the one printed in the supplement.
  - **Two requests are declined, and both are conceded in Limitations** — item 4 carries the
    temporal-split position in full, and item 2 names the sensitivity label as one of two
    things that would sharpen the target and are not done here. What Limitations does not
    say is *why* the label cannot be built from this extract, which is the one piece the
    retired response memo carried alone. A high-yield sensitivity label is declined
    because the motive behind a post-anchor medication change is not recoverable from this
    extract, so a label conditioned on "clinically plausible" switching intervals would
    encode an assumption rather than remove one — invisibly, since any threshold would be
    defensible and none verifiable. A temporal validation split is declined for this
    submission on the review's own alternative: every risk-stratification claim is gone, and
    Limitations item 4 states that this is internal validation by one random split, that the
    paper says nothing about temporal transportability or coding drift, and that the reported
    discrimination is an upper bound on deployment.
  - Still authors' judgement rather than work: whether most of the retrieval, judge and
    fusion material moves to the supplement.

  They are itemized with their costs and decision rules in `planning/TRD-EHR_TODO.txt`.

- **The review round of 2026-09-02 is a restructuring round, and it is applied (2026-09-03).**
  Paulus returned tracked changes and nine comments together with two replacement documents —
  a condensed Methods with a matching supplementary-methods appendix, and an integrated
  Discussion carrying new literature. Four things changed shape rather than substance. **Time
  zero is now the *index*, not the anchor**, in all four packet documents; "anchor" survives
  only in its retrieval sense (a query anchor), and the deterministic renderer's own field
  labels, which still say `MDD-to-anchor gap`, are reproduced verbatim in Supplement S6 with a
  sentence saying so. **Methods went from ~4,600 words to ~2,540** against a ~2,000 target;
  nothing was deleted, it was relocated into a new Supplementary Methods block (Supplement
  M1-M13) that now sits at the front of the supplement, with every Methods subsection pointing
  at its M-section. **Two sections left the main text** — the participant-flow table, now
  Supplement M2 Table M1, and subgroup outcome prevalence, now Supplement S12 — so the cohort
  table is Table 1 and its Results prose is one sentence; the train/test summary table was
  dropped outright, its two numbers now living in Methods. **The Discussion is his**, with one
  consequence: **his draft has no Limitations section, and as of 2026-09-03 neither does the
  packet.** The nine items are held whole in `limitations_reserve.md`, and the removal is
  smaller than it sounds — seven of the nine still say something the packet says elsewhere,
  because his Methods absorbed several of them wholesale, Supplement M1–M13 carry the rest,
  and his own Discussion argues fairness and the outcome proxy at length in its own words.
  **Exactly two disclosures left the packet**: that dropping the vital signs may be the wrong
  handling for a prediction problem, where informative missingness is usable signal; and that
  the reported discrimination is an upper bound on later or external data. Both are one
  sentence, both are recorded, and the checklist's TRIPOD item 26 now points at the sections
  that carry limitations rather than at a heading — which is true, and weaker than a heading. Seven references were appended (25-31). The embedding is a "generalized pretrained
  transformer embedding" throughout the body **and in the title**, which changed with it
  (2026-09-03) to *Typed Feature Vectors Versus Generalized Pretrained Transformer Embeddings
  of Patient Narratives …*, propagated to the cover letter and the checklist.
- **The one comment that was a defect rather than a preference was the figure.** Comment 172
  said the ablation forest plot's labels could not be read, and the cause was the same
  geometric one solved for the panels on 2026-08-21 and missed here: the figure was generated
  one-by-four at 20 inches wide, so at the manuscript's 6in text width it downscales 3.3x and
  15pt type lands at 4.5pt. It is now a two-by-two grid at 10 x 7.4in — 4.44in tall on the
  page, inside the 4.50in pair-on-a-page threshold — with row labels on every panel.
  `TRD-EHR` gained `redraw_ablation_forest.py`, which rebuilds the PNG from
  `ablation_summary.csv` and the baseline metrics JSON and checks every delta against the
  recorded value before writing, and `plot_ablation_roc_ci` in the pipeline carries the same
  geometry so a re-run cannot regress it. No number moved.
- **Methods is now his Methods, and the cut has a paper trail.** Rather than meet his
  ~2,000-word target by trimming our own condensation, the manuscript carries his supplied
  replacement essentially as written: **1,851 words against the 6,057 it started at**, with
  departures confined to cross-references, citation markers, and two facts his draft could
  not have known — the eligibility cascade had moved to the supplement under his own comment
  115, and the cohort table had become Table 1 under comment 119. Almost everything the cut
  removed was already relocated into Supplement M1–M13, which is submitted. The remainder is
  `paper1-trd-prediction/reserve/methods_reserve.md`, held out of the packet: eight
  passages that survive nowhere in the submission, each reproduced verbatim with the section
  it came from and the reviewer question that would want it back. It also carries the rule
  that keeps the section from re-inflating — **Methods does not grow**; new material goes in
  its M-section, and anything ever removed from the packet gets an entry there.
- **The third one-off "does this change anything" analysis is closed, it is a null, and it
  does not go in the paper: religion.** His supplementary methods asked for a sensitivity
  analysis comparing retaining religion against removing it, and the question is really about
  the missingness rather than the field. Religion is unrecorded for 29.4% of the cohort and
  the absence is not uniform — 43.8% at ages 18–29 against 17.5% at 65 or older — and both
  representations make that absence readable, the feature matrix as its own one-hot level and
  the narrative as a literal `Missing` token, so a model can use the field's absence as an age
  proxy without ever using the field. **Removing is not permuting**, which is why the ablation
  slate does not answer it: a permutation destroys the link between a patient and their own
  value while leaving the pattern of who has one intact. `TRD-EHR` gained
  `scripts/pipeline/review/religion/`, mirroring the parity package, with two arms — the
  feature matrix minus the Religion column (59 → 58), and the narrative re-rendered without
  the field and re-embedded. **All six contrasts are nulls.** The deciding pair, the
  religion-free narratives against the parity round's `narrative_control`, are +0.0013 (95% CI
  −0.0017 to +0.0039) for logistic regression and −0.0031 (−0.0083 to +0.0024) for XGBoost;
  the feature arm is a precise null at +0.0001 and +0.0002 with both intervals inside ±0.0015
  and both models on the published hyperparameters. So the field is not load-bearing, and
  neither is the shape of its silence: taking away the content *and* the pattern of who has a
  value changes neither model's ranking. On the parity precedent the write-up is held in
  reserve — `paper1-trd-prediction/reserve/religion_sensitivity.md`, numbers tracked beside it in
  `reserve/religion_results/`, out of the submitted packet — and the packet changes by the one
  sentence the pre-fixed rule allowed: Supplement M6 no longer says no such analysis was
  performed, and states the null in a clause instead.
- **The comparator was the whole analysis, and the corroborating contrast shows why.** Scoring
  the religion-free arm against the parity round's re-render-with-no-content-change, rather
  than against the published embedded arm, is what made this affordable — the control was
  already on disk — and it is also what made it honest. The same arm scored against the
  *published* run returns +0.0042 (−0.0006 to +0.0087) for logistic regression: three times
  the deciding point estimate, within a thousandth of excluding zero, and mostly measuring the
  +0.0029 that the parity round had already attributed to re-rendering alone. Had that been
  the deciding contrast, a null would have been written up as a near-miss. One caveat sits on
  the other row: embedded XGBoost moved from depth 5 to depth 8, which is the parity round's
  known grid instability across a rebuild rather than anything about religion — the published
  embedded XGBoost is itself depth 8 — so that single point estimate is not cleanly
  attributable, and its interval includes zero regardless.
- **A calibration lead was chased and dropped, which is the outcome worth recording.** In the
  feature arm, removing the column moved calibration further than it moved discrimination:
  the linear model's slope 0.778 → 0.935 and its intercept 0.058 → 0.014, with nothing
  re-rendered and the hyperparameters unchanged, so the movement is attributable. It stays an
  observation and not a finding for three reasons. The sign is inconsistent inside the same
  arm — XGBoost moves 1.016 → 1.094, *away* from one. Brier moves by at most 0.0004 anywhere
  and not at all in the two feature-arm cells, so the same total error is redistributed rather
  than reduced. And the embedded arm cannot corroborate it, because its own noise floor is
  larger than the effect: a bare re-render moved the embedded XGBoost slope from 0.750 to
  1.636, about twice what removing religion then contributed and in the opposite direction.
  The lead was worth following and it was worth not publishing.
- **The seven new references are verified, and three of them were wrong as first entered.**
  Checked 2026-09-03 against PubMed and, where obtainable, the papers themselves: all seven
  resolve to a real work, and Cepeda's issue and pages, Iveson's author list with its volume
  and pages, and Walsh's author list were all incorrect and are corrected. **Every competitor
  discrimination figure quoted in *Comparison with prior work* is exact** — Liberman's 0.83
  over 24 months in 35,246 people, Lage's externally validated 0.652 (0.623–0.682) with a
  top-quintile lift of 1.99, Lee's 0.684 / 0.569 / 0.728, and Walsh's internal 0.58–0.64
  falling to 0.51–0.58. Five are now held as PDFs in `references/`; Lage and Lee are not open
  access and have reprint requests drafted, so nothing is now blocked on them — their numbers
  are already confirmed from the published abstracts. The whole round is written up item by
  item in `paper1-trd-prediction/review/round_2026-09-02.md`.
- **A follow-up round arrived 2026-09-04, and it is staged rather than applied.** The
  reason to hold it is that more rewritten sections are coming, and every item in it would
  otherwise be done twice — once over our text and once over his. Its verdict is on the
  prose: the writing is dense, correct, and machine-sounding, and a sentence has to be read
  three times before it gives up its meaning. That is measurable rather than a matter of
  taste — the body text averages 26.2 words a sentence against a readable 18–20, 23% of its
  sentences run past 35 words, and it carries 74 semicolons and 34 em-dashes, nearly every
  one of which welds a second claim into a sentence that already had one. It also collides
  with his own comment 84, which cut Methods from 6,057 words to 1,851: compression is what
  produces density, so shorter and clearer are two different instructions, and the way out
  is fewer claims with more room each. The rest of the round is three word changes
  (deterministic → algorithmic, patient → participant, trained classifier → machine learning
  model), two supplement sections moving to `reserve/` rather than being cut (the
  cosine-similarity bimodality, S5, and the fusion analysis, S7 — the third demotion of that
  material, on the same argument each time), and one instruction about the Discussion's
  take-home that is being confirmed before anyone acts on it, since it would reframe
  *Principal findings* around parity with the published literature rather than parity
  between the two representations. Each item is costed, with its exclusions, in
  `paper1-trd-prediction/review/round_2026-09-02.md` and staged in
  `planning/TRD-EHR_TODO.txt`.

- The Paulus review of 2026-08-20 is **applied, with three items still open.** He reviewed
  the *2026-08-14* build, which predated the 2026-08-17 coauthor edits, so his
  "two or more"→"three or more" changes on the TRD definition were already satisfied and
  were not re-applied. What his review changed structurally:
  - **A new Figure 2, a discrimination forest plot**, replacing the eight-row Table 4 as the
    primary display of model discrimination — he sketched it as ASCII in the margin. This
    **renumbered every figure**: old 2–11 are now 3–12, across manuscript, supplement, and
    checklist. The PNG landed 2026-08-20 and was revised into a two-panel figure on
    2026-08-21 (see *Status* above) — a request for a display turned into a change of result,
    which is the most useful thing a reviewer margin note has done on this paper.
  - **Results were evicted from the Discussion.** The `Fusing the farthest-retrieval signal`
    subsection was split: its results and Figure 12 became a new Results subsection, and the
    Discussion keeps interpretation only.
  - **A methods section was evicted from Results.** `Provenance of performance results` moved
    into Methods as the *Evaluation coverage* paragraph.
  - Two long Methods digressions — the missing-not-at-random justification and the
    preprocessing-leakage explanation — were cut to two sentences and one paragraph
    respectively, on the grounds that neither belongs in a Methods section.
  - All eleven comments are now closed. Nothing in the manuscript carries a `[CONFIRM]` marker,
    and no item is blocked on a coauthor. The only work left is the two plotting jobs.
- A **references folder** dropped 2026-08-20 answered a different question than the one asked.
  Paulus' comment 44 wanted the prior papers behind our *predictor* selection; none of the 20
  files concerns treatment-resistant depression or antidepressants at all. They are the
  digital-twin / LLM-EHR-representation literature. **Comment 44 was closed without new
  literature**: the provenance was already in the reference list, anchored on Perlis 2013 —
  a logistic-regression TRD risk model whose manual-review-then-prune selection strategy is
  precisely the one this study follows — with Kautzky, Sheu, and Chekroud supplying the
  predictor domains. Four papers from the batch *were* worth keeping and are now refs 21-24 (they were 22-25 before Varma & Simon left the list):
  Shmatko 2025 (*Nature*, Delphi-2M) and Waxler 2025 (CoMET) frame event-sequence pretraining
  in the Introduction as the expensive alternative our cheap serialize-and-embed design
  competes with; Hegselmann 2024 (CHIL, LLM patient summaries — a different paper from ref 9)
  justifies the deterministic renderer; Lee 2026 (LLM-as-a-judge reporting) pre-empts the obvious
  objection to the judge arm. The rest of the batch was discarded.
- The same folder contained **`SFHS Dataset Query Documentation`**, which closed comment 30 and
  **corrected a factual error**: the Setting paragraph claimed the extract "spans the full
  system rather than any one service line," but it is restricted to a single Epic service area.
  Methods now names Epic, Caboodle and Clarity, the seven delivered tables, the MD5-hashed keys
  and SFTP transfer, the extract-level person and encounter filters, and the verbatim
  ICD-9/ICD-10 code lists behind the three diagnosis flags. That document is now kept at
  `paper1-trd-prediction/references/DATA_PROVENANCE_SFHS_query_documentation.docx`, since the
  Methods section is unverifiable without it. The extraction dates are confirmed from the
  filesystem rather than inferred: the delivered tables are named `*_Table-26_06_29-v1.tsv`
  against the documented naming convention, and the analysis-ready tables were built 2026-07-10.
- **The most consequential finding of this round did not come from Paulus.** That documentation
  revealed, and the data then confirmed, that the delivered extract is **case-enriched**: all
  depression-flagged patients were retained while unflagged patients entered through a 4:1
  random sample. `Person_Table.csv` carries a `GroupType` column splitting its 501,718 rows
  100,420 / 401,298 — exactly 20/80 — and joining that column against the 42,579 analysis-cohort
  patients shows **29.4% (12,530) arrived through the sampled arm**, because the cohort
  definition counts encounter diagnoses while the flag was built from the problem list. So
  501,718 is a sampling frame, not a source population. This is now written into a new Methods
  subsection *Sampling frame*, the participant-flow paragraph, the Table 1 row label, and
  Limitations item 2. The position taken is that it bounds the cohort's descriptive reading —
  17.5% is not a population prevalence, and is if anything biased upward — but leaves the
  head-to-head representation comparison untouched, since both arms use identical patients.
- Coauthor feedback of 2026-08-17 **closed all three outstanding people-items**, and all three
  are now in the built documents:
  - **TRD definition** restated in the wording of Forthman et al. (*J Affect Disord*
    2025;390:119858) — TRD assigned to MDD patients with three or more antidepressant treatments
    within one year — with that paper added as reference 21 and cited as the source of the
    definition. Numerically unchanged from the previous switch-count phrasing; the arithmetic
    equivalence is stated in *Outcome*, and the Abstract, Limitations, and TRIPOD item 8a were
    re-worded to match.
  - **Ethics/IRB**: secondary analysis of de-identified data, therefore not human-subjects
    research subject to IRB approval. No reviewing body, protocol number, or consent waiver
    exists to name; TRIPOD item 17 is recorded as not applicable on that basis.
  - **Funding**: the William K. Warren Foundation, and no other funder. The previous "no
    specific grant" sentence is gone.
  - Also applied: the author list and ORCID table now read **Katherine L. Forthman**, and the
    contributions statement uses KLF.
- Reference library: **assembled** at `paper1-trd-prediction/references/` — **21 of the 24** cited papers on
  disk (reporting standard, ML software, embedder/LLM-judge model cards, TRD epidemiology, prior
  EHR/ML TRD-prediction work, the LLM-as-EHR-encoder antecedent, and as of 2026-08-20 two EHR
  foundation-model papers plus two design-justification papers). Two remain (Rush 2006 STAR\*D,
  Kautzky 2017), both paywalled with reprint emails drafted; refs 18–19 are background-only with
  no PDF held. Gaynes 2020 obtained 2026-07-27, Hegselmann 2025 added 2026-07-29. The folder also
  holds the SFHS extract query documentation as a data-provenance source rather than a citation.
- Causal supplement: **decided 2026-08-13 — no.** Target Trial 1 does not join Paper 1. The
  Discussion already names causal-forest / heterogeneous-treatment-effect modelling as future
  work and explicitly declines to pursue it, and that stays the whole treatment unless a reviewer
  asks for more. The causal-forest numbers now serve Paper 2 as its triangulating estimator
  instead.

---

## 2. Paper 2 — Counterfactual antidepressant selection

For a patient about to start or switch antidepressants, which drug *class* gives the best expected
outcome — and can a recommendation rule built on that beat standard prescribing?

### The pivot

The obvious version of this project — "learn a heterogeneous-treatment-effect model, read off the
best drug per patient, claim clinical utility" — is unrealistic and so this paper will build
around that fact rather than hide it.

The causal-forest sweep over three active-comparator class contrasts returned:

| Contrast | ATE (95% CI) | Read |
| ------------ | --------------------- | --------------------- |
| SNRI vs SSRI | 0.037 (−0.086, 0.161) | thin, CI crosses zero |
| Bupropion vs SSRI | 0.040 (−0.092, 0.172) | null |
| Bupropion vs SNRI | 0.017 (−0.084, 0.119) | null |

Every average effect is statistically indistinguishable from zero, and the heterogeneity signal is
essentially flat. The one apparent "hit" in earlier runs turned out to be dominated by
illness-burden proxies (encounter count, age) — **confounding by indication wearing a heterogeneity
costume**, not a real treatment effect.

### The diagnosis

The problem is not the estimator; it is **identification**. A causal forest can only remove
confounding through *measured* covariates, but antidepressant choice is driven by severity that is
only partially recorded. We can't see everything the doctor sees. No model can change that. This
diagnosis is grounded in Angrist & Pischke's *Mostly Harmless Econometrics* and
is documented in full in `paper2-counterfactual/CAUSAL_IDENTIFICATION.md`.

### How an effect is estimated — and how we try to break it

In plain terms: for each drug pair (say SNRI vs SSRI) we build a model of expected TRD risk under
each drug. For every test patient we then read off *both* predictions — the risk under the drug they
actually received (factual) and the risk under the drug they did not (the imputed counterfactual) —
and take the difference as that patient's individual treatment effect. Averaging those differences
over all test patients gives the average treatment effect (the ATE in the table above). The
two-models-and-take-the-difference picture is not a simplification — it is literally the design.

The **counterfactual pipeline** (design locked 2026-08-13 from
`paper2-counterfactual/counterfactual_project_notes_2026-08-13.pdf`) implements it directly as a T-learner. For a
pair like SNRI vs SSRI, one outcome model is trained on the training patients who actually started an
SNRI and a second on those who started an SSRI; each model is then run across the whole eligible test
set. It consumes the interpretable feature vectors only — no narratives, no embeddings, no LLM
similarity. The causal forest already built is the *triangulating* estimator on the same estimand,
not the primary one.

The distinction that matters most is between the two predictions each test patient receives:

- **Gradeable (factual).** The prediction for the drug the patient actually received. Their real TRD
  outcome exists, so this prediction can be scored — AUC, Brier, calibration. This is the only
  performance evidence the project will ever have.
- **Ungradeable (counterfactual).** The prediction for the drug they did *not* receive. No ground
  truth exists and none ever will, so nothing about it can be measured directly.

The whole difficulty of the paper lives in that asymmetry: the quantity we care about — the
difference between the two — is half-built from something that can never be checked. Its credibility
comes only from the gradeable half performing well on its own arm, and from the falsification battery
failing to knock the estimate down.

That number alone proves nothing, so we then try to *break* it with a four-rung falsification battery
(balance, overlap, E-value, negative-control outcome — detailed below). Each rung is an attempt to
show the effect is an artifact of confounding rather than a real drug effect. The logic runs in only
one direction, and that is the whole point:

- **No observational method can prove a causal effect exists** — the assumption it rests on (that we
  measured everything driving both drug choice and outcome) is fundamentally untestable.
- The battery can only ever **cast doubt**. If a rung fires, the effect is probably confounding in
  disguise. If *no* rung fires, the effect has **survived every attempt to debunk it** — credible and
  consistent with a real effect, but still not proven.
- Because our ATEs are already ~null, the battery mostly asks a slightly different question: is the
  null trustworthy, and is the design sound enough that a real effect would not have been missed?

So the honest bottom line is: we can never prove an effect is there; the best we can do is fail to
knock it down. A clean pass means "not debunked," not "confirmed" — and an honest null that survives
the same scrutiny is itself a legitimate result.

### The reframe

The paper's contribution became **methodological and adversarial** rather than "we found the optimal
drug." We estimate a recommender's value with proper off-policy evaluation, triangulate its causal
claims across three identification strategies, and subject every claim to a pre-specified
falsification battery. Three landing outcomes are all designed to be publishable *before* seeing the
numbers:

1. **Positive-and-survives** — a rule with real value that holds up under the strongest test.
2. **Signal-but-fragile** — apparent value that collapses under scrutiny (a methods-cautionary
   result, arguably more valuable).
3. **Honest null** — no robust differential benefit; recommendation is no better than
   baseline-severity triage.

### Where it sits relative to the field

The closest prior work is Bilu et al. (2026, *BMC Psychiatry*). They learned a policy choosing among
three SSRIs and found it barely beat routine prescribing on expected PHQ-9 symptom reduction — the
three SSRIs are near-interchangeable for most patients, and outcome is dominated by baseline severity.
On a larger cohort (73,601) with a real symptom-scale outcome, personalized selection still bought
almost nothing over standard care — the direct empirical reason we do not stake this paper on a large
positive effect.

### Status of Project 2

- Design and identification strategy: **documented** (`PAPER2_OUTLINE.md`, `CAUSAL_IDENTIFICATION.md`).
- Counterfactual pipeline: **design locked 2026-08-13; build started 2026-08-18; runnable end to end
  and run on all three contrasts as of 2026-08-28**, with the falsification battery still the one
  thing standing between it and a reportable number. **As of 2026-09-01** the battery's second rung
  is most of the way there: population accounting (per-arm counts, shares and TRD rates on *both*
  sides of the split, with retained-as-well-as-trimmed counts and the arm ratio either side of the
  overlap band), the arm-coloured positivity figure, and the persisted frame the balance tables are
  computed from have all landed. What is left is the SMD tables, the formal metrics judging the
  propensity model itself, the E-value, and the negative control. The scope is the
  index anchor — treatment is the antidepressant class started at the anchor prescription, the
  outcome is the existing TRD label, and eligibility per contrast is every cohort patient whose index
  class is one of the two compared arms. Architecture spec lives in the `TRD-EHR` README under
  Planned Extensions; the design source is `counterfactual_project_notes_2026-08-13.pdf`.
  Landed so far: the two pieces the causal package and this one must not fork — the patient→index-class
  map (`get_AD_mappings`) and the contrast list (`TREATMENT_REGISTRY`) — now both live in
  `scripts/shared/` and are read by both packages; and in the new `scripts/pipeline/counterfactual/`
  package, three working halves, each verified against the live cohort on all three contrasts:
  eligibility construction (one contrast spec into the four populations the T-learner needs), the
  **two-arm T-learner fit and counterfactual scoring** (per-arm logistic regression reusing Paper 1's
  preprocessing, each model scored over *every* eligible test patient, yielding a per-patient risk
  table where exactly one of the two risks is factual), and the **gradeable-metrics half** (each arm
  model scored against the arm it actually treated, with its row and event counts attached).
  Reference-arm discrimination lands right where Paper 1's feature-vector logistic regression does,
  which is the reassurance the substrate is behaving.
  One methodological wrinkle was resolved along the way: the shared metrics helper fits its
  calibration line over *unweighted* bin means, which on the smaller arms describes the bin grid
  rather than the model. Rather than re-bin Paper 1's published measurement surface, this package
  emits its own per-arm calibration bin table and a count-weighted slope beside the shared one. That
  correction relocated the problem — the arm that first looked badly calibrated is fine, and a
  different one is genuinely overdispersed.

  Landed since: the **overlap/positivity screen** (a propensity model for arm assignment, fit on
  train and scored on test, with a trim band and a per-arm trim report rather than a silent
  truncation); the **effect estimates** themselves, reported as two averages over the same
  replicate — a hard-trimmed one restricted to the in-band patients and an overlap-weighted one over
  everybody — so that disagreement between them isolates the averaging rule; a **whole-pipeline
  bootstrap** that refits all three models inside every draw, under two nested schemes (training
  rows only, versus training and test rows) reported side by side rather than chosen between; the
  **array runner and its sbatch**; and three families of figure whose observations are deliberately
  different objects — one per patient, one per patient-per-draw, and one per draw's average. Only
  the last of these has the reported confidence interval as its shaded span, which is why it exists:
  the pooled per-patient figure is wider than the interval by roughly the square root of the sample
  size and had been the only visual available. The per-draw averages are persisted alongside the
  figures, so any later re-cut of an interval is a file read rather than a rerun.

  Queued next, from the 2026-08-28 meeting, and specified in the `TRD-EHR` README rather than built:
  a **population report** covering the training side as well as the test side, because the arm counts
  currently in the artifacts are all test-side and the training population — the input half of all
  three models — is recorded nowhere; a **propensity histogram coloured by arm**, with the trim band
  drawn on it, since the overlap screen presently reports two counts where it should show a
  distribution; and **5-fold cross-validation over the whole pipeline**, so that the effect is
  estimated over the entire eligible population instead of the fifth of the cohort that happens to
  sit in the frozen test split. The last two each carry an open decision recorded with them — whether
  a symmetric trim band survives contact with heavily imbalanced arms, and whether cross-validation
  replaces the shared split here or sits beside it as a robustness layer.

  Two findings from that work are methodological rather than clinical and belong here. First, the
  original interval omitted model-estimation uncertainty entirely — it resampled a frozen vector of
  predicted contrasts while the models stayed fitted once — and that term turns out to dominate;
  the corrected intervals are several times wider, and one contrast no longer excludes zero. Second,
  comparing the two bootstrap schemes shows test-set sampling variability contributes almost nothing
  next to model-estimation uncertainty, which means precision here is limited by how well the arm
  models are known and not by how many patients are averaged over. Both belong in Limitations.
  (Numbers live in the manuscript and supplement, not here.)
  Next: the propensity column, which feeds both the hard overlap trim (the headline estimand) and an
  overlap-weighted sensitivity average, then the effect with its bootstrap CI, then the rest of the
  falsification battery. The negative-control outcome is the largest unstarted piece — no such label
  exists in the codebase yet, so it is a data-loading job rather than a check to write.
- Causal sweep: **re-derived cleanly** on the new cohort; the validation suite passes (sign-flip
  antisymmetry near-perfect, transitivity gap ~0.014) — the machinery is correct, the identification
  is what's empty. It is now the triangulating estimator, not the headline one.
- Reference library: **assembled** (see below).
- Ongoing: econometrics tutoring to shore up the methods.
- **Deferred, not cancelled:** the prescriber-preference instrument and its relevance gate, the
  switch-event library, PHQ-9-free outcome proxies, and the off-policy-evaluation module. These
  belong to the switch-decision framing (Trial 3), which is a later scope than the index-anchor
  pipeline now being built. The IV arm remains the only strategy that addresses *unmeasured*
  confounding, so it stays on the roadmap.

### Supporting work — the reference library

The citation set for Paper 2 was gathered into `paper2-counterfactual/references/` (a role-grouped
manifest): **21 of 22 papers plus the source textbook** are on disk. Three arrived by author reprint:
Szmulewicz et al. (2023, the STAR*D target-trial emulation) on 2026-07-26 — article plus
supplementary appendix — Chekroud et al. (2016, cross-trial ML prediction, *Lancet Psychiatry*) on
2026-07-27, and **Davies et al. (2013) on 2026-08-05**, emailed by the author after the Bristol
address worked where the UCL one had bounced. That leaves only Komorowski et al. (2018), for which
the supplements alone are held; the request drafts live in
`paper2-counterfactual/references/reprint_request_emails.md`.

Davies (2013) anchors the prescriber-preference-instrument strategy and has now been read and
verified against the plan (see the notes at the end of the Paper 2 reference README). It supports
the pivot on instrument strength and on exchangeability, and it supplies a useful design detail —
build the instrument from a window of the prescriber's recent prescriptions rather than the single
last one. **The one caveat to carry forward:** its validity conclusion is scoped to the *short-term*
effects of antidepressants, whereas Paper 2's outcome runs over a year, so the exclusion restriction
at that horizon is a stronger assumption than Davies establishes. The recorded DOI in the library was
also wrong and has been corrected to 10.1016/j.jclinepi.2013.06.008.

---

## Current state at a glance

| | Paper 1 — TRD prediction | Paper 2 — Counterfactual selection |
| --- | --- | --- |
| **Core question** | Will this patient become TRD? | Which antidepressant class? |
| **Pipeline** | Complete; analysis complete (2026-08-07) | Causal sweep re-derived; counterfactual T-learner runnable end to end and run on all three contrasts (eligibility, two-arm fit/scoring, gradeable metrics, overlap screen, both effect estimands, whole-pipeline bootstrap under two schemes, array runner, three figure families) — falsification battery is the remaining blocker; no cross-contrast leaderboard reduce; OPE/IV modules not built |
| **Headline result** | ROC ≈ 0.66 (Qwen-8B primary; all 4 encoders in). Embedded vs feature is a statistical tie on a paired test (+0.008, CI −0.003 to +0.019), but the embedding significantly helps a linear model and significantly hurts every tree ensemble | Null causal signal → reframed as method + falsification |
| **Manuscript** | In senior-author revision; Paulus' tracked-changes round applied and packet rebuilt (2026-08-20, again 2026-08-21 and 2026-08-22). Figures renumbered (old 2–11 → 3–12) to seat a new Figure 2, now a two-panel forest plot whose paired-difference panel changed the representation claim from "marginally edged" to a stated null; Figure 12 then cut with the fusion analysis, leaving 11 figures, and every panel redrawn wide-and-short at full width so the pages no longer break with blank half-pages. Sixth ablation written into Methods, Results, Table 7, Figure 10, Discussion, Limitations item 5 and TRIPOD 6c (2026-08-22), and rebuilt into the packet the same day. Second review round (2026-08-28, nine items) analytically closed: the index event was misdescribed as "the first adequate antidepressant exposure" and is corrected to the first antidepressant prescription after a documented depression diagnosis, with the full algorithmic definition now in Methods; the target is renamed a treatment-switch–defined proxy in the title and throughout; "statistically equivalent", the fairness claim, and all risk-stratification language are withdrawn; the test-set-selected operating point, the case-enriched calibration, the MNAR argument, the judge rubric's absent fields, and the representation field mismatch are all now disclosed. Its analyses are all closed and both of the late ones are nulls held in reserve outside the packet: matched-input parity on 2026-08-30, and the religion retention-versus-removal sensitivity — the last analysis on this paper — on 2026-09-03, which moved one sentence of Supplement M6 and nothing else. The packet is four documents — the response memo was retired the same day — and rebuilds clean at 23 figures. What remains is judgement, itemized in `planning/TRD-EHR_TODO.txt` | Design documented; not drafted |
| **Immediate next step** | Send the packet back to Paulus. Nothing analytical or mechanical is outstanding: all three review rounds are closed, the last analysis (religion retention versus removal) landed 2026-09-03 as a null and went to a reserve document outside the packet exactly as matched-input parity did on 2026-08-30, and all four documents rebuild clean at 23 figures with zero figure warnings and no panel tall enough to be stranded on its own page. No `[CONFIRM]` or `[PENDING]` marker remains anywhere and nothing waits on a coauthor. Six things want judgement rather than work, and they are the list for the covering note: the sampling-frame framing (below); whether the classifier-by-representation interaction from Figure 2B deserves more than the two paragraphs it currently gets; whether the fusion analysis should have stayed in the main text at all (Paulus asked for it to move *into* Results and it has since moved out to the supplement entirely); whether the treatment-exposure result — third on the slate rather than first, explained by the section being empty for 76% of the cohort — deserves the paragraph it now gets in *Principal findings* or belongs in the supplement; whether the sparsity sentence (385 of 4,096 dimensions) should carry a clause now that the parity control arm has shown a re-render selects a dense solution of equal discrimination; and whether Limitations goes back in, which is the only one of the six with a cost rather than a preference attached — his Discussion has no such section so the packet has none, seven of the nine disclosures survive elsewhere but two do not, and TRIPOD item 26 now points at scattered places instead of a heading | **ACTIVE** — the propensity column feeding the overlap trim and the overlap-weighted sensitivity average (then the effect + bootstrap CI, then the rest of the falsification battery). Instrument-relevance feasibility gate remains deferred. |

The sibling projects' columns of this table live in their own journeys:
`~/PSYCH-ASR/JOURNEY.md` and `~/libr-local-llm/JOURNEY.md`.
