# TRD-EHR

## Where things are

- Paper 1 (predicting TRD): paper1-trd-prediction/, split per section in parts/.
- Paper 2 (counterfactual antidepressant selection): paper2-counterfactual/.
- Figures reach the Mac only through exports/, once the owner marks them aggregate.
- Settled decisions and done tasks: threads.json in git history.

## Now

Paper 1, as of 2026-10-10 (done on the cluster, at the owner's word, once):
- Figure 4: all four encoders in one 2x2, width in each title, best k a diamond. The dimension scatters are S6's Figures S10-S11 (count; share of width); old S10-S15 are S12-S17.
- Results: Nearest-Neighbor Retrieval, Across Encoders, then Subgroup Performance with Figure 5, every contrast surviving Benjamini-Hochberg. Subgroup text is discrimination only.
- The feature arm's subgroup stand-in is XGBoost (Tables S10-S11, Figure S13).
- Discussion: Interpreting Nearest-Neighbor Retrieval, from Martin's note, citing [30] NCA and [31] Cawley. References checked against Crossref and arXiv.
- Forthman is third author; Acknowledgments name Claude beside ChatGPT. Packet and parts rebuilt; exports/ holds the new figures.

The owner steers by inking the PDF; marks carry no text, so open every PNG. Cluster reports come three at a time, one card per batch. Check export timestamps yourself: a report does not prove the copy reached the Mac.

Paper 1:
- [ ] Learn: why ROC AUC against k has its shape: the random arm at 1/2, k = 1, the climb in log k, the right edge, why every best k is optimistic. Its one unworked concept; teach it when the owner returns to learning.
- [ ] Ask Martin: the corresponding author (2026-09-29 ink round, item 1); the title, which now names retrieval; whether Limitations stays; whether the similarity judge stays in reserve; the Discussion's take-home; the sparsity sentence (385 of 4,096 dimensions); whether S12.1 quotes the bootstrap intervals (job 2120643).
- [ ] Martin accepts or reverts items 2-14 of that round.
- [ ] Then: deterministic to algorithmic in 18 places; patient to participant (about 261 places), never in title or quotations; trained classifier to machine learning model where generic.
- [ ] Re-run the paper reviewer over the new KNN section; answer it.
- [ ] Check every TRIPOD+AI row against the current sections.
- [ ] Answer the five round-2 data questions on the cluster (race, BH contrasts, operating points, n = 32 recurrence row, Table S4 bins).
- [ ] After Martin: Clarity pass on our sections, one per turn, numbers frozen; the owner reads each first.
- [ ] Check every number and cross-reference agrees across the four documents.
- [ ] Confirm at proof: ref 10's TRIPOD+AI primary DOI, and ref 12's C-Pack SIGIR page range.
- [ ] Rebuild the packet again and check that no panel moved.
- [ ] Make rebuild-packet.sh resolve the sections' ../results/*.png from exports/results/.
- [ ] S7 mismatch (14,437/28,142, 0.70 against Tables S5-S6's 14,438/28,141, 0.69): re-run the clustering with a fixed seed.
- [ ] Give suicidality_flag an explicit window, as psych_utilization has, or document the precondition.

Paper 2 (causal forest, preference instrument and switch framing deferred):
- [ ] Learn: the target trial at the index anchor; gradeable against ungradeable predictions; why confounding by indication survives adjustment; why the 0.10/0.90 trim changes the estimand; the four-rung robustness ladder.
- [ ] Build: the per-arm calibration bin table out of grade_arm_models, persisted per arm.
- [ ] Build: one folder per contrast: SMD table, E-value and benchmark, negative control.
- [ ] Coach: the SMD per covariate from balance_frame.csv; how a multi-level categorical field becomes balance rows.
- [ ] Build: the Love plot over the three balance tables.
- [ ] Coach: the overlap coefficient; the E-value on the point estimate and CI limit; both risk-ratio arrows for every measured covariate.
- [ ] Coach: the owner chooses the negative-control outcome; then extract its label from the raw diagnosis tables.

## Open decisions

- The abstract's "rule-based" narratives (3 places) breaks RULES.md, but it is Martin's prose: ask him.
- Owed: the CSV question (card 0006) and the S7 re-run (card 0007), in the imported session.
- Where the sensitivity-label decline's reason goes: Limitations or the covering note.
- suicidality_flag: a window parameter or a stated precondition.
- A train-side panel on the propensity figure.
- The symmetric 0.10/0.90 band, or an adaptive one.
- Whether population_report carries a per-fold section.
- Further balance measures.
- Which negative-control outcome.

## Done recently

- The owner's 2026-10-01 KNN direction: sweep, name, section, Figure 5. The handoff's uncommitted files were committed 2026-10-06.
