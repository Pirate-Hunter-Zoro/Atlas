#!/bin/bash
#SBATCH --job-name=diagnose
#SBATCH --partition=c3_short
#SBATCH --time=00:15:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH -o slurm_jobs/quick_runs/logs/diagnose_%j_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/diagnose_%j_err.txt
#RELAY-VAR EMBEDDER (bge-small-en-v1\.5|bge-en-icl|Qwen-Qwen3-Embedding-4B|Qwen-Qwen3-Embedding-8B)
#RELAY-VAR LOOK (RESULTS_DIR|EMBEDDINGS_DIR)(/[A-Za-z0-9_][A-Za-z0-9._-]{0,79}){0,4}/?
#RELAY-VAR MODULE scripts(\.[a-z_][a-z0-9_]{0,60}){1,6}

# A question for the cluster about a failed job, answered in RELAY: lines and
# nothing else. It produces no file and reads no row: the relay publishes what it
# prints, and the Mac fixes the job from it (`board diagnose`).
#
# It prints the checkout, which .env locations are set and exist (by key, never
# by where), RESULTS_DIR and EMBEDDINGS_DIR two levels down, and whether MODULE
# is found. A file or directory is named only if the repository publishes that
# name (`relay_hook.allowlist`); the rest of a directory is counts by extension.
#
#   EMBEDDER=<name>   look at that encoder's directories, as the sweep re-derives
#                     them; one of RELAY_ENCODERS (relay_trap.sh), nothing else
#   LOOK=RESULTS_DIR/neighbor_count_sweep
#                     list that one directory three levels down instead; every
#                     segment after the key must be an allowlisted name
#   MODULE=scripts.pipeline.predictions.best_k_panels
#                     say whether that module is found (it is not run); one of
#                     DIAGNOSABLE below, the modules the pipeline's recipes run

set -e
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

DIAGNOSABLE="
scripts.data_loading.build_jsons
scripts.data_loading.fit_to_anchor
scripts.pipeline.causal.build_leaderboard
scripts.pipeline.causal.run_one
scripts.pipeline.causal.validate
scripts.pipeline.counterfactual.run_one
scripts.pipeline.embeddings.embedding_audit
scripts.pipeline.embeddings.forge_ablated_embeddings
scripts.pipeline.embeddings.forge_embeddings
scripts.pipeline.narratives.forge_narratives
scripts.pipeline.neighbors.llm_similarity_audit
scripts.pipeline.neighbors.merge_judgements
scripts.pipeline.neighbors.narrative_audit
scripts.pipeline.predictions.ablation_runner
scripts.pipeline.predictions.analyze_trd_prediction
scripts.pipeline.predictions.best_k_panels
scripts.pipeline.predictions.classical_ml
scripts.pipeline.predictions.feature_importance
scripts.pipeline.predictions.fusion_analysis
scripts.pipeline.predictions.neighbor_count_sweep
scripts.pipeline.predictions.plot_cross_embedder
scripts.pipeline.predictions.plot_cross_embedder_retrieval
scripts.pipeline.predictions.plot_discrimination_forest
scripts.pipeline.predictions.plot_neighbor_sweep_figure
scripts.pipeline.predictions.plot_time_zero_timeline
scripts.pipeline.predictions.redraw_feature_importance
scripts.pipeline.predictions.redraw_manuscript_panels
scripts.pipeline.predictions.run_neighborhood_constructor
scripts.pipeline.review.history_quintiles
scripts.pipeline.review.holdout_representativeness
scripts.pipeline.review.judge_prompt.run_comparison
scripts.pipeline.review.metric_intervals
scripts.pipeline.review.parity.render_narratives
scripts.pipeline.review.parity.run_embedded_arm
scripts.pipeline.review.parity.run_feature_arm
scripts.pipeline.review.religion.render_narratives
scripts.pipeline.review.religion.run_embedded_arm
scripts.pipeline.review.religion.run_feature_arm
scripts.pipeline.review.religion.summarize
scripts.pipeline.review.subgroups.run_subgroups
scripts.pipeline.vectors.forge_vectors
"

# Checked here as well as by the relay, so a bare sbatch is held to the same
# lists. A refused value is never echoed.
if [[ -n "${EMBEDDER:-}" ]]; then
  # One whole word of the list: a value holding a space is two names.
  _known=0
  for _e in ${RELAY_ENCODERS}; do [[ "${EMBEDDER}" == "${_e}" ]] && _known=1; done
  if [[ "${_known}" != 1 ]]; then
    echo "RELAY: probe EMBEDDER refused: not one of RELAY_ENCODERS"
    exit 12
  fi
fi
if [[ -n "${MODULE:-}" && "${DIAGNOSABLE}" != *$'\n'"${MODULE}"$'\n'* ]]; then
  echo "RELAY: probe MODULE refused: not one of DIAGNOSABLE"
  exit 12
fi

CONDA_ENV=/media/studies/ehr_study/analysis/mferguson/venvs/embedder_pipeline
module purge
module load Anaconda3/2025.06-0
eval "$(conda shell.bash hook)"
set +u; conda activate "${CONDA_ENV}"; set -u || exit 10

ENV_FILE="${SLURM_SUBMIT_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "RELAY: probe .env missing"
  exit 11
fi
set -a; source "${ENV_FILE}"; set +a
if [[ -n "${EMBEDDER:-}" ]]; then
  export EMBEDDER_MODEL_NAME="${EMBEDDER}"
  export EMBEDDINGS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}"
  export RESULTS_DIR="${ARTIFACTS_DIR}/${EMBEDDER_MODEL_NAME}/${VLLM_MODEL_NAME}"
fi

python -m relay_hook --look "${LOOK:-}" --module "${MODULE:-}"
