#!/bin/bash
#SBATCH --job-name=stage1a_transcribe
#SBATCH --partition=c3_accel
#SBATCH --time=0-02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -o slurm_jobs/logs/stage1a_transcribe_out.txt
#SBATCH -e slurm_jobs/logs/stage1a_transcribe_err.txt
#SBATCH --gres=gpu:1

# Stage 1a-i: ONE typist, audio in, untimed words out -> <stem>.<typist>.asr.json
#
#     sbatch slurm_jobs/stage1a_transcribe.sbatch large-v3
#     sbatch slurm_jobs/stage1a_transcribe.sbatch parakeet
#
# THE ENV FOLLOWS THE TYPIST, which is the whole reason this is a separate job from the
# alignment that used to sit in the same function. faster-whisper is asr_env; Parakeet and
# Canary are nemo_env, the env the Sortformer arms already run in. Nothing imports whisperx
# and NeMo into one process, so the two passes pass a FILE between them instead -- the same
# seam the RTTM cuts between Stage 1b and Stage 1c.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

# INPUT_DIR comes from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default ~/phi/PSYCH-ASR).
TYPIST="${1:-large-v3}"

case "${TYPIST}" in
    large-v3|large-v3-turbo) ENV_NAME=asr_env ;;
    parakeet|canary)         ENV_NAME=nemo_env ;;
    *) echo "Unknown typist ${TYPIST}: large-v3, large-v3-turbo, parakeet, canary" >&2; exit 1 ;;
esac

activate_env "${ENV_NAME}"
report_gpu

AUDIO_PATH="$(sole_wav "${INPUT_DIR}")"
echo "Transcribing $(basename "${AUDIO_PATH}") with ${TYPIST}"
python -m psych_asr.cli.transcribe "${AUDIO_PATH}" --typist "${TYPIST}"
