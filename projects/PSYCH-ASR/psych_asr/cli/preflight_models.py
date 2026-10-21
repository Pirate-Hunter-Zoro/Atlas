"""Check every staged model asset, by file and (with --load) by an offline load.

    python -m psych_asr.cli.preflight_models                 file tier + inbox count
    python -m psych_asr.cli.preflight_models --load          + offline loads (asr_env)
    python -m psych_asr.cli.preflight_models --skip-data     models only

scripts/stage_models.sh ends with this, slurm_jobs/preflight_models.sbatch runs it as a
job, and the grid driver runs its file tier before asking Slurm for any GPU.

Prints one line per asset (status, axis, name, path, file count, bytes), one RELAY: line
per asset that is not ok, and a final RELAY: summary. Exits 0 only when every asset is ok,
nothing failed to load, and the inbox holds exactly one WAV.

THE LOAD TIER NEVER DOWNLOADS. HF_HUB_OFFLINE is set before anything else is imported, and
a torchaudio bundle is loaded only when its .pth is already in TORCH_HOME -- torch would
otherwise fetch it, and HF_HUB_OFFLINE does not stop that. It runs what asr_env can:
ctranslate2 for the whisper directories, the two stopwatch bundles with one forward pass
each, community-1's pipeline, and a member listing of every .nemo archive. NeMo and
DiariZen need their own envs and are not loaded here.

A load failure records the exception TYPE only.
"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"
# pyannote.audio 4.x sends telemetry to otel.pyannote.ai unless this is 0.
os.environ["PYANNOTE_METRICS_ENABLED"] = "0"

import sys  # noqa: E402
import tarfile  # noqa: E402
from argparse import ArgumentParser  # noqa: E402
from pathlib import Path  # noqa: E402

from .. import config, grid, preflight  # noqa: E402

NEMO_MEMBERS = ("model_config.yaml", "model_weights.ckpt")


def build_parser():
    parser = ArgumentParser(description="Check the staged model assets, by file and by offline load.")
    parser.add_argument("--load", action="store_true",
                        help="also load what asr_env can, offline, on CPU")
    parser.add_argument("--skip-data", action="store_true",
                        help="do not count the inbox WAVs")
    parser.add_argument("--typist", action="append", default=None,
                        help="typist(s) to check; repeatable, colon lists accepted (default: all)")
    parser.add_argument("--stopwatch", action="append", default=None,
                        help="stopwatch(es) to check (default: all)")
    parser.add_argument("--name-tagger", action="append", default=None,
                        help="name-tagger(s) to check (default: all)")
    return parser


def _load_whisper(asset):
    import ctranslate2
    if not ctranslate2.contains_model(str(asset.path)):
        raise RuntimeError("not a CTranslate2 model directory")


def _load_stopwatch(asset):
    import torch
    import torchaudio
    bundle = torchaudio.pipelines.__dict__[config.STOPWATCHES[asset.name]]
    # The cache filename the preflight checked must be the one torch will look for, or a
    # job would fetch a file this check never saw.
    if bundle._path != config.STOPWATCH_CHECKPOINTS[asset.name]:
        raise AssertionError("bundle checkpoint name differs from config.STOPWATCH_CHECKPOINTS")
    model = bundle.get_model()
    model.eval()
    with torch.inference_mode():
        emissions, _ = model(torch.randn(1, int(bundle.sample_rate)))
    if emissions.dim() != 3:
        raise AssertionError("emissions are not 3-D")


def _load_pyannote(asset):
    from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained(str(asset.path))
    if pipeline is None:
        raise RuntimeError("Pipeline.from_pretrained returned nothing")


def _nemo_archive(asset):
    path = Path(asset.path)
    if path.is_file():
        return path
    archives = sorted(path.glob("*.nemo"))
    if len(archives) != 1:
        raise FileNotFoundError("expected exactly one .nemo archive")
    return archives[0]


def _list_nemo(asset):
    with tarfile.open(str(_nemo_archive(asset)), mode="r:*") as archive:
        names = {name[2:] if name.startswith("./") else name for name in archive.getnames()}
    absent = [m for m in NEMO_MEMBERS if m not in names]
    if absent:
        raise KeyError("archive lacks a required member")


def load_checks(results):
    """IN: [(Asset, Result)] from the file tier   OUT: (log lines, {asset name: error type}).

    Only assets whose files passed are loaded. Each load is isolated: one failure is
    recorded by type and the rest still run.
    """
    lines, failures = [], {}
    for asset, result in results:
        if result.status != preflight.OK:
            continue
        loader = None
        if asset.kind == "whisper":
            loader = _load_whisper
        elif asset.axis == "stopwatch":
            loader = _load_stopwatch
        elif asset.kind == "pyannote":
            loader = _load_pyannote
        elif asset.kind in ("nemo-dir", "nemo-file"):
            loader = _list_nemo
            lines.append(f"{asset.axis} {asset.name}: full load not attempted (needs nemo_env)")
        elif asset.kind == "diarizen":
            lines.append(f"{asset.axis} {asset.name}: load not attempted (needs diarizen_env)")
        if loader is None:
            continue
        try:
            loader(asset)
            lines.append(f"loaded {asset.axis} {asset.name}")
        except (SystemExit, Exception) as error:   # noqa: BLE001 -- recorded by type only
            failures[(asset.axis, asset.name)] = type(error).__name__
            lines.append(f"{preflight.LOAD_FAILED} {asset.axis} {asset.name} {type(error).__name__}")
    return lines, failures


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        typist_names = grid.select(args.typist, grid.TYPISTS, "typist")
        stopwatch_names = grid.select(args.stopwatch, grid.STOPWATCHES, "stopwatch")
        tagger_names = grid.select(args.name_tagger, tuple(grid.NAME_TAGGERS), "name-tagger")
    except SystemExit as error:
        print(error, file=sys.stderr)
        print("RELAY: preflight refused: unknown axis value", flush=True)
        return 2

    lines, results = preflight.run_file_tier(typist_names, stopwatch_names, tagger_names)
    print("\n".join(lines), flush=True)

    failures = {}
    if args.load:
        load_lines, failures = load_checks(results)
        print("\n".join(load_lines), flush=True)
        for (axis, name), error_type in failures.items():
            print(f"RELAY: preflight {preflight.LOAD_FAILED} {axis} {name} {error_type}", flush=True)

    wavs = None
    if not args.skip_data:
        exists, wavs = preflight.check_data()
        if not exists:
            print("RELAY: preflight data root PSYCH_ASR_DATA does not exist", flush=True)

    statuses = [r.status for _, r in results]
    print(preflight.summary_line(statuses, len(failures), wavs), flush=True)
    return 0 if preflight.passed(statuses, len(failures), wavs) else 1


if __name__ == "__main__":
    sys.exit(main())
