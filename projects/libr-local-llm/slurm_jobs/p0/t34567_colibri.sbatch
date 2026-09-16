#!/bin/bash
#SBATCH --job-name=p0t3457
#SBATCH --partition=c3_short
#SBATCH --nodelist=compute302
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=92
#SBATCH --mem=950G
#SBATCH --time=09:00:00
#SBATCH --output=logs/t3457_%j.out
#SBATCH --error=logs/t3457_%j.err
#
# FLEET-BUILD.md §9 tests 3, 4, 5 and 7 on ONE A40.
# compute300-305 have a single A40 each; test 6 (1 vs 4 cards) is a separate
# job on compute306 under c3_accel, which is the only partition holding it.
#
# --nodelist=compute302 is load-bearing for test 3: the cold-load number is
# only cold on a node whose page cache has never seen the 429 GB.
set -uo pipefail

B=/media/studies/ehr_study/analysis/mferguson
export MODEL=$B/models/colibri/glm52_i4
# The build tree is `vendor/colibri-build` inside the Atlas checkout, not a clone in
# $HOME. Derived from the submit directory so any checkout finds its own, and refused
# outright when it is not there: a path that silently points at nothing turns "colibri
# moved" into "coli is broken".
ATLAS="$(git -C "${SLURM_SUBMIT_DIR:-$PWD}" rev-parse --show-toplevel 2>/dev/null)"
export COLI_DIR="$ATLAS/vendor/colibri-build/c"
[ -x "$COLI_DIR/coli" ] || { echo "no coli at '$COLI_DIR'; is this inside the Atlas"\
    " checkout, and has vendor/colibri-build been built?" >&2; exit 1; }
export OUTDIR=$B/fleet-p0/t3457_$SLURM_JOB_ID
mkdir -p "$OUTDIR"
AB=$B/fleet-p0/coli_ab.sh

module load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0 2>/dev/null

# P0 finding: colibri sizes its thread pool from the MACHINE (96 logical CPUs),
# not from the allocation, and re-execs once to apply it. Inside a job that does
# not own the node that is an oversubscription. Pin it from the allocation.
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-92}
export TMPDIR=$B/tmp

{
echo "node=$(hostname) job=$SLURM_JOB_ID start=$(date -Is)"
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS  cpus=$SLURM_CPUS_PER_TASK  mem=$SLURM_MEM_PER_NODE"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
free -g | head -2
echo "--- page cache before the cold load (this is what makes test 3 meaningful) ---"
grep -E "^(Cached|MemFree|MemAvailable):" /proc/meminfo
} | tee "$OUTDIR/env.txt"

python3 "$COLI_DIR/coli" plan --model "$MODEL" > "$OUTDIR/plan.txt" 2>&1
echo "--- coli plan ---"; cat "$OUTDIR/plan.txt"

# ---------------------------------------------------------------- test 3
# Two identical runs back to back. The first reads 429 GB off the Isilon into a
# cold page cache; the second finds it resident in 1 TB of RAM. The gap IS the
# answer to "does page cache kill the cold start".
NGEN=64 "$AB" t3_cold
echo "--- page cache after the cold load ---" | tee -a "$OUTDIR/timeline.txt"
grep -E "^Cached:" /proc/meminfo | tee -a "$OUTDIR/timeline.txt"
NGEN=64 "$AB" t3_warm

# ---------------------------------------------------------------- test 4
# coli tune writes the measured profile; run it after the model is warm so the
# tuner is not timing the filer.
echo "=== coli tune === $(date -Is)" | tee -a "$OUTDIR/timeline.txt"
( time python3 "$COLI_DIR/coli" tune --model "$MODEL" --tokens 96 --repeats 3 ) \
    > "$OUTDIR/tune.log" 2>&1
echo "tune rc=$? $(date -Is)" | tee -a "$OUTDIR/timeline.txt"
tail -40 "$OUTDIR/tune.log" | tee -a "$OUTDIR/timeline.txt"

# ---------------------------------------------------------------- test 5
# How much of the 122 ms per-token dense half does the GPU actually take.
# The variable is CUDA_DENSE, unprefixed -- colibri.c mixes prefixed and bare
# names and COLI_CUDA_DENSE is silently ignored.
NGEN=64 "$AB" t5_dense_off CUDA_DENSE=0
NGEN=64 "$AB" t5_dense_on  CUDA_DENSE=1

# ---------------------------------------------------------------- test 7
# The remaining tier-2 levers, one at a time against the same restored profile.
# 429 GB of warm experts against two 515 GB NUMA nodes: membind=0 only just
# fits (429 + 12 dense + 7 runtime = 448), which is why it is worth measuring
# against interleave rather than assumed.
NGEN=64 "$AB" t7_base
NGEN=64 "$AB" t7_xexp       XEXP=1
NGEN=64 "$AB" t7_numa       COLI_NUMA=1
WRAP="numactl --interleave=all" NGEN=64 "$AB" t7_interleave
WRAP="numactl --membind=0 --cpunodebind=0" NGEN=64 "$AB" t7_membind0
NGEN=64 "$AB" t7_draft2     DRAFT=2
NGEN=64 "$AB" t7_draft4     DRAFT=4
NGEN=64 "$AB" t7_mtp        MTP=1
NGEN=64 "$AB" t7_pipe_off   COLI_CUDA_PIPE=0

echo "=== all configurations done $(date -Is) ===" | tee -a "$OUTDIR/timeline.txt"
echo "--- summary ---"
grep "^RESULT" "$OUTDIR/timeline.txt"
