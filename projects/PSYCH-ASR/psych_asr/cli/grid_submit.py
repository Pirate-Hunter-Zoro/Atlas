"""The Stage 1 grid driver: submit every job of one grid run, wait, report from the manifest.

    python -m psych_asr.cli.grid_submit --dry-run                    print the plan, call nothing
    python -m psych_asr.cli.grid_submit --wait                       the real run (in a Slurm job)
    python -m psych_asr.cli.grid_submit --typist parakeet:canary --name-tagger community-1 --wait
    python -m psych_asr.cli.grid_submit --rejoin <grid id> --wait    re-join a run's kept inputs

Run by slurm_jobs/stage1_grid.sbatch, which is what the relay files. A real run must itself
be a Slurm job: its SLURM_JOB_ID is the grid id, and so names the run's output directory
(stage1/grid-<id>/ under the data root) and its log directory (slurm_jobs/logs/grid-<id>/).

THE FLOW. Select the axes and refuse an unknown name; preflight the selected assets and
the inbox (exactly one WAV, because every child reads it); refuse if another grid driver
is live; submit the plan (psych_asr/grid.py) in order, recording each id in jobs.tsv; then,
with --wait, poll squeue until every job has left the queue, read the manifest the join
wrote, and print its RELAY: lines. A failed submission cancels what was already submitted.

STDLIB ONLY. Slurm is reached through `run`, which a test replaces.
"""

import json
import os
import shlex
import subprocess
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

from .. import config, grid, preflight

DRIVER_JOB_NAME = "stage1_grid"
MAX_QUEUE_FAILURES = 10


def build_parser():
    parser = ArgumentParser(description="Submit, wait for and report one Stage 1 grid run.")
    parser.add_argument("--typist", action="append", default=None,
                        help="typist(s); repeatable, colon lists accepted (default: all)")
    parser.add_argument("--stopwatch", action="append", default=None,
                        help="stopwatch(es); repeatable, colon lists accepted (default: all)")
    parser.add_argument("--name-tagger", action="append", default=None,
                        help="name-tagger(s); repeatable, colon lists accepted (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print every sbatch command with {key} placeholders and submit nothing")
    parser.add_argument("--preflight", dest="preflight", action="store_true", default=None,
                        help="run the asset and inbox preflight (default: on, except in a dry run)")
    parser.add_argument("--no-preflight", dest="preflight", action="store_false")
    parser.add_argument("--wait", action="store_true",
                        help="poll squeue until every job has finished, then report the manifest")
    parser.add_argument("--poll-seconds", type=float, default=120.0)
    parser.add_argument("--grid-id", type=str, default=None,
                        help="default: $SLURM_JOB_ID; a dry run falls back to local-<epoch>")
    parser.add_argument("--rejoin", type=str, default=None, metavar="GRID_ID",
                        help="submit only the join, for an existing run's directory")
    return parser


def _say(line, stream=None):
    print(line, file=stream or sys.stdout, flush=True)


def _run_preflight(axes, rejoin_id=None):
    """IN: the selected axes (+ the run being re-joined)   OUT: True when it passed.

    A rejoin needs no model, only the data root and the run's own directory.
    """
    exists, wavs = preflight.check_data()
    if rejoin_id is not None:
        run_dir = Path(config.DATA_ROOT) / "stage1" / f"grid-{rejoin_id}"
        if not exists:
            _say("RELAY: grid refused: data root PSYCH_ASR_DATA does not exist")
            return False
        if not run_dir.is_dir():
            _say("RELAY: grid refused: no output directory for that grid id")
            return False
        return True

    lines, results = preflight.run_file_tier(*axes)
    _say("\n".join(lines))
    statuses = [r.status for _, r in results]
    if not exists:
        _say("RELAY: preflight data root PSYCH_ASR_DATA does not exist")
    _say(preflight.summary_line(statuses, 0, wavs))
    return preflight.passed(statuses, 0, wavs)


def _other_drivers(run, own_id):
    """IN: the runner + this job's id   OUT: the ids of other live grid drivers, or None
    when squeue itself failed (which refuses, rather than risking two runs at once)."""
    user = os.environ.get("USER", "")
    p = run(["squeue", "-h", "-u", user, "-n", DRIVER_JOB_NAME, "-o", "%i"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        return None
    return [i.strip() for i in (p.stdout or "").split() if i.strip() and i.strip() != own_id]


def _cancel(run, ids):
    if ids:
        run(["scancel"] + list(ids), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)


def _record(tsv, job, job_id):
    new = not tsv.exists()
    with open(tsv, "a") as f:
        if new:
            f.write("key\trole\tid\n")
        f.write(f"{job.key}\t{job.role}\t{job_id}\n")


def _wait(run, sleep, ids, poll_seconds):
    """IN: the runner, the sleep, the submitted ids   OUT: True once none is queued,
    False after MAX_QUEUE_FAILURES squeue failures in a row."""
    failures = 0
    while True:
        p = run(["squeue", "-h", "-j", ",".join(ids), "-o", "%i"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode == 0:
            failures = 0
            if not (p.stdout or "").split():
                return True
        elif "Invalid job id" in (p.stderr or ""):
            # Every id has aged out of the controller: they are all gone.
            return True
        else:
            failures += 1
            if failures >= MAX_QUEUE_FAILURES:
                return False
        sleep(poll_seconds)


def main(argv=None, run=None, sleep=None):
    args = build_parser().parse_args(argv)
    run = run or subprocess.run
    sleep = sleep or time.sleep

    # ---- 1. axes ----
    try:
        typist_names = grid.select(args.typist, grid.TYPISTS, "typist")
        stopwatch_names = grid.select(args.stopwatch, grid.STOPWATCHES, "stopwatch")
        tagger_names = grid.select(args.name_tagger, tuple(grid.NAME_TAGGERS), "name-tagger")
    except SystemExit as error:
        _say(str(error), sys.stderr)
        _say("RELAY: grid refused: unknown axis value")
        return 2
    axes = (typist_names, stopwatch_names, tagger_names)

    # ---- the grid id ----
    rejoin = args.rejoin is not None
    own_id = os.environ.get("SLURM_JOB_ID", "")
    if rejoin:
        grid_id = args.rejoin
    else:
        grid_id = args.grid_id or own_id
    if not grid_id and args.dry_run:
        grid_id = f"local-{int(time.time())}"
    if not grid_id:
        # The driver must be a Slurm job, never a login-node process.
        _say("submit slurm_jobs/stage1_grid.sbatch; the driver runs as a Slurm job", sys.stderr)
        _say("RELAY: grid refused: no Slurm job id")
        return 2
    if not grid.GRID_ID_RE.fullmatch(grid_id):
        _say("RELAY: grid refused: bad grid id")
        return 2

    jobs = grid.plan(*axes, grid_id, rejoin=rejoin)

    # ---- 2. preflight ----
    do_preflight = args.preflight if args.preflight is not None else not args.dry_run
    preflight_ok = True
    if do_preflight:
        preflight_ok = _run_preflight(axes, args.rejoin if rejoin else None)
        if not preflight_ok and not args.dry_run:
            _say("RELAY: grid refused: preflight failed")
            return 2

    if args.dry_run:
        placeholders = {job.key: "{%s}" % job.key for job in jobs}
        for job in jobs:
            _say(" ".join(shlex.quote(a) for a in grid.sbatch_argv(job, placeholders)))
        _say(grid.plan_line(*axes))
        _say(f"RELAY: grid dry run jobs {len(jobs)}")
        return 0 if preflight_ok else 2

    # ---- 3. one driver at a time ----
    others = _other_drivers(run, own_id)
    if others is None:
        _say("RELAY: grid refused: squeue failed")
        return 2
    if others:
        _say("RELAY: grid refused: another grid driver is running")
        return 2

    # ---- 4. the run's log directory ----
    workspace = Path(config.WORKSPACE_ROOT)
    logs = workspace / grid.log_dir(grid_id)
    logs.mkdir(parents=True, exist_ok=True)
    tsv = logs / "jobs.tsv"
    # A rejoin reports only a manifest its own join wrote: one left by the first join has
    # this mtime, and an unchanged mtime afterwards means the rejoin wrote nothing.
    manifest_path = logs / "manifest.json"
    manifest_before = manifest_path.stat().st_mtime_ns if manifest_path.is_file() else None

    # ---- 5. submit, in plan order ----
    env = grid.child_env(os.environ, grid_id)
    ids = {}
    for job in jobs:
        p = run(grid.sbatch_argv(job, ids), cwd=str(workspace), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        job_id = (p.stdout or "").strip().split(";")[0].strip() if p.returncode == 0 else ""
        if not job_id.isdigit():
            _cancel(run, list(ids.values()))
            _say(f"RELAY: grid submit failed at {job.role}")
            return 2
        ids[job.key] = job_id
        _record(tsv, job, job_id)
        _say(f"submitted {job.key} {job_id}")

    # ---- 6. ----
    _say(grid.plan_line(*axes))
    _say(f"RELAY: grid submitted jobs {len(ids)}")
    if not args.wait:
        return 0

    # ---- 7. wait, then report from the manifest ----
    if not _wait(run, sleep, list(ids.values()), args.poll_seconds):
        _say("RELAY: grid lost the queue")
        return 2
    if (not manifest_path.is_file()
            or manifest_path.stat().st_mtime_ns == manifest_before):
        _say("RELAY: grid join wrote no manifest")
        return 1
    with open(manifest_path) as f:
        manifest = json.load(f)
    _say("\n".join(grid.relay_summary(manifest)))
    return grid.exit_code(manifest)


if __name__ == "__main__":
    sys.exit(main())
