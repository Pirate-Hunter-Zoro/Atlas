#!/bin/bash
#SBATCH --job-name=neighbor_count_sweep
#SBATCH --partition=c3
#SBATCH --time=06:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH -o slurm_jobs/quick_runs/logs/neighbor_count_sweep_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/neighbor_count_sweep_err.txt

# Both retrieval metrics, swept over every neighbourhood size from 1 to the whole
# candidate pool. No GPU and no vLLM server: the importance-weighted metric is read off
# the already-fitted logistic regression and plain cosine needs nothing at all, so this is
# two BLAS matmuls and a lot of sorting. The memory request is what holds the three
# per-alpha risk matrices, each n_anchors x n_pool; the metrics run one after another and
# free theirs between, so a second metric costs time and not memory.
#
# Requires a fitted logistic_regression_EMBEDDED.joblib in RESULTS_DIR/trained_models,
# which scripts.pipeline.predictions.classical_ml writes.

# Exit immediately if command fails
set -e

# ---- Conda configuration ----
CONDA_ENV=/media/studies/ehr_study/analysis/mferguson/venvs/embedder_pipeline

# ---- Boilerplate env/bootstrap ----
module purge
module load Anaconda3/2025.06-0
eval "$(conda shell.bash hook)"

# Conda often dislikes 'set -u'—use this safe pattern:
set +u; conda activate "${CONDA_ENV}"; set -u || exit 10

# Load env variables
ENV_FILE="${SLURM_SUBMIT_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found." >&2
  exit 11
fi
set -a; source "${ENV_FILE}"; set +a

echo "Running on $(hostname) with ${SLURM_CPUS_PER_TASK} cpus"

python -m scripts.pipeline.predictions.neighbor_count_sweep

# Copy the sweep folder back beside the other results for easier access
TARGET_DIR="results/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}/"
mkdir -p "${TARGET_DIR}"
rsync -av "${RESULTS_DIR}/neighbor_count_sweep" "${TARGET_DIR}"
