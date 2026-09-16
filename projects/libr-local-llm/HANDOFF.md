# HANDOFF.md

**The harness is built and reachable from a terminal. It is not reachable from the iPad, and that
is the next build.**

`coli-up`, `coli-code`, `coli-ask`, `coli-down` and `coli-build` exist, are on `PATH`, and serve
GLM-5.2 int4 to a coding agent in any directory. README §4c is the architecture and is the file to
read before touching any of it; `P0-STATUS.md` findings 16–20 are the measurements. This file says
what is left.

**Three parts, and the third is not about colibrì at all.** Part one makes the board able to start
colibrì on any workspace from anywhere. Part two uses that to do the diarization job, which is how
part one is tested. Part three is two things the board got wrong in a Galois-Theory sitting, both
reported from the iPad, both unrelated to everything above and both waiting here because this is
the file the next session opens.

What has actually been run through it: the model emits a correct Anthropic `tool_use` block in
43.6 s, which is the whole of a coding CLI's loop; `coli-ask` answers a real question in 51 s at
3.14 tok/s; and Claude Code's system prompt, 21 tool definitions and streaming all cross the
protocol intact. What has **not** been run is a full agent turn against the model, because the
client's preamble is 15,900 tokens and prefill at that size is two to three hours.

---

## Read these first, in this order

- `README.md` §4c — what exists and why each flag is there. Traps 27–32 are the failures already
  paid for, and every one of them cost a run.
- `P0-STATUS.md` findings 16–20 — the measured rates. **Finding 20 governs the whole design below**,
  because it is the reason none of this can be request-shaped.
- `../../board/bin/tutor` — the agent registry, `resolve_agent`, and the headless daemon. Most of
  what follows is a sixth entry in a table that already has five.

**The board tree is clean and that afternoon has shipped.** `POST /aim`, `_aim` and
`test/aiming.py` are in the history now, so they are something to CALL and copy rather than a
design to agree with — read `_aim` in `board/tutorboard/server/routes/lesson.py` and its suite
before writing piece 4, which is the same shape. Two other things from it govern what follows:
`course/config.py` now holds `aim_for`, `AIM_STANCE` and a `stance_for` derived from the aim, so a
fifth `resolve_agent` layer has a precedence function to sit beside rather than invent; and
`config.read_config` is where a per-workspace default is read, if an agent ever needs one. Ship
with a pathspec regardless: one repository, nine workspaces.

---

# Part one — reach it from the iPad

**The want, in the owner's words:** start colibrì on a specified project from the iPad, in any old
tutoring session or any old project or course map, at any time.

Five pieces. **One shipped and checked, then the next** — three of them touch `bin/tutor` and the
sitting's `state.json` together.

---

## 1. There is no `colibri` agent, and adding one is a table entry

**Now.** `DEFAULT_CONFIG["agents"]` in `board/bin/tutor` holds `claude`, `opencode`, `codex`,
`aider` and `cursor`. Each is a command recipe: `cmd` for the interactive session, `headless_first`
to open a headless one, `headless` to continue it, `{prompt}` substituted. The file says the rule
out loud — *"an agent entry is a command recipe, so a second model is a second entry whose `cmd`
carries the flag. Nothing in this file knows what a model is."* colibrì is exactly such an entry,
and the daemon does not have to learn anything to accept it.

**Want.** A `colibri` entry whose `cmd` is `coli-code`, whose `headless_first` is
`coli-code --yes {prompt}`, and whose `headless` continues the same agent session.

**The blocker, and it is in this repository rather than the board.** `coli-code` has no way to
continue a session. The board's whole cost argument rests on `headless` resuming what
`headless_first` opened, and on colibrì the argument is much stronger than it is for a hosted
model: a resumed session reuses the KV prefix and a fresh one pays the 15,900-token preamble
again, which is hours rather than pennies. **`coli-code` gains `-c`/`--continue`**, passed through
as `--continue` to Claude Code and `-c` to opencode. The session store is already per-agent under
`$COLI_SESSION_ROOT`, so there is nothing else to wire.

**Where.** `bin/coli-code` for the flag; `board/bin/tutor` `DEFAULT_CONFIG["agents"]` for the entry.

**Check.** `board/test/agents.py` is the suite for this table and is committed. `tutor --agents`
lists the entry, and `missing_command` does not reject it — that helper checks the recipe's first
word against `PATH`, and `coli-code` is on `PATH` only where README §3's `bin` line has been added
to `~/.bashrc`. A machine without it should say so by name, which `headless` already does.

---

## 2. A colibrì turn is killed at one hour, in the middle of its first prefill

**Now.** `turn_timeout` in `board/bin/tutor` returns `headless_timeout` (900 s) for a teaching turn
and `max(that, doing_timeout)` — 3600 s — for a turn that was asked to write the code. Both numbers
were chosen against a hosted model. **A colibrì first turn spends two to three hours in prefill
before it emits a token.** Every one would be killed, and the board would paint it as a turn that
failed rather than a turn that was interrupted.

**Want.** The timeout is a property of the agent as well as of the sitting. A `timeout` key in the
agent recipe, taken as a floor by `turn_timeout`, is the smallest change that expresses it: the
existing two numbers stay exactly as they are for every other agent, and the `colibri` entry
carries its own.

**Where.** `turn_timeout` in `board/bin/tutor`, just above `handoff_clause`, and the recipe from
piece 1. Find it by name — that file is being edited by somebody else and a line number will be
wrong by the time you read this.

**What is already right, so nobody re-solves it.** The board will *not* paint a long turn as dead.
A 30-second beat thread runs for the whole of a turn and was added for this exact reason — the
comment beside it says a turn longer than the two-minute window "showed on the iPad as *assistant
not responding* while the assistant was in the middle of teaching". A two-hour turn keeps the
indicator green with no further work.

**Check.** Assert that a `colibri` sitting gets the recipe's number and that a `claude` sitting's
two numbers are unchanged. `board/test/agents.py` already loads `bin/tutor` as a module to test
`resolve_agent`, so it is the cheapest place to put it.

---

## 3. Nothing starts the server, and starting it is not something a request can wait for

**Now.** `coli-code` exits 1 with *"No colibri server is running. Start one: coli-up"*. That is the
right message in a terminal and a dead end on an iPad. `coli-up` submits a Slurm job, waits for an
allocation, waits out a 429 GB load and then warms the model with a real generation — **seven to
eight minutes on a good day, longer when the partition is full**, and it can pend indefinitely
behind a 950 GB ask.

**Want.** One control that starts the server and returns at once, and a board that says which of
the four states it is in: nothing running, queued, loading, warm.

**Where, and the precedent is exact.** `spawn.wake_tutor` in
`board/tutorboard/server/spawn.py` starts a tutor on a daemon thread and returns immediately,
*"because nothing that takes as long as a start can be reported by the request that triggered it"*.
A `spawn.wake_colibri` is the same function against `coli-up`. The state to paint is not new
either: `processes.agent_is_attached` already has a `waking` record that is attached without a pid,
written before the slow work, and the comment above it is the whole argument — *"the one thing that
must never happen here is the board saying nothing is listening while something is in the middle of
arriving."*

**Do not invent a state file.** `squeue` is the source of truth for whether the job exists and
where, exactly as it is for `coli-up`, `coli-code` and the `ollama-*` three — a state file goes
stale the moment a job ends and `squeue` never does. It is asked once per poll, though, and the
board polls four times a second, so cache it: `machines.held_nodes` caches its own `squeue` for
fifteen seconds and is the pattern to copy, not the function to reuse.

**Check.** A new suite. With no job: the control reports it and offers to start one. With a job
`PENDING`: the reason from `squeue` is shown, and the control does not submit a second. With a job
`RUNNING` but no `API listening on` line yet: loading, not ready.

---

## 4. A sitting cannot choose its assistant, and the map is where it should

**Now.** `resolve_agent` in `board/bin/tutor` has four layers, most specific first: `--agent` on the
command line, `agent` in the workspace's `tutorboard.json`, `hosts` by hostname, `default_agent`.
**None of them is the sitting.** So choosing colibrì for one evening's work means editing a file
that is a statement about the workspace for ever, and the iPad cannot reach any of the four.

**Want.** A fifth layer above all of them — the open sitting — chosen with one tap, cleared when a
sitting that does not name it opens.

**Where, and the shape already exists.** `_mark` in
`board/tutorboard/server/routes/lesson.py` writes `node` and `aim` into `state.json` and pops them
when they are absent, with the reason written above it: *"both belong to the SITTING and not to the
repository … a box chosen for an evening's work is not a statement about what the repository is."*
An `agent` belongs beside them under precisely that rule, and `sense.SIGNAL_SENSE` is where the
tutor is told what the tap meant — it has an `aim` entry now, written for exactly this kind of tap.
`POST /aim` is the worked example of a control that changes the open sitting without archiving it,
it has landed, and `board/test/aiming.py` is its suite.

**Decide before writing.** Switching the assistant mid-sitting is not the same as switching the
aim. The aim changes what the next card is; the agent changes *who writes it*, and the conversation
the old one was holding does not transfer. Either the tap ends the current agent's session and the
next turn starts a fresh one — which on colibrì costs the whole preamble — or an agent can only be
chosen as a sitting opens. **The second is probably right and is certainly cheaper**, but it is a
judgement about what a sitting is, so make it deliberately rather than by writing the easier route.

**Check.** `board/test/agents.py` owns the resolution order and gains a fifth layer above the four
it already asserts. For the route, the in-flight `board/test/aiming.py` is the model: it asserts the
route writes the field, leaves `live/archive/` untouched and leaves the card count unchanged.

---

## 5. Starting it on a workspace you are not looking at

**Now.** Everything above puts colibrì to work in the workspace whose board you have open. The ask
is broader: *a different section of a project, or a different project completely, at any time.*

**Want.** From any board, pick a workspace and a task, and colibrì starts there. You go back to
what you were doing and are told when it lands.

**Where, and three of the four pieces already exist.**

- **The list** is `machines.workspaces(repo)` in `board/tutorboard/machines.py` — every workspace on
  this machine, built by walking the tree, never registered. `/atlas.json` already serves it.
- **The start** is `spawn.tutor_cli(["agent", "start", <course>])`, which is exactly what
  `wake_tutor` calls today. With piece 4 done it carries the agent choice.
- **The notification** is `news.elsewhere` in `board/tutorboard/news.py`, and it was built for this
  request almost word for word: *"I want to be able to go into a different section of a project, or
  a different fucking project completely, and put other agents to work on other things while the
  first one is working."* Its rule is that a workspace's newest card is newer than the last time
  anybody looked at it, which is true of a colibrì turn that lands three hours later. **Nothing
  here needs building.**
- **The fourth piece is the refusal, and it is new.** The server runs **one KV slot**. A second
  colibrì sitting anywhere on the machine evicts the first one's prefix, and the first one then
  re-pays its preamble — hours of work destroyed by a tap that looked harmless. So: **one colibrì
  sitting at a time, machine-wide, refused by name with which workspace already holds it.**

**Check.** Start one in workspace A, ask for one in workspace B, and assert the refusal names A.

---

# Part two — the acceptance test, which is the real job

**Put colibrì on the diarization repair from the iPad.** That is the test of everything above and
it is also the work that has been waiting since before any of this existed.

## The job, in the owner's words

> Look at all the dirty details of `phi`, look at the community-1 diarization, and look at
> Madison's corrections/error-log CSV. Using those two things, do whatever you need to do to
> reproduce a perfect transcription based on the corrections, and document how you did it.

The agent can read `phi` — that is the entire reason this exists, and it is why `coli-code` gives
the client a fresh config directory with no PHI hook in it.

## How it is scored, without anybody rereading the session

A number, not a judgement:

```
python3 -m psych_asr.cli.apply_corrections --dry-run --anonymise
```

Counts, spreadsheet row numbers and seconds, naming the participant nowhere. **Before: `unplaced_rows`
is `[16, 32]`, `within_2s` is 68 of 74, stray marks are at zero.** A reconstruction is better if
those move the right way. That is what makes a rule colibrì proposes checkable by somebody not
cleared for what it was tested on — including whichever hosted assistant reviews the algorithm
afterwards.

`research/PSYCH-ASR/HANDOFF.md` holds the teaching thread on the same code and is a different
conversation; do not merge them.

## Start it before you stop for the day

**The first turn is hours, not minutes.** After it the KV prefix carries the preamble, so the thing
not to do is kill it at the ninety-minute mark and start again — that is the whole cost, paid twice.
Leave the server up between tasks for the same reason; `coli-down` between two jobs is expensive.

---

# Part three — two things the board got wrong last sitting

Neither is a colibrì change, so both follow the board's own rules rather than this project's:
`bash board/test/all.sh` green before and after, **`VERSION` in `board/web/sw.js` bumped**, and
`bash board/scripts/ship.sh "message"`, which commits only `board/`. Read `../../HANDOFF.md`
first — it says what has just changed in the board and what is left of it.

---

## 6. The tutor told the student to write it up, and the write-up is the tutor's job

**Now.** Card 0004 in Galois-Theory: *"Two words to add when you write it up."* Reported in exactly
these terms — *"I'M not fucking writing anything up. The tutor's going to write up what I want it
to, right? Once I've corrected my work? It should put phrases in like that - that makes me uneasy."*

The rule is already in `board/TEACHING.md` and it is not weakly put: a whole section, *An agreed
answer gets written up, and that is your job*, saying every sitting produces a compiled document and
the tutor transcribes the agreed answer in the same turn. That section governs **the act**, and the
card obeyed it. What escaped is **the sentence**. Nothing in the document forbids addressing the
student as the person who will write something up, so the tutor did, and handed over an errand that
does not exist.

**There is a second defect inside the same clause and it is the worse one.** "Two words to add when
you write it up" *defers a correction*. The argument is incomplete without the word **non-zero** —
that is a fact about the proof, not a note for later — and the place it gets fixed is the write-up,
which the tutor writes. Phrasing it that way makes the fix conditional on something the student was
never going to do, so the proof stays wrong in a document they have been told is finished.

**Want.** Two sentences of rule.

- A card never tells the student to write, typeset, transcribe or *add to* anything. The write-up is
  the tutor's, stated as a fact about what the document now says rather than as an instruction to a
  person.
- A correction belonging in the write-up is made in the write-up, in the same turn, and the card
  says what was wrong and that it is now right. Never *"add X when you write it up"*, which is both
  halves of this failure in one clause.

**Where.** `board/TEACHING.md`. The rule's home is the section that already owns the act — *An
agreed answer gets written up, and that is your job* — and the phrasing half belongs beside *Say it
plainly*, where sentence-level rules already live. *Work done on a laptop is theirs, and saying
otherwise is the worst card you can write* is the model to copy: a named phrasing failure, quoted,
with the reason it lands badly. Check `board/AI_INSTRUCTIONS.md` says nothing that contradicts it.
TEACHING.md is copied into every workspace's `live/` on `board start`, so nothing else needs
touching for the rule to reach every course.

**Check.** `board/test/teaching.py` already asserts that particular rules survive into the delivered
copy, and that is where this goes. **A phrasing rule cannot honestly be unit-tested against a real
card**, and a test that pretended to would be a test of nothing — so assert the rule is in the
document that reaches the course, and treat the next sitting's first card as the real check.

---

## 7. The next board arrived before the answer, and the pulse stopped

**Now.** From the same sitting: *"the response appeared how I wanted it to, but before it did, the
second board showed up right underneath the last board, and I was left hanging."*

Two surfaces answer the question *has the reply arrived*, and they answer it differently.

- **The writing surface asks whether a card is typing.** `placeWriter` is handed
  `typingCards() && !workingOn && reopenedFor === null` as its hold. That is already the right idea,
  and the comment above the typeset pass in `render` records this same defect being fixed once
  before, when `typeOut` ran a hundred lines too late: *"the surface came straight down under the
  new question, and the answer then filled in above it. Every frame after that held correctly, which
  is why this looked intermittent rather than wrong."*
- **The busy strip asks whether a card exists.** `awaitingReply` is recomputed near the top of
  `render` — the last item in the transcript, if that item is not text — and is cleared the instant
  a card lands after the student's turn. `paintSent` hides the strip on the same frame. **Nothing on
  that path consults `typingCards()`**, so the yellow pulse stops when the card's *record* arrives,
  which is before a word of it is on the glass.

That is the gap the student fell into, and it explains the shape of the report exactly: the pulse
went, the next board came down, and the answer arrived afterwards. Note also that `typingCards()` is
`typingNow > 0 && Date.now() < typingUntil` — a hold with a **deadline**, which fails on precisely
the longest card.

**Want.** One predicate, asked by both, and it is not *does a card exist*. A reply has landed when
its node is in the document, its mathematics is typeset, its images have decoded and the type-out
has finished. Until then the strip keeps pulsing and the surface does not move. The student's words
are the specification and they are exact: **no next board until the whole response is rendered, and
the pulse visible at all times until it is.**

**Where.** `board/web/board.js` — `awaitingReply` in `render`, `paintSent`, the hold argument to
`placeWriter`, and `typingCards`. The deadline inside `typingCards` is the part to think about
rather than copy forward.

**Decide.** Whether the strip's words change while it holds. It currently reads *"sent at 20:14 —
the tutor is reading it"*, which stops being true the moment the card starts typing and then stays
on screen for the whole of it. *"the tutor is writing"* is the honest second state and the board
already uses that wording elsewhere. One more state, or one that is slightly wrong for a few
seconds — pick it deliberately rather than by leaving the string alone.

**Check.** `board/test/hanging.js`, which is the suite for exactly this — *"Nothing the reader can
be waiting on is allowed to be silent"* — is jsdom, asserts what a person can read on the glass, and
was written from the same person saying *"I don't ever want to be left hanging."* Assert: on the
frame a card arrives and begins typing, the strip is still visible and the writing surface has not
moved; on the frame the type-out ends, both change.

**And bump `VERSION` in `board/web/sw.js`.** `board.js` is a shell file, so without the bump the
installed app serves its cached copy — the fix ships and nothing happens, which on a rendering
change is indistinguishable from the fix not working.

---

## Decisions to take before writing, not during — parts one and two

**A colibrì turn writes a card, and in one workspace that card is committed.** Cards are how every
turn reports, and `research/PSYCH-ASR/.gitignore` excludes `live/*` with `live/map.json` the single
exception — so a card there is never tracked, and that is load-bearing rather than incidental.
**`courses/Galois-Theory/live/cards/` is tracked**, and its cards are in the pushed history. So the
same feature, used in a course, commits the model's output to a remote. Decide which: a colibrì
sitting refuses to open where its cards would be tracked, or the card goes somewhere else. **Do not
leave this to whichever workspace somebody tries first.**

**`MTP`.** The engine turns native speculative decoding on by itself, and what P0 measured as a loss
was setting `MTP=1` explicitly on top of that. Which of the two states it measured is not
recoverable from the result. One A/B on a warm server, in one job on one node.
`fleet-p0/prefill_probe.py` is the instrument. **Do not quote a tier-2 tok/s figure again until it
is settled.**

**KV slots.** One today, and piece 5's refusal is written against that. The engine supports 16 and
`COLI_KV_SLOTS` is wired through the serve job, but nobody has measured what a slot costs at a
131072 window. If it is cheap, the refusal becomes a queue and two sittings can run at once. Measure
before designing for it.

---

## One thing left over

`rm -rf ~/.local/lib/python3.12` recovers **8.7 GB** on a home share that is 86 % full. It is an
accidental pip install and nothing depends on it; the sandbox refused the recursive delete.
`~/.local/lib/python3.{9,11,13}` and `~/.local/bin` are unrelated — leave them.

---

## About this user

They work in a VSCode terminal on a compute node and close the laptop without warning; leave long
work as Slurm jobs that survive it, and leave a file behind that says where things are. They read
the runbook as the source of truth, so a finding that contradicts it belongs *in* the repo, not in
a chat message they will not have tomorrow.

They will tell you when an answer is convoluted, and they are usually right. When the direct path
is blocked, say what blocks it in one line and then take the most direct remaining path — do not
build a clever detour around it and present that as the answer.
