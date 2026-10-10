<!--
Section 22 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: S8 Training and Test Characteristics
-->

# S8 Training and Test Characteristics

Table S9 compares selected characteristics in the shared training and test split.

Across 100 predictor rows, maximum absolute SMD was 0.036. The largest value involved a social-determinant flag present in 22 training patients and no test patient. Outcome rates match because the split was stratified.

Table S9. Held-out patients against training patients on the characteristics reported in Table 1. Continuous variables are median (IQR); categorical and boolean entries are n (%). SMD is training minus held-out, in pooled standard deviations. Vital signs are shown because they describe the cohort, but they are rendered only in the narrative representation and are absent from the feature matrix as published (Supplement S10).

  **Characteristic**                      **Training**       **Held-out**       **SMD**
  --------------------------------------- ------------------ ------------------ ---------
  Demographics                                                                  
  Age (years)                             55 (38-70)         55 (38-70)         -0.014
  Age band: 18-29                         4,428 (13.0%)      1,085 (12.7%)      +0.008
  Age band: 30-44                         7,198 (21.1%)      1,827 (21.5%)      -0.008
  Age band: 45-64                         10,632 (31.2%)     2,636 (31.0%)      +0.006
  Age band: 65+                           11,805 (34.7%)     2,968 (34.9%)      -0.004
  Sex: Female                             24,682 (72.5%)     6,168 (72.4%)      +0.001
  Race: White/Caucasian                   27,244 (80.0%)     6,835 (80.3%)      -0.007
  Race: Black/African American            1,894 (5.6%)       474 (5.6%)         -0.000
  Race: Am. Indian/Alaska Native          1,637 (4.8%)       396 (4.7%)         +0.007
  Race: Missing                           247 (0.7%)         50 (0.6%)          +0.017
  Language: English only                  33,698 (98.9%)     8,425 (98.9%)      -0.000
  Depression phenotype                                                          
  MDD recurrence: Recurrent               9,036 (26.5%)      2,177 (25.6%)      +0.022
  MDD severity: Severe                    1,818 (5.3%)       468 (5.5%)         -0.007
  MDD severity: Moderate                  5,807 (17.0%)      1,426 (16.7%)      +0.008
  Psychiatric and substance comorbidity                                         
  Suicidality flagged                     1,392 (4.1%)       361 (4.2%)         -0.008
  Anxiety disorder                        17,975 (52.8%)     4,426 (52.0%)      +0.016
  Substance use disorder (any)            7,472 (21.9%)      1,793 (21.1%)      +0.021
  Insomnia                                7,452 (21.9%)      1,898 (22.3%)      -0.010
  PTSD                                    1,241 (3.6%)       300 (3.5%)         +0.006
  Alcohol use disorder                    1,523 (4.5%)       352 (4.1%)         +0.017
  Medical comorbidity                                                           
  High cholesterol                        12,591 (37.0%)     3,156 (37.1%)      -0.002
  Uncontrolled hypertension               12,544 (36.8%)     3,136 (36.8%)      +0.000
  Vital signs (narrative only)                                                  
  BMI                                     29 (25-35)         29 (25-35)         -0.013
  Systolic BP                             126 (118-136)      126 (118-136)      -0.010
  BMI: not recorded                       7,484 (22.0%)      1,911 (22.4%)      -0.011
  Treatment and utilization                                                     
  Active med count                        1 (0-2)            1 (0-2)            +0.008
  Encounter count                         21 (8-46)          20 (8-47)          -0.001
  Pre-index history (days)                1792 (1213-2547)   1797 (1222-2541)   +0.004
  Prior adequate AD trial (any class)     5,014 (14.7%)      1,262 (14.8%)      -0.003
  Benzodiazepine days recorded            3,775 (11.1%)      949 (11.1%)        -0.002
  Hypnotic recorded                       1,319 (3.9%)       342 (4.0%)         -0.007
  Augmentation therapy used               326 (1.0%)         96 (1.1%)          -0.017

The measured balance supports internal comparability. It does not establish distributional identity or representativeness of the health system, because both partitions inherit the same sampling design.
