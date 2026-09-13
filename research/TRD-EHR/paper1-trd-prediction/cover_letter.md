<!--
DRAFT cover letter for journal submission (editor-facing, NOT for the
coauthor circulation). Title, corresponding author, COI, and funding
filled 2026-08-05.

No placeholders remain. Two fields are filled with the best available
answer and are worth a glance before the letter actually goes out:

  Date    - carries the date this draft was finalized. Reset it to the day
            of submission.
  Address - "The Editors / JMIR Mental Health", because the current
            editor's name was not verified. If someone confirms it on the
            journal site, a name is better. A WRONG name is worse than
            none, so do not guess one: the salutation is "Dear Editor,"
            either way and is standard and safe on its own.

The IRB/ethics position and the funder were settled by coauthor feedback
2026-08-17 and are stated below in the same terms as the manuscript
Declarations: secondary analysis of de-identified data, not subject to
IRB approval; funded by the William K. Warren Foundation.

Also handled in the submission portal rather than here: suggested
reviewers, article type, and any fee-waiver request.

Build with: rebuild (see the repository README)
-->

30 August 2026

The Editors
JMIR Mental Health

Dear Editor,

We are pleased to submit our original research manuscript,
**"Typed Feature Vectors, Generalized Pretrained Transformer Embeddings of
Deterministic Patient Narratives, and Nearest-Neighbor Retrieval for Predicting
a Treatment-Switch–Defined Electronic Health Record Proxy for Treatment-
Resistant Depression: Retrospective Cohort Study,"** for
consideration in *JMIR Mental Health*.

This study asks whether routinely collected electronic health record
(EHR) data can predict a treatment-switch–defined EHR proxy for
treatment-resistant depression (TRD) at the point of a patient's index
antidepressant prescription. It makes two points, and the manuscript is organized around them.

The first is that writing the record out as text and embedding it with a
general-purpose transformer does not beat a transparent typed feature
vector built from the same record. In a cohort of 42,579 patients the
paired difference between the two best models is +0.008 ROC AUC (95% CI
−0.003 to +0.019), and the result holds across four encoders. The
comparison is nevertheless not a simple tie: the embedding significantly
helps logistic regression and significantly hurts all three tree
ensembles, so representation and learner are one design choice rather
than two.

The second is that predicting a patient from their nearest neighbors in
that embedding — the clinical digital-twin premise — recovers real
signal and still loses decisively to a model fitted on the same
representation. Nearest retrieval reaches 0.594 against 0.499 for random
retrieval and 0.432 for farthest retrieval, which establishes that
proximity in the embedding tracks TRD risk. It nevertheless falls 0.063
ROC AUC short of the trained classifier, on intervals that do not
overlap, and that shortfall reproduces on every encoder tested.

One thing is true of both results and bounds both, and the manuscript stresses
it rather than leaving it to be inferred: in both arms the patient data were
hand-picked. Predictor selection ran once, before either representation
existed, and the narrative the encoder reads is a fixed template over that same
selection. Serialize-and-embed is often recommended as a way to stop choosing
features, and a reader arriving at a parity result with that expectation will
read it as "the embedder did as well with no feature engineering". The
engineering was relocated, not removed, and a whole untailored record was never
embedded. Supplement S10 is the field-by-field evidence.

Discrimination is modest throughout (ROC AUC ≈ 0.65)
and the predictive signal localizes to clinical content, psychiatric history
and medication burden, rather than to the sociodemographic fields supplied to
the models. Subgroup discrimination and calibration are reported across
eight strata with multiplicity control. We are explicit throughout that
the target is a treatment-switch proxy rather than measured
non-response, that the study is an internal validation by a single
random split, and that it reports no fairness assessment. A Limitations
section states these and seven others in order of how much they bound
the conclusions.

This work is reported in accordance with the **TRIPOD+AI** guideline for
the reporting of clinical prediction models that use regression or
machine learning methods; a completed TRIPOD+AI checklist is included
with this submission.

We confirm that this manuscript describes original work, is not under
consideration for publication elsewhere, and that all listed authors
have read and approved the submission. The EHR data are not publicly
shareable; the full analysis code is available at
https://github.com/Pirate-Hunter-Zoro/TRD-EHR. Funding, conflict
of interest, and ethics/IRB statements are provided in the manuscript's
Declarations: no conflicts of interest are declared; the work was funded
by the William K. Warren Foundation, with no other funding source; and
the study is a secondary analysis of de-identified data and is therefore
not human-subjects research subject to institutional review board
approval. All analysis was performed on local institutional hardware with
a de-identified extract containing no protected health information, with
no patient data transmitted to any external or commercial service.

Thank you for considering our work.

Sincerely,

Mikey Ferguson, BS
Laureate Institute for Brain Research
6655 South Yale Avenue, Tulsa, OK 74136, United States
mferguson@laureateinstitute.org
on behalf of all authors
