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
| 7 | `XEXP` / NUMA / MTP / `DRAFT` | **PASS** — interleave wins, everything else loses |
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
accidental pip install described in finding 7, on a home share that is 86 % full. Nothing depends on
it. Leave `~/.local/bin` alone.
