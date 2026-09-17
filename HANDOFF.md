# HANDOFF — the iPad is where the work is directed from

**The aim is one sentence and it is a test: the only reason to open the laptop is
to type code a card told you to type.** Everything else — choosing what a sitting
is for, choosing who writes it, starting the local model, putting a workspace to
work, reading a document, marking it up, complaining about it — is a tap.

**Most of the pieces are in and none of them has been used in anger.** A document
can be written up, listed, read on the glass, marked up, complained about in
words or in ink, and revised by whichever machinery made it. A student's own
answer carries its verdict and every attempt they typed is kept. The local model
can be chosen for a sitting, started from the glass, watched through four states,
and handed a job in a workspace nobody is looking at.

**What is left is what still sends somebody to a keyboard**, and that is the next
section.

`board/README.md` is the architecture. This file says what is left.

---

## How to work from this file

**ONE ITEM PER SESSION, AND THE ITEM COMES OUT OF THIS FILE WHEN IT IS DONE.**
Nobody has to ask for that. *"Look at HANDOFF"* means all of it:

1. **Take the lowest-numbered item under *What to do next* that is a build.** It
   is the lowest-numbered one on purpose — the numbering carries the order things
   have to land in, and each item says what it depends on where that matters. If
   the owner names a different one, that wins.
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

**Two of them are not builds and do not come out this way.** Item 8's last part
is a standing rule — it lands in `TEACHING.md` and `sense.py` and then it is a
*Settled* entry like anything else. Item 10 is a list of evenings in front of the
thing, and only the person holding the iPad can strike those.

---

## Before anything

- `bash board/test/all.sh` — 78 suites, about twelve minutes. Green before and
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

**`projects/libr-local-llm` has its own handoff and it is still the live one.**
The five pieces it asked for against the board are shipped and are under
*Settled* below; what is left in that file is the diarization job itself, which
is item 11 here.

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

**Items 1, 2 and 3 are one piece of work** — a *mission* — and they land in that
order: a mission cannot be told to ship itself before it is a record, and it
cannot be a record before the board knows which workspaces are fenced. Item 4 is
independent of all three, and is where a document is corrected; item 5 is where
a lesson turns into one, so those two are worth reading together. Item 6 is the
answer box and is independent of everything. Item 7 is the meeting deck, which
reuses item 4's reader and deliberately does NOT reuse its feedback route. Item 8
is the map, and the last part of it is a standing rule rather than a task. Item 9
is item 8's other half and must land after it, because the refactor renames the
boxes its TODOs are attached to. Item 10 is the verdict a person can feel, and it
settles a question item 12 has been holding open. Item 11 is the acceptance test
of 1, 2 and 3 and is also the job all of it exists for. Item 12 is not a build.

---

## What to do next

### 1. The board must know which workspaces hold a fence, and say so before the tap

**The want:** *"if I'm in PSYCH-ASR on the iPad, we should know that there is a
phi folder that I can't let claude or any outsourced AI model see."*

**Now.** The fence is real and it is per-PATH. `ai-config/policy/phi.py` answers
`names_phi(text)` and `bash_is_blocked(command)`; the per-assistant adapters in
`ai-config/adapters/` translate a tool call into one of those two; and
`tutorboard/fenced.py` is the list of directory names nothing in the board may
point at, read by `course/reading.py` and `manuscript.py`. All of that holds.

**What is missing is per-WORKSPACE and it is a question about what a person can
see.** Nothing anywhere says *this workspace holds fenced content, and one
assistant on this machine may read it*. So the `who:` row offers `claude` and
`colibri` side by side in PSYCH-ASR exactly as it does in Galois-Theory, and the
only thing standing between a tap and a hosted model reaching for session
content is a hook the person cannot see.

**Want.** A workspace says whether it holds a fence, and the chooser says which
assistant may read it. `fenced.NEVER` is the list and the answer is a directory
walk one level deep, which is what `machines.workspaces` already does.

**Decide, and do not take the easy half.** Refusing a hosted assistant outright
in a fenced workspace is the wrong answer and must not be written: the teaching
thread on that same code is a hosted conversation today and works, because the
fence stops it reading `phi` rather than stopping it existing. What is owed is
**visibility plus a default**: the row says the workspace is fenced and names the
one assistant that may read it, the mission dispatcher defaults to that one
there, and a hosted pick carries a line saying what it will not be able to open.
The protection stays where it is.

**Check.** `board/test/colibri.py` owns the registry half; the fence half
belongs beside `test/plan.py`'s fenced-document case, which already asserts that
a document inside a fenced directory is offered nowhere.

### 2. A mission is a thing, and closing the iPad does not end it

**The want:** *"when I put colibri or anything on a mission, just because I close
the iPad doesn't mean that should end. Next time I open the iPad and access the
board, that mission should still be going or notify me somewhere if it's done."*

**Now.** `POST /elsewhere` writes the task into another workspace's inbox and
starts a daemon there. The daemon is detached — `setsid`, stdin on DEVNULL — so a
closed lid genuinely does not touch it. What does not exist is any RECORD that a
mission was dispatched, so:

- Nothing says a mission is **still running**. `news.elsewhere` reports a card
  newer than the last time anybody looked at that workspace, which is the right
  answer for a finished turn and says nothing at all about one in flight.
- Nothing says a mission **failed**. A failed turn is reported in the busy strip
  of that workspace's own board, which is precisely the board nobody is looking
  at. It is invisible until you go there.
- Nothing survives the two ways a mission really dies. The daemon belongs to the
  allocation that started it, so an allocation ending takes it with it — the rule
  already settled for the board — and **a colibrì turn runs inside the SERVE
  job's allocation**, because `coli-code` steps into it with `srun --overlap`. So
  a colibrì mission's ceiling is the serve job's walltime, 8 h by default and 9 h
  on `c3_short`. A mission longer than that cannot finish, and `coli-up -t` is
  the only lever.

**Want.** A mission is a record in the workspace it is about, and every board can
read every workspace's. It carries what was asked, which assistant, when it was
dispatched, whether it is to ship itself, and how it ended. Three states a person
can act on: **running**, **done**, **failed**.

**Where.** Under `live/`, per workspace, beside the records already there —
`agent.json`, `push.json`, `state.json` — because that is the directory a board
already reads and no repository tracks. `news.elsewhere` is the walk to copy and
the surface to widen: the newsbar is already *"work that came back while you were
elsewhere"* and a mission in flight is the same sentence in the present tense.

**The one thing not to do.** Do not put the mission list in the browser's memory
or in this board's process. The whole point is that it is there when you come
back on another device, on another node, tomorrow.

**Check.** A new suite, or `test/elsewhere.py`, which already owns both halves of
this sentence. Assert: a dispatched mission is on disk and readable from a board
serving a different workspace; a mission whose daemon has gone reads as failed
rather than as running; and a mission that has landed a card reads as done and
comes off the list when it is looked at.

### 3. A mission can be told to ship itself, and the diff is checked before it goes

**The want:** *"when I put anything on a mission, I should have the option to tell
it to ship its changes once it is done - I don't know if colibri is capable of
doing that, but the tutor certainly should be once colibri is done."*

**Now.** `board push` exists, commits and pushes, does not end the session, and
is written to run unattended — *"the tutor may push on its own"*. What is missing
is the instruction, the guarantee, and one check that is not in the repository at
all.

**Want.** A switch on the dispatcher, carried in the mission record, and honoured
when the mission finishes.

**Whose job the ship is, and the owner has already answered it.** Not the local
model's: it decodes at three tokens a second and it is the one assistant that can
read `phi`. So when a colibrì mission finishes, the workspace's ORDINARY tutor is
woken with the mission's own report and ships it — a hosted turn, a second pair
of eyes on a local model's work, and a turn that cannot read the session data
itself. The signal mechanism is the same one item 2 uses, and the one `/handover`
already runs on.

**AND THE CHECK THAT DOES NOT EXIST YET, which is the sharp end of this.**
`research/PSYCH-ASR/.gitignore` keeps `/phi/` out of git and `test/tracked.py`
audits it, so a diff cannot contain a phi FILE. A diff can absolutely contain phi
CONTENT: a test fixture, a hard-coded example, a docstring quoting a transcript —
written by the one assistant that was allowed to read it, pushed by a turn that
was not. `ai-config/policy/phi.py` already answers exactly this question and
nothing calls it: **`names_phi` is not invoked anywhere in this repository.**

So `board push` runs the diff past `names_phi` in a workspace that holds a fence,
and refuses by name when it matches. A machine check with no model's judgement in
it, which is what lets the hosted turn ship at all. `worktree.busy_reason` is the
shape: say what is in the way, change nothing, and write it where the board can
read it.

**Decide.** Whether the refusal is per-workspace or everywhere. Everywhere is
cheaper to reason about and costs a regex over a diff; per-workspace is faster and
is one more thing that can be wrong. Take it deliberately.

**Check.** `test/tracked.py` is the suite that already exists to stop PHI reaching
a remote, and this is the same failure one step earlier. A fixture diff carrying a
transcript line must be refused, and the refusal must name the file.

### 4. A document is corrected, or overhauled, without leaving the page it is on

**The want, and it was asked as a question:** *"let's say I'm working in
PSYCH-ASR, and want to view the presentation on stage2. That presentation needs
an overhaul now that we plan to use colibrì. But can I view it in a slick UI very
easily, and complain to the tutor/agent about things about it that need to be
fixed, and will the tutor just fix, recompile, and make that fix and it'll appear
right in front of me?"*

**Most of that chain already answers yes, and it was checked rather than
assumed.** `/library` finds that deck — `docs-stage2-reference-walkthrough`, *Did
the Computer Hear It Right?*, 33 pages, `.pdf` beside `.tex`, not stale — and the
fence does not catch it, because `fenced.NEVER` matches a DIRECTORY named
`stage2` and this is a stem in `docs/`. It reads in the same rasteriser the board
uses, takes ink, and `POST /library/feedback` writes the note and dispatches the
revision in the same request. It is not a Paper-Writer document, so the board
takes it: a `[revise]` line, a fresh turn that writes no card, and
`HEADLESS_REVISE_PROMPT` telling it to edit the source **and rebuild the PDF**,
which the tutor's own grants allow.

**Three things answer no, and each is a missing piece rather than a missing
mechanism.**

**(a) It does not appear in front of you.** `library.js` does not poll: `load()`
runs after a send and on `visibilitychange`, and the open reader never re-fetches
at all. The render cache is keyed on the PDF's modification time — `paper._digest`
— so a re-fetch WOULD get the new pages. Nothing asks for one.

*Want.* The page says a revision is in flight, and re-draws when it lands.
`test/hanging.js`'s charter is *"nothing the reader can be waiting on is allowed
to be silent"*, and this page has no version of it: you send, and the only thing
that ever changes is a line saying the note was filed.

*Where, and do not reach for the stream.* A stamp, not a subscription:
`GET /library/stamp` returning one hash of every document's `rel`, mtime and size
is cheap enough to ask every few seconds while the page is visible, where
`/library.json` walks the workspace and reads titles out of sources (cached 30 s
in `CACHE_SECONDS`). **Do not put the hub's SSE payload on this page.** It opens
no sitting on purpose, and that payload is the lesson's.

*And the reader keeps the reader's place.* `read(doc)` sets
`els.readerPages.scrollTop = 0` and rebuilds every page. A re-draw that throws a
33-page deck back to page 1 after a one-line fix is its own defect.

*Decide: what happens to the ink.* Marks are keyed `doc/<id>/p<n>` and come back
with the pages through `library.ink`. After a correction that is right. After an
overhaul that reflows the deck, the ink on page 7 is about something that is no
longer on page 7. Either it is cleared when the page count moves, or it is kept
and the page says out loud that it was drawn on an older version. Both are
defensible; choosing by accident is not.

**(b) You cannot read what it says it changed.** The turn appends
`## What was changed` to the feedback file, which is the answer to *did it do what
I asked* — and `library.notes` returns names, sizes and dates, not a word of the
contents. So the page can say a document has had three rounds and cannot say what
any of them did, and the record lives in a file the iPad cannot open.

*Want.* `GET /library/note/<id>/<name>`, and the rounds already listed under each
document become readable. An id and a name matched against what `library.notes`
found, never a path from the browser — the rule the rest of that route follows.

**(c) An overhaul is refused by design, and that refusal is correct.**
`HEADLESS_REVISE_PROMPT` says to keep the document's structure, its names for
things and its claims: *"Do not start it again and do not widen it."* That is
exactly right for a correction and exactly wrong for *"that presentation needs an
overhaul now that we plan to use colibrì."* There is no second ask, so the only
route to an overhaul today is a terminal.

*Want.* Two asks from one panel. **Fix this** is what exists. **Rework it** is
new: the same feedback file and the same record, a `[rework]` signal, and a
prompt that may restructure, cut, reorder and rewrite. It requires a sentence
saying what the document is now FOR, which is `/direction`'s shape one level
down — an overhaul with no new purpose in it is a rewrite for its own sake.

Two things a rework must do that a revision does not:

- **Stay a library turn.** No card, no sitting, no `state.json`. The charter of
  this page is that correcting a deck cannot interrupt somebody's proof, and an
  overhaul is a longer turn rather than a different kind of interruption. **Do
  not route it through a `make` sitting:** every path into one calls `board
  open`, which archives the lesson.
- **Commit the source before it starts.** An overhaul replaces thirty-three pages
  and git is the only undo there is. `docs/*.tex` is tracked, so one commit of
  the source before the turn touches it makes the whole overhaul one diff. A
  rework against an uncommitted source is refused by name, the way
  `worktree.busy_reason` refuses a push mid-rebase.

**Check.** `test/library.py` owns discovery and the note; `test/revising.py` owns
which machinery takes which document. Assert: the stamp moves when a PDF is
rebuilt and not otherwise; a re-draw keeps the page the reader was on; `## What
was changed` is readable through the route and a name that is not in
`library.notes` is refused; a `[rework]` line reaches the inbox carrying the new
purpose, and the prompt that turn is given does **not** contain the do-not-widen
sentence; and a rework against an uncommitted source is refused rather than
started.

**And the half no test reaches:** whether that reader is in fact *slick* on a
tablet. It is two taps from the board — `▤ library · papers & decks` in the bar
menu — and no person has read a real document on it. That is item 6.

### 5. Any sitting can be asked for a paper OR a deck of what it covered, at any moment

**The want, and it was asked as a question:** *"let's say I open up libr-local-llm
and I want to learn how colibrì works. Can I have a tutoring session where I'm
walked through simple lessons to understand this and how we utilize the cluster
hardware, and at any point can I have a presentation or paper written up going
through the things we talked about in that tutoring session? Can I do that in ANY
tutoring session?"*

**The lesson half mostly answers yes.** `libr-local-llm` is a workspace the walk
finds, `library` offers `DESIGN.md`, `FLEET-BUILD.md`, `P0-STATUS.md` and the
fleet-walkthrough deck, and the `paper` and `slides` aims, the `make` method and
`writeups/<slug>/` all exist — so both products have machinery behind them
already. **The asking half answers no, for a paper and for a deck alike, and it
is refused in writing.** Four things, and the first is the one that matters.

**(a) It is refused outright, in four places, and it is one rule doing two jobs.**
**BOTH PRODUCTS, EVERY TIME.** A paper and a deck are the same ask with a
different file at the end of it — *"have you write up papers"* and *"build me a
presentation about it"* are the two sentences the `make` sitting was built for —
so every change below lands in **both**, and two of the four places word the
refusal differently, which is exactly how a rule gets fixed in one and left in
the other:

| where | what it says now |
| --- | --- |
| `sense.MAKE_SENSE` | *"AND ITS SCOPE IS THE BOX, NOT THE EVENING … not about everything that came up while you were looking at it"* — shared by both products |
| `config.AIM_MEANS["paper"]` | *"It is not a write-up of this sitting."* |
| `config.AIM_MEANS["slides"]` | *"it is not a record of this sitting."* |
| `TEACHING.md` | *A make sitting: the product is a document, not an answer* — *"The scope is the box they tapped, not the evening"* |

All four were written against a real failure: a tutor that has just spent three
hours teaching, asked to write it up, writes up the three hours — first person,
*"as we saw above"*, the hand-check narrated instead of the concept explained.

That failure is about **content** and the rule against it is right. What got
banned alongside it is **scope**, and scope is exactly what was asked for. Those
are two different sentences welded into one refusal — the same shape as the
condition that set `awaitingReply` and popped the transcript. Split them:

- **Content is always the subject.** No first person, no *"we covered"*, no *"the
  student then"*, no reference to the sitting, its cards or its questions. A
  concept taught by hand-checking three examples is explained and its examples
  shown; the hand-check is not narrated. **Unchanged.**
- **Scope may be the box, the chapter, OR THE EVENING.** When it is the evening
  the scope is *the concepts the cards covered* — the topic list, off `board
  recap` — and each is explained from scratch for somebody who was not in the
  room. Not the order it was taught in, not the questions, not the answers.
  *"A deck about the four things this sitting covered"* and *"write those four
  things up as a paper"* are both legitimate asks, and there is currently no way
  to phrase either that the rule does not refuse.

**(b) Asking for a document is an AIM CHANGE, so it is refused wherever changing
the aim is refused.** `paintAim` hides the whole `for:` row when
`sittingKind` is `review` or `walk`, and `WRITEUP_SENSE` is deliberately withheld
from both. So in the two sittings where a write-up is worth the most — you have
just traced `coli-code` line by line, or just been drilled cold over a scope —
there is no way to ask for one at all. That is the answer to *"in ANY tutoring
session?"* and it is no.

*Want.* **A document is not an aim.** An aim says what the sitting is FOR; a
paper or a deck is a *product* you can ask any sitting for without changing what
it is for. So it is its own act — `POST /writeup`, carrying **`paper` or
`slides`** and optionally what it is about, defaulting to what this sitting has
covered — which changes no aim, archives nothing, replaces no tutor, and is
therefore available in a review and a walkthrough like everything else.

**Two controls, not one, and not a second question after the tap.** Which of the
two is known at the moment of tapping, and `config.AIMS` keeps `paper` and
`slides` as separate words for exactly this reason — *"what the tutor has to do
differs and the word for it should not"*. **The words already exist and must not
be reinvented:** `WORK` in `board.js` carries `{aim: "paper", makes: "paper",
label: "Write it up as a paper"}` and `{aim: "slides", makes: "slides", label:
"Build me a deck about it"}`. Draw the control from that table, filtered to those
two, the way `aimWays` already filters it — one set of words for the map's sheet
and for this, or the two drift.

*Decide: where it lands while it is being written.* A `make` sitting puts the
sections on the board one at a time, because there the document IS the evening;
that stays exactly as it is, for a paper and for a deck. One asked for
**alongside** a lesson must not push the lesson off the glass — so it lands in
the library, the board says it is being written and says when it is there, and
correcting it is item 4's loop. Take that deliberately rather than by streaming
sections, or slides, into a transcript somebody is mid-proof in.

**(c) The default style fights the ask, in this workspace above all.**
`libr-local-llm` declares only a name, so `aim_for` falls through to its family's
default in `atlas.json`, which is `build` — and `stance_for` is therefore `do`. A
plain lecture opened there is a DOING turn: the tutor writes code and reports.
Being taught costs a tap on `teach` in the `for:` row first, which is one tap and
is the wrong way round for a workspace somebody arrives at wanting to understand
it. Decide whether a family default should apply to a sitting nobody chose a
style for, or only to one opened from the map.

**(d) The thing most worth walking through is not offered.** `walk._walkable`
keys on the file EXTENSION and `walk.SOURCE` lists twenty-one of them, none of
which is *none*. `bin/coli-code`, `bin/coli-up`, `bin/coli-ask` and `bin/coli`
are extensionless bash scripts with a shebang, and they are the entire surface of
colibrì — so a walkthrough of that workspace offers six files and not one of them
is the one you would ask for. A shebang is as good a declaration as a suffix and
is what `file(1)` would use.

*And the map is undrawn.* `projects/libr-local-llm/live/` is empty, so there is
no `map.json`: no picture of the project, and no box to tap to open a sitting
about the engine or the gateway. The plan's five steps are all build tasks — *WEB
ACCESS FOR THE CODING AGENT*, *THE VLLM PATH* — so the contents drawer offers
engineering work rather than lessons. `board map` is what draws one and
`map._unclaimed` gives it its document boxes; nothing needs building, it needs
doing once.

**Check.** `test/teaching.py` owns the rule that the places agree, and it is where
the split content/scope wording is asserted — **for a paper and for a deck
separately**, because `AIM_MEANS` words the refusal differently in each, and
explicitly that the anti-narration half is still refused in all four places.
`test/aiming.py` owns a route that changes a sitting without losing it and is the
model for `/writeup`; assert both products, and assert both work in a review and
a walkthrough, where the aim row does not appear. `test/walk.py` owns what is
offered: assert that a `#!` script with no suffix is walkable and that a README
still is not.

### 6. The answer box renders as it is typed, and what was sent stays where it was typed

**The want, in two messages:** *"when I'm typing a response to a tutor, I want to
be able to type latex commands in the typing box — like \gamma, etc. — and have
that render as I type it. And then when I send it, have it stay rendered that way.
I still like how everything else is rendered dyslexic friendly."*

*"The typed prompt also disappears after I send it, unlike the written board when
I send that. I don't want the typed prompt disappearing — I want it rendering just
like you said."*

**The second message is the frame for the whole item, and the comparison in it is
exact.** Sent ink stays where it was made: `paintBoards` draws a board per
attempt with the ink still on it, down the page, and the live surface stays open
underneath — *"I want the actual writing board containing my response"* is why.
Sent typing leaves **nothing** where it was made: `say()` empties the box, and
the answer becomes an entry in the transcript instead. One half of the panel
keeps what you handed in and the other half clears it, and the person is looking
at the half that clears.

**Half of this already works, and it is worth knowing which half before building
anything.** Measured by driving the real page: a typed answer goes through
`renderMarkdown`, which parks `$\gamma^2 = 2$` into a `span.math-raw`, and
`reconcile` pushes **every** newly inserted node into `freshNodes` — a card or a
turn, no distinction — which `typeset` then walks with `$`, `$$`, `\(` and `\[`
and 64 macros out of `macros.js`. So **a sent answer containing `$\gamma^2 = 2$`
already comes back typeset in the transcript, today.** Nothing needs building for
the "stay rendered" half.

**Three things do not work, and the last is a decision rather than a build.**

**(a) Nothing renders while you type, and nothing ever can in that box.**
`#saybox` is a `<textarea>`. A textarea holds characters and no markup, by
definition, so there is no version of this that renders inside it.

*Want.* A preview under the box that renders on a debounce and says, in advance,
exactly what the transcript will show.

*And do not reach for the clever option.* Replacing the textarea with a
`contenteditable` renders in place and costs everything that textarea carries:
iOS autocorrect and its undo stack, selection behaviour under a thumb, the
`input` handler that drives `saveTextDraft` and `correctingTurn`, `autosize`, the
⌘-Enter send — and `test/mine.js` and `test/typed.js` both drive that element
directly. A preview loses none of it.

*One renderer, or the preview lies.* `renderMarkdown` then `typeset`, the same
pair a card goes through, on the same debounce the draft save already uses. Two
renderers would differ on exactly the input somebody is squinting at.

*Only when there is something to show.* A preview that is always there doubles
the height of the answer panel for everybody who never types a formula. It
appears when the text contains a delimiter or a backslash command, and not
otherwise.

*And the face stays where it is, which is the half that was asked to be left
alone.* The reading face is `body.dataset.face` — OpenDyslexic by default — and
KaTeX ships its own fonts, so prose is dyslexic-friendly and mathematics is not
touched, by construction rather than by a rule. The preview inherits that for
free. **Do not give it a font of its own**, and `test/typeface.js` is the suite
that already asserts the reading face reaches prose and never the maths.

**(b) The sent answer does not stay where it was typed.** `say()` runs
`els.saybox.value = ""`, so the words leave the place the person is looking at.
They come back only on a *reopen* of that question, through `restoreTextAnswer`,
and they come back as raw source in a textarea rather than as the mathematics
they were written as.

*What was checked, so nobody hunts for a phantom.* Nothing deletes a typed answer
from the transcript. The `items.pop()` in `render` is ink-only, `paintSuperseded`
touches `[data-card]` and never a `.mine` node, and every attempt is kept and
labelled *answer 2 of 3* — and that entry is already rendered through
`renderMarkdown` and KaTeX, and already sits directly above the writing surface.
The disappearance to fix is the BOX, not the transcript. (The other half of the
same old report — *"it disappears once the tutor response comes in"* — was the
`answering.latest` overwrite, and that is fixed and shipped; an iPad still
serving a shell older than `board-shell-v126` will go on showing it.)

*Want.* **The typed half keeps what it sent, in place, rendered — the way the
slate keeps its ink.** After a send, the block above the box holds the answer as
mathematics and prose rather than as source, and the box under it is empty and
ready for the next thing. A second answer pushes the first up, the way a second
page of ink gets a second board.

*And this is the same build as (a), not a second one.* One rendered block above
the box: a **preview** of what is being typed before the send, and the **record**
of what was sent after it. That is what makes the two halves of the panel finally
symmetrical — box and rendered block against slate and board — and it is why
these are one item.

*Decide: what a tap on it does.* The slate's answer is that going back to an
earlier board hands the ink back on a surface that can take another line, and
`restoreTextAnswer` is the typed counterpart already written. So a tap on the
rendered block should load it back into the box for correction — which sets
`correctingTurn`, which is what makes the send a revision of that answer rather
than a new one. Wire it to the function that exists rather than to a new one.

**(c) A bare `\gamma` renders nowhere, and never will without a decision.**
Verified in the same run: `$\gamma^2 = 2$` is typeset and the `\gamma` beside it
with no delimiters stays literal. On an iPad keyboard a `$` is a hunt, so this is
the whole of why it feels like the feature is missing.

Three ways, and one of them must not be written:

- **Auto-wrap anything that looks like TeX.** *Refused.* `\d+` in a regex,
  `C:\temp`, and a shell escape are all backslash commands to a pattern and none
  of them is mathematics — and this board is used in code workspaces, where that
  is what a person is most likely to be typing.
- **Make the `$` cost a thumb rather than a keyboard hunt.** A one-tap `$…$` on
  the answer panel that wraps the selection or drops a pair and puts the caret
  between them. Cheap, obvious, and nothing can misread it.
- **Say what is wrong rather than doing nothing.** A backslash command sitting
  outside any delimiter is almost certainly a mistake, and the preview is exactly
  where to say so: *"`\gamma` will not render — wrap it in `$…$`"*. That is the
  board's own rule, the same one `board write` follows when it refuses a card
  over 450 words instead of trimming it silently.

Take the second and the third. They compose, they are each one control, and
neither of them can be wrong about what somebody meant.

**Check.** `test/typed.js` owns the answer panel and `test/mine.js` owns what
happens to an answer after it is sent. Assert: with `$\gamma$` in the box the
block holds a `.katex`; with plain prose there is no block at all; what it shows
before the send is what the transcript shows after it, because it is the same
renderer; **the words are still on the glass on the frame after the send, and
still rendered**; a tap on them loads them back into the box and the next send
revises that answer rather than starting a new one; the prose carries
`body.dataset.face` and the `.katex` does not; and a bare `\gamma` raises the
hint rather than silently rendering nothing. `test/markdown.js` and `test/macros.js` own the renderer and
the macro list either side of it — `test/markdown.js` matters more than it looks,
because the renderer parks math and code before any markdown parsing and
restores it afterwards, and every change to it needs a case proving that still
holds.

### 7. The meeting deck: one at a time, annotated for DIRECTION rather than for correction

**The want.** *"I have generally two — sometimes three — meetings per week to talk
about my research… We should somehow be keeping track of our most recent updates
in ALL courses/projects, and I want to be able to select which projects meeting
notes are generated for. From that list, I'll select the meeting notes I care
about, I want a presentation like the ones made for PSYCH-ASR created and rendered
for me, which I want to be able to give feedback on in the same way we talked
about giving feedback on presentations earlier. I want to be able to annotate
these presentations, but NOT to give feedback on them in terms of the
presentation — they're just for a meeting to communicate what I've been working
on. My mentors, seeing this presentation, will give me suggestions on new
directions to take — THAT'S what these annotations will serve as — the agent
should use them to decide which new directions we will take after the meeting's
feedback. We're also not gonna save every presentation pertaining to meeting
notes — this is a one-off communication tool. BUT what we will do is save each
most recent one… if I elect to make a new one, then that new one REPLACES the old
one. So we only save one at a time."*

**Five stages. Two and a half exist. The two decisions in it matter more than the
code, and one of them is a trap.**

**Stage 1 — what landed in every workspace. EXISTS, and it is the expensive
half.** `meeting.gather(base, ws, since_ts)` already does, per workspace,
`landed` / `touched` / `closed` / `meaning` / `blocked` / `nextup`: commits by
their own subjects, plan steps that closed, boxes of the written map named the way
the person named them, and what is blocked. `resolve_since` takes a date, a span,
a weekday, or *since the last lot*. **Nothing here needs building.**

And read the charter at the top of `meeting.py` before touching any of it, because
everything below depends on it: *"Nothing here is generated prose. Every sentence
is assembled from something already written down by a person… A meeting note whose
sentences were invented is a meeting note that has to be checked before it can be
used, which is worse than no note."*

**Stage 2 — choosing which projects. EXISTS ONE LAYER DOWN AND CANNOT BE
REACHED.** `meeting.build(base, since_ts, human, want=None, …)` already filters
`atlas.workspaces(base)` by `want`, matching on `id` or `dir`, and refuses with
*"none of those are workspaces in this repository"*. **`POST /notes` never passes
it**, and the front door's sheet asks only *how far back*. So the capability is
written, tested by nothing, and invisible. This is the smallest gap in the item:
one field on the request, and a list of workspaces on that sheet with what each
one has to report since the chosen date — which is `gather`'s own output, so the
list can say *three commits, one step closed* beside each name rather than
offering bare names to tick.

**Stage 3 — a PRESENTATION, not a document. MISSING.** `document.TEX_HEAD` is
`\documentclass[11pt]{article}`, and there is no Beamer path anywhere in
`course/document.py`. The decks this is being compared to —
`research/PSYCH-ASR/docs/stage2_reference_walkthrough.tex` and its `stage1`
sibling — are hand-written Beamer, which is why they have `.nav` and `.snm`
beside them.

*Decide, and this is the first of the two decisions.* **Assembled, not
generated.** A Beamer head in `document.py` and a frame per workspace, built out
of exactly what `gather` returns — no model call, nothing invented. The
alternative is asking a tutor to write the deck, and it must be refused for the
reason `meeting.py` already gives in capitals: a slide you are going to stand
behind in front of mentors is the last place for a sentence nobody wrote. What a
model would add is polish; what it would cost is the one property that makes the
deck usable without checking it. If the assembled deck reads badly, the fix is the
renderer, not a model.

**Stage 4 — reading and annotating it on the glass. MISSING, and the reason is
structural.** `library.documents(root)` walks ONE workspace, and `meetings/` is at
the REPOSITORY root — deliberately, because *"a note about five workspaces filed
under one of them is misfiled"*. So the meeting deck is in no workspace's library:
there is no page-image reader for it, no `data-ann="doc/<id>/p<n>"` anchor, no pen
and no ink store. What exists is `GET /meeting/<name>`, which hands the PDF to the
browser's own viewer — where a stylus does nothing.

*Want.* The same reader, the same pen, the same page addresses, over a document
that belongs to the repository rather than to a workspace. `library.pages` is
already only *"how the file was found"* away from generic — it calls
`paper.pages_of(repo, target, filename, "library", width)`, and the tag argument
is there precisely so a second caller can have its own cache namespace. So this is
a second finder in front of machinery that is already shared, not a second reader.

*And note what has never happened:* `meetings/` does not exist in this repository.
The three stages that DO exist have never produced a note, so stage 1's output has
never been read by anybody.

**Stage 5 — the marks are DIRECTION, and this is the trap. DO NOT WIRE THEM TO
`/library/feedback`.** Everything about stage 4 makes that the obvious next line
of code, and it is wrong: that route writes a feedback file and dispatches a
`[revise]` turn, which would spend a turn *fixing the slides* — polishing a
throwaway communication tool while throwing away what the marks actually said. The
owner's sentence is the specification and it is unambiguous: *"NOT to give
feedback on them in terms of the presentation… My mentors will give me suggestions
on new directions to take — THAT'S what these annotations will serve as."*

*Want.* A mark on a slide is **input to what that workspace does next**. The slide
is already about one workspace — stage 3 builds a frame per workspace — so the
routing is already in the geometry: ink on the TRD-EHR frame is direction input
for TRD-EHR. `writing.ann_doc_page` is the one place a page key is taken apart and
is what turns `doc/<id>/p7` back into a page number.

*Decide, and this is the second decision: proposed, not applied.* `direction.write`
and `POST /direction` already exist per workspace and already do the right four
things — write it at the root, open a new sitting which ARCHIVES the lesson, forget
the last turn's note, and REPLACE the assistant. Two of those are destructive, and
doing them unattended to five workspaces because somebody drew on five slides is
the worst outcome available here. So: one turn per marked workspace, woken with the
marks and the frame they were on, whose job is to **propose** the new direction on
that workspace's board and stop. The person taps it. That also puts the proposal
where `news.elsewhere` will tell them it landed.

**One at a time, and the replacement rule.** `document.next_version(out_dir, stem)`
returns `-v1, -v2, -v3` and the stem is `meeting-<date>`, so today's notes
accumulate and every day starts a new series. The want is exactly one. So the deck
is a FIXED path — one stem, overwritten — and the sheet offers two things: **read
the one from before**, which is what you want in the ten minutes before the
meeting, and **make a new one**, which replaces it.

*And the history comes free, which is worth knowing before somebody builds a
retention scheme.* `meetings/` is tracked — not ignored — so one overwritten path
means nothing accumulates in the tree while `git log` keeps every past deck
anyway. That is the cheap version of *"we're not gonna save every presentation"*
and it is recoverable, which a delete is not.

*One thing to check rather than assume:* the marks are keyed to `doc/<id>/pN`, and
the new deck replaces the old at the same path with different pages. Ink drawn on
last week's slide 4 must not reappear over this week's slide 4. Clear the ink when
the deck is replaced — this is the one document in the system where old marks have
no meaning at all, because the marks were consumed into a direction the moment
they were sent.

**Check.** `test/meeting.py` exists and owns *"a meeting note is assembled from
what somebody wrote, and every claim carries its address"* — extend it rather than
starting a suite. Assert: `want` reaches `build` from the route and an unknown name
is refused by name; the deck compiles as Beamer with one frame per chosen
workspace; every line on a frame traces to a commit subject, a plan step or a box
name, and none of it is invented; making a new one leaves exactly one deck on disk;
the ink store for it is empty after a replacement; and — the one that guards the
trap — a mark on a meeting deck produces a direction PROPOSAL on that workspace's
board and does **not** write a feedback file, does not archive anything, and does
not replace any assistant.

### 8. Three doors, then a family, then a diagram that explains the project

**The complaint, and it is about all three levels at once.** *"It's just an ugly
grid of projects in an inner box that has wacky zooming. On the homescreen, I want
a nice 'Research' option, 'Courses' option, and 'Projects' option, and honestly
something pertaining to vendor/ as well, because who knows when we'll want to
explore external tools in the same way we're exploring everything else with
tutoring sessions. That's the best way to dive into how Colibri works. When I
select one of those four options, I want to see all available
projects/courses/research projects/vendor tools portrayed in again a visually
pleasing way, and then we can go into an individual project map."*

**(a) The front door draws a list as though it were a diagram, and that is the
whole of the complaint.** `home.js` builds ONE SVG plane — a region per family, a
card per workspace, `A_FAM_TOP`, `A_FAM_GAP`, `A_EDGE` — and hands it to
`plane-core.js` to be panned and pinched, with a `fit` button because it cannot be
seen at once. Six families and a dozen workspaces is **a list of six**. A list is
not a diagram, and drawing it on a plane is what produces the wacky zooming: the
gesture layer is solving a problem the content does not have.

*Want.* Three levels, and only the last of them is a plane.

1. **The door:** the families, as large tappable things. `atlas.json` already
   carries them in the order they should be drawn, with a `name` and a one-sentence
   `blurb` each — *"Graduate coursework, taught chapter by chapter."*, *"The
   projects that become papers."* Those sentences exist and the front door does
   not use them as anything but a heading. No plane, no pinch, no fit button.
2. **The family:** its workspaces, each with what it is and what is happening in
   it. `machines.atlas_payload` already computes per workspace what is next, how
   many cards, which chapter, whether a board is up and on which node — all of it
   is in the payload today and gets drawn as a small card in a grid. No plane here
   either.
3. **The project map:** a diagram, which is the one thing here that genuinely
   needs a plane. `plane-core.js` stays, and it finally has content whose shape
   justifies it.

**(b) `vendor/` becomes explorable, and that changes a rule that is written
down.** `atlas.json` says today: *"vendor — somebody else's repositories, tracked
by pointer. Discovery skips the family entirely — nothing in it is the person's to
be graded on."* The reason given is about GRADING, and the ask is about TRACING:
*"who knows when we'll want to explore external tools in the same way… That's the
best way to dive into how Colibri works."* Those are different claims and the rule
conflates them, the same way `MAKE_SENSE` conflated content with scope.

*Want.* A vendor tree is walkable and diagrammable and is **never** a workspace
you hand work in to: no cards, no write-up, no homework, no push. A `trace`
sitting over `vendor/colibri` is exactly the right shape and it is currently
impossible. Split the rule in `atlas.json`'s own prose so the next reader does not
re-merge it, and remember that `atlas.workspaces()` skipping the family is what
several things depend on — widen the walk, do not widen what counts as a
workspace.

**(c) The project map is a package diagram and the ask is a class diagram. More of
it exists than it looks.** `map._from_code(root)` already derives nodes and
weighted edges from the source: on `research/PSYCH-ASR` it returns **13 nodes and
19 edges** right now, with real arrows — `psych-asr-cli → psych-asr-artifacts`
carrying 25 imports, `→ psych-asr-transcript` carrying 10. `_module_paths` reads
what a file imports, `_owner` decides which box owns the target, `_edges`
deduplicates and counts, and `_rollup` groups. The skeleton is there and it works.

What is missing is **granularity**. The nodes are DIRECTORIES. IntelliJ's diagram
is worth what it is worth because its nodes are the *things* — the classes — and
its arrows are uses and inheritance. *"Just looking at it should communicate
everything one needs to know to understand how the project works, and when we work
on a TODO, it's obvious what moving parts we'll be affecting."*

*The primitive for the nodes already exists in another file.*
`walk.DEFINITION` is a per-language pattern for *"is there a thing called X
defined here"*, anchored at the start of a line, for Python, Go, JS/TS, Lean, sh,
R and Rust. That is the definition-finder a symbol-level diagram needs, and it is
already written and already used to check a walkthrough's symbol before it reaches
a prompt.

*Decide: how far without a parser, and the answer is not the same in every
language.* A regex is honest about definitions and a liar about calls. **For
Python — which is most of this repository — use `ast`.** It is standard library,
which is this codebase's own rule in every module, and it gives classes,
functions, decorators, base classes and call sites exactly rather than
approximately. For everything else keep `walk.DEFINITION`, draw the coarser
diagram, and **say on the diagram that it is coarser** rather than letting
somebody trust a Lean box as much as a Python one.

*And decide the levels, because `MAX_NODES = 44` is about to be the binding
constraint.* A symbol-level diagram of a real project is hundreds of boxes, and
400 boxes on a plane is the ugly grid again with more effort. Three depths —
package, module, symbol — expanding on a tap, with the arrows rolled up to
whatever depth is showing. `_rollup` already does exactly that kind of grouping
for files.

*What must NOT be lost.* The written map is judgement and the derived one is not.
`live/map.json` carries *the typist*, *the stopwatch*, *the name-tagger* — names
*"which is judgement no file in this repository contains and which no amount of
reading the tree recovers"*, and `meeting.py` spends those names in every note it
writes. The derived diagram is a second layer UNDER the hand-drawn one, not a
replacement: the boxes keep their human names, and the structure appears inside
and between them. `map._unclaimed` is where the two are already reconciled.

**(d) And the code has to deserve the diagram. This is a standing rule, not a
task.** *"Not only do I want the project/course/research-project level maps to be
rendered in this way, but we need to make the code behave so that it can be
rendered that way too. Basically, all code ever produced, be it by vibe-coding or
coach-coding, must keep this desire for organization and scalability in mind. No
piece-of-shit code even though we can get away with it in Python."*

A diagram is a mirror. A module that does six unrelated things draws as one box
with eleven arrows into it and teaches nobody anything — and the failure is the
module, not the renderer. So the rule belongs where every turn is bound by it,
which is `TEACHING.md` beside *A doing turn: the work first, then one short card*
and in `sense.DOING_SENSE`, which in a headless turn is the whole prompt. In one
sentence: **a new thing goes in a module named for the one job it does, and if
that means moving something first, move it first.**

*And the refactor is real work with a real order.* The owner's own reading is
*"courses are pretty organized, and we've tried our best in the research projects
and other projects like Algo-Solutions and Lean-Theorem-Proving, but still, we
need to LOCK IN."* **Draw the diagram before refactoring anything.** The diagram is
the instrument: the box with too many arrows into it is the next refactor, and
guessing which module is untidy before you can see the graph is how the wrong one
gets rewritten. Take them one workspace at a time, and take the one the diagram
makes look worst.

**Check.** `test/map.py` owns *"the map is of the content, and none of it is
invented"*, which is the property that must survive all of this: assert every
derived node and every arrow traces to a real definition or a real import, that a
symbol `ast` cannot find is not drawn, and that the hand-written names still win
over derived ones. `test/hub.js` owns the front door — assert the three levels are
three surfaces, that the top two are not planes, and that `atlas.json`'s blurbs
reach the glass. `test/walk.py` owns what is walkable, and gains vendor. And
`test/teaching.py` for the standing rule, in the two places it has to agree.

### 9. A sitting belongs to ONE component, and leaving it is a new sitting

**The want, and it is item 8's other half.** *"When a tutoring session is
launched, that should happen from tapping on the particular component of that
project/course/research-project map. There should be TODOs present, each
corresponding with some component. The tutoring session should be AWARE of what
component it is active in, which isn't to say it can't know or talk about other
components, but for maximal organization, the session should be focused ON that
component. If a task starts turning into needing to go into a separate component,
the tutor should direct the user to get to a good stopping/saving point, and go
back to the map and open up a tutoring session in that component, which should
hopefully have a TODO associated with it."*

**The awareness already exists, and it is better than it looks.** `sense.node_sense`
hands a sitting its box rather than making it hunt: the box's name, its
one-line purpose, the files it is made of, the steps of the plan that name it, and
any document about it — *"all of that is on disk already, and a tutor that has to
go and find it pays for the search on every cold turn, in money and in latency,
before a word is taught."* It already ends with the focus rule in so many words:
**"Read those before your first card; do not survey the rest of the repository for
an agenda of your own."**

**The TODOs already hang off components.** `map._attach` puts each step of the
plan on the box it NAMES, and the match is *the path existing* rather than the
words looking similar, because *"a chip on the wrong box is worse than a chip in
the tray."* Anything it cannot place comes back rather than being dropped.
`plan._collect` reads `STEP` markers and `- [ ]` lines together in file order,
`MAX_STEPS` is 24, and `/session` already accepts a `node` and a `step`, looks both
up against what discovery found, and builds the sitting's label out of what came
back rather than out of anything a browser sent.

**So three things are missing, and the middle one is the whole of the ask.**

**(a) The map tap is one door among several, and the ask is that it is THE door.**
`config.aim_for`'s own note records the consequence: *"A SITTING NOBODY OPENED FROM
THE MAP HAD NO STYLE AT ALL. `tutor galois`, `board open`, a chapter tapped in the
contents drawer and a board resumed after a reboot all left `aim` unset."* The same
is true of the box: those routes leave `node` unset, so the sitting has no
component, and `node_sense` returns the empty string — no focus rule, no files, no
steps, nothing.

*Decide, and do not answer it the same way everywhere.* A course is chapters and a
project is components, and a lecture on Chapter 4 of Galois Theory has no
"component" to be scoped to. So this is a property of the WORKSPACE's shape, not a
rule for the whole board: where a workspace has a drawn map, a sitting without a
box is the exception and the board should say so; where it has a syllabus, the
chapter is already the scope and nothing changes. `map.py` knows which a
workspace is.

**(b) NOTHING TELLS A TUTOR WHAT TO DO WHEN THE WORK LEAVES ITS COMPONENT, and
that is the new rule.** The existing line is about not WANDERING — not choosing an
agenda outside the box. It says nothing about the honest case: the work genuinely
leads into another component, and the right answer is to stop rather than to
follow it.

*Want.* One rule, in `TEACHING.md` and in `sense.node_sense` so a headless turn
has it: **a component boundary is a stopping point.** When the next step of the
work is in another box, the turn does not follow it. It gets what is in hand to a
saving point, writes up what was agreed, says which box the work continues in, and
stops.

*And the hand-off must be a TAP, not an errand.* This is the failure this session
has already paid for twice — a card that says *"go back to the map and open the
retrieval component"* is an instruction to a person holding a tablet, which is the
same defect as *"two words to add when you write it up."* Every place already has
an ADDRESS (§2.1) and the board already renders one as something you can open, so
the card names the box by its address and the tap opens the sitting there. With
item 8's diagram, the boundary it is pointing at is also visible.

*Decide: what happens when that box has no TODO.* The want says *"which should
hopefully have a TODO associated with it"* — hopefully is doing a lot of work
there. `map._attach` already returns the steps it could not place, so the board
knows which boxes have none. Either the hand-off card proposes the TODO it is
handing over (the turn has just discovered it, so it is the one thing in the system
that knows what it should say), or the box is opened with nothing in it and the
first card asks. **Proposing it is better and is barely more work**, because the
discovery is the valuable part and it is lost otherwise.

**(c) And the refactor will move every box, which is the ordering constraint.**
Item 8 rewrites what a component IS — from a directory to a thing in a diagram —
and the TODOs are attached by path. So: item 8 first, then this. Doing them the
other way round means attaching the plan to boxes that are about to be renamed.

**Check.** `test/map.py` owns *"the map is of the content, and none of it is
invented"* and already guards the step-to-box attachment; extend it to assert a
box with no steps is KNOWN to have none rather than silently empty. `test/aiming.py`
owns what a sitting is told and is where the boundary rule's delivery goes — assert
`node_sense` carries it, and that a sitting with no box says so rather than
pretending to a focus it has not got. `test/teaching.py` for the rule itself, in
both places it has to agree. And the hand-off card's address is `test/address.js`'s
subject: assert the box it names opens.

### 10. A verdict you can feel: dopamine for right, playful frustration for wrong

**The want.** *"dopamine for the user when they answer correctly, and playful
frustration when they answer incorrectly. When we're in the context of the user
providing an answer, and it's a right or wrong, then the response should be
highlighted with a green (correct) or red (incorrect) band… If the user asks a
question, or we're not really in a 'right or wrong' scenario, then the response
should be highlighted with a yellow kind of band. I don't care exactly how you do
this; just make sure it's visually appealing."*

**More of this exists than it looks, and it is worth reading before adding
anything.** `board.css` already gives every card kind one `--accent` and derives
the rest from it: `correct` is `--good`, `wrong` is `--bad`, `question` is
`--ask`. Each of those gets a 3 mm left band, a `--wash` panel tinted from its own
accent — and the panel costs **no height**, deliberately, because ink is anchored
as a fraction of the card it was drawn on and a card that grows by a padding moves
marks made weeks ago onto the wrong line. A verdict card **arrives lit**: the
`verdict` keyframe lands it at `--flash` and settles it to `--wash` over a second
and a half. The label is a chip carrying a ✓, a ✕ or a ?, as TEXT rather than an
icon, and the tick has a `pop` — described in the stylesheet as *"the one flourish
that is purely a reward"*.

So the green and the red are there. **Three things are missing, and the first is
the one that makes the yellow case wrong today.**

**(a) THE TWO HALVES DISAGREE, AND ONLY IN THE YELLOW CASE.** `verdictOf` already
computes exactly the right thing — for each question, what its NEWEST reply says
about the answer: `correct`, `wrong`, or `open`, where open is the amber default
*because most replies in a doing sitting and most in a walkthrough are neither
right nor wrong*. It is painted on the student's own answer and on the board
holding the working. **It is not painted on the card.** The card takes its band
from its own KIND instead — so for the not-right-or-wrong reply the answer says
amber and the card says `--ink-3`, which is grey.

*And this answers a question that has been sitting open.* Item 12 asks whether
green on the answer and a tick on the card a finger's width apart is the same
thing said twice. The want above settles it: **the response carries the band.**
The answer keeps a quieter version of it, and one of the two is the moment while
the other is a label. Decide which way round, but decide it once.

**(b) THE BAND IS KEYED ON A CARD'S KIND AND THE QUESTION IS ABOUT AN ANSWER.**
`REPLY_KIND` is `{wrong, correct, review, note}` — `lesson` is not in it. A
`lesson` card is the commonest reply in a doing sitting and in a coaching one, so
in exactly the sittings where *"we're not really in a right-or-wrong scenario"* is
the normal case, there is no band at all.

*And the fix is NOT to tint every lesson card.* The stylesheet's own objection is
right and must survive: *"`lesson` and `recap` get no panel. They are the reading,
and a page tinted end to end says nothing at all."* A transcript that is yellow
from top to bottom has said nothing. The band belongs to a card that is a **reply
to work that was handed in**, which is a question `verdictOf` already answers — so
paint the card from the VERDICT rather than from the kind, and let a lesson card
that is teaching rather than replying stay plain.

**(c) THE FEELING IS NOT DESIGNED, ONLY COLOURED.** One `pop` on a tick is what
exists. The ask is emotional and the two halves are not symmetrical.

*Dopamine:* it can be bigger than it is. The card already arrives lit; the tick
already pops. What is missing is that a correct answer is the end of a piece of
work and nothing marks the *streak*, the problem being finished, or the write-up
landing because of it.

*Playful frustration, and the word playful is load-bearing:* **wrong is the
normal state of learning.** This person will be wrong many times an evening, on
purpose, and a board that punishes it teaches them to stop answering — which is
the only outcome here that cannot be undone by the next card. So: no shake, no
buzz, no red that fills the glass. One beat of character, then the card reads like
any other card, and the way forward is the thing left on screen.

**Decisions to take before writing, and the first is not negotiable.**

- **REDUCE MOTION, AND THIS SESSION PAID FOR THE LESSON.** A flourish is pure
  animation and somebody with that preference set must get none of it. What they
  must still get is the COLOUR and the MARK, because those are the meaning. And
  **nothing about the lesson's behaviour may depend on the flourish**: conflating
  the animation with the behaviour is exactly what let the next board land on top
  of an answer for everybody who has Reduce Motion on — see *The hold is not the
  animation* under *Settled*. Build the feeling on top of a page that is already
  correct without it, and test it with the preference both ways. jsdom has no
  `matchMedia`, so a suite that does not set it tests only one of the two.
- **Colour is never the only signal.** The ✓ / ✕ / ? chips carry it as text: they
  inherit the colour, they scale with the type, they survive a card being folded
  to its heading, and they work for somebody who cannot tell the green from the
  red. Keep them, keep them as text, and do not replace them with icons.
- **Tokens, not new colours.** `--good`, `--bad`, `--ask`, with `--wash` and
  `--flash` mixed from the kind's own accent so light and dark both follow. A new
  colour means adding it to BOTH blocks at the top of `board.css`, or half the
  board changes theme and the rest does not.
- **Do not say one thing five times.** Green on the answer, green on the board,
  green on the card, a tick, and a flash is five. Pick the surface that carries
  the moment and let the others be quiet.

**Check.** `test/mine.js` owns the verdict on the student's own answer and is where
the card half goes beside it — assert that a reply painted `correct` on the answer
is painted `correct` on the card, that the open case is the amber token and not
grey, and that a `lesson` card which is not replying to anything stays plain.
`test/typed.js` is the suite that now runs a second window with
`prefers-reduced-motion` on; assert there that the colour and the mark are both
still on the glass with every animation refused.

### 11. Put colibrì on the diarization repair, which is what all of the above is for

It is now the acceptance test of items 1, 2 and 3 as well as the job that has
been waiting since before any of this existed. **The ask, the scoring and the
numbers to beat are in `projects/libr-local-llm/HANDOFF.md`**, in the owner's own
words; they are not repeated here, because a number in two files is a number
that goes stale in one of them.

Three things about running it that are the board's rather than that file's:

- **Start it before you stop for the day.** The first turn is hours rather than
  minutes — a 15,900-token preamble at a few tokens a second of prefill — and
  after it the KV prefix carries the preamble. The thing not to do is kill it at
  ninety minutes and start again; that is the whole cost, paid twice.
- **Nothing on the board will kill the turn.** The `colibri` recipe carries a
  four-hour `timeout` that `turn_timeout` takes as a floor, and the daemon's beat
  thread keeps the indicator green throughout. What WILL kill it is the serve
  job's walltime — item 2's last paragraph.
- **`PSYCH-ASR` is the only kind of workspace it will open in**, because a colibrì
  sitting refuses where a card of its own would be committed and that workspace
  ignores `live/*` while a course does not.

`research/PSYCH-ASR/HANDOFF.md` holds the *teaching* thread on the same code; it
is a different conversation and the two do not merge.

### 12. And the three things no test can hold

None of these is a build. Each is an evening in front of the thing.

- **The colours, in a real sitting.** The verdict down the student's own answer
  and the labelled run of typed answers are both in and both covered by
  `board/test/mine.js`. One thing to watch for, because a test cannot: whether
  *answer 2 of 3* is useful or is a number on a bubble that did not need one —
  the `nth` clause in `render`, and one line to remove. (The other question this
  bullet used to ask — whether green on the answer and a mark on the card is the
  same thing said twice — is answered in item 10: the response carries the band.)
- **One document, all the way round** — item 4 is the build; this is the evening.
  Open a `paper` sitting on a box, let it write into `writeups/<slug>/`, compile
  it, open `/library`, read it on the glass, draw on it, and say something is
  wrong with it. Four things no suite reaches: **the content/scope split against a
  model** — item 5 lets the evening be the scope, and whether a tutor holding
  that still refuses to narrate the evening is the whole of whether the split
  worked; **the revision turn against a model**; **ink a person actually drew** —
  the marks route is tested with fixture strokes, which is not a ring round a
  figure at 200% zoom on an iPad, and that page's pen has never met a stylus —
  and **whether the reader is any good**, which is the one word in the question
  item 4 came from that no amount of code answers: *slick*.
- **The three teaching rules that were asked for out loud**, all of them
  instructions rather than mechanisms: the question restated under the definition
  list so it is the last thing above the board, the write-up compiled problem by
  problem rather than at the end, and no card telling the student to write
  anything up. `test/teaching.py` holds the places each is written down, and
  asserts only that they reach the course. **The first card of the next sitting is
  the real check.**

---

## Still open from the harness

- **KV slots.** `projects/libr-local-llm` serves GLM-5.2 int4 with one slot. One
  slot means one conversation's prefix cache; a second client evicts the first
  and pays the whole preamble again. That is why a colibrì sitting is refused
  machine-wide while another holds one. The engine supports 16 and
  `COLI_KV_SLOTS` is wired through; nobody has measured what a slot costs at a
  131072 window. Measure it and the refusal becomes a queue — one line out of
  the `colibri` recipe in `board/bin/tutor`, and nothing else changes.
- **`MTP`.** The engine turns native speculative decoding on by itself, and what
  P0 measured as a loss was setting `MTP=1` on top of that. One A/B on a warm
  server, worth doing before anybody quotes a tok/s figure again.

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
  `restoreTextAnswer` and `restoreTextDraft` were asked only while the type half
  was up, so a question that opened on the slate left the previous question's
  words in the box — and the restore refused any box that was not empty. Both are
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
  wake-ups is the window. Over ssh only and not the hop's Slurm fallback: a step
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
  it; four `tutorboard.json` files still carry one and it means nothing.
- **And the six changes before these.** `scripts/tool.sh` holds `tool_prefix` and
  `tool_root`, and both scripts read them. `tutorboard/fenced.py` is the one
  fence list and `reading.py` reads it. `plan._collect` takes `STEP` and `- [ ]`
  together in file order, `_distinct` settles the label collisions, and
  `MAX_STEPS` is 24. `course/results.py` and `/result/` put a figure on the
  glass. `map._unclaimed` gives a written map its document boxes.
  `paper1-trd-prediction` has its PDFs and `reading.py` finds them with no board
  change at all.
