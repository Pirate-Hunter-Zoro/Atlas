"""What the board says about itself right now: the tutor, the write-up, the
documents and figures it can show.

The constraint: nothing here may raise into the payload, because the agent
block exists to report what went wrong.
"""

import json
import os
import time

from .. import machine
from ..runner import daemon
from ..course import homework, library, paper


def load_agent(repo):
    """The session's agent record, with `state` "stale" where the process it
    names is gone (`daemon.attached`), and its `failure` and `stood_down`."""
    try:
        with open(os.path.join(repo.live, "agent.json"), "r", encoding="utf-8") as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        return None
    if not daemon.attached(st, machine.node_name()):
        # A restart marks the record on its way out, so the gap reads
        # "reattaching", not "no tutor attached".
        st["state"] = "reattaching" if _reattaching(st) else "stale"
    # The last failure, while it is news (`_failure`).
    st["failure"] = _failure(repo, st)
    # A stood-down provider and its expiry, so the iPad can say why nothing
    # is happening.
    st["stood_down"] = _stood_down(st.get("agent"))
    # `turn_signal` belongs to the turn; cleared here once it ends, so a stale
    # one never labels an idle tutor.
    if st.get("state") != "working":
        st["turn_signal"] = ""
    return st


# A failed turn is stamped and reported while it is the newest thing that
# happened, so the iPad never shows "listening" over unanswered work. This
# cap is only a backstop, so a board opened the next morning does not lead
# with last night's timeout.
FAILURE_FRESH = 12 * 3600


def _failure(repo, st):
    """The last turn's failure, while it is still the newest thing that
    happened: a newer card or answer ends it, not a clock, because a timed-out
    doing turn leaves a present-tense card that must not go unexplained.
    """
    if not st.get("last_error"):
        return None
    try:
        at = float(st.get("failed_at") or 0)
    except (TypeError, ValueError):
        return None
    # A turn in flight is newer than the failure before it: it is not shown,
    # but the record keeps the reason in case this turn dies too.
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
    `until` is epoch seconds; the glass formats it."""
    if not agent:
        return None
    from ..net import egress
    got = egress.stood_down(agent)
    if not got:
        return None
    return {"host": got["host"], "why": got["why"], "until": got["until"]}


def _newest(repo):
    """When the board last had something happen on it: a card, or an answer.
    Uses `getattr`, because every payload runs this and it must never raise."""
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


# How long a restart may claim to be in progress.
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
    """The session's write-up and how much is written: the pinned set or
    `docs/` write-up, parsed from its .tex, with the last compile's outcome.
    None when nothing is pinned. Reads one file, never a listing."""
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
    """The documents this course can show (`course/library.py`)."""
    try:
        return library.drawer_status(repo)
    except Exception:                                        # noqa: BLE001
        return None


def load_results(repo):
    """The figures this workspace's pipeline made (`course/library.py`)."""
    try:
        return library.figures_status(repo)
    except Exception:                                        # noqa: BLE001
        return None


def load_papers(repo):
    """Which of the two documents exist on disk now, and their names
    (`course/paper.py`): answered from the files on every payload, so the
    controls never vanish with the build banner. Four stats.
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
    """The outcome of the last export, kept in a file so it survives the
    payload that lands when it finishes."""
    try:
        with open(os.path.join(repo.live, "export.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
