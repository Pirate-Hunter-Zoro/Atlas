"""Taking a document off the board, and reading one ON the board.

A download puts a built document on the iPad (Files, mail); `/view/<kind>`
reads one on the board as PNG pages, because iOS shows a PDF in a frame as
one unscrollable page (`course/paper.py`).

The constraint: the client never names a path. It names a kind (the lesson,
the written-up homework) or an id, resolved through what discovery found:
`export.json` and `hw.json` for built documents, `library.readable` for the
rest.
WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    session   under `/s/<id>/` only: GET /download/lesson  /download/homework
              /view/lesson  /view/homework  /view/doc/<id>  /doc/<id>/<n>.png
              /marked/<kind>/<name>, a marked copy `/annotate/burn` kept
              beside the PDF of `homework`, `lesson` or `doc/<id>`
    both      GET /paper/<digest>-<n>.png: one page cache for every session
              and subject (`paths.PAGES`), so it is answered here under
              `/s/<id>/` and by the handler's `paper` class unprefixed
"""

import os
import re
from urllib.parse import unquote

from . import NOT_MINE
from ...course import burn
from ...course import paper
from ...course import library
from ...lesson import notes


def _inked(repo, got, ident):
    """A page manifest with the document's ink beside it, `doc/<ident>/p<n>`:
    the board payload carries card ink only, so a document brings its own."""
    if isinstance(got, dict) and got.get("ok"):
        got["ink"], got["ink_sent"] = notes.doc_ink(repo, ident)
    return got

def get(h, repo, path):
    if path in ("/download/lesson", "/download/homework"):
        kind = path.rsplit("/", 1)[1]
        target, filename = paper.resolve(repo, kind)
        if not target:
            return h.send_bytes(_nothing_yet(kind), "text/plain", status=404)
        return h.send_file(target, download=filename)

    if path in ("/view/lesson", "/view/homework"):
        # Rendering behind a GET: idempotent, and cached on the PDF's mtime.
        kind = path.rsplit("/", 1)[1]
        return h.send_json(_inked(repo, paper.pages(repo, kind), kind))

    if path.startswith("/marked/"):
        # A marked copy as an attachment; kind and name matched on disk
        # (`burn.marked_of`).
        kind, _slash, name = path[len("/marked/"):].rpartition("/")
        found = burn.marked_of(repo, unquote(kind), unquote(name))
        if not found:
            return h.send_json({"ok": False, "error": "no such copy"}, status=404)
        return h.send_file(found, download=os.path.basename(found))

    if path.startswith("/view/doc/"):
        # A document the course points at, an upload or a material: same
        # rasteriser, cache and page route; `library.readable` is the check.
        ident = path[len("/view/doc/"):]
        return h.send_json(_inked(repo, library.drawer_pages(repo, ident), ident))

    if path.startswith("/doc/"):
        # One page addressed by document and number, not by render digest, so
        # a card linking `/doc/<id>/24.png` survives a rebuild.
        rest = path[len("/doc/"):]
        m = re.match(r"^([a-z0-9-]{1,40})/(\d{1,3})\.png$", rest)
        if not m:
            return h.send_bytes(b"not found", "text/plain", status=404)
        ident, page = m.group(1), int(m.group(2))
        got = library.drawer_pages(repo, ident)
        if not got.get("ok"):
            return h.send_bytes(b"not found", "text/plain", status=404)
        urls = got.get("pages") or []
        if page < 1 or page > len(urls):
            return h.send_bytes(b"no such page", "text/plain", status=404)
        name = os.path.basename(urls[page - 1])
        # Not cached hard: the name is stable, what is behind it is not.
        target = paper.page_file(name)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        return h.send_file(target)

    if path.startswith("/paper/"):
        name = os.path.basename(path[len("/paper/"):])
        # Content-addressed by the digest (which carries the mtime): cached
        # hard.
        target = paper.page_file(name)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        return h.send_file(target, cache=True)

    return NOT_MINE


def _nothing_yet(kind):
    if kind == "homework":
        return (b"There is no compiled homework PDF yet. Build it first "
                b"(the menu: export the written-up homework).")
    return (b"There is no exported lesson PDF yet. Export it first "
            b"(the menu: export this lesson).")
