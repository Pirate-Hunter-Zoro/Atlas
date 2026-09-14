<!--
Section 4 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M4. Predictor selection and the typed feature representation
-->

# Supplement M4. Predictor selection and the typed feature representation

The candidate predictor set was specified before model fitting and before
predictor-outcome associations were examined. The approach followed manual
clinical and literature-based selection, as in the treatment-resistance model
of Perlis [18], rather than univariate screening or automated selection. No
variable was retained or removed because of its observed association with
TRD, and no automated selection step ran at any stage.

The selected domains reflect prior treatment-resistance and
antidepressant-response research: depression severity and recurrence;
psychiatric and substance-use comorbidity, medical comorbidity, prior
antidepressant exposure and medication burden, health-care utilization, and
sociodemographic characteristics [18,19]. Unlike clinical-trial studies that
use scheduled symptom scales and structured interviews, this study is
restricted to structured fields recorded in routine EHR care, so depression
severity enters as diagnostic coding rather than as a rating-scale score.
Prior EHR prediction studies informed the feasible domains [20,21].

Prescribing-constraint flags were retained because they describe whether
escalation options may be limited. Sociodemographic and social-determinant
fields were retained so that their direct contribution could be tested by the
semantic-feature ablation rather than rendered unobservable by design. The
only prespecified fields later removed were body mass index and systolic and
diastolic blood pressure, for the missingness reasons in Supplement M6 rather
than because of any association with the outcome.

FEATURE assigns an explicit type to every field. Quantitative counts and
durations are continuous, including encounter count, pre-index history
length, age, per-agent adequate-trial counts, and medication burden. Single
binary flags and multi-label indicator sets are boolean, including
psychiatric and medical comorbidity, prescribing constraints, substance-use
categories, and social-determinant categories. Single-valued nominal
variables are categorical, including sex, preferred language, marital status,
religion, smoking status, race/ethnicity, MDD recurrence, and coded MDD
severity. An adequate prior antidepressant trial requires at least 42 days of
continuous exposure to an agent. The complete predictor inventory, with each
field's type and encoded form, is Multimedia Appendix 1.
