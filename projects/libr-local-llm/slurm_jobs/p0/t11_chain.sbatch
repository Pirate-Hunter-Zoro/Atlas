#!/bin/bash
#SBATCH --job-name=p0t11
#SBATCH --partition=c3_short
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/t11_%j.out
#SBATCH --error=logs/t11_%j.err
#SBATCH --signal=B:TERM@30
W=/media/studies/ehr_study/analysis/mferguson/fleet-p0
GEN=${GEN:-1}
ME=$SLURM_JOB_ID
echo "gen=$GEN job=$ME node=$(hostname) start=$(date +%s)"

on_term() {
  echo "gen=$GEN job=$ME caught SIGTERM at $(date +%s)"
  exit 0
}
trap on_term TERM

if [ "$GEN" -lt 3 ]; then
  NEXT=$((GEN+1))
  SUCC=$(
    for v in $(env | grep -oE '^SLURM_[A-Za-z0-9_]+'); do unset "$v"; done
    export GEN=$NEXT
    sbatch --parsable --dependency=afterany:$ME --export=ALL,GEN=$NEXT \
           --chdir="$W" "$W/t11_chain.sbatch"
  )
  echo "gen=$GEN job=$ME submitted successor [$SUCC] with afterany:$ME"
else
  echo "gen=$GEN job=$ME is the last generation; no successor"
fi

for i in $(seq 1 200); do echo "gen=$GEN job=$ME tick $i $(date +%s)"; sleep 3 & wait $!; done
