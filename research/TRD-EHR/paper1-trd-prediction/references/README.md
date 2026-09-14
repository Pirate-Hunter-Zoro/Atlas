# References — Paper 1 (TRD prediction)

Citation set for the Paper 1 manuscript (`../manuscript.md`). The manuscript's reference
list now runs to **31 entries**; this library holds the PDFs behind it plus the tools, models, and
prior work it names in the body. Groupings are by **role**, not order. File-number prefixes
are a **library index**, not manuscript reference numbers — the two have never matched
(`01_Collins2024` is manuscript ref 10). `CITATION_MAP.md` is the authority on which
manuscript number is which.
Last updated 2026-09-03.

**Status: 26 of 31 held.** Four still needed: Rush 2006 (STAR\*D) and Kautzky 2017, both
paywalled and long outstanding; Lage 2022 and Lee 2024, added this round and likewise not
open access. Reprint-request emails for all four are in `reprint_request_emails.md`. Refs
18–19 (González 2010, Alegría 2008) remain background-only with no PDF held.

**Refs 25–31 added 2026-09-03** (section I below) from M. Paulus' review of 2026-09-02 —
the EHR-phenotype and structural-EHR prediction literature the revised Introduction and the
new Discussion subsection *Comparison with prior work* rest on. Unlike the 2026-08-20 batch,
these were supplied as a reference list rather than as files, so all seven were **verified
against PubMed on 2026-09-03** and five were obtained from open-access sources the same day.
Three had wrong fields as first entered and were corrected in the manuscript: Cepeda's issue
and pages, Iveson's author list plus volume and pages, and Walsh's author list. **Every
discrimination figure the Discussion quotes from them was checked against the source
abstract and every one is exact** — see `CITATION_MAP.md`.

**Refs 21–24 added 2026-08-20** (sections G and H below) from a batch of ~20 papers M. Paulus
supplied. That batch was checked file by file for the predictor-selection papers his comment 44
asked for and **contained none of them** — not one of the twenty mentions treatment-resistant
depression or antidepressants. The four kept here earn their place on other grounds: two frame
the Introduction's representational argument, two defend specific design choices in Methods. The
predictor-selection provenance is instead carried by refs 4–7, anchored on Perlis, whose
manual-review-then-prune strategy is the one this paper follows.

Three papers (Sheu 2023, Chekroud 2016, Chekroud 2021) are shared with Paper 2 and carry a second
physical copy here so this library is self-contained; the primary copies live under
`../../paper2-counterfactual/references/`.

---

## A. Reporting standard

| # | File                               | Role                                                                                               |
|---|------------------------------------|----------------------------------------------------------------------------------------------------|
| 1 | `01_Collins2024_TRIPOD-AI_BMJ.pdf` | TRIPOD+AI reporting guideline — the checklist the manuscript is written against (cited throughout) |

## B. ML software & methods

| # | File                                            | Role                                                            |
|---|-------------------------------------------------|-----------------------------------------------------------------|
| 2 | `02_Pedregosa2011_scikit-learn_JMLR.pdf`        | scikit-learn — classical-ML pipeline, GridSearchCV, metrics     |
| 20 | `20_VarmaSimon2006_CV-selection-bias_BMCBioinformatics.pdf` | Cross-validation selection bias — the methodological warrant for scoring the tuned fusion variants out of fold rather than in sample (Supplement S7.1; obtained 2026-08-10, open access) |
| 3 | `03_ChenGuestrin2016_XGBoost_KDD.pdf`           | XGBoost — one of the four classifiers                           |
| 4 | `04_ReimersGurevych2019_SentenceBERT_EMNLP.pdf` | Sentence-BERT / sentence-transformers — the embedding framework |

## C. Embedding & LLM model cards / technical reports

| # | File | Role |
| --- | ------ | ------ |
| 5 | `05_Qwen2025_Qwen3-Embedding_arXiv.pdf` | Qwen3-Embedding tech report — primary encoder (8B) + comparison encoder (4B) |
| 6 | `06_Xiao2023_CPack-BGE_arXiv.pdf` | C-Pack / BGE — covers the `bge-small-en-v1.5` comparison encoder |
| 7 | `07_Li2024_bge-en-icl_arXiv.pdf` | `bge-en-icl` comparison encoder |
| 8 | `08_Google2025_MedGemma_arXiv.pdf` | MedGemma technical report — the `medgemma-27b-text-it` LLM similarity judge |

## D. TRD epidemiology & definition

| # | File | Role |
| --- | ------ | ------ |
| 21 | `21_Forthman2025_TRD-AllOfUs_JAffectDisord.pdf` | **Source of this study's operational TRD definition** — TRD assigned to MDD participants with ≥3 antidepressant treatments within 1 year, applied to the All of Us cohort. Supplied by the coauthors 2026-08-17 and adopted unchanged in Methods, *Outcome*. Shares two authors (Forthman, Paulus) with this manuscript. Note: the paper's *Supplemental Methods; EHR Based Definition of TRD* — the fuller statement of the definition — is **not held**; only the article PDF is |
| 11 | `11_AlHarbi2012_TRD-review_PPA.pdf` | TRD burden / therapeutic-trends review (open access) |
| 10 | `10_Gaynes2020_TRD-definition_DepressAnxiety.pdf` | Consensus definition of TRD — the AHRQ/CMS review establishing the ≥2 prior-treatment-failure MDD definition (obtained 2026-07-27) |
| 9 | ⚠ **MISSING** — Rush et al. 2006, STAR\*D acute outcomes, Am J Psychiatry | Canonical remission/treatment-step source underpinning the operational TRD definition — **paywalled** |

## E. Prior EHR / ML-based TRD prediction

| # | File | Role |
| --- | ------ | ------ |
| 12 | `12_Perlis2013_TRD-risk-stratification_BiolPsych.pdf` | Clinical risk-stratification tool for treatment resistance (NIH author MS) |
| 14 | `14_Sheu2023_perclass-prediction_npjDM.pdf` | Per-class antidepressant-response prediction from EHR — closest predictive work (*also Paper 2*) |
| 15 | `15_Chekroud2016_crosstrial-prediction_LancetPsych.pdf` | Cross-trial ML prediction of antidepressant response (*also Paper 2*) |
| 16 | `16_Chekroud2021_promise-ML_WorldPsych.pdf` | Field-level self-critique on ML-in-psychiatry generalization (*also Paper 2*) |
| 13 | ⚠ **MISSING** — Kautzky et al. 2017, "A New Prediction Model for … Treatment-Resistant Depression," J Clin Psychiatry | Prior ML/clinical TRD-prediction model — **paywalled** (see email note on the 2017-vs-2018 ambiguity) |

## F. LLM-as-EHR-encoder — direct methodological antecedent

| # | File | Role |
| --- | ------ | ------ |
| 17 | `17_Hegselmann2025_LLM-EHR-encoders_arXiv.pdf` | Hegselmann et al. 2025, "Large Language Models are Powerful Electronic Health Record Encoders" (arXiv:2502.17403v3, 21 May 2025). The closest methodological sibling to this paper's EMBEDDED arm: serialize structured EHR into Markdown plain text (medical codes replaced with natural-language descriptions), encode with general-purpose LLM embedding models (GTE-Qwen2-7B, LLM2Vec-Llama-3.1-8B), fit a logistic-regression head, and match or surpass a domain-specific EHR foundation model (CLMBR-T-Base) across 15 EHRSHOT tasks + external UK Biobank validation. Validates the serialize→embed→linear-classifier design at population scale (not TRD-specific — a methods anchor, not a prior-TRD-prediction entry). |

---

## G. EHR foundation models — the alternative this paper does not use

Added 2026-08-20 from the batch M. Paulus supplied. Both are cited in the Introduction to
establish what the *dominant* approach to neural EHR modelling is, so that the
serialize-and-embed design is framed as the cheap alternative to it rather than as the only
option. Neither is a TRD study.

| # | File | Role |
| --- | ------ | ------ |
| 22 | `22_Shmatko2025_generative-disease-transformers_Nature.pdf` | Shmatko et al. 2025, "Learning the natural history of human disease with generative transformers," *Nature* 647(8082):248–256. Delphi-2M — a GPT architecture modified for competing-risk disease progression, trained on 0.4M UK Biobank participants and validated without reparameterization on 1.9M Danish individuals; predicts rates of >1,000 diseases from prior history. Cited as the state of the art in event-sequence pretraining. Note an Author Correction exists (`10.1038/s41586-025-09879-y`); the manuscript cites the primary article, consistent with how ref 10's correction notice is handled. |
| 23 | `23_Waxler2025_CoMET-medical-event-scaling_arXiv.pdf` | Waxler et al. 2025, "Generative Medical Event Models Improve with Scale" (arXiv:2508.12104). CoMET, decoder-only transformers pretrained on Epic Cosmos — 118M patients, 115B medical events — with the largest scaling-law study for medical event data. Cited for the corpus-and-compute point: this class of model improves predictably with scale, which is exactly the resource most groups lack. Still a preprint as of 2026-08-20 (verified). |

## H. Narrative generation and LLM-judge methodology

Added 2026-08-20 from the same batch. Both support *design choices* rather than results.

| # | File | Role |
| --- | ------ | ------ |
| 24 | `24_Hegselmann2024_LLM-patient-summaries_CHIL.pdf` | Hegselmann et al. 2024, "A Data-Centric Approach To Generate Faithful and High Quality Patient Summaries with Large Language Models," *PMLR* 248:339–379 (CHIL 2024). Measures hallucination rates in LLM-written summaries of clinical records (2.60 → 1.55 per summary for Llama 2 after fine-tuning on hallucination-free data). Cited in Methods to justify why the narrative renderer is **deterministic**: a generative renderer would inject unverifiable perturbations into the predictor itself. Same first author as ref 17, different paper — do not conflate. |
| 25 | `25_Lee2026_LLM-as-judge-reporting_arXiv.pdf` | Lee et al. 2026, "How to Correctly Report LLM-as-a-Judge Evaluations" (arXiv:2511.21140v2, 4 Jan 2026). Shows that imperfect judge sensitivity/specificity biases any score computed from judge verdicts, and that correcting it requires a human-labelled calibration set. Cited in Methods to state precisely why our design is *not* exposed to that bias — the judge supplies a neighbour **weight** inside a predictor scored against real outcomes, so judge error degrades measured discrimination instead of inflating an agreement statistic. This is the citation that pre-empts the obvious reviewer objection to the LLM-judge arm. |

---

## Data provenance (not a citation)

| File | Role |
| ------ | ------ |
| `DATA_PROVENANCE_SFHS_query_documentation.docx` | **Internal LIBR working document — NEVER cite this in the paper.** The Saint Francis extract's own query documentation, supplied 2026-08-20. Not a reference — this is the **primary source for Methods, _Source of data and study design_**: it establishes Epic/Caboodle/Clarity as the warehouses, the seven delivered tables, the MD5-hashed keys and SFTP transfer, the person- and encounter-level filters, the verbatim ICD-9/ICD-10 code lists behind the three diagnosis flags, and — most consequentially — the **4:1 case-enrichment sampling** that Methods now describes under *Study population* as the study design. Because this document cannot be cited, that design is stated in prose without a reference; this file is the only record of where the claim comes from, which is why it is kept here rather than left with the data. A second copy lives with the data at `Data/` in the DV260629v1-PV260710v1 study folder. Keep this copy: the Methods section is unverifiable without it. |

---

## Still needed — request via ILL or author reprint

Both remaining are paywalled with no legitimate free copy found. Reprint-request emails are drafted in
`reprint_request_emails.md`. (Gaynes 2020 was the third; obtained 2026-07-27.)

| # | Paper | DOI | Corresponding author |
| --- | ------- | ----- | ---------------------- |
| 9 | Rush et al. 2006, STAR\*D acute/longer-term outcomes, Am J Psychiatry 163(11):1905–1917 | 10.1176/ajp.2006.163.11.1905 | A. John Rush (now Duke-NUS Singapore) |
| 13 | Kautzky et al. 2017, prediction model for TRD, J Clin Psychiatry 78(2):215–222 | 10.4088/JCP.15m10381 | Alexander Kautzky, <alexander.kautzky@ki.se> (Karolinska; first author of both papers). Cc Kasper. The paper's <sci-biolpsy@meduniwien.ac.at> bounced. |

## Notes

- None of the held PDFs have been read in full yet — they are source files, not vetted. (Hegselmann
  2025, #17, has had its abstract/intro/experimental-setup skimmed to confirm role; body not yet read.)
- **Hegselmann 2025 (#17)** sits in its own category F rather than E: it is not a TRD-prediction
  study but the general-method antecedent for the EMBEDDED arm (LLM embeddings of serialized EHR
  rivalling a purpose-built EHR foundation model). It is the natural citation to anchor "why encode
  a narrative with a general-purpose LLM at all" in the Methods/Discussion, distinct from the
  clinical TRD-prediction prior work in category E.
- **Two references added 2026-08-05 (#18 González 2010, #19 Alegría 2008)** to satisfy TRIPOD+AI
  item 3c (known health inequalities between sociodemographic groups), which the checklist audit
  found unaddressed in the Introduction. They document that Black and Mexican American adults
  meeting MDD criteria receive less depression treatment and less guideline-concordant care than
  white adults at comparable severity. PDFs are not held here yet — González 2010 is open access at
  PMC2887749, Alegría 2008 is at doi:10.1176/ps.2008.59.11.1264. Both are background citations and
  neither blocks submission.
- The LLM judge is MedGemma-27B (`google_medgemma-27b-text-it`); ref 8 is the original MedGemma
  technical report (arXiv 2507.05201), which covers that checkpoint, not the later MedGemma 1.5 report.
- **Kautzky year ambiguity (#13): RESOLVED 2026-08-03.** Web verification confirms the manuscript's
  cited DOI `10.4088/JCP.15m10381` resolves to Kautzky et al. 2017, "A New Prediction Model for
  Evaluating Treatment-Resistant Depression," *J Clin Psychiatry* 78(2):215–222 — the intended 2017
  model paper, **not** the 2018 companion "Refining Prediction in Treatment-Resistant Depression"
  (PMID 29228516). The drafted reprint email (2017 model paper) is therefore correct as-is; no change
  needed. A full citation-rationale map for all 17 refs lives in `CITATION_MAP.md`.

## I. EHR TRD phenotypes and structural-EHR prediction (manuscript refs 25–31)

Added 2026-09-03. The first three carry the Introduction's claim that computable TRD
phenotypes are distinct from symptom-confirmed non-response and that varying the operational
rules materially alters prevalence and cohort composition. The last four are the
performance comparisons in Discussion, *Comparison with prior work*.

| # | File | Manuscript ref | Role |
|---|------|---:|------|
| 26 | `26_Cepeda2018_data-driven-TRD-definition_DepressAnxiety.pdf` | 25 | Data-driven TRD definition against expert heuristics; ≥3 antidepressants or ≥1 antipsychotic in a year, giving 15.8% TRD |
| 27 | `27_Fabbri2021_TRD-primary-care-genetics_MolPsychiatry.pdf` | 26 | TRD from UK primary-care prescribing (≥2 switches, ≥6 weeks each); 13.2–13.5% of MDD cases |
| 28 | `28_Iveson2026_TRD-definitions-matter_BMCPsychiatry.pdf` | 27 | Nine TRD definitions across three cohorts — **the direct warrant for "definitions matter"**: more inclusive rules classify more people and shift the sample older and more deprived |
| — | *not held* | 28 | Liberman 2020 — see below, held |
| 29 | `29_Liberman2020_incident-TRD-health-systems_JMCP.pdf` | 28 | Claims+EHR model, 35,246 adults, 24-month follow-up, **AUC 0.83** — the high end of the range |
| — | *not held (not open access)* | 29 | Lage 2022, *J Affect Disord* — externally validated **0.652** (0.623–0.682), top-quintile lift 1.99. Reprint request drafted |
| — | *not held (not open access)* | 30 | Lee 2024, *Psychiatry Res* — multimodal: structured **0.684**, notes **0.569**, combined **0.728**, all sources 0.794. Reprint request drafted |
| 32 | `32_Walsh2025_TRD-model-generalizability_medRxiv.pdf` | 31 | Three health systems: internal **0.58–0.64** falling to **0.51–0.58** external — the transportability constraint the Discussion leans on |
