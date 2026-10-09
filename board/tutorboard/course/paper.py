"""The documents a board can hand over, and how to look at one on the device.

Resolving and naming a built document serves the download route, the
payload (whether a document exists, at any moment) and the viewer. Viewing
rasterises PDF pages to PNGs here, because iOS shows a PDF in a frame as one
unscrollable page; pages are cached against the PDF's mtime.

The constraint: a machine with no rasteriser (launchd's PATH is
`/usr/bin:/bin`) says so rather than failing, so the board can offer the
copy instead of an empty panel.
"""

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time

from .. import paths, tex


# Kinds the client names (never a path), and the record that builds each.
KINDS = ("lesson", "homework")
_RECORD = {"lesson": "export.json", "homework": "hw.json"}

# A little over an iPad Pro's reading column at 2x; wider buys nothing.
PAGE_WIDTH = 1240

# A page cap that says where it stopped, rather than quietly ending.
MAX_PAGES = 160

# Page sets kept: shared by every session, and a marked copy needs the build
# its ink was drawn on. Least recently opened goes first.
CACHE_SETS = 24


def record(repo, kind):
    """The build record for one kind of document, or None."""
    name = _RECORD.get(kind)
    if not name:
        return None
    try:
        with open(os.path.join(repo.live, name), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def slug(text):
    text = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-")
    return text or "lesson"


def pdf_in(repo, rel):
    """A repo-relative path from one of our own records, checked anyway
    (disk is editable): a .pdf that exists inside the repository."""
    if not rel or not str(rel).endswith(".pdf"):
        return None
    root = os.path.realpath(repo.root)
    target = os.path.realpath(os.path.join(root, str(rel)))
    if target != root and not target.startswith(root + os.sep):
        return None
    return target if os.path.isfile(target) else None


def named(repo, stem):
    """The download's file name, with the course in front so it is
    recognisable in Files."""
    st = repo.state() or {}
    course = slug(st.get("course") or os.path.basename(repo.root))
    stem = slug(stem)
    return stem if stem.lower().startswith(course.lower()) else course + "-" + stem


def resolve(repo, kind):
    """`(path, filename)` for one kind of document, or `(None, None)` when
    there is none yet, which is ordinary."""
    rec = record(repo, kind)
    target = pdf_in(repo, (rec or {}).get("pdf"))
    if not target:
        return None, None
    if kind == "homework":
        # The set's name, not the file's.
        stem = (rec or {}).get("set") or os.path.splitext(os.path.basename(target))[0]
    else:
        stem = os.path.splitext(os.path.basename(target))[0]
    return target, named(repo, stem) + ".pdf"


def describe(repo):
    """What can be taken off this board right now, keyed by kind: a document
    is a file whose existence is always answerable, not a build event. Four
    stats."""
    out = {}
    for kind in KINDS:
        target, filename = resolve(repo, kind)
        if not target:
            continue
        rec = record(repo, kind) or {}
        try:
            at = os.path.getmtime(target)
        except OSError:
            at = rec.get("at") or 0
        out[kind] = {
            "name": filename,
            "at": at,
            "size": _size(target),
            "iso": time.strftime("%Y-%m-%d %H:%M", time.localtime(at)),
            "set": rec.get("set") if kind == "homework" else None,
            "scope": rec.get("scope") if kind == "lesson" else None,
        }
    return out


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# turning a PDF into something an iPad can read in place
# ---------------------------------------------------------------------------
def raster_env():
    """The environment a page renderer is looked for in: `tex.tex_env` plus
    poppler's and Ghostscript's places, since a launchd PATH has neither."""
    env = tex.tex_env()
    extra = [d for d in ("/usr/local/bin", "/usr/bin", "/bin")
             if os.path.isdir(d)]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def renderer(env=None):
    """Which page renderer this machine has, as (name, path), or None. poppler
    first, because it scales to a width; Ghostscript (MacTeX without poppler)
    gets a DPI that lands close."""
    env = env or raster_env()
    path = env.get("PATH", "")
    for name in ("pdftoppm", "pdftocairo", "gs"):
        found = shutil.which(name, path=path)
        if found:
            return name, found
    return None


def _digest(pdf_path, width):
    """A name for this exact document at this width; the mtime is in it, so a
    rebuild is a new page set, never a stale one."""
    try:
        stamp = os.stat(pdf_path)
        key = "%s|%d|%d|%d" % (os.path.realpath(pdf_path), stamp.st_mtime_ns,
                               stamp.st_size, width)
    except OSError:
        key = "%s|%d" % (os.path.realpath(pdf_path), width)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def cache_dir():
    """The shared page cache, `paths.PAGES`, one `<digest>/` per build:
    outside the tree, so nothing rendered can be committed."""
    d = paths.PAGES
    os.makedirs(d, exist_ok=True)
    return d


PAGE_NAME = re.compile(r"^([0-9a-f]{6,})-\d+\.png$")


def page_file(name):
    """The file behind a page name `<digest>-<n>.png` (what `/paper/` is
    asked for and `cached` returns), or None for any other name."""
    m = PAGE_NAME.match(name or "")
    if not m:
        return None
    return os.path.join(cache_dir(), m.group(1), name)


def cached(digest):
    """The pages already rendered for this digest, in page order."""
    found = sorted(glob.glob(os.path.join(cache_dir(), digest, digest + "-*.png")),
                   key=_page_number)
    return [os.path.basename(p) for p in found]


def _page_number(path):
    m = re.search(r"-(\d+)\.png$", path)
    return int(m.group(1)) if m else 0


def pages(repo, kind, width=PAGE_WIDTH):
    """Every page of one of the two built documents, as PNGs, cached on the
    PDF's mtime."""
    target, filename = resolve(repo, kind)
    if not target:
        return {"ok": False, "why": "none",
                "detail": ("There is no %s PDF yet."
                           % ("compiled write-up" if kind == "homework" else "exported lesson"))}
    return pages_of(repo, target, filename, kind, width)


def pages_of(repo, target, filename, tag, width=PAGE_WIDTH):
    """Every page of any PDF this board may show, as PNGs: the cache, lock,
    renderer and page cap of `pages`, for a file the caller found."""
    width = max(400, min(2200, int(width or PAGE_WIDTH)))
    kind = tag
    digest = _digest(target, width)
    have = cached(digest)
    if have:
        _touch(digest)
        return _manifest(kind, filename, digest, have, target)

    # One render per document at a time: the server is threaded, and a
    # double-tap must not write the same page files twice.
    with _lock_for(digest):
        have = cached(digest)
        if have:
            return _manifest(kind, filename, digest, have, target)
        return _draw(kind, target, filename, digest, width)


_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(digest):
    with _LOCKS_GUARD:
        # Bounded.
        if len(_LOCKS) > 32:
            _LOCKS.clear()
        return _LOCKS.setdefault(digest, threading.Lock())


def _draw(kind, target, filename, digest, width):
    env = raster_env()
    tool = renderer(env)
    if not tool:
        return {"ok": False, "why": "no-renderer", "name": filename,
                "detail": ("This machine has no page renderer on it -- pdftoppm, "
                           "pdftocairo and gs are all absent -- so the pages "
                           "cannot be drawn here. The document itself is fine: "
                           "save a copy and read it in Files.")}

    where = os.path.join(cache_dir(), digest)
    os.makedirs(where, exist_ok=True)
    prefix = os.path.join(where, digest)
    try:
        code, out = _render(tool, target, prefix, width, env)
    except subprocess.TimeoutExpired:
        # A timeout is reported, not a 500 that blames the network.
        _sweep(digest)
        return {"ok": False, "why": "failed", "name": filename,
                "detail": ("%s took longer than five minutes on this document "
                           "and was stopped. Save a copy and read it in Files."
                           % tool[0])}
    except OSError as exc:
        code, out = 1, str(exc)
    made = cached(digest)
    if not made:
        # Never leave a partial set: it would be served as the whole document.
        _sweep(digest)
        return {"ok": False, "why": "failed", "name": filename,
                "detail": ("%s could not draw the pages (exit %d). %s"
                           % (tool[0], code, out[-400:] or "it printed nothing.")).strip()}
    _prune(digest)
    return _manifest(kind, filename, digest, made, target)


def _manifest(kind, filename, digest, files, target):
    return {
        "ok": True,
        "kind": kind,
        "name": filename,
        "digest": digest,
        "n": len(files),
        "truncated": len(files) >= MAX_PAGES,
        "pages": ["/paper/" + f for f in files],
        "size": _size(target),
    }


def _render(tool, pdf_path, prefix, width, env):
    name, _found = tool
    if name in ("pdftoppm", "pdftocairo"):
        cmd = [name, "-png",
               "-scale-to-x", str(width), "-scale-to-y", "-1",
               "-f", "1", "-l", str(MAX_PAGES), pdf_path, prefix]
    else:
        # Ghostscript cannot scale to a width: a resolution close to A4's.
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
               "-sDEVICE=png16m", "-r%d" % max(72, int(width / 8.27)),
               "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
               "-dFirstPage=1", "-dLastPage=%d" % MAX_PAGES,
               "-sOutputFile=%s-%%d.png" % prefix, pdf_path]
    p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def _touch(digest):
    """An opened set is a recently used one, so `_prune` keeps it."""
    try:
        os.utime(os.path.join(cache_dir(), digest))
    except OSError:
        pass


def _sweep(digest):
    shutil.rmtree(os.path.join(cache_dir(), digest), ignore_errors=True)


def _prune(keep):
    """Old page sets go, by least recent use, keeping several, since the
    cache is shared by every session."""
    base = cache_dir()
    sets = []
    for name in os.listdir(base):
        where = os.path.join(base, name)
        if name == keep or not re.match(r"^[0-9a-f]{6,}$", name) \
                or not os.path.isdir(where):
            continue
        try:
            sets.append((os.path.getmtime(where), where))
        except OSError:
            pass
    sets.sort(reverse=True)
    for _at, where in sets[CACHE_SETS - 1:]:
        shutil.rmtree(where, ignore_errors=True)
