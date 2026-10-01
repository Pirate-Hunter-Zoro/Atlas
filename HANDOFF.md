# HANDOFF — projects become threads

**A course works on the board because a book gives it a spine: chapters, in order, each one a
sitting. A project has no spine, so the board draws one out of the directory tree, and nobody
thinks about their research as `scripts-pipeline-predictions`.** This build gives a project a
spine of its own: **deliverables, and threads under them**. Learning, coached coding, building
and agents all hang off a thread.

`board/README.md` is the architecture. `board/SETTLED.md` holds the rules already built.
This file says what is left to build.

---

## The model

| Thing | What it is | Example (TRD-EHR) |
|---|---|---|
| **Deliverable** | Something handed to another person: a paper, a deck, a dataset, a decision | Paper 1, the TRD-prediction manuscript |
| **Thread** | One question or claim the deliverable needs, with its code, outputs and write-up | LR-weighted nearest neighbours across four embedders → Figure 4 and the KNN section |
| **Sitting** | One session on one thread, of one kind | A *learn* sitting on why AUC climbs with log k |
| **Job** | Long-running work registered to a thread: a Slurm job or an agent mission | The neighbour-count sweep on bge-small |
| **Decision** | A choice the science depends on, which the owner makes | How to count the dimensions an L2 fit uses |

**A course is the same model with its threads given.** The book is the one deliverable and each
row of `chapters.tsv` is a thread. A course writes no thread file. Its map, its sittings and
its "what is next" come out of the same code path as a project's.

**Every sitting has one of three kinds**, chosen when it opens and changeable mid-sitting:

- **learn** — a board lesson run by `TEACHING.md`: exercises, handwriting, a compiled write-up.
  No code. This is where the counterfactual mathematics and the prediction mathematics are taught.
- **coach** — the owner writes the statistical code and the tutor guides one step per card.
  The split follows the division of labour in the assistant contract. The owner writes
  estimators, resampling and validation, and any choice with a defensible alternative. The tutor
  writes figures, dataframe plumbing, serialization and job scaffolding without being asked.
  The tutor reads the owner's diff itself. It never assigns a check.
- **build** — the assistant or its agents do the work, and the card is a report. Paper and deck
  aims are kinds of build.

**A thread's status is computed from facts on disk, and only one part of it is typed.**
The stages are below, and the first true row wins:

| Status | True when |
|---|---|
| done | the owner closed it, which is one tap and the only typed state |
| running | a job registered to it is pending or running |
| written | every `outputs` path exists and every `writes` anchor is found in its file |
| result | every `outputs` path exists |
| open | otherwise |

Two flags sit beside the status. An **open decision** is a chip on the box. **Unsaved** means
git shows changes under any of the thread's paths. A tracked file has nothing to say on either.

---

## How to work from this file

1. Items 1 to 7 are the build. Each item heading says what it depends on. Items with no
   dependency between them can go to parallel agents. Give each agent its own worktree and
   one item, and let it ship its own item.
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
  stay green.
- **Leave the serving chain's files alone:** `tutor serve`, `tutor watch`,
  `tutorboard/supervise.py`, `slurm/tutor-serve.sbatch`, `test/perpetual.py` and the
  `serve_*` keys. Nothing here needs them, and `watch_once` is not where a job poll goes.
- Provider keys live in `~/.config/tutor-board/keys.env`. If an item needs a key that file
  lacks, say so in one line naming the path.
- `projects/libr-local-llm/HANDOFF.md` is that project's own handoff and stays live.

---

## What to build

### 1. The thread file — depends on nothing

Each project keeps one tracked file, **`threads.json` at the workspace root**. It does not go
in `live/`, because several workspaces ignore `live/` wholesale (TRD-EHR does), and git cannot
un-ignore a file inside an ignored directory.

It **replaces the written map** (`live/map.json`, handled in `course/map.py`) and absorbs it.
Each existing written-map node becomes a thread: `files`, `doc` and `blockedBy` carry over,
and `status` is dropped because status is derived now. Migrate PSYCH-ASR's and
libr-local-llm's `live/map.json`, then delete them.

The shape:

```json
{
  "version": 1,
  "deliverables": [
    {"id": "paper1", "title": "Paper 1 — predicting TRD from the EHR",
     "doc": "paper1-trd-prediction/manuscript.md"}
  ],
  "threads": [
    {"id": "knn-across-embedders",
     "deliverable": "paper1",
     "title": "LR-weighted nearest neighbours across four embedders",
     "question": "Does importance-weighted retrieval beat plain cosine on every embedder, and at what k?",
     "files":   ["scripts/pipeline/predictions/importance_weighted_knn.py"],
     "outputs": ["results/cross_embedder_retrieval/cross_embedder_retrieval.csv"],
     "writes":  [{"file": "paper1-trd-prediction/manuscript.md", "anchor": "## Nearest-neighbour retrieval"}],
     "tasks":   [{"text": "Draw dimensions-vs-importance figure", "done": false}],
     "decisions": [{"q": "How to count dimensions an L2 fit uses", "rule": "Fewest dimensions holding 90% of |coefficient| mass"}],
     "blockedBy": [],
     "closed": false}
  ]
}
```

- A decision with `"rule": null` is open. A rule is written in the present tense: it is what
  the work does now.
- `tasks` is where the project's next steps live. `course/plan.py` reads `threads.json` first.
  Once a workspace has one, its old TODO file is migrated into threads and deleted. One plan,
  not two.
- **`board thread`** writes the file, the way `board map` does: it validates and refuses the
  whole write with every problem listed. Subcommands: `--show`, `--check`, `add`, `task`,
  `done <task>`, `decide <decision> "<rule>"`, `close`. Turns edit threads only through it.
- Keep `course/map.py`'s resolution rule. A path that has gone drops out, and `--check` says
  aloud what the file claims that the tree does not.
- Status derivation is a pure function of the file, `git status`, the job registry from item 4
  and file existence. It lives beside `validate` and needs no network.

Tests: validation, migration of both existing maps, status derivation for every row of the
table above, and that the file is visible to git in a workspace that ignores `live/`.

### 2. The map draws deliverables and threads — depends on 1

- Each deliverable is a frame. Its threads are the boxes inside it, coloured by status. Chips
  on a box show open tasks and open decisions. `blockedBy` draws an arrow.
- **Code is never a box.** A thread's sheet lists its files, outputs, write-up anchors, jobs,
  past sittings (from the archive, by thread id) and documents. A file opens in the existing
  code walk (`#/w/…/code/<path>`). The directory-derived map remains only for vendor trees
  and for a workspace with no thread file.
- The deliverable's `doc` and every library document attached to a thread show in the map's
  documents region. The owner works from the map and expects every paper and deck on it.
- In a course, the frame is the book and the boxes are chapters, both read from
  `chapters.tsv`.
- **The atlas card's "next" line** becomes the first open task of the first thread that is not
  blocked, and it names the thread.
- Tapping a box opens a sitting on that thread. The sheet asks which kind (learn, coach,
  build) and defaults to the thread's last kind.

### 3. Sittings belong to a thread and have a kind — depends on 1

- `live/state.json` carries `thread` and `kind`, replacing `node` and the free-text chapter a
  rethink makes. Map the kinds onto the existing `stance` and `aim` (`tutorboard.json`,
  `brief.py`) rather than adding a third axis. Learn and coach are both the teach stance.
  Coach is told apart because the thread's files are code. Build is the do stance.
- `board brief` opens with the thread: its question, open tasks, open decisions, outputs, and
  the last sitting's report. A cold turn reads one thread, not the project's README and plan.
- Write coach mode into `board/TEACHING.md` as a short section. One step per card. Imports come
  first, in prose. The tutor writes the plumbing itself. The tutor reads the owner's diff and
  runs the check itself. **That rule is the one that stops a coach sitting turning into a
  build:** the tutor writes no code for estimators or validation design.
- **Rethink, in a workspace with a thread file**, attaches the owner's sentence to the current
  thread. The woken turn rewrites that thread's tasks with `board thread` and reports what it
  changed. If the sentence names a new question, it proposes a new thread on a card, and the
  owner accepts it with one tap. The lesson is still archived and the tutor still replaced, as
  now (`direction.py`). The sitting is named after the thread, never after the first words of
  the sentence.

### 4. Jobs are registered and report themselves — depends on 1

- `board job <thread> [--produces <path>…] -- sbatch <args>` submits the job and appends
  `{thread, jobid, cmd, produces, submitted}` to `live/jobs.jsonl`. Track that file. Add it
  to each workspace's `live/*` allowlist, or to the root of the workspace where `live/` is
  ignored wholesale.
- Missions (`tutorboard/missions.py`) carry a thread id the same way.
- The per-board tutor daemon in `board/bin/tutor` polls `sacct` for unfinished jobs each pass.
  On a terminal state it drops a `[job]` message in the inbox, which wakes a turn, the way
  `[direction]` does (`turn_signal`). The woken turn reports: what finished, what it produced,
  any non-zero exit. Then it moves the thread on. A failed job is reported with the tail of
  its log.
- The busy strip and the box both say "running" while a job is pending or running.
- Every assistant contract says: **a turn that starts long work submits it through `board job`**.
  A bare `sbatch` is work the board cannot see.

### 5. A turn ends on a report — depends on nothing

- A placeholder card ("this card is replaced by the report") is written with `kind: pending`
  in its front matter. `lesson/cards.py` already reads front matter.
- When a turn exits and the newest card is still `pending`, the daemon wakes it once more with
  `[unfinished]`. If that turn also leaves it pending, the card is replaced with a plain one:
  "the turn stopped without reporting; here is what changed on disk". It lists `git status`
  under the thread's paths and the jobs registered since. The box shows a badge.
- A report names any file it changed and left uncommitted. That way, the board's view and the
  disk cannot disagree without the card saying so.

### 6. A save commits only its own workspace — depends on nothing

- `board finish` and the lesson save (`lesson/git.py` around the `"lesson complete"`
  message, and `board/bin/board` near lines 1402 and 1524) commit with a pathspec limited to
  the workspace's own directory. They never include `board/` or another workspace, and never
  an `.nfs*` file. Commit `8137b751` swept board code and an NFS temp file into a TRD-EHR
  lesson commit, and that is exactly what this prevents.
- Work on the thread's paths is committed by the turn that did it, with a message naming the
  thread. "lesson complete" stays only for the transcript.
- Once this lands, delete the memory note `a-live-lesson-commits-your-board-work`, since it
  describes the defect.

### 7. Write the thread files — depends on 1; the owner confirms each one on the glass

Draft each one from the workspace's README, plan files and code. Run `board thread --check`
clean. Then put a card in front of the owner listing deliverables and threads, for one
round of corrections.

- **research/TRD-EHR.** Fold in `planning/TRD-EHR_TODO.txt`, `paper2-counterfactual/PAPER2_OUTLINE.md`
  and `CAUSAL_IDENTIFICATION.md`.
  - **Paper 1**, with threads for:
    - `knn-across-embedders`, below;
    - the reviewer findings and TRIPOD checklist;
    - the final consistency pass across the manuscript, the supplement and the cover letter.
  - **Paper 2: counterfactuals**, with threads for the estimand and identification (learn
    first), and for each pipeline expansion the outline names (coach for the statistics,
    build for the rest).
- **research/PSYCH-ASR.** **Stage 1**: the eight boxes of the current map become threads,
  renamed to what they are (transcription, word alignment, diarization, and so on, rather
  than "the typist"). A **grid-sweep** thread. A **diarized-recording review** thread whose
  one task is the owner's own: listening to the recording.
- **projects/libr-local-llm.** The existing map becomes threads. Add a deliverable, **the Colibri
  PHI-safety deck**, with threads for where PHI goes end to end, the LIBR hardware it runs
  on, and the deck itself.

---

## After the build: the work it is for

In this order. Each is a thread in item 7's files.

1. **Paper 1, `knn-across-embedders`.**
   - **Decided:** the per-embedder dimension count is the fewest dimensions holding 90% of
     absolute coefficient mass (`dimensions_holding_share`, `MASS_SHARE` in
     `plot_cross_embedder_retrieval.py`). The grid search picks L2 for bge-small and
     Qwen3-4B, and L2 zeroes nothing. So the non-zero count is reported beside the 90%
     count but never compared across embedders.
   - Five files are uncommitted in TRD-EHR: `importance_weighted_knn.py`,
     `plot_neighbor_sweep_figure.py`, `neighbor_count_sweep.sbatch`, `manuscript.md` and
     `supplement.md`. A sixth is new: `plot_cross_embedder_retrieval.py`. Read them, then
     commit them under this thread.
   - Run the cross-embedder figures and rename the method to "logistic-regression-weighted
     nearest neighbours" in labels and prose.
   - Write the KNN section. Report the dimension-count vs best-k scatter to the owner. It
     **stays out of the write-up** until it has been discussed.
2. **The Colibri deck.** Learn sittings first, so the owner can defend every slide. Then build
   the deck.
3. **PSYCH-ASR grid sweep**, built by agents, and the owner's listening task.
4. **Paper 2.** Learn sittings on the counterfactual mathematics, then coach sittings on the
   statistics, then build.

---

## On the glass — the owner's, not a build

These are already built and have never been used for real. Strike each one after an evening
on the iPad.

- Zoom and palm rejection on a paper and a deck, and whether ink stays on its words through
  a pinch.
- One document all the way round: ask, compile, read, ink, complain, revise.
- The edit ledger on a real round of the TRD-EHR manuscript.
- The meeting deck written by a real turn.
- Sending selected annotations.
- A response typing out, and the typed half of the answer panel, in a real sitting.
- Whether the verdict band and streak chip feel like information or like a scoreboard.
