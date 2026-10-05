#!/bin/bash
# ---------------------------------------------------------------------------
# relay_trap.sh -- what a failed job says about itself, behind RELAY:.
#
#     source slurm_jobs/lib/job_env.sh        # which sources this, first
#
# SOURCED BY job_env.sh, so every recipe has it. On a non-zero exit the job prints
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

# NO FILE IS NAMED HERE, not even by basename: a session's WAV and every artifact
# beside it carry the participant ID (job_env.sh, `session_stem`). A path is its
# location's key and its extension, and nothing under `phi/` is opened to count.
export RELAY_PATH_KEYS="PSYCH_ASR_DATA TORCH_HOME NLTK_DATA HF_HOME"
export RELAY_OPEN_KEYS=""
export RELAY_NAMES=0

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
    local fn
    for fn in ${_RELAY_ON_EXIT}; do
        "$fn"
    done
    return "$status"
}

trap '_RELAY_LINE=$LINENO' ERR
trap _relay_exit EXIT
