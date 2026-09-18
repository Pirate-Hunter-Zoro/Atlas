"""A mission is a job somebody set going somewhere they are not looking.

WHY THIS EXISTS, in the words it was asked for:

    "when I put colibri or anything on a mission, just because I close the iPad
     doesn't mean that should end. Next time I open the iPad and access the
     board, that mission should still be going or notify me somewhere if it's
     done."

The job already survives a closed lid. `POST /elsewhere` starts a detached
daemon -- `setsid`, stdin on DEVNULL -- so nothing about a browser going away
touches it. What it left behind was no RECORD, and without one there were three
questions with no answer anywhere on the machine: is it still running, did it
fail, and what was it put on.

THE RECORD IS A FILE IN THE WORKSPACE THE MISSION IS ABOUT, under
`live/missions/`, beside `agent.json` and `push.json`. Not in the browser and
not in the dispatching board's process: the whole point is that it is still
there on another device, on another node, tomorrow. Every board reads every
workspace's, because one shared filesystem is how the rest of this tool answers
questions about machines it is not serving -- `news.py` is this module's twin
and answers the past tense of the same sentence.

ONE FILE PER MISSION, NAMED FOR THE TURN THAT CARRIES THE TASK. A mission IS
that turn: the task is written into the target's transcript as a turn of the
student's, so the turn id is the name. One `missions.json` per workspace would
be a read-modify-write, and two boards on two nodes dispatching into the same
workspace would silently lose one of them.

THE STATE IS DERIVED, AND THEN FROZEN. Both halves are load-bearing.

* **Derived**, because nothing is alive to write it. A mission ends by the
  daemon writing a card, by the daemon dying, or by the allocation under it
  ending -- and in two of those three there is no process left to record
  anything. So the ending is read off what the workspace already keeps: the
  newest card, and `agent.json`.
* **Frozen**, because the evidence expires. A mission that failed at nine and a
  card written by some unrelated turn at eleven reads as `done` to anything
  looking after eleven. The first reader to derive a terminal state writes it
  into the record; every reader after that reads the ending rather than deriving
  it again. `ended` is that field, and it is why the record can say how a
  mission ended rather than how the workspace looks now.

THREE STATES, BECAUSE THEY ARE THE THREE A PERSON ACTS ON. `running` -- leave it
alone. `done` -- go and read it. `failed` -- send it again, or send it somewhere
else. Anything finer is a state nobody does anything different about.

A MISSION COMES OFF THE LIST WHEN IT IS LOOKED AT, and looking means going
there: the board serving that workspace stamps its own finished missions when
the page says somebody is reading it. A running one stays on the list after a
look, because it is still running and that is the fact being reported.

THE CEILING IS PART OF THE RECORD, for the one assistant that has one. A
colibrì turn runs inside the serve job's allocation -- `coli-code` steps into it
with `srun --overlap` -- so a colibrì mission cannot outlive that job's
walltime, and nothing anywhere used to say so. The time left on the job is
stamped at dispatch, and a mission still running past it has failed for a reason
worth printing rather than by a silence.
"""

import json
import os
import re
import time

from . import atlas, machine, news, paths, processes


MISSIONS = "missions"

# What a task is truncated to in the record. The record is read on a tablet in a
# strip two lines high; the whole task is in the target's transcript, which is
# where it belongs.
TASK_CHARS = 400

# How long after dispatch a workspace with nothing attached is still a start in
# flight rather than a mission that died. `agent start` forks and returns, the
# daemon writes `waking` before it does any of the slow work, and the slow work
# is a `git pull` and a tailnet coming back. `processes.WAKING_GRACE` is the
# same window for the same reason.
START_GRACE = float(processes.WAKING_GRACE)

# How long an ended mission stays on disk. Long enough that a week away still
# shows what happened; short enough that `live/missions/` is not a log.
KEEP = 7 * 24 * 3600

# The list is rebuilt at most this often. The hub polls four times a second and
# this is a directory walk over every workspace on the machine. `news.TTL`, for
# the same reason: the answer changes on the scale of a turn.
TTL = 5.0

_CACHE = {"at": 0.0, "value": None}

# A mission id is a turn id and nothing else ever reaches the filesystem from a
# request. Matched rather than sanitised: a name that is not one of these is not
# a mission, and joining it onto a path to find out is the mistake.
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")

# Everything that is stored. A judged mission carries derived keys as well --
# `state`, `card`, `ws` -- and writing those back would turn a reading into a
# fact.
FIELDS = ("id", "task", "agent", "at", "ship", "from", "host", "card_at",
          "ceiling", "ended", "ended_at", "reason", "looked", "shipped")


def _dir(root):
    return os.path.join(root, "live", MISSIONS)


def _path(root, mid):
    return os.path.join(_dir(root), "%s.json" % mid)


def write(root, rec):
    """Store one mission record. Atomically, and never raising.

    Two boards on two nodes share this filesystem and a half-written record
    reads as a mission that was never dispatched.
    """
    mid = str(rec.get("id") or "")
    if not ID_RE.match(mid):
        return False
    target = _path(root, mid)
    tmp = target + ".tmp"
    try:
        os.makedirs(_dir(root), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({k: rec[k] for k in FIELDS if k in rec}, fh)
        os.replace(tmp, target)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def dispatch(root, task, turn, agent="", ship=False, frm="", ceiling=0.0,
             now=None):
    """Record that a mission has just been sent into this workspace.

    `turn` is the turn the task was written as, and is the mission's name.
    `ceiling` is when the machinery under it stops existing, or 0 where nothing
    limits it. `card_at` is what the workspace's newest card was at dispatch, so
    "a card has landed since" is a comparison rather than a guess -- without it
    a clock a second out between two nodes reports a mission done the instant it
    starts.
    """
    now = float(now or time.time())
    rec = {
        "id": str(turn),
        "task": (task or "").strip()[:TASK_CHARS],
        "agent": agent or "",
        "at": now,
        "ship": bool(ship),
        # Where it was sent FROM, which is the thing a person cannot reconstruct
        # a day later and the only field here that is about them rather than
        # about the work.
        "from": frm or "",
        "host": machine.node_name(),
        "card_at": newest_card_at(root),
        "ceiling": float(ceiling or 0),
        "ended": "",
        "ended_at": 0.0,
        "reason": "",
        "looked": 0.0,
        # When the ship was handed to a tutor, which is not when it landed: the
        # push itself is reported in `push.json`, which the board already
        # paints. This field is the CLAIM -- see `claim_ship`.
        "shipped": 0.0,
    }
    write(root, rec)
    return rec


def newest_card_at(root):
    """When this workspace's newest card was written. `news` owns the walk."""
    try:
        return news.newest_card(root)[0]
    except OSError:
        return 0.0


def stored(root):
    """Every mission record on disk in one workspace, newest dispatch first."""
    out = []
    try:
        names = os.listdir(_dir(root))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(_dir(root), name), "r",
                      encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict) or not ID_RE.match(str(rec.get("id") or "")):
            continue
        out.append(rec)
    out.sort(key=lambda r: -float(r.get("at") or 0))
    return out


def _agent(root):
    """That workspace's `agent.json`, raw.

    Raw on purpose. `state.load_agent` judges a record for the board SERVING it
    -- it rewrites the state, hangs a failure on it and clears the turn's signal
    -- and every one of those is about painting a lesson. What is wanted here is
    the two facts on disk: is something attached, and did the last turn fail.
    """
    try:
        with open(os.path.join(root, "live", "agent.json"), "r",
                  encoding="utf-8") as fh:
            rec = json.load(fh)
        return rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        return {}


def _listening(rec):
    """Is anything still attached to the workspace holding this mission?

    Which question that is depends on where the record was written. A pid from
    this node can be checked; a pid from another one cannot be -- the home
    directory is shared, so the number is very likely alive here and belonging
    to a stranger -- and there the heartbeat is the only evidence there is.
    """
    if not rec:
        return False
    node = machine.node_name()
    host = rec.get("host") or ""
    if host and host != node:
        return processes.agent_attached_away(rec, host)
    return processes.agent_is_attached(rec, node)


def holder(root):
    """Which assistant is listening in that workspace right now, or "".

    The public half of the two private helpers above, and it exists for the
    moment BEFORE a mission rather than after one: a dispatch names an
    assistant, `agent start` is a no-op where something is already attached,
    and without this the record would name whoever was asked for while the
    work went to whoever was there.
    """
    rec = _agent(root)
    return str(rec.get("agent") or "") if _listening(rec) else ""


def _stamp(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def judge(root, rec, now=None, card=None, said=None):
    """One mission, with `state` and `reason` on it. Never raises.

    `card` and `said` are the workspace's newest card and its `agent.json`,
    passed in by `of` so a workspace with four missions is one walk rather than
    four.
    """
    now = float(now or time.time())
    out = dict(rec)
    out.setdefault("card", "")
    if rec.get("ended"):
        # Read, not re-derived. See the module docstring: the evidence a state
        # was derived from expires, and the state must not.
        out["state"] = rec["ended"]
        return out
    when, which = card if card is not None else (newest_card_at(root), "")
    st = _agent(root) if said is None else said
    at = _stamp(rec.get("at"))
    # A card that is newer than the mission AND newer than the one that was
    # already there when it started.
    landed = when > max(at, _stamp(rec.get("card_at")))
    failed_at = _stamp(st.get("failed_at")) if st.get("last_error") else 0.0

    if failed_at > at and failed_at >= when:
        out["state"] = "failed"
        out["ended_at"] = failed_at
        out["reason"] = str(st.get("last_error") or "")[-300:]
        return out
    if landed:
        out["state"] = "done"
        out["ended_at"] = when
        out["card"] = which
        out["reason"] = ""
        return out
    ceiling = _stamp(rec.get("ceiling"))
    if ceiling and now > ceiling:
        # The one ending that is neither a card nor a dead process: the
        # allocation the assistant runs inside stopped existing, which takes
        # every `srun --overlap` in it and leaves nothing anywhere to notice.
        out["state"] = "failed"
        out["ended_at"] = ceiling
        out["reason"] = ("the allocation %s runs in ended before the mission "
                         "did" % (rec.get("agent") or "that assistant"))
        return out
    if now - at > START_GRACE and not _listening(st):
        out["state"] = "failed"
        out["ended_at"] = now
        out["reason"] = "nothing is attached to that workspace any more"
        return out
    out["state"] = "running"
    return out


def of(root, now=None, freeze=True):
    """Every mission in one workspace, judged, newest first.

    `freeze` writes a terminal state back into the record -- see the module
    docstring -- and is the reason a read is allowed to write. It also prunes:
    an ended mission older than `KEEP` is history and its file goes.
    """
    now = float(now or time.time())
    recs = stored(root)
    if not recs:
        return []
    card = (newest_card_at(root), "")
    try:
        card = news.newest_card(root)
    except OSError:
        pass
    said = _agent(root)
    out = []
    for rec in recs:
        got = judge(root, rec, now, card=card, said=said)
        if got.get("ended") and now - _stamp(got.get("ended_at")) > KEEP:
            try:
                os.remove(_path(root, str(got.get("id"))))
            except OSError:
                pass
            continue
        if freeze and got["state"] != "running" and not rec.get("ended"):
            # The reading and the record say the same thing from here on. Both,
            # not just the file: `looked` stores what it was handed, and a
            # caller holding a copy that still says "never ended" would write
            # the freeze straight back out.
            got["ended"] = got["state"]
            got["ended_at"] = got.get("ended_at") or now
            got["reason"] = got.get("reason") or ""
            write(root, got)
        out.append(got)
    return out


def looked(root, now=None):
    """Somebody is looking at this workspace, so its finished missions come off.

    THIS WORKSPACE AND NO OTHER, which is the same rule `/seen` follows: there
    is exactly one root a board may write into, and a name from a browser never
    reaches the filesystem. A running mission is left alone -- it is still
    running, and that is the fact being reported.
    """
    now = float(now or time.time())
    hit = 0
    for got in of(root, now):
        if got["state"] == "running" or got.get("looked"):
            continue
        rec = {k: got[k] for k in FIELDS if k in got}
        rec["looked"] = now
        if write(root, rec):
            hit += 1
    return hit


# ---------------------------------------------------------------------------
# A mission that was told to ship itself
# ---------------------------------------------------------------------------
# The switch is set at dispatch and the work is done by somebody else entirely:
# when a mission finishes, the workspace's ORDINARY tutor is woken with the
# mission's own report and pushes it. The owner answered why before it was
# built -- the local model decodes at three tokens a second and it is the one
# assistant allowed to read the fenced directory, so it is the wrong thing to
# push its own diff. What is here is the half that belongs to the record: which
# missions are owed a ship, and taking one exactly once.


def due(now=None):
    """Every mission that ended `done`, was told to ship, and has not been.

    `done` only. A mission that FAILED may well have left changes in the working
    tree, and pushing those is the opposite of what a person who set a mission
    going would want from the word "failed" -- they have to look first. Nothing
    is lost by refusing: the changes are still there and `board push` is a tap.
    """
    now = float(now or time.time())
    out = []
    for w in atlas.workspaces():
        try:
            got = of(w["root"], now)
        except Exception:                                    # noqa: BLE001
            continue
        for rec in got:
            if rec["state"] != "done" or not rec.get("ship"):
                continue
            if rec.get("shipped"):
                continue
            out.append((w, rec))
    return out


def claim_ship(root, rec, now=None):
    """Take this mission's ship, once, across every board on this machine.

    AN EXCLUSIVE CREATE, and it is not belt-and-braces. Every board reads every
    workspace's missions, so two boards -- or two generations of the serving
    chain overlapping by a second -- would both see the same finished mission
    and both wake a turn to push the same diff. `O_EXCL` is the one thing here
    that is atomic on a shared filesystem; the field in the record is written
    after it and is what a person reads.
    """
    now = float(now or time.time())
    mid = str(rec.get("id") or "")
    if not ID_RE.match(mid):
        return False
    flag = os.path.join(_dir(root), mid + ".shipping")
    try:
        os.makedirs(_dir(root), exist_ok=True)
        fd = os.open(flag, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        return False
    try:
        os.write(fd, ("%f\n" % now).encode("utf-8"))
    except OSError:
        pass
    finally:
        os.close(fd)
    out = dict(rec)
    out["shipped"] = now
    write(root, out)
    return True


def listing(here, now=None):
    """Every mission on this machine, newest first, with where each one is.

    `here` is the workspace this board serves. Unlike `news.elsewhere` it is not
    excluded: a mission in the workspace you happen to have open is still a
    mission that was set going yesterday and may still be running, and the strip
    says so rather than leaving it to the busy indicator, which knows a turn is
    happening and nothing about what it was for. `here` on the row is what lets
    the surface leave off a way back to where somebody already is.
    """
    now = float(now or time.time())
    out = []
    for w in atlas.workspaces():
        root = w["root"]
        for got in of(root, now):
            if got["state"] != "running" and got.get("looked"):
                continue
            got["ws"] = w["id"]
            got["repo"] = w["dir"]
            got["family"] = w["family"]
            got["family_name"] = w["family_name"]
            got["course"] = news.course_name(root) or w["dir"]
            got["here"] = paths.same_dir(root, here)
            out.append(got)
    out.sort(key=lambda x: -_stamp(x.get("at")))
    return out


def waiting(repo, now=None):
    """`listing`, cached, for the payload the hub pushes four times a second."""
    now = float(now or time.time())
    if _CACHE["value"] is not None and now - _CACHE["at"] < TTL:
        return _CACHE["value"]
    try:
        value = listing(repo.root, now)
    except Exception:                                        # noqa: BLE001
        # A front door that throws is a blank screen where the app used to be,
        # and a mission is the least important thing on it.
        value = []
    _CACHE["at"] = now
    _CACHE["value"] = value
    return value


def forget():
    """Drop the cache, because something just changed it: a dispatch, or a look."""
    _CACHE["at"] = 0.0
    _CACHE["value"] = None
