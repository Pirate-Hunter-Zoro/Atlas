"""library.py -- one inventory of a subject's documents and results.

Three views, each a filter of one walk (`_files`): `documents` (every stem
the subject wrote, as artifacts, then legacy documents, then materials),
`drawer` (the PDFs a card can show), and `results` (what a pipeline produced
under the allowlist `LOOK_IN`, walked separately because `IGNORE` prunes
`results/`). A document is a stem in a directory in however many formats it
has; title, kind and staleness are read from the files, never declared.

The constraint: an id, never a path. What arrives from a browser is matched
against what discovery found, and the fence (`fenced.refused`) is asked of
every pruned directory and every whole path offered.
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import time
from urllib.parse import unquote

from . import paper
from .. import artifacts, fenced, paths, subjects

# A stem with neither a source nor a PDF is not a document.
SOURCE = (".tex", ".md")
BUILT = (".pdf", ".docx")
FORMATS = SOURCE + BUILT

# Where a document this board makes goes, one directory per document.
WRITEUPS = "writeups"

# Never entered. Not the fence: `fenced.NEVER` is asked on whole paths too.
IGNORE = {"live", "node_modules", "__pycache__", "build", "dist", "target",
          "venv", ".venv", "env", "site-packages", "vendor", "results",
          "data", "test_data", "archive"}

# Reference libraries of other people's papers.
NOT_OURS = ("references", "reference", "library", "papers", "reading",
            "literature", "formats", "feedback")

# Bounded, because the walk is the one thing here that costs more than a stat.
MAX_DEPTH = 4

# A subject with more than this has something other than documents in it.
MAX_DOCS = 120

# A sourceless PDF smaller than this is a figure, not a document.
MIN_PDF_BYTES = 20000

# Repository furniture, matched on the stem.
FURNITURE = {"readme", "handoff", "license", "licence", "notice", "changelog",
             "contributing", "todo", "ai_instructions", "teaching", "claude",
             "agents", "direction", "index", "rules", "tutor"}

# `writing.ANN_DOC` allows forty characters for `doc/<ident>/p<n>`.
IDENT_MAX = 40

# A piece of a manuscript (`<dir>/parts/<stem>/`) names the `whole` it was cut
# from, because an edit to a piece is lost on the next cut.
PIECES = ("parts", "sections")

# Every view is rebuilt on demand and the hub asks often.
CACHE_SECONDS = 30


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
# A `.tex` title can sit far into the preamble, so read all of it.
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
    """`(title, kind)` out of the source; a document naming no title is
    called after its file."""
    fallback = _pretty(stem)
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


# Page counts come from `pdfinfo`, because a compressed page tree hides
# `/Type /Page` from a byte count. Memoised on mtime.
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
# the walk
# ---------------------------------------------------------------------------
def _pretty(path, fallback="document"):
    """What to call a file in a list: its name, unpunctuated."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[_-]+", " ", stem).strip() or fallback


def _depth(rel):
    return 0 if rel in (".", "") else rel.count(os.sep) + 1


def _files(root, skip=()):
    """`(rel, name, path)` for every file the subject may offer, in walk order.

    Hidden names, `IGNORE`, `NOT_OURS`, fenced names and anything below
    `MAX_DEPTH` are never entered; nor are `skip` directories (artifacts at
    `docs/<slug>/`, listed from their doc.json).
    """
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        if _depth(rel) >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and d not in IGNORE
                         and d.lower() not in NOT_OURS
                         and not fenced.refused(d)
                         and (d if rel == "." else os.path.join(rel, d))
                         .replace(os.sep, "/") not in skip)
        for name in sorted(files):
            if name.startswith("."):
                continue
            path = os.path.join(here, name)
            # The fence is asked of the whole path too, at any depth.
            if fenced.refused(path):
                continue
            yield rel, name, path


# A marked copy (`<stem>-marked[-N].pdf`, burn.py) belongs to its PDF and is
# never a document of its own.
MARKED = "-marked"
_MARKED_STEM = re.compile(r"\A(.+)-marked(?:-\d+)?\Z")


def marked_copy(path):
    """Is the file at `path` a marked copy of a PDF beside it?"""
    stem, ext = os.path.splitext(os.path.basename(path))
    m = _MARKED_STEM.match(stem)
    return bool(m) and ext.lower() == ".pdf" and os.path.isfile(
        os.path.join(os.path.dirname(path), m.group(1) + ".pdf"))


def _walk(root, skip=()):
    """Every stem in this subject that has a document's formats beside it, as
    `((rel, stem), {ext: path})`, in walk order."""
    found, order = {}, []
    for rel, name, path in _files(root, skip):
        if name.startswith("_"):
            continue
        stem, ext = os.path.splitext(name)
        if not stem or ext.lower() not in FORMATS:
            continue
        if stem.lower() in FURNITURE or marked_copy(path):
            continue
        key = (rel, stem)
        if key not in found:
            found[key] = {}
            order.append(key)
        found[key][ext.lower()] = path
    return [(k, found[k]) for k in order]


def _ident(rel, stem, taken):
    """A short, stable, URL-safe name for one document, derived from where it
    is so a restarted board hands out the same ids."""
    base = stem if rel in (".", "") else rel.replace(os.sep, "-") + "-" + stem
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:IDENT_MAX] or "document"
    out, n = slug, 1
    while out in taken:
        n += 1
        out = "%s-%d" % (slug[:IDENT_MAX - 4], n)
    return out


def _offered(formats, material=False):
    """The source and the PDF of one stem, or None if it is not a document.
    The one definition `_listing`, and so `stamp`, read. A material is any PDF
    under `materials/`, whatever its size."""
    src = formats.get(".tex") or formats.get(".md") or ""
    pdf = formats.get(".pdf") or ""
    if material:
        return ("", pdf) if pdf else None
    if not src and not pdf:
        return None
    # A PDF nobody here wrote the source of, and small enough to be a figure.
    if not src and _size(pdf) < MIN_PDF_BYTES:
        return None
    return src, pdf


def _record(root, rel, stem, formats, ident, group="legacy", art=None):
    """One document as the library draws it. `art` is its artifact, when it
    has a doc.json; then the title, type and status come from there."""
    if art:
        src = art["path"]
        pdf = formats.get(".pdf") or ""
        title = art["title"]
        kind = "deck" if art["type"] == "deck" else "paper"
    else:
        src, pdf = _offered(formats, group == "material")
        title, kind = _from_source(src, stem)
    where = "" if rel in (".", "") else rel.replace(os.sep, "/")
    built = _mtime(pdf)
    rec = {
        "id": ident,
        "group": group,
        "dir": where,
        "stem": stem,
        "title": title,
        "kind": kind,
        "formats": sorted(e.lstrip(".") for e in formats),
        "rel": os.path.relpath(pdf or src, root).replace(os.sep, "/"),
        # The source, not `rel` (which is the PDF on the glass): a revision
        # edits the file the document was built from.
        "source": (os.path.relpath(src, root).replace(os.sep, "/") if src else ""),
        "at": built or max([_mtime(p) for p in formats.values()] or [0]),
        "built": built,
        "size": _size(pdf or src),
        "pages": _pages(pdf),
        # Source newer than PDF.
        "stale": bool(src and pdf and _mtime(src) > built),
        "pdf": bool(pdf),
        # A `docs/<slug>/` artifact's feedback needs no stem in its name.
        "own": bool(art and art["own"]),
    }
    if art:
        rec.update({"artifact": art["rel"], "type": art["type"],
                    "status": artifacts.status(art["dir"]),
                    "asked_at": art["asked_at"], "sessions": art["sessions"]})
    rec["piece"] = group == "legacy" and _piece_of(where) is not None
    rec["notes"] = notes(root, rec)
    return rec


def _piece_of(where):
    """`(dir, stem)` of the whole a piece in `where` was cut from, or None:
    `paper1/parts/manuscript` is a piece of `paper1/manuscript`."""
    bits = where.split("/") if where else []
    for i in range(len(bits) - 1):
        if bits[i].lower() in PIECES:
            return "/".join(bits[:i]), bits[i + 1]
    return None


# One `pdfinfo` per document, paid once.
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


def _listing(root):
    """Every document, in library order, as `(group, id, rel, stem, formats,
    art)`. Stats, listings and doc.json reads only.

    Ids are handed out in walk order before reordering, so a legacy document
    and an artifact placed in place keep their ids (ink is keyed on them). A
    `docs/<slug>/` artifact is not walked; its id is its slug.
    """
    arts = artifacts.list(root)
    own = [a for a in arts if a["own"]]
    placed = {}
    for a in arts:
        if not a["own"] and a["path"]:
            src_rel = os.path.relpath(os.path.dirname(a["path"]), root)
            placed[(src_rel, os.path.splitext(os.path.basename(a["path"]))[0])] = a
    taken, walked = set(), []
    for (rel, stem), formats in _walk(root, skip=set(a["rel"] for a in own)):
        material = rel.replace(os.sep, "/").split("/")[0] == "materials"
        if not _offered(formats, material):
            continue
        ident = _ident(rel, stem, taken)
        taken.add(ident)
        art = placed.get((rel, stem))
        group = "material" if material else ("artifact" if art else "legacy")
        walked.append((group, ident, rel, stem, formats, art))
        if len(walked) >= MAX_DOCS:
            break
    out = []
    for a in own:
        ident, n = a["id"], 1
        while ident in taken:
            n += 1
            tail = "-%d" % n
            ident = a["id"][:IDENT_MAX - len(tail)] + tail
        taken.add(ident)
        stem = os.path.splitext(os.path.basename(a["path"]))[0]
        formats = {}
        for ext in FORMATS:
            p = os.path.join(a["dir"], stem + ext)
            if os.path.isfile(p):
                formats[ext] = p
        out.append(("artifact", ident, a["rel"], stem, formats, a))
    for group in ("artifact", "legacy", "material"):
        out += [w for w in walked if w[0] == group]
    return out


def _documents(root):
    out = []
    for group, ident, rel, stem, formats, art in _listing(root):
        out.append(_record(root, rel, stem, formats, ident, group, art))
    # Wholes before pieces inside the legacy group, each in file order.
    wholes = [d for d in out if not d["piece"]]
    for d in out:
        if d["piece"]:
            base, stem = _piece_of(d["dir"])
            d["whole"] = next((w["id"] for w in wholes
                               if w["dir"] == base and w["stem"] == stem), "")
    first = [d for d in out if d["group"] == "artifact"]
    legacy = [d for d in out if d["group"] == "legacy"]
    return (first + [d for d in legacy if not d["piece"]]
            + [d for d in legacy if d["piece"]]
            + [d for d in out if d["group"] == "material"])


def forget():
    """Drop every cache: documents, page counts, the drawer and the results.
    For a test, and for a job or a note that has just written a file."""
    _cache.clear()
    _PAGES.clear()
    _shown.clear()
    _made.clear()


# ---------------------------------------------------------------------------
# HAS ANYTHING MOVED? -- the cheap question, asked often
# ---------------------------------------------------------------------------
# A cheap stamp the library page polls, because `/library.json` walks, reads
# titles and runs pdfinfo. Stats only: no titles or notes, so filing a note
# never moves it. The source is in it so a failed rebuild still marks the row
# stale. Per document as well as overall, so only the moved document redraws.
def stamp(root):
    """Where every document is and when it last changed. Stats only."""
    docs, lines = {}, []
    for group, ident, rel, stem, formats, art in _listing(root):
        src, pdf = (art["path"], formats.get(".pdf") or "") if art else \
            _offered(formats, group == "material")
        held = [p for p in (src, pdf) if p and os.path.exists(p)]
        if art:
            held.append(os.path.join(art["dir"], artifacts.DOC_JSON))
        one = "|".join(
            "%s@%d:%d" % (os.path.relpath(p, root).replace(os.sep, "/"),
                          int(_mtime(p) * 1000), _size(p))
            for p in held)
        docs[ident] = hashlib.sha1(one.encode("utf-8")).hexdigest()[:12]
        lines.append(ident + " " + one)
    whole = hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:16]
    return {"ok": True, "stamp": whole, "documents": docs}


def find(root, ident_wanted):
    """The document with this id, or None. Matched against discovery."""
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None
    for doc in documents(root):
        if doc["id"] == wanted:
            return doc
    return None


def find_any(root, ident_wanted):
    """The document under either of its names (`find`, then `mark_idents`),
    or None. Matched against discovery, never a path."""
    doc = find(root, ident_wanted)
    if doc:
        return doc
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None
    for doc in documents(root):
        if wanted in mark_idents(root, doc):
            return doc
    return None


def path_of(root, doc, ext=".pdf"):
    """Where one format of one document is, or "". Built from the found
    document, so nothing from a browser touches the filesystem."""
    if not doc:
        return ""
    here = os.path.join(root, *([] if not doc["dir"] else doc["dir"].split("/")))
    target = os.path.join(here, doc["stem"] + ext)
    if fenced.refused(target) or not os.path.isfile(target):
        return ""
    return target


def pages(repo, ident_wanted, width=paper.PAGE_WIDTH):
    """Every page of one document, drawn and cached by `course/paper.py`."""
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
        _settle(repo, doc)
        try:
            wipe_delivered(repo, doc)
        except Exception:                                    # noqa: BLE001
            pass
        out["ink"] = ink(repo, doc)
        out["wiped"] = wiped(repo, doc)
        # The build on the glass, so a save records what marks were drawn on.
        out["build"] = {"digest": out.get("digest") or "",
                        "at": _mtime(target), "pages": out.get("n") or 0}
        out["rebuilt"] = drawn_on(repo, doc, out["build"]["digest"],
                                  out["ink"])["rebuilt"]
    return out


def when_built(at):
    """`28 Sep 21:40`: a build, named the way the reader says it."""
    if not at:
        return "an earlier"
    return time.strftime("%d %b %H:%M", time.localtime(at)).lstrip("0")


def drawn_on(repo, doc, current, ink_now=None):
    """Which build this document's marks were drawn on, against `current`.

    `current` is `paper._digest` of the PDF on disk now. Returns
    `{"digest", "rebuilt", "refuse"}`:

        digest    the build a marked copy is burned from -- `current`, or the
                  one older build every stamped mark was drawn on
        rebuilt   None when nothing was drawn on another build; otherwise
                  `{at, when, pages, copy, detail}` for the reader's flag
        refuse    "" or the sentence saying why no copy can be made

    A page with no stamp goes with whichever build is burned. An older build
    is burned only from its own cached rendering, because marks drawn on one
    build must not land on another's pages. Marks on two builds are refused.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    ink_now = ink(repo, doc) if ink_now is None else ink_now
    builds = lesson_notes.load_notes_builds(repo)
    older, on_current = {}, False
    for key in ink_now:
        b = builds.get(key)
        if not b:
            continue
        if b.get("digest") == current:
            on_current = True
            continue
        got = older.setdefault(b["digest"], {"at": b.get("at") or 0,
                                             "was": b.get("pages") or 0,
                                             "pages": []})
        page = writing.ann_doc_page(key)
        if page and page[1] not in got["pages"]:
            got["pages"].append(page[1])
    if not older:
        return {"digest": current, "rebuilt": None, "refuse": ""}
    digest = min(older, key=lambda d: older[d]["at"])
    first = older[digest]
    refuse = ""
    if len(older) > 1:
        refuse = ("These marks were drawn on %d different builds, so no one "
                  "rendering of the document is under all of them and a marked "
                  "copy cannot be made." % len(older))
    elif on_current:
        refuse = ("Some of these marks were drawn on the %s build and some on "
                  "this one, so no one rendering is under all of them and a "
                  "marked copy cannot be made." % when_built(first["at"]))
    elif not paper.cached(digest):
        refuse = ("The %s build these marks were drawn on is no longer in the "
                  "page cache, so a marked copy of it cannot be made."
                  % when_built(first["at"]))
    pages_on = sorted(p for o in older.values() for p in o["pages"])
    return {"digest": digest if not refuse else "", "refuse": refuse,
            "rebuilt": {"at": first["at"], "when": when_built(first["at"]),
                        "was": first["was"], "pages": pages_on,
                        "copy": not refuse, "detail": refuse}}


def ink(repo, doc):
    """The strokes already on this document's pages, `{key: strokes}`.

    Sent with the pages, because this page holds no live payload. Coordinates
    are fractions of the page box, read only by `annotate.js`. Read under both
    names the document has (`mark_idents`).
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
# Feedback files are dated and versioned, and tracked.
NOTE_RE = re.compile(r"^(?P<stem>.*?)(?P<day>\d{4}-\d{2}-\d{2})-v(?P<n>\d+)\.md$")


def _is_writeup(doc):
    """Is this a document the board made, in its own directory? There a note
    needs no stem in its name; in flat layouts it does."""
    if (doc or {}).get("own"):
        return True
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


# Bounded, because a looping turn writes a large file.
NOTE_BYTES = 200000


def note_text(root, doc, name_wanted):
    """One round of feedback on one document, as text, so the page can show
    what the turn's `## What was changed` said.

    A name out of `notes`, never a path: a browser's name is matched against
    the names found beside this document.
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
    """Where the next round of feedback on this document goes: in its own
    `feedback/` for a board-made document, else `<dir>/feedback/<stem>-...`
    where several documents share a directory."""
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
# Ink on a document page is feedback too: strokes saved against
# `doc/<ident>/p<n>` are read here as a complaint. A document has two idents
# (the drawer's filename slug and the library's), and both are asked.

def marked_pages(repo, strokes_of=None):
    """Every page of every document with ink on it, `{ident: {page: n}}`, `n`
    counting strokes. One pass over the drawer for the whole library, because
    per document it is thousands of reads. No page count is consulted: a
    missing `pdfinfo` must not lose ink. `strokes_of` is `load_notes`, for a
    caller that has read the drawer.
    """
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    if strokes_of is None:
        strokes_of = lesson_notes.load_notes(repo)
    out = {}
    for key, strokes in strokes_of.items():
        found = writing.ann_doc_page(key)
        n = len(strokes or []) if found else 0
        if not n:
            continue
        out.setdefault(found[0], {})[found[1]] = n
    return out


def mark_idents(root, doc):
    """Every annotation ident this one document could have been marked under."""
    out = [doc["id"]]
    target = path_of(root, doc, ".pdf")
    if target:
        drawer = drawer_ident(root, target)
        if drawer and drawer not in out:
            out.append(drawer)
    return out


def marks(repo, doc, index=None):
    """Every page of one document with ink on it, in page order:
    `[{page, ident, key, strokes, png}]`, `png` repository-relative, the
    picture a revision turn opens. `index` is a precomputed `marked_pages`.
    """
    from ..server.routes import writing               # local: avoids a cycle

    index = marked_pages(repo) if index is None else index
    if not index:
        return []
    out = []
    for ident in mark_idents(repo.root, doc):
        for page, strokes in (index.get(ident) or {}).items():
            key = "doc/%s/p%d" % (ident, page)
            # The filename comes from the one function that derives it, never
            # rebuilt here: security rests on that rule.
            png = writing.png_path(repo, key)
            out.append({"page": page, "ident": ident, "key": key,
                        "strokes": strokes,
                        "png": (os.path.relpath(png, repo.root).replace(os.sep, "/")
                                if os.path.isfile(png) else "")})
    out.sort(key=lambda m: (m["page"], m["ident"]))
    return out


# The brief beside a deck (`briefs.py`, which imports this module).
DECK_BRIEF = "_brief.md"


def from_sittings(root, doc):
    """Is this a deck with its brief beside it?"""
    where = (doc or {}).get("dir") or ""
    return bool(where) and os.path.isfile(
        os.path.join(root, *(where.split("/") + [DECK_BRIEF])))


def last_round_landed(root, doc):
    """Did the newest round of feedback on this document come back? Yes with
    no round, answers in its ledger, `## What was changed` under the note, or
    a PDF rebuilt after the note (`ledger.landed`)."""
    from . import ledger                              # local: avoids a cycle

    rounds = notes(root, doc)
    if not rounds:
        return True
    path = os.path.join(feedback_dir(root, doc), rounds[-1]["name"])
    if not os.path.isfile(path):
        return True
    return ledger.landed(root, doc, path)


def carried(repo, doc, found, sent=None):
    """The marks in `found` that the next note on `doc` carries: every mark,
    except on a deck made from sittings whose last round landed, where only
    ink no round delivered goes, because its slides renumber. A round that did
    not land sends everything again, so a retry is a tap.
    """
    if not found or not from_sittings(repo.root, doc) \
            or not last_round_landed(repo.root, doc):
        return list(found)
    from ..lesson import notes as lesson_notes        # local: avoids a cycle

    sent = lesson_notes.load_notes_sent(repo) if sent is None else sent
    return [m for m in found if not sent.get(m["key"])]


def wipe_delivered(repo, doc, sent=None):
    """Delete the ink a landed round delivered; return the keys that went.

    Spent marks would sit over changed (or renumbered) slides. Only pages a
    note carried lose their strokes (`strip`); ink drawn since is `sent:
    false` and stays. A round that has not landed keeps everything. A round's
    own crops and pictures are never wiped.
    """
    if not notes(repo.root, doc) or not last_round_landed(repo.root, doc):
        return []
    from . import ledger                              # local: avoids a cycle
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    # Every round keeps the pictures its requests point at before ink goes.
    ledger.keep_evidence(repo, doc)

    sent = lesson_notes.load_notes_sent(repo) if sent is None else sent
    wanted = set(mark_idents(repo.root, doc))
    filed = _filed_ink(repo, doc)
    if filed:
        sent = dict(sent)
        strokes_of = lesson_notes.load_notes(repo)
        builds = lesson_notes.load_notes_builds(repo)
        for key, (digest, count) in filed.items():
            # Ink a landed round filed and unchanged since counts as delivered
            # even without its `sent` flag; a new stroke changes the count.
            if not sent.get(key) and (builds.get(key) or {}).get("digest") == digest \
                    and len(strokes_of.get(key) or []) == count:
                sent[key] = True
    gone = []
    for key, was_sent in sent.items():
        found = writing.ann_doc_page(key)
        if not was_sent or not found or found[0] not in wanted:
            continue
        if strip(repo, key):
            gone.append(key)
    return gone


def strip(repo, key):
    """Take the ink off one page, strokes and picture. True if anything went.
    The strokes are buried (`writing.bury`), so a stale reader cannot save
    them back."""
    from ..server.routes import writing               # local: avoids a cycle

    import json as _json
    path = writing.ann_path(repo, key)
    changed = False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rec = _json.load(fh)
    except (OSError, ValueError):
        rec = None
    if isinstance(rec, dict):
        try:
            os.remove(path)
            changed = True
            writing.bury(repo, key, rec.get("strokes") or [])
        except OSError:
            pass
    try:
        os.remove(writing.png_path(repo, key))
        changed = True
    except OSError:
        pass
    return changed


def wiped(repo, doc, buried=None):
    """`{key: strokes}` that `strip` took off this document and a reader may
    still show; every reply handing ink out carries it, because `Annotate.load`
    never removes a mark. `buried` is a precomputed `buried_all`."""
    from ..server.routes import writing               # local: avoids a cycle

    buried = buried_all(repo) if buried is None else buried
    wanted = set(mark_idents(repo.root, doc))
    out = {}
    for key, strokes in buried.items():
        found = writing.ann_doc_page(key)
        if found and found[0] in wanted and strokes:
            out[key] = strokes
    return out


def buried_all(repo):
    """`{key: strokes}` for every page with buried strokes, one pass."""
    from ..server.routes import writing               # local: avoids a cycle

    from . import repo as course_repo                  # local: light

    out = {}
    for where, name in course_repo.ink_records(repo, ".gone"):
        try:
            with open(os.path.join(where, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        key = rec.get("card") if isinstance(rec, dict) else None
        if key and writing.ann_ok(str(key)) and course_repo.ink_dir(repo, key) == where:
            out[key] = writing.gone_of(repo, key)
    return out


def _filed_ink(repo, doc):
    """`{key: (drawn_on, strokes)}` for the ink every landed round filed: the
    page it was on, the build it was drawn on and how many strokes it had."""
    from . import ledger                              # local: avoids a cycle

    out = {}
    rs = ledger.rounds(repo.root, doc)
    for n, (_rec, path) in enumerate(rs):
        if not ledger.check(repo.root, doc, path, later=n < len(rs) - 1).get("landed"):
            continue
        per = {}
        for it in ledger.items_of(path):
            if it.get("kind") == "ink" and it.get("ann") and it.get("drawn_on"):
                was = per.get(it["ann"], (it["drawn_on"], 0))
                per[it["ann"]] = (was[0], was[1] + int(it.get("count") or 0))
        out.update(per)
    return out


def _handed_over(repo, found):
    """Record that these marks were delivered, so autosaved ink can be told
    apart from sent ink."""
    from ..server.routes import writing               # local: avoids a cycle

    import json as _json
    for mark in found:
        path = writing.ann_path(repo, mark["key"])
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


# `revise` corrects what the note points at and keeps structure and claims.
# `rework` may restructure and rewrite, and requires a sentence saying what
# the document is now for.
ASKS = ("revise", "rework")

# Short enough to refuse "make it better".
PURPOSE_LEAST = 25


def clean_ask(ask):
    """Which of the two asks this is. Anything unrecognised is a correction."""
    want = str(ask or "").strip().lower()
    return want if want in ASKS else "revise"


def write_note(repo, ident_wanted, text, page=0, ask="revise", purpose="",
               hand_over=True, merge=()):
    """One round of feedback on one document. Returns a record to paint.

    Marks count as saying something, so an empty textarea with ink is a note;
    which ink goes is `carried`'s. A round is a list of requests
    (`course/ledger.py`): each inked region, each typed paragraph, and each
    reopened earlier request under its own id; `merge` joins marks on one page
    into one request. The ledger beside the note is what the turn answers.

    `hand_over` False leaves recording delivery to the caller, once the
    revision was actually asked, so a failed ask sends the ink again. A
    rework is the same file and rounds, with its purpose as its own section.
    """
    from . import ledger                              # local: avoids a cycle

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
    reopen = ledger.reopened(root, doc)
    if ask == "revise" and not said and not found and not reopen:
        return {"ok": False, "error": "say what is wrong with it, or mark it up"}
    target = next_note(root, doc)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
    except OSError as exc:
        return {"ok": False, "error": "could not make %s: %s"
                                      % (os.path.dirname(target), exc)}
    name = os.path.basename(target)
    round_no = ledger.next_round(root, doc)
    items = ledger.number(ledger.split(repo, found, said, page=page, merge=merge),
                          round_no, name) + reopen
    led = None
    if items:
        whole = find(root, doc.get("whole") or "") if doc.get("piece") else None
        try:
            led = ledger.file_round(repo, doc, whole or doc, target, round_no, items,
                                    ask, path_of(root, doc, ".pdf"))
        except OSError:
            led = None
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
    if led:
        head.append("- round %d, %d request%s: `%s`"
                    % (round_no, len(items), "" if len(items) == 1 else "s",
                       os.path.relpath(ledger.ledger_path(target), root)
                       .replace(os.sep, "/")))
    # With a ledger the typed words are the requests below; written once.
    typed_below = bool(led) and any(i.get("kind") == "text" for i in items)
    head += ["", ("What they typed is below, under *The requests, by id*: one "
                  "request to a paragraph.") if typed_below else said or
             ("There is nothing wrong with it in particular. What it is for has "
              "changed." if ask == "rework" else
              "They wrote on it rather than typing. The marks are the feedback."
              if found else
              "Nothing new was typed or drawn. The requests below were reopened "
              "on an earlier round, and are why this round exists."),
             ""]
    if aim:
        head += ["## What this document is FOR now", "",
                 "THIS IS THE OVERHAUL'S BRIEF, and it outranks the document's "
                 "present shape. Restructure, cut, reorder and rewrite as this "
                 "requires.", "", aim, ""]
    if led:
        head += _requests(root, target, items)
    marked_copy = {}
    for it in items:
        if it.get("kind") == "ink" and it.get("marked"):
            marked_copy.setdefault(it["page"], os.path.relpath(
                os.path.join(ledger.round_dir(target), it["marked"]), root)
                .replace(os.sep, "/"))
    if found:
        head += ["## What they marked", "",
                 "Each line is one page of this document with their ink on it. "
                 "OPEN THE IMAGE: the marks are where the complaint is, and the "
                 "page number alone does not say what they point at.", ""]
        for mark in found:
            line = "- page %d, %d stroke%s" % (mark["page"], mark["strokes"],
                                               "" if mark["strokes"] == 1 else "s")
            # The round's own copy, because the live picture is wiped once
            # the round lands.
            pic = marked_copy.get(mark["page"]) or mark["png"]
            line += " -- `%s`" % pic if pic else " -- no image was "\
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
        ledger.carry(root, doc, reopen, name)
    forget()
    return {"ok": True, "document": doc["id"], "path": target,
            "rel": os.path.relpath(target, root).replace(os.sep, "/"),
            "title": doc["title"],
            "ask": ask, "purpose": aim,
            "marks": len(found), "keys": [m["key"] for m in found],
            "items": len(items) if led else 0,
            "ids": [i["id"] for i in items] if led else [],
            "ledger": (os.path.relpath(ledger.ledger_path(target), root)
                       .replace(os.sep, "/") if led else ""),
            "carry": reopen, "note": name}


def _requests(root, note_path, items):
    """The note's list of this round's requests, by id, as the ledger holds
    them."""
    from . import ledger                              # local: avoids a cycle

    out = ["## The requests, by id", "",
           "Every request below has an id. The revision answers each one in the "
           "ledger named above, and the board writes the account of what was "
           "changed from those answers.", ""]
    for it in items:
        if it["kind"] == "ink":
            head = "### %s -- ink on page %d (%d stroke%s)" % (
                it["id"], it["page"], it.get("count") or 0,
                "" if it.get("count") == 1 else "s")
        elif it["kind"] == "reopened":
            head = "### %s -- REOPENED from %s" % (it["id"], it.get("from") or "")
        else:
            head = "### %s -- %s" % (it["id"], ("about page %d" % it["page"])
                                     if it.get("page") else "in words")
        out += [head, ""]
        crop = ledger._crop_path(note_path, it)
        if crop:
            out += ["The ink, cropped: `%s`" % os.path.relpath(crop, root)
                    .replace(os.sep, "/"), ""]
        if it["kind"] == "reopened":
            out += ["Not done yet, because: %s" % (it.get("why") or ""), ""]
            if it.get("previous"):
                out += ["Last answered: %s" % it["previous"], ""]
        if it.get("text"):
            out += [it["text"], ""]
    return out


def hand_over(repo, keys):
    """Record the marks under these keys as delivered. `write_note`'s `keys`,
    once the round they went with has been asked for."""
    _handed_over(repo, [{"key": k} for k in keys or [] if isinstance(k, str)])


def _settle(repo, doc):
    """Validate the rounds' answers where the wipe runs; a failure goes to the
    board's log, because an unheard failure is a silent round."""
    from . import ledger                              # local: avoids a cycle

    try:
        ledger.settle(repo, doc)
    except Exception as exc:                                 # noqa: BLE001
        import sys
        print("ledger: could not settle %s: %s" % (doc.get("id"), exc),
              file=sys.stderr)


def status(repo):
    """What the library page draws, and nothing more."""
    from . import ledger                              # local: avoids a cycle

    root = repo.root
    try:
        found = documents(root)
    except Exception:                                        # noqa: BLE001
        found = []
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle
    try:
        index = marked_pages(repo)
    except Exception:                                        # noqa: BLE001
        index = {}
    try:
        sent = lesson_notes.load_notes_sent(repo)
    except Exception:                                        # noqa: BLE001
        sent = {}
    buried = None
    for doc in found:
        doc["iso"] = (time.strftime("%Y-%m-%d", time.localtime(doc["at"]))
                      if doc["at"] else "")
        _settle(repo, doc)
        # What the rounds asked, and how much is still open.
        try:
            doc["ledger"] = ledger.summary(root, doc)
        except Exception:                                    # noqa: BLE001
            doc["ledger"] = None
        # Spent ink goes first, so the counts below are of what remains.
        went = []
        try:
            went = wipe_delivered(repo, doc, sent)
            for key in went:
                sent.pop(key, None)
                got = writing.ann_doc_page(key)
                if got and got[0] in index:
                    index[got[0]].pop(got[1], None)
        except Exception:                                    # noqa: BLE001
            pass
        # Ink on it, so the page can say marks go with the note.
        try:
            ink = marks(repo, doc, index=index)
        except Exception:                                    # noqa: BLE001
            ink = []
        # What a note would carry, via `carried` so the two cannot disagree.
        try:
            waiting = len(carried(repo, doc, ink, sent))
        except Exception:                                    # noqa: BLE001
            waiting = len(ink)
        doc["marks"] = {"pages": len(ink),
                        "strokes": sum(m["strokes"] for m in ink),
                        "waiting": waiting}
        # What was taken off, read after the wipe, so an open reader drops it.
        try:
            if buried is None or went:
                buried = buried_all(repo)
            doc["wiped"] = wiped(repo, doc, buried)
        except Exception:                                    # noqa: BLE001
            doc["wiped"] = {}
    found_subject = subjects.find(root) if root else None
    return {"workspace": subjects.identify(root), "documents": found,
            "subject": (found_subject or {}).get("id") or "",
            "writeups": WRITEUPS}


# ---------------------------------------------------------------------------
# THE DRAWER -- a page of a PDF in a card
# ---------------------------------------------------------------------------
# A page of a PDF in a card. A filter of the walk with a card's limits, plus
# what the README points at. Ids are the filename slug; board ink is keyed on
# them (`mark_idents`).

# How deep below the subject a drawer PDF may sit.
DRAWER_DEPTH = 3

# A drawer is not a file manager.
DRAWER_MAX = 24

# A `.pdf` path the subject's README names.
POINTER = re.compile(r"[~\w./-]+\.pdf\b")

_shown = {}


def _big(path):
    return _size(path) >= MIN_PDF_BYTES


def _ours(path):
    """Neither a reference library nor fenced, asked of the whole path,
    because the README reaches files the walk never pruned to."""
    norm = os.path.normpath(path)
    if any(p.lower() in NOT_OURS for p in norm.split(os.sep)):
        return False
    return not fenced.in_fence(norm.replace(os.sep, "/"))


def _drawer_walked(root):
    """The walk's PDFs a card may show: shallow enough, big enough, ours."""
    return [path for rel, name, path in _files(root)
            if _depth(rel) <= DRAWER_DEPTH and name.lower().endswith(".pdf")
            and _big(path) and _ours(path) and not marked_copy(path)]


def _pointed_at(root):
    """Every PDF the subject's README names and can reach, in README order.

    Bounded to the subject, its parent, the Atlas root and
    `paths.outside_tree()`, because a path from a file is untrusted. A bare
    filename is looked for beside the decks already found.
    """
    try:
        with open(os.path.join(root, "README.md"), "r", encoding="utf-8") as fh:
            text = fh.read(200000)
    except OSError:
        return []
    root = os.path.realpath(root)
    parent = os.path.dirname(root)
    base = subjects.root()

    def keep(target):
        if not os.path.isfile(target) or not _big(target) or not _ours(target):
            return False
        return paths.within(target, root, base, *paths.outside_tree())

    named = [m.group(0) for m in POINTER.finditer(text)]
    out, seen, where = [], set(), [root, parent, base]

    for rel in named:
        if not os.path.dirname(rel.lstrip("~/")):
            continue                      # a bare name; the second pass has it
        tries = ([os.path.expanduser(rel)] if rel.startswith("~")
                 else [os.path.join(root, rel), os.path.join(parent, rel),
                       os.path.join(base, rel)])
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


def drawer(root):
    """The PDFs a card can show a page of, README-named first, then walk order,
    as `{id, name, rel, at, size}`. Remembered for `CACHE_SECONDS`."""
    key = os.path.realpath(root)
    hit = _shown.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    got = _drawer(key)
    _shown[key] = (time.time(), got)
    return got


def _drawer(root):
    seen, out = set(), []
    for path in _pointed_at(root) + _drawer_walked(root):
        key = os.path.realpath(path)
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": drawer_ident(root, key), "name": _pretty(key),
                    "rel": _drawer_rel(root, key), "at": _mtime(key),
                    "size": _size(key)})
        if len(out) >= DRAWER_MAX:
            break
    return out


def _drawer_rel(root, path):
    """The PDF's path as a person would write it."""
    root = os.path.realpath(root)
    if path.startswith(root + os.sep):
        return os.path.relpath(path, root)
    home = os.path.realpath(os.path.expanduser("~"))
    if path.startswith(home + os.sep):
        return "~/" + os.path.relpath(path, home)
    return path


def drawer_ident(root, path):
    """The drawer's id for one PDF: the slug of its filename, derived and never
    stored, so a restarted board hands out the same ids."""
    stem = re.sub(r"[^a-z0-9]+", "-", _pretty(path).lower()).strip("-")
    return (stem or "doc")[:40]


def drawer_find(root, ident_wanted):
    """The drawer PDF with this id, as `(path, name)`, or `(None, None)`.
    Matched against `drawer`, and the fence asked once more, because this
    turns a browser's name into a file the rasteriser opens."""
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    for doc in drawer(root):
        if doc["id"] == wanted:
            target = os.path.realpath(os.path.expanduser(doc["rel"])
                                      if doc["rel"].startswith("~")
                                      else os.path.join(root, doc["rel"]))
            if not _ours(target):
                return None, None
            return (target, doc["name"]) if os.path.isfile(target) else (None, None)
    return None, None


# ---------------------------------------------------------------------------
# every PDF the board's reader opens as `doc/<id>`
# ---------------------------------------------------------------------------
# An upload's id is `_ident` on `uploads/<name>`, the id `sessions.ink_ident`
# keys its ink on, so `board file` can re-key it (`ident_map`).
UPLOADS = "uploads"


def uploads(repo):
    """The PDFs in the session's `uploads/`, by name: `[{id, name, path,
    size, at}]`. Dot files and a part still arriving are not listed."""
    where = getattr(repo, "uploads", None)
    try:
        names = sorted(os.listdir(where)) if where else []
    except OSError:
        names = []
    taken, out = set(), []
    for name in names:
        path = os.path.join(where, name)
        if name.startswith(".") or not name.lower().endswith(".pdf") \
                or not os.path.isfile(path):
            continue
        ident = _ident(UPLOADS, os.path.splitext(name)[0], taken)
        taken.add(ident)
        out.append({"id": ident, "name": name, "path": path,
                    "size": _size(path), "at": _mtime(path)})
    return out


def upload_find(repo, ident_wanted):
    """The upload with this id, as a path, or ""."""
    wanted = str(ident_wanted or "").strip().lower()
    for up in uploads(repo) if wanted.startswith(UPLOADS + "-") else ():
        if up["id"] == wanted:
            return up["path"]
    return ""


def readable(repo, ident_wanted):
    """`(path, name)` of the PDF the reader opens as `doc/<id>`, or `(None,
    None)`: the session's upload of that id, else the drawer's PDF, else any
    library document with a PDF -- a material among them. Matched against what
    was found, never joined onto a path."""
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    up = upload_find(repo, wanted)
    if up:
        return up, _pretty(up)
    target, name = drawer_find(repo.root, wanted)
    if target:
        return target, name
    # The Atlas root is no subject: its walk would be every subject's.
    if os.path.isfile(os.path.join(repo.root, "board", "bin", "board")):
        return None, None
    doc = find(repo.root, wanted)
    pdf = path_of(repo.root, doc, ".pdf") if doc else ""
    if pdf and _ours(pdf):
        return pdf, _pretty(pdf)
    return None, None


def ident_map(root):
    """`{real path: library id}` for every file of every document the library
    lists, stats only (`_listing`): what `board file` re-keys ink to, and the
    id a material's row opens in the reader."""
    out = {}
    for _group, ident, _rel, _stem, formats, _art in _listing(root):
        for p in formats.values():
            out.setdefault(os.path.realpath(p), ident)
    return out


def drawer_pages(repo, ident_wanted, width=paper.PAGE_WIDTH):
    """Every page of one PDF the reader opens as `doc/<id>` (`readable`),
    drawn and cached by `paper.pages_of`."""
    target, name = readable(repo, ident_wanted)
    if not target:
        return {"ok": False, "why": "none",
                "detail": "This course does not offer a document by that name."}
    return paper.pages_of(repo, target, name + ".pdf", "reading", width)


def drawer_status(repo):
    """The drawer as the subject payload carries it, or None when empty, so
    the board does not offer the group."""
    try:
        found = drawer(repo.root)
    except Exception:                                        # noqa: BLE001
        return None
    if not found:
        return None
    for doc in found:
        doc["iso"] = time.strftime("%Y-%m-%d", time.localtime(doc["at"])) \
            if doc["at"] else ""
    return {"documents": found}


# ---------------------------------------------------------------------------
# RESULTS -- what a pipeline produced
# ---------------------------------------------------------------------------
# A second tree, entered only through the allowlist `LOOK_IN`. One walk
# builds an index by id; the figures view is its newest `MAX_FIGURES`
# pictures. `/figure/` is compiled TikZ; `/result/<id>` is a pipeline's
# picture, never cached by `sw.js` because jobs rewrite it in place.

# Where to look, and nowhere else, in the order a person would look.
LOOK_IN = fenced.RESULT_DIRS

# What a figure is: raster only. Vector pictures are `/figure/`'s.
FIGURE_SUFFIXES = (".png", ".jpg", ".jpeg")

# A 300-byte PNG is an axis and no data -- a plot that failed, or a spacer.
FIGURE_MIN_BYTES = 1000

# The figures view: what a card's briefing and drawer are offered.
MAX_FIGURES = 24

# Below a result directory; deeper is an intermediate.
RESULT_DEPTH = 3

# A stop on the walk itself, whatever the tree contains.
MAX_SEEN = 5000

# What a table is. Read, never executed: `.json` is loaded to be re-printed.
TABLES = (".csv", ".json", ".md", ".txt")

# An empty file is not a table.
MIN_TABLE_BYTES = 1

# How many result directories the results page is offered, and rows in one.
MAX_GROUPS = 120
MAX_IN_GROUP = 60

# A table read back for a page: rows read to the cap and stopped, the rest
# counted up to `MAX_SCAN`; a text table bounded in bytes and characters.
MAX_ROWS = 300
MAX_COLS = 40
MAX_CELL = 200
MAX_SCAN = 200000
MAX_TEXT_BYTES = 2000000
MAX_TEXT_CHARS = 200000

# A result id: long enough for a real path's slug, ended by a digest of the
# path so a trimmed id stays unique.
RESULT_ID_MAX = 80
RESULT_STAMP = 8

_made = {}


def _result_where(rel):
    """The directory a result sits in, below its result directory. A pipeline
    writes `propensity_by_arm.png` once per contrast; this tells them apart."""
    parts = rel.replace("\\", "/").split("/")[:-1]
    return "/".join(parts[1:]) if len(parts) > 1 else "/".join(parts)


def result_ident(rel):
    """A stable, unique, URL-safe id for one result: the slug of its path
    trimmed from the front, plus a digest of the path, so the id does not
    depend on what else was found."""
    rel = rel.replace("\\", "/")
    stamp = hashlib.sha1(rel.encode("utf-8", "replace")).hexdigest()[:RESULT_STAMP]
    parts = os.path.splitext(rel)[0].split("/")
    said = "/".join(parts[1:]) if len(parts) > 1 else rel
    out = re.sub(r"[^a-z0-9]+", "-", said.lower()).strip("-")
    out = out[-(RESULT_ID_MAX - RESULT_STAMP - 1):].strip("-")
    return "%s-%s" % (out, stamp) if out else "figure-%s" % stamp


def _result_tops(root):
    """`(name, directory)` for each result directory here, in `LOOK_IN` order.
    `exports/results/` is walked as `results/`: a figure the cluster exported
    keeps the path and the id it has there, and is not offered twice."""
    out = []
    for name in LOOK_IN:
        if fenced.refused(name):
            continue
        tops = [os.path.join(root, name)]
        if name == "results":
            tops.append(os.path.join(root, paths.EXPORTS, name))
        out.extend((name, t) for t in tops if os.path.isdir(t))
    return out


def _result_files(root):
    """`(rel, mtime, size)` for every figure and table under the result
    directories. The allowlist picks the trees, `fenced.refused` the
    directories inside them, and `MAX_SEEN` stops the walk regardless."""
    found, seen, had = [], 0, set()
    root = os.path.realpath(root)
    for name, top in _result_tops(root):
        for here, dirs, files in os.walk(top):
            rel_dir = os.path.relpath(here, top)
            if _depth(rel_dir) >= RESULT_DEPTH:
                dirs[:] = []
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and not fenced.refused(d))
            for f in sorted(files):
                seen += 1
                if seen > MAX_SEEN:
                    return found
                if f.startswith(".") or not f.lower().endswith(FIGURE_SUFFIXES + TABLES):
                    continue
                path = os.path.join(here, f)
                rel = os.path.join(name, os.path.relpath(path, top))
                if fenced.refused(rel) or rel in had:
                    continue
                had.add(rel)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size < MIN_TABLE_BYTES:
                    continue
                found.append((rel.replace(os.sep, "/"), st.st_mtime, st.st_size))
    return found


def _result_record(rel, at, size):
    ext = os.path.splitext(rel)[1].lower()
    return {
        "id": result_ident(rel),
        "name": _pretty(rel, "figure"),
        "where": _result_where(rel),
        "rel": rel,
        "at": at,
        "size": size,
        "kind": "figure" if ext in FIGURE_SUFFIXES else "table",
        "format": ext.lstrip("."),
        "iso": time.strftime("%Y-%m-%d", time.localtime(at)) if at else "",
        # The filename as it stands, because a job's card names it.
        "file": os.path.basename(rel),
    }


def _produce(root):
    """`(index, page)`: every result by id, newest first, and the results page
    -- groups by directory, each capped and saying what it dropped."""
    rows = sorted(_result_files(root), key=lambda r: (-r[1], r[0]))
    index, groups, order = {}, {}, []
    figs = tabs = 0
    for rel, at, size in rows:
        rec = _result_record(rel, at, size)
        pic = rec["kind"] == "figure"
        # The size floor is per kind.
        if pic and size < FIGURE_MIN_BYTES:
            continue
        if rec["id"] in index:
            continue              # a digest collision: dropped, never aliased
        index[rec["id"]] = rec
        where = rec["where"]
        if where not in groups:
            groups[where] = []
            order.append(where)
        groups[where].append(rec)
        figs += 1 if pic else 0
        tabs += 0 if pic else 1

    out = []
    for where in order[:MAX_GROUPS]:
        rows_here = groups[where]
        # Groups newest first; inside one, figures then tables by name.
        kept = sorted(rows_here, key=lambda r: (r["kind"] != "figure",
                                                r["name"]))[:MAX_IN_GROUP]
        out.append({
            "where": where or "results",
            "at": max(r["at"] for r in rows_here),
            "iso": max(rows_here, key=lambda r: r["at"])["iso"],
            "figures": [_public(r) for r in kept if r["kind"] == "figure"],
            "tables": [_public(r) for r in kept if r["kind"] == "table"],
            "more": max(0, len(rows_here) - len(kept)),
        })
    return index, {"groups": out, "more": max(0, len(order) - MAX_GROUPS),
                   "figures": figs, "tables": tabs}


def _public(rec):
    """A result as a page may see it: never with its path."""
    one = dict(rec)
    one.pop("rel", None)
    return one


def _results(root):
    key = os.path.realpath(root)
    hit = _made.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        got = _produce(key)
    except OSError:
        got = ({}, {"groups": [], "more": 0, "figures": 0, "tables": 0})
    _made[key] = (time.time(), got)
    return got


def result_index(root):
    """Every result this subject has, by id, newest first."""
    return _results(root)[0]


def produced(root):
    """What the library's results page draws: groups, and what was left off."""
    return _results(root)[1]


FIGURE_KEYS = ("id", "name", "where", "rel", "at", "size")


def figures(root):
    """THE FIGURES VIEW, a filter of the index: the newest `MAX_FIGURES`
    pictures, as `{id, name, where, rel, at, size}`."""
    out = []
    for rec in result_index(root).values():
        if rec["kind"] != "figure":
            continue
        out.append(dict((k, rec[k]) for k in FIGURE_KEYS))
        if len(out) >= MAX_FIGURES:
            break
    return out


def figures_status(repo):
    """The figures view as the subject payload carries it, without paths, or
    None for a subject with no figures."""
    try:
        found = figures(repo.root)
    except Exception:                                        # noqa: BLE001
        return None
    if not found:
        return None
    out = []
    for fig in found:
        one = _public(fig)
        one["iso"] = time.strftime("%Y-%m-%d", time.localtime(fig["at"])) \
            if fig["at"] else ""
        out.append(one)
    return {"figures": out}


def _result_path(root, ident_wanted, kind):
    """`(path, label)` of the result of this kind with this id, against the
    whole index rather than the figures view, or `(None, None)`."""
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    root = os.path.realpath(root)
    rec = result_index(root).get(wanted)
    if not rec or rec["kind"] != kind:
        return None, None
    if fenced.refused(rec["rel"]):
        return None, None
    target = os.path.realpath(paths.present(root, rec["rel"]) or
                              os.path.join(root, rec["rel"]))
    if not target.startswith(root + os.sep) or not os.path.isfile(target):
        return None, None
    label = rec["name"]
    if rec["where"]:
        label = "%s — %s" % (label, rec["where"])
    return target, label


def find_result(root, ident_wanted):
    """The figure with this id, as `(path, label)`, or `(None, None)`: what
    `/result/<id>` serves. An id, never a path."""
    return _result_path(root, ident_wanted, "figure")


# A card's image whose source is `/result/` and then anything up to the closing
# parenthesis. Which of those are paths is decided by `embed_result_ids`.
EMBED_SRC_RE = re.compile(r"(!\[[^\]]*\]\(\s*)/result/([^)\s]+)(\s*\))")


def embed_result_ids(root, text):
    """A card's text with every `/result/<path>` image rewritten to its id.
    The path is looked up among the indexed figures, never joined; a miss is
    left alone and 404s."""
    text = text or ""
    if "/result/" not in text:
        return text
    by_rel = []

    def sub(m):
        src = unquote(m.group(2))
        if "/" not in src and "." not in src:
            return m.group(0)                 # already an id
        if not by_rel:
            try:
                by_rel.append(dict((rec["rel"], rid)
                                   for rid, rec in result_index(root).items()
                                   if rec.get("kind") == "figure"))
            except Exception:                                # noqa: BLE001
                by_rel.append({})
        rel = src[2:] if src.startswith("./") else src
        rid = by_rel[0].get(rel)
        return m.group(1) + "/result/" + rid + m.group(3) if rid else m.group(0)

    return EMBED_SRC_RE.sub(sub, text)


def browse_results(repo):
    """The results page's whole payload, or a sentence saying why it is empty:
    where it looked, and which fenced directories it would not enter."""
    root = repo.root
    try:
        got = produced(root)
    except Exception:                                        # noqa: BLE001
        got = {"groups": [], "more": 0, "figures": 0, "tables": 0}
    out = dict(got)
    out["ok"] = True
    out["workspace"] = subjects.identify(root)
    real = os.path.realpath(root)
    out["looked"] = [os.path.relpath(t, real) for _n, t in _result_tops(real)]
    out["fenced"] = list(fenced.holds(root))
    if not out["groups"]:
        out["why"] = _no_results(out)
    return out


def _no_results(out):
    """Why the results page is empty: where it looked, then what it refused."""
    if not out["looked"]:
        said = ("This workspace has no results directory. A job that writes "
                "one into %s appears here, with no registration of any kind."
                % ", ".join("`%s/`" % n for n in LOOK_IN))
    else:
        said = ("There is a %s directory here, and nothing in it yet that this "
                "board can show: a figure has to be a %s of at least %d bytes, "
                "and a table one of %s."
                % (", ".join("`%s/`" % n for n in out["looked"]),
                   " or ".join(FIGURE_SUFFIXES), FIGURE_MIN_BYTES,
                   " or ".join(TABLES)))
    if out["fenced"]:
        said += (" %s also holds %s. Nothing on this board looks inside it -- "
                 "it is session content, and the refusal is by name in "
                 "`tutorboard/fenced.py` -- so nothing in there is listed here "
                 "or anywhere else."
                 % (out["workspace"],
                    ", ".join("`%s/`" % n for n in out["fenced"])))
    return said


def result_table(root, ident_wanted):
    """One table, read back as rows (CSV) or text, for a page that cannot open
    a file. An id, never a path; a miss is a miss."""
    target, label = _result_path(root, ident_wanted, "table")
    if not target:
        return {"ok": False, "why": "none",
                "detail": "This workspace has no result by that name."}
    rec = result_index(os.path.realpath(root)).get(
        str(ident_wanted or "").strip().lower()) or {}
    out = {"ok": True, "id": rec.get("id") or "", "label": label,
           "name": rec.get("name") or "", "where": rec.get("where") or "",
           "file": rec.get("file") or "", "format": rec.get("format") or "",
           "size": rec.get("size") or 0, "iso": rec.get("iso") or ""}
    try:
        if out["format"] == "csv":
            out.update(_table_rows(target))
        else:
            out.update(_table_text(target))
    except (OSError, UnicodeError, ValueError) as exc:
        return {"ok": False, "why": "unreadable",
                "detail": "%s could not be read: %s" % (out["file"], exc)}
    return out


def _table_rows(path):
    """The head of a CSV as columns and rows, streamed: the rest is counted, up
    to `MAX_SCAN`, past which the page says *at least*."""
    columns, rows, more, capped = [], [], 0, False
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        for n, row in enumerate(csv.reader(fh)):
            if n == 0:
                columns = [str(c)[:MAX_CELL] for c in row[:MAX_COLS]]
                continue
            if len(rows) >= MAX_ROWS:
                more += 1
                if more >= MAX_SCAN:
                    capped = True
                    break
                continue
            rows.append([str(c)[:MAX_CELL] for c in row[:MAX_COLS]])
    return {"shape": "rows", "columns": columns, "rows": rows,
            "more": more, "capped": capped}


def _table_text(path):
    """A JSON, markdown or plain-text table, as text. Bounded twice."""
    size = os.path.getsize(path)
    if size > MAX_TEXT_BYTES:
        return {"shape": "text", "text": "", "more": 0,
                "why": "big",
                "detail": ("This file is %.1f MB, which is too much to put on "
                           "a page. It is at the path the row shows."
                           % (size / 1000000.0))}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        said = fh.read(MAX_TEXT_CHARS + 1)
    more = max(0, len(said) - MAX_TEXT_CHARS)
    said = said[:MAX_TEXT_CHARS]
    if path.lower().endswith(".json") and not more:
        # Re-printed, never acted on: `json.dumps` of what `json.loads` read.
        try:
            said = json.dumps(json.loads(said), indent=2, sort_keys=False)
        except ValueError:
            pass
    return {"shape": "text", "text": said, "more": more}
