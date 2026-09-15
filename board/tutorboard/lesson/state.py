"""What the board says about itself right now: the tutor, the write-up, the
review scope, the contents.
"""

import json
import os
import time

from .. import machine, processes
from ..course import homework, paper, plan, reading, results, review, syllabus, walk
# `map` is a builtin, and a module called `map` imported under its own name
# would shadow it for the rest of this file. The file keeps the name the board
# calls the thing; the binding does not.
from ..course import map as mapping
from . import archive, cards


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
    if not at or time.time() - at > FAILURE_FRESH:
        return None
    # Anything newer than the failure means the board has moved on.
    if _newest(repo) > at + 1:
        return None
    return {"error": st["last_error"], "at": at}


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


def load_hw(repo):
    """This sitting's problem set, and how much of it is written up.

    Parsed from the .tex on every build so the board tells the truth as the
    assistant fills it in, with the last compile's outcome bolted on from
    `live/hw.json` -- a failed compile has to reach the person holding the iPad
    the same way a failed push does.
    """
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:
        return None
    if not st:
        return None
    st["ambiguous"] = st.get("ambiguous", [])[:8]
    st["sets"] = [x["name"] for x in homework.sets(repo.root)][:40]
    st.pop("dir", None)          # an absolute path on this machine is no use to a browser
    try:
        with open(os.path.join(repo.live, "hw.json"), "r", encoding="utf-8") as fh:
            st["build"] = json.load(fh)
    except (OSError, ValueError):
        st["build"] = None
    return st


def load_review(repo):
    """What this test review covers, so the board can say so and paint the picker.

    Cheap and always sent: it is a directory listing behind a lookup the payload
    already does, and the picker needs the list of things to pick from before a
    review sitting exists. The scope is re-resolved on every build rather than
    echoed back from `state.json` -- a chapter renamed out from under a sitting
    would otherwise stay on the strip for ever.
    """
    try:
        st = review.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        return None
    if not st:
        return None
    st.pop("chosen", None)     # the names are enough; the board paints from units
    return st


def load_walk(repo):
    """What this walkthrough covers, and what else could be walked through.

    Sent on every payload for the same reason the review block is: the picker
    needs something to offer before the sitting exists, and a student on an iPad
    cannot name a file they cannot see. The list is a directory walk rather than
    a directory listing, so it is the one discovery here that costs more than a
    `stat` -- and is remembered for half a minute in `walk.units` rather than
    redone four times a second for a repository whose files are not moving.
    """
    try:
        st = walk.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        return None
    if not st:
        return None
    st.pop("chosen", None)     # the names are enough; the board paints from units
    return st


def load_plan(repo):
    """What this project says it is doing next, so the drawer can offer it.

    A course that follows a book has chapters and the drawer lists them; a
    project had nothing, and the drawer said so -- "sittings here are made as
    you go" -- which put every decision about what a sitting was about back on
    the person holding the iPad. A project does write down what comes next; it
    just does not call it a syllabus and does not keep it in this repository.
    See `course/plan.py`.
    """
    try:
        return plan.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        return None


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


def load_map(repo):
    """The picture of this repository, which is the way into it.

    A course used to open on an empty board, and the drawer that came before
    this one lists what a repository holds without saying how any of it fits
    together -- which is a fine index and a poor front door. See
    `course/mapping.py`.

    Every repository gets one. Where nobody has drawn a map, it is derived from
    what is on disk -- chapters, or the steps in the plan, or the repository's
    own parts -- and says so. The past lessons go in because they are the only
    record this board keeps of work actually finished, and a box that is done
    should not be painted as though nobody had started it.
    """
    try:
        return mapping.status(repo.root, repo.state(),
                              archive.list_archive(repo))
    except Exception:                                        # noqa: BLE001
        return None


def load_contents(repo):
    """What this course is made of, so the board can offer a way around it.

    Everything here is discovered, not registered: the chapter table or the
    chapter directories, the problem sets, and the lessons already filed. A
    course that is not a book simply has no chapters, and says so by returning
    none rather than by inventing a chapter one.
    """
    try:
        chapters = [{"num": c.get("num"), "label": syllabus.label(c)}
                    for c in syllabus.chapters(repo.root)][:60]
    except Exception:
        chapters = []
    try:
        sets = [{"name": x["name"], "rel": x["rel"]}
                for x in homework.sets(repo.root)][:60]
    except Exception:
        sets = []
    return {"chapters": chapters, "sets": sets}


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
