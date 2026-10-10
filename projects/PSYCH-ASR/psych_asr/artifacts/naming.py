"""The Stage 1 filename convention, in one place.

STDLIB ONLY.

Every Stage 1 artifact is named "<stem>.<arm>.<kind>", where stem is the audio file's
stem and arm is the diarizer that produced it. THE ARM NAME IS CARRIED IN THE FILENAME
FROM STAGE 1b ONWARD, so which model produced which artifact is a property of the file
rather than of a note somewhere -- and Stage 1c derives the arm from the RTTM's own name,
which is why adding a fifth arm needs no change to the join.

    <stem>.<typist>.asr.json            Stage 1a-i, one typist's untimed words (PHI)
    <stem>.aligned.json                 Stage 1a-ii, no speaker keys
    <stem>.<arm>.rttm                   Stage 1b, that arm's speaker turn table
    <stem>.<arm>.exclusive.rttm         Stage 1b baseline only, the overlap-free view
    <stem>.<arm>.diarized.json          Stage 1c, the machine artifact
    <stem>.<arm>.transcript.txt         Stage 1c, the readable copy

THE ARM NAME IS WHAT MAKES THE MODEL GRID FREE. A grid cell is a typist, a stopwatch and a
name-tagger, and nothing in this module needs to know that: the arm is whatever string
sits between the stem and the suffix, so "large-v3+wav2vec2-base+community-1" is a
perfectly good arm name and the discovery helpers and the join already handle it. That is
only true because the parsing below is by exact suffix rather than by splitting on ".": an
arm name may contain dots, and splitting would cut it in the wrong place.
"""

from pathlib import Path

ASR_SUFFIX = ".asr.json"
ALIGNED_SUFFIX = ".aligned.json"
DIARIZED_SUFFIX = ".diarized.json"
TRANSCRIPT_SUFFIX = ".transcript.txt"
RTTM_SUFFIX = ".rttm"
EXCLUSIVE_RTTM_SUFFIX = ".exclusive.rttm"


def _strip_suffix(name, suffix):
    """IN: filename + expected suffix  OUT: the name without it, or the name unchanged."""
    return name[: -len(suffix)] if name.endswith(suffix) else name


def stem_from_aligned(path):
    """IN: path to <stem>.aligned.json   OUT: "<stem>"."""
    return _strip_suffix(Path(path).name, ALIGNED_SUFFIX)


def stem_from_diarized(path):
    """IN: path to <stem>.diarized.json or <stem>.<arm>.diarized.json   OUT: what precedes
    the suffix, arm included. Callers that want the bare stem pass the stem in."""
    return _strip_suffix(Path(path).name, DIARIZED_SUFFIX)


def arm_from(path, stem, suffix):
    """IN: an artifact path, the session stem, and the artifact's suffix   OUT: the arm name.

    "<stem>.<arm><suffix>" -> "<arm>". A file that does not start with "<stem>." keeps its
    whole basename as the arm, which is what makes a hand-placed RTTM with an unexpected
    name still join rather than raise -- it just labels itself oddly, visibly.
    """
    base = _strip_suffix(Path(path).name, suffix)
    prefix = stem + "."
    return base[len(prefix):] if base.startswith(prefix) else base


def asr_path(directory, stem, typist):
    """IN: output directory + stem + typist   OUT: Path to <stem>.<typist>.asr.json.

    Stage 1a-i's artifact: ONE typist's segments, with loose boundaries and no word-level
    times, before any stopwatch has seen them. PHI -- it carries verbatim session text.

    It exists because a typist and a stopwatch do not share an environment. faster-whisper
    lives in asr_env and the NVIDIA models live in nemo_env, so the two passes that used to
    be one function are now two jobs and this file is what passes between them. That is the
    RTTM seam of Stage 1b, cut again for Stage 1a.
    """
    return Path(directory) / f"{stem}.{typist}{ASR_SUFFIX}"


def aligned_path(directory, stem, arm=None):
    """IN: output directory + stem + optional arm   OUT: Path to the aligned transcript.

    Without an arm: <stem>.aligned.json, the un-armed name the single-typist Stage 1 has
    always written, and the name the regression gate identifies its fixture by.

    With one: <stem>.<arm>.aligned.json, where the arm names the typist and the stopwatch
    that produced it -- "large-v3+wav2vec2-base". The third component of a grid cell, the
    name-tagger, is appended by Stage 1b, so the arm here is deliberately half a cell name.
    """
    name = f"{stem}.{arm}" if arm else stem
    return Path(directory) / f"{name}{ALIGNED_SUFFIX}"


def rttm_path(directory, stem, arm):
    """IN: output directory + stem + arm   OUT: Path to <stem>.<arm>.rttm."""
    return Path(directory) / f"{stem}.{arm}{RTTM_SUFFIX}"


def exclusive_rttm_path(directory, stem, arm):
    """IN: output directory + stem + arm   OUT: Path to <stem>.<arm>.exclusive.rttm."""
    return Path(directory) / f"{stem}.{arm}{EXCLUSIVE_RTTM_SUFFIX}"


def diarized_path(directory, stem, arm=None):
    """IN: output directory + stem + optional arm   OUT: Path to the machine artifact.

    With an arm: <stem>.<arm>.diarized.json, what Stage 1c writes. Without one:
    <stem>.diarized.json, the un-armed name the SINGLE-JOB Stage 1 has always written. The
    regression gate identifies the fixture by exactly that absence of an arm, so the two
    names are not interchangeable.
    """
    name = f"{stem}.{arm}" if arm else stem
    return Path(directory) / f"{name}{DIARIZED_SUFFIX}"


def transcript_path(directory, stem, arm=None):
    """IN: output directory + stem + optional arm   OUT: Path to the readable .txt.

    The single-job Stage 1 path writes <stem>.transcript.txt with no arm in it; the
    bake-off path writes one per arm. Both name it here.
    """
    name = f"{stem}.{arm}" if arm else stem
    return Path(directory) / f"{name}{TRANSCRIPT_SUFFIX}"


def find_sole_stem(stage1_dir):
    """IN: the Stage 1 directory   OUT: the one session stem present, by its aligned JSON.

    Raises SystemExit naming the count when it is not exactly one, because "which session"
    is not something to guess at when the answer decides which files get overwritten.

    ONCE THE TYPIST GRID RUNS THIS STOPS FINDING ONE. Each typist/stopwatch pair writes its
    own <stem>.<arm>.aligned.json, and a dotted arm is indistinguishable from a dotted stem,
    so the count goes to eight and every caller must pass --stem. That is the intended
    failure: it says so and stops rather than picking a cell at random.
    """
    aligned = sorted(Path(stage1_dir).glob(f"*{ALIGNED_SUFFIX}"))
    if len(aligned) != 1:
        raise SystemExit(
            f"Found {len(aligned)} {ALIGNED_SUFFIX} files in {stage1_dir}; pass --stem explicitly."
        )
    return stem_from_aligned(aligned[0])


def find_arm_rttms(stage1_dir, stem):
    """IN: Stage 1 directory + stem   OUT: sorted list of (arm, Path) for every arm's RTTM.

    The .exclusive.rttm is skipped: it is the baseline's overlap-free view, a diagnostic on
    an existing arm rather than an arm of its own. Discovery is by glob rather than by a
    hardcoded arm list, so an arm whose job crashed is simply absent -- which is a visible
    result rather than a raised exception.
    """
    found = []
    for path in sorted(Path(stage1_dir).glob(f"{stem}.*{RTTM_SUFFIX}")):
        if path.name.endswith(EXCLUSIVE_RTTM_SUFFIX):
            continue
        found.append((arm_from(path, stem, RTTM_SUFFIX), path))
    return found


def find_asr_transcripts(stage1_dir, stem):
    """IN: Stage 1 directory + stem   OUT: sorted list of (typist, Path) for every .asr.json.

    Same discovery-by-glob reasoning as find_arm_rttms: a typist whose job crashed is simply
    absent from the bake-off, which is a visible result rather than a raised exception.
    """
    return [
        (arm_from(path, stem, ASR_SUFFIX), path)
        for path in sorted(Path(stage1_dir).glob(f"{stem}.*{ASR_SUFFIX}"))
    ]


def find_arm_transcripts(stage1_dir, stem):
    """IN: Stage 1 directory + stem   OUT: sorted list of (arm, Path) for every joined JSON.

    Same discovery-by-glob reasoning as find_arm_rttms.
    """
    return [
        (arm_from(path, stem, DIARIZED_SUFFIX), path)
        for path in sorted(Path(stage1_dir).glob(f"{stem}.*{DIARIZED_SUFFIX}"))
    ]
