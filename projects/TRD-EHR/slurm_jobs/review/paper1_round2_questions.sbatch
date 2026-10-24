#!/bin/bash
#SBATCH --job-name=paper1_round2_questions
#SBATCH --partition=c3_short
#SBATCH --time=01:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o slurm_jobs/review/logs/paper1_round2_questions_%j_out.txt
#SBATCH -e slurm_jobs/review/logs/paper1_round2_questions_%j_err.txt
#RELAY-VAR QUESTION (curve|subgroup_race|subgroup_bh|operating_point|recurrence_level|calibration_bins)

# Paper 1, round-2 review: one data question per job, answered in RELAY: lines and
# nothing else (scripts/pipeline/review/round2_questions.py). It writes no file, refits
# nothing and prints no row: every line is a curve value, a count, an interval or a
# category label. One question per job because a report keeps only 40 RELAY: lines.
#
#   QUESTION=curve             plain-cosine ROC AUC at k = 25,000 .. 34,063 for
#                              bge-small-en-v1.5 and bge-en-icl, with raw facts beside
#                              it (float32 against float64 AUC, tied similarities at
#                              the cut, risk spread); no verdict on the drop near
#                              k = 30,000 (one process per encoder, because each
#                              encoder's paths are read at import)
#   QUESTION=subgroup_race     White-minus-non-White contrasts with their CIs
#   QUESTION=subgroup_bh       the Table S12 contrasts with their CIs
#   QUESTION=operating_point   S12.1 sensitivity/specificity with bootstrap CIs
#   QUESTION=recurrence_level  the MDD recurrence level of Table S11's n = 32 row
#   QUESTION=calibration_bins  Table S4's retrieval rows on Figure S5's bins
#
# Everything except curve reads the primary encoder (Qwen-Qwen3-Embedding-8B), whose
# RESULTS_DIR holds the per-patient predictions and the best-k files; the subgroup
# questions read ARTIFACTS_DIR/review/subgroups, which run_subgroups wrote.

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

case "${QUESTION:-}" in
  curve|subgroup_race|subgroup_bh|operating_point|recurrence_level|calibration_bins) ;;
  *) echo "RELAY: round2 QUESTION refused: not one of the six"; exit 12 ;;
esac

CONDA_ENV=/media/studies/ehr_study/analysis/mferguson/venvs/embedder_pipeline
module purge
module load Anaconda3/2025.06-0
eval "$(conda shell.bash hook)"
set +u; conda activate "${CONDA_ENV}"; set -u || exit 10

ENV_FILE="${SLURM_SUBMIT_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "RELAY: round2 .env missing"
  exit 11
fi
set -a; source "${ENV_FILE}"; set +a
cd "${SLURM_SUBMIT_DIR}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

use_encoder() {
  export EMBEDDER_MODEL_NAME="$1"
  export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
  export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
}

if [[ "${QUESTION}" == "curve" ]]; then
  for ENCODER in bge-small-en-v1.5 bge-en-icl; do
    use_encoder "${ENCODER}"
    python -m scripts.pipeline.review.round2_questions curve
  done
else
  use_encoder Qwen-Qwen3-Embedding-8B
  python -m scripts.pipeline.review.round2_questions "${QUESTION}"
fi
