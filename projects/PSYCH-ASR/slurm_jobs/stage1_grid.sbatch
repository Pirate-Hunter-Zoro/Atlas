#!/bin/bash
#SBATCH --job-name=stage1_grid
#SBATCH --partition=c3_accel
#SBATCH --time=3-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH -o slurm_jobs/logs/stage1_grid_%j_out.txt
#SBATCH -e slurm_jobs/logs/stage1_grid_%j_err.txt
#RELAY-VAR GRID_TYPISTS [a-z0-9-]+(:[a-z0-9-]+)*
#RELAY-VAR GRID_STOPWATCHES [a-z0-9-]+(:[a-z0-9-]+)*
#RELAY-VAR GRID_TAGGERS [a-z0-9-]+(:[a-z0-9-]+)*
#RELAY-VAR GRID_DRY_RUN [01]
#RELAY-VAR GRID_REJOIN [0-9]+

# The Stage 1 grid driver: 4 typists x 2 stopwatches x 5 name-taggers = 40 cells, from
# 17 GPU jobs and one CPU join. It submits them, waits, and reports from the manifest.
#
#     board job -- slurm_jobs/stage1_grid.sbatch GRID_DRY_RUN=1     the plan + preflight, no GPU
#     board job -- slurm_jobs/stage1_grid.sbatch                     the whole grid
#     board job -- slurm_jobs/stage1_grid.sbatch GRID_TYPISTS=parakeet:canary GRID_TAGGERS=community-1
#     board job -- slurm_jobs/stage1_grid.sbatch GRID_REJOIN=<driver job id>
#     sbatch slurm_jobs/stage1_grid.sbatch                           without the relay
#
# THE JOB GRAPH (psych_asr/grid.py):
#
#     transcribe:<t>  (4, GPU, the typist's env)
#         --afterok + kill-on-invalid-dep-->  align:<t>+<s>  (8, GPU, asr_env)  --+
#     diarize:<n>     (5, GPU, its own env, no dependency)  ---------------------+--afterany--> join (CPU)
#
# An align waits for its own typist with afterok, and --kill-on-invalid-dep cancels it
# when that typist failed; otherwise it would stay pending forever and the join would never
# start. The join waits for everything with afterany, so one dead arm still lets every
# other cell join, and the dead arm's cells are reported as missing.
#
# ONE OUTPUT DIRECTORY PER RUN. Every child runs with PSYCH_ASR_GRID=<this job's id>, and
# job_env.sh writes its outputs under stage1/grid-<id>/ in the data root, so no run touches
# an earlier run's files. Logs, jobs.tsv and manifest.json go to slurm_jobs/logs/grid-<id>/;
# this driver's own log, which the relay reads, is slurm_jobs/logs/stage1_grid_<id>_out.txt.
#
# GRID_REJOIN=<id> submits only the join, for run <id>: when the join died, it re-joins
# that run's kept inputs without any GPU job. Pass the same GRID_* subsets the run had.
#
# c3_accel with no GPU: c3 is suspended by c3_short, which would stall this driver while
# its children run, and c3_short's time limit is shorter than a grid. One CPU, 2 GB.
#
# The grid runs arms and keeps every output. It never scores, compares or ranks them.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

activate_env asr_env

FLAGS=()
if [[ -n "${GRID_TYPISTS:-}" ]]; then
    FLAGS+=(--typist "${GRID_TYPISTS}")
fi
if [[ -n "${GRID_STOPWATCHES:-}" ]]; then
    FLAGS+=(--stopwatch "${GRID_STOPWATCHES}")
fi
if [[ -n "${GRID_TAGGERS:-}" ]]; then
    FLAGS+=(--name-tagger "${GRID_TAGGERS}")
fi

if [[ "${GRID_DRY_RUN:-0}" == 1 ]]; then
    # Prints every sbatch command and the preflight, submits nothing, waits for nothing.
    FLAGS+=(--dry-run --preflight)
elif [[ -n "${GRID_REJOIN:-}" ]]; then
    FLAGS+=(--rejoin "${GRID_REJOIN}" --wait)
else
    FLAGS+=(--wait)
fi

python -m psych_asr.cli.grid_submit "${FLAGS[@]}"
