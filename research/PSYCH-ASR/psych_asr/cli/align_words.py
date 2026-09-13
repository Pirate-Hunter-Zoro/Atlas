"""Stage 1a-ii: one stopwatch, one typist's words in, word times out.

    python -m psych_asr.cli.align_words <audio.wav> <stem>.<typist>.asr.json

Runs in asr_env on a GPU, whatever typed the words: forced alignment is torchaudio and
whisperx, and never NeMo. That is the point of the seam -- a NeMo typist's output crosses
into this job as a file and the stopwatch never learns where it came from.

IN:  the original audio + <stem>.<typist>.asr.json from Stage 1a-i
OUT: data/stage1/<stem>.<typist>+<stopwatch>.aligned.json -- segments, word_segments and
     language, with NO "speaker" keys anywhere. Stage 1c adds those.

THE ARM NAME IS HALF A GRID CELL. "large-v3+wav2vec2-base" says who typed and who timed;
Stage 1b appends the name-tagger. Nothing downstream parses the string -- every artifact
name is read by exact suffix -- so a two-part arm needs no change to the join, the
comparison or the grader.
"""

from argparse import ArgumentParser
from pathlib import Path

from .. import config
from ..artifacts.naming import ASR_SUFFIX, aligned_path, arm_from
from ..artifacts.transcripts import load_transcript, save_transcript
from ..asr.align import align_segments, format_alignment_summary, load_audio
from ._common import add_output_dir, prepare_output_dir, report

STOPWATCHES = config.STOPWATCHES


def build_parser():
    parser = ArgumentParser(description="Stage 1a-ii: force-align one typist's words.")
    parser.add_argument("audio", type=str, help="the original audio the words were typed from")
    parser.add_argument("asr", type=str, help="path to <stem>.<typist>.asr.json from Stage 1a-i")
    parser.add_argument("--stopwatch", type=str, default="wav2vec2-base", choices=sorted(STOPWATCHES),
                        help="which forced-alignment bundle re-times the words "
                             "(default: %(default)s, whisperx's own default for English)")
    add_output_dir(parser)
    parser.add_argument("--arm", type=str, default=None,
                        help="arm name for the output filename (default: <typist>+<stopwatch>)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    audio_path = Path(args.audio)
    asr_file = Path(args.asr)
    stem = audio_path.stem
    output_dir = prepare_output_dir(args.outdir)

    transcribed = load_transcript(asr_file)
    # The typist is taken from the file that recorded it, and only falls back to the
    # filename for a hand-placed artifact -- which then labels itself oddly, visibly.
    typist = transcribed.get("typist") or arm_from(asr_file, stem, ASR_SUFFIX)
    arm = args.arm or f"{typist}+{args.stopwatch}"

    report([
        f"Arm {arm}: {typist} typed, {STOPWATCHES[args.stopwatch]} times",
        f"Segments in        : {len(transcribed['segments'])}",
    ])

    decoded_audio = load_audio(audio_path)
    align_result = align_segments(
        transcribed["segments"], transcribed.get("language", "en"), decoded_audio,
        stopwatch=STOPWATCHES[args.stopwatch],
    )

    output_path = save_transcript(align_result, aligned_path(output_dir, stem, arm))
    report(format_alignment_summary(align_result, len(transcribed["segments"]))
           + [f"Wrote {output_path}"])


if __name__ == "__main__":
    main()
