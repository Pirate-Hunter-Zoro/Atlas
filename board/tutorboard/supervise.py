"""Keeping the board up, and keeping the machine it is up on.

Two failures, and nothing in here used to watch for either of them.

The first is a process dying: `serve.py` on an exception, the tutor daemon on an
OOM, either of them on a `kill` somebody meant for something else. The record on
disk goes on naming a pid that is gone, the iPad says the tutor stopped, and that
is where it stays -- because a login was the only moment anything looked, and the
person holding the iPad is not logging in to anything.

The second is the allocation ending, which takes the node, the board, the tutor
and `tailscaled` with it and leaves no process anywhere to notice.

A Slurm job answers the second, and that is what makes the first worth writing: a
batch job that submits its own successor with `--dependency=afterany:<itself>`
before it does anything else is an allocation that renews itself for as long as
the queue will have it, and its script is a supervisor that lives exactly as long
as the machine it supervises. `scripts/install-autostart.sh` says a supervisor is
the wrong shape for a compute node, and it is right about the shape it refused --
one that outlives the machine and comes back to a machine that is not there. This
one IS the machine: when the allocation ends the supervisor ends with it, and the
successor that was queued seven days ago is the thing that brings the board back.

Nothing in this module starts, stops or kills anything. It decides, off records
and a clock, so every decision is testable without a cluster; `cmd_watch` and
`cmd_serve` in `bin/tutor` do the acting.
"""

import json
import os
import subprocess
import time

from . import paths, processes


# The one name every generation of the chain carries. `squeue --name` is how the
# chain is found, how a second chain is refused, and how `scancel` ends it, so it
# is a constant rather than a string typed in four places.
JOB_NAME = "tutor-serve"

SCRIPT = os.path.join(paths.TOOL, "slurm", "tutor-serve.sbatch")

# What the chain knows about itself, in the shared state directory rather than in
# the repository: it is machine-local truth about machines, no clone should carry
# it, and every node reads the same copy.
RECORD = os.path.join(paths.STATE_DIR, "serve.json")
WATCH = os.path.join(paths.STATE_DIR, "watch.json")

# THE ONLY WAY A SELF-RENEWING CHAIN IS ALLOWED TO EXIST: something that stops it
# which is not a race. `scancel` alone is not enough -- cancelling the running
# generation is exactly what the successor's `afterany` dependency is waiting
# for, so a chain cancelled one job at a time comes straight back, which is the
# correct behaviour for a walltime and the wrong one for a person who wants it to
# stop. So a stop is a FILE first and a cancel second: the file is checked before
# any successor is submitted and on every pass of the watch loop.
STOP = os.path.join(paths.STATE_DIR, "serve-stopped")

# How often the watch loop looks. Twenty seconds is the answer to "how long is a
# board allowed to be dead", and the cost of it is one socket connect and one
# /health per workspace, which is a quiet request the board does not even log.
POLL = 20.0

# A board that is alive and not answering is the failure a pid check cannot see,
# and one miss is not evidence: a board writing a large slate PNG can be a second
# late. Two consecutive misses, twenty seconds apart, is.
HEALTH_MISSES = 2

# What a repair waits before trying again, per workspace, climbing. A tutor that
# cannot start -- no allowance, no command on the path, a repository mid-rebase --
# must not be started every twenty seconds for seven days; a board that died once
# must come back at once.
BACKOFF = (0, 15, 30, 60, 120, 300)

# How often the loop asks whether its own successor is still queued. The chain
# dies quietly if a submission was refused (a queue limit, a controller restart),
# and a chain that has silently stopped being a chain is the one failure of this
# whole arrangement that nobody would see until the board went dark.
SUCCESSOR_EVERY = 300.0

# HOW OLD A RECORD MAY BE AND STILL DESCRIBE SOMETHING THAT WAS JUST SERVING.
#
# `live/.board.json` is swept on every resume, so a surviving one is recent by
# construction. `live/agent.json` is never swept -- it is kept on purpose, so the
# board can say "tutor stopped" rather than "no tutor here" -- and a record from a
# node whose allocation ended two days ago reads exactly like one from a node
# whose allocation ended a minute ago. Measured on this machine while this was
# written: a TRD-EHR record saying `listening` on compute300, forty-two hours
# after that node stopped being anybody's.
#
# A listening daemon rewrites its record at least every `board wait` timeout, so
# an hour is many missed beats; it is also longer than any handover has to wait
# for the successor to be scheduled.
ADOPT_WINDOW = 3600

# How long before the walltime Slurm is asked to warn the job, so the tutors can
# write their handoffs and the transcript can be pushed while there is still a
# machine to do it on. Five minutes: a handoff is one model turn and `bin/tutor`
# allows it 600 s, so this is not enough for a pathological one and is enough for
# every one that has been measured.
HANDOVER_WARNING = 300


# ---------------------------------------------------------------------------
# What is wrong here, if anything
# ---------------------------------------------------------------------------
def board_verdict(record, host, pid_alive, answering, misses):
    """What to do about the board this record describes.

    - `none`      no record: nothing was ever started here, or `board stop`
                  removed it, which is a person saying no. Both mean leave it.
    - `elsewhere` the record names another node. On a shared home that is the
                  common case and touching it is how a stranger's process gets
                  killed.
    - `ok`        alive and answering.
    - `waiting`   alive, not answering, and not for long enough to act on.
    - `hung`      alive, not answering, twice. Needs a stop before a start.
    - `revive`    the pid is gone.
    """
    if not record:
        return "none"
    if record.get("node") and record["node"] != host:
        return "elsewhere"
    if not pid_alive:
        return "revive"
    if answering:
        return "ok"
    return "hung" if misses >= HEALTH_MISSES else "waiting"


def tutor_verdict(record, host, pid_alive, now=None):
    """What to do about the tutor this record describes.

    The distinction this exists to make is between a daemon that DIED and one
    that was told to go. They leave different records, and the difference is the
    whole safety of restarting anything automatically:

    - `tutor headless --stop` and `tutor agent stop` REMOVE the record, or leave
      `state: stopped` with `restarting` false. A person said no. Reviving that
      is the watchdog arguing with its owner, and it never does.
    - `tutor restart --tutors` writes `restarting: true` and a `stopped_at`
      before it signals, precisely so the board can tell a bounce from a death.
      That is given the same grace the board gives it, and only then treated as
      a start that failed.
    - a start in flight writes `waking` with a `waking_at`, which expires on its
      own; `processes.waking_now` owns that window.
    - anything else with a dead pid is a death, and is the case this module was
      written for.
    """
    if not record:
        return "none"
    if record.get("host") and record["host"] != host:
        return "elsewhere"
    if record.get("mode") == "interactive":
        # Somebody's terminal. Not a daemon, not ours to bounce.
        return "somebody's"
    if record.get("restarting"):
        return "reattaching" if _within(record.get("stopped_at"),
                                        _reattach_grace(), now) else "revive"
    state = record.get("state")
    if state == "stopped":
        # A HANDOVER IS NOT A STOP, AND THE DIFFERENCE IS ONE FIELD.
        #
        # The walltime warning makes every daemon write its handoff and exit,
        # which leaves exactly the record a person's `tutor agent stop` leaves --
        # and one of those must be picked back up by the next generation while
        # the other must never be. So the thing that asks for the stop says
        # which it was: `hand_over` writes `handover` first, the daemon's own
        # exit merges `state: stopped` over the top of it, and whoever brings the
        # tutor back clears it. Without the flag a seven-day handover ends the
        # lesson; with it honoured regardless of node, a chain that lands back on
        # the same machine picks up where it left off too, which on a
        # single-node partition is the common case rather than the exotic one.
        return ("revive" if record.get("handover")
                and _within(record.get("last_seen"), ADOPT_WINDOW, now)
                else "stopped")
    if state == "waking":
        return "waking" if processes.waking_now(record) else "revive"
    return "ok" if pid_alive else "revive"


def left_behind(record, now=None):
    """Was this tutor serving when its machine went, rather than told to stop?

    Asked of a record from a node that is no longer an allocation of yours,
    which is the one case where the pid proves nothing at all -- so the clock is
    the evidence, and `ADOPT_WINDOW` is what it is asked.
    """
    if not record or not record.get("state"):
        return False
    if not _within(record.get("last_seen"), ADOPT_WINDOW, now):
        return False
    if record["state"] == "stopped":
        return bool(record.get("handover"))
    return True


def _reattach_grace():
    """How long a bounce is believed. The board's own number, read where it lives.

    Imported here rather than at the top of the file: `tutor resume --quiet` runs
    on every interactive shell and pays for every import this module makes.
    """
    try:
        from .lesson.state import REATTACH_GRACE
        return REATTACH_GRACE
    except Exception:                                        # noqa: BLE001
        return 180


def _within(then, window, now=None):
    try:
        since = (time.time() if now is None else now) - float(then or 0)
    except (TypeError, ValueError):
        return False
    return 0 <= since <= window


def next_try(attempts):
    """How long to wait before repairing this thing again, having tried already."""
    if attempts <= 0:
        return BACKOFF[0]
    return BACKOFF[min(attempts, len(BACKOFF) - 1)]


# ---------------------------------------------------------------------------
# The chain
# ---------------------------------------------------------------------------
def stopped():
    """Has somebody told the chain to stop? Nothing submits a successor if so."""
    return os.path.exists(STOP)


def mark_stopped(why=""):
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    with open(STOP, "w", encoding="utf-8") as fh:
        fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), why))


def clear_stopped():
    try:
        os.remove(STOP)
    except OSError:
        pass


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def chain_record():
    return _read(RECORD)


def note_generation(**kw):
    """Record which generation of the chain is running, and where."""
    rec = chain_record()
    rec.update(kw)
    _write(RECORD, rec)
    return rec


def watch_record():
    return _read(WATCH)


def note_watch(**kw):
    rec = watch_record()
    rec.update(kw)
    _write(WATCH, rec)
    return rec


def serve_jobs(user=None):
    """Every generation of the chain Slurm currently knows about.

    None means Slurm did not answer, which is not the same as no jobs and must
    not be treated as one: a controller that is briefly unreachable would
    otherwise look like a chain that had ended, and the repair for that is to
    submit another one.
    """
    user = user or os.environ.get("USER") or ""
    try:
        p = subprocess.run(["squeue", "-h", "-u", user, "--name", JOB_NAME,
                            "-o", "%i|%T|%N|%E|%L|%P"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    rows = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        bits = line.strip().split("|")
        if len(bits) < 6 or not bits[0]:
            continue
        rows.append({"id": bits[0], "state": bits[1], "node": bits[2],
                     "dependency": bits[3], "left": bits[4], "partition": bits[5]})
    return rows


def successor_of(job_id, rows):
    """The queued generation waiting on this one, if it is there.

    Matched on the dependency rather than on submission order, because a requeued
    job runs its script again from the top and must not submit a second
    successor -- `%E` reads `afterany:2073166(unfulfilled)`, which is the only
    evidence that the one already queued belongs to this generation.
    """
    for r in rows or []:
        if r["state"] in ("PENDING", "CONFIGURING") and str(job_id) in (r["dependency"] or ""):
            return r
    return None


def submit(partition, walltime, cpus, mem, after=None, log=None, chdir=None,
           env=None):
    """Put one generation of the chain in the queue. Returns (job id, error).

    Every resource is passed on the command line even though the script carries
    the same values as `#SBATCH` lines. The directives are what a hand-submitted
    `sbatch slurm/tutor-serve.sbatch` gets; these are what the config says, and
    one of the two has to win where they disagree.
    """
    if not os.path.exists(SCRIPT):
        return None, "no job script at %s" % SCRIPT
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    out = log or os.path.join(paths.STATE_DIR, "serve-%j.log")
    cmd = ["sbatch", "--parsable",
           "--job-name", JOB_NAME,
           "--partition", partition,
           "--time", walltime,
           "--nodes", "1", "--ntasks", "1",
           "--cpus-per-task", str(cpus),
           "--mem", str(mem),
           # Slurm signals the batch shell this long before the walltime, which
           # is the only warning a generation gets that its machine is about to
           # stop being its machine. `B:` so it reaches the script rather than
           # the job's other steps -- a tutor turn is a step, and a USR1 to a
           # model call in progress is a lost card.
           "--signal", "B:USR1@%d" % HANDOVER_WARNING,
           # A node failure should put the chain back in the queue rather than
           # end it, and the log should survive that.
           "--requeue", "--open-mode", "append",
           "--output", out]
    if chdir:
        cmd += ["--chdir", chdir]
    if after:
        cmd += ["--dependency", "afterany:%s" % after]
    cmd.append(SCRIPT)
    run_env = dict(os.environ)
    # WHERE THE TOOL IS, HANDED OVER EXPLICITLY. Slurm copies a batch script to
    # its own spool directory before running it, so `$0` inside the job is that
    # copy and a path derived from it points at nothing. The script has a
    # fallback (`scontrol show job` still reports the submitted path), and this
    # is the answer that does not depend on the controller being asked.
    run_env["TUTOR_BOARD_TOOL"] = paths.TOOL
    run_env.update(env or {})
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=run_env, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    said = p.stdout.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        return None, said or "sbatch exited %d" % p.returncode
    # `--parsable` prints the id, and `id;cluster` on a federation.
    return said.split(";")[0].strip(), None


def cancel(user=None):
    """End the chain: every generation of it, running and queued, at once.

    One `scancel` for the whole name, deliberately. Cancelling them one at a
    time is how a chain survives being cancelled -- take the running one out and
    its successor's `afterany` is satisfied, which is the chain working exactly
    as designed at the worst possible moment.
    """
    user = user or os.environ.get("USER") or ""
    try:
        p = subprocess.run(["scancel", "--name", JOB_NAME, "-u", user],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    if p.returncode != 0:
        return p.stdout.decode("utf-8", "replace").strip() or "scancel failed"
    return None


def answering(port, timeout=3.0):
    """Is the board on this port actually serving, not merely running?

    A pid says a process exists. `/health` says it can still answer, which is
    the difference between a board that died and a board that is wedged -- and
    the second one looks perfect from the outside while the iPad spins.

    It is a quiet path in the server's request log, so this costs nothing that
    anybody has to read.
    """
    import urllib.error
    import urllib.request
    if not port:
        return False
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % int(port),
                                    timeout=timeout) as r:
            if r.status != 200:
                return False
            json.loads(r.read().decode("utf-8", "replace"))
            return True
    except (urllib.error.URLError, OSError, ValueError, TypeError):
        return False
