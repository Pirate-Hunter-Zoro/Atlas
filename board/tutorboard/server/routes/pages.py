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
"""

import hashlib
import json
import os
import re
import threading

from . import NOT_MINE
from .. import multipart
from ... import paths
from ...course import results


# THE SERVICE WORKER'S VERSION IS A HASH OF ITS OWN SHELL.
#
# `web/sw.js` names its cache `VERSION`, and an installed app keeps serving the
# shell it cached until that name moves. So the name is computed here, from the
# bytes of every file its SHELL list names plus sw.js itself, and written over
# the placeholder literal as the file is served. A process computes it once and
# again only when one of those files' mtime or size changes.
SW_PLACEHOLDER = '"board-shell-dev"'
SW_PAGES = {"/": "home.html", "/board": "board.html", "/slate": "slate.html",
            "/library": "library.html", "/meeting": "meeting.html"}
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
            target, cache=rel.startswith("katex/") or rel.startswith("fonts/"))

    if path.startswith("/figure/"):
        digest = multipart.safe_filename(path[len("/figure/"):]).replace(".svg", "")
        return h.send_file(os.path.join(repo.tikz, digest + ".svg"), cache=True)

    if path.startswith("/result/"):
        # A FIGURE THE PIPELINE MADE, ADDRESSED BY AN ID RATHER THAN BY A PATH.
        #
        # `/figure/` above is TikZ the tutor wrote and this board compiled. This
        # is somebody's own output, out of their workspace, and the difference
        # that matters here is where the name came from: a digest this board
        # produced can be joined onto a directory, and a name out of a browser
        # cannot. So it is looked up in what discovery found -- `results.find`
        # is the whole of the check, the same rule as `reading.find` and
        # `walk.resolve` -- and a miss is a miss.
        ident = path[len("/result/"):]
        if not re.match(r"^[a-z0-9-]{1,80}$", ident):
            return h.send_bytes(b"not found", "text/plain", status=404)
        target, _name = results.find(repo.root, ident)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        # NOT CACHED. The next job writes a new figure at the same name, and the
        # id is derived from that name -- so a hard cache here serves last
        # week's result under this week's label. `web/sw.js` keeps the same rule
        # on its side.
        return h.send_file(target)

    if path.startswith("/uploads/"):
        name = multipart.safe_filename(path[len("/uploads/"):])
        return h.send_file(os.path.join(repo.uploads, name), untrusted=True)

    if path.startswith("/answers/"):
        name = multipart.safe_filename(path[len("/answers/"):])
        return h.send_file(os.path.join(repo.answers, name))
    return NOT_MINE
