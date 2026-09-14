<!--
Section 1 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M1. Source data, setting, and sampling frame
-->

# Supplement M1. Source data, setting, and sampling frame

The study used a single de-identified extract from the Epic EHR of Saint
Francis Health System. Seven files were delivered: person, encounter,
diagnosis, medication, procedure, and laboratory/flowsheet tables together
with a medication-to-RxNorm mapping table. The clinical tables originated
from the Caboodle enterprise data warehouse. The RxNorm mapping originated
from the Clarity reporting database. Body mass index and systolic and
diastolic blood pressure were obtained from the laboratory/flowsheet table.
Each table was delivered as a flat file after patient and encounter keys had
been replaced by one-way MD5 hashes, and was transferred by secure file
transfer protocol. No names, medical record numbers, direct identifiers, or
dates of birth were included.

The delivering data team restricted the person table to one administrative
division of the health system and to patients who were current, valid,
non-test, non-historical, not recorded as deceased, and aged 18-110 years at
extraction. Eligible source encounters were completed on or before the
extraction date, had at least one associated diagnosis, and had an
inpatient, outpatient, observation, or emergency patient class.

Investigators prespecified the diagnosis code lists. Depression comprised
ICD-9 codes 296.2, 296.3, 300.4, and 311 or ICD-10 codes F32.\*, F33.\*, and
F34.1. Bipolar disorder comprised ICD-9 codes 296.0 and 296.4-296.8 or
ICD-10 codes F30.\* and F31.\*. Schizophrenia-spectrum disorders comprised
ICD-9 codes 295.\* and 298.\* or ICD-10 codes F20.\*, F23.\*, F25.\*, F28.\*,
and F29.\*.

The extract was assembled as a case-enriched sample. All patients with a
depression diagnosis on the problem list were retained, and a random sample
of patients without that flag was added at an approximate 4:1
unflagged-to-flagged ratio. The remaining tables were then linked to the
person table. The delivered extract included 501,718 patients: 100,420
(20.0%) with and 401,298 (80.0%) without a problem-list depression flag.

Sampling used the problem list, whereas study eligibility used diagnoses
recorded at individual encounters. A depression code entered at a visit is a
documented diagnosis whether or not it was ever added to the problem list. In
routine care the problem list is frequently not updated, so the two sets
overlap without either containing the other. Of the 42,579
analysis-cohort patients, 12,530 (29.4%) qualified through an encounter-level
depression diagnosis despite lacking the problem-list flag and therefore
entered through the randomly sampled group. The analysis cohort is
consequently a sample, not an enumeration, of the health system's patients
with depression, and cohort TRD and subgroup proportions are not population
prevalence estimates. The paired comparison between representations remains
internally valid because both were evaluated in the same patients on the
same held-out split.

The setting is a single community health system in Tulsa, Oklahoma, serving
inpatient, outpatient, observation, and emergency care. Patients enter the
cohort through routine antidepressant prescribing across those settings
rather than through psychiatric specialty referral, and the index
prescription may be written in any of them.
