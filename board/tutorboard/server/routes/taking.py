"""Taking a document off the board, and reading one ON the board.

Everything here already exists in the repository and is tracked in git -- that
is the archival copy and none of it changes. This is the other half, asked for
from the iPad:

    "when we save the .pdf, we should also have the option to download it
    locally on the iPad so I can save it to files in my iCloud, get it on my
    phone, and email it to my prof, lickety split. Also, I want the ability to
    do this with the written up work too."

A repository on a compute node is not a place an iPad can reach, and neither is
a tailnet path a person can hand to a professor. A download is.

AND READING IT IS NOT THE SAME AS SAVING IT, which is the second report:

    "It compiles the homework, but it's not letting me view the compiled .pdf or
    save it anywhere locally on the iPad."

*Save a copy* raises the share sheet, and a share sheet is somewhere to put a
document rather than somewhere to read one. `/view/<kind>` is the reading half:
the pages come back as PNGs, drawn by the machine that has the PDF, because a
PDF handed to a frame on iOS is one unscrollable page and a PDF navigated to in
a standalone web app is a lesson nobody can get back to. `course/paper.py` says
the whole of why.

THE CLIENT NEVER NAMES A PATH. It names a KIND -- the lesson, or the written-up
homework -- or an ID, and this resolves either to a file through what discovery
already found: `live/export.json` and `live/hw.json` for the two the board
builds, `library.drawer_find` for a document the course points at. A query parameter carrying a repo-relative path
would be a directory traversal waiting to be written, and there is nothing it
would buy -- the board knows where every one of these is.

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


# The download route's own helpers moved into `course/paper.py`, because the
# payload and the viewer need the same answers. These names are kept because
# they are what `test/document.py` asserts against, and because a caller here
# reads better for them.
_pdf_in = paper.pdf_in
_named = paper.named



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
        # The pages, rendered here. It is a POST-shaped amount of work behind a
        # GET, and deliberately: the request is idempotent, the result is a
        # cache keyed on the PDF's own modification time, and a second open of
        # the same document is a directory listing.
        kind = path.rsplit("/", 1)[1]
        return h.send_json(_inked(repo, paper.pages(repo, kind), kind))

    if path.startswith("/marked/"):
        # A MARKED COPY, handed over to be kept: the kind and the name, both
        # matched against what is on disk beside that document's PDF
        # (`burn.marked_of`), and sent as an attachment for Files.
        kind, _slash, name = path[len("/marked/"):].rpartition("/")
        found = burn.marked_of(repo, unquote(kind), unquote(name))
        if not found:
            return h.send_json({"ok": False, "error": "no such copy"}, status=404)
        return h.send_file(found, download=os.path.basename(found))

    if path.startswith("/view/doc/"):
        # A document this course POINTS AT rather than one it built: a slide
        # deck, a walkthrough, a set of lecture slides -- or a PDF handed to
        # this session, or one of the subject's materials. Same rasteriser,
        # same cache, same page route -- the only thing that differs is how the
        # file was found, and `library.readable` is the whole of that check.
        ident = path[len("/view/doc/"):]
        return h.send_json(_inked(repo, library.drawer_pages(repo, ident), ident))

    if path.startswith("/doc/"):
        # ONE PAGE, ADDRESSED BY WHAT IT IS RATHER THAN BY THIS RENDER OF IT.
        #
        # The manifest's own URLs carry the digest, which carries the PDF's
        # modification time -- exactly right for a viewer that just asked, and
        # exactly wrong for a card. A tutor teaching `grade` writes
        # `![slide 24](/doc/stage2-reference-walkthrough/24.png)` into a lesson
        # that is kept, exported and read again next month; the deck gets
        # rebuilt at 33 slides, and every slide in the transcript would break.
        # So a card names the document and the page, and this resolves that to
        # whatever the current render is.
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
        # Not cached hard: the name is stable and what is behind it is not, so
        # a rebuilt deck has to be able to change what this returns.
        target = paper.page_file(name)
        if not target:
            return h.send_bytes(b"not found", "text/plain", status=404)
        return h.send_file(target)

    if path.startswith("/paper/"):
        name = os.path.basename(path[len("/paper/"):])
        # Content-addressed by construction -- the digest in the name carries
        # the PDF's modification time -- so it can be cached hard, and a
        # rebuilt document is a different name rather than a stale picture.
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
