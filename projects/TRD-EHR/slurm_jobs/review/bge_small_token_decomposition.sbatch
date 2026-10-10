#!/bin/bash
#SBATCH --job-name=bge_small_token_decomposition
#SBATCH --partition=c3_short
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o slurm_jobs/review/logs/bge_small_token_decomposition_%j_out.txt
#SBATCH -e slurm_jobs/review/logs/bge_small_token_decomposition_%j_err.txt

# Supplement Figure S7, both panels, redrawn from bge-small-en-v1.5's embeddings.db by
# scripts/pipeline/review/bge_small_token_decomposition.py, the notebook's computation as a
# module, with panel B titled "Cluster A". It reads the narratives' text to find the
# driving token and prints only RELAY: yes/no on whether each token is the expected one,
# the two cluster sizes, and cluster A's nested silhouette. Writes the two PNGs to
# results/notebook_figures/ and notebooks/figures/ only when both tokens are the expected
# ones; otherwise it prints a RELAY: refusal and fails having written neither, so nothing
# mismatched is exported. Refits no prediction model.
#
# Pairs are histogrammed one block of rows at a time; the KMeans fits and the vectorizer
# over 42,579 narratives are what the memory is for.

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

export EMBEDDER_MODEL_NAME=bge-small-en-v1.5
export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

python -m scripts.pipeline.review.bge_small_token_decomposition
