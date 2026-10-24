# CAUSAL IDENTIFICATION STRATEGY — TRD Causal-Forest Supplement

A reading of Angrist & Pischke, *Mostly Harmless Econometrics* (MHE), against this
project's causal arm. Written so a future session can act on the conclusions without
re-reading the book — only opening the specific sections named below when the math is
needed. Page numbers are the book's printed page numbers (the PDF is offset by +17:
book p.83 = PDF p.100).

NOTE TO FUTURE EDITORS (INCLUDING CLAUDE): This is a CONCLUSIONS + STRATEGY document,
not a task tracker. It records *why* the causal results are weak and *what the book says
to do about it*. It is stable reference, not a checklist — do not delete sections as
"done." If the science changes (e.g. a prescriber instrument is found and an IV/LATE arm
is built), append a dated revision at the bottom rather than rewriting history. The
companion action list lives in writeup/TODO.txt under "CAUSAL FOREST — Target Trial 1".

This file is designed to be SELF-SUFFICIENT: reading it alone — without consulting the
memory store — is enough to (a) understand the identification problem and strategy, and
(b) RESUME the live tutoring thread. Section 8 carries the tutoring curriculum, teaching
style, and the currently pending exercise; keep its STATE block current after each lesson.
Math is written in Unicode plain text (not LaTeX) because the user reads in a terminal.

================================================================
0. BOTTOM LINE (read this first)
================================================================
The estimator was never the problem; the IDENTIFICATION is. `CausalForestDML` +
`DRTester` is a sophisticated way of enforcing one assumption — the Conditional
Independence Assumption (CIA, a.k.a. selection-on-observables) — that confounding by
indication almost certainly violates. Consequences:
  - The ATE's SIGN is uninterpretable (sickest patients get the aggressive arm AND
    progress to TRD; DML only deconfounds through MEASURED covariates).
  - The CATE heterogeneity signal is faint because it is a second-order signal (effect
    must exist, vary with measured X, AND satisfy the CIA) sitting on a noisy binary
    outcome with a high-variance doubly-robust score.
  - The one apparent "hit" (SSRI-vs-SNRI BLP) is dominated by illness-burden proxies
    (num_encounters, age) — i.e. confounding wearing a heterogeneity costume.

The single highest-value move the book prescribes is CHAPTER 4: find a prescriber /
clinic PREFERENCE INSTRUMENT and estimate a LATE among compliers. Absent an instrument,
everything else (sensitivity bounds, negative controls, balance tables, ATT reframing,
honest nulls) is damage control that makes the observational story defensible but cannot
manufacture a causal signal that is not in the data.

================================================================
1. WHAT THE PIPELINE IS, IN MHE'S LANGUAGE
================================================================
MHE predates causal forests, so "causal forest" is not in the index. Strip the machinery
and every load-bearing assumption is Chapter 3:

  - `model_t` (propensity e(X)) + `model_y` exist to make the CIA hold. The forest is a
    flexible way of "conditioning on X." (§3.2.1, pp.38–44)
  - `passes_overlap` (the 0.10/0.90 band in core.py) is the common-support / POSITIVITY
    requirement. (§3.3.2–3.3.3, pp.59–65)
  - The active-comparator pairwise design (SSRI vs SNRI, never drug-vs-nothing) is the
    book's core instinct: make the two groups as alike as possible so the SELECTION-BIAS
    term (eq. 3.2.1, p.40) is as small as possible. The mentor's CRF doc and MHE say the
    identical thing.
  - `forest.ate()` = E[Y1 − Y0] (eq. 3.2.3); per-patient CATE = the X-conditional version
    (the "embarrassment of riches" of X-specific effects, p.42).
  - The DR pseudo-outcome Γ that `evaluate_blp` plots on the y-axis is the AIPW estimating
    equation (§4 below). The forest's τ̂(X) is the x-axis being validated against it.

Directly relevant sections: §3.2.1 (CIA), §3.2.2 (OVB), §3.3.1–3.3.3 (matching, propensity,
propensity-vs-regression), all of Ch.4 (IV/LATE). NOT relevant: Ch.5 (DiD/panel — no policy
shock, no panel), Ch.6 (RD — no running variable). Ch.8 (clustered SEs) matters only if a
prescriber-level design is adopted.

================================================================
2. FEATURE-TIMING AUDIT — "BAD CONTROL" IS ALREADY AVOIDED
================================================================
Checked scripts/data_loading/features.py. `polypharmacy`, `benzo_days`,
`prior_adequate_trials` (the trials_* counts), `psych_utilization` (in_patient_days,
num_emergency), and `augmentation_flag` all clamp intervals to min(0, end) and require
start <= 0. EVERY covariate is measured at or before the anchor (t=0). Therefore the
classic immortal-time / bad-control trap (MHE §3.2.3, pp.47–51: never condition on a
variable that is itself an OUTCOME of the treatment) is NOT the cause of the weak results.
The trials_* covariates are PRIOR adequate trials (treatment history), not post-index
consequences — legitimate controls. This is a genuine strength of the current build; do
not "fix" it. The problem is upstream of controls: it is the CIA itself.

================================================================
3. WHY THE RESULTS ARE UNDERWHELMING — THREE DIAGNOSES
================================================================
(a) THE BINDING CONSTRAINT IS THE CIA, NOT THE FOREST. MHE p.46: "if you claim an absence
    of omitted variables bias, then you're saying the regression you've got is the one you
    want." You cannot claim that here. Confounding by indication leaves a non-zero
    selection-bias term in eq. 3.2.1 that 63 measured covariates do not zero out, because
    severity is only partially observed. No amount of forest flexibility repairs an unmet
    CIA.

(b) HETEROGENEITY IS SECOND-ORDER AND THE DR SCORE IS NOISY ON A BINARY OUTCOME. Detecting
    CATE variation needs the effect to exist, to vary with MEASURED X, and the CIA to hold,
    all at once. The AIPW score carries a 1/(e(1−e)) inflation factor that explodes near the
    overlap floor; on a 0/1 outcome the linear-probability-model heteroskedasticity point
    (§3.1.3, p.36) compounds it. Near-zero calibration R² and mostly non-significant BLP is
    the EXPECTED outcome of that combination, not a bug.

(c) THE ONE HIT IS CONFOUNDING IN DISGUISE. In the (now-void) stale run the only significant
    BLP was SSRI-vs-SNRI, and the moderator dominating SHAP + subgroup Spearman was
    num_encounters (rho ~ -0.50) and AgeInYears — illness-burden / utilization proxies. The
    OVB formula (§3.2.2) predicts exactly this: the forest reads residual
    confounding-by-indication structure and reports it as effect modification.

CAVEAT: all specific numbers above are from the OLD cohort and are VOID (see TODO "DATA
OVERHAUL"). The STRUCTURAL reasons the signal stays weak will survive re-derivation.

================================================================
4. THE KEY MATH, STATED SO THE BOOK IS OPTIONAL
================================================================
Potential outcomes: for a binary treatment D (here: comparison arm = 1), each patient has
Y1 (outcome if treated) and Y0 (outcome if control); we observe Y = Y0 + (Y1 − Y0)D and
never both potential outcomes.

4.1 SELECTION-BIAS DECOMPOSITION (eq. 3.2.1, p.40). The naive group difference splits as
      E[Y|D=1] − E[Y|D=0]
        = E[Y1 − Y0 | D=1]            (ATT: average effect on the treated)
        + ( E[Y0|D=1] − E[Y0|D=0] )   (SELECTION BIAS: gap in baseline potential outcome).
    Randomization kills the second term. Conditioning on X kills it only IF the CIA holds.

4.2 CIA (eq. 3.2.2 / the general "CIA" line, pp.40–41):  {Y0, Y1} ⫫ D | X.
    Then E[Y|X,D=1] − E[Y|X,D=0] = E[Y1 − Y0 | X] = τ(X), the CATE. "D is as good as randomly
    assigned conditional on X." This is the ONE assumption the whole forest rests on.

4.3 OMITTED-VARIABLES-BIAS FORMULA (eq. 3.2.11, p.45). For a short vs long regression,
      Cov(Y,s)/V(s) = ρ + γ' δ_{As},
    verbally: SHORT = LONG + (effect of omitted) × (regression of omitted on included). This
    is why controlling for illness-burden proxies moves coefficients, and why leftover
    unmeasured severity biases both the ATE and the apparent heterogeneity.

4.4 AIPW / DOUBLY-ROBUST SCORE (the Γ inside DRTester / evaluate_blp). With outcome models
    μ1(X)=E[Y|X,D=1], μ0(X)=E[Y|X,D=0] and propensity e(X)=P(D=1|X):
      Γ_i = ( μ1(X_i) − μ0(X_i) )
            + D_i (Y_i − μ1(X_i)) / e(X_i)
            − (1 − D_i)(Y_i − μ0(X_i)) / (1 − e(X_i)).
    DOUBLE ROBUSTNESS: E[Γ | X] = τ(X) if EITHER the μ's OR e is correctly specified. The
    BLP test regresses Γ on the forest's τ̂(X); slope ~1 and positive means the forest's
    heterogeneity is real. Variance of Γ blows up as e → 0 or 1 — the reason for the overlap
    floor and for the noisy near-zero calibration. NOTE: τ̂(X) is NOT inside Γ; the two-arm
    "clusters" in the BLP scatter are the +1/e (treated) vs −1/(1−e) (control) correction
    bands, i.e. benign AIPW structure, not a bug.

4.5 LATE THEOREM (Theorem 4.4.1, p.114) — the escape hatch. Instrument Z, treatment D,
    potential treatment-take D1 (if Z=1) and D0 (if Z=0). Assume:
      (A1 Independence) {Y(d,z) for all d,z; D1, D0} ⫫ Z.
      (A2 Exclusion)    Y(d,0) = Y(d,1) ≡ Y_d for d=0,1  (Z acts only through D).
      (A3 First stage)  E[D1 − D0] ≠ 0.
      (A4 Monotonicity) D1 ≥ D0 for all i (no "defiers"), or ≤ for all i.
    Then the Wald estimand equals the effect on COMPLIERS:
      ( E[Y|Z=1] − E[Y|Z=0] ) / ( E[D|Z=1] − E[D|Z=0] ) = E[Y1 − Y0 | D1 > D0] = LATE.
    Subpopulations (§4.4.2, p.117): COMPLIERS (D1=1,D0=0), ALWAYS-TAKERS (D1=D0=1),
    NEVER-TAKERS (D1=D0=0). LATE says nothing about always/never-takers, so in general
    LATE ≠ ATE ≠ ATT. It is a LOCAL, internally-valid parameter; external validity is a
    separate question (pp.111–112). Weak first stage (§4.1.3, p.100) makes IV useless — check
    it before believing anything.

================================================================
5. STRATEGIES TO ADOPT, RANKED
================================================================
A. PREFERENCE-BASED INSTRUMENT → LATE (Ch.4; the headline move). Instrument = prescriber
   or clinic PRESCRIBING PREFERENCE (e.g. the class the provider gave their PREVIOUS MDD
   patient, or the provider's baseline-period class rate). Requirements to defend, in order:
     - First stage / relevance (§4.1, §4.1.3): the provider's lean must strongly shift THIS
       patient's class. Verify empirically; a marginal first stage gives useless estimates.
     - Independence (§4.4, eq. 4.4.2): which provider a patient lands on is plausibly
       as-good-as-random w.r.t. unmeasured severity, conditional on clinic/covariates.
     - Exclusion (Thm 4.4.1 A2): provider preference affects TRD ONLY through the drug chosen.
     - Monotonicity (A4): a provider's SNRI lean never makes a patient LESS likely to get SNRI.
   Payoff: a clean LATE among compliers (marginal patients whose class was swayed by
   preference) where you currently have a confounded ATE. State the two mandatory caveats:
   LATE is local to compliers, and it is silent on always/never-takers.
   PREREQUISITE: a prescriber/department identifier must survive into the medication records
   (check MDD_MED_DATE_CSV_PATH source + encounters). If it does not, strategy A is dead and
   B–E are the ceiling.

B. IF NO INSTRUMENT: perfect the design, stop overselling heterogeneity.
   - Keep the active-comparator new-user design (exactly what §3.2–3.3 endorses).
   - BOUND the unmeasured confounding instead of assuming it away: Rosenbaum sensitivity
     bounds or an E-value ("how strong must an unmeasured confounder be to overturn this?").
     MHE §3.2.2 (OVB) is the intuition; the E-value is the modern operationalization.
   - NEGATIVE-CONTROL OUTCOME: pick an outcome the class contrast cannot plausibly cause; if
     an "effect" appears there, the CIA is falsified. (Mentor already floated NSAID as a
     negative-control variable — same logic, applied to outcomes.)

C. HARDEN THE ATE VIA THE OVERLAP LENS (§3.3.2–3.3.3). The book's verdict (§3.3.3, pp.63–65):
   propensity methods and regression usually agree; the payoff is OVERLAP, not the estimator.
   So trim more aggressively than the 0.10 floor and REPORT A COVARIATE-BALANCE TABLE in the
   trimmed/weighted two-arm sample (Table 3.3.1 template, p.54). Won't create signal; makes
   the ATE credible to reviewers.

D. CHANGE THE ESTIMAND TO ONE THE DATA SUPPORTS (ATT, not population CATE). MHE distinguishes
   population ATE from the effect on the treated (ATT, eq. 3.2.5). The minority arm
   (bupropion / SNRI initiators, N >= 4,768) is both policy-relevant ("who actually got
   switched") and better powered than a population-wide CATE surface.

E. REPORT THE NULL HONESTLY. Weak/absent heterogeneity, stated cleanly with the CIA caveat,
   is a legitimate finding — the book's whole temperament favors a credible null over an
   incredible positive. If the prescriber route is taken, cluster SEs by prescriber/clinic
   (Ch.8, Moulton factor, pp.231–238).

================================================================
6. WHAT TO READ, IN ORDER (section + page map)
================================================================
  §3.2.1  Conditional Independence Assumption ........... pp.38–44  (name your core assumption)
  §3.2.2  Omitted Variables Bias formula ................ pp.44–47  (why leftover severity bites)
  §3.2.3  Bad Control ................................... pp.47–51  (confirm you avoided it)
  §3.3.1–3.3.3  Matching / Propensity / vs Regression ... pp.51–65  (estimator barely matters; overlap does)
  §4.1    IV and causality (first stage, reduced form) .. pp.84–90  (the instrument mechanics)
  §4.1.3  Weak-instrument caveat ........................ p.100     (check first stage or quit)
  §4.4.1–4.4.2  LATE + complier subpopulation ........... pp.111–119 (the actual pivot)
  Ch.8    Clustered SEs (Moulton) ....................... pp.231–238 (only if prescriber design)

================================================================
7. OPEN QUESTIONS / PREREQUISITES
================================================================
  - [PREREQ for Strategy A] Does a prescriber / ordering-provider / department identifier
    exist in the medication or encounter source tables? This gates the entire IV/LATE pivot.
  - If yes: is there enough within-provider variation and a strong enough first stage
    (providers who genuinely split across classes) to build a preference instrument?
  - Independence threat to log: are patients triaged to particular prescribers BY severity
    (e.g. sickest routed to specialists)? If so, condition on clinic/covariates and argue
    residual as-good-as-random assignment — or the exclusion/independence story collapses.

================================================================
8. TUTORING THREAD (live lesson state — keep current)
================================================================
The user is being taught the econometrics in sections 1–5 above, tutor-style. This section
is the resumable state so any session can continue teaching from this file alone.

STYLE / LEVEL (do not violate):
  - CS + applied-math double major. Give real derivations and proofs; use adult examples,
    NOT baby examples.
  - Claude does ALL the reading (writeup/Mostly Harmless Econometrics.pdf). The user will
    not read the book; that is the tutor's job.
  - ONE concept per turn; the user does the work; end each turn with exactly ONE exercise;
    GRADE it before advancing. If wrong, re-teach the same point from a fresh angle.
  - Write math in UNICODE plain text, never LaTeX (the terminal renders markdown, not LaTeX:
    $...$ shows as raw source). Use subscripts (Y₀ᵢ, Y₁ᵢ), operators (⟂ × ≥ ≈ ≠ → τ μ Σ √),
    E[·]. Markdown tables render fine. For unavoidably heavy math, offer a rendered Artifact.

CURRICULUM (mirrors the reading map in section 6, in order):
  1. Selection-bias decomposition (eq 3.2.1) — naive contrast = ATT + selection bias.
  2. CIA as a matching estimator (§3.2.1, §3.3.1) — what "condition on X" actually buys.
  3. OVB formula (§3.2.2) — short = long + bias; the leftover-severity problem.
  4. Overlap/positivity + the AIPW/DR score Γ — ties to DRTester; why 1/(e(1−e)) detonates.
  5. IV mechanics — first stage, reduced form, exclusion, weak-instrument caveat (§4.1).
  6. LATE theorem + compliers (§4.4) — the headline pivot (prescriber-preference instrument).

STATE (last updated 2026-07-19): Lesson 1 DELIVERED (selection-bias decomposition).
PENDING — the user owes answers to the 4-patient toy exercise below; grade it, then advance
to curriculum item 2 (CIA as matching).

  Exercise setup: constant effect τ = +0.10 for everyone; assignment is severity-driven (the
  two highest-Y₀ patients get D=1). Observed Y = Y₀ for controls, Y₁ for treated.
    patient   Y₀     Y₁     D
      A       0.20   0.30   0
      B       0.30   0.40   0
      C       0.60   0.70   1
      D       0.70   0.80   1
  Tasks: (1) naive diff E[Y|D=1] − E[Y|D=0]; (2) true ATT; (3) selection-bias term;
  (4) verify (2)+(3)=(1); (5) state the CIA in this toy's own terms.
  Answer key (to grade against):
    (1) naive diff = mean(Y|D=1) − mean(Y|D=0) = 0.75 − 0.25 = 0.50
    (2) true ATT = τ = 0.10
    (3) selection bias = E[Y₀|D=1] − E[Y₀|D=0] = 0.65 − 0.25 = 0.40
    (4) 0.10 + 0.40 = 0.50 ✓
    (5) X must capture the severity that drove assignment, so that WITHIN a severity cell the
        treated and control share the same baseline: E[Y₀|D=1,X] = E[Y₀|D=0,X]. Then the
        selection-bias term vanishes cell-by-cell and the within-X contrast equals the CATE.

================================================================
9. DATED REVISIONS (append-only)
================================================================
2026-07-23 — ATE ROBUSTNESS LADDER CONSOLIDATED. The individual robustness moves already
described in §5B (E-value, negative-control outcome) and §5C (overlap trimming + covariate-
balance table) have been consolidated into a single ordered, pre-specified "defense of the ATE"
ladder, now the authoritative falsification protocol in writeup/PAPER2_OUTLINE.md §8(iv) and
Aim 4. No science changed; this is an ordering + reporting convention. The four rungs:
    1. BALANCE (SMD) — SMD = (mean_A − mean_B)/pooled SD per covariate in the trimmed/weighted
       sample; |SMD| < 0.1 negligible. Speaks ONLY to measured covariates.
    2. OVERLAP / POSITIVITY — propensity e(X)=P(armA|X) via model_t, 0.10/0.90 trim; estimand
       becomes the overlap population (§3.3.2–3.3.3). e(X) is a separate classifier of D on
       pre-index X only; the outcome and any post-index variable must never be inputs.
    3. E-VALUE — E = RR + √(RR(RR−1)) for RR≥1 (flip if <1); express the risk-difference ATE as
       an RR first; report on BOTH the point estimate and the CI limit nearest null. A confounder
       bites only if BOTH its arrows (RR-with-treatment AND RR-with-outcome) clear E (WITHIN-var
       AND); the effect is fragile if EVEN ONE measured covariate clears both (ACROSS-var EXISTS),
       since that proves E-strength confounding is real in this data.
    4. NEGATIVE-CONTROL OUTCOME — rerun on an outcome the class cannot cause (NSAID/fracture);
       true effect =0, so any detected effect is confounding via the backdoor treatment←U→outcome
       (the treatment→outcome arrow is absent — that absence is the whole test). DETECTS/falsifies
       the CIA, whereas the E-value only BOUNDS it.
Logic: rungs 1–2 clean the measured world, 3 bounds the unmeasured, 4 tries to catch it. An ATE
caught confounded is a reportable finding under PAPER2_OUTLINE §4, not a failure. STILL OPEN
(next tutoring session): the mechanical jump from per-patient imputed counterfactual differences
to one ATE with a bootstrap confidence interval — the piece that gives the point estimate its
error bars. See writeup/TODO.txt "CAUSAL FOREST — Target Trial 1" for the companion action list.

2026-09-01 — RUNG 2 GAINS ITS FORMAL METRICS; RUNG 1 GAINS ITS THIRD TABLE. No identification
argument changed; both are reporting additions that close holes a reviewer would find.

RUNG 2. The screen as specified stops at the trim: e(X), a 0.10/0.90 band, and per-arm counts.
Counts are not a distribution, and nothing anywhere judged the propensity MODEL. Four metrics are
added, all off the one e(X) column:
  (a) CALIBRATION of e(X) — slope, intercept, a reliability table of observed arm share against
      predicted e(X) by bin, and the Brier score. This is load-bearing rather than cosmetic: the
      band's meaning ("at least 10% of people like this one received each arm") is a statement
      about a PROBABILITY, and an uncalibrated 0.10 does not carry it. If e(X) is miscalibrated
      the trim boundary is not the boundary the estimand claims.
  (b) C-STATISTIC of e(X) against arm assignment, reported with its direction stated. HIGH IS BAD
      here — it is separation, i.e. failure of positivity — which inverts the reading of every
      other discrimination number in this project and must be labelled wherever it appears.
  (c) OVERLAP COEFFICIENT between the two arm-conditional densities of e(X): the scalar summary of
      how much of the two distributions is shared.
  (d) KISH EFFECTIVE SAMPLE SIZE under the overlap weights e(X)(1−e(X)): the honest n behind the
      overlap-weighted sensitivity average, which is otherwise reported as though it had the full
      in-band sample behind it.
Also added, as the visual half of the same rung: e(X) drawn per arm with the band edges marked.
NOTE the E-value does NOT serve this purpose. It is rung 3 and it bounds UNMEASURED confounding;
it says nothing about whether the propensity model is any good. Conflating the two was the
specific confusion this revision resolves.

RUNG 1. The SMD table is computed THREE ways, not one: raw over every eligible test patient,
hard-trimmed over the in-band population, and overlap-weighted. Rung 1 as written above already
says "in the trimmed/weighted sample" and that remains the diagnostic of record; the raw table is
added beside it because a balance table with no "before" column cannot show that adjustment did
anything, and because the companion action list had drifted to specifying raw only. Report raw and
hard-trimmed as the table, overlap-weighted as a sensitivity column — the same headline/sensitivity
pattern already locked for the ATE itself.
