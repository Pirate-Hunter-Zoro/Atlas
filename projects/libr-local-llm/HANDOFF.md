# HANDOFF.md

**The harness is built. The first job has not been run through it.**

`coli-up`, `coli-code`, `coli-ask`, `coli-down` and `coli-build` exist, are on `PATH`, and serve
GLM-5.2 int4 to a coding agent in any directory. README §4c is the architecture and is the file to
read; this one says what is left.

What has actually been run through it: the model emits a correct Anthropic `tool_use` block in
43.6 s, which is the whole of a coding CLI's loop; `coli-ask` answers a real question in 51 s at
3.14 tok/s; and Claude Code's system prompt, 21 tool definitions and streaming all cross the
protocol intact. What has **not** been run is a full agent turn against the model, because the
client's preamble is 15,900 tokens and prefill here is two to three hours at that size. That is the
first item below, and it is an overnight job.

---

## The job still waiting, in the owner's words

> Look at all the dirty details of `phi`, look at the community-1 diarization, and look at
> Madison's corrections/error-log CSV. Using those two things, do whatever you need to do to
> reproduce a perfect transcription based on the corrections, and document how you did it.

Nothing about that has changed. What has changed is that there is now something to hand it to.

The half that cannot be delegated is still the same: a hosted assistant cannot read `phi`.
Everything it *can* do — review the algorithm colibrì writes, referee the before-and-after counts,
write the documentation — it should keep doing, because those artefacts are code and numbers and
both cross the fence.

---

## What to do next

**1. Run it, and start it before you stop for the day.** `coli-up`, then
`coli-code -d <the PSYCH-ASR checkout>` with the task above. The agent can read `phi` — that is the
whole point, and it is why `coli-code` gives the client a fresh config directory with no PHI hook in
it. **The first turn is hours, not minutes**, and after it the KV prefix carries the preamble, so the
thing not to do is kill it at the ninety-minute mark and start again. Leave the server up between
tasks for the same reason.

**2. Score it, and do not read the session to do so.** The acceptance test is a number, not a
judgement. `unplaced_rows` is `[16, 32]`, `within_2s` is 68 of 74, stray marks are at zero. A
reconstruction is better if those move the right way:

```
python3 -m psych_asr.cli.apply_corrections --dry-run --anonymise
```

Counts, spreadsheet row numbers and seconds. It names the participant nowhere, which is what makes
a rule colibrì proposes testable by somebody not cleared for what it was tested on.

**3. Decide the two questions the harness deliberately left open.**

- **KV slots.** The server runs one. One slot means one conversation's prefix cache; a second
  client evicts the first, and the eviction costs the whole preamble again. The engine supports 16
  and `COLI_KV_SLOTS` is wired through, but each slot costs real memory at a 131072 window and
  nobody has measured how much. Decide when there is a second driver, not before.
- **`MTP`.** The engine turns native speculative decoding on by itself, and what P0 measured as a
  loss was setting `MTP=1` explicitly on top of that. Which of the two states it measured is not
  recoverable from the result. It is one A/B on a warm server, in one job on one node, and it is
  worth doing before anybody quotes a tok/s figure again.

---

## Where the model's own words go, and why that was the hard part

**A driver that can read `phi` writes a transcript that quotes `phi`.** This is settled and should
not be re-opened.

`slurm_jobs/logs/**` is exempt from the fence on a stated understanding — *the jobs print counts
and durations, not text* — and `COLI_DEBUG` would break it for everybody downstream with one
environment variable. The serve job refuses to start when it is set, by name, at the top. That is
enforcement, not hope.

The agent's own session store does not go in `~/.claude` or `~/.local/share` either, because that
is where a hosted assistant reads all day. It goes under `$COLI_SESSION_ROOT`, which ends in a
directory named `phi` and is therefore already fenced whole, at any depth, by the rule that
survived the data moving twice. Nothing new was invented and there is no second rule to keep in
step with the first.

That fence was tested the only way worth testing it: it refused this session's own attempt to write
a scratch file underneath it.

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
