# HANDOFF — the iPad is where the work is directed from

**The aim is one sentence and it is a test: the only reason to open the laptop is
to type code a card told you to type.** Everything else — choosing what a sitting
is for, choosing who writes it, starting the local model, putting a workspace to
work, reading a document, marking it up, complaining about it — is a tap.

**Most of the pieces are in and none of them has been used in anger.** A document
can be asked for from any sitting at all — about a box, a chapter or the evening
that has just been taught — written up, listed, read on the glass, marked up,
complained about in words or in ink, corrected or overhauled by whichever
machinery made it, and re-drawn in front of you where you were reading it, with
what each round changed readable on the glass. The response itself carries the
verdict as a band — green, red, or the amber of a reply that is neither — with a
run of right answers saying how many, and every attempt they typed is kept. The
local model can be chosen for a sitting, started from the glass, watched through four states, and handed a job in
a workspace nobody is looking at. The front door is four doors rather than a
pinchable grid, and behind a workspace the map opens to the module and to the
class or function inside it — with the arrows rolled up to whatever depth is
showing, and a box a pattern found rather than a parser saying so. A vendor tree
is drawn on that same surface and traced from it, in the workspace that is
reading it. And a sitting belongs to a box on that map: one opened without a box
says so and asks for one, and one working in a box stops at the boundary and
hands the work to the next box as an address you tap.

**What is left is two things, and both of them are the iPad's** — one dispatch
and a list of evenings. Nothing left here is a keyboard's.

`board/README.md` is the architecture. This file says what is left.

---

## How to work from this file

**ONE ITEM PER SESSION, AND THE ITEM COMES OUT OF THIS FILE WHEN IT IS DONE.**
Nobody has to ask for that. *"Look at HANDOFF"* means all of it:

1. **Take the lowest-numbered item under *What to do next* that is a build YOU
   CAN DO.** It is the lowest-numbered one on purpose — the numbering carries the
   order things have to land in, and each item says what it depends on where that
   matters. If the owner names a different one, that wins. **Each item's heading
   says whose hands it needs**, and both of the two say the iPad's: item 1 is a
   build that only the person holding it can dispatch, item 2 is a list of
   evenings. **So there is nothing here for a session typing at a keyboard to
   build.** Such a session reads both, confirms nothing has rotted under them,
   and says so rather than inventing work — and if the owner names something
   else, that is the item.
2. **Read that item whole before touching anything.** Each one says what already
   exists (measured, not assumed), what is missing, where it goes, the decisions
   to take deliberately, and what to assert. The decisions are the expensive part:
   several items name a route that is *wrong* to reuse and say why, and taking
   the obvious next line of code instead is how the work gets undone.
3. **Build it, test it, ship it.** `bash board/test/all.sh` green before and
   after, `VERSION` in `board/web/sw.js` bumped if a shell file changed, and
   `ship.sh` / `save-and-push.sh` per the split below.
4. **Then DELETE that item from this file** and write what landed into
   *Settled, so nobody re-derives it* — the rule, not the story, in the tense of
   something that is true now. Renumber what is left. The file is *what is left*;
   an item that is done and still sitting here is the next session's wasted
   half-hour.
5. **Say what was cut.** If part of the item turned out to be wrong, blocked, or
   a bad idea once the code was in front of you, do not silently drop it: leave
   that part in the file with one line saying what blocks it, and take out only
   what actually landed.

An item is not done because its code runs. It is done when the suite is green,
the rule is written where the next turn will read it, and the item is out of this
file.

**One of them is not a build and does not come out this way.** Item 2 is a list
of evenings in front of the thing, and only the person holding the iPad can
strike those.

---

## Before anything

- `bash board/test/all.sh` — 89 suites, about twelve minutes. Green before and
  after.
  The last of them is Paper-Writer's own, run where it is checked out, so the
  factory's tests are part of the board's habit rather than a second one nobody
  has.
- `cd projects/Paper-Writer && python3 -m unittest discover -s tests` — 517 tests,
  about twenty seconds. Still worth running alone while working in there.
- Bump `VERSION` in `board/web/sw.js` whenever a shell file changes. The library
  page is three of them.
- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and
  restarts every running board. Anything outside `board/` — `atlas.json`, a
  workspace's `writeups/`, `projects/Paper-Writer` — goes through
  `bash board/scripts/save-and-push.sh "message" -- <paths>`.
- Commits carry no assistant trailers. `.githooks/commit-msg` strips them.

**A session of its own is live on the serving chain, so leave it alone.**
`tutor serve`, `tutor watch`, `tutorboard/supervise.py`,
`slurm/tutor-serve.sbatch`, `test/perpetual.py` and the `serve_*` keys in
`DEFAULT_CONFIG` are being worked on there. What has landed is under *Settled*
below and in `board/README.md`; what is in flight is in neither, so reading the
code is fine and editing any of those six is how two sessions produce one
conflict. `board/bin/tutor` will move under you either way: pull before you
start, and keep whatever your item needs in there small enough to rebase.
Everything else in the tree is yours. **And that session is owed one line**: the
address block in `watch_once` tests `supervise.answering(port)`, which cannot
tell a serving board from a leftover that is merely alive — see *ANSWERING IS NOT
OWNING* under Settled, where the condition it wants is written out. The half in
`bin/board` is shipped. **The chain is running** while that session
works — `tutor serve status` names the live generation and the successor queued
behind it, and stopping, restarting or resubmitting it is that session's call
rather than yours. This block comes out when that session ships.

**`projects/libr-local-llm` has its own handoff and it is still the live one.**
The five pieces it asked for against the board are shipped and are under
*Settled* below; what is left in that file is the diarization job itself, which
is item 1 here, and nothing else.

---

## The goal, and it is a test rather than a direction

**In the owner's words:** *"When Atlas really gets at a working phase, I should
be able to just work from the iPad, and the ONLY time I should have to hop on the
laptop to code something is if I'm being coach-coded by the tutor, whose
instructions I'd still be reading on the iPad."*

That is checkable, so check it that way: **an evening in which the laptop is
opened for any reason other than typing code a card told you to type is an
evening this failed.** Everything in this section is a thing that still sends
somebody to a keyboard.

**A mission is finished work, and so is a document asked for from any sitting
at all, corrected or overhauled without leaving the page it is on, and so is
which half of the answer panel a question opens on, and so is a response that
types out with the next board waiting for the last character of it, and so is
the whole of that panel: what the box renders while it is being typed in, and
where a sent answer stays once it is sent — and so is the meeting deck, chosen
project by project, read and marked up on the glass, with a mark on a project's
frame becoming that project's next direction — and so, now, is the front door:
four doors rather than a pinchable grid, a family behind each of them, and a
project map that opens to the module and to the class or function inside it —
and so is somebody else's repository, read on that same map and traced from it
in the workspace that is reading it, with nothing handed in to it — and so, now,
is a sitting BELONGING to a box on that map: one that has none says so and asks,
and one that has one stops at the boundary and hands the work on as a tap rather
than an errand — and so, now, is the VERDICT: the response itself carries the
band, amber included, a run of right answers says how many, and the colour and
the mark both survive somebody who has asked for less movement — and so, now, is
the LOCAL MODEL ITSELF, which does not go away at a walltime any more: it moves
node, with the next machine pinned and answering before the last one is given
back — and so, now, is THE WAY IN: a tap on a box opens the sitting rather than
a menu of eight, the style is changed while working instead of chosen at the
door, and a paper or a deck is asked for at the front door against any
workspace on the machine. All of that is Settled below.**
Item 1 is the acceptance test of the mission and is also the job all of it
exists for. Item 2 needs the account holder rather than a build. Item 3 is not a
build at all.

---

## What to do next

### 1. Ask GitHub to collect the instructor slides, which the rewrite did not reach — A KEYBOARD

**The seventeen decks and sheets are out of every commit here and off `main`, and
GitHub still serves all seventeen at the pre-rewrite SHA.** A raw fetch of
`Prob.Homework1.2026.pdf` at `1205290d` returns 200 and 53,045 bytes. That is
GitHub holding objects no branch reaches until it collects them, which it does
on request and not on a push, so the force-push moved the branch and reached
nothing that is already on their disks.

Two ways to finish it, and both need the account holder:

- **Ask GitHub Support to run garbage collection on `Pirate-Hunter-Zoro/Atlas`**,
  naming the repository and saying the objects are unreferenced after a history
  rewrite. This is the documented route and it keeps the stars, the clone URL
  and every commit SHA the rest of this file cites.
- **Delete the repository and push it again from this clone.** Immediate and
  certain, and it throws away whatever GitHub holds that the local clone does
  not — the issue list, the fork graph, the URL's history.

Until one of those lands, treat the decks as published. Nothing else is
outstanding: `.gitignore` refuses them, `test/tracked.py` refuses them for every
course, and the files are on disk where the board reads them.

### 2. And the five things no test can hold — THE IPAD'S

None of these is a build. Each is an evening in front of the thing.

- **The typed half of the panel, in a real sitting.** The build is Settled: a
  formula renders above the box as it is typed, what was sent stays there
  rendered, a tap on it corrects that answer, and a `$` is one tap. Three things
  a suite cannot say. Whether the block arriving under your thumb reads as a help
  or as a jump — the panel changes height the moment a dollar is typed. Whether
  the hint nags in a code workspace, where a backslash is usually a path and the
  block will say so every time. And whether the tap to correct is findable
  without being told, which is the only part of this nobody can be walked
  through.
- **A response typing out, in a real sitting.** The build is Settled, and the
  trace has already caught this wrong once, which is the reason to trust the
  reading rather than the sentence: a card lands above the surface and types
  where the reader is looking, nothing moves, and a stall keeps the order it
  cannot keep the pacing. `board/test/seam.js` asserts all of it. What a suite
  cannot say is whether it READS as one event: send a written answer and watch
  the reply arrive. If it is wrong again, **☰ → what just happened** before a
  line of code — its head names the shell on the glass, and the `type`/`typed`
  pair says whether the card was animated at all. A first reload after a ship
  still runs the old shell; the second gets the new one.
- **The verdict, in a real sitting, and this is the one that is a FEELING rather
  than a fact.** The band is on the response, amber included; the answer and its
  board are quieter; a run of right answers says how many; and `test/mine.js`,
  `test/typed.js` and `test/theme.js` cover every one of those as a fact. Four
  things no suite can say, and all four are about an evening of being wrong on
  purpose. Whether *playful frustration* is what the cross dropping into place
  actually reads as, or whether it reads as nothing at all — it is one beat by
  design, and the design could be too quiet as easily as too loud. Whether the
  streak chip is a reward or a scoreboard: **the failure mode is that it starts
  to matter**, and somebody who does not want to break a run of four stops
  answering until they are sure, which is the exact outcome the reset rule was
  written to avoid. Whether amber on a doing sitting's every reply reads as
  information or as wallpaper — a build evening is amber almost end to end, which
  is honest and may still be too much. And whether *answer 2 of 3* is useful or
  is a number on a bubble that did not need one: the `nth` clause in `render`,
  and one line to remove.
- **One document, all the way round** — the build is Settled; this is the evening.
  Open a `paper` sitting on a box, let it write into `writeups/<slug>/`, compile
  it, open `/library`, read it on the glass, draw on it, and say something is
  wrong with it. Four things no suite reaches: **the content/scope split against a
  model** — the scope may now be the evening, and whether a tutor holding that
  still refuses to narrate the evening is the whole of whether the split worked;
  **a document asked for from a review, against a model**, which is the same
  question with no box to fall back on; **the revision turn against a model**; **ink a person actually drew** —
  the marks route is tested with fixture strokes, which is not a ring round a
  figure at 200% zoom on an iPad, and that page's pen has never met a stylus —
  and **whether the reader is any good**, which is the one word in the question
  the library came from that no amount of code answers: *slick*.
- **The three teaching rules that were asked for out loud**, all of them
  instructions rather than mechanisms: the question restated under the definition
  list so it is the last thing above the board, the write-up compiled problem by
  problem rather than at the end, and no card telling the student to write
  anything up. `test/teaching.py` holds the places each is written down, and
  asserts only that they reach the course. **The first card of the next sitting is
  the real check.**

---

## Still open from the harness

**Nothing.** Both levers it held are measured and both answers are under
*Settled*: speculation costs 10 % and is off, and one KV slot is the answer
rather than a placeholder.

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

- **THE DIARIZATION REFERENCE IS A HUMAN-ADJUDICATED ARTIFACT, AND NOTHING IN
  THE TREE BUILDS IT.** colibrì made it from the community-1 baseline and the
  annotator's error log across ten hours and two node hops; the annotator
  approved it. It is the reference because she says it is. It lives under
  `phi/`, outside git and inside the fence, so **every downstream number rests
  on a file git cannot see and no assistant working here can read** —
  `research/PSYCH-ASR/HANDOFF.md` carries the provenance because nothing else
  can. The correction algorithm, the error-log reader, the grader, the DER
  scorer and the reference-free arm comparison are all gone, with their decks
  and their tests: a placement rule that could not place two of 117 rows was
  doing a job that turned out to be judgement rather than code. **How an arm is
  measured against that reference is an open decision and waits on nothing but
  the owner** — it may not turn out to be code either. What survives is the
  Stage 1 pipeline, the renderer `join_speakers` needs, and the split-regression
  gate.

- **A COLIBRÌ MISSION CROSSES THE NODE THE WAY THE SERVER DOES, AND TWO
  DRIVERS CARRY IT.** The client is a step of the serve job's allocation and
  dies with it; the work does not. `coli-code` asks `squeue` whether that job
  is still `RUNNING` and exits **75** where it is gone, **76** where there is
  no generation worth stepping into yet. On 75 the mission's own daemon
  re-queues the task as a `[carry]` line and the next turn resumes the
  conversation by name — `turn_plan` answers `carry` with the `--continue`
  recipe whatever the session count says, and the id is in the record rather
  than left to whichever conversation is newest. On 76 nothing is counted at
  all: the daemon waits `CARRY_BACKOFF`, stamps `defer_carry` either side of
  the wait so an ordinary chain gap is not read as a mission nobody is
  driving, and asks again. **Where the board went in the same minute** the
  repair is derived from disk instead: `missions.carry_verdict` is a pure
  function of the record, `agent.json` and a clock, and `spawn.carry_missions`
  runs it in the hub poll of whichever board comes up next, stopping an
  assistant of another name that is holding the workspace, because a start
  will not swap one for another. `turn_at` is the evidence and it lives in
  the record because `agent.json` cannot hold it — the new board adopts the
  left-behind daemon and writes `waking` over the state within seconds. **A hop costs one client start and the re-prefill a
  resumed conversation needs**, minutes against the 15,900-token preamble a
  fresh one pays, and each hop is claimed with `O_EXCL` so every board on the
  machine picks a mission up exactly once. **What it refuses**: a stop with no
  `handover` on it, because a person decided; a mission somebody has already
  looked at, because a record they have acted on is theirs; more than 18 h of
  budget, more than 6 pick-ups, or 2 pick-ups that produce nothing; and a
  generation with less walltime left than the session needs to prefill, where
  a successor exists to take it. Nothing new runs for any of it — no sudo, no
  cron, no extra job, a call inside a loop that already turns. `test/carry.py`,
  `test/hopping.py` and `test/elsewhere.py` hold it; `board/README.md` under
  *A mission* has the four numbers.

- **A CARD ENDS A MISSION ONLY WHERE THE TURN THAT WROTE IT IS OVER.** A doing
  turn writes one sentence saying what it is about to do, does the work, and
  writes the report over the top of it — so the first card of a mission lands
  seconds after the dispatch and hours before the answer. Read as an ending it
  says *done, go and read it* over an assistant that has not started, and
  `looked` then takes the row off the list while the work is still running.
  `judge` asks `_working` as well as the card: `working` is the record's own
  word for mid-turn and it is the one `tutor restart` holds a tutor back by.
  **The process has to be attached as well as the word written**, because a
  record left saying `working` by a daemon that died is a turn nobody is
  taking, and there the card IS the ending it looks like. `test/elsewhere.py`
  holds all three, and the look is the assertion rather than the list, because
  a done mission nobody has looked at is on the list either way.

- **EVERY TURN WHOSE PRODUCT IS A CHANGE IS TOLD TO FIX THE RULE RATHER THAN ITS
  OUTPUT, AND EVERY SITTING IS ASKED FOR THE MEASURE THE WORK ALREADY HAS.** Two
  blocks in `sense.py`. **`RULE_SENSE`** (117 words): where a wrong thing was
  produced by code, the code is what is wrong — fix the module and run it again,
  because a hand-edited artifact cannot be reproduced, cannot be reviewed by
  anybody without the inputs, and is wiped by the next run, and that holds
  however close to right the file could have been got by hand. Its other half is
  where the change goes: **write where the code already writes, never over an
  input you are scored against**, because overwriting the input makes the measure
  agree with you for free. A rule that cannot be written is said on the card with
  what stops you named. **`MEASURE_SENSE`** (46 words): name the measure the work
  already has *where it has one*, RUN it before and after rather than quoting the
  plan — the plan's number is the number *before* — and name a gap rather than
  inventing one. **Wired in one mechanism per turn, and counted rather than
  looked for.** `session_sense` carries the measure on every branch and the rule
  on the doing branch, which is every sitting, every inbox line `routes/lesson.py`
  writes, and `board brief`. The four turns that never run `board brief` carry
  both in their own line: `ship_sense`, `writeup_sense`, `revise_sense`,
  `rework_sense`. **A MISSION IS BRIEFED AS A DOING TURN WHATEVER THE WORKSPACE
  TEACHES UNDER** — `/elsewhere` writes the task as a plain sentence of the
  student's, so `cmd_brief` asks `missions.running(root)` and passes `doing=True`
  to `brief.briefing`. Only ever `True` or `None`; `False` would take the order
  away from a workspace that declares `do`. `missions.running` is a pure read —
  no freeze, no prune, and no walk for the newest card where no record is open —
  and the dispatch writes the mission record **before** the inbox line, because
  that line is the waking. **The dispatch says none of this in the line itself.**
  A rule stated in the line as well as the brief is paid for twice, and 497
  doubled words is five minutes of colibrì prefill. Measured, in words of the
  whole briefing: a teaching sitting +46 (~58 tokens, 1.5% of it), a doing
  sitting +163 (~208), a mission into a workspace that teaches +542 against its
  lesson brief (~698 tokens) — 380 of those words `DOING_SENSE`, which is the
  rest of what a mission was missing. `test/teaching.py` holds the wording, the
  count of exactly one on every path including the whole string a woken mission
  holds, and the two places the rules are written down in step;
  `test/elsewhere.py` holds the other half of that — the dispatched line is their
  words and carries no rules — and the record's order against the waking;
  `test/tokens.py` holds the measure reaching a real `board brief` and the size
  budget, 7,299 bytes against a 9,541 ceiling.

- **A DISPATCH THAT NAMES AN ASSISTANT TAKES THE WORKSPACE, AND TAKES IT WITHOUT
  A TERMINAL.** `⇥ put an assistant to work elsewhere` reads `missions.holder`
  before the start, and where a DIFFERENT assistant is attached it runs
  `tutor agent stop <workspace> --wait` and then starts the named one. The stop
  is what makes the start mean anything: `agent_start` answers *already
  listening* and returns 0 against a live daemon, so without it the task is
  worked by whoever is there under a record naming whoever was asked for — and
  for colibrì that is the fenced directory's job going to an assistant that may
  not read it. **`holder` names the old one until its process is gone**, not
  until SIGTERM lands, so the wait is `--wait` and the holder is read AGAIN
  afterwards rather than believed; one still wrapping up when the wait runs out
  is refused with *ask again in a minute*, because the handoff is a model call
  and nothing with an iPad waiting on it holds a request open that long. Naming
  **nobody** is still whoever is there, and the same assistant already attached
  is left alone — a warm prefix costs hours to rebuild. **`swap_blocked` in
  `server/routes/machines.py` decides what a swap may take**, for two kinds of
  reason: the stop cannot land — the daemon is attached from another node and a
  signal reaches this machine's process table only — or it would land and take
  something claimed: somebody's own interactive sitting, a board a second device
  has open inside the route's `LOOKING` window, a daemon mid-turn, a running
  mission, a handed-in message nothing has picked up. **Cards do not block.**
  Every taught workspace has them, and a rule that refuses the ordinary case is
  the feature not landing. Every refusal names what is in the way and none names
  a command. The stop is the one irreversible thing that precedes the ask, so a
  start refused after it puts the old assistant back BY NAME and READS the
  put-back's exit code — a reply claiming a workspace was restored when it is
  empty is worse than one saying it is empty. **`mark_waking` clears `handover`
  alongside `restarting`**, because a start is what answers a handover: a record
  still carrying the flag while it listens makes the next stop read as a machine
  going away, and `supervise.tutor_verdict` returns `revive`, which puts the
  workspace's CONFIGURED assistant back over the one a dispatch deliberately
  placed. **Every start into a workspace nobody is looking at carries
  `--respawn`** — this route, `spawn.ship_missions` and `/writeup` — because
  `tutor agent start` records the chosen course and the one address, the next
  login and every other machine's idea of *the course* follow that record, while
  the person is still looking at the board they tapped. A hub tap records,
  because a hub tap is a person. `test/elsewhere.py` holds the server half,
  `test/who.js` the sentence the panel stays open to say, `test/choice.py` the
  address and `test/waking.py` the handover flag.

- **A WORKSPACE CONTRACT DESCRIBES THE BOARD THAT IS THERE, AND THE BOARD IS THE
  SAME ONE EVERYWHERE.** `tutorboard.json` declares a `name` and, where the
  repository has answered for itself, a `stance`. **It does not declare a
  subject.** No key in it chooses a layout, a vocabulary or a shape of lesson,
  so a contract saying *this repository is in code mode* is describing a switch
  that does not exist — and an assistant obeys it, which is how four of them
  came to promise three docked signal buttons that are not on the page. Every
  repository answers through the one panel: **✎ write** and **⌨ type**, under
  the question, whichever was used last opening next. `live/` is scratch space
  and the lesson transcript inside it is tracked, by an allowlist in each
  workspace's own `.gitignore`. `board export` compiles by default and
  `--no-build` stops at the `.tex`. **`test/truthful.py` holds the mechanical
  half in both directions**: a key the board drops on read is refused in a
  config and refused as a JSON spelling in prose, because the same dead setting
  lands in the file and in the sentence about the file.

- **OTHER PEOPLE'S SLIDES AND SHEETS ARE ON DISK AND OUT OF GIT, IN EVERY
  COURSE.** Four lines in the root `.gitignore` do it: `/courses/**/lectures/*`
  and `/courses/**/assignment/*`, each with a `.gitkeep` negation under it. The
  leading slash anchors the pattern at the repository root and `**` reaches a
  course at whatever depth it keeps a unit, so a second course gets the rule
  without writing it again. **`*` excludes the FILES, not the directory**, which
  is what lets git keep descending and lets the `.gitkeep` come back — a clone
  arrives with the directories held open and nothing in them, and the owner
  drops the slides back on disk. `test/tracked.py` refuses the same set from the
  index, scoped to `courses/` and exempting `.gitkeep`, with **no extension
  filter** so the two guards refuse the identical set and a `.docx` sheet cannot
  fall between them. `textbook/` is held open by a `.gitkeep` too.

- **ONE `save-and-push.sh`, AND IT IS THE TOOL'S.** `board/scripts/save-and-push.sh`
  is the only copy in the tree and a workspace has none of its own. Both doors run
  it — `lesson/git.py` for the ⤓ save button, `cmd_push` for `board push` — and
  both hand it the toplevel `git rev-parse --show-toplevel` answers as the working
  directory, because the script takes its repository from `pwd` rather than from
  where it is installed. **One repository holds every workspace, so either door
  commits the whole tree**, and both NAME the other workspaces that had
  uncommitted work in them before the commit runs rather than leaving it to be
  discovered, and both lead the commit subject with the workspace so one history
  of many can be read back. The script fetches and merges its upstream first,
  so a second machine committing the same repository — a compute node compiling
  the same document — cannot wedge every later push as a non-fast-forward. A
  conflict outside `build/` stops by hand, and a merge that cannot be completed
  is abandoned rather than left standing, because `MERGE_HEAD` in the tree is
  every later save refused from an iPad. `test/homework.py` asserts the path
  `cmd_push` resolves is under `TOOL` and that its commit leads with the
  workspace, and `test/tracked.py` refuses a second copy anywhere in the index —
  a copy nothing runs is a copy somebody reads.

- **A TAP ON A BOX OPENS THE SITTING, AND A DOCUMENT IS COMMISSIONED AT THE
  DOOR.** The map asked *what do you want to do about this* and offered eight
  answers, so a style was the thing you got past to start rather than the thing
  you change while working — *"these are tutoring styles that I don't want to be
  selecting when I open up a lesson."* Now the tap IS the door and what the box
  is decides which sitting: a part opens a lecture on it, a chapter a lecture on
  the chapter, a problem set a homework sitting, a module or a function or a
  vendor box a walkthrough over exactly that scope, a document the page viewer,
  a wall the sibling it points at. **No `aim` goes over the wire** — the `for:`
  row owns the style and owns it at any moment. **One rule sorts `WORK` and it
  is `needs`**: a way chosen over something is offered on the map, a way with
  none is a style and is the `for:` row, and a paper and a deck are neither, so
  they are out of that table and in `DOCS`, which also takes them out of the aim
  row where they contradicted the rule written twenty lines under them. **What
  is left is a second tap** — the control at the bottom right of the box,
  opposite the one that digs — offering the walkthrough, the drill and the
  document, and carrying the `blockedBy` line; a box whose tap is its one honest
  way gets no control, and `/plan/step` is gone with the panel that read it.
  **An address to a box opens the sitting and is then SPENT**: the bar stops
  naming the box, because this board reloads itself on a ship and a bar still
  naming one files the evening away again. **And the front door commissions a
  document against any workspace on the machine** — which product, which
  workspace, what it is over, the third answered by `POST /writeup/scopes` out
  of `tutorboard/scopes.py`, which offers that workspace's own chapters, sets,
  parts, result directories and documents and walks nothing the board's pages
  have not walked already. `POST /writeup` takes a `repo` and a `scope` key,
  both looked up in what discovery found; for another workspace it asks for the
  start FIRST and writes second, which is `/elsewhere`'s order and its reason,
  and it builds no `Repo` for the target until the ask is allowed, because
  constructing one writes `live/` into a workspace a refusal never touched.
  **The workspace is named `family/name` on the wire**, never the bare
  directory: a workspace is discovered rather than registered, two families can
  hold the same name, and both routes take the first walk hit for a bare one.
  **A picker that stops says how much it is not offering** — forty rows a group
  and the count of what was left off, because a list that ends at a cap in
  silence reads as all there is. **The document lands in THAT workspace's
  library, not on the board that asked**, and the reply says so — and the way
  back is read off the reply rather than off the card that was tapped three
  questions earlier. `test/map.js`, `test/address.js`, `test/door.js` and
  `test/aiming.py`.

- **A DOCUMENT IS AUDITED AGAINST THE CODE IT DESCRIBES, AND THE CLASS THAT
  PRODUCED MOST OF THE LIES IS NOW A SUITE.** Nineteen readers over the five
  surfaces in `board/tools/docs-audit.md`, one refuter per candidate defaulting
  to *the document was right*: **132 candidates, 115 survived**, spread over
  nineteen documents. The shape of them is the finding. **A quarter were one
  class** — a document naming the home-directory clone a workspace lived in
  before this tree became one repository, or the directory a package was called
  before it was renamed. The rest were numbers with two homes — one command's
  suite count had three different values in three documents, Paper-Writer's test
  count two, `atlas.json`'s own family count two — and *not built yet* about
  something built months ago: three of TRD-EHR's four *Planned* bullets name
  functions that are in `core.py`, and `DESIGN.md` still opened *Nothing in this
  document is built* over an engine that has been serving since September.
  **`board/test/truthful.py` keeps the two halves a machine can keep**: no
  document names a retired address unless the sentence is saying it is retired,
  and every count of the suites, of Paper-Writer's tests and of the families is
  re-derived and compared. It found seven more the fleet never saw, because the
  `practice/` workspaces and the root `README.md` are not among the five
  surfaces. **A third check was written and deleted, and the reason is the rule**:
  *every source file a document names exists* fired three times and all three
  sentences were true — `board/README.md` naming a course's `scripts/build.sh`,
  PSYCH-ASR naming a job script in the paragraph that says it was deleted. An
  auditor that reports true sentences as false is one somebody silences rather
  than reads, so that class stays a reader's job and `truthful.py` says so in
  place of the check.
  **Three of the findings were not about prose, and each is its own rule in this
  list.** The professor's module slides and the assignment sheets sat in a public
  repository under a README sentence saying the repository was private and that
  they were tracked *for that reason* — the sentence that would have kept
  somebody from looking. The save button and `board push` ran two different
  copies of the push script, and the terminal's was the older one. And a contract
  describing a setting the board does not read is a contract an assistant obeys:
  four of them promised three docked signal buttons that are not on the page.

- **ONE KV SLOT, AND `exclusive` IS THE ANSWER RATHER THAN A PLACEHOLDER.** A
  slot costs 23.9 GB at a 131072 window and fits only by eating the whole pin
  margin, so the second one drops roughly 17 GB of experts off 100 % residency
  and onto the filer. A second slot also turns speculation off machine-wide, and
  colibrì's own full-residency run has two sessions at 3.16 tok/s each against
  4.84 for one. `exclusive` stays in the `colibri` recipe — P0-STATUS
  **finding 22**.

- **MTP: SPECULATION COSTS 10 % ON THIS BOX, SO THE SERVED CONFIGURATION DOES
  NOT TURN IT ON.** Job 2073575 on compute303, six measured runs ABBAAB, the
  first time speculation has been on under CUDA here: **3.23 tok/s at `draft=1`
  against 3.58 at `draft=0`, and the slowest off-run beats the fastest on-run.**
  Acceptance was 62–77 % and it did not convert — the run that saved the most
  forwards (78 tokens in 44) was the slowest of the three. The drafting works;
  the per-forward cost of it exceeds what the saved forwards are worth on a box
  whose bottleneck `coli plan` already names as the CPU expert tail. So
  `colibri_serve.sbatch` gains nothing and stays as it is, and §3.3's conclusion
  has an A/B under it rather than a misreading. The numbers, the table and why
  the question needed asking at all are `projects/libr-local-llm/P0-STATUS.md`
  **finding 21**; the per-configuration logs stay outside the repository because
  they carry generated text.

- **A LEVEL YOU CAN ONLY ENTER IS A TRAP, AND THE FRONT DOOR HAD ONE.** The
  control back out of a family existed from the day the doors landed and nobody
  found it: a `.72rem` pill in the corner of the atlas head, the same weight and
  colour as `notes`, worded *all of it* — and the head scrolled away with the
  page, so by the time anybody was reading the cards there was nothing on the
  glass that led back. The only route out was to open a workspace and let the
  reload land on the doors. **Three things carry it now and a fourth makes it
  unnecessary.** `#atlas-up` is first in the head, 44px tall, and says
  *Everything*, which is the word on the heading it returns to — a control that
  names itself instead of its destination is one nobody connects to the place
  they are trying to reach. `.atlas-head` is `position: sticky`, so it is on the
  glass at the bottom of the longest family. Opening a family pushes a history
  entry, so the back gesture and Escape both come out; **the entry carries no
  url**, because the hash on that page belongs to `address.js` and a family
  spelled into it is two grammars in one address. And `closeFamily` paints
  first and calls `history.back()` second — `back()` answers when the browser
  feels like it and a tap has to land now.
  **The fourth is a flat read over the top of both levels.** A hierarchy answers
  *what is in Courses* and cannot answer *where is the thing called colibri*,
  because at the door no workspace is drawn and inside a family every other
  family's is hidden. `#atlas-q` filters every workspace and every tree from
  every family at once — the name on the card, the repository directory, the
  chapter, the written title, the next step — and each hit carries the family it
  came out of. It is a level of its own drawn over whichever of the other two
  was showing, so clearing the field puts back the family you were standing in
  rather than dropping you at the door. Its face is `1rem` exactly: iOS zooms the
  whole page when a field it focuses computes below 16px, and the page's own
  magnification is the one way left to be lost on that screen.
  **And the rule generalised, because the front door was not the only page with
  it.** Every way back to the front door says *Everything* — `#atlas-up`, the
  deck's `#deck-back`, and the library's `#lib-back` when that is where it was
  opened from. The board's `#btn-home` stays a bare glyph and is the one
  exception: that bar is at seven controls and `test/link.js` holds the line.
  **And the library leads back where it was opened from.** `#lib-back` is
  `/board` by default, which is right for the board's own row into it and wrong
  for the front door's *Papers & decks* — reading a document nobody is teaching
  from has nothing to do with the lesson, which is the whole reason that button
  exists. `?from=home` carries it: a query parameter rather than a stored flag,
  so it survives a reload and a cached shell and has no second copy to go stale.
  `board/test/hub.js`, `test/library.js` and `test/deck.js` hold all of it;
  `board/README.md` has the rule.

- **EGRESS: A LOCAL MODEL READS PHI BECAUSE A GUARD STOPS IT SENDING ANY,
  NOT BECAUSE THE NODE CANNOT REACH ANYTHING.** These compute nodes resolve DNS
  and reach arbitrary hosts over HTTPS — checked on the serving node, not
  argued. So any sentence anywhere that reasons from *the node has no outbound
  route* is a hole rather than a mitigation, and the two that existed have been
  rewritten. `ai-config/policy/egress.py` is the control: web fetch and search,
  `curl`/`wget`/`ssh`/`scp`/`rsync`, package installs, `git push`/`fetch`, a
  `/dev/tcp/` redirection, an interpreter importing a socket library, and any
  MCP server are refused; loopback is allowed, because that is where the
  gateway answers. It is the mirror of `phi.py` and it is written the same way
  — no vendor, no tool protocol, a test that asserts so.
  **It judges the shell, and that is the whole point.** A deny list over the
  two web tools is decoration when the agent has `curl`. **And it is a
  `PreToolUse` hook rather than a permission**, because the session that needs
  it most is the unattended one running under `--dangerously-skip-permissions`,
  and a hook runs whatever the permission mode says.
  `coli-code` installs it into the local model's own config directory and
  **refuses to start without it**; the front end with no hook system is refused
  outright in a fenced directory, since it cannot carry the guard and still
  gets a shell. Clause 2 of *The exception* in
  `research/PSYCH-ASR/AI_INSTRUCTIONS.md` now says all of this, so item 1's
  dispatch is no longer a session reading its own contract as a violation.

- **THE CHAIN: COLIBRÌ IS ALWAYS UP, AND IT MOVES NODE RATHER THAN GOING AWAY.**
  `coli-up` starts a chain. Two hours before its walltime a generation submits
  the next one with `--exclude` of its own node; that one pins 406.7 GB while
  this one goes on answering, and prints `COLIBRI-SERVE LOADED`; only THEN does
  the incumbent cancel itself and give its node back. Nothing is down at any
  point, and a generation leaves early rather than running out its walltime, so
  the chain hops about every seven hours.
  **Not `--dependency=afterany`, which is what the board's own chain uses**, and
  the reason is one number: a board generation costs nothing to start and a
  colibrì one costs 68 minutes, so a successor that begins when its incumbent
  ENDS is an hour with no server.
  **The chain replaces the server and the carry replaces the client** — the entry at the
  top of this section.
  **The successor cannot land on the incumbent's node** — two 800 GB jobs do not
  fit on a 1 TB box — so every hop pays a cold pin, and that is the deliberate
  price of never being down. A same-node successor would re-read its checkpoint
  out of page cache at **9064 MB/s against 422 MB/s cold**, because page cache
  SURVIVES the teardown of the job that filled it: two jobs, one node, one cgroup
  destruction between them, measured on compute300 on 2026-09-18. The one case
  that gets that speed back is the partition being full — a successor still
  `PENDING` twenty minutes out is re-queued without the exclusion, takes the
  incumbent's node the moment it ends, and pins against the cache still holding
  the checkpoint. On a `c3_short` as busy as it usually is, that is the ordinary
  path rather than the exception.
  **The warm-up waits for the incumbent to go, and one file is why.** KV
  persistence is per checkpoint — `<model>/.coli_kv`, opened `r+b`, written at
  offsets each process computes from its own record count — so two live servers
  interleave their writes and neither reading survives it. The engine READS that
  file at startup, which is harmless, so the 68-minute load overlaps freely; only
  the first write has to wait, and a warm-up is a real write. What that costs is
  the turns the incumbent completed while the successor was loading: they are not
  in the prefix the successor read, so the first turn after a handover re-prefills
  them.
  **A generation's walltime is a ceiling on the CLIENT, not on the chain.**
  `coli-code` steps in with `srun --overlap`, so the client is a step of one
  generation and dies with it. `left` means this hop and must not be widened to
  the chain — a record saying a mission is still running while its client is dead
  is the false fact `missions.holder` exists to stop. `coli-code -c` continues,
  and the on-disk KV makes it cheap.
  **Every generation writes its own pair of logs**,
  `colibri_serve_{out,err}-<jobid>.txt`: one fixed pair would judge a successor by
  the incumbent's `COLIBRI-SERVE READY`. `coli`, `coli-code`, `coli-ask` and
  `tutorboard/colibri.py` all resolve the names from the job id, and all four pick
  the generation that can ANSWER — warm beats loading, and more walltime left
  breaks the tie.
  **Ending it takes the flag AND the cancel, in that order.** A bare `scancel` is
  how you REPLACE a server; the chain reads it as a node failure and does exactly
  what it was built to do. `coli-down` writes `slurm_jobs/state/chain-stopped`,
  then sweeps the queue twice — a generation can queue its successor in the gap —
  and a generation that starts while the flag is there stands down without
  serving. `coli-up` clears it, because asking for a server is asking for the
  chain back.
  **The handover loop is written once**, as `coli_chain_watch` in
  `scripts/colibri-env.sh`, because there are two callers: every generation runs
  it against itself in the background, and `coli-adopt` runs it as a one-CPU job
  of its own against a generation that has none — one submitted with `--once`,
  one whose watcher died with a node, or one already running when this was built.
  It refuses a generation whose log carries `COLIBRI-SERVE LOADED`, because that
  one watches itself and two watchers queue two successors.
  `board/test/colibri.py` holds both halves of this; the cluster half is an
  evening rather than a suite: bring it up, `scancel` the incumbent by hand, and
  time the successor's pin.
- **950 GB IS NOT AN ALLOCATION THIS PARTITION OFFERS, AND THE DEFAULT WAS ONE.**
  `sbatch` refuses anything above roughly 900 GB outright — *Requested node
  configuration is not available*, at submission, at every CPU count, measured
  across `c3_short` on 2026-09-18 — so `coli-up` with no flags could not run at
  all, and a chain would have had its successor refused the moment it was needed.
  The defaults are 80 CPUs and 800 GB, which is what the served job runs on: it
  pins the whole 406.7 GB plan and reports full residency.

- **A CARD IS WHOLE OR IT IS NOT ON THE BOARD, AND THE FOURTH REPORT OF "THE
  NEXT BOARD CAME FIRST" WAS NOT ABOUT THE ANIMATION AT ALL.** `open(path, "w")`
  truncates before it writes; the poll that builds the payload runs four times a
  second over a shared network filesystem. A poll landing between those two
  moments puts a card on the glass with NOTHING IN IT — and an empty card is
  worse than a blank one, because there is nothing to type, so `typeOut` skips
  it, so **no hold is taken**, so the writing surface comes down and the next
  board arrives before the response. Then the real body lands and types
  underneath a board that is already there. **Measured, from the trace the
  report carried:** `fresh cards=0041` then `skip card=0041 why=no units` at
  10:38:38, `fresh cards=0041` again then `type … units=122 chars=1817` at
  10:39:14. Thirty-six seconds for a write that takes microseconds, because the
  empty parse is cached against `(mtime, size)` read through NFS attribute
  caching. **The trace is what settled it and it is why the animation was not
  touched:** both cards carry `typed … stalled=0`. They typed. The board was
  handed something that was not a card. So `board write` renames a finished file
  into place — `os.replace`, same directory, atomic — and `cards.has_body` keeps
  a bodyless card off the board whoever wrote the file, because an interactive
  tutor writes its own and a shell redirect truncates identically. A `.`-prefixed
  part file is not a card either. `test/whole.py` drives a real write and asserts
  the truncate is gone from `cmd_write`.
  **And the trace itself was lying in the same report.** `holdTyping` bumped
  `typingNow` and then asked `keepTyping()`, which tests a `typingUntil` left
  behind by the PREVIOUS card — so a card arriving minutes after the last one
  traced `stall late=358559 held=1` before painting a character, beside its own
  truthful `stalled=0`. It arms the deadline now rather than asking about it, and
  `keepTyping` has exactly one caller: a frame of the animation, the only place
  its question means anything. `test/seam.js` counts the callers. **A diagnostic
  that lies costs more than no diagnostic**, and this one lied on the one class
  of fault it was built for.
- **A RESTART FINISHES THE RESTART IT STARTED, AND THE WATCHDOG IS THE BACKSTOP
  RATHER THAN THE PLAN.** `tutor restart --tutors` signals the daemon, waits 90
  seconds for the wrap-up turn to write `HANDOFF.md`, and gives up — a handoff
  turn is a model call and routinely outruns that, 97 seconds measured. The
  branch that gave up returned with `restarting: True` on the record and NOTHING
  pending, so the board said *claude is restarting*, truthfully, until somebody
  else noticed. Somebody else was `tutor watch` at `REATTACH_GRACE`, 180
  seconds. **That is a backstop and it was being used as a plan**: it exists
  only where a watch loop runs, so a hand restart in an `salloc` left the tutor
  down with no clock anywhere, and where it does run the person holding the iPad
  watches a lesson say *restarting* for three minutes. Reported, minutes after a
  ship: *"Suddenly it says 'claude is restarting' - and I don't foresee that
  finishing... what the hell happened?"* — and it was a ship from this session
  that caused it. Now that branch spawns `tutor finish-restart`, detached
  (`handed_off`), which waits for the record to clear and starts the replacement
  the moment the turn ends rather than at a fixed grace. Detached and not a
  thread, because the restart is a CLI that exits. **`supervise.py` is
  untouched** — it belongs to the serving-chain session, and the two may both
  decide to start one tutor without racing for one reason only: `agent_start`
  refuses where one is already there. If that stops being true, two daemons
  answer one inbox. `test/waking.py` asserts every half, including that one.
- **ANSWERING IS NOT OWNING, AND THAT IS HOW A HEALTHY MACHINE LEAVES SOMEBODY
  HANGING.** A board writes its port into its own repository's `.board.json`,
  and the next board in that repository OVERWRITES it — so a board an ended
  generation left behind keeps running, keeps answering, and is named by no
  record anywhere. `ts_repoint` refused to move the HTTPS name off it, correctly
  by its own rule, because the rule was *a name pointing at a board that is up
  and answering is that board's*. **Measured:** a Galois Theory board from a dead
  generation held `https://compute-node…/` on 9098 for an hour and three
  quarters while the live one served 9195. `tutor serve status` said generation
  3, watched, last check 12 seconds ago; `tutor agent status` said claude
  listening; the tutor's card 0038 was written at 09:53 and sat on a board
  nothing was pointing at. From the iPad: *"If claude is working, and the
  tutoring server is up, how could we ever be left hanging?"* — like this, and
  every layer was green while it happened. A port owns the address when a LIVE
  RECORD names it (`recorded_ports`), and a leftover is stopped rather than
  merely outranked: `drop_strays` runs before `Popen` in `cmd_start`, this
  repository's own and on this node only, because the moment a repository's next
  board starts is the moment the previous one became a leftover.
  `test/serving.py` is the fourth thing in its own list of how this goes wrong.
  **One line is left and it is not in this session's half.** `watch_once`'s
  address block in `bin/tutor` asks `supervise.answering(port)`, which is the
  same test that failed here — so the watch loop would still never call the
  repair. It belongs to the session working on the serving chain: the condition
  wants *and the port is one a live record on this node names*, beside the
  `answering` call it already makes. Until then the repair happens at the next
  board start, which is where this fault actually occurred.
- **A STROKE THAT NEVER ENDS REFUSES EVERY SCROLL ON THE PAGE, so silence has to
  end it.** The non-passive `touchmove` is on the DOCUMENT and exists only while
  a stroke is drawn — that is what keeps scrolling smooth — so *a stroke is in
  progress* cancels a pan everywhere, not just over a card. Every rescue for a
  lift that goes missing is filtered by `pointerId` (the window
  `pointerup`/`pointercancel` pair, `blur`, the next `begin`), and `mine` is
  right to refuse a foreign one, because a second contact must not end the pen's
  stroke. So the floor is not another event: `STROKE_QUIET`, a mark every
  sample moves forward, ends a stroke nothing has been heard from and KEEPS its
  ink. One timer per stroke rather than one per sample, the shape `penSeen`
  already uses and for the same reason: a pencil reports at 240 Hz.
  Four seconds on purpose — a nib held motionless mid-word sends nothing, and
  cutting a stroke in two is a real cost where a latch nobody can clear is the
  whole fault. **And leaving the mode finishes what is in hand**, which it did
  not: `setOn(false)` dropped the latch and disarmed both listeners and left the
  stroke open. That is why this was visible exactly once per sitting — 'done'
  took the refusal off, and the next pen-down cleared the stale stroke, so it
  could never be reproduced after the first time. Reported in those words: *"When
  I annotated for the first time in a session just now, I couldn't scroll at all.
  Then I selected 'done' to stop annotating, and I could scroll. Then I started
  annotating again, and I could scroll."* `window.BoardTrace` is how the layer
  reaches the log at all — `☰ → what just happened` carries an `ink-drop` line,
  because this arrives as a sentence about scrolling and nothing in it can name a
  stroke. `test/link.js` drives a lift under a foreign pointer and waits the
  floor out on a real clock.
- **THE PEN LATCH IS ABOUT A PAGE THAT IS MOVING, AND ITS WINDOW RUNS FROM THE
  LAST SCROLL.** Nib down shuts it; with the page standing still it opens on the
  LIFT, and only a page that has scrolled inside `PEN_MODE` holds it shut. The
  latch exists so a stroke is not re-read as a pan, and a stroke can only be
  re-read as a pan during a fling — `preventDefault` on `touchstart` is refused
  then and honoured at every other moment, and `onTouchStart` already makes it
  for a stylus. Measured from the last SAMPLE instead, it ate the first swipe
  after every mark: `touch-action` is read when a gesture STARTS, so `penLet`
  opening the latch on that finger's first `touchmove` was always too late for
  the gesture that opened it — the source called that the one gesture it gives
  up, and it is the gesture somebody swipes. That is the fourth report of
  *"Scrolling while annotating works now, but when I STARTED annotating a few
  seconds ago, it did not"*, and the first one settled off a trace rather than a
  guess: `ink-end` at 522591 and `ink-latch on=0` at 522941, which the 700 ms
  timer could not have done before 523291, and only `penLet` opens it early.
  `penLift` is why the lift asks at all — `penSeen` arms one timer per stroke
  and never re-arms it, so a two-tenths-of-a-second tick used to leave the latch
  shut for half a second after the nib had gone. `test/link.js`, `latchFlow`.
  **And the layer says which thing refused a pan**, because that diagnosis was
  arithmetic across three timestamps: `ink-latch` carries `why` (`quiet` for the
  window, `moved` for a finger that dragged, `off` for leaving the mode), and
  `ink-pan` is a finger landing against a shut latch — the one refusal that is
  made in CSS and so leaves no event of its own. With `ink-mode`, `ink-begin`,
  `ink-end`, `ink-hold` and `ink-late` that is the whole vocabulary.
  **Two things this trace also closed.** The standing suspicion — that the cost
  was `body.annotating` restyling every card, paid by the first gesture — is
  dead: `ink-mode ms=35` across 42 layers. And an `ink-late at=touchmove`
  following an `ink-hold at=touchstart` is not a page that moved; it is one
  non-cancelable first move per stroke, because `armMove` installs the
  non-passive `touchmove` inside `begin` and the compositor learns about it a
  move later. Read the pair, not the line.
- **ONLY THE ASKER MAY SAY WHY A DAEMON WAS STOPPED.** `restarting` and
  `handover` are written BEFORE the signal, by whoever is asking; the daemon's
  own exit merges `state: stopped` over the top and touches neither, because a
  daemon receiving a SIGTERM cannot tell a bounce from a person leaving. It used
  to write `restarting: False` — and that turned every restart nobody finished
  into a record identical to `tutor agent stop`, which the watch loop obeys for
  ever. **Measured in Galois Theory:** a ship's `tutor restart --tutors` wrote
  the flag and signalled, the handoff turn took 97 seconds against the 90 it is
  given, so the restart printed *still writing its handoff* and returned without
  starting anything; the daemon exited through that line, wiped the flag, and
  three generations of the serving chain revived that course's BOARD and refused
  its TUTOR. Fifteen hours of a board serving perfectly with nothing reading it,
  with `turn_signal` still naming an answer that had been handed in. From the
  iPad: *"it says the tutor is down, though the app is working."* `mark_waking`
  is what clears the flag and it is written by both halves of a start, so the
  flag lives exactly as long as the restart is unfinished — and **a restart
  nobody finished is now one the watch loop finishes** after `REATTACH_GRACE`.
  `test/waking.py` holds both halves: an abandoned bounce is revived, and a
  person's own stop is still never touched. `supervise.py` is READ by that test
  and not changed — the contract is between the record the daemon leaves and the
  watchdog that reads it.
- **THE RESPONSE CARRIES THE BAND, and which card is a reply is a question about
  the transcript rather than about its kind.** The verdict was computed once and
  painted on the student's own answer and on the board holding the working; the
  CARD took its band from its own KIND, so a reply that was neither right nor
  wrong painted the answer amber and the card grey, a finger's width apart. It is
  painted from the verdict now (`cardVerdict` in `board.js`,
  `.card[data-verdict]` in the stylesheet, and the verdict rules sit AFTER the
  kind rules on purpose — same specificity, later wins). **A reply is the first
  card written after an answer**, nothing else in the question's run between the
  two: `correct` and `wrong` say so themselves and carry their verdict wherever
  they fall, and every other kind is amber only where it is answering something.
  That is what makes the amber case exist at all — `REPLY_KIND` has no `lesson`
  in it and `lesson` is the commonest reply in a sitting that DOES the work —
  while keeping a `lesson` card teaching Chapter 5, and a `recap` anywhere,
  plain. **A page tinted end to end says nothing**, which is the objection the
  rule had to survive rather than the rule to overturn. The answer and its board
  keep the colour at 2 mm mixed back toward the rule: the card is the moment, the
  other two are a label, and green on the answer, green on the board, green on
  the card, a tick and a flash is one thing said five times.
- **A run of right answers says how many, and a wrong answer is the only thing
  that resets it.** From the second one the card carries a green chip — *3 in a
  row* — beside the tick, on the card where it happened, so scrolling back up the
  evening shows where a run started and where it broke (`streakAt`, in the same
  walk). Not reset by an aside, not by a question, not by an evening's teaching
  in between: **wrong is the normal state of learning**, this person will be
  wrong many times an evening on purpose, and a counter that also punished
  thinking out loud teaches somebody to stop answering — the one outcome here the
  next card cannot undo. For the same reason the red half is one beat and over:
  the cross drops into place, and then the card reads like any other card.
- **The flourish sits on top of a page that is already correct without it.**
  With `prefers-reduced-motion` set the stylesheet refuses the flash, the pop,
  the drop and the streak chip's entrance and **takes away nothing else** — every
  band, every chip, the tick, the cross, the question mark and the count stay,
  because those are the meaning and the movement is not. **Nothing in `board.js`
  consults the preference for any of it**, which is the standing lesson: the last
  time an animation and a behaviour shared a branch, the next board landed on top
  of an answer for everybody with the preference set — see *Every card types out*
  below. `test/typed.js` runs the second window that
  reports `reduce`, asserts the colour and the mark are both still on the glass,
  and asserts the reduced-motion block in `board.css` contains nothing but
  `animation: none`.
- **The front door is THREE LEVELS, and only the last of them is a plane.** The
  door is the families — large tappable things, each with the sentence
  `atlas.json` already carried for it and a line saying how many, how many live,
  how many have an answer waiting, how many still have something going. Behind
  one is its workspaces, as cards. Behind a card is the project map, on the
  board. **Six families and a dozen workspaces is a list of six**, and drawing a
  list on a pannable pinchable plane is what produced the wacky zooming: the
  gesture layer was solving a problem the content did not have, on a page that
  could be pinched over the top of it. So the top two levels are HTML in a grid
  — no pan, no pinch, no fit, no second re-centre, and neither `plane-core.js`
  nor `gauge.js` loaded by `home.html` at all. **The browser wraps the text**,
  which is why a SHOUTED plan step can no longer run out of a card; how many go
  across is a media query, which is the old constant's promise kept by the thing
  whose job it is. `test/hub.js` asserts the three levels are three surfaces and
  that the top two are not planes.
- **A sitting belongs to ONE box, and leaving it is a new sitting.** Whether a
  box is what scopes a sitting is a property of the WORKSPACE, not a rule for
  the board: `map.scoped` says yes where the picture has a `part` on it and no
  where it has chapters, because a lecture on Chapter 4 of Galois Theory has no
  component to be scoped to and the chapter already is the scope. **In a
  workspace made of components, a sitting with no box says so** — the map tap is
  meant to be the door and it is one door among several, and `node_sense`
  answering those with the empty string left the sitting with no scope AND
  nothing saying one was missing, which is how a turn with no scope picks one. It
  now refuses to choose a part of the repository, and asks in its first card as
  the addresses of every box. **And a component boundary is a STOPPING POINT**,
  in `TEACHING.md` and in `sense.BOUNDARY_SENSE` because in a headless turn that
  line is the whole prompt: the old focus rule was about not wandering, and this
  is the honest case it left open. The turn gets what is in hand to a saving
  point, writes up what was agreed, says which box the work continues in, and
  stops; reading another part is not forbidden, working in one is. **The hand-off
  is a TAP** — every box has an address (§2.1), so the turn is handed the address
  of every other box beside whether any of the plan sits on it, and **a box with
  no step gets the step PROPOSED in the same card**, because the turn has just
  discovered what the work there is and the discovery is lost otherwise. The
  paragraph goes only to the sittings a box scopes: a review, a walkthrough and a
  make sitting are each held over a scope already chosen, so each is still told
  what the box IS and is not told to stop at a boundary it is not working inside.
  `tutorboard/spell.py` is the Python side's one speller for §2.1 — the meeting
  deck was its first caller and a hand-off card is the second.
- **The project map opens to the module, and to the class or function inside
  it.** A directory is not a moving part. Every box with files in it carries a
  second tap at its top right; it redraws the plane as the inside of that box
  with a crumb back up — `PSYCH-ASR › evaluate › grade.py`. **An expansion is a
  new picture, not a bigger one**: splicing twelve modules into a forty-box
  diagram is the ugly grid again with more effort. An arrow that LEAVES is
  rolled up to the sibling it lands in, drawn as a dashed wall keeping its own
  name and tappable to step sideways; at symbol depth a use points at the FILE
  it came from, never at the box the symbol is already inside. `map.inside` is
  the derivation and `GET /map/inside/<id>` the surface — **on the tap and never
  on a payload**, because the payload is rebuilt four times a second and this
  parses files whole. The id is looked up in what discovery found; a miss is a
  404 and the picture already on the glass is untouched. A poll arriving while
  somebody is two boxes deep leaves them there.
- **Python is parsed, everything else is grepped, and the picture says which.**
  `course/symbols.py` answers one question — what does this file define and what
  does each definition use. Python through `ast` (standard library, like every
  module here): classes, functions, decorators, base classes and the names a
  body really mentions. Everything else through `walk.DEFINITION`, the same
  line-anchored patterns that already check a walkthrough's symbol. **A regex is
  honest about definitions and a liar about calls**, so a grepped file reports
  its boxes, draws no arrows at all, and reports `exact: false` — which reaches
  the foot of the map as *trust it less than a Python box*, and is said on a
  module box BEFORE anybody taps it. Caps that say they are caps:
  `MAX_INSIDE = 40`, `symbols.MAX_SYMBOLS = 40`.
- **The written map is not replaced by the derived one; the derived one lives
  UNDER it.** `inside` works off the files a box claims rather than off a
  directory, so a box a person drew and named keeps its name and opening *the
  typist* shows `typists.py`, `transcribe.py` and `run_asr.py` with their real
  arrows out to *the stopwatch*. And **a symbol box opens a walkthrough over
  that symbol** — `psych_asr/asr/typists.py::run`, spelt the way `walk.label`
  spells it. A module or symbol id is never sent as `node`: `map.find` resolves
  the repository's own parts and has no box by that name, so the scope is what
  says what the sitting is about. It is the only way to work offered on a
  derived box, because a function is not a directory to be examined on.
- **Tracing is not grading, and that is two rules rather than one sentence.**
  `atlas.json` skipped the vendor family and the reason written down was that
  nothing in it is the person's to be GRADED on, which made reading how colibrì
  works impossible for a reason about homework. Now: `atlas.workspaces()` skips
  the family — no cards, no write-up, no homework, no push, no board of its own
  — and `atlas.trees()` lists it, shaped exactly like a workspace record, with
  `atlas.find_tree()` to look one up and refuse anything else. `walk.units` and
  `map.shape` take a root and neither asks whose it is. An unpulled submodule is
  an empty directory and is not a tree; a `tutorboard.json` inside somebody
  else's repository does not make one either, because the family decides.
  **Widening the walk is not widening what counts as a workspace.** The prose in
  `atlas.json` makes both claims separately so the next reader cannot merge
  them.
- **A TRACE OVER A TREE IS A SITTING IN THE WORKSPACE THAT IS READING IT.** Not
  a sitting held over a foreign root: that would end `Repo.root` as the single
  answer to *where are we* and make `scope`, `sense`, the card writer and the
  archive each say WHICH root. Somebody tracing colibrì is doing it FOR
  PSYCH-ASR, so the cards, the marks and the transcript are PSYCH-ASR's and the
  tree is only the scope. **The tree is named IN the scope** —
  `@vendor/colibri/bin/coli-up::warm`, the marker, the tree as `atlas.trees`
  spells it, then exactly what a name in that repository would be. Two
  resolvers, deliberately: `walk.resolve` still answers for one root and only
  that, `walk.resolve_elsewhere` goes through `atlas.find_tree` and then asks
  `resolve` against the tree's own root, and `walk.resolve_any` is the single
  entry point the board, the command line and the re-resolution all use. A name
  from a request is looked up on both halves — the tree in what `trees()`
  found, the path in what that tree's own walk found — and a miss is a miss.
  `sense._elsewhere_sense` tells the turn whose code it is and says the one
  thing it could get badly wrong: **a weakness found in a pulled repository is
  not work to be done.**
- **A tree's picture is one level SIDEWAYS, and there is still one renderer.**
  `map.of_tree` is `map.status` in the shape `map.inside` already answers in, so
  `mapDeep` holds it and `paintMap` draws it; `GET /map/tree/<family>/<name>`
  and `…/inside/<id>` are the surface, on the tap and never on a payload.
  `mapTree` on the client is what makes every tap inside a foreign picture ask
  the tree's route — the workspace and the tree have boxes of the same name, and
  answering the wrong one draws somewhere else with nothing on the glass saying
  so. **Nothing on it is working, next or done**, because none of it is work
  this side has taken on, and the one way to work offered on a foreign box is a
  trace. The front door's tree sheet offers *Trace it*, addressed at the
  workspace the board is already serving; where it is serving none, the sheet
  says so rather than offering a button that cannot work. `test/walk.py` asserts
  the tree is byte for byte unchanged after the whole of it.
- **A new thing goes in a module named for the one job it does, and if that
  means moving something first, move it first.** A standing rule rather than a
  task, because every workspace has a map whose boxes are its modules and whose
  arrows are drawn from what they import: a module that does six unrelated
  things draws as one box with eleven arrows into it and teaches nobody
  anything. **The picture is a mirror, and the failure is the module rather than
  the renderer.** `helpers`, `utils`, `common` and `misc` are four spellings of
  *nobody decided*. Written in `TEACHING.md` under *Where a new thing goes* and
  in `sense.DOING_SENSE`, which in a headless turn IS the prompt;
  `test/teaching.py` holds the two in step with the whitespace flattened,
  because both documents wrap their prose. **Draw the diagram before refactoring
  anything** — the box with too many arrows into it is the next refactor, and
  guessing which module is untidy before you can see the graph is how the wrong
  one gets rewritten.
- **The meeting deck: one of it, chosen project by project, and a mark on a
  frame is that project's next DIRECTION.** `meetings/meeting.pdf`, a Beamer
  frame per workspace that moved, read at `/meeting` and marked up there.
  **Assembled, not generated** — every line is a commit subject, a plan step or
  the name somebody gave a box, because a slide you are going to stand behind
  in front of your mentors is the last place for a sentence nobody wrote. A
  model would buy polish at the price of the one property that makes it usable
  without checking, and if it reads badly the fix is `meeting.frames`.
  **ONE DECK, AT ONE PATH, OVERWRITTEN.** No `-v1, -v2, -v3`: this is a one-off
  communication tool. `meetings/` is tracked, so nothing accumulates in the tree
  and `git log` holds every deck there has ever been — recoverable, which a
  delete is not. `--print` therefore writes NOTHING: with one path, assembling
  the source without building the PDF would leave a `.tex` and a `.pdf` beside
  each other that are not the same deck.
  **One frame is exactly one page, and that is load-bearing.** `[shrink]` scales
  a frame that would overflow rather than spilling it, because the page a mark
  is on is how the mark finds its workspace. `meeting.page_map` is written to
  `meetings/meeting.json` at build time; page 1 is the title and belongs to
  nobody, and a mark there is refused by name rather than attached to whichever
  project is first.
  **Which projects is asked with what each one HAS.** `POST /notes/what` returns
  `gather`'s own counts per workspace and the sheet draws them with the ones
  that moved already ticked; `POST /notes` carries `want` to `meeting.build`,
  which filters on it and refuses an unknown name by name. Bare names to tick
  are a guess; "three commits, one step closed" is the answer.
  **The reader is the library's, over a document that belongs to the
  repository.** `paper.pages_of(..., "meeting")` — the same rasteriser, cache
  and `/paper/<name>.png` addresses, in its own cache namespace, which is what
  the `tag` argument was for. Pages carry `data-ann="doc/meeting/p<n>"` and the
  caption names the project that frame is about before anybody draws on it.
  **THE MARKS MUST NOT GO TO `/library/feedback`.** That route files a complaint
  about the document and wakes a `[revise]` turn — it would spend a turn
  polishing a throwaway deck while throwing away the only thing the marks said.
  `tutorboard/proposals.py` routes them by geometry instead: ink on the TRD-EHR
  frame is direction input for TRD-EHR. One turn per marked workspace, in that
  workspace, handed the picture at `meetings/marks/p<n>.png` — beside the deck,
  because a path into the serving board's `live/annotations/` means nothing
  from where the turn reads it.
  **Proposed, never applied.** `POST /direction` writes the direction at the
  root, archives the lesson, forgets the last turn's note and replaces the
  assistant; doing that unattended to five workspaces because somebody drew on
  five slides is the worst outcome available. The turn writes ONE card saying
  what it would change and stops, the person taps ⟳ rethink, and
  `news.elsewhere` is what says the card landed.
  **And the ink goes with the deck it was drawn on.** The one document here
  where an old mark means nothing: it was consumed into a direction the moment
  it was sent, and the replacement has a different project on page 4.
  `test/meeting.py` holds the server half and `test/deck.js` the page.

- **The typed half renders as it is typed, and keeps what it sent where it was
  typed.** One block above the box — `#said` — doing two jobs that are one job:
  before a send it PREVIEWS what the transcript will show, after a send it is the
  RECORD of what was sent, and the box under it opens empty for the next thing.
  Box and block against slate and board is what makes the two halves of the
  answer panel symmetrical; sent ink always stayed where it was made and sent
  words used to leave nothing behind at all.
  **Nothing renders inside the box and nothing can.** `#saybox` is a textarea,
  which holds characters and no markup by definition. A `contenteditable` renders
  in place and costs iOS autocorrect, its undo stack, selection under a thumb,
  `autosize`, the draft save and the ⌘-Enter send. Do not reach for it.
  **One renderer, or the block lies.** `renderMarkdown` then `typeset`, the pair
  a card goes through, and `test/mine.js` asserts that what the block shows and
  what the transcript shows are character for character the same string. The
  preview's debounce is 160ms and is deliberately NOT the draft save's 800ms: a
  save nobody sees can wait, and a preview most of a second behind the keystroke
  reads as broken rather than as considered.
  **It opens only when there is something to show** — a dollar, a TeX delimiter
  or a backslash command in the box, or an answer already sent on this question.
  A block that is always there doubles the height of the panel for everybody who
  never types a formula.
  **A tap on it is how a typed answer is corrected.** `correctSaid` hands the
  words back to the box and sets `correctingTurn`, so the next send revises that
  answer rather than landing beside it, and that is the ONLY place the restore
  runs. While it ran on every paint of the panel the box could never open empty.
  **`saidNow` is kept locally as well as read off the payload**, because the box
  empties on the tap and the turn comes back a round trip later: a block that
  waited for the payload would leave the answer nowhere on the page for exactly
  the moment somebody is looking at it.
  **A bare `\gamma` is NAMED, not fixed.** One tap on `$…$` wraps the selection
  or drops a pair with the caret between them, and a backslash command sitting
  outside any delimiter raises *\gamma will not render — wrap it in $…$*.
  Auto-wrapping anything that looks like TeX was refused: `\d+`, `C:\temp` and a
  shell escape are all backslash commands to a pattern and none of them is
  mathematics, and this board is used in code workspaces. The hint asks
  `protect` — the renderer's own first pass — what counts as code, so a regex
  inside backticks raises nothing.
  **The block declares no font of its own.** The prose inherits the reading face
  from the body and KaTeX brings the one it ships, so the words are
  dyslexic-friendly and the mathematics is untouched by construction rather than
  by a rule. `test/typed.js` owns the panel and loads the REAL KaTeX to do it —
  a stub cannot tell a block that was typeset from one handed to nothing.
- **A card lands ABOVE the writing surface, so a response types out where the
  reader is looking and nothing on the page moves.** `tailAnchor` in `board.js`:
  a node at the end of the lesson goes in front of the surface, never appended
  after it. The surface has no key, so a reconcile that appends puts the reply
  UNDER a full-height open board — it types out off the bottom of the glass, and
  the jump at the end is the surface taking its proper place, revealing a
  finished card in one go.
  **That was reported four times and patched three times in the wrong half.**
  "The next board appeared under my answer and then the whole response showed up
  at once between the boards" sounds like a question about when the surface
  moves, and every fix before this one answered that question. The board's own
  trace settled it in six lines: `type card=0037 ms=4200`, then `typed
  asked=4200 took=4256 stalled=0`, with `hold=1` throughout. The card typed.
  Nobody saw it. **Read the trace before touching this code.** `test/seam.js`
  asserts what follows — the surface is never MOVED at all between a reply
  landing and its last character — in three windows, and `test/chain.js`,
  `test/feedback.js`, `test/link.js` and `test/typed.js` each assert that a card
  is above the surface while it types.
- **Every card types out, character by character, and a surface that is not open
  yet waits for the last character.** Three rules hold that up, and each of them
  replaced something that looked reasonable.
  **Reduce Motion does not govern this animation.** `typeOut` does not consult
  `prefers-reduced-motion` at all: an explicit request about one animation —
  asked for three times, in these words, *"show up character by character"* —
  outranks a system-wide default about movement, which goes on governing
  everything else on the page. A shorter animation is not a compromise available
  here, because what gets reported is the answer arriving all at once and a
  faster dump is still a dump.
  **The hold is a list of nodes, not a class on a body.** `typingHeld` is taken
  and given back with the hold itself. `.body.typing` is set by the ANIMATION, so
  every path that holds without animating left that lookup nothing to find; a
  marker that can drift from the thing it marks will. What reads the hold is
  `writerHeldShut`, the receipt, and how far a surface moved up by hand may come
  back down.
  **A stall loses the pacing and never the order.** `keepTyping` says whether the
  frame it was handed arrived after the watchdog deadline, and a card told that
  is finished WHOLE and hands its hold to a 250ms settle rather than giving it
  back. Letting go still beats parking the surface for ever — that is what the
  deadline is for — but letting go silently meant the rest of the card and the
  next board arrived as one event, which is the fault the whole mechanism exists
  to prevent, coming back out of its own safety valve.
  **And the board says which board it is.** `☰ → what just happened` keeps the
  last three hundred moves, and its head — and the first line of what it copies —
  is the shell cache's own name, read from the page and never from the server:
  a server on new code serving a device that kept an old shell is exactly the
  case that reading needs to catch. `test/seam.js` drives the flow a person
  performs (ink, Send, receipt, reply, next question) in three windows —
  ordinary, Reduce Motion on, and frames arriving too late to be proof of
  anything — because the fault survived three reports by living in the seam
  between one suite that sends and never replies and one that replies and never
  sends. `test/typed.js` and `test/chain.js` are the other two.
  **And no suite can opt out of the animation any more.** `test/link.js` used
  Reduce Motion for exactly that, so that it could read the page one frame after
  a payload; its two flows that put a new card up and then ask where the surface
  went are at the foot of that file now, and they wait. Anything asserting where
  the surface sits has to.
- **The answer panel opens on the half an answer was last SENT on, and a typed
  box only ever holds what was typed against the question it sits under.**
  `setAnswerKind` runs from both send paths — `say` for the words, the writer's
  `onSend` for the ink — and from a tab press as well, because a tap is a
  statement; what it writes is stamped with the sitting (`sittingTag`: the course
  and `opened`), so a half remembered in another workspace names no sitting here
  and is ignored. Per-question answers still outrank it, in this order: a tab
  press on THIS question, then what this question was answered with, then the
  remembered half. **The first question of a sitting has no last half, so its aim
  answers it** — `answerKind` falls back to `doingTurn`, which opens the box in
  a sitting that does the work and the board in one that teaches. That is the
  board's one map from aims onto surfaces and must not grow a second.
  **Ink carries over from question to question on request and typing never
  does:** `carryOver` has no typed twin and must not be given one — *"there's no
  way I'm going to type the same thing again."* A new box opens empty apart from
  an unsent draft typed against that question, which is kept per question and
  survives a reload. A SENT typed answer comes back rendered in the block ABOVE
  the box rather than into it, and a tap on the block is what hands it back for
  correction — which is what lets the box open empty on every question.
  `test/half.js` is the suite.
- **A document is corrected, or overhauled, without leaving the page it is on.**
  Three things used to answer *no* to that and each was a missing piece rather
  than a missing mechanism.
  **It appears in front of you.** `GET /library/stamp` is where every document
  is, when its source and its PDF last changed and how big they are — `stat`
  and nothing else, no titles read out of sources and no `pdfinfo` — so the page
  asks it every four seconds while it is visible and asks the expensive
  `/library.json` only when the answer moves. One hash overall says *ask for the
  list again*; a hash per document says *the one being read moved*, so a
  33-page deck is not re-drawn because something else was built. **Not the hub's
  SSE payload:** that is the lesson's, and this page opens no sitting on
  purpose. Filing a note cannot move the stamp, which is what stops the page
  redrawing on its own feedback. The re-draw **keeps the reader's place** —
  restored as the images above it decode, because a picture has no height until
  it has, and abandoned after eight seconds, by which time they have scrolled
  somewhere themselves — and **keeps the ink**: a ring somebody drew is theirs,
  and where the page count moved the reader says out loud which version they
  were drawn on rather than pretending page 7 is still page 7. A turn that was
  asked for says so on the row and in the reader until that document's own bytes
  move, and nothing else clears it: the reply says a turn was WOKEN, which is
  not the same as the document having changed.
  **You can read what it says it changed.** `GET /library/note/<id>/<name>`, and
  the rounds under each document are the button that opens it. That file is
  where the turn writes `## What was changed`; the name is matched against what
  `library.notes` found beside THAT document, which is the rule `find` holds for
  an id one level down.
  **And an overhaul is a second ask rather than a longer note.** `revise` keeps
  the document's structure, its names for things and its claims — *do not start
  it again and do not widen it* — which is right for "figure 3 is mislabelled"
  and wrong for *"that presentation needs an overhaul now that we plan to use
  colibrì"*. `rework` may restructure, cut, reorder and rewrite:
  `HEADLESS_REWORK_PROMPT` is the revision's prompt with that sentence gone and
  a brief in its place, `turn_plan` and `carry_after` treat it as they treat
  `revise`, and `doing_now` gives it a doing turn's clock because thirty-three
  pages and a LaTeX build is not fifteen minutes. A plain revision stays on the
  sitting's clock; it changes what a note names and is over in a minute. It
  costs a **purpose** — a sentence saying what the document is FOR now, written
  into the note as its own section, because an overhaul with no new purpose in
  it is a rewrite for its own sake — and a **committed source**, refused
  otherwise by name with nothing written, because an overhaul replaces the whole
  document and git is the only undo it has; committed as it stands, the whole
  overhaul is one diff. The board refuses rather than committing a half-finished
  edit, since the state that would be reverted to is one nobody chose. The
  refusal names **⤓ save** on the board rather than `git commit`: a guard whose
  remedy is a terminal has sent somebody to a keyboard to get past this board's
  own rule. `leaving.uncommitted` is the git half and is there because
  `git status --porcelain -uall` has one parser in this tool and a second goes
  quietly false on one side; a workspace with no repository over it refuses
  nothing, having no undo to protect. A **delivered manuscript** is not
  overhauled from here at all: the factory holds its evidence, its terminology
  lock and its venue, and "restructure, cut and rewrite" is what every one of
  those gates exists to refuse. A paper whose purpose has changed is a new
  paper. Still a LIBRARY turn either way — no card, no sitting, no
  `state.json` — because correcting a deck must not interrupt somebody's proof.
- **A mission can be told to ship itself, and the assistant that did the work is
  never the one that pushes it.** One switch on `⇥ put an assistant to work
  elsewhere`, carried in the record as `ship`, honoured when the mission ends
  `done` — and `done` only, because a mission that FAILED may well have left
  changes in the tree and pushing those is the opposite of what that word means
  to whoever set it going. The push is the workspace's ordinary tutor, woken
  with a `[ship]` line naming what the mission was asked to do and who did it:
  the local model decodes at three tokens a second and is the one assistant
  allowed to read the fence, so its own diff is the one thing it must not push,
  and what ships it is a hosted turn that could not have read the session
  content it is checking the diff for. The switch says that on the glass,
  because *ship it* otherwise reads as *and nobody looks*. **A private daemon is
  stopped first and only when it is listening** — `tutor agent start` will not
  swap one assistant for another, a live record is *already listening* and the
  start is a no-op — while a daemon mid-turn is doing something somebody asked
  for and the ship waits for the next pass rather than killing it; and a tutor
  already there that may NOT read the fence ships it where it stands, because
  the rule is not *the default assistant*, it is that whoever pushes could not
  have read what it is checking. The turn is a revision's twin: fresh session,
  no card, no `state.json`, and the lesson does not resume into it —
  `HEADLESS_SHIP_PROMPT`, with `turn_plan`, `carry_after` and `doing_now`
  treating `ship` as they treat `revise` plus a doing turn's clock. **Handed
  over exactly once**, claimed with an `O_EXCL` create because every board on
  the machine sweeps every workspace from its own poll loop, and `shipped` in
  the record is what a person reads; what the push then did is `push.json`,
  which the board already paints. One surface per fact.
- **Nothing leaves this machine without the diff being read past the lab's own
  PHI rule.** `board push` and the save button both call it and nothing did
  before: `names_phi` in `ai-config/policy/phi.py` had no caller in the
  repository at all. A `.gitignore` stops a phi FILE and `test/tracked.py`
  audits every tracked path; neither can do anything about phi CONTENT — a
  fixture cut out of a transcript, an example hard-coded from one, a docstring
  quoting a span, written by the one assistant allowed to read that directory
  and pushed by a turn that was not. **Per file, by the workspace it is in**,
  and that decision is the whole of `tutorboard/leaving.py`: a push here commits
  the whole repository, so *is the pushing workspace fenced* is the wrong
  question, and checking every changed line is wrong the other way because this
  repository's own documentation names the fenced directory on nearly every page
  — it would refuse the commit that documents the check. Prose about a fence is
  not a hole in one. `git status --porcelain -uall`, because the file at risk
  has never been tracked and `git diff` cannot see one; the ADDED lines for a
  tracked one. **What it catches is said plainly** — the fenced directory by
  name, the old data tree, the artifact shapes — and a bare sentence of dialogue
  with no shape on it is not catchable by a regex, which is exactly why the ship
  turn is a hosted assistant READING the diff as well: the machine check has no
  judgement in it, which is what lets it run unattended. The refusal names the
  file, changes nothing, and is written where the board paints it;
  `board push --anyway` is the override and is deliberately a keyboard act,
  because a button on a tablet that waves a PHI fence through is the thing the
  fence is for. The policy is loaded out of the repository by path rather than
  copied in, and a repository with no policy file refuses nothing rather than
  deciding for itself what session content is.

- **A mission is a record in the workspace it is about, and closing the iPad
  never touched it.** The daemon `POST /elsewhere` starts is detached, so a
  closed lid was never what ended one; what did not exist was any record that
  one had been sent, so nothing could say a mission was still running and a
  failed turn said so only in the busy strip of the board nobody was looking at.
  `live/missions/<turn>.json` is that record — one file per mission, named for
  the turn that carries the task, in the workspace the mission is about, read by
  every board off the shared filesystem the way `news.py` reads cards. A single
  `missions.json` would be a read-modify-write and two boards dispatching into
  one workspace would lose one of them. **The state is derived and then frozen,
  and both halves are load-bearing.** Derived, because nothing is alive to write
  it: a mission ends by a card being written, by the daemon dying, or by the
  allocation under it going, and in two of those three there is no process left
  to record anything — so the ending is read off the newest card and off
  `agent.json`. Frozen, because that evidence expires: a mission that failed at
  nine and any later card at eleven reads as `done` to anything looking after
  eleven, so the first reader to derive a terminal state writes it into the
  record and every reader after that reads the ending. **Three states and no
  more** — `running`, `done`, `failed` — because they are the three a person
  does something different about, and a failure carries its reason on the row:
  *nothing is attached to that workspace any more* and *the allocation colibrì
  runs in ended* are the same word and two different next moves. `done` is a
  card newer than the mission, which is `news.py`'s rule, compared against the
  newest card at dispatch as well as the dispatch time so a clock a second out
  between two nodes cannot report a mission done the instant it starts; nothing
  attached is not a failure for the first `processes.WAKING_GRACE`, because
  `agent start` forks and the daemon writes `waking` before a `git pull` and a
  tailnet coming back. **Colibrì's ceiling is stamped at dispatch**, off Slurm's
  own `%L` in `colibri.status()["left"]`, because a colibrì turn runs inside the
  serve job's allocation and cannot outlive its walltime — `coli-up -t` is the
  only lever, and a mission past the ceiling says that rather than nothing. **It
  comes off the list when it is looked at**, and looking means going there: the
  board serving that workspace stamps its own finished missions on `POST /seen`,
  this workspace and no other, and a running one survives a look because it is
  still running. On the glass it is above the answers in the board's strip and
  above them on the front door — a thing that has not finished comes before one
  that has — and a running or failed mission marks its atlas box bottom right,
  so the answer badge and this can sit on one box. `ship` is written and
  honoured when it finishes, which is the entry below.
  **And a mission names the assistant that is actually doing it.** `agent start`
  returns 0 where one is already attached — correctly, because a start that
  found its work already done did not fail — so a dispatch naming `colibri`
  into a workspace a hosted tutor is listening in wrote the task to that tutor
  and stamped the record `colibri`, with a ceiling read off a serve job the
  worker was not running in. Two things that read as facts and were not, and in
  the one case this route exists for it is the fenced directory's job handed
  quietly to an assistant that may not read it. `missions.holder` is who is
  attached over there right now, and `/elsewhere` refuses when an assistant was
  named and a different one holds the workspace — in the grammar of the other
  two refusals, which is who is holding it and the one command that frees it.
  **Naming nobody is still whoever is there**, because that is what a dispatch
  that names nobody asks for. `test/elsewhere.py`.

- **The allocation renews itself, and a loop inside it puts back what dies.**
  Two failures had no answer here. A process died — `serve.py` on an exception,
  the tutor daemon on an OOM — and the record on disk went on naming a dead pid
  until somebody logged in, because a login was the only moment anything looked.
  And the allocation ended, which takes the node, both processes and
  `tailscaled` with it and leaves nothing anywhere to notice. `tutor serve` is
  the answer to the second: a batch job that submits its successor with
  `--dependency=afterany:<itself>` **before it does anything else**, so the
  queue always holds the next machine and a generation that falls over in its
  first second still leaves one behind it. `afterany` rather than `afterok`,
  because a generation that crashed is when the next one is most needed. That
  makes the first worth writing, and `tutor watch` is it — one pass every twenty
  seconds over every workspace, inside the generation: a board whose pid is
  gone; a board that is alive and has failed `/health` twice, which is *wedged*
  and is the failure a pid check cannot see, stopped before it is started
  because otherwise the port is still held and the new one lands where the iPad
  is not looking; and a tutor daemon that died. `scripts/install-autostart.sh`'s
  refusal stands exactly as it was written and this does not contradict it: the
  supervisor it refused OUTLIVES the machine and comes back to a machine that is
  not there, and this one IS the machine — it ends when the allocation does, and
  the thing that brings the board back is the successor queued nine hours
  earlier, at the start of this generation.
  **Ending it is a flag BEFORE a cancel**, which is not belt-and-braces:
  cancelling the running generation is precisely what its successor's dependency
  is waiting for, so a chain cancelled one job at a time comes straight back,
  which is the design working at the worst possible moment. `serve-stopped` in
  the state directory is checked before any submission and on every pass of the
  loop, and `tutor serve stop` writes it and then cancels the whole job name at
  once. **The partition is the one setting in here with a wrong answer**: `c3` is
  PreemptMode SUSPEND under higher-tier partitions, so a board there is
  SIGSTOPped by the first busy afternoon — alive, holding its port, answering
  nothing, and undiagnosable. `c3_accel` is no escape either: measured from
  inside a job on compute306, its node has no route to Tailscale's control plane
  at all, so a tutor can teach from there and the iPad cannot reach it. That
  leaves `c3_short`, nine hours, top tier and preempted by nothing — a ceiling
  which is exactly what a self-renewing chain makes irrelevant. It is
  `serve_partition`, `serve_time`, `serve_cpus` and `serve_mem` in the config,
  because the day the cluster is rearranged this has to be answerable without a
  commit. **A handover is not a stop, and the difference is one field**: the
  walltime warning (`--signal=B:USR1@300`, so the handoffs get written while
  there is still a machine) makes every daemon exit leaving the same record a
  person's `tutor agent stop` leaves, and one of those must be picked back up
  while the other must never be — `hand_over` writes `handover` first, and it is
  honoured regardless of which node the next generation lands on, since on a
  single-node partition the same one is the common case. Believed for an hour:
  `live/agent.json` is never swept, so a record saying `listening` on a node
  whose allocation ended two days ago reads exactly like one from a node that
  went a minute ago. What the watchdog REFUSES is the load-bearing half —
  nothing without a record, because `board stop` and `tutor headless --stop`
  remove theirs and that is a person saying no; nothing on a node Slurm still
  says is yours, because the pid in that record cannot be read from here and the
  live one is usually an `salloc` with somebody mid-proof on it; nothing a
  `restarting` flag says is already in flight. And the chain cannot watch itself
  all the way down, so the loop re-checks its own successor every five minutes
  and `tutor resume` repairs the chain on any login, but only where one was
  started and not stopped. `board/README.md` has the shape;
  `tutorboard/supervise.py` holds every decision off records and a clock so none
  of it needs a cluster to test, and `test/perpetual.py` is mostly assertions
  about what it will not do.
- **A workspace says whether it holds a fence, and both choosers say it before
  the tap.** The fence was real and per-PATH — every walk refused a fenced
  directory — and nothing anywhere said that a WORKSPACE had one, so the *who:*
  row offered a hosted model in a box holding session content exactly as it does
  in one holding a textbook. `fenced.holds` is the answer: a walk one level down
  for the names in `NEVER`, cached a minute, carried on `machines.workspaces` and
  on the board's own payload so a dispatcher can say it about a box nobody is
  looking at. **One level deep is the rule**, because this labels a workspace on
  a chooser rather than guarding a file about to be opened — a `data/` directory
  six levels down inside a vendored dependency is not this workspace's fence.
  **Visibility and a default, never a refusal**, and that was the decision: the
  fence stops a hosted assistant READING `phi` rather than stops it existing, and
  the teaching thread on this code is a hosted conversation that works. So every
  assistant stays on the row, a tap is honoured, `⇥ put an assistant to work
  elsewhere` merely DEFAULTS to the reader over a fenced target, and a pick that
  is not the reader carries a line naming what it will not be able to open.
  **Who the reader is comes out of the registry** — the recipe carrying
  `private`, and exactly one does — never a name written into the browser, where
  it would go out of step with `bin/tutor` the first time either moved. A machine
  that has not got that assistant draws the row anyway and says so: a fenced box
  with nothing that may read it is the one case where the absence of a choice is
  the thing worth saying. `board/test/plan.py`, `board/test/colibri.py`,
  `board/test/who.js`.
- **One step of a coaching sitting can be handed over, and the sitting stays a
  coaching one.** `coach` names the calls and lets them type it, and the only
  way out of one step of that was `POST /aim`, which changes the WHOLE sitting
  to `build` — so the way to get one step written for you was to stop being
  coached. A coach card now carries a tap at its foot and `POST /handover` takes
  the card's id: `state.json` is untouched, nothing is archived, no tutor is
  replaced. **Offered on the newest card only**, because that is the step and
  the ones above it have already been typed — and the offer is part of the
  card's render key, or a node kept because nothing else about it moved keeps a
  button the sitting no longer offers. Refused where the stance already resolves
  to `do`: there is nothing being withheld, so the tap means nothing and waking
  a turn costs real money, which is where a second tap on the aim it already has
  stops too. The turn carries the card in `card` and not in `answers`, because
  `answers` means *the student answered that card* and gives it a writing
  surface of its own. **The signal reaches the clock, not only the prompt:**
  `doing_now` takes it, so a handed-over step runs on a doing turn's hour rather
  than a teaching turn's fifteen minutes, and `sense.session_sense(repo,
  doing=True)` gives it the doing turn's order. **The card that comes back is a
  short report with the NEXT step posed under it, never a coach card about the
  step just done** — a card explaining how it was done is a lecture nobody asked
  for, and their next act is the next step; the rule is in `TEACHING.md` beside
  *A doing turn* and in `sense.HANDOVER_SENSE`, which is the one a headless turn
  actually reads. `board/test/aiming.py`, `board/test/handover.js`.
- **Which assistant tutors a sitting is the sitting's to say, and it is the only
  layer a tablet can reach.** `resolve_agent` had four — a flag on a command
  line, a line in the workspace's `tutorboard.json`, a hostname, a default — and
  none of them was the sitting, so choosing a different model for one evening's
  work meant editing a file that is a statement about the workspace for ever.
  The fifth goes into `state.json` through `_mark`, beside `node` and `aim`,
  under exactly their rule: a choice made for an evening is not a decision about
  what the repository is, so it is cleared by opening a sitting that does not
  name one. It is chosen as a sitting OPENS and there is deliberately no
  `/agent` beside `/aim`: an aim changes what the next card is, an assistant
  changes **who writes it**, and the conversation the outgoing one was holding
  does not transfer — which on the local model is a 15,900-token preamble paid
  again, in hours. A name the machine has not got falls back with a line saying
  so where every layer below it refuses, because this is the one layer written
  from a browser and a misspelling must not leave a course with no tutor.
  `config.clean_agent` checks that it is a NAME and nothing more, because the
  registry is in `bin/tutor` where a recipe belongs. The *who:* row in the
  sitting chooser is the control; `board/test/colibri.py`, `board/test/who.js`.
- **The local model is a row in a table, and three fields on it carry everything
  unlike the other five.** `timeout` is four hours and `turn_timeout` takes it
  as a FLOOR, so a colibrì turn is not killed mid-prefill and painted as a turn
  that failed while the two numbers about the sitting stay exactly as they were
  for everybody else. `exclusive` is one sitting at a time machine-wide, found
  off the heartbeat and never the pid, because a pid written on one node names a
  process table this one cannot read — the server has one KV slot and a second
  sitting destroys the first one's preamble. `private` refuses to open where
  `git check-ignore` says a card of its own would be tracked, because this is the
  only assistant allowed to read `phi`. Each is a string that is its own reason,
  so the day one stops being true a line comes out of the table rather than out
  of a function.
- **Starting the server is four states off `squeue` and a thread that returns at
  once.** Nothing running, queued with Slurm's own reason, loading, warm.
  `coli-code`'s answer to a missing server is *start one: coli-up*, which is
  right in a terminal and a dead end on an iPad — and an allocation, a 429 GB
  load and a warm-up generation cannot be reported by the request that asked for
  them, which is the reason written above `spawn.wake_tutor` and now above
  `spawn.wake_colibri`. No state file: `squeue` never goes stale and a file does,
  cached fifteen seconds the way `machines.held_nodes` caches its own. Loading
  versus warm is not a question Slurm can answer — the gateway binds its port
  before it loads anything, so a TCP probe answers instantly and says nothing —
  so the job's own `API listening on` and `COLIBRI-SERVE READY` are what is read.
- **A workspace you are not looking at can be handed a job, and only the seam
  was missing.** `machines.workspaces` was the list, `tutor agent start --agent`
  was the start, and `news.elsewhere` was already how it comes back. `POST
  /elsewhere` asks for the start FIRST and writes the task second: the other
  order leaves a refused job in another workspace's transcript with nothing that
  will ever read it, and two refusals fire routinely. Nothing is missed by
  writing second, because `agent_start` forks and returns and `board wait` blocks
  rather than reading the inbox once. The assistant is named on the command
  line — layer 1, this once — and never written into a sitting nobody is
  watching.
- **The receipt lets go when the answer is ON THE GLASS, not when its record
  arrives.** Two surfaces asked "has the reply landed" and answered differently:
  the writing surface asked `typingCards()` and held, the receipt asked whether a
  card existed and let go the instant one did. So the pulse stopped, the next
  board came down, and the answer filled in afterwards — *"the response appeared
  how I wanted it to, but before it did, the second board showed up right
  underneath the last board, and I was left hanging."* One predicate now,
  `replyArriving`, asked by both. The type-out's deadline is a WATCHDOG rather
  than a budget — it measures silence, refreshed by every frame that lands — since
  the card that runs longer in wall-clock than its own animation asked for is
  precisely the longest one, which is the card the hold is most needed for. And
  the receipt has a fourth state, `arriving`, because *"the tutor is reading it"*
  stops being true the moment the card starts typing and that is the few seconds
  somebody is actually watching it. `board/test/hanging.js`.
- **A typed answer is owed the same pulse as a page of ink.** One condition was
  doing two unrelated jobs: it set `awaitingReply` and it decided whether the
  turn was rendered into the transcript, and only the second is about the kind.
  The `items.pop()` is an argument about ink — the same page is on the surface
  directly below — and a typed answer is duplicated nowhere, so it stays. A
  signal is not an answer and raises no receipt: a tap on "begin" is in the
  transcript because they did it, and *"sent at 20:14"* is a sentence about work
  handed in.
- **The box belongs to the question, not to whichever tab is showing.**
  `restoreTextDraft` was asked only while the type half
  was up, so a question that opened on the slate left the previous question's
  words in the box — and the restore refused any box that was not empty. It is
  now asked whenever the panel is open, and the refusal asks the narrower and
  right question: does `textDrafts` hold typing of their own, on THIS question,
  that has not been sent. That is the same correction `correctingTurn` is on the
  send side. The height is measured only where it can be, because `scrollHeight`
  on a hidden textarea is zero.
- **The write-up is the tutor's, and so is the sentence about it.** A card said
  *"two words to add when you write it up"*, which is two failures welded into
  one clause: it hands over an errand that does not exist, and it defers a
  correction — the missing word was `non-zero`, a fact about the proof rather
  than a note for later, so the fix was made conditional on something the student
  was never going to do. A card now says what the file NOW SAYS, and a correction
  belonging in the write-up is made there in the same turn. In `TEACHING.md`
  twice and in `sense.WRITEUP_SENSE`, which in a headless turn is the whole
  prompt.
- **A board and its tutor die separately, and the board coming back is not the
  tutor coming back.** The daemon belongs to the allocation that started it; the
  board comes back on whichever node you next log in to, so the two end up on
  different machines and the older one ends. From the machine you work on, the
  course then reads *board on compute301, no tutor*, and every path that could
  have repaired it looked away: `cmd_resume` said it was leaving the board where
  it was and returned **before** `ensure_agent`, and `tutor restart --tutors`
  bounces tutors that are attached and reports *no tutors were attached* about
  one that has died. A login now asks the node the board is on, over ssh, with
  `tutor agent ensure` — `start` that says nothing when there is nothing to do.
  The record is believed first and `processes.agent_attached_away` is the only
  honest test from another machine: the heartbeat, never the pid, because a pid
  written on one node names a process table this one cannot read. Three missed
  wake-ups is the window. Inside a serving generation `tutor watch` makes the
  same repair on its own node every twenty seconds, and a login is what reaches
  across to another. Over ssh only and not the hop's Slurm fallback: a step
  holds itself open for the life of what it starts, and one sleeping step per
  login is too much for a repair usually not needed. And `tutor where` names a
  tutor on another node instead of calling it `stale`, which it did because it
  asked whether that pid was alive HERE -- about a daemon listening perfectly
  well over there, on the machine the question is typed on.
  `board/test/agents.py`.
- **The verdict is painted on the student's own answer, and amber is the
  default.** The newest reply in a question's run decides it — `correct` is
  green, `wrong` is red, and every other reply to working is amber, because most
  replies in a doing sitting and most in a walkthrough are neither right nor
  wrong. `--ask` is that amber and `--note` is not: `--note` is the blue of an
  aside, and what was asked for is yellow. A question with no reply yet is
  painted **nothing** — waiting is not a verdict, and the pulsing strip is what
  says so. The verdict is part of the turn's identity on the page, so a node
  already on screen takes the colour when the reply lands instead of keeping the
  one it was born with, and the board holding the working is painted with it
  because that is what a person scrolls back to. `verdictOf` in `board.js`,
  `board/test/mine.js`.
- **A correction revises; a second answer is a second answer.** A send asked
  `answering.latest` — the newest turn on the question, of any kind — so every
  typed answer overwrote the one before it, and a Galois evening spent entirely
  on card 0001 kept the last of four. `correctingTurn` is the narrower question
  and the right one: the box is correcting an answer exactly when an answer was
  loaded into it, and it is cleared by a send, by emptying the box, and by
  moving to another question. Everything typed into an empty box is new and is
  kept, in the order it was given, under the feedback it replied to — a turn
  sits under the card it answers but never above a card written before it — and
  labelled *answer 2 of 3*, which is the wording the boards already use for a
  second page of ink.
- **A delivered manuscript lands in the workspace that asked for it.** The job
  carries `## Delivery` with one absolute `landing:` line —
  `manuscript.landing_for`, read by `jobspec.landing` through `_path_value` —
  and `stages/delivery` places a second copy of every artifact there, appending
  nothing, and keeps its own under `OUT_DIR`. The line names the PAPER'S OWN
  directory, which is what lets a revision land over the document it corrects
  rather than beside it under a slug of a title that has drifted. Not a setting:
  one harness serves every workspace, so `PAPER_OUT_DIR` cannot be each asking
  workspace's own. Absolute, because the factory cannot resolve a relative path
  against a root nobody named. It never raises — a landing that is relative or
  unwritable is recorded and the paper stays DELIVERED, the rule a missing
  pandoc already gets — and re-delivery is content-addressed, so a job run twice
  copies nothing twice. The do-not-rewrite list skips `feedback/`, `parts/`,
  `sections/` and `report.md`: telling the factory not to rewrite its own report
  is telling it the report is the paper.
- **The library reader takes ink.** Each page carries
  `data-ann="doc/<id>/p<n>"`, `annotate.js` attaches to it, and the pen is off
  until asked for so a long document still scrolls. `send` is never set from
  that page — ink on a document is a complaint about the document and becomes a
  turn when the note goes. The marks already on it arrive **with its pages**,
  through `library.ink`, because that page opens no sitting and has no live
  payload to read them out of.
- **The board's suite runs the factory's.** The two repositories hold one seam
  and only the board's suite is a habit, so `test/all.sh` runs
  `projects/Paper-Writer`'s tests last, and skips loudly where it is not checked
  out. `test/revising.py` checks the other direction, field by field.
- **`--help` on a subcommand is the dispatcher's, not the command's.** Answered
  before the repository is found, and only in the first position: further along
  it may be the value of an option. It exists because `board write --help`
  reached `cmd_write`, which drops anything option-shaped, read an empty body off
  the terminal and put a blank card on a lesson with no undo.
- **A posed problem is asked twice on its own card.** Statement, definitions,
  then the question again as the last line — because the definition list sits
  between the first asking and the board they write on. And the write-up is part
  of the turn that agrees an answer: `board hw use`, transcribe, `board hw file`,
  `board hw build`, before the next problem is posed. Both are in `TEACHING.md`,
  in `sense.METHOD_SENSE` and `sense.WRITEUP_SENSE`, and in `test/teaching.py`
  — which now actually runs the block that guards them, having imported
  `sense.py` by path under a name of its own for long enough that every check in
  it was being skipped.
- **A revision is not a new paper, and the factory now knows it.** A job
  carrying `## Revision` skips gathering, grounding, planning, the argument map
  and outlining; `stages/revision.py` splits the delivered Markdown on its own
  headings into the sections the editor works on, and the anchored-edit loop
  changes what the feedback names and nothing else. The outline gate is skipped
  because it asks whether a proposed plan is a well-formed manuscript, which is
  a question about a document that does not exist yet.
- **The job names three things and all three are load-bearing.** The
  **source**, never the rendering — `library.py` puts the PDF in `rel` because
  that is what goes on the glass, so the record carries `source` beside it. The
  feedback file. And the **workspace** the other two are relative to, because
  the factory is another workspace and cannot resolve a relative path against a
  root nobody named.
- **A delivered section is not re-budgeted.** Its budget is the length it
  already is, and `length.check` takes `absolute=0` from that path: a forty-word
  data-availability statement is the right length, and a floor telling the
  editor to grow it is a gate asking for invented content.
- **Ink is a complaint.** `library.marks` reads the strokes already stored
  against `doc/<ident>/p<n>`, a note carries the marked pages and the picture of
  each, the send button is live with an empty box, and the marks are recorded as
  handed over. A document is asked for under both names it has — the drawer's
  and the library's — because it is one document and its ink is its ink.
  `writing.ann_doc_page` is the one place a key is taken apart.
- **Fifty documents cost 0.74 s to open cold on the shared home**, 0.41 s on
  local disk, 0.1 s reopened, and 0.21 s on a machine with no poppler — where
  every document is still listed with its title, kind, formats and staleness,
  and only the page count is missing. Measured, and in `board/README.md`.
- **The aim of the open sitting changes in place.** `POST /aim`, `board aim`, and
  the five aims that need no scope in the sitting-kind chooser. Nothing is
  archived, no tutor is replaced, and the tap wakes a turn because the tap is the
  instruction. `board/test/aiming.py`.
- **A document is a PRODUCT, not an aim, and any sitting can be asked for one.**
  `POST /writeup` carries `paper` or `slides`, changes no aim, archives nothing,
  replaces no tutor and writes nothing into the transcript — a student turn with
  no card coming is what leaves the board waiting for one. Two controls in the
  sitting-kind panel, drawn from `WORK`'s own words, and that row is never
  hidden: a review and a walkthrough are the two sittings the `for:` row leaves
  out and the two where a write-up is worth the most.
- **It lands in the library, and the board says so.** The turn writes no card at
  all — a make sitting shows sections because there the document IS the evening;
  one asked for alongside a lesson must not push the lesson off the glass. So
  `tutorboard/writeups.py` is the record: one file per ask under `live/writeups/`,
  three states, a row in the chrome strip. The state is **derived from
  `library.stamp` and then frozen**, which is `missions.py`'s reasoning — nothing
  is alive to report it, and every later document also differs from the stamp
  taken at the ask. Reading it retires the row and the server remembers. **An
  empty library and an unreadable one are different values**, `[]` and `None`:
  crediting an ask with every document a workspace already had, because the
  stamp came back empty by accident, is the one wrong answer this can give, so
  nothing is derived from `None` and the ask runs to its two-hour ceiling.
- **A writeup turn runs fresh and on a doing turn's clock.** `doing_now` and
  `turn_plan` take it off the SIGNAL, because the sitting's aim deliberately has
  not moved: a paper with a LaTeX build on a teaching turn's fifteen minutes is a
  turn killed half way. Fresh for a revision's reason — a lesson resumed into a
  write-up is exactly the narration a write-up must not be.
- **How a document reads and what it covers are two questions.** The refusal
  answered both with one sentence, so *"a deck about the four things this sitting
  covered"* had no phrasing anywhere that the rule did not refuse. Never a
  narration of the sitting, unchanged. Scope may be the box, the chapter or the
  evening; where it is the evening it is the concepts the cards covered, read
  back with `board recap --all`. Both halves hold in all four places —
  `sense.MAKE_SENSE`, both `config.AIM_MEANS` entries, `TEACHING.md` — because
  two of the four worded the old refusal differently.
- **A family default is a style, never an instruction to write code.**
  `config.aim_for` drops a doing aim inherited from `atlas.json` and the sitting
  runs on stance, which is `teach` unless the workspace said otherwise in
  writing. The rule it follows from is already in `read_config`: writing the code
  for somebody who wanted to learn it is the one failure that cannot be undone by
  the next card, and a sentence about a directory is not a repository asking. A
  teaching default still applies. A tapped aim and a declared one are untouched.
- **A `#!` line is as good a declaration as a suffix.** `walk._walkable` reads a
  shebang where there is no extension, and the interpreter it names is what
  decides which language's patterns look for a definition inside it — so
  `bin/coli`, `bin/coli-up`, `bin/coli-ask` and `bin/coli-code` are walkable, and
  `libr-local-llm` offers sixteen files rather than six. A file with neither a
  suffix nor a shebang declared nothing and is still not machinery.
- **`libr-local-llm` has a written map.** Nine boxes in the project's own words —
  the everyday server, the consultant, the five colibrì commands, the engine, the
  measurement campaign, the fleet — and `board map --check` says it is true. Its
  `.gitignore` had `live/`, which git cannot see past, so it is `live/*` plus
  `!live/map.json`, after the `*.json` rule or that rule wins.
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
  it; six `tutorboard.json` files still carry one and it means nothing.
- **And the six changes before these.** `scripts/tool.sh` holds `tool_prefix` and
  `tool_root`, and both scripts read them. `tutorboard/fenced.py` is the one
  fence list and `reading.py` reads it. `plan._collect` takes `STEP` and `- [ ]`
  together in file order, `_distinct` settles the label collisions, and
  `MAX_STEPS` is 24. `course/results.py` and `/result/` put a figure on the
  glass. `map._loose_docs` gives a written map its document boxes, eight at most.
  `paper1-trd-prediction` has its PDFs and `reading.py` finds them with no board
  change at all.
