"""Handwriting, both what is on the surface and what was handed in.

The slate saves constantly and sends deliberately, and the difference
between those two is most of what these routes are about.

    GET  /slate/state       session    the slate's pages
    POST /slate/save        session    a slate page, saved or sent
    POST /annotate/save     subject?   ink on a card or a document page, saved
                                       or sent. Unprefixed (the library, with
                                       `?subject=` or without) it saves
                                       document ink only, into the subject's
                                       or the Atlas root's `.ink/`: a card
                                       and a send need a session.
    POST /annotate/burn     session    the ink made into a marked copy
    POST /upload            session    files into the session's uploads/,
                                       streamed, at most 1 GB; each a
                                       non-waking `[uploaded]` line

The classes are `handler.UNPREFIXED`'s.
"""

import re
import shutil
import time
import hashlib
import json
import os

from . import NOT_MINE
from .. import multipart
from ...runner import service as runner
from ..registry import is_sessionless
from ...course import burn
from ...course import repo as course_repo
from ...lesson import notes
from ...lesson import slate
from ...lesson import turns


def get(h, repo, path):
    if path == "/slate/state":
        return h.send_json({"pages": slate.read_slate_pages(repo)})
    return NOT_MINE


# ---------------------------------------------------------------------------
# WHAT A MARK CAN BE ANCHORED TO
# ---------------------------------------------------------------------------
# A card, and now a page of a document. The key is the tail of a §2.1 address,
# so the tutor can be told WHERE a mark is in the same words a link uses.
#
#     0007                  card 7 of the lesson
#     doc/<ident>/p<n>      page n of a document this workspace offers
#
# A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM, and this is the one place
# in the annotation path where it could: the record used to be written to
# `<notes>/<card>.json`, which was safe only because a card is four digits. A
# key with a slash in it joined onto a path is the oldest hole there is, so the
# key is VALIDATED against these shapes and then the filename is DERIVED from
# it rather than being it.
# `\Z`, NOT `$`. In Python `$` also matches just before a trailing newline, so
# `"doc/a/p1\n"` passed a `$`-anchored check -- and that string then went into a
# filename. A key arrives from a browser; it gets the strict end-of-string.
ANN_CARD = re.compile(r"\A\d{1,4}\Z")
ANN_DOC = re.compile(r"\Adoc/([a-z0-9-]{1,40})/p(\d{1,4})\Z")


def ann_ok(key):
    return bool(ANN_CARD.match(key) or ANN_DOC.match(key))


def ann_doc_page(key):
    """`(ident, page)` for a mark on a page of a document, or None.

    THE ONE PLACE THAT TAKES A KEY APART. Everything else that wants to know
    which document a mark is on -- the sentence the tutor is told, the library
    reading ink back as feedback -- asks here, because a second spelling of this
    pattern is a second answer to "is this key one of ours", and that question
    is the one this file exists to answer exactly once.
    """
    found = ANN_DOC.match(str(key or ""))
    return (found.group(1), int(found.group(2))) if found else None


def ann_file(key):
    """The filename for one key's record, and it can never climb out.

    A card keeps its own name, so every record already on disk is found exactly
    where it was. Anything else is flattened -- there is no `/` left in it to be
    a directory -- and carries a short digest of the key, because two different
    addresses must never flatten onto one file.
    """
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


# THE STROKES THE BOARD TOOK OFF A PAGE, kept until every reader has let them
# go. A landed round's wipe deletes strokes on disk, but a reader still showing
# them saves them back as new ink. So `library.strip` buries
# what it takes in `<stem>.gone` (not `.json`, so no drawer read sees it), the
# reader is told which (`library.wiped`), and `/annotate/save` refuses those
# exact strokes on that page. A save carrying none of them means the reader has
# caught up, and the record goes.
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

    The digest is `paper._digest`'s -- the name the page cache gives one exact
    PDF -- so it says both which build this was and where its pages are drawn.
    Anything else in it is dropped, and a digest that is not one is no build.
    """
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
        # INK ASKING FOR A CHANGE TO A DOCUMENT IS ANSWERED IN ITS LEDGER,
        # whichever surface it was sent from: answered anywhere else, it stays
        # drawn over the revision. A mark asking a question about the page --
        # a sitting's "why is this true?" on its own write-up -- is the lesson's,
        # and filing it as a round would spend a revision on a question.
        return ("they wrote on page %d of the document `%s`"
                % (m[1], m[0]),
                "Open the image to see the marks. The document itself is one "
                "this workspace offers -- `board doctor` lists them -- and the "
                "address of that page is #/w/<family>/<workspace>/%s. Where the "
                "marks ask for changes to the document, they are feedback on it, "
                "not the lesson: run `board round %s` and answer every id in the "
                "ledger it prints. Where they ask a question about the page, "
                "answer it in the lesson." % (key, m[0]))
    return "they wrote on %s" % key, "Open the image to see the marks."


def post(h, repo, path):
    if path == "/annotate/burn":
        # THE INK, MADE INTO A DOCUMENT. Marking up your own compiled write-up
        # already worked; what it produced was a record in the board's drawer,
        # which is not a thing anybody can hand over or read next year. This is
        # the way out, and there are exactly three of them because there are
        # three things "save" means: over the original, as a new file, or not at
        # all. `none` writes nothing and is answered without drawing a page.
        #
        # Deliberately a POST that can overwrite a file the repository builds.
        # That is the asked-for behaviour and it is safe for one reason worth
        # stating where it happens: the strokes are not in the PDF. They are in
        # the annotation record, so a compile that destroys the burned rendering
        # destroys nothing that cannot be burned again.
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
            # The PDF under the viewer just changed, so the payload has to go
            # out again -- the page cache is keyed on modification time and the
            # controls are drawn off `papers`.
            h.hub.worker.dirty.set()
        return h.send_json(got, status=200 if got.get("ok") else 400)

    if path == "/annotate/save":
        # Marks written over the tutor's own cards. Saving keeps them across
        # a reload; sending makes them a turn. They are anchored to a card,
        # in that card's own coordinates, so changing the type size or the
        # reading face moves the ink with the words instead of leaving it
        # stranded where the words used to be.
        try:
            payload = json.loads(h.read_body().decode("utf-8"))
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        card = str(payload.get("card") or "")
        if not ann_ok(card):
            return h.send_json({"ok": False, "error": "bad anchor"}, status=400)
        if is_sessionless(repo) and (not ANN_DOC.match(card) or payload.get("send")):
            # Outside a session there is no card and no inbox: only a
            # document page's ink is kept, and only saved.
            return h.send_json({"ok": False, "error": "card ink and a send are a "
                                "session's: /s/<id>/annotate/save"}, status=400)
        # INK ON ANOTHER DECK IS NOT THIS ONE'S. A library left open on the
        # meeting deck while a new deck was asked for still owes the old
        # deck's marks, and keys are page numbers, so they would land on the
        # new deck's slides. The save names its deck (`briefs.deck_id`, sent
        # by library.js); `gone` tells the page to let it go.
        if card.startswith("doc/meeting/") and payload.get("deck") is not None:
            from ... import briefs                     # local: avoids a cycle
            from ..registry import base_of
            here = briefs.deck_id(base_of(repo) or repo.root)
            if str(payload.get("deck")) != here:
                return h.send_json(
                    {"ok": False, "gone": True,
                     "error": "these marks were drawn on another deck"},
                    status=409)
        record_path = ann_path(repo, card)
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        strokes = payload.get("strokes") or []
        # Whether these marks have been handed to the tutor, recorded next
        # to them. Without it a reload cannot tell ink that was delivered
        # from ink that was only ever autosaved, so yesterday's forgotten
        # marks went on demanding a decision every time anything was sent.
        # A plain save only ever arrives for a card that just changed, so
        # "not a send" is exactly the right moment to clear the flag.
        sent = bool(payload.get("send"))
        # UNLESS NOTHING CHANGED. The library re-saves a page only to attach
        # its picture before a note goes, with the very strokes already on
        # disk; clearing the flag there would send ink a round already
        # delivered a second time.
        try:
            with open(record_path, "r", encoding="utf-8") as fh:
                was = json.load(fh)
        except (OSError, ValueError):
            was = {}
        # INK THE BOARD TOOK OFF THIS PAGE DOES NOT COME BACK (`gone_path`): a
        # reader that still had it on the glass sends it with whatever it drew
        # next, and written here it would be new, unsent ink again.
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
        # WHICH BUILD THE INK WAS DRAWN ON, as the reader that drew it says.
        # A document rebuilt overnight moves its text under the marks, and the
        # page it was drawn on is only knowable here, at save. A save that
        # names no build keeps the one on record while the strokes are the
        # same ones.
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
            # WHICH CARD THIS SITS UNDER in the transcript -- and a mark on a
            # page of a document sits under no card at all. Claiming one would
            # file the turn beneath a card it has nothing to do with; empty
            # lets it fall to where its time puts it, which is the truth.
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
        # The tutor wrote this card and can read it back off disk, so what it
        # needs from here is which card was marked, roughly where, and the
        # ink itself.
        # Marks on the card that is currently asking are an answer, and the
        # tutor has to be told that rather than left to infer it -- a card
        # that asked the student to decide something gets marks back, and
        # "they wrote on your card" reads like a passing note.
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

        with open(stem + ".json", "w", encoding="utf-8") as fh:
            json.dump({"page": n, "w": payload.get("w"), "h": payload.get("h"),
                       "strokes": payload.get("strokes") or []}, fh)

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
            # Frozen, because the slate page it came from will be written
            # over. What was handed in has to stay what was handed in.
            try:
                shutil.copyfile(stem + ".png", os.path.join(repo.answers, base + ".png"))
            except OSError:
                pass
            with open(os.path.join(repo.answers, base + ".json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"w": payload.get("w"), "h": payload.get("h"),
                           "strokes": strokes}, fh)
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
            # What arrived is a page, not a verdict. It may be an attempt,
            # a question written in the margin, or "I don't know how to
            # start" -- and reading it as a wrong answer when it is a
            # question is the most discouraging thing this can do.
            msg["text"] = ("[slate] %s rev %d, %d strokes. Open the image and "
                           "read what is actually on it: if there is a question "
                           "anywhere on the page, answer that first, in its own "
                           "card, before assessing any working. Do not mark a "
                           "question wrong."
                           % (tid, rev, len(strokes)))
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
    return NOT_MINE


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
    """`POST /upload`: every file of a multipart form into the session's
    `uploads/` (D21), streamed to disk (`multipart.save_parts`), at most
    `multipart.MAX_UPLOAD`. Each one appends a non-waking `[uploaded] <name>
    (<size>)` line: the next turn reads it, and none is started for it. The
    tutor files it (`board file`)."""
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
    from ... import sessions                       # local: sessions imports this
    saved = []
    for _filename, where, size in got:
        name = os.path.basename(where)
        saved.append({"name": name, "size": size})
        sessions.quiet_line(repo.messages_path,
                            "[uploaded] %s (%s)" % (name, _size(size)),
                            "uploaded", files=[name])
        h.note("upload %s: %d bytes" % (name, size))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "saved": [s["name"] for s in saved],
                        "files": saved})
