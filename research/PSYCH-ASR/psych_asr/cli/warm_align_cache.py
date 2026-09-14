"""Fetch the torchaudio forced-alignment bundle into TORCH_HOME. Login node only.

    TORCH_HOME=<models>/torch_home python -m psych_asr.cli.warm_align_cache

FORCED ALIGNMENT IS NOT A HUGGING FACE DOWNLOAD. For English, WhisperX resolves its
alignment model to the TORCHAUDIO bundle WAV2VEC2_ASR_BASE_960H, fetched from
download.pytorch.org into the Torch hub cache -- not from the Hugging Face Hub. Setting
HF_HUB_OFFLINE=1 therefore does NOT protect this path, and on a compute node with no
outbound internet it stalls exactly the way an unstaged Hub model does.

torch writes the 360 MB wav2vec2_fairseq_base_ls960_asr_ls960.pth into a hub/checkpoints
subfolder of TORCH_HOME, and a re-run reuses it silently. EVERY JOB MUST EXPORT THE SAME
TORCH_HOME -- exporting the variable, not merely having the files on disk, is what makes
torch reuse the cache instead of re-fetching into ~/.cache.
"""

import os
from argparse import ArgumentParser

import torchaudio

from .. import config


def build_parser():
    parser = ArgumentParser(description="Stage the torchaudio forced-alignment bundle. Login node only.")
    parser.add_argument("--stopwatch", type=str, default="wav2vec2-base",
                        choices=sorted(config.STOPWATCHES),
                        help="which bundle to fetch (default: %(default)s, whisperx's own "
                             "default for English). The grid's second stopwatch needs its own "
                             "run of this, on the login node, before any job asks for it")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    name = config.STOPWATCHES[args.stopwatch]

    bundle = torchaudio.pipelines.__dict__[name]
    bundle.get_model()
    labels = bundle.get_labels()
    print(
        f"Bundle: {name}\n"
        f"Sample rate: {bundle.sample_rate}\n"
        f"Number of labels: {len(labels)}\n"
        f"TORCH_HOME: {os.environ.get('TORCH_HOME', 'unset')}",
        flush=True,
    )


if __name__ == "__main__":
    main()
