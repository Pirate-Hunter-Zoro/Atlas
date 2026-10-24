#!/bin/bash
#SBATCH --job-name=stage1c_join_grid
#SBATCH --partition=c3_short
#SBATCH --time=0-01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/logs/stage1c_join_grid_out.txt
#SBATCH -e slurm_jobs/logs/stage1c_join_grid_err.txt

# The grid's Stage 1c: join every cell whose aligned transcript and turn table both
# landed in this run, then write slurm_jobs/logs/grid-<id>/manifest.json.
#
# Submitted by the grid driver (stage1_grid.sbatch) with afterany on every align and
# diarize job, with PSYCH_ASR_GRID set, so STAGE1_DIR is this run's own directory. The
# driver passes --grid-id and the axes; the stem comes from the inbox WAV here.
#
# NO GPU: a timestamp join and a text render, seconds per cell.
#
# The stem is never echoed. Each cell's log line names the cell, not the session.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

activate_env asr_env

STEM="$(session_stem "${INPUT_DIR}")"
python -m psych_asr.cli.join_grid --stem "${STEM}" --stage1-dir "${PSYCH_ASR_STAGE1_DIR}" "$@"
