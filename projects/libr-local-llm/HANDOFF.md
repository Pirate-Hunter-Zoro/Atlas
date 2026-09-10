# HANDOFF.md

**Session of 2026-09-09, second sitting. A build session on `FLEET-BUILD.md`, not a lesson.**

## Where to pick up

Read [`P0-STATUS.md`](P0-STATUS.md). It is the live record of the P0 campaign and the only file that
knows what has actually been run. `fleet-p0/RESULTS.md`, on the studies share, is the long form with
every table.

## What happened

**P0 is done except for tests 8 and 12.** Ten of the twelve tests have passed. Nothing is left
running — every job exited on its own and `squeue -u $USER` is clear of P0 work.

The result the campaign existed to get: **the 30B int4 helper on one A40 serves six concurrent users
at 51 tok/s each with a 0.2-second first token, behind a 15,000-token preamble, and is still gaining
throughput at eight users. The 744B on a whole 1 TB node manages 3.3–4.4 tok/s for one user.**
Roughly 30× per session on a thirtieth of the hardware.

Two sections of `FLEET-BUILD.md` are now retracted rather than amended:

- **§2.2** claimed colibrì's "four GPUs are worth under 2 %" did not apply to our hardware. It does.
  Measured on compute306: 4.31 tok/s on one card, 4.35 on four. **Give tier 2 one card, not four.**
- **§10's starting configuration** listed `CUDA_DENSE=1`, `XEXP=1` and a `DRAFT` sweep. Measured,
  `CUDA_DENSE` does nothing, `XEXP=1` costs 12 %, and `DRAFT` costs 11–19 %. The one lever that
  works is `numactl --interleave=all`, worth **+14–18 %**, which `coli tune` structurally cannot
  find because its candidate set is thread counts and CUDA stream shapes.

## The two failures that cost the most, and what fixes them

Both are recorded as findings 7 and 8 in `P0-STATUS.md` and as traps 25 and 26 in `README.md`.

1. **`pip` put 8.7 GB of vLLM in `~/.local` and the job then ran that copy instead of the
   environment's.** pip's writability probe is `os.access`, which lies on this Isilon — it returns
   False for a directory the same process writes to fine, because the filer synthesises POSIX mode
   bits lossily from the NFSv4 ACL. `--no-user` did not stop it. **`PYTHONNOUSERSITE=1` does**, and
   it also stops the shadowing at import time.
2. **vLLM 0.29's default sampler JIT-compiles a CUDA kernel at warm-up and there is no
   `/usr/local/cuda`.** The server died minutes into startup, after the weights loaded and the KV
   cache was allocated. `CUDA_HOME=$EBROOTCUDA` fixes the lookup; we also set
   `VLLM_USE_FLASHINFER_SAMPLER=0`, because a kernel build inside the serving path is a cold-start
   hazard.

## One thing left for you

`rm -rf ~/.local/lib/python3.12` recovers **8.7 GB** on a home share that is 86 % full. It is the
whole accidental install and nothing depends on it; the sandbox refused the recursive delete, so it
did not happen. `~/.local/lib/python3.{9,11,13}` and `~/.local/bin` are unrelated — leave them.

## What the user decided

Nothing new was put to them this sitting. The 429 GB stage they authorised in the first sitting
finished: 61.6 minutes at 116 MB/s, which is half the rate the runbook assumed.

## About this user

They work in a VSCode terminal on a compute node and close the laptop without warning; leave long
work as Slurm jobs that survive it, and leave a file behind that says where things are. They read
the runbook as the source of truth, so a finding that contradicts it belongs *in* the repo, not in a
chat message they will not have tomorrow.
