#!/usr/bin/env python3
"""A colibri mission whose node went away reads as mid-hop, not as failed.

Nothing picks such a mission up any more -- Colibri runs only as relay tasks,
so the daemon's hop and the hub's pick-up are gone. What is left is the read
side in `tutorboard/missions.py`, for records already on disk:

1. `carry_verdict` -- a pure decision off a record, an `agent.json` and a clock.
2. `judge` and `of` -- the freeze held off, and `thaw`, the one entitlement to
   undo one.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import machine, missions                # noqa: E402

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

    The hop, faked the way `watching.py` fakes one: a foreign host and a chosen
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
# `supervise.tutor_verdict` takes one.

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
# B, C. the freeze and the thaw -- on a real tree
# ---------------------------------------------------------------------------
base = tempfile.mkdtemp(prefix="tutor-carry-")
was_courses = os.environ.get("TUTORBOARD_COURSES")
try:
    psych = os.path.join(base, "projects", "PSYCH-ASR")
    write(os.path.join(psych, "tutorboard.json"), json.dumps({"name": "PSYCH-ASR"}))
    os.makedirs(os.path.join(psych, "live", "cards"), exist_ok=True)
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

    # AN `agent.json` WRITTEN OVER BY A LATER START. `mark_waking` writes over
    # `state`, and the heartbeat rule needs `AWAY_SILENCE`, fifteen minutes, so
    # it never fires. `turn_at` on a record already on disk is the daemon's own
    # word for a turn that was in flight.
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

    # THE SAME FIXTURE WITHOUT THE FIELD, WHICH IS THE DEFECT IT EXISTS FOR.
    # An unfinished mission reads `done` off the first card a doing turn writes
    # seconds after dispatch, and `of` freezes that.
    missions.write(psych, rec(turn_at=0.0))
    check("without `turn_at` the same hop reads as DONE off a card written "
          "before the work, which is why the field is in the record",
          missions.judge(psych, missions.stored(psych)[0], NOW,
                         said=json.loads(adopted))["state"] == "done")

    # A PERSON'S STOP IS NOT A HOP, and the difference is one field.
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

finally:
    os.environ.pop("TUTORBOARD_COURSES", None)
    if was_courses is not None:
        os.environ["TUTORBOARD_COURSES"] = was_courses
    shutil.rmtree(base, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails
      else "a mission that outlived its node reads as mid-hop, not as failed")
sys.exit(1 if fails else 0)
