#!/bin/bash
# ---------------------------------------------------------------------------
# stage_models.sh -- download every offline model asset, ONCE, on the LOGIN NODE.
#
#     bash scripts/stage_models.sh            stage what is missing, then check all
#     bash scripts/stage_models.sh --check    only the check: no .env, no downloads
#
# LOGIN NODE ONLY, because staging is the owner's action. Everything here lands in
# a models/ directory on study storage, and every job loads it by ABSOLUTE PATH
# with HF_HUB_OFFLINE=1 set, so a model nobody staged fails fast in the job
# instead of being fetched there.
#
# ALREADY-STAGED MODELS ARE KEPT. `hf download` resolves a repo to its latest
# revision, so re-fetching a staged directory could move the weights earlier
# runs used. A non-empty directory (or, for a single-file stage, a non-empty
# file) prints "kept" and is not touched. Delete it to re-fetch.
#
# THE TOKEN IS NEEDED ONLY FOR THE GATED REPO. pyannote's community-1 is the one
# gated download; with it already staged, the script runs without a .env.
#
# Two caches here are NOT Hugging Face downloads and are not covered by
# HF_HUB_OFFLINE, which is exactly why they are easy to forget:
#   * the two torchaudio wav2vec2 stopwatch bundles, fetched from
#     download.pytorch.org into TORCH_HOME by psych_asr.cli.warm_align_cache
#   * nltk's punkt_tab, which WhisperX's alignment step loads for sentence
#     splitting and would otherwise nltk.download() from a compute node
# DiariZen's WavLM is NOT a download at all -- see below.
#
# VERIFY A STAGED MODEL, DO NOT ASSUME IT. `hf download` can terminate leaving a
# directory holding only README.md and empty weight subfolders, with lock files
# under .cache/huggingface/download/ as the only trace. It looks staged from a
# casual ls. So the script ends with psych_asr.cli.preflight_models --load,
# which checks every asset by file and by an offline load, and exits with its
# status. An `empty` or `incomplete` line means: delete that directory, rerun.
#
# It also creates slurm_jobs/logs/, which is ignored by git and which Slurm does
# not create for a job's -o path.
# ---------------------------------------------------------------------------

CHECK_ONLY=0
case "${1:-}" in
    --check) CHECK_ONLY=1 ;;
    "") ;;
    *) echo "Unknown argument '$1'. Usage: bash scripts/stage_models.sh [--check]" >&2; exit 1 ;;
esac

eval "$(/opt/apps/easybuild/software/Anaconda3/2025.06-0/bin/conda shell.bash hook)"

set -o errexit
set -o nounset
set -o pipefail

# Derived from this script's own location rather than hardcoded, so a clone
# anywhere stages into its own tree.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENV_BASE="${PSYCH_ASR_VENV_ROOT:-/media/studies/ehr_study/analysis/mferguson/venvs}"
MODELS_ROOT="${PSYCH_ASR_MODELS_ROOT:-/media/studies/ehr_study/analysis/mferguson/models}"
export CONDA_PKGS_DIRS="${ENV_BASE}/conda_pkgs"

set +o nounset
export PYTHONNOUSERSITE=1
conda activate "${ENV_BASE}/asr_env"
set -o nounset

mkdir -p "${REPO_ROOT}/slurm_jobs/logs"

# The two caches that are not Hugging Face. Exported, because each library reads
# its own variable, and the preflight checks the same paths every job uses.
export TORCH_HOME="${MODELS_ROOT}/torch_home"
export NLTK_DATA="${MODELS_ROOT}/nltk_data"
# pyannote.audio 4.x telemetry is on by default and posts to otel.pyannote.ai;
# the preflight's pipeline load would send it from the login node.
export PYANNOTE_METRICS_ENABLED=0

# Run from the repo root: nothing is pip installed, so the repo landing on
# sys.path is what makes `python -m psych_asr...` resolve.
cd "${REPO_ROOT}"

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
    exec python -m psych_asr.cli.preflight_models --load
fi

# A directory counts as staged when it exists and holds anything at all.
is_staged_dir () {   # is_staged_dir <directory>
    [[ -d "$1" ]] && [[ -n "$(ls -A "$1" 2>/dev/null)" ]]
}

# ---- the token, exported so the `hf` CLI actually inherits it ----
# WITHOUT allexport the token stays shell-local and the download 401s. The .env
# is gitignored; never commit it.
ENV_PATH="${REPO_ROOT}/.env"
if [[ -f "${ENV_PATH}" ]]; then
    set -o allexport
    source "${ENV_PATH}"
    set +o allexport
fi

GATED_DIR="${MODELS_ROOT}/pyannote-speaker-diarization-community-1"
if ! is_staged_dir "${GATED_DIR}" && [[ -z "${HF_TOKEN:-}" ]]; then
    echo "community-1 is not staged, and pyannote/speaker-diarization-community-1 is gated." >&2
    echo "Put HF_TOKEN=<read-scoped token> in ${ENV_PATH}, accept the repo's terms on" >&2
    echo "huggingface.co while logged in as that token's account, and run this again." >&2
    exit 1
fi

# For the DOWNLOAD only. Every job sets it back on.
unset HF_HUB_OFFLINE

# ---- Hugging Face repos, staged by --local-dir and loaded by absolute path ----
# GATED: only the pyannote diarizer. Accept its terms once while logged in as the
# token's account; community-1 is auto-gated so access is instant.
#
#   A  DiariZen: 278 MB pytorch_model.bin holds the pruned WavLM + Conformer EEND
#      model. Its config.toml names wavlm_src "wavlm_large_s80_md", which looks
#      like a repo id and is NOT -- it resolves to a hardcoded dict in
#      diarizen/models/module/wavlm_config.py, and the pruned weights are already
#      inside that .bin. Nothing to stage.
#      Its speaker embedder is pyannote/wespeaker-voxceleb-resnet34-LM, staged
#      below for the community-1 baseline too, and handed in as a FILE path.
#   B  Sortformer offline: ships BOTH a .nemo archive and transformers-native
#      safetensors. We load the .nemo through SortformerEncLabelModel.restore_from,
#      because arm C ships no safetensors and ONE loading path across both arms is
#      worth more than saving 500 MB.
#   C  Streaming Sortformer: .nemo only.
stage () {   # stage <repo id> <local directory name>
    local target="${MODELS_ROOT}/$2"
    if is_staged_dir "${target}"; then
        echo "kept $2 (already staged; delete it to re-fetch)"
        return 0
    fi
    echo "==== staging $1 -> ${target}"
    hf download "$1" --local-dir "${target}"
}

stage_file () {   # stage_file <repo id> <filename> <local directory name>
    local target="${MODELS_ROOT}/$3"
    if [[ -s "${target}/$2" ]]; then
        echo "kept $3 (already staged; delete it to re-fetch)"
        return 0
    fi
    echo "==== staging $1:$2 -> ${target}"
    hf download "$1" "$2" --local-dir "${target}"
    hf download "$1" README.md --local-dir "${target}"
}

stage Systran/faster-whisper-large-v3                  faster-whisper-large-v3
stage pyannote/speaker-diarization-community-1         pyannote-speaker-diarization-community-1
stage pyannote/wespeaker-voxceleb-resnet34-LM          pyannote-wespeaker-voxceleb-resnet34-LM
stage BUT-FIT/diarizen-wavlm-large-s80-md-v2           diarizen-wavlm-large-s80-md-v2
stage nvidia/diar_sortformer_4spk-v1                   diar_sortformer_4spk-v1
stage nvidia/diar_streaming_sortformer_4spk-v2.1       diar_streaming_sortformer_4spk-v2.1

# ---- the other three typists ----
# TURBO: Systran never published a CTranslate2 build of large-v3-turbo. deepdml's is the
# widely used conversion, MIT, and its six files are the same layout as the large-v3
# directory above -- which is what lets one loader take both.
# THE TWO NVIDIA TYPISTS: both CC-BY-4.0, so unlike diarizer arms A and B they carry no
# non-commercial restriction. Only the .nemo archive and the model card are pulled; the
# canary repo also ships a safetensors copy we never load, and it is 3.5 GB of nothing.
stage      deepdml/faster-whisper-large-v3-turbo-ct2   faster-whisper-large-v3-turbo
stage_file nvidia/parakeet-tdt-0.6b-v2 parakeet-tdt-0.6b-v2.nemo  parakeet-tdt-0.6b-v2
stage_file nvidia/canary-1b-flash      canary-1b-flash.nemo       canary-1b-flash

# ---- the two caches that are not Hugging Face ----
mkdir -p "${TORCH_HOME}" "${NLTK_DATA}"

# Both stopwatch bundles, base and large. A bundle already in TORCH_HOME is reused.
python -m psych_asr.cli.warm_align_cache

# NOTE: english.pickle DOES NOT EXIST as a file. punkt_tab ships per-language
# folders of .tab/.txt data and NLTK synthesizes a PunktTokenizer from them when
# that name is requested. The absence of a .pickle on disk is not a failed
# download.
python -m nltk.downloader -d "${NLTK_DATA}" punkt_tab

# The check every asset must pass before a job may use it, by file and by an
# offline load. This script exits with its status.
echo ""
exec python -m psych_asr.cli.preflight_models --load
