#!/bin/bash
# GLM-5.2 int4 behind an OpenAI- and Anthropic-compatible HTTP gateway, on one
# node. Submit with `coli-up`, which exports LLM_REPO and picks the allocation.
#
#SBATCH --job-name=colibri_serve
# compute300-305 under c3_short, never c3: the two partitions are the same six
# nodes and differ only in time limit and depth of queue, and c3_short is far
# shallower. compute306 is reachable only through c3_accel and is not wanted
# here -- four A40s are worth 0.9% on this model, and the other three cards are
# each worth roughly 300 tok/s of aggregate throughput to somebody else.
#SBATCH --partition=c3_short
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
# PER JOB. Two generations of the chain overlap for the whole of a successor's
# load, and one pair of files would have both of them writing it -- with the
# incumbent's `COLIBRI-SERVE READY` sitting in the file the successor is being
# judged by. `coli-up` and the board resolve these names from the job id.
#SBATCH -o slurm_jobs/logs/colibri_serve_out-%j.txt
#SBATCH -e slurm_jobs/logs/colibri_serve_err-%j.txt
#
# --cpus-per-task, --mem and --time come from coli-up on the command line, where
# they override these directives. The defaults are in scripts/colibri-env.sh.
#SBATCH --cpus-per-task=80
#SBATCH --mem=800G
#SBATCH --time=0-08:00:00

set -uo pipefail

# ---------------------------------------------------------------- the checkout
# In a batch job $0 is a copy in the spool directory, so the script cannot find
# its own repository. coli-up exports LLM_REPO; a hand submission from the repo
# root gets SLURM_SUBMIT_DIR instead.
: "${LLM_REPO:=${SLURM_SUBMIT_DIR:-}}"
if [ -z "$LLM_REPO" ] || [ ! -r "$LLM_REPO/scripts/colibri-env.sh" ]; then
    echo "colibri_serve: LLM_REPO is not set and SLURM_SUBMIT_DIR ('${SLURM_SUBMIT_DIR:-}')" >&2
    echo "               is not this project's root. Submit with coli-up." >&2
    exit 1
fi
. "$LLM_REPO/scripts/colibri-env.sh"
coli_require engine || exit 1

# ------------------------------------------------------------------ the fence
# slurm_jobs/logs/** is exempt from the PHI fence on one stated understanding:
# the jobs print counts and durations, not text. COLI_DEBUG=1 tees every decoded
# token to stderr and COLI_DEBUG=2 adds the whole rendered prompt -- prior turns,
# tool results and all. Either would put session content into the one directory
# everything downstream has been told is safe to read. Refuse at the top rather
# than discover it in a log somebody has already opened.
if [ -n "${COLI_DEBUG:-}" ] && [ "${COLI_DEBUG}" != "0" ]; then
    echo "colibri_serve: COLI_DEBUG=${COLI_DEBUG} would tee prompts and generated" >&2
    echo "               text into slurm_jobs/logs, which is declared counts-only" >&2
    echo "               by ai-config/policy/phi.py. Refusing to serve." >&2
    echo "               To debug generation, run coli chat outside this job." >&2
    exit 1
fi
export COLI_DEBUG=0

# ------------------------------------------------------- who this generation is
MY_JOB="${SLURM_JOB_ID:-0}"
MY_NODE="${SLURMD_NODENAME:-$(hostname -s)}"
OUT_LOG="$(coli_log_out "$MY_JOB")"
ERR_LOG="$(coli_log_err "$MY_JOB")"
mkdir -p "$COLI_LOG_DIR" "$COLI_STATE_DIR"

# Every generation of the chain that is running and is not this one. There is at
# most one, and it is the one this generation is replacing.
coli_elders() {
    coli_jobs | awk -v me="$MY_JOB" '$2 == "RUNNING" && $1 != me { print $1 }'
}

# A GENERATION THAT STARTS AFTER SOMEBODY SAID STOP DOES NOT SERVE. `coli-down`
# writes the flag and then cancels, and a successor submitted in the gap between
# those two is a server that comes back an hour after it was told to go. The flag
# is cleared by `coli-up` and by nothing else.
if coli_chain_stopped; then
    echo "colibri_serve: the chain was stopped ($(cat "$COLI_STOP_FILE" 2>/dev/null))."
    echo "               This generation is standing down. 'coli-up' starts it again."
    exit 0
fi

coli_load_modules || exit 1

# colibri sizes its thread pool from the MACHINE (96 logical CPUs here), prints a
# note about physical cores and re-execs once to apply 48. Both halves are wrong
# for this box: inside an allocation that does not own the node, 96 is an
# oversubscription, and measured on this Xeon Gold 6342 tok/s rises monotonically
# past the physical core count -- 0.65 at 12 threads, 2.00 at 48, 2.75 at 92.
# `coli tune` independently retained the 92-thread baseline on a warm cache.
# So: take the number from the allocation, and let it exceed 48.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-88}"

# Not /tmp. It is a node-local RAM tmpfs, so a pidfile written on compute303 is
# invisible from compute300 and `coli stop` cannot find its own server.
export TMPDIR="${TMPDIR_SHARED:-/media/studies/ehr_study/analysis/mferguson/tmp}"
mkdir -p "$TMPDIR" "$COLI_SESSION_ROOT"

# Levers deliberately NOT set, each measured a loss on this workload:
#   XEXP=1  -12%      DRAFT=2  -11%      DRAFT=4  -19%
#   COLI_NUMA=1 is 8 points behind plain interleaving, and `coli doctor` still
#   recommends it. It is wrong here; the reason is at the exec line below.
#
# CUDA_DENSE is different: it has to be turned OFF rather than left alone, because
# `--gpu` turns it on by itself. Every variable the planner sets is a setdefault,
# so an explicit 0 in the environment wins. It measured 2.56 tok/s against 2.67.
export CUDA_DENSE=0

echo "colibri_serve job=${SLURM_JOB_ID} node=$(hostname) start=$(date -Is)"
echo "  model=$COLI_MODEL"
echo "  engine=$COLI_ENGINE"
echo "  cpus=${SLURM_CPUS_PER_TASK} omp=$OMP_NUM_THREADS mem=${SLURM_MEM_PER_NODE}M port=$COLI_PORT"
nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader
free -g | head -2

# Refuse a port somebody else already holds, rather than letting the bind error
# scroll past under a two-minute model load -- but RETRY FIRST, and that is the
# chain's doing. A generation can land on a node whose previous tenant is still
# being torn down, and a hand submission's correct refusal is a successor's
# spurious death. Sixty seconds, then refuse.
for _ in $(seq 1 30); do
    (exec 3<>"/dev/tcp/127.0.0.1/${COLI_PORT}") 2>/dev/null || break
    sleep 2
done
if (exec 3<>"/dev/tcp/127.0.0.1/${COLI_PORT}") 2>/dev/null; then
    echo "colibri_serve: something is still listening on 127.0.0.1:${COLI_PORT}" >&2
    echo "               on ${MY_NODE} after a minute of waiting. Pick another" >&2
    echo "               port with COLI_PORT, or find what holds that one." >&2
    exit 1
fi

# The readiness watcher. It runs beside the server because the server is the
# foreground process that keeps the allocation alive.
#
# A bound socket is not a loaded model and a loaded model is not a warm one, and
# both gaps are minutes wide. The gateway binds the port in milliseconds -- it is
# constructed before the engine, deliberately, so that a bad argument fails fast
# instead of after 429 GB -- and only then loads. Then, warm is a second thing
# again: the engine mmaps the checkpoint and faults expert slabs in DURING
# generation, so a cold replica decodes at 0.64 tok/s where a warm one does 2.88.
# Loading only halves, 101 s to 48 s; the rest of the cold-start cost is paid one
# token at a time by whoever asks first.
#
# So this connects as soon as it can -- which is at once, and the request then
# sits in the accept queue costing nothing until the engine is up -- and sends
# the first generation itself. WARMING means the request is lodged; READY means
# the model has answered one. The prompt is nine words of nothing and the reply is
# counted, never echoed.
#
# THREE SENTINELS NOW, NOT TWO, AND THE NEW ONE IS THE HANDOVER'S WHOLE SIGNAL.
# LOADED means the engine is up and this generation can answer -- it is what the
# generation being replaced waits for before it gives its node back. READY still
# means a real generation has come back, and under a chain it comes LATER than
# LOADED on purpose: see the hold below.
(
    for _ in $(seq 1 3600); do
        grep -q 'API listening on' "$ERR_LOG" 2>/dev/null && break
        sleep 2
    done
    if ! grep -q 'API listening on' "$ERR_LOG" 2>/dev/null; then
        echo "COLIBRI-SERVE FAILED reason=never-listened"
        exit 0
    fi
    echo "COLIBRI-SERVE LOADED host=${MY_NODE} port=${COLI_PORT} at=$(date -Is)"

    # THE WARM-UP WAITS FOR THE GENERATION IT IS REPLACING, AND THE REASON IS ONE
    # FILE. KV persistence is per CHECKPOINT -- `<model>/.coli_kv`, opened `r+b`
    # and written at absolute offsets computed from each process's own record
    # count -- so two live servers on the same model interleave their writes into
    # one file and neither reading survives it. A warm-up is a real generation and
    # therefore a real write. The engine READS that file at startup, which is
    # harmless, so the 68-minute load overlaps freely; only the first write has to
    # wait. What the wait costs is the turns the incumbent completed while this
    # one was loading: they are not in the prefix this generation read, so the
    # first turn after a handover re-prefills them.
    HELD=""
    while [ -n "$(coli_elders)" ]; do
        [ -z "$HELD" ] && echo "COLIBRI-SERVE HOLDING for=$(coli_elders | tr '\n' ' ')"
        HELD=1
        sleep 15
    done
    echo "COLIBRI-SERVE WARMING host=${MY_NODE} port=${COLI_PORT} at=$(date -Is)"
    python3 - "$COLI_PORT" "$COLI_MODEL_ID" <<'WARM'
import json, sys, time, urllib.request
port, model_id = sys.argv[1], sys.argv[2]
body = json.dumps({"model": model_id, "max_tokens": 16, "temperature": 0,
                   "messages": [{"role": "user",
                                 "content": "Reply with the single word: ready"}]}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                             data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=7200) as r:
        out = json.load(r)
except Exception as exc:
    print(f"COLIBRI-SERVE FAILED reason=warmup-{type(exc).__name__}", flush=True)
    sys.exit(0)
dt = time.time() - t0
u = out.get("usage") or {}
# Counts and durations. The completion itself is never printed: this watcher
# writes into slurm_jobs/logs, and that directory's exemption is the promise
# that nothing in it is text.
# Seconds, not a rate. This request was lodged in the accept queue before the
# engine existed, so its wall clock is mostly the 429 GB load and a tok/s
# computed from it would be a number that looks like a benchmark and is not one.
print("COLIBRI-SERVE READY prompt_tok=%s completion_tok=%s seconds_incl_load=%.1f"
      % (u.get("prompt_tokens", "?"), u.get("completion_tokens", "?"), dt), flush=True)
WARM
) &

# ------------------------------------------------------------------- the chain
#
# THE SERVER IS ALWAYS UP AND IT MOVES NODE RATHER THAN GOING AWAY.
#
# `COLI_CHAIN_LEAD_MIN` before this generation's walltime ends it submits the
# next one, which the scheduler puts wherever there is room; that one pins its
# 406.7 GB and says `COLIBRI-SERVE LOADED`; and only then does this one cancel
# itself and give its node back. There is no window in which nothing is serving,
# which is the whole of the ask.
#
# `--exclude` OF THIS NODE, AND IT IS NOT A PREFERENCE. Two 800 GB jobs do not
# fit on a 1 TB box, so an overlapping successor is somewhere else by arithmetic;
# naming it makes the scheduler say so at submission instead of pending. The
# price is a cold pin every hop -- 68 minutes -- where a same-node successor
# would re-read its checkpoint out of page cache at 21x that. Availability was
# chosen over the cheap hop deliberately, and the one case that gets the cheap
# hop back is the fallback below.
#
# Not `--dependency=afterany`, which is what the board's own chain uses: a
# dependency means the successor starts when this job STOPS, and a load that
# begins at the handover is an hour with no server. The board's generations cost
# nothing to start and colibri's cost 68 minutes; that one number is the whole
# difference between the two designs.
(
    [ "${COLI_CHAIN:-1}" = "1" ] || exit 0
    coli_chain_watch "$MY_JOB" "$MY_NODE"
) &

# numactl --interleave=all, which is worth 14% and which `coli tune` cannot find:
# its candidate set is thread counts and CUDA stream shapes only, so it cannot
# propose memory placement and retained a baseline 14% off the best available.
# 429 GB of warm experts against two 515 GB NUMA nodes -- binding to one socket
# fits, barely, and loses 6%.
#
# Foreground, not backgrounded: Slurm tears the allocation down when the last
# command exits, so the job must last exactly as long as the server.
# --gpu auto is not optional and its absence is silent. On Linux the launcher
# enables CUDA only when --gpu, --vram or --auto-tier says so: the auto-enable
# block that would do it for you is scoped to win32, and the engine then runs
# CPU-only on a node holding an idle A40 while `coli doctor` goes on reporting a
# 45.7 GB VRAM hot tier, because doctor plans and serve runs. Upstream calls this
# out as issue #121 -- "GPU benchmarks published by mistake" -- which is exactly
# what you get. --auto-tier is what applies the plan doctor prints.
SERVE=(
    python3 "$COLI_LAUNCHER" serve
    --model "$COLI_MODEL"
    --model-id "$COLI_MODEL_ID"
    --host 127.0.0.1
    --port "$COLI_PORT"
    --gpu auto
    --auto-tier
    --max-queue "${COLI_MAX_QUEUE:-8}"
    # An agent's first turn can spend a long time in prefill, and the default
    # 300 s admission timeout would answer it with a 429 before it was ever run.
    --queue-timeout "${COLI_QUEUE_TIMEOUT:-3600}"
)
SERVE+=(--ctx "${COLI_CTX:-131072}")
[ -n "${COLI_KV_SLOTS:-}" ] && SERVE+=(--kv-slots "$COLI_KV_SLOTS")
# Split on whitespace on purpose: this is the escape hatch for a flag nobody has
# needed yet, and quoting it would make it one argument.
# shellcheck disable=SC2206
[ -n "${COLI_SERVE_EXTRA:-}" ] && SERVE+=(${COLI_SERVE_EXTRA})

exec numactl --interleave=all "${SERVE[@]}"
