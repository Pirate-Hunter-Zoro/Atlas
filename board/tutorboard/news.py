"""An answer that landed somewhere nobody was looking.

WHY THIS EXISTS, in the words it was asked for:

    "maybe something I give the agent to do or think about is going to take a
     while. I want to be able to go into a different section of a project, or a
     different fucking project completely, and put other agents to work on other
     things while the first one is working. We should set up a notification
     system where if a response that takes a while comes back in a session, I'll
     get notified somewhere in the app and can click that notification to take me
     back to that tutoring session."

Nothing in here talks to another machine and nothing is registered. Every
workspace's lesson is a directory of files on one shared filesystem, so the
board serving ONE workspace can answer "has anything landed in the others" by
looking -- the same rule the rest of this tool is built on, for the same reason:
a list somebody has to maintain goes quietly false.

THE WHOLE OF IT IS TWO NUMBERS PER WORKSPACE.

* **When its newest card was written.** A card is the tutor's answer and it is a
  file, so this is the mtime of the newest file in `live/cards`. It costs one
  `listdir` and one `stat` per card, and it is cached.
* **When somebody last LOOKED at it.** `live/.seen.json`, written by the board
  serving that workspace while a browser actually has it open. Not when the
  board starts, and not when a request arrives: a board is a long-lived process
  that goes on running in an empty room.

News is the first being newer than the second. That is the entire rule, and it
is right in the case that matters -- a turn that runs for twenty minutes in
PSYCH-ASR while the person is in Galois-Theory ends with a card, and the card is
newer than the last time anybody looked at PSYCH-ASR.

A WORKSPACE NOBODY HAS EVER OPENED SINCE THIS SHIPPED IS NOT NEWS. With no
marker at all every lesson on the machine is "newer than never", so the first
board to come up would announce eleven workspaces at once, every one of them
about something that happened last week. The first look at a workspace writes
the marker at its newest card instead, so day one is silent and everything after
it is exact.
"""

import json
import os
import time

from . import atlas, paths
from .lesson import cards as lesson_cards


SEEN = ".seen.json"

# What a card has to be to count, in seconds. A lesson archived months ago whose
# directory was never cleared is not news about tonight, and a clock skew across
# a shared filesystem should not be able to invent an answer that never came.
FRESH = 7 * 24 * 3600

# The list is rebuilt at most this often. The hub polls four times a second and
# this is a directory walk over every workspace on the machine; the answer
# changes on the scale of a turn, not of a poll.
TTL = 5.0

_CACHE = {"at": 0.0, "value": None}


def _live(root):
    return os.path.join(root, "live")


def newest_card(root):
    """(when, which) of the newest card in this workspace's open lesson.

    `which` is the four-digit card id, which is what an address spells -- so a
    notification can point AT the answer rather than at the workspace holding
    it. (0.0, "") where there is no lesson and where there are no cards in it.
    """
    when, which = 0.0, ""
    where = os.path.join(_live(root), "cards")
    try:
        names = os.listdir(where)
    except OSError:
        return when, which
    for name in names:
        m = lesson_cards.CARD_RE.match(name)
        if not m:
            continue
        try:
            at = os.stat(os.path.join(where, name)).st_mtime
        except OSError:
            continue
        if at > when:
            when, which = at, m.group(1)
    return when, which


def seen_at(root):
    """When a browser last had this workspace open, or None if never recorded."""
    try:
        with open(os.path.join(_live(root), SEEN), "r", encoding="utf-8") as fh:
            return float((json.load(fh) or {}).get("at") or 0)
    except (OSError, ValueError, TypeError):
        return None


def mark_seen(root, when=None):
    """Somebody is looking at this workspace now. Never raises.

    Written atomically, because two boards on two machines share this filesystem
    and a half-written marker reads as "never seen" -- which would put every
    lesson on the machine back into the notifications.
    """
    target = os.path.join(_live(root), SEEN)
    tmp = target + ".tmp"
    try:
        os.makedirs(_live(root), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"at": float(when or time.time())}, fh)
        os.replace(tmp, target)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _title(root, card_id):
    """The card's own title, for the notification to say. "" if it has none."""
    where = os.path.join(_live(root), "cards")
    try:
        names = os.listdir(where)
    except OSError:
        return ""
    for name in names:
        m = lesson_cards.CARD_RE.match(name)
        if not m or m.group(1) != card_id:
            continue
        try:
            with open(os.path.join(where, name), "r", encoding="utf-8") as fh:
                meta, _ = lesson_cards.parse_front_matter(fh.read(2000))
        except OSError:
            return ""
        return (meta.get("title") or "").strip()[:80]
    return ""


def elsewhere(here, now=None):
    """Every OTHER workspace holding an answer nobody has looked at.

    `here` is the root of the workspace this board serves -- excluded, because a
    board does not notify somebody about the lesson they are reading. Newest
    first, because that is the one they want.
    """
    now = now or time.time()
    out = []
    for w in atlas.workspaces():
        root = w["root"]
        if paths.same_dir(root, here):
            continue
        when, which = newest_card(root)
        if not when or now - when > FRESH:
            continue
        seen = seen_at(root)
        if seen is None:
            # First sight of this workspace. Start the clock rather than
            # reporting a lesson from before there was anything to report with.
            mark_seen(root, when)
            continue
        if when <= seen:
            continue
        out.append({
            "id": w["id"],
            "repo": w["dir"],
            "family": w["family"],
            "family_name": w["family_name"],
            "course": _course_name(root) or w["dir"],
            "chapter": _chapter(root),
            "card": which,
            "title": _title(root, which),
            "when": when,
        })
    out.sort(key=lambda x: -x["when"])
    return out


def _state(root):
    try:
        with open(os.path.join(_live(root), "state.json"), "r",
                  encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def _course_name(root):
    return (_state(root).get("course") or "").strip()


def _chapter(root):
    return (_state(root).get("chapter") or "").strip()[:60]


def waiting(repo, now=None):
    """`elsewhere`, cached, for the payload the hub pushes four times a second."""
    now = now or time.time()
    if _CACHE["value"] is not None and now - _CACHE["at"] < TTL:
        return _CACHE["value"]
    try:
        value = elsewhere(repo.root, now)
    except Exception:                                        # noqa: BLE001
        # A front door that throws is a blank screen where the app used to be,
        # and a notification is the least important thing on it.
        value = []
    _CACHE["at"] = now
    _CACHE["value"] = value
    return value


def forget():
    """Drop the cache, so the next ask is answered off disk. For the tests, and
    for the moment a board marks its own workspace seen."""
    _CACHE["at"] = 0.0
    _CACHE["value"] = None
