"""Files: the app shell, the fonts, a compiled figure, a result, a photograph.

Everything here is bytes off disk, and everything a person handed in is
served with the headers that stop a browser executing it.

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    shell     unprefixed, the same for everybody, and under `/s/<id>/` too:
              GET /manifest.webmanifest  /sw.js  /static/*
    subject   under `/s/<id>/` for the session's subject, or unprefixed with
              `?subject=<id>` (the library page): GET /result/<id>
    session   under `/s/<id>/` only: GET /figure/<digest>.svg  /uploads/<name>
              /answers/<name>
    subject?  under `/s/<id>/`, or unprefixed with `?subject=<id>` or over the
              Atlas root: GET /source/<path>?from=&to=
"""

import hashlib
import html
import json
import os
import re
import threading
import urllib.parse

from . import NOT_MINE
from .. import multipart
from ... import fenced, gitops, paths
from ...course import library, walk


# The service worker's VERSION is a hash of its shell (every SHELL file plus
# sw.js), written over the placeholder as served, so an installed app picks
# up any change. Recomputed when a file's mtime or size moves.
SW_PLACEHOLDER = '"board-shell-dev"'
# The board and the slate are cached under their /static/ names: a session's
# `/s/<id>/board` falls back to them (`web/sw.js`).
SW_PAGES = {"/": "home.html", "/library": "library.html"}
_sw = {"stamp": None, "body": None, "src_stamp": None, "shell": ()}
_sw_lock = threading.Lock()


def _stamp(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def shell_urls(src):
    """The URLs in sw.js's `var SHELL = [...]`, in order."""
    m = re.search(r"var SHELL = \[(.*?)\];", src, re.S)
    return tuple(re.findall(r'"([^"]+)"', m.group(1))) if m else ()


def shell_file(url):
    """The file on disk a SHELL URL is served from."""
    if url in SW_PAGES:
        return os.path.join(paths.WEB, SW_PAGES[url])
    if url.startswith("/static/"):
        return os.path.normpath(os.path.join(paths.WEB, url[len("/static/"):]))
    return os.path.join(paths.WEB, url.lstrip("/"))


def sw_body():
    """sw.js as served, with its hashed VERSION, and that VERSION."""
    src_path = os.path.join(paths.WEB, "sw.js")
    with _sw_lock:
        src_stamp = _stamp(src_path)
        if src_stamp != _sw["src_stamp"]:
            with open(src_path, encoding="utf-8") as fh:
                src = fh.read()
            _sw.update(src_stamp=src_stamp, src=src, shell=shell_urls(src), stamp=None)
        files = [(u, shell_file(u)) for u in _sw["shell"]]
        stamp = (src_stamp,) + tuple(_stamp(f) for _u, f in files)
        if stamp != _sw["stamp"]:
            digest = hashlib.sha256(_sw["src"].encode("utf-8"))
            for url, f in files:
                digest.update(b"\0" + url.encode("utf-8") + b"\0")
                try:
                    with open(f, "rb") as fh:
                        digest.update(fh.read())
                except OSError:
                    digest.update(b"missing")
            version = "board-shell-" + digest.hexdigest()[:16]
            body = _sw["src"].replace(SW_PLACEHOLDER, '"%s"' % version, 1)
            _sw.update(stamp=stamp, body=body.encode("utf-8"), version=version)
        return _sw["body"], _sw["version"]


def get(h, repo, path):
    if path == "/manifest.webmanifest":
        return h.send_bytes(open(os.path.join(paths.WEB, "manifest.webmanifest"), "rb").read(),
                               "application/manifest+json")

    if path == "/sw.js":
        body, version = sw_body()
        return h.send_bytes(body, "text/javascript; charset=utf-8",
                            gzip_key=("/sw.js", version))

    if path.startswith("/static/"):
        rel = path[len("/static/"):]
        target = os.path.normpath(os.path.join(paths.WEB, rel))
        if not target.startswith(paths.WEB):
            return h.send_bytes(b"nope", "text/plain", status=403)
        return h.send_file(
            target, cache=rel.startswith(("katex/", "fonts/", "vendor/")))

    if path.startswith("/source/"):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(h.path or "").query)
        status, body = source_page(repo, path[len("/source/"):], query)
        return h.send_bytes(body, "text/html; charset=utf-8" if status == 200
                            else "text/plain", status=status)

    if path.startswith("/figure/"):
        digest = multipart.safe_filename(path[len("/figure/"):]).replace(".svg", "")
        return h.send_file(os.path.join(repo.tikz, digest + ".svg"), cache=True)

    if path.startswith("/result/"):
        # A pipeline's figure, by id: `library.find_result` is the whole check,
        # since a browser's name is never joined onto a directory.
        ident = path[len("/result/"):]
        if not re.match(r"^[a-z0-9-]{1,80}$", ident):
            return h.send_bytes(b"not found", "text/plain", status=404)
        target, _name = library.find_result(repo.root, ident)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        # Not cached: jobs rewrite figures under the same name (sw.js agrees).
        return h.send_file(target)

    if path.startswith("/uploads/"):
        name = multipart.safe_filename(path[len("/uploads/"):])
        return h.send_file(os.path.join(repo.uploads, name), untrusted=True)

    if path.startswith("/answers/"):
        name = multipart.safe_filename(path[len("/answers/"):])
        return h.send_file(os.path.join(repo.answers, name))
    return NOT_MINE


# ---------------------------------------------------------------------------
# GET /source/<path>?from=&to= -- the read-only source viewer
# ---------------------------------------------------------------------------
# The read-only source viewer for `path#Lx-y` excerpts. The path is resolved
# by `walk.resolve`, never joined, and must be outside the fence and private
# directories and tracked by git; anything else is a bare 404.

# Big enough for any source file worth reading on a tablet.
SOURCE_MAX_BYTES = 2 * 1024 * 1024

# highlight.js's name for an extension. The page is numbered and marked without
# it; `web/codeview.js` only colours it.
SOURCE_LANG = {".py": "python", ".go": "go", ".sh": "bash", ".bash": "bash",
               ".lean": "lean", ".r": "r", ".sql": "sql"}

NOT_FOUND = (404, b"not found")


def _line(query, key):
    try:
        n = int((query.get(key) or [""])[0])
    except ValueError:
        return 0
    return n if n > 0 else 0


def source_file(repo, raw):
    """`(full path, label)` of the tracked file `/source/<raw>` names, or None."""
    raw = str(raw or "")
    parts = raw.replace("\\", "/").split("/")
    if (not raw or raw.startswith("/") or ":" in raw or "\0" in raw
            or any(not x or x == ".." or x.startswith(".") for x in parts)
            or fenced.in_fence(raw)):
        return None
    try:
        from ..registry import base_of
        base = os.path.realpath(base_of(repo))
        chosen, _unknown = walk.resolve(repo.root, [raw], base=base)
    except Exception:
        return None
    if len(chosen) != 1:
        return None
    unit = chosen[0]
    root, rel = unit["root"], unit["path"]
    atlas_rel = walk._atlas_rel(base, root, rel)
    if (fenced.in_fence(rel) or not atlas_rel or fenced.in_fence(atlas_rel)
            or atlas_rel.split("/", 1)[0].lower() in walk.PRIVATE):
        return None
    full = os.path.realpath(os.path.join(root, rel))
    if not full.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(full):
        return None
    code, _out = gitops._git(root, "ls-files", "--error-unmatch", "--", rel, timeout=10)
    if code != 0:
        return None
    return full, rel


def source_page(repo, raw, query):
    """`(status, body)` of the source viewer for `raw`, lines `from`..`to` marked."""
    found = source_file(repo, raw)
    if not found:
        return NOT_FOUND
    full, rel = found
    try:
        if os.path.getsize(full) > SOURCE_MAX_BYTES:
            return NOT_FOUND
        with open(full, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return NOT_FOUND
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) > 1 and lines[-1] == "":
        lines.pop()
    first, last = _line(query, "from"), _line(query, "to")
    if first and not last:
        last = first
    if first and last < first:
        first, last = last, first
    if first:
        first, last = min(first, len(lines)), min(last, len(lines))
    out = []
    for n, line in enumerate(lines, 1):
        cls = "line mark" if first and first <= n <= last else "line"
        out.append('<span class="%s" data-n="%d" id="L%d">%s%s</span>' % (
            cls, n, n, html.escape(line, quote=False),
            "\n" if n < len(lines) else ""))
    lang = SOURCE_LANG.get(os.path.splitext(rel)[1].lower(), "")
    where = ("lines %d&ndash;%d" % (first, last) if first and last > first
             else "line %d" % first if first else "%d lines" % len(lines))
    page = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>%(title)s</title>\n'
        '<link rel="stylesheet" href="/static/typeface.css">\n'
        '<link rel="stylesheet" href="/static/board.css">\n'
        '</head>\n<body class="source-page" data-mode="auto">\n'
        '<header class="source-head"><span class="source-path">%(title)s</span> '
        '<span class="muted">%(where)s, read-only</span></header>\n'
        '<pre class="code numbered"><code data-source="1" data-lang="%(lang)s" '
        'data-from="%(first)d" data-to="%(last)d">%(body)s</code></pre>\n'
        '<script src="/static/typeface.js"></script>\n'
        '<script src="/static/vendor/highlight/highlight.min.js"></script>\n'
        '<script src="/static/codeview.js"></script>\n'
        '</body>\n</html>\n') % {
            "title": html.escape(rel), "where": where, "lang": lang,
            "first": first, "last": last, "body": "".join(out)}
    return 200, page.encode("utf-8")
