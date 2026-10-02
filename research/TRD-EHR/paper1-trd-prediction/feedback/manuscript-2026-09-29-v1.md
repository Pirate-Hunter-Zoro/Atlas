# Feedback on Title page

- document: `paper1-trd-prediction/manuscript.pdf`
- written: 2026-09-29 14:51
- ask: revise
- marked up on 7 pages
- round 1, 14 requests: `paper1-trd-prediction/feedback/manuscript-2026-09-29-v1.ledger.json`

Filed after the fact. This is the ink round of 2026-09-29, answered in commit b6214bcf and written up in `paper1-trd-prediction/review/round_2026-09-29.md`. The ink on pages 2-7 was erased by hand on 2026-10-02, so requests 2-14 are what that file transcribed; request 1 keeps the ink still on page 1. Items 15 and 16 of that file needed no action and are not requests.

## The requests, by id

Every request below has an id. The revision answers each one in the ledger named above, and the board writes the account of what was changed from those answers.

### R1.1 -- ink on page 1 (85 strokes)

The ink, cropped: `paper1-trd-prediction/feedback/manuscript-2026-09-29-v1/R1.1.svg`

### R1.2 -- about page 2

p2, Abstract Conclusions: "and prioritize validation of the outcome, transportability, and clinical value before deployment." — "What does this mean?" (transcribed)

### R1.3 -- about page 3

p3, Introduction: "longitudinal" — "Meaning?" (transcribed)

### R1.4 -- about page 4

p4, end of Introduction: "The comparison concerns complete representation pipelines because their field inventories were not identical." — "I don't understand this sentence" (transcribed)

### R1.5 -- about page 4

p4, Study Design: "The resulting sample was enriched … 12,530 eligible patients (29.4%) entered through the randomly sampled group." — sketch: 80% flagged, 20% random (transcribed)

### R1.6 -- about page 4

p4, Participants: "Index selection did not require …" — "How can index selection require anything?" (transcribed)

### R1.7 -- about page 5

p5, Figure 1 caption: "The 57.9% annotation describes candidate index orders, not the final cohort." — "This means AD prescription happened on same day of MDD prescription right? SAY that if so." (transcribed)

### R1.8 -- about page 5

p5, Outcome: "Standardized symptom response was unavailable, and dose and duration adequacy were not established …" — "Meaning?" (transcribed)

### R1.9 -- about page 6

p6, top: "Access to depression treatment differs … 'TRD proxy' …" — "I don't understand this blurb" (transcribed)

### R1.10 -- about page 6

p6, Representations: "this duration rule did not establish adequate dose." — "Just time?" (transcribed)

### R1.11 -- about page 7

p7, Model Development: "Tuning grids were identical across representations …" — "We didn't necessarily pick the same hyperparameters right?" (transcribed)

### R1.12 -- about page 7

p7, calibration: "The supplementary calibration-curve summaries use slopes … not interchangeable." — "What?" (transcribed)

### R1.13 -- about page 7

p7, "Nonparametric bootstrap resampling of test patients provided 95% CIs." — "what does this mean?" (transcribed)

### R1.14 -- about page 7

p7, comparisons passage, through the Youden J sentence — "I don't understand this" (transcribed)

<!-- ledger: the section below is written by the board from this round's ledger; edit the ledger rather than this -->

## What was changed

Written by the board from `paper1-trd-prediction/feedback/manuscript-2026-09-29-v1.ledger.json`: 14 of 14 requests answered.

- **R1.1** (page 1) -- partly: Partly. Authors' Contributions now credits the writing correctly. The corresponding author is unchanged: moving it to Martin needs his agreement, so it is a question for him, not an edit.
- **R1.2** (page 2) -- done: Done. The clause is now 3 named tests.
- **R1.3** (page 3) -- done: Done.
- **R1.4** (page 4) -- done: Done, by cutting it. Methods, *Patient Representations and Missing Data*, already says in plain words which fields each pipeline had and lacked.
- **R1.5** (page 4) -- done: Done, with one correction to the sketch. The shape is right: 2 groups, and some of the unflagged random sample still qualified. The proportions are reversed. Flagged patients are 20.0% of the extract (100,420) and the random unflagged sample is 80.0% (401,298), the 4:1 design in Supplement M1. The 29.4% is the unflagged share of the eligible cohort, not of the extract. The 20.0% and 80.0% carry no interval because they are the design's own counts, not estimates.
- **R1.6** (page 4) -- done: Done, here and in Supplement M2.
- **R1.7** (page 5) -- done: Done, and the figure changed. The reading is right in kind, but 57.9% was a share of upstream candidate orders, which no reader can place. The figure now counts patients in the cohort, read from the feature table: 25,645 of 42,579 (60.2%) were prescribed on the day of their first depression diagnosis. The figure also says "index" throughout instead of "anchor", the manuscript's one word for that date. Supplement M2 drops the 57.9% for the same count. Supplement S7's 27,906 counted diagnosis-to-prescription gaps of 0 or 1 day and called them "same-day"; it now says "the day of diagnosis or the 
- **R1.8** (page 5) -- done: Done.
- **R1.9** (page 6) -- done: Done. The mechanism is now spelled out, and the duplicate section pointer went.
- **R1.10** (page 6) -- done: Done. Yes, time only.
- **R1.11** (page 7) -- done: Done. His reading is correct: one grid, searched separately per representation. TRIPOD item 12c says the same.
- **R1.12** (page 7) -- done: Done, by cutting both sentences. The distinction between binned and individual-level slopes stays where a reader of those numbers meets it, Supplement M13, S3 and S9.
- **R1.13** (page 7) -- done: Done.
- **R1.14** (page 7) -- done: Done. Rewritten as the 2 comparisons we made, in order, with the reason the second is post hoc and what an interval through zero means.

<!-- ledger: end -->
