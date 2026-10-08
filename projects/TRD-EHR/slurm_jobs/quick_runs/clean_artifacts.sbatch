#!/bin/bash
#SBATCH --job-name=clean_artifacts
#SBATCH --partition=c3_accel
#SBATCH --time=7-00:00:00
#SBATCH --ntasks=1
#SBATCH -o slurm_jobs/quick_runs/logs/clean_artifacts_out.txt
#SBATCH -e slurm_jobs/quick_runs/logs/clean_artifacts_err.txt

# A failure prints its RELAY: lines (slurm_jobs/lib/relay_trap.sh).
source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"

cd /media/studies/ehr_study/analysis/mferguson/
echo "Removing artifacts and json..."
rm -rf patient_json/ && rm -rf sliced_patient_json/ && rm -rf artifacts/ && rm -f ./test_patient_ids.txt
echo "Artifacts and json removed!"