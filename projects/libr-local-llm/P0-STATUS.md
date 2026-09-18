# P0-STATUS.md — where the measurement campaign actually is

**Live record of `FLEET-BUILD.md` §9. Read this before running anything in P0.**
Last written 2026-09-09 22:5x. **The campaign is complete except for tests 8 and 12.**

Working directory for everything P0: **`/media/studies/ehr_study/analysis/mferguson/fleet-p0`**
(not this repo — the repo is public and job logs are not architecture). Its `RESULTS.md` is the
long form with every table; this file is the state of play and the findings that change the plan.

---

## The one result that matters

**Tier 1 on a single A40 serves six concurrent users at 51 tok/s each with a 0.2-second first
token, behind a 15,000-token agent preamble. Tier 2 — the 744B on a whole 1 TB node — tops out at
3.2–4.4 tok/s for one user, depending on which node it lands on.**

That is **12–16× per session and 70–90× in aggregate, on a thirtieth of the hardware.** §9 called
test 8b "the question that decides everything" and the answer is unambiguous: the floor alone is
good enough, and the 744B is not an interactive model on this cluster. See "What this does to the
design" below.

---

## Test results

| # | test | verdict |
|---|---|---|
| 1 | colibrì build + `AVX512 i4 selftest` | **PASS** |
| 2 | stage GLM-5.2 | **PASS** — 429.2 GB in 61.6 min at 116 MB/s |
| 3 | cold vs warm load | **PASS** — and the cost is in decode, not load |
| 4 | `coli plan` + `coli tune` | **PASS** — 100 % expert residency; tune changed nothing |
| 4b | OpenMP thread sweep *(added)* | **PASS** — the allocation's count wins, not the physical one |
| 5 | `CUDA_DENSE` A/B | **PASS on re-run** — it is not a lever |
| 6 | one A40 vs four | **PASS** — four cards are worth 0.9 % |
| 7 | `XEXP` / NUMA / MTP / `DRAFT` | **PARTIAL** — interleave wins; the MTP arm never tested what it named, see finding 21 |
| 8 | vLLM TP shapes | not started — needs the large helper (73.1 GB) downloaded |
| 8b, 9 | tier 1 under 1–8 concurrent users | **PASS** — see above |
| 10 | `c3` preemption | **CONFIRMED in 4 s** |
| 11 | restart chain via `afterany` | **PASS** |
| 12 | the `eval/` suite | not started — but now unblocked, a backend answers |

---

## Jobs still running

**None.** Every P0 job submitted on 2026-09-09 has finished and its output is on disk. Jobs 2070808,
2070811, 2070817, 2070818, 2070819 and 2070821 all exited on their own; nothing needs cancelling.

Each colibrì job wrote `RESULT tag=… tps=…` lines into its own `timeline.txt`, so
`grep '^RESULT' fleet-p0/*/timeline.txt` is the whole campaign in one screen.

---

## Findings that change the runbook

The first six were recorded earlier on 2026-09-09 and still stand. Seven through fifteen are new.

1. **`--exclusive` is refused on every partition.** `MaxCPUsPerNode=92`. Asking 94/95/96 or
   `--exclusive` fails at submission with `Requested node configuration is not available`, which
   names neither the limit nor the flag. **92 is the ceiling for every fleet job.**
2. **"`c3_short` for everything" cannot be honoured on compute306.** `c3_accel` is the *only*
   partition containing that node. It is safe anyway — partition-priority preemption needs a
   higher-tier partition on the same node and there is none. State the rule as **`c3_short` on
   compute300–305, `c3_accel` on compute306, never `c3`**.
3. **GLM-5.2 is 429 GB, not 372** — and it occupies **498 GB** of the share. Corrected in
   `FLEET-BUILD.md` and `README.md`. The two numbers are the same files measured two ways and
   both are needed: 429.3 GB is the data (`du --apparent-size`), 498.5 GB is what the filer
   actually allocates for it, a 16 % gap across 142 shards. **Plan free space against the
   larger one.** Quoting the smaller against a quota is how a stage runs out at 90 %.
4. **colibrì sizes its thread pool from the machine, not the allocation** — it prints *"48
   physical-core threads instead of 96 logical CPUs"* and re-execs once to apply it.
   **Superseded in part by finding 9: the pin is right, the engine's choice of value is wrong.**
5. **`sbatch --test-only` lies about start times here.** It predicted 17 hours out for a job that
   started in 2 seconds. **The supervisor must not use it as an availability probe** — submit and
   read the state.
6. **`pip` disables its cache anywhere under `…/analysis/mferguson`**, because that directory is
   owned by a different uid than the account using it. Every install there re-downloads.

### 7. `pip` installs into `~/.local` even when told not to, and it is `os.access`'s fault

This cost the first tier-1 measurement run and 8.7 GB of a 100 GB home share.

pip decides where to install by calling `test_writable_dir()`, which on POSIX is one line:
`os.access(path, os.W_OK)`. On this Isilon that call returns **False** for a directory the same
process can then write to without error — the filer synthesises the POSIX mode bits lossily from
the real NFSv4 ACL, which is the same defect `ai-config/PERMISSIONS.md` documents for the mode bits generally.
pip concludes the environment is unwritable, logs *"Defaulting to user installation because normal
site-packages is not writeable"*, and puts 8.7 GB in `~/.local` — which then **shadows the
environment at import time**, so the job runs a copy of vLLM nobody meant to install.

**`--no-user` is not the fix**, or not reliably: pip only consults it before the probe if it was
actually parsed, and the failure is silent when it is not. **`PYTHONNOUSERSITE=1` is the fix.** It
flips `site.ENABLE_USER_SITE` to False, which pip checks *ahead* of the writability probe, and it
also stops `~/.local` shadowing the environment at run time. **Set it in every install script and
every job script that activates an environment on this filer.**

There are still 8.7 GB of the accidental install at `~/.local/lib/python3.12` and home is 86 % full.
Nothing depends on it — `~/.local/lib/python3.{9,11,13}` are unrelated and older, and the whole
`python3.12` tree is from the accident. **`rm -rf ~/.local/lib/python3.12` is safe and yours to
run**; leave `~/.local/bin` alone, it holds TeX and other tools that predate this.

### 8. There is no `/usr/local/cuda`, and vLLM's default sampler needs one

vLLM 0.29 defaults to the FlashInfer sampler, which **JIT-compiles a CUDA kernel during warm-up**.
The build looks for `nvcc` at `/usr/local/cuda`, which does not exist here because CUDA is a module.
The server dies after loading weights, allocating 21.8 GiB of KV cache and capturing CUDA graphs —
minutes in, with `RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't
exist` buried under two screens of unrelated traceback.

`module load CUDA/13.1.0` and exporting `CUDA_HOME=$EBROOTCUDA` fixes the lookup. **We set
`VLLM_USE_FLASHINFER_SAMPLER=0` as well and should keep it**: a kernel build inside the serving path
is a cold-start hazard for a fleet whose whole promise is fast restarts, and the JIT cache would
land on a slow shared filer. The measured tier-1 numbers were taken with it off.

### 9. On this CPU, more threads than physical cores keeps winning — the engine disagrees and is wrong

Our nodes are **2 sockets × 24 cores × 2 threads = 48 physical, 96 logical**, Xeon Gold 6342.
colibrì's own source table (from a single-socket 24-core EPYC) shows decode *falling* from 2.90 to
2.06 tok/s going from physical to logical, and the engine self-tunes down to 48 on that basis.

Measured here, tok/s rises monotonically with thread count: 0.65 at 12, 2.00 at 48, **2.75 at 92**.
Self-tuned (48) gives 2.65. The sweep alone is confounded — it ran ascending on a warming page
cache — but **`coli tune` independently tested `omp-48` and `omp-24` with interleaved replays on a
fully warm cache and retained the 92-thread baseline.** Two instruments, same answer.

**Set `OMP_NUM_THREADS` from `SLURM_CPUS_PER_TASK` and let it exceed the physical core count.**

### 10. The cold-start penalty is in generation, not in loading

Cold, a tier-2 run decodes at **0.64 tok/s**. Warm, the same run decodes at **2.88**. Loading only
halves, 101 s to 48 s. colibrì mmaps the checkpoint and faults expert slabs in *during* generation,
so a cold replica pays the filer on every token.

**A tier-2 replica is not in service when the process is up.** It is in service roughly one full
generation later. Any supervisor that equates "ready" with "listening" hands the first user a model
running at a fifth of its speed. §4.3's pool needs a warm-up request before a replica is advertised.

### 11. `numactl --interleave=all` is worth 14 %, and `coli tune` cannot find it

429 GB of warm experts against two 515 GB NUMA nodes. Binding to one socket fits, barely, and loses
6 %. Interleaving wins **14 %** over doing nothing, and beats colibrì's own `COLI_NUMA=1` by 8
points. `coli tune`'s candidate set is thread counts and CUDA stream shapes only — it cannot propose
memory placement, so it retained a baseline that was 14 % off the best available configuration.

**Run `coli tune` once for the profile, then do the NUMA A/B by hand.** And in the same sweep:
`XEXP=1` costs 12 % and should be dropped from §10's starting configuration, `DRAFT=2` costs 11 %
and `DRAFT=4` costs 19 %, confirming §3.3's argument that speculation fails on this workload.

### 12. Four A40s are worth 0.9 %, and §2.2's correction of colibrì was the error

§2.2 dismissed colibrì's published "four GPUs are worth under 2 %" as *"colibrì's number on a
CPU-starved host, not ours"*. Measured on compute306 with 88 CPUs, 900 GB and all four cards warm:
**4.31 tok/s on one card, 4.35 on four.** We reproduced their number almost exactly.

The bottleneck is the CPU expert tail, which is what `coli plan` says in one line — `limit  CPU
expert tail and GPU compute`. Adding VRAM does not move it.

**Give tier 2 one card, not four.** The other three on compute306 are worth roughly 300 tok/s of
aggregate tier-1 throughput each against a 0.9 % gain here. Nothing in §4.3's pool should reserve
compute306 for the big model.

### 13. tok/s is not comparable across nodes — a 36 % spread with no configuration difference

compute306 ran at **4.31 tok/s** on one card where compute302 managed **3.17** — same model, same
commit, same `numactl --interleave=all`, both warm. compute302 was sharing its page cache with other
tenants. Every A/B in this campaign was therefore run inside one job on one node, and any future
comparison must be too. The absolute tier-2 figure is a range, **~3.2–4.4 tok/s**, depending on who
else is on the node.

### 14. `MaxCPUsPerNode` is a partition-wide cap, so a co-tenant lowers your ceiling

A 92-CPU request for compute306 pended on `(Resources)` indefinitely while all four of its GPUs sat
idle, because another user's job held 2 CPUs there and 92 is the cap on what the *partition* may
hold on that node. Asking for 88 started immediately. **On a shared node, ask for a little under the
cap** — and read `(Resources)` as "somebody else is here", not "the hardware is busy".

### 15. `CUDA_DENSE` is not a lever, and it fails loudly only if you set `COLI_CUDA=1`

`CUDA_DENSE=1` alone exits at once with `CUDA_DENSE requires COLI_CUDA=1` — a one-line message that
a harness records as a fast failure and a human reads as a fast run. With both set and three
alternated repeats: `CUDA_DENSE=0` gives 2.67 tok/s, `CUDA_DENSE=1` gives 2.56. §3.4 asked how much
of the dense half the GPU takes; the answer is that moving it does not change the total. **Drop it
from §10.**

Plus the one already known and paid for twice: **job output must not go to `/tmp`.** It is a
node-local RAM tmpfs, so a job on compute303 writes logs compute300 cannot see.

### 16. `coli serve` ran CPU-only on a node holding an idle A40, and said nothing

(Added 2026-09-16.) The launcher's GPU auto-enable block is scoped to `win32`; on Linux CUDA is
turned on only by an explicit `--gpu`, `--vram` or `--auto-tier`. A serve command with none of them
loads 429 GB, answers requests, and never touches the card. **Measured on that configuration:
0.64 tok/s decode, 1.3 tok/s prefill** — which is the same 0.64 recorded above as the *cold* tier-2
number, so it is worth asking whether the cold/warm gap in finding 10 was partly this.

`coli doctor` does not catch it. Doctor **plans** and serve **runs**: doctor reported a 45.7 GB VRAM
hot tier and ~2152 hot experts for a configuration that used neither. `GET /health` is the thing
that tells the truth — it carries `"gpus"` and `"vram_gb"` from the running engine.

Two smaller facts fell out. `--gpu` does `setdefault("CUDA_DENSE","1")`, and finding 15 measured
`CUDA_DENSE=1` at 2.56 against 2.67, so a job wanting the GPU has to turn that back off explicitly;
every variable the planner writes is a `setdefault`, so an exported `CUDA_DENSE=0` wins. And with
the plan applied the engine reports `[MTP] … draft=0` where the CPU-only run reported `draft=1`.

### 17. The context window defaults to 4096 and the maximum is 1048576

(Added 2026-09-16.) `family_by_id("glm").limits.default_context` is **4096**. That is smaller than
any coding agent's system prompt, and an over-long prompt is truncated from the front, which is
where the system prompt and the tool definitions live — trap 24's failure mode at a twentieth of
the size. Raising it is nearly free here: `coli plan` at 4096 / 32768 / 65536 / 131072 gives runtime
allocations of 7.3 / 15.8 / 25.6 / **45.0 GB** and moves nothing else. Warm experts stay at
371.7 GB, the VRAM hot tier at 45.7 GB, projected residency at 100%.

### 18. The cold load is no longer 101 seconds, because the router learned

(Added 2026-09-16.) `.coli_usage` has grown from the 58,240 selections noted below to **1,735,272**,
and at that confidence the planner stops streaming and pins: `plan 424.5 GB (conf 1.00) … -> pinning
424.5 GB`, read off the filer before the first token. Observed rate against a cold-ish page cache:
93 GB at 3:45 and 250 GB at 6:00, so several hundred MB/s and **minutes, not seconds**. That is the
better trade — the cold-start cost is paid in one place instead of leaking into the first user's
decode rate, which is what finding 10 describes — but a supervisor budgeting 101 seconds for a load
will call it a hang.

### 19. Two things the launcher reports that are not true on this filer

(Added 2026-09-16.) `coli doctor` warns `storage.persistence: model directory is read-only; disable
persistence or change permissions` against a directory the same account writes to without error.
Same root cause as finding 7: `os.access` believes mode bits the filer synthesised lossily from an
NFSv4 ACL. The warning is a false negative; `.coli_usage` and KV persistence both work. **Do not
chmod to satisfy it** — a chmod on this filer writes back a mode derived from that same bad reading.

And the gateway **binds its port before it loads the model** — `APIServer` is constructed before
`Engine`, on purpose, so a bad argument fails in milliseconds instead of after 429 GB. A TCP probe
therefore succeeds about two seconds into a job whose model needs minutes. The line that means the
model is up is the gateway's own `OpenAI-compatible API listening on …` on stderr. The connection a
probe gets is not wasted: a request lodged in the accept queue during the load is served the
instant the engine exists, which is how `colibri_serve.sbatch` has its warm-up already in flight.

### 20. Tier 2 measured as a served endpoint: 3.8 tok/s prefill, 2.3–3.0 tok/s decode

(Added 2026-09-16. One A40, 88 CPUs, `numactl --interleave=all`, `--gpu auto --auto-tier`,
`CUDA_DENSE=0`, `--ctx 131072`, compute301, warm, one request at a time.)

| prompt | time to first token | implied prefill | decode |
|---|---|---|---|
| 35 tokens | 6.0 s | — | 2.98 tok/s |
| 961 tokens | 249.9 s | 3.8 tok/s | 2.26 tok/s |
| 3,857 tokens | 1382.7 s | **2.8 tok/s** | — |
| 35 tokens, **CPU-only** (finding 16) | 26.6 s | 1.3 tok/s | 0.64 tok/s |

Decode lands inside the 3.2–4.4 range recorded above, at the low end, on the node that was the slow
one in finding 13. **Prefill is the new number and it is the one that governs**, because it had
never been measured here.

**And prefill does not scale linearly.** Four times the tokens cost six times the wall clock, so the
rate falls as the prompt grows — attention, and it means a preamble cannot be priced by multiplying
a small measurement. Extrapolating those two points to a 15,900-token coding-agent preamble gives
**somewhere between two and three hours before the first word.** That is an extrapolation from two
measurements and is labelled as one; what is measured is the two rows above it. Upstream warns about
exactly this and says it applies hardest to Claude Code, and nothing here disagrees.

**What makes an agent loop survivable anyway is the KV prefix cache, and it works.** Observed in the
gateway's own accounting across two stateless HTTP requests that shared a preamble:

```
[API] KV slot 0 prefix  19/980  token, prefill 961
[API] KV slot 0 prefix 963/4820 token, prefill 3857
```

963 tokens matched and were not re-run. So the 80 minutes is paid **once per conversation**, not per
turn, and each later turn prefills only what it added. That is the difference between an overnight
job and an impossible one, and it is the argument for the serve job holding one long-lived process
rather than starting an engine per task.

Two consequences for anything built on this. **A drive that resets the conversation resets the
bill** — a fresh session per task is right advice for tier 1 and expensive advice here. And **a
second concurrent client evicts the first client's prefix**, because the server runs one KV slot.
What a second slot costs, and why it stays at one, is finding 22.

**The coding agent's preamble, priced exactly.** Claude Code's first request was captured against a
stub endpoint that answers instantly, rather than discovered by waiting for the real one:

```
/v1/messages?beta=true  bytes=63009  system=5991  tools=21 (48223 chars)  messages=9272
```

63 kB, **~15,900 tokens, and the tool catalog is three quarters of it** — 21 tools, 48 kB. Against
3.8 tok/s falling with length, that is **an hour and a half before the first word**, once per
conversation. A fresh, empty config directory is what keeps it to 15,900: MCP servers, plugins and
a global `CLAUDE.md` all land in the same request and are all paid at the same rate.

Two client facts fell out of the same capture, and both are settings rather than surprises. The
client does not recognise the model id, so it assumes the 200k window it uses for the ones it does
know and sizes auto-compact against that — 69k tokens past what the server accepts. It names its own
fix: `CLAUDE_CODE_MAX_CONTEXT_TOKENS`. And the protocol itself needs nothing: system prompt, 21 tool
definitions and streaming all went through the Anthropic path unmodified, and the reply came back.

**And a disconnected client does not stop a prefill.** The probe was killed mid-request and the
engine went on prefilling 3,857 tokens for another twenty minutes, with everything behind it queued.
`/health` counted the request `cancelled` while still reporting it `active`. Budget for that before
cancelling something and immediately submitting its replacement.

### What was actually run through it, end to end

(Added 2026-09-16, same server, after the queue drained.)

**The agent mechanism works on the real model.** One tool definition, a short prompt, no agent
preamble — `POST /v1/messages` came back in **43.6 s** with `stop_reason=tool_use` and a single
`tool_use` block naming the tool and its argument correctly:

```
tool_use: name=read_file  input={"path": "notes.txt"}
```

That is the thing a coding CLI's loop is made of, and it is the last part that could have been
protocol rather than wall clock. It is not. What stands between this and a finished task is time.

**`coli-ask` is genuinely interactive.** A real question, 200 tokens of answer: **7.2 s to first
token, 51.2 s total, 3.14 tok/s**, and the answer was correct. This is the command to reach for.

**Claude Code's protocol path is verified but was not run to completion against the model.** Its
system prompt, 21 tool definitions and streaming all went through against a stub endpoint and the
reply came back; the preamble is the 15,900 tokens priced above, so a first turn is the two-to-three
hours the extrapolation gives. Nobody has sat through one yet. That is the next thing to do and it
is an overnight job, not a demonstration.

---

## What this does to the design

**§11.2's escalation problem is now a resource question with an answer.** Tier 2 is not a slower
interactive model. At 4 tok/s a 500-token reply takes two minutes and occupies a whole
1 TB node while doing it. The runbook should stop describing it as a tier users are *routed* to and
start describing it as one they are **queued** for.

**Size the tier-1 pool by tokens, not by users.** One A40 holds 237,904 KV tokens. Six users can
carry ~39k tokens of context each; the advertised 65,536-token window supports only 3.6 simultaneous
sessions. Throughput was still climbing at 8 users, so KV is the binding constraint, not compute.

**§12's build order should be re-read in that light.** Everything the service promises interactively
is delivered by tier 1 on one of the ten cards, today.

---

## Decisions taken since the runbook was written

### The two checkpoints (§13 decision 3, §4.5)

Chosen off the live Hugging Face roster on 2026-09-09 under §0.4's rule — fewest active parameters
that clears the bar.

| | repo | on disk | active | cards | status |
|---|---|---|---|---|---|
| **standard helper** | `cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` | **18.1 GB** | **3.3B** of 30B | 1 | **downloaded and measured** |
| **large helper** | `QuantTrio/GLM-4.5-Air-AWQ-FP16Mix` | 73.1 GB | 12B of 106B | **2** | not downloaded |

The standard helper is compressed-tensors int4 at **group size 32** — finer than the usual 128,
which is the same grouped-scale argument §11.1 makes in colibrì's favour. 128 experts, top-8, 48
layers, 262144 native context. Measured: 17.94 GiB of weights on the card, leaving 21.78 GiB of KV.
It ships its own `qwen3coder_tool_parser.py`, and vLLM 0.29 has a matching built-in
`--tool-call-parser qwen3_coder`.

**§4.5's same-family preference was deliberately broken for the large helper.** The Qwen sibling is
`Qwen3-235B-A22B-AWQ`: 124 GB, four cards, 22B active, 737 downloads, untouched since May 2025.
GLM-4.5-Air is 12B active on **two** cards and leaves half of compute306 for somebody else, which
wins on both of §0.3's hard rules. vLLM has a `glm45` tool parser for it.

### The stage was authorised

The user was asked (§0.1) and said **start it now, in parallel**. That was job 2070808, and it
finished.

---

## Environment built for P0

| what | where |
|---|---|
| colibrì binary, `ARCH=native CUDA=1 CUDA_ARCH=sm_86` | `~/colibri-build/c/colibri` (clone of `~/colibri` at `fd93c41`) |
| colibrì launcher | `~/colibri-build/c/coli` — **needs Python ≥ 3.10** |
| vLLM 0.29.0, torch 2.13.0+cu130 | conda env `…/mferguson/venvs/vllm_env`, python 3.12 |
| Hugging Face downloader | venv `…/mferguson/venvs/hfdl`, `hf` 1.8.0 |
| standard helper weights | `…/mferguson/models/vllm/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` |
| GLM-5.2 int4, 429.2 GB | `…/mferguson/models/colibri/glm52_i4` — **staged** |
| colibrì tuning profile | `~/.config/colibri/tuning/7c3733f730b0062b4ce6.json` |
| job files, harness, results | `…/mferguson/fleet-p0/` |

**`coli` will not run under the node's `python3`.** It is 3.9.25, and `coli` uses
`dataclass(slots=True)`, which is 3.10 and later. The failure is a bare `TypeError: dataclass() got
an unexpected keyword argument 'slots'` with no hint about versions. Load
`Python/3.12.3-GCCcore-13.3.0` in every job that drives colibrì.

**`~/colibri-build` is a separate clone on purpose.** `~/colibri` is the read-only checkout the daily
`colibri-pull` timer fast-forwards (`README.md` §2.1); building in it would leave objects in a tree
the timer expects clean.

Modules the build needs: `CUDA/13.1.0`, `GCC/13.3.0`. `ARCH=native` is load-bearing and verified —
it defines `__AVX512VNNI__`, which is the 67.8 → 89.5 GB/s int4 kernel.

**The `.coli_usage` shipped with the checkpoint already carries 58,240 selections.** Measurements
are not starting from an unlearned router, which is one more reason §10's snapshot protocol matters:
the harness at `fleet-p0/coli_ab.sh` saves it, sleeps 35 s for VRAM to drain, restores it
byte-for-byte, then measures.

### 21. Speculation is OFF on the served configuration, and `[MTP] active` does not mean it is on

(Added 2026-09-18. Read out of the engine source and the serve job's own log; no GPU hour spent.)

The runbook said the engine turns native speculative decoding on by itself and that what P0 measured
was setting `MTP=1` on top of that. **Both halves are wrong**, and the line that misled everybody is
`colibri.c:11198`:

```
[MTP] active: native speculative decoding (draft=0)
```

`active` is chosen by `m.has_mtp` — whether the CHECKPOINT carries an MTP head. Ours is the
`-with-int8-mtp` container, so that word is printed on every start whatever happens next. **`draft=`
is the half that says whether anything is drafted**, and at 0 nothing is: `g_spec_live = (g_draft>0)`
and every drafting branch is gated on the same test.

Two independent layers both hold it at 0 on the configuration the serve job runs:

- **The engine's own CUDA default.** `g_draft` is `-1` when `DRAFT` is unset, and the auto
  resolution is `g_draft = (m.has_mtp && (!g_cuda_enabled || cuda_mtp)) ? 1 : 0`. We pass `--gpu
  auto`, so CUDA is enabled and the answer is 0 unless `COLI_CUDA_MTP=1` is exported. The reason is
  named upstream (#163): cold experts run on the CPU, where the S==1 fused-pair kernel and the S>=2
  IDOT kernel diverge in FP accumulation order, and draft acceptance collapses.
- **`--auto-tier`.** `resource_plan._auto_tune` exports `DRAFT=0` for a compute-bound plan, which
  `coli plan` says this is in one line — `limit  CPU expert tail and GPU compute`.

**`MTP=1` is not a lever and never was.** `MTP` is read in exactly one place, `colibri.c:2406`, and
only `MTP=0` does anything — it strips the head. So the `t7_mtp` configuration in the P0 campaign
measured the baseline a second time: 2.72 tok/s against `t7_base`'s 2.88, which is run-to-run spread.

**And `DRAFT=2`/`DRAFT=4` were measured against speculation ON, not off.** `coli_ab.sh` runs `coli
run` with no `--gpu`, so `g_cuda_enabled` is false and the auto path gives `draft=1`. Every
`[MTP]` banner in the campaign's logs confirms the split: 25 runs at `draft=1` (every CPU-only
configuration), 12 at `draft=0` (every one with CUDA on), one each at 2 and 4. So P0's −11 % and
−19 % are **depth 2 and depth 4 against depth 1**, which is what the engine's own sweep already
predicts — the comment at `colibri.c:11169` reports ~85 % acceptance at depth 1 against ~44–62 % at
2–3, and calls depth 1 the fastest MTP setting in every configuration it measured. §3.3's conclusion
that "speculation fails on this workload" does not follow from those two numbers.

**Nothing on disk isolates MTP, and that is structural rather than an oversight**: the variable is
perfectly confounded with CUDA across the whole campaign, because the engine ties them together.
Every `draft=1` run is CPU-only and every `draft=0` run has the card.

**The two layers are not two locks, and that matters for how the A/B is built.** The planner's
DRAFT=0 is written with an explicit exception for exactly this variable: `_auto_tune` returns no
`DRAFT` at all when `COLI_CUDA_MTP=1` is in the environment, and its own comment says why — an
exported `DRAFT=0` preempted the engine's auto path and made the opt-in silently inert. Verified by
calling it directly, no GPU hour: compute-bound with the variable unset gives `DRAFT=0`, with it set
to `1` gives nothing, with it set to `0` gives `DRAFT=0` again. So `COLI_CUDA_MTP=1` clears both
layers with one export, and the arms differ in that one variable.

**The A/B is written and is `slurm_jobs/p0/t21_mtp_depth1.sbatch`.** One job on one node under §10's
snapshot protocol, mirroring the served configuration rather than a convenient one — `--gpu auto
--auto-tier --ctx 131072`, `CUDA_DENSE=0`, 80 CPUs, 800 GB, `numactl --interleave=all`, which is
what `colibri_serve.sbatch` runs. A discarded warm-up run first, because the first pin on a node
reads 424.5 GB off the filer at 422 MB/s and a cold run decodes at 0.64 tok/s against a warm 2.88.
Then six runs ordered ABBAAB rather than ABABAB, so drift over the job does not land on one arm.
**The depth to test is 1**, which no P0 run tried.

**It records the draft depth and the acceptance rate, not just tok/s**, and that is the correction
this finding is made of: a tok/s difference between two arms that both ran `draft=0` would be noise
read as a result. `[MTP] … (draft=N)` says what the engine resolved and the `speculation:` line at
`colibri.c:8205` says what happened — tokens per forward, and MTP acceptance as a percentage. The
job also refuses to start if `COLI_CUDA_MTP` or `DRAFT` is set in the submitting environment, which
would put the lever in both arms.

It is worth the hour because the engine's CUDA default is written for a host where "the cold subset
always exists on a single 16 GB card" — and this box plans 100 % expert residency with 45.4 GB of
hot experts in VRAM, which is the one condition under which that divergence mostly does not arise.

### 22. A KV slot costs 23.9 GB at a 131072 window, and the refusal stays anyway

(Added 2026-09-18. Computed from the planner's own geometry for this checkpoint, cross-checked
against a real serve job's log; no GPU hour spent.)

`resource_plan.build_plan` prices slots linearly — `kv_bytes = (context_state_bytes +
fixed_state_bytes) * kv_slots` — and for `glm` at this checkpoint:

| context | per-slot KV | runtime reservation at 1 slot | at 2 |
|---:|---:|---:|---:|
| 4,096 | 0.75 GB | 7.3 GB | 8.1 GB |
| 32,768 | 5.96 GB | 15.8 GB | 21.8 GB |
| 65,536 | 11.93 GB | 25.6 GB | 37.6 GB |
| **131,072** | **23.86 GB** | **45.0 GB** | **68.9 GB** |

The 45.0 GB column reproduces finding 17's measured `coli plan` figures exactly, which is what makes
the second column trustworthy.

**It fits, and it comes straight out of expert residency.** From the serve job's own log at 950 GB:
`[PIN] … max_pin 431.6 GB -> pinning 424.5 GB` and `[RAM_GB=905.3] … projected peak 856.6 GB`. There
is 7.1 GB of pin headroom, not 23.9, so a second slot drops `max_pin` below what the plan wants to
pin and roughly 17 GB of experts stop being resident — off 100 %, onto the filer, at 0.64 tok/s a
token for whatever faults.

**And a second slot turns speculation off machine-wide**, if finding 21's A/B ever turns it on:
`mux_will_disable_mtp` is `SERVE && SERVE_BATCH && KV_SLOTS>1`, because drafting is not ragged-safe
across slots. (FLEET-BUILD §3.3 states this the wrong way round — it says `KV_SLOTS=1` and MTP are
*mutually exclusive*, when `KV_SLOTS=1` is the case that KEEPS MTP. Its next sentence gets it right.)

**And the throughput half was already measured, by colibrì, under full residency**: aggregate
saturates at ~8.3 tok/s by four sessions — *below* that host's own single-stream baseline — while
per-session falls 4.84 → 3.16 → 2.04 → 1.04 at 1/2/4/8. The union arithmetic in §3.3 says why, and
it is a property of top-8-of-256 routing rather than of that host.

**So the machine-wide refusal in the `colibri` recipe stays**, and now for a written reason. Two
sittings at once would each run slower than one, both would lose the pin margin, and both would lose
speculation. `exclusive` is not a placeholder waiting on a measurement any more; it is the answer.

---

## The next three things, in order

1. **Test 12, the `eval/` suite.** It was blocked on a serving backend and is not any more: tier 1
   answers, on one card, 281 seconds from a cold submit. This is now the last thing standing between
   P0 and P1, and §11.3 already specifies it.
2. **Re-read §4.3's pool against findings 12 and 13.** Tier 2 should hold one card, not four, and
   the supervisor must warm a replica before advertising it. Both are small edits to a design that
   has not been built yet, which is the cheapest moment to make them.
3. **Test 8** — TP=2 vs TP=4 vs independent replicas — needs the large helper downloaded (73.1 GB).
   **Ask whether it is still wanted first.** Its whole justification was that tier 2 is too slow to
   escalate to; tier 1 measured well over 10× faster than tier 2, and four cards buy 0.9 % on the big model.
   A second, larger vLLM helper may be solving a problem P0 just dissolved.

**One cleanup for the user, not urgent:** `rm -rf ~/.local/lib/python3.12` recovers 8.7 GB of the
accidental pip install described in finding 7. Nothing depends on it. Leave `~/.local/bin` alone.
The share is at 57 % as of 2026-09-18, so this is tidiness rather than pressure.
