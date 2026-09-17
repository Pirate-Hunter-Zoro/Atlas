"""A document asked for from a sitting, and where the board says it got to.

WHY THIS EXISTS, in the words it was asked in:

    "let's say I open up libr-local-llm and I want to learn how colibri works.
     Can I have a tutoring session where I'm walked through simple lessons to
     understand this and how we utilize the cluster hardware, and at any point
     can I have a presentation or paper written up going through the things we
     talked about in that tutoring session? Can I do that in ANY tutoring
     session?"

A `make` sitting already answers the first half: it drafts a document a section
at a time and the document IS the evening. What it cannot do is arrive in the
middle of somebody else's evening. Asking for one was an AIM change -- the whole
sitting becomes a make sitting -- and the aim row is withheld from a review and a
walkthrough, so in the two sittings where a write-up is worth the most there was
no way to ask at all.

A DOCUMENT IS NOT AN AIM. An aim says what the sitting is FOR; a paper or a deck
is a PRODUCT any sitting can be asked for. So it is its own act -- `POST
/writeup` -- which changes no aim, archives nothing and replaces no tutor, and
the turn it wakes writes no card. The document lands in the library, where
correcting it is already a loop that exists.

WHICH LEAVES ONE THING WITH NOWHERE TO BE SAID: that it is being written, and
that it is there. A turn that writes no card is invisible on the board by
construction, and "I asked for a deck and nothing happened" is the same defect
`missions.py` was built against one workspace over. This module is the record.

THE STATE IS DERIVED FROM THE LIBRARY, AND THEN FROZEN. Both halves matter, and
both are `missions.py`'s reasoning applied to a document rather than to a job:

* **Derived**, because nothing is alive to write it. The turn is headless and
  ends by exiting; it is told to build the document and not to report anywhere.
  `library.stamp` is where every document is and when it last changed, in stats
  and nothing else, so what landed since the ask is arithmetic over two stamps.
* **Frozen**, because the evidence expires. Every later document this workspace
  writes also differs from the stamp taken at the ask, so an unfrozen reading
  would credit this ask with somebody else's deck a week later.

THREE STATES, BECAUSE THEY ARE THE THREE A PERSON ACTS ON. `writing` -- leave it.
`done` -- go and read it. `failed` -- ask again. Anything finer is a state nobody
does anything different about.

Standard library only, like everything else.
"""

import json
import os
import re
import time


WRITEUPS = "writeups"

# The two products, and they are the two words `config.AIMS` already keeps apart.
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
FIELDS = ("id", "makes", "about", "at", "agent", "had", "ended", "ended_at",
          "doc", "seen")


def clean_makes(makes):
    """`paper`, `slides`, or None. Never raises."""
    makes = str(makes or "").strip().lower()
    return makes if makes in MAKES else None


def _dir(root):
    return os.path.join(root, "live", WRITEUPS)


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


def ask(root, wid, makes, about="", agent=""):
    """Record that a document has been asked for. Returns the record.

    `had` is the library AS IT IS NOW, which is the whole of the derivation
    below: what this ask produced is whatever the library has that this list
    does not, or whatever in it has changed since. `None` where the library could
    not be read at all -- see `_library_now` -- and then nothing is derived and
    the ask runs to its ceiling.
    """
    rec = {
        "id": str(wid), "makes": clean_makes(makes) or "paper",
        "about": (about or "").strip()[:ABOUT_CHARS],
        "at": time.time(), "agent": agent or "",
        "had": _library_now(root),
        "ended": "", "ended_at": 0, "doc": "", "seen": False,
    }
    write(root, rec)
    _CACHE.pop(os.path.realpath(root), None)
    return rec


def _library_now(root):
    """Every document this workspace has, as `id@hash`, or None. Stats only.

    `library.stamp` is the cheap question the library page already asks every few
    seconds, and it is exactly the right shape here: where each document is and
    when it last changed, with no titles read and no `pdfinfo` run. Imported
    where it is used rather than at the top, because this module is read by the
    hub on every payload and the library's own imports are not.

    NONE IS NOT AN EMPTY LIBRARY. A workspace that has written nothing has an
    empty list, and that is a fact the derivation below can work from. A stamp
    that could not be taken is not: crediting an ask with every document a
    workspace already had, because the list at the ask came back empty by
    accident, is exactly the wrong answer. So the two are different values and
    everything downstream refuses to derive from None.
    """
    try:
        from .course import library
        docs = (library.stamp(root) or {}).get("documents") or {}
    except Exception:                                        # noqa: BLE001
        return None
    return sorted("%s@%s" % (k, v) for k, v in docs.items())


def _landed(rec, now):
    """Which document this ask produced, or "". Arithmetic over two stamps.

    A NEW id is the ordinary case -- a document asked for goes in
    `writeups/<slug>/`, which nothing else claims -- and a CHANGED hash is the
    other honest one: a second paper about the same machinery is written into the
    slug that already exists, and a document that moved since the ask is a
    document this ask moved.

    `now` is the library as it is, passed in rather than read: reading it is a
    walk of the workspace, and three open asks must not be three walks. Either
    side being unknown -- `None` from `_library_now`, at the ask or now -- means
    nothing can be derived, and the ask stays as it is until the ceiling. That is
    the safe direction: a document nobody can see is better reported as still
    being written than as some other document that was already there.
    """
    if now is None or rec.get("had") is None:
        return ""
    had = set(rec.get("had") or [])
    ids = set(x.split("@", 1)[0] for x in had)
    moved = ""
    for one in now:
        if one in had:
            continue
        ident = one.split("@", 1)[0]
        if ident not in ids:
            return ident
        moved = moved or ident
    return moved


def _judge(root, rec, now):
    """`writing`, `done` or `failed`, freezing the first terminal answer.

    Frozen for the reason a mission's ending is: the evidence expires. Every
    document written in this workspace after the ask also differs from the stamp
    taken at it, so a reading taken tomorrow would credit this ask with
    tomorrow's deck.
    """
    if rec.get("ended"):
        return rec["ended"]
    doc = _landed(rec, now)
    if doc:
        rec["ended"], rec["ended_at"], rec["doc"] = "done", time.time(), doc
        write(root, rec)
        return "done"
    if time.time() - (rec.get("at") or 0) > CEILING:
        rec["ended"], rec["ended_at"] = "failed", time.time()
        write(root, rec)
        return "failed"
    return "writing"


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
    `live/writeups/` is one `listdir` that fails. Cached for `TTL` otherwise,
    because deriving a state walks the workspace for its documents and this is
    read on every payload.
    """
    root = getattr(repo, "root", repo)
    key = os.path.realpath(root)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    every = _every(root)
    # The library, ONCE, and only where something is still open. A walk of the
    # workspace for a list of records that have all ended is a walk for nothing.
    now = _library_now(root) if any(not r.get("ended") for r in every) else []
    # `[]` above is "nothing to derive for", which is not the same as "the
    # library could not be read" -- see `_library_now`. Only the second is None,
    # and `_landed` refuses to derive from it.
    out = []
    for rec in every:
        # JUDGED WHETHER OR NOT IT IS REPORTED. `MOST` caps what the strip is
        # given, and capping the judging instead would leave a fourth ask never
        # frozen -- so never carrying `ended_at`, so never pruned, so on disk for
        # ever. The cap belongs on the painting, not on the reading.
        state = _judge(root, rec, now)
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
