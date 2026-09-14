"""Where the staged model weights and the pipeline's own artifacts live.

STDLIB ONLY. Every env imports this.

Model weights are staged ONCE on the login node into a models/ directory on study
storage and loaded thereafter by ABSOLUTE PATH with HF_HUB_OFFLINE=1, because the compute
nodes have no outbound internet (see README, "Staging model weights"). Those absolute
paths used to be repeated as literal defaults in five argument parsers, which meant
moving the staging directory was a five-file edit with no way to tell whether one had
been missed. They are here instead, and every parser's default reads from here.

The root is overridable with PSYCH_ASR_MODELS_ROOT for anyone running this off a
different filesystem; nothing in the pipeline sets it, so the default is what runs.
"""

import os
from pathlib import Path

# Study storage, not the home folder: the weights are ~5 GB and every compute node
# mounts this path.
MODELS_ROOT = Path(os.environ.get(
    "PSYCH_ASR_MODELS_ROOT",
    "/media/studies/ehr_study/analysis/mferguson/models",
))

# ---- Stage 1a: ASR and forced alignment ----
# Systran/faster-whisper-large-v3, staged by `hf download --local-dir`. Loaded with
# local_files_only, and the path must be handed over as a STRING -- only a str takes
# faster-whisper's local-directory branch.
WHISPER_MODEL_DIR = MODELS_ROOT / "faster-whisper-large-v3"

# The fast decoder, four decoder layers instead of thirty-two. Same env, same call path,
# same loader -- which is the whole point of having it in the bake-off: it measures what
# the speed-up costs in words, with nothing else varying. Systran never published a
# CTranslate2 build of turbo; staged from deepdml/faster-whisper-large-v3-turbo-ct2, MIT,
# whose six files are byte-for-byte the same LAYOUT as the staged large-v3 (config.json,
# model.bin, preprocessor_config.json, tokenizer.json, vocabulary.json), which is what
# makes it a drop-in for the same loader.
WHISPER_TURBO_MODEL_DIR = MODELS_ROOT / "faster-whisper-large-v3-turbo"

# The two NVIDIA typists. Both load through nemo.collections.asr straight off disk, so no
# Hub call is made -- the same reason the Sortformer arms need no HF_HUB_OFFLINE dance.
# LICENCES READ 2026-09-13: both are CC-BY-4.0, i.e. commercial use permitted with
# attribution, so neither adds to the two diarizer arms that are already non-commercial.
# These name the staged DIRECTORY, not the archive: `hf download --local-dir` writes the
# .nemo file inside it, and restore_from wants the file, so typists.resolve_nemo_checkpoint
# does that last hop at load time.
PARAKEET_CHECKPOINT = MODELS_ROOT / "parakeet-tdt-0.6b-v2"
CANARY_CHECKPOINT = MODELS_ROOT / "canary-1b-flash"

# ---- Stage 1a: who typed and who timed, carried in every filename from here on ----
# A Stage 1a arm is "<typist>+<stopwatch>", and Stage 1b appends the name-tagger. Three
# swappable boxes, three axes, one string -- and nothing downstream parses it, because
# every artifact name is read by exact suffix rather than by splitting on ".".
TYPIST_LARGE_V3 = "large-v3"
TYPIST_LARGE_V3_TURBO = "large-v3-turbo"
TYPIST_PARAKEET = "parakeet"
TYPIST_CANARY = "canary"

# The stopwatch is a torchaudio bundle NAME, not a path: whisperx resolves an English
# alignment model through torchaudio.pipelines and fetches it into TORCH_HOME, which is why
# warm_align_cache exists and why HF_HUB_OFFLINE does not cover this download.
STOPWATCH_WAV2VEC2_BASE = "WAV2VEC2_ASR_BASE_960H"
STOPWATCH_WAV2VEC2_LARGE = "WAV2VEC2_ASR_LARGE_LV60K_960H"

# Short name -> bundle name. The short name is what goes in the filename; the bundle name
# is what torchaudio answers to. Keeping them apart is what stops an arm string reading
# "large-v3+WAV2VEC2_ASR_LARGE_LV60K_960H" in a directory listing.
STOPWATCHES = {
    "wav2vec2-base": STOPWATCH_WAV2VEC2_BASE,
    "wav2vec2-large": STOPWATCH_WAV2VEC2_LARGE,
}

# ---- Stage 1b: one entry per arm ----
# Baseline. Pipeline.from_pretrained takes the DIRECTORY and finds config.yaml inside it;
# the config's $model/... references resolve against that same directory.
PYANNOTE_MODEL_DIR = MODELS_ROOT / "pyannote-speaker-diarization-community-1"

# Arm A. DiariZen's own from_pretrained calls snapshot_download, so the pipeline is
# constructed from these two absolute paths instead (see diarize/diarizen_arm.py).
DIARIZEN_MODEL_DIR = MODELS_ROOT / "diarizen-wavlm-large-s80-md-v2"
# The speaker embedder, handed over as a plain FILE path rather than a directory. Already
# staged for the baseline arm, so it is not a third download.
WESPEAKER_EMBEDDING_FILE = MODELS_ROOT / "pyannote-wespeaker-voxceleb-resnet34-LM" / "pytorch_model.bin"

# Arms B and C. Both load through SortformerEncLabelModel.restore_from, which reads the
# .nemo archive straight off disk and makes no Hub call at all.
SORTFORMER_OFFLINE_CHECKPOINT = MODELS_ROOT / "diar_sortformer_4spk-v1" / "diar_sortformer_4spk-v1.nemo"
SORTFORMER_STREAMING_CHECKPOINT = MODELS_ROOT / "diar_streaming_sortformer_4spk-v2.1" / "diar_streaming_sortformer_4spk-v2.1.nemo"

# ---- Caches that are NOT Hugging Face and are not covered by HF_HUB_OFFLINE ----
# WhisperX resolves its English alignment model to a torchaudio bundle fetched from
# download.pytorch.org, and its sentence splitter to an nltk package. Each library reads
# its OWN variable to find its cache, so every job must EXPORT these -- having the files
# on study storage is necessary and not sufficient.
TORCH_HOME = MODELS_ROOT / "torch_home"
NLTK_DATA = MODELS_ROOT / "nltk_data"

# AND IMPORTING THIS MODULE EXPORTS THEM, because "every job must export these" was only
# ever true of the jobs. `slurm_jobs/lib/job_env.sh` exports both and every .sbatch sources
# it, so a queued job has always been safe -- but nothing else was. A pytest run, a
# `python -m psych_asr...` on the login node, an interactive check: each got the library
# default, and nltk's default is `~/nltk_data`. On 13 September 2026 one of them downloaded
# `punkt_tab` into the home folder, silently, because whisperx's alignment.py calls
# `nltk.download('punkt_tab', quiet=True)` when the lookup misses. 18 MB nobody asked for,
# a duplicate of what was already staged, and on a compute node with no egress that same
# call is a hang rather than a download.
#
# setdefault, NOT assignment: an explicit export still wins, which is what keeps
# PSYCH_ASR_MODELS_ROOT meaningful and lets a job override either path. Every env imports
# this module, so this is the one place that reaches all of them.
#
# HF_HUB_OFFLINE IS DELIBERATELY NOT SET HERE. It belongs to the compute node, where there
# is no outbound internet and a stray Hub request should fail fast. Setting it from an
# import would also set it for `psych_asr.cli.warm_align_cache`, whose entire job is to
# reach download.pytorch.org from the login node.
os.environ.setdefault("TORCH_HOME", str(TORCH_HOME))
os.environ.setdefault("NLTK_DATA", str(NLTK_DATA))

# ---- Artifacts ----
# Session content, and therefore PHI.
#
# IT LIVES IN THE WORKSPACE AND OUTSIDE GIT: `phi/`, beside this package. 308 MB of
# identifiable therapy session audio with participant IDs in the filenames, and
# everything the pipeline writes goes beside it. It was at `~/phi/PSYCH-ASR` until
# 14 September 2026; it is here now, because a project's data belongs with the project.
#
# THREE FENCES, and not one of them is trusted alone: `/phi/` is the first rule in this
# workspace's .gitignore, `board/test/tracked.py` fails the whole suite if any of it is
# ever tracked, and `ai-config/policy/phi.py` refuses to let an assistant read it by
# matching the directory NAME. That last one is why this directory is called what it is
# called -- rename it and 308 MB of PHI silently stops being fenced while everybody goes
# on believing in the hook. Do not rename it.
#
# It is NOT symlinked in. A symlink is a tracked file pointing at PHI, which hands the
# next reader of a public repository a map straight to it.
#
# `PSYCH_ASR_DATA` overrides the root, the same way `PSYCH_ASR_MODELS_ROOT` overrides the
# weights, for anyone running this off other storage. Absolute on purpose, and derived
# from THIS FILE rather than from $HOME: these paths used to resolve against the submit
# directory, so a job launched from the wrong place wrote session content somewhere
# nobody was looking for it. `slurm_jobs/lib/job_env.sh` works the same root out the same
# way, so a Python step and a shell step in one job cannot disagree.
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get(
    "PSYCH_ASR_DATA", str(WORKSPACE_ROOT / "phi")))

STAGE1_DIR = DATA_ROOT / "stage1"
# Stage 2's own directory, and deliberately not a subdirectory of Stage 1's: the
# arm-discovery globs in artifacts/naming.py match "<stem>.*" inside STAGE1_DIR, so a
# corrected reference stored there would be enrolled as a fifth diarization arm by the
# bake-off it exists to judge.
STAGE2_DIR = DATA_ROOT / "stage2"
INBOX_DIR = DATA_ROOT / "inbox"

# ---- Arm names, which are carried in every filename from Stage 1b onward ----
# Which model produced which transcript is a property of the file, not of a note
# somewhere, and Stage 1c derives the arm from the RTTM's own name -- so adding a fifth
# arm needs no change to the join.
ARM_BASELINE = "community-1"
ARM_DIARIZEN = "diarizen"
ARM_SORTFORMER = "sortformer"
ARM_SORTFORMER_STREAMING = "sortformer-streaming"
