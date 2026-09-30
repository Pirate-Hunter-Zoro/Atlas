<!--
Section 3 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Introduction
-->

# Introduction

Treatment-resistant depression (TRD) is commonly defined as inadequate response to at least 2 antidepressant trials of adequate dose and duration \[1\]. The probability of remission declines with successive treatment steps \[2\], and persistent depression carries substantial clinical and economic burden \[3\]. Identifying patients likely to experience a difficult treatment course could inform monitoring and follow-up. Clinical prediction studies suggest that relevant information is available, but reliable individual prediction remains challenging \[4-8\].

Electronic health records (EHRs) record diagnoses, prescribing, and health care use over time. They rarely establish why a medication was changed or whether an adequate trial failed. Consequently, EHR studies often define TRD through treatment sequences. These definitions identify observable care trajectories, and changes in the rules alter both outcome frequency and cohort composition \[9-11\]. A model predicting repeated switching therefore requires a more limited interpretation than one predicting symptom-confirmed treatment resistance.

Prior EHR models have reported widely varying discrimination. Internal performance as high as a receiver operating characteristic area under the curve (ROC AUC) of 0.83 contrasts with an externally validated estimate of 0.652 and cross-system estimates of 0.51--0.58 \[12-14\]. Combining structured records with clinical notes has improved performance in a smaller study \[15\]. These findings make the source and representation of information, the prediction time, and the validation setting central to interpreting any apparent advance.

General-purpose text encoders provide one way to represent an EHR without training a large clinical foundation model \[16-18\]. Structured fields can be converted into a patient narrative and then encoded as a numerical embedding for prediction. The practical question is whether this additional processing improves on a transparent feature vector. A narrative created from the same structured records adds no new measurement, although the encoding may organize existing information differently.

We asked whether pretrained embeddings of rule-based patient narratives improve prediction of a treatment-switching proxy for TRD beyond structured feature vectors at the index antidepressant prescription. We compared the pipelines in the same patients, using a common temporal design and test set. Secondary analyses examined whether performance depended on the classifier or encoder, which clinical domains contributed, and whether embedding similarity supported prediction.
