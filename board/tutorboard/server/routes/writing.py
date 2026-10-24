"""Handwriting, both what is on the surface and what was handed in.

The slate saves constantly and sends deliberately, and the difference
between those two is most of what these routes are about.

    GET  /slate/state       session    the slate's pages
    POST /slate/save        session    a slate page, saved or sent; its
                                       typeset givens (`objects`) kept as
                                       stored when the save has no such key
    POST /annotate/save     subject?   ink on a card or a document page, saved
                                       or sent. Unprefixed (the library, with
                                       `?subject=` or without) it saves
                                       document ink only, into the subject's
                                       or the Atlas root's `.ink/`: a card
                                       and a send need a session.
    POST /annotate/burn     subject    the ink made into a marked copy,
                                       `<name>-marked.pdf` beside the PDF
    POST /upload            session    files into the session's uploads/,
                                       streamed, at most 1 GB; each a
                                       non-waking `[uploaded]` line, and a
                                       PDF's `doc`, the id the reader opens
    POST /file              session    one upload `{upload, dest?}` filed into
                                       the bound subject (`sessions.file`),
                                       its ink re-keyed; `doc` is its new id
    POST /fetch             session    `{url}`: a PDF fetched over http or
                                       https into the session's uploads/,
                                       answered as /upload answers

The classes are `handler.UNPREFIXED`'s.
"""

import re
import shutil
import tempfile
import time
import hashlib
import json
import os
import posixpath
import urllib.error
import urllib.parse
import urllib.request

from . import NOT_MINE
from .. import multipart
from ...runner import service as runner
from ..registry import is_sessionless
from ...course import burn
from ...course import repo as course_repo
from ...lesson import notes
from ...lesson import slate
from ...lesson import turns


def placed_says(objects):
    """What the `[slate]` line says of the typeset givens on a page: they
    are the problem's data, placed from the panel, and not their working."""
    names = []
    for o in objects or []:
        if o.get("id") not in names:
            names.append(o.get("id"))
    if not names:
        return ""
    return (" The typeset %s (%s) %s placed from the problem's givens: the "
            "problem's data, not their working. Credit only what they wrote "
            "around %s." % ("given" if len(names) == 1 else "givens",
                             ", ".join(names), "was" if len(names) == 1 else "were",
                             "it" if len(names) == 1 else "them"))


def get(h, repo, path):
    if path == "/slate/state":
        return h.send_json({"pages": slate.read_slate_pages(repo)})
    return NOT_MINE


# ---------------------------------------------------------------------------
# WHAT A MARK CAN BE ANCHORED TO
# ---------------------------------------------------------------------------
# What a mark can be anchored to: a card (`0007`) or a document page
# (`doc/<ident>/p<n>`), the tail of a §2.1 address. A browser's key never
# reaches the filesystem: it is validated against these shapes (with `\Z`,
# because `$` admits a trailing newline) and the filename is derived from it.
ANN_CARD = re.compile(r"\A\d{1,4}\Z")
ANN_DOC = re.compile(r"\Adoc/([a-z0-9-]{1,40})/p(\d{1,4})\Z")


def ann_ok(key):
    return bool(ANN_CARD.match(key) or ANN_DOC.match(key))


def ann_doc_page(key):
    """`(ident, page)` for a mark on a document page, or None. The one place a
    key is taken apart, so "is this key ours" has one answer."""
    found = ANN_DOC.match(str(key or ""))
    return (found.group(1), int(found.group(2))) if found else None


def ann_file(key):
    """The filename for one key's record, which can never climb out: a card
    keeps its own name; anything else is flattened and carries a digest of
    the key, so two addresses never share a file."""
    if ANN_CARD.match(key):
        return key
    flat = re.sub(r"[^A-Za-z0-9-]+", "-", key).strip("-")[:60]
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return "%s-%s" % (flat or "mark", digest)


def ann_path(repo, key, ext=".json"):
    """Where one key's record (`.json`), picture or burial is kept: a card's
    in the session, a document page's in the subject's `.ink/` once the
    session is bound (`course.repo.ink_dir`)."""
    return os.path.join(course_repo.ink_dir(repo, key), ann_file(key) + ext)


def png_path(repo, key):
    """Where one key's picture of its ink is kept. A `<stem>.dir.png` beside
    it is a retired kind's picture, and nothing reads it."""
    return ann_path(repo, key, ".png")


# Strokes the board took off a page, buried in `<stem>.gone` until every
# reader lets them go: `/annotate/save` refuses those exact strokes, and a
# save carrying none of them retires the record.
def gone_path(repo, key):
    return ann_path(repo, key, ".gone")


def gone_of(repo, key):
    try:
        with open(gone_path(repo, key), "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return []
    got = rec.get("strokes") if isinstance(rec, dict) else None
    return [s for s in got if isinstance(s, dict)] if isinstance(got, list) else []


def bury(repo, key, strokes):
    """Add `strokes` to what was taken off `key`."""
    strokes = [s for s in strokes or [] if isinstance(s, dict)]
    if not strokes:
        return
    had = gone_of(repo, key)
    seen = set(notes.stroke_sig(s) for s in had)
    rec = {"card": key, "at": time.time(),
           "strokes": had + [s for s in strokes if notes.stroke_sig(s) not in seen]}
    try:
        with open(gone_path(repo, key), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    except OSError:
        pass


def unbury(repo, key):
    try:
        os.remove(gone_path(repo, key))
    except OSError:
        pass


BUILD_DIGEST = re.compile(r"\A[0-9a-f]{6,40}\Z")


def clean_build(build):
    """`{digest, at, pages}` for the rendering a mark was drawn on, or None.
    The digest is `paper._digest`'s; anything else is dropped."""
    if not isinstance(build, dict):
        return None
    digest = str(build.get("digest") or "")
    if not BUILD_DIGEST.match(digest):
        return None
    try:
        at = float(build.get("at") or 0)
        pages = int(build.get("pages") or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    if not 0 <= at < 1e11:                  # NaN fails this too
        at = 0.0
    return {"digest": digest, "at": at, "pages": max(0, min(pages, 100000))}


def ann_says(key, answering_now):
    """What the tutor is told about WHERE the mark is, in §2.1 terms."""
    if ANN_CARD.match(key):
        lead = ("this is their ANSWER to your question on card %s" % key
                if answering_now else "they wrote on your card %s" % key)
        return lead, ("Open the image, read what they marked, and answer it "
                      "against that card's own text in live/cards/.")
    m = ann_doc_page(key)
    if m:
        # Ink asking for a document change is answered in its ledger, from
        # any surface; a question on the page stays the lesson's.
        return ("they wrote on page %d of the document `%s`"
                % (m[1], m[0]),
                "Open the image to see the marks. The document itself is one "
                "this workspace offers -- `board doctor` lists them -- and the "
                "address of that page is #/s/<this session's id>/%s. Where the "
                "marks ask for changes to the document, they are feedback on it, "
                "not the lesson: run `board round %s` and answer every id in the "
                "ledger it prints. Where they ask a question about the page, "
                "answer it in the lesson." % (key, m[0]))
    return "they wrote on %s" % key, "Open the image to see the marks."


def post(h, repo, path):
    if path == "/annotate/burn":
        # The ink made into a marked copy beside the PDF (`burn.burn`), or
        # nothing (`none`). The strokes stay in the annotation record, so a
        # copy can always be burned again.
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        kind = str(payload.get("kind") or "")
        mode = str(payload.get("mode") or "")
        got = burn.burn(repo, kind, mode)
        h.note("burn %s (%s): %s" % (kind, mode,
                                     got.get("detail") or got.get("why")))
        if got.get("ok") and got.get("mode") != "none":
            # The viewer's PDF list changed: send the payload again.
            h.hub.worker.dirty.set()
        return h.send_json(got, status=200 if got.get("ok") else 400)

    if path == "/annotate/save":
        # Ink on the tutor's cards: saved across reloads, or sent as a turn.
        # Stored in the card's own coordinates, so it moves with the words.
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        card = str(payload.get("card") or "")
        if not ann_ok(card):
            return h.send_json({"ok": False, "error": "bad anchor"}, status=400)
        if is_sessionless(repo) and (not ANN_DOC.match(card) or payload.get("send")):
            # No session: only document ink, and only saved.
            return h.send_json({"ok": False, "error": "card ink and a send are a "
                                "session's: /s/<id>/annotate/save"}, status=400)
        record_path = ann_path(repo, card)
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        strokes = payload.get("strokes") or []
        # Whether these marks were handed to the tutor, so a reload tells
        # delivered ink from autosaved ink; a plain save clears it.
        sent = bool(payload.get("send"))
        # Unless nothing changed: a re-save to attach a picture must not
        # resend delivered ink.
        try:
            with open(record_path, "r", encoding="utf-8") as fh:
                was = json.load(fh)
        except (OSError, ValueError):
            was = {}
        # Ink the board took off this page (`gone_path`) is refused.
        gone = set(notes.stroke_sig(s) for s in gone_of(repo, card))
        if gone:
            kept = [s for s in strokes if notes.stroke_sig(s) not in gone]
            if len(kept) == len(strokes):
                unbury(repo, card)
            strokes = kept
        if not sent:
            sent = bool(was.get("sent")) and \
                (was.get("strokes") or []) == strokes
        rec = {"card": card, "strokes": strokes, "sent": sent}
        # The build the ink was drawn on, knowable only at save; a save naming
        # none keeps the recorded one while the strokes are unchanged.
        build = clean_build(payload.get("build"))
        if not build and was.get("strokes") == strokes:
            build = clean_build(was.get("build"))
        if build:
            rec["build"] = build
        with open(record_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        h.note("annotate %s: %d strokes, %s"
                  % (card, len(strokes), "SENT" if sent else "saved only"))

        png = payload.get("png") or ""
        marker = "base64,"
        saved_png = None
        if marker in png:
            import base64
            try:
                saved_png = png_path(repo, card)
                with open(saved_png, "wb") as fh:
                    fh.write(base64.b64decode(png.split(marker, 1)[1]))
            except Exception:
                saved_png = None
        if not payload.get("send"):
            h.hub.worker.dirty.set()
            return h.send_json({"ok": True, "card": card})

        tid = payload.get("turn") or turns.next_turn_id(repo)
        rev = turns.turn_revision(repo, tid)
        base = "%s-r%d" % (tid, rev)
        if saved_png:
            try:
                shutil.copyfile(saved_png, os.path.join(repo.answers, base + ".png"))
            except OSError:
                pass
        with open(os.path.join(repo.answers, base + ".json"), "w", encoding="utf-8") as fh:
            json.dump({"card": card, "strokes": strokes}, fh)
        record = {
            "id": tid, "rev": rev, "kind": "annotation",
            # The card this sits under in the transcript; a document page
            # sits under none.
            "answers": card if ANN_CARD.match(card) else "",
            "anchor": card,
            "t": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from": "student",
            "strokes": len(strokes),
            "where": payload.get("where") or "",
            "png": "/answers/" + base + ".png",
            "ink": "/answers/" + base + ".json",
            "read": False,
        }
        turns.write_turn(repo, record)
        msg = dict(record)
        # Which card, roughly where, and the ink. Marks on the asking card
        # are an answer, and the tutor is told so.
        answering_now = (card == turns.newest_question(repo))
        lead, how = ann_says(card, answering_now)
        msg["text"] = ("[annotation] %s%s. %s%s"
                       % (lead,
                          (", " + record["where"]) if record["where"] else "",
                          how,
                          " Treat it as the answer to that question."
                          if answering_now else ""))
        msg["slate"] = os.path.join(repo.answers, base + ".png")
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(msg) + "\n")
        # Handed in: the runner queues a turn to read it.
        runner.wake(repo)
        h.hub.worker.dirty.set()
        return h.send_json({"ok": True, "card": card, "turn": tid, "rev": rev})

    if path == "/slate/save":
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        n = int(payload.get("page") or 1)
        if not (1 <= n <= 999):
            return h.send_json({"ok": False, "error": "bad page"}, status=400)
        stem = os.path.join(repo.slate, "page-%02d" % n)

        # The typeset givens on the page: what the save carries, or what the
        # page already had when it carries no `objects` key (an older client).
        objects = (slate.clean_objects(payload.get("objects")) if "objects" in payload
                   else slate.stored_objects(stem + ".json"))
        with open(stem + ".json", "w", encoding="utf-8") as fh:
            json.dump({"page": n, "w": payload.get("w"), "h": payload.get("h"),
                       "strokes": payload.get("strokes") or [],
                       "objects": objects}, fh)

        png = payload.get("png") or ""
        marker = "base64,"
        if marker in png:
            import base64
            try:
                with open(stem + ".png", "wb") as fh:
                    fh.write(base64.b64decode(png.split(marker, 1)[1]))
            except Exception:
                pass

        if payload.get("send"):
            strokes = payload.get("strokes") or []
            # Revising an answer supersedes it; a new answer starts a turn.
            tid = payload.get("turn") or turns.next_turn_id(repo)
            rev = turns.turn_revision(repo, tid)
            base = "%s-r%d" % (tid, rev)
            # Frozen: the slate page will be written over.
            try:
                shutil.copyfile(stem + ".png", os.path.join(repo.answers, base + ".png"))
            except OSError:
                pass
            with open(os.path.join(repo.answers, base + ".json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"w": payload.get("w"), "h": payload.get("h"),
                           "strokes": strokes, "objects": objects}, fh)
            record = {
                "id": tid, "rev": rev, "kind": "ink",
                "answers": payload.get("answers") or turns.newest_question(repo),
                "t": time.time(),
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "from": "student",
                "page": n, "strokes": len(strokes),
                "png": "/answers/" + base + ".png",
                "ink": "/answers/" + base + ".json",
                "read": False,
            }
            turns.write_turn(repo, record)
            msg = dict(record)
            # A page is not a verdict: it may be an attempt or a question.
            msg["text"] = ("[slate] %s rev %d, %d strokes. Open the image and "
                           "read all of it. Credit what is already on it and "
                           "never ask for that again. A question NEW on this "
                           "page is answered first, before any working is "
                           "assessed; one carried over from their last page "
                           "was answered by your last card. A direction on it "
                           "-- move on, stop, focus on -- binds. Do not mark a "
                           "question wrong.%s"
                           % (tid, rev, len(strokes), placed_says(objects)))
            msg["slate"] = os.path.join(repo.answers, base + ".png")
            with open(repo.messages_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(msg) + "\n")
            runner.wake(repo)
            h.hub.worker.dirty.set()
            h.note("slate page %d: %d strokes, SENT as %s rev %d answering %s"
                      % (n, len(strokes), tid, rev, record["answers"] or "-"))
            return h.send_json({"ok": True, "page": n, "turn": tid, "rev": rev})
        h.hub.worker.dirty.set()
        h.note("slate page %d: %d strokes, saved only (not sent)"
                  % (n, len(payload.get("strokes") or [])))
        return h.send_json({"ok": True, "page": n})

    if path == "/upload":
        return upload(h, repo)
    if path == "/fetch":
        return fetch(h, repo)
    if path == "/file":
        return file_upload(h, repo)
    return NOT_MINE


def file_upload(h, repo):
    """`POST /file {upload, dest?}`: `sessions.file` from the page. 400 in
    its own words on refusal; nothing wakes."""
    from ... import sessions                       # local: sessions imports this
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    if is_sessionless(repo) or not getattr(repo, "stored", False):
        return h.send_json({"ok": False, "error": "an upload is a session's: "
                            "/s/<id>/file"}, status=400)
    sid = os.path.basename(repo.live)
    base = os.path.dirname(os.path.dirname(repo.live))
    try:
        got = sessions.file(sid, payload.get("upload"), payload.get("dest") or None,
                            base=base)
    except (sessions.NoSession, sessions.Refused) as exc:
        return h.send_json({"ok": False, "error": str(exc)}, status=400)
    h.note("filed %s -> %s/%s" % (got["from"], got["subject"], got["to"]))
    h.hub.worker.dirty.set()
    return h.send_json(dict(got, ok=True))


def _size(n):
    """`n` bytes as a person reads it: 812 B, 14 KB, 2.3 MB, 1.1 GB."""
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return ("%d %s" if unit == "B" or n >= 10 else "%.1f %s") % (n, unit)
        n /= 1024.0
    return "%.1f GB" % n


def _free_name(folder, filename):
    """`folder/<safe name>`, with `-2`, `-3`, ... before the extension when
    that name is taken."""
    name = multipart.safe_filename(filename)
    stem, ext = os.path.splitext(name)
    out, n = name, 1
    while os.path.lexists(os.path.join(folder, out)):
        n += 1
        out = "%s-%d%s" % (stem, n, ext)
    return os.path.join(folder, out)


def upload(h, repo):
    """`POST /upload`: every multipart file into the session's `uploads/`
    (D21), streamed, at most `multipart.MAX_UPLOAD`, each with a non-waking
    `[uploaded] <name> (<size>)` line. The tutor files it (`board file`)."""
    def refuse(status, error):
        # The body may be unread: this connection carries nothing more.
        h.close_connection = True
        return h.send_json({"ok": False, "error": error}, status=status)

    if is_sessionless(repo):
        return refuse(400, "an upload is a session's: /s/<id>/upload")
    m = re.search(r"boundary=([^;]+)", h.headers.get("Content-Type", ""))
    if not m:
        return refuse(400, "no boundary")
    try:
        length = int(h.headers.get("Content-Length") or "")
    except ValueError:
        return refuse(411, "an upload says its length")
    if length > multipart.MAX_UPLOAD:
        return refuse(413, "%s is over the 1 GB an upload may be"
                      % _size(length))
    boundary = m.group(1).strip().strip('"').encode("utf-8")
    os.makedirs(repo.uploads, exist_ok=True)
    try:
        got = multipart.save_parts(
            h.rfile, length, boundary, repo.uploads,
            lambda _i, filename: _free_name(repo.uploads, filename))
    except multipart.Broken as exc:
        h.note("upload refused: %s" % exc)
        return refuse(400, "the upload did not arrive whole: %s" % exc)
    except OSError as exc:
        h.note("upload failed: %s" % exc)
        return refuse(500, "the upload could not be written: %s" % exc)
    return _landed(h, repo, [(where, size) for _filename, where, size in got])


def _landed(h, repo, got):
    """The reply to files now in the session's `uploads/`, `[(path, size)]`:
    each with a non-waking `[uploaded]` line, and a PDF's `doc`, the id the
    reader opens it as."""
    from ... import sessions                       # local: sessions imports this
    from ...course import library
    ids = dict((u["name"], u["id"]) for u in library.uploads(repo))
    saved = []
    for where, size in got:
        name = os.path.basename(where)
        one = {"name": name, "size": size}
        if ids.get(name):
            one["doc"] = ids[name]
        saved.append(one)
        sessions.quiet_line(repo.messages_path,
                            "[uploaded] %s (%s)" % (name, _size(size)),
                            "uploaded", files=[name])
        h.note("upload %s: %d bytes" % (name, size))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "saved": [s["name"] for s in saved],
                        "files": saved})


# ---------------------------------------------------------------------------
# A PDF FROM A URL
# ---------------------------------------------------------------------------
# Only these schemes are fetched, before a redirect and after it: a file://
# or ftp:// answer would read the Mac's own disk or a server nobody chose.
FETCH_SCHEMES = ("http", "https")
FETCH_TIMEOUT = 60
# The whole download's limit: FETCH_TIMEOUT bounds one read, so a server
# sending a byte a minute would otherwise hold the request for ever.
FETCH_DEADLINE = 600
PDF_MAGIC = b"%PDF-"


class _Refused(ValueError):
    """A fetch refused as asked; `status` is the reply's."""

    def __init__(self, why, status=400):
        ValueError.__init__(self, why)
        self.status = status


def _off_http(url):
    """A refusal for an address that is not http or https, else None."""
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme in FETCH_SCHEMES:
        return None
    return _Refused("it redirects to %s, and only http and https are fetched"
                    % (scheme + "://" if scheme else url))


class _Redirects(urllib.request.HTTPRedirectHandler):
    """The stock redirect handler, refusing any redirect off http or https in
    the board's own words (the stock one follows one to ftp)."""

    def http_error_302(self, req, fp, code, msg, headers):
        said = headers.get("location") or headers.get("uri")
        if said:
            refused = _off_http(urllib.parse.urljoin(req.full_url, said))
            if refused:
                fp.close()
                raise refused
        return urllib.request.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        refused = _off_http(newurl)
        if refused:
            raise refused
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl)


def _opener():
    """An opener with http, https and redirects only: built by hand, because
    `build_opener` adds a FileHandler, an FTPHandler and a DataHandler."""
    out = urllib.request.OpenerDirector()
    for one in (urllib.request.ProxyHandler(), urllib.request.UnknownHandler(),
                urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(),
                urllib.request.HTTPDefaultErrorHandler(), _Redirects(),
                urllib.request.HTTPErrorProcessor()):
        out.add_handler(one)
    return out


def pdf_name(said):
    """`said` as an upload's name that ends `.pdf` within the 120 characters
    `multipart.safe_filename` keeps (`library.uploads` lists only `.pdf`),
    `fetched.pdf` when nothing of it is left."""
    name = multipart.safe_filename(said or "")
    if name == "drop":
        name = "fetched"
    ext = name[-4:] if name.lower().endswith(".pdf") else ".pdf"
    stem = name[:-4] if name.lower().endswith(".pdf") else name
    stem = stem[:120 - 4].strip("-.") or "fetched"
    return stem + ext


def _fetched_name(url, headers):
    """The name a fetched PDF is kept under: Content-Disposition's filename,
    else the URL's last path part, else `fetched`, ending `.pdf`."""
    said = ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?',
                  headers.get("Content-Disposition") or "", re.I)
    if m:
        said = urllib.parse.unquote(m.group(1))
    if not said:
        said = urllib.parse.unquote(posixpath.basename(urllib.parse.urlsplit(url).path))
    return pdf_name(said)


def fetch_pdf(url, folder, limit=None, timeout=FETCH_TIMEOUT, deadline=FETCH_DEADLINE):
    """Fetch the PDF at `url` into `folder` under a free name: `(path, size)`,
    or `_Refused`. http and https only, checked before and after redirects;
    at most `limit` bytes (`multipart.MAX_UPLOAD`); the body must start with
    `%PDF-`. `timeout` seconds for any one read, and refused (504) once the
    download has run past `deadline` seconds. Nothing is left behind on a
    refusal."""
    limit = multipart.MAX_UPLOAD if limit is None else limit
    url = str(url or "").strip()
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if not url:
        raise _Refused("name the PDF's address")
    if scheme not in FETCH_SCHEMES or not urllib.parse.urlsplit(url).netloc:
        raise _Refused("only an http or https address is fetched, not %s"
                       % (scheme + "://" if scheme else url))
    began = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": "tutor-board",
                                               "Accept": "application/pdf, */*"})
    try:
        resp = _opener().open(req, timeout=timeout)
    except _Refused:
        raise
    except urllib.error.HTTPError as exc:
        raise _Refused("the server answered %d %s" % (exc.code, exc.reason), 502)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise _Refused("it could not be fetched: %s"
                       % getattr(exc, "reason", exc), 502)
    tmp = None
    try:
        final = resp.geturl() or url
        if urllib.parse.urlsplit(final).scheme.lower() not in FETCH_SCHEMES:
            raise _Refused("it ended at %s, and only http and https are fetched"
                           % final)
        try:
            said = int(resp.headers.get("Content-Length") or -1)
        except ValueError:
            said = -1
        if said > limit:
            raise _Refused("%s is over the 1 GB an upload may be" % _size(said), 413)
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".fetch-", suffix=".part",
                                   dir=os.path.dirname(folder))
        size = 0
        with os.fdopen(fd, "wb") as fh:
            head = b""
            while True:
                # read1: what one read of the socket brings, so the deadline
                # is checked as bytes trickle in, not after a whole chunk.
                chunk = resp.read1(multipart.CHUNK)
                if not chunk:
                    break
                if len(head) < len(PDF_MAGIC):
                    head = (head + chunk)[:len(PDF_MAGIC)]
                    if len(head) >= len(PDF_MAGIC) and head != PDF_MAGIC:
                        raise _Refused("that is not a PDF: it does not start "
                                       "with %PDF-")
                size += len(chunk)
                if size > limit:
                    raise _Refused("it is over the 1 GB an upload may be", 413)
                if time.monotonic() - began > deadline:
                    raise _Refused("it took over %d s to arrive" % deadline, 504)
                fh.write(chunk)
        if head != PDF_MAGIC:
            raise _Refused("that is not a PDF: it does not start with %PDF-")
        dest = _free_name(folder, _fetched_name(final, resp.headers))
        os.replace(tmp, dest)
        tmp = None
        return dest, size
    except (OSError, ValueError) as exc:
        if isinstance(exc, _Refused):
            raise
        raise _Refused("it could not be fetched: %s" % exc, 502)
    finally:
        resp.close()
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def fetch(h, repo):
    """`POST /fetch {url}`: the PDF at `url` into the session's `uploads/`
    (`fetch_pdf`), replied to as `/upload` replies, its line waking nothing."""
    if is_sessionless(repo) or not getattr(repo, "stored", False):
        return h.send_json({"ok": False, "error": "a fetch is a session's: "
                            "/s/<id>/fetch"}, status=400)
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:                                        # noqa: BLE001
        payload = None
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    try:
        where, size = fetch_pdf(payload.get("url"), repo.uploads)
    except _Refused as exc:
        h.note("fetch refused: %s" % exc)
        return h.send_json({"ok": False, "error": str(exc)}, status=exc.status)
    return _landed(h, repo, [(where, size)])
