# colibri-env.sh -- the one place that answers "where is colibri, what does it
# serve, and where does its output land". Sourced by bin/coli-build, bin/coli-up,
# bin/coli-code, bin/coli-ask, bin/coli-down and slurm_jobs/colibri_serve.sbatch.
#
# One file rather than the same derivation in six, because the derivation has a
# trap in it: `git -C "$(dirname "${BASH_SOURCE[0]}")"` resolves a RELATIVE
# directory against wherever the caller happens to be standing, so the same
# script invoked as `bash scripts/x.sh` and `bash /abs/path/scripts/x.sh` can
# reach different answers -- or an empty one, silently. This resolves to an
# absolute path before anything else looks at it.
#
# Nothing here executes. Every caller sources it and then decides what to do.

# --------------------------------------------------------------- where we are
#
# In a Slurm batch job $0 is a COPY of the script in the spool directory, so
# neither BASH_SOURCE nor $0 finds the checkout. coli-up therefore exports
# LLM_REPO into the job's environment, and this honours it when it is set.
if [ -z "${LLM_REPO:-}" ]; then
    _ce_self="${BASH_SOURCE[0]:-$0}"
    LLM_REPO="$(cd "$(dirname "$(dirname "$_ce_self")")" && pwd -P)"
fi
export LLM_REPO

# The build tree is a submodule of the Atlas checkout this project lives in, not
# a loose clone in $HOME. Ask git rather than counting directories upward, so a
# checkout anywhere builds and runs against its own vendored engine.
ATLAS_ROOT="$(git -C "$LLM_REPO" rev-parse --show-toplevel 2>/dev/null || true)"
export ATLAS_ROOT

# vendor/colibri-build is the pinned tree to BUILD from; vendor/colibri is the
# read-only checkout the daily colibri-pull timer fast-forwards. Building in the
# second would leave objects in a tree the timer expects clean.
export COLI_DIR="${COLI_DIR:-$ATLAS_ROOT/vendor/colibri-build/c}"
export COLI_LAUNCHER="$COLI_DIR/coli"
export COLI_ENGINE="$COLI_DIR/colibri"

# ------------------------------------------------------------------ the model
#
# 429.3 GB of data occupying 498.5 GB of the share (the gap is allocation across
# 142 shards; plan free space against the larger number).
export COLI_MODEL="${COLI_MODEL:-/media/studies/ehr_study/analysis/mferguson/models/colibri/glm52_i4}"
export COLI_MODEL_ID="${COLI_MODEL_ID:-glm-5.2-colibri}"

# ------------------------------------------------------------------ the server
export COLI_JOB_NAME="${COLI_JOB_NAME:-colibri_serve}"
export COLI_PORT="${COLI_PORT:-8000}"

# The family's default context is 4096, which is smaller than a coding agent's
# system prompt -- the agent would be truncated before its first word. Raising it
# is nearly free on this box: from 4096 to 131072 the plan's runtime allocation
# grows 7.3 GB to 45.0 GB and nothing else moves. Warm experts stay at 371.7 GB,
# the VRAM hot tier stays at 45.7 GB, projected residency stays at 100%.
export COLI_CTX="${COLI_CTX:-131072}"

# Default allocation. 88 CPUs rather than the 92 partition cap: MaxCPUsPerNode is
# a PARTITION-wide cap, so one co-tenant holding 2 CPUs makes a 92-CPU request
# pend forever on "(Resources)" while every GPU on the node sits idle.
export COLI_CPUS="${COLI_CPUS:-88}"
# 950 GB holds all 429 GB of experts warm in page cache. Lower it to schedule
# sooner: the engine mmaps the checkpoint and faults expert slabs in during
# generation, so less memory is not a failure, it is a slower tail.
export COLI_MEM_GB="${COLI_MEM_GB:-950}"
export COLI_HOURS="${COLI_HOURS:-8}"

# ----------------------------------------------------- where the transcript goes
#
# THE FENCE, and it is the reason this variable exists rather than a default
# somewhere in a client's own config.
#
# A driver that can read `phi` produces a transcript that quotes `phi`. The
# model's reasoning is session content the moment it repeats a line of the
# session back, so it cannot live in the two places a coding agent would put it
# by default: not the job log (`slurm_jobs/logs/**` is exempt from the PHI fence
# on the stated understanding that jobs print COUNTS AND DURATIONS, NOT TEXT --
# see ai-config/policy/phi.py), and not `~/.claude` or `~/.local/share`, which a
# hosted assistant reads freely all day.
#
# So it goes behind the fence that already exists, by name: everything under a
# directory called `phi/` is refused, at any depth, by the rule that survived the
# data moving twice. Nothing new had to be invented and nothing new can rot.
export COLI_SESSION_ROOT="${COLI_SESSION_ROOT:-/media/studies/ehr_study/analysis/mferguson/colibri-sessions/phi}"

# -------------------------------------------------------------------- modules
# `coli` will not run under the node's python3: it is 3.9 and the launcher uses
# dataclass(slots=True), which fails with a bare TypeError naming no version.
coli_load_modules() {
    module purge >/dev/null 2>&1 || true
    module load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0 >/dev/null 2>&1 || {
        echo "colibri: could not load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0" >&2
        return 1
    }
    export CUDA_HOME="${EBROOTCUDA:-}"
    # pip's writability probe is os.access(), and on this filer os.access lies:
    # it returns False for a directory the same process then writes to without
    # error, because the POSIX mode bits are synthesised lossily from the real
    # NFSv4 ACL. pip concludes the environment is unwritable and installs into
    # ~/.local, which then SHADOWS the environment at import time. This flips
    # site.ENABLE_USER_SITE off, which pip checks ahead of the probe, and stops
    # the shadowing at run time as well.
    export PYTHONNOUSERSITE=1
}

# Refuse by name rather than failing later against a path that resolves to
# nothing. `$want` is "engine" when a built binary is required.
coli_require() {
    local want="${1:-engine}"
    if [ -z "$ATLAS_ROOT" ]; then
        echo "colibri: $LLM_REPO is not inside a git checkout, so the vendored" >&2
        echo "         engine cannot be located. Run this from a checkout." >&2
        return 1
    fi
    if [ ! -x "$COLI_LAUNCHER" ]; then
        echo "colibri: no launcher at '$COLI_LAUNCHER'." >&2
        echo "         Is vendor/colibri-build checked out? git submodule update --init" >&2
        return 1
    fi
    if [ "$want" = engine ] && [ ! -x "$COLI_ENGINE" ]; then
        echo "colibri: the engine is not built. '$COLI_ENGINE' does not exist." >&2
        echo "         Build it:  coli-build" >&2
        return 1
    fi
    return 0
}

# The serve job's own log DOES go in slurm_jobs/logs, and it keeps the bargain
# by enforcement rather than by hope. With COLI_DEBUG unset the gateway writes
# only its banner, the resolved plan, and one access line per request -- a peer,
# a method and a status, no body. COLI_DEBUG=1 tees every decoded token to
# stderr and COLI_DEBUG=2 adds the whole rendered prompt, which would put
# session text straight into the one directory the fence exempts. The serve job
# refuses to start when it is set; see slurm_jobs/colibri_serve.sbatch.
export COLI_LOG_DIR="${COLI_LOG_DIR:-$LLM_REPO/slurm_jobs/logs}"
