"""Fetch the torchaudio forced-alignment bundles into TORCH_HOME. Login node only.

    TORCH_HOME=<models>/torch_home python -m psych_asr.cli.warm_align_cache
    TORCH_HOME=<models>/torch_home python -m psych_asr.cli.warm_align_cache --stopwatch wav2vec2-large

With no --stopwatch, every stopwatch in config.STOPWATCHES. scripts/stage_models.sh runs
it that way.

FORCED ALIGNMENT IS NOT A HUGGING FACE DOWNLOAD. For English, WhisperX resolves its
alignment model to a TORCHAUDIO bundle, fetched from download.pytorch.org into the Torch
hub cache -- not from the Hugging Face Hub. HF_HUB_OFFLINE=1 therefore does NOT cover this
fetch, which is why the bundles are staged here rather than by the job that needs them.

torch writes each bundle's .pth (config.STOPWATCH_CHECKPOINTS) into a hub/checkpoints
subfolder of TORCH_HOME, and a re-run reuses a cached file rather than fetching it again.
EVERY JOB MUST EXPORT THE SAME TORCH_HOME -- exporting the variable, not merely having the
files on disk, is what makes torch reuse the cache instead of re-fetching into ~/.cache.
"""

import os
from argparse import ArgumentParser
from pathlib import Path

import torchaudio

from .. import config


def build_parser():
    parser = ArgumentParser(description="Stage the torchaudio forced-alignment bundles. Login node only.")
    parser.add_argument("--stopwatch", action="append", default=None,
                        choices=sorted(config.STOPWATCHES),
                        help="which bundle to fetch; repeatable (default: every stopwatch)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    # Canonical order, duplicates dropped, so the log reads the same however it was asked.
    wanted = [name for name in config.STOPWATCHES if not args.stopwatch or name in args.stopwatch]
    torch_home = Path(os.environ.get("TORCH_HOME") or config.TORCH_HOME)

    for short_name in wanted:
        bundle_name = config.STOPWATCHES[short_name]
        bundle = torchaudio.pipelines.__dict__[bundle_name]
        bundle.get_model()
        labels = bundle.get_labels()
        checkpoint = torch_home / "hub" / "checkpoints" / config.STOPWATCH_CHECKPOINTS[short_name]
        print(
            f"Stopwatch: {short_name}\n"
            f"Bundle: {bundle_name}\n"
            f"Sample rate: {bundle.sample_rate}\n"
            f"Number of labels: {len(labels)}\n"
            f"Checkpoint {checkpoint.name} in TORCH_HOME: {'yes' if checkpoint.is_file() else 'NO'}",
            flush=True,
        )
    print(f"TORCH_HOME: {torch_home}", flush=True)


if __name__ == "__main__":
    main()
