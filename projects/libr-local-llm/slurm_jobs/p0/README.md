# slurm_jobs/p0 — the P0 measurement harness

The job files that produced [`../../P0-STATUS.md`](../../P0-STATUS.md), kept here so the campaign is
reproducible. **Their output does not live in this repo.** Every one of them writes to
`/media/studies/ehr_study/analysis/mferguson/fleet-p0/`, where `RESULTS.md` is the long form with
every table — the repo is public, and job logs are not architecture.

Run them from that directory, not from here; the `#SBATCH --output` paths are relative to `logs/`.

| file | test | what it settles |
|---|---|---|
| `install_vllm.sh` | — | builds the vLLM environment. `PYTHONNOUSERSITE=1` is load-bearing; see trap 25 in `README.md` |
| `t2_stage_glm52.sbatch` | 2 | stages GLM-5.2 int4, 429 GB, and times it |
| `coli_ab.sh` | 3–7 | **one colibrì configuration under §10's snapshot protocol.** The other colibrì jobs are loops over this |
| `t34567_colibri.sbatch` | 3, 4, 5, 7 | cold vs warm load, `coli plan`/`tune`, and the lever sweep |
| `t4b_omp_sweep.sbatch` | 4b | the OpenMP thread curve, 12 through 92 |
| `t5b_dense_confirm.sbatch` | 5 | `CUDA_DENSE` re-run with `COLI_CUDA=1`, plus interleave repeats |
| `t6_gpu_scaling.sbatch` | 6 | one A40 against four, on compute306 |
| `t8b_tier1_1gpu.sbatch` | 8b, 9 | the standard helper under 1–8 concurrent users |
| `bench_tier1.py` | 8b, 9 | the concurrency harness `t8b` drives — TTFT and tok/s against an OpenAI-shaped endpoint |
| `t11_chain.sbatch` | 11 | the `afterany` restart chain |

## Three things that are easy to get wrong

**`coli_ab.sh` exists because `.coli_usage` is a persistent learned routing profile.** A
byte-for-byte identical configuration has measured 5.46 and then 2.56 tok/s with nothing changed. It
snapshots the file, sleeps 35 s for VRAM to drain, restores it byte-for-byte, then measures — and
every A/B in P0 went through it. Do not benchmark colibrì without it.

**Alternate configurations; never sweep them in order.** The page cache warms as a job runs, so an
ascending sweep cannot separate the knob from the cache. `t4b_omp_sweep.sbatch` has this defect and
its results needed a second instrument to confirm; `t5b` and `t6` alternate and do not.

**Never compare tok/s across two nodes.** compute306 and compute302 differed by 36 % in the same
configuration on the same commit. Every comparison here runs inside one job on one node.
