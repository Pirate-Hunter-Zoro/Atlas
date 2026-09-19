# HANDOFF.md

**The harness is built, reachable from a terminal, and now reachable from the iPad. What has never
been run is the job it exists for.**

`coli-up`, `coli-code`, `coli-ask`, `coli-down` and `coli-build` exist, are on `PATH`, and serve
GLM-5.2 int4 to a coding agent in any directory. README §4c is the architecture and is the file to
read before touching any of it; `P0-STATUS.md` findings 16–22 are the measurements.

**One thing is left in this file, and it is the whole point: put colibrì on the diarization
repair.** It is below, in the owner's own words, with the scoring already decided. Everything under
*Settled* is machinery that now exists to make it one tap.

**The board owes this job nothing further** — a mission dispatched from the iPad is a record that
outlives it, says whether it is still running, and can be told to ship when it finishes; all of it
is under *Settled* in `../../HANDOFF.md`. Two facts from this project decided how that got built,
and they still govern running it:

- **A colibrì turn runs inside the SERVE JOB'S allocation.** `coli-code` steps into it with `srun
  --overlap` rather than ssh, because the endpoint is loopback-only on the serving node. So a
  mission's ceiling is the serve job's walltime — 8 h by default, 9 h on `c3_short` — and `coli-up
  -t` is the only lever. A mission longer than that cannot finish, whatever the board records.
- **Shipping is not this model's job.** It decodes at 3.2–4.4 tok/s and it is the one assistant
  that may read `phi`. The ship belongs to a hosted follow-up turn, which is also a second pair of
  eyes on a local model's diff — a turn that could not have read the session content it is
  checking for. **The machine half of that check is wired**: `names_phi` in
  `ai-config/policy/phi.py` is loaded, not copied, by `board/tutorboard/leaving.py`, and both
  `board push` and the board's save button call it before anything leaves the machine. It reads
  the added lines of each changed file that lives inside a fenced workspace, and refuses naming
  the file. It is a regex — it catches a diff reaching for session content or carrying a piece of
  one with its shape still on it, and a bare sentence of dialogue with no path or extension around
  it is not catchable that way. That last part is what the hosted turn's judgement is for.
  `board push --anyway` is the override and is deliberately a keyboard act; the save button has
  none.

---

## Read these first, in this order

- `README.md` §4c — what exists and why each flag is there. Traps 27–32 are the failures already
  paid for, and every one of them cost a run.
- `P0-STATUS.md` findings 16–22 — the measured rates. **Finding 20 governs the whole design**,
  because it is the reason none of this can be request-shaped.
- `../../board/README.md`, *Any agent, not just one* — the five layers that resolve which
  assistant tutors a sitting, and the three things about the `colibri` row that are unlike the
  other five.

---

# The job

**Put colibrì on the diarization repair.** It has been waiting since before any of the machinery
below existed, and running it is also the only real test of that machinery.

## In the owner's words

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

Counts, spreadsheet row numbers and seconds, naming the participant nowhere. **Before:
`unplaced_rows` is `[16, 32]`, `within_2s` is 68 of 74, stray marks are at zero.** A reconstruction
is better if those move the right way. That is what makes a rule colibrì proposes checkable by
somebody not cleared for what it was tested on — including whichever hosted assistant reviews the
algorithm afterwards.

`research/PSYCH-ASR/HANDOFF.md` holds the teaching thread on the same code and is a different
conversation; do not merge them.

## How to start it

From the iPad, from any board: **⇥ put an assistant to work elsewhere** in the bar menu, pick
`PSYCH-ASR`, pick `colibri`, and give it the ask above. Or from a terminal: `coli-up`, then
`coli-code -d ~/Atlas/research/PSYCH-ASR --yes "…"`.

`PSYCH-ASR` is the workspace it is allowed to open in, and that is not an accident:
`research/PSYCH-ASR/.gitignore` excludes `live/*`, so a card written there is never tracked. A
colibrì sitting refuses to open anywhere its cards would be committed, and says which line
changes that.

**Start it before you stop for the day.** The first turn is hours rather than minutes: prefill on
a 15,900-token preamble is two to three hours. After it the KV prefix carries the preamble, so the
thing not to do is kill it at the ninety-minute mark and start again — that is the whole cost,
paid twice. Leave the server up between tasks for the same reason; `coli-down` between two jobs is
expensive.

---

## One thing left over, and it needs the owner's own shell

`rm -rf ~/.local/lib/python3.12` recovers **9.3 GB**, and an assistant cannot run it: every
sandbox here refuses a recursive delete of that size. It is an accidental pip install, and the
reason it is provably dead is that **there is no `python3.12` interpreter on this machine at all**
— `python3` is 3.9 and the only other one under `/usr/bin` is 3.11, so nothing can import from
that tree. `~/.local/lib/python3.{9,11,13}` and `~/.local/bin` are unrelated — leave them.
`~/.local/bin` in particular holds TeX. The share is at 56 % as of 2026-09-18, so this is tidiness
rather than pressure.

---

## Settled, so nobody re-derives it

**`MTP` IS MEASURED AND THE SERVED CONFIGURATION DOES NOT TURN IT ON.** `COLI_CUDA_MTP=1` is the
lever — `MTP=1` never was, and `[MTP] active … (draft=0)` says `active` about the checkpoint
rather than about the run — and depth 1 is the only depth worth the question. Job 2073575 on
compute303, six runs ABBAAB, the first time speculation has been on under CUDA on this box:
**3.23 tok/s at `draft=1` against 3.58 at `draft=0`**, and the slowest off-run beats the fastest
on-run. Acceptance ran 62–77 % and did not convert — the run that saved the most forwards, 78
tokens in 44, was the slowest of the three. The drafting works; the per-forward cost of it exceeds
what the saved forwards are worth on a box whose bottleneck `coli plan` already names as the CPU
expert tail. So `colibri_serve.sbatch` stays as it is, and a tier-2 tok/s figure is quotable
again. **P0-STATUS finding 21** holds the table and the derivation; the per-configuration logs
stay outside the repository because they carry generated text.

**`coli-code -c/--continue` continues the session already open**, passed through as `--continue`
to Claude Code and `-c` to opencode's `run`. The session store is already per-agent under
`$COLI_SESSION_ROOT` and `CLAUDE_CONFIG_DIR` points at it, so there was nothing else to wire. It
is not a nicety: a fresh session re-pays the whole preamble, which on this engine is hours.

**`colibri` is a row in the agent table and the board learned nothing to accept it.** `cmd` is
`coli-code`, `headless_first` opens a session, `headless` continues it, `--yes` because a headless
turn has nobody to approve a tool call. Three fields on the recipe carry everything that is
unlike the other five, so each of them stops mattering by deleting a line rather than by editing
this file: `timeout` (four hours, taken as a FLOOR by `turn_timeout`, so a colibrì turn is not
killed mid-prefill and painted as a failure), `exclusive` (one sitting at a time machine-wide, off
the heartbeat and never the pid, because a pid written on one node names a process table this one
cannot read) and `private` (it refuses to open where `git check-ignore` says a card would be
tracked). `board/test/colibri.py`.

**The sitting is the fifth layer of `resolve_agent`, and the only one a tablet can reach.** Above
`tutorboard.json`, under `--agent`, written into `state.json` by `_mark` beside `node` and `aim`
and cleared by opening a sitting that does not name one. Chosen as a sitting OPENS rather than
changed in place, and that is the decision rather than the shortcut: an aim changes what the next
card is, an assistant changes who writes it, and the conversation the outgoing one was holding
does not transfer. A name this machine has not got falls back with a line saying so, where every
layer below refuses — it is the one layer written from a browser.

**The server has four states and `squeue` answers three of them.** Nothing running, queued with
Slurm's own reason, loading, warm. Cached fifteen seconds, the way `machines.held_nodes` caches its
own; no state file anywhere, because a state file goes stale the moment a job ends and `squeue`
never does. Loading versus warm cannot come from Slurm — the gateway binds its port before it
loads anything, deliberately, so a bad argument fails in milliseconds rather than after 429 GB —
so the job's own `API listening on` and `COLIBRI-SERVE READY` are read instead. `spawn.wake_colibri`
starts one on a daemon thread and returns at once, for the reason written above `wake_tutor`:
nothing that takes as long as a start can be reported by the request that triggered it.

**A workspace you are not looking at can be handed a job**, and three of the four pieces already
existed. `machines.workspaces` is the list, `tutor agent start <name> --agent <name>` is the start,
and `news.elsewhere` is how it comes back — built for this request almost word for word. What was
added is the seam: `POST /elsewhere` writes the task as a turn of theirs in that workspace's inbox,
**after** the start is allowed rather than before, so a refused job is not left in another
workspace's transcript with nothing that will ever read it.

**A colibrì card is never committed, and that is a rule about the assistant rather than about a
list of workspaces.** `research/PSYCH-ASR/.gitignore` excludes `live/*` with `live/map.json` the
single exception, so a card there is never tracked; `courses/Galois-Theory/live/cards/` is in the
pushed history. Same feature, two workspaces, and in one of them it would push the local model's
output to a remote where nothing can audit what it quoted. `git check-ignore` decides, per
workspace, at the moment of starting.

**A KV SLOT COSTS 23.9 GB AT A 131072 WINDOW, AND THE REFUSAL STAYS.** This file asked for the
measurement so that `exclusive` could come out of the `colibri` recipe and two sittings could run at
once. The measurement is in — **P0-STATUS finding 22** — and it says the opposite. A second slot
fits in RAM but takes the whole pin margin, so roughly 17 GB of experts stop being resident; it
turns speculation off machine-wide, because drafting is not ragged-safe across slots; and colibrì's
own full-residency run already shows two sessions at 3.16 tok/s each against 4.84 for one, with
aggregate saturating *below* the single-stream ceiling by four. **`exclusive` is not a placeholder
waiting on a number any more. It is the answer**, and the line stays in.

**And the four board defects reported from that Galois sitting are fixed.** The write-up phrasing
rule, the pulse that stopped before the answer arrived, the typed answer that raised no pulse at
all, and the typed answer that did not come back for correction. All four are in
`../../HANDOFF.md` under *Settled*, because they are the board's and follow the board's rules.
