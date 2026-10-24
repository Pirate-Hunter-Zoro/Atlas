# References — Paper 2 (counterfactual antidepressant selection)

Citation set for the eventual Paper 2 manuscript, per `../PAPER2_OUTLINE.md` §14 plus the
book underlying `../CAUSAL_IDENTIFICATION.md`. Filenames are prefixed with the §14 reference
number; the groupings below are by **role in the argument**, not by number. Last updated 2026-08-05.

**Status: 21 of 22 papers held, plus the book. 1 still needed — Komorowski 2018 (partial,
supplements only). Davies 2013 arrived by author reprint 2026-08-05 and is now held; it was the
last fully-missing paper and the one anchoring the IV pivot.**

Three papers here are also cited by Paper 1 and carry a second physical copy under
`../../paper1-trd-prediction/references/` (Sheu 2023, Chekroud 2016, Chekroud 2021) — each library
is self-contained.

---

## Textbook — identification foundation
- `Mostly Harmless Econometrics.pdf` — Angrist & Pischke 2009. The source for
  `../CAUSAL_IDENTIFICATION.md`; CIA / IV / LATE spine. **Page offset: book p.N = PDF p.(N+17).**

## Off-policy evaluation & policy learning (Aim 2)
| # | File | Role |
|---|------|------|
| 1 | `01_AtheyWager2021_PolicyLearning.pdf` | OPE / policy-learning machinery |
| 2 | `02_Dudik2011_DR-OPE.pdf` | Doubly-robust off-policy evaluation |
| 3 | `03_Swaminathan2015_SNIPS_NeurIPS.pdf` | Self-normalized IPS estimator |

## Target-trial emulation & identification framing
| # | File | Role |
|---|------|------|
| 7 | `07_HernanRobins2016_target-trial_AJE.pdf` | Target-trial emulation (framing spine) |
| 16 | `16_Wu2021_ITR-targettrial_JPM.pdf` | ITR validated by target-trial emulation |
| 22 | `22_Szmulewicz2023_STARD-targettrial_BiolPsych.pdf` (+ `_SUPPL-APPENDIX.pdf`) | STAR*D target-trial emulation (received from author 2026-07-26) |

## Prescribing-preference instrumental variable (the IV pivot)
| # | File | Role |
|---|------|------|
| 8 | `08_Brookhart2006_preference-IV_Epi.pdf` | Prescribing-preference IV (origin of the pivot) |
| 10 | `10_WiddingHavneraas2021_preferenceIV-assumptions_JCE.pdf` | Preference-IV assumption-reporting caveats |
| 9 | `09_Davies2013_preferenceIV-antidepressants_JCE.pdf` | Antidepressant preference-IV validation in UK general practice (CPRD); *anchors the IV pivot*. Received from the author 2026-08-05 |

## Falsification battery — robustness tools
| # | File | Role |
|---|------|------|
| 11 | `11_VanderWeeleDing2017_Evalue_AnnInternMed.pdf` | E-value (robustness ladder rung 3) |
| 12 | `12_Lipsitch2010_negative-controls_Epi.pdf` | Negative-control outcomes (rung 4) |

## Proxy-outcome lineage
| # | File | Role |
|---|------|------|
| 17 | `17_Hughes2020_treatment-stability_JAMANO.pdf` | Proxy-outcome lineage (treatment stability) |

## Closest competitors & positioning
| # | File | Role |
|---|------|------|
| 13 | `13_Bilu2026_datadriven-policy_BMCPsych.pdf` | Closest competitor; drove the reframe |
| 14 | `14_Sheu2023_perclass-prediction_npjDM.pdf` | Closest EHR predictive work (positioning) — *also Paper 1* |
| 15 | `15_PuacPolanco2024_VHA-ITR_MolPsych.pdf` | VHA individualized treatment rule (NIHMS author MS) |
| 21 | `21_Perlis2023_GPT4-antidepressant.pdf` | LLM vignette recommender (gap claim) |

## Generalization & replication (predictive-model caveats)
| # | File | Role |
|---|------|------|
| 18 | `18_Chekroud2016_crosstrial-prediction_LancetPsych.pdf` | Cross-trial ML prediction (received from author 2026-07-27) — *also Paper 1* |
| 19 | `19_Chekroud2021_promise-ML_WorldPsych.pdf` | Generalization self-critique — *also Paper 1* |
| 20 | `20_Nunez2021_replication_PLoSONE.pdf` | Replication-failure evidence |

## Cautionary canon — RL / AI in healthcare
| # | File | Role |
|---|------|------|
| 5 | `05_Gottesman2019_RL-guidelines_NatMed.pdf` | RL-in-healthcare guidelines |
| 6 | `06_Jeter2019_AIClinician-critique.pdf` | Proxy/reward-design critique |
| 4 | `04_Komorowski2018_AIClinician_METHODS-SUPPLEMENT.docx`, `04_..._SUPPL-APPENDIX.docx` | AI Clinician — ⚠ **PARTIAL**: only the green-deposited supplements are held; **main article text** still needs ILL or author reprint. Sufficient as-is for a positioning cite. |

---

## Still needed — request via ILL or author reprint
The remaining reprint-request email is drafted in `reprint_request_emails.md`.

| # | Paper | Identifier | State |
|---|-------|-----------|-------|
| 4 | Komorowski et al. 2018, AI Clinician, Nat Med | DOI 10.1038/s41591-018-0213-5 | partial — supplements only |

## Notes
- Apart from Davies 2013 (below), none of the held PDFs have been read in full yet — they are the
  source files, not vetted.
- Two citations still carry "unverified" flags from the §14 literature scan: **Brookhart 2006**
  (page range) and **Puac-Polanco 2024** (effect size). Confirm these against the primary text
  before final formatting.

### Davies 2013 — verified against the primary text, 2026-08-05

Full citation, confirmed from the PDF: Davies NM, Gunnell D, Thomas KH, Metcalfe C, Windmeijer F,
Martin RM. Physicians' prescribing preferences were a potential instrument for patients' actual
prescriptions of antidepressants. *J Clin Epidemiol.* 2013;66(12):1386-1396.
doi:10.1016/j.jclinepi.2013.06.008.

**The DOI previously recorded here (10.1016/j.jclinepi.2013.01.007) was wrong** — corrected above.

Does it say what the plan assumes? Substantially yes, with one scope caveat:

- **Instrument strength.** A physician who previously prescribed a TCA was 14.9 percentage points
  (95% CI 14.4-15.4) more likely to prescribe a TCA to the next patient; for paroxetine vs. other
  SSRIs the gap was 27.7 points (26.7-28.8). Preference is a strong predictor of the next
  prescription.
- **Exchangeability evidence.** Prior prescriptions were *less* strongly associated with patients'
  observed baseline characteristics than actual prescriptions were — the empirical signature the
  preference-IV design needs.
- **Design detail worth copying.** Multiple prior prescriptions formed a stronger instrument than a
  single prior prescription. Build the instrument from a window of a prescriber's recent history,
  not just their last script.
- **⚠ Scope caveat.** The authors' conclusion is explicitly that preferences are valid instruments
  "for evaluating the **short-term** effects of antidepressants." Paper 2's outcome is treatment
  resistance over a one-year horizon, which is outside the window Davies validated. The exclusion
  restriction over a year is a stronger assumption than anything this paper establishes, and the
  falsification battery has to carry that weight.
- **Setting difference.** UK general practice via the CPRD, single-payer, GP-gatekept. Paper 2's
  setting is a US community health system, where formulary and insurance pressures shape
  prescribing differently.
