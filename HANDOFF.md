# HANDOFF — the style of a sitting, and the documents it produces

Seven changes, and they are one piece of work in two halves.

**The first half is that a sitting's style is chosen once, at the moment it opens, and cannot
be changed afterwards.** `aim` reaches `live/state.json` from exactly one place — a tap on the
map, through `POST /session` — and `/session` opens a *new* sitting: `board open` archives the
lesson and a chapter change replaces the tutor. So "wait, now teach me how this works", said
three hours into building something, costs the evening it is said in. That is the limitation.

**The second half is that a sitting cannot produce a document about what it just did.** There
is a `make` sitting and it makes one, but it is a sitting you have to *leave the lesson for*,
its product has no agreed home, its briefing never says the write-up is about the machinery
rather than about the lesson, and once the file exists nothing shows it beside the others or
takes a word of feedback on it.

Ordered smallest first. **One change, shipped, checked, then the next** — four of these touch
`config.py`, `sense.py` and `routes/lesson.py` together, so the order matters more than usual.

Each section says what is true now, what should be true, and where. The paths are real and were
read.

---

## Before anything

- `bash board/test/all.sh` — 71 suites, about twelve minutes. Green before and after.
- Bump `VERSION` in `board/web/sw.js` whenever a shell file changes. Changes 5 and 7 both
  change the shell, and change 7 is *only* a shell change, so it is invisible without the bump.
- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and restarts every
  running board. Anything outside `board/` — `atlas.json`, a workspace's `writeups/`,
  `projects/Paper-Writer/PROMPT_TEMPLATE.md` — goes through
  `bash board/scripts/save-and-push.sh "message" -- <paths>` with a pathspec.
- Commits carry no assistant trailers. `.githooks/commit-msg` strips them.

**The working tree holds an unfinished afternoon in `projects/libr-local-llm`** — four modified
files and seven untracked ones under `bin/`, `scripts/` and `slurm_jobs/`. None of it belongs to
anything below. Ship with a pathspec.

---

## The vocabulary, settled first, because everything below uses it

`config.AIMS` already has the seven words and they are the words to keep. The names used out
loud map onto them, and nothing new is coined:

| Said out loud | The aim | What the tutor does |
|---|---|---|
| vibe coding | `build` | writes the code, runs it, reports what changed |
| math coaching | `teach` | works it through properly and makes the person do the step |
| coach coding | `coach` | names the calls and arguments in English; the person types |
| — | `trace` | reads code that already exists, line by line |
| — | `drill` | asks cold over a scope |
| — | `paper` | the product is a write-up |
| — | `slides` | the product is a deck |

A **stance** (`teach` / `do`) is who writes the code. An **aim** is what the sitting is for. They
are not independent — `build` with a `teach` stance is a contradiction — and today the browser
resolves that by sending both from the `WORK` table in `board.js`. It should not: see change 2.

---

## 1. The aim cannot be changed without losing the lesson

**Now.** `_mark` in `board/tutorboard/server/routes/lesson.py` writes `st["aim"]`, and `_mark`
is called only from `POST /session`. Every path through `/session` calls
`spawn.board_cli(root, ["open", …])`, which archives the open lesson; the chapter path also
calls `spawn.fresh_tutor`. There is no route, no button and no `board` subcommand that changes
the aim of the sitting that is open.

The running tutor is the other half of it. A turn is a headless call and only a *fresh* one
reads `sense.session_sense` — `HEADLESS_RESUME_PROMPT` in `board/bin/tutor` tells a resumed turn
in as many words not to re-read anything. So writing a new `aim` into `state.json` and stopping
there changes nothing for the assistant that is mid-conversation.

**Want.** One control, reachable from anywhere on the board, that changes the style of the
sitting that is open. Nothing is archived, no tutor is replaced, the transcript carries on, and
the next card is written under the new aim.

**Where.**

- **`POST /aim`** in `routes/lesson.py`, beside `/direction`. It does the same four things
  `_direction` does, minus the two destructive ones: write the aim to `state.json`, write the
  person's tap into `live/turns.jsonl` as a turn of theirs with `signal: "aim"`, append a line
  to `repo.messages_path` carrying `[aim] ` + `config.AIM_MEANS[aim]` + `sense.session_sense(repo)`,
  and `spawn.wake_tutor` if nothing is listening. It does **not** call `board_cli(["open", …])`
  and it does **not** call `fresh_tutor`.
- **`sense.SIGNAL_SENSE` gains `"aim"`** — one sentence saying the person has changed what they
  want from this sitting mid-lesson, that everything already on the board stands, and that the
  next card is written the new way.
- **`bin/board` gains `board aim <name>`**, so the terminal can do it too. `--aim` on
  `board open` already exists and stays.
- **`board.js`** gains the control. The seven labels already exist in `WORK` (~4301) — reuse the
  strings, do not write a second set. Show which aim is in force: `state.aim` is already in the
  payload, and `els.kindStance` (~3295) is the precedent for a control that displays what is
  current.

**The tap is the instruction.** It wakes a turn, the same way choosing a way to work on the map
does and for the reason written above `_begin`. "Wait, now teach me how this works" is an
interruption, not a preference to be applied later.

**Only the five aims that need no scope** — `teach`, `build`, `coach`, `paper`, `slides`. `trace`
needs a list of files and `drill` needs a scope, and choosing one of those is choosing what it is
over, which is a map tap and a new sitting. Say that in the panel rather than offering a button
that then asks a second question.

**And `MAKE_SENSE` has to stop being keyed on the sitting kind.** `sense._session_sense` reaches
it through `if kind == "make"`, so an aim of `paper` in a lecture gets `AIM_MEANS["paper"]` and
none of the method. Key it on `kind == "make" or aim in ("paper", "slides")`. Without this,
change 3 lands and nothing reads it.

**Check.** A new `board/test/aiming.py`: the route writes the aim, leaves `live/archive/`
untouched, leaves the card count unchanged, and puts a line in the inbox that contains the new
aim's sentence. `test/steering.js` is the model for the panel; `test/direction.py` is the model
for the route, and is also the contrast — that one asserts the lesson *is* archived.

---

## 2. A sitting that nobody opened from the map has no style at all

**Now.** `aim` is unset unless somebody tapped a box. `tutor galois`, `board open`, a chapter tap
in the contents drawer, and a board resumed after a reboot all leave it empty, and `aim_sense`
returns `""`. The sitting then runs on stance alone, which is `teach` everywhere except
`research/TRD-EHR` and `projects/Paper-Writer`. So the ordinary way in has no style, and the
style it falls back to is the wrong one for a project.

**Want.** A family default, overridable at every level below it.

    courses, practice   →  teach     the mathematics worked properly
    research, projects  →  build     the tutor writes it and reports

Precedence, once, in one function: **the sitting's own aim → the workspace's `tutorboard.json` →
the family's default in `atlas.json`.**

**Where.**

- **`atlas.json` gains `"aim"` on each family.** That file "names and orders the five families
  and says which hold somebody else's work" — a default style is a property of a family, and it
  is still not a registry of workspaces. `atlas.families()` carries it through; `atlas.family_of`
  already answers which family a root is in.
- **`config.py` gains `aim_for(root, state)`**, written beside `stance_for` and in the same
  shape.
- **`stance_for` becomes derived, not parallel.** Add `AIM_STANCE` to `config.py` — `build`,
  `paper` and `slides` are `do`; `teach`, `coach`, `trace` and `drill` are `teach` — and resolve
  stance as: the sitting's own stance → the sitting's aim → the repository's stance → the family
  aim's stance. This is what stops the browser from deciding it, and `board.js`'s `WORK` table
  should then stop sending `stance` at all.
- **`bin/tutor.doing_now` (~815) re-implements this and must stop.** It reads `state.json` and
  `config.read_config` by hand to decide a turn's timeout, and its `DOING_AIMS` is a third copy
  of the same list. Import the one answer.
- `config.read_config` still drops `mode`, and four `tutorboard.json` files still carry one.
  Leave them ignored. Do not resurrect `mode` as the place a default aim is declared.

**Check.** A new `board/test/aiming.py` (the same suite as change 1): a course with no
`tutorboard.json` aim gets `teach`, a project gets `build`, a workspace that names one wins over
its family, a sitting that names one wins over its workspace, and `stance_for` agrees with
`doing_now` for all seven aims.

---

## 3. A document a sitting produces has no home, and the three that exist disagree

**Now.** `MAKE_SENSE` tells the tutor to "keep it in the repository, as a file, under a name that
says what it is", and that is the whole of the convention. What actually exists is three:

| Where | Shape |
|---|---|
| `research/TRD-EHR/paper1-trd-prediction/` | `manuscript.{md,pdf,docx}`, `supplement.*`, `cover_letter.*`, `tripod_ai_checklist.*`, with `parts/`, `references/`, `review/`, `reserve/` beside them |
| `research/PSYCH-ASR/docs/` | `stage1_pipeline_walkthrough.{tex,pdf}` and `stage2_reference_walkthrough.{tex,pdf}` — beamer, aspectratio 169, Boadilla |
| `manuscripts/` | where `manuscript.LANDING` says a Paper-Writer delivery goes |

And `reading.py` finds a document only if it is a PDF of at least 20 kB within three levels,
capped at 24, with `NOT_OURS` names pruned — which is right for a drawer and does not scale to a
workspace with fifty.

**Want.** One shape, discovered rather than registered, that the two existing layouts already
satisfy so nothing has to move.

**The shape: a document is a STEM in a DIRECTORY, in however many formats it has.**
`manuscript.md` + `manuscript.pdf` + `manuscript.docx` is one document. `stage1_pipeline_walkthrough.tex`
+ `.pdf` is one document. The directory is the group, and the group is what the library draws a
heading from. Nothing is declared:

- **Title** from the source — `\title{…}` in a `.tex`, the first `# ` in a `.md`. The filename is
  the fallback, through `reading._pretty`.
- **Kind** from the source — `\documentclass[…]{beamer}` is a deck, anything else is a paper.
- **Stale** is arithmetic: the source's mtime against the PDF's.

**New documents land in `writeups/<slug>/`** — `<slug>.tex`, `<slug>.pdf`, `figures/`,
`feedback/`. One directory per document, because a deck's figures and its rounds of feedback need
somewhere to be. `writeups` and not `papers`: `reading.NOT_OURS` already means a `papers/`
directory is somebody else's library.

**Where.** A new `board/tutorboard/course/library.py`. It is not an edit to `reading.py` —
that module answers "what can be put on the glass in a card", is capped at 24 and walks three
deep, and those are the right numbers for a drawer. `library.py` answers "everything this
workspace has written", groups it, and is allowed to be bigger and deeper. Both read
`fenced.refused`, and `library.py` refuses `NOT_OURS` names the same way, or TRD-EHR's
`references/` arrives as forty documents by other people. Cache it the way `reading.documents`
does — 30 seconds off a bounded walk — because the payload is polled four times a second.

**Check.** A new `board/test/library.py` with both existing shapes as fixtures: the flat pair in
a `docs/` directory, the four-stem `paperN-*` directory, a `phi/` directory that is found
nowhere, a `references/` directory that is found nowhere, and a `.tex` newer than its `.pdf`
reported stale.

---

## 4. The write-up would be about the lesson, and it must be about the subject

**Now.** `MAKE_SENSE` in `sense.py` is entirely about *how* to work — sections, show each one,
take corrections, keep it in the repository. It says nothing about what the document is. A tutor
that has just spent three hours teaching, asked to write it up, writes up the three hours.

**Want.** An explainer. **"Here is how this works, and here is the mathematics"** — written for
somebody who was not there. No first person, no "we covered", no "the student then", no reference
to the sitting, the cards, the questions or the person. If a concept was taught by hand-checking
three examples, the document explains the concept and shows the examples; it does not narrate the
hand-check.

**Where.**

- `sense.MAKE_SENSE` gains that paragraph, stated as a refusal rather than a preference.
- `config.AIM_MEANS["paper"]` and `["slides"]` say it in one sentence each, because those are the
  words a person taps and the words the tutor is given and they must not drift — which is why
  that dictionary is in `config.py` in the first place.
- `board/TEACHING.md`, the "A make sitting" section (~1104). That file is the contract and is
  copied into every workspace's `live/` on start, so a rule that is in `sense.py` and not in
  there is a rule with two versions.
- **The scope is the box, not the evening.** `node_sense` already puts `state.node` and its files
  into the prompt. Say outright that the document is about that machinery. A mid-sitting
  "write this up" with no node set is about the chapter label, and with neither it asks before
  it drafts.

**Check.** `board/test/teaching.py` asserts the phrases are in the briefing for both aims and in
both files. `board/test/writing_up.py` covers the job side.

---

## 5. Nothing shows a workspace's documents together, and nothing takes feedback on one

**Now.** The ⋯ menu's `btn-papers` panel (`openPapers`, `board.js` ~1850) offers exactly two
things: `lesson` and `homework`, off `state.load_papers`. The contents drawer offers what
`reading.py` found, one flat list, as things to put on the glass. Neither is "every paper and
presentation in this project", neither is reachable without opening a lesson first, and there is
nowhere to say what is wrong with one.

**Want.** A library: one surface, per workspace, that draws everything `library.py` found and
takes feedback on any of it.

**Where.**

- **A page of its own, `/library`,** with its own `library.html`, `library.js`, `library.css`.
  `/slate` is the precedent, and it is served in `board/tutorboard/server/handler.py` (~169) —
  put this one beside it. Add all four to `SHELL` in `web/sw.js` and bump `VERSION`.
- **Reachable without the lesson.** A button in the ⋯ menu on the board, and a link on each
  workspace's tile on the atlas front door (`web/home.js`), because "view all papers and
  presentations related to a project very easily" means not opening a sitting to get there.
- **What it draws.** Grouped by directory: title, kind, page count, when the PDF was last built,
  and a stale mark where the source is newer. Tapping one reads it on the glass through the
  existing renderer — `reading.pages` and `/doc/<id>/<page>.png` in `routes/taking.py`, which
  already do exactly this and need no change.
- **Feedback** is written where the document is: `writeups/<slug>/feedback/<date>-v<n>.md` for a
  new document, `<dir>/feedback/<stem>-<date>-v<n>.md` for the two existing layouts. Dated and
  versioned, never stamped with the time — `manuscript._next_version` is the rule. Tracked, so it
  crosses machines. A note may carry a page number, since the reader is looking at a page when
  they write it.
- **An id, never a path.** What arrives from the browser is compared against what `library.py`
  discovered, and a miss is a miss. `reading.find` is the rule and `/result/` is the worked
  example.

**Check.** A new `board/test/library.js` for the page, in the shape of `test/pages.js`; the route
and the feedback write in `board/test/library.py`.

---

## 6. Feedback has to change the document, and that is where the two kinds part

**Now.** Nothing acts on feedback because there is no feedback. This is the change that decides
what the library *is*, so decide it before writing any of it.

**The two kinds are changed by different machinery.**

- **A board-made explainer** — a `.tex` under `writeups/` the board compiled — is revised by the
  board.
- **A Paper-Writer manuscript** — delivered into `manuscripts/` — is revised by Paper-Writer.
  `manuscript.submit` is the seam and it only knows how to ask for a NEW paper:
  `projects/Paper-Writer/PROMPT_TEMPLATE.md` has `Evidence`, `Claims`, `Venue`,
  `Reporting checklist`, `Scope` and `Anything the harness cannot work out`, and no revision
  section at all. **That half is a change in Paper-Writer's own repository** — a `## Revision`
  section naming the delivered document and the feedback file — with `manuscript.revise(root,
  document, feedback)` beside `submit` on this side. Until it exists, a revision is a fresh job
  carrying the feedback in the free-prose section and the existing prose in the do-not-rewrite
  list that `_sections` already builds.

**Do not route an explainer through Paper-Writer.** It is a manuscript factory with gates for
venue, claims, citations and a reporting checklist. "How the serve harness works, and the
arithmetic behind the batch size" has no venue and makes no claims, and every one of those gates
would either refuse it or invent something to satisfy itself.

**The decision, and it is the one that matters.** A revise turn runs on the same daemon as the
lesson, and `turn_plan` in `bin/tutor` resumes the agent's conversation by default. A revision
resumed into a lesson drags the lesson into the document and the document back into the lesson.
So a `[revise]` turn must run **fresh** — `turn_plan`'s `fresh` path, its own session — and must
write no card: its report goes back to the library, not onto the glass. The alternative is a
second daemon per workspace, which doubles the cost and the failure modes for a turn that takes
a minute. Prefer the fresh turn.

**And that is what makes the library a separate interface rather than a sitting.** Feedback from
it never writes to `live/cards/`, never archives the lesson, and never changes `state.json`.
Somebody mid-proof on an iPad is not interrupted by somebody correcting a deck.

**Where.** `bin/tutor` — `turn_signal` (~968) already reads the signal off the inbox line, and
`turn_plan` (~932) is where fresh-versus-resumed is decided. `board/tutorboard/manuscript.py`
for `revise`. `routes/` for the dispatch. `projects/Paper-Writer/PROMPT_TEMPLATE.md` for the
other half, shipped separately with its own pathspec.

**Check.** A new `board/test/revising.py`: a `[revise]` line takes the fresh path, writes no
card, leaves `state.json` byte-identical, and lands its report beside the document.

---

## 7. A revised document is served from the service worker's cache, one page at a time

**Now.** `LIVE` in `board/web/sw.js` (~70) sends `download/`, `view/`, `paper/`, `result/`,
`figure/` and the rest straight to the network. **`doc/` is not in it.** `/doc/<id>/<page>.png`
is deliberately the *stable* address — `routes/taking.py` says so where it refuses to cache it
server-side, because a card written last month has to survive the deck being rebuilt — so it
falls through to the shell rule, which caches any 200 it sees.

That is the same mistake the file's own comments describe twice, in the third place, and every
change above makes it bite: a document revised on feedback is rebuilt at the same name, and the
person who asked for the change is served the page they asked to have changed.

**Want.** `doc/` in `LIVE`. Bump `VERSION`.

**Check.** `board/test/offline.js` reads `sw.js` and asserts the rule. It already does this for
the others; add the case.

---

## Settled, so nobody re-derives it

**The previous six changes are done.** `scripts/tool.sh` holds `tool_prefix` and `tool_root` and
both scripts read them. `tutorboard/fenced.py` is the one list, and `reading.py` reads it.
`plan._collect` takes `STEP` and `- [ ]` together in file order, with `_distinct` settling the
label collisions, and `MAX_STEPS` is 24. `course/results.py` and `/result/` put a figure on the
glass. `map._unclaimed` gives a written map its document boxes. `paper1-trd-prediction` has its
PDFs and `reading.py` finds them with no board change at all.

**`mode` is gone and is not coming back.** `config.read_config` reads and drops it; four
`tutorboard.json` files still carry `"mode": "math"` or `"mode": "code"` and it means nothing.
A default style is declared per family in `atlas.json`, not per repository in a `mode`.

**Aim and stance are not two settings to be set two ways.** One is derived from the other —
`AIM_STANCE` in `config.py`, change 2 — and the browser sends neither on its own authority.
