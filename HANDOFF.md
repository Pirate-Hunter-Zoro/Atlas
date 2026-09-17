# HANDOFF — everything is one tap away, and nothing has been tapped

**The loop is closed everywhere a machine can check it, and nowhere a model or a
person can.** A document can be written up, listed, read on the glass, marked
up, complained about in words or in ink, and revised by whichever machinery made
it. A student's own answer carries its verdict and every attempt they typed is
kept. The local model can be chosen for a sitting, started from the glass,
watched through four states, and put to work on a workspace nobody is looking at.
**None of it has been done once by a person with a real document, a real evening
or a real transcript in front of them, and the one job all of it was built for
has not been run.**

`board/README.md` is the architecture. This file says what is left.

---

## Before anything

- `bash board/test/all.sh` — 78 suites, about twelve minutes. Green before and
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

**`projects/libr-local-llm` has its own handoff and it is still the live one.**
The five pieces it asked for against the board are shipped and are under
*Settled* below; what is left in that file is the diarization job itself, which
is item 2 here.

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

**2. Put colibrì on the diarization repair.** Everything it needs now exists —
the agent is a row in the table, the sitting can choose it, the server says
which of four states it is in and offers to start one, and a workspace nobody is
looking at can be handed a job — and the job itself has never been run. From any
board: **⇥ put an assistant to work elsewhere**, pick `PSYCH-ASR`, pick
`colibri`, and give it the ask. It is written out in full in
`projects/libr-local-llm/HANDOFF.md`, in the owner's own words, with the scoring
already decided:

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
twice. Leave the server up between tasks. Nothing will kill the turn: the
`colibri` recipe carries a four-hour `timeout` that `turn_timeout` takes as a
floor, and the daemon's beat thread keeps the indicator green for the whole of it.

**`PSYCH-ASR` is the workspace it will open in, and it is the only kind that
will.** A colibrì sitting refuses where a card of its own would be committed;
that workspace ignores `live/*`, and a course does not.

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
- **And a third, of the same kind and newer: no card tells the student to write
  anything up.** The act was already governed and the card still said *"two
  words to add when you write it up"*. The rule is now in `TEACHING.md` twice —
  as its own section under the write-up, and as a sentence-level rule beside
  *Say it plainly* — and in `sense.WRITEUP_SENSE`, which in a headless turn is
  the whole prompt. A phrasing rule cannot honestly be unit-tested against a
  real card, so what `test/teaching.py` asserts is that it reaches the course,
  and **the first card of the next sitting is the real check.**

---

## Still open from the harness

- **KV slots.** `projects/libr-local-llm` serves GLM-5.2 int4 with one slot. One
  slot means one conversation's prefix cache; a second client evicts the first
  and pays the whole preamble again. That is why a colibrì sitting is refused
  machine-wide while another holds one. The engine supports 16 and
  `COLI_KV_SLOTS` is wired through; nobody has measured what a slot costs at a
  131072 window. Measure it and the refusal becomes a queue — one line out of
  the `colibri` recipe in `board/bin/tutor`, and nothing else changes.
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

- **Which assistant tutors a sitting is the sitting's to say, and it is the only
  layer a tablet can reach.** `resolve_agent` had four — a flag on a command
  line, a line in the workspace's `tutorboard.json`, a hostname, a default — and
  none of them was the sitting, so choosing a different model for one evening's
  work meant editing a file that is a statement about the workspace for ever.
  The fifth goes into `state.json` through `_mark`, beside `node` and `aim`,
  under exactly their rule: a choice made for an evening is not a decision about
  what the repository is, so it is cleared by opening a sitting that does not
  name one. It is chosen as a sitting OPENS and there is deliberately no
  `/agent` beside `/aim`: an aim changes what the next card is, an assistant
  changes **who writes it**, and the conversation the outgoing one was holding
  does not transfer — which on the local model is a 15,900-token preamble paid
  again, in hours. A name the machine has not got falls back with a line saying
  so where every layer below it refuses, because this is the one layer written
  from a browser and a misspelling must not leave a course with no tutor.
  `config.clean_agent` checks that it is a NAME and nothing more, because the
  registry is in `bin/tutor` where a recipe belongs. The *who:* row in the
  sitting chooser is the control; `board/test/colibri.py`, `board/test/who.js`.
- **The local model is a row in a table, and three fields on it carry everything
  unlike the other five.** `timeout` is four hours and `turn_timeout` takes it
  as a FLOOR, so a colibrì turn is not killed mid-prefill and painted as a turn
  that failed while the two numbers about the sitting stay exactly as they were
  for everybody else. `exclusive` is one sitting at a time machine-wide, found
  off the heartbeat and never the pid, because a pid written on one node names a
  process table this one cannot read — the server has one KV slot and a second
  sitting destroys the first one's preamble. `private` refuses to open where
  `git check-ignore` says a card of its own would be tracked, because this is the
  only assistant allowed to read `phi`. Each is a string that is its own reason,
  so the day one stops being true a line comes out of the table rather than out
  of a function.
- **Starting the server is four states off `squeue` and a thread that returns at
  once.** Nothing running, queued with Slurm's own reason, loading, warm.
  `coli-code`'s answer to a missing server is *start one: coli-up*, which is
  right in a terminal and a dead end on an iPad — and an allocation, a 429 GB
  load and a warm-up generation cannot be reported by the request that asked for
  them, which is the reason written above `spawn.wake_tutor` and now above
  `spawn.wake_colibri`. No state file: `squeue` never goes stale and a file does,
  cached fifteen seconds the way `machines.held_nodes` caches its own. Loading
  versus warm is not a question Slurm can answer — the gateway binds its port
  before it loads anything, so a TCP probe answers instantly and says nothing —
  so the job's own `API listening on` and `COLIBRI-SERVE READY` are what is read.
- **A workspace you are not looking at can be handed a job, and only the seam
  was missing.** `machines.workspaces` was the list, `tutor agent start --agent`
  was the start, and `news.elsewhere` was already how it comes back. `POST
  /elsewhere` asks for the start FIRST and writes the task second: the other
  order leaves a refused job in another workspace's transcript with nothing that
  will ever read it, and two refusals fire routinely. Nothing is missed by
  writing second, because `agent_start` forks and returns and `board wait` blocks
  rather than reading the inbox once. The assistant is named on the command
  line — layer 1, this once — and never written into a sitting nobody is
  watching.
- **The receipt lets go when the answer is ON THE GLASS, not when its record
  arrives.** Two surfaces asked "has the reply landed" and answered differently:
  the writing surface asked `typingCards()` and held, the receipt asked whether a
  card existed and let go the instant one did. So the pulse stopped, the next
  board came down, and the answer filled in afterwards — *"the response appeared
  how I wanted it to, but before it did, the second board showed up right
  underneath the last board, and I was left hanging."* One predicate now,
  `replyArriving`, asked by both. The type-out's deadline is a WATCHDOG rather
  than a budget — it measures silence, refreshed by every frame that lands — since
  the card that runs longer in wall-clock than its own animation asked for is
  precisely the longest one, which is the card the hold is most needed for. And
  the receipt has a fourth state, `arriving`, because *"the tutor is reading it"*
  stops being true the moment the card starts typing and that is the few seconds
  somebody is actually watching it. `board/test/hanging.js`.
- **A typed answer is owed the same pulse as a page of ink.** One condition was
  doing two unrelated jobs: it set `awaitingReply` and it decided whether the
  turn was rendered into the transcript, and only the second is about the kind.
  The `items.pop()` is an argument about ink — the same page is on the surface
  directly below — and a typed answer is duplicated nowhere, so it stays. A
  signal is not an answer and raises no receipt: a tap on "begin" is in the
  transcript because they did it, and *"sent at 20:14"* is a sentence about work
  handed in.
- **The box belongs to the question, not to whichever tab is showing.**
  `restoreTextAnswer` and `restoreTextDraft` were asked only while the type half
  was up, so a question that opened on the slate left the previous question's
  words in the box — and the restore refused any box that was not empty. Both are
  now asked whenever the panel is open, and the refusal asks the narrower and
  right question: does `textDrafts` hold typing of their own, on THIS question,
  that has not been sent. That is the same correction `correctingTurn` is on the
  send side. The height is measured only where it can be, because `scrollHeight`
  on a hidden textarea is zero.
- **The write-up is the tutor's, and so is the sentence about it.** A card said
  *"two words to add when you write it up"*, which is two failures welded into
  one clause: it hands over an errand that does not exist, and it defers a
  correction — the missing word was `non-zero`, a fact about the proof rather
  than a note for later, so the fix was made conditional on something the student
  was never going to do. A card now says what the file NOW SAYS, and a correction
  belonging in the write-up is made there in the same turn. In `TEACHING.md`
  twice and in `sense.WRITEUP_SENSE`, which in a headless turn is the whole
  prompt.
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
  login is too much for a repair usually not needed. And `tutor where` names a
  tutor on another node instead of calling it `stale`, which it did because it
  asked whether that pid was alive HERE -- about a daemon listening perfectly
  well over there, on the machine the question is typed on.
  `board/test/agents.py`.
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
