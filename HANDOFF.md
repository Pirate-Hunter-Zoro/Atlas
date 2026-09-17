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
is item 8 here.

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

**Items 2, 3 and 4 are one piece of work** — a *mission* — and they land in that
order: a mission cannot be told to ship itself before it is a record, and it
cannot be a record before the board knows which workspaces are fenced. Items 1
and 5 are independent of that and of each other; item 1 is the smallest, so start
there. Item 6 is where a lesson turns into a document, and item 5 is how that
document is then corrected, so they are worth reading together. Item 7 is the
answer box and is independent of everything. Item 8 is the acceptance test of 2,
3 and 4 and is also the job all of it exists for. Item 9 is not a build.

---

## What to do next

### 1. Coach coding needs a "you do this step" tap

**The want:** *"in coach coding mode, I still want to be able to have a 'fuck
this, you do this step' option."*

**Now.** `coach` is an aim and its sentence is in `config.AIM_MEANS`: name the
calls, the arguments and the order in English, one step per card, and let them
type it. There is no way out of one step of it. The only escape is `POST /aim`,
which changes **the whole sitting** to `build` — so the way to get one step
written for you is to stop being coached, and the next card and every card after
it is written the new way.

**Want.** One tap, on the step's own card, that hands over **that step** and
leaves the sitting coaching. The next card is a coach card again.

**Where, and the shape exists three times over.** A signal on a turn: `[begin]`,
`[aim]` and `[direction]` are all a tap that becomes a line in the inbox, which
in a headless turn IS the prompt. So `POST /handover` carrying the card id,
`sense.SIGNAL_SENSE["handover"]` saying what the tap meant, and a turn woken on
it. `_aim` in `routes/lesson.py` is the worked example of a control that changes
nothing about the sitting, and `board/test/aiming.py` is its suite.

**The detail that will be missed.** `doing_now(root)` answers "is this a turn
that writes code" from the SITTING's aim, and `turn_timeout` reads it — so a
handover turn inside a coaching sitting gets a teaching turn's fifteen minutes
for work that stages files and runs a suite. The signal has to reach that
decision, not only the prompt.

**Decide before writing.** Whether a handed-over step is written up as a coach
card afterwards. It must not be: a card explaining how it did the step is a
lecture nobody asked for, and the person's next act is the NEXT step. One short
report — what changed, what it ran, what came back — and then the next coach
card. Put that in `TEACHING.md` beside *A doing turn: the work first, then one
short card*, which already says the shape.

**Check.** `board/test/aiming.py` owns this kind of route. Assert the sitting's
aim is unchanged, the lesson is not archived, no tutor is replaced, the inbox
line carries `[handover]` and the card it is about, and that the turn is given a
doing turn's clock.

### 2. The board must know which workspaces hold a fence, and say so before the tap

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

### 3. A mission is a thing, and closing the iPad does not end it

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

### 4. A mission can be told to ship itself, and the diff is checked before it goes

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
itself. The signal mechanism is the same one items 1 and 3 use.

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

### 5. A document is corrected, or overhauled, without leaving the page it is on

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
menu — and no person has read a real document on it. That is item 7.

### 6. Any sitting can be asked for a paper OR a deck of what it covered, at any moment

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
correcting it is item 5's loop. Take that deliberately rather than by streaming
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

### 7. Mathematics renders in the answer box as it is typed

**The want:** *"when I'm typing a response to a tutor, I want to be able to type
latex commands in the typing box — like \gamma, etc. — and have that render as I
type it. And then when I send it, have it stay rendered that way. I still like
how everything else is rendered dyslexic friendly."*

**Half of this already works, and it is worth knowing which half before building
anything.** Measured by driving the real page: a typed answer goes through
`renderMarkdown`, which parks `$\gamma^2 = 2$` into a `span.math-raw`, and
`reconcile` pushes **every** newly inserted node into `freshNodes` — a card or a
turn, no distinction — which `typeset` then walks with `$`, `$$`, `\(` and `\[`
and 64 macros out of `macros.js`. So **a sent answer containing `$\gamma^2 = 2$`
already comes back typeset in the transcript, today.** Nothing needs building for
the "stay rendered" half.

**Two things do not work, and the second is a decision rather than a build.**

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

**(b) A bare `\gamma` renders nowhere, and never will without a decision.**
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

**Check.** `test/typed.js` owns the answer panel. Assert: with `$\gamma$` in the
box the preview holds a `.katex`; with plain prose there is no preview at all;
what the preview shows is what the transcript shows after the send, because it is
the same renderer; the prose in the preview carries `body.dataset.face` and the
`.katex` does not; and a bare `\gamma` raises the hint rather than silently
rendering nothing. `test/markdown.js` and `test/macros.js` own the renderer and
the macro list either side of it — `test/markdown.js` matters more than it looks,
because the renderer parks math and code before any markdown parsing and
restores it afterwards, and every change to it needs a case proving that still
holds.

### 8. Put colibrì on the diarization repair, which is what all of the above is for

It is now the acceptance test of items 2, 3 and 4 as well as the job that has
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
  job's walltime — item 3's last paragraph.
- **`PSYCH-ASR` is the only kind of workspace it will open in**, because a colibrì
  sitting refuses where a card of its own would be committed and that workspace
  ignores `live/*` while a course does not.

`research/PSYCH-ASR/HANDOFF.md` holds the *teaching* thread on the same code; it
is a different conversation and the two do not merge.

### 9. And the three things no test can hold

None of these is a build. Each is an evening in front of the thing.

- **The colours, in a real sitting.** The verdict down the student's own answer
  and the labelled run of typed answers are both in and both covered by
  `board/test/mine.js`. Two things to watch for, because a test cannot: whether
  green on the answer and a tick on the card a finger's width apart is the same
  thing said twice, and whether *answer 2 of 3* is useful or is a number on a
  bubble that did not need one. Both are one line to remove —
  `.mine[data-verdict]` in `board/web/board.css`, and the `nth` clause in
  `render`.
- **One document, all the way round** — item 5 is the build; this is the evening.
  Open a `paper` sitting on a box, let it write into `writeups/<slug>/`, compile
  it, open `/library`, read it on the glass, draw on it, and say something is
  wrong with it. Four things no suite reaches: **the content/scope split against a
  model** — item 6 lets the evening be the scope, and whether a tutor holding
  that still refuses to narrate the evening is the whole of whether the split
  worked; **the revision turn against a model**; **ink a person actually drew** —
  the marks route is tested with fixture strokes, which is not a ring round a
  figure at 200% zoom on an iPad, and that page's pen has never met a stylus —
  and **whether the reader is any good**, which is the one word in the question
  item 5 came from that no amount of code answers: *slick*.
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
