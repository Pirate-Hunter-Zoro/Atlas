"""The Stage 1 grid: 4 typists x 2 stopwatches x 5 name-taggers = 40 cells, as Slurm jobs.

STDLIB ONLY. Imports config, the typist registry and the naming helpers, nothing else, so
the plan can be built, printed and tested on a login node or a Mac.

THE GRID RUNS ARMS AND KEEPS EVERY OUTPUT. Nothing here scores, compares or ranks a cell.

THE JOB GRAPH, per run:

    transcribe:<t>  (4, GPU, the typist's env)
        --afterok + kill-on-invalid-dep-->  align:<t>+<s>  (8, GPU, asr_env)  --+
    diarize:<n>     (5, GPU, its own env, no dependency)  ---------------------+--afterany--> join (1, CPU)

A cell is one typist's words, timed by one stopwatch, labelled by one name-tagger. The
words come from 1a alone and the name-tagger reads no words, so 1b depends on nothing and
the 40 cells cost 17 GPU jobs rather than 40.

THE DEPENDENCY KINDS ARE NOT INTERCHANGEABLE. An align needs its typist's words, so it
waits with afterok, and --kill-on-invalid-dep cancels it if the typist failed: without
that it stays pending forever and the afterany join never starts. The join waits with
afterany on everything, so one dead arm still lets every other cell join; the dead arm's
cells show up as missing, which is a result rather than a silent gap.

ONE OUTPUT DIRECTORY PER RUN. Every child gets PSYCH_ASR_GRID=<grid id> (child_env), and
slurm_jobs/lib/job_env.sh turns that into stage1/grid-<id>/ under the data root. No run
overwrites an earlier one, and a missing input can only mean "did not land in this run".
Logs, jobs.tsv and manifest.json go to log_dir(<id>), which is open.
"""

import re
from collections import OrderedDict, namedtuple
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from . import config
from .artifacts import naming
from .asr import typists

# ---- the three axes, in canonical order ----
TYPISTS = tuple(typists.TYPISTS)
STOPWATCHES = tuple(config.STOPWATCHES)
# Name-tagger -> the stem of the Stage 1b recipe that writes <stem>.<name-tagger>.rttm.
NAME_TAGGERS = OrderedDict([
    (config.ARM_BASELINE, "stage1b_pyannote"),
    (config.ARM_DIARIZEN, "stage1b_diarizen"),
    (config.ARM_DIARIZEN_FREE, "stage1b_diarizen_free"),
    (config.ARM_SORTFORMER, "stage1b_sortformer"),
    (config.ARM_SORTFORMER_STREAMING, "stage1b_sortformer_streaming"),
])

TRANSCRIBE_SBATCH = "slurm_jobs/stage1a_transcribe.sbatch"
ALIGN_SBATCH = "slurm_jobs/stage1a_align.sbatch"
JOIN_SBATCH = "slurm_jobs/stage1c_join_grid.sbatch"

# A grid id becomes a directory name under the data root, so job_env.sh holds it to this
# and so does everything here.
GRID_ID_RE = re.compile(r"[A-Za-z0-9-]+")

# What a RELAY: line may be. The relay keeps the last 40 lines of a report and drops any
# line that looks like a path or a PHI artifact name, so a grid line carries no "/" and no
# "." at all, and the whole summary stays under the window.
RELAY_MAX_LINES = 35
RELAY_MAX_CHARS = 190
MAX_INPUT_LINES = 17
MAX_FAILED_LINES = 15

PRESENT, MISSING, EMPTY = "present", "missing", "empty"
JOINED, FAILED = "joined", "failed"


def select(values, known, axis):
    """IN: the values given on the command line (each may be a colon list), the known
    names in canonical order, and the axis name for the message
    OUT: a tuple of the chosen names, in canonical order, duplicates dropped.

    Nothing given means every known name. An unknown name raises SystemExit listing the
    known ones, before any GPU has been asked for.
    """
    chosen = []
    for value in values or ():
        for name in str(value).split(":"):
            name = name.strip()
            if name and name not in chosen:
                chosen.append(name)
    unknown = [name for name in chosen if name not in known]
    if unknown:
        raise SystemExit(f"Unknown {axis} {', '.join(unknown)}. Known: {', '.join(known)}")
    if not chosen:
        return tuple(known)
    return tuple(name for name in known if name in chosen)


class Cell(namedtuple("Cell", "typist stopwatch tagger")):
    """One grid cell. .name is "<typist>+<stopwatch>+<name-tagger>", the arm string its
    artifacts carry; .half is "<typist>+<stopwatch>", the aligned transcript's arm."""

    __slots__ = ()

    @property
    def name(self):
        return f"{self.typist}+{self.stopwatch}+{self.tagger}"

    @property
    def half(self):
        return f"{self.typist}+{self.stopwatch}"


def cells(typist_names, stopwatch_names, tagger_names):
    """IN: the three selected axes   OUT: every Cell, typist-major, then stopwatch, then tagger."""
    return [Cell(t, s, n) for t, s, n in product(typist_names, stopwatch_names, tagger_names)]


def log_dir(grid_id):
    """IN: a grid id   OUT: the run's log directory, relative to the workspace root."""
    return Path("slurm_jobs/logs") / f"grid-{grid_id}"


@dataclass
class Job:
    """One sbatch submission in the plan. Paths are relative to the workspace root."""

    key: str
    role: str                       # transcribe | align | diarize | join
    sbatch: str
    args: list = field(default_factory=list)
    out: str = ""
    err: str = ""
    after_ok: list = field(default_factory=list)
    after_any: list = field(default_factory=list)
    kill_on_invalid_dep: bool = False


def _logs(grid_id, name):
    base = log_dir(grid_id)
    return str(base / f"{name}_out.txt"), str(base / f"{name}_err.txt")


def _join_job(typist_names, stopwatch_names, tagger_names, grid_id, log_name, after_any):
    args = ["--grid-id", str(grid_id)]
    for flag, names in (("--typist", typist_names), ("--stopwatch", stopwatch_names),
                        ("--name-tagger", tagger_names)):
        for name in names:
            args += [flag, name]
    out, err = _logs(grid_id, log_name)
    return Job("join", "join", JOIN_SBATCH, args, out, err, after_any=list(after_any))


def plan(typist_names, stopwatch_names, tagger_names, grid_id, rejoin=False):
    """IN: the three selected axes + the grid id (+ rejoin)
    OUT: the list of Jobs, in an order where every dependency precedes its dependant.

    rejoin=True is the join alone, with no dependency, for a run whose GPU jobs finished
    and whose join died: it re-joins that run's kept inputs. Its logs carry the rejoin's
    own job id (%j), so the first join's logs are kept.
    """
    if rejoin:
        return [_join_job(typist_names, stopwatch_names, tagger_names, grid_id,
                          "stage1c_join_grid_%j", after_any=())]

    jobs = []
    for t in typist_names:
        out, err = _logs(grid_id, f"stage1a_transcribe_{t}")
        jobs.append(Job(f"transcribe:{t}", "transcribe", TRANSCRIBE_SBATCH, [t], out, err))
    for t in typist_names:
        for s in stopwatch_names:
            out, err = _logs(grid_id, f"stage1a_align_{t}_{s}")
            jobs.append(Job(f"align:{t}+{s}", "align", ALIGN_SBATCH, [t, s], out, err,
                            after_ok=[f"transcribe:{t}"], kill_on_invalid_dep=True))
    for n in tagger_names:
        out, err = _logs(grid_id, f"stage1b_{n}")
        jobs.append(Job(f"diarize:{n}", "diarize", f"slurm_jobs/{NAME_TAGGERS[n]}.sbatch",
                        [], out, err))
    waits_on = [job.key for job in jobs if job.role in ("align", "diarize")]
    jobs.append(_join_job(typist_names, stopwatch_names, tagger_names, grid_id,
                          "stage1c_join_grid", after_any=waits_on))
    return jobs


def sbatch_argv(job, ids):
    """IN: a Job + {key: Slurm job id} for the jobs already submitted
    OUT: the sbatch argv for it.

    A dry run passes {key: "{key}"}, so the printed dependency names the job it waits on.
    """
    argv = ["sbatch", "--parsable", "-o", job.out, "-e", job.err]
    dependencies = []
    if job.after_ok:
        dependencies.append("afterok:" + ":".join(str(ids[key]) for key in job.after_ok))
    if job.after_any:
        dependencies.append("afterany:" + ":".join(str(ids[key]) for key in job.after_any))
    if dependencies:
        argv.append("--dependency=" + ",".join(dependencies))
    if job.kill_on_invalid_dep:
        argv.append("--kill-on-invalid-dep=yes")
    return argv + [job.sbatch] + list(job.args)


def child_env(environ, grid_id):
    """IN: the driver's environment + the grid id   OUT: the environment for each child.

    Slurm's own variables are dropped, because a child submitted with the driver's
    SLURM_* set inherits the driver's job's settings; RELAY_* too, because each child's
    relay_trap sets its own; and GRID_*, which only the driver reads. PSYCH_ASR_GRID is
    what puts the child's outputs in this run's directory.
    """
    env = {key: value for key, value in environ.items()
           if not key.startswith(("SLURM_", "RELAY_", "GRID_"))}
    env["PSYCH_ASR_GRID"] = str(grid_id)
    return env


def input_state(path):
    """IN: a path   OUT: "missing", "empty" (zero bytes) or "present"."""
    path = Path(path)
    if not path.is_file():
        return MISSING
    return EMPTY if path.stat().st_size == 0 else PRESENT


def classify(stage1_dir, stem, cell):
    """IN: the run's Stage 1 directory + stem + a Cell   OUT: {"aligned": state, "rttm": state}."""
    return {
        "aligned": input_state(naming.aligned_path(stage1_dir, stem, cell.half)),
        "rttm": input_state(naming.rttm_path(stage1_dir, stem, cell.tagger)),
    }


def input_states(stage1_dir, stem, typist_names, stopwatch_names, tagger_names):
    """IN: the run's Stage 1 directory + stem + the three axes
    OUT: {"asr": {typist: state}, "aligned": {half: state}, "rttm": {tagger: state}}.

    Keyed by arm only, never by path, so the manifest it goes into carries no stem.
    """
    return {
        "asr": {t: input_state(naming.asr_path(stage1_dir, stem, t)) for t in typist_names},
        "aligned": {f"{t}+{s}": input_state(naming.aligned_path(stage1_dir, stem, f"{t}+{s}"))
                    for t in typist_names for s in stopwatch_names},
        "rttm": {n: input_state(naming.rttm_path(stage1_dir, stem, n)) for n in tagger_names},
    }


def build_manifest(grid_id, axes, inputs, records):
    """IN: the grid id, {"typists": [...], "stopwatches": [...], "taggers": [...]}, the
    input states, and one record per cell ({"cell", "status", "error"?, "counts"?})
    OUT: the manifest dict. No stem, no path, no text, no exception message."""
    totals = {"cells": len(records), JOINED: 0, MISSING: 0, FAILED: 0}
    for record in records:
        totals[record["status"]] += 1
    return {"grid_id": str(grid_id), "axes": {k: list(v) for k, v in axes.items()},
            "inputs": inputs, "cells": list(records), "totals": totals}


def _relay(text):
    """One RELAY: line, with "/" and "." made impossible and the length capped."""
    text = text.replace("/", "-").replace(".", "-")
    return ("RELAY: grid " + text)[:RELAY_MAX_CHARS]


def plan_line(typist_names, stopwatch_names, tagger_names):
    """IN: the three axes   OUT: the RELAY: line that states the plan's size."""
    count = len(typist_names) * len(stopwatch_names) * len(tagger_names)
    return _relay(f"plan typists {len(typist_names)} stopwatches {len(stopwatch_names)} "
                  f"taggers {len(tagger_names)} cells {count}")


def relay_summary(manifest):
    """IN: the manifest   OUT: at most 35 RELAY: lines, totals LAST.

    The relay keeps the last 40 lines, so the three totals lines are the ones that can
    never be cut off. Detail first: one line per input that did not land in this run, one
    per cell whose join raised (exception TYPE only -- a message can carry a stem).
    """
    axes, inputs = manifest["axes"], manifest["inputs"]
    lines = []
    for kind in ("asr", "aligned", "rttm"):
        for name, state in inputs.get(kind, {}).items():
            if state != PRESENT:
                lines.append(_relay(f"{kind} {name} {state}"))
    lines = lines[:MAX_INPUT_LINES]

    failed = [c for c in manifest["cells"] if c["status"] == FAILED]
    lines += [_relay(f"cell {c['cell']} failed {c.get('error') or 'unknown'}")
              for c in failed[:MAX_FAILED_LINES]]

    def landed(kind):
        states = list(inputs.get(kind, {}).values())
        return f"{sum(1 for s in states if s == PRESENT)} of {len(states)}"

    totals = manifest["totals"]
    lines += [
        plan_line(axes["typists"], axes["stopwatches"], axes["taggers"]),
        _relay(f"inputs asr {landed('asr')} aligned {landed('aligned')} rttm {landed('rttm')}"),
        _relay(f"cells {totals['cells']} joined {totals[JOINED]} missing {totals[MISSING]} "
               f"failed {totals[FAILED]}"),
    ]
    return lines[-RELAY_MAX_LINES:]


def exit_code(manifest):
    """IN: the manifest   OUT: 1 if any cell failed or none joined, else 0.

    A missing cell is reported and is not fatal: an upstream job that died is visible in
    the inputs lines, and every other cell still stands.
    """
    totals = manifest["totals"]
    return 1 if totals[FAILED] > 0 or totals[JOINED] == 0 else 0
