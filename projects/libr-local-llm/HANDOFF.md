# HANDOFF.md

**The harness is built and reachable from a terminal. It is not reachable from the iPad, and that
is the next build.**

`coli-up`, `coli-code`, `coli-ask`, `coli-down` and `coli-build` exist, are on `PATH`, and serve
GLM-5.2 int4 to a coding agent in any directory. README §4c is the architecture and is the file to
read before touching any of it; `P0-STATUS.md` findings 16–20 are the measurements. This file says
what is left, and it is two things: **make the board able to start colibrì on any workspace from
anywhere**, and then **use that to do the diarization job**. They are one piece of work, because
the second is how the first is tested.

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

**The board tree is not clean, and roughly twenty files under `board/` belong to somebody else's
unfinished afternoon** — `bin/tutor`, `sense.py`, `server/routes/lesson.py`, `web/board.js` and the
rest. Three of the five pieces below touch files in that set. Read `../../HANDOFF.md` before
editing any of them, check what is already in the working tree rather than assuming the committed
version, and ship with a pathspec. In particular **`POST /aim`, `_aim` and `test/aiming.py` are in
the working tree and not in the history**; treat them as a design to agree with, not as something
you can call.

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
tutor is told what the tap meant. The in-flight `POST /aim` is the worked example of a control that
changes the open sitting without archiving it — read it, but do not build on it until it lands.

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

## Decisions to take before writing, not during

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
