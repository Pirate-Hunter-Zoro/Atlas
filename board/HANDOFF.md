# HANDOFF — the repository is one, the front door is a map, and five things are left

> **You are in Atlas, in `board/`, in a fresh session, and you have been pointed at this file.**
>
> The migration is **done**. Eleven repositories are one, the board runs out of it, the front
> door is a drawn map of everything, and 32 test suites are green. What is left is the old
> brief's stage 2 onwards. The address grammar is now done as well (§2.1) and everything
> below it is written against it: the written map, meeting notes, documents, and the briefing
> seeing what was done on a laptop.
>
> This file was rewritten on 14 September 2026 and it replaces a brief for work that is
> finished. Read §0 and §1 before you touch anything. §2 is what is actually left, in the
> order it should be done. §6 is the one thing the migration did not finish.
>
> *(This is not a `board handoff` file. Those are capped at 350 words and live in a
> workspace. Nothing reads this automatically. Delete it when §2 is finished and fold what
> survives into `README.md` and `TEACHING.md` — see §8.)*

---

## 0. Before anything, and none of it is negotiable

**The person who asked for this uses the board while you change it**, on an iPad, in the
middle of real work. A regression does not annoy them later; it stops the lesson now.
Galois-Theory and PSYCH-ASR must be openable and teachable at every point, and if you cannot
keep that true, stop and say so rather than press on.

- **Ship, do not merely commit.** `bash board/scripts/ship.sh "message"` commits **only
  `board/`**, pushes, and restarts every board. A board is a long-lived process that read
  `serve.py` when it started, so a commit alone changes nothing for them. The pathspec is
  new and load-bearing: there is one repository now, and a ship without it would file nine
  workspaces' unfinished work under a commit message about the board.
- **Bump `VERSION` in `board/web/sw.js`** when any shell file changed (`board.html`,
  `board.js`, `board.css`, `plane-core.js`, `gauge.js`, `home.html`, `home.js`, anything new
  you add to the cache list), or the installed app serves its cached copy and your work is
  invisible. It is at `board-shell-v102`.
- **Run `bash board/test/all.sh` before every ship.** 32 suites, all green. Keep them green.
- **`test/tracked.py` is the one that cannot be fixed afterwards.** It runs first in
  `all.sh` and it refuses PHI, 25-megabyte files, model dumps, other authors' papers and
  books, and machine-local config — anywhere in the repository. This is public. A thing that
  is public for an hour has been published, and git remembers.
- **The lesson must always be reachable.** Every surface you add is one somebody can be
  stranded on mid-proof.
- **Commits are authored by the person, with no assistant trailers.** `.githooks/commit-msg`
  strips them; `save-and-push.sh` turns the hook on for a fresh clone.
- **Do not "fix" things you notice in passing.** One change, shipped, checked, then the next.
- **Nothing that cannot go into a public repository may live inside the repository.** Not
  ignored inside it — outside it, with something inside naming the path. §4.

---

## 1. What is here now

```
Atlas/                          github.com/Pirate-Hunter-Zoro/Atlas
  README.md  atlas.json  .gitignore  .gitmodules
  board/                        the tool. 2,061 commits of history across the whole tree
  courses/      Galois-Theory · Probability · Mathematical-Modeling
  research/     PSYCH-ASR · TRD-EHR
  projects/     libr-local-llm · Paper-Writer
  practice/     Algo-Solutions · Lean-Theorem-Proving
  vendor/       colibri (pulled every login) · colibri-build (pinned fd93c41)
```

**Nothing lists the workspaces.** A second-level directory holding `tutorboard.json`,
`AI_INSTRUCTIONS.md` or `live/` is one, found by looking. `atlas.json` names and orders the
five families and flags the two that hold no workspaces — `vendor` (somebody else's work)
and `board` (what does the offering). Starting a new course is `mkdir courses/Topology`.

`tutorboard/atlas.py` is the walk, and everything asks it rather than taking a `dirname`.
`root()` walks up from `paths.TOOL` for `atlas.json`; `TUTORBOARD_COURSES` overrides it and
now means *the repository root*, which is the same sentence about a different shape. A tree
with no `atlas.json` gets ONE nameless family whose directory is the root — which is what
lets the old flat layout and every test fixture work through the same code path.

### What is outside the tree, and why

| What | Where | The rule |
|---|---|---|
| 308 MB of therapy audio | `~/phi/PSYCH-ASR/` | Identifiable PHI; participant IDs in the filenames |
| 1.5 GB of job output | `~/artifacts/TRD-EHR/results/` | Regenerable; seven files over GitHub's 50 MB warning |
| Other authors' papers and books | on disk, ignored | Their copyright, and this is public |
| The assistant configuration | `ai-config/`, its own private repository | Its settings name real paths on lab storage. Inside the tree, ignored by it, tracked by its own git |

Neither of the first two is symlinked in. A symlink is a tracked file pointing at PHI, which
hands the next reader a map to it. `PSYCH_ASR_DATA` finds the first — read by
`psych_asr/config.py`, exported by `slurm_jobs/lib/job_env.sh`, absolute on purpose because
those paths used to resolve against the submit directory.

**The PHI directory is still waiting to be moved.** See §6; it is the one thing in the
migration that is not finished.

---

## 2. What is left, in order

The old brief's stages 2 and 4 through 7. Stage 3 — the atlas — was done first because it is
what the person asked for first and sees first, and because it needed no grammar to exist.
**2.1 is now done too**; it is kept below because 2.2 through 2.5 are all written against it
and because what was deliberately deferred inside it has to be findable.  The next thing is
2.2.

### 2.1 The address grammar — DONE, and three features are no longer waiting on it

`web/address.js` is the grammar and nothing else: it parses, it spells, it
touches no DOM and makes no request, so both pages load it and a test drives it
with no browser at all. `addrGo` in `web/board.js` is the one resolver.
`test/address.js` is the suite, in `all.sh` — and the Python `test/address.py`,
which is about the *tailnet* address and a different thing entirely, is now
labelled `tailnet` in the runner so two rows are not called the same name.

```
#/w/<family>/<workspace>                   the workspace, on its map
#/w/…/node/<id>                            one box, selected, sheet open
#/w/…/card/<nnnn>                          one card in the current lesson
#/w/…/archive/<sitting>/<nnnn>             one card in a finished sitting
#/w/…/doc/<ident>[/p<n>]                   a document, optionally one page
#/w/…/code/<path>[::<symbol>]              a walk unit
#/w/…/hw/<set>/<problem>                   one problem of a problem set
#/w/…/slate/<nnnn>                         one page of handwriting
```

The three rules, and where each one lives:

1. **A name from a browser never reaches a filesystem.** Nothing in
   `address.js` builds a path; every component is looked up by the resolver in
   the payload the board already holds — `mapInfo.nodes`, `lastLive.cards`,
   `readingInfo.documents`, `walkInfo.units`, `knownSets`, `lastLive.slate`,
   and for a past sitting the archive's own list. A miss is said as "that is
   not here any more", never as an error and never as something near it.
2. **A link that no longer resolves says so where it is written.**
   `markAddresses` runs at the end of every render and marks every `#/w/…`
   anchor in the lesson against that same payload: struck through and grey for
   an address whose target has gone, red and wavy for text that is not an
   address at all, ordinary for one that still resolves. Rendered links to an
   address also lost their `target="_blank"` — a second tab is a second board.
3. **One resolver, one speller.** `Address.format` is the only thing anywhere
   that builds an address and it refuses to spell anything its own parser would
   reject. `spell()` on the board fills in this workspace. The grammar is
   strict for the same reason: a card is four digits, never one and never
   seven.

**How the board knows which workspace it is**: `/health`'s `id`, fetched once at
load. Until that answers, `mapLand` does not land — an address naming another
workspace cannot be told from one naming this one, and landing on the wrong
guess is worse than landing a moment later.

**Another workspace is another board on another port**, and the only thing that
can move the one address between them is the front door. The board hands the
whole address to `/` ; `home.js` routes it — switch, then on to `/board` plus
the address. Recorded in `sessionStorage`, so a switch that does not land is
reported rather than bounced between two pages for as long as anybody watches.
The atlas's sheet now opens a workspace *through* the address as well, so a tap
and a link do the same thing by the same code.

**The bar carries where the board is**, by `replaceState`, riding on
`mapRemember` — which already decides what "here" means and is called from
everywhere that changes it. Never `pushState`: a pan is not a page. It never
downgrades, either: landing on a card and then having the bar revert to the
bare workspace is a link nobody can copy off the glass.

**Two forms name something finer than the board can paint today**, and neither
is dropped or faked. `code/<path>::<symbol>` opens the walkthrough picker with
that file chosen and says which function it was pointing at; `hw/<set>/<problem>`
opens the set in the contents drawer and names the problem. Both are one line of
honest text over the containing surface. A code viewer and a per-problem surface
are §2.4's business; when they exist, two branches of `addrGo` change and no
address written before then breaks.

### 2.2 The written map, per workspace

**Structure is derived from disk. Meaning is written by the tutor. Neither is guessed.**
`course/map.py` discovers parts, arrows and work from the tree and it is honest — but nothing
on disk knows that the grid search is half-built, or that the scorer is blocked on a seam
that does not exist yet.

So: **`live/map.json`** per workspace, written once by the tutor and kept up to date by it,
**merged against discovery on every read and never echoed back**. A node naming a file that
no longer exists drops the file; a node whose files have all gone drops out; an edge naming
an id that is not there is not an edge. Same rule as `walk.scope` and `review.scope`, and
the same reason: *a fact cannot go stale, a declaration can, so a declaration is checked
against the facts every time it is read.*

What it adds that discovery cannot is a node that is a **stage of the work** rather than a
directory. PSYCH-ASR's owner's own names are *the typist*, *the stopwatch*, *the
name-tagger*, *the corrections*, *the grader*, *the grid*, *the scorer* — which is how they
talk about it and is not derivable from a directory listing. Each such node *carries* the
files it is made of, so every tap on the sheet works unchanged. Plus the three things
nothing sets today: `blockedBy`, `doc` and `slide` on a part, and edge labels saying what
flows (`words`, `turns`, `a graded transcript`).

```json
{
  "version": 1,
  "title": "Stage 1 — audio to a graded transcript",
  "nodes": [{
    "id": "typist", "name": "the typist", "also": "faster-whisper large-v3",
    "kind": "part", "status": "working",
    "does": "Turns the waveform into words. One candidate, never compared.",
    "files": ["psych_asr/cli/run_asr.py"], "dir": "psych_asr/asr",
    "doc": "stage2-reference-walkthrough", "slide": 7, "blockedBy": ["seam"]
  }],
  "edges": [{"from": "typist", "to": "stopwatch", "label": "words", "weight": 3}]
}
```

Every field except `blockedBy` is already in `map._node()` and already painted. `kind` is
`part · doc · chapter · set`; `status` is one of `map.STATUSES`; `does` is capped at
`map.DOES` (110) because it is read inside a box on a tablet; `id` is `[a-z0-9-]{1,40}` and
stable, because everything keys off it including `localStorage`'s memory of where you were.
**The plain name leads** and `also` carries the real identifier.

Where a written map exists it **replaces** the derived one. Do not merge the two sets of
boxes — that puts `psych_asr/asr` and *the typist* on the same picture saying the same thing
twice. The derived map stays the fallback for every workspace nobody has drawn, which is
most of them.

```
board map < map.json      write live/map.json (validated, rejected loudly if not valid)
board map --show          print it
board map --check         what is stale: nodes naming files that are gone, steps that no
                          longer exist, documents that moved, ids an edge names that do
                          not exist, a node marked `done` whose plan step is still open
```

Same shape as `board note` and `board handoff` — JSON on stdin. **The tutor writes it, on
request, in a sitting**; do not try to generate it in Python. Make it a documented thing a
person can ask for — *"draw the map"* — and have `TEACHING.md` say how: read the README and
the plan, name the boxes the way the project's own documents name them, one sentence each,
and stop. `board brief` must tell a tutor whether this workspace has a map and when it was
last written, and `TEACHING.md` gains a short section: **keeping the map true is part of
finishing a piece of work**, exactly as updating the plan already is.

Track `live/map.json` in git. It is the one exception to "nothing is registered", because it
carries judgement no file contains — and even it is re-resolved on every read. Write
PSYCH-ASR's by hand as the worked example, from its README, its plan and its Stage-2 deck.

The atlas already has a place for one field off it: a workspace with a written map has a
title and a status for the whole of it. That is the only coupling between the front door and
this, and it is one field.

### 2.3 Meeting notes

> "have functionality to produce 'meeting notes' for me with in-built links that will take
> me to those results/code/sections of my board writing to explain those notes."

A control on the atlas: **notes for a meeting**, over a period (since a date, since last
Monday, since the last set of notes) and over a chosen set of workspaces. It produces a
document in the same pipeline as every other one — markdown into `document.md_to_tex` into a
compiled PDF, tracked, numbered v1/v2/v3 rather than stamped with the time. Per workspace:

- **what landed** — commits in the period, scoped to that workspace, summarised rather than
  listed, plus plan steps that closed;
- **what it means** — the written map's own words for the parts that changed (§2.2), which
  is the entire reason the written map is worth having;
- **what is next** — the next open plan steps;
- **what is blocked**, and on what — `blockedBy`, the field nothing sets today;
- **links**, in the §2.1 grammar, on every claim.

Two rules about the prose. It is **short** — a meeting note nobody can read in a lift is not
a meeting note. And every sentence obeys the one-read rule: one idea per sentence, the
conclusion first, names and numbers rather than adjectives.

`board notes --meeting --since <date> [--workspace …]`, and the same thing from the atlas,
because the person is holding an iPad when they need it.

### 2.4 Documents: annotate, export, write

In this order. The first two extend machinery that exists; the third needs another
repository read first.

**Annotating.** `web/annotate.js` puts an ink layer on each **card** and stores strokes in
that card's own coordinates — fractions of its width and height, not page pixels — because
the lesson reflows constantly and ink anchored to the page ends up somewhere else. The same
trick, one level out: on a **document page**, ink anchored in fractions of the page box,
keyed by document ident and page number; on **code**, anchored to a line within a walk unit,
so a comment on line 74 survives the file growing a line at the top. Either one, when sent,
becomes what a card annotation already becomes — a message in the inbox carrying the picture
and the anchor — with `writing.py`'s wording extended to name the place in §2.1 terms. You
are widening the target, not inventing a mechanism.

**Exporting.** `document.build(root, scope=…)` already compiles a lesson, tracks it in git
and numbers it. Add scopes rather than exporters, keep the numbering, and keep the one
property that makes an export trustworthy: it is **the whole sitting in reading order** —
the question, every revision of the working as it was actually sent, what the tutor said,
and the next attempt underneath. Half a conversation is what `board archive` refuses to
keep, for the same reason.

**Writing, and this is where Paper-Writer comes in.** It is a workspace in this repository
now — `projects/Paper-Writer`, with its own `service/`, `prompts/`, `config/`, an inbox it
reads job prompts out of and an out-directory it delivers to. **Read its README and
`PROMPT_TEMPLATE.md` before you design this seam**, and keep the seam to one function: a
`make` sitting in workspace W assembles a job — the plan, the written map, the figures and
tables it names, the manuscript sections that already exist — drops it in Paper-Writer's
inbox, and the delivered manuscript lands in W under a tracked path. Then it is a document
like any other. A correction round is an annotation that goes back in as another job. **Do
not fold Paper-Writer's engine into the board.** It is a working manuscript factory with its
own state directory and its own ledgers; the board's business is handing it a job and
showing the result.

### 2.5 The briefing sees what was done on a laptop

> "I want to be able to pop open my laptop and code up something and have the tutor see that
> if it pertains to whatever project we're in."

Cheap, and it makes every turn better. Every turn is a cold turn — `session_turns: 1`, a
fresh `claude -p` reading `board brief` and `board recap` off disk — so the briefing is the
only place this can go. Add to `tutorboard/brief.py`: commits in this workspace since the
turn's own timestamp with their subjects, the names of files uncommitted right now, and a
one-line count of what the diff touches. **Not the diff** — a briefing is about 22k tokens
and it stays that way.

Two rules. It is **scoped to the workspace**, or a turn about Galois Theory is told about
PSYCH-ASR's afternoon — `machines._last_touched` already shows the shape of that query. And
it is **named as the person's work, not the tutor's**: a turn that mistakes a commit
somebody made on their laptop for something it did itself will report having done work it
has not done, which is the worst failure mode this board has. Put it in `lesson/git.py` with
a TTL, because the payload is polled four times a second.

---

## 3. The atlas, as built

`web/home.html` + `home.js` + `home.css`, and `test/hub.js` is its suite. One plane, a region
per family, a card per workspace carrying its name, what is next in it, how much is
outstanding, whether a board is live and on which node, and when it was last committed to.
Tapping a card opens a sheet; opening from the sheet moves the board through `/switch`,
which is unchanged.

Things worth knowing before you change it:

- **`/atlas.json`** is the payload — `machines.atlas_payload()`, cached 30 seconds because
  it is a `plan.steps` read and a `git log` per workspace. The `current` flag is recomputed
  on every call even from cache, because it is what the door opens and it moves the instant
  a board is switched.
- **"What is next" has two answers and neither is a fallback for the other.** A course that
  follows a book is planned by `chapters.tsv`, so what is next is the chapter after the one
  it is in. A project is planned by a task list, so it is the first open step. Asking only
  about steps left every course's card blank, which on a front door reads as "nothing to do
  here" rather than "this one is a book".
- **`gauge.js`** is the measuring, shared with the board's map. It was extracted from
  `board.js` for this: two surfaces measuring text two slightly different ways is two
  spellings of one answer.
- **The layout reads no width of the glass.** Three cards across, a constant. What adapts is
  the *view*: below 640px the plane opens framed on the card you are in rather than on the
  whole picture, because a 300-unit card fitted to a 390-unit phone is unreadable. The sheet
  is the other half of that answer.
- **`paintAtlas` is wrapped and cannot throw**, the same way `paintMap` is. A front door
  that throws is a blank screen where the app used to be.
- A board on an older tool serves no `/atlas.json`; the page says so and the door above it
  still works.

**It is addressable now.** `#/w/<family>/<workspace>[/…]` on the front door is routed by
`addrRoute` in `home.js`: a workspace that is already serving goes straight to the board, one
that is not is switched to first, and a workspace that is not in the repository any more says
so on the atlas rather than throwing. The sheet's own "open" goes through the same route, so a
tap and a link cannot drift apart. §2.1.

---

## 4. What is ignored, and what is moved instead

> **If it cannot go into a public repository, it does not live in the repository.** It lives
> outside the tree and something inside the tree says where.

The root `.gitignore` therefore holds two honest categories: files a command regenerates,
and other people's papers and books. **Each workspace keeps its own `.gitignore`**, and
those are the load-bearing ones — in particular the `live/*` allowlist (cards, slate,
answers, archive, inbox, text, `state.json`, `turns.jsonl` tracked, the rest ignored), which
is what makes a lecture the same lesson on whichever machine picks it up. Nothing in the
root file may shadow one of those: git will not descend into a directory ignored higher up,
so a rule for `live/` written at the root would make every deeper `!live/cards/`
unreachable.

Three things were found on the way in and are worth knowing, because they are the shape of
what will be found next:

- **Three copyrighted textbooks and forty chapter excerpts were tracked**, in the three
  courses. `split-textbook.sh` said of its own output "they are derived artifacts and
  git-ignored" — the intent was there from the start and the ignore rule never was. Dropped
  from history on the way in; the books stay on disk and the excerpts regenerate.
- **TRD-EHR's `.env` was tracked for 477 commits.** No credentials in it — but it enumerated
  the on-disk locations of identifiable patient data on lab storage, which is exactly what
  §4.4's reasoning keeps `ai-config` private for. Dropped from history; `.env.example`
  carries the keys.
- **2.19 GiB of TRD-EHR's pack was other authors' published papers.** Dropped, all 477
  commits kept, 19 MB out the other side. Its old GitHub remote still has every one of them;
  deleting it is the fix.

One caution, not a blocker: Galois-Theory's tracked `live/archive` is 114 MB of lesson
transcript and Probability's tracked `live/` is another 20 MB. It is all small files and it
is the transcript, so it is right that it is tracked. Do not "solve" it by untracking the
transcript.

`test/tracked.py` is the audit, written as a test rather than as a paragraph. A rule nobody
can break by accident beats a rule written down.

---

## 5. colibri

`vendor/colibri` is pulled forward on every login and `vendor/colibri-build` is pinned at
`fd93c41` and never pulled — a build tree that moves underneath a build is the failure it
exists to avoid.

The pull is `pull_vendor()` in `bin/tutor`, called from `cmd_resume`, because a compute node
gets one moment and it is the login. **It commits the pointer bump itself**, with a fixed
message naming the old and new commit, and that is **the only commit anything in this system
makes on its own**. Without it the repository is left dirty every time colibri moves and the
board shows the person "unsaved work" for something they did not do. It is guarded three
ways: only when `vendor/colibri` is the *only* dirty path, never mid-merge or mid-rebase,
never on a detached HEAD. `scripts/catch-up.sh` does the same update on the same guards.

A clone needs `--recurse-submodules` or `vendor/` arrives empty, which is the first thing a
new machine gets wrong and gives no error when it happens. `bootstrap.sh` repairs it — and
it no longer clones anything else, because there is nothing else to clone.

---

## 6. The one thing the migration did not finish

**`~/PSYCH-ASR/data` has not been moved to `~/phi/PSYCH-ASR/`.** Everything else about that
move is done — the code reads `PSYCH_ASR_DATA`, the READMEs and `AI_INSTRUCTIONS.md` name
the new path, `~/phi` exists, and the PHI hook fences `phi/` whole and has a test that says
so. The directory itself is still at the old address, because the tooling declined to move
308 MB of PHI without a person saying so.

```
mv ~/PSYCH-ASR/data ~/phi/PSYCH-ASR
```

Do it before the old directories are deleted, and check afterwards that
`~/phi/PSYCH-ASR/inbox` holds the one `.wav` the jobs expect. Until it is done, a pipeline
run will look in `~/phi/PSYCH-ASR/inbox`, find nothing, and say so in one line — which is
the guard in `job_env.sh` doing its job, not a break.

**The old working directories are still in `~`.** They are not the repository any more and
nothing points at them: the board, the tutor, `~/.local/bin/tutor` and `~/.local/bin/board`
all run out of Atlas. Delete them one at a time, and only the ones whose workspace you have
opened and taken a turn in since the move. `~/live`, `~/R`, `~/bin`, `~/go`, `~/lib`,
`~/opt` and `~/wolfram-engine-install` are machine state, not work, and go into nothing.

Every old history is archived at `~/archive/*.bundle` — twelve bundles, 298 MB, each
verified with `git bundle verify`. That is the only copy of the unfiltered TRD-EHR history
once its remote is deleted.

---

## 7. Traps, each one already paid for

- **A list is not a diagram.** The map's first version drew the plan's steps in a column and
  was rejected. The boxes are the content; the work is drawn ON them.
- **Estimated text overflows.** Measure with a canvas. Cache it. `gauge.js`.
- **A rule that is right for one kind of turn can be exactly wrong for the other.** Before
  you make any rule about the order of a turn, ask which kind of turn it is for. The fix is
  always to scope the rule, never to weaken it.
- **A second tap is ceremony.** `POST /session` takes `begin: true` for exactly this reason.
- **A glyph is not a label.** A bare diamond did not read as "the map".
- **Nothing a reader can be waiting on may be silent.** A failure is news until something
  newer happens, not until a timer says so.
- **`board open` is the only thing that opens a sitting.** Writing `state.json` directly
  skips the archive and the handoff parking, and loses the lesson being left.
- **Nothing is registered.** `live/map.json` and `atlas.json`'s five family names are the
  only exceptions in the whole system, and both are re-resolved against the tree on every
  read.
- **A path out of a file is untrusted**, including out of a README. The bound WIDENED to the
  whole repository plus `~/phi` and `~/artifacts` — `paths.within` is the one containment
  test — and it did not stop being a bound.
- **The payload is polled four times a second.** Cache anything that touches disk.
- **`map` is a builtin**, and now `paths` is shadowed too: `course/plan.py` defines a public
  `paths(root)`, so its import of the tool's `paths` is bound as `toolpaths`. Same trap,
  same answer — the module keeps its name and the import moves.
- **A drawer's list is the part that scrolls**: `flex: 1` *and* `overflow-y: auto`, both.
- **The title bar holds six controls** and `test/link.js` refuses a seventh.
- **`[hidden]` loses to any author rule that sets a `display`.** Toggle `el.hidden`.
- **Every colour is a token**, defined in *both* blocks at the top of the stylesheet.
  `test/hub.js` now checks that for the front door.
- **Gestures**: read `plane-core.js` first. A gesture is decided by which contacts are LIVE;
  two fingers are never the pen. And **a pan must not also be a tap** — dragging the atlas
  with a finger that started on a card used to open that card when it was lifted.
- **`#panic` is z-index 62, the map is 96 and the document viewer 95**, so the re-centre
  button is painted over by both. Known, left alone deliberately.

### The four the migration added

- **A SCRIPT THAT DERIVES ITS REPOSITORY FROM ITS OWN LOCATION IS WRONG NOW.**
  `save-and-push.sh` did, which was right while the tool was its own clone and the script
  only ever pushed itself. There is one copy of it now and `lesson/git.py` calls it for
  every workspace — so for about an hour every save committed the repository the *tool* was
  in. `test/beside.py` taps save on a throwaway repository, and three of its runs committed
  the real Atlas under the test's own message. The working directory decides, the caller
  sets it, and `test/beside.py` now asserts the tool's HEAD did not move.
- **AN IGNORE PATTERN WITH A SLASH IN IT IS ANCHORED TO ITS OWN DIRECTORY.**
  `.claude/settings.local.json` at the root matched exactly one file and silently missed the
  nine inside the workspaces, which are the only ones that exist. `**/` on purpose.
- **A HOOK THAT SILENTLY STOPS MATCHING IS WORSE THAN NO HOOK.** Every path
  `block-phi.py` knew changed the day the data moved; it would have kept refusing a
  directory that no longer exists and waved through the same content at its new address. It
  fences `phi/` **whole**, by the directory rather than by what is under it, and
  `hooks/test-block-phi.py` drives the real hook through its real entry point: nine things
  it must refuse at both addresses, nine it must allow.
- **A FALLBACK THAT IS RIGHT FOR THE MACHINE CAN BE WRONG FOR EVERY EXPLICIT CALLER.**
  A saved `courses_dir` can only be wrong after the move, so `courses(cfg)` was made to
  ignore it and use `atlas.root()`. But every test builds a config naming a temporary tree,
  and ignoring the key pointed all of them at the real repository: one run of the suite
  swept two live boards' records and stopped a tutor, through `prune_dead_records` walking
  a tree it was never given. **Staleness is fixed where it enters, not where it is read** —
  `load_config` drops a `courses_dir` that holds no `atlas.json`, and everything downstream
  goes on believing what it is told.

---

## 8. Done, and what to do then

The whole of it is done when the person can open the app, see everything they are working on
in one picture, tap into any of it, be taught or coached or have it built, have it written
up as a paper or a deck by asking, mark up any of those with a finger and get the change
back, and hand somebody a page of meeting notes whose links land where the notes say they
do.

The first of those is done. The last three are §2.

Then **delete this file** — `git rm board/HANDOFF.md` — and fold what survived into
`README.md` as sections and into `TEACHING.md` as the rules for keeping a map true. This
file is scaffolding. A repository that keeps its scaffolding accumulates two descriptions of
itself that disagree, which is exactly why this one was rewritten rather than appended to.

---

## 9. The machine

A Slurm compute node, no root, shared home, reachable under two spellings
(`/home/<user>/…` and `/mnt/dell_storage/homefolders/<user>/…`) — which is why
`paths.same_dir` compares by realpath and why a string comparison of two paths is a bug
waiting to be found. Standard library only in Python; plain browser JavaScript; nothing that
needs a package manager at runtime. `git` is 2.52.0, **`git subtree` is not installed**,
`git-filter-repo` is, at `~/.local/bin/`. The home directory has about 12 GB free; Atlas is
1.1 GB of it including `vendor/`.

**One board per workspace stays.** Its own port, its own `live/`, its own state, and the hub
moves the address between them. `ports.py` is unchanged and must stay unchanged: a port is a
pure function of the workspace's *directory basename*, the basenames are unique across the
repository, and two machines derive the same number without talking. Do not make it a
function of the path.

**Every turn is its own session.** `session_turns: 1` in `bin/tutor`: a fresh `claude -p`
that reads `board brief` and `board recap` off disk, ~22k tokens whether it is turn 2 or turn
40. What the last turn was thinking is carried in `live/NEXT.md` by `board note`, not in a
conversation. Do not change this without reading the arithmetic in the comment above it.
