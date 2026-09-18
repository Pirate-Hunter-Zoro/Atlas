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

# Default allocation. 80 CPUs, well under the 92 partition cap: MaxCPUsPerNode is
# a PARTITION-wide cap, so one co-tenant holding 2 CPUs makes a 92-CPU request
# pend forever on "(Resources)" while every GPU on the node sits idle.
export COLI_CPUS="${COLI_CPUS:-80}"
# 800 GB, AND 950 IS NOT A CHOICE THIS PARTITION OFFERS. `sbatch --test-only`
# refuses anything above roughly 900 GB outright -- "Requested node configuration
# is not available", at submission, at every CPU count, measured across c3_short
# on 2026-09-18 -- so a default of 950 is a `coli-up` that cannot run and a chain
# whose successor is refused the moment it is needed. 800 GB is what the served
# job runs on: it pins the whole 406.7 GB plan and reports full residency. Lower
# it to schedule sooner; the engine mmaps the checkpoint and faults expert slabs
# in during generation, so less memory is not a failure, it is a slower tail.
export COLI_MEM_GB="${COLI_MEM_GB:-800}"
# 9 hours is the c3_short cap and the chain takes all of it. Every hop pays a
# cold pin on a new node (see the handover below), so the number of hops per day
# is the number to minimise and a shorter walltime buys nothing.
export COLI_HOURS="${COLI_HOURS:-9}"

# ---------------------------------------------------------------------- the chain
#
# THE SERVER IS ALWAYS UP, AND IT MOVES NODE RATHER THAN GOING AWAY. A generation
# lasts one walltime. `COLI_CHAIN_LEAD_MIN` before its own end it submits the next
# one, which lands on whichever node the scheduler has room on, pins 406.7 GB, and
# says so; only THEN does the incumbent cancel itself and give its node back. So
# there is no window in which nothing is serving, which is the whole ask.
#
# THE SUCCESSOR CANNOT LAND ON THE INCUMBENT'S NODE, and that is the price of the
# overlap. A warm page cache makes a second pin on the same node 21x faster
# (9064 MB/s against 422 MB/s cold, measured on compute300 on 2026-09-18 across a
# job teardown), but two 800 GB jobs do not fit on a 1 TB box, so an overlapping
# successor is always somewhere else and always cold. Availability was chosen over
# the cheap hop deliberately.
export COLI_CHAIN="${COLI_CHAIN:-1}"

# Two hours: a cold pin is 68 minutes measured, and the rest is queue wait and
# margin. Too short and the incumbent's walltime ends with the successor still
# reading off the filer, which is the one gap this exists to prevent.
export COLI_CHAIN_LEAD_MIN="${COLI_CHAIN_LEAD_MIN:-120}"

# How often a generation re-checks its own chain. A submission can be refused --
# a queue limit, a controller restart mid-sbatch -- and a chain that has quietly
# stopped being one is the failure nobody sees until the server goes away.
export COLI_CHAIN_EVERY="${COLI_CHAIN_EVERY:-300}"
# ...and how often it looks while a successor is actually loading, which is the
# window where seconds of staleness cost a gap in service.
export COLI_CHAIN_WATCH_EVERY="${COLI_CHAIN_WATCH_EVERY:-30}"

# Where the flag that ends a chain lives. Outside `slurm_jobs/logs`, which is
# declared counts-only, and outside git. Nothing else may spell this path.
export COLI_STATE_DIR="${COLI_STATE_DIR:-$LLM_REPO/slurm_jobs/state}"
export COLI_STOP_FILE="${COLI_STOP_FILE:-$COLI_STATE_DIR/chain-stopped}"

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

# --------------------------------------------------------- one generation's log
#
# PER JOB, AND THAT IS THE CHAIN'S DOING. Two generations overlap for the whole
# of a successor's load, and a single pair of files would have both of them
# writing it -- with the incumbent's `COLIBRI-SERVE READY` still in the file the
# successor is being judged by, which reads as a warm server that has not
# finished pinning. The fixed names are still answered for a job submitted by an
# older copy of these scripts, so a board does not go blind on one.
coli_log_out() { printf '%s/colibri_serve_out-%s.txt\n' "$COLI_LOG_DIR" "$1"; }
coli_log_err() { printf '%s/colibri_serve_err-%s.txt\n' "$COLI_LOG_DIR" "$1"; }

# ------------------------------------------------------------------- the queue
# Every generation Slurm knows about, newest last: `id state node reason left`.
# `|| true` on both: every caller runs under `set -e` or `pipefail` or both, and
# a controller that is briefly unreachable must read as "ask again" rather than
# kill the script that asked.
coli_jobs() {
    squeue -u "$USER" -n "$COLI_JOB_NAME" -h -o '%i %T %N %r %L' 2>/dev/null || true
}

# Seconds of walltime left on a job, or empty where Slurm does not say a number.
# The spellings are Slurm's own: `d-hh:mm:ss`, `hh:mm:ss`, `mm:ss`, and a bare
# number is minutes. UNLIMITED and INVALID are not numbers and are not zero.
coli_seconds_left() {
    { squeue -j "$1" -h -o '%L' 2>/dev/null || true; } | awk '
        { s=$1
          if (s !~ /^[0-9]/) exit
          d = 0
          if (index(s, "-")) { d = substr(s, 1, index(s, "-") - 1) + 0
                               s = substr(s, index(s, "-") + 1) }
          n = split(s, p, ":")
          if (n > 3) exit
          t = 0
          for (i = 1; i <= n; i++) t = t * 60 + p[i]
          if (n == 1) t *= 60
          printf "%d\n", d * 86400 + t }'
}

# ------------------------------------------------------- the end of a chain
# The only thing that ends one is something that meant to. `coli-down` writes
# this and then cancels; `coli-up` clears it, because asking for a server is
# asking for the chain back.
coli_chain_stopped() { [ -e "$COLI_STOP_FILE" ]; }
coli_mark_stopped() {
    mkdir -p "$COLI_STATE_DIR"
    printf '%s %s\n' "$(date -Is)" "${1:-}" > "$COLI_STOP_FILE"
}
coli_clear_stopped() { rm -f "$COLI_STOP_FILE"; }

# ------------------------------------------------------------ submit one of them
#
# THE ONE PLACE A GENERATION IS SUBMITTED, because there are now two callers --
# `coli-up` for the first and the running generation for every one after it --
# and a successor submitted with different resources is a chain that quietly
# degrades. Extra sbatch arguments (a `--exclude`) come first; the job id is
# printed on success and nothing on failure.
#
# The SLURM_* scrub is load-bearing in BOTH callers. sbatch inherits the
# submitting environment's SLURM_* and those OVERRIDE the #SBATCH directives, so
# a successor submitted from inside a running generation would otherwise inherit
# that generation's job id, node list and step context.
coli_submit() {
    (
        for v in $(env | grep -oE '^SLURM_[A-Z_0-9]+' || true); do unset "$v"; done
        sbatch --parsable \
               --chdir="$LLM_REPO" \
               --job-name="$COLI_JOB_NAME" \
               --cpus-per-task="$COLI_CPUS" \
               --mem="${COLI_MEM_GB}G" \
               --time="${COLI_HOURS}:00:00" \
               --output="$(coli_log_out %j)" \
               --error="$(coli_log_err %j)" \
               --export="ALL,LLM_REPO=${LLM_REPO},COLI_PORT=${COLI_PORT},COLI_MODEL=${COLI_MODEL},COLI_MODEL_ID=${COLI_MODEL_ID},COLI_CHAIN=${COLI_CHAIN}" \
               "$@" \
               "$LLM_REPO/slurm_jobs/colibri_serve.sbatch"
    )
}

# ------------------------------------------------- which generation to talk to
#
# A CHAIN MEANS TWO SERVERS ARE RUNNING FOR AN HOUR AT A TIME, and `head -1` of
# `squeue` picks between them by luck. The one to use is the one that can answer:
# WARM beats loading, and between two warm ones the one with more walltime left
# is the one that is not about to hand over. A first server that has not warmed
# yet is still better than nothing, so it is the fallback rather than a refusal.
coli_serving_job() {
    local job secs best="" best_left=-1 warm="" warm_left=-1
    for job in $(coli_jobs | awk '$2 == "RUNNING" { print $1 }'); do
        secs="$(coli_seconds_left "$job")"
        [ -n "$secs" ] || secs=0
        if grep -q 'COLIBRI-SERVE READY' "$(coli_log_out "$job")" 2>/dev/null; then
            if [ "$secs" -gt "$warm_left" ]; then warm_left="$secs"; warm="$job"; fi
        fi
        if [ "$secs" -gt "$best_left" ]; then best_left="$secs"; best="$job"; fi
    done
    printf '%s' "${warm:-$best}"
}

# The generation that is loading behind the one serving, if there is one -- which
# is what makes "this server goes away in twenty minutes" a thing anybody can say.
coli_successor_job() {
    local serving="$1" job
    for job in $(coli_jobs | awk '{ print $1 }'); do
        [ "$job" = "$serving" ] && continue
        printf '%s' "$job"
        return 0
    done
    return 0
}
