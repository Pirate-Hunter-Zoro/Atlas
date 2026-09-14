<!--
Section 2 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Abstract
-->

# Abstract
<!-- TRIPOD+AI 2 (structured abstract); JMIR structured format -->

**Background.** As many as 1 in 3 patients with major depressive disorder (MDD)
progress to treatment-resistant depression (TRD) after failing successive
antidepressant trials [1]. An electronic health record (EHR) can be given to a
model as a typed feature vector, or written out as text and encoded by a
pretrained transformer, and the two have not been compared. A third approach
predicts a patient from the outcomes of their closest analogues, the premise
behind clinical digital twins.

**Objective.** Two questions on one cohort. Whether a generalized pretrained
transformer embedding of a patient narrative outperforms a typed feature vector
for predicting a treatment-switch–defined EHR proxy for incident TRD, and
whether nearest-neighbor retrieval over that embedding predicts as well as a
trained classifier. In both arms the patient data were hand-picked before
either representation was built, which bounds both answers.

**Methods.** Retrospective cohort of 42,579 adults with unipolar MDD from one
community health system. Following Forthman et al [2], TRD was 3 or more
antidepressant treatments within 1 year of the index date, the earliest
antidepressant prescription after a documented depression diagnosis; predictors
came only from the 730 days before it. Two representations were built from the
same hand-picked fields: a typed feature vector, and a Markdown narrative
written by fixed rules with no generative model, encoded by a pretrained
sentence-transformer (4 encoders; primary `Qwen3-Embedding-8B`). Four
classifiers were tuned by cross-validated grid search and scored on one held-
out stratified 20% split (8,516 patients, 1,491 TRD-positive). A retrieval
predictor scored each patient as the weighted mean TRD rate of 50 retrieved
training patients under 4 retrieval schemes. A semantic-feature ablation
shuffled each narrative concept across patients in turn to locate the embedded
signal. Reporting follows TRIPOD+AI [3].

**Results.** The embedding did not outperform the feature vector: ROC
AUC 0.657 (95% CI 0.643–0.672) against 0.649 (0.634–0.664), paired
difference +0.008 (−0.003 to +0.019). Holding the classifier fixed, it
helped logistic regression (+0.028) and hurt all 3 tree ensembles
(−0.013 to −0.022). Discrimination stayed within 0.012 across 4
encoders. The ablation localized the signal to psychiatric history,
medication burden and prior treatment exposure rather than to
sociodemographic fields. Retrieval was informative, not competitive:
nearest 0.594 (0.578–0.610) against random 0.499 on all 4 encoders, yet
0.063 short of the trained classifier on intervals that do not overlap.

**Conclusions.** Embedding matched, but did not exceed, a feature vector built
from the same fields, and retrieval over that embedding lost to a fitted model.
Both arms encode the same hand-picked inventory, so neither result shows that
embedding removes the feature engineering. Discrimination near 0.65 is too
modest for clinical use, and the outcome is a treatment-switch phenotype rather
than verified non-response.

**Keywords.** treatment-resistant depression; major depressive disorder;
electronic health records; clinical prediction model; machine learning; text
embeddings; nearest-neighbor retrieval; feature engineering; TRIPOD+AI.
