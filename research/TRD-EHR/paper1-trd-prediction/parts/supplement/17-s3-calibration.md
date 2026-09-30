<!--
Section 17 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S3 Calibration
-->

# S3 Calibration

Table S3 reports Brier score and weighted calibration error (WCE), for which lower values are better. Scores ranged from 0.137 to 0.140 and 0.004 to 0.018, respectively. The binned calibration slopes and intercepts originally reported in the manuscript are retained below, separately from the individual-level logistic slopes in section S9. Binned slopes should not be interpreted as conventional logistic calibration slopes.

Table S3. Brier score and weighted calibration error for all 8 primary representation--classifier combinations. Both metrics describe the cohort's observed outcome frequency.

  **Representation**   **Classifier**        **Brier**   **WCE**
  -------------------- --------------------- ----------- ---------
  EMBEDDED             Logistic regression   0.137       0.010
  EMBEDDED             Random forest         0.140       0.006
  EMBEDDED             Gradient boosting     0.139       0.004
  EMBEDDED             XGBoost               0.139       0.013
  FEATURE              Logistic regression   0.139       0.005
  FEATURE              Random forest         0.139       0.018
  FEATURE              Gradient boosting     0.138       0.010
  FEATURE              XGBoost               0.138       0.012

Retrieval rows, each at its own test-selected best k, with bootstrap 95% CIs:

  **Retrieval arm**                          **Brier (95% CI)**       **WCE (95% CI)**
  ------------------------------------------ ------------------------ ------------------------
  Importance-weighted cosine, k = 295        0.140 (0.134--0.145)     0.005 (0.003--0.014)
  Plain cosine, k = 757                      0.141 (0.135--0.146)     0.009 (0.004--0.016)
  Random, uniform weights, k = 32,720        0.144 (0.139--0.150)     0.000 (0.000--0.009)

Table S4. Slopes and intercepts fitted to the binned calibration curves. These descriptive values are retained from the original overall calibration analysis and are not individual-level logistic calibration parameters. See section S9 for the latter.

  **Representation**   **Classifier**        **Binned slope**   **Binned intercept**
  -------------------- --------------------- ------------------ ----------------------
  EMBEDDED             Logistic regression   1.27               −0.07
  EMBEDDED             Random forest         1.15               −0.02
  EMBEDDED             Gradient boosting     1.01               0.01
  EMBEDDED             XGBoost               0.75               0.07
  FEATURE              Logistic regression   0.78               0.06
  FEATURE              Random forest         1.84               −0.15
  FEATURE              Gradient boosting     0.87               0.04
  FEATURE              XGBoost               1.02               0.02

Retrieval rows, each at its own test-selected best k, with bootstrap 95% CIs. For random retrieval every predicted risk lies between 0.173 and 0.176, so a slope cannot be estimated.

  **Retrieval arm**           **Slope (95% CI)**    **Intercept (95% CI)**
  --------------------------- --------------------- ------------------------
  Weighted cosine, k = 295    1.37 (1.07--1.69)     −0.06 (−0.11 to −0.01)
  Plain cosine, k = 757       2.66 (1.30--2.78)     −0.27 (−0.29 to −0.05)
  Random, k = 32,720          not estimable         not estimable

A Embedded logistic regression

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_logistic_regression_EMBEDDED.png){width=5.8in}

B Feature vector XGBoost

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/calibration_curves/calibration_curve_xgboost_FEATURE.png){width=5.8in}

C Importance-weighted nearest retrieval, k = 295

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_IMPORTANCE_WEIGHTED_alpha1_k295.png){width=5.8in}

D Plain-cosine nearest retrieval, k = 757

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_NEAREST_PLAIN_COSINE_alpha1_k757.png){width=5.8in}

E Random retrieval, uniform weights, k = 32,720

![](../results/Qwen-Qwen3-Embedding-8B/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels/calibration_curve_RANDOM_UNIFORM_k32720.png){width=5.8in}

Figure S5. Calibration curves for embedded logistic regression (A), feature-vector XGBoost (B), and the 3 retrieval arms at their own test-selected best k (C--E). Panels C--E carry a 95% CI on each bin. Retrieval panels use 10 bins of equal patient count, because retrieval risks crowd near the outcome rate. Random risks all lie near 0.175, so panel E is one cluster of points. The diagonal indicates agreement between predicted and observed outcome frequency; points above it indicate underprediction in that bin, and points below indicate overprediction. The sample is enriched for depression.
