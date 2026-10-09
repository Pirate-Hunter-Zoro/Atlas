"""What the board says about itself right now: the tutor, the write-up, the
documents and figures it can show.
"""

import json
import os
import time

from .. import machine, processes
from ..course import homework, paper, reading, results


def load_agent(repo):
    """Is an assistant attached, and is it working or waiting?

    An assistant nobody can see is worse than none. How that is decided depends
    on which kind it is: a headless daemon has a heartbeat and goes stale after
    two minutes of silence, while an interactive one is idle for as long as the
    person is thinking and is judged by whether its process is still there.
    Applying the heartbeat rule to both is why this indicator never once turned
    green in an ordinary `tutor` session.
    """
    try:
        with open(os.path.join(repo.live, "agent.json"), "r", encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        return None
    if st.get("state") == "waking" and processes.waking_now(st):
        # Say so, rather than letting the pid test below judge a record that has
        # no pid yet. This is the state the board most needs to be able to
        # paint: a start is in flight, nothing is lost, and the thing NOT to do
        # is send again. See `processes.agent_is_attached`.
        st["failure"] = None
        return st
    if not processes.agent_is_attached(st, machine.node_name()):
        # A daemon being BOUNCED is not a daemon that died, and the board is the
        # only place anybody finds out which it was. A restart marks the record
        # on its way out, so the gap between the old process going and the new
        # one writing its first heartbeat says "reattaching" rather than "no
        # tutor attached" -- which is what a course that never had one says, and
        # is a dead end in the middle of a lesson.
        st["state"] = "reattaching" if _reattaching(st) else "stale"
    # And whatever went wrong last, if it is still news. See `_failure`.
    st["failure"] = _failure(repo, st)
    # AND WHETHER THE PROVIDER ON THIS RECORD IS STANDING ASIDE, which until now
    # reached nobody. The expiry is written into `unreachable.json`, read by
    # `seeing.route`, and rendered in two places a person holding an iPad
    # cannot see: the `!!` lines in `agent.log` and the terminal output of
    # `board agents`. It is the one fact that answers "why is nothing
    # happening" -- the host, and when it will be asked again -- so it goes in
    # the payload beside the record it is about.
    st["stood_down"] = _stood_down(st.get("agent"))
    # WHAT THE TURN WAS WOKEN FOR belongs to the turn, and the record outlives
    # it: `turn_signal` is written when a turn starts and every path out of a
    # turn would otherwise have to remember to clear it. Cleared HERE, once,
    # because a stale one is a strip saying "re-planning" over a tutor that has
    # been listening for an hour.
    if st.get("state") != "working":
        st["turn_signal"] = ""
    return st


# WHAT A FAILED TURN LOOKS LIKE FROM THE IPAD, WHICH USED TO BE NOTHING AT ALL.
#
# A turn that fails writes `state: listening, last_error: <why>` and goes back
# to waiting. Every one of those words is true and not one of them reached the
# reader: the board painted "claude listening", the busy strip went away, and
# the student was left looking at a lesson with their working handed in and no
# answer coming -- with the chrome cheerfully saying the tutor was fine.
#
# Reported as "the tutor also appears to be very non responsive. Now it's just
# hanging. I need you to make the tutor way more robust. I don't ever want to be
# left hanging." The daemon was robust; it recovered from every one of those
# failures. It just never told anybody one had happened.
#
# So the failure is stamped with when it happened and handed over, and it is
# only reported while it is still the newest thing that has happened to this
# tutor -- a turn that has since succeeded clears it, and one from an hour ago
# is history rather than news.
# A cap on how long a failure can still be called news, and it is generous on
# purpose. What ENDS a failure is something newer happening -- see `_failure`.
# This is only here so that a board opened the morning after does not lead with
# last night's timeout.
FAILURE_FRESH = 12 * 3600


def _failure(repo, st):
    """The last turn's failure, while it is still the newest thing that happened.

    THIS USED TO EXPIRE ON A CLOCK, at fifteen minutes, and the clock was the
    wrong instrument. A doing turn that timed out left an opening sentence on the
    board -- "running the four typists on the pilot session's real audio" -- and
    fifteen minutes later the board stopped mentioning the failure at all. What
    was left was a present-tense card about work that had stopped, a tutor
    listening, and nothing anywhere saying so. That is the exact shape of the
    complaint this whole indicator exists for: "I don't ever want to be left
    hanging."

    So a failure is news until something newer happens -- a card written, an
    answer sent -- which is the thing that actually makes it old. A turn that has
    since succeeded clears it, because a card newer than the failure IS the
    success. The clock stays only as a long backstop.
    """
    if not st.get("last_error"):
        return None
    try:
        at = float(st.get("failed_at") or 0)
    except (TypeError, ValueError):
        return None
    # A TURN IN FLIGHT IS NEWER THAN THE FAILURE BEFORE IT. The record keeps the
    # reason -- a turn that starts settles nothing, and a daemon that dies
    # mid-turn must not have erased it -- but a turn that is running is the
    # newest thing that has happened, and painting last time's failure over it
    # tells the student their work has already failed when it is being answered.
    if st.get("state") == "working":
        try:
            if float(st.get("turn_started") or 0) >= at:
                return None
        except (TypeError, ValueError):
            pass
    if not at or time.time() - at > FAILURE_FRESH:
        return None
    # Anything newer than the failure means the board has moved on.
    if _newest(repo) > at + 1:
        return None
    return {"error": st["last_error"], "at": at}


def _stood_down(agent):
    """Why this provider cannot take a turn here and until when, or None.

    `until` is epoch seconds, formatted on the glass rather than here: the board
    already draws every other clock that way, and a string built in Python is a
    second place for the format to be decided.
    """
    if not agent:
        return None
    from ..net import egress
    got = egress.stood_down(agent)
    if not got:
        return None
    return {"host": got["host"], "why": got["why"], "until": got["until"]}


def _newest(repo):
    """When the board last had something happen on it: a card, or an answer.

    Asked with `getattr` rather than by attribute, and it is not defensive habit:
    this is called from `load_agent`, which every payload runs, and the whole
    point of the agent block is to say when something has gone wrong. A board
    that threw while working out what to report would take the lesson with it.
    """
    newest = 0.0
    cards_dir = getattr(repo, "cards", None)
    if cards_dir:
        try:
            for name in os.listdir(cards_dir):
                if not name.endswith(".md"):
                    continue
                try:
                    newest = max(newest, os.path.getmtime(os.path.join(cards_dir, name)))
                except OSError:
                    continue
        except OSError:
            pass
    turns_path = getattr(repo, "turns_path", None)
    if turns_path:
        try:
            newest = max(newest, os.path.getmtime(turns_path))
        except OSError:
            pass
    return newest


# How long a restart is given before the board stops calling it a restart. Long
# enough for a daemon to write its handoff turn and come back; short enough that
# a bounce that genuinely failed does not go on claiming to be in progress.
REATTACH_GRACE = 180


def _reattaching(st):
    """Was this record left behind by a restart that is still in flight?"""
    if not st.get("restarting"):
        return False
    try:
        since = time.time() - float(st.get("stopped_at") or 0)
    except (TypeError, ValueError):
        return False
    return 0 <= since <= REATTACH_GRACE


def load_hw(repo, st=None):
    """The session's write-up, and how much of it is written: the set or
    `docs/` write-up session.json pins (`Repo.state`'s `hw`), parsed from its
    .tex, with the last compile's outcome from the session's `hw.json`.

    None when nothing is pinned. Nothing here lists or globs the subject:
    the payload reads one file, the one the session is writing into.
    """
    st = repo.state() if st is None else st
    rel = str((st or {}).get("hw") or "")
    if not rel.endswith(".tex"):
        return None
    tex = os.path.abspath(os.path.join(repo.root, rel))
    inside = os.path.relpath(tex, os.path.abspath(repo.root))
    if inside.startswith("..") or not os.path.isfile(tex):
        return None
    try:
        probs = homework.problems(tex)
    except Exception:                                        # noqa: BLE001
        return None
    left = homework.outstanding(probs)
    out = {
        "name": homework._name_for(repo.root, tex),
        "rel": inside.replace(os.sep, "/"),
        "ambiguous": [],
        "problems": probs,
        "total": len(probs),
        "written": sum(1 for p in probs if p["written"]),
        "stated": sum(1 for p in probs if p["stated"]),
        "outstanding": left,
        "next": (left or [None])[0],
    }
    try:
        with open(os.path.join(repo.live, "hw.json"), "r", encoding="utf-8") as fh:
            out["build"] = json.load(fh)
    except (OSError, ValueError):
        out["build"] = None
    return out


def load_reading(repo):
    """The documents this course can be shown, as opposed to the two it builds.

    A deck explaining the machinery is the most useful thing in some of these
    repositories and the board could not display a page of it. See
    `course/reading.py`.
    """
    try:
        return reading.status(repo)
    except Exception:                                        # noqa: BLE001
        return None


def load_results(repo):
    """The figures this workspace's own pipeline made.

    The other half of `load_reading`. A document is what the project was written
    with; a figure is what it produced, and `results/<contrast>/
    propensity_by_arm.png` could not be put on the glass without somebody
    copying it into the lesson inbox. See `course/results.py`.
    """
    try:
        return results.status(repo)
    except Exception:                                        # noqa: BLE001
        return None


def load_papers(repo):
    """Which of the two documents exist on disk right now, and what they are called.

    THE CONTROLS FOR A DOCUMENT CANNOT LIVE IN THE BANNER OF THE BUILD THAT MADE
    IT. That is the defect this exists to close, reported from the iPad about
    the write-up: "it compiles the homework, but it's not letting me view the
    compiled .pdf or save it anywhere locally."

    The compile worked. What happened next is that the client painted the banner
    from a record it had invented locally -- `kind: "hw"` on the reply to
    `/hw/build`, which is on no disk anywhere -- and the very next payload, a
    second later, repainted the same banner from `push.json`. `save a copy` went
    with it, along with the URL behind it, so a tap after that second did
    nothing at all. A minute of LaTeX, a document sitting in the repository, and
    no way to reach it.

    So whether a document exists is a question the board answers on every
    payload, from the files, the way it answers every other question about
    itself. Four `stat` calls behind a payload that is already reading a dozen.

    See `course/paper.py`.
    """
    try:
        return paper.describe(repo)
    except Exception:                                        # noqa: BLE001
        return {}


def load_push(repo):
    """The outcome of the last push, so the iPad can see it without a terminal."""
    try:
        with open(os.path.join(repo.live, "push.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_export(repo):
    """The outcome of the last export, for the same reason.

    A LaTeX run is a minute of somebody staring at an iPad, and the answer to
    "did that work" cannot be a line in a terminal nobody is looking at. It also
    has to survive the payload that lands the moment it finishes, which is why
    it is a file rather than a message.
    """
    try:
        with open(os.path.join(repo.live, "export.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
