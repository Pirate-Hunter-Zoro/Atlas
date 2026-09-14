"""reading.py -- the documents a course can be SHOWN, as opposed to the two it builds.

`paper.py` owns the two documents this board makes: the exported transcript and
the compiled write-up. Both are events -- something was built, and here it is.

This is the other kind, and it is the one a project has: **a document that was
written months ago and explains how the thing works.** PSYCH-ASR's
`stage2_reference_walkthrough` is 33 slides on exactly the machinery its owner
says he cannot follow, its own README says to read it first if you want the state
of the project in half an hour, and there was no way to put a page of it on the
board. So it was read on a laptop, in a PDF viewer, beside a lesson on an iPad --
which is the same split-attention the board exists to remove, and is why a
walkthrough of code had nothing to point at.

Two things live here.

**Finding them.** Any PDF in this repository, plus any PDF this repository's
README names in a sibling directory -- because the decks for a project routinely
live in the narrative hub beside it rather than in the code, which is exactly the
arrangement `plan.py` already reads task lists out of. Nothing is registered; a
deck that gets rebuilt is the same document with a new modification time.

**Showing one page of one.** The board already renders a PDF to PNGs and shows
them in a viewer it owns -- that is `paper.pages_of`, and reading a deck is that
with a different way of finding the file. What is new is that a SINGLE page can
be addressed, so a tutor teaching `grade` can put slide 24 in the card that asks
about the three-pass order rather than telling somebody to go and find it.

Standard library only, like everything else.
"""

import os
import re
import time

from . import paper

# Where a document worth showing is kept. `live/` is the board's own working
# directory -- the exported transcript is in there and it is `paper.py`'s, not
# this module's -- and the rest are build output, dependencies, or data.
IGNORE = {"live", "node_modules", "__pycache__", "build", "dist", "target",
          "venv", ".venv", "env", "site-packages", "vendor", "results",
          "data", "test_data", "archive"}

# A deck or a walkthrough is worth offering; a figure exported as a one-page PDF
# is not, and neither is a paper somebody downloaded into a reference library.
MIN_BYTES = 20000

# A drawer is not a file manager. A project has two or three documents worth
# being shown; a reference library has thirty and none of them are this.
MAX_DOCS = 24

# How deep to look. A deck lives in a project directory one or two levels down
# -- `psych-asr-feasibility/stage2_reference_walkthrough.pdf` -- and nothing
# worth showing is buried five deep.
MAX_DEPTH = 3

# A PDF this repository's README names. The path is what is matched, not the
# prose around it, and it has to end in `.pdf` -- so a sentence about slides
# finds nothing and a path to a deck finds the deck.
POINTER = re.compile(r"[~\w./-]+\.pdf\b")

# What a reference library is called. These are papers by other people; a
# walkthrough of your own pipeline is not in one.
NOT_OURS = ("references", "reference", "library", "papers", "reading",
            "literature", "formats", "feedback")


def _pretty(path):
    """What to call a document in a drawer.

    The filename, unpunctuated. `stage2_reference_walkthrough.pdf` becomes
    `stage2 reference walkthrough`, which is what its author calls it out loud
    and is the only name anybody would recognise it by.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[_-]+", " ", stem).strip() or "document"


def _ok(path):
    try:
        return os.path.getsize(path) >= MIN_BYTES
    except OSError:
        return False


def _in_repo(root):
    """Every PDF in this repository worth showing, nearest the top first."""
    out = []
    root = os.path.realpath(root)
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and d not in IGNORE and d.lower() not in NOT_OURS)
        for name in sorted(files):
            if not name.lower().endswith(".pdf") or name.startswith("."):
                continue
            path = os.path.join(here, name)
            if _ok(path) and _ours(path):
                out.append(path)
    return out


def _ours(path):
    """Is this a document about this project, or somebody else's paper?

    A reference library is PDFs by other people. A README cites them by path,
    so the directory test that keeps them out of the walk has to apply to what
    the README names too -- or `E-value, Ann Intern Med` turns up in a drawer
    next to the pipeline walkthrough as though it were one of ours.
    """
    parts = [p.lower() for p in os.path.normpath(path).split(os.sep)]
    return not any(p in NOT_OURS for p in parts)


def _pointed_at(root):
    """Every PDF this repository's README names and can actually reach.

    The same rule `plan.py` uses for task lists, and for the same reason: a
    README that names a document has declared it, and the decks for a project
    live in the hub beside the code rather than in it. Bounded to this
    repository and its siblings under the same home -- a path out of a file is a
    path somebody could have written anything into.

    Two passes, because a README names the second deck the way a person would:
    the first is given in full, and *"in the same directory"* is how the one
    beside it is referred to. So a bare filename is looked for where the
    documents already found actually live, which is what that sentence means.
    """
    try:
        with open(os.path.join(root, "README.md"), "r", encoding="utf-8") as fh:
            text = fh.read(200000)
    except OSError:
        return []
    root = os.path.realpath(root)
    parent = os.path.dirname(root)
    home = os.path.realpath(os.path.expanduser("~"))

    def keep(target):
        if not os.path.isfile(target) or not _ok(target) or not _ours(target):
            return False
        return (target.startswith(root + os.sep)
                or (target.startswith(parent + os.sep)
                    and target.startswith(home + os.sep)))

    named = [m.group(0) for m in POINTER.finditer(text)]
    out, seen, where = [], set(), [root, parent]

    for rel in named:
        if not os.path.dirname(rel.lstrip("~/")):
            continue                      # a bare name; the second pass has it
        tries = ([os.path.expanduser(rel)] if rel.startswith("~")
                 else [os.path.join(root, rel), os.path.join(parent, rel)])
        for candidate in tries:
            target = os.path.realpath(candidate)
            if keep(target) and target not in seen:
                seen.add(target)
                out.append(target)
                if os.path.dirname(target) not in where:
                    where.append(os.path.dirname(target))
                break

    for rel in named:
        if os.path.dirname(rel.lstrip("~/")):
            continue
        for folder in where:
            target = os.path.realpath(os.path.join(folder, rel))
            if keep(target) and target not in seen:
                seen.add(target)
                out.append(target)
                break
    return out


# The payload is rebuilt on every change and polled four times a second, and
# this is a walk of the repository plus a read of its README -- the same reason
# `walk.units` is remembered, and the same answer. A deck appears when somebody
# builds one, which is not on a quarter-second boundary.
CACHE_SECONDS = 30
_cache = {}


def _fresh(key, make):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    got = make()
    _cache[key] = (time.time(), got)
    return got


def documents(root):
    """Everything this course can be shown, in the order it should be offered.

    What the README names comes first, because a README that points at a
    document is saying which one to read -- and in these repositories it says so
    in the first screen, with a sentence about why.
    """
    return _fresh(os.path.realpath(root), lambda: _documents(os.path.realpath(root)))


def _documents(root):
    seen, out = set(), []
    for path in _pointed_at(root) + _in_repo(root):
        key = os.path.realpath(path)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": ident(root, key),
            "name": _pretty(key),
            "rel": _where(root, key),
            "at": _mtime(key),
            "size": _size(key),
        })
        if len(out) >= MAX_DOCS:
            break
    return out


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _where(root, path):
    """The document's path as a person would write it."""
    root = os.path.realpath(root)
    if path.startswith(root + os.sep):
        return os.path.relpath(path, root)
    home = os.path.realpath(os.path.expanduser("~"))
    if path.startswith(home + os.sep):
        return "~/" + os.path.relpath(path, home)
    return path


def ident(root, path):
    """A short, stable name for one document, safe to put in a URL.

    Derived from where the file is rather than kept in a record: a board that
    restarts hands out the same ids, and an id that arrives from a browser is
    checked by being looked up in `documents()` rather than by being trusted --
    so a name that is not one of ours resolves to nothing and never reaches a
    filesystem.
    """
    stem = re.sub(r"[^a-z0-9]+", "-", _pretty(path).lower()).strip("-")
    return (stem or "doc")[:40]


def find(root, ident_wanted):
    """The document with this id, as `(path, name)`, or `(None, None)`.

    The whole check. Nothing constructs a path from a request: an id is compared
    against the ids of documents this repository actually offers, and a miss is
    a miss.
    """
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    for doc in documents(root):
        if doc["id"] == wanted:
            # `rel` is how the document was found, and resolving it back is
            # cheaper and more honest than walking the repository again looking
            # for something we have already located.
            target = os.path.realpath(os.path.expanduser(doc["rel"])
                                      if doc["rel"].startswith("~")
                                      else os.path.join(root, doc["rel"]))
            return (target, doc["name"]) if os.path.isfile(target) else (None, None)
    return None, None


def pages(repo, ident_wanted, width=paper.PAGE_WIDTH):
    """Every page of one document, drawn and cached the way any other PDF is."""
    target, name = find(repo.root, ident_wanted)
    if not target:
        return {"ok": False, "why": "none",
                "detail": "This course does not offer a document by that name."}
    return paper.pages_of(repo, target, name + ".pdf", "reading", width)


def status(repo):
    """What the board shows in the drawer, and nothing more.

    Cheap enough for every payload: a bounded walk of a repository's own
    directories to a depth of three, plus one read of its README. A course with
    no documents sends nothing rather than an empty list, and the drawer does
    not offer the group.
    """
    try:
        found = documents(repo.root)
    except Exception:                                        # noqa: BLE001
        return None
    if not found:
        return None
    for doc in found:
        doc["iso"] = time.strftime("%Y-%m-%d", time.localtime(doc["at"])) \
            if doc["at"] else ""
    return {"documents": found}
