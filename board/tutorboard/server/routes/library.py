"""The library: every document this workspace has written, and feedback on one.

A SURFACE RATHER THAN A SITTING, and that is the whole design. Nothing here
writes to `live/cards/`, archives a lesson or touches `live/state.json`, because
somebody mid-proof on an iPad must not be interrupted by somebody correcting a
deck. What a note does is land beside the document it is about and wake a turn
that is not the lesson's.

    GET  /library.json              everything `course/library.py` found
    GET  /library/stamp             one hash of where every document is and
                                    when it last changed, cheap enough to ask
                                    every few seconds
    GET  /library/view/<id>         the pages of one, drawn by the renderer the
                                    board already has
    GET  /library/note/<id>/<name>  one round of feedback, read back -- which is
                                    where the turn wrote what it changed
    POST /library/feedback          one round of feedback, written where the
                                    document is, and then acted on -- in words,
                                    in ink, or in both

AN ID, NEVER A PATH. What arrives from the browser is compared against what
discovery found -- `library.find` -- and a miss is a miss. `reading.find` is the
rule and `/result/` is the worked example. A NOTE'S NAME is the same rule one
level down: matched against the names `library.notes` found beside that
document, never joined onto a directory.

AND FEEDBACK IS NEVER JUST FILED. A note nothing acts on is a note the person
believes is in force, which is the same defect `/direction` was built to avoid.
So writing one dispatches the revision in the same request, and the reply says
which machinery took it: the board revises a document it compiled, and
Paper-Writer revises a manuscript it delivered.

TWO ASKS, NOT ONE. `revise` is a correction and keeps the document's structure,
its names for things and its claims. `rework` is an overhaul -- "that
presentation needs an overhaul now that we plan to use colibri" -- and may
restructure, cut, reorder and rewrite. It costs a sentence saying what the
document is FOR now, and it is refused against an uncommitted source, because
git is the only undo an overhaul has.
"""

import json
import time
from urllib.parse import unquote

from . import NOT_MINE
from .. import spawn
from ... import leaving, manuscript, sense
from ...course import library
from ...lesson import turns


def get(h, repo, path):
    if path == "/library.json":
        return h.send_json(library.status(repo))

    # HAS ANYTHING MOVED. Asked every few seconds while the page is in front of
    # somebody, so it is stats and nothing else -- no titles read out of
    # sources, no `pdfinfo`, no notes listed. `/library.json` is the expensive
    # answer and is fetched only once this says the answer has changed.
    if path == "/library/stamp":
        try:
            return h.send_json(library.stamp(repo.root))
        except Exception as exc:                             # noqa: BLE001
            # A poll that 500s makes the page paint "the board is not
            # answering", which points a reader at the network for a fault that
            # is a walk of a directory.
            return h.send_json({"ok": False, "error": str(exc)})

    if path.startswith("/library/view/"):
        # The same rasteriser, the same cache and the same `/paper/<name>.png`
        # page addresses the lesson's own documents use. What differs is only
        # how the file was found.
        return h.send_json(library.pages(repo, path[len("/library/view/"):]))

    # WHAT A ROUND ACTUALLY SAID. The turn writes `## What was changed` at the
    # bottom of the feedback file, and that is the answer to *did it do what I
    # asked* -- in a file the iPad cannot open. An id and a name, both matched
    # against what discovery found.
    if path.startswith("/library/note/"):
        rest = path[len("/library/note/"):].split("/", 1)
        doc = library.find(repo.root, rest[0] if rest else "")
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        got = library.note_text(repo.root, doc,
                                unquote(rest[1]) if len(rest) > 1 else "")
        return h.send_json(got, status=200 if got.get("ok") else 404)

    return NOT_MINE


def post(h, repo, path):
    if path == "/library/feedback":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        ident = str(payload.get("document") or "").strip()
        text = payload.get("text") or ""
        ask = library.clean_ask(payload.get("ask"))
        purpose = payload.get("purpose") or ""
        try:
            page = int(payload.get("page") or 0)
        except (TypeError, ValueError):
            page = 0
        doc = library.find(repo.root, ident)
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        if ask == "rework":
            stop = rework_refused(repo, doc)
            if stop:
                # NOTHING IS WRITTEN WHEN THIS REFUSES. A note filed for an
                # overhaul that never started is a note somebody believes is in
                # force, which is the defect the whole route was built against.
                return h.send_json({"ok": False, "ask": "rework",
                                    "error": stop}, status=409)
        rec = library.write_note(repo, ident, text, page=page, ask=ask,
                                 purpose=purpose)
        if not rec.get("ok"):
            return h.send_json(rec, status=400)
        rec.update(_revise(h, repo, doc, rec["rel"], ask=ask,
                           purpose=rec.get("purpose") or ""))
        return h.send_json(rec)

    return NOT_MINE


def rework_refused(repo, doc):
    """Why this document may not be overhauled from here, or "".

    THREE REFUSALS, AND EACH NAMES WHAT IS IN THE WAY. `worktree.busy_reason`
    is the shape: this runs where nobody is reading a terminal, so it says what
    is in the way, changes nothing, and leaves a sentence the board can paint.

    THE SOURCE HAS TO BE COMMITTED. An overhaul replaces a whole document and
    git is the only undo there is; committed as it stands, the whole overhaul is
    one diff and reverting it costs nothing. The board refuses rather than
    committing on somebody's behalf -- a commit of a half-finished edit is a
    worse undo than none, because the state they would revert to is one they
    never chose.

    A DELIVERED MANUSCRIPT IS NOT OVERHAULED FROM HERE either, and that is the
    same seam `_revise` holds one function down. The factory owns the evidence,
    the terminology lock, the reporting checklist and the venue's word limit,
    and "restructure, cut and rewrite" is the one instruction every one of those
    gates exists to refuse. A paper whose purpose has changed is a new paper and
    is asked for as one.
    """
    if doc.get("made") == "paper-writer":
        return ("%s was delivered by the manuscript factory, and an overhaul is "
                "not something that comes back through here: the factory holds "
                "its evidence, its terminology lock and its venue. Say what is "
                "wrong with it instead, or ask for a new paper."
                % doc["title"])
    src = doc.get("source") or ""
    if not src:
        return ("%s has no source in this repository -- there is only a built "
                "file -- so there is nothing to rework."
                % doc["title"])
    if leaving.uncommitted(repo.root, src):
        # AND IT NAMES A TAP RATHER THAN A COMMAND. The whole point of this
        # surface is that the laptop is not opened, so a refusal whose remedy is
        # `git commit` has sent somebody to a keyboard to get past the board's
        # own guard. `⤓ save` on the board is that commit and is already there.
        return ("`%s` has changes nothing has committed, and an overhaul "
                "replaces the whole document: git is the only undo it has. Tap "
                "⤓ save on the board to commit it as it stands, then ask again "
                "-- the overhaul is one diff after that. Nothing has been "
                "written." % src)
    return ""


def _revise(h, repo, doc, note_rel, ask="revise", purpose=""):
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

    `ask` is which of the two the person tapped, and it changes the signal, the
    prompt that turn is woken with and how long it gets -- see `turn_plan` and
    `doing_now` in `bin/tutor`. It never reaches the factory: `rework_refused`
    has already turned an overhaul of a delivered manuscript away by name.
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

    # AN OVERHAUL IS A DIFFERENT SIGNAL AND A DIFFERENT PROMPT, and it names the
    # SOURCE rather than the rendering: that is the file whose committed state
    # was just checked, and it is the file the turn edits.
    if ask == "rework":
        line = "[rework] " + sense.rework_sense(doc.get("source") or doc["rel"],
                                                note_rel, purpose)
    else:
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
        "from": "student", "text": line, "signal": ask, "read": False,
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
        h.note("nothing was reading the board; starting a tutor for %s"
               % ("an overhaul" if ask == "rework" else "a revision"))
    h.server.hub.worker.dirty.set()
    return {"revise": "board", "asked": True,
            "detail": ("The tutor has been asked to rework it, and an overhaul "
                       "takes longer than a correction. That turn is not part "
                       "of the lesson: it writes no card and leaves the sitting "
                       "on the board alone."
                       if ask == "rework" else
                       "The tutor has been asked to revise it. That turn is not "
                       "part of the lesson: it writes no card and leaves the "
                       "sitting on the board alone.")}
