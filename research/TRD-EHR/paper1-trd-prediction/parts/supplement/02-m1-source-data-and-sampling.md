<!--
Section 2 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M1 Source Data and Sampling
-->

# M1 Source Data and Sampling

The study used a single de-identified extract from the Epic EHR of Saint Francis Health System. Seven files were delivered: person, encounter, diagnosis, medication, procedure, and laboratory/flowsheet tables together with a medication-to-RxNorm mapping table. The clinical tables originated from the Caboodle enterprise data warehouse; the RxNorm mapping originated from the Clarity reporting database. Body mass index and systolic and diastolic blood pressure were obtained from the laboratory/flowsheet table. Each table was delivered as a flat file after patient and encounter keys had been replaced by one-way MD5 hashes, and was transferred by secure file transfer protocol. No names, medical record numbers, direct identifiers, or dates of birth were included.

The delivering data team restricted the person table to one administrative division of the health system and to patients who were current, valid, non-test, non-historical, not recorded as deceased, and aged 18-110 years at extraction. Eligible source encounters were completed on or before the extraction date, had at least one associated diagnosis, and had an inpatient, outpatient, observation, or emergency patient class.

Investigators prespecified the diagnosis code lists. Depression comprised ICD-9 codes 296.2, 296.3, 300.4, and 311 or ICD-10 codes F32.\*, F33.\*, and F34.1. Bipolar disorder comprised ICD-9 codes 296.0 and 296.4-296.8 or ICD-10 codes F30.\* and F31.\*. Schizophrenia-spectrum disorders comprised ICD-9 codes 295.\* and 298.\* or ICD-10 codes F20.\*, F23.\*, F25.\*, F28.\*, and F29.\*.

The extract was assembled as a case-enriched sample. All patients with a depression diagnosis on the problem list were retained, and a random sample of patients without that flag was added at an approximate 4:1 unflagged-to-flagged ratio; the remaining tables were then linked to the person table. The delivered extract included 501,718 patients: 100,420 (20.0%) with and 401,298 (80.0%) without a problem-list depression flag.

Sampling used problem-list flags, whereas eligibility used encounter diagnoses. Of 42,579 eligible patients, 12,530 (29.4%) lacked the problem-list flag and entered through the randomly sampled group. The analytic cohort therefore does not enumerate all patients with depression in the health system. Its outcome and subgroup frequencies are sample descriptions, not population prevalence estimates. Both representations were evaluated in the same sampled patients.

The setting is a single community health system in Tulsa, Oklahoma, serving inpatient, outpatient, observation, and emergency care. Patients enter the cohort through routine antidepressant prescribing across those settings rather than through psychiatric specialty referral, and the index prescription may be written in any of them.

Analyses used data version DV260629v1 and patient version PV260710v1. Source files were extracted June 29, 2026; analysis-ready tables were created July 10, 2026. No later refresh entered the study.
