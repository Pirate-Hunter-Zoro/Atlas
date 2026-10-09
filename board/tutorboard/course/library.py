"""library.py -- one inventory of a subject's documents and results.

THREE VIEWS, AND EACH IS A FILTER, NOT A WALK OF ITS OWN:

    documents   everything the subject has WRITTEN, grouped by stem (below)
    drawer      the PDFs a card can show a page of: what the README points at,
                then every PDF of the walk at least `MIN_PDF_BYTES` big and no
                deeper than `DRAWER_DEPTH`, at most `DRAWER_MAX` of them
    results     what a pipeline PRODUCED under the allowlist `LOOK_IN`: an
                index by id, the library's results page, and the figures view
                -- the newest `MAX_FIGURES` pictures of that index

A session's `uploads/` PDFs are readable too (`uploads`), and `readable` is
what the board's reader opens as `doc/<id>`: an upload, a drawer PDF, or any
document with a PDF, a material among them.

`documents` and `drawer` filter one walk of the subject, `_files`. Results are
a second tree, walked by `_result_files`, because `IGNORE` prunes `results/`
from the first and the allowlist is the only way into it.

A DOCUMENT IS A STEM IN A DIRECTORY, in however many formats it has.
`paper.md` + `paper.pdf` + `paper.docx` is one document. Nothing is declared:

    title   `\\title{...}` in a `.tex`, the first `# ` in a `.md`, and the
            filename through `_pretty` when a source says neither
    kind    `\\documentclass[...]{beamer}` is a deck; anything else is a paper
    stale   arithmetic -- the source's modification time against the PDF's

THREE GROUPS of documents, in this order. ARTIFACTS: a directory with a
doc.json (`tutorboard/artifacts.py`) -- new ones at `docs/<slug>/`, whose id is
the slug, and ones placed in an existing tree, which keep the id the walk gives
them. LEGACY documents, found by the walk, ids unchanged: ink is keyed on them.
MATERIALS: any PDF under `materials/`, put there to be read.

AN ID, NEVER A PATH. What arrives from a browser is compared against what
discovery found, and a miss is a miss. The fence (`fenced.refused`) is asked of
every directory pruned and every whole path offered, and `NOT_OURS` keeps a
reference library of other people's papers out.

Standard library only, like everything else.
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

# What a document can be written in, and what it can be built into. A stem with
# neither a source nor a PDF is not a document, whatever else is beside it.
SOURCE = (".tex", ".md")
BUILT = (".pdf", ".docx")
FORMATS = SOURCE + BUILT

# Where a document this board makes goes, one directory per document.
WRITEUPS = "writeups"

# Directories the walk never enters: the board's own working directory, build
# output, dependencies and data. NOT THE FENCE -- `fenced.NEVER` is, and it is
# asked on the whole path as well as here.
IGNORE = {"live", "node_modules", "__pycache__", "build", "dist", "target",
          "venv", ".venv", "env", "site-packages", "vendor", "results",
          "data", "test_data", "archive"}

# What a reference library is called. These are papers by other people; a
# walkthrough of your own pipeline is not in one.
NOT_OURS = ("references", "reference", "library", "papers", "reading",
            "literature", "formats", "feedback")

# How deep the walk goes. A manuscript directory is two levels inside a subject
# and its parts are a third. Not unbounded: a walk of a repository is the one
# thing here that costs more than a stat.
MAX_DEPTH = 4

# A library is allowed to be long. It is not allowed to be a file manager, and a
# subject with more than this has something other than documents in it.
MAX_DOCS = 120

# A PDF with no source beside it earns its place on size: a figure exported as
# a one-page PDF is not a document. The drawer's floor for every PDF.
MIN_PDF_BYTES = 20000

# A repository's furniture, which is not something it wrote up. Matched on the
# stem, so `README.md` in every directory is skipped and `readme_of_the_grid.md`
# is not.
FURNITURE = {"readme", "handoff", "license", "licence", "notice", "changelog",
             "contributing", "todo", "ai_instructions", "teaching", "claude",
             "agents", "direction", "index"}

# HOW LONG AN ID MAY BE: `writing.ANN_DOC` anchors a mark on a page of a
# document to `doc/<ident>/p<n>` and allows forty characters.
IDENT_MAX = 40

# A PIECE OF A DOCUMENT. `paper1-trd-prediction/parts/manuscript/` holds that
# manuscript's own sections, one file each. They are offered, tagged `piece`,
# after every whole document, and each names the `whole` it was cut from: a
# correction goes to the whole, because an edit made to a piece is lost on the
# next cut.
PIECES = ("parts", "sections")

# Every view is rebuilt on demand and the hub asks for the drawer and the
# figures on every subject payload. A file appears when a job or a build
# finishes, which is not on a quarter-second boundary.
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
# the walk
# ---------------------------------------------------------------------------
def _pretty(path, fallback="document"):
    """What to call a file in a list: its name, unpunctuated.

    `stage1_pipeline_walkthrough.pdf` is `stage1 pipeline walkthrough`, which is
    what its author calls it out loud.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[_-]+", " ", stem).strip() or fallback


def _depth(rel):
    return 0 if rel in (".", "") else rel.count(os.sep) + 1


def _files(root, skip=()):
    """`(rel, name, path)` for every file the subject may offer, in walk order.

    THE ONE WALK of a subject's own tree: `documents` groups it into stems and
    the drawer filters it. Nearest the top first, directories and files sorted.
    Hidden names, `IGNORE`, `NOT_OURS` and fenced names are never entered, and
    nothing below `MAX_DEPTH` is. `skip` holds directories, relative to `root`,
    never entered either: the artifacts at `docs/<slug>/`, listed from their
    doc.json.
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
            # The pruning above sees only the directories descended through.
            # The fence is asked of the whole path too, at any depth.
            if fenced.refused(path):
                continue
            yield rel, name, path


# A MARKED COPY sits beside the PDF it was burned from, `<stem>-marked.pdf`,
# then `-marked-2.pdf`, ... (`burn.py`). It belongs to that document, so no
# walk offers it as a document of its own.
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


def _offered(formats, material=False):
    """The source and the PDF of one stem, or None if it is not a document.

    WHAT MAKES A STEM A DOCUMENT, IN ONE PLACE. `_listing` hands out ids from
    this, and both `_documents` and `stamp` read `_listing`, so an id the stamp
    knows is always one the list offers.

    A MATERIAL is any PDF under `materials/`, whatever its size: it was put
    there to be read.
    """
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
        # THE SOURCE, SEPARATELY, AND IT IS NOT `rel`. `rel` is what to put on the
        # glass, which is the PDF wherever there is one -- and a revision handed that
        # is a revision asked to edit a rendering. Whatever revises this document
        # edits the file it was built from.
        "source": (os.path.relpath(src, root).replace(os.sep, "/") if src else ""),
        "at": built or max([_mtime(p) for p in formats.values()] or [0]),
        "built": built,
        "size": _size(pdf or src),
        "pages": _pages(pdf),
        # Arithmetic, not a record: the source is newer than the PDF, so what is
        # on the glass is not what the file says any more.
        "stale": bool(src and pdf and _mtime(src) > built),
        "pdf": bool(pdf),
        # A new artifact's own directory, `docs/<slug>/`: its feedback needs no
        # stem in the name, the way `writeups/<slug>/` does not.
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
    """`(dir, stem)` of the whole a piece in `where` was cut from, or None.

    `paper1/parts/manuscript` is a piece of `paper1/manuscript`: the directory
    above `parts/`, and the stem named by the directory below it.
    """
    bits = where.split("/") if where else []
    for i in range(len(bits) - 1):
        if bits[i].lower() in PIECES:
            return "/".join(bits[:i]), bits[i + 1]
    return None


# A library of fifty documents is fifty `pdfinfo` runs, and a person tapping
# between pages of one should not pay for them again.
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
    """Every document of this subject, in the order the library draws it, as
    `(group, id, rel, stem, formats, art)`. Stats, directory listings and
    doc.json reads only: no titles, no `pdfinfo`.

    ARTIFACTS FIRST, LEGACY DOCUMENTS SECOND, MATERIALS LAST. Ids are handed
    out in walk order before anything is reordered, and the walk is the one
    the library always made, so a legacy document keeps its id: ink is keyed
    on it. An artifact placed in place is found by that walk and keeps its id
    too. A new artifact at `docs/<slug>/` is not walked; its id is its slug.
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
    """The document with this id, or None.

    AN ID, NEVER A PATH. What arrives from the browser is compared against what
    this module discovered, and a miss is a miss.
    """
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None
    for doc in documents(root):
        if doc["id"] == wanted:
            return doc
    return None


def find_any(root, ident_wanted):
    """The document under either name it has, or None.

    The library's id first (`find`), then any document whose `mark_idents`
    holds it: the board's drawer and its ink name a document by the slug of
    its filename. Still matched against discovery, never a path.
    """
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
    out = paper.pages_of(repo, target, doc["stem"] + ".pdf", "library", width)
    if out.get("ok"):
        _settle(repo, doc)
        try:
            wipe_delivered(repo, doc)
        except Exception:                                    # noqa: BLE001
            pass
        out["ink"] = ink(repo, doc)
        out["wiped"] = wiped(repo, doc)
        # THE BUILD ON THE GLASS, which the reader hands back with every save
        # so the record says what the marks were drawn on.
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

    A page with no stamp is ink from before builds were recorded, or from the
    board's own viewer, and goes with whichever build is burned. One older
    build is burned only from ITS OWN rendering, still in the page cache:
    putting marks drawn on 21:40's pages over this morning's is the defect the
    stamp exists to catch. Marks on two builds have no one page under them.
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
# DATED AND VERSIONED, NEVER STAMPED WITH THE TIME. Tracked, so a note written
# on an iPad is there on the compute node.
NOTE_RE = re.compile(r"^(?P<stem>.*?)(?P<day>\d{4}-\d{2}-\d{2})-v(?P<n>\d+)\.md$")


def _is_writeup(doc):
    """Is this a document the board made, in its own directory?

    `writeups/<slug>/` is one directory per document, so the note does not have
    to repeat the stem in its name. The two layouts that already exist are flat
    -- four stems in one directory -- and there it does.
    """
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
# by `drawer_ident` -- the slug of its filename -- and this module names it by
# where it sits, because a library has to tell two `paper.pdf`s apart.
# Marking works on the board today, which means under the drawer's name; the
# library's own name is what a mark made on the library page would carry. A
# document is one document and its ink is its ink, so a note carries whatever is
# there under either.

def marked_pages(repo, strokes_of=None):
    """Every page of every document with ink on it. `{ident: {page: n}}`, `n`
    counting its strokes. One kind of ink: a stroke stored with a retired kind
    field counts as any other.

    ONE PASS OVER THE DRAWER, FOR THE WHOLE LIBRARY. Asked per document it is a
    read and a parse of every annotation record per document, which on a
    workspace with fifty documents and a term's worth of marked-up cards is
    thousands of file reads for one payload. The drawer is small and the
    question is the same for every row, so it is asked once.

    A page count is NOT consulted here, deliberately. `pdfinfo` missing is a
    page count of zero, and deriving "which pages could be marked" from it would
    lose the ink for a reason that has nothing to do with the ink.

    `strokes_of` is `load_notes`, for a caller that has read the drawer.
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
    """Every page of one document with ink on it, in page order.

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
            png = writing.png_path(repo, key)
            out.append({"page": page, "ident": ident, "key": key,
                        "strokes": strokes,
                        "png": (os.path.relpath(png, repo.root).replace(os.sep, "/")
                                if os.path.isfile(png) else "")})
    out.sort(key=lambda m: (m["page"], m["ident"]))
    return out


# The file beside a deck that says what it covers (`briefs.py`, which imports
# this module).
DECK_BRIEF = "_brief.md"


def from_sittings(root, doc):
    """Is this a deck with its brief beside it -- the meeting deck, or an
    older deck made from sittings?"""
    where = (doc or {}).get("dir") or ""
    return bool(where) and os.path.isfile(
        os.path.join(root, *(where.split("/") + [DECK_BRIEF])))


def last_round_landed(root, doc):
    """Did the newest round of feedback on this document come back?

    Yes where there is no round yet; where its ledger has answers in it; where
    the turn or the board wrote `## What was changed` under the note; or where the
    PDF was rebuilt after the note was written (`ledger.landed`). A round whose
    turn died, or whose build failed, is none of those.
    """
    from . import ledger                              # local: avoids a cycle

    rounds = notes(root, doc)
    if not rounds:
        return True
    path = os.path.join(feedback_dir(root, doc), rounds[-1]["name"])
    if not os.path.isfile(path):
        return True
    return ledger.landed(root, doc, path)


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
    has landed (`last_round_landed`, and there must BE a round), every page of
    this document that a note carried (`sent`) loses its strokes and their
    picture (`strip`). Ink drawn since is `sent: false` -- `/annotate/save` writes
    that on every change -- and stays for the next round. A round that has not
    landed keeps everything, so a retry is still a tap. What a round's requests
    point at -- the crops and the page pictures -- is the round's own and is
    never wiped.
    """
    if not notes(repo.root, doc) or not last_round_landed(repo.root, doc):
        return []
    from . import ledger                              # local: avoids a cycle
    from ..lesson import notes as lesson_notes        # local: avoids a cycle
    from ..server.routes import writing               # local: avoids a cycle

    # THE EVIDENCE STAYS. Every round keeps the pictures its requests point at,
    # in its own directory, before a single live mark goes.
    ledger.keep_evidence(repo, doc)

    sent = lesson_notes.load_notes_sent(repo) if sent is None else sent
    wanted = set(mark_idents(repo.root, doc))
    filed = _filed_ink(repo, doc)
    if filed:
        sent = dict(sent)
        strokes_of = lesson_notes.load_notes(repo)
        builds = lesson_notes.load_notes_builds(repo)
        for key, (digest, count) in filed.items():
            # INK A LANDED ROUND FILED, UNTOUCHED SINCE, IS DELIVERED even where
            # its `sent` flag never got written: same build, same strokes. A
            # stroke added since changes the count, and stays for the next round.
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

    The strokes taken are buried (`writing.bury`), so a reader still showing
    them cannot save them back, and are named by `wiped`.
    """
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
    """`{key: strokes}`: the strokes `strip` took off this document's
    pages that some reader may still be showing (`writing.gone_path`).

    Every reply that hands ink to the reader carries it, because a page the
    reader holds keeps its own copy (`Annotate.load` never takes a mark away):
    told which strokes went, it drops them. `buried` is `buried_all`, for a
    caller asking about every document.
    """
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
               hand_over=True, merge=()):
    """One round of feedback on one document. Returns a record to paint.

    The note says which document and which page it is about, because it is read
    later by a turn that was not in the room -- and a page number is worth
    carrying, since the person writing it is looking at a page when they do.

    MARKS COUNT AS SAYING SOMETHING. A ring round a figure and an arrow to its
    caption is a complaint, and refusing the note for an empty textarea would be
    the board asking somebody to type out what they have already drawn. Which
    ink goes is `carried`'s: all of it, except on a deck made from sittings
    whose last round came back, where ink already acted on stays behind.

    A ROUND IS A LIST OF REQUESTS (`course/ledger.py`). Each inked region of a
    page is one, each typed paragraph is one, and each request reopened on an
    earlier round rides this one under the id it already has -- so a round of
    nothing but reopened requests is a round. `merge` is the filing panel's
    *these marks on page N are one request*. The note lists the requests by id
    and the ledger beside it is what the turn answers.

    `hand_over` records the ink as delivered here, and the reopened requests as
    carried. The route passes False and records both only once the revision was
    actually asked (`hand_over`, `ledger.carry`), so a note written beside an
    ask that failed leaves them to go again.

    A REWORK IS THE SAME FILE AND THE SAME ROUNDS. It is a longer turn rather
    than a different kind of record, so it lands where a correction lands and is
    read back the same way -- with the purpose it was given as its own section,
    because that sentence is the thing the turn is working to.
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
    # THE TYPED WORDS ARE WRITTEN ONCE. With a ledger they are the requests
    # below, a paragraph under each id; a second copy up here would double the
    # note.
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
            # The round's own copy where there is one: the live picture is
            # wiped once the round lands, and a note pointing at it would point
            # at nothing.
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
    """The note's list of this round's requests, by id -- the same list the
    ledger holds, written for a person and for a turn that reads Markdown."""
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
    """The rounds' answers validated, where the wipe runs -- the only code
    after a turn that is not `bin/tutor`. Said on the board's log if it fails,
    rather than swallowed: a validation nobody hears fail is a silent round."""
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
        # WHAT THE ROUNDS ASKED, AND HOW MUCH OF IT IS STILL OPEN.
        try:
            doc["ledger"] = ledger.summary(root, doc)
        except Exception:                                    # noqa: BLE001
            doc["ledger"] = None
        # SPENT INK GOES FIRST, so the counts below are of what is still on
        # the page. `index` and `sent` were read before it, so they are pruned
        # of what went rather than read again.
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
        # WHAT WAS TAKEN OFF ITS PAGES, read after the wipe above, because
        # this list is often the reply a wipe happens in and an open reader
        # drops these strokes from its glass (`wiped`).
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
# A deck that explains the machinery is shown a page at a time: a tutor
# teaching `grade` puts slide 24 in the card that asks about it. The drawer is
# a filter of the walk with a card's numbers rather than a library's, plus what
# the README points at. Its ids are the slug of the filename, and ink drawn from
# the board is keyed on them (`mark_idents`).

# How deep a drawer PDF may sit: in a directory at most this far below the
# subject. `docs/stage1_pipeline_walkthrough.pdf` is one.
DRAWER_DEPTH = 3

# A drawer is not a file manager.
DRAWER_MAX = 24

# A PDF the subject's README names. The path is matched, not the prose around
# it, and it has to end in `.pdf`.
POINTER = re.compile(r"[~\w./-]+\.pdf\b")

_shown = {}


def _big(path):
    return _size(path) >= MIN_PDF_BYTES


def _ours(path):
    """Neither in a reference library nor inside the fence, asked of the whole
    path: the README reaches files the walk never pruned its way to."""
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

    Bounded to the subject, its parent and the Atlas root, plus
    `paths.outside_tree()`: a path out of a file is a path anybody could have
    written. Two passes, because a README gives the first deck in full and
    names the one "in the same directory" by its bare filename, so a bare name
    is looked for where the decks already found live.
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

    The id is compared against what `drawer` offers; nothing builds a path from
    a request. The fence is asked once more, because this is what turns a name
    from a browser into a file the rasteriser opens.
    """
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
# A SESSION'S UPLOADS ARE READABLE PDFS, and a subject's materials are already
# documents of the library. An upload's id is the library's rule (`_ident`) on
# `uploads/<name>` -- `uploads-slides` -- the id `sessions.ink_ident` keys its
# ink on, so `board file` can re-key that ink to the id the library hands the
# file in its new place (`ident_map`).
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
    # The Atlas root, which an unbound session works in, is no subject: its
    # walk would be every subject's at once.
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
# A second tree: `IGNORE` keeps `results/` out of the walk above, and the
# allowlist `LOOK_IN` is the only way in. One walk builds an index of every
# figure and table by id; the results page draws it grouped by directory, and
# the figures view -- what a card can show -- is its newest `MAX_FIGURES`
# pictures. A FIGURE IS NOT A `figure`: `/figure/` is TikZ the board compiled,
# and `/result/<id>` serves a picture a pipeline wrote. `sw.js` never caches
# `/result/`, because the next job rewrites a figure under the same name.

# Where to look, and nowhere else, in the order a person would look.
LOOK_IN = fenced.RESULT_DIRS

# What a figure is: raster only. Vector pictures are `/figure/`'s.
FIGURE_SUFFIXES = (".png", ".jpg", ".jpeg")

# A 300-byte PNG is an axis and no data -- a plot that failed, or a spacer.
FIGURE_MIN_BYTES = 1000

# The figures view: what a card's briefing and drawer are offered.
MAX_FIGURES = 24

# How deep under a result directory to look. `results/counterfactual_pipeline/
# bupropion_vs_ssri/propensity_by_arm.png` is three; deeper is an intermediate.
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
    """A stable, unique, URL-safe id for one result, from its whole path.

    The slug of the path below its result directory, trimmed from the front to
    fit, and a digest of the path on the end: no counter, so the id does not
    depend on what else was found, and a card written today resolves next month.
    """
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
        # The filename as it stands, because a mission's card names it.
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
        # The size floor is per kind: a 300-byte PNG is a plot that failed, and
        # a 300-byte CSV is three rows of numbers.
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
        # Groups newest first; inside one, figures then tables by name, since a
        # job writes its whole directory in the same few seconds.
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

    A tutor knows a figure by its path relative to the subject. The path is
    LOOKED UP among the figures the index holds, never joined: one that is not
    exactly one of them is left alone, and the route 404s it.
    """
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
    where it looked, and which fenced directories it refused to look in."""
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
