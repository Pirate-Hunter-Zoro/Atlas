#!/bin/bash
#SBATCH --job-name=p0t4b
#SBATCH --partition=c3_short
#SBATCH --nodelist=compute303
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=92
#SBATCH --mem=950G
#SBATCH --time=09:00:00
#SBATCH --output=logs/t4b_omp_%j.out
#SBATCH --error=logs/t4b_omp_%j.err
#
# FLEET-BUILD.md §9 test 4, the OpenMP half -- split out because the first pass
# got it wrong in a way worth recording.
#
# P0 finding 4 said "pin OMP_NUM_THREADS from SLURM_CPUS_PER_TASK". That is only
# half right. These nodes are 96 LOGICAL CPUs over 48 PHYSICAL cores, and
# colibri's own measured table (c/coli, the OMP_NUM_THREADS block) shows decode
# FALLING from 2.90 to 2.06 tok/s when the thread count goes from physical to
# logical -- two SMT siblings share one AVX-512 unit and contend for it.
# --cpus-per-task=92 therefore hands colibri a number that is 1.9x the physical
# core count. This sweep measures the actual curve on OUR hardware.
set -uo pipefail

B=/media/studies/ehr_study/analysis/mferguson
export MODEL=$B/models/colibri/glm52_i4
export COLI_DIR=$HOME/colibri-build/c
export OUTDIR=$B/fleet-p0/t4b_omp_$SLURM_JOB_ID
mkdir -p "$OUTDIR"
AB=$B/fleet-p0/coli_ab.sh

module load CUDA/13.1.0 GCC/13.3.0 Python/3.12.3-GCCcore-13.3.0 2>/dev/null
export TMPDIR=$B/tmp

{
echo "node=$(hostname) job=$SLURM_JOB_ID start=$(date -Is)"
lscpu | grep -E "^CPU\(s\)|Thread|Core\(s\) per socket|Socket"
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
grep -E "^Cached:" /proc/meminfo
} | tee "$OUTDIR/env.txt"

# One warm-up load so the sweep measures threads, not the filer. Its own number
# is the cold-load figure for this node and is kept.
OMP_NUM_THREADS=48 NGEN=64 "$AB" warmup_cold

for T in 12 24 36 48 64 92; do
  OMP_NUM_THREADS=$T NGEN=96 "$AB" omp_$T OMP_NUM_THREADS=$T
done

# and the same physical-core count with colibri's own tuner left switched on,
# to check the re-exec is not quietly undoing the pin
NGEN=96 "$AB" omp_selftuned COLI_NO_OMP_TUNE=0

echo "=== done $(date -Is) ==="
grep "^RESULT" "$OUTDIR/timeline.txt"
