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

FOUR STATES AND ONE FACT. The fact is the chain: a generation two hours from its
walltime submits the next one, which loads 406.7 GB on another node while this one
goes on answering, and only once that one says `COLIBRI-SERVE LOADED` does this one
give its node back. So `squeue` lists TWO generations for an hour at a time, and
the one to report is the one that can ANSWER -- warm beats loading, and between two
warm ones the one with more walltime left is the one that is not about to hand
over. The other is reported as a clause on the end of the sentence, because "this
server goes away in twenty minutes" is not sayable without it.

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
LOADED = "COLIBRI-SERVE LOADED"
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


def time_left(said):
    """Slurm's `%L` as seconds, or None where it does not mean a number.

    `UNLIMITED`, `INVALID` and a blank are all None, which is "nothing here
    limits it" rather than zero -- and the difference matters, because a mission
    is failed by a ceiling that has passed and a zero is a ceiling that passed
    the instant it was written. The spellings are Slurm's own: `d-hh:mm:ss`,
    `hh:mm:ss`, `mm:ss`.
    """
    said = (said or "").strip()
    if not said or not said[0].isdigit():
        return None
    days = 0
    if "-" in said:
        first, said = said.split("-", 1)
        try:
            days = int(first)
        except ValueError:
            return None
    parts = said.split(":")
    if len(parts) > 3:
        return None
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    secs = 0
    for n in nums:                      # mm:ss, hh:mm:ss -- rightmost is seconds
        secs = secs * 60 + n
    if len(nums) == 1:
        secs *= 60                      # a bare number is minutes
    return days * 86400 + secs


def _jobs():
    """Every generation of the chain Slurm knows about: id, state, node, reason, left.

    THE TIME LEFT IS WHY THIS ASKS FOR MORE THAN IT PAINTS. A colibrì turn runs
    inside this allocation -- `coli-code` steps into it with `srun --overlap` --
    so a job set going on the local model cannot outlive the walltime here, and
    nothing anywhere used to say what that was. `missions.py` stamps it on a
    mission at dispatch, and under a chain it is the ceiling of THIS generation
    rather than of the chain: the server comes back on another node, the client
    does not.
    """
    out = _run(["squeue", "-u", os.environ.get("USER", ""), "-n", JOB_NAME,
                "-h", "-o", "%i|%T|%N|%r|%L"])
    if not out:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 2 or not parts[0]:
            continue
        rows.append({"id": parts[0].strip(), "state": parts[1].strip().upper(),
                     "node": (parts[2].strip() if len(parts) > 2 else ""),
                     "reason": (parts[3].strip() if len(parts) > 3 else ""),
                     "left": time_left(parts[4] if len(parts) > 4 else "")})
    return rows


def _serving(rows):
    """Which generation to report, and which one is queued behind it.

    Warm beats loading; between two warm ones, more walltime left wins, because
    that is the one that is not handing over. A generation that has not warmed is
    still better than nothing and is the fallback rather than a refusal.
    """
    running = [r for r in rows if r["state"] == "RUNNING"]
    warm = [r for r in running if _tail(_out(r["id"]), READY)]
    pick = None
    if warm or running:
        pick = max(warm or running, key=lambda r: r["left"] or 0)
    elif rows:
        pick = rows[0]
    other = [r for r in rows if pick is None or r["id"] != pick["id"]]
    return pick, (other[0] if other else None)


def _out(job):
    """The names this generation's stdout could be under, best first.

    PER JOB, BECAUSE A CHAIN RUNS TWO OF THEM AT ONCE. One pair of files would
    have an overlapping successor judged by the incumbent's `COLIBRI-SERVE READY`
    -- a server reported warm while it is still reading off the filer. The fixed
    name is still answered second, so a job submitted by an older copy of
    `colibri_serve.sbatch` does not make the board go blind.
    """
    return ["colibri_serve_out-%s.txt" % job, "colibri_serve_out.txt"]


def _err(job):
    return ["colibri_serve_err-%s.txt" % job, "colibri_serve_err.txt"]


def _tail(names, needle, limit=200000):
    """Is this sentinel in that log. The tail only: these files grow all day."""
    where = log_dir()
    if not where:
        return False
    for name in ([names] if isinstance(names, str) else names):
        path = os.path.join(where, name)
        try:
            size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if size > limit:
                    fh.seek(size - limit)
                return needle in fh.read()
        except OSError:
            continue
    return False


def _next_clause(nxt):
    """What the generation behind this one is doing, as a clause or nothing.

    This is the whole of what a chain adds to the glass, and it is what makes
    "the server goes away in twenty minutes" sayable at all.
    """
    if not nxt:
        return ""
    if nxt["state"] != "RUNNING":
        return "; the next generation is queued"
    if _tail(_out(nxt["id"]), LOADED):
        return "; the next generation is loaded on %s and takes over in a moment" \
               % (nxt["node"] or "another node")
    return "; the next generation is loading on %s" % (nxt["node"] or "another node")


def _read():
    """The state, uncached. Four states, a sentence for each, and the chain."""
    rows = _jobs()
    job, nxt = _serving(rows)
    if not job:
        if time.time() - _ASKED["at"] <= SUBMIT_GRACE:
            # ASKED FOR AND NOT YET IN THE QUEUE. `sbatch` takes about a second
            # and the board polls four times a second, so without this a tap
            # reports "nothing is running" back to the person who just tapped it
            # -- which is how a second tap happens.
            return {"state": "queued", "job": None, "node": "", "next": None,
                    "left": None, "detail": "submitting the job"}
        return {"state": "off", "job": None, "node": "", "next": None,
                "left": None, "detail": "no server is running"}
    tail = _next_clause(nxt)
    said = {"job": job["id"], "node": job["node"], "left": job["left"],
            "next": (nxt["id"] if nxt else None)}
    if job["state"] != "RUNNING":
        said.update(state="queued", node="",
                    # Slurm's own word for why, not a guess. A 950 GB ask can pend
                    # indefinitely behind a nearly-full node and the reason is the
                    # only thing that says so.
                    detail=(job["reason"] or "waiting for an allocation") + tail)
        return said
    if _tail(_out(job["id"]), READY):
        said.update(state="warm",
                    detail="warm on %s" % (job["node"] or "a compute node") + tail)
        return said
    if _tail(_err(job["id"]), LISTENING):
        said.update(state="loading",
                    detail="listening, still warming — the first generation "
                           "runs at about a fifth of the steady rate" + tail)
        return said
    if _tail(_out(job["id"]), FAILED):
        said.update(state="off",
                    detail="the job is running but the engine failed to load" + tail)
        return said
    said.update(state="loading", detail="reading 429 GB off the filer" + tail)
    return said


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
