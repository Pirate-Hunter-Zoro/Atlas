#!/bin/bash
#SBATCH --job-name=p0t5b
#SBATCH --partition=c3_short
#SBATCH --nodelist=compute302
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=92
#SBATCH --mem=950G
#SBATCH --time=02:00:00
#SBATCH --output=logs/t5b_%j.out
#SBATCH --error=logs/t5b_%j.err
#
# Test 5 re-run, plus a repeat of the one lever that actually won.
#
# The first pass of test 5 measured nothing: CUDA_DENSE=1 exits immediately with
# "CUDA_DENSE requires COLI_CUDA=1". Both halves of the A/B now carry COLI_CUDA=1
# so the only thing that differs is the flag under test.
#
# compute302 is pinned because it already holds the 429 GB in page cache, so
# these runs measure the knob and not the filer. Order is ALTERNATED rather than
# blocked, because the first pass swept ascending and cannot separate the knob
# from a warming cache.
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
export OUTDIR=$B/fleet-p0/t5b_$SLURM_JOB_ID
mkdir -p "$OUTDIR"
AB=$B/fleet-p0/coli_ab.sh
module load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0 2>/dev/null
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-92}
export TMPDIR=$B/tmp
{ echo "node=$(hostname) job=$SLURM_JOB_ID start=$(date -Is)"; grep -E "^Cached:" /proc/meminfo; } | tee "$OUTDIR/env.txt"

for R in 1 2 3; do
  NGEN=64 "$AB" r${R}_dense_off  COLI_CUDA=1 CUDA_DENSE=0
  NGEN=64 "$AB" r${R}_dense_on   COLI_CUDA=1 CUDA_DENSE=1
  NGEN=64 "$AB" r${R}_base
  WRAP="numactl --interleave=all" NGEN=64 "$AB" r${R}_interleave
done
echo "=== done $(date -Is) ==="; grep "^RESULT" "$OUTDIR/timeline.txt"
