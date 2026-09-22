#!/usr/bin/env python3
"""A mission whose node went away under it, and the pick-up that finishes it.

    "make it so that no matter when a task by colibri is started, it will carry
     over to the next compute node that comes up when the current one expires
     [...] make it work so that all colibri tasks will eventually finish."

The server already survives: `coli-up` starts a chain and a generation hands
over to its successor before it cancels itself. The CLIENT does not. `coli-code`
runs `srun --jobid --overlap`, so it is a step of one generation and dies with
it, and nothing re-ran it -- the mission froze `failed` within one hub poll with
a reason shaped exactly like the hop it was.

What is guarded here is the repair, in the four places it lives:

1. `carry_verdict` -- a pure decision off a record, an `agent.json` and a clock,
   because the case that matters is both allocations ending in the same minute
   with nothing left running anywhere to remember anything.
2. `judge` and `of` -- the freeze held off, and the one entitlement to undo one.
3. `spawn.carry_missions` -- the driver that runs in whichever board comes up
   next, waking exactly one turn per hop.
4. `tutor` -- the two decisions the daemon makes, as functions with no daemon.

`hopping.py` is the other half and takes the two things that only happen when a
process runs: killing a turn's whole group, and three passes of a stub client.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import (atlas, brief, machine, missions,     # noqa: E402
                        progress, sense)
from tutorboard.course import repo as course_repo               # noqa: E402
from tutorboard.server import spawn as _spawn                   # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
_spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(_spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def card(root, num, slug, body, when=None):
    p = os.path.join(root, "live", "cards", "%s-%s.md" % (num, slug))
    write(p, body + "\n")
    if when:
        os.utime(p, (when, when))
    return p


NOW = 1_800_000_000.0


def rec(**kw):
    """A colibri mission record, dispatched an hour before `NOW`."""
    out = {"id": "t0054", "task": "repair the diarization", "agent": "colibri",
           "at": NOW - 3600, "ship": False, "from": "", "host": "compute300",
           "card_at": 0.0, "ceiling": NOW + 600, "ended": "", "ended_at": 0.0,
           "reason": "", "looked": 0.0, "shipped": 0.0, "carry": 0.0,
           "carries": 0, "carried_at": 0.0, "stalls": 0,
           "life": NOW - 3600 + missions.MISSION_LIFE}
    out.update(kw)
    return out


def gone(**kw):
    """An `agent.json` left by a daemon that went with another node.

    The hop, faked the way `perpetual.py` fakes one: a foreign host and a chosen
    `last_seen`. `AWAY_SILENCE` is 900 s, so twenty minutes of silence from a
    node this machine cannot read a process table on is a daemon that is gone.
    """
    out = {"agent": "colibri", "state": "working", "pid": 1,
           "host": "compute999", "last_seen": NOW - 1200, "last_error": None,
           "turns": 1, "mode": "headless"}
    out.update(kw)
    return out


# ---------------------------------------------------------------------------
# A. carry_verdict, as a decision table
# ---------------------------------------------------------------------------
# No cluster and no clock to wait on: `now` is an argument, the way
# `supervise.tutor_verdict` and `left_behind` take one.

check("a colibri mission whose daemon went silent with its node is owed a "
      "pick-up rather than called failed",
      missions.carry_verdict(rec(), gone(), NOW) == "owed")

check("and the same record with a failure on it is NOT, because an ordinary "
      "failure is still a failure",
      missions.carry_verdict(rec(), gone(last_error="the model refused"),
                             NOW) == "no")

check("and one whose daemon is still beating is not either -- two clients on "
      "one conversation is the one outcome worse than the hop",
      missions.carry_verdict(rec(), gone(last_seen=NOW - 10), NOW) == "no")

check("a mission run by an assistant whose client is not a step of somebody "
      "else's allocation is nothing to do with this",
      missions.carry_verdict(rec(agent="claude"), gone(), NOW) == "no")

spent = missions.carry_verdict(rec(carries=missions.CARRY_HOPS), gone(), NOW)
check("six pick-ups and it is spent, and the row says six",
      isinstance(spent, tuple) and spent[0] == "spent" and "six" in spent[1])

spent = missions.carry_verdict(rec(at=NOW - 19 * 3600, life=NOW - 3600),
                               gone(), NOW)
check("eighteen hours of picking it up and it is spent, and the row says "
      "eighteen -- the budget pays for every re-prefill a hop causes",
      isinstance(spent, tuple) and "eighteen hours" in spent[1])

spent = missions.carry_verdict(rec(stalls=missions.STALL_CAP), gone(), NOW)
check("two pick-ups that produced nothing and it is spent, which is what "
      "bounds a resume that dies on sight",
      isinstance(spent, tuple) and "produced nothing" in spent[1])

check("a pick-up claimed thirty seconds ago is not due yet, so a start "
      "refused for the one KV slot retries under a backoff rather than looping",
      missions.carry_verdict(rec(carried_at=NOW - 30), gone(), NOW) == "soon")

check("and it says `soon` rather than `no`, because the backoff is about when "
      "a turn may be woken and says nothing about whether the work is over",
      missions.carry_verdict(rec(carried_at=NOW - 30), gone(), NOW)
      != missions.carry_verdict(rec(agent="claude"), gone(), NOW))

check("and the backoff lives in the record rather than in a daemon's locals, "
      "so a hop does not reset it",
      "carried_at" in missions.FIELDS and "carries" in missions.FIELDS
      and "life" in missions.FIELDS)

# A record written before any of this existed must still be carryable: there is
# one on disk right now with a mission running against it.
old = rec()
for k in ("carry", "carries", "carried_at", "stalls", "life"):
    old.pop(k)
check("a record written before the carry existed is carried all the same, "
      "because its budget falls back to its dispatch",
      missions.carry_verdict(old, gone(), NOW) == "owed"
      and isinstance(missions.carry_verdict(old, gone(), NOW + 19 * 3600),
                     tuple))
check("and that fallback budget is eighteen hours, because it pays for every "
      "re-prefill a hop causes and six of those do not fit in twelve",
      missions.MISSION_LIFE == 18 * 3600
      and missions.carry_verdict(old, gone(), NOW + 16 * 3600) == "owed")


# ---------------------------------------------------------------------------
# B, C, D. the freeze, the thaw, and the wake -- on a real tree
# ---------------------------------------------------------------------------
base = tempfile.mkdtemp(prefix="tutor-carry-")
was_courses = os.environ.get("TUTORBOARD_COURSES")
real_tutor_cli = _spawn.tutor_cli
try:
    write(os.path.join(base, "atlas.json"),
          json.dumps({"families": [{"id": "research", "name": "Research"}]}))
    psych = os.path.join(base, "research", "PSYCH-ASR")
    write(os.path.join(psych, "tutorboard.json"), json.dumps({"name": "PSYCH-ASR"}))
    os.makedirs(os.path.join(psych, "live", "cards"), exist_ok=True)
    atlas.forget()
    os.environ["TUTORBOARD_COURSES"] = base

    # THE FIXTURE: a doing turn that wrote its first card seconds after dispatch
    # and then lost its node.
    missions.write(psych, rec())
    card(psych, "0001", "starting", "About to repair the diarization.",
         NOW - 3590)
    write(os.path.join(psych, "live", "agent.json"), json.dumps(gone()))

    got = missions.judge(psych, missions.stored(psych)[0], NOW)
    check("a mission with a card down and a dead daemon reads as RUNNING, not "
          "done -- the first card of a doing turn is written before the work",
          got["state"] == "running")

    missions.of(psych, NOW)
    check("and nothing is frozen into the record, which is the one line the "
          "whole design stands on",
          missions.stored(psych)[0]["ended"] == "")

    # THE ADOPTION, WHICH ERASES `agent.json` BEFORE ANY RULE OFF IT RIPENS.
    # A board coming up starts the left-behind daemon within seconds --
    # `left_behind` only wants `last_seen` inside `ADOPT_WINDOW`, an hour --
    # and `mark_waking` writes over `state`. The heartbeat rule needs
    # `AWAY_SILENCE`, fifteen minutes, so it never fires. `turn_at` is the
    # daemon's own word for a turn in flight and nothing else writes it.
    adopted = json.dumps(gone(state="listening", host=machine.node_name(),
                              pid=os.getpid(), last_seen=NOW))
    write(os.path.join(psych, "live", "agent.json"), adopted)
    missions.write(psych, rec(turn_at=NOW - 1800))
    check("a daemon adopted onto the next node erases `agent.json`, and the "
          "mission is still owed",
          missions.carry_verdict(missions.stored(psych)[0],
                                 json.loads(adopted), NOW) == "owed")
    check("and `judge` says running with a card already down, because the "
          "pick-up is ahead of the card rule",
          missions.judge(psych, missions.stored(psych)[0], NOW,
                         said=json.loads(adopted))["state"] == "running")

    # THE FIVE MINUTES AFTER A HOP IS CLAIMED, which every hop has. The backoff
    # says when another pick-up may be WOKEN and nothing about the work, and a
    # reader that takes it for "nothing is owed" walks on into the card rule
    # with the card already down.
    missions.write(psych, rec(turn_at=NOW - 1800, carries=1,
                              carried_at=NOW - 30))
    check("a mission inside the backoff of the hop it has just taken is still "
          "mid-hop, and does not read as done off a card written before the "
          "work",
          missions.carry_verdict(missions.stored(psych)[0],
                                 json.loads(adopted), NOW) == "soon"
          and missions.judge(psych, missions.stored(psych)[0], NOW,
                             said=json.loads(adopted))["state"] == "running")
    missions.of(psych, NOW)
    check("and nothing is frozen into the record inside that window either, "
          "because `done` is terminal and no thaw reaches it",
          missions.stored(psych)[0]["ended"] == "")
    check("and the walk offers it to nobody all the same, which is what the "
          "backoff is for",
          [m["id"] for _, m in missions.owed(NOW)] == [])

    # THE SAME FIXTURE WITHOUT THE FIELD, WHICH IS THE DEFECT IT EXISTS FOR.
    # An unfinished mission reads `done` off the first card a doing turn writes
    # seconds after dispatch, and `of` freezes that.
    missions.write(psych, rec(turn_at=0.0))
    check("without `turn_at` the same hop reads as DONE off a card written "
          "before the work, which is why the field is in the record",
          missions.judge(psych, missions.stored(psych)[0], NOW,
                         said=json.loads(adopted))["state"] == "done")

    # AND THE TURN ENDING ON ITS OWN TERMS CLEARS IT.
    missions.write(psych, rec(turn_at=NOW - 1800))
    missions.turn_over(psych, missions.stored(psych)[0], 600.0)
    check("`turn_over` clears the turn, so a mission that finished judges done "
          "rather than being picked up for ever",
          missions.stored(psych)[0]["turn_at"] == 0.0
          and missions.judge(psych, missions.stored(psych)[0], NOW,
                             said=json.loads(adopted))["state"] == "done")
    missions.write(psych, rec(turn_at=NOW - 60, stalls=1))
    missions.turn_over(psych, missions.stored(psych)[0], 30.0)
    check("a turn shorter than the floor leaves the stall count standing, "
          "because a pick-up that produced nothing is what that counts",
          missions.stored(psych)[0]["stalls"] == 1
          and missions.stored(psych)[0]["turn_at"] == 0.0)
    missions.write(psych, rec(turn_at=NOW - 60, stalls=1))
    missions.turn_over(psych, missions.stored(psych)[0], missions.CARRY_FLOOR)
    check("and a turn that got past it resets them, because the two that end "
          "a mission are consecutive",
          missions.stored(psych)[0]["stalls"] == 0)

    # A PERSON'S STOP IS NOT A HOP, and the difference is one field --
    # `supervise.left_behind` draws the same line for the same reason.
    stopped = gone(state="stopped")
    check("a mission whose assistant somebody stopped is left stopped",
          missions.carry_verdict(rec(turn_at=NOW - 1800), stopped, NOW) == "no")
    check("and one whose board handed over is picked up, because a handover is "
          "the board moving node with the work going on",
          missions.carry_verdict(rec(turn_at=NOW - 1800),
                                 gone(state="stopped", handover="2026-09-21"),
                                 NOW) == "owed")

    # THE CEILING YIELDS TO THE BUDGET. It is the walltime of the generation
    # the client stepped into, and the chain brings another one up.
    missions.write(psych, rec(ceiling=NOW - 60, turn_at=0.0))
    beating = gone(host=machine.node_name(), pid=os.getpid(), last_seen=NOW)
    check("a ceiling that has passed with budget left is a hop rather than an "
          "ending, so the mission is still running",
          missions.judge(psych, missions.stored(psych)[0], NOW,
                         card=(0.0, ""), said=beating)["state"] == "running")
    missions.write(psych, rec(ceiling=NOW - 60, turn_at=0.0,
                              carries=missions.CARRY_HOPS))
    spent_here = missions.judge(psych, missions.stored(psych)[0], NOW,
                                card=(0.0, ""), said=beating)
    check("and with the budget gone it fails, on the count rather than on the "
          "allocation, which is the reason that is actually true",
          spent_here["state"] == "failed"
          and "picked up six times" in spent_here["reason"])

    # THE THAW. A board that predates this change froze the mission `failed`
    # with a reason shaped like the hop it was; this is the only thing that
    # recovers such a record. Back to a daemon that went with its node, which
    # is what the record on disk looks like before anything adopts it.
    write(os.path.join(psych, "live", "agent.json"), json.dumps(gone()))
    def frozen(**kw):
        r = rec(ended="failed", ended_at=NOW - 60, reason="exit 1")
        r.update(kw)
        missions.write(psych, r)
        return r

    frozen()
    judged = missions.of(psych, NOW)
    check("a mission frozen `failed` by a board that ran before this is thawed "
          "and reads as running again",
          [m["state"] for m in judged] == ["running"])
    check("and the file says so too, or every reader would derive the same "
          "clearing for ever",
          missions.stored(psych)[0]["ended"] == "")

    frozen(looked=NOW - 30)
    check("a mission somebody has already READ is theirs and stays failed, "
          "because resurrecting it under them is worse than the defect",
          [m["state"] for m in missions.of(psych, NOW)] == ["failed"])

    frozen(reason="the model refused the task")
    check("and one that failed on its own stays failed, because only a hop "
          "wears a hop's reasons",
          [m["state"] for m in missions.of(psych, NOW)] == ["failed"])

    # THE WAKE. `carry_missions` is the second driver: the mission's own daemon
    # went with the board's allocation, so this runs in the next board's hub.
    ran = []
    _spawn.tutor_cli = lambda args, timeout=30: (ran.append(list(args))
                                                 or (0, "started"))
    missions.write(psych, rec())
    write(os.path.join(psych, "live", "agent.json"), json.dumps(gone()))
    _spawn._CARRIES["at"] = 0.0
    handed = _spawn.carry_missions(NOW)
    check("the board that comes up next picks the mission up, off the record "
          "and `agent.json` alone",
          [h["mission"] for h in handed] == ["t0054"]
          and handed[0]["agent"] == "colibri")
    check("and starts the assistant that was on it, named rather than "
          "defaulted, without moving the one address",
          ["agent", "start", "PSYCH-ASR", "--respawn", "--agent", "colibri"]
          in ran)

    target = course_repo.Repo(psych)
    with open(target.messages_path, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    check("the turn it is woken with is a [carry] line in that workspace's "
          "inbox, which is what `board wait` watches",
          len(lines) == 1 and lines[-1]["signal"] == "carry"
          and lines[-1]["text"].startswith("[carry] "))
    check("and it carries the task, so the resumed turn is told what it was on",
          "repair the diarization" in lines[-1]["text"])
    check("and the record counts the hop, so the row can say picked up 1x and "
          "the budget can run out",
          [m["carries"] for m in missions.stored(psych)] == [1])

    ran[:] = []
    _spawn._CARRIES["at"] = 0.0
    check("a second board sweeping straight afterwards wakes nothing, because "
          "the pick-up it just claimed is stamped in the record",
          _spawn.carry_missions(NOW) == [] and ran == [])

    # AND THE CLAIM ITSELF, which is what two boards racing on the SAME hop hit.
    # Both read the record before either wrote it, so the stamp is no use and
    # the exclusive create is the only thing that is atomic here.
    stale = missions.stored(psych)[0]
    stale["carries"] = 0
    check("two boards claiming the same hop off the same record get one yes "
          "and one no, which is what stops two turns on one conversation",
          not missions.claim_carry(psych, stale, NOW)
          and missions.claim_carry(psych, dict(stale, carries=1), NOW))

    # AND THE TWO-CLIENTS GUARD, from the other side: the walk judged a moment
    # ago and a daemon has been adopted onto this node since. `owed` is stubbed
    # to say yes, because the point is the SECOND look -- the one that happens
    # between deciding and waking.
    missions.write(psych, rec(id="t0055"))
    write(os.path.join(psych, "live", "agent.json"), json.dumps(
        gone(host=machine.node_name(), pid=os.getpid(), last_seen=NOW)))
    ran[:] = []
    _spawn._CARRIES["at"] = 0.0
    real_owed = missions.owed
    missions.owed = lambda now=None: [({"id": "research/PSYCH-ASR",
                                        "dir": "PSYCH-ASR", "root": psych},
                                       rec(id="t0055"))]
    try:
        woke = _spawn.carry_missions(NOW)
    finally:
        missions.owed = real_owed
    check("nothing is woken where a turn started between the walk and the "
          "wake, because two clients on one conversation is worse than the hop "
          "it would repair",
          woke == [] and ran == [])
    check("and the pick-up is in the record all the same, so the board that "
          "adopts that daemon does not have to derive it again",
          [m["carry"] > 0 for m in missions.stored(psych)
           if m["id"] == "t0055"] == [True])

    # THE ADOPT RACE, WHICH THE LAST CLAUSE OF `carry_verdict` CANNOT SEE ON
    # ITS OWN. A board coming up starts the daemon before its hub polls, so the
    # record has already gone from `working` to `listening` by the time the
    # walk looks. An idle daemon is what an inbox line is FOR.
    write(os.path.join(psych, "live", "agent.json"), json.dumps(
        gone(host=machine.node_name(), pid=os.getpid(), last_seen=NOW,
             state="listening")))
    ran[:] = []
    _spawn._CARRIES["at"] = 0.0
    woke = _spawn.carry_missions(NOW + missions.CARRY_BACKOFF + 1)
    check("a daemon adopted onto this node and sitting idle is handed the "
          "pick-up rather than left blocked on an inbox nobody will fill",
          [h["mission"] for h in woke] == ["t0055"]
          and any(a[:2] == ["agent", "start"] for a in ran))

    # A WORKSPACE SOMEBODY ELSE'S ASSISTANT IS SITTING IN. `tutor agent start`
    # will not swap one for another -- a live record is "already listening" --
    # so a pick-up that only starts would leave its `[carry]` line to be
    # answered by the wrong assistant, in a workspace that is fenced.
    missions.write(psych, rec(id="t0056", carry=NOW, carried_at=0.0))
    write(os.path.join(psych, "live", "agent.json"), json.dumps(
        gone(agent="claude", state="listening", host=machine.node_name(),
             pid=os.getpid(), last_seen=NOW)))
    ran[:] = []
    _spawn._CARRIES["at"] = 0.0
    woke = _spawn.carry_missions(NOW + missions.CARRY_BACKOFF + 1)
    stops = [i for i, a in enumerate(ran) if a[:2] == ["agent", "stop"]]
    starts = [i for i, a in enumerate(ran)
              if a[:2] == ["agent", "start"] and "colibri" in a]
    check("an assistant of another name holding that workspace is stopped "
          "before the pick-up is woken, so the mission's own assistant is the "
          "one that answers the line",
          "t0056" in [h["mission"] for h in woke]
          and stops and starts and stops[0] < starts[0])
    # AND THE PICK-UP IS WHAT PUT THAT ASSISTANT THERE, recorded, because a
    # release reads it: an assistant started FOR a mission is given back when
    # the mission ends, and the node the dispatch's one was on has gone. The
    # record said the mission brought nobody -- it took whoever was listening
    # -- and this hop is the moment that stops being true.
    check("a pick-up records that it brought the assistant, so the workspace "
          "is given back when the mission ends rather than left holding one "
          "nobody asked for",
          [m.get("brought") for m in missions.stored(psych)
           if m["id"] == "t0056"] == ["colibri"])

    # WHICH MISSION THE DEAD TURN WAS ON. A daemon answers one workspace and a
    # workspace runs one mission at a time, so the newest OPEN record is it --
    # and a mission that finished an hour ago is newer than the one still going.
    solo = os.path.join(base, "research", "TRD-EHR")
    os.makedirs(os.path.join(solo, "live"), exist_ok=True)
    missions.write(solo, rec(id="t0060", at=NOW - 1800))
    missions.write(solo, rec(id="t0061", at=NOW - 60, ended="done",
                             ended_at=NOW - 30))
    check("the daemon finds the mission that is still open rather than the one "
          "that finished after it",
          (tutor.open_mission(solo) or {}).get("id") == "t0060")

    # And the walk itself refuses it for the same reason, one layer up.
    _spawn._CARRIES["at"] = 0.0
    check("and the walk does not offer it either",
          [m["id"] for _, m in missions.owed(NOW)] == [])
finally:
    _spawn.tutor_cli = real_tutor_cli
    os.environ.pop("TUTORBOARD_COURSES", None)
    if was_courses is not None:
        os.environ["TUTORBOARD_COURSES"] = was_courses
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------------------
# E. the two decisions the daemon makes, with no daemon
# ---------------------------------------------------------------------------
check("exit 75 is the hop and nothing else is",
      tutor.reads_as_carry("exit 75") and not tutor.reads_as_carry("exit 1")
      and not tutor.reads_as_carry("timed out"))

line = tutor.carry_line("[2026-09-20 17:37:53] do the thing")
check("a re-queued inbox line is tagged where `turn_signal` reads the tag "
      "from, which is the text and not a field beside it",
      tutor.turn_signal(line) == "carry")
check("and the stamp stays in front of it, because `board inbox` wrote that "
      "stamp and this is the same message",
      line.startswith("[2026-09-20 17:37:53] [carry] do the thing"))
check("a line that already carries the tag is handed back untouched, so a "
      "second hop does not stack a second tag on it",
      tutor.carry_line(line) is line)
check("and an untagged line still gets one, stamp and all",
      tutor.turn_signal(tutor.carry_line("do the thing")) == "carry")
check("every later line is kept, because the file paths are in them",
      tutor.carry_line("[2026-09-20 17:37:53] do it\nfile: live/a.png")
      .endswith("\nfile: live/a.png"))


SRC = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
check("the daemon's one retry is held off a hop, a wait and the cap, because "
      "all three keep the session and retrying one fresh pays a whole "
      "preamble and eats the signal that says what happened",
      "keeps = timed_out or reads_as_carry(err) or reads_as_wait(err)" in SRC
      and "use is not first and not keeps" in SRC)
check("a hop stamps no failure, because `missions.judge`'s failure rule fires "
      "off `last_error` and a mission frozen failed is never re-derived",
      "missions.owe_carry(root, mrec)" in SRC
      and 'last_error=None,\n                            failed_at=0' in SRC)


# ---------------------------------------------------------------------------
# G. the client, which is the only process that knows which job it stepped into
# ---------------------------------------------------------------------------
CODE = os.path.join(os.path.dirname(ROOT), "projects", "libr-local-llm",
                    "bin", "coli-code")
if not os.path.isfile(CODE):
    print("note libr-local-llm is not checked out here; skipping the client half")
else:
    src = open(CODE, encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    check("`coli-code` exits 75 when the generation its step ran in ended "
          "under it, by the name the number is given rather than by a literal "
          "in two places",
          "COLI_CARRIED_AWAY=75" in code
          and 'exit "$COLI_CARRIED_AWAY"' in code)
    check("and the srun is guarded, or the script would die on the exit code "
          "before it could ask what the code meant",
          "set +e" in code and "set -e" in code.split("srun_on_server")[-1])
    check("Slurm is asked rather than the exit code read, because a cancelled "
          "step and a bad answer are the same number",
          "coli_jobs" in code.split("RC=$?")[-1])
    check("and asked more than once, because an empty answer is also what a "
          "controller nobody can reach looks like",
          "for _ in 1 2 3" in code and "sleep 10" in code)
    check("a job that has self-cancelled sits in the queue COMPLETING, so only "
          "RUNNING counts as still there",
          '$2 == "RUNNING"' in code)
    check("and 76 where there is nothing worth stepping into yet, which is a "
          "wait and is neither a hop nor a failure",
          "COLI_NOTHING_YET=76" in code
          and code.count('exit "$COLI_NOTHING_YET"') >= 2)
    nojob = code.split('if [ -z "$JOB_ID" ]; then')[1].split("\nfi\n")[0]
    check("no generation running at all is that wait, because a chain gap is "
          "ordinary -- the successor is a 68-minute cold pin and pends behind "
          "a full node -- and a pick-up landing in one must record no failure",
          'exit "$COLI_NOTHING_YET"' in nojob and "exit 1" not in nojob)
    short = code.split("FLOOR=3600")[1].split('exit "$COLI_NOTHING_YET"')[0]
    check("a generation with less left than the session needs to prefill is "
          "refused -- an hour cold, half an hour warm -- and only where a "
          "successor exists, because with the chain broken trying beats "
          "stalling",
          "FLOOR=1800" in code and "NEXT_JOB" in short
          and "coli_jobs" in short)
    check("and the successor has to be a job Slurm says is arriving, because "
          "a self-cancelled generation sits in the queue COMPLETING and "
          "waiting for one that is leaving is waiting for ever",
          '$2 == "PENDING"' in short and '$2 == "RUNNING"' in short)
    check("and the conversation is named where a driver knows the name, "
          "because `--continue` takes the newest in the directory and the "
          "newest is not necessarily this mission's",
          "COLI_SESSION_ID" in code and "--resume" in code
          and "--session-id" in code)
    check("the header names both numbers, because the board's daemon branches "
          "on them",
          "exits 75 here" in src and "and 76 where there is no generation" in src)
    check("and the client is syntactically sound",
          subprocess.run(["bash", "-n", CODE]).returncode == 0)

# ---------------------------------------------------------------------------
# H. two watchers writing the same record, and one waiting while the other looks
# ---------------------------------------------------------------------------
# The claim is atomic and the WRITE AROUND IT IS NOT. Every board sweeps every
# workspace and the daemon sweeps its own, so two of them hold a copy of the
# same record at once -- the hub's is minutes old by the time an `agent start`
# has returned -- and `write` replaces the file rather than merging into it.
book = tempfile.mkdtemp(prefix="tutor-carry-race-")
try:
    ws = os.path.join(book, "PSYCH-ASR")
    os.makedirs(os.path.join(ws, "live", "missions"))
    missions.write(ws, rec())
    mine = missions.stored(ws)[0]
    theirs = missions.stored(ws)[0]          # the same instant, another board

    missions.owe_carry(ws, mine, NOW)
    missions.claim_carry(ws, mine, NOW)
    missions.owe_carry(ws, theirs, NOW + 1)  # the loser's copy, written back
    check("a board writing back a copy it read before somebody else's hop "
          "cannot rewind the count, because the flag for the number it would "
          "write already exists and nothing could ever claim it again",
          missions.stored(ws)[0]["carries"] == 1)
    check("and the loser's claim is refused rather than counted twice",
          not missions.claim_carry(ws, theirs, NOW + 1))
    check("while the next hop is still there to be taken, which is what the "
          "budget is for",
          missions.claim_carry(ws, missions.stored(ws)[0],
                               NOW + missions.CARRY_BACKOFF + 1)
          and missions.stored(ws)[0]["carries"] == 2)

    # AND THE CLAIM ITSELF IS A WRITE, so it drops whatever the daemon wrote
    # while the sweep that is claiming was busy starting an assistant in the
    # workspace before this one -- which is `turn_at` and the conversation id,
    # the two fields the whole repair is derived from.
    missions.write(ws, rec(id="t0056"))
    sweeping = [r for r in missions.stored(ws) if r["id"] == "t0056"][0]
    opened = missions.turn_open(ws, sweeping, session="6f1a-not-a-guess",
                                now=NOW + 60)
    missions.claim_carry(ws, sweeping, NOW + 61)
    landed = [r for r in missions.stored(ws) if r["id"] == "t0056"][0]
    check("and claiming a hop off a copy read before the turn opened leaves "
          "the turn and its conversation where the daemon put them, because "
          "those two fields are the repair",
          landed.get("session") == opened["session"]
          and landed.get("turn_at") == opened["turn_at"])

    # AND THE DAEMON'S OWN TWO WRITES, one line apart. `owe_carry` puts the
    # repair on disk before anything can refuse it; `stalled` follows it with
    # the same record, and a copy written back over that is the repair gone.
    missions.write(ws, rec(id="t0055"))
    held = [r for r in missions.stored(ws) if r["id"] == "t0055"][0]
    missions.owe_carry(ws, held, NOW)
    missions.stalled(ws, held, 1.0)
    after = [r for r in missions.stored(ws) if r["id"] == "t0055"][0]
    check("counting a pick-up that produced nothing does not take the pick-up "
          "owed off the record with it, which is the one thing a node dying "
          "in that window leaves behind",
          after["carry"] > 0 and after["stalls"] == 1)

    # THE CHAIN GAP, WHICH IS THE ORDINARY CASE AND THE EXPENSIVE ONE. The
    # daemon loops on exit 76 with its backoff while the successor cold-pins,
    # and from the record alone that is indistinguishable from a mission
    # nobody is driving: `turn_at` set, `listening`, on a node that is fine.
    gap = os.path.join(book, "TRD-EHR")
    os.makedirs(os.path.join(gap, "live", "missions"))
    missions.write(gap, rec(id="t0060"))
    here = gone(host=machine.node_name(), pid=os.getpid(), last_seen=NOW,
                state="listening")
    t, stolen = NOW, 0
    while t < NOW + 68 * 60:                     # a 68-minute cold pin
        missions.turn_open(gap, missions.stored(gap)[0], now=t)
        t += 5                                   # the client exits 76
        missions.defer_carry(gap, missions.stored(gap)[0], now=t)
        end = t + missions.CARRY_BACKOFF
        while t < end:                           # the hub polls underneath it
            got = missions.stored(gap)[0]
            here["last_seen"] = t
            if (missions.carry_verdict(got, here, t) == "owed"
                    and missions.claim_carry(gap, got, t)):
                stolen += 1
            t += _spawn.CARRY_EVERY
        missions.defer_carry(gap, missions.stored(gap)[0], now=t)
    check("a daemon waiting out a chain gap is not a mission nobody is "
          "driving, so the fallback takes no hop off it -- a pick-up every "
          "backoff would spend `CARRY_HOPS` inside half an hour and fail a "
          "mission whose client has not run once",
          stolen == 0 and missions.stored(gap)[0]["carries"] == 0)
    check("and the hold expires on its own, so a node dying inside the "
          "backoff costs the pick-up one backoff rather than losing it",
          missions.carry_verdict(missions.stored(gap)[0], gone(),
                                 t + missions.CARRY_BACKOFF + 1) == "owed")

    # -----------------------------------------------------------------------
    # I. AND WHAT THE LOST TURN ACHIEVED CROSSES OVER WITH THE WORK
    # -----------------------------------------------------------------------
    # The hop keeps the task. Until the trail existed it threw away everything
    # the cut-off turn had done: the conversation may be resumable and where
    # the node took the client with it there is nothing to resume, so the next
    # turn started the same nine hours again from the same sentence. A trail is
    # a file in the workspace for exactly the reason the record is -- both
    # allocations end in the same minute, and nothing is running anywhere to
    # remember anything.
    trail = os.path.join(book, "Galois-Theory")
    os.makedirs(os.path.join(trail, "live", "missions"))
    missions.write(trail, rec(id="t0070"))
    missions.turn_open(trail, missions.stored(trail)[0], now=NOW)
    progress.add(trail, "t0070", "rebuilt the reference from the error log",
                 now=NOW + 10)
    missions.owe_carry(trail, missions.stored(trail)[0], NOW + 20)
    missions.claim_carry(trail, missions.stored(trail)[0],
                         NOW + missions.CARRY_BACKOFF + 1)
    crossed = progress.read(trail, "t0070")
    check("a pick-up keeps what the cut-off turn reported, because the trail "
          "is a file in the workspace and not something a dead client was "
          "holding",
          any(s["said"] == "rebuilt the reference from the error log"
              and s["who"] == "agent" for s in crossed))
    check("and the hop writes itself onto the trail, because half an hour with "
          "nothing new on it reads as a wedged mission and is the machinery "
          "working",
          any(s["who"] == "board" and "picked up" in s["said"]
              and "1 of %d" % missions.CARRY_HOPS in s["said"]
              for s in crossed))
    check("and a turn opening says so too, so the gap between a dispatch and "
          "the first word of a model that prefills for hours is not a silence",
          [s["said"] for s in crossed if s["who"] == "board"][0].startswith(
              "a turn started on"))
    # AND THE CARRIED TURN READS IT. A resumed conversation has it already; a
    # cold one after the node went has nothing else that says the first four
    # hours happened, and `board brief` is the whole of what it reads.
    briefed = brief.briefing(course_repo.Repo(trail), sense,
                             mission=missions.stored(trail)[0])
    check("and the briefing the carried turn reads carries the trail, which is "
          "the only thing that says the hours before it happened",
          "rebuilt the reference from the error log" in briefed
          and "Do not do any of that again" in briefed)
    # AND THE TRAIL DIES WITH THE RECORD. A `.steps` file with no `.json`
    # beside it is what turns `live/missions/` back into a log.
    old = dict(missions.stored(trail)[0])
    old.update(ended="done", ended_at=NOW - missions.KEEP - 60)
    missions.write(trail, old)
    missions.of(trail, NOW)
    check("and an ended mission pruned off disk takes its trail with it",
          not os.path.exists(progress.steps_path(trail, "t0070")))
finally:
    shutil.rmtree(book, ignore_errors=True)

wait_branch = SRC.split("if reads_as_wait(err)")[1].split("if reads_as_carry")[0]
check("and the daemon says so on both sides of the wait, because the hold "
      "runs out as the sleep does and the next turn needs the second it takes "
      "to write `working`",
      wait_branch.count("missions.defer_carry(root, mrec)") == 2)

print("%d FAILURES" % len(fails) if fails
      else "a mission outlives the node it was started on, and says how many "
           "times it has")
sys.exit(1 if fails else 0)
