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

**Results:** The outcome occurred in 7,455 patients (17.5%, 95% CI 17.2--17.9). In 8,516 test patients, embedded logistic regression achieved a receiver operating characteristic area under the curve (ROC AUC) of 0.657 (95% CI 0.643--0.672), compared with 0.649 (95% CI 0.634--0.664) for feature-vector XGBoost. The post hoc difference between these leading models was 0.008 (95% CI −0.003 to 0.019). Embeddings improved logistic regression by 0.028 (95% CI 0.017--0.039) but reduced discrimination for the 3 tree ensembles, by 0.013 (95% CI 0.001--0.026) to 0.022 (95% CI 0.011--0.033). Across encoders, embedded logistic regression reached 0.645 (95% CI 0.629--0.660) to 0.657. Permuting psychiatric history produced the largest loss for the primary encoder, 0.024 (95% CI 0.010--0.036) to 0.028 (95% CI 0.017--0.039) across classifiers; medication burden and prior treatment exposure also contributed. Permuting race/ethnicity or recorded social determinants changed ROC AUC by no more than 0.003, and every such interval included zero. Nearest-neighbor retrieval, scored at every neighborhood size from 1 to 34,063, stayed below both leading classifiers at every size. Its maximum, 0.625 (95% CI 0.610--0.641) for logistic-regression-weighted retrieval, was read at a size chosen on the test patients and is optimistic. Randomly chosen neighbors stayed at chance, at most 0.500 (2.5th--97.5th percentile across draws 0.484--0.515).

**Conclusions:** Narrative embeddings did not demonstrate superior discrimination over the strongest structured feature model for this treatment-switching proxy. Performance depended on the classifier, and neither pipeline established clinical utility. These findings support structured features as a practical benchmark. Before either pipeline is used in care, 3 things need testing: whether the switching label reflects true treatment resistance, whether the models work in other health systems, and whether their predictions improve clinical decisions.

Keywords: treatment-resistant depression; depression; electronic health records; machine learning; clinical prediction; text embeddings; antidepressants
