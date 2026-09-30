#!/bin/bash
#SBATCH --job-name=metric_intervals
#SBATCH --partition=c3_short
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o slurm_jobs/review/logs/metric_intervals_out.txt
#SBATCH -e slurm_jobs/review/logs/metric_intervals_err.txt

# =============================================================================
# Intervals for every number the paper prints that the pipeline wrote without
# one: AUPRC, Brier, WCE and the binned calibration slope and intercept for the
# 8 primary classifiers (Table 2, Tables S1, S3, S4), embedded logistic-
# regression AUPRC for all 4 encoders (Table S2), and the cohort descriptives of
# Figure 1 and Supplement S7, plus Figure S10D.
#
# Refits nothing. The three non-primary encoders are rescored from their saved
# logistic regression and their own embeddings.db, and every recomputed ROC AUC
# must match the pipeline's classical_ml_results or the job fails.
#
# CPU only, minutes: 12 models x N_BOOTSTRAP compute_metrics calls and 3 x
# N_BOOTSTRAP Spearman correlations over the cohort. Submit from the project root.
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

python -m scripts.pipeline.review.metric_intervals

LOCAL_RESULTS_DIR="results/review/metric_intervals"
mkdir -p "${LOCAL_RESULTS_DIR}"
rsync -av "${ARTIFACTS_DIR}/review/metric_intervals/" "${LOCAL_RESULTS_DIR}/"

echo "Done."
