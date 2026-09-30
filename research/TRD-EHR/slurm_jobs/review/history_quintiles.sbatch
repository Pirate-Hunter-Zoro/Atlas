#!/bin/bash
#SBATCH --job-name=history_quintiles
#SBATCH --partition=c3_short
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH -o slurm_jobs/review/logs/history_quintiles_out.txt
#SBATCH -e slurm_jobs/review/logs/history_quintiles_err.txt

# =============================================================================
# Supplement Table S8: retrieval ROC AUC by quintile of pre-index history length,
# each arm at its own best k (importance-weighted 295, plain cosine 757, uniform
# random 32,720), with a bootstrap 95% CI per quintile. Reads the sweep's
# best_k_predictions_*.csv, so run it after neighbor_count_sweep.sbatch.
# Minutes, not hours: 3 arms x 5 quintiles x N_BOOTSTRAP AUCs.
# =============================================================================

set -e

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

python -m scripts.pipeline.review.history_quintiles

LOCAL_RESULTS_DIR="results/review/history_quintiles"
mkdir -p "${LOCAL_RESULTS_DIR}"
rsync -av "${ARTIFACTS_DIR}/review/history_quintiles/" "${LOCAL_RESULTS_DIR}/"

echo "Done."
