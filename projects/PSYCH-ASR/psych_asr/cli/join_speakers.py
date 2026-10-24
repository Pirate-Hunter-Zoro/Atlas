"""Stage 1c: join one arm's RTTM onto the shared aligned transcript, then render.

    python -m psych_asr.cli.join_speakers <stem>.aligned.json <stem>.<arm>.rttm

IN:  <stem>.aligned.json from Stage 1a + <stem>.<arm>.rttm from Stage 1b
OUT: <stem>.<arm>.diarized.json + <stem>.<arm>.transcript.txt

CPU only -- no model loads, no GPU. Runs in asr_env for whisperx.assign_word_speakers.

The arm is derived from the RTTM's OWN FILENAME by default, which is why adding a fifth arm
needs no change here.

join_cell is the same join as a function, for the grid's join (cli/join_grid.py): it
writes the same two files and returns counts instead of printing.
"""

from argparse import ArgumentParser
from pathlib import Path

from ..artifacts.naming import RTTM_SUFFIX, arm_from, diarized_path, stem_from_aligned, transcript_path
from ..artifacts.transcripts import load_transcript, save_transcript, speaker_labels, unlabeled_counts
from ..join import format_join_summary, join_arm
from ..transcript.render import write_readable_transcript
from ..transcript.summary import format_summary
from ._common import report


def build_parser():
    parser = ArgumentParser(description="Stage 1c: join a diarization RTTM onto the aligned transcript.")
    parser.add_argument("aligned", type=str, help="path to <stem>.aligned.json from Stage 1a")
    parser.add_argument("rttm", type=str, help="path to <stem>.<arm>.rttm from Stage 1b")
    parser.add_argument("--arm", type=str, default=None,
                        help="arm name for the output filenames (default: inferred from the RTTM filename)")
    parser.add_argument("--stem", type=str, default=None,
                        help="session stem; default is the aligned filename minus its suffix, "
                             "which is only the bare stem when Stage 1a ran un-armed")
    parser.add_argument("--outdir", type=str, default=None,
                        help="where to write (default: beside the aligned JSON)")
    return parser


def _write_joined(aligned_file, rttm_file, stem, arm, output_dir):
    """IN: aligned JSON + RTTM + stem + arm + output dir
    OUT: (joined transcript, turns joined, path of the .diarized.json written).

    Loads the aligned JSON fresh every call: join_arm mutates it in place, so a transcript
    shared between two joins would carry the first arm's speakers into the second.
    """
    aligned = load_transcript(aligned_file)
    augmented, num_turns = join_arm(aligned, rttm_file, arm)
    output_path = save_transcript(augmented, diarized_path(output_dir, stem, arm))
    return augmented, num_turns, output_path


def _write_readable(augmented, stem, arm, output_dir):
    """IN: joined transcript + stem + arm + output dir   OUT: (label, summary, path written).

    The label carries the stem; the file sits beside the session content, never in a log.
    """
    label = f"{stem} [{arm}]"
    readable_path = transcript_path(output_dir, stem, arm)
    summary = write_readable_transcript(augmented, readable_path, label)
    return label, summary, readable_path


def join_counts(augmented, num_turns):
    """IN: a joined transcript + its turn count   OUT: the numbers the join log prints."""
    unlabeled_segments, unlabeled_words = unlabeled_counts(augmented)
    return {
        "segments": len(augmented["segments"]),
        "words": len(augmented["word_segments"]),
        "turns": num_turns,
        "labels": len(speaker_labels(augmented)),
        "unlabeled_segments": unlabeled_segments,
        "unlabeled_words": unlabeled_words,
    }


def join_cell(aligned_file, rttm_file, stem, arm, output_dir):
    """IN: aligned JSON + RTTM + stem + arm + output dir
    OUT: the counts dict (join_counts). Writes <stem>.<arm>.diarized.json and
    <stem>.<arm>.transcript.txt into output_dir; prints nothing."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    augmented, num_turns, _ = _write_joined(aligned_file, rttm_file, stem, arm, output_dir)
    _write_readable(augmented, stem, arm, output_dir)
    return join_counts(augmented, num_turns)


def main(argv=None):
    args = build_parser().parse_args(argv)

    aligned_file = Path(args.aligned)
    rttm_file = Path(args.rttm)

    # stem_from_aligned strips the suffix and nothing else, so an ARMED aligned transcript
    # hands back "<stem>.<typist>+<stopwatch>" -- and naming the output from that gives a
    # file with the cell in it twice. --stem is how a grid caller says which part is the
    # session; without a grid there is no arm in the name and the two agree.
    stem = args.stem or stem_from_aligned(aligned_file)
    arm = args.arm or arm_from(rttm_file, stem, RTTM_SUFFIX)

    output_dir = Path(args.outdir) if args.outdir else aligned_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    augmented, num_turns, output_path = _write_joined(aligned_file, rttm_file, stem, arm, output_dir)
    report(format_join_summary(arm, augmented, num_turns) + [f"Wrote {output_path}"])

    # Talk-time split is the cheapest diarization sanity check there is: two people in a
    # room do not split 97/3, so that number falsifies a collapsed clustering from the log
    # alone, before anyone opens the audio.
    label, summary, readable_path = _write_readable(augmented, stem, arm, output_dir)
    report(format_summary(label, summary) + [f"Wrote {readable_path}"])


if __name__ == "__main__":
    main()
