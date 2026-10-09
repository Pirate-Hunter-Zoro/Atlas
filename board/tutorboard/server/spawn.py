"""Running the board's own commands, from inside the board.

A route that runs `board ...` or asks `tutor --agents` shells out here, so
there is one implementation rather than two that drift. Turns are not started
here: the runner (`runner/service.py`) takes them.
"""

import json
import os
import subprocess
import sys
import time

from .. import paths


# A SERVER HAS NO STANDARD INPUT, AND A CHILD THAT INHERITS ONE THAT IS CLOSED
# DOES NOT RUN AT ALL.
#
# Both helpers below inherited this process's stdin. A board started by launchd,
# or detached by `board start`, has fd 0 closed -- so the python3 they spawn
# dies before it reaches its first line, with:
#
#     Fatal Python error: init_sys_streams: can't initialize sys standard streams
#     OSError: [Errno 9] Bad file descriptor
#
# which is what a board started by a supervisor recorded when it was asked to
# hand its tutor over: the answer it got back was an interpreter crash where a
# wrap-up should have been. Every route that runs a command goes through these
# two functions, so on such a machine none of them could do anything -- and
# each returned a plausible non-zero and was reported as an ordinary failure.
_NO_STDIN = subprocess.DEVNULL


def board_cli(repo, args, timeout=90, given=None, session=None):
    """Drive the board command line from inside the server, for /switch.

    `repo` is the directory it runs in. `session` is the session directory
    it works on (`TUTORBOARD_SESSION`); a route serving a stored session
    passes its own, so the command never reaches another.

    `given` is text for its stdin (`board thread add` reads the thread there);
    without it stdin is closed, for the reason `_NO_STDIN` gives.
    """
    cli = os.path.join(paths.TOOL, "bin", "board")
    env = None
    if session:
        env = dict(os.environ, TUTORBOARD_SESSION=session)
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           stdin=_NO_STDIN if given is None else None,
                           input=None if given is None else given.encode("utf-8"),
                           cwd=repo, stdout=subprocess.PIPE, env=env,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def tutor_cli(args, timeout=30):
    """Drive the launcher from inside the server: `tutor --agents --json`,
    and the old workspace routes until their deletion."""
    cli = os.path.join(paths.TOOL, "bin", "tutor")
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           cwd=paths.TOOL, stdin=_NO_STDIN,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


# ---------------------------------------------------------------------------
# a mission that was told to ship itself
# ---------------------------------------------------------------------------
#     "when I put anything on a mission, I should have the option to tell it to
#      ship its changes once it is done - I don't know if colibri is capable of
#      doing that, but the tutor certainly should be once colibri is done."
#
# The switch is set when the mission is dispatched and carried in the record.
# This is what happens when the mission ends: the changes are in the working
# tree of a workspace nobody is looking at, and a turn is woken to read them and
# push them.
#
# IT IS NOT THE ASSISTANT THAT DID THE WORK, and the owner answered why before
# this was built. The local model decodes at three tokens a second and it is the
# one assistant allowed to read the fenced directory, so it is the wrong thing
# to push its own diff. The workspace's ordinary tutor is woken instead -- a
# hosted turn, a second pair of eyes, and a turn that could not have read the
# session content it is checking the diff for. `board push` makes the machine
# check underneath it either way; see `tutorboard/leaving.py`.
#
# A PRIVATE DAEMON IS STOPPED FIRST, because `tutor agent start` will not swap
# one assistant for another: a record that is live is "already listening" and
# the start is a no-op. Only when it is LISTENING -- a daemon mid-turn is doing
# something somebody asked for, and this waits for the next pass rather than
# killing it.
SHIP_EVERY = 20.0
_SHIPS = {"at": 0.0}


def shipper():
    """Which assistant may push, off the registry. None if this machine has none.

    The rule is the reason rather than a name: it must be headless (this is an
    unattended turn), it must be installed here, and it must NOT be the one that
    may read fenced content -- the whole point is a pair of eyes that could not
    have read what it is checking. The machine's default first, because that is
    what every other unattended turn in this workspace already runs as.
    """
    from .. import assistants, jobs

    # No hosted model call on an institute machine: a board serving where
    # Slurm is ships no mission, because every shipper here is hosted.
    if jobs.has_slurm():
        return None
    reg = assistants.listing() or {}
    agents = reg.get("agents") or []
    ok = [a for a in agents
          if a.get("headless") and not a.get("missing") and not a.get("private")]
    want = reg.get("default")
    for a in ok:
        if a.get("name") == want:
            return a["name"]
    return ok[0]["name"] if ok else None


def ship_missions(now=None):
    """Hand every finished mission that asked for a ship to a tutor that can.

    Called from `sweep_missions`, throttled: this is a directory walk over
    every workspace on the machine and a mission ends on the scale of an hour.
    Returns the missions actually handed over, which is what a test reads.
    """
    from .. import missions, sense
    from ..course.repo import Repo
    from ..lesson import state, turns

    now = float(now or time.time())
    if now - _SHIPS["at"] < SHIP_EVERY:
        return []
    _SHIPS["at"] = now

    from .. import assistants

    reg = assistants.listing() or {}
    known = {a.get("name"): a for a in (reg.get("agents") or [])}

    handed = []
    for w, rec in missions.due(now):
        root = w["root"]
        target = Repo(root)
        # Whatever is attached there now, which is usually the assistant that
        # ran the mission.
        attached = state.load_agent(target) or {}
        live = attached.get("state") in ("listening", "working", "waking",
                                         "reattaching")
        mine = known.get(attached.get("agent")) or {}
        if live and not mine.get("private"):
            # IT IS ALREADY THE RIGHT KIND OF ASSISTANT. The rule is not "the
            # default one" -- it is that whoever pushes could not have read the
            # fenced content it is checking the diff for. An ordinary tutor
            # sitting there satisfies that, and swapping it for the default
            # would be evicting a daemon to prove a point.
            who = attached.get("agent")
        else:
            who = shipper()
            if not who:
                continue
            if live:
                if attached.get("state") != "listening":
                    continue            # mid-turn; ask again on the next pass
                # `tutor agent start` will not swap one assistant for another:
                # a live record is "already listening" and the start is a no-op.
                code, said = tutor_cli(["agent", "stop", w["dir"], "--wait"],
                                       timeout=180)
                if code != 0:
                    continue
        if not missions.claim_ship(root, rec, now):
            continue                    # another board took it
        line = "[ship] " + sense.ship_sense(rec.get("agent"), rec.get("task"))
        record = {
            # An id from the lesson's own series so nothing in the inbox has to
            # be told apart by shape, and NOT written into `turns.jsonl`: the
            # transcript belongs to the lesson and this is not part of one.
            "id": turns.next_turn_id(target),
            "rev": 0, "kind": "text", "answers": None,
            "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": "student", "text": line, "signal": "ship", "read": False,
        }
        try:
            with open(target.messages_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError:
            continue
        # Written before the wake, deliberately: the work already exists and the
        # line must not be lost if the start fails. A line sitting in an inbox is
        # picked up by whichever tutor comes up next, which is the recovery.
        # `--respawn`: a sweep over every workspace on the machine is machinery
        # deciding, not somebody naming a course, and recording one here moves
        # the one address to whichever workspace shipped last.
        tutor_cli(["agent", "start", w["dir"], "--respawn", "--agent", who],
                  timeout=60)
        handed.append({"ws": w["id"], "mission": rec["id"], "agent": who})
    return handed


def sweep_missions():
    """Ship every finished mission that asked for it, every SHIP_EVERY
    seconds, forever.

    A thread of its own, so the hub's rebuild loop never waits on a walk over
    every workspace.
    """
    while True:
        try:
            ship_missions()
        except Exception:
            pass
        time.sleep(SHIP_EVERY + 1.0)
