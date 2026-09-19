# libr-local-llm

Local LLM inference on LIBR compute — **no admin rights, no data leaving the cluster.**

> **This repo is public** (`github.com/Pirate-Hunter-Zoro/libr-local-llm`). That is defensible
> because it holds serving configuration only — no PHI, no data, no credentials — but it is a
> standing constraint on every future commit, not a one-time decision. Nothing sensitive goes in
> here. Ever.

This repo holds the serving infrastructure (Slurm jobs, client config) that the research repos sit
on top of. It is deliberately *not* part of `PSYCH-ASR` or `TRD-EHR`: both projects need local
inference, and a general-purpose model server is not a stage in either pipeline. If a third project
appears, it uses this too.

> **Why local at all.** `PSYCH-ASR` processes identifiable PHI (psychotherapy session recordings and
> their transcripts). Its README states the constraint plainly: no audio, transcript, or derived
> feature may ever leave the node or reach an external API. Every model that touches that data must
> therefore run on LIBR hardware. This repo is how that happens.

> **Documentation convention** (mirrored across all three project repos): this README documents
> **architecture only** — what exists, where it lives, how it is wired, and which traps were paid
> for. No empirical results, no findings, no model-quality claims. Sizes, ports, walltimes, and
> resource asks are architecture and belong here.

> **Companion documentation.** The live task list is
> [`planning/LOCAL-LLM_TODO.txt`](planning/LOCAL-LLM_TODO.txt) and is the answer to "what do we
> do next".

> **Where the next phase is planned.** [`DESIGN.md`](DESIGN.md) holds the design for **the fleet** —
> a preemption-aware service running all three engines (ollama, vllm, colibrì) across the cluster's
> GPUs, acquiring nodes when they are free and yielding them when somebody else needs them. It is
> design only; **nothing in it is built.** This README stays the record of what *exists*, and the two
> must not be read as one document. Durable facts graduate from `DESIGN.md` into here when a piece
> is built and verified. (Added 2026-08-22.)

> **Where the next phase is scheduled.** [`FLEET-BUILD.md`](FLEET-BUILD.md) is the build runbook.
> **Revised 2026-09-09 (fourth pass): an elastic pool over 7 nodes and 10 A40s.** The everyday
> helper needs **one GPU of ten**, so it is effectively never absent; a larger version appears on
> compute306 when that node has cards to spare; colibrì's GLM-5.2 (744B, int4, **429 GB**) sits behind
> an explicit tool call as the consultant; batch corpus work soaks up whatever is left on the
> filesystem queue, with no socket at all. The pool is filled in priority order and emptied in
> reverse, **eight of the ten GPUs release within seconds**, and the last free GPU in the partition
> is never taken.
>
> The reason for more than one model is arithmetic, not taste: GLM-5.2 routes top-8 of 256 experts,
> so the expert **union** grows almost linearly with batch size and **neither continuous batching
> nor speculative decoding amortises the dominant cost** — confirmed by a controlled full-residency
> run, not projected. Multi-user speed has to come from a different model, not a different setting.
>
> **Acceptance is assistant-run** (§11.3): a durable suite in `eval/` covering plumbing, speed,
> capability graded against ground truth already sitting in these repositories, and a pushback test
> for whether the model holds a correct answer when told it is wrong. Objective, keyed and
> subjective grading are reported separately — an assistant grading its own replacement is a
> conflict of interest that task design has to solve, not good intentions.
>
> **P0, the measurement campaign, is the only part under way, and as of 2026-09-09 ten of its
> twelve tests have passed.** [`P0-STATUS.md`](P0-STATUS.md) is its live record — which tests
> passed, what is still running, the fifteen findings that contradict the runbook, and the two
> checkpoints chosen. Nothing beyond P0 is built. A 17-slide plain-language walkthrough is
> [`docs/fleet_walkthrough.pdf`](docs/fleet_walkthrough.pdf) (source `docs/fleet_walkthrough.tex`,
> built with `pdflatex`).

> **Picking up mid-build? Read these three, in this order.**
> [`HANDOFF.md`](HANDOFF.md) — what the last session did and what it left for you.
> [`P0-STATUS.md`](P0-STATUS.md) — the measured state, and the only file that knows what has
> actually been run.
> [`FLEET-BUILD.md`](FLEET-BUILD.md) — the plan, whose §9 and §10 P0 has already partly overruled.
> Where any two of them disagree, **the one that measured it wins**, and that is almost always
> `P0-STATUS.md`. `HANDOFF.md` is rewritten at the end of every session and is never a record of
> architecture — this README is.

> **How the assistant is fenced in.** Not here. `Atlas/ai-config` is the private repository that
> owns every AI assistant's configuration on this account: the operating contract, the PHI guard
> that makes `PSYCH-ASR` diarization and ASR outputs unreadable no matter which interpreter is
> asked to open them, one settings file per vendor, and the daily audit that checks all of it. Its
> `PERMISSIONS.md` is the architecture record. It is private because the settings name real paths
> on the lab's storage and the guard describes what it is guarding; this repository is public.

---

## 0. Bootstrap from zero (order matters)

How this was built, in the order it must be redone on a fresh account or after a wipe. Details for
each step are in the numbered sections below.

1. **Get `zstd`.** `module load zstd/1.5.6-GCCcore-13.3.0`. It is not installed system-wide, and all
   Ollama Linux release assets are zstd-compressed. Prefer the `GCCcore-13.3.0` build — the 1.5.5
   build is against 13.2.0 and forces a downgrade-reload of `GCCcore` and `zlib`.
2. **Download the Ollama tarball.** `curl -L -O -f` against the GitHub release asset
   `ollama-linux-amd64.tar.zst` (v0.32.14 at time of writing, 1.42 GB). The `-L` is mandatory —
   the URL 302-redirects and curl without it silently writes a redirect stub and exits 0. The
   `ollama.com/download/...tgz` URL in older install scripts is **dead**: it redirects to an asset
   that 404s.
3. **Verify it.** `sha256sum` against the release's published `sha256sum.txt`.
4. **Extract into `$HOME`.** `tar -x --zstd -f <tarball> -C ~`. The `-C ~` is load-bearing: the
   archive holds `bin/ollama` and `lib/ollama/`, and the binary finds its bundled CUDA runtime by a
   fixed relative path. Extracted anywhere else it starts fine and then reports no GPU. This yields
   `~/bin/ollama` (39 MB) and `~/lib/ollama` (2.2 GB). Delete the tarball afterwards.
5. **Add the `~/.bashrc` block** (§3). Eight variables. `PATH`, then the seven `OLLAMA_*` settings.
   Open a new shell; `ollama --version` should print `0.32.14` and warn that no server is running.
6. **Create the model store.** `mkdir -p` the directory named by `OLLAMA_MODELS`. Use a dedicated
   `ollama/` subdirectory — the parent `models/` already holds ~120 GB of HuggingFace weights
   (whisper, pyannote, embedders) and ollama's `blobs/`+`manifests/` should not be scattered among
   them.
7. **Start a server.** `sbatch slurm_jobs/ollama_serve.sbatch` from the repo root. A GPU is *not*
   required to download models, but you need a running server for the next step, so this doubles as
   the first real test. Confirm from `slurm_jobs/logs/ollama_serve_err.txt` that it is listening and
   found the A40.
8. **Pull the models.** `ssh` to the node from `squeue`, then `ollama pull <tag>` once per model
   (§5). ~117 GB total. Concurrent pulls in separate shells are safe — different models write
   different blobs. Verify afterwards that the store grew and `~/.ollama` did **not** (it should
   hold only a ~200 KB keypair).
9. **Install opencode.** `npm install -g opencode-ai` — with `-g`, or it installs into the current
   directory and litters the repo.
10. **Write the opencode config** (§6), including the `enabled_providers` allowlist. Verify with
    `opencode models` on the server's node: exactly three `ollama/` entries, nothing remote.
11. **Put the repo's `bin/` on `PATH`.** Append it inside the `# >>> ollama >>>` block in `~/.bashrc`
    (§3). **This step is required, not cosmetic** — the driver commands (§4a) live in the repo rather
    than in `~/bin` so they stay tracked in git, which means nothing finds them until `PATH` says
    where they are. After this, steps 7 and 8 above collapse into `ollama-up` and `ollama-code`.
    A clone on a fresh account is not usable until this is done.
12. **Source the opencode guard.** Add the `if`-block for `config/opencode-guard.sh` to the same
    `~/.bashrc` block (§3). Not cosmetic either: without it, `opencode` run directly — which is the
    obvious thing to type, and which nothing else stops — fails with an unreachable API and no
    indication that `ollama-up`/`ollama-code` exist. See trap §7.22.

---

## 1. Cluster facts this repo depends on

| Fact | Value |
| --- | --- |
| Scheduler | Slurm |
| GPU partitions | `c3_short` (9 h cap), `c3` (7 d cap), `c3_accel` (7 d cap) |
| `c3` / `c3_short` nodes | 6 nodes, **1× NVIDIA A40 (46 GB) each**, ~1 TB RAM |
| `c3_accel` node | **compute306 only**, **4× A40**, 96 CPUs, 1 TB RAM |
| CPU (every node) | 2× Intel Xeon Gold 6342 @ 2.80 GHz — 24 cores/socket, **48 physical cores / 96 threads**, **2 NUMA nodes of ~515 GB each**, **AVX-512 with VNNI** |
| CPUs a job may hold | **92.** `MaxCPUsPerNode=92` on every partition, so `--exclusive`, `-c 96`, `-c 95` and `-c 94` are all refused at submission with `Requested node configuration is not available` — a message naming neither the limit nor the flag. It caps the **partition's** total on that node, so a co-tenant holding 2 CPUs lowers your own ceiling to 90 |
| CUDA | **A module, not a path.** There is no `/usr/local/cuda`. `module load CUDA/13.1.0` and use `$EBROOTCUDA` |
| Node `python3` | **3.9.25**, too old for `dataclass(slots=True)` and much else. `module load Python/3.12.3-GCCcore-13.3.0` |
| GPU compute capability | **8.6** (Ampere), driver 610.43.02. No FP8 tensor cores — AWQ/GPTQ int4, int8 and bf16 are the usable formats |
| GPU interconnect | **NVLink reports all links inactive.** Cross-GPU traffic goes over PCIe, so tensor parallelism pays an all-reduce tax on every layer |
| GPU isolation | **None.** `nvidia-smi` shows a node's GPUs whether or not you reserved one |
| Node-local scratch | **None.** `TmpDisk=0`, and `/` is a RAM-backed tmpfs. Every cold model load is an NFS read |
| `/tmp` | RAM-backed **tmpfs**, node-local, vanishes with the node. Never write logs there |
| Home | NFS, 100 GB share. Not a model store |
| Studies share | `/media/studies` → `/mnt/dell_storage/studies`, ~16 TB free |
| Outbound HTTPS | Works from compute nodes (model pulls succeed inside an allocation) |
| `zstd` | Not installed system-wide; available via `module load zstd/1.5.6-GCCcore-13.3.0` |

**The GPU-isolation point is the one that bites.** A job with no `--gres=gpu:N` still *sees* the
node's cards and can use them, but Slurm has not reserved them and will hand the same card to
someone else. Always request GPUs explicitly; verify with `scontrol show job <id>` that `AllocTRES`
contains `gres/gpu=N`, and that `CUDA_VISIBLE_DEVICES` is set inside the job.

---

## 2. What is installed, and where

Nothing here required admin rights.

| Component | Location | Notes |
| --- | --- | --- |
| Ollama binary | `~/bin/ollama` | v0.32.14, user-local |
| Ollama CUDA runtime | `~/lib/ollama` | ~2.2 GB, bundled `cuda_v12` + `cuda_v13` backends. Path is relative to the binary — do not move one without the other |
| Model weights (GGUF) | `/media/studies/ehr_study/analysis/mferguson/models/ollama` | ~117 GB. `blobs/` + `manifests/` |
| Ollama client identity | `~/.ollama/` | ed25519 keypair only, ~200 KB. **Not** model storage |
| opencode CLI | `~/.nvm/versions/node/v24.15.0/bin/opencode` | v1.18.18, `npm install -g opencode-ai` |
| opencode config | `~/.config/opencode/opencode.json` | tracked copy in `config/opencode.json` |
| Driver commands | `bin/ollama-up`, `bin/ollama-code`, `bin/ollama-down` | tracked here; put `bin/` on `PATH` (§3). See §4a |
| opencode guard | `config/opencode-guard.sh` | tracked here; sourced from `~/.bashrc` (§3). Turns a bare `opencode` into a pointer at the driver commands |
| Pre-existing HF models | `/media/studies/ehr_study/analysis/mferguson/models/` | whisper, pyannote, embedders, and `google_medgemma-27b-text-it` (safetensors, for vllm) |
| Fleet standard helper | `…/models/vllm/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` | 18.1 GB. `cyankiwi/…`, compressed-tensors int4 at **group size 32**, 30B total / **3.3B active**, 128 experts top-8, 262144 native context. Staged 2026-09-09 in 167 s |
| Fleet specialist | `…/models/colibri/glm52_i4` | **429 GB**, 149 files. `mastouri/GLM-5.2-colibri-int4-g64-with-int8-mtp` — the group-scaled container with the int8 MTP head, which is the one colibrì's own docs require |
| colibrì upstream checkout | `~/colibri` | ~89 MB. Read-only clone of `github.com/JustVugg/colibri`, kept current by a daily user timer (§2.1). Never build in it — the timer expects a clean tree |
| colibrì build | `~/colibri-build` | A second clone, pinned at the commit that was measured. Built 2026-09-09 with `make -C c glm CUDA=1 CUDA_ARCH=sm_86 CUDA_HOME=$EBROOTCUDA ARCH=native` under `CUDA/13.1.0` + `GCC/13.3.0`; 44 s. `ARCH=native` is load-bearing and verified — it defines `__AVX512VNNI__`, which selects the faster int4 kernel. Both AVX-512 selftests pass |
| vLLM | conda env `/media/studies/ehr_study/analysis/mferguson/venvs/vllm_env` | v0.29.0, torch 2.13.0+cu130, python 3.12. Selects the **Marlin** WNA16 MoE backend on these sm_86 cards |
| Hugging Face downloader | venv `/media/studies/ehr_study/analysis/mferguson/venvs/hfdl` | `huggingface_hub` 1.8.0, for the `hf download` command only |
| P0 job files, harness, logs, results | `/media/studies/ehr_study/analysis/mferguson/fleet-p0` | Deliberately outside this repo: it is public, and job logs are not architecture |

### Installing ollama from scratch

Ollama no longer publishes `.tgz` for Linux — only `.tar.zst`. The old `ollama.com/download/...tgz`
URL redirects to a GitHub release asset that 404s.

1. `module load zstd/1.5.6-GCCcore-13.3.0` (choose the GCCcore-13.3.0 build; the 1.5.5 build forces
   a downgrade-reload of `GCCcore` and `zlib`).
2. Download `ollama-linux-amd64.tar.zst` from the GitHub release with `curl -L -O -f`. **`-L` is
   mandatory** — the URL 302-redirects and curl without it writes a redirect stub and exits 0.
3. Verify with `sha256sum` against the release's `sha256sum.txt`.
4. Extract with `tar -x --zstd -f <tarball> -C ~`. The `-C ~` target is load-bearing: the archive
   contains `bin/ollama` and `lib/ollama/`, and the binary locates its CUDA libraries by a fixed
   relative path. Extract anywhere else and it starts but reports no GPU.

### Installing opencode

`npm install -g opencode-ai` (note: package `opencode-ai`, command `opencode`). Node v24.15.0 via
nvm; the global prefix is inside `$HOME`, so no sudo and it is visible on every node. npm warns that
a postinstall script was blocked — **ignore it**; the platform binary arrives as an optional
dependency and works.

### 2.1 Keeping the colibrì checkout current

(Added 2026-08-30.) `~/colibri` is a plain clone of the upstream engine, tracking `main`. It is
fast-forwarded **once a day, automatically**. This is unrelated to any tutoring or serving process
and shares nothing with them: its own script, its own log, its own timer.

| Piece | Path |
| --- | --- |
| The script | `~/.local/bin/colibri-pull` |
| Log (one line per run) | `~/.local/state/colibri-pull.log` |
| Once-a-day guard | `~/.local/state/colibri-pull.stamp` |
| Timer + service units | `~/.config/systemd/user/colibri-pull.{timer,service}` |
| Tracked copies, for a rebuild | [`config/colibri-pull*`](config/) |

Everything in the table above lives outside this repository, so verbatim copies are tracked
under [`config/`](config/) — `~/.local/bin` and `~/.config/systemd` are not backed up by
anything, and a documented timer whose script is gone rebuilds into a dead unit. Same
arrangement as §2.2, whose own copies live in `Atlas/ai-config`. The copies are
reference, not the running article: if you edit one, install it and check `diff`.

`colibri-pull` is fast-forward-only and never fatal: a dirty tree or a diverged branch is logged and
left alone, because merging somebody else's repository is not a decision a timer gets to make.
`colibri-pull --force` runs it by hand regardless of the day guard.

**Why a systemd `--user` timer and not cron.** `crontab` is refused on this cluster — *"You
(mferguson) are not allowed to access to (crontab) because of pam configuration"* — so cron was
never available to us. The user timer is what is left, and it needs two deliberate settings to work
on a machine like this:

- **`Persistent=true`, which is the load-bearing one.** The account has `Linger=no`, so the systemd
  user manager exists only while a session does, and a compute node's allocation takes it away
  besides. A timer alone would therefore not be running at midnight and would simply never fire.
  `Persistent=true` records the last run in `~/.local/share/systemd/timers/`, and **that path is on
  the shared home** — so a *different* node, on a *later* day, reads the same record, sees the run is
  overdue, and fires it at login. The node is disposable; the record is not.
- **A small `RandomizedDelaySec` (2m).** The jitter's usual job — spreading load across many
  machines — buys one user with one repository nothing, and a delay longer than a short editor
  session would let the day's pull be missed entirely.

Net effect: at most one pull per day, taken on the first login of the day on whatever node you land
on, or at 00:00 if you happen to already be logged in. Verified 2026-08-30 by backdating the
persistent record three days and cold-starting the timer: it fired at once, then re-armed for the
following day.

### 2.2 Keeping the assistant fencing honest

The permission audit runs **once a day, automatically**, on the same machinery as §2.1 and for the
same reason: crontab is refused by pam on this cluster, so a systemd `--user` timer with
`Persistent=true` is what is left. See §2.1 for why that setting is load-bearing — the argument is
identical and is not repeated here.

**It lives in `Atlas/ai-config`, not here**, along with everything else that configures an AI
assistant on this account. `ai-config/scripts/install.sh` installs the wrapper and the timer;
`ai-config/PERMISSIONS.md` §6 says what the audit checks and what it refuses to do on a timer. The
short version: it reports, it repairs file modes, and it never deletes.

| Piece | Path |
| --- | --- |
| Wrapper (day guard, logging) | `~/.local/bin/ai-config-audit` |
| The audit itself | `ai-config/scripts/audit.sh` |
| Log (one line per run) | `~/.local/state/ai-config-audit.log` |
| Timer + service units | `~/.config/systemd/user/ai-config-audit.{timer,service}` |

**One deliberate difference from `colibri-pull`: this one is fatal on a real problem.** A failed
pull is benign and is only logged. A missing PHI guard is not, so the wrapper exits non-zero and
the unit lands in `systemctl --user --failed`, which is the only passive way anybody finds out. A
log nobody reads is not a notification.

---

## 3. Environment (`~/.bashrc`)

A delimited `# >>> ollama >>>` block in `~/.bashrc` sets these. A backup of the pre-edit file is at
`~/.bashrc.bak.20260817160921`.

| Variable | Value | Why |
| --- | --- | --- |
| `PATH` | **prepend** `$HOME/bin` | reach the ollama binary |
| `PATH` | **append** `$HOME/Atlas/projects/libr-local-llm/bin` | reach the driver commands — `ollama-*` (§4a) and `coli-*` (§4c). See below — this one has three constraints |
| `OLLAMA_MODELS` | `/media/studies/.../models/ollama` | weights on studies, not the 100 GB home share |
| `OLLAMA_HOST` | `127.0.0.1:11500` | non-default port avoids collisions on shared nodes; **loopback keeps a PHI-processing endpoint off the cluster network** |
| `OLLAMA_CONTEXT_LENGTH` | `65536` in `~/.bashrc`, **overridden to `131072` in the accel sbatch** | ollama defaults to a few thousand tokens; an agent silently truncates its own history there. 65536 is the number that has to be safe on *one* 46 GB card, where `medgemma:27b-it-q8_0` is 29.6 GB before any KV cache. The accel profile has four cards and 114 GB of them idle, so it serves `gpt-oss:120b` at the model's full 131072 — see §7.24 for why that is a *quality* setting and not just a capacity one |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | roughly halves long-context VRAM |
| `OLLAMA_FLASH_ATTENTION` | `1` | same |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | qwen3-coder + medgemma = 48.2 GB, more than one A40 holds; evict cleanly |
| `OLLAMA_KEEP_ALIVE` | `20m` | release VRAM when idle so others can use the card |

**`OLLAMA_MODELS` is read from the *server's* environment, not the client's.** `ollama pull` is only
a client; the server writes the files. Start the server from a shell that has not sourced `.bashrc`
and 117 GB lands in `~/.ollama`.

### The `bin/` PATH entry (three constraints, all deliberate)

The driver commands live in the repo, not in `~/bin`, so that they stay tracked in git and are
reviewable alongside the sbatch files they drive. The cost is that `PATH` has to point at them, and
the line that does it is fussier than it looks:

1. **Reference it through `$HOME`, not the storage path.** `$HOME/Atlas/projects/libr-local-llm` and
   `/mnt/dell_storage/homefolders/.../libr-local-llm` are the *same directory* — same inode, two
   mounts. Hardcoding the `/mnt` form works but bakes in a mount layout for no benefit.
2. **Append, never prepend.** `$HOME/bin` is prepended because the ollama binary must win. The repo's
   `bin/` is appended so that repo contents can never shadow a system command — a file added here
   later should not silently outrank one in `/usr/bin`.
3. **Guard it with an `if` block, not `[ -d … ] && …`.** The `&&` form returns non-zero when the
   directory is absent, and this is the last executable line in the block — so sourcing `.bashrc`
   would exit non-zero and abort a batch job running under `set -e`. That is trap §7.6 in a new
   costume. The `if` form returns zero either way.

Verified: the commands resolve in a fresh login shell and on a compute node, and sourcing `.bashrc`
under `set -e` returns zero both with the directory present and with it missing.

### The `opencode` guard (why it is a function, not a script in `bin/`)

The same block sources [`config/opencode-guard.sh`](config/opencode-guard.sh), which defines a shell
function named `opencode`. Typing `opencode` directly is the obvious mistake — it is the tool's real
name, it is on `PATH`, and it starts without complaint — and the failure it produces is useless: the
configured endpoint is `127.0.0.1:11500`, loopback-only on whichever node holds the allocation, so
anywhere else the TUI reports that the API could not be reached and names no node, no job, and
neither of the two commands that would have worked.

The guard intercepts exactly three cases and passes everything else through untouched:

- **`opencode up …` / `down` / `code`** — the driver commands are named `ollama-*`. It prints the
  corrected command. This is trap §7.22, which is worse than a typo because it does not error.
- **Anything needing a live model** (no arguments, a bare directory, `run`, `serve`, `web`, `attach`)
  when nothing answers on `OLLAMA_HOST` — it asks `squeue` whether a server is up elsewhere and
  either names that node and says to use `ollama-code`, or says no server is running and gives the
  `ollama-up` lines.
- Everything else — `models`, `agent`, `providers`, `stats`, `--help` and the rest of §6's
  verification commands — reaches the real binary directly, including from the login node.

Two design constraints, both forced:

1. **A function, not `bin/opencode`.** The repo's `bin/` is *appended* to `PATH` on purpose
   (constraint 2 above), so a wrapper script there would lose to the real binary in `~/.nvm` and
   never run. Prepending to make it win would break that constraint for every other file in `bin/`.
   A function is consulted before `PATH` regardless of order, and `command opencode` still reaches
   the real binary — the guard is a signpost, not a fence.
2. **It probes with bash's own `/dev/tcp`, not `nc` or `curl` or `timeout`.** The check has to work
   from `ollama-code`'s `bash -lc` on the server node, where it must pass straight through. No
   timeout is needed because the endpoint is loopback by definition: the connect lands or is refused
   at once.

Verified: the corrected command for `opencode up accel`; the no-server message with nothing running;
the named-node message against a stubbed `squeue` reporting a job on another node; pass-through for
`opencode models` (still exactly three `ollama/` entries) and for the TUI and `run` when the port is
answering; and `bash -lc 'set -e'` returning zero with the guard file present and absent.

---

## 4. Serving

Three Slurm jobs. Submit **from the repo root** — the log paths are relative.

| Job | Partition | GPUs | CPUs | Use |
| --- | --- | --- | --- | --- |
| `slurm_jobs/ollama_serve.sbatch` | `c3_short` | 1 | 4 | daily driver (qwen3-coder, medgemma) |
| `slurm_jobs/ollama_serve_accel.sbatch` | `c3_accel` | 4 | 8 | `gpt-oss:120b` only |
| `slurm_jobs/colibri_serve.sbatch` | `c3_short` | 1 | 88 | GLM-5.2 int4 for work that cannot leave the building (§4c) |

The rest of this section is about the two ollama jobs. The colibrì one is a different animal —
88 CPUs and most of a terabyte to answer one user — and has §4c to itself.

**On the partition choice.** `c3` and `c3_short` are two queues over the *same six nodes*
(compute300–305, one A40 each). They differ only in time limit — 7 days versus 9 hours — and in how
contended they are: `c3` was carrying 201 running jobs against `c3_short`'s 13 when this was
measured. A server that lives under 9 hours schedules sooner on `c3_short`, so that is the default.

> **Do not act on the "switch to `c3`" sentence below without reading
> [`FLEET-BUILD.md`](FLEET-BUILD.md) §2.1 first.** (Added 2026-09-09.) `c3_short` sits at
> `PriorityTier=20` and `c3` at `10`, with `PreemptType=preempt/partition_prio` and `c3`'s
> `PreemptMode=SUSPEND`. On that reading a `c3_short` job can `SIGSTOP` a server running in `c3` on
> the same node — which does not free its VRAM, so it helps nobody, and leaves the client waiting on
> a frozen generation with no error. **Observed on 2026-09-09** (`P0-STATUS.md`, test 10): the
> suspension landed four seconds after the competing `c3_short` job was submitted, and Slurm resumed
> the victim about three seconds after that job finished. `Reason=None` and `PreemptTime=None`
> throughout — nothing in the job record says it was preempted. **Use `c3_short`, not `c3`.**
Switch the file to `c3` if you want one to outlive that; `ollama-up` rejects a `single` walltime over
9 h rather than letting Slurm return a partition-limit error that does not say what to change.

**On the CPU ask.** Neither job reserves more CPU than it uses. Measured on a live server
holding a 70 GB model at 100% GPU: **0.1% CPU, 73 MB RSS, node load 0.00.** With weights on the GPU
the host does almost nothing, and the one expensive phase — the cold model load — is disk-I/O bound,
not CPU bound. This is not a micro-optimization: an 8-CPU ask left the single-GPU job **queued behind
two nodes whose A40 was idle but which had only 4 free CPUs.** Memory stays generous on purpose; it
is page cache for the mmap'd weights, which is what makes a reload fast.

Both source `~/.bashrc` (batch jobs do not do this automatically), guard on `OLLAMA_MODELS`, and run
`ollama serve` **in the foreground** — backgrounding it would let the script exit and Slurm would
tear down the allocation within seconds.

The accel job additionally exports `OLLAMA_SCHED_SPREAD=1` to force sharding across all four cards.

### After submitting

1. `squeue -u $USER` → note the node (e.g. `compute300`) and confirm `gres/gpu:N`.
2. Read `slurm_jobs/logs/ollama_serve_err.txt` — ollama logs to **stderr**. Look for
   `Listening on 127.0.0.1:11500`.
3. Step onto the node (see below) and use the client from there.

In practice you should not do any of this by hand — `ollama-up` (§4a) does all three and refuses to
report success unless they all pass.

### Reaching the server

The endpoint is **loopback on the job's node**. From any other node the connection is refused —
this is deliberate, not a bug. Do **not** rebind to `0.0.0.0`: that exposes a PHI-processing endpoint
to every user on the cluster.

Two ways onto the node. **Prefer the first.**

- **`srun --jobid=<id> --overlap`** steps into the existing allocation and runs a command there. No
  SSH key, no password, and it inherits the job's `CUDA_VISIBLE_DEVICES`. Add `--pty` for anything
  interactive (a TUI needs it). This is what `ollama-code` uses.
- **`ssh <node>`** also works *if* your key agent is set up. It is not always: a non-interactive SSH
  from the login node was refused with `Permission denied (publickey,password)` while `srun
  --overlap` to the same node succeeded in the same shell. Treat SSH as the fallback.

### Verifying a 4-GPU shard

**Verified 2026-08-20** on compute306, job 2041641, `gpt-oss:120b`. Observed, not specified:

| Check | Observed |
| --- | --- |
| `nvidia-smi` per-card VRAM | 18877 / 17139 / 17205 / 16573 MiB — 16–18 GB on each of four cards |
| `ollama ps` | `100% GPU`, 70 GB, context 65536 |
| GPU detection | 4× A40, `compute=8.6`, `cuda_v13` backend, driver 13.3 |

`OLLAMA_SCHED_SPREAD=1` engages as intended. One card near 46 GB with three idle would mean it had
not; any CPU offload in `ollama ps` would mean it fell back and would be unusably slow.

Cold-start cost, same run: **total 5m00s, of which load was 4m46s** — 65.4 GB paging off the NFS
studies share at roughly 230 MB/s. Warm generation ran at 34.1 tok/s. That load figure is the whole
argument for warming a model *before* a demo rather than during one (§4a).

`CUDA_VISIBLE_DEVICES` indices are **relative to the allocation**, not physical device numbers —
Slurm remaps them. Never hardcode a device index.

---

## 4a. Driver commands (`bin/`)

Three tracked scripts wrap everything above. They run **from anywhere, including the login node** —
they find the job through `squeue` and step onto its node with `srun --overlap`.

**They are not on `PATH` by default.** They live in the repo rather than `~/bin` so they stay under
version control, which means `~/.bashrc` has to be told where they are — §3 covers the line and the
three constraints on it. Until that is done, they only work when called by path from the repo root.
Once it is, none of §4's manual steps need doing by hand again.

Deliberately **no state file**: the client asks Slurm which job is running every time. A state file
goes stale the moment a job ends or a second one is submitted; `squeue` never does.

| Command | Does |
| --- | --- |
| `ollama-up [single\|accel] [hours]` | Submits the matching sbatch, waits for `RUNNING`, asserts `AllocTRES` contains `gres/gpu=`, waits for `Listening on` in the stderr log. Exits non-zero unless the server is actually serving. Optional walltime in hours overrides the file's 8 h. Reports the pending reason while it waits, and leaves the job queued if it gives up. |
| `ollama-code [-m model] [-d dir] [-k dur] [-p single\|accel] [-s id \| -c] [-l] [message…]` | Finds the running server and launches opencode on its node. No message → the TUI. A message → a one-shot `opencode run`. `-s` resumes one session by id, `-c` resumes the most recent one in `-d`, `-l` lists what that directory has and exits without needing a server. |
| `ollama-down [all\|single\|accel]` | Cancels the server jobs. Run it when done — compute306 is the only 4-GPU node. |

Behaviors worth knowing:

- **`ollama-up` refuses to double-submit.** `OLLAMA_MAX_LOADED_MODELS` is 1 and both profiles bind
  the same loopback port, so a second server is never useful. It also truncates the stderr log first,
  because the readiness check greps for `Listening on` and a stale hit from the previous job would
  report success before the new server had started.
- **`ollama-code` adopts the resident model** when `-m` is absent, reading it from `ollama ps`.
  Naming a different model evicts the warm one and pays the multi-minute reload — not something to
  discover mid-demo. With nothing resident it falls back to the profile's default.
- **`ollama-code -k <duration>` warms and exits.** Use it before a demo. It sends one throwaway
  prompt with `--keepalive` so the load cost is paid up front, then stops rather than dropping into
  the TUI, which makes it safe to call from a script.
- `ollama-up` prefers `--chdir` over a `cd`, since §4's log paths are relative to the repo root, and
  captures the job id via `sbatch --parsable` rather than parsing "Submitted batch job N".
- **Both scripts scrub `SLURM_*` before shelling out**, which is what lets them run from inside
  another allocation. See trap §7.19 — this is not defensive garnish, the unscrubbed version fails.
- **Past sessions are reachable from any node, and `-s` / `-c` / `-l` are how you reach them.**
  (Added 2026-09-09.) opencode's session store is under `~/.local/share/opencode` on NFS home,
  mounted on every node, so a session started on compute306 is fully readable from wherever you
  next log in. Only the *endpoint* was ever node-bound. What that means in practice: nothing is
  lost when an allocation ends, and `ollama-code -s <id>` resumes on the node that can actually
  serve it. `-l` answers without a server at all, since listing touches only the store.
  opencode scopes sessions **per project directory**, so `-l` and the TUI's own picker show only
  what belongs to `-d` (default: the current directory) — a session started in one repo is
  invisible from another, which looks like data loss and is not.
- **A resumed session can override `-m` and evict the resident model.** (Added 2026-09-09.)
  Verified by launching the TUI on the node with `--print-logs` against a session whose history
  was qwen3-coder: the footer opened on the model `-m` named, then switched to the session's own
  model once the history replayed. On the accel profile that is a 70 GB eviction on the first
  message. `ollama-code` prints a warning when resuming there; the TUI footer is the thing to
  read before sending.
- **Typing `opencode` instead of `ollama-code` is caught, not punished.** A shell function sourced
  from `~/.bashrc` (§3) answers a bare `opencode` with which node the server is on, or with the
  `ollama-up` lines if none is. It exists because the wrong command produced an unreachable-API
  error that pointed at nothing — see trap §7.22.

---

## 4b. Working from an editor on a compute node

The common case: a VSCode remote session whose workspace is served from an interactive job on some
compute node, while the model server holds a *different* node. The endpoint is loopback on the
server's node, so the editor's node cannot reach it directly — and the two nodes are not the same
one.

The driver commands already handle this. From the VSCode terminal, `ollama-code` finds the server
through `squeue` and hops to its node with `srun --overlap`, exactly as it would from the login node.
Nothing about the editor's own allocation needs changing, and no port forwarding is involved.

Two things to know:

- **Your files are visible from both nodes.** Home and `/media/studies` are network filesystems
  mounted everywhere, so the opencode session started on the server's node sees the same workspace.
  Pass the workspace path with `-d` if you launch from somewhere else; the default is the current
  directory, which is usually what you want.
- **This is the case that trips trap §7.19.** Running Slurm commands from inside an allocation is
  what breaks without the `SLURM_*` scrub. Verified working from compute302 against a server on
  compute306.

---

## 4c. colibrì (GLM-5.2): serving it, and putting it to work

The second serving stack, and it is not a second Ollama. One job, five driver commands, and a
model that holds most of a 1 TB node to answer one user at a time. Use it for the work that
cannot leave the building; use §4a for everything else.

| Piece | Path |
| --- | --- |
| Engine source, pinned | `vendor/colibri-build/c` in the Atlas checkout (a submodule) |
| Built engine | `vendor/colibri-build/c/colibri` — **not in git**, rebuild after a clone |
| Launcher | `vendor/colibri-build/c/coli` — needs Python ≥ 3.10 |
| Checkpoint | `…/mferguson/models/colibri/glm52_i4`, 429 GB of data in 498 GB of share |
| Serve job | `slurm_jobs/colibri_serve.sbatch` |
| Shared derivation | `scripts/colibri-env.sh` |

### The commands

| Command | Does |
| --- | --- |
| `coli-build [clean]` | Compiles the engine with `ARCH=native CUDA=1 CUDA_ARCH=sm_86`. |
| `coli-up [-t hours] [-c cpus] [-M gb] [--once]` | Starts the **chain**, waits for the engine to load, then **warms it with one real generation** and only then reports success. `--once` submits a single generation that ends at its walltime. |
| `coli-code [-d dir] [-a claude\|opencode] [--yes] [message…]` | Opens a coding agent in any directory, pointed at the served model. No message → the TUI; a message → one shot. |
| `coli-ask [-f file] [-n tokens] [--think] "question"` | One question, no agent, no tools, no preamble. |
| `coli-down` | Ends the chain: writes the stop flag, **then** cancels every generation. It holds most of a node — run it. |
| `coli-adopt [job] [--force]` | Puts a chain watcher beside a running generation that has none — one submitted with `--once`, or one whose watcher died with its node. One CPU and 2 GB until the handover. Not an everyday command. |
| `coli` | Not the engine launcher — a signpost that prints the five above and says which generation is serving, how many minutes it has left, and whether one is queued behind it. `coli --raw` reaches the real launcher. |

They find the job through `squeue` and step onto its node with `srun --overlap`, exactly as the
`ollama-*` trio does, and for the same reason: the endpoint is loopback on the serving node and
**must stay that way**. Every path, default and module list is derived once in
`scripts/colibri-env.sh` and sourced by all five plus the sbatch, so there is one answer to "where
is colibrì" rather than five that can drift.

### Why `coli-up` warms before it returns

A bound socket is not a loaded model, and a loaded model is not a warm one. The gateway constructs
its HTTP server **before** the engine, deliberately, so a bad argument fails in milliseconds
instead of after 429 GB — which means a TCP probe answers instantly and tells you nothing. Then the
engine mmaps the checkpoint and faults expert slabs in *during generation*, so the first caller
pays the rest of the cold start one token at a time.

So `coli-up` watches the gateway's own `API listening on` line for the load, and the job sends its
own first request for the warm. The request is lodged in the accept queue while the model is still
loading, costing nothing, and `COLIBRI-SERVE READY` carries the prompt-token count, the completion
count and the seconds — not a rate, because that clock is mostly the load and a tok/s computed from
it would look like a benchmark and not be one. `--no-warm` skips the wait and says what it skipped.

### The chain: the server is always up, and it moves node rather than going away

`c3_short` caps a job at nine hours and `c3` is refused on measurement — a `c3_short` job at
`PriorityTier=20` `SIGSTOP`s a `c3` job on the same node, four seconds after submission, with no
error anywhere the client can see (P0-STATUS test 10). So the server has to hop, and a hop costs
**68 minutes** of pinning 406.7 GB off the filer. The chain is what makes that invisible.

Two hours before its walltime ends (`COLI_CHAIN_LEAD_MIN`), the running generation submits the next
one with `--exclude` of its own node. That one pins its 406.7 GB while this one goes on answering,
and prints `COLIBRI-SERVE LOADED`. **Only then** does the incumbent cancel itself and give its node
back. Nothing is down at any point, and the generation that was replaced leaves early rather than
running out its walltime — so the chain hops roughly every seven hours, not every nine.

Three things follow from that and none of them is obvious:

- **The successor cannot land on the incumbent's node**, because two 800 GB jobs do not fit on a
  1 TB box. So every hop pays a cold pin. A same-node successor would re-read its checkpoint out of
  page cache at **9064 MB/s against 422 MB/s cold** — page cache survives the teardown of the job
  that filled it, measured on compute300 on 2026-09-18 — but that route needs a gap in service, and
  availability was chosen over the cheap hop deliberately.
- **The one case that gets the cheap hop back** is the partition being full. If the successor is
  still `PENDING` twenty minutes before the incumbent dies, it is cancelled and re-queued *without*
  the exclusion, so it takes the incumbent's node the moment that job ends and pins against a page
  cache that still holds the checkpoint. That is a gap of minutes rather than an hour, and with
  `c3_short` as busy as it usually is it is the ordinary path rather than the exception.
- **The warm-up waits for the incumbent to go, and one file is why.** KV persistence is per
  checkpoint — `<model>/.coli_kv`, opened `r+b` and written at offsets each process computes from
  its own record count — so two live servers interleave their writes into one file and neither
  reading survives it. The engine *reads* that file at startup, which is harmless, so the load
  overlaps freely; only the first write has to wait, and a warm-up is a real write. What it costs is
  the turns the incumbent completed while the successor was loading: they are not in the prefix the
  successor read, so the first turn after a handover re-prefills them.

Not `--dependency=afterany`, which is what the board's own self-cloning chain uses. A dependency
means the successor starts when this job *stops*, and a load that begins at the handover is an hour
with no server. The board's generations cost nothing to start and colibrì's cost 68 minutes; that
one number is the whole difference between the two designs.

**A generation's walltime is a ceiling on the client, not on the chain.** `coli-code` steps into the
serve job's allocation with `srun --overlap`, so the client is a *step* of that generation and dies
with it. The chain replaces the server, not the session. `coli-code -c` continues where it left off
and the on-disk KV makes that continuation cheap; `coli-code` prints the minutes left when there is
less than an hour of them.

**Every generation writes its own pair of logs**, `colibri_serve_{out,err}-<jobid>.txt`, because
during a handover two of them are running and one fixed pair would have the successor judged by the
incumbent's `COLIBRI-SERVE READY`. `coli`, `coli-code`, `coli-ask` and the board all resolve the
names from the job id.

**A generation with no watcher can be given one.** `coli-adopt` submits the same loop as a one-CPU
job of its own, against a generation named on the command line — the case that matters is a server
that was already running when the chain was built, or one submitted with `--once` that you have
changed your mind about. It refuses a generation whose log already carries `COLIBRI-SERVE LOADED`,
because that one watches itself and two watchers queue two successors.

**Ending it takes the flag and the cancel, in that order.** `scancel` on a generation is how you
*replace* a server — the chain reads it as a node failure and does exactly what it was built to do.
`coli-down` writes `slurm_jobs/state/chain-stopped` first, then sweeps the queue twice, and a
generation that starts while that flag is there stands down without serving. `coli-up` clears it.

### What the serve job does differently from `t34567_colibri.sbatch`

Every P0 finding, applied rather than measured, plus the two things P0 did not have to get right
because it never served:

- **`--gpu auto --auto-tier`, and `CUDA_DENSE=0` behind it.** Without the first the engine runs
  CPU-only beside an idle card and says nothing (trap 30). The second is needed because the first
  turns `CUDA_DENSE` on by itself.
- **`--ctx 131072`.** The family default is 4096, which is smaller than a coding agent's system
  prompt (trap 31).
- **One GPU.** Four are worth 0.9 % on this model; the other three cards are each worth far more as
  tier-1 throughput to somebody else. `c3_short` on compute300–305, never `c3`, never compute306.
- **88 CPUs, not 92.** `MaxCPUsPerNode` is a *partition*-wide cap, so one co-tenant holding two CPUs
  makes a 92-CPU request pend on `(Resources)` forever beside an idle GPU.
- **`OMP_NUM_THREADS` from `SLURM_CPUS_PER_TASK`, allowed to exceed the physical core count.** The
  engine self-tunes down to 48 on this box and is wrong to.
- **`numactl --interleave=all`.** `coli tune`'s candidate set is thread counts and CUDA stream
  shapes; it cannot propose memory placement, so it cannot find this and does not know it is
  missing. `coli doctor` recommends `COLI_NUMA=1` instead, and that is measurably behind.
- **`XEXP` and `CUDA_DENSE` unset**, each a measured loss. **`DRAFT` unset means speculation is
  OFF here, and the log's `[MTP] active` line does not say otherwise.** `active` is chosen by
  whether the CHECKPOINT carries an MTP head — ours is the `-with-int8-mtp` container, so it is
  printed always — and `draft=` is the half that says whether anything is drafted. Under CUDA the
  engine resolves the auto depth to 0 unless `COLI_CUDA_MTP=1` is in the environment, and
  `--auto-tier` exports `DRAFT=0` again on a compute-bound plan. So this job serves with
  speculation off, deliberately at both layers, and `MTP=1` is not the lever that changes it:
  `MTP` is read in one place and only `MTP=0` does anything, which strips the head. **Off is the
  measured answer and not merely the default**: at depth 1 speculation costs 9.7 % here — 3.23
  tok/s against 3.58, with acceptance at 62–77 % that does not convert — so turning it on is a
  loss on a box whose bottleneck is the CPU expert tail. P0-STATUS finding 21 has the A/B.
- **`PYTHONNOUSERSITE=1`**, because `os.access` lies on this filer and pip installs 8.7 GB into
  `~/.local` that then shadows the environment at import time.
- **`TMPDIR` on the studies share.** `/tmp` is a node-local RAM tmpfs, so `coli`'s serve pidfile
  written on one node is simply absent from the next.

Lower `-M` to schedule sooner. 950 GB holds every expert warm in page cache; less memory is not a
failure, it is a slower tail, because the engine streams what will not fit.

### Where the transcript goes, and why it is not in this repo

**A driver that can read `phi` writes a transcript that quotes `phi`.** The model's reasoning is
session content the moment it repeats a line of the session back, and that rules out both places a
coding agent would put it by default.

Not `slurm_jobs/logs/**`: that directory is *exempt* from the PHI fence, on the stated
understanding that the jobs print counts and durations and never text. The gateway honours that
with `COLI_DEBUG` unset — it writes a banner, a plan and one access line per request, no bodies —
but `COLI_DEBUG=1` tees every decoded token to stderr and `COLI_DEBUG=2` adds the whole rendered
prompt, prior turns and tool results included. **The serve job refuses to start when it is set**,
by name, at the top. That is enforcement rather than hope, and it is the right shape for a promise
everything downstream is relying on.

Not `~/.claude/projects` or `~/.local/share/opencode` either, which is where both front ends keep
their history and where a hosted assistant reads all day.

So `coli-code` points both stores at `$COLI_SESSION_ROOT`, which ends in a directory named `phi`.
That name is fenced whole and at any depth by `ai-config/policy/phi.py` — the rule that survived
the session data moving twice in one day without changing by a character. Nothing new had to be
invented and there is no second rule to keep in step with the first.

### The preamble is the bill, and it decides which command you want

The engine decodes at single-digit tokens per second and **prefills at a few**, so the cost of a
question is dominated by how much text precedes it. A coding agent sends its system prompt and its
whole tool catalog before your first word, and that is the larger half of a working day's wait.
`P0-STATUS.md` finding 20 has the measured rates and the measured preamble; the shape of the answer
is that **`coli-ask` is the interactive command and `coli-code` is an overnight one.**

Three consequences are built into the tools rather than left as advice. `coli-code` gives each front
end a **fresh, empty config directory** — no MCP servers, no plugins, no global `CLAUDE.md`, all of
which travel in the same request and are billed at the same rate — and `--instructions` is what opts
the repository's instructions back in, with a warning about what they cost. It tells the client the
real context window, because the client does not recognise this model and otherwise assumes one
nearly twice as large. And `coli-ask` exists at all because a bare question skips the preamble
entirely; it streams, so that a long prefill looks like work rather than a hang.

Leave the server up between tasks. The engine keeps a KV prefix per slot and matches each request's
tokenised prompt against it, so a preamble already paid for is not paid again — that is what makes
an agent loop finish at all, and it is why `coli-down` between two jobs is expensive.

A fresh config directory also means **the PHI hook in `~/.claude` is not loaded**. That is the
point: this model runs on our own hardware and reading `phi` is the job it exists for. It is also
exactly why the transcript goes behind the fence.

---

## 5. Models

| Tag | Size | Role |
| --- | --- | --- |
| `qwen3-coder:30b` | 18.6 GB | Default coding model. MoE, 30B total / ~3B active, tuned for agentic tool-calling. Fits one A40 with room for a 64k context |
| `medgemma:27b-it-q8_0` | 29.6 GB | Clinical prototyping. q8, not q4 — quantization damage shows up first on careful text extraction |
| `gpt-oss:120b` | 65.4 GB | Strongest coder available here. MoE. **Requires `c3_accel`**. Reasoning model — `ollama run` exposes `--think` (true/false or high/medium/low) and `--hidethinking` |

The store on disk is ~131 GB, larger than the sum of the tags above: `blobs/` also holds layers that
no current manifest points at.

Pull with `ollama pull <tag>` from a shell on the node running the server. A server must already be
running — no GPU needed for a pull, it is network and disk only. Pulls are chunked and resumable;
re-running the same tag continues from an orphan blob rather than restarting.

**Cold loads are slow and it is the studies share, not the GPUs.** `gpt-oss:120b` took 4m46s to page
65.4 GB off NFS (~230 MB/s) before its first token. vLLM 0.29 prefetches its shards into page cache
in parallel and pulled 16.85 GiB in 23 s on the same share, so the figure is a floor for a
cold-cache serial read, not a constant. Warm it before you need it — `ollama-code -k`
(§4a) exists for exactly that.

`ollama list` shows only *completed* models — the manifest is written last. Mid-flight, the store
directory will be larger than the sum of listed models.

---

## 6. opencode (the coding assistant)

Config lives at `~/.config/opencode/opencode.json`; a tracked copy is `config/opencode.json`.
Structure:

- `enabled_providers: ["ollama"]` — **default-deny provider allowlist.** opencode ships ~8 hosted
  "free" models under an `opencode/` provider (OpenCode Zen). Those are **remote**; selecting one
  sends the prompt off-cluster. This key hides every provider not listed, so future opencode releases
  cannot quietly add another remote option to the picker.
- `provider.ollama` — `npm: "@ai-sdk/openai-compatible"`, `options.baseURL:
  "http://127.0.0.1:11500/v1"` (note the `/v1` suffix and port **11500**, not ollama's default 11434).
- `provider.ollama.models` — keys must exactly match the ids returned by `GET /v1/models`, which for
  ollama are the tag names.
- `model` — the default, `ollama/qwen3-coder:30b`.
- `permission` — **top-level default-deny for `webfetch` and `websearch`.** Same principle as
  `enabled_providers`: the default is "no", and exceptions are named explicitly. This matters because
  opencode's built-in default for almost every gated tool is `allow` — an *absent* `permission`
  section is not a closed door, it is an open one.
- `agent.coder` — a `primary` agent that overrides both web tools back up to `ask` (not `allow`).
  `default_agent` points at it. Every other agent — the built-in `build`, `plan`, `general`,
  `explore`, `title`, `summary`, `compaction` — inherits the global deny.

Resolution order is built-in agent defaults, then the top-level `permission` block, then the
per-agent block; last one wins. Verified against the built-in `explore` agent, which ships with
`webfetch: allow` and is correctly overridden to `deny` by the global block.

Verify with `opencode models` on the server's node: it should list exactly three `ollama/` entries
and nothing else. Verify the permission wiring with `opencode agent list`, which prints each agent's
fully resolved rule stack — `coder` should end in `ask`, everything else in `deny`.

**opencode cannot be used to reach Claude.** Its docs state Anthropic prohibits routing Claude
Pro/Max subscriptions through it, and the plugins that did so were removed in 1.3.0. The only
supported Anthropic path is a per-token API key. Claude Code (LIBR seat) and opencode+ollama are
separate tools with a clean split: Claude Code for non-PHI work, opencode for anything local.

### Web access: decided scope (2026-08-20, not yet applied)

The intent is to let the coding assistant reach the web. Recorded here as a decision so the
reasoning survives the config change.

**Permissions are per *agent*, not per model.** There is no setting that grants web access to
`qwen3-coder:30b`. Any model can be driven by any agent, so the boundary that matters is the
*workload*, not the weights: a `coder` agent running medgemma is fine, a transcript-coding agent
running qwen3 is not. "Enable web for all our models" does not map onto anything opencode exposes,
and thinking in those terms is how the wrong agent ends up with the wrong tool.

Two distinct risks, and the second is the one usually missed:

- **Egress.** Anything in the context window can leave in a search query or a fetch URL. §1 confirms
  outbound HTTPS works from compute nodes, so opencode's config is the *only* thing keeping PHI on
  the cluster.
- **Ingress — prompt injection.** Fetched pages enter the context as text the model cannot
  distinguish from your instructions. The `coder` agent has file and shell access, so every page it
  reads becomes a potential instruction source. This risk is present even with no PHI anywhere near
  the session.

What will change, and what deliberately will not:

| Setting | Decision |
| --- | --- |
| Top-level `permission` deny | **Unchanged.** It is what closes the built-in `explore` subagent, which ships with `webfetch: allow` (trap §7.12). A per-agent-only config would leave that open. |
| `coder` → `webfetch` | Raise `ask` → `allow`. A URL you typed is the lower-risk direction. |
| `coder` → `websearch` | **Keep at `ask`.** This is the direction where your prompt text leaves the building. |
| Any transcript-reading agent | Never. No web tools, ever. |

**This makes layer 3 more urgent, not less** (§8). Loosening layers 1 and 2 is precisely why the
layer that cannot be misconfigured needs to exist.

---

## 7. Traps already paid for

Do not re-learn these.

1. **The dead `.tgz` URL.** `ollama.com/download/ollama-linux-amd64.tgz` redirects to a GitHub asset
   that no longer exists (404). All Linux assets are `.tar.zst` now.
2. **`curl` without `-L`** writes a redirect stub and exits 0 — looks like "nothing happened".
3. **`-C` on curl takes an argument** (`-C -` to auto-resume). Bare `-C` swallows the next token.
4. **`[` is a command, not punctuation.** `[!` is parsed as a command named `[!` and fails with
   "command not found" — and `bash -n` *passes*, because it is syntactically valid. The failing
   command returns non-zero, the `if` reads that as false, and the guard silently never fires.
   Write `[ ! -d ... ]` with spaces.
5. **`ollama pull` needs a running server.** `/api/generate` does *not* download a missing model; it
   errors. A script that pipes that call to `/dev/null` and prints "Model loaded" is lying.
6. **`.bashrc` is not sourced by batch jobs.** Source it explicitly, and do so *before* `set -e` —
   `.bashrc` contains `[ -s file ] && source file` patterns that return non-zero when a file is
   absent and would abort the job during startup.
7. **`npm install` without `-g`** installs into the current directory and pollutes the repo with
   `node_modules/`, `package.json`, and `package-lock.json`.
8. **The npm postinstall warning for `opencode-ai` is harmless.** The real binary arrives as an
   optional dependency.
9. **`~/.ollama` appearing is not a failure.** It holds an ed25519 client keypair, ~200 KB. Check its
   *size*, not its existence.
10. **A Slurm job without `--gres=gpu:N` still sees the node's GPUs.** Seeing a card is not reserving
    one.
11. **opencode's permission defaults are `allow`, not `deny`.** Every gated tool except `doom_loop`
    and `external_directory` defaults to `allow`. "We never configured web tools" therefore means
    the web tools were *on*, not off. Only `.env` files are denied out of the box.
12. **The built-in `explore` subagent ships with `webfetch`/`websearch` set to `allow`.** A global
    deny does override it, but agent-level defaults exist and are invisible until you read the
    resolved stack from `opencode agent list`. Do not assume the built-ins are inert.
13. **conda envs are not Python venvs.** `setup_envs.sh` in PSYCH-ASR creates *conda* prefix envs; a
    conda env can hold compiled binaries (which is why it was a candidate for `zstd`), a `python -m
    venv` cannot.
14. **`--keepalive` is per *request*, not per session.** It sets the hold for that one call. Any
    later request that omits it — and **opencode omits it on every call** — resets the model's expiry
    to `OLLAMA_KEEP_ALIVE` (20 m). Warming a model two hours before a demo and then poking it once
    through opencode drops the hold back to 20 minutes, so it evicts before the audience arrives and
    you pay the ~5-minute reload live.
15. **GPU discovery in ollama 0.32.14 is lazy.** The `inference compute ... NVIDIA A40` lines appear
    when the *first model loads*, not at startup. A freshly started server logs `Listening on` and
    then `discovering available GPUs...` and stops. An absent A40 line at that point means nothing
    has loaded yet, **not** that the GPUs were missed.
16. **SSH to a compute node is not guaranteed; `srun --overlap` is.** A non-interactive SSH from the
    login node was refused (`publickey,password`) while `srun --jobid=<id> --overlap` reached the same
    node from the same shell. Build tooling on `srun`, not `ssh`.
17. **Grepping a Slurm log for a readiness string needs the log truncated first.** `Listening on`
    from the *previous* job is still sitting in the file and will report success before the new
    server has started. `ollama-up` empties the stderr log before submitting.
18. **`ollama run` writes a spinner to the captured stream.** Piping it to a file yields tens of
    thousands of ANSI escape sequences around the actual answer. Strip escapes before reading it
    programmatically, or the timings block is unfindable.
19. **Slurm commands run *inside* an allocation inherit `SLURM_*` and misbehave.** This is the one
    that bites when your editor is already on a compute node (§4b). A nested `srun --jobid=<other>
    --overlap` dies with **exit 192** despite naming a different job explicitly, because it picks up
    the outer job's `SLURM_JOB_ID` and step context. Worse and quieter: `sbatch` inherits the outer
    job's `SLURM_*` too, and those **override the `#SBATCH` directives in the file** — a server
    submitted from a compute-node terminal can come up with the wrong partition, memory, or GPU
    count and never say so. Both `ollama-up` and `ollama-code` unset every `SLURM_*` variable before
    shelling out. Verified failing and then passing from compute302 against a server on compute306.
20. **Loopback is not a security boundary on a shared node.** (Added 2026-08-22.) Slurm gives a job
    no network namespace, so *any* user with a shell on the node running the server can connect to
    `127.0.0.1:11500` on it. §4's "the endpoint is loopback, from any other node the connection is
    refused" is true and is a real control against the *cluster network* — it is not a control
    against the *node's other users*, and it must not be read as both. The honest statement:
    loopback is necessary and not sufficient, and **ollama has no authentication
    at all**, so today the only thing between another account on compute30x and our endpoint is that
    they have no reason to look. Two consequences: keep the endpoint on the least-populated node we
    reasonably can, and treat "does this engine support an API key" as a selection criterion for
    anything added next (colibrì does; ollama does not). This is a live gap, not a hypothetical one.

21. **There is no cron here, and a user timer does not survive on its own.** (Added 2026-08-30.)
    `crontab` is blocked by PAM for this account, and `Linger=no` means the systemd user manager
    dies with your last session — on a compute node it dies with the allocation regardless. So
    "schedule it for 3am" is not a thing this cluster can do for a user account: nothing of ours is
    running at 3am. Anything recurring must be written to *catch up when a session next exists*
    (`Persistent=true`, whose record lives on the shared home and therefore survives the node), and
    must be idempotent for the period, because two logins on two nodes in one day will otherwise run
    it twice. §2.1 is the worked example.

22. **`opencode up accel` does not fail — it opens a TUI in a directory called `up`.** (Added
    2026-09-03.) opencode has no `up` subcommand, and its argument parser treats an unrecognized
    first positional as the `[project]` directory for the default TUI command. So the typo submits
    nothing to Slurm, discards `accel` silently, exits 0, and the damage only surfaces on the *next*
    command as `opencode`'s unreachable-API error — which names the endpoint but not the node, the
    job, or the fact that `ollama-up` and `ollama-code` are the commands that work. Two separate
    footguns stacked: a subcommand that is silently reinterpreted as a path, and a client whose
    connection failure carries no diagnosis. `config/opencode-guard.sh` (§3) closes both by
    intercepting the `ollama-*` names and by naming the serving node before handing over.

23. **A passthrough list ending in `-*` is not a passthrough list, it is a hole.** (Added
    2026-09-09.) The guard from §7.22 had a second case listing the subcommands that need no model
    endpoint — `models`, `agent`, `session` and so on — so that §6's verification steps still work
    from the login node. That list ended in `-*`, meant for `--help` and `--version`. But opencode's
    `--session`, `--continue`, `--model`, `--prompt`, `--agent` and `--mini` are options on the
    **default** command, which is the TUI: they need the endpoint as much as a bare `opencode` does.
    So `opencode -s <id>` matched `-*`, was handed to the real binary, and produced exactly the
    contentless *"Cannot connect to API"* that the guard exists to replace — from a shell where the
    guard was correctly installed and loaded. A fence with a wildcard in it protects nothing it did
    not enumerate. Only `-h`/`--help`/`-v`/`--version` are listed now; every other dash argument
    falls through to the endpoint probe.
    Two things fell out of fixing it. The guard now forwards the session flags it saw into the
    corrected `ollama-code` line, because someone typing `-s <id>` has a specific session in mind
    and a generic example is not an answer. And a flag's value is consumed with two single shifts
    rather than `shift 2`, which with one argument left **fails and shifts nothing** — this function
    runs in an interactive shell where no `set -e` stops the loop, so a trailing bare `-s` spins
    forever.

24. **A context window that is merely "large" still has a cliff at the edge, and the model falls off
    it silently.** (Added 2026-09-09.) A 55K-token agentic coding session against a 65536 window
    started returning empty and near-empty turns — 50 seconds of reasoning, then nothing worth
    reading. That is not the model being stupid. `gpt-oss` uses sliding-window attention (128), so
    llama.cpp logs **`KV cache shifting is not supported for this context, disabling KV cache
    shifting`** at startup, and the slot runs with `n_keep = 4`. With shifting off and only four
    tokens pinned, crossing the window has no graceful path: the prompt is truncated from the
    **front**, which is exactly where the system prompt and the tool definitions live. An agent that
    has lost its tools does not announce it. It keeps answering, uselessly, and the symptom reads as
    a capability problem when it is a capacity one.
    Three consequences worth separating. **The window was set too low for the hardware** — 65536 is
    the number that must fit one 46 GB card, but the accel profile has four and 114 GB idle, so it
    was serving a 131072-capable model at half its window for no reason; the accel sbatch now
    overrides it. **A window is not a target.** Raising it to 131072 buys headroom, not quality at
    100K: models degrade well before their nominal limit, so a fresh session per task still beats
    growing one to 55K. And **check the serving numbers before blaming the weights** — the log had
    the answer at line 271, before any argument about which model to run next.
    Not yet verified against a running server: the override takes effect on the next `ollama-up
    accel`, and it was not restarted while a live session depended on the resident model.

25. **`pip` installs into `~/.local` on this filer even when the environment is writable, because
    `os.access` lies.** (Added 2026-09-09.) pip decides where to install with
    `test_writable_dir()`, which on POSIX is one line: `os.access(path, os.W_OK)`. The Isilon
    synthesises POSIX mode bits lossily from the real NFSv4 ACL, so that call returns **False** for
    a directory the same process then writes to without error — the same defect `ai-config/PERMISSIONS.md`
    documents for mode bits generally. pip logs *"Defaulting to user installation because normal
    site-packages is not writeable"* and puts the payload in `~/.local`, which then **shadows the
    environment at import time**. 8.7 GB of vLLM landed on a 100 GB home share this way and a job
    ran a copy of the library nobody meant to install.
    **`--no-user` is not a reliable fix. `PYTHONNOUSERSITE=1` is.** It flips
    `site.ENABLE_USER_SITE` to False, which pip checks *ahead* of the writability probe, and it also
    stops `~/.local` shadowing the environment at run time. Set it in every install script and every
    job that activates an environment on this filer. The related, harmless half of the same defect:
    pip disables its own cache under `/media/studies/…/mferguson` for the same reason, so installs
    there re-download.
26. **vLLM's default sampler compiles a CUDA kernel at warm-up, and there is no `/usr/local/cuda`
    to compile it with.** (Added 2026-09-09.) vLLM 0.29 defaults to the FlashInfer sampler, which
    JIT-builds `top_k_mask_logits` the first time it samples. The build hardcodes `/usr/local/cuda`
    as its fallback and dies with `RuntimeError: Could not find nvcc and default
    cuda_home='/usr/local/cuda' doesn't exist`. It happens **after** the weights load, the KV cache
    is allocated and the CUDA graphs are captured — minutes into startup, under two screens of
    traceback whose top frames are all `contextlib`. Export `CUDA_HOME=$EBROOTCUDA` to fix the
    lookup, and set `VLLM_USE_FLASHINFER_SAMPLER=0` anyway: a kernel build inside the serving path
    is a cold-start hazard, and the JIT cache would land on a shared NFS filer.

27. **`coli serve` binds its port before it loads the model, so a TCP probe reports a server that
    cannot generate a token.** (Added 2026-09-16.) The gateway constructs its `APIServer` first and
    the `Engine` second, on purpose — a bad argument then fails in milliseconds instead of after
    429 GB. The consequence at the other end is that `127.0.0.1:8000` accepts a connection about two
    seconds into a job whose model needs several minutes, so the readiness check that works for
    ollama — probe the port — reports success against a socket with nothing behind it. The line that
    actually means the model is up is the gateway's own `OpenAI-compatible API listening on …`, on
    **stderr**, printed after the engine is constructed; `coli-up` greps for that.
    The connection a probe gets is not wasted, though, and the serve job uses it: a request sent
    into the accept queue while the engine is still loading costs nothing and is served the instant
    it can be, which is how the warm-up generation is already in flight before the model finishes
    loading.

28. **`coli doctor` reports the model directory read-only when it is writable — it is `os.access`
    again.** (Added 2026-09-16.) `storage.persistence` warns *"model directory is read-only; disable
    persistence or change permissions"* against a directory the same account writes to without
    error. Same root cause as trap 25: the filer synthesises POSIX mode bits lossily from the real
    NFSv4 ACL and `os.access` believes them. The warning is a false negative and KV persistence and
    `.coli_usage` both work; do not go changing permissions to satisfy it.

29. **The cold load is not 101 seconds any more, and the reason is that the router learned.**
    (Added 2026-09-16.) The checkpoint's `.coli_usage` has grown from 58,240 expert selections to
    1,698,816, and at that confidence the planner stops streaming and **pins**: `plan 432.5 GB
    (conf 1.00) … -> pinning 432.5 GB`, read off the filer before the first token. That is minutes,
    not seconds, and it is the load `coli-up` waits through. It is also the cold-start cost being
    paid in one place instead of leaking into the first user's decode rate, which is the better
    trade — but a job that budgets 101 seconds for a load will conclude the server hung.

30. **On Linux, `coli` runs CPU-only unless you pass `--gpu`, and it does not mention that it
    did.** (Added 2026-09-16.) The launcher has a block that detects a card and enables CUDA by
    itself — and it is scoped to `win32`, with a comment saying Linux has "the explicit-flag UX"
    instead. So `coli serve --model …` on a node holding an A40 loads 429 GB, serves happily, and
    never touches the card. Nothing in the startup output says so; `nvidia-smi` reports 0 MiB used
    and `GET /health` reports `"gpus": 0`. Upstream knows the shape of this failure — the code
    carries a note about `--gpu`/`--vram` once being ignored silently and *"GPU benchmarks published
    by mistake (#121)"*.
    **`coli doctor` will not catch it**, because doctor plans and serve runs: doctor reported a
    45.7 GB VRAM hot tier and ~2152 hot experts for a configuration that then used neither. Measured
    cost of the mistake on the first pass here: **0.64 tok/s decode and 1.3 tok/s prefill**, which is
    the same 0.64 P0 recorded as its "cold" number. Pass `--gpu auto --auto-tier`, and read
    `/health` rather than the plan to confirm it took.
    One thing rides along with the fix: `--gpu` does `setdefault("CUDA_DENSE", "1")`, and
    `CUDA_DENSE=1` measured 2.56 tok/s against 2.67. Every variable the planner writes is a
    setdefault, so exporting `CUDA_DENSE=0` in the job wins.

31. **The context window defaults to 4096, which is smaller than a coding agent's system prompt.**
    (Added 2026-09-16.) The GLM family's registered `default_context` is 4096 and its maximum is
    1048576. An agent whose preamble does not fit is truncated from the front, which is where the
    system prompt and the tool definitions live — the same failure mode as trap 24, at a
    twentieth of the size. Raising it is nearly free on this box: `coli plan` from 4096 to 131072
    grows the runtime allocation from 7.3 GB to 45.0 GB and moves nothing else, with warm experts at
    371.7 GB, the VRAM hot tier at 45.7 GB and projected residency at 100% throughout. The serve job
    passes `--ctx 131072`.

32. **`core.fileMode` is `false` here, so `chmod +x` never reaches the index and a fresh clone gets
    a driver script it cannot run.** (Added 2026-09-16.) The setting is right — the filer's mode bits
    are synthesised from an NFSv4 ACL and are not to be trusted, which is traps 25 and 28 — but the
    consequence is that git records a new script as 644 however it looks on disk, `git status` says
    nothing, and the failure appears only in somebody else's checkout as a bare *Permission denied*
    from a command on `PATH`. `git update-index --chmod=+x <path>` sets it in the index directly
    — **and then `save-and-push.sh` throws it away**, because that script commits with
    `git commit --only -- <paths>`, which re-reads those paths from the working tree, where
    there is no mode to read. Set the bit, check `git diff --cached --summary` shows the mode
    changes and nothing else, then commit the index with a plain `git commit`.
    **The `ollama-*` three are still 644** and have been since August; they work here because this
    clone's on-disk bits are fine, and they will not work in the next one.

---

## 8. Not done yet

- **The fleet — the repo's next phase, designed 2026-08-22. P0 is nearly done; nothing past it is
  built.** [`P0-STATUS.md`](P0-STATUS.md) is the live record of the measurement campaign and should
  be read before any fleet work: **nine of its twelve tests have passed** and twelve of its findings
  contradict `FLEET-BUILD.md` as originally written.
  **The headline measurement, 2026-09-09:** the 30B int4 helper on **one** A40 serves six concurrent
  users at **51 tok/s each** with a **0.2-second** first token behind a 15,000-token preamble, and
  still gains throughput at eight. The 744B model on a whole 1 TB node manages **3.2–4.4 tok/s for one
  user**. Everything the fleet promises interactively is delivered by one of the ten cards today;
  the big model is a batch instrument you queue for, not a tier you route to. All three engines
  (ollama, vllm, colibrì) behind one front door, spread across the cluster's GPUs by a supervisor
  that acquires nodes when they are free, **yields them when another user's job is blocked by what we
  hold**, and regrows when it can. The full design — goals and non-goals, the placement argument, the
  two data planes, the yield ladder, the citizenship rules, milestones with exit criteria, the
  measurements we owe ourselves, and the traps anticipated but not yet paid for — is
  [`DESIGN.md`](DESIGN.md). Read that before writing any of it — and then
  [`FLEET-BUILD.md`](FLEET-BUILD.md), which turns it into an ordered build with exit criteria and
  **supersedes its engine choice**: ollama is dropped, colibrì becomes the escalation tier, and
  vLLM becomes both the daily driver and the batch engine. Two findings there change how the rest
  of this repo should be read — the **expert-union arithmetic** that caps every multi-token
  optimisation on a 744B top-8-of-256 model, and the **~31-minute cold start** that constrains
  anything holding one. Three things from `DESIGN.md` that change how the items below should be
  read:
  - **Replicas, not shards.** With NVLink inactive (§1), independent single-GPU replicas beat
    tensor parallelism for any model that fits on one card — more aggregate throughput, and a replica
    can be surrendered one at a time where a 4-GPU job cannot. This supersedes the tensor-parallel
    assumption in the vllm item below.
  - **`c3_accel` is booked, never held.** Unchanged in spirit, tightened in practice.
  - **Citizenship is the core feature.** The hardware is already bought and already powered; the real
    cost of this service is other people's queue time, plus our own fair-share, which the *research*
    jobs then pay for. A fleet that has to be torn down by hand when a colleague complains has
    already failed.
- **Web access for the coding agent — NEXT.** Decision made and recorded in §6; the config edit
  itself is not applied. Raise `coder`'s `webfetch` from `ask` to `allow`, leave `websearch` at
  `ask`, and leave the top-level deny alone so the built-in `explore` subagent stays closed. Verify
  afterwards with `opencode agent list`, which prints each agent's fully resolved rule stack: `coder`
  should show `webfetch: allow` / `websearch: ask`, and **every other agent must still show both as
  `deny`**. If `explore` comes back with `allow`, the global block was edited by mistake — that is
  trap §7.12 and it is silent.
- **The PHI boundary, layer 3.** Layers 1 and 2 are done (§6): global default-deny on `webfetch` /
  `websearch`, and a single `coder` agent that raises them to `ask`. Both are config, and config is
  one bad edit from being wrong — and the web-access change above deliberately makes layer 2 weaker,
  which raises the value of this one rather than lowering it. The remaining layer is the one that
  cannot be misconfigured:
  **the clinical model must never run through opencode at all** — a plain Python client against the
  loopback endpoint with no tool-calling surface in the code. Nothing stops a tool-enabled agent from
  putting a transcript fragment into a search query, which is an exfiltration event under
  PSYCH-ASR's on-prem constraint. Not yet written.
- **vllm for PSYCH-ASR Stage 3c.** (Stage *3c* — behavioral and content coding with a local LLM.
  PSYCH-ASR's Stage 4 is feasibility modeling at N=20 and involves no LLM at all.) Ollama is right
  for interactive single-user coding. Batch transcript work
  wants vllm: continuous batching for throughput, and guided decoding against a JSON schema so the
  model is structurally incapable of emitting anything but a valid rating object. The HF safetensors
  copy of `google_medgemma-27b-text-it` is already staged and vllm consumes it directly. Intended
  workflow: prototype prompts against ollama q8, run production passes on vllm bf16.
  **Revised 2026-08-22:** at bf16 (~55 GB) MedGemma 27B does not fit one A40, so it needs either two
  cards with tensor parallelism *or* 8-bit weights and a single card. `DESIGN.md` §4.2 argues for the
  second — one card per replica, several replicas — because on a PCIe-only host replicas are both
  faster in aggregate and yieldable one at a time. The 4-GPU shard verification (§4) stands either
  way; it says the multi-GPU path works, not that we should prefer it.
  `DESIGN.md` §5.3 also changes *how* the batch pass is driven: a filesystem work queue on the
  studies share rather than a network service. That is not a detour — it delivers the layer-3 PHI
  property above as a consequence of the architecture (there is no socket to misconfigure) instead of
  as a discipline someone has to maintain.
- **Walltime.** Both sbatch files default to 8 h. `c3` and `c3_accel` allow up to 7 days if a
  longer-lived server is wanted; `ollama-up` takes an hours argument for shorter ones, which is the
  right choice on `c3_accel` since compute306 is the only 4-GPU node.

**`ollama-code` passes the adopted model to the TUI as well as to one-shots.** `--model` is a
top-level option in opencode 1.18.x, and this matters because the config default is
`qwen3-coder:30b`: without it the TUI is one keystroke from evicting a resident `gpt-oss:120b`.
No config mutation is needed. The live caveat is in §4a: a *resumed* session
can still carry its own model and override the flag.

The 4-GPU shard and one-command serving are done (§4, §4a). The shard verification says the
multi-GPU path on this hardware is sound, which is worth having established even though `DESIGN.md`
argues for replicas over sharding wherever a model fits on one card: knowing the option works is
what makes declining to use it a choice.

---

## The live board

Lessons are not read in the terminal. The assistant runs `board start` from this repository and
tells you which address to open. This machine gets a `127.0.0.1` one; the iPad, which is not on
the institute network, reaches the same board over **Tailscale**. All of them show the same page
at the same time.

On the iPad, open it once in Safari and use Share → **Add to Home Screen**. After that it is an
app with its own icon, no browser chrome, and a long-press shortcut straight to the slate.

Everything the assistant teaches appears there as typeset mathematics the moment it is written:
real LaTeX, real subgroup lattices and commutative diagrams, no refresh and no compile step. You
answer in the terminal, in the box at the bottom of the board, or by hand: the ✎ button opens a
slate you write on with the Apple Pencil. Tap send and the assistant opens the page and reads
your handwriting — no exporting, no airdropping, no retyping a proof you already wrote. Turn on
*live* and it sees each page as you pause. Photos and PDFs dropped anywhere on the board work
too.

With the board on the iPad and the slate for your working, a whole session can happen without
touching the keyboard.

You never run a board command. The tool is `~/Tutor-Board`; its README explains the rest.
