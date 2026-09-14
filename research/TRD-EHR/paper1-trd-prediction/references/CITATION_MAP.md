# Citation map — Paper 1 (TRD prediction)

Maps every numbered reference in `../manuscript.md` to **where it is cited**, **why it is
cited** (the load-bearing reason it appears), and its **verification status**. Numbering follows
order of first appearance in the body.

**Verification:** all 17 original references were independently re-checked against the open web on
2026-08-03 (title, first author, year, venue, and DOI/arXiv ID). **17 of 17 resolve to a real
work exactly as cited; zero discrepancies.** Two references (#18, #19) were added 2026-08-05 to
satisfy TRIPOD+AI item 3c and were verified the same way at the time of addition. The four highest-risk entries (#5 Kautzky, #12 C-Pack,
#14 Qwen3-Embedding, #15 MedGemma) all checked out. See the note on #5 below — the 2017-vs-2018
ambiguity is now resolved.

| # | Reference (short) | Cited where | Why it is cited (rationale) | Status |
|---|-------------------|-------------|-----------------------------|--------|
| 1 | Al-Harbi 2012, TRD review, *Patient Prefer Adherence* | Abstract (background); Introduction | Anchors the claim that TRD carries a **disproportionate share** of depression's morbidity, functional impairment, and cost — the motivation for early prediction | ✅ real, exact |
| 2 | Gaynes 2020, defining TRD, *Depress Anxiety* | Introduction; Outcome | Source for the **operational TRD definition** (failure of ≥2 adequate-dose/duration trials) the outcome label operationalizes | ✅ real, exact |
| 3 | Rush 2006, STAR\*D acute outcomes, *Am J Psychiatry* | Introduction; Outcome | The **sequential-treatment evidence base**: remission rates fall sharply with each step, so later steps face lower recovery odds — why resistance matters | ✅ real, exact |
| 4 | Perlis 2013, TRD risk-stratification tool, *Biol Psychiatry* | Introduction; **Methods → *Predictor selection*** (added 2026-08-20); Discussion | Two roles. (a) Prior **clinical risk-stratification** effort, cited in Discussion as the historical benchmark that achieved only limited separation. (b) **The predictor-selection strategy this study follows** — Perlis assembled clinically plausible candidates by manual review and then pruned them to protect events-per-variable, rather than running a data-driven screen; that is the approach taken here, and saying so is what answers MP's comment 44. It is also a logistic-regression model that outperformed its own ML comparators, which parallels this paper's result | ✅ real, exact |
| 5 | Kautzky 2017, new TRD prediction model, *J Clin Psychiatry* | Introduction [5,7]; Discussion [5,7] | Prior **ML/clinical prediction model on trial/registry data** — comparable-discrimination prior art | ✅ real, exact — see note |
| 6 | Sheu 2023, per-class AD-response prediction, *npj Digit Med* | Introduction [6]; Discussion [6] | The **closest EHR-scale predictive work**: large-sample EHR model whose modest discrimination our results sit beside | ✅ real, exact |
| 7 | Chekroud 2016, cross-trial ML prediction, *Lancet Psychiatry* | Introduction [5,7]; Discussion [5,7] | **ML on richly-phenotyped trial cohorts** reaching comparable discrimination — the ceiling this literature keeps hitting | ✅ real, exact |
| 8 | Chekroud 2021, promise of ML in psychiatry, *World Psychiatry* | Introduction [8]; Discussion [8] | The field's **self-critique on generalization**: strong models often fail out-of-sample — supports our caution against over-claiming | ✅ real, exact |
| 9 | Hegselmann 2025, LLM EHR encoders, *arXiv:2502.17403* | Introduction [9]; Methods (EMBEDDED) | The **direct methodological antecedent**: LLM embeddings of serialized EHR rival purpose-built EHR foundation models — justifies the whole EMBEDDED arm | ✅ real, exact |
| 10 | Collins 2024, TRIPOD+AI statement, *BMJ* | Abstract; Introduction; Methods; Declarations | The **reporting guideline** the manuscript is written against (cited throughout) | ✅ real, exact |
| 11 | Reimers & Gurevych 2019, Sentence-BERT, EMNLP | Methods (encoder); Reproducibility | The **sentence-transformer framework** used to embed narratives | ✅ real, exact |
| 12 | Xiao 2023/2024, C-Pack / BGE, SIGIR '24 (arXiv:2309.07597) | Methods | Model card for the **`bge-small-en-v1.5`** comparison encoder | ✅ real, exact (SIGIR '24 & author list confirmed) |
| 13 | Li 2024, bge-en-icl, *arXiv:2409.15700* | Methods | Model card for the **`bge-en-icl`** comparison encoder | ✅ real, exact |
| 14 | Zhang 2025, Qwen3 Embedding, *arXiv:2506.05176* | Methods | Model card for the **`Qwen3-Embedding-4B`** and primary **`Qwen3-Embedding-8B`** encoders | ✅ real, exact |
| 15 | Sellergren 2025, MedGemma technical report, *arXiv:2507.05201* | Methods (neighbor-weighted) | Model card for **`MedGemma-27B`**, the LLM clinical-similarity judge | ✅ real, exact |
| 16 | Pedregosa 2011, scikit-learn, *JMLR* | Reproducibility | The **classical-ML implementation** (pipeline, grid search, metrics) | ✅ real, exact (JMLR paper carries no DOI) |
| 17 | Chen & Guestrin 2016, XGBoost, KDD '16 | Reproducibility | The **XGBoost implementation** — one of the four classifiers | ✅ real, exact |

## Note on #5 (Kautzky) — ambiguity resolved

The references README flagged a 2017-vs-2018 uncertainty: a companion paper, Kautzky et al. 2018
"Refining prediction in treatment-resistant depression" (PMID 29228516), could have been the
intended citation. Web verification confirms the cited **DOI `10.4088/JCP.15m10381` resolves to
"A New Prediction Model for Evaluating Treatment-Resistant Depression," Kautzky et al.,
*J Clin Psychiatry* 2017;78(2):215–222** — i.e. the manuscript cites the intended 2017 model paper,
**not** the 2018 companion. No change to the reference is needed. (The physical PDF for this one is
still outstanding/paywalled per the references README, but the citation itself is correct.)

## Coverage check

Every in-text marker [1]–[25] in `../manuscript.md` maps to exactly one entry above, and every
entry is cited at least once. The only citation-adjacent open items are the two paywalled PDFs
still being sourced (Rush 2006 #3, Kautzky 2017 #5) — a *library* gap, not a *citation* error; both
references are bibliographically correct as printed.

Numbering note: #18–#19 (2026-08-05), #20 (2026-08-10), and #21 (2026-08-17) were **appended**
rather than interleaved by first appearance, matching the policy stated in the manuscript's
reference-block comment — the existing order is not strictly by first appearance anyway (the
Abstract cites TRIPOD as [10]), so a strict renumber would churn every marker for no gain.
| 18 | González 2010, depression care in the US, *Arch Gen Psychiatry* | Introduction | **TRIPOD+AI item 3c** (known health inequalities): Mexican American and African American adults meeting MDD criteria had lower odds of any depression therapy and of guideline-concordant therapy, with severity comparable across groups. Motivates the fairness analysis and the concern that a switching-derived label can encode unequal access | ✅ real, exact (verified via PMC2887749, 2026-08-05) |
| 19 | Alegría 2008, disparity in depression treatment, *Psychiatr Serv* | Introduction | **TRIPOD+AI item 3c**, paired with #18: the canonical US disparity estimate — nearly all racial/ethnic minority groups had lower odds of adequate depression treatment than white adults | ✅ real, exact (Psychiatr Serv 59(11):1264-1272, doi:10.1176/ps.2008.59.11.1264, PMID 18971402) |

| 20 | Varma & Simon 2006, CV selection bias, *BMC Bioinformatics* | Discussion → Future directions; Supplement S7.1 | The **methodological warrant for out-of-fold scoring** of the two tuned fusion variants: a CV error computed for a model that has itself been tuned by CV is significantly biased, so the reported AUC must come from held-out predictions while the deployable parameters are fitted separately on the full set. Also supplies the statement that the CV estimate is an estimate of the true error of the model the same procedure returns when trained on the entire dataset | ✅ real, exact (open access, PDF held; verified against the article 2026-08-10) |

| 21 | Forthman 2025, TRD in All of Us, *J Affect Disord* | Methods → *Outcome* (operational definition) | **The source of this study's outcome label.** Its EHR-based definition — "TRD was assigned to MDD participants with 3 or more antidepressant treatments within 1 year" — is adopted here unchanged, so the target modelled in this paper is the one already characterized in that cohort. Cited at the coauthors' direction 2026-08-17; two authors (Forthman, Paulus) are shared with this manuscript, and KLF prepared the labels for this study | ✅ real, exact (bibliographic fields read off the publisher PDF held as #21: *J Affect Disord* 2025;390:119858, doi:10.1016/j.jad.2025.119858) |
| 22 | Shmatko 2025, generative disease transformers (Delphi-2M), *Nature* | Introduction (representational motivation) | Establishes the **dominant alternative** this paper does not use: pretraining a transformer directly on coded medical-event sequences, predicting >1,000 disease rates from prior history at UK Biobank scale with external Danish validation. Cited so that the serialize-and-embed design reads as the affordable alternative to event-sequence pretraining rather than as the only available approach | ✅ real, exact — *Nature* 2025;647(8082):248-256, doi:10.1038/s41586-025-09529-3, web-verified 2026-08-20. An Author Correction exists (10.1038/s41586-025-09879-y); the primary article is cited, as with #10 |
| 23 | Waxler 2025, CoMET medical-event scaling, arXiv | Introduction (representational motivation, with #22) | Carries the **resource** half of that same argument: CoMET's power-law scaling over Epic Cosmos (118M patients, 115B events) shows this model class improves predictably with corpus and compute — precisely what a single-site group does not have. Together #22 and #23 justify why a cheap serialize-and-embed pipeline is worth evaluating at all | ✅ real, exact — arXiv:2508.12104, still a preprint as of 2026-08-20 (web-verified); cite as arXiv, consistent with #5, #6, #7, #8, #17 |
| 24 | Hegselmann 2024, faithful LLM patient summaries, *PMLR* (CHIL) | Methods → *Predictors and patient representations* (deterministic narrative) | **Defends the deterministic renderer.** Quantifies hallucination in LLM-generated summaries of clinical records (2.60 → 1.55 per summary for Llama 2 when fine-tuned on hallucination-free data), so the risk is measured rather than speculative. In our pipeline a generative renderer would perturb the *predictor itself* in unverifiable ways, which is the reason rendering is deterministic. Same first author as #17, a different paper — do not conflate | ✅ real, exact — *Proc Mach Learn Res* 2024;248:339-379, CHIL 2024; fields read off the held PDF |
| 25 | Lee 2026, reporting LLM-as-a-judge evaluations, arXiv | Methods → *Model development* (neighbor-weighted retrieval, LLM judge) | **Pre-empts the central objection to the LLM-judge arm.** Shows that imperfect judge sensitivity and specificity bias any score computed from judge verdicts, and that de-biasing needs a human-labelled calibration set we do not have. Cited to state why this design is not exposed to that bias: the judge produces a neighbour *weight* inside a predictor scored against real TRD outcomes, so judge error shows up as degraded measured discrimination, never as an inflated agreement statistic | ✅ real, exact — arXiv:2511.21140v2, 4 Jan 2026; fields read off the held PDF |


**PDFs for #18 and #19 are not yet held in this library.** González 2010 is open access at
PMC2887749; Alegría 2008 is at doi:10.1176/ps.2008.59.11.1264 (PMID 18971402). Both are
background citations, so neither blocks submission.

**Refs 22–25 added 2026-08-20** from the batch M. Paulus supplied, and web-verified on
addition. They are appended rather than interleaved, for the same reason as #18–19 and #21: the
existing numbering is not strictly by first appearance, so a strict renumber would churn every
reference for no gain.

**On comment 44 (predictor selection).** MP's tracked-changes review asked for the prior papers
behind the predictor set, believing he had sent them. He had not — all ~20 files in the supplied
batch were checked and none concerns treatment-resistant depression or antidepressants. The
provenance is therefore carried by references already in the list: **#4 Perlis 2013 is the
methodological anchor**, since this study follows its manual-review-then-prune selection strategy
rather than any data-driven screen, and #5 Kautzky, #6 Sheu, and #7 Chekroud supply the predictor
domains. #4's role in the map above has widened accordingly — it is now cited in Methods as the
selection-strategy source, not only in the Introduction and Discussion as a performance benchmark.

| 25 | Cepeda 2018, data-driven TRD definition, *Depress Anxiety* | Introduction [25-27]; Discussion, *Clinical interpretation* [25-27] | One of three sources for the claim that **computable TRD phenotypes vary with their rules**: its data-driven rule (≥3 antidepressants or ≥1 antipsychotic in a year) yields 15.8% TRD, against the switch-count definitions used elsewhere | ✅ verified 2026-09-03 — issue and pages were wrong as first entered (35(2):126-133) and are corrected to 35(3):220-228; PDF held |
| 26 | Fabbri 2021, TRD in UK primary care, *Mol Psychiatry* | Introduction [25-27]; Discussion, *Clinical interpretation* [25-27] | Second source for the same claim, from **prescribing records rather than claims**: ≥2 switches of ≥6 weeks each gives 13.2–13.5% of MDD cases across two cohorts | ✅ verified 2026-09-03, exact as cited; PDF held |
| 27 | Iveson 2026, definitions matter, *BMC Psychiatry* | Introduction [25-27, 25/27 in the temporal-separation clause, 27 in the closing clause]; Discussion, *Clinical interpretation* [25-27] | The **direct warrant for the phrase**: nine TRD definitions across three cohorts, and more inclusive rules do not merely classify more people, they shift the sample older and more deprived | ✅ verified 2026-09-03 — author list, volume and pages were wrong as first entered and are corrected; PDF held |
| 28 | Liberman 2020, incident TRD for health systems, *J Manag Care Spec Pharm* | Introduction (the 0.83 high-end figure); Discussion, *Comparison with prior work* | The **high end of the reported range**, and why: linked claims and EHR data on 35,246 adults over 24 months, with predictors that mix illness burden with the structure and intensity of care | ✅ verified 2026-09-03 — **AUC 0.83, 24-month follow-up and 35,246 all confirmed against the abstract**; PDF held |
| 29 | Lage 2022, TRD risk from EHR, *J Affect Disord* | Introduction (the 0.652 figure); Discussion, *Comparison with prior work* | The **externally validated** counterpoint to Liberman, and the estimate our own 0.65 is closest to | ✅ verified 2026-09-03 — **0.652 (95% CI 0.623–0.682) and top-quintile lift 1.99 (1.76–2.22) confirmed**; not open access, reprint request drafted |
| 30 | Lee 2024, explainable multimodal TRD prediction, *Psychiatry Res* | Introduction (the 0.728 figure); Discussion, *Comparison with prior work* | Establishes that **structured data are informative but benefit from genuinely incremental modalities** — the sentence that stops our null being read as "text adds nothing, ever" | ✅ verified 2026-09-03 — **structured-only 0.684, notes-only 0.569, combined 0.728, all-sources 0.794 confirmed**; not open access, reprint request drafted |
| 31 | Walsh 2025, generalizability across three health systems, *medRxiv* | Introduction (the 0.51–0.58 figure); Discussion, *Comparison with prior work* | **Transportability is the binding constraint, not discrimination**: internal 0.58–0.64 falls to 0.51–0.58 externally, with poorly concordant patient-level risk — the reason the paper claims no clinical role | ✅ verified 2026-09-03 — **both ranges confirmed**, as is the poor concordance (CCC 0.13–0.38); PDF held (preprint, as cited) |

**Verification of refs 25–31, 2026-09-03.** All seven resolve to a real work in PubMed. Three
had wrong bibliographic fields as first transcribed from the senior author's list and are
corrected in the manuscript. **All four discrimination figures quoted in Discussion,
*Comparison with prior work*, were checked against the source abstracts and every one is
exact.** Five PDFs obtained the same day from open-access sources; Lage and Lee are not open
access.
