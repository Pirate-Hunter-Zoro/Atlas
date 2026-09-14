<!--
Section 3 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Introduction
-->

# Introduction
<!-- TRIPOD+AI 3a (background and rationale), 3b (objectives) -->

Major depressive disorder is among the most prevalent and disabling
medical conditions, and antidepressant pharmacotherapy is its
first-line treatment. A substantial minority of patients fail to achieve
remission despite successive adequate trials. These patients are
described as having treatment-resistant depression (TRD), most commonly
operationalized as the failure of at least two antidepressant trials of
adequate dose and duration [4]. The sequential-treatment evidence base,
anchored by the STAR\*D program, established that remission rates fall
sharply with each successive treatment step. Patients who move into a
third or fourth step face a markedly lower probability of recovery [5].
TRD accordingly accounts for a disproportionate share of the clinical
morbidity, functional impairment, and health-care cost attributable to
depression [1].

Escalation options become both more necessary and less likely to succeed
as resistance develops. There is therefore longstanding interest in
identifying, as early as possible, which patients are at high risk of
progressing to TRD. If such patients could be flagged at the point of
their index antidepressant prescription, clinicians could in principle
monitor them more closely and escalate sooner.

An electronic health record (EHR) does not say whether a patient got better,
and rarely says whether a drug was given long enough at a high enough dose to
count as a fair trial. What it does record is which antidepressants were
prescribed and when. So studies define TRD from the prescription sequence
itself, which is what makes a cohort of tens of thousands possible at all. A
sequence is not proof of failure. A patient may be switched because the drug
did not work, or because it was not tolerated, or because they stopped taking
it. And the rule is not fixed: research groups count treatments, minimum
durations, switches and augmentations differently, and changing the rule
changes both how many patients count as TRD and which ones [6-8].

Others have already tried to predict TRD from what an EHR records, and the
numbers they report vary far more than the methods do. One study of 35,246
adults reported a ROC AUC of 0.83 [9]. A model that was validated on a second
health system reached 0.652 [10]. Adding clinical notes to structured fields
reached 0.728 at a single site [11]. And in a three-system study, figures of
0.58 to 0.64 inside the site that built the model fell to 0.51 to 0.58 when it
was tested elsewhere [12]. The spread comes from how each study defined TRD,
how far ahead it predicted, and whether it was ever tested outside the site it
was built in, so there is no single figure to beat. Two things survive the
variation. Structured EHR fields carry real signal, and the sharpest drops come
at the point where a model meets a health system it was not built on
[8,10-12].

Two questions about how to use such a record motivate this study, and they are
the two the paper answers. The first is representational. Predicting clinical
outcomes with large, purpose-built EHR foundation models requires data and
compute at scales most groups cannot reach [13,14]. Serializing an EHR into
text and applying general-purpose language-model embeddings is a
computationally efficient alternative that has proved competitive across
clinical prediction tasks [15]. It has not been compared directly against a
transparent, hand-crafted feature vector for TRD prediction. The comparison
matters because the two are not equally auditable. A feature vector can be
read, and a 4,096-dimensional embedding cannot, so a gain in discrimination is
the only thing that would pay for the loss of interpretability.

The second question concerns prediction by analogy. A recurring proposal in
precision psychiatry is that a patient's likely course can be read off the
recorded courses of the patients most similar to them, an idea usually
described as a clinical digital twin. An embedding makes that proposal directly
testable, because similarity in the embedding space is a defined quantity and
the neighbors it selects have observed outcomes. If the premise holds,
retrieving a patient's closest analogues and averaging their outcomes should
predict well. Whether it does, and how it compares with fitting a model to the
same representation, has not been established for TRD.

One thing is true of both questions and bounds both answers, so we state it
here rather than leaving it to be inferred. **The patient data were hand-picked in both arms.** Serializing a record
and embedding it is often read as a way to stop choosing features, and
that is not what happens here. Neither answer below is evidence about
what a model would do with a raw record, because neither arm was given
one.

Embedding a whole untailored record would be the interesting version of
that, and this study does not attempt it. The obstacle is input length
rather than principle.

This study evaluated whether EHR-derived patient data can predict this
prescription-sequence definition of TRD within one year, and addressed
the two objectives in order. To ensure methodological transparency and
facilitate rigorous appraisal, we report it in full accordance with the
TRIPOD+AI reporting guideline for clinical prediction models developed
with regression or machine-learning methods [3]. First, we compared a
transparent typed feature vector against generalized pretrained
transformer embeddings of patient narratives, evaluating both with four
standard classifiers on an identical cohort and held-out split. We
repeated that comparison across four encoders and located the embedded
signal with a semantic-feature ablation that permutes individual
clinical concepts. Second, we tested nearest-neighbor retrieval over the
same embedding against a random-retrieval control, and against the
trained classifiers themselves. Field by field, what each representation
receives is documented in Supplement S8.
