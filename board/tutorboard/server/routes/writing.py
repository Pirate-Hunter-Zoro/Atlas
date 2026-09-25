"""Handwriting, both what is on the surface and what was handed in.

The slate saves constantly and sends deliberately, and the difference
between those two is most of what these routes are about.
"""

import re
import shutil
import time
import hashlib
import json
import os

from . import NOT_MINE
from .. import multipart
from .. import spawn
from ...course import burn
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


def ann_says(key, answering_now):
    """What the tutor is told about WHERE the mark is, in §2.1 terms."""
    if ANN_CARD.match(key):
        lead = ("this is their ANSWER to your question on card %s" % key
                if answering_now else "they wrote on your card %s" % key)
        return lead, ("Open the image, read what they marked, and answer it "
                      "against that card's own text in live/cards/.")
    m = ann_doc_page(key)
    if m:
        return ("they wrote on page %d of the document `%s`"
                % (m[1], m[0]),
                "Open the image to see the marks. The document itself is one "
                "this workspace offers -- `board doctor` lists them -- and the "
                "address of that page is #/w/<family>/<workspace>/%s." % key)
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
            h.server.hub.worker.dirty.set()
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
        stem = ann_file(card)
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
        if not sent:
            try:
                with open(os.path.join(repo.notes, stem + ".json"), "r",
                          encoding="utf-8") as fh:
                    was = json.load(fh)
                sent = bool(was.get("sent")) and was.get("strokes") == strokes
            except (OSError, ValueError):
                sent = False
        with open(os.path.join(repo.notes, stem + ".json"), "w", encoding="utf-8") as fh:
            json.dump({"card": card, "strokes": strokes, "sent": sent}, fh)
        h.note("annotate %s: %d strokes, %s"
                  % (card, len(strokes), "SENT" if sent else "saved only"))

        png = payload.get("png") or ""
        marker = "base64,"
        saved_png = None
        if marker in png:
            import base64
            try:
                saved_png = os.path.join(repo.notes, stem + ".png")
                with open(saved_png, "wb") as fh:
                    fh.write(base64.b64decode(png.split(marker, 1)[1]))
            except Exception:
                saved_png = None

        if not payload.get("send"):
            h.server.hub.worker.dirty.set()
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
        # Handed in, so there had better be somebody to read it. See
        # `spawn.wake_tutor`: a no-op unless the board really is unattended.
        if spawn.wake_tutor(repo):
            h.note("nothing was reading the board; starting a tutor")
        h.server.hub.worker.dirty.set()
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
            if spawn.wake_tutor(repo):
                h.note("nothing was reading the board; starting a tutor")
            h.server.hub.worker.dirty.set()
            h.note("slate page %d: %d strokes, SENT as %s rev %d answering %s"
                      % (n, len(strokes), tid, rev, record["answers"] or "-"))
            return h.send_json({"ok": True, "page": n, "turn": tid, "rev": rev})
        h.server.hub.worker.dirty.set()
        h.note("slate page %d: %d strokes, saved only (not sent)"
                  % (n, len(payload.get("strokes") or [])))
        return h.send_json({"ok": True, "page": n})

    if path == "/upload":
        ctype = h.headers.get("Content-Type", "")
        m = re.search(r"boundary=([^;]+)", ctype)
        if not m:
            return h.send_json({"ok": False, "error": "no boundary"}, status=400)
        boundary = m.group(1).strip('"').encode("utf-8")
        parts = multipart.parse_multipart(h.read_body(), boundary)
        saved = []
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for i, part in enumerate(parts):
            if not part["filename"]:
                continue
            name = "%s-%02d-%s" % (stamp, i, multipart.safe_filename(part["filename"]))
            with open(os.path.join(repo.uploads, name), "wb") as fh:
                fh.write(part["data"])
            saved.append(name)
        if saved:
            record = {
                "t": time.time(),
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "from": "student",
                # A picture has no sentence in it, so its inbox line has to
                # carry its own meaning -- the same reason a `begin` signal
                # spells itself out. A tutor woken by a bare filename has no
                # reason to think opening it is the next thing to do.
                "text": ("[uploaded] %s — the student handed this over for you "
                         "to look at. Open the file below and answer what is "
                         "in it." % ", ".join(saved)),
                "files": saved,
                "read": False,
            }
            with open(repo.messages_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            if spawn.wake_tutor(repo):
                h.note("nothing was reading the board; starting a tutor")
        h.server.hub.worker.dirty.set()
        return h.send_json({"ok": True, "saved": saved})
    return NOT_MINE
