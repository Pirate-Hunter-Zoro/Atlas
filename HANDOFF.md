# HANDOFF — a sitting's style, and the documents it produces

**The seven changes are in and the suite is green. What has not happened is a
document going round the loop: nothing has been written into `writeups/` yet, so
the shape is defined, routed and tested, and unproven.**

`board/README.md` is the architecture. This file says what is left.

---

## Before anything

- `bash board/test/all.sh` — 74 suites, about twelve minutes. Green before and after.
- Bump `VERSION` in `board/web/sw.js` whenever a shell file changes. The library
  page is three of them.
- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and
  restarts every running board. Anything outside `board/` — `atlas.json`, a
  workspace's `writeups/`, `projects/Paper-Writer/PROMPT_TEMPLATE.md` — goes
  through `bash board/scripts/save-and-push.sh "message" -- <paths>`.
- Commits carry no assistant trailers. `.githooks/commit-msg` strips them.

**The working tree still holds an unfinished afternoon in
`projects/libr-local-llm`** — four modified files and seven untracked ones under
`bin/`, `scripts/` and `slurm_jobs/`. None of it belongs to anything below. Ship
with a pathspec.

---

## What to do next

**1. Take one document all the way round, and it is the only thing here that
proves the rest.** Open a `paper` sitting on a box — PSYCH-ASR's correction
algorithm is the obvious one — let it write into `writeups/<slug>/`, compile it,
then open `/library`, read it on the glass, and say something is wrong with it.
What to watch: the explainer is about the machinery rather than about the evening
(that rule is a refusal in three files and has never been tested against a model),
the revision turn writes no card, and `live/state.json` is untouched when it
finishes.

**2. Paper-Writer does not read `## Revision` yet.** Its template names the
section and `manuscript.revise` fills it in, but `paperwriter/`'s own parsers
ignore it, so a revision is admitted as a fresh job — which works, and re-plans
the manuscript from the claims list, which is how a correction becomes a
different paper. That half is a change in `projects/Paper-Writer`: read the
section, skip the outline gate when it is present, and edit the delivered
document instead of drafting one.

**3. A correction round made of MARKS.** Written feedback has a route; ink does
not. Any page of any document can already be marked up, and turning those marks
into the body of a revision is one function reading `Annotate`'s stored marks
where the textarea is read now. It waits on a worked example: nothing has come
back marked up yet.

**4. Two measurements nobody has taken.** A library of fifty documents runs
`pdfinfo` once per PDF on a cold open — memoised on modification time, so it is
one hit per build, and it has only been run against three workspaces. And a
machine without poppler shows no page count at all rather than a wrong one,
which is right and untested on such a machine.

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
