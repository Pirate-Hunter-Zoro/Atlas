<!--
Section 24 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S10 Representation Field Crosswalk
-->

# S10 Representation Field Crosswalk

Table S13 documents how the pipelines encode each source field, based on scripts/data_loading/feature_vector.py and scripts/data_loading/deterministic_narrative.py. It distinguishes shared information from differences in field content and resolution.

Fields were available by the index date. Clinical content used the 730-day lookback, while recorded history length summarized the longer pre-index record and index date identified the prediction date. Neither representation used post-index clinical data.

Table S13. Field-level crosswalk. Asymmetric marks a row where the two representations do not receive the same information. Missing-value rules are as implemented, not as intended.

  **Source field**                        **Feature-matrix encoding**              **Narrative rendering**                           **Missing-value rule**                                                                   **Parity**
  --------------------------------------- ---------------------------------------- ------------------------------------------------- ---------------------------------------------------------------------------------------- ----------------------------------
  MDD recurrence, severity                two categorical columns                  Condition: MDD (recurrence, severity)             empty string is a level in both                                                          matched
  Index date                              no column                                Index date: YYYY-MM-DD                            never missing                                                                            asymmetric
  Lookback window width                   no column (constant)                     Baseline window: −730\...0 days                   never missing                                                                            matched (carries no information)
  MDD-to-index gap                        mdd_to_anchor_days, float                MDD-to-anchor gap: N days                         never missing                                                                            matched
  Encounter count in window               num_encounters, float                    Encounters in window: N                           never missing                                                                            matched
  MDD inside lookback window              mdd_within_window, boolean               MDD within window: Present/Absent                 never missing                                                                            matched
  Recorded pre-index history length       pre_anchor_history_days, float           not rendered                                      never missing                                                                            asymmetric
  Age                                     AgeInYears, float                        AgeInYears: N                                     never missing                                                                            matched
  Sex                                     categorical                              Sex: X                                            absent value becomes its own one-hot level; narrative prints the raw token               matched
  Race / ethnicity                        categorical, seven levels                Race_Ethnicity: X                                 own one-hot level; narrative prints raw token                                            matched
  Preferred language                      categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Marital status                          categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Religion                                categorical, collapsed to five levels    raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Smoking status                          categorical, collapsed to three levels   raw Epic value                                    own one-hot level                                                                        asymmetric (finer in narrative)
  Sexual orientation                      no column                                SexualOrientation: X                              rendered as the literal token nan when recorded-but-empty                                asymmetric
  Social determinants of health           nine boolean columns                     SDOH: list of present categories only             absence is an explicit False in the matrix, an omission from the list in the narrative   matched in content
  BMI, systolic BP, diastolic BP          dropped at load                          BMI: N \| BP (mean): S/D, or Missing              dropped, so no rule; narrative prints Missing                                            asymmetric
  Psychiatric comorbidity (8 flags)       eight boolean columns                    ARM: Present/Absent for all eight                 never missing                                                                            matched
  Suicidality flag                        boolean                                  SUICIDE FLAG (2y): Present/Absent                 never missing                                                                            matched
  Substance-use specifics (10)            ten boolean columns                      names of present substances only                  absence explicit in matrix, omitted in narrative                                         matched in content
  General medical comorbidity (4)         four boolean columns                     ARM: Present/Absent for all four                  never missing                                                                            matched
  Prior adequate AD trials                five per-class trial counts                Prior adequate AD trials: CLASS: n for all five   never missing                                                                            matched
  Benzodiazepine days                     benzo_days_coverage, float               Benzodiazepine days (2y): N                       never missing                                                                            matched
  Hypnotics                               hypnotics_burden, count only             count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  Active medications                      polypharmacy_count, count only           count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  NSAIDs                                  nsaid_count, count only                  count plus ingredient names                       never missing                                                                            asymmetric (finer in narrative)
  Psychiatric inpatient days, ED visits   two float columns                        Psych inpatient days: N \| ED psych visits: N     never missing                                                                            matched
  Prescribing-safety comorbidity (2)      two boolean columns                      ARM: Present/Absent                               never missing                                                                            matched

Eleven rows are asymmetric. Ten provide additional or finer information to the narrative, including index date, sexual orientation, vital signs, 4 sociodemographic categories, and 3 medication blocks. Recorded history length is available only to FEATURE. The primary comparison therefore cannot isolate encoding from information content.

FEATURE retains categorical missingness as explicit levels. Its primary vital-sign fields were dropped rather than imputed; narratives retained measured values or missing-value tokens. The raw sexual-orientation token nan is a further implementation-specific exception to the general missing-value convention.

A sensitivity analysis added vital signs to FEATURE using missingness indicators and within-fold median imputation and added recorded history length to the narratives. The best-model contrast was reported to remain nonsignificant. These changes address selected asymmetries, not all differences listed above. Quantitative results are not included here and are available from the corresponding author.
