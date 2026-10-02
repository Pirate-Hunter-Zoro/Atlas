"""Keeping the boards and tutors up: the decisions `tutor watch` acts on.

A process dies -- `serve.py` on an exception, the tutor daemon on an OOM -- and
the record on disk goes on naming a pid that is gone. `tutor watch` looks every
`POLL` seconds and repairs it. On the Mac it runs from the
`tutor-board.tutor-watch` LaunchAgent, which is what brings every board back
after a reboot.

Nothing in this module starts, stops or kills anything. It decides, off records
and a clock, so every decision is testable without a machine; `cmd_watch` in
`bin/tutor` does the acting.
"""

import json
import os
import time

from . import paths, processes


# What the watch loop last did, in the state directory rather than the
# repository: it is machine-local truth, and no clone should carry it.
WATCH = os.path.join(paths.STATE_DIR, "watch.json")

# A file that stands the watch loop down. Nothing in the tool writes it; a person
# who wants the loop to stop without killing the LaunchAgent creates it.
STOP = os.path.join(paths.STATE_DIR, "watch-stopped")

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
# an hour is many missed beats and longer than any handover takes.
ADOPT_WINDOW = 3600


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
        # `tutor down` makes a daemon write its handoff and exit, which leaves
        # exactly the record a person's `tutor agent stop` leaves -- and one of
        # those must be picked back up while the other must never be. So the
        # thing that asks for the stop says which it was: `cmd_down` writes
        # `handover` first, the daemon's own exit merges `state: stopped` over
        # the top of it, and whoever brings the tutor back clears it.
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
# The loop's own records
# ---------------------------------------------------------------------------
def stopped():
    """Has somebody told the watch loop to stand down?"""
    return os.path.exists(STOP)


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


def watch_record():
    return _read(WATCH)


def note_watch(**kw):
    rec = watch_record()
    rec.update(kw)
    _write(WATCH, rec)
    return rec


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
