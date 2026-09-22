"""Running the board's own commands, from inside the board.

The hub can start a course, open a chapter or wake a tutor, and every one of
those is a command that already exists. Shelling out to it keeps one
implementation rather than two that drift.
"""

import json
import os
import subprocess
import sys
import threading
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
# wrap-up should have been. Every hub tap that starts a course, opens a chapter
# or wakes a tutor goes through these two functions, so on such a machine none
# of them could do anything -- and each returned a plausible non-zero and was
# reported as an ordinary failure.
#
# `bin/tutor` already learned this where it forks the daemon (`agent_start`
# passes DEVNULL); it simply never reached here.
_NO_STDIN = subprocess.DEVNULL


def board_cli(repo, args, timeout=90):
    """Drive the board command line from inside the server, for /switch."""
    cli = os.path.join(paths.TOOL, "bin", "board")
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           cwd=repo, stdin=_NO_STDIN,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def fresh_tutor(root, course):
    """Stop this course's assistant and start a new one, out of the way.

    The name is the whole of it: what comes back has read the new chapter's
    lesson and nothing else. `--wait` on the stop, so the two do not overlap;
    a start against a daemon that is still going would be a second one.
    """
    def run():
        tutor_cli(["agent", "stop", course, "--wait"], timeout=180)
        tutor_cli(["agent", "start", course], timeout=120)
    threading.Thread(target=run, daemon=True).start()


def tutor_cli(args, timeout=30):
    """Drive the launcher from inside the server, to move the tutor.

    The assistant belongs to the course, not to this process and not to the
    terminal anyone happens to have open, so switching course has to move it.
    Short timeout deliberately: `tutor agent start` detaches and returns, and
    `stop` only signals -- the wrap-up turn it triggers takes as long as it
    takes and nobody is waiting on it.
    """
    cli = os.path.join(paths.TOOL, "bin", "tutor")
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           cwd=paths.TOOL, stdin=_NO_STDIN,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def configured_agent(where):
    """Which assistant that workspace runs when nobody names one, or "".

    ASKED, NOT WORKED OUT HERE. `resolve_agent` in `bin/tutor` is the one place
    the five layers live -- this once, this sitting, this workspace, this
    machine, the default -- and a copy of them in the server is a copy that
    drifts the first time either moves. `where` is the workspace directory the
    launcher already matches names against.
    """
    code, out = tutor_cli(["agent", "which", where], timeout=30)
    if code != 0:
        return ""
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


# ---------------------------------------------------------------------------
# work handed in with nobody to read it
# ---------------------------------------------------------------------------
# A message going into the inbox did not start a tutor, and the inbox is not a
# queue anybody drains: `board wait` only ever returns to a daemon that is
# already running. So a send to a board whose tutor had died, or had never been
# started, or was still coming up when the allocation that held the last one
# ended, went onto disk and stayed there. The board said "listening" or said
# nothing, and the person who had just handed in an hour of working waited.
#
# Reported as: "the tutor was just marked as dead... which put me in 'send
# again' mode", and then "I don't ever want to be left hanging."
#
# So handing work in wakes a tutor. It is the same `tutor agent start` the hub
# tap and the login hook use -- one implementation -- and it is safe to call
# whenever, because that command refuses when a record is already live or
# already waking. The debounce here is for the case it cannot see: several sends
# in the same second, each forking a launcher that has not yet written the
# record the next one would read.
_WOKE = {}
WAKE_DEBOUNCE = 20.0


def wake_tutor(repo):
    """Start this course's tutor if nothing is reading the board. Never blocks.

    Returns whether an attempt was actually made, which is what the caller wants
    for its log line -- not whether a tutor is now up, because nothing that
    takes as long as a start can be reported by the request that triggered it.
    """
    from ..lesson import state

    try:
        agent = state.load_agent(repo)
    except Exception:                                        # noqa: BLE001
        agent = None
    # A record the board would paint as attached, waking, working or
    # reattaching. Only a genuinely dead one gets past here.
    if agent and agent.get("state") not in ("stale", "stopped"):
        return False

    course = os.path.basename(os.path.abspath(repo.root))
    now = time.time()
    if now - _WOKE.get(course, 0) < WAKE_DEBOUNCE:
        return False
    _WOKE[course] = now
    threading.Thread(target=tutor_cli, args=(["agent", "start", course],),
                     kwargs={"timeout": 60}, daemon=True).start()
    return True


# ---------------------------------------------------------------------------
# the local model's server, which takes minutes rather than seconds
# ---------------------------------------------------------------------------
# `coli-code` exits 1 with "No colibri server is running. Start one: coli-up",
# which is the right message in a terminal and a dead end on an iPad. Starting
# one is not something a request can wait for: `coli-up` waits for an
# allocation, waits out a 429 GB load and then warms the model with a real
# generation -- seven to eight minutes on a good day, and it can pend
# indefinitely behind a 950 GB ask.
#
# So this is `wake_tutor` against `coli-up`, for the reason written above that
# function: nothing that takes as long as a start can be reported by the request
# that triggered it. What the board paints while it happens comes from
# `colibri.status`, off `squeue`, and not from anything written here.


def wake_colibri(timeout=1800):
    """Submit the local model's server and return at once. Never blocks.

    Returns (started, what to say). A second tap does nothing and says why:
    `coli-up` itself refuses when a job is already submitted, and this refuses
    before it gets there so the answer comes back inside the request.
    """
    from .. import colibri

    now = colibri.status(fresh=True)
    if now["state"] != "off":
        return False, "already %s" % now["detail"]
    cmd = colibri.up_command()
    if not cmd:
        return False, ("`coli-up` is not on the path here; see "
                       "projects/libr-local-llm/README.md §3")
    colibri.submitted()

    def run():
        try:
            subprocess.run([cmd], cwd=paths.TOOL, stdin=_NO_STDIN,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            pass
        colibri.forget()

    threading.Thread(target=run, daemon=True).start()
    return True, ("starting the server — seven or eight minutes, longer if the "
                  "partition is full")


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

CARRY_EVERY = 20.0
_CARRIES = {"at": 0.0}

RELEASE_EVERY = 20.0
_RELEASES = {"at": 0.0}


def shipper():
    """Which assistant may push, off the registry. None if this machine has none.

    The rule is the reason rather than a name: it must be headless (this is an
    unattended turn), it must be installed here, and it must NOT be the one that
    may read fenced content -- the whole point is a pair of eyes that could not
    have read what it is checking. The machine's default first, because that is
    what every other unattended turn in this workspace already runs as.
    """
    from .. import assistants

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

    Called from the hub's poll loop, throttled: this is a directory walk over
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


def carry_missions(now=None):
    """Pick up every mission whose node went away under it.

    The second driver, and there are two because nothing admin-free is one. The
    first is the mission's own daemon, which re-queues the work itself when
    `coli-code` exits 75 -- but that daemon lives in the BOARD's allocation and
    goes with it. This runs in whichever board comes up next, off the record and
    `agent.json` alone, which in the case that matters is all there is: both
    allocations ended within the same minute and nothing is running anywhere.

    Called from the hub's poll loop, throttled, beside `ship_missions`. Returns
    the missions actually picked up, which is what a test reads.
    """
    from .. import missions
    from ..course.repo import Repo
    from ..lesson import state, turns

    now = float(now or time.time())
    if now - _CARRIES["at"] < CARRY_EVERY:
        return []
    _CARRIES["at"] = now

    handed = []
    for w, rec in missions.owed(now):
        root = w["root"]
        # RECORDED BEFORE ANYTHING CAN REFUSE IT. The board hop is derived from a
        # record that still says `working`, and the board coming up adopts that
        # daemon within seconds -- which flips the state and takes the
        # derivation with it. A pick-up that is derived and then lost is one
        # nobody makes; written into the record it is owed until it is taken.
        missions.owe_carry(root, rec, now)
        # THE TWO-CLIENTS GUARD, SECOND HALF. `owed` judged a moment ago and a
        # turn may have started since. MID-TURN, not merely attached: an idle
        # daemon is exactly what an inbox line is for, and a daemon with a client
        # running is the one thing a second client must not land on.
        if missions.mid_turn(root, now):
            continue
        target = Repo(root)
        who = rec.get("agent") or "colibri"
        # AND A WORKSPACE HELD BY ANOTHER ASSISTANT IS TAKEN OFF IT FIRST.
        # `tutor agent start` will not swap one assistant for another -- a live
        # record reads as "already listening" and the start is a no-op -- so
        # without this the `[carry]` line is answered by whoever is sitting
        # there rather than by the one the mission was dispatched to, which in
        # a fenced workspace is a different assistant entirely. Same move as
        # `ship_missions`, and a holder mid-turn is left alone: `mid_turn`
        # above has already refused this pass.
        attached = state.load_agent(target) or {}
        if attached.get("agent") and attached.get("agent") != who:
            if attached.get("state") != "listening":
                continue                # waking or reattaching; ask again
            code, _said = tutor_cli(["agent", "stop", w["dir"], "--wait"],
                                    timeout=180)
            if code != 0:
                continue
        if not missions.claim_carry(root, rec, now):
            continue                    # another board took it
        # AND THIS PICK-UP IS WHAT PUT THAT ASSISTANT THERE, recorded, because
        # the node the dispatch's one was on has gone and whatever was
        # listening went with it. A mission that brought nobody at the dispatch
        # brings one here, and it is released when the mission ends like any
        # other -- see `release_missions`.
        missions.brought_by(root, rec, who, now)
        # The task WHOLE, out of the transcript the dispatch wrote it into. The
        # record's copy is truncated to `TASK_CHARS` for a two-line strip and is
        # the fallback rather than the source.
        task = str(rec.get("task") or "")
        try:
            for t in turns.load_turns(target):
                if t.get("id") == rec.get("id") and t.get("text"):
                    task = t["text"]
                    break
        except OSError:
            pass
        # The `[carry] ` tag is not decoration: `board inbox` prints a message
        # as `[<iso>] <text>` and `tutor.turn_signal` reads the signal back out
        # of the text, so the tag is how the woken turn learns what it is.
        record = {
            "id": turns.next_turn_id(target),
            "rev": 0, "kind": "text", "answers": None,
            "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": "student", "text": "[carry] " + task,
            "signal": "carry", "read": False,
        }
        try:
            with open(target.messages_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError:
            continue
        # Written before the wake, for `ship_missions`'s reason: the work
        # already exists and the line must not be lost if the start fails.
        # A non-zero is not an error here. Colibri is `exclusive` -- one KV slot
        # on the machine -- so a refused start is routine, and the line stays in
        # the inbox for whichever daemon comes up. `carried_at` is stamped, so
        # the retry is under `CARRY_BACKOFF` rather than on the next pass.
        tutor_cli(["agent", "start", w["dir"], "--respawn", "--agent", who],
                  timeout=60)
        handed.append({"ws": w["id"], "mission": rec["id"], "agent": who})
    return handed


# ---------------------------------------------------------------------------
# a mission that brought its own assistant, and has ended
# ---------------------------------------------------------------------------
#     "Make missions release the workspace."
#
# AN ASSISTANT STARTED FOR A MISSION IS RELEASED WHEN THE MISSION ENDS. One
# that a person chose stays. `brought` on the record carries which it was,
# written by whatever started it -- the dispatch, or a pick-up after a hop --
# because afterwards both are the same name in the same `agent.json`.
#
# WHAT A RELEASE LEAVES IS THE WORKSPACE'S OWN ASSISTANT, not an empty
# workspace. A workspace with nothing attached does not answer a message
# anybody hands in to it -- `spawn.wake_tutor` covers only the workspace the
# board it runs in is serving, and a release happens in one nobody is looking
# at. The start names NOBODY, so `resolve_agent` answers, which is the same
# one implementation `watch_once` uses when it puts a tutor back after a hop.
#
# AND THE STOP IS A STOP RATHER THAN A HANDOVER, which is what makes it hold:
# `agent_stop` leaves `state: stopped` with no `handover`, and
# `supervise.tutor_verdict` reads that as a person saying no and never revives
# it. A release the watchdog undoes five seconds later is not a release.


def release_missions(now=None):
    """Give back the assistant every ended mission brought with it.

    Called from the hub's poll loop beside `ship_missions`, throttled, and
    AFTER it: a release must not land between a ship being owed and the turn
    that pushes it being woken. Returns the workspaces actually released,
    which is what a test reads.
    """
    from .. import missions
    from ..lesson import state
    from ..course.repo import Repo
    # The guards live where the dispatch's own swap consults them, and there is
    # one copy of them. Imported here rather than at the top of the file
    # because that module imports this one.
    from .routes.machines import swap_blocked

    now = float(now or time.time())
    if now - _RELEASES["at"] < RELEASE_EVERY:
        return []
    _RELEASES["at"] = now

    gave = []
    for w, rec in missions.releasable(now):
        root = w["root"]
        mine = str(rec.get("brought") or "")
        # WHOEVER IS ACTUALLY ATTACHED, not whoever was asked for. An assistant
        # somebody swapped in by hand while the mission ran is theirs; the ship
        # may have swapped one in too. Either way this mission has nothing left
        # to give back, and the record is stamped so no board asks again.
        if missions.holder(root) != mine:
            missions.claim_release(root, rec, now)
            continue
        if (rec.get("ship") and rec["state"] == "done"
                and not rec.get("shipped")):
            # The push has not been handed to anybody yet. Stopping the daemon
            # now empties the workspace under a ship that is about to look for
            # one; `ship_missions` runs first in the same loop and this is one
            # pass behind it.
            #
            # `done` ONLY, which is the same line `missions.due` draws. A
            # mission that failed is never shipped however its switch was set,
            # so waiting for a ship that is not coming would hold its assistant
            # for the week the record lives.
            continue
        keep = swap_blocked({"root": root, "repo": w["dir"]}, mine)
        if keep:
            # Somebody is in that workspace, a turn is in flight, another
            # mission is open, or a line handed in has not been picked up.
            # Every one of those is a reason a dispatch may not swap the
            # assistant either, and a release is the same act.
            continue
        if configured_agent(w["dir"]) == mine:
            # IT IS THE WORKSPACE'S OWN ASSISTANT AFTER ALL. Asked here rather
            # than at the dispatch, and asked last, because this is the moment
            # the answer has to be true and because it is a subprocess: a
            # release held off for an hour by an open mission must not pay for
            # one every twenty seconds. Stopping it to start the same one again
            # would throw away a warm prefix to prove a point.
            missions.claim_release(root, rec, now)
            continue
        if not missions.claim_release(root, rec, now):
            continue                    # another board took it
        code, _said = tutor_cli(["agent", "stop", w["dir"], "--wait"],
                                timeout=180)
        # `--respawn`, and no `--agent`: a sweep over every workspace on the
        # machine is machinery deciding rather than somebody naming a course,
        # and the assistant that belongs here is the one the configuration
        # names. `agent start` is a no-op against a daemon that is still
        # wrapping up, and the watchdog is what brings the workspace back if
        # this one comes too early -- the record it would read says `stopped`,
        # so nothing revives the assistant that was just let go.
        back = ""
        if code == 0:
            tutor_cli(["agent", "start", w["dir"], "--respawn"], timeout=60)
            back = state.load_agent(Repo(root)) or {}
            back = str(back.get("agent") or "")
        gave.append({"ws": w["id"], "mission": rec["id"], "agent": mine,
                     "back": back})
    return gave
