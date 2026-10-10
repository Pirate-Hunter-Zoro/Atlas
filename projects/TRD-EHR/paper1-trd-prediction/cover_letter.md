<!--
DRAFT cover letter for journal submission (editor-facing, NOT for the
coauthor circulation). Title and every number follow manuscript.md; when the
manuscript changes, this letter is checked against its Abstract.

Two fields are filled with the best available answer and are worth a
glance before the letter actually goes out:

  Date    - a placeholder the owner sets on the day the letter is sent.
            Until then it carries the date of the current draft.
  Address - "The Editors / JMIR Mental Health", because the current
            editor's name was not verified. If someone confirms it on the
            journal site, a name is better. A WRONG name is worse than
            none, so do not guess one: the salutation is "Dear Editor,"
            either way and is standard and safe on its own.

The IRB/ethics position and the funder were settled by coauthor feedback
and are stated below in the same terms as the manuscript's Ethical
Considerations and Funding sections: secondary analysis of de-identified
data without direct identifiers, not subject to IRB approval; funded by the
William K. Warren Foundation. Hard line breaks (a trailing backslash) keep
the addressee and signature on separate lines.

Also handled in the submission portal rather than here: suggested
reviewers, article type, and any fee-waiver request.

Build with: rebuild (see the repository README)
-->

6 October 2026

The Editors\
JMIR Mental Health

Dear Editor,

We are pleased to submit our original research manuscript,
**"Feature Vectors and Narrative Embeddings for Predicting a Treatment
Switching Proxy for Treatment Resistant Depression: Retrospective Cohort
Study,"** for consideration in *JMIR Mental Health*.

The study asks whether pretrained embeddings of template-generated patient
narratives predict a treatment-switching proxy for treatment-resistant
depression (TRD) better than structured feature vectors built from the same
electronic health records (EHRs). Prediction is made at the index
antidepressant prescription.

In 42,579 patients from one community health system, narrative embeddings
did not demonstrate superior discrimination over structured feature vectors.
Embedded logistic regression reached a receiver operating characteristic area under the curve (ROC AUC) of 0.657 (95% CI
0.643–0.672). Feature-vector XGBoost reached 0.649 (95% CI 0.634–0.664).
Their paired difference was 0.008 (95% CI −0.003 to 0.019). The classifier
changed the result: embeddings improved logistic regression and reduced
discrimination for all three tree ensembles. Logistic regression led the
embedded models on all four encoders, at 0.645 (95% CI 0.629–0.660) to 0.657
(95% CI 0.643–0.672).

The predictive signal came from familiar clinical history. Permuting
psychiatric history caused the largest loss, and medication burden and
prior treatment also contributed. Permuting race/ethnicity or social
determinants changed ROC AUC by no more than 0.003, and every such interval
included zero. Nearest-neighbor retrieval over the embedding showed that
proximity tracks outcome risk, but it stayed below both leading classifiers
at every neighborhood size from 1 to 34,063, for all four encoders. Its
maximum for Qwen3-Embedding-8B at similarity exponent 1, 0.625 (95% CI
0.610–0.641), was read at a
size chosen on the test patients. Randomly chosen neighbors stayed at
chance, at most 0.500 (2.5th–97.5th percentile across 1,000 draws
0.484–0.515).

We are explicit that the outcome is a treatment-switching proxy rather than
confirmed treatment resistance, that validation is internal, and that the
subgroup analyses do not establish equitable performance. Both
representations encode the same hand-selected predictors, so the comparison
says nothing about embedding an unselected record. We think the
results give a practical structured-feature benchmark for EHR embedding
pipelines, and a clear case for validating the outcome before deploying
either approach.

This work is reported in accordance with the **TRIPOD+AI** guideline for
the reporting of clinical prediction models that use regression or
machine learning methods; a completed TRIPOD+AI checklist is included
with this submission.

We confirm that this manuscript describes original work, is not under
consideration for publication elsewhere, and that all listed authors
have read and approved the submission. The EHR data are not publicly
shareable; the full analysis code is available at
https://github.com/Pirate-Hunter-Zoro/Atlas/tree/main/projects/TRD-EHR. Ethics/IRB, funding,
and conflict of interest statements are provided in the manuscript's
Ethical Considerations, Funding, and Conflicts of Interest sections: no
conflicts of interest are declared; the work was funded by the William K. Warren Foundation, with no other funding source; and
the study is a secondary analysis of de-identified data and is therefore
not human-subjects research subject to institutional review board
approval. All analysis was performed on local institutional hardware with
a de-identified extract without direct identifiers, with
no patient data transmitted to any external or commercial service.

Thank you for considering our work.

Sincerely,

Mikey Ferguson, BS\
Laureate Institute for Brain Research\
6655 South Yale Avenue, Tulsa, OK 74136, United States\
mferguson\@laureateinstitute.org\
on behalf of all authors
