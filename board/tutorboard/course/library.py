"""library.py -- everything a workspace has WRITTEN, grouped into documents.

`reading.py` answers a different question and keeps its own numbers: "what can
be put on the glass in a card", three levels deep, twenty-four documents, PDFs
of at least 20 kB. Those are the right numbers for a drawer that offers a page
of a deck, and the wrong ones for a workspace with fifty documents in it.

This answers "everything this workspace has written", and the difference is
GROUPING. **A document is a STEM in a DIRECTORY, in however many formats it
has.** `manuscript.md` + `manuscript.pdf` + `manuscript.docx` is one document.
`stage1_pipeline_walkthrough.tex` + `.pdf` is one document. The directory is the
group, and the group is what the library draws a heading from.

NOTHING IS DECLARED, which is what lets the two layouts that already exist stay
where they are:

    title   `\\title{...}` in a `.tex`, the first `# ` in a `.md`, and the
            filename through `reading._pretty` when a source says neither
    kind    `\\documentclass[...]{beamer}` is a deck; anything else is a paper
    stale   arithmetic -- the source's modification time against the PDF's

New documents land in `writeups/<slug>/`, one directory per document, because a
deck's figures and its rounds of feedback need somewhere to be. `writeups` and
not `papers`: `reading.NOT_OURS` already means a `papers/` directory is somebody
else's library.

THE FENCE IS THE SAME ONE. `fenced.refused` on the whole path, and
`reading.NOT_OURS` on the directory names -- without the second, TRD-EHR's
`references/` arrives as forty documents by other people.

Standard library only, like everything else.
"""

import os
import re
import subprocess
import time

from . import paper, reading
from .. import atlas, fenced, manuscript

# What a document can be written in, and what it can be built into. A stem with
# neither a source nor a PDF is not a document, whatever else is beside it.
SOURCE = (".tex", ".md")
BUILT = (".pdf", ".docx")
FORMATS = SOURCE + BUILT

# Where a document this board makes goes, one directory per document.
WRITEUPS = "writeups"

# Deeper than the drawer, because a manuscript directory is two levels inside a
# workspace already and its parts are a third. Not unbounded: a walk of a
# repository is the one thing here that costs more than a stat.
MAX_DEPTH = 4

# A library is allowed to be long. It is not allowed to be a file manager, and a
# workspace with more than this has something other than documents in it.
MAX_DOCS = 120

# A stem with no source at all has to earn its place on size, the same way the
# drawer's PDFs do: a figure exported as a one-page PDF is not a document.
MIN_PDF_BYTES = reading.MIN_BYTES

# A repository's furniture, which is not something it wrote up. Matched on the
# stem, so `README.md` in every directory is skipped and `readme_of_the_grid.md`
# is not.
FURNITURE = {"readme", "handoff", "license", "licence", "notice", "changelog",
             "contributing", "todo", "ai_instructions", "teaching", "claude",
             "agents", "direction", "index"}

# HOW LONG AN ID MAY BE, and the number is not this module's. It is
# `writing.ANN_DOC`'s: a mark on a page of a document is anchored to
# `doc/<ident>/p<n>` and that pattern allows forty characters, so an id longer
# than this is a document that cannot be written on. Derived rather than stored,
# so shortening it costs nothing but a different URL.
IDENT_MAX = 40

# A PIECE OF A DOCUMENT IS NOT A DOCUMENT. `paper1-trd-prediction/parts/
# manuscript/` holds that manuscript's own sections, one file each, and drawing
# them beside it makes one document look like twelve. The whole is in the
# directory above; these are what it was assembled from.
PIECES = ("parts", "sections")


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


# ---------------------------------------------------------------------------
# what the source says about itself
# ---------------------------------------------------------------------------
# A `.tex` title is 140 lines into `stage2_reference_walkthrough`, after the
# macros, so the whole preamble is read rather than the first screen of it.
_TEX_TITLE = re.compile(r"\\title\s*(?:\[[^\]]*\])?\{(.+?)\}", re.S)
_TEX_CLASS = re.compile(r"\\documentclass\s*(?:\[[^\]]*\])?\{([^}]*)\}")
_MD_TITLE = re.compile(r"^#[ \t]+(.+?)\s*$", re.M)
_TEX_NOISE = re.compile(r"\\[a-zA-Z]+\s*|[{}~$\\]")


def _said(path, limit=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def _plain(text):
    """A title out of a source file, as a person would read it aloud."""
    return re.sub(r"\s+", " ", _TEX_NOISE.sub(" ", text or "")).strip()


def _from_source(src, stem):
    """The title and the kind, out of the source. `(title, kind)`.

    A document with no source, or one that names no title, is called after its
    file -- which is what its author calls it out loud, and is the only name
    anybody would recognise it by.
    """
    fallback = reading._pretty(stem)
    if not src:
        return fallback, "paper"
    text = _said(src)
    kind = "paper"
    if src.lower().endswith(".tex"):
        said = _TEX_CLASS.search(text)
        if said and "beamer" in said.group(1).lower():
            kind = "deck"
        found = _TEX_TITLE.search(text)
        title = _plain(found.group(1)) if found else ""
    else:
        found = _MD_TITLE.search(text)
        title = _plain(found.group(1)) if found else ""
    return (title or fallback), kind


# HOW MANY PAGES, and it is asked of the tool that already draws them rather
# than of the bytes. A modern PDF keeps its page tree in a compressed object
# stream, so counting `/Type /Page` in the file finds nothing at all in both of
# the layouts this has to work on -- a count that is silently zero is worse than
# no count. Memoised on the file's own modification time, so a library opened
# twice costs one `stat` per document.
_PAGES = {}


def _pages(path):
    if not path:
        return 0
    key = (os.path.realpath(path), _mtime(path))
    if key in _PAGES:
        return _PAGES[key]
    n = 0
    env = paper.raster_env()
    try:
        p = subprocess.run(["pdfinfo", path], env=env,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20)
        found = re.search(r"^Pages:\s+(\d+)", p.stdout.decode("utf-8", "replace"),
                          re.M)
        n = int(found.group(1)) if found else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        n = 0
    if len(_PAGES) > 400:
        _PAGES.clear()
    _PAGES[key] = n
    return n


# ---------------------------------------------------------------------------
# finding them
# ---------------------------------------------------------------------------
def _walk(root):
    """Every stem in this workspace that has a document's formats beside it.

    In file order, nearest the top first, which is the order the library draws.
    """
    found, order = {}, []
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and d not in reading.IGNORE
                         and d.lower() not in reading.NOT_OURS
                         and d.lower() not in PIECES
                         and not fenced.refused(d))
        for name in sorted(files):
            if name.startswith(".") or name.startswith("_"):
                continue
            stem, ext = os.path.splitext(name)
            if not stem or ext.lower() not in FORMATS:
                continue
            if stem.lower() in FURNITURE:
                continue
            path = os.path.join(here, name)
            # The pruning above is the cheap half and it is not the rule: it
            # only sees the directories this walk descends through. Asked of the
            # whole path, at any depth, the way `reading._fenced` is.
            if fenced.refused(path):
                continue
            key = (rel, stem)
            if key not in found:
                found[key] = {}
                order.append(key)
            found[key][ext.lower()] = path
    return [(k, found[k]) for k in order]


def _ident(rel, stem, taken):
    """A short, stable name for one document, safe to put in a URL.

    Derived from where it is rather than kept in a record, so a board that
    restarts hands out the same ids -- and an id that arrives from a browser is
    checked by being looked up in `documents()` rather than trusted.
    """
    base = stem if rel in (".", "") else rel.replace(os.sep, "-") + "-" + stem
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:IDENT_MAX] or "document"
    out, n = slug, 1
    while out in taken:
        n += 1
        out = "%s-%d" % (slug[:IDENT_MAX - 4], n)
    return out


def _record(root, rel, stem, formats, taken):
    src = formats.get(".tex") or formats.get(".md") or ""
    pdf = formats.get(".pdf") or ""
    if not src and not pdf:
        return None
    # A PDF nobody here wrote the source of, and small enough to be a figure.
    if not src and _size(pdf) < MIN_PDF_BYTES:
        return None
    title, kind = _from_source(src, stem)
    where = "" if rel in (".", "") else rel.replace(os.sep, "/")
    built = _mtime(pdf)
    rec = {
        "id": _ident(rel, stem, taken),
        "dir": where,
        "stem": stem,
        "title": title,
        "kind": kind,
        "formats": sorted(e.lstrip(".") for e in formats),
        "rel": os.path.relpath(pdf or src, root).replace(os.sep, "/"),
        # THE SOURCE, SEPARATELY, AND IT IS NOT `rel`. `rel` is what to put on the
        # glass, which is the PDF wherever there is one -- and a revision handed that
        # is a revision asked to edit a rendering. Whatever revises this document
        # edits the file it was built from.
        "source": (os.path.relpath(src, root).replace(os.sep, "/") if src else ""),
        "at": built or max(_mtime(p) for p in formats.values()),
        "built": built,
        "size": _size(pdf or src),
        "pages": _pages(pdf),
        # Arithmetic, not a record: the source is newer than the PDF, so what is
        # on the glass is not what the file says any more.
        "stale": bool(src and pdf and _mtime(src) > built),
        "pdf": bool(pdf),
        # Which machinery revises it, and it is the one thing about a document
        # the library has to know. See `change 6` in HANDOFF.md: an explainer the
        # board compiled is revised by the board, and a manuscript delivered into
        # `manuscripts/` is revised by Paper-Writer.
        "made": ("paper-writer"
                 if where == manuscript.LANDING
                 or where.startswith(manuscript.LANDING + "/")
                 else "board"),
    }
    rec["notes"] = notes(root, rec)
    return rec


# The payload this feeds is fetched when somebody opens the library rather than
# four times a second, but a library of fifty documents is fifty `pdfinfo` runs
# and a person tapping between pages of one should not pay for them again.
CACHE_SECONDS = 30
_cache = {}


def documents(root):
    """Every document this workspace has written, grouped, in file order."""
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    got = _documents(key)
    _cache[key] = (time.time(), got)
    return got


def _documents(root):
    out, taken = [], set()
    for (rel, stem), formats in _walk(root):
        rec = _record(root, rel, stem, formats, taken)
        if not rec:
            continue
        taken.add(rec["id"])
        out.append(rec)
        if len(out) >= MAX_DOCS:
            break
    return out


def forget():
    """Drop the cache. For a test that writes a document under the process."""
    _cache.clear()
    _PAGES.clear()


def find(root, ident_wanted):
    """The document with this id, or None.

    AN ID, NEVER A PATH. What arrives from the browser is compared against what
    this module discovered, and a miss is a miss -- `reading.find` is the rule
    and this is the same rule for a longer list.
    """
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None
    for doc in documents(root):
        if doc["id"] == wanted:
            return doc
    return None


def path_of(root, doc, ext=".pdf"):
    """Where one format of one document actually is, or "".

    Built from the document that was FOUND rather than from anything that
    arrived, which is what keeps a name out of a browser off the filesystem.
    """
    if not doc:
        return ""
    here = os.path.join(root, *([] if not doc["dir"] else doc["dir"].split("/")))
    target = os.path.join(here, doc["stem"] + ext)
    if fenced.refused(target) or not os.path.isfile(target):
        return ""
    return target


def pages(repo, ident_wanted, width=paper.PAGE_WIDTH):
    """Every page of one document, drawn and cached the way any other PDF is.

    The renderer, the cache and the page addresses are `course/paper.py`'s and
    are unchanged: what differs is only how the file was found.
    """
    doc = find(repo.root, ident_wanted)
    if not doc:
        return {"ok": False, "why": "none",
                "detail": "This workspace has no document by that name."}
    target = path_of(repo.root, doc, ".pdf")
    if not target:
        return {"ok": False, "why": "unbuilt",
                "detail": ("%s has no PDF beside it yet, so there are no pages "
                           "to draw." % doc["title"])}
    return paper.pages_of(repo, target, doc["stem"] + ".pdf", "library", width)


# ---------------------------------------------------------------------------
# feedback, written where the document is
# ---------------------------------------------------------------------------
# DATED AND VERSIONED, NEVER STAMPED WITH THE TIME -- `manuscript._next_version`
# is the rule and this is the same rule for a different directory. Tracked, so a
# note written on an iPad is there on the compute node.
NOTE_RE = re.compile(r"^(?P<stem>.*?)(?P<day>\d{4}-\d{2}-\d{2})-v(?P<n>\d+)\.md$")


def _is_writeup(doc):
    """Is this a document the board made, in its own directory?

    `writeups/<slug>/` is one directory per document, so the note does not have
    to repeat the stem in its name. The two layouts that already exist are flat
    -- four stems in one directory -- and there it does.
    """
    where = (doc or {}).get("dir") or ""
    return where == WRITEUPS or where.startswith(WRITEUPS + "/")


def feedback_dir(root, doc):
    here = os.path.join(root, *([] if not doc["dir"] else doc["dir"].split("/")))
    return os.path.join(here, "feedback")


def notes(root, doc):
    """The rounds of feedback already written on this document, newest last."""
    where = feedback_dir(root, doc)
    prefix = "" if _is_writeup(doc) else doc["stem"] + "-"
    out = []
    try:
        names = sorted(os.listdir(where))
    except OSError:
        return out
    for n in names:
        m = NOTE_RE.match(n)
        if not m or m.group("stem") != prefix:
            continue
        p = os.path.join(where, n)
        out.append({"name": n, "at": _mtime(p), "size": _size(p),
                    "day": m.group("day"), "v": int(m.group("n"))})
    out.sort(key=lambda x: (x["day"], x["v"]))
    return out


def next_note(root, doc, day=None):
    """Where the next round of feedback on this document goes.

    `writeups/<slug>/feedback/<date>-v<n>.md` for a document the board made, and
    `<dir>/feedback/<stem>-<date>-v<n>.md` for the two layouts that already
    exist, where four documents share one directory.
    """
    day = day or time.strftime("%Y-%m-%d")
    prefix = "" if _is_writeup(doc) else doc["stem"] + "-"
    where = feedback_dir(root, doc)
    high = 0
    try:
        names = os.listdir(where)
    except OSError:
        names = []
    for n in names:
        m = NOTE_RE.match(n)
        if m and m.group("stem") == prefix and m.group("day") == day:
            high = max(high, int(m.group("n")))
    return os.path.join(where, "%s%s-v%d.md" % (prefix, day, high + 1))


# ---------------------------------------------------------------------------
# feedback made of MARKS
# ---------------------------------------------------------------------------
# WRITTEN FEEDBACK HAD A ROUTE AND INK DID NOT, and the two say different
# things. "Figure 3 is wrong" is a sentence; a ring round the axis label and an
# arrow to the caption is the same complaint located, and typing out where it
# points is a translation nobody should have to perform.
#
# Nothing new is stored. A page of a document already carries ink -- the viewer
# gives every page a box, `annotate.js` attaches to it, and the strokes are
# saved against `doc/<ident>/p<n>` exactly as a mark on a card is saved against
# its card. What was missing is the reading: this is the function that looks
# the marks up where the textarea is read.
#
# TWO IDENTS FOR ONE DOCUMENT, and both are asked. The drawer names a document
# by `reading.ident` -- the slug of its filename -- and this module names it by
# where it sits, because a library has to tell two `manuscript.pdf`s apart.
# Marking works on the board today, which means under the drawer's name; the
# library's own name is what a mark made on the library page would carry. A
# document is one document and its ink is its ink, so a note carries whatever is
# there under either.

def marked_pages(repo):
    """Every page of every document that has ink on it. `{ident: {page: n}}`.

    ONE PASS OVER THE DRAWER, FOR THE WHOLE LIBRARY. Asked per document it is a
    read and a parse of every annotation record per document, which on a
    workspace with fifty documents and a term's worth of marked-up cards is
    thousands of file reads for one payload. The drawer is small and the
    question is the same for every row, so it is asked once.

    A page count is NOT consulted here, deliberately. `pdfinfo` missing is a
    page count of zero, and deriving "which pages could be marked" from it would
    lose the ink for a reason that has nothing to do with the ink.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    out = {}
    for key, strokes in lesson_notes.load_notes(repo).items():
        found = writing.ann_doc_page(key)
        if not found or not strokes:
            continue
        out.setdefault(found[0], {})[found[1]] = len(strokes)
    return out


def mark_idents(root, doc):
    """Every annotation ident this one document could have been marked under."""
    out = [doc["id"]]
    target = path_of(root, doc, ".pdf")
    if target:
        drawer = reading.ident(root, target)
        if drawer and drawer not in out:
            out.append(drawer)
    return out


def marks(repo, doc, index=None):
    """Every marked page of one document, in page order.

    `[{page, ident, key, strokes, png}]`, where `png` is repository-relative and
    is the picture of that page's ink the viewer saved beside the strokes. The
    strokes themselves are coordinates and are no use to a reader; the image is
    the thing a revision turn opens.

    `index` is `marked_pages`, which a caller asking about every document in a
    workspace reads once and passes in.
    """
    from ..server.routes import writing               # local: avoids a cycle

    index = marked_pages(repo) if index is None else index
    if not index:
        return []
    out = []
    for ident in mark_idents(repo.root, doc):
        for page, strokes in (index.get(ident) or {}).items():
            key = "doc/%s/p%d" % (ident, page)
            # The filename is DERIVED from the key by the one function that
            # does that derivation, never rebuilt here. It is the rule this
            # system is load-bearing on for security, and a second
            # implementation of it is the way that rule stops holding.
            png = os.path.join(repo.notes, writing.ann_file(key) + ".png")
            out.append({"page": page, "ident": ident, "key": key,
                        "strokes": strokes,
                        "png": (os.path.relpath(png, repo.root).replace(os.sep, "/")
                                if os.path.isfile(png) else "")})
    out.sort(key=lambda m: (m["page"], m["ident"]))
    return out


def _handed_over(repo, found):
    """Record that these marks have gone to somebody, next to the marks.

    The board asks this to tell ink that was delivered from ink that was only
    autosaved -- without it, yesterday's forgotten marks demand a decision every
    time anything is sent. A note that carries them IS the delivery, so the flag
    is set here for the same reason `/annotate/save` sets it when a mark is sent
    as a turn.
    """
    from ..server.routes import writing               # local: avoids a cycle

    import json as _json
    for mark in found:
        path = os.path.join(repo.notes, writing.ann_file(mark["key"]) + ".json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rec = _json.load(fh)
            if rec.get("sent"):
                continue
            rec["sent"] = True
            with open(path, "w", encoding="utf-8") as fh:
                _json.dump(rec, fh)
        except (OSError, ValueError):
            continue


def write_note(repo, ident_wanted, text, page=0):
    """One round of feedback on one document. Returns a record to paint.

    The note says which document and which page it is about, because it is read
    later by a turn that was not in the room -- and a page number is worth
    carrying, since the person writing it is looking at a page when they do.

    MARKS COUNT AS SAYING SOMETHING. A ring round a figure and an arrow to its
    caption is a complaint, and refusing the note for an empty textarea would be
    the board asking somebody to type out what they have already drawn. The ink
    goes into the note as the pages it is on and the picture of each, because
    the strokes are coordinates and the image is what a reader can open.
    """
    root = repo.root
    doc = find(root, ident_wanted)
    if not doc:
        return {"ok": False, "error": "no such document"}
    said = (text or "").strip()
    found = marks(repo, doc)
    if not said and not found:
        return {"ok": False, "error": "say what is wrong with it, or mark it up"}
    target = next_note(root, doc)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
    except OSError as exc:
        return {"ok": False, "error": "could not make %s: %s"
                                      % (os.path.dirname(target), exc)}
    head = ["# Feedback on %s" % doc["title"], "",
            "- document: `%s`" % (doc["rel"]),
            "- written: %s" % time.strftime("%Y-%m-%d %H:%M")]
    if page:
        head.append("- about page %d" % int(page))
    if found:
        head.append("- marked up on %d page%s"
                    % (len(found), "" if len(found) == 1 else "s"))
    head += ["", said or
             "They wrote on it rather than typing. The marks are the feedback.",
             ""]
    if found:
        head += ["## What they marked", "",
                 "Each line is one page of this document with their ink on it. "
                 "OPEN THE IMAGE: the marks are where the complaint is, and the "
                 "page number alone does not say what they point at.", ""]
        for mark in found:
            line = "- page %d, %d stroke%s" % (mark["page"], mark["strokes"],
                                               "" if mark["strokes"] == 1 else "s")
            line += " -- `%s`" % mark["png"] if mark["png"] else " -- no image was "\
                                                                 "saved for this page"
            head.append(line)
        head.append("")
    try:
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("\n".join(head))
    except OSError as exc:
        return {"ok": False, "error": "could not write %s: %s" % (target, exc)}
    _handed_over(repo, found)
    forget()
    return {"ok": True, "document": doc["id"], "path": target,
            "rel": os.path.relpath(target, root).replace(os.sep, "/"),
            "made": doc["made"], "title": doc["title"],
            "marks": len(found)}


def status(repo):
    """What the library page draws, and nothing more."""
    root = repo.root
    try:
        found = documents(root)
    except Exception:                                        # noqa: BLE001
        found = []
    try:
        index = marked_pages(repo)
    except Exception:                                        # noqa: BLE001
        index = {}
    for doc in found:
        doc["iso"] = (time.strftime("%Y-%m-%d", time.localtime(doc["at"]))
                      if doc["at"] else "")
        # HOW MUCH INK IS ON IT, because the page has to be able to say that
        # marks will go with the note -- somebody who drew on three pages and
        # then found an empty textarea refusing to send has been told their
        # marks do not count.
        try:
            ink = marks(repo, doc, index=index)
        except Exception:                                    # noqa: BLE001
            ink = []
        doc["marks"] = {"pages": len(ink),
                        "strokes": sum(m["strokes"] for m in ink)}
    return {"workspace": atlas.identify(root), "documents": found,
            "writeups": WRITEUPS}
