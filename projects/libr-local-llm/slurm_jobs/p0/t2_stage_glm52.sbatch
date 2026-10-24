#!/bin/bash
#SBATCH --job-name=p0t2_stage
#SBATCH --partition=c3_short
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=logs/t2_stage_%j.out
#SBATCH --error=logs/t2_stage_%j.err
B=/media/studies/ehr_study/analysis/mferguson
DEST=$B/models/colibri/glm52_i4
export TMPDIR=$B/tmp
export HF_HUB_ENABLE_HF_TRANSFER=0
mkdir -p "$DEST"
echo "stage start $(date -Is) on $(hostname) job=$SLURM_JOB_ID"
S=$(date +%s)
$B/venvs/hfdl/bin/hf download mastouri/GLM-5.2-colibri-int4-g64-with-int8-mtp \
  --local-dir "$DEST" --max-workers 16
RC=$?
E=$(date +%s)
echo "stage end $(date -Is) rc=$RC DOWNLOAD_SECONDS=$((E-S))"
BYTES=$(du -sb "$DEST" | cut -f1)
echo "STAGED_BYTES=$BYTES  GB=$(echo "scale=1; $BYTES/1000000000" | bc)"
echo "MB_PER_S=$(echo "scale=1; $BYTES/1000000/($E-$S)" | bc)"
