#!/bin/bash
# THE MTP A/B THAT P0 NEVER RAN. P0-STATUS.md finding 21 is the derivation; this
# is the measurement it asks for, and it is one job on one node.
#
# What P0 measured was not speculation. `MTP=1` is read in exactly one place and
# only `MTP=0` does anything, so `t7_mtp` re-measured the baseline; and DRAFT=2/4
# ran CPU-only, where the engine's auto path already gives draft=1, so those two
# are depth 2 and 4 against depth 1 rather than against off. Depth 1 under CUDA
# is the configuration nothing on disk has ever tried.
#
# The lever is COLI_CUDA_MTP=1 and it reaches the engine through TWO gates, which
# is why the arms are exactly this and not something simpler:
#   - resource_plan._auto_tune exports DRAFT=0 for a compute-bound plan -- which
#     `coli plan` says this is -- UNLESS COLI_CUDA_MTP=1 is in the environment,
#     in which case it leaves DRAFT alone deliberately (its own comment says so).
#   - the engine then resolves DRAFT=-1 as `has_mtp && (!cuda || cuda_mtp) ? 1:0`
#     at colibri.c:11173. Depth 1, not 3: the sweep in that comment has depth 1
#     at ~85% acceptance against ~44-62% at 2-3.
# So ONE variable moves between the arms. Nothing else in this file differs.
#
# The arms mirror the SERVED configuration, because that is the configuration the
# question is about: --gpu auto --auto-tier --ctx 131072, CUDA_DENSE=0, 80 CPUs,
# 800 GB, numactl --interleave=all. Every one of those is what colibri_serve.sbatch
# runs, and a lever measured on a different configuration answers about that one.
#
#SBATCH --job-name=p0t21mtp
#SBATCH --partition=c3_short
# compute303 because it is the node with room -- 10 of 96 CPUs and 108 GB held by
# a co-tenant at submission time, against 92/96 on 302 and 305 and a full 301.
# compute306 is left alone: it is the four-card node and worth ~300 tok/s of
# aggregate throughput to somebody else per spare card.
#SBATCH --nodelist=compute303
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=80
#SBATCH --mem=800G
#SBATCH --time=04:00:00
# Absolute, and outside the repository on purpose. slurm_jobs/logs is declared
# counts-only by ai-config/policy/phi.py; this job's per-configuration logs carry
# generated text, so they go to the scratch tree with the rest of the campaign.
#SBATCH -o /media/studies/ehr_study/analysis/mferguson/fleet-p0/logs/t21_mtp_%j.out
#SBATCH -e /media/studies/ehr_study/analysis/mferguson/fleet-p0/logs/t21_mtp_%j.err

set -uo pipefail

: "${LLM_REPO:=${SLURM_SUBMIT_DIR:-}}"
if [ -z "$LLM_REPO" ] || [ ! -r "$LLM_REPO/scripts/colibri-env.sh" ]; then
    echo "t21_mtp: submit this from the project root ($LLM_REPO is not it)." >&2
    exit 1
fi
. "$LLM_REPO/scripts/colibri-env.sh"
coli_require engine || exit 1
coli_load_modules || exit 1

# THE ONE WAY THIS JOB CAN LIE. COLI_CUDA_MTP inherited from the submitting shell
# would be in BOTH arms, and the off arm would silently be a second on arm -- the
# exact shape of the mistake finding 21 exists to correct. Refuse rather than
# measure it twice.
if [ -n "${COLI_CUDA_MTP:-}" ]; then
    echo "t21_mtp: COLI_CUDA_MTP=${COLI_CUDA_MTP} is set in the job environment." >&2
    echo "         Both arms would carry it and the off arm would be a duplicate" >&2
    echo "         of the on arm. Unset it and resubmit." >&2
    exit 1
fi
if [ -n "${DRAFT:-}" ]; then
    echo "t21_mtp: DRAFT=${DRAFT} is set and forces a depth on both arms," >&2
    echo "         which preempts the auto resolution this job measures." >&2
    exit 1
fi

B=/media/studies/ehr_study/analysis/mferguson
export MODEL="$COLI_MODEL"
export COLI_DIR
export OUTDIR="$B/fleet-p0/t21_mtp_${SLURM_JOB_ID:-manual}"
mkdir -p "$OUTDIR" "$B/fleet-p0/logs"
AB="$LLM_REPO/slurm_jobs/p0/coli_ab.sh"
[ -r "$AB" ] || { echo "t21_mtp: no coli_ab.sh at '$AB'" >&2; exit 1; }

# colibri sizes its thread pool from the MACHINE rather than the allocation and
# picks the physical core count. Both are wrong inside a job that does not own
# the node; take the number from the allocation, as the serve job does.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-80}"
export TMPDIR="$B/tmp"
mkdir -p "$TMPDIR"

# 131072 to match the served window. `coli run` allocates KV for the tokens it
# actually uses (np+ngen+draft+2), not for the window, so finding 22's 23.9 GB
# per slot does not apply here -- the window only sets the ceiling.
export CTX="$COLI_CTX"

{
echo "node=$(hostname) job=${SLURM_JOB_ID:-manual} start=$(date -Is)"
echo "cpus=${SLURM_CPUS_PER_TASK:-?} omp=$OMP_NUM_THREADS mem=${SLURM_MEM_PER_NODE:-?}M ctx=$CTX"
nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader
free -g | head -2
grep -E "^(Cached|MemFree|MemAvailable):" /proc/meminfo
} | tee "$OUTDIR/env.txt"

# The plan, on the record: the DRAFT line it prints is half of what this job is
# testing, and `limit  CPU expert tail and GPU compute` is the compute-bound
# classification that makes _auto_tune want DRAFT=0 in the first place.
python3 "$COLI_DIR/coli" plan --model "$MODEL" > "$OUTDIR/plan.txt" 2>&1
echo "--- coli plan ---"; cat "$OUTDIR/plan.txt"

# `coli_ab.sh` records tok/s and the expert hit rate. It does not record whether
# anything was drafted, and that is the one thing this job exists to establish:
# `[MTP] active ... (draft=N)` says what the engine resolved, and the
# `speculation:` line at colibri.c:8205 says what actually happened -- tokens per
# forward, and MTP acceptance as a percentage. A tok/s difference with draft=0 on
# both arms would be noise being read as a result.
# Anchored at column 0 and taking the LAST match, both deliberately: the engine
# tees the generated tokens into this same log, and an unanchored first match
# would happily quote the model back at itself if it ever wrote the word.
witness() {
    local log="$OUTDIR/cfg_$1.log"
    { grep -oE "^\[MTP\] .*\(draft=[0-9]+\)" "$log" | tail -1 | sed 's/^/    /'
      grep -oE "^speculation: .*"                "$log" | tail -1 | sed 's/^/    /'
    } 2>/dev/null | tee -a "$OUTDIR/timeline.txt"
}

run_arm() {   # run_arm <tag> [env assignments...]
    local tag=$1; shift
    WRAP="numactl --interleave=all" NGEN=128 \
        bash "$AB" "$tag" CUDA_DENSE=0 "$@" -- --gpu auto --auto-tier
    witness "$tag"
}

# ------------------------------------------------------------------ warm-up
# NOT A MEASUREMENT, and it is here because the first pin on this node reads
# 424.5 GB off the filer at 422 MB/s while every later one finds it in page cache
# at 9064 MB/s. A cold run decodes at 0.64 tok/s against a warm 2.88, so an arm
# that ran first would be measuring the Isilon.
run_arm warmup_discard

# ------------------------------------------------------------------- the A/B
# ABBAAB rather than ABABAB. A strict alternation puts every A before its paired
# B, so any monotone drift over the job -- a page cache still settling, a
# co-tenant arriving -- lands entirely on one arm. This ordering splits it.
run_arm r1_mtp_on  COLI_CUDA_MTP=1
run_arm r1_mtp_off
run_arm r2_mtp_off
run_arm r2_mtp_on  COLI_CUDA_MTP=1
run_arm r3_mtp_on  COLI_CUDA_MTP=1
run_arm r3_mtp_off

echo "=== done $(date -Is) ==="
echo "--- summary ---"
grep -E "^RESULT|draft=|^    speculation" "$OUTDIR/timeline.txt"
