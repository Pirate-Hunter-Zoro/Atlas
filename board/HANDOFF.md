# HANDOFF — the written map, and what the map taught us

> **You are in Tutor-Board, in a fresh session, and you have been pointed at this file.**
>
> The map is built and shipped. A course opens on a diagram of its own working parts, the
> outstanding work is drawn on it, and tapping anything offers six ways to work on that part.
> **One piece of the original brief is left — the WRITTEN map — and it is §4.**
>
> This file was rewritten on 14 September 2026, replacing a 6,000-word brief for work that is
> now done. What is here is what is still true and what is still missing. Read §0 and §1 before
> you touch anything; read the rest as you need it.
>
> *(This is not a `board handoff` file. Those are capped at 350 words, live in a course, and are
> read by every turn's briefing. This repository is the tool rather than a course — `machines.py`
> excludes it from the course list — so nothing reads this automatically and the cap does not
> apply. It is deleted when §4 is done; see §8.)*

---

## 0. Before anything, and none of it is negotiable

**The person who asked for this uses the board while you change it**, on an iPad, in the middle
of real work. A regression does not annoy them later; it stops the lesson now.

- **Ship, do not merely commit.** `bash scripts/ship.sh "message"` commits, pushes, and restarts
  every board. A board is a long-lived process that read `serve.py` when it started, so a commit
  alone changes nothing for them.
- **Bump `VERSION` in `web/sw.js`** when any shell file changed (`board.html`, `board.js`,
  `board.css`, `plane-core.js`, anything new you add to the cache list), or the installed app
  serves its cached copy and your work is invisible. It is at `board-shell-v100`.
- **Run `bash test/all.sh` before every ship.** 29 suites, all green right now. Keep them green.
- **The lesson must always be reachable.** Every surface you add is one somebody can be stranded
  on mid-proof.
- **Commits here are authored by the person, with no assistant trailers.** `ship.sh` handles it.
- **Do not "fix" things you notice in passing.** One change, shipped, checked, then the next.

---

## 1. What the last four sessions learned, because it will happen to you too

Everything below was found by the person using the thing, usually within an hour of it shipping,
and each one is a rule now rather than an anecdote.

- **A list is not a diagram.** The map's first version drew the plan's steps in a column.
  Rejected: *"I don't want just a list of all the TODOs. I want a map of the CONTENT in the
  repository."* The boxes are the repository's parts; the work is drawn ON them.
- **Estimated text overflows.** Labels were wrapped by counting characters against an assumed
  width. A line of capitals is half again wider than that, so the words ran out of their boxes:
  *"that visual is shit."* Text is measured with a canvas now, and cached.
- **One direction is one direction whichever axis it is on.** The column was rejected; a
  twenty-chapter chain then laid out 6,600px wide, which is the same failure sideways. Long rank
  sequences wrap into bands of six.
- **A rule that is right for one kind of turn can be exactly wrong for the other.** Three
  separate defects, all this shape: the card-first rule produced a plan and no code; the busy
  strip hid on the card a doing turn OPENS with; a 900-second timeout killed a doing turn
  mid-flight. In each case the fix was to scope the rule, not to weaken it.
- **A second tap is ceremony.** Choosing "write the code for me" opened the sitting and then left
  them looking at *ask the tutor to begin*. Found as a question — *"do I ask the tutor to
  begin?"* — which is the worst way to find anything.
- **A glyph is not a label.** A bare diamond did not read as "the map".
- **Nothing a reader can be waiting on may be silent.** A failure expired off the board on a
  15-minute clock, leaving a present-tense card over work that had stopped. A failure is news
  until something newer happens, not until a timer says so.

**The standing instruction behind all of it:** *"I'm tired of getting massive word dumps from you
when I need you to explain how something works in these repos."* If a change ends with more
prose on screen rather than less, it has gone wrong.

---

## 2. What exists now

### 2.1 The map

| | |
|---|---|
| `tutorboard/course/map.py` | 710 lines. `status(root, state, archived)`, `shape(root)`, `find(root, id)`. Discovers **parts** (directories holding source, rolled up past `MAX_NODES`), **arrows** (imports between them, counted), **work** (plan steps matched to the part they name). A box's `does` is its own package docstring. 30s cache; `MAX_SCAN`/`HEAD_BYTES` bound the only discovery on this board that opens files rather than listing them. |
| payload | `load_map` in `lesson/state.py`, one line in `hub.build()`. Key `map`, version 2. |
| renderer | the map block in `web/board.js`: measured text, layered graph (ranks from dependency depth with cycle-closing edges left out of the ranking, four barycentre passes), bands of `MAP_RANKS_ACROSS`, chips, one column below 640px. |
| the plane | `web/plane-core.js` — contacts with expiry, pinch pair, clamp, zoom, frame. **Shared with `slate-core.js`**, which delegates to it. Not a fork. |
| the sheet | `openWork` / `takeWork` in `board.js`, `#work` in `board.html`. Six ways plus "show me the document". |
| the way back | `.to-map` controls in the bar, every drawer head, the document viewer; `?map=1` from `/slate`. |
| landing | `board.where.<course>` in `localStorage`: surface, plane `x/y/k`, last box. |

What it draws today: PSYCH-ASR 13 boxes / 19 arrows / 4 chips / 4 in the tray · TRD-EHR 25/30/1/4
· Galois-Theory 40/30 · Paper-Writer 13/26 · Probability 14/10 · Algo-Solutions 5/2 ·
libr-local-llm 4/0/0/5.

### 2.2 Sittings, and what a turn is told

`state.json` carries `session` ∈ `lecture | homework | review | walk | make`, plus `chapter`,
`node`, `aim`, `makes`, `stance`, `review`/`walk` scopes, `hw`.

- **`aim`** ∈ `teach · build · coach · trace · drill · paper · slides` — `course/config.py`,
  with `AIM_MEANS` saying in writing what each asks of the tutor. Chosen on the map.
- **`make`** is a sitting whose product is a document. `board open ... --make paper|slides`.
- **`sense.py`**: `PLAIN_SENSE` (how every card reads, in every briefing), `DOING_SENSE` (the
  order of a turn that does the work — and it says outright that it overrides `TEACHING.md`),
  `node_sense` (the box, its purpose, its files, its steps, its document), `aim_sense`,
  `MAKE_SENSE`.
- **`board write --over <card>`** replaces a card in place, which is what lets a doing turn open
  with one sentence and write the report over it. `--title` is a real option now.
- **`POST /session` takes `begin: true`** and starts the turn itself. The map's sheet sends it;
  the contents drawer does not.
- **`doing_timeout: 3600`** in `bin/tutor`, chosen per turn by `turn_timeout(cfg, root)`.
- A failure stays on the board until something newer lands: `state._failure` / `_newest`.

### 2.3 Tests

29 suites in `test/all.sh`. The ones that will bite you: **`test/map.py`** (the three
discoveries, arrows being real imports, a chip only where a step names the part, ids looked up
never constructed, build under a second), **`test/map.js`** (real DOM: every label inside its
box, ranks, bands, chips, the sheet's six bodies, the landing rule), **`test/teaching.py`** (the
method, the doing-turn shape, `--over`, the per-turn clock), **`test/panic.js`** (the way back,
one check per surface), **`test/hanging.js`** (nothing a reader waits on is silent),
**`test/plane.js`** (the shared plane, both halves).

---

## 3. What the map is for, in the person's own words

> "The tutor should create a massive diagram of the repository, with its various working parts.
> This diagram should mark what's completed, what's still being done, etc… I want to be able to
> tap on something and have some options. Maybe I want to learn about it. Maybe I want to
> vibecode some progress. Maybe I want to be told what to code and do it myself. Maybe I want to
> work some problems on it… when going into a course/repo, I should start with the visual map of
> everything."

> "A TODO is a tutoring session. All tutoring sessions should have the capability of being a math
> tutor, a coder, a coding coacher, a presentation creator, a paper creator, and the ability to
> show any or all sections of said papers or presentations."

All of that is built. The half that is not is the next section.

---

## 4. WHAT IS LEFT: the written map

**Structure is derived from disk. Meaning is written by the tutor. Neither is guessed.** The
derived half is done and it is honest — but nothing on disk knows that the grid search is
half-built, or that the scorer is blocked on a seam that does not exist yet. A directory listing
cannot say it, and a model asked to redraw the whole map every turn would disagree with itself
between turns.

So: **`live/map.json`**, written once by the tutor and kept up to date by it, merged against
discovery on every read.

### 4.1 What it adds that discovery cannot

A node that is a **stage of the work** rather than a directory. For PSYCH-ASR its owner's own
names are *the typist*, *the stopwatch*, *the name-tagger*, *the corrections*, *the grader*, *the
grid*, *the scorer* — which is how they talk about it and is not derivable from a directory
listing. Each such node *carries* the files it is made of, so every tap on the sheet works
unchanged.

And the three things nothing sets today: `blockedBy`, `doc` + `slide` on a part, and edge
labels that say what flows (`words`, `turns`, `a graded transcript`).

### 4.2 The schema, against what the renderer already reads

```json
{
  "version": 1,
  "title": "Stage 1 — audio to a graded transcript",
  "nodes": [
    {
      "id": "typist",
      "name": "the typist",
      "also": "faster-whisper large-v3",
      "kind": "part",
      "does": "Turns the waveform into words. One candidate, never compared.",
      "status": "working",
      "files": ["psych_asr/cli/run_asr.py", "psych_asr/asr/align.py"],
      "dir": "psych_asr/asr",
      "doc": "stage2-reference-walkthrough",
      "slide": 7,
      "blockedBy": ["seam"],
      "note": "five of the six error labels are a property of this box alone"
    }
  ],
  "edges": [{"from": "typist", "to": "stopwatch", "label": "words", "weight": 3}]
}
```

Every field except `blockedBy` is already in `_node()` and already painted. `kind` is
`part · doc · chapter · set`; `status` is one of `map.STATUSES`; `does` is capped at `map.DOES`
(110) because it is read inside a box on a tablet.

- `id` — `[a-z0-9-]{1,40}`, stable. Everything keys off it, including the remembered "where you
  are" in `localStorage`.
- `name` — **the plain name leads**; `also` carries the real identifier. Same rule `TEACHING.md`
  already imposes on a walkthrough, and the thing the person's own 33-slide deck does that makes
  it the plainest document in the project.
- `files` — re-resolved against `walk.units` on read. A `path::symbol` entry is allowed and goes
  straight to `walk.resolve`.
- `status` — `blocked` requires `blockedBy`. Nothing sets `blocked` today.

### 4.3 The merge, and it is the whole safety argument

**`live/map.json` is merged against discovery on every read, never echoed back.** A node naming
a file that no longer exists drops the file; a node whose files have all gone drops out; an edge
naming an id that is not there is not an edge. That is the same rule as `walk.scope` and
`review.scope`, and it is why a written map cannot rot into a lie: *a fact cannot go stale, a
declaration can, so a declaration is checked against the facts every time it is read.*

Where a written map exists it **replaces** the derived one — do not merge the two sets of boxes,
which would put `psych_asr/asr` and *the typist* on the same picture saying the same thing twice.
The derived map stays as the fallback for every repository nobody has drawn, which is most of
them.

Track `live/map.json` in git like the rest of the transcript, so the map a machine draws is the
map every machine draws. Add it to the allowlist block in the course `.gitignore` documented in
README §"Setting up a course repository".

### 4.4 `board map`

```
board map < map.json      write live/map.json (validated, rejected loudly if not valid)
board map --show          print it
board map --check         say what is stale: nodes naming files that are gone, steps that no
                          longer exist, documents that moved, ids an edge names that do not
                          exist, and a node marked `done` whose plan step is still open
```

Same shape as `board note` and `board handoff` — JSON on stdin. Reject loudly: a half-written map
that silently becomes the front door of a course is worse than none.

### 4.5 Who writes it

**The tutor, on request, in a sitting.** Do not try to generate it in Python. Make it a
documented thing a person can ask for — *"draw the map"* — and have `TEACHING.md` say how: read
the README and the plan, name the boxes the way the project's own documents name them, one
sentence each, and stop.

`board brief` must tell a tutor whether this course has a map and when it was last written.
`TEACHING.md` gains a short section: **keeping the map true is part of finishing a piece of
work**, exactly as updating the plan already is. A map that is a lie after three commits is worse
than no map, because it *looks* authoritative.

Write PSYCH-ASR's by hand as the worked example, from its README, its plan and its Stage-2 deck.

---

## 5. Smaller things known to be missing or wrong

- **Git recency is deliberately absent.** `lesson/git.py` already talks to git; a node whose
  files changed in the last few days could carry a subtle mark. It must never be a *status* —
  touched is not progressed, and painting them alike would make the map agree with whatever was
  edited last.
- **`#panic` is z-index 62, the map is 96 and the document viewer 95.** So the re-centre button
  is painted over by both. Pre-existing for the viewer; left alone deliberately, because raising
  it changes a shipped surface. If somebody gets stranded pinch-zoomed on the map, this is why.
- **Job logs and PHI.** The user-level guard at `~/.claude/hooks/block-phi.py` fences the
  PSYCH-ASR session data properly — by filename shape and by directory, quote-aware, and it
  refuses the arm-comparison CLI because running it prints transcript text to stdout. It allows
  the job-log tree on the understanding that jobs print counts rather than text, and that holds
  only while nothing in the pipeline logs a transcript line. Worth adding that tree to the guard
  with a counts-only exemption.
- **`reading.documents` on the map is capped at 8** and document boxes stand apart, wired to
  nothing. A written map could attach them to the part they explain.
- **TRD-EHR draws 25 boxes.** Legible, but near the edge of being a picture. If it gets worse,
  lower `MAX_NODES` rather than dropping boxes — `_rollup` draws the same repository coarser.

---

## 6. UI rules that still bind

- **A drawer's list is the part that scrolls**: `flex: 1` *and* `overflow-y: auto`, both.
  `test/chrome.js` asserts it for six of them.
- **The title bar holds six controls.** `test/link.js` refuses a seventh. A label that gets cut
  in half is a label whose second half was the useful one.
- **`[hidden]` loses to any author rule that sets a `display`.** Toggle `el.hidden`;
  `test/hidden.js` guards it.
- **Every colour is a token**, defined in *both* blocks at the top of `board.css`. A colour in
  one block is half the board changing theme and the other half not.
- **Phone width is 390px** and `body` never scrolls horizontally.
- **The layout is deterministic.** No viewport-dependent geometry: the same repository must lay
  out identically on every device, or it is not a map you can learn.
- **Gestures**: read `plane-core.js` before writing a `pointerdown`. A gesture is decided by
  which contacts are LIVE; a non-passive `touchmove` makes the browser ask the main thread before
  scrolling a pixel; two fingers are never the pen.

---

## 7. Traps, each one already paid for

- **`board open` is the only thing that opens a sitting.** Writing `state.json` directly skips
  the archive and the handoff parking, and loses the lesson being left.
- **Nothing is registered.** If you find yourself writing an index or a list that has to be kept
  in step with reality, stop — read the thing itself. `live/map.json` is the one exception,
  because it carries *judgement* no file contains, and even that is re-resolved on every read.
- **A name from a browser never reaches a filesystem.** Look it up in what discovery found;
  a miss is a miss. `walk.resolve`, `reading.find`, `map.find`.
- **A path out of a file is untrusted**, including out of a README. `plan._resolve` and
  `reading._pointed_at` bound themselves to the repository and its siblings under the same home.
- **The payload is polled four times a second.** Cache anything that touches disk.
- **`map` is a builtin.** The module keeps the name; every import binds it as `mapping` or
  `course_map`.
- **Nothing in `render()` may throw.** `paintMap` is wrapped for exactly this reason: a map that
  threw would stop the lesson painting, which is a blank board mid-proof caused by the one
  surface they were not using.
- **A doing turn and a teaching turn are different shapes.** Before you make any rule about the
  order of a turn, ask which one it is for. Three defects in one day came from not asking.

---

## 8. Done, and what to do then

§4 is done when a tutor can be asked to draw PSYCH-ASR's map, `board map --check` says what has
gone stale in it, the board draws *the typist* and *the scorer* with an arrow between them
labelled `words`, and tapping *the scorer* still offers the same six ways to work — over the
files that node carries.

Then **delete this file** — `git rm HANDOFF.md` — and fold what survived into `README.md` as a
section and into `TEACHING.md` as the rules for keeping a map true. This file is scaffolding. A
repository that keeps its scaffolding accumulates two descriptions of itself that disagree, which
is exactly why this one was rewritten rather than appended to.

---

## 9. Context you would otherwise rediscover

- **The repositories**, siblings in the home folder: `PSYCH-ASR` (spoken-therapy ASR pipeline,
  its plan now in its own tree under `planning/`), `TRD-EHR` (EHR causal pipeline and a
  manuscript), `libr-local-llm` (local inference infrastructure), `Paper-Writer` (a manuscript
  factory), `Algo-Solutions` (LeetCode, Go, 188 files), `Galois-Theory` and `Probability` (book
  courses with `chapters.tsv` — **these two already work well; do not regress them**),
  `Lean-Theorem-Proving`, `Mathematical-Modeling`. **`Research-Journey` is gone** — the narrative
  hub was retired into PSYCH-ASR on 13 September, so anything in the history about a hub holding
  three projects' plans is history.
- **The machine** is a Slurm compute node, no root, shared home. Standard library only in Python;
  plain browser JavaScript; nothing that needs a package manager at runtime. jsdom is a
  development-only dependency and `test/all.sh` fetches it.
- **Every turn is its own session.** `session_turns: 1` in `bin/tutor`: a fresh `claude -p` that
  reads `board brief` and `board recap` off disk, ~22k tokens whether it is turn 2 or turn 40.
  What the last turn was thinking is carried in `live/NEXT.md` by `board note`, not in a
  conversation. Do not change this without reading the arithmetic in the comment above it.
