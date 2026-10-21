"""Stage 1c for the grid: join every cell whose two inputs landed, and write the manifest.

    python -m psych_asr.cli.join_grid --stem <stem> --grid-id <id> [--stage1-dir DIR]
        [--typist T ...] [--stopwatch S ...] [--name-tagger N ...]

Run by slurm_jobs/stage1c_join_grid.sbatch, which the grid driver submits with afterany on
every align and diarize job. CPU only.

IN:  the run's Stage 1 directory (stage1/grid-<id>/): <stem>.<typist>+<stopwatch>.aligned.json
     and <stem>.<name-tagger>.rttm
OUT: per cell, <stem>.<cell>.diarized.json + <stem>.<cell>.transcript.txt beside them, and
     slurm_jobs/logs/grid-<id>/manifest.json

A CELL WHOSE INPUT DID NOT LAND IS "missing", NOT AN ERROR: an upstream job died, its
cells are reported, and every other cell still joins. A cell whose join raises is "failed",
recorded by exception TYPE only -- the messages name stem paths.

THE MANIFEST CARRIES NO STEM, NO PATH AND NO TEXT: axes, per-input states, and per cell
its status and the counts the join log already prints. It is the grid driver's only
source for its RELAY: lines. Nothing here scores, compares or ranks a cell.
"""

import json
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from .. import config, grid
from ..artifacts import naming

COUNT_KEYS = ("segments", "words", "turns", "labels", "unlabeled_segments", "unlabeled_words")


def build_parser():
    parser = ArgumentParser(description="Stage 1c for the grid: join every cell, write the manifest.")
    parser.add_argument("--stem", type=str, required=True,
                        help="the session stem; the inbox WAV's name without .wav")
    parser.add_argument("--stage1-dir", type=str, default=str(config.STAGE1_DIR),
                        help="this run's Stage 1 directory (default: %(default)s)")
    parser.add_argument("--grid-id", type=str, required=True,
                        help="the grid run's id; names the log directory the manifest goes to")
    parser.add_argument("--typist", action="append", default=None)
    parser.add_argument("--stopwatch", action="append", default=None)
    parser.add_argument("--name-tagger", action="append", default=None)
    return parser


def cell_line(record):
    """IN: one cell record   OUT: its log line. Names the cell, never the stem."""
    if record["status"] == grid.JOINED:
        counts = record["counts"]
        return f"cell {record['cell']} joined " + " ".join(f"{k} {counts[k]}" for k in COUNT_KEYS)
    if record["status"] == grid.FAILED:
        return f"cell {record['cell']} failed {record['error']}"
    return f"cell {record['cell']} missing aligned {record['inputs']['aligned']} rttm {record['inputs']['rttm']}"


def run_cells(cells, stage1_dir, stem, join):
    """IN: the Cells, the run's Stage 1 directory, the stem, and the join callable
    (join(aligned, rttm, stem, arm, output_dir) -> counts dict)
    OUT: one record per cell: {"cell", "status", "inputs", and "counts" or "error"}.

    The join is a parameter so a test can drive this without whisperx.
    """
    records = []
    for cell in cells:
        states = grid.classify(stage1_dir, stem, cell)
        record = {"cell": cell.name, "inputs": states}
        if states["aligned"] != grid.PRESENT or states["rttm"] != grid.PRESENT:
            record["status"] = grid.MISSING
        else:
            try:
                counts = join(naming.aligned_path(stage1_dir, stem, cell.half),
                              naming.rttm_path(stage1_dir, stem, cell.tagger),
                              stem, cell.name, stage1_dir)
                record["status"] = grid.JOINED
                record["counts"] = {k: int(counts[k]) for k in COUNT_KEYS}
            except (SystemExit, Exception) as error:   # noqa: BLE001 -- recorded by type only
                record["status"] = grid.FAILED
                record["error"] = type(error).__name__
        print(cell_line(record), flush=True)
        records.append(record)
    return records


def write_manifest(manifest, path):
    """IN: the manifest dict + destination   OUT: the Path. Atomic: tmp file, then rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, path)
    return path


def main(argv=None, join=None):
    args = build_parser().parse_args(argv)
    if not grid.GRID_ID_RE.fullmatch(args.grid_id):
        print("RELAY: grid join refused: bad grid id", flush=True)
        return 2
    try:
        typist_names = grid.select(args.typist, grid.TYPISTS, "typist")
        stopwatch_names = grid.select(args.stopwatch, grid.STOPWATCHES, "stopwatch")
        tagger_names = grid.select(args.name_tagger, tuple(grid.NAME_TAGGERS), "name-tagger")
    except SystemExit as error:
        print(error, file=sys.stderr)
        print("RELAY: grid join refused: unknown axis value", flush=True)
        return 2

    if join is None:
        # Imported here, not at the top: it pulls in whisperx, and the module must stay
        # importable without it.
        from .join_speakers import join_cell as join

    stage1_dir = Path(args.stage1_dir)
    inputs = grid.input_states(stage1_dir, args.stem, typist_names, stopwatch_names, tagger_names)
    records = run_cells(grid.cells(typist_names, stopwatch_names, tagger_names),
                        stage1_dir, args.stem, join)
    axes = {"typists": typist_names, "stopwatches": stopwatch_names, "taggers": tagger_names}
    manifest = grid.build_manifest(args.grid_id, axes, inputs, records)
    write_manifest(manifest, Path(config.WORKSPACE_ROOT) / grid.log_dir(args.grid_id) / "manifest.json")

    print("\n".join(grid.relay_summary(manifest)), flush=True)
    return grid.exit_code(manifest)


if __name__ == "__main__":
    sys.exit(main())
