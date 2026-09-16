# HANDOFF.md

**Build a way to put colibrì on a task that requires reading PHI.**

Everything else in this project serves a question about throughput. This does not. It exists
because there is work nobody cleared for the session can do, and a frontier model running on
this hardware is the only thing that can do it without the data leaving the building.

---

## The job, in the owner's words

> Look at all the dirty details of `phi`, look at the community-1 diarization, and look at
> Madison's corrections/error-log CSV. Using those two things, do whatever you need to do to
> reproduce a perfect transcription based on the corrections, and document how you did it.

That is the first task, not the only one. **What is being built is the harness that makes a
task like that easy to hand over** — a second one will follow and should not need new
plumbing.

The half that cannot be delegated: a hosted assistant cannot read `phi`, which is why this
exists. Everything a hosted assistant *can* still do — review the algorithm colibrì writes,
referee the before-and-after counts, write the documentation — it should keep doing, because
the artefacts that cross the fence are code and numbers, and both are readable.

---

## What is already here

**The engine.** `vendor/colibri`, a submodule, fast-forwarded daily by `colibri-pull.timer`
and on every login by `tutor resume`. `vendor/colibri-build` is the same upstream pinned at
`fd93c41` and is the tree to *build* from; pulling it underneath a build is the failure the
pin exists to prevent. The `p0` jobs find it by asking git for the submit directory's root,
so a checkout anywhere uses its own build tree and one outside a checkout is refused by name
rather than run against nothing.

**The model.** GLM-5.2 int4, 429 GB, staged at
`/media/studies/ehr_study/analysis/mferguson/models/colibri/glm52_i4`.

**The front door.** `coli serve --model <dir>` is an OpenAI-compatible HTTP gateway with no
browser. GLM-5.2 supports **both** OpenAI `tools` and Anthropic `tool_use`
(`vendor/colibri/docs/api.md:52`), which is the fact the whole design turns on: an agent loop
with file and shell tools can point at it by setting `OPENAI_BASE_URL`, rather than being
written from scratch around a chat endpoint.

**The speed, measured, not guessed.** 3.2–4.4 tok/s for one user on a whole 1 TB node
(`P0-STATUS.md`). That is a batch tool. An unattended overnight run is the shape of every job
here; an interactive one is not.

**The scoreboard.** `research/PSYCH-ASR`'s correction pass already reports on itself with no
transcript text in it:

```
python3 -m psych_asr.cli.apply_corrections --dry-run --anonymise
```

Counts, spreadsheet row numbers and seconds. It names the participant nowhere. Any change to
the repair algorithm is scored by re-running it, which takes about a second — so a rule
colibrì proposes is testable by somebody who cannot read what it was tested on.

---

## What to build

**1. A serve job.** An sbatch that brings `coli serve` up on one node and writes its address
where a driver can find it. Follow `slurm_jobs/p0/t34567_colibri.sbatch`, with P0's findings
already applied: **one GPU, not four** (four are worth 0.9 %), `numactl --interleave=all`
(worth +14–18 %, and `coli tune` cannot find it), and no `CUDA_DENSE`, `XEXP` or `DRAFT` —
all three measured as losses.

**2. A driver.** The agent loop: read a file, write a file, run a command, repeat. Pointed at
the served endpoint. The decision to make before writing it is whether to adopt an existing
agent CLI by pointing its base URL at `coli serve`, or write the loop directly against
`/v1/chat/completions`. The first is far less code and inherits a tool protocol that already
works; the second is the only option if the CLI in question assumes a hosted vendor. **Try
the first.**

**3. The bargain that keeps the fence intact.** The driver runs where it can read `phi`, so
its own logs are the new risk surface. `ai-config/policy/phi.py` already exempts
`slurm_jobs/logs/**` on a stated understanding — *the jobs print counts and durations, not
text*. A driver that echoes model output into its log breaks that for everyone downstream.
**The transcript of the model's reasoning is itself PHI once it quotes the session.** Decide
where it goes, and it is not the job log.

**4. The acceptance test.** Not a judgement, a number. `unplaced_rows` is currently `[16, 32]`,
`within_2s` is 68 of 74, and stray marks are at zero. A reconstruction is better if those move
the right way, and the report says so without anyone rereading the session.

---

## Traps that cost a run each

Two from P0, both written up as findings 7 and 8 in `P0-STATUS.md`:
`PYTHONNOUSERSITE=1` (pip's writability probe lies on this filer and shadows the environment),
and `CUDA_HOME=$EBROOTCUDA` with `VLLM_USE_FLASHINFER_SAMPLER=0` if vLLM is in the picture.

Partitions: `c3_short` on compute300–305, `c3_accel` on compute306, never `c3`. **92 CPUs is
the ceiling** — asking for more, or for `--exclusive`, is refused at submission with a message
that names neither.

---

## One thing left over

`rm -rf ~/.local/lib/python3.12` recovers **8.7 GB** on a home share that is 86 % full. It is
an accidental pip install and nothing depends on it; the sandbox refused the recursive delete.
`~/.local/lib/python3.{9,11,13}` and `~/.local/bin` are unrelated — leave them.

---

## About this user

They work in a VSCode terminal on a compute node and close the laptop without warning; leave
long work as Slurm jobs that survive it, and leave a file behind that says where things are.
They read the runbook as the source of truth, so a finding that contradicts it belongs *in*
the repo, not in a chat message they will not have tomorrow.

They will tell you when an answer is convoluted, and they are usually right. When the direct
path is blocked, say what blocks it in one line and then take the most direct remaining path —
do not build a clever detour around it and present that as the answer.
