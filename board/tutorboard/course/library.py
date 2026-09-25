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

import hashlib
import os
import re
import subprocess
import time

from . import homework, paper, reading
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
def _paired_pdf(root, rel, stem):
    """The compiled PDF for this stem, wherever the build actually put it, or "".

    THE SOURCE AND THE THING IT BUILDS INTO ARE ONE DOCUMENT, and in a course
    they are not in the same directory. `chapters/ch04-field-extensions/
    homework/ch04-homework.tex` compiles to `chapters/ch04-field-extensions/
    build/ch04-homework.pdf` -- one level up and across -- and `build` is in
    `reading.IGNORE`, so this walk never reaches it. Forty compiled PDFs in one
    course were visible to nothing.

    The chain is `homework.compiled_pdf`'s and is not copied here: beside the
    source, then `build/` beside it, then the nearest `chNN`/`hwNN` unit
    directory's `build/`, matching the SOURCE'S OWN basename. One chain, so a
    course whose `scripts/build.sh` changes where it writes changes one file.

    Taking `build/` out of `IGNORE` instead is the answer that looks simpler and
    is wrong: the walk then groups by `(directory, stem)`, so every document
    arrives twice -- once as its source and once as its PDF -- and `build`
    sorting before `handwritten` renumbers ids that ink is anchored on.
    """
    here = root if rel in (".", "") else os.path.join(root, rel)
    found = homework.compiled_pdf(root, os.path.join(here, stem + ".tex"))
    if not found or fenced.refused(found):
        return ""
    return found


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
    # The build output the walk cannot see, joined back onto the source it came
    # from. Asked once per stem that has no PDF beside it, and it is three
    # `isfile` calls -- everything downstream reads it as though the walk had
    # found it there, because as far as the document is concerned it did.
    for (rel, stem), formats in found.items():
        if ".pdf" in formats:
            continue
        built = _paired_pdf(root, rel, stem)
        if built:
            formats[".pdf"] = built
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


def _offered(formats):
    """The source and the PDF of one stem, or None if it is not a document.

    WHAT MAKES A STEM A DOCUMENT, IN ONE PLACE. `_record` builds a record from
    this and `stamp` hands out ids from it, and the two have to agree exactly:
    an id the stamp invented for a stem the list does not offer is an id the
    page would ask about and never be answered.
    """
    src = formats.get(".tex") or formats.get(".md") or ""
    pdf = formats.get(".pdf") or ""
    if not src and not pdf:
        return None
    # A PDF nobody here wrote the source of, and small enough to be a figure.
    if not src and _size(pdf) < MIN_PDF_BYTES:
        return None
    return src, pdf


def _record(root, rel, stem, formats, taken):
    pair = _offered(formats)
    if not pair:
        return None
    src, pdf = pair
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


# ---------------------------------------------------------------------------
# HAS ANYTHING MOVED? -- the cheap question, asked often
# ---------------------------------------------------------------------------
# A revision is dispatched in the same request that files the note, and then the
# page went silent: `load()` ran after a send and on `visibilitychange`, and the
# open reader never re-fetched at all. So the deck was rebuilt on disk and the
# only thing that ever changed on the glass was a line saying the note was
# filed.
#
# A STAMP, NOT A SUBSCRIPTION. The hub's SSE payload is the LESSON's -- this
# page opens no sitting on purpose, and putting a sitting's stream on it would
# undo the one rule it exists to keep. So the page asks a question small enough
# to ask every few seconds, and `/library.json` stays the expensive answer it
# already is: that one walks the workspace, reads titles out of sources and runs
# `pdfinfo` per PDF, which is why it is cached for `CACHE_SECONDS`.
#
# WHAT IS IN IT, AND WHAT IS NOT. Where each document is, when its source and
# its PDF last changed, and how big they are -- `stat` and nothing else. No
# titles, no page counts, no notes: a note being filed must not move the stamp,
# or the page redraws on its own feedback. And the source is in it beside the
# PDF because a revision that edits the `.tex` and fails to rebuild has still
# changed the row -- that document is stale now, and the list says so.
#
# PER DOCUMENT AS WELL AS OVERALL. The overall hash answers "ask for the list
# again"; the per-document one answers "the document being read is the one that
# moved, so redraw it" -- and redrawing a 33-page deck because a different
# document was rebuilt is its own defect.
def stamp(root):
    """Where every document is and when it last changed. Stats only."""
    taken, docs, lines = set(), {}, []
    for (rel, stem), formats in _walk(root):
        pair = _offered(formats)
        if not pair:
            continue
        src, pdf = pair
        ident = _ident(rel, stem, taken)
        taken.add(ident)
        one = "|".join(
            "%s@%d:%d" % (os.path.relpath(p, root).replace(os.sep, "/"),
                          int(_mtime(p) * 1000), _size(p))
            for p in (src, pdf) if p)
        docs[ident] = hashlib.sha1(one.encode("utf-8")).hexdigest()[:12]
        lines.append(ident + " " + one)
        if len(docs) >= MAX_DOCS:
            break
    whole = hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:16]
    return {"ok": True, "stamp": whole, "documents": docs}


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
    if ext == ".pdf" and not os.path.isfile(target):
        # A compiled PDF is routinely NOT beside its source -- `_paired_pdf` is
        # what found it and `rel` is where. Still the document's own record
        # rather than anything that arrived, and still fenced below.
        rel = doc.get("rel") or ""
        if rel.lower().endswith(".pdf"):
            target = os.path.join(root, *rel.split("/"))
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
    out = paper.pages_of(repo, target, doc["stem"] + ".pdf", "library", width)
    if out.get("ok"):
        try:
            wipe_delivered(repo, doc)
        except Exception:                                    # noqa: BLE001
            pass
        out["ink"] = ink(repo, doc)
    return out


def ink(repo, doc):
    """The strokes already on this document's pages, `{key: strokes}`.

    SENT WITH THE PAGES, because the reader has to put them back the moment it
    draws one. The board's viewer gets the same thing out of the live payload it
    is already holding; this page holds no payload -- it opens no sitting and
    reads no `state.json` -- so the pages it asks for carry their own ink.

    Coordinates, not pictures. They are fractions of the page's own box, which
    is what lets the same marks land in the same place on a rotated iPad, and
    `annotate.js` is the only thing that reads them.

    UNDER BOTH NAMES THIS DOCUMENT HAS. A document marked from the drawer
    carries the drawer's ident and one marked from here carries the library's,
    and it is one document either way -- `mark_idents` is the same answer
    `marks` uses when it reads the ink back as a complaint.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    wanted = set(mark_idents(repo.root, doc))
    out = {}
    for key, strokes in lesson_notes.load_notes(repo).items():
        found = writing.ann_doc_page(key)
        if found and strokes and found[0] in wanted:
            out[key] = strokes
    return out


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


# HOW MUCH OF A ROUND IS READ BACK. A note is a paragraph and a list of marked
# pages; the `## What was changed` the turn appends to it is the longest part and
# is the half worth reading. Bounded anyway, because this is a file a turn writes
# and a turn that loops writes a large one.
NOTE_BYTES = 200000


def note_text(root, doc, name_wanted):
    """One round of feedback on one document, as text.

    WHY THIS EXISTS. The revision turn writes `## What was changed` at the
    bottom of the feedback file, and that is the answer to *did it do what I
    asked* -- while `notes` returns names, sizes and dates and not a word of the
    contents. So the page could say a document had had three rounds and could
    not say what any of them did, and the record lived in a file the iPad cannot
    open.

    A NAME OUT OF `notes`, NEVER A PATH. What arrives from the browser is
    compared against the names this module found beside this document, and a
    miss is a miss -- the rule `find` holds for an id, one level down. Nothing
    here joins a name from a browser onto a directory.
    """
    wanted = str(name_wanted or "").strip()
    found = None
    for rec in notes(root, doc):
        if rec["name"] == wanted:
            found = rec
            break
    if not found:
        return {"ok": False, "error": "no such round of feedback on this document"}
    path = os.path.join(feedback_dir(root, doc), found["name"])
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(NOTE_BYTES)
    except OSError as exc:
        return {"ok": False, "error": "could not read %s: %s" % (found["name"], exc)}
    out = dict(found)
    out.update({"ok": True, "document": doc["id"], "title": doc["title"],
                "rel": os.path.relpath(path, root).replace(os.sep, "/"),
                "text": text,
                "truncated": _size(path) > NOTE_BYTES})
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


# The file beside a deck made from sittings that says what it covers. Named here
# rather than imported from `sittings`, which imports this module.
DECK_BRIEF = "_brief.md"


def from_sittings(root, doc):
    """Is this a deck made from sittings -- its brief beside it?"""
    where = (doc or {}).get("dir") or ""
    return bool(where) and os.path.isfile(
        os.path.join(root, *(where.split("/") + [DECK_BRIEF])))


def last_round_landed(root, doc):
    """Did the newest round of feedback on this document come back?

    Yes where there is no round yet; where the turn wrote its `## What was
    changed` under the note, which is the last thing a revision does; or where
    the PDF was rebuilt after the note was written. A round whose turn died, or
    whose build failed, is none of those.
    """
    rounds = notes(root, doc)
    if not rounds:
        return True
    path = os.path.join(feedback_dir(root, doc), rounds[-1]["name"])
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            if "## What was changed" in fh.read(NOTE_BYTES):
                return True
    except OSError:
        return True
    pdf = path_of(root, doc, ".pdf")
    return bool(pdf) and _mtime(pdf) >= _mtime(path)


def carried(repo, doc, found, sent=None):
    """The marks in `found` that the next note on `doc` carries.

    EVERY MARK, for every document but one kind -- the rule this library has
    always had, and a paper's reader has never asked for another.

    A DECK MADE FROM SITTINGS carries only ink no round has delivered once the
    last round came back (`last_round_landed`). Its slides are redrawn in place
    and renumber, so a ring that already produced a revision, sent again, points
    at whatever slide now sits under it. `/annotate/save` writes `sent: false`
    every time a page's ink changes, so a slide drawn on again is back in,
    whole. And where the last round did NOT come back -- the turn died, the
    build failed, nothing could be asked -- everything goes again, so a retry
    is a tap rather than a redrawing.
    """
    if not found or not from_sittings(repo.root, doc) \
            or not last_round_landed(repo.root, doc):
        return list(found)
    from ..lesson import notes as lesson_notes        # local: avoids a cycle

    sent = lesson_notes.load_notes_sent(repo) if sent is None else sent
    return [m for m in found if not sent.get(m["key"])]


def wipe_delivered(repo, doc, sent=None):
    """Delete the ink a landed round delivered. Returns the keys that went.

    A mark is spent once the revision it asked for came back: left on the
    page, it sits over a slide that has already been changed, and on a deck
    whose slides renumber it sits over the wrong one. So once the newest round
    has landed (`last_round_landed`, and there must BE a round), every mark on
    this document that a note carried (`sent`) goes, picture and all. Ink
    drawn since is `sent: false` -- `/annotate/save` writes that on every
    change -- and stays for the next round. A round that has not landed keeps
    everything, so a retry is still a tap.
    """
    if not notes(repo.root, doc) or not last_round_landed(repo.root, doc):
        return []
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    sent = lesson_notes.load_notes_sent(repo) if sent is None else sent
    wanted = set(mark_idents(repo.root, doc))
    gone = []
    for key, was_sent in sent.items():
        found = writing.ann_doc_page(key)
        if not was_sent or not found or found[0] not in wanted:
            continue
        stem = os.path.join(repo.notes, writing.ann_file(key))
        for ext in (".json", ".png"):
            try:
                os.remove(stem + ext)
            except OSError:
                continue
        gone.append(key)
    return gone


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


# THE TWO ASKS, AND THEY ARE NOT THE SAME DOCUMENT AFTERWARDS.
#
# `revise` is a correction: the structure, the names for things and the claims
# stand, and what the note points at changes. That is the right answer to
# "figure 3 is mislabelled" and it is the wrong answer to "that presentation
# needs an overhaul now that we plan to use colibri" -- and the prompt a
# revision is woken with says outright *do not start it again and do not widen
# it*, so until there was a second ask the only route to an overhaul was a
# terminal.
#
# `rework` may restructure, cut, reorder and rewrite. What it requires in
# exchange is a sentence saying what the document is now FOR: that is
# `/direction`'s shape one level down, and an overhaul with no new purpose in it
# is a rewrite for its own sake.
ASKS = ("revise", "rework")

# HOW SHORT A PURPOSE MAY BE. Not a validation for its own sake: "make it
# better" is the sentence this refusal exists to catch, and a turn handed that
# is a turn choosing the document's purpose on its own.
PURPOSE_LEAST = 25


def clean_ask(ask):
    """Which of the two asks this is. Anything unrecognised is a correction."""
    want = str(ask or "").strip().lower()
    return want if want in ASKS else "revise"


def write_note(repo, ident_wanted, text, page=0, ask="revise", purpose="",
               hand_over=True):
    """One round of feedback on one document. Returns a record to paint.

    The note says which document and which page it is about, because it is read
    later by a turn that was not in the room -- and a page number is worth
    carrying, since the person writing it is looking at a page when they do.

    MARKS COUNT AS SAYING SOMETHING. A ring round a figure and an arrow to its
    caption is a complaint, and refusing the note for an empty textarea would be
    the board asking somebody to type out what they have already drawn. The ink
    goes into the note as the pages it is on and the picture of each, because
    the strokes are coordinates and the image is what a reader can open. Which
    ink goes is `carried`'s: all of it, except on a deck made from sittings
    whose last round came back, where ink already acted on stays behind.

    `hand_over` records the ink as delivered here. The route passes False and
    records it only once the revision was actually asked (`hand_over`), so a
    note written beside an ask that failed leaves the ink to go again.

    A REWORK IS THE SAME FILE AND THE SAME ROUNDS. It is a longer turn rather
    than a different kind of record, so it lands where a correction lands and is
    read back the same way -- with the purpose it was given as its own section,
    because that sentence is the thing the turn is working to.
    """
    root = repo.root
    doc = find(root, ident_wanted)
    if not doc:
        return {"ok": False, "error": "no such document"}
    ask = clean_ask(ask)
    said = (text or "").strip()
    aim = (purpose or "").strip()
    found = carried(repo, doc, marks(repo, doc))
    if ask == "rework" and len(aim) < PURPOSE_LEAST:
        return {"ok": False,
                "error": "say what the document is FOR now, in a sentence -- an "
                         "overhaul with no new purpose in it is a rewrite for "
                         "its own sake"}
    if ask == "revise" and not said and not found:
        return {"ok": False, "error": "say what is wrong with it, or mark it up"}
    target = next_note(root, doc)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
    except OSError as exc:
        return {"ok": False, "error": "could not make %s: %s"
                                      % (os.path.dirname(target), exc)}
    head = ["# %s %s" % ("Rework of" if ask == "rework" else "Feedback on",
                         doc["title"]), "",
            "- document: `%s`" % (doc["rel"]),
            "- written: %s" % time.strftime("%Y-%m-%d %H:%M"),
            "- ask: %s" % ask]
    if page:
        head.append("- about page %d" % int(page))
    if found:
        head.append("- marked up on %d page%s"
                    % (len(found), "" if len(found) == 1 else "s"))
    head += ["", said or
             ("There is nothing wrong with it in particular. What it is for has "
              "changed." if ask == "rework" else
              "They wrote on it rather than typing. The marks are the feedback."),
             ""]
    if aim:
        head += ["## What this document is FOR now", "",
                 "THIS IS THE OVERHAUL'S BRIEF, and it outranks the document's "
                 "present shape. Restructure, cut, reorder and rewrite as this "
                 "requires.", "", aim, ""]
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
    if hand_over:
        _handed_over(repo, found)
    forget()
    return {"ok": True, "document": doc["id"], "path": target,
            "rel": os.path.relpath(target, root).replace(os.sep, "/"),
            "made": doc["made"], "title": doc["title"],
            "ask": ask, "purpose": aim,
            "marks": len(found), "keys": [m["key"] for m in found]}


def hand_over(repo, keys):
    """Record the marks under these keys as delivered. `write_note`'s `keys`,
    once the round they went with has been asked for."""
    _handed_over(repo, [{"key": k} for k in keys or [] if isinstance(k, str)])


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
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle
    try:
        sent = lesson_notes.load_notes_sent(repo)
    except Exception:                                        # noqa: BLE001
        sent = {}
    for doc in found:
        doc["iso"] = (time.strftime("%Y-%m-%d", time.localtime(doc["at"]))
                      if doc["at"] else "")
        # SPENT INK GOES FIRST, so the counts below are of what is still on
        # the page. `index` and `sent` were read before it, so they are pruned
        # of what went rather than read again.
        try:
            for key in wipe_delivered(repo, doc, sent):
                sent.pop(key, None)
                got = writing.ann_doc_page(key)
                if got and got[0] in index:
                    index[got[0]].pop(got[1], None)
        except Exception:                                    # noqa: BLE001
            pass
        # HOW MUCH INK IS ON IT, because the page has to be able to say that
        # marks will go with the note -- somebody who drew on three pages and
        # then found an empty textarea refusing to send has been told their
        # marks do not count.
        try:
            ink = marks(repo, doc, index=index)
        except Exception:                                    # noqa: BLE001
            ink = []
        # AND HOW MUCH OF IT A NOTE WOULD CARRY, which is what the send button
        # is live on -- `carried`, so the count and the note cannot disagree.
        try:
            waiting = len(carried(repo, doc, ink, sent))
        except Exception:                                    # noqa: BLE001
            waiting = len(ink)
        doc["marks"] = {"pages": len(ink),
                        "strokes": sum(m["strokes"] for m in ink),
                        "waiting": waiting}
    return {"workspace": atlas.identify(root), "documents": found,
            "writeups": WRITEUPS}
