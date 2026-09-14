#!/bin/bash
#SBATCH --job-name=stage1a_align
#SBATCH --partition=c3_accel
#SBATCH --time=0-02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -o slurm_jobs/logs/stage1a_align_out.txt
#SBATCH -e slurm_jobs/logs/stage1a_align_err.txt
#SBATCH --gres=gpu:1

# Stage 1a-ii: ONE stopwatch re-times ONE typist's words
#   -> <stem>.<typist>+<stopwatch>.aligned.json
#
#     sbatch slurm_jobs/stage1a_align.sbatch large-v3
#     sbatch slurm_jobs/stage1a_align.sbatch parakeet wav2vec2-large
#
# ALWAYS asr_env, whatever typed the words: forced alignment is torchaudio and whisperx and
# never NeMo. That is what the seam buys -- a NeMo typist's output arrives as a file and the
# stopwatch never learns where it came from.
#
# TORCH_HOME must be exported (activate_env does it): the alignment bundle comes from
# download.pytorch.org, not the Hugging Face Hub, so HF_HUB_OFFLINE does not cover it and an
# unstaged bundle hangs on a node with no outbound internet rather than failing.
#
# Submit FROM THE REPO ROOT.

set -e
source slurm_jobs/lib/job_env.sh

# INPUT_DIR comes from job_env.sh: the session audio lives OUTSIDE this
# repository, at $PSYCH_ASR_DATA (default ~/phi/PSYCH-ASR).
STAGE1_DIR=data/stage1
TYPIST="${1:-large-v3}"
STOPWATCH="${2:-wav2vec2-base}"

activate_env asr_env
report_gpu

AUDIO_PATH="$(sole_wav "${INPUT_DIR}")"
ASR_PATH="${STAGE1_DIR}/$(basename "${AUDIO_PATH}" .wav).${TYPIST}.asr.json"
if [[ ! -f "${ASR_PATH}" ]]; then
    echo "No ${ASR_PATH}. Did stage1a_transcribe run for ${TYPIST}?" >&2
    exit 1
fi

echo "Aligning ${TYPIST}'s words with ${STOPWATCH}"
python -m psych_asr.cli.align_words "${AUDIO_PATH}" "${ASR_PATH}" --stopwatch "${STOPWATCH}"
