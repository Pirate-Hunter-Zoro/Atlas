#!/bin/bash
#SBATCH --job-name=preflight_models
#SBATCH --partition=c3_short
#SBATCH --time=0-00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH -o slurm_jobs/logs/preflight_models_%j_out.txt
#SBATCH -e slurm_jobs/logs/preflight_models_%j_err.txt

# Check every staged model asset from a compute node, by file and by an offline load on
# CPU, and count the inbox WAVs. The same check scripts/stage_models.sh ends with.
#
#     board job -- slurm_jobs/preflight_models.sbatch
#
# Prints one RELAY: line per asset that is not ok and a final RELAY: summary, and fails
# unless every asset is ok and the inbox holds exactly one WAV. No GPU.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

activate_env asr_env

python -m psych_asr.cli.preflight_models --load
