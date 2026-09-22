"""Stage 1a-i: the typists, and the one shape all of them must emit.

STDLIB ONLY AT IMPORT TIME. Every heavy import is inside the function that needs it, so
the registry can be listed, validated and unit-tested from an env that has neither
whisperx nor NeMo installed -- which is what lets `--typist` be checked by the parser
before a GPU is allocated.

WHY THIS MODULE EXISTS. Stage 1a used to be one function, transcribe_and_align, and it
was whisper all the way down: whisperx loaded the typist, whisperx ran the stopwatch, and
"which model wrote these words" was not a question the pipeline could ask. That is a
DEFAULT, not a decision -- we ran faster-whisper because whisperx bundles it.

THE SEAM. A typist takes audio and returns SEGMENTS OF TEXT WITH LOOSE BOUNDARIES:

    {"segments": [{"text": str, "start": float, "end": float, ...}, ...],
     "language": "en"}

That is exactly the shape faster-whisper already returned to the aligner, which is the
point -- the stopwatch downstream cannot tell which typist produced it, and did not have
to change. Anything extra a typist knows (avg_logprob, its own word times) rides along in
the same dict and is ignored by the aligner, because the aligner re-times every word
against the waveform anyway. A typist's own timings are NOT the stopwatch's; keeping them
would confound the two axes of the grid that exist to be varied separately.

WHY THE TWO PASSES ARE NOW TWO JOBS. faster-whisper lives in asr_env; Parakeet and Canary
need nemo_env, the same env the Sortformer diarizer arms run in. They cannot be imported
into one process, so the seam is a FILE -- <stem>.<typist>.asr.json -- exactly as the RTTM
is the file between Stage 1b and Stage 1c.
"""

from .. import config

# The sliding-attention half-window, in encoder frames, that the NVIDIA typists are given
# before a session-length file is handed to them. 256 frames is 20 seconds each side at
# the FastConformer's 80 ms stride -- comfortably longer than any single utterance, and
# short enough that the attention matrix stops growing with the recording.
NEMO_LOCAL_ATTENTION_CONTEXT = 256

# One entry per candidate in the typist bake-off. "env" is not read by any code here; it
# is in the table because the answer to "why did this import fail" is always in it.
TYPISTS = {
    config.TYPIST_LARGE_V3: {
        "backend": "faster-whisper",
        "env": "asr_env",
        "checkpoint": config.WHISPER_MODEL_DIR,
        "note": "the incumbent, and the baseline every other number is read against",
    },
    config.TYPIST_LARGE_V3_TURBO: {
        "backend": "faster-whisper",
        "env": "asr_env",
        "checkpoint": config.WHISPER_TURBO_MODEL_DIR,
        "note": "drop-in for the incumbent; measures what the fast decoder costs in words",
    },
    config.TYPIST_PARAKEET: {
        "backend": "nemo",
        "env": "nemo_env",
        "checkpoint": config.PARAKEET_CHECKPOINT,
        "note": "no free-running language model, so it invents less on silence",
    },
    config.TYPIST_CANARY: {
        "backend": "nemo",
        "env": "nemo_env",
        "checkpoint": config.CANARY_CHECKPOINT,
        "note": "attention-encoder-decoder; the other half of the NVIDIA comparison",
    },
}


def describe(name):
    """IN: a typist name   OUT: its registry entry.

    Raises SystemExit listing the known names, rather than KeyError, because this is
    reached from a command line and a stack trace is a worse answer than the menu.
    """
    if name not in TYPISTS:
        raise SystemExit(f"Unknown typist {name!r}. Known: {', '.join(sorted(TYPISTS))}")
    return TYPISTS[name]


def check_segment_contract(segments):
    """IN: a typist's segment list   OUT: nothing; raises SystemExit on a violation.

    THE SEAM'S ONLY GUARANTEE, checked at the moment it is produced rather than three jobs
    later. A typist that returns segments out of time order, or with an end before its
    start, would still serialize fine and would still align -- it would simply re-time the
    words against the wrong stretch of audio and produce a transcript that reads plausibly
    and is wrong by minutes. Nothing downstream can see that; this does.

    Empty text is allowed through: a VAD chunk with nothing in it is a real thing a typist
    can say, and dropping it silently would change the segment count the log reports.
    """
    previous_end = 0.0
    for index, segment in enumerate(segments):
        if "text" not in segment:
            raise SystemExit(f"Segment {index} has no 'text'; the stopwatch has nothing to align.")
        start, end = segment.get("start"), segment.get("end")
        if start is None or end is None:
            raise SystemExit(f"Segment {index} is missing start or end.")
        if end < start:
            raise SystemExit(f"Segment {index} ends ({end}) before it starts ({start}).")
        if start < previous_end - 1e-6:
            raise SystemExit(
                f"Segment {index} starts at {start}, before segment {index - 1} ended at "
                f"{previous_end}. Segments must be in time order; alignment would otherwise "
                f"re-time these words against the wrong audio and say nothing about it."
            )
        previous_end = end


def segments_from_nemo(timestamps):
    """IN: a NeMo hypothesis's segment timestamps   OUT: segments in the seam's shape.

    PURE, and stdlib -- no NeMo import -- so the one place a NeMo transcript could be
    mis-shaped is unit-testable without a GPU or a 3 GB checkpoint.

    NeMo returns a list of {"start": float, "end": float, "segment": str}; the text lives
    under "segment" rather than "text", and that single key rename is the entire difference
    between a NeMo typist and a whisper one as far as anything downstream can tell.
    """
    return [
        {"text": entry.get("segment", ""), "start": float(entry["start"]), "end": float(entry["end"])}
        for entry in timestamps
    ]


def transcribe_faster_whisper(decoded_audio, checkpoint, batch_size=16, device="cuda"):
    """IN: the (N,) waveform + the staged model directory   OUT: the seam dict.

    Imports whisperx, so it runs only in asr_env. The path must be handed over as a STRING,
    not a Path -- only a str takes faster-whisper's local-directory branch, and a Path sends
    it to the Hub, which on a compute node with no outbound internet hangs instead of
    failing. Language is forced to English so per-chunk detection is skipped.
    """
    import whisperx

    pipeline_model = whisperx.load_model(
        str(checkpoint), device=device, compute_type="float16", language="en", local_files_only=True,
    )
    return pipeline_model.transcribe(decoded_audio, batch_size=batch_size, print_progress=True)


def resolve_nemo_checkpoint(checkpoint):
    """IN: the staged path   OUT: the .nemo archive inside it, as a Path.

    NeMo's restore_from wants a .nemo FILE and nothing else; `hf download --local-dir`
    leaves a DIRECTORY with that file inside, next to the README. The registry therefore
    names the directory -- which is the thing staging produces and the thing the README
    documents -- and this turns it into the file at the moment of loading.

    A path that is already a .nemo file is returned unchanged, so --checkpoint can point
    straight at one.
    """
    from pathlib import Path

    path = Path(checkpoint)
    if path.is_file():
        return path
    archives = sorted(path.glob("*.nemo"))
    if len(archives) != 1:
        raise SystemExit(
            f"Expected exactly one .nemo archive in {path}, found {len(archives)}. "
            f"Stage the checkpoint on the login node before running this typist."
        )
    return archives[0]


def enable_long_audio(model, context=NEMO_LOCAL_ATTENTION_CONTEXT):
    """IN: a restored NeMo model (+ the half-window, in encoder frames)   OUT: nothing.

    SWITCHES THE ENCODER FROM GLOBAL ATTENTION TO A SLIDING WINDOW. Both NVIDIA typists are
    FastConformers, and full self-attention costs memory in the SQUARE of the input length.
    A 7-second clip is free; a 50-minute therapy session asks for an 86 GiB attention matrix
    and dies on a 44 GiB card. That is not a tuning problem -- a bigger GPU does not exist
    for it -- so the encoder is told to attend within a window instead.

    The convolution subsampling in front of the encoder has the same problem for its own
    reason, and chunking factor 1 makes it process the waveform in pieces.

    THIS CHANGES THE MODEL, and it is honest to say so: a NeMo typist in this bake-off is
    the published checkpoint with local attention, not the published checkpoint. Both calls
    are NVIDIA's own documented recipe for audio longer than the training segments, and the
    alternative is no NeMo row in the grid at all.
    """
    model.change_attention_model("rel_pos_local_attn", [context, context])
    model.change_subsampling_conv_chunking_factor(1)


def transcribe_nemo(audio_path, checkpoint, batch_size=1, device="cuda", long_audio=True):
    """IN: the audio file path + the staged checkpoint   OUT: the seam dict.

    Imports NeMo, so it runs only in nemo_env. It takes the PATH rather than the decoded
    waveform: NeMo's transcribe reads and resamples the file itself, and handing it the
    array whisperx decoded would mean two different decoders for the same audio across the
    typist axis -- a difference in the bake-off that is not the thing being compared.

    timestamps=True is what makes the model emit segment boundaries at all; without it the
    hypothesis carries text and nothing the stopwatch could start from.
    """
    from nemo.collections.asr.models import ASRModel

    model = ASRModel.restore_from(str(resolve_nemo_checkpoint(checkpoint)), map_location=device)
    model.eval()
    if long_audio:
        enable_long_audio(model)
    hypotheses = model.transcribe([str(audio_path)], batch_size=batch_size, timestamps=True)
    # NeMo has returned both a bare list and a (hypotheses, all_hypotheses) tuple across
    # versions. One file went in, so one hypothesis comes out either way.
    if isinstance(hypotheses, tuple):
        hypotheses = hypotheses[0]
    return {"segments": segments_from_nemo(hypotheses[0].timestamp["segment"]), "language": "en"}


def run(name, audio_path, decoded_audio=None, batch_size=None, device="cuda"):
    """IN: typist name + audio path (+ the decoded waveform, for the whisper backend)
    OUT: the seam dict, contract-checked.

    decoded_audio is required by the faster-whisper backend and ignored by the NeMo one,
    which reads the file itself. Passing it anyway is harmless.
    """
    entry = describe(name)
    if entry["backend"] == "faster-whisper":
        result = transcribe_faster_whisper(
            decoded_audio, entry["checkpoint"], batch_size=batch_size or 16, device=device,
        )
    else:
        result = transcribe_nemo(audio_path, entry["checkpoint"], batch_size=batch_size or 1,
                                 device=device)

    result.setdefault("language", "en")
    check_segment_contract(result["segments"])
    return result


def format_transcription_summary(name, result):
    """IN: the typist name + its output   OUT: log lines.

    Covered seconds is here because it is the one number that catches a typist which ran,
    succeeded, and heard a tenth of the session: the segment count alone does not.
    """
    segments = result["segments"]
    covered = sum(s["end"] - s["start"] for s in segments)
    return [
        f"Typist             : {name}",
        f"Segments           : {len(segments)}",
        f"Last segment end   : {segments[-1]['end'] if segments else 0.0}",
        f"Covered seconds    : {covered:.1f}",
        f"Language           : {result['language']}",
    ]
