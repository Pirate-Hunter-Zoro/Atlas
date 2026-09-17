"""Is the local model up, and what is it doing on its way there.

`coli-code` is the recipe the `colibri` agent runs, and it needs a server: a
Slurm job on a compute node holding 429 GB of weights warm behind a loopback
gateway. On a terminal the answer to "there is no server" is one line of advice
-- *start one: coli-up* -- and on an iPad that is a dead end.

So this module answers two questions and nothing else. WHICH OF FOUR STATES the
server is in, in words a board can paint; and START ONE, returning at once.

    off      nothing is submitted. There is a control, and it offers to start one
    queued   the job exists and Slurm has not run it yet; the reason is Slurm's
    loading  the job is running. 429 GB off the filer, then a warm-up generation
    warm     it has answered a request, which is the only proof that it can

`squeue` IS THE SOURCE OF TRUTH and nothing here writes a state file. A state
file goes stale the moment a job ends and `squeue` never does -- the same choice
`coli-up`, `coli-code` and the `ollama-*` three already made. It is asked once
per poll and the board polls four times a second, so the answer is cached for
`TTL` seconds; `machines.held_nodes` is the pattern, not the function.

THE DIFFERENCE BETWEEN `loading` AND `warm` IS WORTH PAINTING and cannot be got
from Slurm. The gateway binds its port before it loads anything -- deliberately,
so a bad argument fails in milliseconds rather than after 429 GB -- so a TCP
probe answers instantly and says nothing about whether the thing can generate.
The job prints two lines instead, and they are what is read here: `API listening
on` when the engine is up, and `COLIBRI-SERVE READY` when it has completed a
real generation. Between them the model answers at roughly a fifth of its steady
rate, which is worth knowing before somebody sends an hour of work into it.
"""

import os
import subprocess
import time

from . import atlas


# The job, the workspace it belongs to, and the two sentinels. All four match
# `scripts/colibri-env.sh`, which is the one file in that project that answers
# "where is colibri and what does it serve" -- so every one of them is read from
# the environment first, exactly as that file does it.
JOB_NAME = os.environ.get("COLI_JOB_NAME") or "colibri_serve"
WORKSPACE = "libr-local-llm"
LISTENING = "API listening on"
READY = "COLIBRI-SERVE READY"
FAILED = "COLIBRI-SERVE FAILED"

TTL = 15.0
_CACHE = {"at": 0.0, "was": None}

# The window in which a start that has been asked for but is not yet in the
# queue still says so. `sbatch` returns a job id in about a second, so this is
# short -- and it is in memory rather than on disk for the same reason the rest
# of this file reads `squeue`: a record of an intention outlives the intention.
SUBMIT_GRACE = 45.0
_ASKED = {"at": 0.0}


def log_dir():
    """Where the serve job writes, or None if this machine has not got the tree.

    `COLI_LOG_DIR` first, because that is what the project's own scripts honour.
    Otherwise the workspace's own `slurm_jobs/logs`, found by the walk rather
    than by counting directories: nothing registers a workspace, and a machine
    with half the tree checked out has no colibri at all.
    """
    said = os.environ.get("COLI_LOG_DIR")
    if said:
        return said
    try:
        for w in atlas.workspaces():
            if w["dir"] == WORKSPACE:
                return os.path.join(w["root"], "slurm_jobs", "logs")
    except Exception:                                        # noqa: BLE001
        return None
    return None


def _run(args, timeout=10):
    """A command's stdout, or None if it could not be asked at all.

    One place, so a test can put a `squeue` in front of this module without a
    cluster, and so "no Slurm here" is one answer rather than four.
    """
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def _job():
    """The serve job as Slurm sees it: id, state, node, reason. Or None."""
    out = _run(["squeue", "-u", os.environ.get("USER", ""), "-n", JOB_NAME,
                "-h", "-o", "%i|%T|%N|%r"])
    if not out:
        return None
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 2 or not parts[0]:
            continue
        job = {"id": parts[0].strip(), "state": parts[1].strip().upper(),
               "node": (parts[2].strip() if len(parts) > 2 else ""),
               "reason": (parts[3].strip() if len(parts) > 3 else "")}
        # A RUNNING job wins over a pending one: the queue can hold both while
        # one is being replaced, and the one that can answer is the answer.
        if job["state"] == "RUNNING":
            return job
        if job["state"] in ("PENDING", "CONFIGURING"):
            return job
    return None


def _tail(name, needle, limit=200000):
    """Is this sentinel in that log. The tail only: these files grow all day."""
    where = log_dir()
    if not where:
        return False
    path = os.path.join(where, name)
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            if size > limit:
                fh.seek(size - limit)
            return needle in fh.read()
    except OSError:
        return False


def _read():
    """The state, uncached. Four states, and a sentence for each."""
    job = _job()
    if not job:
        if time.time() - _ASKED["at"] <= SUBMIT_GRACE:
            # ASKED FOR AND NOT YET IN THE QUEUE. `sbatch` takes about a second
            # and the board polls four times a second, so without this a tap
            # reports "nothing is running" back to the person who just tapped it
            # -- which is how a second tap happens.
            return {"state": "queued", "job": None, "node": "",
                    "detail": "submitting the job"}
        return {"state": "off", "job": None, "node": "",
                "detail": "no server is running"}
    if job["state"] != "RUNNING":
        return {"state": "queued", "job": job["id"], "node": "",
                # Slurm's own word for why, not a guess. A 950 GB ask can pend
                # indefinitely behind a nearly-full node and the reason is the
                # only thing that says so.
                "detail": job["reason"] or "waiting for an allocation"}
    if _tail("colibri_serve_out.txt", READY):
        return {"state": "warm", "job": job["id"], "node": job["node"],
                "detail": "warm on %s" % (job["node"] or "a compute node")}
    if _tail("colibri_serve_err.txt", LISTENING):
        return {"state": "loading", "job": job["id"], "node": job["node"],
                "detail": "listening, still warming — the first generation "
                          "runs at about a fifth of the steady rate"}
    if _tail("colibri_serve_out.txt", FAILED):
        return {"state": "off", "job": job["id"], "node": job["node"],
                "detail": "the job is running but the engine failed to load"}
    return {"state": "loading", "job": job["id"], "node": job["node"],
            "detail": "reading 429 GB off the filer"}


def status(fresh=False):
    """The state, cached. Safe to ask on every poll."""
    now = time.time()
    if fresh or _CACHE["was"] is None or now - _CACHE["at"] > TTL:
        _CACHE["was"] = _read()
        _CACHE["at"] = now
    return dict(_CACHE["was"])


def forget():
    """Drop the cache, because something just changed it."""
    _CACHE["at"] = 0.0


def up_command():
    """`coli-up`, if this machine has it. Named so a refusal can say what is missing."""
    import shutil
    return shutil.which("coli-up")


def submitted():
    """Somebody has just asked for a start that Slurm has not listed yet.

    Set by `spawn.wake_colibri` and read by `_read`, in memory rather than on
    disk for the same reason the rest of this file reads `squeue`: a record of
    an intention outlives the intention.
    """
    _ASKED["at"] = time.time()
    forget()
