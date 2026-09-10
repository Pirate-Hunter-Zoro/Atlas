#!/bin/bash
#SBATCH --job-name=p0t6
#SBATCH --partition=c3_accel
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=88
#SBATCH --mem=900G
#SBATCH --time=04:00:00
#SBATCH --output=logs/t6_%j.out
#SBATCH --error=logs/t6_%j.err
#
# FLEET-BUILD.md §9 test 6 -- one A40 against four, the question §2.2 says pass
# two closed prematurely.
#
# c3_accel, not c3_short: compute306 is the only node with four cards and
# c3_accel is the only partition that contains it (P0 finding 2). It reads as
# preemptible at PriorityTier=10 with PreemptMode=SUSPEND, but partition-priority
# preemption needs a HIGHER tier partition on the same node and there is none.
#
# 88 CPUs, not 92. MaxCPUsPerNode=92 is a cap on what the PARTITION may hold on
# that node, not on what one job may ask for: a co-tenant sitting on compute306
# with 2 CPUs lowers your own ceiling to 90, and a 92-CPU request then pends on
# (Resources) forever while all four GPUs sit idle. Ask for a little less than
# the cap on the shared node.
set -uo pipefail
B=/media/studies/ehr_study/analysis/mferguson
export MODEL=$B/models/colibri/glm52_i4
export COLI_DIR=$HOME/colibri-build/c
export OUTDIR=$B/fleet-p0/t6_$SLURM_JOB_ID
mkdir -p "$OUTDIR"
AB=$B/fleet-p0/coli_ab.sh
module load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0 2>/dev/null
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-92}
export TMPDIR=$B/tmp
{
echo "node=$(hostname) job=$SLURM_JOB_ID start=$(date -Is)"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
grep -E "^Cached:" /proc/meminfo
} | tee "$OUTDIR/env.txt"

python3 "$COLI_DIR/coli" plan --model "$MODEL" > "$OUTDIR/plan_4gpu.txt" 2>&1
cat "$OUTDIR/plan_4gpu.txt"

# compute306 has never read this checkpoint: the first run is a second, independent
# cold-load measurement, on a node whose page cache is someone else's.
NGEN=64 "$AB" cold_4gpu

# Alternate 1 card and 4 so a warming cache cannot masquerade as a GPU effect.
# --interleave=all is carried on every run: it won test 7 by +14% and is the
# configuration we would actually ship.
for R in 1 2 3; do
  WRAP="numactl --interleave=all" NGEN=64 "$AB" r${R}_gpu1 -- --gpu 0
  WRAP="numactl --interleave=all" NGEN=64 "$AB" r${R}_gpu4 -- --gpu 0,1,2,3
done
echo "=== done $(date -Is) ==="; grep "^RESULT" "$OUTDIR/timeline.txt"
