<!--
Section 5 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Results
-->

# Results

## Cohort Characteristics

Of 501,718 patients in the extract, 42,579 met eligibility criteria and 7,455 (17.5%, 95% CI 17.2--17.9) met the TRD proxy definition. Median age was 55 years (IQR 38--70); 72.5% (95% CI 72.0--72.9) were female, 80.0% (95% CI 79.7--80.4) were recorded as White/Caucasian, and 98.9% (95% CI 98.8--99.0) preferred English. Outcome-positive patients more often had coded suicidality, severe depression, anxiety, insomnia, and substance use disorders (Table 1). Expanded characteristics and subgroup outcome frequencies are in Multimedia Appendix 1, section S11.

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

AUPRC was 0.302 (95% CI 0.281--0.325) for embedded logistic regression and 0.298 (95% CI 0.276--0.322) for feature-vector XGBoost, compared with the test patients' positive-rate reference of 0.175 (95% CI 0.167--0.183). Brier scores were 0.137 (95% CI 0.132--0.142) and 0.138 (95% CI 0.132--0.143), respectively. Calibration varied by model and method of assessment; the individual-level logistic calibration slope for embedded logistic regression was 0.97 (95% CI 0.88--1.06). Full calibration summaries, precision--recall curves, and descriptive operating points appear in Multimedia Appendix 1, sections S2--S3, S9, and S12.

## Clinical Contributions and Encoder Robustness

For Qwen3-Embedding-8B, permuting psychiatric history reduced ROC AUC by 0.024 (95% CI 0.010--0.036) to 0.028 (95% CI 0.017--0.039) across classifiers, with all paired CIs excluding zero. For embedded logistic regression, medication burden and prior treatment exposure reduced ROC AUC by 0.027 (95% CI 0.018--0.037) and 0.019 (95% CI 0.011--0.027), respectively. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003, and every such interval included zero (Table 3). These results describe direct input reliance under the tested perturbations.

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

## Nearest-Neighbor Retrieval

Retrieval is reported as a curve over neighborhood size (Figure 4D for Qwen3-Embedding-8B). At every k from 1 to 34,063, both nearest-neighbor metrics stayed below both leading classifiers, and random retrieval stayed at chance. Neighborhood size mattered more than the similarity metric. Discrimination rose with k up to a few hundred neighbors. From k = 261 onward, logistic-regression-weighted retrieval stayed inside the interval at its best k. Plain cosine retrieval peaked and then drifted down, to 0.605 (95% CI 0.589--0.620) at k = 16,988. Each arm's maximum was read at its best k, chosen on the test patients, so these maxima are optimistic. Logistic-regression-weighted retrieval reached 0.625 (95% CI 0.610--0.641) at k = 295, plain cosine 0.618 (95% CI 0.602--0.634) at k = 757, and random retrieval 0.500 (2.5th--97.5th percentile across draws 0.484--0.515) at k = 32,720, a best k that is noise. The 2 nearest-neighbor metrics exceeded random retrieval by 0.125 (95% CI 0.103--0.147) and 0.118 (95% CI 0.096--0.140), respectively, and differed from each other by 0.007 (95% CI −0.001 to 0.014). The best retrieval result over every k and exponent was logistic-regression-weighted retrieval with α = 2 at k = 1,090, 0.625 (95% CI 0.610--0.640). It was still lower than feature-vector XGBoost by 0.024 (95% CI 0.012--0.036) and lower than embedded logistic regression by 0.032 (95% CI 0.022--0.043). Using all 34,063 training patients as neighbors, with no k chosen, gave 0.624 (95% CI 0.607--0.639) for logistic-regression-weighted retrieval and 0.608 (95% CI 0.592--0.624) for plain cosine. These stay above chance because each neighbor's vote is weighted by its similarity, so the same 34,063 neighbors are weighed differently for each patient. With equal weights, every patient would get the same score and ROC AUC would be exactly 0.5, which is what random retrieval gave at k = 34,063. ROC curves and confusion matrices at each arm's best k are in Multimedia Appendix 1, section S6.

```{=latex}
\begin{figure}[tbp]
```

![](../results/cross_embedder_retrieval/neighbor_count_sweep_panels.png){width=6in}

***Figure 4.** Retrieval discrimination by neighborhood size for the 4 encoders: (A) bge-small-en-v1.5, (B) bge-en-icl, (C) Qwen3-Embedding-4B, and (D) Qwen3-Embedding-8B. Each panel title gives the encoder's number of embedding dimensions. Each panel draws ROC AUC in 8,516 test patients at every k from 1 to 34,063. Lines are the retrieval arms: logistic-regression-weighted and plain cosine retrieval with bootstrap 95% bands, and random retrieval with uniform weights, as the mean across 1,000 draws within the 2.5th--97.5th percentile of the draws. Each encoder's weights come from its own embedded logistic regression. Random retrieval does not use the embedding, so it is the same in every panel. Diamonds mark each arm's best k, chosen on the test patients, so the values there are optimistic; the random arm's best k is noise. Each panel's best-k values are listed beneath it. Horizontal lines mark that encoder's embedded logistic regression and feature-vector XGBoost, which is the same in every panel. Curves use α = 1; for Qwen3-Embedding-8B, the maxima under α = 1, 2, and 5 agreed within 0.002.*

```{=latex}
\end{figure}
```

## Nearest-Neighbor Retrieval Across Encoders

We repeated the neighborhood-size sweep for the other 3 encoders under the same rules, for both nearest-neighbor metrics and random retrieval. Each encoder's logistic-regression-weighted similarity used the coefficients of that encoder's own embedded logistic regression. For every encoder, both nearest-neighbor curves stayed below that encoder's embedded logistic regression at every k (Figure 4A--D). Each metric's maximum was read at its own best k under α = 1, chosen on the test patients, so these maxima are optimistic.

Logistic-regression-weighted retrieval at its best k reached 0.606 (95% CI 0.590--0.620) at k = 579 for bge-small-en-v1.5, 0.631 (95% CI 0.616--0.646) at k = 1,519 for bge-en-icl, 0.623 (95% CI 0.607--0.639) at k = 684 for Qwen3-Embedding-4B, and 0.625 (95% CI 0.610--0.641) at k = 295 for Qwen3-Embedding-8B. Embedded logistic regression reached 0.645 (95% CI 0.629--0.660), 0.655 (95% CI 0.641--0.670), 0.655 (95% CI 0.641--0.670), and 0.657 (95% CI 0.643--0.672) for the same encoders. For each encoder, the upper bound of the retrieval interval lay below the logistic-regression estimate. Paired contrasts were computed for Qwen3-Embedding-8B only.

Plain cosine retrieval peaked at k = 1,243, 413, 493, and 757 for the same 4 encoders. It reached 0.602 (95% CI 0.586--0.618), 0.620 (95% CI 0.605--0.637), 0.621 (95% CI 0.605--0.637), and 0.618 (95% CI 0.602--0.634), lower than the weighted metric for every encoder. Only Qwen3-Embedding-8B's difference was tested, 0.007 (95% CI −0.001 to 0.014), and its interval includes zero. Agreement in direction across 4 encoders does not show that weighting helps, because each maximum was read at its own best k. Every best k for either metric lay between 295 and 1,519. Using all 34,063 training patients as neighbors, weighted retrieval gave 0.617 (95% CI 0.600--0.633) to 0.629 (95% CI 0.614--0.645) for the 3 larger encoders. For bge-small-en-v1.5 it fell to 0.580 (95% CI 0.565--0.595), the steepest decline of any encoder's weighted curve at large k. Near the whole pool (k above about 30,500), every patient's neighborhood is nearly the same set, so the risk estimates differ by about 0.0004 (risk SD 4.00 × 10⁻⁴ at bge-small-en-v1.5's lowest point, k = 31,447), and plain cosine ROC AUC becomes unstable, ranging from 0.511 to 0.582 for bge-small-en-v1.5 and from 0.579 to 0.606 for bge-en-icl, with no change to any conclusion. ROC curves and confusion matrices for each encoder's nearest-neighbor metrics at their best k are in Multimedia Appendix 1, section S6.

Best k followed no clear pattern. Two encoders with the same 4,096 dimensions moved in opposite directions when weighting was added: best k rose from 413 to 1,519 for bge-en-icl and fell from 757 to 295 for Qwen3-Embedding-8B. The curves were flat near their peaks, which accounts for much of this. For every encoder and metric, ROC AUC stayed within 0.005 of its maximum over a wide range of k. That range began between k = 164 and 549 and ended between k = 1,613 and the whole pool of 34,063. These ranges describe the observed curves and carry no sampling interval. On a curve this flat, a small change in the patients can move the best k a long way while barely changing ROC AUC. The range of k that performs near the peak is more informative than the single best k.

Best k also did not follow how many embedding dimensions each logistic regression relied on, whether counted directly or as a share of the encoder's dimensions (Multimedia Appendix 1, section S6, Figures S10--S11).

## Subgroup Performance

Subgroup analyses covered all 8 classifiers and both nearest-neighbor arms, for Qwen3-Embedding-8B; each retrieval arm was scored at its best k. Each contrast compared one group's ROC AUC with that of all other test patients, for the same model. The groups were of 2 kinds. Sociodemographic groups (sex, race, age, marital status, smoking, and religion) ask whether the models work equally well for different people. Clinical groups (MDD recurrence and severity) ask whether they work equally well across ways the illness was recorded.

Of 240 contrasts, 23 survived Benjamini--Hochberg adjustment for multiple comparisons, and both kinds of group contributed (Figure 5). Nineteen were clinical, all involving recurrence. Every model discriminated better in patients coded with recurrent depression, by +0.053 (95% CI +0.022 to +0.085) to +0.072 (95% CI +0.041 to +0.104). Nine of 10 discriminated worse in patients coded with a single episode, by −0.047 (95% CI −0.079 to −0.014) to −0.071 (95% CI −0.105 to −0.039). These describe how the illness was recorded, not who the patients are, so they are not fairness findings.

The other 4 were sociodemographic. Discrimination was lower among never-married patients for 2 embedded classifiers and logistic-regression-weighted retrieval, by −0.047 (95% CI −0.080 to −0.012) to −0.054 (95% CI −0.090 to −0.019). It was lower among patients aged 18--29 for feature-vector XGBoost, by −0.068 (95% CI −0.117 to −0.022). Sex contrasts did not show clear differences. White-minus-non-White ROC AUC differences were consistently positive, from +0.005 (95% CI −0.031 to +0.042) to +0.046 (95% CI +0.006 to +0.087), but none survived adjustment. These findings do not establish equitable performance. Calibration within each subgroup is in Multimedia Appendix 1, section S9.

```{=latex}
\begin{figure}[tbp]
```

![](../results/review/subgroups/subgroup_surviving_contrasts.png){width=5.5in}

***Figure 5.** Subgroup contrasts that survived Benjamini--Hochberg adjustment across 240 contrasts, for Qwen3-Embedding-8B. Each row is one model's ROC AUC in the named group minus its ROC AUC in all other test patients, with a bootstrap 95% CI. Every model whose contrast survived is shown; the other 217 contrasts did not survive. Multimedia Appendix 1, section S9 gives discrimination and calibration within each subgroup for one model per approach and summarizes the sex and race contrasts. Clinical groups describe how depression was recorded; sociodemographic groups describe the patients. Group sizes and outcome counts are for the test patients. Retrieval arms are scored at their best k, chosen on the test patients. LR: logistic regression; MDD: major depressive disorder.*

```{=latex}
\end{figure}
```
