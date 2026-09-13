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

# The fast decoder, four layers instead of thirty-two. Same env, same call path, same
# loader -- which is the whole point of having it in the bake-off: it measures what the
# speed-up costs in words, with nothing else varying.
WHISPER_TURBO_MODEL_DIR = MODELS_ROOT / "faster-whisper-large-v3-turbo"

# The two NVIDIA typists. Both load through nemo.collections.asr straight off disk, so no
# Hub call is made -- the same reason the Sortformer arms need no HF_HUB_OFFLINE dance.
# NEITHER IS STAGED YET, AND NEITHER MAY BE STAGED UNTIL ITS WEIGHT LICENCE IS READ: two of
# five diarizer arms are already non-commercial and a third one added blind is how a pilot
# ends up undeployable without anyone having decided that.
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

# ---- Artifacts ----
# Session content, and therefore PHI. data/ is gitignored wholesale; nothing here may be
# written anywhere else.
STAGE1_DIR = Path("data/stage1")
# Stage 2's own directory, and deliberately not a subdirectory of Stage 1's: the
# arm-discovery globs in artifacts/naming.py match "<stem>.*" inside STAGE1_DIR, so a
# corrected reference stored there would be enrolled as a fifth diarization arm by the
# bake-off it exists to judge.
STAGE2_DIR = Path("data/stage2")
INBOX_DIR = Path("data/inbox")

# ---- Arm names, which are carried in every filename from Stage 1b onward ----
# Which model produced which transcript is a property of the file, not of a note
# somewhere, and Stage 1c derives the arm from the RTTM's own name -- so adding a fifth
# arm needs no change to the join.
ARM_BASELINE = "community-1"
ARM_DIARIZEN = "diarizen"
ARM_SORTFORMER = "sortformer"
ARM_SORTFORMER_STREAMING = "sortformer-streaming"
