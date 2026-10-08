# PAPER 2 — PROJECT OUTLINE

## Counterfactual Antidepressant Selection from EHR: An Identification-First, Similarity-Grounded Recommender With a Falsification Battery

> **SCOPE RECONCILIATION (added 2026-08-13) — READ BEFORE ACTING ON THIS DOCUMENT.**
> This outline is written around the **switch-decision** framing: time zero at a line-2 switch,
> eligibility restricted to patients with an observed line-2 decision, and Phase 1 devoted to
> building a switch-event library. **That is not the pipeline currently being built.**
>
> The pipeline under construction is **index-anchor scoped** (the mentor's Target Trial 1 shape):
> treatment is the antidepressant class started at the *anchor* prescription, eligibility per
> contrast is every cohort patient whose index class is one of the two compared arms, and the
> outcome is the existing TRD label. No post-anchor medication sequence is required, and none of
> the Paper-1 artifacts need to be rebuilt — the sliced patient JSONs being strictly pre-anchor is
> a *guarantee* here (no covariate can be measured after time zero), not an obstacle.
> The authoritative design source is `counterfactual_project_notes_2026-08-13.pdf` in this directory; the
> implementation spec lives in the `TRD-EHR` README under Planned Extensions.
>
> Everything in this outline that depends on the switch framing — the switch-event library, the
> line-2 outcome proxies, Trial 3, Phase 1 as written, and the G3 sample-size gate — is **deferred,
> not cancelled**. It is a later scope. Everything that is framing-independent still applies in
> full: the falsification battery, the three landing outcomes, the Bilu comparison, the
> identification diagnosis, and the prescriber-preference instrument as the eventual answer to
> *unmeasured* confounding.

**Status:** design document, not a task tracker. Written 2026-07-22.
**Companion documents (read alongside):** `writeup/CAUSAL_IDENTIFICATION.md` (the econometric
constraints, authoritative), `writeup/NextSteps.pdf` (mentor's Part C/D spec),
`CRF_AnalysesConsiderations_07.08.2026.docx` (mentor's target-trial framing),
`writeup/manuscript.md` (Paper 1, the shared substrate).

---

## 0. The one-paragraph thesis

We already have a patient-representation substrate (deterministic narratives → neural
embeddings → LLM-judged clinical similarity → interpretable feature vectors) validated in
Paper 1 for TRD *prediction*. Paper 2 turns that substrate on the harder question the
mentor's spec calls Part C: **given a patient about to start (or switch) an antidepressant,
what is the expected outcome under each feasible class, and does a recommendation rule built
on those estimates carry defensible value over standard prescribing?** The intellectually
honest version of this project is **not** "we found the optimal drug per patient" — the causal
forest arm already shows that signal is faint on this data, and a near-identical study (Bilu et
al. 2026) found only a small improvement. The contribution is instead **methodological and
adversarial**: a recommender whose value is estimated with proper off-policy evaluation,
whose causal claims are triangulated across three identification strategies (selection-on-
observables, prescriber/clinic-preference instrument, and target-trial ATT), and whose result
— positive **or** null — survives a pre-specified falsification battery. On this data a
rigorously-bounded, well-falsified null is a publishable finding; an un-falsified positive is not.

---

## 1. Why the naive project fails (grounded, not hypothetical)

The obvious framing — "learn a heterogeneous-treatment-effect model, read off the best drug
per patient, claim clinical utility" — is a bad bet here, for three reasons we can already
document from our own artifacts and the literature:

**(a) Our own causal signal is empirically flat.** The current three-contrast causal-forest
sweep (`results/causal_pipeline/leaderboard.csv`) returns:

| Contrast | ATE (95% CI) | CATE calibration R² | BLP p (BH) | Read |
|---|---|---|---|---|
| SNRI vs SSRI | 0.037 (−0.086, 0.161) | 0.046 | 0.019 | thin "hit" |
| Bupropion vs SSRI | 0.040 (−0.092, 0.172) | −0.099 | 0.75 | null |
| Bupropion vs SNRI | 0.017 (−0.084, 0.119) | 0.010 | 0.75 | null |

Every average effect is statistically indistinguishable from zero. The heterogeneity
calibration R² are essentially zero. The single surviving BLP signal is — per our own
`CAUSAL_IDENTIFICATION.md` §3(c) — dominated by illness-burden proxies (encounter count, age),
i.e. confounding by indication wearing a heterogeneity costume. The machinery is correct (the
validation suite shows near-perfect sign-flip antisymmetry and a small transitivity gap); the
*identification* is empty.

**(b) The binding constraint is the CIA, not the estimator.** No amount of forest flexibility
repairs an unmet conditional-independence assumption. Severity is only partially observed,
so the selection-bias term does not zero out. This is structural and will survive any
re-derivation.

**(c) The near-identical study already exists and also came up weak.** Bilu et al. (2026, *BMC
Psychiatry*, n = 73,601 NHS EHR) learned a data-driven policy over three SSRIs with RF + EconML
and an explicit counterfactual policy-value comparison — and found only a *small* improvement
over standard practice, with policy AUC (0.65) barely above what baseline PHQ-9 alone gives
(0.61). If the closest prior work with a *better* outcome (real PHQ-9 change) and a *larger*
cohort found a small effect, we should not stake a paper on a large one.

**Conclusion:** the deliverable must be reframed so that the scientific value does not depend on
a large positive effect existing. That reframe is Section 4.

---

## 2. Prior-work landscape (verified) and where we sit

Two literature scans were run for this outline. The verified map:

**Closest competitors (must position explicitly against these):**

- **Bilu et al. 2026, *BMC Psychiatry*** — EHR policy learning over 3 SSRIs, PHQ-9 outcome,
  counterfactual policy value. *Small* improvement; baseline severity dominates. This is the
  study we most resemble and must differentiate from.
- **Sheu, Perlis et al. 2023, *npj Digital Medicine*** (n = 17,556, Mass General Brigham) —
  per-class **response prediction** (SSRI/SNRI/bupropion/mirtazapine), outcome proxy derived
  from clinical-note language (hand-labeled 3,600 + imputed), best AUROC ≈ 0.74. Closest
  EHR predictive work. Note: this is *prediction with treatment-selection features*, not causal
  identification.
- **Puac-Polanco, Kessler et al. 2024, *Molecular Psychiatry*** — VHA EHR individualized
  treatment rule, n = 43,470 (essentially our cohort size), medication vs psychotherapy vs
  combined. Effect size unverified (paywalled) — read before citing a number.
- **Wu et al. 2021, *J. Personalized Medicine*** — Taiwan claims, n ≈ 715k, Super Learner ITR
  validated by target-trial emulation; ~16–18% treatment-failure reduction. Claims-derived
  failure proxy — same proxy-outcome situation we face.

**Method backbone (cite as the machinery):**

- Off-policy evaluation / policy learning: **Athey & Wager 2021** (policy learning from
  observational data, doubly-robust scores), **Dudík, Langford & Li 2011** (doubly-robust OPE),
  **Swaminathan & Joachims 2015** (self-normalized IPS / SNIPS).
- The healthcare-RL cautionary canon: **Komorowski et al. 2018** (AI Clinician) and its
  critiques **Gottesman et al. 2019** (Nature Medicine guidelines) and **Jeter et al. 2019**
  (reward/proxy design drives wrong policies; report effective sample size).
- Comparative-effectiveness framing: **Hernán & Robins 2016** (target trial emulation);
  psychiatry applications exist (Szmulewicz/Perlis 2023 STAR*D emulation) but are class ATEs,
  not learned individualized policies with OPE.
- Identification escape hatch: **Brookhart et al. 2006** and **Davies et al. 2013**
  (physician prescribing-preference instrument, the latter *specifically validated for
  antidepressants*), with the assumption-reporting caveats (Widding-Havneraas et al. 2021).
- Sensitivity tooling reviewers now require: **VanderWeele & Ding 2017** (E-value),
  **Lipsitch et al. 2010** (negative-control outcomes), Rosenbaum bounds if matched.

**Proxy-outcome lineage (cover for having no PHQ-9):**

- **Hughes, Pradier, Perlis, Doshi-Velez 2020, *JAMA Netw Open*** — antidepressant *treatment
  stability* (no switch/augment/discontinue) as a PHQ-9-free EHR outcome. This legitimizes our
  switching/stability/discontinuation proxies.

**The generalization critique (our strongest motivating hook):**

- **Chekroud et al. 2016** (Lancet Psychiatry, STAR\*D, ≈65% remission accuracy) and the
  field-level self-critique **Chekroud et al. 2021** (World Psychiatry) plus replication
  **Nunez et al. 2021** — ML antidepressant-response models routinely fail to transport across
  trials/outcomes. The bar is recommendation *utility*, not in-sample AUC.

**LLM recommenders (an un-validated gap we can claim):**

- **Perlis 2023/2024** — GPT-4 selecting next-step antidepressants from *vignettes*: optimal
  pick 76% of runs but a contraindicated pick in ~48%; bipolar version 50.8% agreement. All
  vignette-based, none validated against real EHR outcomes.

**The apparent open gap:** no published work uses an **LLM-embedding patient-similarity ("digital
twin") representation to recommend the next antidepressant validated against real EHR
outcomes.** Treat as "not found," not "proven absent" — but it is a real differentiator.

---

## 3. Our differentiators (the novelty, stated defensively)

Novelty here is a *combination and rigor* claim, not a "first-ever" claim. Against the map above
we own four distinct axes, and the paper should assert exactly these and no more:

1. **Representation.** LLM-judged clinical-similarity twins (Paper 1's substrate) as the
   counterfactual-outcome estimator, rather than a random forest on tabular features (Bilu) or a
   note-language classifier (Sheu). No prior antidepressant recommender uses an outcome-validated
   LLM-similarity twin.
2. **Class breadth with honest overlap.** SSRI / SNRI / bupropion active-comparator contrasts,
   not three near-identical SSRIs (Bilu). Broader clinical question, at the cost of harder
   overlap — which we *report*, not hide.
3. **Triangulated identification.** Three identification strategies on the same estimand
   (selection-on-observables DML, a **prescriber/clinic-preference instrument → LATE**, and a
   target-trial ATT), with agreement/disagreement across them as the actual evidence. The
   preference instrument is feasible on this data (Section 8) and no psychiatric-policy EHR paper
   we found triangulates this way.
4. **Falsification-first evaluation.** A pre-specified battery — negative-control outcomes,
   E-values, effective-sample-size gating, out-of-fold OPE with SNIPS/DR — where the headline is
   whether the recommendation *survives*, not its point estimate. This is the Gottesman-guideline
   temperament operationalized.

---

## 4. What the paper actually claims (the reframe)

The manuscript's contribution is a **method + a credibility verdict**, structured so a null is
still a paper:

> *We build a counterfactual antidepressant recommender on an EHR-derived digital-twin
> representation, estimate its policy value with off-policy evaluation, and subject its causal
> claims to a three-way identification triangulation and a pre-specified falsification battery.
> We report the honest answer this data supports.*

Three possible landing outcomes, all publishable:

- **Positive-and-survives:** a class-selection rule with policy value above standard prescribing
  that holds under the instrument and passes negative controls. Strong paper.
- **Signal-but-fragile:** apparent value under selection-on-observables that collapses under the
  instrument or fails a negative control. This is a *methods cautionary* paper — arguably more
  valuable, and directly extends the Gottesman/Jeter line into psychiatry.
- **Honest null:** no class carries robust differential benefit on this proxy; recommendation
  value is indistinguishable from baseline-severity triage. Reportable per Chekroud 2021 and
  Bilu 2026, with our added rigor as the contribution.

The design must make all three equally reportable **before** we see the numbers. That is what
separates this from an exercise in p-hunting the one SNRI-vs-SSRI BLP.

---

## 5. Aims

- **Aim 1 — Counterfactual outcome estimation.** For each patient and each feasible
  antidepressant class, estimate expected response and expected adverse-discontinuation using the
  similarity-twin estimator and, in parallel, a doubly-robust DML estimator. Report effective
  sample size per estimate; refuse to estimate where ESS is too low.
- **Aim 2 — Policy value under off-policy evaluation.** Define an explicit utility, derive the
  recommendation rule, and estimate the value of *following the rule* vs the observed prescribing
  policy using self-normalized IPS and a doubly-robust estimator, out-of-fold, with bootstrap CIs.
- **Aim 3 — Identification triangulation.** Re-estimate the key class contrasts under
  (i) selection-on-observables DML, (ii) a prescriber/clinic-preference instrument yielding a
  LATE among preference-sensitive patients, and (iii) a target-trial ATT on the trimmed
  common-support sample. Agreement across strategies is the causal evidence.
- **Aim 4 — Falsification and sensitivity.** Apply the pre-specified four-rung ATE robustness
  ladder (§8(iv)) to every headline contrast — balance/SMD, overlap/positivity, E-value on the
  point estimate and the CI limit nearest null, and a negative-control outcome — plus
  proxy-outcome sensitivity (response defined two ways). A claim survives only if the battery does
  not break it; a claim the battery *does* break is a reportable null under §4.

---

## 6. Assets in hand vs. what must be built

**Already built and reusable (the shared substrate):**

- Cohort construction, index-date/new-user logic, time-anchoring, follow-up gating
  (`create_cohort`, `fit_to_anchor`, `load_patient_data`) — 42,579-patient MDD−(BD∪SCH) cohort.
- Deterministic narratives + four neural embeddings + LLM clinical-similarity judge with a
  durable cache (`embeddings.db`, `judgements.db`) — the twin retrieval/scoring engine.
- Interpretable feature vectors (`feature_vectors.parquet`) with treatment-class exposure and
  medication-burden fields, timing-audited to be measured at or before index.
- Causal DML infrastructure (EconML `CausalForestDML` + `DRTester`, overlap gating, BLP/ATE/CATE
  outputs, sign-flip/transitivity validation) — reusable for Aim 3(i) and as the DR nuisance
  machinery for Aims 1–2.
- The TRD label and the shared train/test split.

**Must be built (net-new work, roughly in dependency order):**

1. **Treatment-line segmentation + switch-event library** (mentor spec Part C2): segment each
   patient's antidepressant history into lines with line-start dates, class, adequacy, and
   adherence proxy; emit one row per observed line-2 decision with the chosen next class and the
   post-switch outcomes. This is the counterfactual analogue of the Paper-1 twin library.
2. **PHQ-9-free outcome definitions** (mentor spec A3(ii); lineage Hughes 2020): acute-response
   proxy, adverse-discontinuation proxy, and time-to-next-switch, each defined from coded EHR
   only, each with a documented rationale and a sensitivity variant.
3. **Feasible-candidate gating** (spec C3 step 2): per-patient candidate class set after
   safety/contraindication and already-failed-adequately filters, so we never score an
   implausible counterfactual.
4. **Propensity / behavior-policy model** over classes, on the pre-index feature block, for both
   the DR estimator and the OPE denominators. Never uses post-decision data.
5. **Off-policy evaluation module**: self-normalized IPS and doubly-robust policy value, with
   out-of-fold scoring and bootstrap CIs, plus the ESS diagnostic that gates every estimate.
6. **Prescriber/clinic-preference instrument construction** (Aim 3(ii)) — see Section 8; this is
   the feasibility-gated centerpiece.
7. **Falsification battery** (Aim 4): negative-control outcome pipeline, E-value computation,
   overlap-trimming and proxy sensitivity re-runs.

---

## 7. Design: target trial, treatments, outcomes

Adopt **target-trial emulation** (Hernán & Robins) as the framing spine for every contrast — it
is what reviewers in comparative effectiveness now expect and it structurally forecloses
immortal-time bias.

**Two target trials (the mentor's Trial 1 and Trial 3):**

- **Trial 1 — initial class selection at index.** Eligible: new-user MDD episode, no active
  antidepressant in the washout. Arms: SSRI / SNRI / bupropion (active-comparator pairwise,
  matching the current causal build and its comfortable minority-arm N). Time zero: first
  qualifying dispense. This trial's *prediction* side is Paper 1; its *policy* side is Paper 2.
- **Trial 3 — next-class selection after line-1 non-response/intolerance.** This is the mentor's
  primary Part C scenario and the true novelty locus: eligible patients reach a switch decision
  point; arms are the feasible next classes; time zero is the switch. Requires the switch-event
  library (Section 6, item 1).

Deliberately **defer** Trial 2 (adequate-trial/persistence) to a landmark sensitivity analysis —
it carries immortal-time risk the mentor's doc flags, and it is not the headline.

**Outcomes (no PHQ-9; all coded-EHR proxies, each with a sensitivity variant):**

- **Response proxy** — treatment stability through the acute window (no switch/augment/
  discontinue-for-inefficacy), per Hughes 2020. Sensitivity variant: switch-or-augment within
  the window as the failure event.
- **Adverse-discontinuation proxy** — stop/switch within ~28 days plus an intolerance signal.
- **Time-to-next-switch** as a secondary continuous-ish outcome.
- The manuscript must **report performance separately** for any subgroup where a symptom scale is
  available vs not, and must state the proxy's known misclassification directions (Jeter's
  warning: the proxy *is* the reward; defend it explicitly).

**Covariates / effect modifiers (not treatments):** medication burden (polypharmacy, benzo,
hypnotics, NSAID), prior-AD exposure, utilization, comorbidities — exactly the mentor's CRF-doc
classification. Timing already audited (`CAUSAL_IDENTIFICATION.md` §2): every covariate is
measured at or before the decision point.

---

## 8. The identification triangulation (the scientific core)

Three routes to the same class-contrast estimand. The evidence is their **agreement**, not any
single point estimate.

**(i) Selection-on-observables (DML).** Reuse the existing `CausalForestDML` + `DRTester` build.
This is the weakest identification (assumes the CIA we know is violated) but the most flexible;
it sets the ceiling on measured-covariate adjustment and supplies the DR nuisance functions used
elsewhere. Expectation, from current results: near-null with faint heterogeneity.

**(ii) Prescriber/clinic-preference instrument → LATE (the headline pivot).** **Feasibility
confirmed at the schema level:** the Encounter table carries `ProviderName`, `DepartmentName`,
and `DepartmentKey`, and the Medication table carries `EncounterId_SH` — so a medication order
can be joined to its ordering encounter's provider and clinic. This makes a Brookhart-style
prescribing-preference instrument constructible (Davies et al. 2013 validated exactly this — for
SHORT-TERM effects; see the horizon caveat in the Paper 2 reference README — for
antidepressants). The instrument candidates, in order of defensibility:

- **Clinic/department baseline class-rate** (department-level lean). Usually the *most* defensible
  on independence grounds — patients are less selectively sorted to a whole clinic's baseline
  prescribing tendency than to an individual physician — and sidesteps sparse per-provider cells.
- **Provider's previous-patient class** (the classic Brookhart "last prescription" instrument).

Four assumptions must each be argued and, where possible, tested, and the manuscript must state
them explicitly (Widding-Havneraas 2021 — reviewers penalize unstated preference-IV assumptions):

- **Relevance / first stage** — the provider/clinic lean must strongly shift *this* patient's
  class. *Test empirically and report the first-stage strength; a weak instrument is worse than
  none.* This is the make-or-break gate (Section 9).
- **Independence** — which provider/clinic a patient lands on is as-good-as-random w.r.t.
  unmeasured severity, conditional on covariates. *Threat to log: triage-by-severity (sickest
  routed to specialists). Condition on clinic/covariates and argue residual randomness.*
- **Exclusion** — provider preference affects the outcome only through the class chosen.
- **Monotonicity** — a provider's lean never makes a patient *less* likely to get that class.

Payoff: a clean **LATE among preference-sensitive patients** where we currently have a confounded
ATE. Mandatory caveats to state: LATE is local to compliers and silent on always/never-takers, so
LATE ≠ ATE ≠ population policy value. If a prescriber-level (not clinic-level) design is used,
cluster standard errors by provider (Moulton).

**(iii) Target-trial ATT on trimmed common support.** Change the estimand to the effect on the
treated in the minority arm (bupropion / SNRI initiators, N ≥ 4,768) with aggressive overlap
trimming and a reported covariate-balance table. This is better-powered and more policy-relevant
("who actually got switched") than a population CATE surface, per `CAUSAL_IDENTIFICATION.md` §5D.

**(iv) The ATE robustness ladder (how each contrast's average effect is defended).** Whichever
route above produces a contrast, its ATE is defended by a fixed, pre-specified four-rung ladder,
reported for every headline contrast. The rungs escalate: 1–2 clean the *measured* world, 3
*bounds* the unmeasured, 4 tries to *catch* it in the act.

| # | Rung | What it attacks | Instrument / verdict |
|---|---|---|---|
| 1 | **Balance (SMD)** | measured imbalance between arms | standardized mean difference = (mean_A − mean_B) / pooled SD, per covariate, computed **three ways** — raw over every eligible patient, hard-trimmed over the in-band population, and overlap-weighted — reporting raw and hard-trimmed as the table with overlap-weighted as a sensitivity column, since a balance table with no "before" column cannot show that adjustment did anything; target \|SMD\| < 0.1 (0.1–0.2 mild, > 0.2 material) |
| 2 | **Overlap / positivity** | non-comparability, model extrapolation | propensity e(X) = P(comparison arm \| X), fit on train and evaluated on test; trim outside the 0.10/0.90 band; estimand becomes the overlap population, stated as such; trimmed **and retained** count and share reported **per arm**, never pooled or silent, with the reference-to-comparison arm ratio given either side of the band; e(X) drawn per arm with the band edges marked; and the propensity model itself judged formally — calibration (slope, intercept, reliability table, Brier), its arm-discrimination c-statistic *where high is bad*, the overlap coefficient between the two arm-conditional densities, and the Kish ESS under the overlap weights. Reported **twice**: the hard-trimmed average as headline, plus an overlap-weighted average, e(X)·(1 − e(X)), as sensitivity (see the note below the table) |
| 3 | **E-value** | unmeasured confounding (bound) | E = RR + √(RR·(RR−1)) on the effect expressed as a risk ratio; report on **both** the point estimate and the CI limit nearest null; benchmark against the strongest measured covariate's two arrows (RR-with-treatment, RR-with-outcome), which must *both* clear E to be a threat |
| 4 | **Negative-control outcome** | unmeasured confounding (detect) | rerun the whole pipeline on an outcome the class cannot plausibly cause (NSAID use, fracture/injury); true effect is known-zero, so any detected effect is confounding leaking through the backdoor treatment ← U → outcome — a direct falsification of the CIA, not a bound |

**Note on rung 2 — hard trim vs. overlap weights (decided 2026-08-19).** The 0.10/0.90 trim is a step
function: full weight inside the band, none outside. Its virtue is an estimand nameable in one
sentence, and a band shared with the causal-forest package, which keeps the two triangulating
estimators comparable. Its vice is the cliff — a patient at e(X) = 0.101 counts fully and one at
0.099 not at all. So the same per-patient contrasts are additionally averaged under **overlap
weights**, e(X)·(1 − e(X)) (Li, Morgan & Zaslavsky 2018, JASA, *Balancing covariates via propensity
score weighting*): weight peaks where both treatments are equally plausible and tapers smoothly to
zero at either extreme. Its estimand is a weighted pseudo-population and therefore harder to
describe to a clinician, which is why it is the sensitivity rather than the headline. Agreement
between the two is the evidence that the effect does not depend on where the cutoff was drawn.

Both are computed from one propensity column, so the second costs a weighted mean. Note also what
neither buys: reporting each patient's e(X) alongside an unsupported counterfactual does *not*
license averaging that counterfactual in. A caveat attached to a row does not repair a mean that has
already absorbed a fabricated number, and the error in an extrapolated counterfactual is unbounded.
The rule is therefore: report every patient's risks and propensity, average over a defensible subset.

A contrast's ATE is called credible only if it survives all four; an ATE caught confounded by
rung 4 (or shown fragile by a rung-3 E-value below the strongest measured confounder) is itself a
reportable finding under the §4 reframe, not a failure. This ladder is the concrete content of
Aim 4 and supplies the covariate-balance table that route (iii) also requires.

---

## 9. Feasibility gates and risk register

The project has hard go/no-go gates. Each must be checked *before* the dependent work, and the
outcome logged. This is where honesty about feasibility lives.

| # | Gate | Test | If it fails |
|---|---|---|---|
| G1 | **Instrument relevance** | Join med orders → ordering provider/clinic; measure between-provider/clinic prescribing variation and first-stage strength (does clinic lean shift patient class?). | Instrument arm (Aim 3ii) is dead. Fall back to DML + ATT + full sensitivity battery as the ceiling. Paper becomes "honest null with rigor." |
| G2 | **Provider = prescriber validity** | Confirm the encounter `ProviderName` on a med-linked encounter is plausibly the ordering clinician, not an unrelated visit provider. | Use department/clinic-level instrument only (arguably preferable anyway); do not claim a physician-level instrument. |
| G3 | **Switch-event sample size** | Count patients with an observed, adequately-observed line-2 decision per candidate class. | Restrict Trial 3 to the 2–3 best-powered next-class contrasts; report the rest descriptively. |
| G4 | **Overlap / positivity per contrast** | Existing overlap gate (0.10/0.90) on each class pair at the switch decision. | Drop contrasts that fail; report which and why (no silent truncation). |
| G5 | **Effective sample size per OPE estimate** | Compute ESS on every importance-weighted value (the single most common way OPE lies — see the Medicaid "0.0% ESS" cautionary case). | Report "insufficient similar patients" rather than a number. |
| G6 | **Proxy-outcome defensibility** | Sensitivity: response defined two ways; do conclusions flip? | If conclusions are proxy-dependent, that *is* the finding — report it. |

**Standing scientific risks (state in the manuscript's limitations):**

- Confounding by indication persists under DML; only the instrument arm addresses unmeasured
  severity, and only among compliers.
- The proxy outcome is not a symptom scale; it can misclassify response.
- Single-site EHR; care outside the system is missing.
- LLM-similarity twins do not solve confounding — they are a *representation*, and their
  weighting can inherit the same selection structure. The OPE and IV arms, not the twins, carry
  the causal claim.

---

## 10. Evaluation plan (mirrors mentor spec Part C4)

- **Layer 1 — observed-treatment outcome prediction.** On held-out switch events, predict the
  outcome for the drug actually received; report Brier/log-loss, calibration, AUROC. Tests whether
  the twin method predicts outcomes *when the treatment is known*.
- **Layer 2 — policy value (off-policy).** Self-normalized IPS as the minimum viable estimator;
  doubly-robust as the primary. Compare the "follow the rule" value against the observed
  prescribing policy and against reference policies ("always SSRI"). Out-of-fold; bootstrap CIs.
- **Layer 3 — sensitivity.** Vary retrieval K and weighting sharpness; restrict to high-overlap
  cases; separate non-response vs intolerance switches; per-class breakdown; PRO-available vs
  not. If the method "works" only in one narrow configuration, report that.
- **Layer 4 — negative control / leakage.** Confirm predictions do not change when post-decision
  data is removed; evaluate a negative-control outcome antidepressant choice cannot plausibly
  cause. A signal there falsifies the design.

**Ablations that prove the twin adds value** (spec C4 step 6): replace LLM similarity with plain
cosine; drop medication-burden variables; drop anxiety/pain variables — performance drops confirm
meaningful signal (or their absence confirms the twin adds nothing, also reportable).

---

## 11. Phased plan (semester-scale, matching Paper 1's arc)

- **Phase 0 — Feasibility gates (weeks 1–2).** Run G1/G2 (instrument) and G3 (switch counts)
  *first*. Their outcome determines whether the paper is "triangulated causal" or "rigorous null."
  Nothing downstream is worth building before these resolve.
- **Phase 1 — Outcomes + switch library (weeks 2–5).** Treatment-line segmentation, the three
  proxy outcomes with sensitivity variants, the switch-event library, candidate-gating.
- **Phase 2 — Estimation (weeks 5–8).** Propensity/behavior-policy model; DML re-run on switch
  contrasts (Aim 3i); twin-based counterfactual outcome estimates (Aim 1); ESS gating.
- **Phase 3 — Policy + OPE (weeks 8–10).** Utility definition, recommendation rule, SNIPS + DR
  policy value out-of-fold with CIs (Aim 2).
- **Phase 4 — Instrument + ATT (weeks 9–12, overlaps).** If G1/G2 passed: build the
  preference instrument, estimate the LATE, cluster SEs; build the trimmed-support ATT.
- **Phase 5 — Falsification battery (weeks 11–13).** Negative controls, E-values, all sensitivity
  re-runs (Aim 4).
- **Phase 6 — Write-up (weeks 13–16).** Target-trial protocol table, results, the triangulation
  verdict, honest limitations.

Reuse the existing SLURM orchestration pattern (`slurm_jobs/pipeline/causal/`) and the
one-folder-per-contrast output layout; the new modules slot alongside the causal build, not
inside Paper 1's frozen prediction modules.

---

## 12. Publication target

- **Primary:** a methods-forward comparative-effectiveness / clinical-informatics venue that
  rewards rigor over positive results — *npj Digital Medicine* (where Sheu/Perlis landed),
  *JAMA Network Open*, or a comparative-effectiveness methods journal. The Gottesman-guideline
  framing and target-trial protocol make it a fit even with a null headline.
- **Framing sentence for the abstract:** "We show that on EHR data an antidepressant-selection
  policy's apparent value is [survives / collapses] under instrumental-variable identification
  and a pre-specified falsification battery, and we provide the protocol for testing it." Fill
  the bracket with the truth Phase 5 returns.

---

## 13. What "novel, feasible, and grounded" resolves to (blunt summary)

- **Feasible:** yes, but *conditional on G1/G2*. The substrate, cohort, DML machinery, and
  outcome-proxy lineage are all in hand. The schema check confirms a prescriber/clinic identifier
  exists, so the one identification move that could carry a real causal claim is at least
  constructible. The switch-event library and OPE module are the main net-new engineering.
- **Novel:** not as "first EHR antidepressant policy" (Bilu took that), but as the first
  outcome-validated LLM-similarity-twin recommender, with class breadth beyond three SSRIs, a
  prescriber-preference IV triangulation, and a falsification-first evaluation — a defensible
  combination-and-rigor novelty.
- **Grounded:** every design choice above traces to a verified citation (Section 2), the mentor's
  spec, our own econometric constraints doc, or our own (null) results. The honest expected
  outcome is a *fragile-or-null* signal — and the entire design is built so that outcome is the
  paper, not a failure of it.

---

## 14. References (verified; to be formatted at write-up)

1. Athey S, Wager S. Policy learning with observational data. *Econometrica* 2021;89(1):133–161.
2. Dudík M, Langford J, Li L. Doubly robust policy evaluation and learning. *ICML* 2011.
3. Swaminathan A, Joachims T. The self-normalized estimator for counterfactual learning. *NeurIPS* 2015.
4. Komorowski M, et al. The AI Clinician learns optimal treatment strategies for sepsis. *Nat Med* 2018;24:1716–1720.
5. Gottesman O, et al. Guidelines for reinforcement learning in healthcare. *Nat Med* 2019;25:16–18.
6. Jeter R, et al. Does the "AI Clinician" learn optimal treatment strategies for sepsis? *arXiv*:1902.03271, 2019.
7. Hernán MA, Robins JM. Using big data to emulate a target trial. *Am J Epidemiol* 2016;183(8):758–764.
8. Brookhart MA, et al. Evaluating short-term drug effects using physician prescribing preference as an IV. *Epidemiology* 2006;17(3):268–275.
9. Davies NM, Gunnell D, Thomas KH, Metcalfe C, Windmeijer F, Martin RM. Physicians' prescribing preferences were a potential instrument for patients' actual prescriptions of antidepressants. *J Clin Epidemiol* 2013;66(12):1386–1396. doi:10.1016/j.jclinepi.2013.06.008. *(PDF held; verified against the primary text 2026-08-05 — see the Paper 2 reference README. Validity conclusion is scoped to SHORT-TERM antidepressant effects.)*
10. Widding-Havneraas T, et al. Preference-based IV methods rely on underreported assumptions. *J Clin Epidemiol* 2021.
11. VanderWeele TJ, Ding P. Sensitivity analysis in observational research: the E-value. *Ann Intern Med* 2017;167(4):268–274.
12. Lipsitch M, Tchetgen Tchetgen E, Cohen T. Negative controls: a tool for detecting confounding. *Epidemiology* 2010;21(3):383–388.
13. Bilu Y, et al. Data-driven versus standard-practice policies for personalized antidepressant treatment. *BMC Psychiatry* 2026;26:119.
14. Sheu Y-H, Magdamo C, Miller M, Das S, Blacker D, Smoller JW. AI-assisted prediction of differential response to antidepressant classes using EHR. *npj Digit Med* 2023;6:73.
15. Puac-Polanco V, Kessler RC, et al. Developing an individualized treatment rule for Veterans with MDD using EHR. *Mol Psychiatry* 2024;29:2335–2345. *(read PDF before quoting effect size)*
16. Wu C-S, et al. Validation of ML-based individualized treatment for depressive disorder using target trial emulation. *J Pers Med* 2021;11(12):1316.
17. Hughes MC, Pradier MF, Ross AS, McCoy TH, Perlis RH, Doshi-Velez F. Assessment of a prediction model for antidepressant treatment stability using supervised topic models. *JAMA Netw Open* 2020;3(5):e205308.
18. Chekroud AM, et al. Cross-trial prediction of treatment outcome in depression: a machine learning approach. *Lancet Psychiatry* 2016;3(3):243–250.
19. Chekroud AM, et al. The promise of machine learning in predicting treatment outcomes in psychiatry. *World Psychiatry* 2021;20(2):154–170.
20. Nunez J-J, et al. Replication of ML methods to predict treatment outcome with antidepressants (STAR\*D, CAN-BIND-1). *PLoS One* 2021;16(6):e0253023.
21. Perlis RH. Application of GPT-4 to select next-step antidepressant treatment in MDD. *medRxiv* 2023; PMID 37131648.
22. Szmulewicz A, Wanis KN, Perlis RH, et al. Emulating a target trial of dynamic treatment strategies for MDD using STAR\*D. *Biol Psychiatry* 2023.

*Verification flags carried from the literature scan: the Puac-Polanco effect size is unverified
(paywalled); Davies 2013 author list, pages, and DOI are now CONFIRMED from the PDF (the previously
recorded DOI was wrong); confirm Brookhart 2006 page range before final formatting; no LLM-embedding patient-similarity next-antidepressant recommender was found (treat
as an open gap, not a proven absence).*
