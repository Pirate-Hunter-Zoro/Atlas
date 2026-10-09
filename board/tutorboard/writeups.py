"""A document asked for from a sitting, and where the board says it got to.

A paper or deck is an action any session can ask for (`POST /artifact`, the
Make menu), not a mode: it changes no mode and its turn writes no card, so
this record is how the board says it is being written and that it landed.
Records are the session's own (`writeups/` in its directory). An ask that
made an artifact is judged by `artifacts.status` of its doc.json; one
without is `writing` until frozen or `CEILING` passes. Three states, the
three a person acts on: `writing`, `done`, `failed`.

The constraint: an id is a turn id, matched, never sanitised; nothing else
from a request reaches the filesystem.
"""

import json
import os
import re
import time

from . import artifacts
from .course import repo as course_repo


WRITEUPS = "writeups"

# The two products. The Make menu's "deck" is recorded as `slides`.
MAKES = ("paper", "slides")

# A subject's length in the record; the full text is in the target's inbox.
ABOUT_CHARS = 400

# How long an empty-handed ask is still `writing`: generous, because "ask
# again" while the first is still working is worse than silence.
CEILING = 2 * 3600

# How long a finished record stays.
KEEP = 7 * 24 * 3600

# Rebuilt at most this often; the hub polls far faster than turns change it.
TTL = 5.0

_CACHE = {}

# Turn ids only.
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")

# Stored fields; `state` is judged on read and never written back.
FIELDS = ("id", "makes", "about", "at", "agent", "dir", "ended", "ended_at",
          "doc", "seen", "session")


def clean_makes(makes):
    """`paper`, `slides`, or None. Never raises."""
    makes = str(makes or "").strip().lower()
    return makes if makes in MAKES else None


def _root(where):
    """The subject root of `where`: a Repo, or a root."""
    return getattr(where, "root", where)


def _dir(where):
    """Where the records are: a Repo's session directory, else the session
    this process bound for the root `where`."""
    live = getattr(where, "live", None) or course_repo.session_dir(where)
    if not live:
        raise ValueError("no session holds the write-ups of %s" % where)
    return os.path.join(live, WRITEUPS)


def _path(where, wid):
    return os.path.join(_dir(where), "%s.json" % wid)


def write(where, rec):
    """Store one record atomically, never raising: a half-written record
    reads as an ask never made."""
    wid = str(rec.get("id") or "")
    if not ID_RE.match(wid):
        return False
    path = _path(where, wid)
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


def read(where, wid):
    """One record, or None."""
    if not ID_RE.match(str(wid or "")):
        return None
    try:
        with open(_path(where, wid), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def _every(where):
    """Every record on disk, newest ask first, with the expired ones removed."""
    out = []
    try:
        names = sorted(os.listdir(_dir(where)))
    except OSError:
        return out
    now = time.time()
    for name in names:
        if not name.endswith(".json"):
            continue
        rec = read(where, name[:-5])
        if not rec:
            continue
        ended = rec.get("ended_at") or 0
        if ended and now - ended > KEEP:
            try:
                os.remove(_path(where, rec.get("id") or name[:-5]))
            except OSError:
                pass
            continue
        out.append(rec)
    out.sort(key=lambda r: r.get("at") or 0, reverse=True)
    return out


def ask(where, wid, makes, about="", agent="", doc_dir=None, session=None):
    """Record that a document has been asked for. Returns the record.
    `doc_dir` is the artifact it made, relative to its root; `session` the
    stored session whose inbox holds the ask."""
    rec = {
        "id": str(wid), "makes": clean_makes(makes) or "paper",
        "about": (about or "").strip()[:ABOUT_CHARS],
        "at": time.time(), "agent": agent or "",
        "dir": (doc_dir or "").replace(os.sep, "/"),
        "ended": "", "ended_at": 0, "doc": "", "seen": False,
    }
    if session:
        rec["session"] = str(session)
    write(where, rec)
    _CACHE.pop(os.path.realpath(_dir(where)), None)
    return rec


def _doc_of(rel):
    """The library id of the artifact at `rel`: its slug under `docs/`."""
    parts = (rel or "").split("/")
    return parts[1] if len(parts) == 2 and parts[0] == artifacts.DOCS else ""


def _judge(where, rec):
    """`writing`, `done` or `failed`. With an artifact, its doc.json decides
    every time; the first terminal answer stamps `ended_at` for `KEEP`.
    Without one, the first terminal answer is frozen."""
    rel = rec.get("dir") or ""
    root = _root(where)
    if rel:
        got = artifacts.status(os.path.join(root, *rel.split("/")),
                               session_dir=os.path.dirname(_dir(where)))
        got = got or "failed"          # the artifact is gone
        if got != "writing" and (rec.get("ended") != got or not rec.get("ended_at")):
            rec["ended"], rec["doc"] = got, _doc_of(rel) if got == "done" else ""
            rec["ended_at"] = rec.get("ended_at") or time.time()
            write(where, rec)
        return got
    if rec.get("ended"):
        return rec["ended"]
    if time.time() - (rec.get("at") or 0) > CEILING:
        rec["ended"], rec["ended_at"] = "failed", time.time()
        write(where, rec)
        return "failed"
    return "writing"


def state(where, wid):
    """`writing`, `done` or `failed` for one ask, or "" with no record: the
    same judging as `waiting`, for a caller watching one ask by id."""
    rec = read(where, wid)
    if not rec:
        return ""
    return _judge(where, rec)


def seen(where, wid):
    """Mark one finished ask as looked at, so the strip stops saying it. A
    `writing` one cannot be waved away; nothing else changes."""
    rec = read(where, wid)
    if not rec or not rec.get("ended"):
        return False
    rec["seen"] = True
    write(where, rec)
    _CACHE.pop(os.path.realpath(_dir(where)), None)
    return True


# The most rows the board is given.
MOST = 3


def waiting(repo):
    """What the board paints: every document being written, and every landed
    one not yet looked at. Cached for `TTL` once nothing is being written;
    judging reads doc.json files and stats, never the library."""
    key = os.path.realpath(_dir(repo))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    out = []
    for rec in _every(repo):
        # Judge every record, not only the reported ones, so each one ends
        # and is pruned.
        state = _judge(repo, rec)
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
    # Not cached while writing, so the rebuild after the turn sees it land.
    if not any(r["state"] == "writing" for r in out):
        _CACHE[key] = (time.time(), out or None)
    return out or None


def forget():
    """Drop the cache. For a test that asks twice inside `TTL`."""
    _CACHE.clear()
