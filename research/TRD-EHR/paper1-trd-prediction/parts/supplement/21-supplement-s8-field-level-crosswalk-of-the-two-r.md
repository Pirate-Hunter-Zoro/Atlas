<!--
Section 21 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement S8. Field-level crosswalk of the two representations
-->

# Supplement S8. Field-level crosswalk of the two representations

The head-to-head comparison in this paper is between two encodings of one
record, so it is only a comparison of encodings to the extent that both
encodings are given the same fields. This section is the field-by-field
accounting, and it does two jobs. **It bounds the null**, because the two representations do not render an
identical inventory: 11 of the 28 rows below are asymmetric,
and in 10 of them the narrative receives information the feature vector
does not. **And it is the evidence for a scope condition the main text states in its own
voice** (Methods, *Predictors and patient representations*; Discussion,
*Principal findings*). Every row here traces to a field that predictor
selection chose before either representation existed. The patient data were
hand-picked in both arms, and neither was handed a raw record. A reader who takes the null to mean that the embedding found structure
without being told where to look can check that against this table, row by row, and the
answer is in the second column.

***Table S9.** Field-level crosswalk. **Asymmetric** marks a row where the two
representations do not receive the same information. Missing-value rules are as
implemented, not as intended.*

| Source field | Feature-vector encoding | Narrative rendering | Missing-value rule | Match |
| --- | --- | --- | --- | --- |
| MDD recurrence, severity | two categorical columns | `Condition: MDD (recurrence, severity)` | empty string is a level in both | matched |
| Index date | **no column** | `Index date: YYYY-MM-DD` | never missing | **asymmetric** |
| Lookback window width | no column (constant) | `Baseline window: −730...0 days` | never missing | matched (carries no information) |
| MDD-to-index gap | `mdd_to_anchor_days`, float | `MDD-to-anchor gap: N days` | never missing | matched |
| Encounter count in window | `num_encounters`, float | `Encounters in window: N` | never missing | matched |
| MDD inside lookback window | `mdd_within_window`, boolean | `MDD within window: Present/Absent` | never missing | matched |
| Recorded pre-index history length | `pre_anchor_history_days`, float | **not rendered** | never missing | **asymmetric** |
| Age | `AgeInYears`, float | `AgeInYears: N` | never missing | matched |
| Sex | categorical | `Sex: X` | absent value becomes its own one-hot level; narrative prints the raw token | matched |
| Race / ethnicity | categorical, seven levels | `Race_Ethnicity: X` | own one-hot level; narrative prints raw token | matched |
| Preferred language | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Marital status | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Religion | categorical, **collapsed to five levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Smoking status | categorical, **collapsed to three levels** | **raw Epic value** | own one-hot level | **asymmetric (finer in narrative)** |
| Sexual orientation | **no column** | `SexualOrientation: X` | **rendered as the literal token `nan`** when recorded-but-empty | **asymmetric** |
| Social determinants of health | nine boolean columns | `SDOH:` list of present categories only | absence is an explicit False in the matrix, an omission from the list in the narrative | matched in content |
| BMI, systolic BP, diastolic BP | **dropped at load** | `BMI: N \| BP (mean): S/D`, or `Missing` | dropped, so no rule; narrative prints `Missing` | **asymmetric** |
| Psychiatric comorbidity (8 flags) | eight boolean columns | `ARM: Present/Absent` for all eight | never missing | matched |
| Suicidality flag | boolean | `SUICIDE FLAG (2y): Present/Absent` | never missing | matched |
| Substance-use specifics (10) | ten boolean columns | names of present substances only | absence explicit in matrix, omitted in narrative | matched in content |
| General medical comorbidity (4) | four boolean columns | `ARM: Present/Absent` for all four | never missing | matched |
| Prior adequate AD trials | five `trials_<class>` counts | `Prior adequate AD trials: CLASS: n` for all five | never missing | matched |
| Benzodiazepine days | `benzo_days_coverage`, float | `Benzodiazepine days (2y): N` | never missing | matched |
| Hypnotics | `hypnotics_burden`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| Active medications | `polypharmacy_count`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| NSAIDs | `nsaid_count`, **count only** | count plus **ingredient names** | never missing | **asymmetric (finer in narrative)** |
| Psychiatric inpatient days, ED visits | two float columns | `Psych inpatient days: N \| ED psych visits: N` | never missing | matched |
| Prescribing-safety comorbidity (2) | two boolean columns | `ARM: Present/Absent` | never missing | matched |

**What the crosswalk shows.** The imbalance is not symmetric, and it is
larger than a count of rows suggests. Eleven rows are asymmetric, and in
ten of them the narrative receives information the feature vector does
not. Two are fields it renders and the feature vector has no column for,
the index date and sexual orientation. One is the row of vital signs
dropped at load. Four are sociodemographic fields where the feature
vector collapses raw Epic values into coarse categories and the
narrative prints the raw token. Three are medication blocks where the
feature vector carries a count and the narrative names the ingredients.
The eleventh
runs the other way: recorded history length, which the narrative did not
render.

Two rules are worth stating because they are easy to assume wrongly. Missingness
is *not* silently imputed on the categorical side of the feature vector: an
absent value becomes its own one-hot level, so the model can use the fact of a
missing record. And the vital signs were dropped rather than imputed, so the published feature
arm never saw them in any form. The reason is mechanical rather than
principled: a numeric column carrying nulls cannot pass through the pipeline's
scaler.

The main text states the imbalance as a bound on the comparison (Methods,
*Predictors and patient representations*). This table is what makes that bound
checkable, row by row.
