"""A document asked for from a sitting, and where the board says it got to.

WHY THIS EXISTS, in the words it was asked in:

    "let's say I open up libr-local-llm and I want to learn how colibri works.
     Can I have a tutoring session where I'm walked through simple lessons to
     understand this and how we utilize the cluster hardware, and at any point
     can I have a presentation or paper written up going through the things we
     talked about in that tutoring session? Can I do that in ANY tutoring
     session?"

A DOCUMENT IS AN ACTION, NOT A MODE. A paper or a deck is a PRODUCT any
session can be asked for. So it is its own act -- `POST /writeup` -- which
changes no mode, archives nothing and replaces no tutor, and the turn it wakes
writes no card. The document lands in the library, where
correcting it is already a loop that exists.

WHICH LEAVES ONE THING WITH NOWHERE TO BE SAID: that it is being written, and
that it is there. A turn that writes no card is invisible on the board by
construction, and "I asked for a deck and nothing happened" is the same defect
`missions.py` was built against one workspace over. This module is the record.

THE STATE IS THE ARTIFACT'S. An ask that made an artifact carries its
directory (`dir`, relative to the root), and its state is `artifacts.status`
of that doc.json: mtimes of the source and its build against `asked_at`. An
ask with no artifact -- the deck from sittings and the meeting deck, which keep
their own records -- is `writing` until somebody freezes it or `CEILING` passes.

THREE STATES, BECAUSE THEY ARE THE THREE A PERSON ACTS ON. `writing` -- leave it.
`done` -- go and read it. `failed` -- ask again. Anything finer is a state nobody
does anything different about.

Standard library only, like everything else.
"""

import json
import os
import re
import time

from . import artifacts
from .course import repo as course_repo


WRITEUPS = "writeups"

# The two products.
MAKES = ("paper", "slides")

# What a subject is truncated to in the record. It is read on a tablet in a strip
# two lines high; the whole of it is in the target's inbox, which is where the
# turn reads it.
ABOUT_CHARS = 400

# How long an ask with nothing to show for it is still being written rather than
# lost. A document is a doing turn -- `doing_timeout` is an hour -- and a paper
# with a LaTeX build at the end of it on the local model is slower than that
# again. Generous on purpose: `failed` is a sentence telling somebody to ask a
# second time, and saying it while the first one is still working is worse than
# saying nothing.
CEILING = 2 * 3600

# How long a finished record stays on disk. Long enough that a week away still
# says what happened; short enough that `live/writeups/` is not a log.
KEEP = 7 * 24 * 3600

# The list is rebuilt at most this often. The hub polls four times a second and
# deriving a state walks the workspace for its documents. `missions.TTL`, for the
# same reason: the answer changes on the scale of a turn.
TTL = 5.0

_CACHE = {}

# An id is a turn id and nothing else ever reaches the filesystem from a request.
# Matched rather than sanitised: a name that is not one of these is not an ask,
# and joining it onto a path to find out is the mistake.
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")

# Everything that is stored. A judged record carries `state` as well, and writing
# that back would turn a reading into a fact.
FIELDS = ("id", "makes", "about", "at", "agent", "dir", "ended", "ended_at",
          "doc", "seen", "session")


def clean_makes(makes):
    """`paper`, `slides`, or None. Never raises."""
    makes = str(makes or "").strip().lower()
    return makes if makes in MAKES else None


def _dir(root):
    return course_repo.session_path(root, WRITEUPS)


def _path(root, wid):
    return os.path.join(_dir(root), "%s.json" % wid)


def write(root, rec):
    """Store one record. Atomically, and never raising.

    Two boards on two nodes share this filesystem and a half-written record reads
    as an ask that was never made.
    """
    wid = str(rec.get("id") or "")
    if not ID_RE.match(wid):
        return False
    path = _path(root, wid)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        keep = {k: rec[k] for k in FIELDS if k in rec}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(keep, fh, indent=2)
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def read(root, wid):
    """One record, or None."""
    if not ID_RE.match(str(wid or "")):
        return None
    try:
        with open(_path(root, wid), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def _every(root):
    """Every record on disk, newest ask first, with the expired ones removed."""
    out = []
    try:
        names = sorted(os.listdir(_dir(root)))
    except OSError:
        return out
    now = time.time()
    for name in names:
        if not name.endswith(".json"):
            continue
        rec = read(root, name[:-5])
        if not rec:
            continue
        ended = rec.get("ended_at") or 0
        if ended and now - ended > KEEP:
            try:
                os.remove(_path(root, rec.get("id") or name[:-5]))
            except OSError:
                pass
            continue
        out.append(rec)
    out.sort(key=lambda r: r.get("at") or 0, reverse=True)
    return out


def ask(root, wid, makes, about="", agent="", doc_dir=None, session=None):
    """Record that a document has been asked for. Returns the record.

    `doc_dir` is the artifact the ask made, relative to `root`, when it made
    one; its doc.json is what the record is judged by. `session` is the id of
    the stored session whose inbox holds the ask, where one does.
    """
    rec = {
        "id": str(wid), "makes": clean_makes(makes) or "paper",
        "about": (about or "").strip()[:ABOUT_CHARS],
        "at": time.time(), "agent": agent or "",
        "dir": (doc_dir or "").replace(os.sep, "/"),
        "ended": "", "ended_at": 0, "doc": "", "seen": False,
    }
    if session:
        rec["session"] = str(session)
    write(root, rec)
    _CACHE.pop(os.path.realpath(root), None)
    return rec


def _doc_of(rel):
    """The library id of the artifact at `rel`: its slug under `docs/`."""
    parts = (rel or "").split("/")
    return parts[1] if len(parts) == 2 and parts[0] == artifacts.DOCS else ""


def _judge(root, rec):
    """`writing`, `done` or `failed`.

    With an artifact, its doc.json decides, every time: a failed one that
    later builds is done. The first terminal answer stamps `ended_at`, which
    is what `KEEP` prunes by. Without one, the first terminal answer is
    frozen, and only `CEILING` or somebody else freezing it ends it.
    """
    rel = rec.get("dir") or ""
    if rel:
        got = artifacts.status(os.path.join(root, *rel.split("/")),
                               session_dir=course_repo.session_dir(root))
        got = got or "failed"          # the artifact is gone
        if got != "writing" and (rec.get("ended") != got or not rec.get("ended_at")):
            rec["ended"], rec["doc"] = got, _doc_of(rel) if got == "done" else ""
            rec["ended_at"] = rec.get("ended_at") or time.time()
            write(root, rec)
        return got
    if rec.get("ended"):
        return rec["ended"]
    if time.time() - (rec.get("at") or 0) > CEILING:
        rec["ended"], rec["ended_at"] = "failed", time.time()
        write(root, rec)
        return "failed"
    return "writing"


def state(root, wid):
    """`writing`, `done` or `failed` for one ask, or "" where there is no record.

    `waiting` answers for the strip, which caps and hides; this answers for ONE
    ask somebody is watching from somewhere else -- the front door's deck from
    sittings, which knows its ask by id. The same judging, so the same freezing:
    a record read here and in the strip cannot come to two answers.
    """
    rec = read(root, wid)
    if not rec:
        return ""
    return _judge(root, rec)


def seen(root, wid):
    """Mark one finished ask as looked at, so the strip stops saying it.

    A `writing` one cannot be waved away: it is still being written, and that is
    the fact being reported. Nothing else about the record changes, so a document
    that has landed is still on disk, still in the library, and still correctable
    from there.
    """
    rec = read(root, wid)
    if not rec or not rec.get("ended"):
        return False
    rec["seen"] = True
    write(root, rec)
    _CACHE.pop(os.path.realpath(root), None)
    return True


# How many rows the board is ever given. Past this it is a list, and a list in
# the chrome is a page somebody scrolls past to reach their own lesson.
MOST = 3


def waiting(repo):
    """What the board paints: every document being written, and every one that
    has landed and not been looked at.

    Cheap when there is nothing to say, which is nearly always: an empty
    `writeups/` in the session is one `listdir` that fails. Cached for `TTL`
    otherwise; judging reads doc.json files and stats, never the library.
    """
    root = getattr(repo, "root", repo)
    key = os.path.realpath(root)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    out = []
    for rec in _every(root):
        # JUDGED WHETHER OR NOT IT IS REPORTED. `MOST` caps what the strip is
        # given, and capping the judging instead would leave a fourth ask never
        # ending -- so never carrying `ended_at`, so never pruned.
        state = _judge(root, rec)
        if len(out) >= MOST or (state != "writing" and rec.get("seen")):
            continue
        out.append({
            "id": rec.get("id") or "",
            "makes": rec.get("makes") or "paper",
            "about": rec.get("about") or "",
            "at": rec.get("at") or 0,
            "agent": rec.get("agent") or "",
            "state": state,
            "doc": rec.get("doc") or "",
        })
    out = out or None
    _CACHE[key] = (time.time(), out)
    return out


def forget():
    """Drop the cache. For a test that asks twice inside `TTL`."""
    _CACHE.clear()
