<!--
Section 17 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S3 Calibration
-->

# S3 Calibration

Table S3 reports Brier score and weighted calibration error (WCE), for which lower values are better. Across the 8 classifiers, Brier scores ran from 0.137 (95% CI 0.132--0.142) to 0.140 (95% CI 0.134--0.145) and WCE from 0.004 (95% CI 0.003--0.013) to 0.018 (95% CI 0.011--0.026). The binned calibration slopes and intercepts originally reported in the manuscript are retained below, separately from the individual-level logistic slopes in section S9. Binned slopes should not be interpreted as conventional logistic calibration slopes.

Table S3. Brier score and weighted calibration error for all 8 primary representation--classifier combinations and the 3 retrieval arms, each arm at its own test-selected best k, with bootstrap 95% CIs. Both metrics describe the cohort's observed outcome frequency.

| **Representation** | **Model** | **Brier (95% CI)** | **WCE (95% CI)** |
| ---------------------- | ------------------------------ | ---------------------- | ---------------------- |
| EMBEDDED | Logistic regression | 0.137 (0.132--0.142) | 0.010 (0.007--0.019) |
| EMBEDDED | Random forest | 0.140 (0.134--0.145) | 0.006 (0.005--0.015) |
| EMBEDDED | Gradient boosting | 0.139 (0.134--0.144) | 0.004 (0.003--0.013) |
| EMBEDDED | XGBoost | 0.139 (0.134--0.144) | 0.013 (0.007--0.022) |
| FEATURE | Logistic regression | 0.139 (0.134--0.144) | 0.005 (0.003--0.015) |
| FEATURE | Random forest | 0.139 (0.134--0.144) | 0.018 (0.011--0.026) |
| FEATURE | Gradient boosting | 0.138 (0.133--0.143) | 0.010 (0.005--0.018) |
| FEATURE | XGBoost | 0.138 (0.132--0.143) | 0.012 (0.006--0.020) |
| Retrieval | Logistic-regression-weighted cosine, k = 295 | 0.140 (0.134--0.145) | 0.005 (0.003--0.014) |
| Retrieval | Plain cosine, k = 757 | 0.141 (0.135--0.146) | 0.009 (0.004--0.016) |
| Retrieval | Random, uniform weights, k = 32,720 | 0.144 (0.139--0.150) | 0.00001* (0.0001--0.009) |

\* The random arm's WCE lies below its own bootstrap interval. Its predicted risks all sit within 0.002 of the outcome rate, so on the full test set the binned error is almost zero. Every resample moves the observed rate away from those fixed risks, so the resampled errors are larger. The interval therefore describes resampling noise around a near-zero error, not uncertainty about a positive one.

Table S4. Slopes and intercepts fitted to the binned calibration curves, with bootstrap 95% CIs, for the 8 classifiers and the 3 retrieval arms at their own test-selected best k. These descriptive values are retained from the original overall calibration analysis and are not individual-level logistic calibration parameters. See section S9 for the latter. For random retrieval every predicted risk lies between 0.173 and 0.176, so a slope cannot be estimated. The wide classifier intervals come from fitting a line through 10 equal-width bins, several of which hold few patients.

| **Representation** | **Model** | **Binned slope (95% CI)** | **Binned intercept (95% CI)** |
| ---------------------- | ------------------------------ | ---------------------- | ---------------------- |
| EMBEDDED | Logistic regression | 1.27 (0.86--1.43) | −0.07 (−0.10 to +0.03) |
| EMBEDDED | Random forest | 1.15 (0.34--1.98) | −0.02 (−0.18 to +0.13) |
| EMBEDDED | Gradient boosting | 1.01 (0.42--1.59) | +0.01 (−0.12 to +0.14) |
| EMBEDDED | XGBoost | 0.75 (0.22--1.39) | +0.07 (−0.08 to +0.19) |
| FEATURE | Logistic regression | 0.78 (0.20--1.33) | +0.06 (−0.08 to +0.20) |
| FEATURE | Random forest | 1.84 (1.41--2.23) | −0.15 (−0.22 to −0.08) |
| FEATURE | Gradient boosting | 0.87 (0.28--1.48) | +0.04 (−0.11 to +0.19) |
| FEATURE | XGBoost | 1.02 (0.53--1.52) | +0.02 (−0.09 to +0.13) |
| Retrieval | Logistic-regression-weighted cosine, k = 295 | 1.37 (1.07--1.69) | −0.06 (−0.11 to −0.01) |
| Retrieval | Plain cosine, k = 757 | 2.66 (1.30--2.78) | −0.27 (−0.29 to −0.05) |
| Retrieval | Random, uniform weights, k = 32,720 | not estimable | not estimable |

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png){width=5.8in}

C Logistic-regression-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

D Plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

E Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_RANDOM_UNIFORM_k32720.png){width=5.8in}

Figure S5. Calibration curves for embedded logistic regression (A), feature-vector XGBoost (B), and the 3 retrieval arms at their own test-selected best k (C--E). Panels C--E carry a 95% CI on each bin. Retrieval panels use 10 bins of equal patient count, because retrieval risks crowd near the outcome rate. Random risks all lie near 0.175, so panel E is one cluster of points. The diagonal indicates agreement between predicted and observed outcome frequency; points above it indicate underprediction in that bin, and points below indicate overprediction. The sample is enriched for depression.
