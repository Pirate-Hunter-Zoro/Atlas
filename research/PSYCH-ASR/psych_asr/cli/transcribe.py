"""Stage 1a-i: one typist, audio in, untimed words out. No stopwatch, no diarization.

    python -m psych_asr.cli.transcribe <audio.wav> --typist large-v3        (asr_env)
    python -m psych_asr.cli.transcribe <audio.wav> --typist parakeet        (nemo_env)

Output: data/stage1/<stem>.<typist>.asr.json -- segments with loose boundaries and no
word-level timing, plus the language. NO word times, because the word times are the NEXT
job's answer and a typist's own guess at them is not the stopwatch being measured.

WHY THIS IS ITS OWN JOB. Stage 1a used to transcribe and align in one call, which was
possible only because both halves were whisperx. Parakeet and Canary need nemo_env, the
same env the Sortformer arms run in, and nothing imports whisperx and NeMo into one
process. So the two passes are two jobs with a file between them -- the RTTM seam of
Stage 1b, cut again one stage earlier.

RUN THIS IN THE ENV THE TYPIST NEEDS. The registry says which; the job log prints it.
"""

from argparse import ArgumentParser
from pathlib import Path

from ..artifacts.naming import asr_path
from ..artifacts.transcripts import save_transcript
from ..asr import typists
from ._common import add_output_dir, prepare_output_dir, report


def build_parser():
    parser = ArgumentParser(description="Stage 1a-i: transcribe one WAV with one typist.")
    parser.add_argument("audio", type=str)
    parser.add_argument("--typist", type=str, default="large-v3", choices=sorted(typists.TYPISTS),
                        help="which ASR model types the words (default: %(default)s, the incumbent)")
    add_output_dir(parser)
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="override the staged weights for --typist (default: the registry's)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="decode width; defaults to 16 for faster-whisper, 1 for NeMo")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    entry = dict(typists.describe(args.typist))
    if args.checkpoint:
        entry["checkpoint"] = Path(args.checkpoint)

    audio_path = Path(args.audio)
    output_dir = prepare_output_dir(args.outdir)

    report([
        f"Typist {args.typist} ({entry['backend']}, {entry['env']}) from {entry['checkpoint']}",
        f"  {entry['note']}",
    ])

    # whisperx is imported only when a whisper-backed typist is asked for, so this entry
    # point still runs in nemo_env -- where whisperx is not installed and importing the
    # module at the top would end the job before the model name had even been read.
    decoded_audio = None
    if entry["backend"] == "faster-whisper":
        from ..asr.align import load_audio
        decoded_audio = load_audio(audio_path)

    result = typists.run(args.typist, audio_path, decoded_audio=decoded_audio,
                         batch_size=args.batch_size)
    # Which model wrote these words is a property of the FILE, not of a note somewhere.
    result["typist"] = args.typist

    output_path = save_transcript(result, asr_path(output_dir, audio_path.stem, args.typist))
    report(typists.format_transcription_summary(args.typist, result) + [f"Wrote {output_path}"])


if __name__ == "__main__":
    main()
