#!/bin/bash
# ---------------------------------------------------------------------------
# job_env.sh -- the boilerplate every PSYCH-ASR Slurm job needs, once.
#
#     source slurm_jobs/lib/job_env.sh
#     activate_env asr_env
#     report_gpu
#     AUDIO_PATH="$(sole_wav "$INPUT_DIR")"
#
# SOURCE IT, do not execute it. Every job submits FROM THE REPO ROOT, so this
# relative path resolves against the submit directory the same way every other
# path in every job does.
#
# One copy of the module load, the conda activation, the exports and the input
# guard, so no two jobs can differ in which caches they export -- a difference
# nobody sees until an arm quietly re-downloads its own weights mid-bake-off.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# WHERE THE SESSION CONTENT IS: `phi/`, IN THIS WORKSPACE AND OUTSIDE GIT.
#
# Identifiable therapy session audio, with participant IDs in the filenames,
# and everything the pipeline writes goes beside it.
#
# THREE THINGS KEEP IT OUT OF A PUBLIC REPOSITORY, and no one of them is
# trusted on its own:
#
#   * `/phi/` is the first rule in this workspace's .gitignore, anchored;
#   * `board/test/tracked.py` fails the whole suite if any of it is ever
#     tracked, which is a rule nobody can break by accident;
#   * `ai-config/policy/phi.py` fences any path naming that directory, whole,
#     so the assistant cannot read a syllable of it at this address either.
#
# THE DIRECTORY KEEPS ITS NAME ON PURPOSE. That third fence matches on the
# directory NAME -- renaming this directory would silently unfence the PHI
# while leaving everybody believing in a hook that had stopped matching. Do not
# rename it.
#
# Exported, so `psych_asr.config` reads the SAME answer -- one root, one
# override, and no way for a Python step and a shell step in the same job to
# disagree about where the audio is.
#
# ABSOLUTE, and derived from THIS FILE's own location rather than from $HOME or
# the submit directory: a job launched from the wrong place cannot write session
# content somewhere nobody is looking. There is exactly one copy of this script
# and it belongs to the workspace it sits in, so its own path is the honest
# answer to "which workspace's data" -- and it stays right if the workspace is
# cloned somewhere else.
_JOB_ENV_LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PSYCH_ASR_WORKSPACE="$(cd "$_JOB_ENV_LIB/../.." && pwd)"
PSYCH_ASR_DATA="${PSYCH_ASR_DATA:-$PSYCH_ASR_WORKSPACE/phi}"
export PSYCH_ASR_DATA
DATA_ROOT="$PSYCH_ASR_DATA"
INPUT_DIR="$DATA_ROOT/inbox"

# A failed job prints its RELAY: lines -- stage, exception type, file and line,
# counts -- and never a name from `phi/`. Here, so every recipe gets it.
source "$_JOB_ENV_LIB/relay_trap.sh"

# A MISSING DATA ROOT STOPS THE JOB. Every step below writes beside the session
# content, and a step that finds no root makes one, empty, where nobody is
# looking. The line names the variable, never its value: the value is a lab
# storage path.
if [ ! -d "$PSYCH_ASR_DATA" ]; then
    echo "RELAY: data root PSYCH_ASR_DATA does not exist; stopping rather than create it empty" >&2
    exit 3
fi

# ---------------------------------------------------------------------------
# WHERE STAGE 1 WRITES. The grid driver (psych_asr/cli/grid_submit.py) sets
# PSYCH_ASR_GRID=<its job id> for every child it submits, and each child then
# writes under stage1/grid-<id>/, so no grid run overwrites an earlier run's
# outputs. Without it, stage1/ itself: the bake-off path.
#
# Exported, so psych_asr.config.STAGE1_DIR -- every CLI's default --outdir --
# agrees with the shell. Nothing is created here; each CLI's prepare_output_dir
# makes the directory when it first writes.
#
# The id becomes a path component, so it is held to letters, digits and "-".
# Anything else ("..", a slash) stops the job before it can write elsewhere.
# ---------------------------------------------------------------------------
if [ -n "${PSYCH_ASR_GRID:-}" ] && [[ ! "${PSYCH_ASR_GRID}" =~ ^[A-Za-z0-9-]+$ ]]; then
    echo "RELAY: grid id refused" >&2
    exit 3
fi
PSYCH_ASR_STAGE1_DIR="${PSYCH_ASR_DATA}/stage1${PSYCH_ASR_GRID:+/grid-${PSYCH_ASR_GRID}}"
export PSYCH_ASR_STAGE1_DIR
STAGE1_DIR="${PSYCH_ASR_STAGE1_DIR}"

VENV_ROOT="${PSYCH_ASR_VENV_ROOT:-/media/studies/ehr_study/analysis/mferguson/venvs}"
MODELS_ROOT="${PSYCH_ASR_MODELS_ROOT:-/media/studies/ehr_study/analysis/mferguson/models}"
ANACONDA_MODULE="${PSYCH_ASR_ANACONDA_MODULE:-Anaconda3/2025.06-0}"

# ---------------------------------------------------------------------------
# activate_env <env name under VENV_ROOT>
#
# Loads Anaconda, activates the prefix env, and exports the five variables every
# job needs. THE EXPORTS ARE THE POINT: each library reads its OWN variable to
# find its cache, so having the weights on study storage is necessary and not
# sufficient. A library that cannot find its cache fetches instead, so the job
# would run a model nobody staged.
#
#   PYTHONNOUSERSITE  keeps ~/.local packages out of a conda prefix env, where
#                     they shadow the pinned ones and break the pin chain
#   HF_HUB_OFFLINE    makes a stray Hub request fail fast instead of fetching
#   PYANNOTE_METRICS_ENABLED=0  turns off pyannote.audio 4.x telemetry, which is
#                     on by default and posts each pipeline load and apply (with
#                     audio duration and speaker count) to otel.pyannote.ai
#   TORCH_HOME        both torchaudio stopwatch bundles; NOT a Hugging Face
#                     asset, so HF_HUB_OFFLINE does not cover it
#   NLTK_DATA         punkt_tab, which WhisperX's alignment step loads for
#                     sentence splitting and would otherwise nltk.download()
#
# The set +u / set -u wrap is not optional: conda's activation script reads
# unset variables and dies under nounset.
# ---------------------------------------------------------------------------
activate_env() {
    local env_name="$1"
    local env_path="${VENV_ROOT}/${env_name}"

    if [[ ! -d "${env_path}" ]]; then
        echo "conda env not found: ${env_path} -- run scripts/setup_envs.sh on the login node" >&2
        return 1
    fi

    module purge
    module load "${ANACONDA_MODULE}"
    eval "$(conda shell.bash hook)"

    set +u; conda activate "${env_path}"; set -u || return 10

    export PYTHONNOUSERSITE=1
    export HF_HUB_OFFLINE=1
    export PYANNOTE_METRICS_ENABLED=0
    export TORCH_HOME="${MODELS_ROOT}/torch_home"
    export NLTK_DATA="${MODELS_ROOT}/nltk_data"

    echo "env: ${env_name} ($(python -V 2>&1))"
}

# ---------------------------------------------------------------------------
# report_gpu -- log which device Slurm handed this job and how much of it is free.
#
# The cluster runs task/cgroup with ConstrainDevices=yes, so a job sees only its
# allocated devices and Slurm sets CUDA_VISIBLE_DEVICES itself. Logging the
# memory line here is what makes a later CUDA OOM explainable from the log alone.
# ---------------------------------------------------------------------------
report_gpu() {
    echo "Pinning to GPU ${CUDA_VISIBLE_DEVICES:-none} on $(hostname)"
    nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv
}

# ---------------------------------------------------------------------------
# sole_wav <dir> / sole_aligned <dir>
#
# Print the one matching file, or fail with a one-line message naming the count.
# INPUT CONVENTION: the inbox holds EXACTLY ONE .wav. The jobs take no arguments
# -- they glob and guard -- so a mistake surfaces as one line instead of a Python
# traceback, and two files cannot become a two-line path.
#
# The glob is expanded into an array rather than counted with `ls | wc -l`: under
# `set -e` a non-matching `ls` kills the job before its own error message runs.
# ---------------------------------------------------------------------------
_sole_match() {
    local description="$1" directory="$2" pattern="$3"
    local matches=( "${directory}"/${pattern} )
    if [[ ! -e "${matches[0]}" ]]; then
        echo "No ${pattern} in ${directory}. ${description}" >&2
        return 1
    fi
    if [[ "${#matches[@]}" -ne 1 ]]; then
        echo "Expected exactly 1 ${pattern} in ${directory}, found ${#matches[@]}. ${description}" >&2
        return 1
    fi
    printf '%s\n' "${matches[0]}"
}

sole_wav() {
    _sole_match "Move the single session you want processed into the inbox." "$1" "*.wav"
}

sole_aligned() {
    _sole_match "Did Stage 1a run?" "$1" "*.aligned.json"
}

# ---------------------------------------------------------------------------
# session_stem <inbox dir>
#
# Print the session stem -- the inbox WAV's basename without ".wav".
#
# THE STEM COMES FROM THE AUDIO, never from globbing the artifacts. A grid run
# writes several aligned transcripts, one per typist and stopwatch, and a dotted
# arm is indistinguishable from a dotted stem -- so the Python side's
# find_sole_stem() stops rather than guessing, and every grid-aware caller must
# pass --stem. The inbox holds exactly one WAV, so the stem is never ambiguous
# there.
# ---------------------------------------------------------------------------
session_stem() {
    local audio_path
    audio_path="$(sole_wav "$1")" || return 1
    basename "${audio_path}" .wav
}
