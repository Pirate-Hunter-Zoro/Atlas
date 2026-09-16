"""The library: every document this workspace has written, and feedback on one.

A SURFACE RATHER THAN A SITTING, and that is the whole design. Nothing here
writes to `live/cards/`, archives a lesson or touches `live/state.json`, because
somebody mid-proof on an iPad must not be interrupted by somebody correcting a
deck. What a note does is land beside the document it is about and wake a turn
that is not the lesson's.

    GET  /library.json              everything `course/library.py` found
    GET  /library/view/<id>         the pages of one, drawn by the renderer the
                                    board already has
    POST /library/feedback          one round of feedback, written where the
                                    document is, and then acted on

AN ID, NEVER A PATH. What arrives from the browser is compared against what
discovery found -- `library.find` -- and a miss is a miss. `reading.find` is the
rule and `/result/` is the worked example.

AND FEEDBACK IS NEVER JUST FILED. A note nothing acts on is a note the person
believes is in force, which is the same defect `/direction` was built to avoid.
So writing one dispatches the revision in the same request, and the reply says
which machinery took it: the board revises a document it compiled, and
Paper-Writer revises a manuscript it delivered.
"""

import json
import time

from . import NOT_MINE
from .. import spawn
from ... import manuscript, sense
from ...course import library
from ...lesson import turns


def get(h, repo, path):
    if path == "/library.json":
        return h.send_json(library.status(repo.root))

    if path.startswith("/library/view/"):
        # The same rasteriser, the same cache and the same `/paper/<name>.png`
        # page addresses the lesson's own documents use. What differs is only
        # how the file was found.
        return h.send_json(library.pages(repo, path[len("/library/view/"):]))

    return NOT_MINE


def post(h, repo, path):
    if path == "/library/feedback":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        ident = str(payload.get("document") or "").strip()
        text = payload.get("text") or ""
        try:
            page = int(payload.get("page") or 0)
        except (TypeError, ValueError):
            page = 0
        doc = library.find(repo.root, ident)
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        rec = library.write_note(repo.root, ident, text, page=page)
        if not rec.get("ok"):
            return h.send_json(rec, status=400)
        rec.update(_revise(h, repo, doc, rec["rel"]))
        return h.send_json(rec)

    return NOT_MINE


def _revise(h, repo, doc, note_rel):
    """Ask for the revision, by whichever machinery wrote the document.

    THE TWO KINDS ARE CHANGED BY DIFFERENT MACHINERY, and this is the seam.

    A board-made explainer -- a `.tex` under `writeups/`, or any document this
    repository holds the source of -- is revised by the board: a `[revise]` line
    in the inbox and a turn woken on it. That turn runs FRESH and writes no
    card; see `HEADLESS_REVISE_PROMPT` in `bin/tutor` for why a resumed one
    would drag the lesson into the document.

    A manuscript delivered into `manuscripts/` is revised by the factory that
    wrote it, because the factory is what holds the evidence, the terminology
    lock, the reporting checklist and the venue's word limit. An explainer is
    NOT routed through it: "how the serve harness works, and the arithmetic
    behind the batch size" has no venue and makes no claims, and every one of
    those gates would either refuse it or invent something to satisfy itself.
    """
    if doc.get("made") == "paper-writer":
        try:
            out = manuscript.revise(repo.root, doc, note_rel)
        except Exception as exc:                             # noqa: BLE001
            return {"revise": "paper-writer", "asked": False,
                    "detail": "the manuscript job could not be assembled: %s" % exc}
        return {"revise": "paper-writer", "asked": bool(out.get("ok")),
                "job": out.get("name") or "",
                "detail": out.get("detail") or ""}

    line = "[revise] " + sense.revise_sense(doc["rel"], note_rel)
    record = {
        # An id from the same series the lesson's turns use, so nothing in the
        # inbox has to be told apart by shape. It is NOT written into
        # `live/turns.jsonl`: the transcript is the lesson's, and this is not
        # part of the lesson.
        "id": turns.next_turn_id(repo),
        "rev": 0, "kind": "text", "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": line, "signal": "revise", "read": False,
    }
    try:
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        return {"revise": "board", "asked": False,
                "detail": "the note is written but nothing could be asked: %s" % exc}
    # A request that sits in an inbox beside a board with no tutor on it is a
    # tap that did nothing for ever -- the same reason `/say` wakes one.
    if spawn.wake_tutor(repo):
        h.note("nothing was reading the board; starting a tutor for a revision")
    h.server.hub.worker.dirty.set()
    return {"revise": "board", "asked": True,
            "detail": "The tutor has been asked to revise it. That turn is not "
                      "part of the lesson: it writes no card and leaves the "
                      "sitting on the board alone."}
