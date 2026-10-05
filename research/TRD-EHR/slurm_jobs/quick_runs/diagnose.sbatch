#!/bin/bash
#SBATCH --job-name=diagnose
#SBATCH --partition=c3_short
#SBATCH --time=00:15:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH -o slurm_jobs/quick_runs/logs/diagnose_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/diagnose_%j_err.txt
#RELAY-VAR EMBEDDER [A-Za-z0-9][A-Za-z0-9._-]{0,79}
#RELAY-VAR LOOK (RESULTS_DIR|EMBEDDINGS_DIR)(/[A-Za-z0-9_][A-Za-z0-9._-]{0,79}){0,4}
#RELAY-VAR MODULE scripts(\.[a-z_][a-z0-9_]{0,60}){1,6}

# A question for the cluster about a failed job, answered in RELAY: lines and
# nothing else. It produces no file and reads no row: the relay publishes what it
# prints, and the Mac fixes the job from it (`board diagnose`).
#
# It prints the checkout, which .env locations are set and exist (by key, never
# by where), every file under RESULTS_DIR and EMBEDDINGS_DIR two levels down by
# name with its row or byte count, and whether MODULE imports.
#
#   EMBEDDER=<name>   look at that embedder's directories, as the sweep re-derives them
#   LOOK=RESULTS_DIR/neighbor_count_sweep
#                     list that one directory three levels down instead
#   MODULE=scripts.pipeline.predictions.best_k_panels
#                     say whether that module is found (it is not run)

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

CONDA_ENV=/media/studies/ehr_study/analysis/mferguson/venvs/embedder_pipeline
module purge
module load Anaconda3/2025.06-0
eval "$(conda shell.bash hook)"
set +u; conda activate "${CONDA_ENV}"; set -u || exit 10

ENV_FILE="${SLURM_SUBMIT_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "RELAY: probe .env missing"
  exit 11
fi
set -a; source "${ENV_FILE}"; set +a
if [[ -n "${EMBEDDER:-}" ]]; then
  export EMBEDDER_MODEL_NAME="${EMBEDDER}"
  export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
  export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
fi

python -m relay_hook --look "${LOOK:-}" --module "${MODULE:-}"
