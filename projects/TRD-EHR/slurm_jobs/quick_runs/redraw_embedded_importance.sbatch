#!/bin/bash
#SBATCH --job-name=redraw_embedded_importance
#SBATCH --partition=c3_short
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/quick_runs/logs/redraw_embedded_importance_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/redraw_embedded_importance_%j_err.txt

# Supplement Figures S1-S3 (cumulative importance, cumulative correlation, ROC AUC by
# retained principal components) for the primary encoder, redrawn with the paper's
# classifier names: feature_importance --redraw-embedded. It loads the CACHED fitted
# models and PCA pipelines and refuses (CacheMiss) rather than refit one, because a refit
# can choose a different fit of equal discrimination and the supplement quotes this fit's
# coefficient counts. Prints RELAY: the logistic regression's non-zero coefficient count
# and every classifier's K80/K90, to check against the supplement (385 of 4,096; 179 and
# 236). Also writes pca_sweep_<model>_EMBEDDED.json, so the next restyle needs no model.

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

export EMBEDDER_MODEL_NAME=Qwen-Qwen3-Embedding-8B
export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"

python -m scripts.pipeline.predictions.feature_importance --redraw-embedded

LOCAL_RESULTS_DIR="results/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
mkdir -p "${LOCAL_RESULTS_DIR}"
rsync -a "${RESULTS_DIR}/feature_importance/" "${LOCAL_RESULTS_DIR}/feature_importance/"
