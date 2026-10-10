<!--
Section 5 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M4 Predictors and Structured Representation
-->

# M4 Predictors and Structured Representation

Predictor domains were selected clinically and from prior literature before model fitting or inspection of outcome associations \[5\]. No univariate screening or automated selection determined the source-field inventory; subsequent model regularization operated on the encoded predictors.

Domains included depression severity and recurrence, psychiatric and substance-use comorbidity, medical comorbidity, prior treatment, medication burden, utilization, and sociodemographic characteristics \[5-8\]. Severity was represented by diagnosis codes because standardized symptom scales were not available.

Prescribing-constraint flags described potential limits on treatment options. Sociodemographic and social-determinant fields were retained to evaluate their direct contribution by permutation. Body mass index and blood pressure were subsequently removed from FEATURE because of missingness (section M6).

FEATURE assigns explicit types to counts and durations, binary indicators, and nominal categories. Prior antidepressant trial counts required at least 42 continuous days of exposure; adequate dose was not established by this rule. Tables M2--M4 provide the 59 retained source fields and their expansion to 92 model columns.

After removal of 3 vital-sign fields, the inventory comprised 15 quantitative, 36 binary, and 8 categorical source fields. Categorical expansion produced 41 columns, for a total of 92. Display labels are those used in the original analyses.

Table M2. Quantitative predictors.

  **Predictor**
  -------------------------------------
  MDD history before index (days)
  History length (days)
  Encounter count
  ED visits (count)
  Inpatient days before index
  Age (years)
  Medications active at index
  Anti-inflammatories active at index
  Sleep meds active at index
  Anxiolytic days before index
  Bupropion trials (6+ wk)
  Mirtazapine trials (6+ wk)
  SNRI trials (6+ wk)
  SSRI trials (6+ wk)
  Vortioxetine trials (6+ wk)

Table M3. Binary predictors by domain.

  **Block**                             **Predictors**
  ------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Clinical flags (3)                    MDD in history; Suicidality; Augmentation therapy
  Psychiatric comorbidities (8)         Adjustment disorder; Anxiety disorder; Dysthymia (chronic depression); Insomnia; OCD; PTSD; Social anxiety disorder; Substance use disorder (any)
  Medical comorbidities (4)             Chronic pain; Diabetes; High cholesterol; Thyroid disorder
  Prescribing-constraint / safety (2)   Seizure disorder; Uncontrolled hypertension
  Substance use disorders (10)          Alcohol; Cannabis; Cocaine; Hallucinogen; Inhalant; Nicotine; Opioid; Other stimulant; Other substance; Sedative/hypnotic
  Social determinants of health (9)     Education or literacy issue; Employment issue; Housing or financial issue; Legal or criminal issue; Occupational hazard exposure; Family/support group issue; Psychosocial circumstances; Social environment issue; Upbringing issue

Table M4. Categorical fields and encoded levels.

  **Field**            **One-hot columns**   **Levels**
  -------------------- --------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------
  Sex                  1                     Male (Female = reference, dropped)
  Preferred language   6                     Asian/Pacific Islander; English; Other; Other Indo-European; Spanish; Missing
  Marital status       6                     Divorced; Never married; Married; Separated; Widowed; Missing
  Religion             6                     Catholic; Non-Christian; Orthodox; Other/Unknown; Protestant; Missing
  Smoking status       4                     Current; Former; Never; Missing
  Race/ethnicity       8                     American Indian/Alaska Native; Asian; Black/African American; Hispanic/Latino; Multi-race; Native Hawaiian/Pacific Islander; White/Caucasian; Missing
  MDD recurrence       4                     Unspecified; Single episode; Recurrent; Dysthymia (chronic depression)
  MDD severity         6                     Unspecified; Mild; Moderate; Severe; Psychotic; Remission
