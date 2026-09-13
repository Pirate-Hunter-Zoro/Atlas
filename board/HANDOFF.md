# HANDOFF — build the map

> **You are in Tutor-Board, in a fresh session, and you have been pointed at this file.**
> Your job is the one thing described here: make the **map** the way into every course.
> Read this whole file before you touch anything. It was written by the session that built
> the machinery you are going to put a face on, and every decision in it was made with the
> code open.
>
> *(This is not a `board handoff` file. Those are capped at 350 words, live in a course, and
> are read by every turn's briefing. This repository is the tool rather than a course —
> `machines.py` excludes it from the course list — so nothing reads this automatically and the
> cap does not apply. It is deleted at the end; see §9.)*

---

## WHERE THIS HAS GOT TO

**Phases 1 and 3 are shipped, and §4.2 changed after the first version was
rejected.** Read this before §4 and §6; the rest of the file is unchanged.

**What the map is now.** Not the plan. The first version drew `plan.steps` in a
column and was rejected: *"I don't want just a list of all the TODOs. I want a
map of the CONTENT in the repository… a fun kind of map/node graph like an
Entity relationship model."* So `tutorboard/course/map.py` discovers:

- **the parts** — directories holding source, rolled up until there are few
  enough to be a picture;
- **the arrows** — imports from one part into another, counted;
- **the work** — plan steps matched to the part they name, as numbered chips on
  the box, coloured by the plan's order. Unmatched steps go in a tray rather
  than being dropped or guessed onto a box.

A box's `does` is its own package docstring. §4.2's node schema is otherwise as
written, plus `kind` (`part` · `doc` · `chapter` · `set`), `dir` and `steps`.

**What else landed.** `web/plane-core.js` (§5.2, extracted from `slate-core.js`,
not forked). The layered-graph renderer: measured text, ranks from dependency
depth with cycles handled, barycentre ordering, bands of six ranks for long
chains, one column below 640px. §7 in full. The tap sheet (§4.8) with six ways
to work, the **make** sitting (§6 phase 4 — brought forward, because it was half
the ask), and an `aim` on `state.json` that `sense.node_sense`/`aim_sense` hand
to the tutor along with the box's purpose, files and steps.

**Still not built:** `live/map.json` and `board map` (§4.3, §6 phase 2) — the
written half, where a box is a stage of the work rather than a directory and an
edge says what feeds what. Everything a written map needs is already in the
schema and the renderer; what is missing is the CLI, the validation, the
merge-against-discovery on read, `--check`, and the `TEACHING.md` section on
keeping it true. Also absent: git recency as a mark (§4.4), and `blockedBy`.

`bash test/all.sh` is green. Shell `board-shell-v97`.

---

## 0. Before anything

**The person who asked for this uses the board while you change it**, on an iPad, in the
middle of real work. Three rules follow and none of them are negotiable.

- **Ship, do not merely commit.** `bash scripts/ship.sh "message"` commits, pushes, and
  restarts every board. A board is a long-lived process that read `serve.py` when it
  started, so a commit alone changes nothing for them. Bump `VERSION` in `web/sw.js` when
  any shell file changed (`board.html`, `board.js`, `board.css`, and anything new you add
  to the cache list), or the installed app serves its cached copy and your work is
  invisible.
- **Run `bash test/all.sh` before every ship.** It is green right now. Keep it green.
- **The lesson must always be reachable.** You are adding a new landing surface to a tool
  somebody opens mid-proof. If the map is broken, empty, slow, or confusing, there must
  still be one obvious tap that lands on the lesson — and a course with a lesson already in
  progress must not be made to go through the map to get back to it. See §7.

**Read, in this order, and nothing else up front:**

1. This file, whole.
2. `TEACHING.md` — §"A repository that is not a book", §"A walkthrough", §"Showing a slide".
   That is the teaching contract the map launches people into.
3. `tutorboard/course/plan.py`, `walk.py`, `reading.py`, `review.py` — the four discovery
   modules. These are your data. Read their module docstrings at minimum.
4. `web/board.js` — the `openContents()` function and the picker below it. That is the
   drawer the map replaces as the way in, and the code you will be moving away from.
5. `README.md` §"Getting around a project", §"A walkthrough", §"Showing a slide on the
   board", and the newest entry under "Picking this up in a new session".

Do **not** read the whole README (368KB) or the whole of `board.js` (5,000 lines). Grep.

---

## 1. What is being built, in the person's own words

> "The tutor should create a massive diagram of the repository, with its various working
> parts. This diagram should mark what's completed, what's still being done, etc., and
> communicate the functionality of everything in a visually pleasing and succinct way. Kind
> of like a software engineering diagram of sorts. I want to be able to tap on something and
> have some options. Maybe I want to learn about it. Maybe I want to vibecode some progress.
> Maybe I want to be told what to code and do it myself. Maybe I want to work some problems
> on it (like in coursework). Each such decision/tapping/picking from this big visual diagram
> would put me in a new tutoring session designed to accomplish what I select. This kind of
> design feels like it should work in all repositories and be compatible... when going into a
> course/repo, I should start with the visual map of everything."

**The map is the front door of a course.** You open PSYCH-ASR and you see its pipeline, not
an empty board. Nodes are the working parts. Colour and mark say what is done, what is in
flight, what is not started, what is blocked. Tap a node and a sheet offers ways to work on
it, and each of those opens a sitting already pointed at that part.

**Why this, and not the drawer that shipped yesterday.** The drawer lists — steps, files,
documents — three flat lists with no relationships in them. The person's difficulty is not
finding a name; it is holding a system in their head. *"Honestly I'm so lost in all of this."*
A list cannot say that the grid depends on a seam that does not exist yet, or that five of
six error labels cannot move along two axes. A diagram can. The drawer stays — it is a fine
index — but it is not the front door.

---

## 2. The single most important thing on this page

**You are building a LAUNCHER and a VIEW. You are not building new teaching machinery.**
Almost every option the person listed already exists and works. Your job is to open the
right one with the right scope, from a tap on a picture.

| what they said they want | what already implements it | how to open it |
|---|---|---|
| "maybe I want to learn about it" | **walkthrough sitting** — hand-trace through existing code | `POST /session {session:"walk", over:[<file or file::symbol>]}` |
| "vibecode some progress" | **lecture, stance do** — tutor writes the code, card is a report | `POST /session {session:"lecture", chapter:<label>, stance:"do"}` |
| "be told what to code and do it myself" | **lecture, stance teach** | same, `stance:"teach"` |
| "work some problems on it (like coursework)" | **review sitting** — asks cold over a chosen scope | `POST /session {session:"review", over:[<part>]}` |
| "have you write up papers/presentations" | *not built* — see §6, phase 4 | — |
| "SHOW me these papers on the iPad" | **reading** — `reading.py` + the page viewer | `openDoc(id, name)` in `board.js` |
| writing boards, typed answers | **the answer panel**, on every card | already on every sitting |

Read that table twice. The temptation in this build is to invent a sixth sitting kind per
node type. Resist it: one card, one question, one board, and the sitting kinds that exist.

**What is genuinely missing is one sitting kind — a *make* sitting** (write me the paper /
build me the deck) — and it is phase 4, not phase 1.

---

## 3. What exists, precisely

### 3.1 Discovery modules — your data layer, all already written

| module | gives you | cached |
|---|---|---|
| `course/plan.py` | `paths(root)`, `steps(root)` → `[{num,title,label,summary,line,from,file}]`, `where(root)`, `status(root,state)` | 30s |
| `course/walk.py` | `units(root)` → every source file `{name,label,short,dir,kind,path,symbol}`; `resolve(root,[names])`; `scope`; `sitting_label` | 30s |
| `course/reading.py` | `documents(root)` → `[{id,name,rel,at,size}]`; `find(root,id)`; `pages(repo,id)` | 30s |
| `course/review.py` | `units(root)` → chapters **or** the project's top-level parts; `resolve`; `scope` | no |
| `course/syllabus.py` | `chapters(root)`, `label(c)`, `opening(root)` — book courses only | no |
| `course/homework.py` | `sets(root)`, `status(root,state)` | no |
| `course/config.py` | `read_config(root)`, `stance_for(root,state)`, `clean_stance(s)` | no |

Every one of them is **discovery, never registration** — that is this repository's central
doctrine and you must not break it. *A fact cannot go stale; a declaration can.* Nothing is
indexed, nothing is registered, and a name arriving from a browser is always checked against
what is actually on disk before it reaches a filesystem or a prompt.

### 3.2 The payload

`tutorboard/server/hub.py::Hub.build()` assembles one JSON payload, pushed over SSE to every
open board on every change (and polled at 0.25s as a safety net). Current keys that matter
to you: `state`, `cards`, `turns`, `contents`, `review`, `walk`, `plan`, `reading`, `papers`,
`agent`, `history`, `hw`, `sets`.

You will add **`map`**. Build it in `tutorboard/lesson/state.py` as `load_map(repo)`, the way
`load_plan` and `load_walk` are built, and add one line to `hub.build()`.

**The payload is rebuilt on every change and polled four times a second.** Anything you add
that touches the filesystem must be cached like `walk.units` (see its `CACHE_SECONDS` /
`_cache` pattern). A directory walk per payload is a real cost on a shared filesystem.

### 3.3 Sittings

`state.json` in `live/` carries `session` ∈ `lecture | homework | review | walk`, plus
`chapter` (the sitting's label), `review` / `walk` (scope lists), `hw`, `stance`, `course`.

Opening a sitting is `POST /session` (`tutorboard/server/routes/lesson.py`). It archives the
lesson being left — whole, into `live/archive/<stamp>-<slug>/` — so nothing is overwritten.
`board open` is what actually writes the state; the route shells out to it via
`spawn.board_cli`. **Follow that pattern.** Do not write `state.json` from a route without
going through `board open`, or the archive and handoff-parking do not happen.

`sense.session_sense(repo)` turns that state into the sentence the tutor is woken with. In a
headless session **that string is the entire prompt** — if the map opens a sitting the tutor
is not told about, the tutor will guess, and guessing is what produced a card of invented
arithmetic in PSYCH-ASR that its owner skipped twice.

### 3.4 The board page

- `web/board.html` — every panel ships `hidden`; the script decides. Panels are `<aside>` or
  `<div>` with an id.
- `web/board.js` — one IIFE. `els` registry at the top, `render(data)` paints from a payload,
  `setSitting(kind, name, chapter)` posts to `/session`, `openPicker(kind)` drives the shared
  scope picker, `openDoc(id, name)` opens a document, `openContents()` builds the drawer.
- `web/board.css` — tokens at `:root` and under `@media (prefers-color-scheme: dark)`:
  `--paper --paper-2 --ink --ink-2 --ink-3 --rule --accent --ask --good --bad --note --mine`.
  **Use these.** Do not introduce a colour that is not one of them without adding it to both
  blocks.
- `web/slate-core.js` — **the pan/zoom plane, already written and already debugged.** See
  §5.4; this is the single biggest shortcut available to you.
- `web/sw.js` — the shell cache. `VERSION` must change when a shell file does.

---

## 4. The design, settled

These are decisions, not options. Each one has a reason; the reasons are what to re-derive
from if you find a decision is wrong.

### 4.1 Where the map comes from: a discovered skeleton, written meaning

**Structure is derived from disk. Meaning is written by the tutor. Neither is guessed.**

A model asked to draw the whole map every time is expensive, non-deterministic, and will
disagree with itself between turns. A map derived purely from the filesystem is honest and
useless — it cannot know that the grid search is half-built or that step 2a blocks everything
downstream. So:

- **Derived, every time, never stored:** which files exist, which steps the plan holds, which
  documents there are, which chapters and problem sets, what git says changed recently.
- **Written once and kept up to date by the tutor, in `live/map.json`:** the nodes that are
  *stages of the work* rather than files, their one-line purpose, their status, and the edges
  between them.

`live/map.json` is **merged against discovery on every read**: a node naming a file that no
longer exists is dropped (the same rule as `walk.scope` and `review.scope` — re-resolve, never
echo back). A repository with no `map.json` still gets a map: see §4.5.

`live/map.json` is **tracked in git** like the rest of the transcript, so the map a machine
draws is the map every machine draws. Add it to the allowlist block in the course
`.gitignore` documented in README §"Setting up a course repository".

### 4.2 What a node is

**A node is a stage of the work, not a file.** For PSYCH-ASR the nodes are *the typist*, *the
stopwatch*, *the name-tagger*, *the corrections*, *the grader*, *the grid*, *the scorer* —
which is how its owner talks about it, and is not derivable from a directory listing. Each
node *carries* the files it is made of, so a tap can open a walkthrough over them.

Node fields, and the whole schema:

```json
{
  "version": 1,
  "title": "Stage 1 — audio to a graded transcript",
  "lanes": ["inputs", "stage 1", "reference", "evaluation", "outputs"],
  "nodes": [
    {
      "id": "typist",
      "name": "the typist",
      "also": "faster-whisper large-v3",
      "lane": "stage 1",
      "does": "Turns the waveform into words. One candidate, never compared.",
      "status": "working",
      "files": ["psych_asr/cli/run_asr.py", "psych_asr/asr/align.py"],
      "step": "1",
      "doc": "stage2-reference-walkthrough",
      "slide": 7,
      "note": "five of the six error labels are a property of this box alone"
    }
  ],
  "edges": [{"from": "typist", "to": "stopwatch", "label": "words"}]
}
```

- `id` — short, stable, `[a-z0-9-]{1,40}`. Everything else keys off it.
- `name` — the plain-English name. **The plain name leads**; `also` carries the real
  identifier. This is the same rule `TEACHING.md` already imposes on a walkthrough, and it is
  the thing the person's own 33-slide deck does that made it the plainest document in the
  project.
- `does` — one sentence, present tense, under ~120 characters. It is read on a tablet inside
  a box. If it does not fit, it is too long.
- `status` — one of **`done` · `working` · `next` · `later` · `blocked` · `unknown`**. Six,
  no more. `blocked` requires `blockedBy: [<id>, ...]`.
- `files` — repository-relative, checked against `walk.units` on read. A `path::symbol` entry
  is allowed and is passed straight to `walk.resolve`.
- `step` — the `num` of a `plan.steps` entry, when this node is what that step is about. This
  is how "vibecode some progress" knows what to tell the tutor.
- `doc` + `slide` — a `reading.documents` id and a page number, when a document already
  explains this box. This is what makes "learn about it" open with the right slide.

### 4.3 Who writes it, and how it stays true

A new CLI command, `board map`, reading JSON on stdin — the same shape as `board note` and
`board handoff`:

```
board map < map.json      write live/map.json (validated, rejected loudly if not valid)
board map --show          print it
board map --check         say what is stale: nodes naming files that are gone, steps that
                          no longer exist, documents that moved, ids referenced by an edge
                          that do not exist
```

`board brief` must tell a tutor whether this course has a map, and when it was last written.
`TEACHING.md` gains a short section: **keeping the map true is part of finishing a piece of
work**, exactly as updating the plan already is. A map that is a lie after three commits is
worse than no map, because it *looks* authoritative.

**The first map is written by the tutor, on request, in a sitting.** Do not try to generate
it in Python. Add it as a documented thing a person can ask for — "draw the map" — and have
`TEACHING.md` say how: read the README and the plan, name the boxes the way the project's own
documents name them, one sentence each, and stop.

### 4.4 Status, and where it comes from

The tutor writes `status`. Two derived hints go beside it and **never overwrite it**:

- **the plan.** A step is in the plan because it is not done. If a node's `step` is still in
  `plan.steps`, the node cannot be `done` — surface that disagreement in `board map --check`,
  do not silently correct it.
- **git recency.** `lesson/git.py` already talks to git. A node whose files changed in the
  last few days is *touched*; paint that as a subtle mark (a dot, a warmer rule), never as a
  status. Recency is not progress.

### 4.5 A repository with no map file

**Every course gets a map.** This is the compatibility requirement the person named — *"this
kind of design feels like it should work in all repositories"* — and it is met by falling
back, never by refusing:

| repository | nodes | lanes | edges |
|---|---|---|---|
| has `live/map.json` | as written | as written | as written |
| a project with a plan | one node per `plan.steps` entry | one lane per plan file (a hub has three) | none |
| a book course | one node per `syllabus.chapters` entry, plus its problem sets | chapters in one lane, sets in another | chapter *n* → *n+1* |
| anything else | `review.units` — the repository's own top-level parts | one | none |

A fallback node's `status` is `unknown` except where the board genuinely knows: a chapter with
an archived lesson is `done`, the sitting currently open is `working`. A fallback map must say,
once and quietly, that it is a fallback and that the tutor can draw a real one.

### 4.6 Layout: lanes, computed in the browser, deterministic

**Do not ship a graph-layout library.** This machine has no npm at runtime, KaTeX is vendored
by hand, and a force-directed layout that settles differently on each open is the opposite of
a map you learn the shape of.

`lanes` is an ordered list. A node's `lane` puts it in a column (or a row at phone width —
see §5.3); order within a lane is the order nodes appear in the file. Layout is then
arithmetic: column index × column width, row index × row height, both from measured text.
The same file lays out identically every time, on every device.

Edges are drawn as orthogonal or gently-curved connectors between box edges. Same lane → a
short side link. Skipping a lane → route around, do not draw through a box. Keep it simple;
a readable right-angle beats a clever spline.

### 4.7 Rendering: inline SVG

SVG, generated by `board.js` into a `<svg>` the page owns.

- Crisp at every zoom, which canvas is not without redrawing on each scale change.
- Hit-testing is free — an `<g>` per node with its own `onclick`.
- Themeable from the CSS tokens in §3.4, so light and dark come out right with no second
  palette.
- Text is real text: selectable, and legible to a screen reader.

Do **not** use `<foreignObject>` (Safari renders it inconsistently). Wrap label text yourself
— measure with a hidden `<text>`, or lay out in fixed character counts and accept a
two-line cap on `does`.

One `<svg>` inside one pan/zoom wrapper. Nodes are `<g class="node" data-id="...">` holding a
`<rect>` and one or two `<text>`. Status is a class on the `<g>` — `.node.done`, `.node.blocked`
— and the entire visual language lives in `board.css` where it can be changed without
touching the generator.

### 4.8 The tap sheet

Tapping a node opens a sheet — the same shape as the existing `#kind` chooser, which is
already the right size for a thumb. It shows the node's name, its `also`, its `does`, its
status, and then the ways to work on it. **Offer only what the node can actually support**:

| offered | when | opens |
|---|---|---|
| **Learn how it works** | the node has `files` | `walk` over those files; if it has `doc`+`slide`, the tutor is told to open there |
| **Read the slides** | the node has `doc` | the document viewer, at `slide` if given |
| **Build it for me** | the node has a `step`, or any files | `lecture`, `stance: "do"`, labelled with the node |
| **Tell me what to write** | same | `lecture`, `stance: "teach"`, labelled with the node |
| **Set me problems** | always | `review` scoped to the node's files or its part |
| **Write it up** | phase 4 | the `make` sitting |

The labels are the person's own words made imperative. Do not name them after the internal
sitting kinds — nobody taps "lecture, stance do".

**A node's label becomes the sitting's `chapter`.** That is what the title bar shows, what the
archive is filed under, and what `session_sense` tells the tutor to open at. Use
`node.name` — "the typist" — not the id.

### 4.9 What the tutor is told

This is the half that decides whether any of it is any good. Extend `tutorboard/sense.py`:

- A sitting opened from a node carries the node in `state.json` (`"node": "typist"`).
- `session_sense` gains a clause naming the node, its `does`, its files, its plan step, and
  its document and slide when it has them — the same way `where_sense` now names the plan and
  its steps rather than sending the tutor to find them. **Every round trip you can remove
  from a cold turn is money and latency the person pays for on every single turn.**
- When the map has edges, say what this node depends on and what depends on it. A tutor that
  knows the grid is blocked on a seam that does not exist will say so instead of building the
  grid.

---

## 5. UI requirements — these are the ones that get skipped

### 5.1 Scrolling

This has been a live defect twice. Every panel on this page is a fixed panel with a head, a
foot, and a list between them, **and the list is the part that scrolls**. Being inside a panel
does not make an element a scroller: it needs `flex: 1` and `overflow-y: auto`, both, and
`test/chrome.js` asserts this for all five existing lists. Add the node sheet to that
assertion.

### 5.2 Pan, zoom and gesture

The map is a plane. **Everything about gestures on a plane is already solved in
`web/slate-core.js` and every trap has been paid for in a broken lesson.** Read it before you
write a single `pointerdown` handler. Specifically:

- A gesture is decided by **which contacts are live**, not by counting a map that may hold a
  stale entry. One moving finger read as a pinch against a frozen phantom is a shipped
  regression; see the 11 September entry in the README.
- **A `touchmove` listener that is not passive makes the browser ask the main thread before
  scrolling a single pixel.** Two of those on every card is what made annotation janky. Attach
  non-passive listeners only while a gesture is actually in progress, and prefer
  `touch-action` in CSS to JavaScript that refuses events.
- Two fingers are never the pen. `touch-action: pinch-zoom` is the right latch, not `none`.
- Clamp panning to the content plus about a viewport of slack. An unclamped plane flung into
  empty space looks exactly like a crash.

Reuse the plane. If it cannot be reused as it stands, extract the view/gesture half of
`slate-core.js` into something both surfaces use, and say so in the commit — do not fork it.

### 5.3 Phone and narrow glass

The map must work at ~400px. Lanes become **rows** below a breakpoint (a horizontal pipeline
becomes a vertical one), or the plane simply starts zoomed to fit and the person pans. Either
is acceptable; silently overflowing is not. No horizontal scroll on `body`, ever.

### 5.4 Theme

Light and dark both, from the tokens. The viewer paints its own ground behind the page, so
give the map surface an explicit token background — never transparent.

### 5.5 Speed

The map is the first thing seen on opening a course. It must paint in well under a second
from a cached payload. Generate SVG once per payload change, not per frame; pan and zoom must
be a CSS transform on the wrapper, never a regenerate.

---

## 6. Build order

Each phase ships on its own and leaves the board better than it found it. Do not start
phase *n+1* before phase *n* is shipped and green.

**Phase 1 — the map, read-only, from fallbacks.**
`course/map.py` with the fallback rules of §4.5 only; `load_map` in the payload; SVG render;
pan/zoom; no `map.json`, no tap sheet, no new sittings. Landing rule from §7. This alone puts
a picture of every repository on the board and is the risky half of the rendering work.

**Phase 2 — `live/map.json`, `board map`, the merge.**
The schema, validation, the re-resolve-on-read rule, `--check`, and the `TEACHING.md` section
telling the tutor how to draw one and to keep it true. Write PSYCH-ASR's map by hand as the
worked example, from its README, its plan, and its Stage-2 deck.

**Phase 3 — the tap sheet, and the sittings it opens.**
The five existing options. `node` in `state.json` and the `session_sense` clause. This is
where it becomes the thing that was asked for.

**Phase 4 — the `make` sitting.**
"Write me the paper / build me the deck / show it to me." A sitting whose product is a
document rather than an answer. `Paper-Writer` next door is a manuscript factory with a
`rebuild` pipeline; `reading.py` already shows a finished PDF on the glass. The gap is the
sitting in between, and it is genuinely new work — do not start it until 1–3 are shipped.

---

## 7. Where a course opens, and getting back to the map

**Two rules, and the second one outranks everything else in this file.**

### 7.1 A course opens where you left it

Not always on the map. **On the surface you were last on in that course**, and if that was
the map, *on the part of the map you were looking at* — the same pan and zoom, with the node
you last opened still marked as where you are. A person who was three steps into a derivation
and taps their course must land in the derivation. A person who was reading the pipeline must
land on the pipeline, at the box they were reading, not scrolled back to the origin.

A course nobody has opened yet, or one whose remembered surface no longer exists, opens on
the map. That is the default, and it is the only time the map is forced on anybody.

What to remember, per course, keyed by the course directory:

| | |
|---|---|
| which surface | `map` · `lesson` · `document:<id>` |
| where on the map | the plane's `x`, `y`, `k`, and the last node's id |
| when | a timestamp, so something absurdly old can be ignored rather than obeyed |

`localStorage`, and it is a per-viewer convenience rather than state: it can throw, it can
come back empty, and it is wiped by a private window or cleared site data. **Wrap every read
and write in try/catch and render correctly with none of it** — which means falling back to
the map, which is the default anyway. Do not put this in `state.json`: two devices reading
the same course are two people looking at different parts of it, and that is correct.

### 7.2 The map is reachable from everywhere, with no exceptions

**From every surface, in every state, one gesture gets you to the map.** Not "from the
lesson". Everywhere:

- the lesson, scrolled anywhere, zoomed to anything
- the full-screen writing surface
- the document viewer, mid-deck
- a past lesson opened read-only under **◷**
- every drawer, sheet and picker — including the node sheet itself
- a board with nothing on it, a board whose tutor is dead, and a board that has lost its
  connection

**The precedent is `#panic`, and it is worth copying exactly.** `web/board.html` §"The way
back, from anywhere" plus `panicPlace` in `board.js`: a control positioned from JavaScript
rather than by CSS, because `position: fixed` is fixed to the *layout* viewport and a pinch
moves the *visual* one — so a CSS-placed control slides off the glass at precisely the moment
somebody needs it, and looks perfect in every test that never zooms. It counter-scales so it
stays a thumb wide at any magnification, it is told tap-from-drag **by time and not by
distance** (a tap on a tablet always travels a few pixels), and **nothing in the board is ever
allowed to hide it** — a guarantee with a condition on it is not a guarantee.

`test/panic.js` holds those rules for the existing button and is the file to extend. The map
control does not have to be a second floating button — a glyph in the title bar is fine for
the lesson, and the full-screen surfaces have their own chrome to carry it — but whatever it
is, **there must be no state of this application from which the map cannot be reached**, and a
test must say so surface by surface rather than in general.

The title bar has no room: it already carries the course, the chapter, the sitting badge and
three controls. A map control there is **one glyph**, not a word. See §10.

**Regressions to check by hand on an iPad before you call any phase done** (each of these has
broken before, in this order of pain):

- The tailnet address still points at the course you think it does — `board net` after every
  ship, and `tutor where`.
- A lesson in progress still paints, still scrolls, and still takes handwriting.
- The answer panel still opens under a question, in both writing and typing halves, and a
  previously-sent answer still comes back editable.
- Annotation over a card still works, and scrolling while annotating is still smooth.
- The contents drawer still scrolls, all five lists.
- A course reopens on the surface it was left on, at the part of the map it was left at.
- The map is one gesture away from the lesson, the slate, a document, a past lesson, and
  every drawer — checked on the glass, not only in a test.
- The installed app picks up the new shell — bump `web/sw.js`.

---

## 8. Tests

`bash test/all.sh` runs everything; add yours to it the way `plan` and `walk` were added.
Follow the house style: every check is a sentence about behaviour, and the comment above a
group says what defect it exists to prevent.

- **`test/map.py`** — the fallbacks for all four repository shapes; the merge dropping a node
  whose file is gone; a node id arriving from a request checked by lookup and never
  constructed; `--check` reporting a node marked `done` whose plan step is still open; an
  edge naming an id that does not exist refused at write time; the `session_sense` clause
  naming the node, its files and its slide.
- **`test/map.js`** — real-DOM, the pattern in `test/walk.js` (note the `className`/`classList`
  stub, which a real element keeps in sync and a naive stub does not). Nodes render; status
  becomes a class; a tap opens the sheet; the sheet offers only what the node supports; each
  option posts the right `/session` body.
- **The way back, and it gets its own checks** — extend `test/panic.js` rather than burying
  them: the map is reachable from the lesson, from the writing surface, from the document
  viewer, from a past lesson, from an empty board, from a board with a dead tutor, and from
  inside every drawer and sheet. **One check per surface, named after the surface**, because
  "there is a way back" as a single assertion is the one that passes while a real state is
  stranded. And: a course reopens on the surface it was left on, restores the plane's `x`,
  `y` and `k` when that was the map, and falls back to the map without throwing when
  `localStorage` is empty or refuses.
- Extend **`test/chrome.js`** with the sheet's scroller, and **`test/hidden.js`** already
  guards that panels ship hidden — make sure yours do.

---

## 9. Done, and what to do then

It is done when, on an iPad, opening PSYCH-ASR shows its pipeline; tapping *the corrections*
offers five ways to work on it; tapping **Learn how it works** lands in a walkthrough over
`psych_asr/transcript/corrections.py` with the tutor already told what that box is and which
slide explains it; and the same gesture does something sensible in TRD-EHR, Research-Journey,
libr-local-llm, Algo-Solutions and Galois Theory — and, from every one of those sittings, one
gesture is back to the map at the box you came from.

Then **delete this file** — `git rm HANDOFF.md` — and fold what survived of it into `README.md`
as a section, and into `TEACHING.md` as the rules for keeping a map true. This file is
scaffolding. A repository that keeps its scaffolding accumulates two descriptions of itself
that disagree.

---

## 10. Traps in this codebase, each one already paid for

- **`board open` is the only thing that opens a sitting.** Writing `state.json` directly skips
  the archive and the handoff parking, and loses the lesson being left.
- **Nothing is registered.** If you find yourself writing an index, a registry, or a list that
  has to be kept in step with reality, stop — the answer here is always to read the thing
  itself. The one exception is `live/map.json`, which carries *judgement* that no file
  contains, and even that is re-resolved against disk on every read.
- **A name from a browser never reaches a filesystem.** Compare it against what discovery
  found; a miss is a miss. See `walk.resolve` and `reading.find` for the two patterns.
- **A path out of a file is untrusted**, including out of a README. `plan._resolve` and
  `reading._pointed_at` bound themselves to the repository and its siblings under the same
  home. Copy that, do not loosen it.
- **The payload is polled four times a second.** Cache anything that touches disk;
  `walk.py`'s `CACHE_SECONDS` is the pattern.
- **`[hidden]` loses to any author rule that sets a `display`.** Toggle `el.hidden`; the
  guard is `test/hidden.js`.
- **The title bar has no room.** It already carries the course, the chapter, the sitting badge
  and three controls. A map control there must be one glyph. A sentence that gets cut in half
  is a sentence whose second half was the useful one — that was a real report.
- **Commits here are authored by the person, with no assistant trailers.** `scripts/ship.sh`
  handles it; do not add co-author lines to this repository's commits.
- **Do not "fix" things you notice in passing.** The person is using this. One change, shipped,
  checked, then the next.

---

## 11. Context you will want and would otherwise have to rediscover

- **The repositories**, all siblings of this one in the home folder: `PSYCH-ASR` (spoken-
  therapy ASR pipeline, `stance: teach`, 7 plan steps, 51 source files, 2 decks), `TRD-EHR`
  (EHR causal pipeline and a manuscript, `stance: do`, 5 steps, 82 files), `Research-Journey`
  (narrative hub, holds all three projects' plans and 5 documents, almost no code),
  `libr-local-llm` (local inference infrastructure, 5 steps, 7 files), `Paper-Writer` (a
  manuscript factory, `stance: do`), `Algo-Solutions` (LeetCode, Go, 188 files),
  `Galois-Theory` and `Probability` (book courses with `chapters.tsv` — **these two already
  work well; do not regress them**), `Lean-Theorem-Proving`, `Mathematical-Modeling`.
- **The machine** is a Slurm compute node, no root, shared home. Standard library only in
  Python; plain browser JavaScript; nothing that needs a package manager at runtime.
- **The person's own words about what is wrong with the status quo**, worth keeping in view:
  *"I'm tired of getting massive word dumps from you when I need you to explain how something
  works for me in these repos, and reading that in the terminal is even worse."* The map is
  the opposite of a word dump. If a phase of this work ends with more prose on screen rather
  than less, it has gone wrong.
