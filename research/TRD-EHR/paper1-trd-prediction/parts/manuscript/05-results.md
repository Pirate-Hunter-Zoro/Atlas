<!--
Section 5 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Results
-->

# Results

## Cohort Characteristics

Of 501,718 patients in the extract, 42,579 met eligibility criteria and 7,455 (17.5%, 95% CI 17.2--17.9) met the TRD proxy definition. Median age was 55 years (IQR 38--70); 72.5% were female, 80.0% were recorded as White/Caucasian, and 98.9% preferred English. Outcome-positive patients more often had coded suicidality, severe depression, anxiety, insomnia, and substance use disorders (Table 1). Expanded characteristics and subgroup outcome frequencies are in Multimedia Appendix 1, section S11.

***Table 1.** Selected cohort characteristics by TRD proxy status. Values are median (IQR) or n (%). SMD is the standardized mean difference between positive and negative groups. MDD: major depressive disorder; PTSD: posttraumatic stress disorder. Expanded characteristics appear in Multimedia Appendix 1, Table S14.*

  --------------------------------------------------------------------------------------------------------------------
  Characteristic                         Overall\               TRD\                   Non-TRD\               SMD
                                         N=42,579               n=7,455                n=35,124               
  -------------------------------------- ---------------------- ---------------------- ---------------------- --------
  Age (years)                            55 (38--70)            51 (36--66)            56 (39--71)            −0.193

  Female                                 30,850 (72.5%)         5,552 (74.5%)          25,298 (72.0%)         0.055

  White/Caucasian                        34,079 (80.0%)         5,942 (79.7%)          28,137 (80.1%)         −0.010

  Recurrent MDD                          11,213 (26.3%)         2,189 (29.4%)          9,024 (25.7%)          0.082

  Severe MDD                             2,286 (5.4%)           720 (9.7%)             1,566 (4.5%)           0.204

  Unspecified MDD severity               28,951 (68.0%)         4,803 (64.4%)          24,148 (68.8%)         −0.092

  Suicidality flagged                    1,753 (4.1%)           641 (8.6%)             1,112 (3.2%)           0.232

  Anxiety disorder                       22,401 (52.6%)         4,499 (60.3%)          17,902 (51.0%)         0.190

  Substance use disorder (any)           9,265 (21.8%)          2,006 (26.9%)          7,259 (20.7%)          0.147

  Insomnia                               9,350 (22.0%)          2,021 (27.1%)          7,329 (20.9%)          0.147

  PTSD                                   1,541 (3.6%)           450 (6.0%)             1,091 (3.1%)           0.141

  Active medication count                1 (0--2)               1 (0--2)               1 (0--2)               0.084

  Encounter count                        21 (8--46)             17 (6--40)             21 (8--47)             −0.140

  Pre-index history (days)               1,792 (1,216--2,546)   1,629 (1,141--2,335)   1,830 (1,239--2,587)   −0.198

  Any prior antidepressant exposure      10,230 (24.0%)         1,793 (24.1%)          8,437 (24.0%)          0.001

  Prior antidepressant course ≥42 days   6,276 (14.7%)          1,050 (14.1%)          5,226 (14.9%)          −0.023
  --------------------------------------------------------------------------------------------------------------------

Training and test characteristics were closely balanced (maximum absolute standardized mean difference 0.036). Weak negative correlations linked the outcome to history length, encounter count, and time from depression diagnosis to the index prescription. These descriptive checks do not exclude effects of observation or care access (Multimedia Appendix 1, sections S7--S8).

## Discrimination and Calibration

Embedded logistic regression had the highest ROC AUC, 0.657 (95% CI 0.643--0.672), followed by feature-vector XGBoost at 0.649 (95% CI 0.634--0.664). Their paired difference was 0.008 (95% CI −0.003 to 0.019). This post hoc comparison did not demonstrate superior discrimination for embeddings (Table 2; Figure 2).

***Table 2.** Discrimination and Brier score in 8,516 test patients for all primary model combinations, with bootstrap 95% CIs. AUPRC: area under the precision--recall curve; ROC AUC: area under the receiver operating characteristic curve. The positive-rate reference for AUPRC is 0.175 (95% CI 0.167--0.183), the test patients' outcome rate. EMBEDDED uses Qwen3-Embedding-8B; FEATURE uses 92 structured columns.*

| **Representation** | **Classifier** | **ROC AUC (95% CI)** | **AUPRC (95% CI)** | **Brier score (95% CI)** |
| ---------- | ------------------- | ---------------------- | ---------------------- | ---------------------- |
| EMBEDDED | Logistic regression | 0.657 (0.643--0.672) | 0.302 (0.281--0.325) | 0.137 (0.132--0.142) |
| EMBEDDED | Random forest | 0.623 (0.608--0.639) | 0.270 (0.250--0.291) | 0.140 (0.134--0.145) |
| EMBEDDED | Gradient boosting | 0.632 (0.618--0.647) | 0.276 (0.256--0.298) | 0.139 (0.134--0.144) |
| EMBEDDED | XGBoost | 0.636 (0.621--0.651) | 0.278 (0.257--0.300) | 0.139 (0.134--0.144) |
| FEATURE | Logistic regression | 0.629 (0.613--0.644) | 0.278 (0.256--0.300) | 0.139 (0.134--0.144) |
| FEATURE | Random forest | 0.644 (0.630--0.659) | 0.293 (0.271--0.315) | 0.139 (0.134--0.144) |
| FEATURE | Gradient boosting | 0.645 (0.629--0.660) | 0.288 (0.267--0.309) | 0.138 (0.133--0.143) |
| FEATURE | XGBoost | 0.649 (0.634--0.664) | 0.298 (0.276--0.322) | 0.138 (0.132--0.143) |

The direction of the representation difference depended on the classifier. Embeddings improved logistic regression by 0.028 ROC AUC (95% CI 0.017--0.039), but reduced performance for random forest by 0.022 (95% CI 0.011--0.033), gradient boosting by 0.013 (95% CI 0.001--0.026), and XGBoost by 0.013 (95% CI 0.002--0.025).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/discrimination_forest_EMBEDDED_vs_FEATURE.png){width=6in}

***Figure 2.** Discrimination by representation and classifier. A: ROC AUC with bootstrap 95% CIs for all primary models. B: paired differences, EMBEDDED minus FEATURE, with 95% CIs. Diamonds hold the classifier fixed; the star compares embedded logistic regression with feature-vector XGBoost, selected post hoc. An interval crossing zero does not demonstrate superiority or establish equivalence.*

AUPRC was 0.302 (95% CI 0.281--0.325) for embedded logistic regression and 0.298 (95% CI 0.276--0.322) for feature-vector XGBoost, compared with the cohort's positive-rate reference of 0.175. Brier scores were 0.137 (95% CI 0.132--0.142) and 0.138 (95% CI 0.132--0.143), respectively. Calibration varied by model and method of assessment; the individual-level logistic calibration slope for embedded logistic regression was 0.97 (95% CI 0.88--1.06). Full calibration summaries, precision--recall curves, and descriptive operating points appear in Multimedia Appendix 1, sections S2--S3, S9, and S12.

## Clinical Contributions and Encoder Robustness

For the primary encoder, permuting psychiatric history reduced ROC AUC by 0.024 (95% CI 0.010--0.036) to 0.028 (95% CI 0.017--0.039) across classifiers, with all paired CIs excluding zero. For embedded logistic regression, medication burden and prior treatment exposure reduced ROC AUC by 0.027 (95% CI 0.018--0.037) and 0.019 (95% CI 0.011--0.027), respectively. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003, and every such interval included zero (Table 3). These results describe direct input reliance under the tested perturbations.

***Table 3.** Change in ROC AUC after permuting each narrative concept and applying the frozen primary models, with paired bootstrap 95% CIs. Negative values indicate reduced discrimination. LR: logistic regression; RF: random forest; GB: gradient boosting; XGB: XGBoost; SDOH: social determinants of health.*

| **Permuted concept** | **LR** | **RF** | **GB** | **XGB** |
| ---------------- | ---------------- | ---------------- | ---------------- | ---------------- |
| Psychiatric history | −0.028 (−0.039 to −0.017) | −0.027 (−0.039 to −0.013) | −0.024 (−0.036 to −0.010) | −0.027 (−0.039 to −0.014) |
| Medication burden | −0.027 (−0.037 to −0.018) | −0.003 (−0.011 to +0.004) | −0.014 (−0.023 to −0.006) | −0.017 (−0.026 to −0.008) |
| Treatment exposure | −0.019 (−0.027 to −0.011) | +0.000 (−0.008 to +0.009) | −0.006 (−0.014 to +0.003) | −0.011 (−0.020 to −0.003) |
| Treatment contraindications | −0.002 (−0.004 to +0.001) | +0.001 (−0.002 to +0.004) | −0.001 (−0.005 to +0.003) | −0.005 (−0.008 to −0.001) |
| Social determinants (SDOH) | −0.000 (−0.001 to +0.000) | +0.000 (−0.001 to +0.001) | +0.000 (−0.001 to +0.001) | +0.001 (−0.001 to +0.002) |
| Race/ethnicity | −0.000 (−0.002 to +0.002) | +0.000 (−0.003 to +0.003) | −0.003 (−0.006 to +0.001) | −0.000 (−0.003 to +0.003) |

Logistic regression was the strongest embedded classifier for all 4 encoders, with ROC AUCs from 0.645 (95% CI 0.629--0.660) to 0.657 (95% CI 0.643--0.672). Psychiatric history and medication burden remained the largest contributors across encoders. Permuting psychiatric history reduced logistic-regression ROC AUC by 0.027 (95% CI 0.017--0.036) to 0.030 (95% CI 0.019--0.041), and permuting medication burden by 0.022 (95% CI 0.013--0.032) to 0.034 (95% CI 0.023--0.044) (Figure 3). Feature-vector coefficient rankings also emphasized psychiatric burden, including suicidality, severe depression coding, insomnia, and anxiety. Detailed importance, dimensionality, and encoder analyses are in Multimedia Appendix 1, sections S1, S4, and S12.

![](../results/cross_embedder_robustness_EMBEDDED.png){width=6in}

***Figure 3.** Encoder robustness for embedded logistic regression. A: ROC AUC with bootstrap 95% CIs. B: change in ROC AUC after permutation of psychiatric history or medication burden, with paired bootstrap 95% CIs. Encoders are bge-small-en-v1.5, bge-en-icl, Qwen3-Embedding-4B, and Qwen3-Embedding-8B. Complete encoder estimates appear in Multimedia Appendix 1, Table S15.*

## Retrieval and Subgroup Performance

Random retrieval stayed at chance at every k: at its best k, 32,720, it reached 0.500 (2.5th--97.5th percentile across draws 0.484--0.515). Farthest retrieval yielded 0.432 (95% CI 0.416--0.449). Neighborhood size mattered more than the similarity metric (Figure 4). Discrimination rose with k up to a few hundred neighbors. From k = 261 onward, importance-weighted retrieval stayed inside the interval at its best k. Plain cosine retrieval peaked at k = 757 and then drifted down, to 0.605 (95% CI 0.589--0.620) at k = 16,988. At its best k, importance-weighted retrieval reached 0.625 (95% CI 0.610--0.641) at k = 295, and plain cosine 0.618 (95% CI 0.602--0.634) at k = 757. They exceeded random retrieval by 0.125 (95% CI 0.103--0.147) and 0.118 (95% CI 0.096--0.140), respectively. The paired difference between the 2 metrics was 0.007 (95% CI −0.001 to 0.014). The best retrieval result over every k and exponent was importance-weighted retrieval with α = 2 at k = 1,090, 0.625 (95% CI 0.610--0.640). It was still lower than feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and lower than embedded logistic regression by 0.032 (95% CI 0.022--0.043). Because the best k was chosen on test patients, these maxima are optimistic. Using all 34,063 training patients as neighbors, with no k chosen, gave 0.624 (95% CI 0.607--0.639) for importance-weighted retrieval and 0.608 (95% CI 0.592--0.624) for plain cosine (Multimedia Appendix 1, section S6).

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/neighbor_count_sweep_manuscript.png){width=6in}

***Figure 4.** Retrieval discrimination by neighborhood size. ROC AUC in 8,516 test patients at every k from 1 to 34,063 for importance-weighted and plain cosine retrieval, with bootstrap 95% bands, and for random retrieval with uniform weights, as the mean across 1,000 draws within the 2.5th--97.5th percentile of the draws. Points mark each arm's best k, chosen on the test patients, so the values there are optimistic; the random arm's best k is noise. Horizontal lines mark the 2 leading trained classifiers. Curves use α = 1; the maxima under α = 1, 2, and 5 agreed within 0.002.*

Subgroup analyses scored each retrieval arm at its best k. Of 240 subgroup contrasts, 23 survived multiplicity adjustment; 19 involved depression recurrence. Discrimination was higher with recurrent coding in all 10 models contrasted and lower with single-episode coding in 9. Performance was lower among never-married patients for 2 embedded classifiers and importance-weighted retrieval, and among patients aged 18--29 for feature-vector XGBoost. Sex contrasts did not show clear differences. White-minus-non-White ROC AUC differences were consistently positive (0.005--0.046), but none survived adjustment. For feature-vector logistic regression, individual-level calibration slopes were 0.98 (95% CI 0.85--1.11) in White patients and 0.79 (95% CI 0.56--1.02) in patients with other recorded racial categories. These findings do not establish equitable performance (Multimedia Appendix 1, section S9).
