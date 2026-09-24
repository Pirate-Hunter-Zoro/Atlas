# Tutor-Board

A live board for tutoring sessions.

The assistant writes a lesson card into a file. A local server sees the file appear and pushes it
to every browser that has the board open — laptop, iPad, phone — where it renders as typeset
mathematics in about a tenth of a second. Nothing is refreshed by hand and nothing is compiled by
the reader. Handwriting, typed answers, and photos travel back the other way, into an inbox the
assistant reads.

It exists because reading mathematics as `\QQ(\sqrt[3]{2})` in a terminal is miserable, and
because a PDF that has to be rebuilt and re-scrolled after every sentence is not a conversation.
The same turned out to be true of being walked through code on a tablet — and, after a while, that
the two wanted the *same* board rather than two. A repository declares nothing about its subject
now: one interface, one method, whether the exercises are proofs or functions.

**It is written for one machine: a compute node on a Slurm cluster, with no administrator rights,
on a shared home.** Nothing needs `sudo`, nothing is supervised, and nothing assumes the machine
will still be yours tomorrow — see [The machine this is written
for](#the-machine-this-is-written-for).

**Contents** — [What it is not](#what-it-is-not) · [The surfaces](#the-surfaces) ·
[Commands](#commands) · [Writing a card](#writing-a-card) · [The slate](#the-slate--writing-by-hand)
· [The library](#the-library--everything-a-workspace-has-written-and-everything-it-has-produced) ·
[Getting work back](#getting-work-back) ·
[Exporting it](#exporting-the-whole-conversation) · [Any agent](#any-agent-not-just-one) ·
[Layout](#layout) · [The machine](#the-machine-this-is-written-for) ·
[Setup, start to finish](#setup-start-to-finish) ·
[Networking](#networking-reaching-it-from-anywhere) · [The iPad app](#the-ipad-app) ·
[What is verified](#what-is-verified-and-what-is-not)

---

## Picking this up in a new session

**Your job here is fixing the board from a person's account of using it.** Teaching the
subject is another session's job, in the workspace, and it does not know about this one.

**They use the board while you change it**, on an iPad, in the middle of a proof. A
regression does not annoy them later; it stops the lesson now. Galois-Theory and PSYCH-ASR
must be openable and teachable at every point.

- **Ship, do not merely commit.** `bash scripts/ship.sh "message"` commits `board/`, pushes,
  and restarts every board. A board is a long-lived process that read `serve.py` when it
  started, so a commit alone changes nothing for somebody holding an iPad. Changes outside
  `board/` need `bash board/scripts/save-and-push.sh "message" -- <paths>`.
- **Bump `VERSION` in `web/sw.js`** when any shell file changes (`board.html`, `board.js`,
  `board.css`, `plane-core.js`, `gauge.js`, `home.html`, `home.js`, `library.html`,
  `library.js`, `library.css`, anything added to the cache list), or the installed app
  serves its cached copy and the work is invisible.
- **`bash test/all.sh` before every ship.** 97 suites, all green. `test/tracked.py` runs
  early — after the browser suites, before everything else — and refuses PHI, 25-megabyte files, model dumps, other authors' papers and
  machine-local config anywhere in the repository — this is public, and git remembers.
  The last of them is **Paper-Writer's own**, run where it is checked out and skipped
  loudly where it is not: the two repositories hold one seam between them and only this
  suite is a habit, so a field renamed in the factory has to break something somebody runs.
- **Check the address after a ship.** `tutor restart` bounces every board; the HTTPS name
  should point at the workspace being worked in.
- **One change, shipped, checked, then the next.** Do not fix things noticed in passing.

Every suite names what it holds in its own first line, and `test/all.sh` prints them. If a
change makes one fail, the test is right. `test/interactive.js` and `test/sizing.js` drive a
real DOM, because a stub that returns a plausible object for everything reports that a broken
page loads fine — extend those two when something is wrong on a device.

### What is not verified, and only hardware can settle

- **How the ink feels.** Smoothing, pressure response and palm rejection are tuned blind.
  The knobs are `SMOOTH` and `RESAMPLE` at the top of `web/slate-core.js`.
- **How it looks.** There is no browser on this machine; every visual judgement here is
  inference.
- **Headless mode against a real agent, end to end.** The `headless` recipes in the config
  are best guesses at each tool's non-interactive flags, and the wrap-up turn that writes
  `HANDOFF.md` rides on that path.
- **What a usage limit prints.** The phrases in `usage_limit_says` are what the default
  agent is documented to say. Everything downstream of the match is under test; a miss falls
  back to the ordinary failed-turn path, so it costs one list in the config and no code.
- **macOS.** The platform paths in `tutorboard/`, `bootstrap.sh` and the LaunchAgent come
  from documentation. Everything this runs on is Linux.

---

## The atlas, addresses, and the four things that spend them

### The atlas — the front door, in three levels

`web/home.html` + `home.js` + `home.css`, and `test/hub.js` is its suite. **Three levels, and only
the last of them is a plane.**

1. **The door** — the families, as large tappable things, each with the one-sentence `blurb`
   `atlas.json` carries for it and a line saying what is true inside it right now: how many, how
   many live, how many have an answer waiting, how many still have something going. The family
   holding the workspace the board is in is marked, so the way back into the lesson is visible
   before the first tap.
2. **The family** — its workspaces, as cards in a CSS grid, each carrying its name, what is next in
   it, how much is outstanding, whether a board is live and on which node, and when it was last
   committed to. Tapping a card opens the sheet; opening from the sheet moves the board through
   `/switch`.
3. **The project map** — a diagram, on the board. That is the one thing in this system whose shape
   genuinely needs a plane, and `plane-core.js` draws it; see *The map — the front door of a
   course*.

**GOING IN IS A TAP AND COMING BACK OUT IS THREE WAYS, because a level you can only enter is a
trap.** `#atlas-up` is first in the head, 44px tall, and named after where it goes — *Everything*,
the word on the heading it returns to. `.atlas-head` is `position: sticky`, so it is on the glass
at the bottom of the longest family rather than scrolled off above the first card. And opening a
family calls `history.pushState`, so the back gesture and Escape both come out. **The pushed entry
carries no url**: the hash on this page belongs to `address.js`, and a family spelled into it would
be two grammars in one address. `closeFamily` paints first and calls `history.back()` second —
`back()` answers when the browser feels like it and a tap has to land now; the `popstate` that
follows repaints the level that is already showing.

**EVERY WAY BACK TO THIS PAGE SAYS THE SAME WORD, AND IT IS THE WORD ON THE HEADING IT LANDS ON.**
*Everything* — on `#atlas-up`, on the deck's `#deck-back`, and on the library's `#lib-back` when the
front door is where it was opened from. A control named after itself rather than its destination is
one nobody connects to the place they are trying to reach, which is how the old *all of it* went
unfound for its whole life. The board's `#btn-home` is the one exception and stays a bare glyph:
that bar carries the course, the chapter, the sitting badge and three controls, and `test/link.js`
holds the line at seven.

**AND THE LIBRARY LEADS BACK WHERE IT WAS OPENED FROM.** `#lib-back` is `/board` by default, which
is right for the board's own row into it — a lesson stepping sideways. It is wrong for the front
door's *Papers, decks & results*, because reading a document nobody is teaching from has nothing to do with
the lesson and that is the whole reason the button exists; landing somebody in a sitting they never
opened, to get back to the door they tapped from, is the trapped level on a different page. The
caller says so with `?from=home` — **a query parameter and not a stored flag**, because it survives
a reload, a share and a cached shell, and there is no second copy of it to go stale. `sw.js` matches
its offline fallback with `ignoreSearch`, so the query does not miss the cached page.

**AND THERE IS A FLAT READ OVER THE TOP OF BOTH, because the hierarchy cannot answer the other
question.** Two levels answer *what is in Courses*; nothing answers *where is the thing called
colibri*, because at the door no workspace is drawn and inside a family every other family's is
hidden. `#atlas-q` filters every workspace and every tree from every family at once — matching the
name on the card, the repository directory, the chapter, the written title and the next step — and
each hit carries the family it came out of. It is a level of its own drawn over whichever of the
other two was showing: clearing the field puts back the family you were standing in, not the door.
The input is `2.75rem` tall and its face is `1rem` exactly, which is the iOS floor: a field that
computes below 16px zooms the whole page when it takes focus, and the page's own magnification is
the one remaining way to be lost on this screen.

**Neither of the first two is a plane, and that is the whole design.** Six families and a dozen
workspaces is a list of six; a list is not a diagram, and drawing one on a pannable, pinchable
plane means the gesture layer is solving a problem the content does not have — on a page that can
be pinched over the top of it, which is two ways to be lost. So there is no pan, no pinch, no fit
button, no second re-centre, no `plane-core.js` and no `gauge.js` on this page at all. **The
browser wraps the text**, which is why a SHOUTED plan step cannot run out of a card: the clamp that
keeps it to three lines is CSS. How many go across is a media query — one, two, then three — which
is the old constant's promise (the same tree lays out the same way everywhere) kept by the thing
whose job it is.

- **`/atlas.json`** is the payload — `machines.atlas_payload()`, cached 30 seconds because it is a
  `plan.steps` read and a `git log` per workspace. The `current` flag, the unread answers and the
  running missions are recomputed on every call even from cache: `current` is what the door opens
  and it moves the instant a board is switched, and a badge that is half a minute stale teaches
  somebody to ignore badges.
- **A vendor family has no workspaces and is not empty.** Its contents are `payload["trees"]`, a
  second list, because a vendor tree is read and drawn and is never something work is handed in to.
  A tree's card says the commit it is pinned at and how much source is in it (with a `+` where
  `walk.MAX_UNITS` capped the count, because "250 source files" when it means "at least 250" is a
  number somebody would quote), and its sheet offers no board to move and no library. See *Vendor
  trees* below.
- **"What is next" has two answers and neither is a fallback for the other.** A course that follows
  a book is planned by `chapters.tsv`, so what is next is the chapter after the one it is in. A
  project is planned by a task list, so it is the first open step. Asking only about steps left
  every course's card blank, which on a front door reads as "nothing to do here" rather than "this
  one is a book".
- **THE BUSY STRIP NAMES THE WORK ONLY WHERE THE SITTING HAS.** `doingTurn` is true for a
  build, a paper, a deck, and for a repository whose standing answer is `do` with no aim at
  all — so the words come off `state.aim`, and with none they claim nothing beyond "working
  on it". `mode` is NOT available to branch on and must not be resurrected: `read_config`
  drops it deliberately, because a subject is not a setting.
- **A PAYLOAD IS HELD WHILE A NIB IS DOWN.** A repaint is a few hundred milliseconds of main
  thread and the main thread is what turns pen samples into ink, so a payload landing
  mid-stroke is felt as the surface going dead. `renderOrHold` in `board.js` keeps the newest
  payload — they are whole pictures, so an older one holds nothing new — and draws it when the
  hand lifts, asking `writer.inking()` (the nib, not `busy()`'s multi-second tail). The hold
  has a **700 ms ceiling**: a stroke that never ends must not stop the lesson.
- **`paintAtlas` is wrapped and cannot throw**, the same way `paintMap` is. A front door that
  throws is a blank screen in place of the app. What it says when it cannot draw is kept in
  `atlasSaid`, so the poll twenty seconds later does not wipe the sentence off the screen.
- A board on an older tool serves no `/atlas.json`; the page says so and the door above it still
  works.
- **`gauge.js` is still the board's.** It measures text into SVG boxes for the project map, where
  the face being a web font means the first measurement is of a narrower fallback: `measureText`
  answers in whatever the canvas can resolve, OpenDyslexic is `font-display: swap`, so a cold
  load lays a map out for a face it is not painted in. `gauge.js` throws its cache away when
  `document.fonts` settles and calls whoever registered with `Gauge.onFace`. The front door no
  longer needs any of it.

### Vendor trees: read and drawn, never handed work

`atlas.json` used to make one claim out of two. The vendor family was skipped, and the reason
written down was that **nothing in it is the person's to be graded on** — so reading how colibrì
works was impossible for a reason about homework. *"Who knows when we'll want to explore external
tools in the same way we're exploring everything else with tutoring sessions. That's the best way
to dive into how Colibri works."*

**Grading and tracing are different claims, and they are two rules now.** The prose in `atlas.json`
says both, separately, so the next reader cannot merge them back:

- **Not handed in to.** `atlas.workspaces()` skips the family, and that skip is what makes a vendor
  tree not a workspace: no cards, no write-up, no homework, no push, no board of its own. Several
  callers depend on it and it did not change.
- **Still read.** `atlas.trees()` lists them — every non-empty directory under a `vendor` family,
  shaped exactly like a `workspaces()` record so a caller that wants a name and a root does not
  care which list it came from. `atlas.find_tree()` looks one up by `vendor/name` or by bare
  directory name, and a miss is a miss. `course/walk.units` and `course/map.shape` take a root and
  neither asks whose it is, so a tree is walkable and diagrammable as it stands.

A submodule nobody has pulled is an empty directory, and an empty directory is not a tree. A
`tutorboard.json` sitting inside somebody else's repository does not make it a workspace either:
the family decides, not a file in the tree.

**A trace over a tree is a sitting in the workspace that is READING it.** That is the decision,
and the alternative was expensive: a sitting held over a foreign root means `Repo.root` stops
being the single answer to *where are we*, and `scope`, `sense`, the card writer and the archive
all start having to say WHICH root. Somebody tracing colibri is doing it *for* PSYCH-ASR, so the
sitting, the cards, the marks and the transcript are PSYCH-ASR's, and the tree is only its scope.

- **The tree is named in the scope**, spelt `@vendor/colibri/bin/coli-up::warm` — the marker, the
  tree as `atlas.trees` names it, then exactly what a name in that repository would be. `walk`
  keeps two resolvers: `resolve` answers for one root and goes on doing only that,
  `resolve_elsewhere` looks the tree up through `atlas.find_tree` and then asks `resolve` against
  that tree's own root, and `resolve_any` is the single entry point everything uses — the board,
  the command line, and the re-resolution `scope` does on the way out.
- **The tutor is told whose code it is.** `sense._elsewhere_sense` fires only when the scope
  actually reaches out: read it, trace it, change nothing in it, and a weakness found in it is not
  work to be done. The sitting's workspace is named, because that is where anything coming out of
  it belongs.
- **The picture is one level SIDEWAYS, and not a second renderer.** `GET /map/tree/<family>/<name>`
  answers with `map.of_tree`, which is `map.status` in the shape `map.inside` already answers in —
  so `board.js`'s `mapDeep` holds it and `paintMap` draws it. `…/inside/<id>` opens a box of it,
  and `mapTree` on the client is what makes every tap inside a foreign picture ask the tree's route
  rather than this workspace's: the two have boxes of the same name, and answering the wrong one
  draws somewhere else with nothing on the glass saying so.
- **Nothing on a tree's picture is working, next or done**, because none of it is work this side
  has taken on, and the one way to work offered on a foreign box is a trace. The rule is written on
  the picture where somebody is looking at it, not only in the prompt of a sitting they have not
  opened yet.
- **The front door is the door.** A tree's sheet offers *Trace it*, addressed at the workspace the
  board is already serving; where it is serving none, the sheet says so rather than offering a
  button that cannot work. `test/walk.py` asserts the tree is byte for byte unchanged after all of
  it.

### Work that came back while you were somewhere else### Work that came back while you were somewhere else

Set a turn going in PSYCH-ASR, go and do something in Galois-Theory, and until now the only way
to find out whether the first one had finished was to switch back and look — which is the one
thing somebody in the middle of other work will not do. **A turn that finishes in an empty room
says so on the surface you are actually looking at**, and the row it says it on is the way back.

`tutorboard/news.py` is the whole of the server half, and it is two numbers per workspace:

| | |
|---|---|
| when its newest card was written | the mtime of the newest file in `live/cards`. A card is the answer, and it is a file |
| when somebody last **looked** at it | `live/.seen.json`, written by the page — not by the server |

News is the first being newer than the second. Nothing is registered and nothing talks to another
machine: every lesson is a directory on one shared filesystem, so the board serving *one*
workspace answers for all of them by looking, which is the same rule the rest of this tool is
built on.

- **Only the page can say somebody is looking.** A board is a long-lived process that goes on
  running in an empty room, so a request arriving proves a browser is open and not that anybody
  is in front of it. `POST /seen` is sent on the first payload, when a card lands in front of the
  reader, and when the tab comes back to the front — throttled to once every twenty seconds,
  with `keepalive` so the last one is not cancelled by the app going into the background. Never
  while the tab is hidden: a board left open behind something else that went on marking itself
  read would cancel its own notification, which is the one case this exists for.
- **A workspace nobody has opened since this shipped is not news.** With no marker at all every
  lesson on the machine is "newer than never", so the first board up would announce eleven of
  them, each about last week. The first sight writes the marker at that workspace's newest card;
  day one is silent and everything after it is exact.
- **Where it appears.** On the board, a strip in `#chrome` — under the bar, with the other things
  that are true and are not what you are doing, never over the lesson and never over the board you
  are writing on. On the front door, a row under the hero, a count on the family's door, and a
  badge on the card behind it.
  Three rows at most on the board, four on the door: a fourth is a list, and a list in the chrome
  is a page to scroll past to reach your own lesson.
- **The row is a link**, spelled with the address grammar — `/#/w/<family>/<workspace>` — so it
  goes through the front door, which is the only thing that can move the one https name from this
  board to that one. Being a link and not a handler is also what makes it hold-to-open and
  readable.
- **`✕` mutes an answer; it does not mark it read.** Somebody who waves it away has read nothing,
  so the next card in that workspace brings the row back. What clears a notification is going
  there.
- Cached five seconds against the hub's quarter-second poll, and the cache is dropped the instant
  a board marks itself seen — a badge still up after the answer was read is a badge nobody trusts
  again. `test/elsewhere.py` and `test/notify.js` are the suites.

### A mission, and closing the iPad does not end it

A **mission** is a job set going in a workspace nobody is looking at — `⇥ put an assistant to work
elsewhere`, below. The daemon it starts is detached, so a closed lid never ended one; what did not
exist was any record that it had been sent, so nothing anywhere could say it was still running, and
a turn that failed said so only in the busy strip of the board nobody was looking at.

**A mission is a file in the workspace it is about**, `live/missions/<turn>.json`, beside
`agent.json` and `push.json`. Not in the browser and not in the dispatching board's process: the
point is that it is there on another device, on another node, tomorrow. Every board reads every
workspace's, off the shared filesystem, the way `news.py` does. One file per mission and the turn
that carries the task is its name — a single `missions.json` would be a read-modify-write, and two
boards dispatching into the same workspace would lose one of them.

**Three states, because they are the three somebody does something different about.** `running` —
leave it. `done` — go and read it. `failed` — send it again, or send it somewhere else. A failure
carries its reason on the row: *nothing is attached to that workspace any more* and *the allocation
colibrì runs in ended* are the same word and two different next moves.

- **The state is derived, then frozen.** Derived because nothing is alive to write it: a mission
  ends by a card being written, by the daemon dying, or by the allocation under it going, and in
  two of those there is no process left to record anything. So the ending is read off the newest
  card and off `agent.json`. Frozen because that evidence expires — a mission that failed at nine
  and any later card at eleven would read as `done` to anything looking after eleven — so the
  first reader to derive a terminal state writes it into the record, and every reader after that
  reads the ending rather than deriving it again.
- **A card newer than the mission is what `done` means**, which is `news.py`'s own rule: a card is
  the answer. Compared against the newest card *at dispatch* as well as against the dispatch time,
  so a clock a second out between two nodes cannot report a mission done the instant it starts.
- **Nothing attached is not a failure for the first five minutes.** `agent start` forks and
  returns, and the daemon writes `waking` before a `git pull` and a tailnet coming back;
  `processes.WAKING_GRACE` is the same window for the same reason.
- **Colibrì has a ceiling and it is re-stamped at every turn.** A colibrì turn runs inside the
  serve job's allocation — `coli-code` steps into it with `srun --overlap` — so the TURN cannot
  outlive that job's walltime. `colibri.status()["left"]` is Slurm's own `%L`, and it is how long
  the client answering right now has. `missions.turn_open` writes it at the start of every mission
  turn, off the generation that turn is about to step into rather than one two hops back.
  `coli-up -t` is the only lever on it. **A passed ceiling with carry budget left is a hop, not an
  ending** — freezing a mission at a dead generation's walltime is how somebody is invited to
  re-dispatch work already running on the successor.
- **A mission that outlives its node is carried, not failed.** The ceiling bounds the turn; it
  does not bound the work. `coli-code` asks `squeue` whether the job it stepped into is still
  `RUNNING` — only `RUNNING`, because a job that has self-cancelled sits there `COMPLETING` — and
  exits **75** when it is gone. That number is the one signal that tells a hop from a bad answer:
  the exit code cannot, and `sacct` is unusable on this cluster. The daemon re-queues the same
  task as a `[carry]` line, `turn_plan` answers it with the `--continue` recipe and `coli-code`
  resumes the conversation by name, so the pick-up costs seconds of client start rather than a
  15,900-token preamble. **76 is the other half**: no generation worth stepping into yet, which is
  a chain gap and neither a hop nor a failure, so the daemon waits `CARRY_BACKOFF` and asks again,
  counting nothing. The client refuses a generation with less walltime left than the session needs
  to prefill — an hour cold, half an hour warm — but only where a successor is `RUNNING` or
  `PENDING`, because with the chain broken trying beats stalling.
- **`run_turn` kills the process GROUP.** `coli-code` is a shell that runs `srun`, so killing the
  direct child orphans the step: the client goes on answering and the next turn is a second client
  on one KV slot. A turn cut at its eight-hour cap is carried like a hop and burns one, which is
  what bounds a wedged client.
- **Where the daemon went with the board, the repair is derived from disk.** `missions.carry_verdict`
  is a pure function of the record, `agent.json` and a clock, and `spawn.carry_missions` runs it
  out of the hub's poll loop in whichever board comes up next, claiming each hop with `O_EXCL` the
  way a ship is claimed. That is the case that matters: both allocations end in the same minute
  and nothing is running anywhere to remember anything. It waits for `missions.mid_turn` to say
  the workspace is idle, because a second client on one conversation is worse than a late pick-up,
  and it stops an assistant of another name that is holding the workspace — `tutor agent start`
  will not swap one for another, so the `[carry]` line would otherwise be answered by whoever is
  sitting there.
- **The evidence is `turn_at` in the record, and it has to be.** `agent.json` saying `working` with
  nothing attached cannot carry that fact across a board hop: the daemon beats every 30 s,
  `AWAY_SILENCE` is 900 s, and the board coming up adopts the left-behind daemon inside
  `ADOPT_WINDOW` and writes `waking` over the state within seconds — so that evidence is erased
  before it ripens, and the mission then reads *done* off the first card a doing turn writes before
  it starts. Only the daemon writes `turn_at`, `missions.turn_open` sets it before the client
  starts, and `turn_over` clears it on the two paths where nothing is owed. A stop is not a hop,
  and the difference is one field: `handover`, the same distinction `supervise.left_behind` draws.
- **Four numbers bound it, all in the record**, because a backoff a hop resets is not one:
  `MISSION_LIFE` 18 h of budget, `CARRY_HOPS` 6 pick-ups, `CARRY_BACKOFF` 300 s between them,
  `STALL_CAP` 2 pick-ups allowed to produce nothing. `missions.thaw` is the one entitlement to
  clear an ending, and it refuses a mission somebody has already looked at — a record a person has
  read and acted on must not be resurrected under them.
- **The backoff holds the WAKE off and says nothing about the work.** A pick-up owed and not yet
  due reads `soon`, and `judge` treats that exactly as `owed`: a mission read as nothing-owed falls
  through to the card rule, the card is already down, and the five minutes after every hop would
  freeze it `done` — which is terminal and which no thaw reaches. `missions.owed` takes only
  `owed`, so the wake is still one per hop. **A daemon waiting is not a mission nobody is driving**,
  and from the record the two are identical, so `missions.defer_carry` stamps `carried_at` on
  every pass of a chain gap — otherwise an hour of ordinary gap spends `CARRY_HOPS` on a mission
  whose client has not run once. **And the daemon stops where the record stops**: `carry_spent`
  reads the budget and the ending back off the file before it waits or hops again, so a chain that
  never comes back is not a turn every five minutes for ever.
- **Nothing new is launched for any of this.** No sudo, no cron, no new job: a function call inside
  a loop that already runs, inside the board's own chained job.
- **What a carry does not cover**, each for its own reason. The board chain stopping, because no
  admin-free process outlives both allocations — if no board comes up nothing sweeps, and the
  mission waits for a login to run `tutor resume`. A mission needing more than 18 h including
  re-prefills, more than 6 pick-ups, or 2 pick-ups that produce nothing. Work the model held in its
  head rather than writing down, which the carry prompt orders against and cannot enforce. The
  colibrì chain being down altogether, which nothing here starts — a mission dispatched with no
  generation running and none queued waits out its budget and fails, and the front door's colibrì
  tap is the lever. And a pick-up whose conversation cannot be named — a record written
  before the id was, or a hop out of a chain gap where the id was minted before the client ran —
  resumes nothing: it fails in seconds and retries as a fresh turn under a new id, which is the
  safe way round, because *the newest conversation in the store* is somebody else's as often as
  it is this mission's.
- **A mission is briefed as a doing turn, whatever the workspace teaches under.** The task arrives
  as a plain sentence of the student's, so `board brief` is the whole of what the daemon reads —
  and a workspace whose standing stance is `teach` would brief a change somebody asked for as a
  lesson. `cmd_brief` asks `missions.running`, which is a pure read: no freeze, no prune, and no
  walk for the newest card where no record is open. Only ever `True`, never `False` — a workspace
  that says `do` in `tutorboard.json` keeps saying it. The record is written *before* the inbox
  line for this, because the inbox line is what wakes the daemon.
- **It comes off the list when it is looked at**, and looking means going there: the board serving
  that workspace stamps its own finished missions on `POST /seen`, which is the far end of the row.
  This workspace and no other — there is exactly one root a board may write into. A *running*
  mission survives a look, because it is still running and that is the fact being reported.
- **Where it appears.** Above the answers in the board's strip, and above them on the front door,
  because a thing that has not finished comes before one that has. A running or failed mission also
  marks its card in the family, beside the answer badge, so one card can carry both — a mission
  that landed a card is both — and the door above it counts how many.
`tutorboard/missions.py` is the whole of it, `GET /missions` is the surface for anything that polls
rather than subscribes, and `test/elsewhere.py`, `test/carry.py`, `test/hopping.py` and
`test/notify.js` are the suites.

### A mission can be told to ship itself, and somebody else pushes it

**The want:** *"when I put anything on a mission, I should have the option to tell it to ship its
changes once it is done — I don't know if colibri is capable of doing that, but the tutor certainly
should be once colibri is done."*

One switch on `⇥ put an assistant to work elsewhere`, carried in the mission record as `ship`, and
honoured when the mission ends `done`.

**The assistant that did the work is never the one that pushes it.** The local model decodes at
three tokens a second and it is the one assistant allowed to read the fenced directory, so its own
diff is the one thing it must not push. When the mission finishes, the workspace's ordinary tutor is
woken with a `[ship]` line naming what the mission was asked to do and who did it — a hosted turn, a
second pair of eyes, and a turn that could not have read the session content it is checking the diff
for. The switch says so on the glass, because *ship it* otherwise reads as *and nobody looks*.

- **`done` only.** A mission that failed may well have left changes in the tree, and pushing those
  is the opposite of what the word "failed" means to whoever set it going. Nothing is lost: the
  changes are still there and save is a tap.
- **A private daemon is stopped first, and only when it is listening.** `tutor agent start` will not
  swap one assistant for another — a live record is *already listening* and the start is a no-op —
  so the local model's daemon is stopped before the hosted one is started. A daemon mid-turn is
  doing something somebody asked for, so the ship waits for the next pass rather than killing it.
  And a tutor already sitting there that may **not** read the fence ships it where it stands: the
  rule is not "the default assistant", it is that whoever pushes could not have read what it is
  checking.
- **The ship turn is a revision's twin.** It runs fresh, writes no card, touches no `state.json`,
  and the lesson does not resume into it. `HEADLESS_SHIP_PROMPT` in `bin/tutor`; `turn_plan` and
  `carry_after` treat `ship` exactly as they treat `revise`, and `doing_now` gives it a doing turn's
  clock because reading a diff and pushing over a tailnet is not a fifteen-minute card.
- **Handed over exactly once.** Every board on the machine sweeps every workspace's missions from
  its own poll loop, so the ship is claimed with an exclusive create — `O_EXCL` is the one thing
  that is atomic on a shared filesystem — and `shipped` in the record is what a person reads.
- **The mission's job ends when the ship is handed over.** What the push then did is `push.json`,
  which the board already paints. One surface per fact.

### And a mission gives the workspace back when it ends

**The want:** *"Make missions release the workspace."*

**An assistant started FOR a mission belongs to the mission and is released when the mission ends.
An assistant a person chose stays.** Both are the same name in the same `agent.json` afterwards, so
the difference is carried in the record: `brought` is written by whatever started it — the dispatch,
or a pick-up after a hop — and is `""` where the mission took whoever was already listening.

What it costs to leave one attached: a colibrì mission ran ten hours in a fenced workspace, shipped,
and was marked done, and colibrì stayed on as that workspace's tutor. The board's allocation hopped,
the watchdog brought the tutor back, and with no mission open the workspace fell into an ordinary
sitting — two hours of a shared node spent on a lecture nobody asked for, and the warm KV prefix that
makes the *next* mission affordable evicted to pay for it.

`spawn.release_missions` is the sweep, beside `ship_missions` and `carry_missions` in the hub's poll
loop and after both.

- **What a release leaves is the workspace's own assistant**, not an empty workspace: one with
  nothing attached does not answer a message anybody hands in to it, and `spawn.wake_tutor` reaches
  only the workspace the board it runs in is serving. The start names nobody, so `resolve_agent`
  answers — `tutor agent which` is how the board asks, because five layers of precedence copied into
  the server is a second copy that drifts.
- **The stop is a stop rather than a handover**, which is what makes it hold. `agent_stop` leaves
  `state: stopped` with no `handover`, and `supervise.tutor_verdict` reads that as a person saying
  no and never revives it.
- **Refused for every reason a dispatch may not swap the assistant**, through the same
  `swap_blocked`: somebody looking at that board, a turn in flight, somebody's own sitting, another
  mission still open, a line handed in that nothing has picked up. A refusal claims nothing, so the
  release happens on a later pass instead of being spent.
- **And refused before a ship has gone.** `done` and owed a ship and not yet claimed is a workspace
  about to be looked for; emptying it under that is the ship landing nowhere.
- **Only an assistant the mission brought.** Whoever is *actually* attached has to be that name —
  one somebody swapped in by hand while the mission ran is theirs — and it must not be the one the
  workspace runs by default, because stopping that to start it again throws away a warm prefix to
  prove a point. Both of those close the record so no board asks again.
- **Once, across every board on the machine**, claimed with an `O_EXCL` create the way a ship is,
  and claimed *before* the stop rather than after: two boards both deciding on a ship write an inbox
  line twice, two both deciding on a release signal a daemon the first already replaced.
- **Either ending.** A mission that failed left an assistant attached just as surely as one that
  finished, and waiting for a ship that is never coming would hold it for the week the record lives.

### What leaves this machine, and the check git cannot make

`board push` and the save button both run what they are about to commit past
`ai-config/policy/phi.py` first. That policy is the lab's, not this tool's: `names_phi` is loaded
out of the repository by path rather than copied in here, and a repository with no policy file
refuses nothing rather than deciding for itself what session content is.

**A `.gitignore` already stops a phi FILE** — `test/tracked.py` audits every tracked path — and it
can do nothing at all about phi CONTENT. A fixture cut out of a transcript, an example hard-coded
from one, a docstring quoting a span: written by the one assistant allowed to read that directory,
pushed by a turn that was not. Every push from this tool is unattended, so the last thing before a
public remote was nothing.

- **Per file, by the workspace it is in.** A push here commits the whole repository, so *is the
  pushing workspace fenced* is the wrong question — a fixture in `PSYCH-ASR` goes out under a push
  from anywhere. Checking every changed line was the other option and it is wrong the other way:
  this repository's own documentation names the fenced directory on nearly every page, so it would
  refuse the commit that documents the check. Prose about a fence is not a hole in one. So each
  changed path is looked up against the workspaces that hold one (`fenced.holds`, already cached on
  every payload), and only those files are read.
- **Untracked files are the whole point.** `git status --porcelain -uall`, because a fixture
  written an hour ago has never been tracked and `git diff` cannot see it. For a tracked file it is
  the ADDED lines, so a line that was already committed is not read again.
- **What it catches, said plainly.** The fenced directory by name, the old data tree, and the
  artifact shapes. It is a regex: a bare sentence of dialogue with no path and no extension around
  it is not catchable this way, and a guard believed to do more than it does is worse than none.
  That is the other half of why the ship turn is a hosted assistant reading the diff — the machine
  check has no judgement in it, which is what lets it run unattended, and the turn has judgement,
  which is what covers what a regex cannot see.
- **The refusal names the file**, changes nothing, and is written where the board paints it —
  `worktree.busy_reason`'s shape, for the same reason. `board push --anyway` is the override and it
  is deliberately a keyboard act: a button on a tablet that waves a PHI fence through is the thing
  the fence is for. From the iPad the way past it is to tell the tutor, which is a person deciding
  and an assistant acting.

`tutorboard/leaving.py` is the whole of it and `test/tracked.py` is the suite.

### What a link in here can name

`web/address.js` is the grammar and nothing else: it parses, it spells, it touches no DOM and makes
no request, so both pages load it and `test/address.js` drives it with no browser at all. `addrGo`
in `web/board.js` is the one resolver. The Python `test/address.py` is about the *tailnet* address
and a different thing entirely, so the runner labels it `tailnet` — two rows called the same name
is how a green suite gets read as covering something it never touched.

```
#/w/<family>/<workspace>                   the workspace, on its map
#/w/…/node/<id>                            one box, selected, sheet open
#/w/…/card/<nnnn>                          one card in the current lesson
#/w/…/archive/<sitting>/<nnnn>             one card in a finished sitting
#/w/…/doc/<ident>[/p<n>]                   a document, optionally one page
#/w/…/code/<path>[::<symbol>]              a walk unit
#/w/…/tree/<family>/<name>                 a vendor tree, drawn and read here
#/w/…/hw/<set>/<problem>                   one problem of a problem set
#/w/…/slate/<nnnn>                         one page of handwriting
```

Three rules, and where each one lives:

1. **A name from a browser never reaches a filesystem.** Nothing in `address.js` builds a path;
   every component is looked up by the resolver in the payload the board already holds —
   `mapInfo.nodes`, `lastLive.cards`, `readingInfo.documents`, `walkInfo.units`, `knownSets`,
   `lastLive.slate`, and for a past sitting the archive's own list. A miss is said as "that is not
   here any more", never as an error and never as something near it.
2. **A link that no longer resolves says so where it is written.** `markAddresses` runs at the end
   of every render and marks every `#/w/…` anchor in the lesson against that same payload: struck
   through and grey for an address whose target has gone, red and wavy for text that is not an
   address at all, ordinary for one that still resolves. Rendered links to an address carry no
   `target="_blank"` — a second tab is a second board.
3. **One resolver, one speller per side.** `Address.format` is the only thing on the board that
   builds an address and it refuses to spell anything its own parser would reject; `spell()` fills
   in this workspace. `tutorboard/spell.py` is the same speller for the Python side — a meeting
   frame pointing at a box, a card handing the work over to another one — and it is a module of its
   own so that there is one of it rather than one per caller. `spell.here` takes a workspace root
   and answers "" for a directory in no family, which has no address at all. The grammar is strict
   for the same reason: a card is four digits, never one and never seven.

**How the board knows which workspace it is**: `/health`'s `id`, fetched once at load. Until that
answers, `mapLand` does not land — an address naming another workspace cannot be told from one
naming this one, and landing on the wrong guess is worse than landing a moment later.

**Another workspace is another board on another port**, and the only thing that can move the one
address between them is the front door. The board hands the whole address to `/`; `home.js` routes
it with `addrRoute` — a workspace already serving goes straight to the board, one that is not is
switched to first, and a workspace that is not in the repository any more says so on the atlas
rather than throwing. Recorded in `sessionStorage`, so a switch that does not land is reported
rather than bounced between two pages for as long as anybody watches. The atlas's sheet opens a
workspace *through* the address as well, so a tap and a link do the same thing by the same code.

**The bar carries where the board is**, by `replaceState`, riding on `mapRemember` — which already
decides what "here" means and is called from everywhere that changes it. Never `pushState`: a pan
is not a page. It never downgrades, either: landing on a card and then having the bar revert to the
bare workspace is a link nobody can copy off the glass.

**Two forms name something finer than the board can paint today**, and neither is dropped or faked.
`code/<path>::<symbol>` opens the walkthrough picker with that file chosen and says which function
it was pointing at; `hw/<set>/<problem>` opens the set in the contents drawer and names the
problem. Both are one line of honest text over the containing surface. When a code viewer and a
per-problem surface exist, two branches of `addrGo` change and no address written before then
breaks.

### The written map

`live/map.json` per workspace, written by the tutor, **merged against discovery on every read and
never echoed back**. Where one exists it REPLACES the derived picture; the derived map stays the
fallback for every workspace nobody has drawn, which is most of them. How to draw one is in
`TEACHING.md`; this is what holds it up.

`course/map.py` holds it: `validate` (pure, no filesystem), `read_written`, `write_written`,
`_resolve_written`, `_from_written` — tried first in `_shape` — plus `check` and `written_status`.
`status()` carries a `written` flag so the board, the briefing and the atlas can all tell whose
words they are looking at.

```
board map < map.json      write it — validated, and refused WHOLE with every
                          problem printed at once. Nothing is half-applied.
board map --show          print it
board map --check         what the map claims that the tree does not
```

**The resolution rule, which is the whole reason this is allowed to exist:** a node naming a file
that has gone loses the file; a node whose files have *all* gone drops out; an edge naming a box
that is not there is not an edge; a `doc` that has moved is cleared; a `blockedBy` naming a dropped
box is dropped. *A fact cannot go stale, a declaration can, so a declaration is checked against the
facts every time it is read.* `--check` is that same pass said out loud instead of silently, plus
the one thing resolution cannot see: a box marked `done` with an open plan step on it.

- **`board map` asks git whether the file it just wrote is visible**, and refuses with the exact
  edit if not. Every workspace ignores `live/`, and `live/` is the *directory* form — git will not
  descend into an excluded directory, so no `!live/map.json` under it can ever fire. It has to
  become `live/*` plus the negation. That is one character's difference between a tracked map and
  one silently lost on the next clone.
- **Edge labels are painted**, on a plate in the gutter between two ranks, which is empty by
  construction. A derived map never carries one: an import is not a thing that flows, and the
  arrow's thickness already says how much of one it is.
- **`blockedBy` is painted on the ways sheet, not on the box.** A box is eleven characters wide at
  the zoom people read the map at, and a list is not a diagram. It is behind the second tap
  rather than the first, and it is one of the two reasons that control is drawn at all: a box
  waiting on another has something to say before anybody opens a sitting on it.
- **The briefing says which kind of map it is**, in `brief.map_sense`, and how stale. A turn that
  cannot tell a drawn map from a directory listing will read `psych_asr/asr` back to the person as
  though it were how they think about their own work.
- **The atlas gets one field**, `drawn` — the written title, on the sheet. One, on purpose: the
  atlas is a picture of the repository, not a picture of every picture in it.

PSYCH-ASR's is written by hand from its README and its plan: *the typist*, *the stopwatch*, *the
name-tagger*, *the joiner*, *the corrections*, *the grader*, *the grid*, *the scorer* — eight
boxes, seven labelled arrows, the grid blocked on the stopwatch and the scorer on the grid.
`board map --check` reports nothing about it: every file, document and arrow on it is still there,
and no box marked `done` has an open plan step sitting on it. A finding is left as it is rather
than silenced, because that is what the check is for and a map edited to quiet a checker is a map nobody
should believe.

### The meeting deck

`tutorboard/meeting.py`, `board notes --meeting --since <spec>`, and a **notes** button on the
atlas head. `test/meeting.py` is the suite. This is the first thing that spends both the
grammar and the written map, and it does not work without either.

```
board notes --meeting --since 7d
board notes --meeting --since 2026-09-01 --workspace research/PSYCH-ASR
board notes --meeting --since last                 since the last deck
board notes --meeting --since monday --print       the text of it; writes nothing
```

A **Beamer frame per workspace that moved**: what landed (commits, summarised past four on a
frame, plus the plan steps that came off), what it means in the written map's own words, what is
next, what is blocked and on what. Every claim carries its address. `document.BEAMER_HEAD` is the
class, themed the way the hand-written decks in `research/PSYCH-ASR/docs/` are themed.

**Assembled, not generated, and this is the decision the whole feature turns on.** A model asked
to write the deck produces better sentences and costs the one property that makes it usable
without checking: a slide you are going to stand behind in front of your mentors is the last place
for a sentence nobody wrote. If the deck reads badly the fix is `meeting.frames`, not a turn.

**One deck, at `meetings/meeting.pdf`, replaced each time.** No `-v1, -v2, -v3`: this is a one-off
communication tool and the only one worth keeping is the most recent. `meetings/` is tracked, so
nothing accumulates in the tree and `git log` still holds every deck there has ever been — the
cheap version of *"we're not gonna save every presentation"*, and recoverable, which a delete is
not.

**One frame is exactly one page, and that is load-bearing rather than typographic.** `[shrink]`
scales a frame that would overflow instead of spilling it, because the page a mark is on is how
the mark finds its workspace — a frame that quietly became two pages would route a mentor's
suggestion into the wrong project. `meeting.page_map` is written beside the deck as
`meetings/meeting.json` at build time; page 1 is the title and belongs to nobody.

**Which projects, with what each one has to report.** `POST /notes/what` takes the period and
returns `gather`'s own counts per workspace — three commits, one step closed — and the sheet
draws them as a list with the ones that moved already ticked. `POST /notes` carries `want` to
`meeting.build`, which filters `atlas.workspaces` by it and refuses an unknown name by name.

**Reading it, and marking it up.** `/meeting` is a page of its own — `web/meeting.html`,
`web/meeting.js`, the library's own reader over a document that belongs to the repository rather
than to a workspace. `GET /meeting/view` hands back pages through `paper.pages_of(..., "meeting")`
— the same rasteriser, cache and `/paper/<name>.png` addresses the library uses, with its own
cache namespace, which is what the `tag` argument was there for. Each page carries
`data-ann="doc/meeting/p<n>"` and the caption under it names the project that frame is about,
before anybody draws.

**A mark on a slide is DIRECTION, and it must not go to `/library/feedback`.** That route files a
complaint about the document and wakes a `[revise]` turn — it would spend a turn polishing a
throwaway deck while throwing away the only thing the marks said. Asked in these words: *"NOT to
give feedback on them in terms of the presentation… My mentors will give me suggestions on new
directions to take — THAT'S what these annotations will serve as."*

`tutorboard/proposals.py` is the routing, and it is the geometry: ink on the TRD-EHR frame is
direction input for TRD-EHR, because that is whose frame it is. `POST /meeting/direction` writes
one turn per marked workspace, in that workspace, with the picture of the ink copied to
`meetings/marks/p<n>.png` — beside the deck, because a path into the serving board's
`live/annotations/` means nothing from where the turn reads it.

**Proposed, never applied.** `direction.write` and `POST /direction` write the direction at the
root, open a new sitting which archives the lesson, forget the last turn's note and replace the
assistant. Two of those are destructive, and doing them unattended to five workspaces because
somebody drew on five slides is the worst outcome available. So the turn is told to write **one
card** saying what it would change and stop — `sense.direction_mark_sense` — and the person taps
⟳ rethink if they agree. `news.elsewhere` is what tells them the card landed.

**And the ink goes with the deck it was drawn on.** This is the one document in the system where
an old mark has no meaning at all: it was consumed into a direction the moment it was sent, and
the replacement deck has a different project on page 4. `meeting.clear_ink` and
`proposals.forget_pictures` run on every build.

**Nothing in a note is generated prose.** Every sentence is assembled from something a person
already wrote: a commit subject, a plan step, the name they gave a box. A note whose sentences were
invented has to be verified before it can be used, which is worse than none.

- **A plan step that closed is a DELETED LINE.** These plans are written to "DELETE, don't
  annotate", so nothing records that a step finished — the deletion is the record, and
  `meeting.closed` reads it out of `git log -U0` over the plan's own files. That is the only place
  in the system that treats a diff as a fact.
- **A workspace is in the note because it MOVED** — commits or a closed step. Being blocked is a
  standing fact, not news: a note for a quiet fortnight listing every blocked box in the repository
  is long, and length is the one thing a meeting note cannot afford. A blockage on a workspace that
  *is* moving is reported, which is when somebody can act on it.
- **A link is real or it is not a link.** With no board running to link through, the address is
  written out as text and the note says why, once. Wrapping an inert fragment in something that
  looks clickable is the same failure the grammar exists to prevent, one layer out.
- **Any running board is a valid base.** Each one serves the same front door and the front door
  switches, so the first reachable board is a door to all of them.
- **One speller.** `tutorboard/spell.py` produces exactly what `Address.format` produces,
  character for character, and the suites check it both ways. The deck is one of its callers; a
  hand-off card naming another box is the other.

Two bugs in the document pipeline surfaced here, both waiting for the first document to contain a
link. `#` is a macro parameter character, and `inline_tex` escaped `#`, `%`, `&` and `_` *after*
turning `[text](url)` into `\href{url}{text}` — so every address came out as `\href{\#/w/…}`, a
fatal LaTeX error and no PDF at all. URLs are lifted out before the escape pass and put back after,
with only `#` and `%` escaped. And `md_to_tex` returns a string, not a list: `"\n".join()` on it
joined its *characters* and produced a forty-page document one letter per line, which compiled
perfectly.

### Documents: annotate, export, write

**Annotating.** `annotate.js` was card-only because of a single assumption spelled eleven times —
that the thing being annotated is found by `[data-card="…"]`. It is found by `keyOf(node)` and
`nodeFor(id)` now, and a node carries **either** `data-card` (a card, the original and still the
common case) **or** `data-ann`, whose value is the tail of an address. Everything downstream — the
store, the undo history, the autosave, the payload — treats the id as an opaque string. Nothing in
`annotate.js` parses it; `writing.py` is the only thing that reads it, because the tutor has to be
told *where* a mark is and the address is that sentence.

`doc/<ident>/p<n>` is live: each page of the document viewer is wrapped in its own `.paper-page`
box, ink is anchored in fractions of that box, and the pen is on the paper bar because `#chrome` is
behind the panel at z-index 95 — which had made a page of a deck the one surface on the board you
could look at and not write on.

- **The key never becomes a path.** `ann_ok` validates the key against known shapes and
  `ann_file` *derives* a flat filename with a short digest, so two anchors can never collide and
  none can climb out — a key written straight into `<notes>/<key>.json` is safe only while every
  key is four digits. A card's record keeps its plain name. The anchors use `\A…\Z`,
  not `^…$`: in Python `$` also matches before a trailing newline, so `doc/a/p1\n` passed a
  `$`-anchored check and went into a filename.
- **A mark on a document answers no card**, so `answers` is empty for one and the turn falls to
  where its time puts it. Claiming a card would file it under one it has nothing to do with.

**A MARK BELONGS TO ITS SITTING, BECAUSE THE KEY DOES NOT.** Cards are numbered from 0001 inside
one sitting, so `0001` names a different card the moment a section is filed — and both halves of
the system held the old one. `board archive` moves the card-keyed records into the sitting's own
folder with the cards, leaving a document's marks where they are: those are anchored to a document
the workspace offers and outlive every lesson in it. The browser's store is dropped when the
sitting under it changes, and only then — `load` merges rather than replaces, deliberately, so a
store dropped on any other payload is ink vanishing between two strokes of one word.
`archived_session` reads a past sitting's marks out of the archive, so the transcript keeps its
markup the way it already keeps its ink.

`test/anchor.py` and `test/marks.js` are the suites.

**Exporting.** Four scopes, one exporter, in `document.SCOPES`:

| | |
|---|---|
| `lesson` | the sitting that is open. The unit, and the common case |
| `chapter` | every sitting filed under one chapter, plus the open one if it is on that chapter |
| `sitting` | one finished sitting, by the id the archive gave it |
| `all` | every filed lesson and the open one, as a master document |

`board export --chapter ["Ch 7"]`, `board export --sitting <id>`, `POST /export` with
`{scope, which}`, and a **PDF** button on every row of the history panel — which is where a person
is already looking at the sitting they want. `chapter` is what makes an evening's work
exportable at the size somebody actually wants it: without it a chapter that took three evenings
comes out as a third of itself or as the whole course, and nothing in between.

What does not change is the property that makes an export worth having — **the whole sitting in
reading order**: the question, every revision of the working as it was actually sent, what the
tutor said, and the next attempt underneath. A scope decides which sittings are in the document and
nothing else about what a document is.

- **A stem per scope**, so two documents about the same chapter do not share one series of version
  numbers. `v4` has to answer "which one is the latest" for *one* document, and one sitting and the
  chapter it belongs to are two.
- **A heading and a contents page wherever there is more than one sitting**, not only in `all`.
  Three evenings running together is a wall of text with one attempt at an exercise directly under
  another and nothing between them.
- **A miss is said as a miss.** A chapter nobody taught and a sitting id that is not in the archive
  are mistakes somebody made, not empty documents; the sitting id is matched against what the
  archive holds and never joined onto a path.

**Writing, and the seam is one module.** `tutorboard/manuscript.py`, `board make --paper
["title"]`, `test/writing_up.py`. Paper-Writer admits a job by finding a filled-in
`PROMPT_TEMPLATE.md` in a drop folder once the file has stopped changing. That is a contract made
of a directory and a file format — the loosest coupling two programs can have — and it is why this
module is under 700 lines rather than a second copy of somebody else's engine.

```
board make --paper ["title"]   assemble a job from this workspace and drop it
board make --paper --dry-run   print the job; drop nothing
board make --status            what the FACTORY says it is doing, verbatim
board make --delivered         manuscripts that have landed in this workspace
```

**The board does not run Paper-Writer.** No import, no process — `test/writing_up.py` checks both.
If the daemon is not running the job waits in the inbox, which is what should happen and is said
out loud rather than discovered later. What the board assembles is all off disk in the workspace:
the plan's open steps, the directories it actually keeps results in, the manuscript prose that
already exists so it is not written twice, and the written map's own names for the parts.

- **`PAPER_SOURCE_DIRS` IS AN ALLOWLIST, WITH A SECOND REFUSAL BEHIND IT.** This is the board
  choosing, on somebody's behalf, which trees a manuscript factory may mine — and one workspace
  here holds 308 MB of identifiable therapy audio and its transcripts. `RESULT_DIRS` names what may
  be offered; `NEVER` refuses `phi`, `data`, `inbox`, `stage1`, `stage2`, `raw`, `audio` by
  directory name whatever else changes. The failure is silent and one-way: a job naming that tree
  would be admitted, gathered, and every number in the resulting ledger would come from patient
  data in a manuscript nobody would think to check. The suite fails if this stops holding.
- **Nothing in a job is invented.** The plan's steps go in as WORK, not as claims — a step is a
  thing to do and a claim is a thing to argue, and the template says so itself. The venue and the
  checklist are left blank on purpose: a wrong venue plans the manuscript to the wrong length and
  an inferred checklist places the wrong obligations.
- **A job appears whole.** Written to `.part` and renamed, because the harness admits a file once
  it has stopped changing and a file that appears empty and grows is one it may read halfway
  through.
- **`service/paperwriter.env` is read, not run** — it is deliberately "plain KEY=value with no
  logic", which is the only reason that is safe. What this machine actually runs with outranks the
  documented default, so a job lands where something is looking.
- **The job names where the paper lands, as a field.** `## Delivery`, one line,
  `landing: <workspace>/manuscripts/<paper>` — `manuscript.landing_for`, read by the factory's
  `jobspec.landing`, and `stages/delivery` places a second copy of every artifact there while
  keeping its own under `PAPER_OUT_DIR`. **Absolute**, for the same reason `## Revision` carries
  `workspace:`: the factory is another repository and cannot resolve a relative path against a root
  nobody named. And it cannot be a setting — one harness serves every workspace, so a single
  out-directory cannot be each asking workspace's own. A landing that is relative or unwritable is
  recorded on the paper and the paper stays DELIVERED; the work is already safe under `OUT_DIR` by
  the time it is attempted, the same rule a missing pandoc gets.
- **It is the paper's own directory, and the factory appends nothing to it.** Two papers from one
  workspace would otherwise both be `manuscript.md` in one folder — and naming it here is what
  lets a **revision** land exactly over the document it corrects: `landing_for` gives the
  corrected document's own directory when the job carries one, and the paper's slug under
  `manuscripts/` when it does not. A correction placed beside the original under a slug of a
  title that has drifted is two documents where there is one paper, and the library offers both.
- **The factory's own output is not this workspace's prose.** `_sections` builds the
  do-not-rewrite list out of `manuscripts/` and now that papers really land there it skips
  `feedback/`, `parts/`, `sections/` and `report.md` — `NOT_DOCUMENTS`, the same names
  `course/library.py` refuses, and `manuscript.delivered` skips them too. Handing the factory its
  own report back as prose to preserve is telling it the report is the paper.

### The briefing sees what was done on a laptop

`lesson_git.beside_the_lesson(repo)` and `brief.beside_sense(repo)`, in the briefing between the
map and the handoff. `test/beside_lesson.py` is the suite. What a turn is told: what the person
committed to **this workspace** since the newest card the tutor wrote, and which files are
uncommitted right now. Subjects and filenames — **never the diff**. A briefing is about 22k tokens
and it stays that way.

- **`_seen_until` is the newest card's mtime**, because a card is the tutor saying something and
  therefore the last moment it certainly knew the state of the world. Failing that, the sitting's
  `opened`. Capped at three days either way: a lecture opened a fortnight ago and left open is the
  ordinary case here, and a fortnight of commits is a changelog, not news.
- **Scoped by pathspec**, not filtered afterwards, and cached for 20 seconds because the payload is
  polled four times a second.
- **`live/` is not somebody's work.** It is where the board writes cards, ink and state while a
  sitting runs, so reporting it would open every turn with a list of what the board itself just
  did. The uncommitted count is taken *after* that filter, so the number and the list are about the
  same files.
- **Paths are relative to the workspace.** `git status --porcelain` prints them relative to the GIT
  ROOT, so in this repository every name arrives with `courses/Galois-Theory/` on the front — a
  turn would have had to strip a prefix to find a file sitting right beside it.
- **Silent when there is nothing.** A heading over "no changes" is forty tokens of nothing, on
  every turn, for ever.

**The wording IS the feature**, and it is the only part of this worth being careful about. A turn
that mistakes a commit somebody made on their laptop for something it did itself will report having
done work it has never seen — confidently, in a card, with nothing on the board able to contradict
it. So whose work it is, is said three times — in the heading, in the sentence, and as an
instruction about what to do with it — and the suite checks that every mention of the tutor having
done it is inside a prohibition.

### What is deliberately not built

- **Annotating code.** `code/<path>[::<sym>]#L<n>` is one entry in `ann_ok` and one in `ann_says`,
  and it is not written, because there is no code viewer to draw on and accepting a key nothing can
  produce is a branch that rots. The `code/` address already lands on the walkthrough picker, which
  is where that viewer goes.

---

## The standing rules

Decisions rather than regressions, so no test holds them. A change that contradicts one of these
is wrong even when every suite is green.

- **A list is not a diagram.** The boxes are the content; the work is drawn ON them. Never draw
  the plan's steps in a column.
- **AND A DIAGRAM IS NOT A LIST.** The other direction cost as much: the front door drew six
  families and a dozen workspaces as one SVG plane, panned and pinched, with a fit button because
  it could not be seen at once. Six families is a list of six. **A plane is for content whose shape
  needs one** — the project map, and nothing else on the front door. Where the content is a list,
  it is HTML in a grid and the browser lays the text out.
- **A NEW THING GOES IN A MODULE NAMED FOR THE ONE JOB IT DOES, and if that means moving
  something first, move it first.** Every workspace has a map whose boxes are its modules and
  whose arrows are drawn from what they import, so a module that does six unrelated things draws
  as one box with eleven arrows into it and the diagram teaches nobody anything. **The picture is
  a mirror, and the failure is the module rather than the renderer.** `helpers`, `utils`, `common`
  and `misc` are four spellings of *nobody decided*. This binds every turn, not just a human one:
  it is written in `TEACHING.md` under *Where a new thing goes* and in `sense.DOING_SENSE`, which
  in a headless turn IS the prompt, and `test/teaching.py` holds the two in step. **Draw the
  diagram before refactoring anything** — the box with too many arrows into it is the next
  refactor, and guessing which module is untidy before you can see the graph is how the wrong one
  gets rewritten.
- **FIX THE RULE, NEVER ITS OUTPUT.** Where a wrong thing was produced by code, the code is what
  is wrong: fix the module that produces it and run it again. A hand-edited artifact cannot be
  reproduced, cannot be reviewed by anybody without the inputs, and is wiped by the next run — and
  that holds however close to right the file could have been got by hand. It binds every turn whose
  product is a change, so it is written in `TEACHING.md` under *Fix the rule, never its output* and
  in `sense.RULE_SENSE`, which in a headless turn IS the prompt; `test/teaching.py` holds the two
  in step. Its other half: **write where the code already writes, never over an input you are
  scored against**, because overwriting the input makes the measure agree with you for free.
- **Name the measure the work already has.** Most of these workspaces keep one — the check they
  run, the number their plan quotes. `sense.MEASURE_SENSE` is in every briefing, teaching and
  doing alike, and in the inbox line of the four turns that never read one — a ship, a write-up,
  a revision, an overhaul. It asks for the measure to be RUN before and after rather than quoted
  off the plan, because the number on the plan is the number *before*. A named gap beats an
  invented number, and a write-up quoting a figure it invented is the worst version of that.
- **Tracing is not grading.** `vendor/` is not a place work is handed in to; that says nothing
  about whether it can be read. Two rules, written separately in `atlas.json`'s own prose:
  `atlas.workspaces()` skips the family, `atlas.trees()` lists it. Widening the walk is not
  widening what counts as a workspace.
- **Estimated text overflows.** Measure with a canvas. Cache it. `gauge.js` — on the board's map,
  which is the one surface that still draws text into SVG boxes it sized itself.
- **A rule that is right for one kind of turn can be exactly wrong for the other.** Before making
  any rule about the order of a turn, ask which kind of turn it is for. The fix is always to scope
  the rule, never to weaken it.
- **A second tap is ceremony.** `POST /session` takes `begin: true` for exactly this reason.
- **A glyph is not a label.** A bare diamond did not read as "the map".
- **Nothing a reader can be waiting on may be silent.** A failure is news until something newer
  happens, not until a timer says so.
- **`board open` is the only thing that opens a sitting.** Writing `state.json` directly skips the
  archive and the handoff parking, and loses the lesson being left.
- **Nothing is registered.** `live/map.json` and `atlas.json`'s six family names are the only
  exceptions in the whole system, and both are re-resolved against the tree on every read.
- **A path out of a file is untrusted**, including out of a README. `paths.within` is the one
  containment test, and widening the bound to the whole repository did not stop it being a bound.
- **The payload is polled four times a second.** Cache anything that touches disk.
- **`map` is a builtin, and so is the shadowing trap.** `course/plan.py` defines a public
  `paths(root)`, so its import of the tool's `paths` is bound as `toolpaths`. `test/document.py`
  imports `tex` as a module, and a new local called `tex` made the name local for the *whole*
  function, breaking a call two hundred lines above it. The module keeps its name; the import moves.
- **A drawer's list is the part that scrolls**: `flex: 1` *and* `overflow-y: auto`, both.
- **The title bar holds six controls** and `test/link.js` refuses a seventh.
- **`[hidden]` loses to any author rule that sets a `display`.** Toggle `el.hidden`.
- **Every colour is a token**, defined in *both* blocks at the top of the stylesheet.
  `test/hub.js` checks that for the front door.
- **Gestures**: read `plane-core.js` first. A gesture is decided by which contacts are LIVE; two
  fingers are never the pen. And **a pan must not also be a tap** — on the map, a finger that
  starts on a box and drags the plane must not open that box when it lifts.
- **The floating buttons are `recentre.js`, shared with the front door.** `#panic` puts the
  PAGE's magnification back; beside it are the re-centres for the planes that have a pan and zoom
  the page knows nothing about — `#findink` (**my ink**) for the writing surface, `#mapback` for
  the map — and `#redirect` (**rethink**), the only one that
  changes what the work IS. All of them are placed against the VISUAL viewport, because
  `position: fixed` pins to the layout one and a pinch moves the other. **Each is its own widget**
  — its own place, remembered under its own `board.panic.<id>` — so a press and hold picks up
  that one and leaves the rest where they are; a tap acts, and the two are told apart by TIME,
  never by distance. They start out down the right-hand edge in order, from wherever the group
  was last left, so nothing jumps the first time a board runs with them separate.
- **They are z-index 62, and 97 while `body.mapping`.** The map is 96 and the document viewer
  95, so on the map the way back was painted over by the thing you were lost in. Raised only
  there: everywhere else 62 is right, over the lesson and under the menu. **`#redirect` is 97
  always** — a plan is most often discovered to be wrong while looking at the picture of it, so
  the one control promised to be reachable at any moment has to be over the two things that
  cover the whole screen.
- **NOTHING AUTOMATIC CLAIMS THE ADDRESS.** `board vpn serve` is the FORCED claim and its
  whole meaning is a person saying "point it at THIS course"; `board vpn serve --if-free`
  asks first, through `ts_repoint`, and is what `link()` in `bin/tutor` calls on every
  launch. Calling the forced one there meant starting a tutor in any workspace took the
  address from whatever course was being read on the iPad. `test/serving.py` is the suite.
- **ONE HTTPS NAME, ONE BOARD, AND A DEPLOY MUST NOT MOVE IT.** `tailscale serve status`
  prints a TCP forward per board AND the https names at the bottom; only the `/ proxy
  http://127.0.0.1:PORT` lines say where a NAME points, and reading the first `127.0.0.1:`
  in the output reads a forward belonging to whichever board printed first. `served_by_name`
  in `bin/board` is the parse. `tutor restart` bounces every board in turn, so the name's
  holder is briefly down and the next board up is free to claim it — `cmd_restart` in
  `bin/tutor` therefore reads the holder BEFORE it stops anything and hands the name back
  afterwards. Getting either half wrong drops somebody mid-proof into another course.
- **A PORT IS A PURE FUNCTION OF THE WORKSPACE'S DIRECTORY BASENAME**, never of its path.
  `ports.py` must stay that way: the basenames are unique across the repository, and two machines
  derive the same number for the same workspace without talking to each other. One board per
  workspace — its own port, its own `live/`, its own state — and the hub moves the address between
  them.
- **A DIRECTORY NAME CAN BE LOAD-BEARING WITH NOTHING IN THE TREE SAYING SO.**
  `research/PSYCH-ASR/phi/` is fenced from the assistant by `ai-config/policy/phi.py`, which
  matches **the directory's name**, not its path. That is why the data could move twice in one day
  and cost the fence nothing — and it means renaming that directory silently unfences 308 MB of
  identifiable PHI while four documents go on promising a guard that has stopped matching.
  `.gitignore`, the README, `AI_INSTRUCTIONS.md` and `job_env.sh` each say DO NOT RENAME IT where
  somebody would be about to.
- **A SCRIPT THAT DERIVES ITS REPOSITORY FROM ITS OWN LOCATION IS WRONG.**
  `board/scripts/save-and-push.sh` is the only copy and `lesson/git.py` and `bin/board`'s `push`
  both run it, for every workspace — so a location-derived root would commit the repository the
  *tool* is in whatever the caller meant. The working directory decides, the caller sets it, and
  `test/beside.py` asserts the tool's HEAD did not move.
- **AN IGNORE PATTERN WITH A SLASH IN IT IS ANCHORED TO ITS OWN DIRECTORY.** A rule for an
  assistant's config directory written at the root matched exactly one directory and silently
  missed the nine inside the workspaces, which were the only ones that existed. `**/` on purpose,
  and the rule is now the directory whole rather than the files under it.
- **A HOOK THAT SILENTLY STOPS MATCHING IS WORSE THAN NO HOOK.** A fence written against a path
  keeps refusing that path after the data moves, and waves the same content through at its new
  address. `block-phi.py` fences `phi/` **whole**, by the directory name rather than by what is
  under it, and `ai-config/adapters/test_claude_code.py` drives the real hook through its real entry point:
  nine things it must refuse, nine it must allow.
- **A FALLBACK THAT IS RIGHT FOR THE MACHINE CAN BE WRONG FOR EVERY EXPLICIT CALLER.** A saved
  `courses_dir` can only be wrong after the move, so `courses(cfg)` was made to ignore it and use
  `atlas.root()`. But every test builds a config naming a temporary tree, and ignoring the key
  pointed all of them at the real repository: one run of the suite swept two live boards' records
  and stopped a tutor, through `prune_dead_records` walking a tree it was never given.
  **Staleness is fixed where it enters, not where it is read** — `load_config` drops a
  `courses_dir` that holds no `atlas.json`, and everything downstream goes on believing what it is
  told.

---

## What it is not

Not a chat client. The conversation still happens wherever the assistant is running — a terminal,
an editor, an SSH session. The board is the *display* for the mathematics, plus a back channel for
the student's answers and working. One process per course repository.

## The surfaces

Pages, and it is worth being clear about which is which, because they were built in that
order and the earlier ones did not know the later ones were coming.

| Surface | Who writes there | What for |
|---|---|---|
| **Home** (`/`) | — | what you are in the middle of, every course found beside it, and the way in |
| **The board** (`/board`) | the assistant | the lesson: prose, typeset mathematics, tables, compiled diagrams |
| **The answer panel** (`/board`) | the student | one block under the question — write on the slate, or type, with a toggle |
| **The drop zone** | the student | a file that was not written on the slate |
| **The library** (`/library`) | the student | every paper and deck this workspace has written; a word about what is wrong with one, or an overhaul of it, and the corrected pages re-drawn where you were reading |
| **The meeting deck** (`/meeting`) | the student | the one deck, read on the glass and marked up on it; a mark on a project's frame is that project's new direction, proposed on its own board |

The library is the one that touches nothing else: it writes no card, opens no
sitting and changes no `state.json`, so reading a document or correcting one
cannot interrupt a lesson in progress.

Answering happens in one panel under the question: the slate and a typed half, and a toggle
between them. Whichever the student used last is the one that opens next. Nothing has to be
typed anywhere else, in the app or in a terminal.

### The first turn

An empty board is the one place that rule left a hole. With no card there is no question, so no
answer is owed, so nothing opens the slate — and in mathematics there is no box to type in either.
The board was a dead end until somebody went to a terminal and prompted the assistant, which is
exactly the ceremony `tutor` exists to abolish.

So an empty board carries one button, **ask the tutor to begin**. It sends a `begin` signal — a
tap that carries its own meaning, not a composer — which lands in the inbox as an ordinary unread
message and so wakes `board wait` like anything else. Sending it makes the board
non-empty, which retires the button; a tutor woken four times writes four opening cards.

Because a signal has no sentence in it, the inbox line carries its own meaning rather than a bare
tag: a headless assistant is woken with *there is nothing on the board yet and they are waiting,
open the session and write the first card*. `test/begin.py` drives that whole round trip.

### How a lesson is taught

The method lives in [`TEACHING.md`](./TEACHING.md) at this root — **not** in each
course's contract — and `board start` copies it into that course's `live/` every
time. The brief, the headless prompt and the cold-start line all point at it, so
every assistant in every repository reads the same document and none of them can
drift out of step.

The rule it all follows from: **a lesson is exercises, all the way down.** There
is no explaining step that stands on its own. Whatever would have been explained
is handed over as something to *do* — the tutor supplies the objects, a group of
order six, two polynomials, three candidate subgroups, and the student shows what
they are: is this one an example, which of these three is not, where exactly does
the second one fail. That showing *is* the teaching.

The shape, in a mathematics course:

1. **Read the section's exercises first.** They are the specification for the
   lesson; the prose is the means.
2. **Choose a manageable few** — three to five, sometimes two — and say in the
   opening card which ones and why each earned its place. Not all of them.
3. **For each in turn:** state the exercise in full, so the student can see what
   the work is for, then **ladder it** — one tiny thing to work themselves per
   idea the exercise actually needs, one per card, thirty seconds of writing
   each, and none at all for an idea it does not need. Two rungs is normal;
   five means the wrong exercise was chosen.
4. **Then put the exercise back in front of them**, restated in full — *now try
   4.12* is not a re-pose when it is eleven cards up a tablet — and ask for it,
   **with every definition it uses listed under it**, one line each. Nobody
   should have to scroll back up a lesson to find out what they are proving.
5. **Then ask it again, as the last line of the card.** Statement at the top,
   definitions under it, the question again at the bottom — so the last thing
   above the board they write on is what they are being asked to do. Asking once
   at the top does not survive six lines of symbols: *"I've got a board to write
   on and have to scroll up to see the question again."* Twice on one card is the
   question standing where the pen is, not repetition.
6. **Read what comes back.** A wrong answer gets its break located, not repaired.
7. **Write it up and compile it, before the next problem is posed.** `board hw
   use`, the statement and their own argument into the file, `board hw file`,
   `board hw build`. Problem by problem — not at the end of the sheet, and not in
   batches of three, because a sitting is abandoned far more often than it is
   finished tidily and the gap between what is agreed and what is on disk is
   exactly what gets lost. Compiling is the tutor's job, never the student's.
8. **When the chosen set is done, offer more** as a question — the student
   answers, or taps **skip**, which means *move on*.

Any rung can be skipped, like any other prompt, and a student who skips every one
of them and goes straight to the exercise is using the board exactly as intended:
the ladder is scaffolding for an answer, and anyone who can reach without it
should.

Front-loading is the failure it exists to prevent: no chapter summary, no "here
is everything we will cover", no card that teaches for four paragraphs and asks
at the bottom. The measure of a sitting is how many exercises got answered.

Sections are archived, so nothing has to be crammed — **◷** reopens any of them
with the student's own working still in it, and an exercise left undone is a note
for the next sitting rather than a loss.

In a repository whose work is code the unit is a change made in the student's own
editor, and it is posed, laddered and re-posed exactly as an exercise out of a
book is. When a turn says it has been implemented — typed, or written on the
slate — the tutor goes and reads what actually changed, and locates the break
rather than repairing it. The rest of the discipline is identical, because it is
the same discipline.

### Sending, and what happens next

Sending says what happened to the ink, and never paints a second copy of it above the surface
it is still sitting on.

Now the surface stays where it is and reports underneath itself: **sent at 8:12 — the tutor is
reading it**, or *waiting for the tutor*, or *no tutor is attached to read it yet*. What was
sent is not rendered into the lesson while it is still the thing you are looking at.

The moment the tutor replies, that changes: your answer takes its proper place under the
question, the receipt stands down, and **the writing surface moves below the feedback** — so
correcting your work happens under the criticism of it rather than scrolled off above it.

### The verdict is a band down the response, and every answer is kept

**Green got it right, red did not, amber is everything else** — a reply that answers rather than
marks, which is most of a build sitting and most of a walkthrough. It is a rule for every kind of
sitting, not for mathematics: a step that worked, a step that did not, and a question put back to
you are the three moods of a build as much as of a proof.

**The response carries the band, and the answer and its board are the quiet half.** The card is
the moment — it is what arrives and it is where the eye goes — so it takes the 3 mm rule, the
wash, and the flash it lands in. The receipt in the transcript and the board holding the working
take the same colour at 2 mm and mixed back toward the rule: findable when you scroll to it an
hour later, not competing for the moment it landed in. Green on the answer, green on the board,
green on the card, a tick and a flash is one thing said five times.

**Which card is a reply is a question about the transcript, not about its kind.** A reply is the
first card written after an answer, with nothing else in the question's run between the two.
`correct` and `wrong` say so themselves and carry their verdict wherever they fall; every other
kind is amber only where it is answering something. That is what makes the amber case exist at
all — `lesson` is the commonest reply in a sitting that does the work, and a rule keyed on the
kind cannot see it — while keeping a `lesson` card that is teaching, and a `recap` anywhere,
plain. A page tinted end to end says nothing.

A question whose reply has not arrived is painted **nothing at all**. Waiting is a different state
from *neither right nor wrong*, and the pulsing strip is what says so. The colour lands the moment
the reply does: the verdict is part of a card's and a turn's identity on the page, so a node
already on screen picks it up rather than keeping the colour it was born with.

**A run of right answers says how many.** From the second one, the card carries a green chip —
*3 in a row* — beside the tick, on the card where it happened, so scrolling back up the evening
shows where a run started and where it broke. A wrong answer resets it and nothing else does: not
an aside, not a question, not an evening's teaching in between.

**The colour and the mark are the meaning; the movement is not.** The chips are text — ✓, ✕, ? —
so they inherit the colour, scale with the type, survive a card folded to its heading, and work
for somebody who cannot tell the green from the red. With `prefers-reduced-motion` set the
stylesheet refuses the flash, the tick's pop, the cross's drop and the streak chip's entrance, and
takes away nothing else. **Nothing in `board.js` consults the preference for this**: the flourish
sits on top of a page that is already correct without it.

`cardVerdict`, `verdictOf` and `streakAt` in `board.js`; `.card[data-verdict]`,
`.card[data-streak]`, `.mine[data-verdict]` and `.board[data-verdict]` in the stylesheet;
`test/mine.js` for both halves and the run, `test/typed.js` for the window that asks for the
animation off, `test/theme.js` for what the tokens are.

**And a typed answer is kept, the way a written one is.** Ink keeps every attempt — a board
apiece, down the page — and typing used to keep one: a send revised the newest turn on the
question, so a second answer overwrote the first, and a question open for an evening ended with
one of the four things said under it. A send now revises **only what the box was handed to
correct** (`correctingTurn`, set where an old answer is loaded back in and nowhere else).
Everything typed into an empty box is a new answer, kept in the order it was given, under the
feedback it was replying to, and labelled *answer 2 of 3* the way a second board says *attempt 2
of 3*.

### The typed half renders as you type, and keeps what it sent

**A rendered block sits above the box, and it does two jobs that are one job.** Before a send it
is a **preview**: type `$\gamma^2 = 2$` and the formula appears above the box, typeset, saying in
advance exactly what the transcript will show. After a send it is the **record**: the words stay
where they were typed, rendered, and the box under them opens empty for the next thing. That is
what makes the two halves of the panel symmetrical — box and block against slate and board —
because sent ink has always stayed where it was made and sent words used to leave nothing behind.

**Nothing renders inside the box, and nothing can.** `#saybox` is a textarea, which holds
characters and no markup by definition. A `contenteditable` would render in place and cost iOS
autocorrect, its undo stack, selection under a thumb, `autosize`, the draft save and the ⌘-Enter
send; a block above it costs none of that.

**One renderer, or the block lies.** `renderMarkdown` then `typeset`, the same pair a card goes
through — `test/mine.js` asserts that what the block shows and what the transcript shows are
character for character the same string.

**The block appears only when there is something to show**: a dollar, a TeX delimiter, or a
backslash command in the box, or an answer already sent on this question. Prose with none of
those leaves the panel exactly the height it was.

**A tap on the block is how a typed answer is corrected.** It hands the words back to the box and
sets `correctingTurn`, so the next send is a revision of that answer rather than a second one.
This is the only place the restore runs: while it ran on every paint of the panel the box could
never open empty, which is what it does now on every question.

**Two things make a `$` cheap, and a third was refused.** A one-tap `$…$` on the panel wraps the
selection or drops a pair with the caret between them, because on an iPad keyboard a `$` is a hunt
through a second layout. And a backslash command sitting outside any delimiter — which renders as
nothing at all — is **named in the block**: *\gamma will not render — wrap it in $…$*. What is
refused is wrapping anything that looks like TeX: `\d+` in a regex, `C:\temp` and a shell escape
are all backslash commands to a pattern and none of them is mathematics, and this board is used in
code workspaces. The hint asks `protect`, the renderer's own first pass, what counts as code, so a
regex inside backticks raises nothing.

**The block declares no font of its own, deliberately.** Its prose inherits the reading face from
the body and KaTeX brings the one it ships, so the words are dyslexic-friendly and the mathematics
is untouched by construction rather than by a rule. `test/typed.js` owns the panel — with the real
KaTeX loaded, because a stub cannot tell a block that was typeset from a block that was handed to
nothing — and `test/mine.js` owns what happens to an answer after it is sent.

### A card is typed out, and nothing moves while it is

A card arrives whole — it is a file — so this is a reveal of something already in hand rather
than a stream. It is typed **character by character** at 110 a second, past reading speed and
still visibly a hand, capped so the longest card there can be is over in four seconds.
`typeOut` in `board.js` is all of it; `test/feedback.js`, `test/typed.js` and `test/seam.js` are
the suites, and `test/seam.js` is the one that drives the whole flow a person performs — ink on
the glass, Send, the receipt, the reply, the next question — because the fault that survived
three reports lived in the seam between the other two.

**Every response, whatever wrote it and however it lands.** A card written once and a card
written *over* are both responses, and `board write --over` is how every turn that does the work
answers: one sentence so the board is not blank, then several minutes of code, then the report
replacing that sentence. So the mtime is part of a card's identity here, exactly as `rev` is part
of a turn's — without it a rewritten card had "already been seen", and the whole effect was
switched off in precisely the sittings that take longest to answer.

**The card is its final size from the first frame, and that is the whole design.** Nothing is
ever taken out of the layout: every character is laid out the moment the card lands, and what
has not been said yet carries `visibility: hidden`, which occupies its space to the pixel and
wraps exactly where it will wrap. Moving one character from unsaid to said cannot reflow the
card or anything under it. The reveal this replaced hid each block outright, so a card was one
paragraph tall when it landed and grew by a paragraph at a time — and what grew with it was the
lesson, the writing surface included.

- **Mathematics, code, tables and figures are atoms.** Cutting a KaTeX subtree into characters
  destroys it, and half a formula is nonsense to read. Each is hidden whole and appears whole
  when the cursor reaches it, costing a few characters of time so it lands in its place in the
  sentence. The typing runs **after** the typesetting pass, never before: KaTeX cannot measure
  what is not laid out.
- **Nothing cancels it.** A hand on the page used to dump the remainder, and on a tablet a touch
  is how you scroll. The cap is the protection instead: a long card is typed faster, never
  skipped.
- **Reduce Motion does not govern this one animation.** The owner asked for the response to
  arrive character by character, by name, three times; an explicit request about one animation
  outranks a system-wide default about movement, and `typeOut` does not consult
  `prefers-reduced-motion` at all. It still governs everything else on the page — the card's
  entry slide, the reveal, the settle. A shorter animation is not a compromise available here:
  what gets reported is the answer arriving all at once, and a faster dump is still a dump.
  A suite therefore cannot opt out of the animation either: anything asserting where the
  writing surface sits has to wait for the typing, the way the two flows at the foot of
  `test/link.js` do.

**A card lands ABOVE the writing surface, and that is the whole of it.** `tailAnchor` in
`board.js`: a new node at the end of the lesson is inserted in front of the surface, never
appended after it. The surface has no key of its own, so a reconcile that appends puts the
tutor's reply *underneath* a full-height open board, off the bottom of the glass — it types out
where nobody can see a character of it, and the jump at the end is the surface taking its proper
place and revealing the finished card in one go. Read from a chair that is "the next board
appeared under my answer and then the whole response showed up at once between the boards",
which sounds like a question about when the surface moves and is not one. Put the card above the
board and nothing has to move at all.

**And a surface that is not open yet does not open** until the last character lands. There is no
tool bar to flicker, so it simply arrives a beat later under a response that has finished, and
nothing is drawn in its place either: a question's dormant board is not photographed while its
live surface is held shut. That is `writerHeldShut`, and it is the branch the hold still exists
for.

The typing pass therefore runs **before** anything decides where the surface goes, on the same
frame the reply lands; deciding first and typing afterwards means nothing is typing yet on the
one frame that matters, and the hold does nothing. A tap on an earlier board overrides it — a
request made by hand outranks an animation.

**A CARD IS WHOLE OR IT IS NOT ON THE BOARD.** `open(path, "w")` truncates
before it writes, and the poll that builds the payload runs four times a second
over a shared network filesystem — so a poll landing between those two moments
sees a card that exists and has nothing in it. On the glass that is worse than a
blank card: there is nothing to type, so `typeOut` skips it, so **no hold is
taken**, so the writing surface comes down and the next board appears before the
response. Then the real body lands and types underneath a board already there.
Measured: card 0041 empty at 10:38:38, its 1,817 characters typed at 10:39:14 —
thirty-six seconds, because the empty parse is cached against `(mtime, size)`
read through NFS attribute caching. Reported as *"the next board showed up before
the tutor response showed up - I thought we fixed this?"*, against a trace
showing both cards typing perfectly, **because they did**. So `board write`
renames a finished file into place (`os.replace`, same directory, atomic), and
`has_body` keeps a bodyless card off the board whoever wrote it — an interactive
tutor writes its own files and a shell redirect truncates the same way.
`test/whole.py`.

**And the watchdog does not report a stall that did not happen.** `holdTyping`
bumped `typingNow` and then asked `keepTyping()` — which tests a `typingUntil`
left behind by the *previous* card, so a card arriving minutes after the last
one traced `stall` before painting a character. It arms the deadline now instead,
and `keepTyping` is called from exactly one place: a frame of the animation,
which is the only place its question means anything. The trace is what this code
is diagnosed from; a trace that lies is worse than no trace.

**The hold is a list of the cards still arriving, not a class on a body.** `typingHeld` in
`board.js` is taken and given back with the hold itself. A marker that the *animation* sets is
lost by every path that holds without animating, and there is always one of those. What reads it:
whether a surface that is not open yet may open, whether the receipt still says the answer is
arriving, and how far down a surface that has been moved up by hand may come.

**A stall loses the pacing and never the order.** The hold carries a deadline as well as a count
— 2500ms of silence, pushed out by every frame — so a card that stops mid-sentence in a
backgrounded tab cannot park the surface for ever. What happens when that deadline passes is that
the card is finished **whole** and the hold moves to a 250ms settle: the animation is gone, the
answer still lands as its own event with the board arriving after it. Letting go silently is how
the fault this machinery exists to prevent comes back out of its own safety valve.

**☰ → what just happened** reads back the board's last three hundred moves — every card that
typed, what it asked for and what it took, every placement of the surface and the hold that
decided it, and every stall. It is in memory and per page load, so it is gone after a reload and
has to be taken from the sitting it happened in; the copy button is there because the person who
can see a fault is not the person who can read the source. Its head, and the first line of what
it copies, is **which shell is running**, read from the page's own cache rather than from the
server: an installed app serves its cached `board.js` until `VERSION` in `sw.js` moves, so *the
fix is wrong* and *the fix never reached this device* are the same sentence from a chair, and a
version the server reported would read correct in exactly the case it is there to catch.

### Writing on the lesson itself

A question about a lesson is nearly always a question about one *place* in it — this line,
that step, the word "clearly". **✎ annotate** in the title bar turns the cards into
something you can write on directly; tap it again to stop, and the lesson scrolls and
selects exactly as before while it is off.

Marks are anchored to the **card**, in that card's own coordinates, not to the page. The
lesson reflows constantly — the type-size buttons, the reading face, the iPad rotating, a
figure finishing its compile — and ink pinned to the page would end up somewhere else every
time. Pinned to the card, it moves with the words it is about.

They save themselves about a second after the pen lifts, so a reload never costs them.

**The rubber takes out what it touches**, rather than the whole stroke it meets — which is what
the slate does, and right there, because a stroke on the slate is a letter. A
stroke *here* is a ring around a paragraph, a line under a sentence, an arrow across half a
card: one pen-down covering the width of the lesson. Touching any part of it took all of it, so
with two or three marks on a card a tick in the corner removed the annotation. A stroke the
rubber crosses is split now, and each surviving run on either side is a mark of its own.

**Select**, beside Pen and Erase, is the same lasso the slate has: loop around something and it
is caught if more than 60% of it is inside the loop. What is picked can be dragged onto the
words it is about, deleted, or put on the clipboard — see [One clipboard, three
surfaces](#one-clipboard-three-surfaces). Like writing, it is a gesture for the pen: with a
finger set to *scroll* a finger scrolls, here as everywhere.

**Send always sends**, and never raises a *Send what?* bar to be answered on a second tap. A
Send button that does nothing is worse than no Send button: it strands an answer on the glass
while the student believes it has been handed in, and the board's receipt never appears because
the code that writes it is never reached.

So the working goes first, unconditionally; the button sits on the surface holding the
working, and that is what it means. If there are marks on the lesson that have not been
sent, they are then *offered* — **send those as well** — which cannot lose anything,
because by then the working has gone. Writing nothing and marking a card is the one
exception: with an empty surface the marks are the answer, and a blank page is not sent
alongside them.

Marks made when no answer is owed — on a card from ten minutes ago — get their own **send
my annotations** button, because otherwise they would be stranded with no Send button
anywhere on the page.

*Unsent* means unsent. Which cards have been handed over is recorded next to the ink, in
`live/annotations/<card>.json`, and comes back on the payload — so a reload can tell ink
that was delivered from ink that was only ever autosaved. Without that record, marks made
in one sitting and forgotten went on demanding a decision every time anything was sent,
for ever, and sending re-delivered them as a fresh turn each time.

What the tutor receives is the ink and the card it sits on, plus roughly where — *near the
top*, *in the middle*. It wrote that card and reads it back off disk, so it does not need a
picture of its own words, and nothing has to rasterise typeset mathematics in a browser.
`test/annotate.py` drives the round trip; `test/link.js` drives the layer in a real DOM.

### Declining a prompt

Teaching goes: explain, then ask for an example or a worked exercise. Not every one of those is
worth writing out, and **a prompt that cannot be declined is a prompt that gets answered badly to
make it go away**. So the answer block carries **skip this one** in its header, where it dies with
the block it belongs to.

Skipping is a turn like any other — it is in the transcript, and it wakes the tutor, because the
tutor has to carry on. Unlike a sent answer, which keeps the block open so a mistake can be
corrected in place, a skip closes it: the whole point is that the prompt goes away. The next
question is a fresh ask, unaffected.

What the tutor is told is *they are not writing this one out; do not re-ask it and do not press
them on it, carry on with the lesson*. Whether to work the exercise aloud anyway is the tutor's
judgement, not a rule.

The drop zone predates the slate: before there was anywhere to write, the only way to get
handwriting to the assistant was to photograph it and drop the photo on the page. It survives
because it still covers the cases the slate cannot:

- paper you worked on away from the iPad, photographed
- a problem sheet, a scan, a page from a book
- a screenshot of something on another machine
- pages written in Notability or GoodNotes and exported as PDF

For ordinary "here is my answer", use the slate. The `＋` in the title bar is the same upload path
and is the practical one on iOS, where dragging a file onto a web page is awkward.

## Changing the direction of the work

Three hours into an evening the shape of the work turns out to be wrong — the scope, the
question, the thing being built. **Saying so is one tap, from any surface**, and the tap is
worth what it costs only if every part of the board that was pointed at the old direction is
pointed at the new one before the next turn runs.

The button says **rethink**, and is placed the way the two re-centres are, against the visual
viewport — a control placed by CSS alone pans off the glass when the page is pinched. It moves on
its own and is remembered on its own; it is nobody's passenger. It sits **over** the map and the
document viewer, which the other two do not: the moment somebody decides a plan is wrong is
usually the moment they are looking at the picture of it.

The sheet says what is about to happen before it happens, because five things happen at once:

| | |
|---|---|
| `DIRECTION.md` at the workspace root | their sentence, stamped with the day. Tracked, so it crosses machines |
| the lesson they were in | archived whole, still readable under ◷ |
| the sitting | reopened, named after what they said; the old handoff parks under its own chapter |
| `live/NEXT.md` | cleared — one turn's note to the next about a lesson that no longer exists |
| the assistant | **replaced**, not asked to change its mind |

That last row is the half a prompt cannot do. A running tutor holds the old direction in its own
conversation and no file on disk can contradict it, which is the same reason a chapter switch
gets a fresh one.

From then on `board brief` puts the direction at the **top** of every briefing, above the
method, the contract and the handoff — because everything under it may have been written for the
direction it replaced, and a turn that reads it last has already believed three documents it
should have doubted. The turn woken by the change is told, in the imperative, to rewrite the
plan, redraw the map and report what it did; a turn asked politely to consider replanning hands
back a plan and does nothing. `board direction --show` reads it from a terminal and
`board direction --clear` takes it off.

**And it says so for the whole of the several minutes it takes.** Replacing the assistant and
rewriting a plan is not quick, and the turn that does it is told to write one sentence FIRST so
the board is not blank — which is exactly the card the busy strip would ordinarily read as *the
answer is here, stop talking*. So the daemon records what a turn was woken for (`turn_signal` in
`bin/tutor`, off the `[direction]` tag the inbox carries), and the strip:

| when | what it says |
|---|---|
| the tap | *changing direction — replacing the tutor* |
| the old one is going, the new one coming up | *the new direction is in the inbox. The tutor is being replaced, and the one that comes up re-plans from it. No need to send again* |
| the turn is running | *re-planning — reading the plan and rewriting it for the new direction* |
| past two minutes | *still re-planning — the new plan lands here* |

None of it is painted as a failure, because nothing has failed: a board that cannot tell a
deliberate replacement from a dead tutor reports the one thing the person just asked for in the
words of the thing they most fear. The strip stops when the **turn** does, not when a card lands.

`test/direction.py` drives the whole round trip against the real handler; `test/steering.js`
drives the button and the sheet in a real DOM; `test/hanging.js` holds the words above and
`test/elsewhere.py` the signal underneath them.

## Setting it up on the cluster

One script does the whole of it, in the shared home, where every node you are ever given can see
it:

```
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git ~/Atlas
bash ~/Atlas/board/bootstrap.sh
```

It installs `tutor` and `board`, fills in the vendored submodules under `vendor/`, names this
machine on the tailnet, and prints what is left to do. No `sudo`, nothing system-wide.

There is no list of repositories to keep anywhere. There is one repository, the courses arrive
inside it, and a workspace is any second-level directory holding `tutorboard.json`,
`AI_INSTRUCTIONS.md` or `live/` — discovered, never registered.

### One identity, whichever node you were given

The tailnet identity is one machine that moves, and that is the whole of why the iPad's address
survives an allocation ending: the registration lives in the shared home, so `compute304` and
`compute309` are the same `*.ts.net` name a week apart. The machine's own name still changes with
the allocation, because it is a different machine and every ownership check depends on knowing
that — see [`board node`](#one-address-and-the-machine-holding-it).

If you ever run a second machine, give it a name of its own (`bootstrap.sh --name`, or `board vpn
up --hostname <name>`) and install the board on the iPad from each. An address only ever opens a
board on the machine holding it, so two machines mean two icons — this tool is written for the one
on the cluster.

### Arriving on a new node

An allocation ending takes the board, the tutor and `tailscaled` with it, on a machine you will
never be given back. The tailnet name the iPad has baked into it then points at nothing, and
**no node can be asked to take over**, because being asked requires something already listening
and that is precisely what died. A supervisor that outlives the machine does not help either: it
brings a service back after a reboot, and a compute node does not reboot, it stops being yours.

So there are two moments a compute node gets. The moment you log in to it, which is this section;
and the whole life of a job that queued its own successor, which is
[the allocation renewing itself](#the-allocation-renews-itself-and-the-board-repairs-itself) and is
a supervisor of the only shape that works here -- one that IS the machine.

```
tutor resume                 take the board over here
tutor resume galois          a particular course, not the last one
tutor resume --no-agent      the board, and you drive the tutor yourself
tutor resume --force         move it even from a node that is still alive
```

It catches this machine up on the board and on the course, brings the link up, starts the board for
the course you were last in, re-points the tailnet name, and attaches a tutor. The first of those is
the reason the hook below matters as much as it does: nothing else pulls this repository on a
compute node, because nothing on one survives long enough to run a timer.

**Which course** is the newer of two signals: when you last *named* one (`tutor galois`,
`tutor headless galois`, `tutor resume galois` — recorded in
`~/.config/tutor-board/chosen.json`) and when a course was last *worked in* (the newest of
`live/.board.json`, `state.json`, `turns.jsonl` and `cards/`). Neither alone is enough. File times
alone cannot tell a course you chose from one a login hook happened to start — and since starting a
course touches its files, a hook that resumed the wrong one would go on resuming it for ever,
quietly. A name alone is no better: one given last week should not beat an afternoon spent
elsewhere. This is not a registry of courses; those are still whatever directories are sitting
there. It records a decision, which is the one thing the filesystem cannot tell you.

What it is careful about is when *not* to act:

- a board already running here is left alone — only the tailnet name is re-checked, since a second
  board on this node moves it;
- a board on a node that Slurm still says is yours is left where it is;
- no Slurm at all means *unknown*, not *gone*, and is also left alone;
- a machine Slurm does not list as yours — a login node — gets no board at all.

**A board and its tutor die separately, and a board coming back is not a tutor coming back.** The
daemon belongs to the allocation that started it; the board comes back on whichever node you next
log in to. So the two end up on different machines, the older allocation ends, and from the
machine you actually work on the course reads *board on compute301, no tutor* — with every
recovery path looking away from it. Leaving the board where it is is right; leaving the question
of whether anything is listening to it unasked is what kept a dead tutor dead for an evening.

So a login asks the node the board is on, over ssh, with `tutor agent ensure`. The record is
believed first, and `processes.agent_attached_away` is the only honest test from another machine:
a heartbeat, never the pid, because a pid written on one node names a process table this one
cannot read and very likely a stranger. A listening daemon rewrites its record every time
`board wait` times out, so three missed wake-ups — a quarter of an hour — is silence nothing
healthy produces. A tutor that is well therefore costs the login nothing, and a silent one is
asked about exactly once per shell. `tutor restart --tutors` is not that path and never was: it
bounces tutors that are attached, and says *no tutors were attached* about one that has died.

Over ssh only, and not the Slurm step the hop falls back to: a step has to hold itself open for
the life of what it started, and one sleeping step per login is too much to pay for a repair that
is usually not needed. When ssh cannot get in, the line says so and names the command to run
there — a board with nothing listening to it is the one thing you must never have to guess at.

### `salloc` is the whole of it

**The machine you were given has nobody on it.** `salloc` grants an allocation and hands you a shell
on the **login node**; the compute node itself never gets a login, so "the only moment a compute
node gets" was a moment that never arrived unless somebody opened a terminal on the node by hand and
left it open. That is the ceremony: the allocation exists, the machine is yours, the board is not
running, and the thing standing between them is a person keeping a second session alive on a laptop.

So the login node hands the whole command over. `tutor resume` on a machine that holds an allocation
it is not part of runs the same command on the node instead, and everything that decides anything
happens over there — the node pulls this repository, re-execs onto what it pulled, bounces whatever
is holding the old code, starts the board for the course you were last in, re-points the tailnet
name and attaches a tutor. The login node only ever decides which node to knock on.

Which node, in three rules: the one a board is already on, because a live board is never moved; then
the allocation this shell belongs to, since `salloc` puts its job id in the environment of the shell
it starts; then the newest allocation. Only ever a node Slurm says is yours.

It goes in over **ssh**, which leaves nothing behind on the login node: the board ends up in the
node's own session, exactly where it sits when somebody opens a terminal there. Where ssh cannot get
in — a cluster whose credentials do not reach the nodes — the work goes into a **Slurm step**
instead, which needs no credential of its own and which holds itself open for the life of the
allocation. That last part is not decoration: everything a step starts lives in the step's cgroup,
and that cgroup is emptied the moment the step ends, detached or not.

The step is asked of the allocation that **holds that node**, which is frequently not the one this
shell sits in: `salloc` exports its own job id, while the node being knocked on is whichever one a
board was last recorded on. Give Slurm a job that holds no part of the node and it refuses the step
for a node configuration, naming neither. So the step is also watched for a moment before anything
claims a board started, since a refusal takes about a hundredth of a second and arrives after
`Popen` has already returned.

```
salloc …                     and nothing else
tutor resume --no-hop        do it here, wherever here is
TUTOR_BOARD_NO_HOP=1         the same, for a shell
```

One line lands in `~/.tutor-resume.log` either way, naming the node and what it said. That is
deliberate even under `--quiet`: quiet is for a login with nothing to do, and this one crossed a
machine.

To make it automatic:

```
bash scripts/install-autostart.sh --login-hook
bash scripts/install-autostart.sh --uninstall
```

That appends a marked block to `~/.bashrc`, which the shared home puts on every node **and on the
login node** — which is the point of it being on every shell rather than only on the ones you open
on a compute node. It is what keeps the node current: a fix shipped from anywhere is pulled, the
launcher re-execs onto it, and
anything still running the old code is bounced — see
[Every session starts by catching up](#every-session-starts-by-catching-up). It runs in
**interactive shells only** — a login file that writes to stdout breaks `scp`, `sftp` and
git-over-ssh with a remote error nobody can read — takes a lock so five terminals do not race, and
backgrounds itself so no prompt ever waits on the network. `~/.tutor-resume.log` has whatever it
said; `export TUTOR_BOARD_NO_RESUME=1` turns it off for one shell.

Nothing on a node outlives the job that gave it to you. That is why the allocation is the thing
that renews itself.

### The allocation renews itself, and the board repairs itself

```
tutor serve                  start the chain: one job, nine hours, and a successor already queued
tutor serve status           which generation is up, where, and what it has repaired
tutor serve stop             end it -- the flag, then the cancel
tutor watch                  the repair loop by itself, worth running inside an `salloc`
tutor down [workspace]       stop serving here: the boards, the tutors, and the link

bash board/scripts/serve.sh  the same, with nothing on the PATH and from any directory
```

`scripts/serve.sh` is there for one moment: **after `scancel -u $USER`**, which is the thing that
really ends a chain, because it takes the running generation and the queued successor together. It
needs no install and takes the same words (`status`, `stop`, `restart`).

**A generation queues its own successor before it does anything else**, with
`--dependency=afterany:<itself>`, so the queue is always holding the next machine. `afterany` and
not `afterok`, because a generation that crashed is when the next one is most needed. Then it
catches the tool up, re-execs onto it, runs `tutor resume`, and watches — and five minutes before
its walltime Slurm signals it (`--signal=B:USR1@300`), which is the daemons' cue to write their
handoffs while there is still a machine to write them on. `slurm/tutor-serve.sbatch` is twenty
lines of finding the checkout and handing the batch shell to `tutor serve inside`; every decision
is in `bin/tutor` and `tutorboard/supervise.py`, where it can be tested without a cluster.

**Ending it takes a flag as well as a cancel, and that is not belt-and-braces.** Cancelling the
running generation is *precisely* what its successor's dependency is waiting for, so a chain
cancelled one job at a time comes straight back — which is the chain working as designed at the
worst possible moment. `tutor serve stop` writes `serve-stopped` in the state directory first and
then cancels the whole job name at once. `scancel -u $USER` also ends it, because that takes the
queued successor with it.

**`c3_short`, nine hours, and both halves are measurements.** The seven-day partitions are the
ones a chain would rather have and neither can serve a board:

- **`c3_accel` has no route to Tailscale's control plane.** From inside a job on compute306:
  github 200, `api.anthropic.com` 405, `controlplane.tailscale.com` reset at the first read, every
  time — while the same request from compute301 answers 200. A tutor can teach from there; the
  iPad cannot reach it, and the iPad is the point.
- **`c3` is suspended by `c3_short`**, which outranks it (priority tier 20 against 10) with
  `PreemptMode=SUSPEND` under a GANG scheduler. A seven-day board there is SIGSTOPped and
  time-sliced by the first busy afternoon: alive, holding its port, answering nothing, on a node
  whose watch loop is frozen in the same cgroup. It is the one failure nothing in here can see.

`c3_short` is the top tier, so nothing preempts it, and its nine-hour ceiling is what the chain
exists to make irrelevant — a handover costs the seconds the scheduler takes, about three times a
day. All four are config keys: `serve_partition`, `serve_time`, `serve_cpus`, `serve_mem`.

**The watch loop is what makes a death cost twenty seconds instead of an evening.** It revives a
board whose pid is gone, stops and restarts one that is alive and has failed `/health` twice —
wedged, which nothing could see before — and puts back a tutor daemon that died. What it refuses
to do is the load-bearing half:

- nothing without a record. `board stop` and `tutor headless --stop` remove theirs, and that is a
  person saying no;
- nothing on another node, **unless it is the serving generation doing the asking** — see the home
  node below;
- nothing a restart is already doing — `tutor restart --tutors` writes `restarting` first, exactly
  so a bounce can be told from a death;
- nothing off a record that has gone stale. `live/agent.json` is never swept, so one saying
  `listening` on a node that died two days ago reads just like one from a node that died a minute
  ago; an hour is the window.

**The serving node is home, and every other machine leaves the board alone.** This was built the
polite way first — a board on any node still allocated to you was left where it was, so an
`salloc` with somebody mid-proof on it was never robbed. What that bought was a lesson on a
machine no watch loop was allowed to touch: the board died on the `salloc` node while the only
watchdog was on the serving node under orders to keep its hands off, and the iPad went white with
a healthy chain running. So:

- a generation **asks every other node of yours to stop serving before it starts anything** —
  `tutor down`, which stops that machine's boards and tutors, waits for each handoff turn, and
  **lets go of the tailnet link**. The link is machine-wide: `board vpn up` refuses while the claim
  in the shared state directory names a node you still hold, so a board started before the ask
  comes up with no address and nothing goes back to check. That ordering is asserted in the suite.
- it gets there by **ssh, then by a Slurm step** in the allocation that holds the node — ssh
  between these compute nodes is refused for want of a key (measured), and a step needs no
  credential. The errand is to *stop* things, so nothing has to outlive the step.
- reachable by neither route, **it starts nothing**: one board on the wrong machine beats two
  boards writing one `live/` directory, both answering the same inbox line.
- `tutor resume` on any other node **starts nothing while a generation is running** — otherwise
  every new terminal on your `salloc` drags the lesson back and the two nodes take turns owning
  the one address the iPad has. `--force` is still a person insisting.

An `salloc` is therefore for coach coding and holds no lesson.

**A handover is not a stop, and it is one field.** The walltime's own stop leaves the same record a
person's `tutor agent stop` leaves, so `hand_over` writes `handover` into it first and the next
generation picks up only those — on whichever node it lands, including the same one, which on a
single-node partition is the common case.

**Only the asker may say why a daemon was stopped, and the daemon's own exit says nothing about
it.** `restarting` and `handover` are both written *before* the signal, by whoever is asking, for
the same reason: a daemon receiving a SIGTERM cannot tell a bounce from a person leaving, so its
exit record merges `state: stopped` over the top and touches neither field. What clears
`restarting` is `mark_waking`, written by both halves of a start — so the flag lives exactly as
long as the restart it describes is unfinished. Without it an abandoned bounce is
indistinguishable from *a person said no*, which the watch loop obeys for ever — while still
reviving that course's **board** every generation, which is a page that serves perfectly with
nothing reading it.

**And the exit write only lands where this process is still the one on the record.** `agent_state`
merges, which is what makes one file safe for several writers adding a field — and is not safe for
the last write a daemon makes. A bounce hands the workspace over, the successor records its own pid,
and the process that was replaced then stamps `stopped` on the record of the one that replaced it;
the watch loop reads `stopped` as *a person said no* and never revives it, so the cost is a board
serving perfectly with nothing reading it until somebody notices by hand. The exit write asks
whether `agent.json` still names this pid, and writes nothing where it does not — the successor's
own `listening` is the truth. The test is deliberately generous: an unreadable record, and a record
whose pid a start has not filled in yet, are both this process's to write.

**A start clears the clocks the daemon before it left behind.** For the same merging reason,
`stopped_at`, `turn_started` and `turn_signal` from a process that is gone otherwise sit in the same
record as this one's `started` and are read as though they were this one's — the board draws how
long a turn has been running off `turn_started`, so a record carrying 17:40 beside a daemon that
came up at 20:16 draws a turn two and a half hours old. A start is the one moment that has earned
the right to clear them, because it is the one moment they are certainly about somebody else.

**And a restart finishes the restart it started.** A handoff turn is a model call and routinely
outruns the ninety seconds the foreground gives it — 97 seconds, measured — so `tutor restart
--tutors` has a branch that gives up. That branch now spawns `tutor finish-restart`, detached,
which waits for the wrap-up turn to actually end and starts the replacement then. **The watch loop
is the backstop and not the plan**: it only exists where one is running, so a hand restart in an
`salloc` used to leave the tutor down with the flag on and no clock anywhere, and where it does run
the person holding the iPad still watched a lesson say *claude is restarting* until
`REATTACH_GRACE` was out. Both may now decide to start the same tutor, and that is not a race —
`agent_start` refuses when one is already there, which is the single property holding it up.
`test/waking.py` holds every half of this.

The chain cannot watch itself all the way down: a generation that fell over in its first second
never reached the line that queues its successor. So the loop re-checks its successor every five
minutes, and `tutor resume` repairs the chain on any login — but only where one was started and
not stopped.

## Starting a session

```
tutor
```

That is the whole entry point. It lists the courses it finds, you pick one, and it brings that
course's board up, opens a session, and launches your assistant already pointed at the repository's
contract — with the board running before the assistant exists.

```
tutor galois                 match a course by name
tutor galois --homework      and open a homework sitting
tutor trd --agent opencode   with a particular assistant
tutor galois --no-agent      just bring the board up
tutor --list                 what courses exist
tutor --agents               what assistants are configured
```

It replaces: remember which directory, `cd` there, start an agent, then tell the agent to start the
board. That last step is ceremony nobody should have to perform, and forgetting it produces a
session where the assistant talks into a terminal no one is reading.

### Headless — no terminal at all

```
tutor headless galois --agent opencode
tutor headless --stop
```

The assistant runs as a daemon. `board wait` blocks until you send something from the board, hands
it over, the assistant writes a card, and it goes back to waiting. You are on the sofa with an
iPad; nobody is at a keyboard at any point.

Each agent needs a `headless` recipe in the config — a command that takes a prompt, does the work,
and exits:

```json
"opencode": { "headless": ["opencode", "run", "--continue", "{prompt}"] },
"claude":   { "headless": ["claude", "-p", "{prompt}", "--continue"] }
```

`{prompt}` is substituted. Continuity across turns is the agent's own business; the flag that
resumes its session belongs in the recipe. Output goes to `live/agent.log`.

**It lives as long as the machine does.** On a cluster node your processes live and die with your
allocation, so the daemon goes when the job ends — which is the same ceiling everything else here
has, and the reason a session's continuity is written to a file and pushed rather than held in a
process.

### What a session costs, and why that is a design question

**A turn is charged for its round trips multiplied by the conversation behind
each of them.** That sentence is the whole of it, and everything below follows.
The lesson is already on disk, so nothing has to be carried in a conversation to
survive — and carrying it anyway is the most expensive thing this tool can do.

The unit that matters is **tokens through the model** — input, output, and cache
both written and read — because on a subscription what runs out is a five-hour
allowance and that is what it is computed from. Dollars are given below as well,
for a machine on a metered key, but they are the second column.

It was carrying the conversation. Measured in Galois Theory on 8 September 2026 —
eleven cards on `claude-opus-5[1m]`, one session resumed throughout, read out of
the agent's own transcript:

| turn | context held | round trips | tokens | cost |
|---|---|---|---|---|
| 1 (cold) | 74k | 18 | 1.14M | $2.24 |
| 3 | 96k | 8 | 0.76M | $1.36 |
| 8 | 152k | 36 | **5.22M** | $4.49 |
| 11 | 176k | 8 | 1.39M | $2.43 |
| **session, 11 cards** | | **150** | **17.9M** | **$25.40** |

The context column is the story. It is *not* the cache expiring: a resumed turn
re-caches only its increment, measured at 40 tokens on a 43k conversation. It is
that turn eleven paid, on each of its eight round trips, to read back ten turns
of history it would never look at again. 1.6M tokens a card, rising, for a lesson
that fits on two sides of paper.

**Measured after the change, on a copy of that same course:** a turn takes
**225k tokens over 6 round trips**, and 443k on the very first turn in a
directory whose harness prefix is not yet cached. That is **one seventh** of what
a turn was taking, and it does not climb — so a response that took 5% of a
five-hour window takes something near 0.7% of one now.

**So a turn is its own session.** `session_turns` is 1. Every turn starts cold,
reads what it needs back off disk in two calls, teaches, writes down what the
next turn needs to know, and dies. Nothing accumulates, so nothing grows.

- **Two calls, and they are the whole cold read.** `board brief` is the standing
  rules — the method as a paragraph, this course's own *rules that do not bend*,
  the chapter's handoff, and the note the last turn left. `board recap` is the
  lesson — every card as a line, the newest in full, the student's turns, which
  question is open. Together about 4.5k tokens. They replaced
  `AI_INSTRUCTIONS.md` (9.1k), `live/TEACHING.md` (9.5k) and `HANDOFF.md` (5.4k)
  read in three round trips, and the full documents are still on disk with their
  sections named for the rare rule that needs its detail.
- **The harness prefix is free.** A second `claude -p` in the same directory
  reads its 28k-token system prompt out of cache for $0.015, because the cache is
  keyed on the prefix and not on the session. Measured. This is why a fresh
  session per turn is cheap and why it was not obvious that it would be.
- **`live/NEXT.md` is what replaced the conversation.** A recap says what was
  asked and what came back. It cannot say that the student is reading a ∃ as a ∀,
  that this is the third attempt at the same line, or that the ladder is aimed at
  the witness rather than the algebra. Every turn writes that with `board note`,
  capped at 120 words, and the next turn reads it out of the brief.
- **A turn does not wait, and `board wait` now refuses it.** Turn 8 above is what
  that cost. The course contract documents `board wait` as the way to be woken —
  true, and correct for a person at a terminal — so a headless tutor reading the
  contract ran it at the end of its own turn, held the whole conversation open
  while the student thought, and answered their next message inside it. Two cards
  in one turn, 36 round trips, $4.49. No wording could fix it, so
  `board wait` asks `live/agent.json` whether a headless turn is in flight and
  says no; the daemon's own waiter passes `--force`, because it is the one caller
  that is not that turn.
- **The handoff is capped by a door, not by a request.** The prompt has said
  "under 350 words" since the day this could bill by the token. The file was
  3,824 words. Nothing had gone visibly wrong: `live/TEACHING.md` listed
  "updating `HANDOFF.md`" among the things a turn involves, every turn duly read
  it, edited it and handed the next turn a longer one, and each edit was
  reasonable on its own. Now `board handoff` is the only thing that writes it, it
  refuses a body over the cap rather than trimming one — the useful half of a
  handoff is at the bottom — and a teaching turn is told not to touch it at all.
- **The recap's own card list is bounded.** It was the last thing that grew with
  the lesson: a hundred and seven cards is 6.4k of titles, read at the start of
  every turn. It now names the last forty and counts the rest, which is what a
  turn reasons about — the older end of a chapter is what `HANDOFF.md` is for —
  and `board recap --all` still prints the lot.
- **Sessions are still recyclable.** `session_turns: 0` resumes for ever, which
  is right on a flat rate and wrong on a meter; any N recycles after N turns,
  which is what this was.

**What is left, and why it is left.** Two things were measured and deliberately
not changed.

*Output is the one lever left, and it is the expensive kind of token.* 3.2k
output on the measured turn — small against 225k total, but on a metered key it
is $0.08 of a $0.39 turn, and a card is a few hundred words, so most of it is
thinking and tool arguments. `--effort medium` cuts it, and the recipe has an
`extra_args` field to put it in. It is empty, because that is a teaching decision
and not a cost decision, and this repository does not get to make it on the
student's behalf.

*The slate PNGs are fine.* Handwriting arrives at most 1415×762, about 1.2k image
tokens, and downscaling handwriting to save a fraction of that is how a tutor
comes to misread a proof. Measured, and left alone.

*And one thing that had not gone wrong yet.* The model is `opus[1m]`, from the
machine's own Claude Code settings, and the largest single request across every
Galois session measured **189,588 tokens** — five per cent short of the 200k
line above which a long context is charged and weighted differently. Twelve
cards was under it; fourteen would not have been. A turn now holds 22k to 44k,
so the 1M window buys nothing and the line is nowhere near. If you want the
standard variant anyway, `extra_args: ["--model", "opus"]` on the recipe pins it
for the tutor without touching what you use at a terminal.

None of this is allowed to cost teaching quality, and the rule cuts both ways: a
change to how the tutor teaches is also a change to what it costs, so a new rule
in `TEACHING.md` is weighed the same way. `test/tokens.py` holds all of it.

### What it actually cost, which is not a matter of opinion

Every claim above is a measurement, and the measuring is now part of the tool
rather than something somebody did once by hand in a session transcript.

`--output-format json` on the recipe makes the agent report what its turn cost.
Every headless turn appends one line to `live/cost.jsonl`, writes a summary line
into `agent.log`, and `tutor cost` adds it up:

```
tutor cost                # the course an assistant is attached to
tutor cost galois --turns # every turn, oldest first
tutor cost --all          # every course on this machine
```

```
when                 turn session  trips     tokens  cacheread cachewrit      out     cost
2026-09-08 11:34:11     1 fresh       10     442.6k     392.5k      43.0k     7.0k    0.804
2026-09-08 11:38:02     2 fresh        6     225.5k     201.1k      21.2k     3.2k    0.394

Galois-Theory — 2 turn(s) on compute301, 2 of them their own session
  334.0k tokens a turn  (1.19% of a window), 8.0 round trips a turn
  668.1k tokens in total  (2.39% of a window), $1.20
  dearest turn: 442.6k tokens  (1.58% of a window) over 10 round trips
  first half 442.6k a turn, second half 225.5k -- flat, which is the point
```

That last line is the one to read. A rising second half means a turn is carrying
something it should have read back off disk, which is the defect this whole
arrangement exists to prevent — and it is the defect that is invisible in every
other form of monitoring, because nothing is broken while it happens.

**The percentage is a calibration, not a published figure.** Nothing says how
many tokens a five-hour window holds, or how a cache read is weighted against an
output token. `quota_tokens` in the config is what to divide by, and it is null
until somebody sets it: calibrate it from one observation — a turn seen taking 5%
of the window, measured at 1.39M tokens, puts the window near 28M. It will be
approximate. It is still worth having, because the thing worth watching is
whether the figure is *flat* across a lesson, and a constant factor does not
affect that.

Two columns matter more than either number. **Round trips** is what a prompt can
change, and the only thing that turned a turn into 5.22M tokens. **Cache read** is
round trips times context: it is what grew without bound while a session was
resumed for twelve turns, and it is what a turn being its own session holds flat.

**And the reading is a dispatch, not one provider.** `usage` on a recipe names a
parser — `claude-json`, `codex-jsonl` — so a provider is a parser added beside
the others, and `tutor cost` splits the evening by agent, because the reason to
have three is to see which one it went on.

**The dollars are computed from the recipe where it has a price table.** A
provider driven through somebody else's binary reports its token counts
correctly — they are the model's own — and the price wrong, because the prices
compiled into that binary are its vendor's. So the counts come from the parser
and the money from a `prices` block: input, cached input, cache write and output
per million, with the provider's own peak window in UTC. **What is recorded is
the rate that applied**, not the window it was derived from: a table of windows
in the reader goes stale silently and a recorded rate cannot. A recipe with no
price table records its tokens and *no* dollar figure, which is the honest answer
rather than a wrong number.

The flag is appended from the recipe's `usage_args` rather than written into its
`headless` command, and that is not fussiness. A machine's config file overrides
`agents` one level deep, and at least one machine here holds a verbatim copy of
the claude recipe from an older version of this tool. Had the flag gone in the
argv, every machine carrying such a copy would have silently stopped reporting —
which is the one failure a measurement must not have.

### Knowing what is actually up

A daemon you cannot see is worse than no daemon, so nothing has to be assumed:

```
tutor where
```

```
this machine: compute301

  Galois Theory            board:up :8787   agent:opencode listening
  Probability              board:-          agent:-
  TRD-EHR                  board:on compute302  agent:claude listening on compute302

  reachable at https://board.<tailnet>.ts.net/
```

On the board itself, a dot beside the course name says whether an assistant is attached: green and
*attached* or *listening*, amber and pulsing while it is *working*, red when it has gone.

**How that expires depends on which kind it is, and getting this wrong is why the indicator was
dark in every ordinary session for a while.** A headless daemon writes a heartbeat as it works, so
two minutes of silence means it died. An interactive assistant is idle for exactly as long as the
person in front of it is thinking, and a heartbeat there would call a perfectly healthy session
dead the moment somebody went to make tea — so it is judged by whether its process is still
running. `tutor` records the pid before handing the terminal over, which is the same pid the
assistant then has.

**A tutor on another of your nodes is named, not called stale.** The board and the tutor can end
up on different machines — see *Arriving on a new node* — and asking whether that pid is alive
*here* said `stale` about a daemon listening perfectly well over there, on the very machine you
type the question on. Across a shared filesystem the heartbeat is what can be checked, and it is
checked the same way the repair checks it: a quarter of an hour of silence, and only then stale.

Either way the host is compared first, and a recycled pid running something else does not count:
the home directory is shared across compute nodes, so a record from an ended allocation is very
likely alive here and belonging to a stranger.

Liveness is checked against the process, not just the pid — a record on a shared filesystem may
have been written by another machine, and a pid on its own can be a stranger's.

### Two machines, and which one owns the address

The tailnet identity is one machine that moves, so `board.<tailnet>.ts.net` points at whichever
host currently holds it, and `board vpn up` refuses to start a second daemon against the same
state. That is the right behaviour for one machine at a time.

If you want two machines live at once, give them separate identities — a different `--hostname`,
and `BOARD_STATE_DIR` set to a path of its own on the second so the two are not sharing one
tailnet state directory — and install the board on the iPad from each address. Two
apps, two icons, no ambiguity about which is which. An address only ever opens a board on the
machine that holds it: `tailscale serve` will not proxy to a remote backend, and answers every
request with a 502 if you ask it to.

### Which assistant runs is configuration

`~/.config/tutor-board/config.json`, written on first run:

```json
{
  "courses_dir": "/home/you/Atlas",
  "default_agent": "claude",
  "agents": {
    "claude":   { "cmd": ["claude"],   "prompt": "argv",
                  "headless_first": ["claude", "-p", "{prompt}"],
                  "headless":       ["claude", "-p", "{prompt}", "--continue"] },
    "opencode": { "cmd": ["opencode"], "prompt": "argv" },
    "aider":    { "cmd": ["aider"],    "prompt": "none" }
  }
}
```

`cmd` is whatever launches it. `prompt: "argv"` appends the opening brief as a final argument;
`prompt: "none"` launches it bare and prints the one line to paste. Add an entry for anything that
runs in a terminal — nothing in the launcher knows which assistant it is starting.

#### A provider is a recipe plus a key, and that is the whole of it

Two more fields carry a hosted provider, and after them **a new one is one entry in `agents` and one
line in a key file**, with a newer model one string inside that entry.

| Field | What it is |
|---|---|
| `needs_key` | the name of the one key this recipe cannot run without |
| `env` | environment variables merged over the turn's own, with `{NAME}` filled from the key store |

**Keys live in `~/.config/tutor-board/keys.env`**, `NAME=value` a line, `#` for a comment, beside
the `config.json` the launcher already reads and never in this repository — which is public. A
world-readable file is refused and its keys read as absent; a group-readable one is not, because
this home is NFSv4 and the server forces `770` on every file in it, `~/.claude/.credentials.json`
included. The root `.gitignore` refuses the shapes a key file gets given, and `test/tracked.py` puts
the same question to git itself on every run of the suite, which is the guard that survives somebody
editing the ignore file.

**`env` never reaches argv.** `usage_args` and `extra_args` are appended to the command because
flags are public; a key on a command line is in `ps` output for anything on the machine to read.

A recipe whose key is absent is `unkeyed` — the same word the browser already understands for an
executable that is not installed. It is drawn dimmed on both choosers with the key and the file in
its title, the daemon refuses to start on it, and an automatic swap never falls into it. A button
drawn, tapped, and dying in a log file hands the person holding the iPad the one thing they cannot
act on.

`deepseek` is the worked example and it is cheap for one reason: DeepSeek serves an Anthropic-format
`/messages` endpoint, so the agent that runs it is **the `claude` executable already installed
here**, with eight environment variables. Every part of this tool that knows how to drive Claude
Code drives it unchanged — the resume, the `--output-format json` accounting, the timeouts, and the
`ai-config` pre-tool hook, which fences PHI by intercepting the binary's tool calls and therefore
fences this provider too, for free.

**Every slot the binary can choose a model from is pinned, and that is the one decision in the
entry.** Unpinned, the endpoint maps by name: an id starting `claude-opus` lands on the older
text-only model, which **substitutes a placeholder for an image block rather than failing** — so a
tutor handed a slate PNG answers confidently about nothing and no exit code says so. Six slots name
`deepseek-flash`, which takes image input natively and is the cheaper of the two anyway:
`ANTHROPIC_MODEL`, the three `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` aliases the binary
resolves a named tier through, `CLAUDE_CODE_SUBAGENT_MODEL` for a Task-tool subagent, and
`ANTHROPIC_SMALL_FAST_MODEL` for its own cheap calls. Six rather than two because any one left unset
is a route back onto the text-only model, and that route loses handwriting silently.

**And the placeholder is caught on the way back, because pinning cannot be the only guard.** A tutor
whose model can see is told to open the slate PNG itself, so the image never passes through `board
see` and never meets `blind_answer` there. The turn's own output is scanned for the same
placeholders instead, and a turn carrying one fails with *the page never reached the model* rather
than landing a fluent card about a page nobody read. `board/test/seeing.py`.

**`claude` is the default**, and it is the only one this has been taught with at length. Claude
Code arrives with the course repository already in front of it, which is most of a tutor: it reads
the slate PNG itself rather than through a transcription model, writes the card, and edits the
course's own `.tex` when a homework sitting needs it.

#### What a headless tutor is allowed to do, and where that is written

Headless there is nobody at a terminal, so nothing can be approved while a turn runs — and **a
refused tool is not an error.** The agent apologises into a log nobody opens and exits 0, so a
turn can read the assignment, compose the whole opening card, and end having written nothing.

That is settled in exactly one place and it is outside this repository:
`ai-config/workspaces/tutors.allow`, which names no vendor, listing what a daemon has to be able
to run — the board's own command, the two PDF readers, and the LaTeX toolchain that turns a
written-up sheet into something readable on an iPad. `bash ai-config/scripts/install.sh` folds it
into whichever assistants are installed. **This tool writes no assistant's config file**, which is
why no workspace here carries one; `test/agents.py` asserts that absence, because nothing fails
loudly when a writer creeps back in — it just starts leaving directories behind again.

It deliberately does **not** also appear as a flag on the agent's command. One policy written in two
places is one policy that drifts the first time either moves, and of the two the committed file is
the half anybody can actually see. `test/agents.py` holds both halves of that.

### Which one, for this course, on this machine

A laptop and a cluster node do not have the same tools installed, and a course may want a
particular assistant regardless of where it runs. Five layers settle it, most specific first:

| Layer | Where it is written | Scope |
|---|---|---|
| `--agent opencode` | the command line | this once |
| `"agent": "opencode"` | the sitting's own `live/state.json` | this evening's work — the only layer the iPad can reach |
| `"agent": "opencode"` | the course's `tutorboard.json` | this course, on every machine |
| `"hosts": { "desk": "deepseek" }` | the config, by short hostname | this machine, every course |
| `"default_agent"` | the config | everything else |

```json
{
  "default_agent": "claude",
  "hosts": { "desk": "deepseek", "compute301": "claude" },
  "agents": {
    "claude":   { "cmd": ["claude"], "prompt": "argv",
                  "headless": ["claude", "-p", "{prompt}", "--continue"] },
    "deepseek": { "cmd": ["opencode", "--model", "…"], "prompt": "argv",
                  "headless": ["opencode", "run", "--continue", "{prompt}"] }
  }
}
```

**A model is not a layer, and must never become one.** An agent entry is a command recipe, so a
second model is a second entry whose `cmd` carries the flag — which is why "opencode with DeepSeek"
and "opencode with something else" are two names in this file and nothing in the code changes.

**The answer is asked again at the top of every turn**, not once as the sitting opens, so a tap on
the front door lands on the next card rather than the next evening. That is cheap because
`session_turns` is 1: a hosted turn holds no conversation worth protecting and reconstructs the
evening from `board brief` and `board recap`, off disk, whoever takes it. Three things do not move —
a session genuinely carrying turns, a `[carry]` resuming a conversation by id, and anything into or
out of a `private` recipe.

**And an allowance that runs out is a climb down rather than a stop**, because a limit belongs to an
agent rather than to the machine — see [when the allowance runs out](#when-the-allowance-runs-out).

**The front door sets `default_agent`.** A row beside the line that already says which machine this
is, offering every recipe it can run, writing that one field and nothing else in the config. The
fenced reader is never offered there: a machine default is a decision about every workspace,
including the ones whose `live/` is pushed to a public remote.

### The assistant belongs to the course, not to the terminal

Each course keeps its own assistant, in its own repository, reading that repository's own
`AI_INSTRUCTIONS.md` and resolved by the table above. Switching course on the hub brings the new
course's board up and starts an assistant there if one is not already listening; it leaves the
others alone.

**They are not exclusive**, and making them so would buy nothing: a listening daemon is blocked on
`board wait` and spends nothing while nobody is asking it anything. Stopping one costs real work on
the way back — returning to that course means a cold assistant re-reading the contract, the method
and the lesson before it can write a word. They write their handoff when they are actually stopped,
which is what a stop is for.

```
tutor agent status           which courses have one attached
tutor agent start galois     attach one there, leaving the others listening
tutor agent ensure galois    the same, silent when one is already listening
tutor agent stop galois      ask it to write its handoff and go
tutor agent which galois     print which assistant that workspace runs by default
```

`ensure` is what another machine asks over ssh on every login — see *Arriving on a new node* —
so it says nothing when there was nothing to do. A line per shell for a tutor that is perfectly
well is noise in the one log a real failure has to be findable in.

Nothing about this asks the student to operate anything. They open a course; the assistant is
there.

### Nothing ends tidily, so every session ends in writing

A session does not finish with a goodbye. A course is switched, a lid closes, an allocation
expires. So the last thing a departing assistant does — before its process goes — is one turn with
no student attached, writing **`HANDOFF.md`** at the root of the course: where the student got to,
what they got wrong and what the misunderstanding actually was, what not to re-teach, and the one
next thing to cover. If the course's README or contract drifted during the session, it fixes those
too.

**It writes it with `board handoff`, which is the only thing that writes it, and which refuses a
body over 350 words** — a cap written as a sentence in a prompt is not a cap: every teaching turn
reads the file and edits it, each edit is reasonable on its own, and it reaches 3,824 words.
A teaching turn leaves **`board note`** instead: at most 120 words in `live/NEXT.md`, read by the
next turn out of `board brief`. The note is what one turn tells the next; the handoff is what one
session tells the next, and it is the only one of the two that crosses a machine.

The brief tells every starting assistant to read that file first. It is committed with the rest of
the work, so it survives the machine, and it is the only continuity there is — an assistant's own
conversation history does not cross a node, a vendor, or a week.

`SIGTERM` is what starts the wrap-up, deliberately: the whole point is that it happens, so nothing
kills the daemon outright. It takes as long as one turn takes, and nobody waits for it.

### It does not matter where you run `tutor` from

Courses are found by name under `courses_dir`, and the launcher changes into the course directory
itself before doing anything. `tutor galois` from your home directory, from inside another course,
or from `/tmp` all do the same thing. The only command that cares where it is run is `board`, which
acts on the repository it is standing in — and the launcher never makes you run that.

### Every session starts by catching up

Before the board comes up and before an assistant is launched, the launcher runs a
fast-forward-only `git pull` in the course. A handoff written on the machine you left is worth
nothing to the one you arrive on until it is fetched, and the whole point of writing it down is that
the work moves between machines.

It is deliberately never fatal. No remote, no network, or a branch that has diverged: it says so in
one line and the session starts anyway on what is on disk. Somebody holding an iPad cannot resolve
a merge, and a session that refuses to start is worse than a session that starts a commit behind.

**And the board pulls itself, on the same beat.** The course was only ever half of it: `tutor` and
`tutor resume` also fast-forward *this* repository, under the same never-fatal rule. No timer can do
it on a compute node, because a schedule on a machine that ceases to exist is not a plan — so a fix
sat on GitHub until somebody remembered to `git pull` by hand. Remembering by hand is the thing this
repository keeps failing at, and a login is the only moment a node gets.

Two things follow from the pull, and neither is optional:

- **The launcher re-execs itself** when the pull moves `HEAD`. `bin/tutor` was read into memory
  when the process started, exactly the way a board reads `serve.py`, so carrying on inside the
  launcher that was there before the pull is the same defect one level further in — and the hardest
  version of it to see, because the code reporting what it did would be the code that was replaced.
- **Then it bounces what is still holding the old code**, which is `tutor restart --tutors`: the
  boards answering on this machine and the tutors that are not mid-turn.
  This is `scripts/ship.sh` seen from the other end. Shipping bounces the machine a
  change is *written* on; without the same act on the machine that *receives* it, the fix is on
  disk and nowhere else, and the pages look new while the endpoints behind them are the old ones.

Only the two commands that begin a session do this. `tutor restart` does not, because `ship.sh`
calls it seconds after its own push and a second fetch there is a network round trip that finds
nothing.

### One address, and the machine holding it

**The goal.** Open the app on the iPad, pick a course, get a session. No command anywhere, ever.
Nothing about how that is arranged is visible to the person holding the iPad.

**The one address is the machine's, and it opens one board at a time.** `tailscale serve` proxies
the tailnet HTTPS name to a port on the machine it is running on; handed a remote tailnet address it
answers every request with a 502, so there is no arrangement in which one origin serves two
machines. Which board it opens is therefore a decision this machine makes, and it makes it twice:

- **a tap in the hub takes the name for the course it opens.** `/switch` records the choice, starts
  the board, and re-points the name in the same request — a tap is a person saying which lesson they
  mean, and nothing else is going to move an address on their behalf. The hub then waits until the
  address really is serving that course before it reloads, because reloading sooner lands on the
  board being tapped away from, which is indistinguishable from a tap that did nothing.
- **a start does not take it.** `ts_repoint` leaves a name alone while it points at a board that is
  up and answering, because `tutor restart` walks every course on the machine one after another and
  would otherwise leave the address wherever the alphabet finished — which once dropped somebody
  halfway through a Galois proof into a different lesson. What takes a name is a tap, an explicit
  `board vpn serve`, the name pointing at nothing, or the watch loop putting it back on the course
  `chosen.json` names.
- **and ANSWERING IS NOT OWNING.** A port holds the address when a live record names it —
  `recorded_ports()`, every `live/.board.json` on this node whose pid is still serving its own
  repository. A board an ended generation left behind answers exactly like a live one and is named
  by no record at all, because the board that replaced it overwrote the one record its repository
  has. On the answering test alone that leftover outranked every board that came after it, for as
  long as its process survived: the tutor was up, the board was up, the serving chain was three
  generations deep and reporting itself healthy, and the card the tutor had written sat on a board
  nothing was pointing at. **A leftover has no claim on anything**, and a new board for the same
  repository stops it — `drop_strays`, before `Popen`, this repository's own and on this node only,
  because the moment a repository's next board starts is the moment the previous one became a
  leftover. `test/serving.py` holds both halves.

**Two names, and they are not the same name.** The *tailnet* name is the service — the one origin
the iPad app is installed against. The *machine* name is who wrote a record — `compute301`.
Conflating them is how this went wrong once: Tailscale's DNS made `uname -n` answer the service
name, the machine stopped recognising boards it had written under its own, and a live board became
unrestartable while still answering perfectly.

- **`board node`** — what this machine calls itself, and whether that is pinned. `board start` pins
  it the first time, before anything writes a record carrying it, on a machine whose name comes from
  the network and must not. `board node <name>` corrects a wrong one.
- **Do not pin the machine's name on a cluster node.** There the name is *supposed* to change
  between allocations, because it is a different machine each time and every ownership check depends
  on that being true: pin `compute301` and the next allocation calls itself `compute301` while Slurm
  says you hold `compute309`, so `tutor resume` refuses to start a board on a machine it thinks is
  not yours. `board start` will not pin where Slurm answers, and `board node --unpin` undoes one set
  by mistake.
- **`board vpn up --hostname <name>`** sets the tailnet name, once. It moves the one origin the app
  is installed against, so nothing does it for you.

> **If you are a tutor putting a compute node right, there is one command:**
>
> ```
> bash scripts/setup-node.sh [--tailnet-name <node-name>]
> ```
>
> It pulls, checks the machine's name is not pinned, picks the tutor this machine can actually run,
> and restarts the boards and tutors so they are on the code it just pulled. Every step is idempotent and reports what it found, so running it again
> when you are unsure costs nothing.
>
> The one thing it will not do for you is `board vpn up --hostname <node-name>`, for the reason
> above; it tells you when it is needed.

#### When the allowance runs out

The failure this handles is not a fault. Everything works and there is simply nothing left to spend:
the agent says so, exits non-zero, and every turn after it does the same until a clock somewhere
rolls over. Treated as an ordinary broken turn it is invisible in the worst way — the board shows a
tutor listening, the student sends again, and nothing comes back for four hours.

There are two moves, and they are taken in order.

**1. Notice, and say so somewhere it can be read.** A turn that has already failed has
its output read back for the phrases a provider uses. Only a *failed* turn — reading every
successful one for the words "rate limit" finds them in the lesson, because a course on queueing
theory says them in earnest. What a limit looks like is `usage_limit_says` in the config, a list of
patterns, for the same reason `egress_probe` is a list of URLs: the board is not allowed to know
which assistant is driving it, so the provider is named in one default value and nowhere else.

**A per-session allowance and an account-level ceiling do not say the same thing**, and the second
one cost a teaching evening to learn. Claude Code answers a spent org budget with *you've hit your
org's monthly spend limit … your session limit resets 8:20pm*: it says neither *usage limit
reached* nor *limit reached … resets*, the word between *limit* and *resets* is *session*, and the
first limit in the sentence is a **spend** limit — so every pattern missed it, nothing was recorded,
and the daemon went on handing turns to a provider that could not spend a token. `spend limit` and
`limit resets` are both in the list, and **neither captures, deliberately**: that reset is a
wall-clock time in a named zone rather than the epoch second the first pattern reads, and a group
around `8:20` would be believed to be an epoch, fail the window test and fall back anyway — by a
longer route, through an arithmetic that looks like it worked. No group means the default window
answers directly, which is the same result said honestly.

The record is per **agent on a machine**: an allowance belongs to an account, so one provider running
out says nothing about another, and marking the whole machine would take the fallback out along with
the thing it is falling back from. It carries an expiry rather than a flag. Claude Code names the
epoch second the limit lifts and that is believed over any window we could guess; without one it is
an hour. A limit that has to be cleared by hand is a limit that outlives itself and quietly demotes a
machine for days.

`/health` publishes it, for exactly the reason `/health` publishes the chosen course: only the
machine that hit the limit can know about it. A board too old to publish the field is not assumed to
be exhausted — silence is an allowance.

**2. Then climb down.** The tutor pushes the transcript first — the message it has just failed to
answer is in there, and the beat that would have carried it is the beat there is no time for — and
the next turn goes to the next recipe that is installed, keyed, not itself limited, and not
`private`. The order is a `fallback` list in the config, defaulting to what `--agents` reports in the
order it reports it. **The lesson loses nothing**, because a turn is already cold and reads the
evening back off disk; there is no conversation to transfer, which is precisely what makes this
automatic.

**3. And where there is nobody to climb down to, stop and say so.** A board that says *the allowance
is gone until 4pm* is worth more than one that answers the question badly with something else.

**And the record says the daemon is retrying, because it is.** The strip reads that field exactly:
without it the board says *send again to carry on*, and a student who obeys queues a second copy of
their work behind a turn this loop was about to take itself. Both climb-downs — the allowance and
the dark host — re-queue the message and set it.

Coming back up is those steps in reverse and nobody types anything. The limit expires, or a turn goes
through on that agent and proves its allowance is back before the clock said it would; the tutor
climbs home at the top of its next turn, because the question is asked again every turn rather than
answered once, and `/health` stops saying it is exhausted.

```
board limit              has the allowance here run out, and until when
board limit --clear      it came back early; stop waiting out the guess
```

`board doctor` names it too.

**The handoff turn re-asks who writes it, rather than inheriting whoever just failed.** It is the
one turn that must not be skipped, and the loop's recipe is rebound only at the top of a turn — so a
session whose last turn stood its own provider down falls out of the bottom still bound to the dead
one, and spends the wrap-up on the single recipe that cannot take it. Measured: the log said *the
next turn goes to `claude`*, and the wrap-up three seconds later ran on DeepSeek's base URL, died
`ECONNRESET` after 179 seconds, was billed to DeepSeek, and wrote nothing. The name **and** the
recipe are rebound, because the environment is what actually points the binary. **And where nothing
on the machine can write one it is skipped rather than attempted**, with the reason in the log:
three minutes of known-dead retries is worse than no handoff, because the `finish-restart` window
burns with them and the next daemon waits behind a turn that was never going to answer. A session
that ends without one is a session the next reconstructs from the cards.

#### When the provider does not answer from this machine at all

An allowance that runs out is the provider working. A hostname this network drops is the provider
being unreachable, and it looks identical from a lesson: a tutor listening, a student sending, and
nothing coming back. `api.deepseek.com` is dropped at the TLS ClientHello here — the same address
answers under its CloudFront name, so the filter keys on the hostname and no client setting reaches
it. The recipe is correct and stays; what changes is everything around it.

**A recipe with a provider of its own is probed before a turn is spent on it.** Only such a recipe:
anything driving the machine's default provider is covered by the machine-wide probe the failure
path already runs, and would pay a round trip for nothing. The probe costs 0.17 s — 0.07 s for the
reset from a filtered host, 0.10 s for the 401 from one that answers — against a first turn that
spends about three minutes retrying and writes no card. It is cached for `PROBE_TTL`, skipped for a
recipe already stood down, and skipped where nothing gets out from here at all, which is not this
provider's fault.

**The climb-down is then taken as the daemon comes up, not at the top of the first turn**, so the
board comes up saying who is actually teaching. A student watching a chip that says `deepseek` over
a hostname this machine cannot open has been told nothing, and the whole of what the swap is worth
is that somebody is told.

**And the sentence goes on being said for as long as it is true.** `agent_why` is rewritten every
turn precisely so it cannot outlive the swap it describes — which wiped it on the first turn after
the daemon came up on the substitute, leaving a student who chose a provider being taught by another
with the board no longer mentioning it. What settles it is the sitting's own choice against the one
taking the turn: they differ for exactly as long as the stand-down or the allowance lasts.

**The stand-down is per agent, carries an expiry, and the window doubles each time the same provider
is found dark again**, to a day. A flat hour is right for a filter that lifts by itself and wrong
for one that does not: a firewall rule outlives every expiry, so a fixed window costs a dead turn an
hour for ever, each one a student waiting three minutes for nothing. The strike count is kept past
the expiry — that is the whole of what makes the second finding cheaper than the first — and only a
turn that goes through resets it, because that is the only evidence the host answers. A recipe that
fails the same way twice for a reason the network is innocent of — a renamed model, a rejected key —
is stood down the same way, with no host on the record.

**And it reaches the glass, which is where it was missing.** Two facts already on disk — an
allowance that has run out, a hostname that does not answer — now come back from
`tutor --agents --json` as `unavailable`, in the launcher's own sentence. The chooser draws such a
provider **offered but dimmed** and says why on the tap, because a stand-down expires and a sitting
opened now is taught by whoever can take the turn when it arrives; what must not happen is it being
drawn as though nothing were wrong. The lesson payload carries the stand-down itself beside the
record it is about — the host, the reason, and when it will be asked again — which until then
reached nobody: it was in the `!!` lines of `agent.log` and the output of `board agents`, two places
a person holding an iPad cannot see, and it is the one fact that answers *why is nothing happening*.
`unavailable` is the only field on a recipe that moves while the board is up and that nobody edits a
file to change, which is why the assistant table's cache is a minute rather than a quarter of an
hour — still a subprocess every four hundredth request rather than every one.

**A machine-wide outage keeps the word the board has for it.** `no egress` survives to the record
instead of being recomputed from the turn's own words as an exit code: the reading face has a case
for *this machine cannot reach the internet*, and it never once fired, because by the time the board
read the record the reason had been replaced.

#### A message is owed until something answers it

`board wait` marks an inbox line read before the turn runs, so from the moment a message is taken
until something answers it, the daemon's own record is the only copy of it anywhere — and a turn is
minutes long. Measured on 23 September: a turn failed at 17:43:05, the message was re-queued in the
loop, the daemon was signalled three seconds later, and the student's work went with the process.
Nothing was answered until the person sent it again two and a half hours later.

So the debt is written into `agent.json` as well as held in the loop, **taken on when the message is
taken** rather than when a turn fails, and a daemon starts by draining whatever the one before it
left owed. That covers a signal, a walltime handover, a `tutor restart` and a lost node, which are
four ways to lose the same thing. Every path out of a turn settles it once, off what the turn left
behind: `None` where the turn went through, and `None` where it failed for something no retry
repairs — so nothing can quietly un-owe a message the daemon has promised to answer, and nothing has
to remember to.

**A failing turn whose result object is long is still a failing turn.** The client's result object
is the only place a turn says whether it actually failed, and it is longest exactly when the turn
had a lot to say: a blind seek to the last 20 KB of the log lands in the middle of it, and measured
on a real turn the tail kept `"result"` and lost the `"is_error"` that comes before it — a failure
read back as a clean turn. The seek is pulled back to the start of the final line when the cap would
have cut it. A fragment that arrives with no verdict in it ends the scan rather than being guessed
at in either direction: guessing failure marks a good turn broken, and guessing success is the
silence this whole path exists to end.

#### Exit nodes, which are invisible until they are not

An exit node routes **all** of this machine's outbound traffic through somewhere else. Nothing about
*serving* a lesson notices — tailnet traffic does not go through it, so the iPad reaches the board
exactly as before. Everything about *teaching* one does, because the tutor's provider is out on the
ordinary internet, and commercial VPN egress is precisely the address a provider geo-blocks,
rate-limits or challenges.

The failure that produces is total and looks like nothing: turns fail, the board shows an assistant
listening, and the reason is four lines into a log nobody opens.

```
board egress             what a turn can reach, and through where
board egress --repair    rotate exit nodes until one works
```

`board doctor` names the exit node when there is one. A headless tutor asks the same question by
itself, but **only after a turn has actually failed** — a probe before every turn would put a round
trip to the internet in front of every card a student is sitting waiting for, to answer a question
whose answer is almost always yes. If the egress is the fault, it rotates, and then re-answers the
message whose turn was lost rather than leaving the student to wonder and send again.

Three things it will not do:

- **It never turns the exit node off.** Dropping back to the bare connection is the obvious repair
  and the wrong one: somebody routing everything through an exit node is doing it deliberately, and
  exposing the address they arranged not to expose in order to rescue a tutoring session is not a
  trade this gets to make on their behalf. If nothing works, the original goes back and the fault is
  reported.
- **It never walks the whole list.** Four tries. A rotation that works through four hundred Mullvad
  endpoints is an outage of its own.
- **It never decides which endpoints matter.** `egress_probe` in the config is a list of URLs, with
  a default that suits the default agent. The board is not allowed to know which assistant is
  driving it — the same rule that makes a model a command recipe rather than a field — so the
  provider is named in one default value and nowhere else.

Ordering matters in the probe: any HTTP answer counts, including `401`. The question is whether the
packets arrive, not whether we are allowed in, and a 401 to an unauthenticated request has proved
the entire path.

#### Which course the address opens

Whichever course was last chosen on the machine holding the name. What that must never be is a race:
picking by knocking on every course's port in sorted order and taking the first that answered is not
a decision, it is the alphabet — and with two boards up it is permanent. Tapping *Probability* in the
hub did every correct thing and changed nothing anybody could see, because G sorts before P.

So it is recorded, published and checked:

- **`chosen.json`** in `~/.config/tutor-board/` records the course a *person* named. `tutor <course>`
  writes it and so does a tap in the hub. It is a decision, and a decision cannot be derived from
  file times — resuming a course touches its files, so "most recently used" is self-reinforcing.
- **`/health` publishes it**, along with the port that course is genuinely serving on, read from its
  own board record. Only the serving machine can read either of those things, which is why a board
  answers for them rather than anybody guessing.
- **the watch loop holds the name there**, and what it checks is the chosen course's own port
  rather than whether anything at all answers. A board nobody chose answers exactly as well as the
  right one, so the weaker question calls the wrong lesson healthy and leaves the iPad in it: one
  moment of the chosen board being down — a restart, a few seconds — hands the name to the next
  course along and nothing asks again. A drifted name is claimed back with the forced `board vpn
  serve`, because `--if-free` will not take a name off a live board and a standing choice is the one
  thing entitled to — once that course's own board answers, since a name is worth moving only onto a
  board that can draw something, and a wedged board is the board half's to fix first. A board an
  ended generation left behind answers exactly like a live one (*answering is not owning*), and the
  same test takes the name off it, because a leftover's port is not the chosen board's recorded one.
  A claim the tailnet refuses reads as a refusal rather than as a repair, and so does holding still:
  the name staying on a course nobody chose is said once, on the way into that state. With nobody
  having chosen, the loop keeps the address alive and never moves it.
- **`/health` also says which course this board is**, and nothing is offered the address whose name
  does not match the course that was asked for. Ports are derived from names, and derivation is not
  proof: a hash can put two courses on one number, and a start whose port was busy moves to the next
  in its sequence. Without the check, a wrong number becomes a wrong lesson silently — somebody
  opens a Galois proof and is shown a problem set.

Several boards may be up at once and each keeps its own assistant. A listening tutor is blocked on
`board wait` and costs nothing while nobody is asking it anything, so exclusivity would buy nothing
and cost the thing that matters: a cold agent re-reading the contract, the method and the lesson
before it can write a word. `test/choice.py` guards all of this, and it is worth reading before
changing any of it.

#### What only real hardware can settle

- Whether the iPad app's SSE stream reconnects cleanly when the address changes which board it
  serves underneath it, or whether it needs a nudge. The service worker caches the shell and nothing
  live, so the risk is a hung stream rather than a stale lesson.
- How long taking the board over on a new node actually takes after an allocation dies, and whether
  that gap is short enough to be invisible or wants a "reconnecting" state on the board.

### Why there is no registry

Courses are whatever directories sit inside the families `atlas.json` names, so adding one is
`mkdir courses/Topology`; there is no list to update and nothing that can go stale. `courses_dir`
moves the search if your repository lives somewhere else.

## Which subjects the app offers

**Whatever the machine that is serving has on disk, and nothing else.** The hub's list is a
directory listing of this machine's `courses_dir`, built when the app asks for it — never cached,
never baked into the installed app, never written down anywhere. A compute node with every
repository cloned into the shared home offers every subject; a laptop with four of them cloned
offers four.

There is no list to edit and nothing that can disagree with reality, and nothing to pick between:
the hub offers this machine's courses because this machine is the one serving the address. There is no subset to clone: a machine gets the
whole repository in one `git clone --recurse-submodules`, and `bootstrap.sh` clones nothing but
the vendored submodules. Offering less means pointing `courses_dir` at a directory holding fewer
courses.

**A course that is not running is still offered**, because opening it is what starts it. What the
hub must never do is claim one is running when it is not. A board that dies with its allocation
leaves `live/.board.json` behind on the shared home, and nothing in the file distinguishes it from
a board answering right now — so *live on compute304* outlives the node, and a tap goes somewhere
nothing is listening. The record is checked against the nodes Slurm says are still yours, and
`tutor resume` sweeps the dead ones as you log in. Where there is no Slurm to ask, the answer is
*unknown*, and unknown is left alone rather than deleted.

## Courses, and the one board

Nothing is registered and nothing is configured centrally. **Any second-level directory — one
sitting inside a family `atlas.json` names — is a course** if it holds a `tutorboard.json`, an
`AI_INSTRUCTIONS.md`, or a `live/` folder. The hub
lists what it finds each time you open it; adding a course means making a directory.

A course says what it is in `tutorboard.json` at its root, and there is very little to say:

```json
{
  "name": "Galois Theory"
}
```

`board init "Galois Theory"` writes it. Without one, the name comes from the directory and
everything works anyway.

**A repository declares nothing about its subject.** There is one board and one method: the
lesson is exercises, they are answered on the board by writing or by typing, and one question ends
the turn. A repository whose subject is code is no exception — the turn that reports an
implementation is a written or typed one, and the tutor goes and looks at what actually changed.
A `mode` key in a `tutorboard.json` is read and dropped.

What a repository *can* still say is **what the tutor is for**:

```json
{
  "name": "TRD-EHR",
  "stance": "do"
}
```

`"stance": "teach"` is the default and the original point of the thing — the
student writes the code, and withholding it is the teaching. `"stance": "do"` is
for a project where that is not what is wanted: the tutor writes the code, runs
it, submits the job, and the card becomes a *report* — what changed, what it does
now, what ran and what came back — rather than an exercise. Everything else about
a turn is unchanged, which is why it is one line of configuration and not a
second mode: still one card, still short, still written before the rest of the work,
still stopping to ask for the one decision it needs. A `--review` sitting is the
single exception, because a review asks rather than sets work.

It is declared and never guessed. Writing the code for somebody who wanted to
learn it is the one mistake here that the next card cannot undo, and nothing
about a repository's contents is evidence either way: a directory full of Python
is not a request to have the Python written.

**A sitting may answer differently from the repository, and this is the half that
made these repositories unusable.** One word in `tutorboard.json` can only answer
for the whole of it, and a project does not have one answer. PSYCH-ASR is the
case that broke it: the plumbing around a grid search is drudgery its owner has
written fifty times and wants written for him, and `transcript/render.py` in
the next directory is the thing he actually needs to understand. Both answers,
one repository, one word to say them in — so the work went to a terminal, and
once it was there the teaching went with it and the board saw neither.

So `tutorboard.json` is the **default** and a sitting may say otherwise:

```
board open "PSYCH-ASR" "the grid sweep" --stance do
```

or the control beside the sitting kinds on the board, which is where it belongs
because the person who knows which kind of work this evening is is holding the
iPad. Two rules go with it. It is **still never guessed** — a sitting that says
nothing inherits, and nothing about what is in the repository is evidence either
way. And it **ends when the sitting does**: the tutor is told in as many words
that the stance is this sitting's, that it must not go into `HANDOFF.md` as
though it were standing, and the next `board open` starts from `tutorboard.json`
again. `board status` and `board brief` print both when they disagree.

A review and a walkthrough ignore it entirely. A review asks and a walkthrough
reads; there is nothing to write in either, so a repository that wants its code
written does not get it written into one of those.

**A tutor with a `do` stance needs the access to match.** Editing files is
granted by `ai-config/workspaces/tutors.allow`; anything else it has
to run — `sbatch`, `squeue`, `git commit` — belongs in that file too,
and a companion repository the README points at (a planning repo, a task list)
has to be named in `additionalDirectories` or the file tools will refuse to open
it. A tutor that may write the code but not submit it can only ever report that
nothing has run.

### What differs between courses, now that nothing declares it

Two things, and both are read off what the repository actually *has* rather than off what it once
said about itself — which is the point, because a fact cannot go stale and a declaration can.

| | a repository with a syllabus | a repository without one |
|---|---|---|
| Where the exercises come from | the end of each section, in the book | whatever the README points at: a task list, a plan, a companion repo |
| The contents drawer (☰) | its chapters and problem sets | sittings made as you go, filed under ◷ |
| A `--review` sitting covers | chapters | the repository's own top-level parts |
| A `--walk` sitting covers | its source files, where it has any | its source files |
| Answering | the answer panel | the answer panel |

A third thing is declared rather than read off the tree, and it is one word:
`aim` in `tutorboard.json`, which says what a sitting in this workspace is for
when nobody chose. It beats its family's default in `atlas.json` and is beaten by
the sitting itself. `mode` is still read and dropped; it means nothing.

`chapters.tsv` or `chapters/chNN-*/` is what makes the first column true; there is no flag for it.
A repository with neither is told so and pointed at its README, and is explicitly told **not** to
manufacture chapters out of the README's own headings — which is a thing that happened, once, on a
repository that has none.

The answer panel is the same everywhere: a writing surface and a typed half, one toggle,
and the half that opens is the half an answer was last **sent** on — recorded on both send
paths rather than by the tab last pressed, and stamped with the sitting it was sent in, so a
half remembered in another workspace does not follow you here. The first question of a sitting
has no last half, so its aim decides: `doingTurn` opens the box where the sitting does the work
and the board where it teaches. An old question remembers its own answer: a board you wrote on
reopens with the ink still on it, and a typed answer reopens rendered in the block above the box —
a tap on it puts the words back in the box, and the send that follows revises that same response
rather than starting a new one. Ink carries
over from one question to the next on request (`carryOver`); typing never does, and a new box
opens empty apart from an unsent draft typed against that question. `test/half.js` is the
suite.

### Working in a course from a terminal, while it is a course

A course repository is somewhere its owner writes code, not only somewhere they are taught — and
the tutoring machinery runs unattended: the transcript beat commits and pushes every ninety
seconds, a session start fast-forwards the repository, and **⤓ save** on the iPad commits the whole
tree from a tap. Two rules keep those out of somebody's way, and they are in
`tutorboard/worktree.py` so that there is one of each:

- **A commit names its pathspec.** The beat commits `live/` with `--only`, so a file staged in a
  terminal a moment earlier stays staged. `git commit` commits the whole index, which is how a
  half-finished refactor once went into history under the message *lesson transcript*.
- **Nothing automatic touches a repository mid-operation.** A rebase, a merge, a cherry-pick, a
  revert or a bisect outstanding — or a detached HEAD — and the beat does nothing that tick and
  says why in its log; a tap on save says what is in the way, on the board, and commits nothing;
  `catch-up.sh` leaves the repository exactly as it is rather than stashing and resetting around
  it. Nothing is lost by waiting: the transcript is append-only and the next tick is ninety
  seconds away.

So `git rebase -i`, a bisect, or an afternoon of half-staged work in a course with a live board on
it is ordinary and safe in both directions. `test/beside.py` holds it, against real repositories.

## The machine this is written for

**A compute node on a Slurm cluster, with no administrator rights, on a shared home.** Every
decision in here follows from those four facts, and it is worth saying which ones:

- **Nothing needs `sudo`, ever.** The server is standard-library Python, the pages are plain
  browser JavaScript, KaTeX is vendored, and `tailscaled` runs in userspace mode out of `$HOME`.
  A change that needs a package manager or a system service is a change that cannot be deployed
  here.
- **TeX lives under `$HOME`**, and is found by globbing rather than guessing an architecture:
  `~/.TinyTeX/bin/*`, `~/.local/TinyTeX/bin/*`, `/usr/local/texlive/*/bin/*`.
- **Nothing may be supervised.** A timer or a service assumes a machine that comes back; an
  allocation ends and the machine stops being yours. A login is the only moment there is, which is
  what `tutor resume` and the login hook are for.
- **The home directory is shared and the machine is not.** Every record that crosses `live/`
  carries the node's name and every liveness check compares it, because a pid on a shared
  filesystem is a pid on somebody else's machine until proved otherwise. Slurm is asked whether a
  node is still yours; where `squeue` does not answer, the answer is *unknown*, and unknown is left
  alone rather than acted on.

It will run elsewhere — the platform knowledge is isolated in `tutorboard/tex.py`, `machine.py` and
`net/tailscale.py`, and `board doctor` says what it thinks it is on — but nothing is kept here for
the sake of a machine that is not this one.

### Driving it with a different assistant

The interface is a command line and a directory of files, so anything that can run a shell command
can drive it — OpenCode, Codex, Cursor, a local model behind a terminal wrapper. See
[Any agent, not just one](#any-agent-not-just-one).

The one thing to check before committing to a setup is **whether the assistant can look at an
image**. Every course's return path runs through the slate, so something that cannot read a page of
handwriting is no use in any of them.

That question has two halves, and both have to be yes:

- **the model** — whether it accepts images at all, which varies by vendor *and* by which model
  of theirs you point at it; a vendor's flagship chat model being text-only says nothing about
  their vision line;
- **the harness** — whether the tool driving it actually attaches the file. Something
  vision-capable behind a reader that only ever sends text is still blind here.

Both move, and neither is worth taking on trust. Settle it by experiment:

```
board eyes
```

renders an image holding a random token, a random word, and a small definite integral, and prints
the path. Ask your assistant to open it and report all three. Then `board eyes --answer` shows
what was actually in it, so an invented answer is obvious.

If it cannot read them, it has one way to read the page anyway:

```
board see live/inbox/uploads/20260922-150639-00-page.png
board see sheet.pdf --page 3
board see --route            # where an image would go, and nothing else
```

A board subcommand rather than a tool protocol, because that is the one interface every agent in
the registry already has — so it needs no MCP, no adapter and no per-vendor plumbing, and a new
provider inherits it by existing. Where the image goes is a `vision` block on a recipe — endpoint,
model, `needs_key` — resolved through the running agent first and `vision_agent` second.

**An answer is not believed because it arrived.** The failure this path cannot have is a confident
paragraph about a page nobody looked at — a text-only model behind the route, a harness that dropped
the image block, a file-reading tool that was denied — and all three come back exit 0 with fluent
prose. So every request carries a strip with six digits on it that are in the **image** and nowhere
in the prompt, and an answer that cannot read them back is refused, with what it did say quoted so
the cause is findable. That strip is a PNG written here from a glyph table and one `zlib` call — no
TeX, no poppler, nothing that can be missing on a machine and turn the guard off quietly. `board
eyes` is the same instrument run by hand for a person; this is it run on every call, for a program.

**And the provider's own words for it are read as well.** DeepSeek's endpoint substitutes
`[Unsupported Image]` for an image block its text-only model cannot take and answers 200, so that
string in a reply names the cause, where a missing code only says that whatever answered did not
look. **The same list is read off the tutor's own turn**, because a tutor whose model can see is
told to open the PNG itself and never goes through `board see` at all: a turn carrying the
placeholder fails with *the page never reached the model* rather than writing a fluent card about
handwriting nobody was shown.

**A command route runs without the sitting's routing variables.** `board see` is run by the tutor's
own Bash tool, inside a turn whose environment the running recipe wrote — so in a DeepSeek sitting
`ANTHROPIC_BASE_URL` is inherited and the `claude` route, whose whole premise is *the binary that is
installed here anyway*, is the provider it is falling back FROM reached through a second door.
Measured on the same PNG both ways: 14.4 s and a correct transcription with `seeing.ROUTING`
scrubbed out, 180 s and a timeout with those variables exported. `env` on a `vision` block is
applied after the scrub, so a route that genuinely wants one of them says so where the command is.

**A stand-down is about a host, not about a name.** Since a command route no longer opens the
provider's hostname, an agent whose *turns* are stood down still has working eyes on the local
binary, and skipping it for its name answers *no vision route here can be used* with one sitting on
the path. An endpoint route is skipped when the stand-down names its own host — and when it names no
host at all, which is a recipe whose requests are being refused for something the network is
innocent of, and this route carries the same key to the same provider. A `vision` block can also
say `sighted: false`, and a route that declares its model blind is never handed a page: an answer
from it is indistinguishable from a transcription.

**The route is re-asked when an attempt fails**, because the attempt that just failed is what writes
the evidence the next choice is made on — a refused connection is marked during the ask, and only a
later resolution reads it. Resolved once and never again, the first `board see` of a DeepSeek
sitting always failed with *the host could not be reached* and the tutor had no reason to believe a
second try would differ, so it did not make one. Only ever onto a name that has not been tried: the
same name back means nothing moved, and the first refusal is the honest answer, with every route's
words kept in the refusal.

**It refuses a fenced path before it reads a byte**, because it sends a file to a hosted provider
and a board command does not go through any assistant's pre-tool hook. The rule it uses is the
workspace-relative one: a fence is a top-level directory of the workspace that holds it, and `phi`
is refused wherever it appears. The any-depth rule would have refused every slate page, because the
board's own uploads land in `live/inbox/`.

A vision route is still a hosted model. For content that may not leave the machine the answer is
the `private` recipe, which reads it where it sits.

## The reading face

The default is **OpenDyslexic** — heavier at the bottom of each letter, with the shapes pulled
apart so `b`/`d` and `p`/`q` stop trading places. The **Aa** button cycles it:

1. **OpenDyslexic** — the default
2. **Atkinson Hyperlegible** — the Braille Institute's face, same goal of making similar letters
   unmistakable, calmer to look at
3. **Serif** — an ordinary book face

The choice is remembered and follows you from the hub to the lesson to the slate. Both faces are
vendored under `web/fonts/` with their OFL licences, so nothing is fetched from a CDN and the
installed app caches them like everything else.

**Mathematics is deliberately excluded**, and this is not an oversight. KaTeX's glyphs, metrics
and spacing are one system; substituting a text face into it does not produce a dyslexia-friendly
formula, it produces a broken one. Code is excluded for the same reason — alignment is the point.
`test/typeface.js` fails if a selector ever gets broad enough to swallow either, which is a
one-character mistake away at all times.

Leading and tracking move with the face, because OpenDyslexic's weighted baseline needs more room
between rows than a book serif does.

## Sessions, and finishing one

A session is opened with a kind, and in a mathematics course the kind matters:

```
board open "Galois Theory" "Ch 7 — Splitting fields" --lecture
board open "Galois Theory" "Problem set 4"           --homework
board open "Galois Theory" --review --over ch01 --over ch07
```

**Lecture** is teaching: one concept, one question, then wait. **Homework** is producing work that
has to end up typeset and compiled — the user writes each solution by hand, the assistant reviews
it, and once it is agreed correct the assistant transcribes it into the `.tex` and compiles the
finished assignment. The write-up is clerical once the mathematics is settled; making someone
retype their own proof teaches nothing. **Test review** is revision: the student says which
chapters the test covers and the tutor asks questions over exactly those, in the same shape a
homework problem is posed, with no document at the end because nothing is being handed in.

**Walkthrough** is the fourth, and it is the one for machinery that already exists: the student
names a file or a function, and the tutor hands them one invented instance and walks them
through the code a step at a time, asking what comes out of each one. Nothing is written in a
walkthrough. See [A walkthrough — code that is already
there](#a-walkthrough--code-that-is-already-there).

The kind shows as a badge on the board, so there is never a question about which sitting this is.

### The map — the front door of a course

**◈** in the title bar opens the map: a diagram of what the repository actually
IS. The boxes are its own parts, the arrows are what imports what, and the
outstanding work sits on that picture as numbered chips. **A course opens on it**
rather than on an empty board.

It is an entity-relationship diagram of a working system, which is the picture
somebody holds in their head when they understand a codebase and does not have
when they do not. That, and not finding a name, was the difficulty: *"Honestly
I'm so lost in all of this."* The contents drawer can find any name in PSYCH-ASR
and cannot say that the grading code depends on the naming convention.

**None of it is declared.** `tutorboard/course/map.py` reads three things off
disk on every build and nothing else:

| | |
|---|---|
| **the parts** | every directory of this repository that holds source, rolled up a level at a time until there are few enough to be a picture |
| **the arrows** | every import from one of those directories into another — Python's absolute and relative forms, and quoted paths in Go and JavaScript — counted, so a dependency carrying eleven imports is drawn heavier than one carrying a passing mention |
| **the work** | every step of the plan, matched to the part it names |

A box says what it is in **its own package docstring** — a sentence somebody
already committed about their own code, so it is true and nothing had to ask a
model for it. Where there is none it says what it is made of instead. A book
course has no packages and no imports: its content is its chapters, and the
arrow between two of them is the order they are read in.

**The work is drawn on the content, not beside it.** Each step of the plan is a
numbered chip on the box it names, coloured hot-to-cold along the plan's own
order — do first, soon, later, after that. So "what is left" and "where it
lives" are one thing you look at rather than two lists you hold together. A step
that names nothing on disk is **not** put on a box anyway: it rides in a tray
under the bar, numbered and coloured the same and opening the same sitting,
because putting it on a box would be a claim about where the work is and
dropping it would take a choice away. **Which one to do next is always yours** —
the colours are the plan's order, not a lock.

A box's own colour is only what the board knows: the sitting open now is
*working*, the box carrying step 1 is where the work goes *next*, a box carrying
any other step is *later*, a chapter with a lesson filed against it is *done*,
and everything else says *unknown*. Git recency is deliberately absent — touched
is not progressed.

### Three depths: the package, the module, the symbol

The boxes above are **directories**, and a directory is not a moving part.
*"Just looking at it should communicate everything one needs to know to
understand how the project works, and when we work on a TODO, it's obvious what
moving parts we'll be affecting."* The things that move are the modules and,
inside them, the classes and the functions — which is what an IntelliJ diagram
is worth its keep for.

So **every box with files in it has a second tap**, at its top right, and it
opens the level below:

| depth | the boxes | the arrows |
|---|---|---|
| package | a directory of source | every import from one into another |
| module | the files in one box | every import between two of them |
| symbol | what one file defines | every use of one definition by another |

**An expansion is a new picture, not a bigger one.** Splicing a package's twelve
modules into a diagram that already has forty boxes on it is the ugly grid the
front door was rejected for, with more effort. So opening a box redraws the
plane as the inside of that box, with a crumb — `PSYCH-ASR › transcript ›
render.py` — that is the way back up. **The crumb is read off the answer, never
remembered from the taps**: a trail kept as history is wrong after a sideways
step, a reload, or a second tap that lands out of order.

**An arrow that leaves is rolled up to the box it lands in.** Inside `evaluate`,
`grade.py`'s import of the naming convention is drawn to a wall marked
`artifacts` — dashed, keeping its own name, tappable to step sideways into it. At
symbol depth a use points at the **file** it came from rather than the box:
`grade` using `tidy` from `labels.py` next door is a fact about `labels.py`, and
rolling it up to `evaluate` would draw an arrow from a symbol to the box the
symbol is already inside, which says nothing.

**It is derived on the tap and never on a payload.** `map.inside(root, node_id)`
does the work and `GET /map/inside/<id>` serves it. The board payload is rebuilt
four times a second and already reads the head of every source file for the
top-level picture; this parses them whole, which is affordable exactly because
nobody is looking inside a box until they ask. The id comes off the path the way
an archived session's name does and is **looked up in what discovery found** —
`map.inside` returns `None` for anything that is not a box or a module of one,
and that is a 404.

**Python is parsed. Everything else is grepped, and the picture says so.**
`tutorboard/course/symbols.py` owns the one question "what does this file define
and what does each definition use":

- **Python, with `ast`** — standard library, which is this codebase's rule in
  every module, and most of this repository. Classes, functions, decorators,
  base classes and the names a body actually mentions, exactly. A class box says
  how many methods it has rather than unfolding into a fourth depth.
- **Everything else, with `walk.DEFINITION`** — the per-language pattern that
  already checks a walkthrough's symbol before it reaches a prompt, anchored at
  the start of a line. A regex is honest about definitions and a **liar about
  calls**, so a grepped file reports its definitions, draws **no arrows at all**,
  and reports `exact: false`. That reaches the foot of the map as *"found by
  pattern rather than parsed… trust it less than a Python box"*, because a Lean
  box nobody may trust as far as a Python one must not look identical to it. A
  module box says which it will be **before** anybody taps it.

**The written map is not replaced by any of this.** `live/map.json` carries *the
typist*, *the stopwatch*, *the name-tagger* — judgement no file in the repository
contains — and `meeting.py` spends those names in every note it writes. The
derived structure is a layer **under** the hand-drawn one: a box a person drew
and named keeps its name, and `inside` works off the files that box claims, so
opening *the typist* shows `typists.py`, `transcribe.py` and `run_asr.py` with
their real arrows out to *the stopwatch*.

**A symbol box opens a walkthrough over that symbol.** That is the payoff of a
diagram whose nodes are the things: tapping `run` opens a walkthrough of `run`
and not of the file it lives in. A module or a symbol is **not** a box the server
knows — `map.find` resolves the repository's own parts — so its id is never sent
as `node`; what goes over the wire is the scope, spelt the way `walk.label`
spells it (`psych_asr/asr/typists.py::run`) and re-resolved on arrival. It is the
one way to work that is offered on a derived box: a function is not a directory
to be examined on, and the tutor cannot be told to write a paper "about" a box
the server has no record of.

Caps, and both say they are caps rather than truncating quietly: `MAX_NODES = 44`
for the picture, `MAX_INSIDE = 40` for one expansion, `symbols.MAX_SYMBOLS = 40`
for one file.

### Tapping something opens the sitting, and what the box IS decides which one

A tap on a box is a door rather than a menu. Nothing is asked first, and the
sitting opens **already pointed at that part**, so nothing is typed and the
tutor is not left to guess. Asked for in these words: *"these are tutoring
styles that I don't want to be selecting when I open up a lesson; I want to just
change tutoring styles to anything any time."*

| tapping | opens |
|---|---|
| a part | a lecture on that part |
| a step chip | the same lecture, with that step named |
| a chapter | a lecture on that chapter |
| a problem set | a homework sitting on that set |
| a module or a function | a walkthrough over exactly that scope |
| a box of a vendor tree | a walkthrough over it, held in this workspace |
| a document | the page viewer |
| a wall — a sibling an arrow leaves towards | that sibling's own picture |

**No `aim` goes over the wire**, which is the point: the style the sitting runs
in is the `for:` row's to say, changed in place at any moment, and a tap that
carried one would be choosing it again at the door.

**What is left is chosen over a scope, and that is a second tap** — the small
control at the bottom right of the box, opposite the one that goes down a level.
It offers a walkthrough, a drill and a document to be shown, each only where the
box supports it, and it carries the `blockedBy` line. A box whose tap IS its one
honest way — a module, a function, a vendor box, a document — gets no control at
all, and neither does one with nothing to say.

**An address to a box does the same thing and is then spent.** A hand-off card
naming the next box is a tap that opens the sitting there; the bar stops naming
the box the moment it does, because a board that reloads on a bar still naming
one would file the evening away again.

What goes over the wire is the **box's id and the step's label**, and the server
looks both up in what discovery found before either reaches a filesystem or a
prompt. The sitting's label is built there too — that is what lets a part of a
repository be opened at all, since "evaluate" is not a chapter of anything.

**A make sitting is new, and it is the thing the board could not do.** Every
other sitting ends with the student having produced something; this one's
product is a file — a write-up or a deck, kept in the repository, drafted a
section at a time and read on the glass rather than pasted into a card.
`TEACHING.md` holds the rules. Asked for as *"have you write up papers or
presentations, and SHOW me these on the iPad."*

And the sitting carries an **aim** into `state.json` and into the line the tutor
is woken with, along with the box's purpose, its files, its steps and its
document — tapped in the `for:` row, or inherited from the workspace and its
family. A tutor woken into "tell me what to write" knows that is what it is; one
woken into "write it for me" knows it is that. A single `stance` cannot tell
those two apart, and they are not the same evening.

**One rule sorts `WORK`, and it is `needs`.** A way with a `needs` is chosen
over something — a walkthrough over files, a drill over a part, a document to be
shown — so it is offered on the map, where the something is a box you can point
at. A way with no `needs` is a style, and styles are the `for:` row. A paper and
a deck are in neither: they are products, they live in `DOCS`, and they are
`POST /writeup`.

**A stance is derived from the aim, never sent beside it.** `build` with a
stance of `teach` is a contradiction, so `config.AIM_STANCE` answers who writes
the code and `config.stance_for` resolves it in one place: the sitting's own
stance, then its aim, then `tutorboard.json`, then the family's default. The
browser sends neither on its own authority.

#### A sitting belongs to ONE box, and leaving it is a new sitting

Asked for as *"the session should be focused ON that component… if a task starts turning into
needing to go into a separate component, the tutor should direct the user to get to a good
stopping/saving point, and go back to the map and open up a tutoring session in that component."*

**Whether a box is what a sitting is scoped by is a property of the workspace, not a rule for the
board.** `map.scoped` answers it: a `part` on the picture means work here belongs to a box; a
`chapter` and a `set` mean the chapter already *is* the scope, and asking a lecture on Chapter 4
of Galois Theory which component it is about is a question with no answer.

**So in a workspace made of components, a sitting with no box says so.** The map tap is meant to
be the door and it is one door among several — `tutor galois`, `board open`, a chapter tapped in
the contents drawer, a board resumed after a reboot. `sense.node_sense` used to answer those with
the empty string, so the sitting had no scope *and* nothing said one was missing, which is how a
turn with no scope picks one. Now it says the sitting is about no part of the map, refuses to
choose one, and asks in its first card — as the addresses of every box, so the answer is a thumb.

**And a component boundary is a stopping point**, in `TEACHING.md` and in `node_sense` because in
a headless turn that line is the whole prompt. The old focus rule was about not *wandering*; this
is the honest case it left open — the work genuinely leads into another box, and the right answer
is to stop. The turn gets what is in hand to a saving point, writes up what was agreed, says which
box the work continues in, and stops. Reading another part of the repository is not what is
forbidden; working in one is.

**The hand-off is a TAP, not an errand.** A card that says *"go back to the map and open the
retrieval component"* is an instruction to somebody holding a tablet, which is the same defect as
asking them to type up the notes. Every box has an address (§2.1) and a card renders one as
something you open with a thumb, so `node_sense` hands the turn the address of every other box on
the map — beside whether any of the plan sits on it, because **a box with no step gets the step
proposed in the same card.** The turn has just found out what the work there is, which makes it
the only thing in the system that knows what it should say, and the discovery is lost otherwise.

The paragraph goes to the sittings a box actually scopes. A review, a walkthrough and a make
sitting are each held over a scope the person already chose, so they are still *told what the box
is* and are not told to stop at a boundary they are not working inside.

#### The aim can be changed without losing the lesson

"Wait, now teach me how this works", said three hours into building something,
used to cost the evening it was said in: the aim reached `state.json` only
through `POST /session`, and every path through that calls `board open`, which
archives the lesson.

The sitting-kind chooser carries the three styles — **teach**, **build**,
**coach** — and a tap on one changes the sitting that is open. `POST /aim`
writes it, puts the tap in the transcript, wakes a turn, and does nothing else:
no archive, no new tutor, every card still on the board. `board aim <name>` is
the same thing from a terminal, minus the waking. **trace** and **drill** are
not offered, because each is held over a scope — a list of files, a part of the
repository — and choosing one is choosing what it is over, which is a tap on the
map and a new sitting. **paper** and **slides** are not offered either: they are
products, and `POST /writeup` is how a sitting asks for one.

The waking is the half no file can do: a turn is a headless call, and only a
*fresh* one re-reads `sense.session_sense`, so writing a new aim into
`state.json` and stopping there changes nothing for the assistant that is
mid-conversation.

#### A paper or a deck can be asked for from ANY sitting, and it is not an aim

Asked as a question — *"at any point can I have a presentation or paper written
up going through the things we talked about in that tutoring session? Can I do
that in ANY tutoring session?"* — and the answer was no, twice over. Asking meant
changing the **aim**, which makes the whole sitting a make sitting and every card
after it a make card; and the aim row is hidden in a review and a walkthrough, so
in the two sittings where a write-up is worth the most there was no route at all.

**A document is a PRODUCT, not an aim.** An aim says what the sitting is *for*; a
paper or a deck is something any sitting can be asked for. So it is its own act:
**`POST /writeup`** carries `paper` or `slides` and optionally what it is about,
changes no aim, archives nothing, replaces no tutor, and is available everywhere.
Two controls in the sitting-kind panel, their words their own in `DOCS` because
nothing on the map makes a document, and that row is never hidden.

**And it is asked for at the front door too, against a workspace nobody is
looking at.** Asked for as *"the ability to write a paper or a slide deck should
just be an option on the homescreen, and from there I want to be able to specify
which projects/course, and which sections/results."* Three questions in one
sheet — which product, which workspace, what it is over — and only the third
costs a request: `POST /writeup/scopes` answers with that workspace's own
chapters, problem sets, parts, result directories and documents, from
`tutorboard/scopes.py`, which walks nothing the board's own pages have not
walked already. The ask is `POST /writeup` with a `repo` and a `scope` key, both
looked up in what discovery found and never joined onto a path.

**It lands in the library of the workspace it was written for**, which is not
the board that commissioned it, and the reply says so. The start is asked for
first and the inbox line written second — `/elsewhere`'s order, for its reason:
a document asked for in another workspace's inbox with nothing that will ever
read it is worse than a refusal. Nothing at all is built for the target until
the ask is allowed, `Repo` included: constructing one calls `ensure_dirs`, and
a refused request that leaves `live/` behind in a workspace it never wrote in
is the same defect one directory deeper.

**The workspace is named `family/name` on the wire**, never the bare directory.
A workspace is discovered rather than registered — making one is
`mkdir courses/Topology` — so two families can hold the same name, and every
route that resolves one takes the first walk hit. The qualified name is the
only spelling that cannot mean two places.

**And the picker says what it is not offering.** Forty rows per group is the
stop; where a group is longer, the count of what was left off comes back with
the list and the sheet paints it. A list that ends at a cap in silence reads as
everything there is, and the scope nobody can find is then the one they do not
know to look for.

**It lands in the library, not on the glass.** A make sitting puts its sections
on the board one at a time, because there the document *is* the evening. One
asked for alongside a lesson must not push the lesson off the screen, so the turn
writes no card at all — it writes the document, compiles it, and ends. Correcting
it is the library's own loop.

**Which leaves one thing with nowhere to be said: that it is being written, and
that it is there.** A turn that writes no card is invisible on the board by
construction. `tutorboard/writeups.py` is the record: one file per ask under
`live/writeups/`, three states — *being written*, *in the library*, *did not
land* — and a row in the chrome strip beside the missions. The state is **derived
from the library and then frozen**, the way a mission's ending is: `library.stamp`
is stats only, so what this ask produced is arithmetic over the stamp taken when
it was asked, and freezing is what stops next week's deck being credited to it.
Reading it retires the row, and the *server* remembers that, because the fact is
about the document rather than about one page.

**It costs nothing when nothing is being written**, which is nearly always: an
empty `live/writeups/` is one failed `listdir`, cached for five seconds. With an
ask open it is one `library.stamp` in the same window — **3 ms in
`libr-local-llm`, 5 ms in `PSYCH-ASR`, 24 ms for the 44 documents in
Galois-Theory**, measured on this cluster's shared home — shared across every
open ask rather than paid per ask.

**Nothing goes in the transcript**, which is the one place this differs from
`POST /aim` and `POST /handover`. Both of those put the tap in as a turn of the
student's because a card is coming back. Here none is: a student turn with
nothing answering it is what leaves the board waiting for a card that this turn
is told not to write.

**And the signal reaches the clock.** `doing_now` answers *is this a turn that
writes* from the sitting, and the sitting's aim deliberately has not moved — so a
paper plus a LaTeX build would run on a teaching turn's fifteen minutes. It also
runs **fresh**, for a revision's reason: a lesson resumed into a write-up is
exactly the narration a write-up must not be.

#### What a document covers, and how it reads, are two questions

The refusal that stopped a tutor narrating the evening it had just taught was
answering both with one sentence. **How it reads is fixed** — the subject
explained, for somebody who was not in the room, no first person and no reference
to the cards. **What it covers is not:** the scope may be the box, the chapter,
**or the whole evening**. Where it is the evening it is *the concepts this sitting
covered* — `board recap --all` reads the lesson back in one call and the card
titles are the topic list — and not the order they were taught in, the questions,
or who got what wrong. The split holds in all four places that say it:
`sense.MAKE_SENSE`, both `config.AIM_MEANS` entries, and `TEACHING.md`.

#### And one step of a coaching sitting can be handed over without leaving it

`coach` names the calls and lets them type it, and changing the aim is a blunt
way out of one step of that: it changes the whole sitting, and every card after
it is written the new way. So a coach card carries a tap at its foot — *you do
this step* — and **`POST /handover` hands over that step and nothing else.**
Asked for as *"in coach coding mode, I still want to be able to have a 'fuck
this, you do this step' option."*

It is `POST /aim` with the part that changes the sitting taken out. `state.json`
is not touched: the aim still says `coach`, nothing is archived, no tutor is
replaced, and the card that comes back is a short report of that step with the
next one posed under it. **Never a coach card about the step just done** — a
card explaining how it was done is a lecture nobody asked for, and the person's
next act is the next step. `TEACHING.md` holds that rule.

**Offered on the newest card only**, because that is the step: the ones above it
have already been typed. Refused where the tutor is already writing the code,
where the tap would mean nothing and waking a turn costs real money.

**The signal reaches the clock as well as the prompt**, and that is the half
that is easy to miss. `doing_now` answers *is this a turn that writes code* from
the SITTING, and the sitting says `coach` on purpose — so a handed-over step
would get a teaching turn's fifteen minutes for work that stages files and runs
a suite. `bin/tutor` takes the inbox line's signal, so the turn runs on a doing
turn's hour, and `sense.session_sense(repo, doing=True)` tells it the order to
work in: the sentence, the work, the report over the top of it.

#### Every sitting has a style, including the ones nobody chose one for

`tutor galois`, `board open`, a chapter tapped in the contents drawer and a board
resumed after a reboot all name no aim. They used to run on stance alone, which
is `teach` nearly everywhere and is the wrong answer for a project. So a family
declares a default in `atlas.json` and it is overridable at every level below:

    courses, practice   →  teach     the mathematics worked properly
    research, projects  →  build     the tutor writes it and reports

`config.aim_for` holds the whole precedence — **the sitting's own aim → the
workspace's `tutorboard.json` → the family's default** — and it is the only
place that knows it. `atlas.json` is still not a registry of workspaces: a
default style is a property of a family, and making a course is still
`mkdir courses/Topology`.

**A family default is a style, never an instruction to write code**, and that is
the one asymmetry in that precedence. `read_config` states the rule it follows
from: writing the code for somebody who wanted to learn it is the one failure
here that cannot be undone by the next card, so it is only ever done because a
repository asked for it **in writing** — and a sentence about a *directory* is
not a repository asking. `projects` defaults to `build` and `libr-local-llm`
declares only a name, so a plain lecture opened in a workspace somebody arrives
at wanting to understand was a doing turn, and being taught cost a tap. So a
doing aim inherited from a family is dropped and the sitting runs on stance,
which is `teach` unless the workspace says otherwise. A **teaching** default
still applies — it takes nothing away, and it is what gives a bare `tutor galois`
its style. Tap an aim, or write one in `tutorboard.json`, and nothing changes.

### The document drawer — everything compiled, under the box it belongs to

**Documents are reached from the map, two ways into one drawer.** Every box
carries a count of the documents under it — `▤ 7`, a plate right-aligned on its
chips — and tapping that plate opens the drawer scoped to that box. **▤** on the
map bar opens the same drawer over the whole workspace, grouped by box, with
whatever is placed nowhere under *Unfiled* at the end. A row reads **read it
here** through the viewer the board already owns, and **save a copy** through
the share sheet, which is `/view/shelf/<sid>` and `/download/shelf/<sid>`. A
document with no compiled PDF is greyed and offers neither.

**The drawer is HTML.** The map is a diagram of what the repository IS, and
[a diagram is not a list](#the-standing-rules): a shelf of files is a list, so it
is `#shelf`, a fixed drawer over the map with a way back to it, and no document
is ever a node on the plane.

**Which box a document belongs to is DERIVED from its path, on every read.**
`course/shelf.py` takes `library.documents` as the inventory and adds the one
thing the library does not know. Three rules, in this order:

| | |
|---|---|
| **a set** | the document IS that set's compiled write-up, or sits inside the set's own directory — `homework.sets` says where that is |
| **a chapter** | the path starts `chapters/chNN-…`, and NN matches the number on a chapter the syllabus lists |
| **a part** | the path starts with the box's own directory, longest prefix winning |

Nothing is registered, and that is the whole of why it stays true: a document
that moves belongs to a different box on the next read, and one that is deleted
stops existing rather than leaving an index entry pointing at nothing. Matching
none of the three is UNFILED, which is an answer rather than a failure — in a
workspace of code it is every document, because `docs/` and `writeups/` are not
source boxes. **A chapter is joined on the number the syllabus record carries,
never on a node id rebuilt from the directory name**: `ch0*(\d+)` on `ch04`
gives `4`, the node is `ch-04`, and a rebuilt id is how a box loses its edges.

**A source and the PDF it compiles into are one document.** A course keeps
`chapters/ch04-field-extensions/homework/ch04-homework.tex` and the build puts
the PDF one level up and across in `build/` — and `build` is in
`reading.IGNORE`, which is shared with every code workspace and does not move,
so the walk never reaches it. `library._walk` pairs them instead: a stem with no
PDF of its own asks `homework.compiled_pdf`, the one chain that knows where a
build lands — beside the source, then `build/` beside it, then the nearest
`chNN`/`hwNN` unit's `build/` — and what comes back is inserted as that stem's
`.pdf`. So a compiled chapter is listed as built, on the map and in the library
both, and only something nobody compiles, a `PLAN.md`, is without one. Taking
`build/` out of `IGNORE` is the answer that looks simpler and is wrong: the walk
groups by directory and stem, so every document arrives twice, and `build`
sorting before `handwritten` renumbers the ids ink is anchored on.

**The counts ride the payload; the list is fetched on a tap.** Each map node
carries `docs`, an integer, and that is all the payload carries — it is rebuilt
four times a second, and sixty documents on it four times a second is a walk of
a repository paid for by nobody looking. `GET /shelf.json` is the list, asked
for when the drawer opens and held against no change signal, because a stale
shelf is a *read it here* that draws last week's pages.

**A document is named by its `sid`, and the dedupe is by SORTED PATH.**
`reading.ident` slugs the filename, which is what makes one legible —
`ch04-homework`, `ch04-notes`, `a-course-in-galois-theory` — and the client
names that and never a path. Where two files in different directories share a
name, the suffix goes on the one whose path sorts later, never on whichever the
walk reached second: ink is anchored on `doc/<sid>/p<n>`, so an id that
renumbers when a directory is added hangs last week's marks on a different
document. It is the same anchor `/view/doc/<id>` uses, so a document reachable
both ways keeps one set of marks.

**And a course shelves work somebody else wrote.** `reading.NOT_OURS` hides a
directory called `reading` — right for a card, because it keeps a reference
library of other people's papers off the glass — and it also hides the textbook
splits a course keeps one per chapter. Three globs of the shelf's own put those
back: `chapters/*/reading/*.pdf`, `chapters/*/lectures/*.pdf` and
`homework/*/assignment/*.pdf`. They are shaped like a course on purpose, so a
repository of Python gains nothing from them; what they find is tagged `theirs`
and says so on its row. The shared lists themselves are not touched.

### The map is a plane

One finger pans it, two pinch it, **⤢ fit** shows the whole thing. The gesture
handling is `web/plane-core.js`, shared with the writing surface, because every
rule in it was paid for by a gesture that stopped working mid-lesson.

The layout is **arithmetic, never a simulation**: ranks from dependency depth
(import cycles are real, so the edges that close one are found and left out of
the ranking rather than allowed to run it away), then four passes of barycentre
ordering within each rank. The same repository lays out identically every time,
on every device — which is what makes a map something you learn the shape of. A
long chain wraps into bands of six ranks and is read like a page: twenty
chapters end to end is otherwise a 6,600-pixel ribbon, which is the same
one-direction failure a column is, turned on its side. At phone width the ranks
become one column.

Labels are **measured**, not estimated — a canvas measures the real face at the
real size, and the results are cached. Counting characters against an assumed
width puts the words outside their boxes: a line of capitals is half again wider
than the assumption.

It opens fit by **width**, at the top, never smaller than half size: fitting a
tall picture by area puts it on screen as a grey smear, and ⤢ is one tap away
for the whole shape.

### A course opens where you left it

Not always on the map: on the surface you were last on in that course, and if
that was the map, at the part of the map you were looking at, same pan and zoom,
with the box you last opened still marked. Somebody three steps into a
derivation who taps their course lands in the derivation. Only a course this
device has never opened — or one whose remembered surface no longer exists —
opens on the map. That memory is `localStorage` and is per-device on purpose:
two people reading one course are looking at different parts of it. It can
throw, it can come back empty, and the fallback for all of that is the map.

**And the map is one gesture from everywhere**, with no exceptions: the lesson,
the full-screen slate, the document viewer mid-deck, a past lesson under **◷**,
an empty board, a board whose tutor has died, a board that has lost its
connection, and the inside of every drawer and picker. `test/panic.js` checks
that surface by surface, one check named after each, because "there is a way
back" as a single assertion is the one that passes while a real state is
stranded.

### Getting around a course

**⋯ → ☰ contents** opens the contents: every chapter the course has, every problem set,
the way into a test review, and the way back to what has already been filed. Tapping a chapter
opens a lecture there; tapping a set opens a homework sitting bound to it. The chapter you are
in is marked. *(It was in the title bar until the map took that place. It kept every entry and
moved one tap away, with everything else that is real but occasional — seven controls in that
row is a row that overlaps itself on a tablet.)*

Nothing here is registered. Chapters come from the course's own `chapters.tsv` or its
`chapters/chNN-*/` directories, problem sets from the two layouts described below — the same
discovery everything else uses, so there is no index to maintain and nothing that can go
stale. Galois Theory offers 20 chapters and 21 sets — the 20 chapter sets and a loose worksheet under
`homework/`; Probability offers 11 and 3.

**Opening one files the lesson you are in** — cards, turns and answers together — so what you
leave stays readable under **◷** rather than being written over by what comes next. Jumping
around a course is therefore free: go to chapter 7, come back to chapter 2, and chapter 2's
lesson is still there with your own working in it.

A code repository has neither chapters nor problem sets, and is not told it is broken: its
sections are made as it goes. Each piece of work that gets committed is filed as one, which
is what `board push` marks there.

### Switching between a lecture, homework and a test review

The **LECTURE / HOMEWORK / REVIEW** badge in the title bar is the control. Tap it, and it offers
*lecture*, any problem set the repository actually has — `hw01`, `hw02`, `ch07` — or *test
review*. Nothing is typed, so nothing invented can reach the filesystem, and switching to homework
binds the set in one action. Switching back to a lecture unbinds it.

This was a terminal-only decision until it wasn't: `board open … --homework`. A student who
wanted help with a problem set had to find a keyboard to say so, which is the ceremony this
whole tool exists to remove.

**The four sittings differ in one thing: who chooses what gets worked on.**

| | lecture | homework | test review | walkthrough |
|---|---|---|---|---|
| The problem list | the tutor picks a manageable few from the section's exercises | the assignment sheet chose them; all of them, in order | the student chose the *chapters*; inside them the questions are the tutor's | the student named the *machinery*; the trace through it is the tutor's |
| Leaving some undone | fine — sections are archived and can be returned to | not fine; a skipped problem is a lost mark | fine — the point is finding what is not solid, not finishing a list | fine, but the trace is the point and it ends at the output |
| A document at the end | only if a set is bound | yes, and compiled | no; nothing is handed in, so nothing is typeset | no; the lesson is the record |
| Everything else | identical | identical | identical | identical |

In a homework sitting the tutor is woken with the path to the sheet itself — for Probability
that is `homework/hw01/assignment/Prob.Homework1.2026.pdf` — and told to read it and do
exactly what it assigns. If no sheet is filed, it is told to ask rather than to infer a
problem list from the chapter. Statements are transcribed into the set's `.tex` first, then
the problems are taught one at a time exactly as in a lecture.

### Test review — revising for a paper

Tapping *test review* does not start a sitting. It asks what the test covers, because the
student is the only person who knows: a drawer of every chapter the course has, each one a
tick, *select all*, and **start review**. Nothing is typed there either — every name in it came
off the repository's own chapter table — and the whole scope goes in one action, because a review
over four chapters is one decision and sending it four times would file the lesson away four
times over.

Then it teaches exactly as a homework sitting does. A card states a question, the answer block
takes the working, the tutor reads it and locates the break rather than repairing it. What
differs is where the questions come from and what happens at the end:

- **The scope is not the tutor's to widen or narrow.** It is named in the line the tutor is
  woken with and it is on a strip under the title bar the student can see, so a review that
  quietly turns into a lecture on chapter one is visible while it is happening. **change** on
  that strip reopens the picker with the current scope already ticked.
- **The questions are spread across the whole scope**, and anything answered cleanly is moved
  on from. A review exists to find what is not solid yet.
- **Nothing is written up.** No `.tex`, no compile, no `board hw` at all — nothing is being
  handed in, and the lesson is the record.

From a terminal, if you are already at one:

```
board review list                     everything this repository can be reviewed over
board open "Galois Theory" --review --over ch01 --over ch07
board review over ch02 ch03           change what it covers, without reopening
board review                          what it covers now
tutor galois --review --over ch07     or straight from the launcher
```

Chapters are matched on their label, their short form or their bare number, so `ch07`, `Ch 7`
and `7` all find the same one. A name the repository does not have is refused and named, never
silently dropped.

**In a repository that follows no book there are no chapters, and it is not told it is broken.**
It is offered its own top-level parts instead — `loader/`, `pipeline/`, `web/` — discovered the same way
everything else here is discovered, and a flat repository falls back to its own source files.
The sitting then asks about code that already exists: what a function does, why it is written
that way, what would break if it changed. It never sets work, and a repository whose stance is
`do` does not turn a review into an implementation — a review asks.

### Getting around a project — the drawer a book course always had

**A course that follows a book is painless for one reason, and it is not the mathematics:
`chapters.tsv` exists.** ☰ lists eleven chapters, a tap opens one, and nobody types a command or
decides anything. A project had none of that, and the drawer said so — *"sittings here are made
as you go"* — which put every decision about what a sitting was about back on the person holding
the iPad.

A project does write down what comes next. It just does not call it a syllabus and does not keep
it in the repository. So ☰ in a project now carries three groups:

| | what it lists | a tap |
|---|---|---|
| **What's next** | the steps in the plan this repository points at | opens a lecture on that step |
| **Walk through** | the repository's own source files | opens a [walkthrough](#a-walkthrough--code-that-is-already-there) |
| **Read** | the documents this project points at | opens them on the board |

**The plan is discovered, in three places, in this order.** `"plan": "..."` in `tutorboard.json`
if the repository says; otherwise whatever its README names — any path ending in a plan-shaped
filename, resolved inside this repository or in a sibling of it under the same home; otherwise a
conventionally named file at the root. A path that resolves anywhere else is refused rather than
read.

That last rule is what makes it work here without a single line of configuration: PSYCH-ASR's
README names `planning/PSYCH-ASR_TODO.txt` and TRD-EHR's names `planning/TRD-EHR_TODO.txt`, each
a path inside its own workspace, and a README that names a plan by filename alone is answered by
two listings — every family under the root, then every workspace inside one — because a plan
lives beside the code it plans.

**Steps are read, never invented and never re-ordered.** A plan that says to start at its fourth
item starts at its fourth item. Three shapes are understood — `STEP 1.` / `PHASE 2.` numbering,
markdown checklists (unticked ones only), and `##` headings — and where the file has a *"start
here"* block, that is where reading begins. Standing context is not a task: the block in these
files headed `ORIENTATION` is not offered as something to do.

**The tutor is handed the same answer.** The plan's path and its next few steps are in the line
it is woken with, with the instruction to open the plan at the step this sitting is labelled with
and not to re-derive any of it from the README. That removes two round trips and a guess from
every cold turn.

### Showing a slide on the board

**The best explanation in a project is often a document somebody already wrote**, and the board
could not show a page of one — so it was read on a laptop beside a lesson on an iPad, which is
the split attention this whole tool exists to remove.

☰ lists them under **Read**, and tapping one opens it in the page viewer the board already owns —
the same rasteriser, cache and viewer the compiled homework uses, because a PDF is a PDF. What
is discovered is any PDF in the repository, plus any the README names in a sibling directory,
and never a paper out of a `references/` library: those are somebody else's work and offering
them buries the two documents that are yours.

**A tutor can also put one page inside a card:**

```markdown
![slide 24](/doc/stage2-reference-walkthrough/24.png)
```

The page is addressed by *which document and which page*, not by which render — so a card written
today still points at the right slide after the deck is rebuilt at a different length, which the
manifest's own digest-carrying URLs would not survive.

The rules that go with it are in `TEACHING.md` and they are short: the slide goes at the top and
the question goes under it, one slide per card, never a slide instead of a question, and never a
page the tutor has not opened and read itself. A slide is an object to work on. A card with a
picture and no question is the word dump in a new medium.

### The library — everything a workspace has written, and everything it has produced

Asked for as *"view all papers and presentations related to a project very
easily"*, and the point of it is that it costs no sitting: `/library` is a page
of its own, reachable from the ⋯ menu on the board and from **Papers, decks &
results** on a workspace's sheet on the atlas front door. Two lists on it: the documents,
below, and **what it has produced** — the figures and tables a job wrote.

**A document is a stem in a directory, in however many formats it has.**
`manuscript.md` + `.pdf` + `.docx` is one document; `stage1_pipeline_walkthrough.tex`
+ `.pdf` is one document. The directory is the group and the heading. Nothing is
registered and nothing had to move: the title comes out of the source
(`\title{…}` in a `.tex`, the first `# ` in a `.md`), the kind comes out of it
too (`\documentclass[…]{beamer}` is a deck), and *stale* is arithmetic — the
source's modification time against the PDF's. `course/library.py` is the whole
of it, and it reads the same fence `reading.py` does, so nothing out of `phi/`
and nothing out of somebody else's `references/` is ever in the list. A source
whose build lands in `build/` is listed with that PDF — [the pairing is
`_paired_pdf`'s](#the-document-drawer--everything-compiled-under-the-box-it-belongs-to),
and the same list under the map's boxes is the shelf.

It is **not** `reading.py`. That module answers "what can go on the glass in a
card", is capped at 24 documents and walks three deep, and those are the right
numbers for a drawer.

**A new document goes in `writeups/<slug>/`** — `<slug>.tex`, `<slug>.pdf`,
`figures/`, `feedback/` — one directory per document, because a deck's figures
and its rounds of feedback need somewhere to be.

**What fifty documents cost, measured.** A cold open is one `pdfinfo` per PDF
and nothing else that costs more than a `stat`: **0.74 s for fifty on this
cluster's shared home, 0.41 s on local disk**, which is about 15 ms and 8 ms a
document. The count is memoised on the file's own modification time, so the
same library reopened is **0.1 s** and only a rebuilt PDF is paid for again —
and inside `CACHE_SECONDS` the whole payload is held, so tapping between pages
of one document costs nothing at all. There is no page-count budget and none is
needed; `MAX_DOCS` is 120 because a library longer than that is a file manager,
not because of what it would cost.

**And on a machine with no poppler it is 0.21 s and there are no page counts at
all** — measured with the renderer's PATH pointed at nothing. Every document is
still listed, with its title, its kind, its formats and whether it is stale,
because all four come off the source file rather than off the PDF. A missing
count is missing, which is what it should be: counting `/Type /Page` in the
bytes finds nothing in either of the layouts here, so the alternative is not a
worse count but a confident zero.

#### Feedback, and what acts on it

Tapping a document reads it on the glass through the viewer the board already
owns. **Say what is wrong** writes a note where the document is —
`feedback/<date>-v<n>.md`, dated and versioned, never stamped with the time,
tracked so it crosses machines — carrying the page they were looking at. The same
request asks for the revision, because a note nothing acts on is a note somebody
believes is in force.

**Ink is a complaint too, and it needs no textarea.** A ring round a figure and
an arrow to its caption is the same objection as "figure 3 is mislabelled",
already located — and typing out where it points is a translation nobody should
have to perform. Nothing new is stored to do this: a page of a document has
carried ink for as long as the viewer has, saved against `doc/<ident>/p<n>` the
way a mark on a card is saved against its card. `library.marks` is the reading
of it, and a note carries the pages that were drawn on and the picture of each,
because the strokes are coordinates and the image is what a reader opens. So the
send button is live with an empty box on a document somebody has marked, the row
says how much ink is on it, and the marks are recorded as handed over — the same
flag `/annotate/save` sets when ink is sent as a turn, so the board stops
offering them as unsent.

**And the ring is drawn on the page being read.** `✎ mark it up` in the reader
bar; each page carries `data-ann="doc/<id>/p<n>"` and `annotate.js` attaches to
it, exactly as the board's own viewer has since it first drew a document. The
pen is off until it is asked for, so a long document still scrolls. Strokes go
to `/annotate/save` with **`send` never set** — ink on a document is a complaint
about the document, and it becomes a turn when the note goes, not when the pen
lifts; sending on every stroke would wake a tutor per ring drawn. The marks
already on a document come back **with its pages**: `library.ink` puts them in
the `/library/view/<id>` payload, because this page opens no sitting and so has
no live payload to read them out of. Closing the reader forgets the store — the
next document has its own page 1, and one paper's marks drawn over another's is
the defect `test/marks.js` exists for.

**A document is named twice and its ink is its ink.** The drawer calls a
document by `reading.ident`, the slug of its filename; the library calls it by
where it sits, because two `manuscript.pdf`s in one workspace have to be told
apart. `library.mark_idents` asks under both, and `IDENT_MAX` is 40 because that
is what `writing.ANN_DOC` allows — an id longer than an annotation key is a
document that cannot be written on.

**And it appears in front of you.** `GET /library/stamp` is where each document
is, when its source and its PDF last changed and how big they are — `stat` and
nothing else, no titles and no `pdfinfo` — so the page asks it every four
seconds while it is visible and asks the expensive `/library.json` only when the
answer moves. One hash overall says *ask for the list again*; a hash per document
says *the one being read moved, re-draw it*, so a 33-page deck is not re-drawn
because something else was built. **Not the hub's stream:** that payload is the
lesson's, and this page opens no sitting on purpose. The render cache is keyed on
the PDF's own modification time, so a re-fetch gets the new pages.

**A re-draw keeps the reader's place, and keeps the ink.** The scroll is
restored as the images above it decode — a picture has no height until it has,
so a position set the instant the markup exists lands nowhere — and it stops
being restored after eight seconds, by which time the reader has scrolled
somewhere themselves. The marks stay: a ring somebody drew is theirs, and a
document that reflowed is not a reason to delete it. Where the page count moved,
the reader says out loud which version they were drawn on rather than pretending
page 7 is still page 7.

**A turn that was asked for says so until it lands.** The reply to a note says a
turn was woken, which is not the same as the document having changed — so the
page holds what was asked for, paints it on the row and in the reader, and clears
it when that document's own bytes move. Nothing else clears it. It is kept where
a reload finds it, because a tablet put down and picked up is the normal case.

**A round of feedback is readable.** `GET /library/note/<id>/<name>`, and the
rounds under each document are the button that opens it. That file is where the
turn writes `## What was changed`, which is the answer to *did it do what I
asked*, and without the route the record lived somewhere the iPad cannot open.
The name is matched against what `library.notes` found beside **that** document
— the rule `find` holds for an id, one level down.

#### Two asks, and an overhaul is not a correction

`revise` keeps the document's structure, its names for things and its claims:
the prompt says outright *do not start it again and do not widen it*, which is
right for "figure 3 is mislabelled" and wrong for *"that presentation needs an
overhaul now that we plan to use colibrì"*.

`rework` may restructure, cut, reorder and rewrite. It is the same panel, the
same feedback file and the same rounds — a longer turn rather than a different
kind of record — and `HEADLESS_REWORK_PROMPT` is `HEADLESS_REVISE_PROMPT` with
the do-not-widen sentence gone and a brief in its place. What it costs:

| | |
|---|---|
| **a purpose** | a sentence saying what the document is FOR now, at least 25 characters, written into the note under `## What this document is FOR now`. `/direction`'s shape one level down: an overhaul with no new purpose in it is a rewrite for its own sake |
| **a committed source** | refused otherwise, by name, with nothing written. An overhaul replaces the whole document and git is the only undo it has; committed as it stands, the whole overhaul is one diff. The board refuses rather than committing a half-finished edit, because the state that would be reverted to is one nobody chose. The refusal names **⤓ save** on the board rather than `git commit`: a guard whose remedy is a terminal has sent somebody to a keyboard to get past the board's own rule |
| **not a delivered manuscript** | the factory holds its evidence, its terminology lock and its venue, and "restructure, cut and rewrite" is what every one of those gates exists to refuse. A paper whose purpose has changed is a new paper |

`leaving.uncommitted` is the git half, and it is there rather than in
`worktree.py` because `git status --porcelain -uall` has one parser in this tool
and a second would go quietly false on one side. A workspace with no repository
over it refuses nothing: there is no undo to protect and refusing would make the
ask unavailable rather than safe.

An overhaul gets a **doing turn's clock** — `doing_now` says so on the signal —
because thirty-three pages rewritten with a LaTeX build at the end of it is not
fifteen minutes. A plain revision is left on the sitting's own clock: it changes
what a note names and is over in a minute.

**Which machinery revises it depends on which wrote it.** A document this
repository holds the source of is revised by the board: a `[revise]` line in the
inbox, and a turn woken on it. A manuscript delivered into `manuscripts/` goes
back to Paper-Writer — `manuscript.revise` drops a job with a `## Revision`
section naming three things, and the factory reads all three — because the
factory is what holds the evidence, the terminology lock, the checklist and the
venue's word limit. An explainer is never routed through it: "how the serve
harness works" has no venue and makes no claims, and every one of those gates
would either refuse it or invent something to satisfy itself.

| | |
|---|---|
| `document` | the **source**, never the rendering. `library.py` puts the PDF in `rel` because `rel` is what goes on the glass, and a revision pointed at a PDF is a revision asked to edit a picture — so the record carries `source` beside it, and that is what the job names |
| `feedback` | where the note landed, so the factory quotes the person's own words rather than the board's summary of them |
| `workspace` | the root the other two are relative to. The factory is another workspace with its own state directory and cannot resolve `manuscripts/manuscript.md` against a root nobody named |

On the other side of that seam a revision **skips the planner**: the delivered
Markdown is split on its own headings into the sections its editor works on, and
the anchored-edit loop changes what the feedback names and nothing else. Its
README has the path. A correction re-planned from the claims list is a different
paper, which is the failure the section exists to prevent.

**A revision turn runs fresh and writes no card**, and so does an overhaul.
`turn_plan` resumes the agent's conversation by default; a revision resumed into
a lesson drags the lesson into the document and the document back into the
lesson. So it is its own
session, its report goes at the bottom of the feedback file, and
`live/cards/`, `live/state.json` and the archive are left exactly as they were —
somebody mid-proof on an iPad is not interrupted by somebody correcting a deck.
That is what makes the library a separate interface rather than a sitting.

#### What it has produced — figures and tables, on the same page

A mission ends by naming what it wrote — *figure `neighbor_count_sweep.png` and
four tables are in `RESULTS_DIR/neighbor_count_sweep/`* — and the second half of
`/library` is where those are looked at. One page, because *everything this
workspace has made* is one question, and because this is the page the front door
and the ⋯ menu already open.

`course/results.py` is the whole of it, and it is the module the board's figure
drawer already uses: one walk, one allowlist (`fenced.RESULT_DIRS`), one fence
(`fenced.NEVER`, matched on the directory **name** at any depth), one id.
Nothing is registered — a directory a job wrote this morning is on the list
because it is on disk.

**The directory is the group**, closed until it is opened, newest first. TRD-EHR
holds **98 result directories, 628 figures and 233 tables**; that is headings
somebody scrolls and rows nobody could. `_where` is the reason: a pipeline
writes `propensity_by_arm.png` once per contrast under the same name, so the
directory is what tells three of them apart.

**A row is the filename, not a prettied version of it.** The drawer prettifies,
because there a figure is being *chosen*; here the reader arrived holding a
string a card gave them, and the search box matches that string.

| | |
|---|---|
| **a figure** | `GET /result/<id>` — the drawer's own route, `<img>` straight onto the glass, never cached by the service worker because the next job rewrites it at the same name |
| **a table** | `GET /library/table/<id>` — read on the board and sent as rows. A CSV handed to a browser is a file an iPad puts where nobody finds it. What a table is on disk is what these pipelines write: `.csv`, `.json`, `.md`, `.txt` |
| **an id, never a path** | `results.index` is the lookup and a miss is a miss. `find` resolves against the whole walk rather than the drawer's `MAX_FIGURES` — that cap is on what a *card* is offered, and a page that lists four hundred and 404s most of them is worse than one that lists none |

**Bounded, and it says what it dropped.** `MAX_GROUPS` directories,
`MAX_IN_GROUP` rows inside one, `MAX_ROWS` rows of a CSV — each reported beside
the list, because a silent cap reads as *this is all there is*. A 2.9 MB,
hundred-thousand-row `sweep_curve.csv` is streamed to the cap, never loaded, and
the page says *300 rows of 101,889*.

**An empty list explains itself, and a fence is named.** Where it looked, and
what it refused: `research/PSYCH-ASR` has no results directory *and* holds
`phi/`, and the page says both — a workspace whose output is session content
must not be able to pass for a workspace that has never run anything.

### A walkthrough — code that is already there

**Every other sitting ends in the student producing something new, and in a working project most
of what has to be understood was written months ago.** That gap is why these repositories were
being worked in a terminal rather than on the board. A tutor with nowhere to put existing
machinery does the only thing it can, which is manufacture exercises around it —
`PSYCH-ASR/live/cards/0003` is that happening: invented diarization arithmetic on fictional
numbers, skipped twice, in a repository whose owner had written down which algorithm he wanted
explained.

A walkthrough is the sitting for it. It is held over a **file, or one definition inside one**:

```
board walk list psych_asr/transcript        every file it could be held over
board open "PSYCH-ASR" --walk --over psych_asr.transcript.render.render
board walk over psych_asr.transcript.turns  change it, without reopening
board walk                                  what it covers now
```

Names are matched the way the language names things: a path
(`psych_asr/transcript/render.py`), a module (`psych_asr.transcript.render`), a definition
inside one (`psych_asr.transcript.render.render`), or a bare filename where the repository
has only one of them. **A definition is checked against the file before it is carried anywhere** — a walkthrough
announced over a function that is not there sends the tutor looking, and it finds something else
and teaches that. A name that matches nothing is refused and named; an ambiguous one resolves to
nothing rather than to whichever was walked first.

**A `#!` line is as good a declaration as a suffix**, and it is what `file(1)` would use. The
list of what can be walked through keyed on the extension, so the entire surface of colibrì —
`bin/coli`, `bin/coli-up`, `bin/coli-ask`, `bin/coli-code` — was invisible: extensionless bash
scripts with a shebang. A walkthrough of `libr-local-llm` offered six files and not one of them
was the one anybody would ask for. Now a file with **no** extension is read for a shebang (256
bytes, only where there is no suffix to go on, and only in a directory the walk already visits),
and the interpreter it names is what decides which language's patterns look for a definition
inside it. A file with neither a suffix nor a shebang — a licence, a lock file, a data dump — is
still not machinery, because it declared nothing.

On the board it is the same picker the test review uses — the sitting badge, then **walk
through…** — over the repository's source files, headed by the directory each sits in. There is
no *select all*: a walkthrough over a hundred files is not a sitting, and is one tap away from
being an accident.

**Nothing is written in one.** No change is assigned, no refactor is proposed, nothing is fixed,
and no code goes into a card — not even where the repository's stance is `do`, because a
walkthrough reads. A real bug the tutor notices is one sentence at the end of a card and a
separate sitting.

**The exercise is a hand trace, and the format is not invented here.**
`research/PSYCH-ASR/docs/stage1_pipeline_walkthrough` is this done by hand, and its own
README entry says to read it before touching Stage 1. What made it work is what the sitting now requires: one invented instance
carried the whole way through, plain names before identifiers — *the typist*, *the stopwatch*,
*the name-tagger* — the algorithm shown as worked passes over that one instance, and the summary
last. The difference is that the student does the passes instead of reading them, one card at a
time, and the tutor finds out where it broke.

So each card is one step: the smallest excerpt of the real source the question is about, never
the file; the state of the instance before that step, as a table; and one question — what does
this return, which branch runs, what is in this variable now, what breaks if this line goes.
When they are wrong the same step is re-asked on a fresh instance rather than explained again.
The destination is the student carrying the instance all the way through and producing what the
code would produce. **The recap comes last**, three or four lines, once the trace is done — a
summary before the trace is the word dump the sitting exists to replace.

The scope is theirs and the rest of the repository is off the table, which is on the strip under
the title bar the whole time. If nothing has been named, the tutor asks which file in its first
card rather than choosing one: they know what they do not understand and it does not.

### A homework sitting is bound to a problem set

The teaching loop is the same as a lecture's — a card states the problem, the answer block takes
the working, the tutor reviews it. What is different is that a homework sitting is *producing a
document*, and the state of that document lives in a `.tex` file nobody holding an iPad can see.

So the sitting is bound to a set, and the board carries a strip saying which one, how much of it is
written up, and whether the last compile passed:

```
board open "Galois Theory" "Ch 7 homework" --homework          discovers the set
board open "Probability" "Homework 4" --homework --set hw04    or says which
```

```
board hw                  which set, and what is still empty
board hw list             every problem set in this repository
board hw use ch07         say which one, when the label was not enough
board hw build            compile it; the result appears on the board
board hw file 7.2         file a sent page into the set's handwritten/
```

```
hw04  homework/hw04/hw04.tex
  1      written up
  2      EMPTY
  3      statement not transcribed
  1 of 3 written up
```

**The board does not write LaTeX and must not.** The assistant edits the `.tex` with its own tools,
as it does with every other file in the course; what the tool owns is the part that is otherwise
invisible from a tablet. `board hw build` records the outcome, and a failed compile puts the actual
LaTeX error on the board the way a failed push does — "the build failed" without the reason is a
message that sends somebody to a laptop.

Two layouts exist across the courses here and neither is more correct, so the set is **discovered,
not assumed** — the same principle as course discovery:

| | |
|---|---|
| `homework/hw04/hw04.tex` | numbered by assignment (Probability) |
| `chapters/ch07-*/homework/ch07-homework.tex` | numbered by chapter (Galois) |

The session's own label usually settles it: *Homework 4* finds `hw04`, *Ch 7 — splitting fields*
finds `ch07`. When it cannot — twenty chapter sets and nothing to choose between them — it says so
and stops rather than guessing, because a wrong guess compiles the wrong document or files
handwriting into somebody else's problem. `board hw use` pins it for the sitting.

Problem labels are opaque strings, not numbers, because one course numbers problems 1, 2, 3 and the
other numbers them 7.1, 7.2, 7.3. `test/homework.py` covers both layouts, all three per-problem
states, and the discovery rules.

### Saving and pushing

```
board finish
```

raises a prompt **on the board** — not in a terminal, because the person answering is holding an
iPad — asking whether to save and push. Tapping **Push** runs the tool's
`board/scripts/save-and-push.sh`, and the outcome appears on the board either way: a green line
naming the branch, or a red one carrying the actual error text. A failed push is never silent, and
the hub shows the last result too.

`board push "message"` does it from the terminal without asking.

**⤓ save commits and pushes.** It runs `board/scripts/save-and-push.sh` from the repository
root — the same script, the same commit, the same push as the offer you get on the way out. There
is one copy of that script and it is the tool's; `board push` from a terminal runs it too. Two
doors onto one path to a commit, and the working directory is what tells the script which
repository to commit. One repository holds every workspace, so that commit carries the whole tree:
both doors name the other workspaces that had uncommitted work in them rather than sweeping them up
in silence, and both lead the commit subject with the workspace the save was made in.

**You can save without the tutor, at any point.** `⤓ save` in the title bar raises the
same offer, worded as what it is — *Save this work? … The lesson stays open.* Sessions end
by being abandoned far more often than they end tidily: a lid closes, an allocation
expires, somebody puts the iPad down. Until this existed the only route to a commit was a
prompt only `board finish` could raise, so leaving mid-session meant leaving the work
uncommitted.

**And the way out asks when there is something to lose.** With everything committed the back
arrow (`‹`) just goes — a prompt that appears regardless is a prompt that gets dismissed
unread, which is how the one time it mattered gets dismissed too. With work outstanding it
offers
*Save and push*, *Leave without saving*, or *Stay*, and says plainly that the lesson is kept
either way — cards, answers and annotations are files, and they are all still there when you
come back. Leaving without committing is a choice somebody makes, not something that happens
by walking away.

The save also shows what is at stake before you go: with uncommitted work it reads **⤓ save 4**
in amber rather than a quiet `⤓ save`. `git status` is asked at most once every eight seconds
and cached, so the poll loop stays cheap. And if you come back to a session you left with work
outstanding, the offer is put in front of you once rather than waiting to be noticed.

It behaves identically in every repository, and it always commits and carries on: a save is a
save. It never ends a session: one button that files the lesson away in one course and leaves it
open in another is a difference nobody can see from the iPad. `board open` and `board archive` are
what file a lesson, everywhere.

The script is deliberately ordinary — `git add -A`, commit, push — and lives in each repository so
it works with or without this tool:

- The commit is authored by whoever `git config user.name` says, with **no trailers, no
  co-authors, and no attribution to any assistant**. The work belongs to the person who did it and
  the history should say only that.
- `GIT_TERMINAL_PROMPT=0`, so a missing credential fails in seconds with a readable message
  instead of hanging on a prompt nobody can see.
- Nothing to commit is a success, not an error; unpushed commits still get pushed.
- No `origin` means it commits locally and says so.

## Exporting the whole conversation

A lesson on the board is a scroll on a piece of glass. Somebody eventually has to *show* it —
to a professor, to themselves in a fortnight.

**There are two documents, and they are not the same document.**

```
board export                     # this lesson, typeset
board export --all               # every lesson in the course, as one
```

and, on the iPad, **⋯ → export this lesson** and **⋯ → export the whole course (typeset)**.
Reading one, or getting back to one made a fortnight ago, is the map's [document
drawer](#the-document-drawer--everything-compiled-under-the-box-it-belongs-to).

**`export this lesson`, from the device, is a photograph of the lesson.** Asked for in those
words — *"I want it as if it were a screenshot of the entire iPad screen scrolled down over the
whole tutoring session"* — and it is what it says: the board's own pixels, dark paper, the card
chrome, the reading face, your handwriting sitting where it sits, packed onto A4 pages and cut
where a card allowed it to be cut. It is taken by the iPad, because the iPad is the only thing in
the system that knows what the lesson looks like: there is no headless browser on a compute node
and there never will be. Everything else about it is the server's, and is the same as for the
typeset export — where it goes, what it is called, which version it is, and that it is staged for
the next commit. So `transcripts/` holds one numbered series, not two.

Two things are deliberately not photographed. **The furniture** — Send, the write/type toggle,
`skip this one` — because a live control in a document somebody is emailing is a picture of a
button that does nothing. And **a blank writing surface**, because a foot of empty paper as the
last page reads as a document that went wrong; working you have drawn and not yet sent is yours
and is in there.

**`board export`, and `export the whole course`, is the typeset transcript.** Both halves of the
sitting in the order they happened — the tutor's cards typeset from their own markdown and
mathematics, and *every page you handed in*, as the picture that was actually sent, labelled
`You wrote — attempt 2 of 5` with the time. An exercise worked over ten attempts is ten pages of
your own handwriting with the tutor's replies between them, which is the record of the work rather
than a summary of it.

The whole course can only be this one. A filed sitting is not on the glass, so there is nothing on
the device to photograph.

**And either one can leave the device.** The banner that reports an export carries **save a copy**
beside it, and it never navigates the app anywhere: the document is fetched and handed to the
system as a file, so iOS raises the share sheet OVER the board — Files, iCloud, a phone by AirDrop,
an email to a professor — and Cancel puts you back in the lesson, because the lesson never went
anywhere. The write-up has the same button, from **⋯ → export the written-up homework**.

**And either one can be read without leaving either.** **read it** sits beside *save a copy*, and
in the panel it opens the pages are pictures: drawn to PNG by the machine that holds the PDF, shown
in a panel the board owns, closed with ✕ back into the lesson. That is not a decoration over a
simpler mechanism — it is the only one that works. iOS renders a PDF in an `<iframe>` as one
unscrollable first page, and *navigating* to a PDF in a home-screen app leaves the board with no
chrome, no back button and no share sheet, which is the trap the download button was rewritten to
escape in the first place. A machine with no page renderer on it — `pdftoppm`, `pdftocairo` or
`gs`, looked for on the same PATH as TeX — says so in the panel and offers the copy instead of
showing an empty one. The pages are cached against the PDF's own modification time, so the first
open of a long document takes a few seconds and every one after it is instant, and a rebuilt
document is drawn again rather than served stale.

**And both are reachable at every moment, from the map's [document
drawer](#the-document-drawer--everything-compiled-under-the-box-it-belongs-to)** — under the
chapter or the set they are about, beside every other document the workspace has compiled. A
control that lives only in the banner of the build that made it has a life of about one second:
the next payload replaces that banner, and the URL behind the tap is cleared with it.

A document is a **file**, not an event. So whether one exists is a question the payload answers on
every change, off the disk (`papers` in `board.json`, four `stat` calls), and the banner's own
**read it here** and **save a copy** are the same two the drawer puts on every row. A write-up
compiled ten days ago is as reachable as one compiled ten seconds ago.

Three rules go with it.

- **The write-up's record now comes off disk.** `board hw build`'s outcome reaches the banner from
  `live/hw.json` by way of the payload, in its own argument rather than in the one that belongs to
  `push.json`. A record the client invents from the reply to `/hw/build` is on no disk anywhere,
  which is what lets the next payload paint over it.
- **The banner is its own function.** `paintBanner`, never `paintSession` with an empty state,
  which repaints the session badge as *lecture* for the second before the next payload puts it
  back — a homework sitting announcing itself as a lecture at the exact moment somebody exports
  their homework.
- **The service worker does not cache the downloads.** `/download/…` matches neither the live
  list nor the runtime list, and anything falling through to the shell rule is cached on any 200.
  That is megabytes of transcript inside the app's own storage allowance, and — worse — a document
  rebuilt at the same URL every time, so a cached one served while the link blinks is last week's
  write-up under this week's name. That is the same mistake as a cached lesson, one layer down, in
  the file whose whole rule is against it. `/download/`, `/view/` and `/paper/` go to the network,
  always.

`test/paper.py` holds all of it against a real board on a real socket: both documents resolved,
named for their course and their set, handed over as attachments rather than previews; the pages
drawn, counted, ordered, cached, re-drawn after a rebuild, and bounded so the cache cannot grow
without limit; a machine with no renderer degrading rather than showing an empty panel; every
traversal refused; and, by reading the client, that the record reaches the banner from the payload,
that nothing navigates the board's own window, and that the service worker leaves all three paths
alone.

It lands in `transcripts/` — outside `live/`, which is runtime state a course repository ignores
— as `<lesson>-v1.pdf`, then `-v2.pdf`, then `-v3.pdf`. **Numbered, never stamped with the time.**
A folder of `20260901-143210-...` is an eyesore and still does not answer the only question anyone
asks of it, which is which one is the latest. The `.tex` is kept beside the PDF, because the
source is the record and a PDF nobody can rebuild is a dead end; the images are named relative to
the repository, so it still builds on another machine.

Both files are `git add`-ed as soon as they are written — **staged, not committed**. An export
happens in the middle of a lesson and a commit in the middle of a lesson is a decision the person
makes, so it goes with the next `⤓ save` or `board push` like everything else.

`--all` puts every filed lesson and the one still open into a single document with a contents
page, each sitting named by the moment it was filed and the open one saying *(in progress)* —
because two evenings on the same chapter carry the same label in `state.json` and a table of
contents that cannot tell them apart is not one.

What it costs: a LaTeX run of a minute or so for a long course, and the board says so while it
waits. A failure never loses the source — the `.tex` is written and staged either way, and the
error appears on the board rather than in a log nobody opens. The photograph costs a few seconds
of the tablet's own time instead, a card at a time, and says which card it is on — a button that
goes quiet for twenty seconds is a button somebody presses twice.

## Setting up a course repository

The minimum is one marker: make the directory inside a family — `mkdir courses/Real-Analysis` —
and put an `AI_INSTRUCTIONS.md` or a `tutorboard.json` in it. A directory with neither is not a
course, and `board start` inside it walks up to the Atlas root and serves that instead. Everything
else below is optional, and each item buys something specific.

1. **`tutorboard.json`** — declare the name rather than having the directory's used.
   One command: `board init "Real Analysis"`. There is nothing else to declare unless the
   repository wants the work *done* rather than set, which is `"stance": "do"` and is written by
   hand.

2. **`latex/coursemacros.sty`** *(maths)* — your own macros, and they win. The board typesets
   twice, and this file goes in front of the board's own vocabulary on **both** sides: ahead of
   the generated `\providecommand` set in every compiled diagram and every exported lesson, and
   laid over `web/macros.js` for the KaTeX that draws a card on the glass, which the hub payload
   carries per workspace. So notation you already use in your `.tex` files renders on the board
   unchanged, at your arity rather than at anybody else's — a name the board happens to know with
   a different number of arguments is you being right about your own notation, not a clash.
   Without the file you still get the shared set in `web/macros.js` — `\QQ`, `\degree{L}{K}`,
   `\Gal`, `\PP`, `\EE` and the rest. `test/vocabulary.py` checks every course in the tree.

3. **`scripts/build.sh`** *(optional)* — how this repository compiles a `.tex` file, called with
   one argument, the path to it. `board hw build` uses it, so a homework write-up comes out
   through the same pipeline as the rest of your documents. (The transcript export compiles
   itself, because it has to work in a repository that has no build script at all.)

4. **`AI_INSTRUCTIONS.md`** — how the assistant should teach *this* subject. The board is a
   display; this is the contract. It is also what marks a directory as a course if you have no
   `tutorboard.json` yet.

5. **A `.gitignore` that keeps runtime state local and tracks the transcript** — the lesson
   transcript (`live/cards/`, `live/turns.jsonl`, `live/state.json`, `live/slate/`,
   `live/answers/`, `live/archive/`, `live/inbox/`) is versioned, so a lecture — the cards, the
   student's turns, their handwriting, the files they uploaded and the archive — is the same
   whichever machine picks it up. What stays ignored is the per-machine runtime: `.board.json`,
   `agent.json`, `board.log`, the compiled figure cache and exports. The exact block is the one
   this repository's courses carry:

   ```
   live/*
   !live/cards/
   !live/slate/
   !live/answers/
   !live/archive/
   !live/inbox/
   !live/text/
   !live/state.json
   !live/turns.jsonl
   ```

   `!live/text/` is there because the per-question typed drafts are transcript too.

6. **Somewhere for finished work** — a `handwritten/` folder, a `notes/` directory, whatever fits.
   The board hands the assistant a path to each slate page; where it should be filed afterwards is
   the repository's business, and `AI_INSTRUCTIONS.md` is where you say so.

**Nothing about pushing.** `board/scripts/save-and-push.sh` is the only copy and it takes its
repository from the working directory, so a new workspace needs no push script of its own — `⤓
save` and `board push` both reach the same one.

**And nothing about other people's slides.** `/courses/**/lectures/*` and
`/courses/**/assignment/*` in the root `.gitignore` reach a course the moment it exists, and
`test/tracked.py` refuses either from the index for every course rather than the one they were
found in. So the professor's decks and the assignment sheets go on disk, a `.gitkeep` holds each
directory open, and there is no per-course rule to write.

### Shipping a change

```
bash scripts/ship.sh ["message"]
```

Commit, push, and put every course on the new code in one act — because they are one act. A
board and a tutor read `serve.py` and `bin/tutor` once, when they start, so changing this
repository does nothing to a course already running: the pages come from disk and look new
while the endpoints and the daemon behind them are the old ones.

If the push fails, nothing is restarted. Running processes stay on the old code, which is the
right place for them while the change is not saved anywhere.

The commit is authored by whoever `git config user.name` says — no trailers, no co-authors, no
attribution to any assistant.

### Changing the tool restarts the boards

A board is a long-lived process that read `serve.py` when it started, so a change to the tool
does not reach a course until its board comes back. The pages are served from disk
and look new while the endpoints behind them are still the old ones — a difference that is
invisible from the outside and costs an evening to find. It cost one here.

So `board/scripts/save-and-push.sh` runs `tutor restart` after a push whose commit touched
`board/`:

```
tutor restart              restart every board running on this machine
tutor restart --tutors     and the headless tutors attached to them
```

A tutor in the middle of a turn is left alone: bouncing it loses the card it is writing, and
the student is who pays for that. Otherwise it is stopped with `SIGTERM` — which is what starts
the wrap-up turn that writes `HANDOFF.md` — and the restart waits for that to finish before
starting the next one, so the continuity is written rather than merely a process killed.

It only touches boards that are genuinely answering **on this node** — a record on a shared
filesystem may belong to another machine, and stopping a stranger's process is worse than
leaving a stale one. A course pushing its own work does not do this; only the tool does. A
failed restart never fails the push.

## Commands

The assistant runs these. The student never does.

```
board start                      # bring the board up
board net                        # every address it answers on, tailnet included
board init "Course"              # name this repository, so the directory is not used
board finish                     # offer the push, on the iPad
board push "message"             # or just do it
board eyes                       # can the assistant driving this see images?
board see <path> [--page N]      # what is in it, in words, when it cannot
board open "Galois Theory" "Ch 7 — Splitting fields"
board next lesson splitting-fields   # -> live/cards/0001-splitting-fields.md
board brief                      # the standing rules, in one call: the method, this
                                 #   course's unbendable rules, the handoff, the note
board direction --show           # what this work is FOR, when they have changed it
board aim                        # what THIS SITTING is for, and whether it was chosen
board aim build                  # change it in place; nothing is archived
board recap                      # the lesson so far, in one call
board note < note.md             # <=120 words for the next turn (a turn is a session)
board handoff < handoff.md       # HANDOFF.md at session end, <=350 words. Capped.
board inbox                      # what the student sent back, with file paths
board slate                      # just the pages written on the iPad
board wait --timeout 300         # block until the student sends something
board export                     # the whole conversation, as transcripts/<lesson>-vN.pdf
board export --all               # every lesson in the course, as one document
board hw                         # this sitting's problem set: what is still empty
board hw build                   # compile it; the result lands on the board
board hw file 7.2                # file a sent page into the set's handwritten/
board review list                # everything this repository can be reviewed over
board review over ch01 ch07      # what a test review covers
board walk list [dir]            # every file a walkthrough could be held over
board walk over psych_asr.transcript.render.render
                                 # what this walkthrough covers
board open "PSYCH-ASR" --walk --over psych_asr.transcript.turns
board open "PSYCH-ASR" "the grid sweep" --stance do   # this sitting only
board vpn up|status|serve|down   # the Tailscale link
board doctor                     # is this machine equipped, and who teaches on it
board limit                      # has the tutor's allowance here run out
board stop
board <command> --help           # what that one command is for, off its own docstring
```

**`--help` on a subcommand is answered by the dispatcher, before the repository is even
found.** `board write --help` used to reach `cmd_write`, which drops anything that looks
like an option, read an empty body off the terminal and put a **blank card on the lesson**
— pushed to every device, in the transcript, with no undo. Somebody finding out what a
command does must not be able to damage a sitting by asking. Only in the first position:
further along it may be the value of an option, and guessing which turns `--title --help`
into a help screen instead of a card.

## Writing a card

The assistant writes card files; that is the entire authoring interface. A card is markdown with
a small front matter block:

```markdown
---
kind: question
title: Which subfield is fixed?
---

Take $L = \QQ(\sqrt[3]{2}, \omega)$ and the subgroup $H = \gen{\sigma}$ of order 3.

Which of the three intermediate fields is $\Fix(H)$, and why can it not be
$\QQ(\sqrt[3]{2})$?
```

`kind` is one of `lesson`, `question`, `correct`, `wrong`, `review`, `note`, `recap`. It only
changes the label and the accent colour; `question` is the one that says *your move*.

### The shape of a card is a door, not a request

**`board write` refuses a card over 450 words, and one carrying a single paragraph over 110.**
Nothing is written and the turn writes it again, shorter. Asked for as *"all tutor responses
should be EASY to read. I never want to face a wall of text"*, and made a door rather than a
line in a prompt for the reason `HANDOFF.md` reached 3,824 words against a documented cap of
350: a prompt is a preference, every edit is reasonable on its own, and nobody notices for a
fortnight.

Two shapes, because either one alone lets the other through. Past the word count the card is a
document, and a document belongs in a file the board can open. Under it, one unbroken block is a
grey rectangle on a tablet held at arm's length — four hundred words in nine paragraphs reads,
two hundred in one does not.

**What is not prose is not counted**, so nothing has to be mangled to get under the cap: a fenced
code block, a displayed equation and a table are as long as the thing they describe, and a list
is counted line by line — which is exactly what a self-contained problem card, carrying every
definition it uses, is made of. `--force` writes it anyway, for the card that genuinely has to be
that long.

The numbers live in `tutorboard/plain.py`, and the briefing quotes them from there, so a turn
knows both before it hits either. `test/plainly.py` holds the door and, just as importantly,
holds it open for the things that must never be refused.

Mathematics is written in ordinary LaTeX, `$…$` and `$$…$$`, using the same macro vocabulary as
the course repository's `latex/coursemacros.sty` — `\QQ`, `\degree{L}{K}`, `\GalG{L}{K}`,
`\Fix`, `\minpoly{\alpha}{K}`, and the rest. See `web/macros.js` for the full list.

### Diagrams

KaTeX cannot draw a subgroup lattice. Anything in a `tikz`, `tikzcd`, or `latex` fence is compiled
by real LaTeX to an SVG, cached by content hash, and dropped into the page:

````markdown
```tikzcd
& L \arrow[dl, dash, "2"'] \arrow[dr, dash, "3"] & \\
\QQ(\sqrt[3]{2}) \arrow[dr, dash, "3"'] & & \QQ(\omega) \arrow[dl, dash, "2"] \\
& \QQ &
```
````

The first render of a new diagram takes a second or two and shows a placeholder; every render
after that is instant. Blank lines inside a fence are stripped, because a blank line inside a
`tikzcd` is a paragraph break and TeX will not have it.

## The slate — writing by hand

The writing surface is **part of the lesson**, not a panel over it. A question puts an answer
block into the card flow directly beneath itself, always the same generous size, and the drawing
tools appear in the page's own chrome bar beside the type-size and theme buttons — they belong to
the app rather than floating on top of it. Nothing to drag, nothing to discover, nothing covered. `/slate` is the same component full-screen, for a derivation that wants the whole page.

Every control is named — Pen, Marker, Erase, Select — because an icon alone was not legible, and a
control you cannot identify is worse than no control. Labels drop on narrow screens in the order
that costs least: nib sizes first, the four tools last.

Strokes are captured as pointer events with pressure. Once a pen has been seen, finger touches
stop drawing, which is the whole of palm rejection.

**Paper is dark by default** — chalk on slate, unruled. The `paper` button cycles black, white and
cream; `plain` cycles unruled, grid and lines. The ink palette follows the paper, so the default
colour is always one you can see, and the last swatch is a colour picker for anything you like.

**A fresh page is exactly the size of the surface showing it**, so one logical unit is one CSS
pixel and 100% is already the right size to write at — on a phone, an iPad or a large display.
Zoom exists for when you want it, not because the page arrived the wrong size. The earlier design
used a fixed 1600-unit page scaled to fit, which made writing small on a small screen and left
zooming as the only remedy; `test/sizing.js` sweeps seven screen shapes and fails if any of them
opens at anything but 100%.

Ink smoothness is deliberate work, not a default. Raw pointer samples are jittery and unevenly
spaced, and drawing them directly is what produces a granular, faceted line. Instead each sample
is blended into the last, a Catmull-Rom curve is run through the result, that curve is resampled
to about a pixel of spacing, and the width varies smoothly along it. Committed strokes are cached
to an offscreen canvas so only the live stroke is redrawn per frame — latency is most of what
"smooth" actually means.

Each page is saved twice: `live/slate/page-NN.json` holds the strokes as vectors, so the page
survives a reload and reopens on any device; `live/slate/page-NN.png` is what the assistant opens
and reads. **`NN` is the page's identity, not its position** — it is carried by the page from the
moment it exists and is what every save addresses. That sounds like pedantry and is not: a file
appears only when a page is saved, so a page cut and never written on leaves a GAP, and a surface
that addressed pages by where they sat in the list it got back wrote each one over its neighbour
after every reload. See 3 September 2026 above for the wreckage. The PNG is exactly what you see, paper colour included — inverting it would wreck a
colour you chose on purpose. Autosave runs about a second after the
pen lifts. **Send** — always visible, outside the scrolling tool strip, because a Send button you have to
scroll sideways to find is a Send button that does not exist — puts the page in the inbox and
tells the assistant to look at it. The **live**
toggle does that automatically whenever writing pauses, at most once every fifteen seconds — that
is the mode for being watched while you work.

### The surface is a plane, not a page

A page is not a box. A box created at the size of the surface showing it, clamped
so the view can never leave it and enlarged only by a *taller* button, means
running out of room in the middle of a derivation and finding a hard edge one
screen away in every direction.

Panning is clamped to the *ink* instead — whatever has been written, plus a
viewport of clear space beyond it, in every direction including above and to the
left of the origin. Write into that space and it moves outward again. There is no
edge to reach, and no **taller** button, because there is nothing to enlarge.
Zoom out reaches a twelfth of fit scale rather than a half. **⤢** now means *show
me everything I have written*, which on a plane is not the same as *fit the page*.

The clamp still exists, deliberately: a stray pinch cannot fling the surface into
empty space a mile from the nearest word, which is how an unbounded canvas
usually goes wrong.

**And it costs nothing to hand in.** What the tutor is sent is a picture of the
writing, not of the plane: the image is cropped to the ink, padded, and then
scaled down if it is still large (2000 px on the longest side). Cost is
proportional to how much was written rather than to how far the canvas reaches —
the same three lines of algebra export to the same ~700×400 image whether the
plane around them is 800 units across or 8000. Rasterising the whole page at one
pixel per unit is survivable only while the page is the size of the screen.

The surface also breaks out of the reading column. `#board` carries a 46rem
measure because prose needs one; sharing it made the writing area about half an
iPad in landscape. Cards keep the measure, the surface bleeds to the width of the
device (capped, so a large display does not get an absurd one), and its height is
`74svh` — `svh` rather than `vh`, because on iOS `vh` is the tallest the viewport
ever gets and anything sized in it spends its first screenful under the browser
chrome.

### A finger is not a pen

**A latch cannot decide this.** *A finger draws until a pen has been seen, and
after that a finger is a palm* is a variable, so every reload hands the first
swipe to the ink — and it leaves somebody with no stylus no way to say so.

It is a setting, in the **⋯** menu under **Finger**: *scrolls* (the default)
or *writes*. Remembered per device in `localStorage`, because it is a property of
how you work and what is in your other hand, not of a lesson. The lesson's
annotation layer reads the same setting — it had its own copy of the old latch, so
the two surfaces disagreed about the same hand.

With a finger set to scroll, one finger pans, two pinch, and the pen writes.
Anything the hand does is ignored for half a second after the pen last reported,
which is what palm rejection actually is: without it, the heel of a hand resting
on the glass drags the canvas out from under the nib mid-word.

**THE PEN LATCH IS ABOUT A NIB THAT IS DOWN, NOT ONE THAT IS NEAR.** An Apple
Pencil hovers — within about a centimetre of the glass it reports `pointermove`
with nothing touching anything — so a latch refreshed on every pen move is a
latch held open for as long as the pencil is in somebody's hand, which while
annotating is the whole time. A stroke in progress is the whole of the test.
`test/link.js` drives a hover and fails if the scroll closes.

**AND IT IS ABOUT A PAGE THAT IS MOVING, SO ITS WINDOW RUNS FROM THE LAST
SCROLL.** Nib down shuts it; with the page standing still it opens on the *lift*;
only a page that has scrolled inside 700 ms holds it shut. A stroke can only be
re-read as a pan during a fling — `preventDefault` on `touchstart` is refused
then and honoured at every other moment, and `onTouchStart` already makes it for
a stylus — so with the page still there is nothing for the CSS to add. Measured
from the last *sample* instead, the latch ate the first swipe after every mark:
`touch-action` is read when a gesture STARTS, so opening the latch on that
finger's first `touchmove` is already too late for the gesture that opened it.
That is the fourth report of *"I could not scroll when I started annotating"* and
the first one settled off a trace. `penLift` is why the lift asks at all: `penSeen`
arms one timer per stroke and never re-arms it, so a short stroke used to leave
the latch shut for the rest of a window that began before it. `latchFlow` in
`test/link.js`.

**AND A STROKE THAT NEVER ENDS REFUSES EVERY SCROLL ON THE PAGE.** The
non-passive `touchmove` listener is on the *document* and exists only while a
stroke is being drawn — that is what keeps scrolling smooth — so *a stroke is in
progress* is the whole of what cancels a pan, everywhere, not just over a card.
A lift that goes missing therefore latches the lesson shut for the rest of the
sitting. Every rescue for a missing lift is filtered by `pointerId` — the window
`pointerup`/`pointercancel` pair, `blur`, the next `begin` — and `mine` is right
to refuse a foreign one, because a second contact must not end the pen's stroke.
So the floor is **silence**: `STROKE_QUIET`, a mark every sample moves forward,
ends a stroke nothing has been heard from and keeps its ink — one timer per
stroke rather than one per sample, the shape `penSeen` already uses, because a
pencil reports at 240 Hz. It is four seconds on
purpose — a nib held motionless mid-word sends nothing, and cutting a stroke in
two is a real cost where a latch nobody can clear is the whole fault. **Leaving
the mode also finishes what is in hand**, which it did not: `setOn(false)` dropped
the latch and disarmed both listeners and left the stroke open, so 'done' looked
like a fix and half of one is what made this visible exactly once per sitting.
**AND THE LAYER SAYS WHAT IT DID.** Scrolling while annotating has been reported
three times and diagnosed twice, and the second diagnosis was wrong — because
`☰ → what just happened` carried every card and every animation and **nothing at
all about the ink layer**, so a report that arrives as *"I couldn't scroll when I
started annotating"* was answered by reading the source and guessing. Six lines
now: `ink-mode` (entering or leaving, how many layers, and how many milliseconds
the restyle cost — `body.annotating` restyles every card in the lesson and
`armTouch` installs a **non-passive** `touchstart` in the same breath, which is a
promise that the main thread will be consulted before any gesture may scroll, so
that restyle is paid for by whoever touches the glass next); `ink-begin` and
`ink-end` with the card and the pointer, so a stroke that never ended can be told
from one that never began; `ink-hold` every time a gesture is refused, which is
the sentence *I could not scroll* written down at the moment it is true;
`ink-late` where the browser had already decided and did not ask; `ink-latch`
when the CSS half goes on or off, **with `why`** — `quiet` for the window
expiring, `moved` for a finger that dragged it open, `off` for leaving the mode;
and `ink-pan`, a finger landing against a shut latch, which is the one refusal
made in CSS and so the one that leaves no event of its own. The last two are
there because the fourth report was diagnosed by arithmetic across three
timestamps rather than read off a line. `test/link.js` asserts each one reaches
the log.

**Read `ink-late at=touchmove` as a pair, not a line.** Following an
`ink-hold at=touchstart` it is not a page that moved: it is one non-cancelable
first move per stroke, because `armMove` installs the non-passive `touchmove`
inside `begin` and the compositor learns about it a move later.

`window.BoardTrace` is how the layer says so — `☰ → what just happened` carries
an `ink-drop` line, because this arrives as a sentence about scrolling and
nothing in it can name a stroke.

### What the slate can do

Strokes are stored as vectors rather than pixels, which is what makes the editing possible.

- **Tools** — pen, highlighter (translucent, multiply-blended, always painted under the ink),
  stroke eraser, and lasso.
- **Lasso and clipboard** — draw a loop around anything to select it, then drag it to move,
  cut, copy, paste, duplicate, recolour, or delete. A stroke has to be more than 60% inside the
  loop to be caught, so clipping the edge of a neighbouring symbol does not drag it along.
  Choosing an ink while something is selected recolours it. ⌘/Ctrl with Z, X, C, V, D work, and
  so does Delete.
- **One clipboard, everywhere** — what is copied here can be pasted onto the other writing
  board, onto the full-screen slate, or onto the tutor's own cards, and marks copied off a card
  can be pasted here. See [One clipboard, three surfaces](#one-clipboard-three-surfaces).
- **Six inks, three nibs**, pressure-sensitive width.
- **Zoom and pan** — pinch to zoom, one finger to pan, trackpad pinch on a laptop. The pen always
  writes; whether a finger does is a setting (**⋯ → Finger**), and touch is ignored for half a
  second after the pen last reported, which is the whole of palm rejection. Panning is clamped to
  the ink and the space around it, so the surface cannot be lost off-screen.
- **Pages**, for starting somewhere clean. A page no longer has to be made taller — it is a
  plane, and it grows into whatever you write on it.
- Grid, ruled, or blank paper. Undo is 60 deep and covers selection edits, not just strokes.

### One clipboard, three surfaces

Ink copied on any writing surface can be pasted on any other. There are three of them — the
drawer under the question, the full-screen page at `/slate`, and the layer over the tutor's own
cards — and until now each had a clipboard of its own, which is the same thing as having none:
copying put ink in a bucket nobody else could see.

| from | to | how |
|---|---|---|
| writing board | the other writing board, or another page of the same one | lasso, **Copy**, then **Paste** on the other |
| writing board | a card in the lesson | lasso, **Copy**, then **✎ annotate → Paste** |
| a card in the lesson | a writing board | **✎ annotate → Select**, loop, **Copy**, then **Paste** on the board |
| a card | another card | **Select**, loop, **Copy**, then **Paste** with the pen on the other card |

A clip is kept in CSS pixels with its own corner at the origin, which is neither surface's own
coordinates: the board stores strokes in logical page units and a card stores them as fractions
of *that card*, because a lesson reflows and ink about a word has to move with the word. So a
mark keeps the size it looked on the glass when it crosses between them, and is shrunk only if
it arrived from somewhere with more room than it is going to — a ring the width of the reading
column, dropped on a surface zoomed into one line of algebra, would otherwise be a mark whose
ends are off the screen.

Where a paste lands is the other half of the same thought. A **duplicate** — copy and paste on
the same surface — lands beside the original, under the hand that will drag it. Anything from
somewhere *else* has coordinates that mean nothing where it is going, so it lands in the middle
of what is on screen, or in the middle of the visible part of the card, and stays selected so it
can be dragged where it is wanted.

It is also written to `localStorage`, because the one journey that is not between two live
surfaces is opening `/slate` — which is a navigation, and took the clipboard with it. The
ceiling is 300 KB on disk and about sixty thousand points in hand; over the first a clip still
pastes in this tab and does not survive a navigation, and over the second the copy is refused
and says so. The app's own cache lives in the same storage allowance, and a clipboard is ink
somebody is carrying for the next few seconds.

The highlighter does not cross onto a card. A card's layer has one kind of mark — a pen line,
over words — and a highlight arrives as a line in its own colour, which is the nearest true
thing. `test/clip.js` drives all four directions in a real DOM.

### What it deliberately cannot do

It does not recognise handwriting. Turning ink into text, or into LaTeX, needs a trained
recogniser — the apps that do this well license an engine built for the purpose, and it is not
something a canvas and a few hundred lines of JavaScript will approximate.

That is a smaller loss here than it sounds, because **the recogniser is the tutor**. Nebo has to
convert your ink into something a computer can act on; this only has to get your ink in front of
someone who reads mathematics. The PNG goes straight to them. Write the way you would on paper.

## The lesson is a transcript

Both halves of the conversation are on the board, in order. A card the assistant writes, then what
the student wrote back, directly beneath the question it answers — not in a drawer.

A **turn** is one contribution from the student. It carries the card it answers, it is frozen at
the moment it is sent (the slate is a working surface and will be written over), and it is
**versioned**: reading feedback and sending a corrected answer supersedes the previous revision *in
place* rather than adding another block at the end. Every revision stays in `live/turns.jsonl`,
which is append-only; only the newest is shown.

That is what makes the loop work. The assistant points at a mistake, the previous answer comes back
under the pen, the student fixes it, and the block updates where it already was.

### A session, and what ends one

| Course | A session is | Ended by |
|---|---|---|
| maths | a lesson, chapter, or homework sitting | `board open`, which files the last one |
| code | a piece of work that got committed | `board push` |

Ending one archives the whole of it — cards, turns and the frozen answers — into
`live/archive/<stamp>-<slug>/`. `board history` lists them; on the board, **◷** in the top bar
opens past lessons and renders one read-only, with everything the student wrote still in it. The
button is hidden until there is something to read.

## What the board is for when the work is code

The work happens in the editor, on the student's own machine. The board is not where code gets
written and never should be — unless the repository declared `"stance": "do"`, which is a decision
made once, in writing.

The board carried three buttons for this once — **Ready to check**, **I need help**, **I'm
confused** — shown only in a `code` course. They are gone with the mode. What says the same things
is the answer panel every course has: a sentence typed, or a page written on the slate, both of
which arrive as ordinary turns and both of which carry the half a tap could not. *Ready to check*
never said what to check or why; *"the recursion is right now but the memo table is still empty on
the second call"* does, and it is the difference between a tutor reading a diff and a tutor
guessing at one.

Turns are recorded like any other, so the transcript of a session is still a record of where the
student got stuck and what unstuck them — and now of what they actually said about it.

**Understanding code that is already written is a different sitting, and it is the one these
repositories mostly need.** See [A walkthrough — code that is already
there](#a-walkthrough--code-that-is-already-there): the student names a file or a function, and
the lesson is a hand trace through it rather than a change to it.

## Getting work back

Everything the student sends lands in `live/inbox/`: typed lines in `messages.jsonl`, files in
`uploads/`, handwriting in `live/slate/`. `board inbox` prints all three with full paths and marks
them read; `board slate` lists the slate pages alone.

`board wait` blocks until something arrives, then prints it and exits. That is the wake-up
primitive, and it is the difference between a session driven from the keyboard and one driven
entirely from the iPad: the student writes, taps send, and the assistant is woken by a process
exiting rather than by anyone typing in a terminal.

## Any agent, not just one

The entire interface is a command line and a directory of files. There is no SDK, no plugin, and
nothing model-specific anywhere in it. Any assistant that can run a shell command and write a file
can drive the board: Claude Code, Codex, DeepSeek, Cursor, a local model behind a terminal
wrapper.

- **To teach:** run `board start`, then write markdown files into `live/cards/`.
- **To listen:** run `board inbox`, or block on `board wait --timeout 300` inside your own loop.
- **To reach the iPad:** `board vpn up`, then `board net`.
- **To read handwriting:** open the PNG that `board inbox` names. This is the one capability the
  agent must supply itself — an agent that cannot look at an image cannot review handwritten
  work, and should ask for a typed answer in the board's text box instead.

### Which one, and who decides

`tutor --agents` is the table. An entry is a **command recipe** — `cmd` for an interactive
session, `headless_first` to open a headless one, `headless` to continue it, `{prompt}`
substituted — so a second model is a second entry whose `cmd` carries the flag. Nothing in
`bin/tutor` knows what a model is.

Five layers resolve it, most specific first, and every one is configuration rather than code:

| | where | what it is a statement about |
| --- | --- | --- |
| 1 | `--agent` on the command line | this once |
| 2 | `agent` in the sitting's `state.json` | this evening's work |
| 3 | `agent` in the workspace's `tutorboard.json` | this workspace, for ever |
| 4 | `hosts` in the config, by hostname | this machine, every workspace |
| 5 | `default_agent` | everything else |

**Layer 2 is the one a tablet can reach**, and it is chosen as a sitting OPENS rather than changed
in place — the *who:* row in the sitting chooser, held like a stance and sent with `/session`. An
aim can change mid-sitting because it changes what the next card is; an assistant changes who
writes it, and the conversation the outgoing one was holding does not transfer. A name at layer 2
that this machine has not got falls back with a line saying so, where the layers below it refuse:
it is the one layer written from a browser, and a misspelling must not leave a course with no
tutor at all.

`⇥ put an assistant to work elsewhere` in the bar menu is the same choice aimed at a workspace you
are **not** looking at: pick one, say what to do, and go back to what you were doing. The list is
`machines.workspaces`, which is a directory walk rather than a registry. The task lands as a turn
of theirs in that workspace's inbox — which is what `board wait` watches — and the start is
`tutor agent start <workspace> --respawn --agent <name>`, layer 1, for that daemon only. The
dispatch is recorded as a mission in that workspace — before the inbox line, because that line is
the waking and `board brief` reads the record to know the turn is a doing one — so the strip says
it is still going and says how it ended; what comes back comes back hours later, on whichever board is open then.

**Naming an assistant where a different one is listening stops that one first.** `agent start` is a
no-op against a live daemon, so without the stop the task would go to whoever is there under a
record naming whoever was asked for — and for colibrì that is the fenced directory's job going to
an assistant that may not read it. The stop is `--wait`, because `missions.holder` names the old
one until its process is gone; a holder still wrapping up when that wait runs out is refused with
*ask again in a minute*, and a start refused after the stop puts the old assistant back by name —
reading the put-back's exit code, because a reply claiming a workspace was restored when it is
empty is worse than one saying it is empty. The panel says who was stopped and who has it now. Naming **nobody** displaces nobody,
and the same assistant already there is left alone — a colibrì preamble costs hours to rebuild.

**`swap_blocked` in the route decides what a swap may take**, and refuses for two kinds of reason.
The stop cannot land: the daemon is attached from another node, and a signal reaches this machine's
process table only. Or the stop would land and take something claimed: somebody's own interactive
sitting, a board a second device has open right now, a daemon mid-turn, a mission running there,
work handed in that nothing has picked up. Each is refused by what it is, never by a command to
type. An idle listening daemon is neither, and that is the ordinary case — it swaps with no tap
anywhere else. **Cards do not block**, because every taught workspace has them.

"Nobody is looking" is the dispatcher's assumption and the board checks it: a visible page posts
`/seen` on a 20-second beat and a hidden one stops, so a marker inside the route's `LOOKING` window
is another device with that lesson open. It has to be NEWER than that workspace's newest card,
because a marker equal to it was written by `news.elsewhere` starting the notification clock rather
than by a browser.

A swap holds the request while it waits — 180 s for the stop, 60 for the start, 60 more for a
put-back — so **the panel says which of the two waits a tap bought and counts the seconds out
loud**. `machines._mark_holder` hangs `holder` on each atlas row, so the row names what is
listening there and the tap reads *stopping claude in PSYCH-ASR, then starting colibri* with the
reason under it: the outgoing daemon writes its handoff, which is a model call. A dispatch that
displaces nobody still reads *starting it…*. The field is **asked for rather than sent** —
`/atlas.json?holders=1` — because it is an `agent.json` per workspace off a shared filer, 37 ms
against 0.4 ms for the rest of a cached payload, and the front door polls the same route every 20
seconds while drawing none of it; the panel re-reads it on every open, because a list read once at
page load is hours old by the evening. Holding the request for minutes is survivable only because
the server is a `ThreadingHTTPServer` and the service worker passes a POST straight through.
`test/elsewhere.py` holds the server half and `test/who.js` the panel.

**`--respawn` on every start into a workspace nobody is looking at** — this route,
`spawn.ship_missions` and `/writeup`. A start records the course somebody named, and the one
address, the next login and every other machine's idea of *the course* follow that record; the
person is still looking at the board they tapped on. A hub tap records, because a hub tap is a
person.

### A workspace that holds a fence

`fenced.holds` walks a workspace one level down and returns the fenced directory names it finds —
`NEVER`, the same list every path check reads. It rides on `machines.workspaces` and on the board's
own payload, so both choosers can say it: the *who:* row names the directories and names the one
assistant that may open them, and `⇥ put an assistant to work elsewhere` marks the row you pick the
workspace from and defaults to that assistant there.

**Visibility and a default, never a refusal.** The fence stops a hosted assistant READING `phi`; it
does not stop one existing, and the teaching thread on this code is a hosted conversation. So every
assistant stays on the row, a tap is honoured, and a pick that is not the reader carries a line
saying what it will not be able to open. The protection stays in `ai-config/policy/phi.py` and in
the walks that refuse a fenced path.

**Who the reader is comes out of the registry**, not out of a name in the browser: it is the recipe
carrying `private`, and exactly one does. A machine that has not got that assistant installed draws
the row anyway and says so — a fenced box with nothing that may read it is the case where the
absence of a choice is the thing worth saying. One level deep is the rule: this labels a workspace
on a chooser, so a `data/` directory six levels down inside a vendored dependency is not a fence.

### The local model

`colibri` is the sixth row and it serves GLM-5.2 int4 from a compute node in this repository; see
`projects/libr-local-llm/README.md` §4c. Three things about it are unlike every other row, and all
three are properties of the recipe:

- **`timeout: 14400`.** The client's preamble is 15,900 tokens and prefill runs at a few tokens a
  second, so a first turn is two to three HOURS before it emits a token. `turn_timeout` takes the
  recipe's number as a floor, so the two numbers about the sitting are unchanged for everybody
  else. Nothing paints a long turn as dead: the daemon's 30-second beat thread keeps the indicator
  green for the whole of it.
- **`exclusive`.** The server runs one KV slot, so a second colibri sitting anywhere on this
  machine evicts the first one's prefix and the first re-pays its whole preamble. Refused by name,
  saying which workspace is holding it. `COLI_KV_SLOTS` is wired through the serve job and the
  engine supports 16; measure what a slot costs at a 131072 window and this becomes a queue.
- **`private`.** It is the only assistant allowed to read `phi`, which is the entire reason it
  exists — so it refuses to open where a card of its own would be committed. `git check-ignore`
  decides, per workspace, and the refusal names the one line that changes it. `research/PSYCH-ASR`
  excludes `live/*`; `courses/Galois-Theory/live/cards/` is in the pushed history.

The server is a Slurm job and starting one is not something a request can wait for — an
allocation, a 429 GB load and a warm-up generation is over an hour on a cold node and can pend
indefinitely behind an 800 GB ask. So the *who:* row says which of four states it is in and
offers to start one: **nothing running**, **queued** (Slurm's own reason), **loading**, **warm**.
`squeue` is the source of truth and nothing writes a state file; the answer is cached for fifteen
seconds, the way `machines.held_nodes` caches its own. The difference between loading and warm
cannot be got from Slurm — the gateway binds its port before it loads anything, so a TCP probe
says nothing — so the job's own lines are read instead: `API listening on`, then
`COLIBRI-SERVE READY` once it has completed a real generation.

**FOUR STATES AND ONE FACT, AND THE FACT IS THE CHAIN.** `coli-up` starts a chain rather than a
job: two hours before its walltime a generation submits the next one, which pins 406.7 GB on
another node while this one goes on answering, and only once it says `COLIBRI-SERVE LOADED` does
the incumbent give its node back. So `squeue` lists TWO generations for an hour at a time. The one
reported is the one that can ANSWER — warm beats loading, and between two warm ones the one with
more walltime left, because that is the one not about to hand over — and the other becomes a
clause on the end of the sentence, which is what makes *the server goes away in twenty minutes*
sayable. Each generation writes its own `colibri_serve_{out,err}-<jobid>.txt`, because one fixed
pair would judge a successor by the incumbent's `COLIBRI-SERVE READY`. The chain is not a fifth
state and the start control is unchanged: under a chain there is always a job, so the control is
simply never offered. `projects/libr-local-llm/README.md` §4c is the design.

## Layout

```
bin/board          the command line (also: tutor)
serve.py           the entry point, and nothing else
TEACHING.md        how to teach on this board -- copied into every course's live/
tutorboard/        the board itself, organised by what a thing is about:
  paths ports      what this machine knows about itself
  choice machine   which course was asked for, and what this machine is
  processes tex    what is alive here, and where TeX is
  limits reasoning what a model may say, and when it may not say it
  handoff sense    what a turn means, and what it leaves behind
  brief carry      what a turn reads before it teaches, and what it tells the
                   next one -- a turn is its own session, so both are files
  machines.py      the other machines, and what each can teach
  news.py          an answer that landed in a workspace nobody was looking at:
                   the newest card against `live/.seen.json`, workspace by
                   workspace, off the shared filesystem
  missions.py      the same sentence in the present tense: a job set going in a
                   workspace nobody is looking at, recorded in the workspace it
                   is about, its ending derived off the newest card and
                   `agent.json` and then frozen into the record
  writeups.py      a paper or a deck asked for from a sitting, which is a
                   PRODUCT rather than an aim: one record per ask, its state
                   derived off `library.stamp` and then frozen, so the board can
                   say a document is being written by a turn that writes no card
  leaving.py       what is about to leave this machine and whether it may: every
                   path a push would commit, checked against the repository's
                   own PHI policy where it sits in a workspace that holds a
                   fence
  net/             reaching them: tailscale, egress
  course/          a course on disk: repo, config, document, homework, review,
                   plan (what a project says it is doing next, which is a book
                   course's chapter table in the form a project has one),
                   reading (the documents it can be SHOWN, as opposed to the two
                   it builds),
                   library (everything the workspace HAS written, grouped into
                   documents by stem and directory, where feedback on one goes,
                   and the stamp that says whether any of it has moved),
                   shelf (the same inventory placed under the boxes of the map,
                   by three rules read off each path, and named by a slug ink
                   can be anchored on),
                   walk (what a walkthrough can be held over: a file, or one
                   definition inside one), syllabus, screenshot, paper (the two
                   documents: resolving one, naming it, and rendering its pages
                   so an iPad can read it)
  lesson/          what is on the board now: cards, turns, notes, slate,
                   archive, state, git, uploads
  server/          app, handler, hub, tikz, spawn, multipart, and routes/ --
                   one module per family of paths
web/               the hub   — home.html, home.css, home.js
                   the board — board.html, board.css, board.js, macros.js, vendored KaTeX
                   the ink layer — annotate.js, over the tutor's own cards
                   the slate — slate.html, slate.css, slate.js
                   the library — library.html, library.css, library.js
                   the app   — manifest.webmanifest, sw.js, icon-*.png (icon.tex makes them)
test/              node test/markdown.js and node test/macros.js
```

Per course repository — the lesson transcript (`cards/`, `slate/`, `answers/`, `archive/`,
`inbox/`, `text/`, `state.json`, `turns.jsonl`) tracked so a lecture is the same whichever
machine picks it up, and everything else here ignored as per-machine runtime state:

```
live/
  state.json       course and chapter labels shown in the title bar
  cards/NNNN-*.md  the lesson, in order
  NEXT.md          <=120 words from the last turn to this one, via `board note`
  cost.jsonl       one line per turn: round trips, tokens, dollars. `tutor cost`
  inbox/           messages.jsonl and uploads/
  slate/           page-NN.json (strokes) and page-NN.png (what the assistant reads)
                   NN is the page's name, not its place in any list
  tikzcache/       compiled SVG, keyed by content hash
  paper/           rendered PDF pages, so a document can be READ on the iPad.
                   Keyed on the PDF's own modification time, bounded to a few
                   page sets, and it carries its own .gitignore -- a course whose
                   minimum is "nothing at all" would otherwise commit it
  archive/         previous lessons, filed by `board open` or `board archive`
  .board.json      which node, which pid, which port
  .seen.json       when a browser last had this workspace open. Written by the
                   page, never by the server: a board goes on running in an
                   empty room. It is what a notification is measured against
```

and one directory outside `live/`, because it is meant to be kept and the rest of `live/` is
runtime state:

```
transcripts/       <lesson>-v1.pdf, -v2.pdf … written by `board export`
writeups/<slug>/   a document a make sitting produced: <slug>.tex, <slug>.pdf,
                   figures/, and feedback/<date>-vN.md — one directory per
                   document, drawn by the library page
```

and one directory at the REPOSITORY root, because what is in it is about every workspace and a
document about five of them filed under one of them is misfiled:

```
meetings/          meeting.tex, meeting.pdf — THE deck, one of it, overwritten
                   meeting.json  which frame is about which workspace
                   marks/p<n>.png  the picture of what somebody drew on a slide,
                   handed to the turn that reads it as a suggested direction
```

---

# Setup, start to finish

This is the whole build, in the order it was done, on a machine with **no administrator rights**.
Everything below lives under `$HOME`. Nothing needs `sudo`; if a step ever seems to, it is the
wrong step.

## 0. What the machine has to have

```
board doctor
```

reports python, `latex`, `pdflatex`, `dvisvgm`, the page renderer, the vendored KaTeX, the node
name, the port, and the tailnet name. What it is checking for:

| Needed | Where it came from here |
|---|---|
| Python 3.7+ | system python3 — standard library only, nothing from pip |
| A TeX installation | TinyTeX in `~/.TinyTeX` |
| `dvisvgm`, `standalone` | `tlmgr install dvisvgm standalone varwidth preview needspace` |
| KaTeX | vendored into `web/katex/`, see step 2 |
| `pdftoppm` (poppler) | `/usr/bin`, where a cluster node has it if it has it at all. Wanted rather than needed: without it — or `pdftocairo`, or Ghostscript's `gs` — a PDF can still be saved to the iPad but cannot be **read on the board**, because the pages are rendered here. `board doctor` says so in as many words rather than leaving it to be found from a panel that will not fill |
| node | only to run the tests |

## 1. The tool itself

```
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git ~/Atlas
bash ~/Atlas/board/install.sh
```

That puts two commands on your path: `tutor`, which starts a session, and `board`, which the
assistant drives.

`install.sh` symlinks `bin/board` into `~/.local/bin`, then reports what is missing and prints the
command that would fix it. It never uses `sudo`, never writes outside `~/.local`, and never
installs anything on your behalf — the TeX and Tailscale steps are printed for you to run.

`bin/board` resolves its own symlink with `realpath`, so the launcher can live anywhere on the
path while the web assets stay next to the script.

A "course" is just a directory with a `live/` folder in it. `board` finds the enclosing repository
by walking up for a `.git` or an `AI_INSTRUCTIONS.md`, so running it anywhere inside a project is
enough. There is nothing to register, and the one file a repository may write — `tutorboard.json`,
from `board init` — is optional: without it the name comes from the directory and the stance is
`teach`.

## 2. Vendoring KaTeX

KaTeX is served from the repository rather than a CDN, so the board works with no internet and
so the iPad app has something to cache. It was taken from the npm tarball rather than by scraping
a CDN file by file:

```
npm pack katex@0.16.11
tar xzf katex-0.16.11.tgz
cp package/dist/katex.min.{css,js} package/dist/contrib/auto-render.min.js web/katex/
cp -r package/dist/fonts web/katex/fonts
rm web/katex/fonts/*.ttf web/katex/fonts/*.woff     # woff2 only; 3.0M -> 1.6M
```

## 3. TeX packages for the diagram pipeline

TinyTeX is deliberately minimal, so the pieces that turn a `tikzcd` fence into an SVG had to be
added:

```
tlmgr install dvisvgm standalone varwidth preview needspace
```

`standalone` crops the page to the picture, `dvisvgm` turns the DVI into an SVG, and `needspace`
is used by `board export` to stop a card's heading from being orphaned at a page break.

The pipeline is `latex` → DVI → `dvisvgm --no-fonts --exact-bbox`, not pdflatex → PDF, because
DVI keeps the geometry `dvisvgm` needs to produce clean vector output with text as paths.

## 4. Tailscale, without root

The board runs on a lab compute node on the institute network. The iPad is not on that network
and never will be. There is no route between them and no administrator rights to make one.

Tailscale's `tailscaled` has a **userspace-networking** mode: it implements its own TCP/IP stack
in the process instead of asking the kernel for a TUN device. That is what makes an unprivileged
install possible.

```
mkdir -p ~/.local/opt/tailscale
curl -L https://pkgs.tailscale.com/stable/tailscale_1.102.4_amd64.tgz \
  | tar xz --strip-components=1 -C ~/.local/opt/tailscale
ln -s ~/.local/opt/tailscale/tailscale{,d} ~/.local/bin/
```

`bash install.sh` prints that same command with the version the index is serving today and the
architecture of the machine you are on, so neither has to be looked up.

### And it keeps itself current

Nothing else on the machine will. No package manager knows this install exists, `tailscale
update` refuses a static build, and there is no administrator to notice — so without this it sits
at the version of the afternoon it was unpacked while the hosted control plane moves on.

`update_userspace` in `net/tailscale.py` fetches the current stable tarball and moves the two
binaries into place. It runs in `vendor/colibri`'s two moments and for the same reasons: `tutor
resume`, which is the one moment a compute node gets, and `tutor pull`, which is what
`tutor-pull.timer` runs daily on a machine that is left up for a week and never has a login.
`scripts/tutor-pull` is that timer's whole script — a stamp, a log and one call — and
`install.sh` links it, copies its units and enables it. The index is asked at
most once a day — four terminals in a morning is four logins — and `tutor pull` forces it, because
that is itself the daily job.

Four things it will not do:

- **Touch a Tailscale it does not own.** Only the copy under `$HOME`. A `/usr/bin/tailscale`
  belongs to root, there is no sudo here, and a second opinion about a root daemon's binary is
  worse than an old one.
- **Restart the daemon.** The binary is replaced with `os.replace`, so a live `tailscaled` keeps
  the inode it opened and goes on serving the tailnet name at the old version; the new one is what
  the next `board vpn up` starts. Taking the address down under somebody holding an iPad is the one
  thing this may not do to repair itself.
- **Install something that does not run.** The archive is unpacked into a temporary directory and
  each binary is run and asked its version before it is moved in — a tarball for the wrong
  architecture unpacks perfectly and leaves a machine with no Tailscale at all.
- **Race the other six nodes.** One home directory, seven compute nodes, every login running this:
  a lock file, stale after half an hour so a node killed mid-download does not stop the next one
  for ever.

`board vpn up` then starts the daemon with:

```
tailscaled --tun=userspace-networking \
           --socket=~/.local/state/tailscale/tailscaled.sock \
           --statedir=~/.local/state/tailscale \
           --socks5-server=localhost:1055
```

The SOCKS5 proxy is not needed for the board, but it is how the setup was *tested* — a request
sent through it traverses the same userspace stack an iPad's traffic does, so it proves inbound
forwarding works without needing a second device.

### Logging in

The daemon starts logged out and prints an authentication URL. Nobody can approve it from the
terminal; a human opens the URL in a browser, signs in to the Tailscale account **the iPad uses**,
and presses Connect.

```
board vpn up          # prints the URL if not linked
board vpn status      # "Log in at: https://login.tailscale.com/a/…"
```

If the tailnet has device approval switched on, the machine also has to be approved under
Machines in the admin console.

### The node is named `board`, not after the machine

This is the part that is easy to get wrong, and it was gotten wrong first.

A cluster hands out whichever node is free, so the board runs on `node-a` today and
`node-b` next week. Registering as `node-a-board` would mean the address changed every
time — and the installed iPad app has exactly one origin baked into its home-screen icon, so a
changed address breaks it silently, days later.

The fix: Tailscale's state directory lives in the **shared home**, and the node registers as plain
`board`. Same state, same node key, same identity — one machine that happens to move, exactly like
a laptop changing networks. `https://board.<tailnet>.ts.net/` is the address forever.

Two hazards come with that, and the tool closes both:

- **One node at a time.** Two daemons sharing one state file would fight over the same node key.
  `board vpn up` refuses when another node holds the link, recorded in
  `~/.local/state/tailscale/owner.json` — and clears that record automatically when the recorded
  node no longer appears in `squeue` for this user, which is the usual reason it is stale.
  `--force` overrides.
- **A pid on a shared filesystem means nothing.** `live/.board.json` records the node name as well
  as the pid, and `board start`, `stop`, and `status` compare the node before trusting the pid.
  Without that, `board stop` from a different machine would signal an unrelated process that
  happened to have the same pid number.

### HTTPS

```
board vpn serve
```

puts a real Let's Encrypt certificate on the node's `*.ts.net` name and proxies it to the current
board. It needs certificates enabled once for the tailnet: admin console → **DNS → HTTPS
Certificates → Enable**.

This is worth the step rather than optional decoration: HTTPS makes the page a *secure context*,
which is what a service worker requires, which is what makes the installed app open instantly and
survive a dropped link instead of showing a blank screen.

Each repository has its own port, so `board start` re-points the proxy automatically. Switching
from Galois theory to probability changes what `https://board.<tailnet>.ts.net/` serves without
changing the address.

## 5. The iPad app

The board is a progressive web app: `web/manifest.webmanifest`, an icon, and `web/sw.js`.

The icon is rendered by TeX — `web/icon.tex` draws a chalk ∑ on slate with TikZ, `pdflatex` makes
a PDF, and `pdftoppm -scale-to N` rasterises 180, 192, and 512 pixel versions. Full bleed, no
rounded corners, because iOS applies its own mask.

Three files have to be served from the site root: `/manifest.webmanifest` and `/sw.js` (a service
worker's scope is its own directory), routed in `tutorboard/server/routes/pages.py`, and
`/apple-touch-icon.png` (where iOS looks), routed beside the other root pages in
`tutorboard/server/handler.py`.

The service worker caches the shell — HTML, CSS, JS, icons, KaTeX fonts — and **nothing live**.
The SSE stream, the board payload, uploads, slate saves, and compiled figures go to the network
every time. A cached lesson is a stale lesson, which is worse than a blank screen. Bump `VERSION`
in `sw.js` whenever a shell file changes.

Install it: open the board in Safari → Share → **Add to Home Screen**. It gets its own icon,
launches without Safari's chrome, and long-pressing the icon offers **Slate** as a shortcut
straight to the writing surface.

---

# Networking: reaching it from anywhere

`board net` prints every address the board currently answers on, in the order worth trying:

```
on this machine
  http://127.0.0.1:8787/
on the local network  (--lan was given; there is no authentication)
  http://192.168.1.24:8787/
over tailscale — from anywhere, on any of your devices
  this address does not change when you move to another compute node
  https://board.<tailnet>.ts.net/       <- open this on the iPad
  http://board.<tailnet>.ts.net:8787/
  http://100.x.y.z:8787/
```

Each repository gets a stable port derived from its directory name, so two courses can hold boards
at the same time. `board start --local` binds to loopback only, for use over an SSH tunnel or VS
Code's port forwarding.

## Security — read this before exposing it

**There is no authentication of any kind.** Anyone who can reach the port can read the lesson,
post to the inbox, upload files, and switch which course is being served. That is a deliberate
trade for a personal tool, and it means the network boundary is the only boundary.

What the code does to keep that honest:

- **It binds to loopback by default.** `board start` listens on `127.0.0.1` only. Opening it to
  the local network takes an explicit `board start --lan`, and `board net` says so when you have.
- **Tailscale needs no exception.** `tailscale serve` proxies from the tailnet to `127.0.0.1`, so
  the board stays closed on every other interface while remaining reachable from your own devices.
  This is the intended way to use it remotely.
- **Uploaded files are served inert.** Anything a person uploaded comes back with
  `X-Content-Type-Options: nosniff`, and anything that is not a plain image or a PDF is sent as
  `application/octet-stream` with `Content-Disposition: attachment`. Without that, uploading an
  `.html` or `.svg` file would put chosen script on the board's own origin.
- **Request bodies are capped** at 64 MB, and slate page numbers, upload names, figure hashes and
  static paths are all validated or sanitised rather than trusted.
- **`/switch` only accepts a workspace the server already discovered** by walking the
  repository's families, and the root comes off that match. Paths from the request never reach
  the filesystem.

What it does **not** do, and you should assume it never will:

- No TLS of its own. HTTPS comes from `tailscale serve`, or from a reverse proxy you put in front.
- No user accounts, no sessions, no CSRF tokens, no rate limiting.
- `/switch` can start a process. On a tailnet of your own devices that is a feature; anywhere else
  it is a hole.

**Do not put this on a public interface.** Loopback plus Tailscale, or loopback plus an SSH
tunnel. If you need it on a LAN you share with anyone, put an authenticating reverse proxy in
front of it.

## The `hidden` attribute needs help

Every element the scripts toggle with `hidden` — the drop overlay, the scratch drawer, the slate's
prompt bar — is also given a `display` by a rule of its own. A user-agent stylesheet's
`[hidden] { display: none }` loses to *any* author rule that sets a display, whatever its
specificity, because author origin outranks user-agent origin. Without a guard those elements are
painted permanently.

Both stylesheets carry `[hidden] { display: none !important; }` and `test/hidden.js` fails if
either loses it. Without it an author rule that sets a `display` wins, and the symptom — an
overlay painted permanently over the lesson — reads as a caching or an iOS-resume problem to
anyone who has not read the CSS.

## If the app looks stale or stuck

**Swiping out of an installed iOS app and back in does not reload it.** It resumes: the document
is restored from memory and no script re-runs, so a fixed bug stays on screen and new code never
executes. This is the single most confusing thing about the platform and it is worth knowing
before it costs an hour.

To actually reload, in rough order of effort:

1. Tap **↻** in the title bar. It exists because a standalone app has no browser reload button,
   and without it there is no way out from inside the app.
2. Force-quit: app switcher, swipe up on the card, reopen.
3. Delete the home-screen icon and Add to Home Screen again — this also drops the service worker's
   cache.

The app also asks the service worker for an update every time it returns to the foreground, but a
new worker is never taken while you are looking at the page: the board offers it in a strip with
**load it now**, and both pages take it on their own the moment the app is put down with no ink
owed — so the fix is already there the next time you pick it up. The `controllerchange` handler is
guarded on there having been a controller already, or the very first visit would reload itself.

Nothing is cached by the browser except what sits under `/static/katex/` and `/static/fonts/` —
the KaTeX CSS and JS as well as its faces — along with the app icons and compiled figures, all of
them `public, max-age=86400`, while HTML, the app's own CSS and JS, and `sw.js` go out
`no-store`, and the service worker is network-first for the shell. A re-vendored KaTeX therefore
survives a force-quit for a day. Bump `VERSION` in `sw.js`
whenever a shell file changes, so the old cache is evicted rather than merged. There is never a
need to revisit the original link.

One iPadOS quirk worth knowing about, since it produced a real bug: the system raises `dragenter`
on the page for gestures that are not file drags — the app-switcher swipe among them — and does
not reliably raise the matching `dragleave` when the gesture ends outside the page. Anything keyed
off those events needs a files-only gate, a watchdog, and a reset on `visibilitychange`. The drop
overlay is also `pointer-events: none`, so if it ever does stick it is cosmetic rather than a wall
across the lesson.

---

# What is verified, and what is not

Run before committing:

```
node test/markdown.js    26 cases on the markdown renderer, including the math-safety ones
node test/macros.js      every KaTeX macro, plus real formulas from both courses
node test/hidden.js      that `hidden` elements are actually hidden
node test/pages.js       every page's script runs against its own markup
node test/modes.js       that the answer panel is one, and the signals stay in code
node test/half.js        which half of that panel a question opens on, and that a new
                         typed box is empty
node test/typeface.js    that the reading face reaches prose and never the maths
node test/interactive.js drives the real board in a real DOM and writes on it
node test/sizing.js      that every screen size opens at natural writing size
node test/link.js        that an unreachable board says so instead of looking empty
node test/theme.js       that the dark theme reaches the whole window, not just the content
node test/shot.js        that the photographed lesson is the lesson, and nothing else is
node test/sheets.js      that a slate page is addressed by its number, so a gap in the
                         numbering cannot slide every board onto its neighbour's sheet
node test/hanging.js     that the board has words for every state a reader can be stuck
                         in -- a tutor waking, a turn that failed, nobody attached
python3 test/shot.py     that the photograph becomes a PDF that actually opens
python3 test/waking.py   that a tutor coming up says so, and that work handed in is
                         never answered by silence
python3 test/annotate.py that marks on a card are anchored to it and can be sent
python3 test/begin.py    that the first turn of a session can come from the device
python3 test/homework.py that a sitting finds its problem set, in either layout
python3 test/paper.py    that both documents can be READ on the board and SAVED off it,
                         at any moment -- the pages rendered, counted, cached against the
                         PDF's own timestamp and re-drawn after a rebuild; a machine with
                         no renderer degrading rather than showing an empty panel; and,
                         by reading the client, that the write-up's record reaches the
                         banner from the payload rather than being invented for one frame
python3 test/shelf.py    that every document is under the box its source lives in, that a
                         source is listed with the PDF its build wrote, and that no id
                         moves when a file is added beside it
node test/shelf.js       that the count on a box opens that box's documents, the one on
                         the map bar opens all of them, and a document read from either
                         keeps the marks drawn on it
python3 test/teaching.py that the teaching method reaches every course
python3 test/choice.py   that the address opens the course a person chose
python3 test/limit.py    that an allowance running out is reported rather than hidden
python3 test/egress.py   that a provider which cannot answer from here stands aside before a
                         turn is spent on it, that the reason reaches the glass, and that a
                         message taken from the inbox is owed until something answers it
python3 test/seeing.py   that no card is written off a page a model never saw: the code
                         printed in the image has to come back, and the provider's own
                         placeholder for a dropped image is read as the failure it is
python3 test/tokens.py   what a turn is allowed to read, what it must not run, and that
                         what it cost is measured rather than argued about
python3 test/colibri.py  that the local model is a recipe and not a feature: the sitting
                         resolves it, its clock is hours rather than minutes, `squeue`
                         answers which of four states its server is in, and the two
                         refusals fire -- one sitting at a time, and never where a card
                         of its own would be committed
node test/who.js         that who writes this sitting is a choice on the glass, held
                         until the sitting opens, and that a workspace you are not
                         looking at can be handed a job

bash test/all.sh         all of the above, in order, and Paper-Writer's 593 tests
                         where it is checked out. The two real-DOM suites need
                         jsdom; this fetches it on first run and carries on
                         without it if there is no network. A setup step someone
                         has to remember is a setup step that does not happen.
python3 tools/sync-macros.py --check   that TeX and KaTeX know the same commands
./install.sh             re-runs the environment check
board doctor
```

`test/markdown.js` matters more than it looks. The renderer parks math and code before any
markdown parsing and restores it afterwards, because otherwise a subscript or an asterisk inside
`$…$` gets eaten by the emphasis rules. Every change to it needs a case proving that still holds.

Confirmed by actually exercising it:

- TikZ fences compile and cache; the exported lesson typesets as a PDF.
- A compiled write-up comes back off a real board as an attachment named for its course, and
  its pages render to legible PNGs through `pdftoppm` — checked by looking at one.
- Slate ink round-trips: strokes in, PNG on disk, opened and read.
- `board wait` blocks and wakes on a send.
- Inbound over the tailnet works in userspace-networking mode, checked through the SOCKS proxy.
- The `ts.net` certificate validates, so the page is a secure context.

Not verified by anything automated: **how the pages look and feel**. There is no browser on the
compute node. Type sizes, spacing, the smoothness of a Pencil stroke, whether palm rejection
actually rejects a palm — those are only ever confirmed by opening the thing and using it. A test
suite cannot tell you the type is too small.
