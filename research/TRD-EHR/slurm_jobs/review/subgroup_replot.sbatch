#!/bin/bash
#SBATCH --job-name=subgroup_replot
#SBATCH --partition=c3_short
#SBATCH --time=00:15:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH -o slurm_jobs/review/logs/subgroup_replot_%j_out.txt
#SBATCH -e slurm_jobs/review/logs/subgroup_replot_%j_err.txt

# Supplement Figure S11 and the subgroup tables, redrawn from the saved
# subgroup_performance.csv and subgroup_contrasts.csv (run_subgroups --replot). No
# bootstrap and no prediction is read: this is a labelling change, the retrieval arm's
# legend entry now "logistic-regression-weighted". Mirrors the folder into results/.

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

python -m scripts.pipeline.review.subgroups.run_subgroups --replot

LOCAL_RESULTS_DIR="results/review/subgroups"
mkdir -p "${LOCAL_RESULTS_DIR}"
rsync -a "${ARTIFACTS_DIR}/review/subgroups/" "${LOCAL_RESULTS_DIR}/"
