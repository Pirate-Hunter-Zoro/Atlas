# HANDOFF — the answer is theirs, and the tutor that reads it stays up

**The loop is closed everywhere a machine can check it, and nowhere a model can.
A document can be written up, listed, read on the glass, marked up, complained
about in words or in ink, and revised by whichever machinery made it — and none
of that has been done once by a person with a real document in front of them.
The same is now true of the two things a student's own answer owes them: the
verdict is down their words and every answer they typed is still there, and no
person has yet spent an evening in front of either.**

`board/README.md` is the architecture. This file says what is left.

---

## Before anything

- `bash board/test/all.sh` — 76 suites, about twelve minutes. Green before and
  after.
  The last of them is Paper-Writer's own, run where it is checked out, so the
  factory's 516 tests are now part of the board's habit rather than a second one
  nobody has.
- `cd projects/Paper-Writer && python3 -m unittest discover -s tests` — 516 tests,
  about twenty seconds. Still worth running alone while working in there.
- Bump `VERSION` in `board/web/sw.js` whenever a shell file changes. The library
  page is three of them.
- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and
  restarts every running board. Anything outside `board/` — `atlas.json`, a
  workspace's `writeups/`, `projects/Paper-Writer` — goes through
  `bash board/scripts/save-and-push.sh "message" -- <paths>`.
- Commits carry no assistant trailers. `.githooks/commit-msg` strips them.

**`projects/libr-local-llm` has its own handoff and it is the live one.** The
colibrì harness is committed, and that file asks for five pieces against the
board — a sixth agent in the registry, a per-agent timeout, a start control
shaped like `spawn.wake_tutor`, a fifth `resolve_agent` layer that is the
sitting, and a machine-wide refusal of a second sitting — plus two phrasing
defects from a Galois sitting. None of that is below. The fifth layer is the one
that touches this work: it goes beside `node` and `aim` in `_mark`, and
`config.aim_for` is the precedence function to sit beside rather than reinvent.

---

## What to do next

**1. Look at a sitting with the colours on and say whether they help.** The
verdict down the student's own answer and the labelled run of typed answers are
both in, both covered by `board/test/mine.js`, and neither has been seen by a
person teaching. Two things to watch for, because a test cannot: whether green
on the answer and a tick on the card a finger's width apart is the same thing
said twice, and whether *answer 2 of 3* is useful or is a number on a bubble
that did not need one. Both are one line to remove if they are noise —
`.mine[data-verdict]` in `board/web/board.css`, and the `nth` clause in
`render`.

**2. Put colibrì on the diarization repair.** `coli-up`, `coli-code` and
`coli-ask` exist and serve GLM-5.2 int4 to a coding agent in any directory, and
the job they were built for has never been run. It is written out as **part two
of `projects/libr-local-llm/HANDOFF.md`**, in the owner's own words, with the
scoring already decided:

```
python3 -m psych_asr.cli.apply_corrections --dry-run --anonymise
```

Counts, spreadsheet rows and seconds, naming the participant nowhere. Before:
`unplaced_rows` is `[16, 32]`, `within_2s` is 68 of 74, stray marks at zero. A
reconstruction is better if those move the right way — which is what makes a
rule colibrì proposes checkable by somebody not cleared for the data it was
tested on.

**Start it before you stop for the day.** The first turn is hours rather than
minutes: the client's preamble is 15,900 tokens and prefill at that size is two
to three hours. After it the KV prefix carries the preamble, so the thing not to
do is kill it at ninety minutes and start again — that is the whole cost, paid
twice. Leave the server up between tasks.

Colibrì is the only assistant that may read `phi`, and that is the entire reason
it exists. `research/PSYCH-ASR/HANDOFF.md` holds the *teaching* thread on the
same code; it is a different conversation and the two do not merge.

**3. Take one document all the way round, and what is left of it is the half a
machine cannot check.** Open a `paper` sitting on a box — PSYCH-ASR's correction
algorithm is the obvious one — let it write into `writeups/<slug>/`, compile it,
open `/library`, read it on the glass, draw on it, and say something is wrong
with it. Every seam under
that is covered end to end (`test/library.py`, `test/revising.py`,
`test/writing_up.py`, and `tests/test_pipeline.py` and `tests/test_revision.py`
in the factory). What is not:

- **The explainer rule against a model.** "A make sitting writes about the
  subject, never about the sitting" is a refusal in `sense.MAKE_SENSE`,
  `config.AIM_MEANS` and `TEACHING.md`, and `test/teaching.py` checks only that
  the three agree with each other. Whether a tutor that has just spent three
  hours teaching obeys it is unknown.
- **The revision turn against a model**, both kinds: the board's own `[revise]`
  turn, and the factory's editorial sweep reading somebody's actual complaint at
  the top of its brief.
- **Ink that a person actually drew.** The marks route is tested with fixture
  strokes, which is not the same as a ring round a figure at 200% zoom on an
  iPad — and the library's own pen has never met a stylus.
- **The two teaching rules that were asked for out loud**, both of them
  instructions rather than mechanisms: the question restated under the
  definition list so it is the last thing above the board, and the write-up
  compiled problem by problem rather than at the end. `test/teaching.py` holds
  the three places each is written down; no test can hold whether a tutor does
  it, and the next sitting is the only way to find out.

---

## Still open from the harness, unchanged

- **KV slots.** `projects/libr-local-llm` serves GLM-5.2 int4 with one slot. One
  slot means one conversation's prefix cache; a second client evicts the first
  and pays the whole preamble again. The engine supports 16 and `COLI_KV_SLOTS`
  is wired through; nobody has measured what a slot costs at a 131072 window.
  Decide when there is a second driver.
- **`MTP`.** The engine turns native speculative decoding on by itself, and what
  P0 measured as a loss was setting `MTP=1` on top of that. One A/B on a warm
  server, worth doing before anybody quotes a tok/s figure again.

---

## About this user

They work in a VSCode terminal on a compute node and close the laptop without
warning; leave long work as Slurm jobs that survive it, and leave a file behind
that says where things are. They read the runbook as the source of truth, so a
finding that contradicts it belongs *in* the repo, not in a chat message they
will not have tomorrow.

They will tell you when an answer is convoluted, and they are usually right. When
the direct path is blocked, say what blocks it in one line and then take the most
direct remaining path — do not build a clever detour around it and present that
as the answer.

---

## Settled, so nobody re-derives it

- **A board and its tutor die separately, and the board coming back is not the
  tutor coming back.** The daemon belongs to the allocation that started it; the
  board comes back on whichever node you next log in to, so the two end up on
  different machines and the older one ends. From the machine you work on, the
  course then reads *board on compute301, no tutor*, and every path that could
  have repaired it looked away: `cmd_resume` said it was leaving the board where
  it was and returned **before** `ensure_agent`, and `tutor restart --tutors`
  bounces tutors that are attached and reports *no tutors were attached* about
  one that has died. A login now asks the node the board is on, over ssh, with
  `tutor agent ensure` — `start` that says nothing when there is nothing to do.
  The record is believed first and `processes.agent_attached_away` is the only
  honest test from another machine: the heartbeat, never the pid, because a pid
  written on one node names a process table this one cannot read. Three missed
  wake-ups is the window. Over ssh only and not the hop's Slurm fallback: a step
  holds itself open for the life of what it starts, and one sleeping step per
  login is too much for a repair usually not needed. `board/test/agents.py`.
- **The verdict is painted on the student's own answer, and amber is the
  default.** The newest reply in a question's run decides it — `correct` is
  green, `wrong` is red, and every other reply to working is amber, because most
  replies in a doing sitting and most in a walkthrough are neither right nor
  wrong. `--ask` is that amber and `--note` is not: `--note` is the blue of an
  aside, and what was asked for is yellow. A question with no reply yet is
  painted **nothing** — waiting is not a verdict, and the pulsing strip is what
  says so. The verdict is part of the turn's identity on the page, so a node
  already on screen takes the colour when the reply lands instead of keeping the
  one it was born with, and the board holding the working is painted with it
  because that is what a person scrolls back to. `verdictOf` in `board.js`,
  `board/test/mine.js`.
- **A correction revises; a second answer is a second answer.** A send asked
  `answering.latest` — the newest turn on the question, of any kind — so every
  typed answer overwrote the one before it, and a Galois evening spent entirely
  on card 0001 kept the last of four. `correctingTurn` is the narrower question
  and the right one: the box is correcting an answer exactly when an answer was
  loaded into it, and it is cleared by a send, by emptying the box, and by
  moving to another question. Everything typed into an empty box is new and is
  kept, in the order it was given, under the feedback it replied to — a turn
  sits under the card it answers but never above a card written before it — and
  labelled *answer 2 of 3*, which is the wording the boards already use for a
  second page of ink.
- **A delivered manuscript lands in the workspace that asked for it.** The job
  carries `## Delivery` with one absolute `landing:` line —
  `manuscript.landing_for`, read by `jobspec.landing` through `_path_value` —
  and `stages/delivery` places a second copy of every artifact there, appending
  nothing, and keeps its own under `OUT_DIR`. The line names the PAPER'S OWN
  directory, which is what lets a revision land over the document it corrects
  rather than beside it under a slug of a title that has drifted. Not a setting:
  one harness serves every workspace, so `PAPER_OUT_DIR` cannot be each asking
  workspace's own. Absolute, because the factory cannot resolve a relative path
  against a root nobody named. It never raises — a landing that is relative or
  unwritable is recorded and the paper stays DELIVERED, the rule a missing
  pandoc already gets — and re-delivery is content-addressed, so a job run twice
  copies nothing twice. The do-not-rewrite list skips `feedback/`, `parts/`,
  `sections/` and `report.md`: telling the factory not to rewrite its own report
  is telling it the report is the paper.
- **The library reader takes ink.** Each page carries
  `data-ann="doc/<id>/p<n>"`, `annotate.js` attaches to it, and the pen is off
  until asked for so a long document still scrolls. `send` is never set from
  that page — ink on a document is a complaint about the document and becomes a
  turn when the note goes. The marks already on it arrive **with its pages**,
  through `library.ink`, because that page opens no sitting and has no live
  payload to read them out of.
- **The board's suite runs the factory's.** The two repositories hold one seam
  and only the board's suite is a habit, so `test/all.sh` runs
  `projects/Paper-Writer`'s tests last, and skips loudly where it is not checked
  out. `test/revising.py` checks the other direction, field by field.
- **`--help` on a subcommand is the dispatcher's, not the command's.** Answered
  before the repository is found, and only in the first position: further along
  it may be the value of an option. It exists because `board write --help`
  reached `cmd_write`, which drops anything option-shaped, read an empty body off
  the terminal and put a blank card on a lesson with no undo.
- **A posed problem is asked twice on its own card.** Statement, definitions,
  then the question again as the last line — because the definition list sits
  between the first asking and the board they write on. And the write-up is part
  of the turn that agrees an answer: `board hw use`, transcribe, `board hw file`,
  `board hw build`, before the next problem is posed. Both are in `TEACHING.md`,
  in `sense.METHOD_SENSE` and `sense.WRITEUP_SENSE`, and in `test/teaching.py`
  — which now actually runs the block that guards them, having imported
  `sense.py` by path under a name of its own for long enough that every check in
  it was being skipped.
- **A revision is not a new paper, and the factory now knows it.** A job
  carrying `## Revision` skips gathering, grounding, planning, the argument map
  and outlining; `stages/revision.py` splits the delivered Markdown on its own
  headings into the sections the editor works on, and the anchored-edit loop
  changes what the feedback names and nothing else. The outline gate is skipped
  because it asks whether a proposed plan is a well-formed manuscript, which is
  a question about a document that does not exist yet.
- **The job names three things and all three are load-bearing.** The
  **source**, never the rendering — `library.py` puts the PDF in `rel` because
  that is what goes on the glass, so the record carries `source` beside it. The
  feedback file. And the **workspace** the other two are relative to, because
  the factory is another workspace and cannot resolve a relative path against a
  root nobody named.
- **A delivered section is not re-budgeted.** Its budget is the length it
  already is, and `length.check` takes `absolute=0` from that path: a forty-word
  data-availability statement is the right length, and a floor telling the
  editor to grow it is a gate asking for invented content.
- **Ink is a complaint.** `library.marks` reads the strokes already stored
  against `doc/<ident>/p<n>`, a note carries the marked pages and the picture of
  each, the send button is live with an empty box, and the marks are recorded as
  handed over. A document is asked for under both names it has — the drawer's
  and the library's — because it is one document and its ink is its ink.
  `writing.ann_doc_page` is the one place a key is taken apart.
- **Fifty documents cost 0.74 s to open cold on the shared home**, 0.41 s on
  local disk, 0.1 s reopened, and 0.21 s on a machine with no poppler — where
  every document is still listed with its title, kind, formats and staleness,
  and only the page count is missing. Measured, and in `board/README.md`.
- **The aim of the open sitting changes in place.** `POST /aim`, `board aim`, and
  the five aims that need no scope in the sitting-kind chooser. Nothing is
  archived, no tutor is replaced, and the tap wakes a turn because the tap is the
  instruction. `board/test/aiming.py`.
- **Every sitting has a style.** A family default in `atlas.json`, overridden by
  `tutorboard.json`, overridden by the sitting. `config.aim_for` is the whole
  precedence and `config.stance_for` derives the stance from it — the browser
  sends neither, and `bin/tutor` no longer keeps its own copy of either.
- **A document is a stem in a directory.** `course/library.py` discovers them,
  groups them, reads the title and the kind out of the source, and reports stale
  as arithmetic. The two layouts already in this repository satisfy it and
  nothing moved. New ones go in `writeups/<slug>/`.
- **A make sitting writes about the subject, never about the sitting.** Stated as
  a refusal in `sense.MAKE_SENSE`, in `config.AIM_MEANS`, and in `TEACHING.md`,
  because a rule in one of those and not the others is a rule with two versions.
- **`/library` is a page, not a panel.** It writes no card, opens no sitting and
  changes no `state.json`, so correcting a deck cannot interrupt a proof.
  Feedback lands beside the document, dated and versioned, and the same request
  asks for the revision.
- **A revision runs fresh.** `turn_plan` resumes by default; a revision resumed
  into a lesson drags each into the other. Its report goes at the bottom of the
  feedback file. `carry_after` is why the next lesson turn does not resume into
  the document's session.
- **`doc/` is live in the service worker.** A page of a document is addressed by
  which document and which page, deliberately, so the shell rule was caching the
  very page a revision changes.
- **`mode` is gone and is not coming back.** `config.read_config` reads and drops
  it; four `tutorboard.json` files still carry one and it means nothing.
- **And the six changes before these.** `scripts/tool.sh` holds `tool_prefix` and
  `tool_root`, and both scripts read them. `tutorboard/fenced.py` is the one
  fence list and `reading.py` reads it. `plan._collect` takes `STEP` and `- [ ]`
  together in file order, `_distinct` settles the label collisions, and
  `MAX_STEPS` is 24. `course/results.py` and `/result/` put a figure on the
  glass. `map._unclaimed` gives a written map its document boxes.
  `paper1-trd-prediction` has its PDFs and `reading.py` finds them with no board
  change at all.
