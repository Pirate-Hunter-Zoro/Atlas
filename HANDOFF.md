# HANDOFF — six changes to the board

Six gaps between what the board does and what it is used for. Five came from asking three
questions of the TRD-EHR map: where is the e(x) histogram TODO, how do I read the paper, and how
do I reach PSYCH-ASR's decks. The sixth came from shipping the answer to the first. Ordered
smallest first. **One change, shipped, checked, then the next** — that is the repository's rule
and it is the right one here, because four of these touch the same three modules.

Each section says what is true now, what should be true, and where. Nothing below is a plan for
a plan: the paths are real and were read, not guessed.

---

## Before anything

- `bash board/test/all.sh` — 71 suites, about twelve minutes. Green before and after.
- Bump `VERSION` in `board/web/sw.js` whenever a shell file changes (`board.html`, `board.js`,
  `board.css`, and the rest of the cache list), or the installed app serves its cached copy.
- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and restarts every
  running board. Anything outside `board/` goes through
  `bash board/scripts/save-and-push.sh "message" -- <paths>` with a pathspec.
- Commits carry no assistant trailers. `.githooks/commit-msg` strips them.

**The working tree is not clean, and what is in it is somebody's unfinished afternoon rather
than anything below.** `TEACHING.md`, `bin/board`, `test/all.sh`, `test/homework.py`,
`tutorboard/brief.py`, `course/homework.py`, `server/hub.py`, `routes/writing.py`, and two
untracked `burn.py` files under `course/` and `test/`. None of it belongs to these six changes,
so ship with a pathspec or ask before ship.sh sweeps it up under one message.

---

## 1. A direct `save-and-push.sh` does not bounce the boards it just changed

**Now.** The tail of `board/scripts/save-and-push.sh` asks *did this commit touch the tool*, and
asks it of the wrong directory. `TOOL_REL` comes from
`git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-prefix`, and the script's own directory
is `board/scripts`, not `board` — so the test is `grep -q "^board/scripts/"` over the commit's
files and a change to `board/tutorboard/` or `board/web/` never matches. `ship.sh` gets this
right two lines from the same idea: it derives its prefix from `$HERE`, which is `board`.

There is a second way to get nothing, and it is quieter. `BASH_SOURCE[0]` is the path as typed,
the script has already `cd`'d to the repository root, and `git -C` resolves a relative directory
against *that*. Run it as `cd board && bash scripts/save-and-push.sh` and `git -C scripts` fails,
`TOOL_REL` is empty, and the `[ -n "$TOOL_REL" ]` guard skips the restart without a word.

`ship.sh` is unaffected in practice — it calls `tutor restart --tutors` itself, and that restarts
boards as well as daemons. What is affected is every direct caller: the board's own save button,
`board finish`, and `lesson/git.py`. Tap save with an uncommitted tool change in the tree and the
commit lands, the push lands, and every board goes on serving the old Python from a page that
looks new. That is the exact failure the comment above the block describes and costs an evening
to find.

**Want.** The prefix is the tool's own, derived once and correctly, and a relative invocation
from any directory reaches the same answer. Consider deriving it in one place both scripts read,
since they are now computing the same value two ways and only one of them works.

**Where.** `board/scripts/save-and-push.sh`, the `TOOL_REL` block at the end. `board/scripts/ship.sh`
holds the correct derivation.

**Check.** `board/test/beside.py` already builds a throwaway repository and taps save on it —
that suite exists because this same block was wrong in a different way. Extend it: a commit
touching `board/` reports the restart, one touching only a workspace does not, and both hold
when the script is invoked by a relative path from inside `board/`.

---

## 2. `reading.py` does not fence `phi`, and the tutor is handed what is inside it

**Now.** `reading.IGNORE` in `board/tutorboard/course/reading.py` lists `live`, `results`,
`data`, `archive` and the usual build directories. It does not list `phi`.
`reading.documents("research/PSYCH-ASR")` therefore returns `phi/stage1/Audio Transcription.pdf`
under the id `audio-transcription`, the drawer offers it, `paper.pages_of` will render it to
PNGs in `live/paper/`, and `sense.reading_sense` writes its `/doc/` address into the tutor's
prompt alongside an instruction to open and read a page before showing one.

`tutorboard/manuscript.py` already refuses this by name — its `NEVER` list is `phi`, `data`,
`inbox`, `stage1`, `stage2`, `raw`, `audio` — so the manuscript factory cannot mine the tree the
document drawer hands over freely. The two should agree, and the agreement should be one list
rather than two that drift.

**Want.** A document under a fenced directory is never found, never named to a tutor, and never
rendered. The refusal is by directory name at any depth, the way `manuscript.NEVER` works, and
it does not depend on `MAX_DEPTH` or on a size floor happening to exclude it.

**Where.** `board/tutorboard/course/reading.py` (`IGNORE`, `_ours`, `_in_repo`, `_pointed_at` —
the README-pointer path needs the same refusal, or a README naming a deck inside `phi` walks
straight past the directory test). `board/tutorboard/manuscript.py` holds the list worth reusing.

**Check.** `board/test/plan.py` is where `reading` is covered. It builds a sandbox repository
with a reference library in it; add a `phi` directory with a fat PDF inside and assert it is
offered nowhere — not by `documents`, not by `find`, not in `sense.reading_sense`, and not when
the sandbox README names it by path.

---

## 3. A plan's steps are read in one form only, so half of TRD-EHR is invisible

**Now.** `plan._collect` is called from `_steps_in` over `(("step", STEP), ("item", TODO_ITEM),
("heading", HEADING))` and **breaks at the first kind that matches anything**.
`planning/TRD-EHR_TODO.txt` opens with `STEP 1.` through `STEP 5.`, all about paper 1's
manuscript, so those five are the entire map. The file's thirteen unchecked `- [ ]` items — the
falsification battery, the 5-fold CV, the whole counterfactual half — reach the board nowhere.
A new checklist item written today is invisible for the same reason.

**Want.** Every kind of step a plan writes, in the plan's own order, from the block the plan says
to start at. Headings stay the last resort they are: a document with `##` sections and no steps
in it is a different case and reading its headings as tasks is what that branch is for.

**Decide before writing.** Three things fall out and none has an obvious answer:

- **Numbering.** `STEP` takes its `num` from the file; `- [ ]` gets a positional counter. Merge
  the two and step 1 collides with item 1. The `num` is shown on the chip and in `label`, and
  `label` is the key `/session` and `/plan/step` look a step up by, so it cannot be cosmetic.
- **`MAX_STEPS` is 12** and TRD-EHR would have eighteen. A drawer is not the plan; decide whether
  the cap rises, stays and truncates, or becomes per-kind.
- **Order.** File order mixes a `STEP 4` at line 47 with a `- [ ]` at line 1550 that carries
  `<<< RESUME HERE >>>`. The plan's own "what we do next" block is the answer for the first, and
  it is not obvious it is the answer for the second.

**Where.** `board/tutorboard/course/plan.py` (`_collect`, `_steps_in`, `MAX_STEPS`).
`map._attach` and `map._step_text` consume the result and window each step against the next one
*in the same file*, so mixed kinds must still produce a correct stop line — get this wrong and
chips land on boxes the step says nothing about.

**Check.** `board/test/plan.py`. Its fixture is a `STEP`-shaped plan; give it both forms and
assert the order, the numbering rule that gets chosen, and that a step's window still stops at
the next step whatever kind that is.

---

## 4. A results figure cannot be shown on the board

**Now.** `results/counterfactual_pipeline/<contrast>/propensity_by_arm.png` exists and cannot be
put on the glass. `reading.py` offers PDFs only and refuses `results` by name. `routes/pages.py`
serves `/static/` (the web directory), `/figure/` (compiled TikZ out of `live/tikzcache`),
`/uploads/` (the lesson inbox) and `/answers/`. Nothing serves an image out of the workspace. The
only route a figure has to the board today is somebody copying it into `live/inbox/uploads/`.

**Want.** A tutor can put a figure the pipeline produced into a card, and a person can open one
from the map, without a copy. This is the largest of the five and the one with the most ways to
get it wrong.

**Constraints, and they are the design.**

- **An id, never a path.** Same rule as `reading.find`: what arrives from a browser is compared
  against what discovery found, and a miss is a miss. A query parameter carrying a repo-relative
  path is a traversal waiting to happen.
- **An allowlist, with the `phi` refusal behind it.** `RESULT_DIRS` and `NEVER` in
  `manuscript.py` are the precedent, and change 1 should have made that list reusable.
- **Bounded.** A results tree holds hundreds of PNGs. `reading.MAX_DOCS` is 24 for a reason a
  figure drawer needs too.
- **Not cached by the service worker.** A figure is rebuilt at the same name by the next job, and
  a cached one served under a new name is last week's result wearing this week's label. `sw.js`
  sends `/download/`, `/view/` and `/paper/` to the network always; a figure route joins them.
- **The payload is polled four times a second.** Whatever discovery this needs is cached the way
  `reading.documents`, `walk.units` and `plan.steps` are — 30 seconds, off a bounded walk.

**Where.** A new module beside `reading.py` for finding them; `routes/pages.py` for serving one;
`sense.py` for telling a tutor the address exists, in the shape `reading_sense` already uses;
`web/sw.js` for the cache rule.

**Check.** A new suite, named for what it protects. Every traversal refused, every fenced
directory refused, the bound held, the cache rule asserted by reading `sw.js`.

---

## 5. A hand-written map has no document boxes

**Now.** `map._from_code` builds a node per document automatically — TRD-EHR's derived map
carries three, and tapping one offers *Show me the document*. `map._from_written` takes `doc`
only from what the map's author typed on a node, and blanks it when `reading.find` cannot resolve
it. PSYCH-ASR's `live/map.json` leaves every `doc` empty, so its two walkthrough decks — the
documents `reading.py` was written for — are on no box, and are reachable from ⋯ and nowhere
else.

**Want.** A written map shows the workspace's documents without the author hand-wiring each one,
and `map.check` says so when a document exists that no box claims.

**Decide.** Whether unclaimed documents become their own boxes on a written map the way they do
on a derived one, or whether `map.check` merely reports them and the author places them. The
first is less typing and risks a written map — which is a hand-drawn statement about a project —
growing boxes its author did not draw. The second keeps the map the author's and costs an edit
per deck. This is a judgement about what a written map *is*, so decide it before writing.

**Where.** `board/tutorboard/course/map.py`: `_from_written` (~909), the `doc` field's validation
(~892), `check` (~943), and `_from_code`'s document-node loop (~512) as the worked example.

**Check.** `board/test/map.py`.

---

## 6. The paper is not a document the board can show

**Now.** Paper 1 is `research/TRD-EHR/paper1-trd-prediction/manuscript.md` and `manuscript.docx`,
with `supplement`, `cover_letter` and `tripod_ai_checklist` beside it in the same two forms.
`reading.py` finds PDFs of at least 20 kB and nothing else, so the paper is on no map, in no
drawer, and cannot be read on the iPad. The board renders PDFs and only PDFs — `paper.pages_of`
is the whole mechanism and it shells out to `pdftoppm`, `pdftocairo` or `gs`.

**Want.** The write-up is readable on the glass, as a document like any other.

**Two ways, and they are not close.** Rendering the packet to PDF keeps the board unchanged and
makes the paper a normal document, at the cost of a build step and a stale PDF whenever the
markdown moves ahead of it — and TRD-EHR rebuilds four packet documents as a deliberate step of
its own plan, so that build already exists to hang it on. Teaching the board to show markdown is
a second viewer, a second renderer, and a second thing to keep working, for a document the rest
of the workflow already converts. Prefer the first unless there is a reason not to.

**Where.** The TRD-EHR side, not the board: whatever builds `manuscript.docx` gains a PDF, and
`reading.py` then finds it with no change at all. Confirm that before writing any board code —
if it is true, this change is not a board change.

---

## Settled, so nobody re-derives it

**The e(x) histogram is built.** `results/counterfactual_pipeline/<contrast>/propensity_by_arm.png`,
per contrast: both arms overlaid on a shared unit bin grid, band edges at 0.10 and 0.90 drawn,
trimmed margins shaded, test set only. It is absent from `planning/TRD-EHR_TODO.txt` because that
file deletes finished entries by its own standing rule, not because it was forgotten. What is
still open beside it, and is written into the plan: whether the figure gains a train-side panel,
and whether the symmetric band stays or adapts to arm prevalence.
