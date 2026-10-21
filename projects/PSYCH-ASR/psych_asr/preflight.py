"""Is every model asset the grid needs actually staged? The file tier, by counting.

STDLIB ONLY. psych_asr.cli.preflight_models adds the load tier on top, and
psych_asr.cli.grid_submit runs this tier before it asks Slurm for any GPU.

A STAGED-LOOKING DIRECTORY IS NOT A STAGED MODEL. `hf download` can stop leaving README.md,
empty weight folders and lock files under .cache/huggingface/download/. So each asset is
judged by its own required files, each non-zero, and the status says which way it fell
short:

    ok          every required file is there and non-zero
    missing     the path does not exist
    empty       nothing non-zero under it (files under .cache/ do not count)
    incomplete  something is there, but a required file is absent or zero bytes, a partial
                download is left under .cache/, or a .nemo is not a tar archive

check_data() counts the inbox's WAVs and never names one.
"""

import os
import tarfile
from collections import namedtuple
from pathlib import Path

from . import config, grid
from .asr import typists

OK, MISSING, EMPTY, INCOMPLETE = "ok", "missing", "empty", "incomplete"
LOAD_FAILED = "load-failed"

# axis: typist | stopwatch | tagger | shared. kind picks the requirement in check().
Asset = namedtuple("Asset", "axis name path kind")
Result = namedtuple("Result", "status files bytes")

# The envs every grid job activates between them.
ENVS = ("asr_env", "nemo_env", "diarizen_env")

WEIGHT_PATTERNS = ("*.bin", "*.safetensors", "*.ckpt", "*.npz")


def _torch_home():
    return Path(os.environ.get("TORCH_HOME") or config.TORCH_HOME)


def _nltk_data():
    return Path(os.environ.get("NLTK_DATA") or config.NLTK_DATA)


def _tagger_asset(name):
    if name == config.ARM_BASELINE:
        return Asset("tagger", name, config.PYANNOTE_MODEL_DIR, "pyannote")
    if name in (config.ARM_DIARIZEN, config.ARM_DIARIZEN_FREE):
        return Asset("tagger", name, config.DIARIZEN_MODEL_DIR, "diarizen")
    if name == config.ARM_SORTFORMER:
        return Asset("tagger", name, config.SORTFORMER_OFFLINE_CHECKPOINT, "nemo-file")
    if name == config.ARM_SORTFORMER_STREAMING:
        return Asset("tagger", name, config.SORTFORMER_STREAMING_CHECKPOINT, "nemo-file")
    raise SystemExit(f"No preflight asset for name-tagger {name!r}")


def assets(typist_names=None, stopwatch_names=None, tagger_names=None):
    """IN: the selected axes (None means all)   OUT: a list of Asset, axis by axis.

    Paths are read at call time, so TORCH_HOME and NLTK_DATA follow the environment the
    check runs in -- the same variables every job exports.
    """
    typist_names = grid.TYPISTS if typist_names is None else typist_names
    stopwatch_names = grid.STOPWATCHES if stopwatch_names is None else stopwatch_names
    tagger_names = tuple(grid.NAME_TAGGERS) if tagger_names is None else tagger_names

    found = []
    for name in typist_names:
        entry = typists.describe(name)
        kind = "whisper" if entry["backend"] == "faster-whisper" else "nemo-dir"
        found.append(Asset("typist", name, Path(entry["checkpoint"]), kind))
    for name in stopwatch_names:
        found.append(Asset("stopwatch", name, _torch_home() / "hub" / "checkpoints"
                           / config.STOPWATCH_CHECKPOINTS[name], "file"))
    for name in tagger_names:
        found.append(_tagger_asset(name))
    found.append(Asset("shared", "nltk-punkt_tab", _nltk_data() / "tokenizers" / "punkt_tab", "dir"))
    for env in ENVS:
        found.append(Asset("shared", env, Path(config.VENV_ROOT) / env / "bin" / "python", "env"))
    return found


def _counted(root):
    """IN: a directory   OUT: its files, recursively, skipping anything under .cache/."""
    return [p for p in root.rglob("*")
            if p.is_file() and ".cache" not in p.relative_to(root).parts]


def _nonzero(path):
    return path.is_file() and path.stat().st_size > 0


def _partial_download(root):
    """True when hf's download cache under root holds a lock or a half-written file."""
    cache = root / ".cache" / "huggingface" / "download"
    if not cache.is_dir():
        return False
    return any(p.name.endswith((".incomplete", ".lock")) for p in cache.rglob("*"))


def _is_tar(path):
    try:
        return tarfile.is_tarfile(str(path))
    except OSError:
        return False


def _missing_required(asset):
    """IN: an Asset whose path is a directory   OUT: True when a requirement is unmet."""
    root = Path(asset.path)
    if asset.kind == "whisper":
        required = [root / n for n in ("model.bin", "config.json", "tokenizer.json")]
        vocabulary = [p for p in root.glob("vocabulary.*") if _nonzero(p)]
        return not all(_nonzero(p) for p in required) or not vocabulary
    if asset.kind == "nemo-dir":
        archives = [p for p in root.glob("*.nemo") if _nonzero(p)]
        return len(archives) != 1 or not _is_tar(archives[0])
    if asset.kind == "pyannote":
        weights = [p for pattern in WEIGHT_PATTERNS for p in root.rglob(pattern)
                   if _nonzero(p) and ".cache" not in p.relative_to(root).parts]
        return not _nonzero(root / "config.yaml") or not weights
    if asset.kind == "diarizen":
        plda = root / "plda"
        plda_files = [p for p in plda.rglob("*") if _nonzero(p)] if plda.is_dir() else []
        return (not _nonzero(root / "config.toml") or not _nonzero(root / "pytorch_model.bin")
                or not plda_files or not _nonzero(Path(config.WESPEAKER_EMBEDDING_FILE)))
    return False   # "dir": non-empty is enough


def check(asset):
    """IN: an Asset   OUT: Result(status, files counted, total bytes)."""
    path = Path(asset.path)

    if asset.kind == "env":
        if not path.exists():
            return Result(MISSING, 0, 0)
        return Result(OK, 1, path.stat().st_size)

    if asset.kind in ("file", "nemo-file"):
        if not path.exists():
            return Result(MISSING, 0, 0)
        size = path.stat().st_size if path.is_file() else 0
        if size == 0:
            return Result(EMPTY, 1 if path.is_file() else 0, 0)
        if asset.kind == "nemo-file" and not _is_tar(path):
            return Result(INCOMPLETE, 1, size)
        return Result(OK, 1, size)

    if not path.is_dir():
        return Result(MISSING, 0, 0)
    files = _counted(path)
    total = sum(p.stat().st_size for p in files)
    if asset.kind == "diarizen" and _nonzero(Path(config.WESPEAKER_EMBEDDING_FILE)):
        files.append(Path(config.WESPEAKER_EMBEDDING_FILE))
        total += Path(config.WESPEAKER_EMBEDDING_FILE).stat().st_size
    missing = _missing_required(asset)
    # A partial download beside an unmet requirement is incomplete even when nothing else
    # is there yet: the download started and did not finish.
    if missing and _partial_download(path):
        return Result(INCOMPLETE, len(files), total)
    if not any(p.stat().st_size > 0 for p in files):
        return Result(EMPTY, len(files), total)
    if missing:
        return Result(INCOMPLETE, len(files), total)
    return Result(OK, len(files), total)


def check_data(data_root=None):
    """IN: the data root (default config.DATA_ROOT)
    OUT: (whether the root exists, how many *.wav files its inbox holds). Counts only."""
    root = Path(data_root) if data_root is not None else Path(config.DATA_ROOT)
    if not root.is_dir():
        return False, 0
    inbox = root / "inbox"
    if not inbox.is_dir():
        return True, 0
    return True, sum(1 for p in inbox.glob("*.wav") if p.is_file())


def asset_line(asset, result):
    """The per-asset log line. It names the model path, which is open; never a data path."""
    return (f"{result.status} {asset.axis} {asset.name} {Path(asset.path).absolute()} "
            f"files {result.files} bytes {result.bytes}")


def relay_line(asset, status):
    """The RELAY: line for an asset that is not ok. Names only: no "/" and no "."."""
    text = f"{status} {asset.axis} {asset.name}".replace("/", "-").replace(".", "-")
    return "RELAY: preflight " + text


def summary_line(statuses, load_failed=0, wavs=None):
    """IN: every asset's file-tier status, the load failures, the inbox WAV count (None
    when the data check was skipped)   OUT: the final RELAY: line."""
    count = {s: sum(1 for x in statuses if x == s) for s in (OK, EMPTY, MISSING, INCOMPLETE)}
    return (f"RELAY: preflight assets {len(statuses)} ok {count[OK]} empty {count[EMPTY]} "
            f"missing {count[MISSING]} incomplete {count[INCOMPLETE]} "
            f"load-failed {load_failed} inbox-wav {'skipped' if wavs is None else wavs}")


def passed(statuses, load_failed=0, wavs=None):
    """True only when every asset is ok, nothing failed to load, and the inbox holds
    exactly one WAV (or the data check was skipped)."""
    return (all(s == OK for s in statuses) and load_failed == 0
            and (wavs is None or wavs == 1))


def run_file_tier(typist_names=None, stopwatch_names=None, tagger_names=None):
    """IN: the selected axes   OUT: (log lines, [(Asset, Result)]). Prints nothing."""
    results = [(a, check(a)) for a in assets(typist_names, stopwatch_names, tagger_names)]
    lines = [asset_line(a, r) for a, r in results]
    lines += [relay_line(a, r.status) for a, r in results if r.status != OK]
    return lines, results
