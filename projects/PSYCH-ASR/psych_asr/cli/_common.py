"""Argument-parser pieces every entry point shares.

STDLIB ONLY.

--outdir, --num-speakers and --arm are declared once here, with one help text and one
default each, so a default cannot drift between two jobs that are supposed to agree.
"""

from pathlib import Path

from .. import config


def add_output_dir(parser, default=config.STAGE1_DIR):
    """--outdir, defaulting to config.STAGE1_DIR: the run's Stage 1 directory under the data
    root (stage1/, or stage1/grid-<id>/ for a grid child). Session content is PHI and the
    data root is outside git; nothing in Stage 1 may be written outside it."""
    parser.add_argument("--outdir", type=str, default=str(default),
                        help="where to write the artifacts (default: %(default)s)")


def add_num_speakers(parser, default=2, help_text=None):
    """--num-speakers. Every pilot session is a known dyad, so pinning the count removes
    both clustering failure modes -- splitting one person in two, merging two into one --
    for free. The flag exists rather than a hardcoded 2 in case a session turns out to have
    a third person present."""
    parser.add_argument(
        "--num-speakers", type=int, default=default,
        help=help_text or ("exact speaker count; every pilot session is a known dyad, and "
                           "pinning it removes both clustering failure modes for free"),
    )


def add_arm(parser, default=None, help_text=None):
    """--arm: the name written into every output filename from Stage 1b onward, so which
    model produced which transcript is a property of the file rather than of a note."""
    parser.add_argument("--arm", type=str, default=default,
                        help=help_text or "name used in the output filenames; identifies which "
                                          "diarizer produced them")


def prepare_output_dir(outdir):
    """IN: the --outdir string   OUT: the Path, created if it did not exist."""
    path = Path(outdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def report(lines):
    """IN: a list of log lines (or one string)   OUT: nothing; printed, flushed.

    Flushed because these are read out of a Slurm log while the job is still running, and
    an unflushed buffer makes a live job look hung.
    """
    if isinstance(lines, str):
        lines = [lines]
    print("\n".join(lines), flush=True)
