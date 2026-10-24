#!/bin/bash
# ---------------------------------------------------------------------------
# relay_trap.sh -- what a failed job says about itself, behind RELAY:.
#
# One copy for every subject. A subject's `slurm_jobs/lib/relay_trap.sh` is a
# two-line shim that sources this, and a recipe sources the shim first:
#
#     set -e
#     source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"
#
# On a non-zero exit the job prints
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
# UNDER THE RELAY'S WRAPPER (`jobs.wrapper`, RELAY_WRAPPED=1) the wrapper has
# already set RELAY_ROOT, RELAY_STAGE, RELAY_CONFIG and PYTHONPATH, and prints
# the failure line itself, so a recipe with no `source` line is fingerprinted
# too. Here the trap then adds only `RELAY: recipe <recipe> stopped after line
# <n>`, where it knows the line.
#
# What a path may say is the subject's tutorboard.json `relay.fingerprint`
# (`relay_hook.config`): RELAY_CONFIG under the wrapper, the file otherwise.
#
# THE STATUS IS THE JOB'S. The relay's wrapper records the exit code after this
# script returns, so the trap changes nothing about it and writes no file. A
# recipe with a cleanup of its own hands it to `relay_on_exit <function>`: a
# second `trap ... EXIT` would replace this one.
#
# Safe under `set -u`, and on bash 3.2.
# ---------------------------------------------------------------------------

# Physical paths (`pwd -P`), so a symlink on the way to the subject cannot make
# the recipe and the subject disagree about where they are. The subject is two
# levels above the shim that sourced this.
_RELAY_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -z "${RELAY_ROOT:-}" ]; then
    if [ -n "${BASH_SOURCE[1]:-}" ]; then
        RELAY_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")/../.." && pwd -P)"
    else
        RELAY_ROOT="$(pwd -P)"
    fi
fi
export RELAY_ROOT
case ":${PYTHONPATH:-}:" in
    *":${_RELAY_LIB}:"*) ;;
    *) export PYTHONPATH="${_RELAY_LIB}${PYTHONPATH:+:${PYTHONPATH}}" ;;
esac

# The recipe, subject-relative: `bash <recipe>` under the relay, and a copy in
# Slurm's spool under a bare sbatch, where the job name is all there is.
# Never fatal under `set -e`: Slurm's spool may not be a directory a job can enter.
if [ -z "${RELAY_STAGE:-}" ]; then
    _relay_recipe="$( (cd "$(dirname "$0")" && pwd -P) 2>/dev/null || true)/$(basename "$0")"
    case "${_relay_recipe}" in
        "${RELAY_ROOT}"/*) RELAY_STAGE="${_relay_recipe#"${RELAY_ROOT}"/}" ;;
        */slurm_script) RELAY_STAGE="${SLURM_JOB_NAME:-slurm_script}" ;;
        *) RELAY_STAGE="$(basename "$0")" ;;
    esac
fi
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
        if [ "${RELAY_WRAPPED:-}" = 1 ]; then
            if [ -n "${_RELAY_LINE}" ]; then
                printf 'RELAY: recipe %s stopped after line %s\n' \
                    "${RELAY_STAGE}" "${_RELAY_LINE}" >&2
            fi
        else
            local sha
            sha="$(git -C "${RELAY_ROOT}" rev-parse --short HEAD 2>/dev/null)"
            printf 'RELAY: recipe %s failed: exit %s%s, checkout %s\n' \
                "${RELAY_STAGE}" "${status}" \
                "${_RELAY_LINE:+ after line ${_RELAY_LINE}}" "${sha:-unknown}" >&2
        fi
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
