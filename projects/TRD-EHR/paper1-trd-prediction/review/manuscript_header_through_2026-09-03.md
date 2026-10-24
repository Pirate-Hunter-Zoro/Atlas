<!--
PRIOR MANUSCRIPT HEADER, PRESERVED VERBATIM.

This is the decision-record comment block that stood at the top of
manuscript.md up to and including the build of 2026-09-03, moved here
whole on 2026-09-06 when the manuscript was refocused on two main points
and its header was rewritten as a statement of the rules currently in
force. Nothing here was deleted; the rules that are still live were
carried forward into the new header, and this file is the archive of how
each of them was arrived at. Read it when the question is *why* a rule
exists rather than *what* the rule is.

Not part of the submitted packet.
-->

# Prior manuscript header (through 2026-09-03)

```text
Digital Twins: predicting treatment-resistant depression (TRD) from
EHR-derived patient representations.

Target venue: JMIR Mental Health. Reporting follows the TRIPOD+AI
checklist. Final form is Word (.docx): iterate here in Markdown, then
convert with `pandoc manuscript.md -o manuscript.docx` into the JMIR
template (writeup/JMIR_template.docx) at submission time.

All performance numbers are final and from the current pipeline run
(42,579-patient cohort, data version DV260629v1-PV260710v1,
Qwen3-Embedding-8B): classical-ML, cross-embedder, ablation, and the
neighbor-weighted results (Table 6, Figures 8-9). Cohort-characterization
numbers are from notebooks/figures/. NUMBERS RE-SYNCED 2026-07-31 to the
DV260629v1-PV260710v1 data overhaul (previous draft was on the superseded
9,724-patient cohort); several conclusions changed direction (embedded
now edges the feature vector; 8B is the top encoder; the embedded signal
is sparse not diffuse; EPV now exceeds the threshold).

Front matter (title page, abstract, keywords, Introduction) and
in-text citations were drafted 2026-07-31. In-text citation markers use
the numbered reference list at the end (order of first appearance).
Title, affiliations, and the operational TRD definition were supplied by
the authors 2026-08-05. The TRD label counts antidepressant treatments
(>=3 distinct agents within one year of the index date, i.e. >=2
post-index changes), and is NOT adequacy-verified, so the Outcome section states it
as a proxy for the consensus definition and Limitations item 2 covers the
consequences. Do not re-describe it as the consensus definition.

Reader-facing provisional notes and [PENDING]/[CONFIRM] markers were
removed 2026-08-14: the draft now reads as the final submitted paper.

NAMING OF THE TWO REPRESENTATIONS. There are exactly two, and they are
called the FEATURE representation ("feature vector", "typed feature
vector", "feature-vector XGBoost") and the EMBEDDED representation
("embedding", "embedded representation"). "Rule-based" is NOT an alias
for either and must not appear anywhere in the manuscript, supplement,
cover letter, or checklist — a third name for the feature
vector reads as a third method. Where the point is that no generative
model participates in narrative construction, the word is
"deterministic", which is what that sentence actually means. The title
carries the same rule ("Typed Feature Vectors Versus Generalized
Pretrained Transformer Embeddings of Patient Narratives ..."); it is
quoted in the cover letter and the checklist, so a title change has to be
propagated to all three.

THE SIX ABLATED CONCEPTS ARE DEFINED IN SUPPLEMENT M11, one paragraph each, by the narrative content the permutation
destroys. Keep the definitions there and keep them concrete: a
permutation result means nothing to a reader who cannot tell medication
burden (every active ingredient at the index date, any indication) from
treatment exposure (prior psychiatric pharmacotherapy). Two things that
fall out of those definitions and must not drift back: treatment
contraindications is a PRESCRIBING-SAFETY concept, not a
sociodemographic one, so the negligible-delta group is "the two
sociodemographic concepts, plus treatment contraindications" and never
"the sociodemographic permutations"; and general medical comorbidity is
a separate narrative section that was never permuted.

Coauthor feedback of 2026-08-17 RESOLVED the three items previously owed
by the authors, and all three are now written into the text:
- Outcome: the label is stated in the same wording as the operational
  definition of Forthman et al. (J Affect Disord 2025;390:119858, ref
  21) — TRD assigned to MDD patients with three or more antidepressant
  treatments within one year — and that paper is cited as the source of
  the definition. The switch-count restatement is kept as the equivalent
  arithmetic, not as the primary phrasing.
- Ethics: this is secondary analysis of de-identified data and is
  therefore not human-subjects research subject to IRB approval; there
  is no reviewing body, protocol number, or consent waiver to name.
- Funding: the William K. Warren Foundation, and no other funder.
Do NOT re-open these as pending.

MP REVIEW OF 2026-08-20 (tracked changes + 11 comments on the 2026-08-14
build; note that build PREDATED the 2026-08-17 coauthor edits above, so
MP's "two or more"->"three or more" edits were already satisfied and were
not re-applied). Applied to this draft:
- Abstract Background rewritten to MP's wording ("As many as 1 in 3",
  "Identifying", "structural elements of EHR data"). Abstract Results
  opens with MP's clearer sentence.
- Methods: data-source section rewritten per comment 30 against the
  "SFHS Dataset Query Documentation" provided 2026-08-20 (now kept at
  references/DATA_PROVENANCE_SFHS_query_documentation.docx) - it now
  names Epic/Caboodle/Clarity, the seven delivered tables, the hashing
  and SFTP transfer, the extract-level person and encounter filters, and
  the verbatim ICD-9/ICD-10 code lists behind the depression, bipolar,
  and schizophrenia flags. The two dates are confirmed from the
  filesystem, not inferred: the delivered tables are named
  *_Table-26_06_29-v1.tsv per the documented convention (source cut
  2026-06-29) and the PrepData tables were built 2026-07-10 by mtime.
  NOTE: Setting previously claimed the extract "spans the full system
  rather than any one service line". That was not accurate - the query
  filters to a single Epic service area - so the coverage claim was
  dropped rather than restated; Setting now simply lists the encounter
  types covered. Do not re-add a system-wide coverage claim.
  Also: new *Predictor selection* paragraph added per comment 44; the
  MNAR discussion cut to two sentences (comment 49); the
  preprocessing-leakage discussion cut from three paragraphs to one
  (comment 56).

COMMENT 44 IS CLOSED (2026-08-20) WITHOUT NEW LITERATURE. MP thought he
had sent the predictor-selection papers; the ~20-file batch he supplied
was checked in full and contains none - not one mentions
treatment-resistant depression or antidepressants. The provenance is
carried instead by references already in the list, anchored on Perlis
(#4), whose manual-review-then-prune selection strategy is the one this
study follows, with #5 Kautzky, #6 Sheu, #7 Chekroud supplying the
predictor domains. The paragraph also now states the substantive
difference from the trial-derived models: they had protocolized severity
instruments, we have diagnostic coding. No [CONFIRM] marker remains.

STUDY POPULATION / CASE-ENRICHED DESIGN (written up 2026-08-20). The
delivered extract is NOT a census of the service area: every patient with a
problem-list depression code was retained, and unflagged patients were added
at an approximate 4:1 ratio. This is INTENTIONAL case-control-style
enrichment, established by the extract's own query documentation, and it is
now written up as the study design in Methods > *Study population* -- NOT as
a limitation. There is deliberately no Limitations item for it; an earlier
draft had one and it was removed.
Verified against the data, not inferred: Person_Table.csv holds 501,718 rows
split 100,420 (20.0%) "Depression Group" / 401,298 (80.0%) "Control Group" in
its GroupType column. Cross-referencing GroupType against the 42,579 sliced
patient JSONs shows 12,530 (29.4%) of the analysis cohort arrived through the
sampled group -- because our eligibility reads ENCOUNTER diagnoses while the
extract's flag was built from the PROBLEM LIST.
The one interpretive consequence that IS stated: prevalence-type figures (the
outcome rate, the Table 2 subgroup proportions) describe this cohort, not the
source population. The representation comparison is untouched, since both
arms use the same patients on the same split. Do not describe 501,718 as a
"source population".
PROVENANCE: the source for all of the above is the SFHS dataset query
documentation held at references/DATA_PROVENANCE_SFHS_query_documentation
.docx. That is an internal LIBR working document and must NEVER be cited in
the paper -- state the design in prose, unreferenced.

REFS ADDED 2026-08-20 from MP's batch, appended not interleaved. They were
22-25 then and are 21-24 now, the numbers having shifted down by one when
Varma & Simon was dropped (see the 2026-08-21 round below): Shmatko
(Nature, Delphi-2M) and Waxler (CoMET) in the Introduction, to frame
event-sequence pretraining as the expensive alternative that
serialize-and-embed is competing with; Hegselmann 2024 (CHIL, LLM
patient summaries - NOT the same paper as #17) in Methods to justify the
deterministic renderer; Lee 2026 (LLM-as-a-judge reporting) in Methods to
pre-empt the obvious objection to the judge arm, by stating that the
judge supplies a WEIGHT inside an outcome-scored predictor rather than a
verdict standing in for human adjudication.
- Results: participant flow compressed. The *Provenance of performance
  results* section was RELOCATED to Methods > *Model development* as
  the "Evaluation coverage" paragraph, per comment 700 ("a lot of this
  is methods not results"); MP's own rewrite of its prose is preserved,
  recast into Methods voice. Subgroup-prevalence intro replaced with
  MP's rewrite; ablation paragraph replaced with MP's results-only
  version (comment 780).
- New Figure 2, a discrimination forest plot, per MP's inserted ASCII
  mock-up. ALL FIGURES RENUMBERED: old 2-11 are now 3-12. Generated
  2026-08-20 by scripts/pipeline/predictions/plot_discrimination_forest.py.
- Figure 2 revised 2026-08-21: the best-feature-vector-model dashed
  reference line was dropped ON RK'S SUGGESTION, and a second panel (2B)
  added carrying the PAIRED bootstrap difference in AUC between
  representations. The reference line only supported an eyeball overlap
  test; the paired difference is the actual test, and it is ~3x more precise. Two
  consequences for the text. The best-versus-best null is now stated
  outright rather than implied ("did not significantly outperform"), in
  Results, Discussion, Limitations item 6, and both halves of the
  Abstract. And the classifier-matched contrasts surfaced a NEW result
  not previously in the paper: the embedding significantly helps logistic
  regression (+0.028) and significantly hurts all three tree ensembles
  (-0.013 to -0.022), so overall parity is an interaction, not a tie.
  This corroborates the pre-existing "predictive structure is
  approximately linear" claim in the Discussion by a second route.
- Figure 6 (feature importance) relaid out one panel per row at 6in
  because the 2x2 grid made the labels unreadable (comment 776).
- Discussion: "This signal was sparse, not diffuse" unpacked (comment
  789). The *Fusing the farthest-retrieval signal* subsection was SPLIT
  (comment 793): its results and Figure 12 moved to a new Results
  subsection, *Fusing nearest and farthest retrieval*, and the
  Discussion carried interpretation only, as *Interpreting the fusion
  null*. BOTH of those were then removed from the main text on
  2026-08-21; see the round below. Do not restore them.
MARKUP ROUND OF 2026-08-21 (handwritten annotations on the built PDFs).
Applied in full:
- Attribution on Figure 2, settled 2026-08-21: the forest plot itself was MP's
  margin sketch (row 12 of the memo, which carried no comment number). Dropping
  the dashed best-feature-vector-model reference line from it was RK's separate
  suggestion, and the memo credits him under *What the forest plot changed
  about the claim*. Do not swap these two round again.
- FUSION ANALYSIS IS OUT OF THE MAIN TEXT. The Results subsection
  *Fusing nearest and farthest retrieval*, its Figure 12, and the
  Discussion subsection *Interpreting the fusion null* were all deleted.
  It lives in Supplement S7 only, reached by one pointer sentence at the
  end of Results > *Neighbor-weighted prediction* and one in *Future
  directions*. This supersedes the split made for MP's comment 793 and
  still satisfies it (no results in the Discussion, because there is no
  fusion subsection in the Discussion). Highest figure number is now 11;
  nothing renumbered, since Figure 12 was last.
  KNOCK-ON: ref 20 (Varma & Simon) was cited only from the deleted
  paragraphs, so it was dropped from the list and 21-25 renumbered to
  20-24, here and in the checklist. Supplement S7 cites it inline in full
  and carries no numbered list, so it needs no marker.
- The treatment-exposure ablation exclusion was WRONG as written. It
  claimed the section "partly restates the information used to construct
  the outcome label itself". It does not: the label counts post-anchor
  treatments and no predictor touches post-anchor data, so the section is
  pre-anchor exposure only. Do not re-describe the treatment-exposure
  section as label leakage. The concept was then permuted and the slate is
  SIX specifications, not five, as of 2026-08-22 — see below.
- THE ABLATION SLATE IS SIX SPECIFICATIONS, and treatment exposure is
  written up EXACTLY LIKE THE OTHER FIVE. It gets its listing in Methods,
  its row in Table 7 and Figure 10, its rank in the Results paragraph, and
  its name in the one-sentence Discussion summary. Nothing more. It was
  scored later than the others (2026-08-22) and that is deliberately absent
  from the text. Three framings were tried and REJECTED on 2026-08-21/22 —
  do not reintroduce any of them: (1) hedging it as post-hoc or "added
  after the primary analysis"; (2) a dedicated Discussion paragraph
  explaining why its delta is smaller than expected; (3) naming it in
  Limitations item 5, which is concept-neutral and stays that way.
  For the record, not for the text: it ranks third (LR -0.019, XGB -0.011,
  both intervals excluding zero; RF and GB include zero), behind
  psychiatric history and medication burden. Table 2 carries the five
  treatment-exposure rows as ordinary cohort characteristics — the section
  is populated for 24.0% of patients with an SMD of 0.001, which is the
  anchor definition showing through: the anchor is the first antidepressant
  prescription after a documented depression diagnosis, so most patients have
  no earlier antidepressant record at all.

  CORRECTION 2026-08-28: the anchor is NOT "the first adequate antidepressant
  exposure". Verified against scripts/data_loading/load_patient_data.py, which
  sorts post_mdd_ad_index.csv by MedStartInstant and keeps the earliest row per
  patient, and against the table itself (every candidate order starts on or
  after first_depression_dx_date; min gap 0 days, 57.9% same day). No adequacy,
  dose, or duration criterion enters anchor selection, which is why 14.7% of
  the cohort carries a pre-anchor course meeting the 42-day threshold. The
  anchor is named "the anchor prescription" or "the first antidepressant
  prescription recorded on or after a documented depression diagnosis"
  throughout, and Methods > *Participants and eligibility* carries the full
  algorithmic definition under **Anchor selection**. Do not reintroduce
  "first adequate antidepressant exposure" anywhere. Computed from feature_vectors.parquet joined to IDs-TRD.txt;
  the augmentation row reproduces its previously published values exactly,
  which is what validates the other four. The five previously published
  specs were re-scored in the same run and came back identical on every ROC
  AUC and CI.
  One accuracy constraint: treatment exposure was scored on the primary
  encoder, and the *Embedder comparison* paragraph names its own two
  concepts (psychiatric history, medication burden) explicitly, so nothing
  there claims a six-concept cross-encoder replication. Keep it that way.
- Terminology: "cohort-averaged" vital signs was wrong and is gone. The
  vitals are means over each patient's OWN pre-anchor encounters, not
  means over patients. "dtypes" is now "data type" in prose.
- The SMD paragraph now says outright that the check is over predictors
  and not over the outcome, and that the TRD rate matches by construction
  because the split is stratified.
- "penalizes axis-aligned recursive partitioning" read as though a
  regularization hyperparameter were involved. Reworded, with an explicit
  note that the tuning grids are identical across representations
  (HYPERPARAMETERS in classical_ml.py is keyed by classifier only).
- Cut: the predictor-selection sentence about "consuming" the split
  (rewritten plainly, claim kept); "if anything, TRD-positive patients had
  slightly shorter histories"; "reporting half a result".

FIGURE GEOMETRY, 2026-08-21. Every panel is now WIDE AND SHORT and stays
at the full 6in text width. The gaps in the previous build were geometric,
not editorial: a 6in-wide panel taller than about half the 9in text column
cannot share a page with its companion panel, so Word pushed the second
panel overleaf and left the rest of the page blank. Tallest offenders were
the confusion matrices (6.21in, metrics text hung under the axes and grown
into the canvas by bbox_inches='tight'), the forest plot (5.88in, axes
spanning only 41% of its own canvas), and the feature-importance panels
(5.44in). All panels now render 1.80-3.75in tall at 6in wide, so they pair
up two per page. Nothing was shrunk on the page and no number moved: the
panels were REDRAWN from the saved per-patient predictions
(test_predictions_*.parquet, summary_predictions.csv) by
scripts/pipeline/predictions/redraw_manuscript_panels.py, which checks every
recomputed ROC AUC against the pipeline's recorded value -- all 24 matched,
bootstrap bands included, since the band is seeded on SEED and indexed by
row count. Font sizes were raised to pay for the deeper downscale, so type
lands where it did before or larger. If a figure is regenerated, geometry
comes from PANEL_FIGSIZE in scripts/shared/plots.py; do not set panel widths
below 6in in this file to fix a gap.

Figure 11 (the ablation forest plot) was redrawn 2026-09-03 for MP's
comment 172. It had been generated 1x4 at figsize (20, 7), which
downscales 3.3x at the 6in text width and made the row labels
unreadable. It is now a 2x2 grid at (10.0, 7.4) -- 4.44in tall on the
page, inside the 4.50in threshold above -- with row labels on every
panel. TRD-EHR gained
scripts/pipeline/predictions/redraw_ablation_forest.py, which rebuilds
the PNG from ablation_summary.csv and classical_ml_results_EMBEDDED.json
and checks every delta against the recorded value before writing;
plot_ablation_roc_ci in ablation_runner.py carries the same geometry so a
pipeline re-run cannot regress it. No number moved.

MP REVIEW OF 2026-09-02 (tracked changes + 9 comments on the manuscript,
plus two supplied documents: JMIR_Methods_and_Supplement.docx and
Integrated_TRD_EHR_Discussion.docx). The rules it leaves behind:

- TIME ZERO IS THE **INDEX**, not the anchor. "index date", "index
  prescription", "pre-index", "post-index" everywhere in the manuscript,
  supplement, checklist and cover letter. The word "anchor" survives in
  exactly one sense: a QUERY anchor in the retrieval arm (anchor-neighbor
  pair, 8,516 test anchors). The deterministic renderer still prints
  `MDD-to-anchor gap` in its own field labels; the narratives in
  Supplement S6 are reproduced verbatim and are NOT re-labelled, and a
  sentence there says so.
- THE EMBEDDING IS A "generalized pretrained transformer embedding", and
  that is now the ONLY name for it, TITLE INCLUDED (changed 2026-09-03 on
  the user's instruction to call it what MP wants). "Neural embedding" and
  "neural narrative embedding" appear nowhere. Spelling is "pretrained",
  unhyphenated, matching "pretrained sentence-transformer encoder" already
  in Methods; MP wrote it both ways and this is the one that does not fight
  the rest of the text.
- "Classical machine learning" is now "standard machine learning".
- METHODS IS THE CONDENSED VERSION. MP's comment 84 called the old one
  verbose at ~4,600 words and asked for ~2,000; it is now ~2,540
  including the Figure 1 caption. Everything cut was RELOCATED, not
  deleted, into Supplementary Methods M1-M13 at the front of
  supplement.md, and every Methods subsection points at its M-section.
  Do not restore detail into the main Methods; put it in the M-section.
- TABLES RENUMBERED. Participant flow left the main text (comment 115)
  and is Supplement M2, Table M1. Cohort characteristics is now TABLE 1
  (comment 119) and its Results prose is ONE SENTENCE (comment 117); do
  not re-expand it. The train/test summary table was dropped, its numbers
  now being stated in Methods. Discrimination 2, calibration 3,
  neighbor-weighted 4, ablation 5, encoder 6. Figures are UNCHANGED, 1-12.
- SUBGROUP OUTCOME PREVALENCE left the main text (comment 136) and is
  Supplement S12. Subgroup PERFORMANCE stays in Results, in MP's
  condensed rewrite.
- DISCUSSION is MP's integrated draft (comment 176), taken as written -
  INCLUDING ITS ABSENCE OF A LIMITATIONS SECTION, decided 2026-09-03.
  The nine named items are held whole in reserve/limitations_reserve.md,
  which is not part of the packet. Do NOT re-add a Limitations heading without
  saying so there: seven of the nine are still said elsewhere (his Methods
  absorbed several, M1-M13 carry the rest, and his own Discussion argues
  fairness and the outcome proxy in its own words), and exactly two left
  the packet - that the informative missingness may be usable signal
  rather than a nuisance, and that the reported discrimination is an
  upper bound on later or external data. The audit is section 2 of that
  file and the two losses are section 3.
- REFS 25-31 are the new literature (comment 50 and the discussion
  document's list). Appended, not interleaved, per the rule in the
  References comment block. Their quoted discrimination figures are MP's
  and are UNVERIFIED against the source papers; none of the seven is held
  as a PDF in references/.

Two of MP's own edits were deliberately NOT taken verbatim: he relabelled
the 501,718 source population as "eligible", which inverts the meaning
(it is the population BEFORE eligibility), so it reads "Source
population"; and he deleted the 17.5% TRD base rate from participant
flow, which is load-bearing for five later passages, so it was kept.
```
