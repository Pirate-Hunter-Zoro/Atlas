# HANDOFF — the repository is one, the front door is a map, and five things are left

> **You are in Atlas, in `board/`, in a fresh session, and you have been pointed at this file.**
>
> The migration is **done**. Eleven repositories are one, the board runs out of it, the front
> door is a drawn map of everything, and 32 test suites are green. What is left is the old
> brief's stage 2 onwards. The address grammar is now done as well (§2.1) and everything
> below it is written against it. The written map is done as well (§2.2). What is left is
> meeting notes, documents, and the briefing seeing what was done on a laptop.
>
> **Read §0 first: it is the working loop, and it tells you how a session in here runs
> from beginning to end.** Then §1. §2 is what is actually left, in the order it should be
> done. This file was rewritten on 14 September 2026 and is kept current by every session
> that touches it — that upkeep is step 5 of the loop, not an afterthought.
>
> *(This is not a `board handoff` file. Those are capped at 350 words and live in a
> workspace. Nothing reads this automatically. Delete it when §2 is finished and fold what
> survives into `README.md` and `TEACHING.md` — see §8.)*

---

## 0. How to work in here, and none of it is negotiable

**ONE PIECE OF WORK, SHIPPED, THEN STOP. That is the loop, and you are in it.**

The person who owns this repository wants to hand it a section number and walk away. So a
session here is not a conversation, it is one turn of a machine:

1. **Read this file.** §2 is what is left, in order. Take the first thing in it that is not
   marked DONE, unless you were told which one.
2. **Do the whole of it.** Not the easy half, and not a plan for it.
3. **Update this file, BEFORE you ship, not after.** Mark what you did DONE, write down
   what you deferred and why, and correct anything §1 through §9 now says that is no longer
   true. A handoff that describes yesterday is worse than none, because it is believed.
   **It comes before the ship because `ship.sh` commits `board/`, and this file is in
   `board/`** — update it afterwards and the edit sits uncommitted until somebody notices,
   which is precisely the drift this step exists to prevent.
4. **`bash board/test/all.sh`.** Green, every suite, before anything is pushed. `tracked.py`
   runs first and is the one that cannot be fixed afterwards.
5. **Ship it** — `bash board/scripts/ship.sh "what changed"`. Not "commit it": a board is a
   long-lived process and a commit alone changes nothing for the person holding the iPad.
   The bullet below says it again because the difference has cost an evening more than once.
6. **Then stop, and say one line: which section is next.** Do not start it. The session
   ends here so that the next one begins with a fresh context and about 20k tokens instead
   of 400k, which is the entire reason this file exists in the form it does.

**The next session's whole prompt is one line**, and it is this:

> Read `board/HANDOFF.md` and do the next thing in §2.

Nothing else needs to be said to it. If that sentence is not enough for the next session to
work unattended, the fault is in this file and fixing this file is part of the job.

*(A session cannot clear itself or re-prompt itself — that is the person's `/clear`, or a
`/loop` running the line above on an interval. What this protocol guarantees is the other
half: that every session is self-contained, so whichever way it is restarted it needs no
memory of the last one.)*

### And the things that are not negotiable

**The person who asked for this uses the board while you change it**, on an iPad, in the
middle of real work. A regression does not annoy them later; it stops the lesson now.
Galois-Theory and PSYCH-ASR must be openable and teachable at every point, and if you cannot
keep that true, stop and say so rather than press on.

- **Ship, do not merely commit, and do it yourself without being asked.** Finishing a
  piece of work includes shipping it; a session that ends with the work only on disk has
  not finished it. `bash board/scripts/ship.sh "message"` commits **only `board/`**,
  pushes, and restarts every board. A board is a long-lived process that read
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
- **Nothing that cannot go into a public repository may be TRACKED by it.** As of
  14 September 2026 two such directories do live inside the tree, by the owner's decision,
  and what holds them is three independent guards rather than their absence. Read §4 before
  you move anything on this subject in either direction; it records the rule that was
  overturned and why.

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

| What | Where | What keeps it out of the public repository |
|---|---|---|
| 308 MB of therapy audio | `research/PSYCH-ASR/phi/` | An anchored `/phi/` ignore rule, `test/tracked.py`, and the assistant fence — three, and none trusted alone |
| 1.5 GB of job output | `research/TRD-EHR/results/` | `results/` was already ignored there; `test/tracked.py` asks git whether it can see it |
| Other authors' papers and books | on disk, ignored | Their copyright, and this is public |
| The assistant configuration | `ai-config/`, its own private repository | Its settings name real paths on lab storage. Inside the tree, ignored by it, tracked by its own git |

**The first two came back INSIDE the tree on 14 September 2026**, by the owner's decision,
reversing the rule §4 used to open with. Read §4 before you argue with it; it records the
reasoning on both sides and what was built to make the new arrangement hold.

Neither is symlinked. A symlink is a tracked file pointing at the real thing, which hands
the next reader of a public repository a map straight to it. `PSYCH_ASR_DATA` finds the
first — read by `psych_asr/config.py`, exported by `slurm_jobs/lib/job_env.sh`, and both
now derive their default from **their own file's location** rather than from `$HOME`, so a
clone anywhere finds its own data and never another checkout's.

---

## 2. What is left, in order

The old brief's stages 2 and 4 through 7. Stage 3 — the atlas — was done first because it is
what the person asked for first and sees first, and because it needed no grammar to exist.
**2.1 and 2.2 are now done too**; both are kept below because 2.3 through 2.5 are written
against them and because what was deliberately deferred inside each has to be findable. The
next thing is 2.3, meeting notes — which is the first thing that spends what 2.1 and 2.2
built: links in the §2.1 grammar, on claims written in the §2.2 vocabulary.

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

### 2.2 The written map — DONE

`live/map.json` per workspace, written by the tutor, **merged against discovery on every
read and never echoed back**. Where one exists it REPLACES the derived picture; the derived
map stays the fallback for every workspace nobody has drawn, which is most of them.

`course/map.py` holds it: `validate` (pure, no filesystem), `read_written`, `write_written`,
`_resolve_written`, `_from_written` — tried first in `_shape` — plus `check` and
`written_status`. `status()` now carries a `written` flag so the board, the briefing and the
atlas can all tell whose words they are looking at.

```
board map < map.json      write it — validated, and refused WHOLE with every
                          problem printed at once. Nothing is half-applied.
board map --show          print it
board map --check         what the map claims that the tree does not
```

**The resolution rule, which is the whole reason this is allowed to exist:** a node naming a
file that has gone loses the file; a node whose files have *all* gone drops out; an edge
naming a box that is not there is not an edge; a `doc` that has moved is cleared; a
`blockedBy` naming a dropped box is dropped. *A fact cannot go stale, a declaration can, so a
declaration is checked against the facts every time it is read.* `--check` is that same pass
said out loud instead of silently, plus the one thing resolution cannot see: a box marked
`done` with an open plan step on it.

**What was built beyond the brief, and why:**

- **`board map` asks git whether the file it just wrote is visible**, and refuses with the
  exact edit if not. Every workspace ignores `live/`, and `live/` is the *directory* form —
  git will not descend into an excluded directory, so no `!live/map.json` under it can ever
  fire. It has to become `live/*` plus the negation. That is one character's difference
  between a tracked map and one silently lost on the next clone, and it is not the kind of
  thing to leave to a paragraph in a document. PSYCH-ASR's `.gitignore` is already changed.
- **Edge labels are painted**, on a plate in the gutter between two ranks, which is empty by
  construction. A derived map never carries one: an import is not a thing that flows, and
  the arrow's thickness already says how much of one it is.
- **`blockedBy` is painted on the work sheet, not on the box.** A box is eleven characters
  wide at the zoom people read the map at, and *a list is not a diagram* was paid for once
  already — but the sheet is what opens when somebody taps a box intending to work on it,
  which is the exact moment "you cannot, yet, and here is why" is worth a line.
- **The briefing says which kind of map it is**, in `brief.map_sense`. A turn that cannot
  tell a drawn map from a directory listing will read `psych_asr/asr` back to the person as
  though it were how they think about their own work. It also says how stale it is, because
  keeping the map true is part of finishing a piece of work and a rule nobody is reminded of
  lasts about three weeks.
- **The atlas gets one field**, `drawn` — the written title, on the sheet. One, on purpose:
  the atlas is a picture of the repository, not a picture of every picture in it.

`TEACHING.md` gains **Drawing the map**: read the README and the plan, name the boxes the way
the project's own documents name them, one sentence each, and stop — plus the ignore-shape
rule and the section on keeping it true.

**PSYCH-ASR's is written**, by hand, from its README and its plan: *the typist*, *the
stopwatch*, *the name-tagger*, *the joiner*, *the corrections*, *the grader*, *the grid*,
*the scorer* — eight boxes, seven labelled arrows, with the grid blocked on the stopwatch and
the scorer on the grid. `board map --check` reports exactly one thing about it, and the
report is correct: the grader is marked `done` while step 3 of the plan still names
`grade_arms`. It has been left as it is rather than silenced, because that is what the check
is for and a map edited to quiet a checker is a map nobody should believe.

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

## 4. What is ignored, and the rule that was overturned

> **THE OLD RULE, 14 September 2026, morning:** if it cannot go into a public repository,
> it does not live in the repository. It lives outside the tree and something inside the
> tree says where.
>
> **THE RULE NOW, the same afternoon, by the owner's decision:** it lives WITH ITS PROJECT,
> inside the tree, and three independent guards keep git blind to it.

This is written out at length because a reversal recorded as a shrug gets re-reversed by the
next person who reads the old reasoning and finds it good — and the old reasoning IS good.
Both halves belong on the page.

**What the old rule was protecting.** A `.gitignore` line is one line, in one file, that
anybody can delete by accident, and this repository has already been bitten by exactly that
class of failure twice: an unanchored `artifacts/` silently swallowed the
`psych_asr/artifacts/` source subpackage, and `.claude/settings.local.json` at the root
matched one file and missed the nine that existed. A thing that is public for an hour has
been published, and git remembers. For 308 MB of identifiable therapy audio with
participant IDs in the filenames, that is not a risk you take for tidiness.

**What the owner wanted instead, and it is not tidiness.** A project's data belongs with the
project. Data kept somewhere nobody can find is data somebody eventually re-creates in a
worse place, and a workspace you cannot hand to a colleague whole is one that only works on
the machine it grew on. The old rule bought safety by making the repository an incomplete
description of the work.

**So the rule changed and the guards were built.** The arrangement rests on three
independent things, none of which is trusted alone:

1. **An anchored ignore rule**, first in the workspace's own `.gitignore`. Anchored because
   of the `artifacts/` lesson above.
2. **`test/tracked.py` asks GIT ITSELF**, on every run of the suite, whether it can see
   either directory — `git status --porcelain --untracked-files=all` over each one, which
   must come back empty. That is the part that makes this safe rather than merely allowed:
   it fails BEFORE a commit rather than after, and it catches an ignore rule that reads
   perfectly well and does not work, which is the only failure mode that has ever actually
   happened here. Break the rule and the whole suite goes red with the words GIT CAN SEE.
3. **`ai-config/policy/phi.py` fences the directory by NAME**, so an assistant cannot read a
   syllable of the audio wherever it sits.

**The directory is called `phi` for that third reason**, and the name is now load-bearing in
a way somebody looking at the tree cannot see. §7 has it as a trap; four files say so where
a person might be about to rename it.

The root `.gitignore` holds two honest categories: files a command regenerates, and other
people's papers and books. **Each workspace keeps its own `.gitignore`**, and
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

## 6. The data move — DONE, 14 September 2026

Both directories are now inside their own workspaces and git is blind to both. Verified,
not assumed: `git status --porcelain --untracked-files=all` over each comes back empty,
`git check-ignore -v` names the rule and the file, the whole suite is green, and the
tracked-file audit was deliberately broken once to watch it go red before being put back.

| | Was | Is |
|---|---|---|
| Session audio | `~/phi/PSYCH-ASR/` | `research/PSYCH-ASR/phi/` |
| Job output | `~/artifacts/TRD-EHR/results/` | `research/TRD-EHR/results/` |

`~/phi` and `~/artifacts` are gone. Both moves were renames on one filesystem, so nothing
was copied and nothing was re-read.

What moved with it: `job_env.sh` and `psych_asr/config.py` derive the root from their own
location instead of `$HOME`; twelve job scripts, two READMEs, `AI_INSTRUCTIONS.md` and the
policy's own comment name the new address. **`ai-config/policy/phi.py` did not change by one
character**, because it fences the directory by name — which is the argument for that design
made twice in one day, since the move out of the tree that morning broke every pattern that
named a location.

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

### The one the data move added

- **A DIRECTORY NAME CAN BE LOAD-BEARING WITH NOTHING IN THE TREE SAYING SO.**
  `research/PSYCH-ASR/phi/` is fenced from the assistant by `ai-config/policy/phi.py`, which
  matches **the directory's name**, not its path. That is why the data could move twice in
  one day and cost the fence nothing — and it means renaming that directory silently
  unfences 308 MB of identifiable PHI while four documents go on promising a guard that has
  stopped matching. A hook that silently stops matching is worse than no hook; this is that
  trap again, wearing a name instead of a path. `.gitignore`, the README,
  `AI_INSTRUCTIONS.md` and `job_env.sh` each say DO NOT RENAME IT where somebody would be
  about to.

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

The first of those is done, and so are the grammar everything else hangs off (§2.1) and the
written map that gives it something worth saying (§2.2). What is left is §2.3 through §2.5,
in that order.

Then **delete this file** — `git rm board/HANDOFF.md` — and fold what survived into
`README.md` as sections and into `TEACHING.md` as the rules for keeping a map true. This
file is scaffolding. A repository that keeps its scaffolding accumulates two descriptions of
itself that disagree, which is exactly why this one was rewritten rather than appended to.

**Deleting it is the last turn of the loop in §0, not an exception to it**: finish §2.5,
ship it, fold this file away, ship that. The line that has been starting every session —
*read `board/HANDOFF.md` and do the next thing in §2* — then has nothing to find, which is
how the loop is meant to end and the only honest signal that it has.

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
