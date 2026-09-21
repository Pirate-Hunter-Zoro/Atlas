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
with `srun --overlap` -- so a colibrì TURN cannot outlive that job's walltime.
The time left on the job is stamped at dispatch, and it is how long the client
answering right now has, printed rather than left to a silence.

A MISSION THAT OUTLIVES ITS NODE IS CARRIED, NOT FAILED. The ceiling bounds the
turn; it does not bound the work. `coli-code` exits 75 when the generation its
step ran in ended under it, the daemon re-queues the same task with a resume
recipe, and where the daemon went with its node too `carry_verdict` derives the
same repair from this record and `agent.json` alone -- because in the case that
matters, both allocations end within the same minute and nothing is running
anywhere to remember anything. `spawn.carry_missions` is the second driver and
runs in whichever board comes up next.

Four numbers bound it, and every one of them is in the record rather than in
some daemon's locals, because a backoff a hop resets is not a backoff.
`MISSION_LIFE` is the total budget, `CARRY_HOPS` the number of pick-ups,
`CARRY_BACKOFF` the space between them and `STALL_CAP` the number of pick-ups
allowed to produce nothing. A carry is claimed with `O_EXCL`, the way a ship is,
so every board on the machine picks each mission up exactly once.

AND THE EVIDENCE IS IN THE RECORD TOO. `turn_at` is the daemon's own word for
"a client is running against this mission", written by nothing else, because
`agent.json` cannot carry that fact across a board hop: the board coming up
adopts the left-behind daemon and writes over it within seconds, long before
the heartbeat has been quiet long enough to mean anything.

`thaw` is the one narrow entitlement to clear an ending, and it refuses a
mission somebody has already read: a record a person has acted on is theirs, and
resurrecting it under them is worse than the defect.
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

# Nine hours of WORK is what has to fit. This budget also pays every step lost
# to a hop and every re-prefill after one, and six hops of re-prefill against a
# nine-hour task do not fit in twelve, so it is eighteen.
MISSION_LIFE = 18 * 3600

# Interruptions picked up. Nine hours across nine-hour generations needs two;
# six leaves slack for a board hop landing on a colibri hop.
CARRY_HOPS = 6

# How long after a carry is claimed before another is owed. IN THE RECORD, not
# in a daemon's locals: a backoff a hop resets is not one, and a refused
# `agent start` -- colibri's `exclusive` is the routine one -- retries under it.
CARRY_BACKOFF = 300.0

# A carried turn that ends faster than this did nothing. On this engine any real
# turn spends minutes in prefill before it can even fail.
CARRY_FLOOR = 120.0

# How many pick-ups may produce nothing before the mission is spent. Without it
# a resume that dies instantly is a tight fail-retry loop for the whole budget.
STALL_CAP = 2

# The three reasons a hop wears. Anything else is a mission that failed on its
# own and stays failed.
_HOP_REASONS = ("exit ", "the allocation ", "nothing is attached")

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
          "ceiling", "ended", "ended_at", "reason", "looked", "shipped",
          # The carry. `carry` is one owed and not yet taken, `carries` how many
          # have been, `carried_at` when the last was claimed, `stalls` how many
          # produced nothing, and `life` the moment the budget runs out.
          "carry", "carries", "carried_at", "stalls", "life",
          # A turn in flight, and which conversation it is in. `turn_at` is the
          # daemon's own word for "a client is running right now", and only the
          # daemon writes it -- see `carry_verdict`. `session` is the id the
          # client is told to open and to resume, so a pick-up names the
          # conversation rather than taking whichever is newest.
          "turn_at", "session")


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
        "carry": 0.0,
        "carries": 0,
        "carried_at": 0.0,
        "stalls": 0,
        "life": now + MISSION_LIFE,
        "turn_at": 0.0,
        "session": "",
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


def _listening(rec, now=None):
    """Is anything still attached to the workspace holding this mission?

    Which question that is depends on where the record was written. A pid from
    this node can be checked; a pid from another one cannot be -- the home
    directory is shared, so the number is very likely alive here and belonging
    to a stranger -- and there the heartbeat is the only evidence there is.

    `now` is passed through to the heartbeat half so `carry_verdict` is a pure
    function of a record and a chosen clock. The pid half needs no clock.
    """
    if not rec:
        return False
    node = machine.node_name()
    host = rec.get("host") or ""
    if host and host != node:
        return processes.agent_attached_away(rec, host, now)
    return processes.agent_is_attached(rec, node)


def _working(rec, now=None):
    """Is that assistant in the middle of a turn right now?

    The question a card cannot answer. A doing turn writes ONE sentence saying
    what it is about to do, does the work, and writes the report over the top of
    it -- so the first card of a mission lands seconds after the dispatch and
    hours before the answer. Read as an ending it says `done, go and read it`
    over an assistant that has not started, and `looked` then takes the row off
    the list while the work is still running.

    `working` is the record's own word for mid-turn, and it is the one
    `tutor restart` holds a tutor back by. The process has to be attached as
    well: a record left saying `working` by a daemon that died is a turn nobody
    is taking, and the ending belongs to whichever rule catches that.
    """
    return bool(rec) and rec.get("state") == "working" and _listening(rec, now)


def mid_turn(root, now=None):
    """Is a turn in flight in that workspace right now?

    The question a pick-up asks before it wakes one, and it is narrower than
    "is anything attached". An IDLE daemon is what a `[carry]` line is for --
    that is how `ship_missions` wakes one too. A daemon in the middle of a turn
    has a client running, and a second client on one conversation is the only
    outcome worse than the hop being repaired.
    """
    return _working(_agent(root), now)


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


def _life(rec):
    """When this mission's budget runs out.

    Falls back to the dispatch plus `MISSION_LIFE`, because a record written
    before the carry existed has no `life` and must still be carryable.
    """
    return _stamp(rec.get("life")) or _stamp(rec.get("at")) + MISSION_LIFE


def _spent(rec, now):
    """Why this mission's carry budget has run out, or "" while it has one.

    One copy of the three numbers, because `carry_verdict` refuses a pick-up on
    them, `thaw` refuses to clear an ending on them and `judge` yields the
    ceiling to them. Three copies drifting apart is how a mission is failed by
    one rule and revived by the next for ever.
    """
    if now > _life(rec):
        return "eighteen hours of picking it up and it is not finished"
    if (rec.get("carries") or 0) >= CARRY_HOPS:
        return "picked up six times and it is not finished"
    if (rec.get("stalls") or 0) >= STALL_CAP:
        return "two attempts to pick it up produced nothing"
    return ""


def has_budget(rec, now=None):
    """Is there anything left to pick this mission up with?"""
    return not _spent(rec, float(now or time.time()))


def carry_verdict(rec, said, now=None):
    """Is this mission owed a pick-up, spent, or neither.

    `"no"`, `"owed"`, `"soon"`, or `("spent", reason)`. A record, that
    workspace's raw `agent.json`, and a clock -- nothing else, and nothing
    started, stopped or killed here. `supervise.tutor_verdict` holds to the
    same standard and for the same reason: the case being repaired is the one
    where both allocations ended within the same minute, so the repair has to
    be derivable from disk by whatever comes up next.

    A TURN IN FLIGHT IS THE RECORD'S OWN WORD FOR IT. `agent.json` is not,
    because the board that comes up next adopts that daemon and overwrites it
    before the heartbeat has gone quiet long enough to mean anything: the
    daemon beats every 30 s, `AWAY_SILENCE` is 900 s, and `supervise.left_behind`
    adopts anything seen inside `ADOPT_WINDOW` -- so `agent_start` writes
    `waking` over the evidence within seconds of the new board coming up. Only
    the daemon writes `turn_at`, and it leaves it set on every path where a
    pick-up is still owed.

    `carry` on the record is the daemon's own word for a hop it has already
    decided on, written before it re-queues, so a daemon that dies in that
    window leaves the repair behind it. The last clause covers the window
    between dispatch and the first `turn_open`, and every part of it carries
    weight. `state == "working"` is
    the record's own word for mid-turn. `not last_error` is what keeps an
    ordinary failure a failure -- the exit-75 path writes no error for exactly
    this reason. `not _listening` is the two-clients guard, and it is the check
    rather than a host test because a daemon that died on THIS node leaves a
    record a board revives into a `board wait` on a consumed inbox, and a host
    test would refuse to repair that.

    A STOP IS NOT A HOP, and the difference is one field. Same distinction
    `supervise.left_behind` draws: somebody stopping the assistant is a person
    deciding, and a handover is the board moving node with the lesson going on.

    A PICK-UP OWED AND NOT YET DUE IS `"soon"` RATHER THAN `"no"`, and the
    difference is the whole reason there are two words for it. `CARRY_BACKOFF`
    holds the WAKE off; it says nothing about the work. `"no"` drops `judge`
    through to the card rule, and the first card of a doing turn is written
    seconds after dispatch and before the work -- so a mission mid-hop would
    freeze `done`, which is terminal and which `thaw` does not reach. `"soon"`
    reads as mid-hop everywhere and is acted on nowhere: `owed` takes only
    `"owed"`.

    No ceiling on how stale the record may be. `MISSION_LIFE` is the only clock
    that bounds this, because a board taking forty minutes to come back is
    exactly the case being repaired.
    """
    now = float(now or time.time())
    # The one assistant whose client is a step of somebody else's allocation.
    if rec.get("agent") != "colibri":
        return "no"
    why = _spent(rec, now)
    if why:
        return ("spent", why)
    if said.get("state") == "stopped" and not said.get("handover"):
        return "no"
    # Owed first, due second, and never the other way round: a pick-up inside
    # the backoff is a mission mid-hop that nothing may wake yet.
    owed_now = "owed" if now - _stamp(rec.get("carried_at")) >= CARRY_BACKOFF \
        else "soon"
    if _stamp(rec.get("turn_at")) and not _working(said, now):
        return owed_now
    if rec.get("carry"):
        return owed_now
    if (said.get("state") == "working" and not said.get("last_error")
            and not _listening(said, now)
            and now - _stamp(rec.get("at")) > START_GRACE):
        return owed_now
    return "no"


def thaw(rec, now=None):
    """May this ending be cleared, because it was a hop rather than an end?

    THE ONE NARROW ENTITLEMENT TO UNDO A FREEZE, and this module is built on the
    opposite rule -- a terminal state is written once and read thereafter -- so
    every clause here is a refusal.

    `looked` is the sharpest of them: a mission somebody has READ is theirs, and
    resurrecting it under them is worse than the defect this repairs. The reason
    has to look like a hop as well, which is the three shapes a vanished node
    leaves: a non-zero exit, the ceiling, and nothing attached.
    """
    now = float(now or time.time())
    if rec.get("ended") != "failed":
        return False
    if rec.get("agent") != "colibri":
        return False
    if rec.get("looked"):
        return False
    if not has_budget(rec, now):
        return False
    return str(rec.get("reason") or "").lstrip().startswith(_HOP_REASONS)


def judge(root, rec, now=None, card=None, said=None):
    """One mission, with `state` and `reason` on it. Never raises.

    `card` and `said` are the workspace's newest card and its `agent.json`,
    passed in by `of` so a workspace with four missions is one walk rather than
    four.
    """
    now = float(now or time.time())
    out = dict(rec)
    out.setdefault("card", "")
    st = _agent(root) if said is None else said
    verdict = carry_verdict(rec, st, now)
    if verdict in ("owed", "soon") and (not rec.get("ended") or thaw(rec, now)):
        # A MISSION THAT OUTLIVED ITS NODE IS MID-HOP, NOT OVER. Ahead of every
        # other rule here, and ahead of the CARD rule in particular: a doing
        # turn writes its first card seconds after dispatch, so a board hop with
        # nothing attached reads as `done` off that card while the work is
        # unfinished. `soon` counts for exactly as much as `owed` here -- the
        # backoff is about when a turn may be woken, not about whether the work
        # is over -- and it is the five minutes after every claimed hop.
        out["state"] = "running"
        out["ended"], out["ended_at"], out["reason"] = "", 0.0, ""
        return out
    if isinstance(verdict, tuple) and not rec.get("ended"):
        # Spent, and only ever said about a mission that has not ended. A
        # colibri mission that finished this morning is still a record on disk
        # tomorrow, and re-reading its age as a failure would rewrite `done`.
        out["state"], out["ended_at"], out["reason"] = "failed", now, verdict[1]
        return out
    if rec.get("ended"):
        # Read, not re-derived. See the module docstring: the evidence a state
        # was derived from expires, and the state must not.
        out["state"] = rec["ended"]
        return out
    when, which = card if card is not None else (newest_card_at(root), "")
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
    # A CARD ENDS A MISSION ONLY WHERE THE TURN THAT WROTE IT IS OVER. The
    # first card is the sentence a doing turn writes BEFORE the work, so a card
    # alone says the assistant started rather than finished.
    if landed and not _working(st):
        out["state"] = "done"
        out["ended_at"] = when
        out["card"] = which
        out["reason"] = ""
        return out
    ceiling = _stamp(rec.get("ceiling"))
    # A PASSED CEILING WITH BUDGET LEFT IS A HOP, NOT AN ENDING, and the rules
    # under this one decide which. The ceiling is the walltime of the
    # generation the client is a step of, re-stamped at every turn, and the
    # chain brings another generation up: freezing the mission at the dead
    # one's walltime is how somebody is invited to re-dispatch work that is
    # already running on the successor.
    if ceiling and now > ceiling and not (
            rec.get("agent") == "colibri" and has_budget(rec, now)):
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
        if freeze and got["state"] == "running" and rec.get("ended"):
            # THE THAW, ACTING. `judge` cleared the ending because the mission
            # is mid-hop; this is the one place that reaches the file, and
            # without it every reader re-derives the same clearing for ever.
            write(root, got)
        elif freeze and got["state"] != "running" and not rec.get("ended"):
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


def running(root, now=None):
    """Is a mission live in this workspace right now?

    `board brief` asks, because a mission is a change somebody asked for and the
    turn working it is a doing turn -- whatever standing stance the workspace
    teaches under. The task arrives in the inbox as a plain sentence of theirs,
    so without this a mission into a workspace that teaches is briefed as a
    lesson and writes a card instead of the change.

    A pure read, unlike `of`: nothing is frozen and nothing is pruned. A
    briefing is not the right place to decide a mission has ended, and the
    board's own poll decides it four times a second anyway. The walk for the
    newest card is skipped entirely where no record is open, which is every
    workspace almost all of the time.
    """
    now = float(now or time.time())
    open_recs = [r for r in stored(root) if not r.get("ended")]
    if not open_recs:
        return False
    try:
        card = news.newest_card(root)
    except OSError:
        card = (0.0, "")
    said = _agent(root)
    for rec in open_recs:
        if judge(root, rec, now, card=card, said=said).get("state") == "running":
            return True
    return False


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


# ---------------------------------------------------------------------------
# A mission whose node went away under it
# ---------------------------------------------------------------------------
# The ship's shape, one field at a time: which missions are owed a pick-up, and
# taking one exactly once across every board on the machine. What differs is
# that a ship happens after an ending and a carry happens INSTEAD of one, so
# nothing here may go through `of` -- `of` freezes, and a freeze is the thing
# being held off.


def owe_carry(root, rec, now=None):
    """Record that this mission is owed a pick-up. `due`'s counterpart.

    Written by the daemon on exit 75 BEFORE it re-queues, so the repair is
    derivable from the record if this node goes too in that window.

    THROUGH `_current`, LIKE EVERY WRITE HERE. `write` replaces the file, the
    caller's copy is minutes old by the time a sweep reaches it -- the hub
    holds one across an `agent start` -- and writing that copy back puts
    `carries` and `carried_at` where they were before a hop that has already
    been claimed. The flag for that hop exists, so nothing can ever claim the
    number again and both drivers go quiet on the mission for good.
    """
    now = float(now or time.time())
    out = _current(root, rec)
    out["carry"] = now
    return write(root, out)


def defer_carry(root, rec, now=None):
    """Hold the fallback pick-up off for one backoff: this daemon has it.

    THE DAEMON WAITING IS NOT A MISSION NOBODY IS DRIVING, and from the record
    alone the two look identical: `turn_at` is set, the node is fine, and
    `agent.json` says `listening` because the daemon is between attempts rather
    than in a turn. A chain gap is minutes to an hour of exactly that, and a
    pick-up per `CARRY_BACKOFF` through one spends `CARRY_HOPS` in half an hour
    and fails a mission whose client has not run once.

    `carried_at` is the field for it -- it is what "how long before another is
    owed" is measured from -- and it expires on its own, so a node dying inside
    the backoff costs the pick-up one `CARRY_BACKOFF` rather than losing it.
    """
    now = float(now or time.time())
    out = _current(root, rec)
    out["carried_at"] = now
    return write(root, out)


def claim_carry(root, rec, now=None):
    """Take this mission's pick-up, once, across every board on this machine.

    `claim_ship`'s twin, and exclusive for the same reason: every board reads
    every workspace's missions, so two of them would wake two turns onto the
    same conversation. The flag is named for the hop number, so hop two is
    claimable after hop one.

    THE COUNT IS READ BACK OFF DISK BEFORE IT IS WRITTEN, and the exclusive
    create is not enough on its own: the flag says nobody else took THIS hop,
    and the record says whether the caller's idea of which hop that is is
    still true. A caller holding a copy from before somebody else's hop would
    otherwise write the count backwards, and the flag for the number it wrote
    already exists.
    """
    now = float(now or time.time())
    mid = str(rec.get("id") or "")
    if not ID_RE.match(mid):
        return False
    hop = int(rec.get("carries") or 0) + 1
    flag = os.path.join(_dir(root), "%s.carry.%d" % (mid, hop))
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
    out = _current(root, rec)
    if int(out.get("carries") or 0) >= hop:
        return False
    out["carries"] = hop
    out["carried_at"] = now
    out["carry"] = 0.0
    write(root, out)
    return True


def _current(root, rec):
    """That record as it is on disk right now, or the one handed over.

    A mission turn lasts hours and the hub writes `carry` into the same file
    while it runs, so writing back a dict read at the start would drop it.
    """
    try:
        for got in stored(root):
            if got.get("id") == rec.get("id"):
                return got
    except Exception:                                        # noqa: BLE001
        pass
    return dict(rec)


def turn_open(root, rec, ceiling=None, session="", now=None):
    """A client is running against this mission right now, and in which session.

    THE ONE PIECE OF EVIDENCE A BOARD HOP CANNOT ERASE, and the reason the
    field exists: `agent.json` says `working` too, and the board that comes up
    next adopts that daemon and writes `waking` over it seconds later. This
    file is the daemon's alone.

    `ceiling` re-stamps when the generation the client just stepped into ends,
    because the one stamped at dispatch is about a generation that may be two
    hops back. `session` is the conversation id the turn is told to open.
    """
    now = float(now or time.time())
    out = _current(root, rec)
    out["turn_at"] = now
    if ceiling:
        out["ceiling"] = float(ceiling)
    if session:
        out["session"] = str(session)
    write(root, out)
    return out


def turn_over(root, rec, ran, now=None):
    """That client is gone and nothing is owed: the turn ended on its own terms.

    Called on exactly two paths -- the turn succeeded, or it failed for a
    reason no pick-up repairs -- and deliberately NOT in a `finally`. The
    carry, the wait and the cap all leave `turn_at` set, because a pick-up is
    still owed there and clearing it first opens a window where a node dying
    leaves nothing derivable.

    `ran` is how long the turn lasted, and a turn that got past `CARRY_FLOOR`
    clears the stall count: pick-ups that produced nothing are consecutive ones.
    """
    out = _current(root, rec)
    out["turn_at"] = 0.0
    out["carry"] = 0.0
    if float(ran or 0) >= CARRY_FLOOR:
        out["stalls"] = 0
    write(root, out)
    return out


def stalled(root, rec, ran, now=None):
    """Count a pick-up that produced nothing, or clear the count.

    `ran` is how long the carried turn lasted. Under `CARRY_FLOOR` it cannot
    have done anything on this engine, where a real turn spends minutes in
    prefill before it can even fail -- and a resume that dies instantly is the
    one branch that can make no progress for ever.
    """
    out = _current(root, rec)
    out["stalls"] = (int(out.get("stalls") or 0) + 1
                     if float(ran or 0) < CARRY_FLOOR else 0)
    return write(root, out)


def owed(now=None):
    """Every mission on this machine whose node went away under it.

    `due`'s twin, and deliberately NOT built on `of`: `of` freezes a terminal
    state into the record, and the whole of this is about a mission that must
    not be frozen.
    """
    now = float(now or time.time())
    out = []
    for w in atlas.workspaces():
        root = w["root"]
        try:
            said = _agent(root)
            recs = stored(root)
        except Exception:                                    # noqa: BLE001
            continue
        for rec in recs:
            if rec.get("ended") and not thaw(rec, now):
                continue
            if carry_verdict(rec, said, now) == "owed":
                out.append((w, rec))
    return out


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
