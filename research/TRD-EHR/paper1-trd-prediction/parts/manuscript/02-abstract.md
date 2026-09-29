<!--
Section 2 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Abstract
-->

# Abstract

**Background:** Electronic health records (EHRs) have been shown to support prediction of subsequent antidepressant switching, an imperfect proxy for treatment-resistant depression (TRD). However, it is unclear whether general-purpose narrative embeddings improve prediction beyond structured feature vectors.

**Objective:** We compared structured feature vectors with pretrained embeddings of rule-based patient narratives for predicting a treatment-switching proxy for TRD at the index antidepressant prescription.

**Methods:** This retrospective study included 42,579 patients with depression from one community health system. The outcome required at least 3 distinct antidepressant treatments, including the index agent, within 365 days. Clinical predictors were derived from a 730-day lookback window. We evaluated 4 classifiers on each representation using a shared 80:20 training and test split, with preprocessing and tuning confined to training data. Four embedding encoders were evaluated; Qwen3-Embedding-8B was primary. The pipelines used the same source records. We assessed discrimination, calibration, and paired bootstrap differences, and used concept permutation and neighbor retrieval to examine the predictive signal.

**Results:** The outcome occurred in 7,455 patients (17.5%). In 8,516 test patients, embedded logistic regression achieved a receiver operating characteristic area under the curve (ROC AUC) of 0.657 (95% CI 0.643--0.672), compared with 0.649 (95% CI 0.634--0.664) for feature-vector XGBoost. The post hoc difference between these leading models was 0.008 (95% CI −0.003 to 0.019). Embeddings improved logistic regression by 0.028 ROC AUC but reduced discrimination for the 3 tree ensembles by 0.013--0.022. Embedded logistic regression achieved ROC AUCs of 0.645--0.657 across encoders. Permuting psychiatric history produced the largest discrimination loss for the primary encoder (0.024--0.028 across classifiers); medication burden and prior treatment exposure also contributed. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003. Nearest-neighbor retrieval over the embedding stayed below both leading classifiers at every neighborhood size tested; its best ROC AUC was 0.625 (95% CI 0.610--0.641).

**Conclusions:** Narrative embeddings did not demonstrate superior discrimination over the strongest structured feature model for this treatment-switching proxy. Performance depended on the classifier, and neither pipeline established clinical utility. These findings support structured features as a practical benchmark and prioritize validation of the outcome, transportability, and clinical value before deployment.

Keywords: treatment-resistant depression; depression; electronic health records; machine learning; clinical prediction; text embeddings; antidepressants
