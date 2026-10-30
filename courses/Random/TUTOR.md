# Random

## Where things are

Teaching source: the uploaded `sessions/20261030-095641/uploads/HANDOFF.md`, a brief for migrating TRD-EHR into a source-traceable longitudinal evidence model. Its `../TRD-EHR` and `CTO` paths are absent on this machine, so lessons use the brief's synthetic forms and say so. Session is bound to `courses/Random`. Write-up: `docs/writeup-20261030-095641/writeup.tex`, one agreed problem, `m17-continuation-unknown`.

## Now

Lesson 2 continues, card `0010-trd-ehr-10-record-is-a-row`. On t0003 they asked whether medication, diagnosis and procedure are rows of one table across all patients, each with its own id; card 0010 confirmed all four points and re-posed the encounter row of `event_log_v2` for E4, 2025-02-28 in full — `source_table`, `source_field`, `raw_value`, `event_type`, `timestamp_role`. The diagnosis row (F32.9) and medication row (sertraline, end missing) follow after it. The D5 table-mapping question stays set aside while this walkthrough runs. Card `0004` stays withdrawn and the one-way-projection exercise stays dropped until they reopen it. `../TRD-EHR` is absent, so every lesson runs on synthetic fixtures and says so; no parity check can be run here.

## Open decisions

## Done recently

2026-10-30 10:58 — Confirmed `event_log_v2` is one table for all patients and event types, each row with its own id; re-posed encounter row on card 0010.
2026-10-30 10:52 — Answered "created from what": Epic/Caboodle flat files plus upstream R files; credited their sketch; re-posed the encounter row in full on card 0009.
2026-10-30 10:49 — `patient_master_v2` row for `P-9001` accepted; encounter row of `event_log_v2` posed.
2026-10-30 10:41 — Card 0007 starts the dummy-patient walkthrough; layer 1 rows are the current exercise.
2026-10-30 10:38 — Card 0006 teaches the six evidence layers; D5 narrowed to a table-mapping question.
2026-10-30 10:36 — 0004 withdrawn as a duplicate of 0001; diagnosis row D5 posed.
2026-10-30 10:31 — M17 exercise agreed: end unknown, neither continued nor stopped; moved on to one-way loss.
