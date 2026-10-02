# HANDOFF — projects are threads

**A project's spine is deliverables, and threads under them.** Each workspace with one keeps
it in `threads.json`. A sitting is learn, coach or build on one thread, status is derived from
disk, jobs report themselves, a turn ends on a report, and a save commits only its workspace.

`board/README.md` is the architecture. `board/SETTLED.md` holds the rules already built.
This file says what is left to build, and the work the build is for.

---

## How to work from this file

1. Each item heading says what it depends on. Items with no dependency between them can go to
   parallel agents. Give each agent its own worktree and one item, and let it ship its own item.
2. Read the whole item before touching code. Each one names the existing code to extend.
   Extend that code. A second mechanism beside an existing one is how this repository ends
   up with two maps.
3. `bash board/test/all.sh` must be green before and after. Bump `VERSION` in
   `board/web/sw.js` if a shell file changed. Ship `board/` with `bash board/scripts/ship.sh`.
   Ship everything else with `bash board/scripts/save-and-push.sh "msg" -- <paths>`.
4. When an item lands, delete it from this file. Write its rule into `board/README.md` in the
   present tense. Renumber what is left.
5. If part of an item proves wrong once the code is in front of you, leave that part here with
   one line saying why. Do not drop it quietly.

## Before anything

- **The PHI rules in the root `README.md` bind every item here.** `board/test/tracked.py` must
  stay green. It needs the private `ai-config/`, which a fresh worktree lacks; `tracked` and
  `colibri` fail there for that reason alone.
- **Leave the serving chain's files alone:** `tutor serve`, `tutor watch`,
  `tutorboard/supervise.py`, `slurm/tutor-serve.sbatch`, `test/perpetual.py` and the
  `serve_*` keys. `watch_once` is not where a job poll goes.
- Provider keys live in `~/.config/tutor-board/keys.env`. If an item needs a key that file
  lacks, say so in one line naming the path.
- `projects/libr-local-llm/HANDOFF.md` is that project's own handoff and stays live.

---

## What to build

### 1. The owner confirms the thread files — depends on nothing; the owner's

TRD-EHR, PSYCH-ASR and libr-local-llm carry drafted `threads.json` files, and
`board thread --check` is clean on each. Nobody has confirmed them.

- Put one card in front of the owner per workspace, listing deliverables and threads, for one
  round of corrections. Apply them with `board thread`.
- `research/PSYCH-ASR/planning/PSYCH-ASR_TODO.txt` and
  `projects/libr-local-llm/planning/LOCAL-LLM_TODO.txt` still exist. Their next steps are
  thread tasks already. The rest is standing PHI and hard-constraint context that fits no
  thread field, so the owner decides where it goes before either file is deleted.

### 2. A proposed thread is accepted with one tap — depends on nothing

A rethink that names a new question proposes a thread in its report, and it is added with
`board thread add` once the owner says yes in words. A card has no way to run a command when
tapped. This needs a route and a control on the card, so it touches shell files.

### 3. The thread sheet dispatches a mission — depends on nothing

`POST /elsewhere` accepts and validates `thread`, and the mission record carries it. Nothing on
the glass sends one. Add the control to the thread sheet (`map.thread_sheet`, the sheet in
`board.js`), so a mission started from a thread says `running` on that box.

### 4. A stopped card says what the thread left — depends on nothing

`cards.stopped_body` and `write_stopped` take a jobs list and `lesson.git.uncommitted` takes
paths, but `report_owed` in `bin/tutor` passes no jobs and the whole workspace.

- List `git status` under the sitting's thread's paths (`files`, `outputs`, `writes` files),
  falling back to the workspace with no thread.
- List the jobs registered to that thread since the turn began (`jobs.registry`).
- A thread box whose newest sitting card is `kind: stopped` carries a badge.

### 5. A turn's commit is checked against the thread file — depends on nothing

`board push "<thread>: msg" -- <paths>` takes the thread name as the turn writes it. Check the
prefix against `threads.json` where one exists, and refuse an id it does not declare.

### Left as they are

- `board/bin/tutor` still has a comment naming `live/map.json`. It is in the serving chain, and
  the line is a comment only.
- `board/AI_INSTRUCTIONS.md` carries no `board job` rule. It is the contract for developing the
  tool, not one a turn's brief reads; the eight workspace contracts carry it.
- A course shares only the map frame with a project. Its sittings, brief and next step still
  come from `chapters.tsv` through the syllabus code, because a chapter sitting already knows
  its chapter and a synthesized thread file would duplicate that without changing what is shown.
- The assistant memory note `a-live-lesson-commits-your-board-work` describes a save that
  sweeps the whole tree. Delete it and its `MEMORY.md` line once this build ships.

---

## After the build: the work it is for

In this order. Each is a thread in the drafted files, and its open tasks are on its box.

1. **Paper 1** (`research/TRD-EHR`, deliverable `paper1`).
   - `knn-across-embedders`: the section, Figure 5 and the cross-encoder figures are written.
     Open: discuss the dimension-count vs best-k scatter (it stays out of the write-up until
     then), fix the last *importance-weighted* in `plot_neighbor_sweep_figure.py`'s docstring,
     re-split `parts/`, and a learn sitting on the shape of the k-sweep.
   - `reviewer-findings`: Martin's open questions, the three staged word changes once his text
     settles, the paper reviewer over the KNN section, and the TRIPOD+AI rows.
   - `consistency-pass`, blocked by `reviewer-findings`: clarity pass, cross-document numbers,
     refs 10 and 12 at proof, and a strict packet rebuild.
2. **The Colibri deck.** Learn sittings on `phi-path` and `libr-hardware` first, so the owner can
   defend every slide. Then build `phi-deck`.
3. **PSYCH-ASR `grid-sweep`**, built by agents through `board job`, and the owner's
   `recording-review` task.
4. **Paper 2.** Learn sittings on `estimand-identification`, then coach sittings on the four
   robustness rungs, then build.

---

## On the glass — the owner's, not a build

These are built and have never been used for real. Strike each one after an evening on the iPad.

- The thread map: frames, coloured boxes, chips, and a tap opening a sheet that asks learn,
  coach or build.
- A `[job]` card waking a turn when a `board job` ends.
- A `working` card that ends on a report, and a `stopped without a report` card.
- Zoom and palm rejection on a paper and a deck, and whether ink stays on its words through
  a pinch.
- One document all the way round: ask, compile, read, ink, complain, revise.
- The round as pairs on the TRD-EHR manuscript: its 09-29 round is round 1, backfilled. Tap the
  chip, a row and a pip, and mark pairs fine or not fixed.
- The meeting deck written by a real turn.
- Sending selected annotations.
- A response typing out, and the typed half of the answer panel, in a real sitting.
- Whether the verdict band and streak chip feel like information or like a scoreboard.
