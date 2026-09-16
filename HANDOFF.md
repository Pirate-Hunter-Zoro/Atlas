# HANDOFF — a sitting's style, and the documents it produces

**The loop is closed everywhere a machine can check it, and nowhere a model can.
A document can be written up, listed, read on the glass, marked up, complained
about in words or in ink, and revised by whichever machinery made it — and none
of that has been done once by a person with a real document in front of them.**

`board/README.md` is the architecture. This file says what is left.

---

## Before anything

- `bash board/test/all.sh` — 74 suites, about twelve minutes. Green before and after.
- `cd projects/Paper-Writer && python3 -m unittest discover -s tests` — 499 tests,
  about fifteen seconds. Green before and after, and it is the other half of the
  document seam now.
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

**1. A delivered manuscript never arrives in the workspace that asked for one,
and the revision route is waiting on documents that are not there.** The job the
board writes ends "The finished paper is to be delivered into `<workspace>/
manuscripts/`", and nothing in `paperwriter` reads that line: `stages/delivery.py`
copies into `config.OUT_DIR/<project>/<paper>/` and stops. So
`manuscript.delivered` finds nothing, `library.py` marks nothing
`made: paper-writer`, and the factory branch of the library's feedback route can
only fire for a manuscript somebody copied in by hand. Two honest fixes and the
first is better: name the landing as a **field** in the job the way
`## Revision` names the document, and have `delivery.deliver` place a second
copy there; or point `PAPER_OUT_DIR` at each asking workspace, which cannot work
because one harness serves every workspace. The prose instruction should go
either way — an instruction no code reads is a promise the board is making on
somebody else's behalf.

**2. Take one document all the way round, and what is left of it is the half a
machine cannot check.** Open a `paper` sitting on a box — PSYCH-ASR's correction
algorithm is the obvious one — let it write into `writeups/<slug>/`, compile it,
open `/library`, read it on the glass, and say something is wrong with it. The
wiring under all of that is now covered end to end (`test/library.py`,
`test/revising.py`, and `tests/test_revision.py` in the factory). What is not:

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
  iPad.

**3. The library reader cannot be drawn on, and the board's viewer can.** Ink on
a page of a document becomes feedback now — `library.marks` reads it where the
textarea is read, and a note carries the marked pages and the picture of each.
But the ink has to be made on the board, through the drawer, and then the note
written on a different surface. `library.js` draws its pages as plain `<img>`
in `#reader-pages`; giving each one `data-ann="doc/<id>/p<n>"` and attaching
`annotate.js` is the missing half, and `IDENT_MAX` is already 40 so a library id
is a legal annotation key. What that costs is a pen UI on a second surface,
which is the reason it is not done rather than an oversight.

**4. `board/test/all.sh` never runs the factory's suite.** The two repositories
hold one seam between them — `manuscript.job` writes a `## Revision` section and
`jobspec.revision` reads it — and `test/revising.py` now checks both sides
against each other when Paper-Writer is checked out. Nothing checks the reverse
direction: a change to `manuscript.job`'s field names passes the board's suite
and breaks the factory silently, and only the board's suite is a habit.

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
