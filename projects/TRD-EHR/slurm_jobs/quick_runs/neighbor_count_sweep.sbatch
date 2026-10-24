#!/bin/bash
#SBATCH --job-name=neighbor_count_sweep
#SBATCH --partition=c3
#SBATCH --time=06:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH -o slurm_jobs/quick_runs/logs/neighbor_count_sweep_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/neighbor_count_sweep_%j_err.txt
#RELAY-VAR EMBEDDER [A-Za-z0-9][A-Za-z0-9._-]{0,79}
#RELAY-VAR REDRAW [01]

# Every retrieval arm swept over every neighbourhood size from 1 to the whole candidate
# pool: logistic-regression-weighted cosine, plain cosine, and random neighbours with
# uniform weights (1,000 seeded draws). Then that encoder's own sweep plot, which the
# manuscript does not place (Figure 4 is the four-encoder composite, drawn by
# plot_cross_embedder_retrieval.sbatch after all four sweeps), and the ROC / PR /
# calibration / decision / ESS / confusion-matrix panels at each arm's best k (Figures
# S8-S9). No GPU and no vLLM server: the
# weighted metric is read off the already-fitted logistic regression and plain
# cosine needs nothing at all, so this is two BLAS matmuls, a lot of sorting, and the
# random draws spread over every CPU. The memory request holds the three per-alpha risk
# matrices, each n_anchors x n_pool; the metrics run one after another and free theirs
# between. The random draws hold about 0.8 GB per worker.
#
# The cosine sweep took about 7 minutes on 32 CPUs; the random arm is about 25 CPU-seconds
# per draw, so roughly 15 minutes more. The 6-hour limit is headroom, not an estimate.
#
# Requires a fitted logistic_regression_EMBEDDED.joblib in RESULTS_DIR/trained_models,
# which scripts.pipeline.predictions.classical_ml writes.
#
# REDRAW=1 skips the sweep and redraws the figures and panels from the CSVs already on
# disk; the panels need best-k CSVs with an ess column, which only a sweep from this
# version writes. Either way the encoder's sweep plot and the best-k panels are
# drawn and the folder is mirrored into results/, because the manuscript links the
# mirror, not RESULTS_DIR.
#
# EMBEDDER=<name> sweeps that embedding model instead of the one .env names, e.g.
#   sbatch --export=ALL,EMBEDDER=bge-en-icl slurm_jobs/quick_runs/neighbor_count_sweep.sbatch
# It needs that model's embeddings.db and fitted logistic regression already on disk.
# .env derives EMBEDDINGS_DIR and RESULTS_DIR from EMBEDDER_MODEL_NAME, so both are
# re-derived here after it is sourced.
#
# Only the primary encoder (PRIMARY_EMBEDDER) has per-patient classifier test
# predictions. For the others the figure reads each classifier line from
# classical_ml_results_*.json and writes no retrieval-minus-classifier contrast; the
# feature-vector XGBoost line, which no encoder changes, is always the primary's
# (FEATURE_RESULTS_DIR), so it is the same in every panel.

# Exit immediately if command fails
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
if [[ -n "${EMBEDDER:-}" ]]; then
  export EMBEDDER_MODEL_NAME="${EMBEDDER}"
  export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
  export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
fi
PRIMARY_EMBEDDER=Qwen-Qwen3-Embedding-8B
export FEATURE_RESULTS_DIR="${ARTIFACTS_DIR}/${PRIMARY_EMBEDDER}/${VLLM_MODEL_NAME}"
echo "Sweeping ${EMBEDDER_MODEL_NAME}: results in ${RESULTS_DIR}"

echo "Running on $(hostname) with ${SLURM_CPUS_PER_TASK} cpus"

if [[ "${REDRAW:-0}" == "1" ]]; then
  python -m scripts.pipeline.predictions.neighbor_count_sweep --redraw
else
  python -m scripts.pipeline.predictions.neighbor_count_sweep
fi
# The two drawing steps may fail without losing what the other drew: the mirror runs
# either way, and the job still exits non-zero if either failed.
DRAW_STATUS=0
python -m scripts.pipeline.predictions.plot_neighbor_sweep_figure || DRAW_STATUS=$?
python -m scripts.pipeline.predictions.best_k_panels || DRAW_STATUS=$?

# Copy the sweep folder back beside the other results for easier access
TARGET_DIR="results/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}/"
mkdir -p "${TARGET_DIR}"
rsync -av "${RESULTS_DIR}/neighbor_count_sweep" "${TARGET_DIR}"
exit "${DRAW_STATUS}"
