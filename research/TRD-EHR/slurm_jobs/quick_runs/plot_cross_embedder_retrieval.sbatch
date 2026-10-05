#!/bin/bash
#SBATCH --job-name=plot_cross_embedder_retrieval
#SBATCH --partition=c3_short
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH -o slurm_jobs/quick_runs/logs/plot_cross_embedder_retrieval_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/plot_cross_embedder_retrieval_%j_err.txt

# Manuscript Figure 6 (lr_dimensions_vs_best_k.png), the embedding-width plot beside
# it, and cross_embedder_retrieval.csv, the table the manuscript's cross-encoder
# retrieval numbers are read from. It reads every encoder's neighbor_count_sweep and
# fitted embedded logistic regression and refits nothing, so it runs only after all
# four neighbor_count_sweep.sbatch runs have finished; it fails naming any encoder
# whose sweep_summary.json is missing. Then ARTIFACTS_DIR/cross_embedder_retrieval is
# mirrored into results/, because the manuscript links the mirror.

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

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

python -m scripts.pipeline.predictions.plot_cross_embedder_retrieval

mkdir -p results/
rsync -av "${ARTIFACTS_DIR}/cross_embedder_retrieval" "results/"
