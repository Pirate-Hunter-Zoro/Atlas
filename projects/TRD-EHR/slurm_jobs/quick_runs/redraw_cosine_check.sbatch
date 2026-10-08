#!/bin/bash
#SBATCH --job-name=redraw_cosine_check
#SBATCH --partition=c3_short
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/quick_runs/logs/redraw_cosine_check_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/redraw_cosine_check_%j_err.txt

# Supplement Figure S6: random-pair against nearest-neighbor-pair cosine similarity, one
# panel per encoder, redrawn as densities so the neighbor pairs are visible beside the
# tens of millions of random pairs (trd_sanity_checks.run_cosine_check). It reads each
# encoder's embeddings.db and its neighbor_results_*.csv, refits nothing, writes only
# cosine_score_random_vs_neighbor.png per encoder, and mirrors it into results/. Each
# encoder runs in its own process, because its paths are read when the modules load.
# Prints RELAY: pair counts and the two medians per encoder.

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

CONDA_ENV=/media/studies/ehr_study/analysis/mferguson/venvs/embedder_pipeline
module purge
module load Anaconda3/2025.06-0
eval "$(conda shell.bash hook)"
set +u; conda activate "${CONDA_ENV}"; set -u || exit 10

ENV_FILE="${SLURM_SUBMIT_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found." >&2
  exit 11
fi
set -a; source "${ENV_FILE}"; set +a
cd "${SLURM_SUBMIT_DIR}"

for ENCODER in bge-small-en-v1.5 bge-en-icl Qwen-Qwen3-Embedding-4B Qwen-Qwen3-Embedding-8B; do
  export EMBEDDER_MODEL_NAME="${ENCODER}"
  export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
  export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
  echo "RELAY: S6 encoder ${ENCODER}"
  python -m scripts.pipeline.predictions.trd_sanity_checks --cosine-only
  TARGET_DIR="results/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
  mkdir -p "${TARGET_DIR}"
  rsync -a "${RESULTS_DIR}/cosine_score_random_vs_neighbor.png" "${TARGET_DIR}/"
done
