<!--
Section 21 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S7 Record Length and Prediction
-->

# S7 Record Length and Prediction

We examined record volume descriptively by correlating the outcome with history length, encounter count, and the diagnosis-to-index interval, then assessed neighbor-prediction discrimination across history-length quintiles.

Using the full recorded history, outcome correlations were small: Spearman ρ=−0.073 (95% CI −0.082 to −0.064) for pre-index history length, −0.064 (95% CI −0.073 to −0.054) for encounter count, and −0.029 (95% CI −0.038 to −0.020) for diagnosis-to-index interval. Prescribing on the day of diagnosis or the next day occurred in 27,906 patients, with outcome frequency 18.4% (95% CI 17.9--18.8), compared with 14,673 patients and 15.9% (95% CI 15.3--16.5) for later prescribing. These weak marginal relationships do not rule out care-process contributions to prediction.

A Pre-index history length

![](../results/notebook_figures/density_pre_anchor_history_days.png){width=5.7in}

B Diagnosis-to-index interval

![](../results/notebook_figures/density_mdd_to_anchor_days.png){width=5.7in}

Figure S10. Continued on the next page.

C Encounter count

![](../results/notebook_figures/density_num_encounters.png){width=5.7in}

D Outcome frequency by prescription timing

![](../results/review/metric_intervals/trd_rate_by_prescription_timing.png){width=5.7in}

Figure S10. Record length, diagnosis-to-index interval, encounter count, and outcome frequency by prescription timing. A--C show outcome-stratified distributions; axes are truncated as labeled in the original plots. D compares prescribing within 1 day of diagnosis (the day of diagnosis or the next day) with prescribing 2 or more days later. Bars carry Wilson 95% CIs, and each bar is labeled with its outcome frequency and counts. The dashed line is the cohort outcome frequency, 17.5%, with its 95% CI (17.2--17.9) shaded.

The held-out test set was divided into quintiles of pre-index history length, and each retrieval arm was scored within each quintile at its own best k from section S6. The best k was chosen on all test patients, so these values are optimistic in the same way.

Table S8. Neighbor-prediction ROC AUC by quintile of pre-index history length (embedded representation, held-out test set, $\alpha$ = 1), with bootstrap 95% CIs within each quintile. Days are the quintile's bounds of pre-index history. Weighted: logistic-regression-weighted cosine; plain: plain cosine. Random retrieval uses uniform weights and the draw whose AUC at its best k is closest to the mean of 1,000 draws.

| **Days** | **n** | **Events** | **Weighted, k = 295** | **Plain, k = 757** | **Random, k = 32,720** |
| -------------- | --------: | --------: | ------------------------ | ------------------------ | ------------------------ |
| 731--1,110 | 1,706 | 372 | 0.625 (0.592--0.657) | 0.619 (0.585--0.651) | 0.479 (0.447--0.513) |
| 1,111--1,554 | 1,704 | 317 | 0.624 (0.590--0.658) | 0.619 (0.584--0.652) | 0.526 (0.489--0.561) |
| 1,555--2,066 | 1,701 | 290 | 0.600 (0.564--0.636) | 0.608 (0.572--0.643) | 0.531 (0.492--0.564) |
| 2,067--2,733 | 1,704 | 282 | 0.633 (0.598--0.669) | 0.626 (0.592--0.663) | 0.487 (0.449--0.523) |
| 2,734--5,288 | 1,701 | 230 | 0.619 (0.580--0.655) | 0.598 (0.561--0.636) | 0.479 (0.437--0.519) |

AUC ranged from 0.600 to 0.633 for logistic-regression-weighted and 0.598 to 0.626 for plain cosine retrieval, without a monotonic trend, and every quintile's interval overlapped the others. Random retrieval stayed near 0.5, and its interval included 0.5 in every quintile. This does not establish independence from record volume; differing case mix and imprecision within strata limit interpretation.

The stratification covers neighbor prediction only, not the trained classifiers. Each quintile contained about 1,700 patients.
