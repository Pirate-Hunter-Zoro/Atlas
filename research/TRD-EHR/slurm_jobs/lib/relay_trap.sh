#!/bin/bash
# ---------------------------------------------------------------------------
# relay_trap.sh -- what a failed job says about itself, behind RELAY:.
#
#     set -e
#     source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"
#
# SOURCE IT FIRST, before the conda block. On a non-zero exit the job prints
#
#     RELAY: recipe <recipe> failed: exit <n> after line <n>, checkout <sha>
#
# and every Python step in it prints its own failure first: the exception type,
# the file and line, and the inputs it held by name and count (`relay_hook.py`,
# installed by `sitecustomize.py`, which the PYTHONPATH below loads into every
# interpreter). Nothing on success. The relay publishes RELAY: lines in the
# job's report, and the Mac fixes the job from them, so they never carry a
# value, a row or an exception message.
#
# THE STATUS IS THE JOB'S. The relay's wrapper records the exit code after this
# script returns, so the trap changes nothing about it and writes no file. A
# recipe with a cleanup of its own hands it to `relay_on_exit <function>`: a
# second `trap ... EXIT` would replace this one.
#
# Safe under `set -u`: it reads no variable that may be unset.
# ---------------------------------------------------------------------------

# Every location `.env` sets, so a path is named by its key and never by where it
# is. Under RESULTS_DIR and EMBEDDINGS_DIR a file or directory name is printed only
# from an allowlist; everywhere else, and for any other name, it is a placeholder,
# because the per-patient trees name files and directories by patient id.
#
# The allowlist is built from tracked files when a report is written
# (`relay_hook.allowlist`): every segment of threads.json's outputs and exports,
# of each tracked request's produces and export, and of every `results/` path a
# recipe names. These two lists are the names those files do not carry:
#   RELAY_ENCODERS  the encoder directories, EMBEDDERS in
#                   scripts/pipeline/predictions/plot_cross_embedder.py; the only
#                   values diagnose.sbatch's EMBEDDER takes
#   RELAY_ALLOW     the judge model's directory, and the fixed directories the
#                   Python writes under RESULTS_DIR by name
export RELAY_ENCODERS="bge-small-en-v1.5 bge-en-icl Qwen-Qwen3-Embedding-4B Qwen-Qwen3-Embedding-8B"
export RELAY_ALLOW="google_medgemma-27b-text-it trained_models trained_models_pca feature_importance neighbor_count_sweep best_k_panels cross_embedder_retrieval review"
export RELAY_PATH_KEYS="PREP_DATA_DIR OUTPUT_DATA_DIR PROCEDURE_CSV_PATH MEDICATION_CSV_PATH DIAGNOSIS_CSV_PATH ENCOUNTER_CSV_PATH VITALS_CSV_PATH PERSON_CSV_PATH TRD_LIST_PATH ANALYSIS_DIR MDD_MED_DATE_CSV_PATH PATIENT_JSON_DIR SLICED_PATIENT_JSON_DIR COHORT_PATH HF_HOME EMBEDDER_MODEL_PATH VLLM_MODEL_PATH ENDPOINTS_DIR ARTIFACTS_DIR NARRATIVES_DIR FEATURE_DATAFRAME_PATH EMBEDDINGS_DIR JUDGEMENTS_DIR RESULTS_DIR"
export RELAY_OPEN_KEYS="RESULTS_DIR EMBEDDINGS_DIR"
export RELAY_NAMES=1

# Physical paths (`pwd -P`), so a symlink on the way to the workspace cannot make
# the recipe and the workspace disagree about where they are.
_RELAY_LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd -P)"
RELAY_ROOT="$(cd "${_RELAY_LIB}/../.." && pwd -P)"
export RELAY_ROOT
export PYTHONPATH="${_RELAY_LIB}${PYTHONPATH:+:${PYTHONPATH}}"

# The recipe, workspace-relative: `bash <recipe>` under the relay, and a copy in
# Slurm's spool under a bare sbatch, where the job name is all there is.
# Never fatal under `set -e`: Slurm's spool may not be a directory a job can enter.
_relay_recipe="$( (cd "$(dirname "$0")" && pwd -P) 2>/dev/null || true)/$(basename "$0")"
case "${_relay_recipe}" in
    "${RELAY_ROOT}"/*) RELAY_STAGE="${_relay_recipe#"${RELAY_ROOT}"/}" ;;
    */slurm_script) RELAY_STAGE="${SLURM_JOB_NAME:-slurm_script}" ;;
    *) RELAY_STAGE="$(basename "$0")" ;;
esac
export RELAY_STAGE

_RELAY_LINE=""
_RELAY_ON_EXIT=""

relay_on_exit() {
    _RELAY_ON_EXIT="${_RELAY_ON_EXIT} $1"
}

_relay_exit() {
    local status=$?
    set +e +u
    if [ "$status" -ne 0 ]; then
        local sha
        sha="$(git -C "${RELAY_ROOT}" rev-parse --short HEAD 2>/dev/null)"
        printf 'RELAY: recipe %s failed: exit %s%s, checkout %s\n' \
            "${RELAY_STAGE}" "${status}" \
            "${_RELAY_LINE:+ after line ${_RELAY_LINE}}" "${sha:-unknown}" >&2
    fi
    # Each cleanup starts with `$?` set to the job's status, so one that asks
    # whether the job failed sees the answer and not the last command's.
    local fn
    for fn in ${_RELAY_ON_EXIT}; do
        (exit "$status")
        "$fn"
    done
    return "$status"
}

trap '_RELAY_LINE=$LINENO' ERR
trap _relay_exit EXIT
