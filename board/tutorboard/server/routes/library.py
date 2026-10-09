"""The library: every document this workspace has written, and feedback on one.

A SURFACE RATHER THAN A SITTING, and that is the whole design. Nothing here
writes to `live/cards/`, archives a lesson or touches `live/state.json`, because
somebody mid-proof on an iPad must not be interrupted by somebody correcting a
deck. What a note does is land beside the document it is about and wake a turn
that is not the lesson's.

    GET  /library.json              everything `course/library.py` found
    GET  /shelf.json                the same inventory GROUPED BY THE BOX ON
                                    THE MAP each document belongs to, which is
                                    what the map's own drawer opens
    GET  /library/results.json      everything this workspace PRODUCED, grouped
                                    by the directory it came out of -- or a
                                    sentence saying why there is nothing
    GET  /library/table/<id>        one table, read back as rows or as text,
                                    because a page cannot open a file
    POST /writeup                   a paper or a deck, asked for from a sitting
                                    on this board or commissioned from the front
                                    door against any workspace on the machine
    POST /writeup/seen              one finished ask waved off the board's strip
    GET  /library/stamp             one hash of where every document is and
                                    when it last changed, cheap enough to ask
                                    every few seconds
    GET  /library/view/<id>         the pages of one, drawn by the renderer the
                                    board already has
    GET  /library/marked/<id>/<name> a marked copy `POST /annotate/burn` made
                                    of one, as an attachment
    GET  /library/note/<id>/<name>  one round of feedback, read back -- which is
                                    where the turn wrote what it changed
    GET  /library/ledger/<id>       every round's requests, what was done about
                                    each, and where each sits on the pages now
    GET  /library/evidence/<id>/<note>/<file>
                                    one crop or page picture a request keeps
    POST /library/ledger/preview    how the panel's words and ink would split
                                    into requests, before anything is sent
    POST /library/ledger/state      one request accepted, or reopened with why
    POST /library/feedback          one round of feedback, written where the
                                    document is, and then acted on -- in words,
                                    in ink, or in both
    POST /doc/delete                one artifact `{subject, id}`, after a
                                    second tap: to the trash with its ink, and
                                    its tracked files out in one commit

WHERE EACH IS SERVED (`handler.UNPREFIXED` is the table that serves them):

    subject   under `/s/<id>/` for the session's own subject, or unprefixed
              with `?subject=<id>` from the library page:
              /library.json  /library/stamp  /library/results.json
              /library/table/*  /library/view/*  /library/note/*
              /library/ledger/* (GET and POST)  /library/evidence/*
              /library/feedback  /library/direction  /doc/delete  /writeup
    session   under `/s/<id>/` only: /shelf.json  /library/marked/*
              /writeup/seen

AN ASK OF A TUTOR THAT IS NOT THIS SESSION'S -- feedback or a write-up from
the library page, a write-up for another subject, the meeting deck -- goes
through `registry.runner_route`, which picks the
session. Only a session asking its own tutor writes its own inbox.

AN ID, NEVER A PATH. What arrives from the browser is compared against what
discovery found -- `library.find` -- and a miss is a miss. `reading.find` is the
rule and `/result/` is the worked example. A NOTE'S NAME is the same rule one
level down: matched against the names `library.notes` found beside that
document, never joined onto a directory. A WORKSPACE and a SCOPE KEY on
`/writeup` are the same rule again: `machines.workspaces` and `scopes.find` are
the lists, and the root comes off the match.

A DOCUMENT IS NOT THE ONLY THING A WORKSPACE MAKES, which is why the results
are on this page rather than on a second one. A mission ends by naming what it
wrote -- *figure `neighbor_count_sweep.png` and four tables* -- and until there
was somewhere to look at those, the only way to read a finished result was a
terminal. `course/results.py` already knew where every one of them is: the
drawer puts a figure in a card, and what was missing was the list. One page,
because "everything this workspace has produced" is one question, and because
this is the page somebody already knows how to reach -- the front door offers it
per workspace and the board's ⋯ menu opens it.

AND FEEDBACK IS NEVER JUST FILED. A note nothing acts on is a note the person
believes is in force, which is the same defect `/direction` was built to avoid.
So writing one dispatches the revision in the same request: a `[revise]` turn
edits the document's source and rebuilds it with `board build`.

TWO ASKS, NOT ONE. `revise` is a correction and keeps the document's structure,
its names for things and its claims. `rework` is an overhaul -- "that
presentation needs an overhaul now that we plan to use colibri" -- and may
restructure, cut, reorder and rewrite. It costs a sentence saying what the
document is FOR now, and it is refused against an uncommitted source, because
git is the only undo an overhaul has.
"""

import json
import os
import re
import time
from urllib.parse import unquote

from . import NOT_MINE
from . import writing
from .. import registry
from ...runner import service as runner
from ... import (artifacts, atlas, briefs, fenced, leaving, machines, paths,
                 scopes, sense, subjects, writeups)
from ...course import burn
from ...course import config
from ...course import ledger
from ...course import library
from ...course import results
from ...course import shelf
from ...lesson import turns


def get(h, repo, path):
    if path == "/library.json":
        return h.send_json(library.status(repo))

    # EVERY DOCUMENT, UNDER THE BOX IT BELONGS TO. The same inventory the page
    # above draws, ordered the way the map orders its boxes, because it is read
    # beside the picture. Fetched on a tap and never on the payload: the map's
    # payload carries the COUNT per box, which is four bytes, and this is the
    # list.
    if path == "/shelf.json":
        try:
            return h.send_json(shelf.grouped(repo))
        except Exception as exc:                             # noqa: BLE001
            # The same reason `/library/stamp` catches: a 500 here paints "the
            # board is not answering" over a fault that is a directory walk.
            return h.send_json({"ok": False, "error": str(exc)})

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

    # WHAT THIS WORKSPACE HAS PRODUCED. Its own fetch rather than a field on
    # `/library.json`, because they are two walks of two different trees: the
    # documents walk reads titles out of sources and runs `pdfinfo` per PDF, and
    # this one walks the result directories. The page draws whichever arrives
    # first, and a workspace with no results still gets its documents.
    if path == "/library/results.json":
        try:
            return h.send_json(results.browse(repo))
        except Exception as exc:                             # noqa: BLE001
            # The same reason `/library/stamp` catches: a 500 here paints "the
            # board is not answering" over a fault that is a directory walk.
            return h.send_json({"ok": False, "error": str(exc)})

    # ONE TABLE, READ HERE RATHER THAN DOWNLOADED. A CSV handed to a browser is
    # a file an iPad puts somewhere nobody can find. An id, never a path --
    # `results.table` does the same lookup `/result/` does, with the kind it
    # will answer for changed, and a miss is a miss.
    if path.startswith("/library/table/"):
        got = results.table(repo.root, unquote(path[len("/library/table/"):]))
        return h.send_json(got, status=200 if got.get("ok") else 404)

    # A MARKED COPY, handed over to be kept. An id and a name, both matched
    # against what is on disk under `live/marked/<id>/` -- `burn.marked_file`
    # -- and sent as an attachment, because it is asked for to go into Files.
    if path.startswith("/library/marked/"):
        rest = path[len("/library/marked/"):].split("/", 1)
        found = burn.marked_file(repo, rest[0] if rest else "",
                                 unquote(rest[1]) if len(rest) > 1 else "")
        if not found:
            return h.send_json({"ok": False, "error": "no such copy"},
                               status=404)
        return h.send_file(found, download=os.path.basename(found))

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

    # WHAT EACH REQUEST WAS AND WHAT WAS DONE ABOUT IT, placed on the build
    # that is on disk now. An id, matched against discovery like every other.
    if path.startswith("/library/ledger/"):
        # Either name: the board's document drawer asks by its own (`find_any`).
        doc = library.find_any(repo.root, unquote(path[len("/library/ledger/"):]))
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        try:
            return h.send_json(ledger.view(repo, doc))
        except Exception as exc:                             # noqa: BLE001
            return h.send_json({"ok": False, "error": str(exc)[-300:]})

    # A REQUEST'S OWN PICTURE. An id, a round's name and a file's name, each
    # matched against what is on disk -- `ledger.evidence` -- never joined.
    if path.startswith("/library/evidence/"):
        rest = path[len("/library/evidence/"):].split("/")
        doc = library.find(repo.root, rest[0]) if len(rest) == 3 else None
        found = (ledger.evidence(repo.root, doc, unquote(rest[1]), unquote(rest[2]))
                 if doc else "")
        if not found:
            return h.send_json({"ok": False, "error": "no such picture"},
                               status=404)
        return h.send_file(found)

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
        merge = _pages(payload.get("merge"))
        doc = library.find(repo.root, ident)
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        # A PIECE IS CORRECTED THROUGH ITS WHOLE. The note and the ink stay on
        # the section they were written on; the revision is asked of the
        # document the section is re-cut from, by that document's machinery.
        whole = (library.find(repo.root, doc.get("whole") or "")
                 if doc.get("piece") else None)
        if doc.get("piece") and ask == "rework":
            return h.send_json({"ok": False, "ask": "rework", "error": (
                "%s is one section of %s, cut from it, so an overhaul of it "
                "alone is lost on the next cut. Overhaul the whole document "
                "instead. Nothing has been written."
                % (doc["title"], (whole or {}).get("title") or "a larger document"))},
                status=409)
        if ask == "rework":
            stop = rework_refused(repo, doc)
            if stop:
                # NOTHING IS WRITTEN WHEN THIS REFUSES. A note filed for an
                # overhaul that never started is a note somebody believes is in
                # force, which is the defect the whole route was built against.
                return h.send_json({"ok": False, "ask": "rework",
                                    "error": stop}, status=409)
        rec = library.write_note(repo, ident, text, page=page, ask=ask,
                                 purpose=purpose, hand_over=False, merge=merge)
        if not rec.get("ok"):
            return h.send_json(rec, status=400)
        keys = rec.pop("keys", [])
        carry = rec.pop("carry", [])
        rec.update(_revise(h, repo, whole or doc, rec["rel"], ask=ask,
                           purpose=rec.get("purpose") or "",
                           ledger_rel=rec.get("ledger") or "",
                           ids=rec.get("ids") or []))
        # THE INK IS DELIVERED WHEN THE REVISION IS ASKED, not when the note is
        # written: a note beside an ask that failed has delivered nothing, and
        # marking its ink sent would leave the retry without it. A reopened
        # request is carried on the same rule.
        if rec.get("asked"):
            library.hand_over(repo, keys)
            ledger.carry(repo.root, doc, carry, rec.get("note") or "")
        elif rec.get("path"):
            # NOTHING IS ANSWERING THIS ROUND. It stays on disk and counts
            # nowhere; the retry files the same ink and the same reopened
            # requests again, so each is counted once.
            ledger.mark_unsent(rec["path"], rec.get("detail") or "")
        return h.send_json(rec)

    # THE SPLIT, SHOWN BEFORE IT IS SENT. What the panel's words and the
    # document's ink would become as requests, so "that was one request, not
    # three" is said with a tap before the round rather than in the next one.
    # Nothing is written.
    if path == "/library/ledger/preview":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        doc = library.find(repo.root, str(payload.get("document") or "").strip())
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        try:
            page = int(payload.get("page") or 0)
        except (TypeError, ValueError):
            page = 0
        found = library.carried(repo, doc, library.marks(repo, doc))
        items = ledger.preview(repo, found, payload.get("text") or "", page=page,
                               merge=_pages(payload.get("merge")),
                               round_no=ledger.next_round(repo.root, doc),
                               reopen=ledger.reopened(repo.root, doc))
        return h.send_json({"ok": True, "items": items})

    # ONE REQUEST CLOSED OR REOPENED. A reopened one costs a line of why, and
    # rides the next round under the id it already has.
    if path == "/library/ledger/state":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        doc = library.find(repo.root, str(payload.get("document") or "").strip())
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        got = ledger.set_state(repo.root, doc, str(payload.get("note") or ""),
                               str(payload.get("id") or ""),
                               payload.get("state"), payload.get("why") or "")
        library.forget()
        return h.send_json(got, status=200 if got.get("ok") else 400)

    # A PAGE MARKED AS A DIRECTION, not as a complaint: the note panel's third
    # ask. It never goes near `_revise` -- see `proposals.from_document`.
    if path == "/library/direction":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        doc = library.find(repo.root, str(payload.get("document") or "").strip())
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        from ... import proposals                      # local: avoids a cycle
        # THE PAGES THE READER PICTURED FOR THIS SEND, each with how many
        # direction strokes it had then. Only those go; a missing list sends
        # nothing drawn.
        pictured = {}
        for it in payload.get("pictured") or []:
            if isinstance(it, dict) and writing.ann_ok(str(it.get("key") or "")):
                try:
                    pictured[str(it["key"])] = int(it.get("n"))
                except (TypeError, ValueError):
                    pass
        rec = proposals.from_document(repo, doc, payload.get("page"),
                                      payload.get("text") or "", pictured)
        # THE INK LEFT ON THE DOCUMENT, so the reader takes the sent direction
        # strokes off its glass: `Annotate.load` never takes a mark away. The
        # reader refreshes the keys named in `stripped` and drops the strokes
        # in `wiped`.
        if rec.get("ok"):
            rec["ink"] = library.ink(repo, doc)
            rec["wiped"] = library.wiped(repo, doc)
        h.hub.worker.dirty.set()
        return h.send_json(rec, status=200 if rec.get("ok") else 400)

    if path == "/writeup":
        return _writeup(h, repo)

    if path == "/doc/delete":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            payload = {}
        got, code = delete_doc(repo, str(payload.get("subject") or "").strip(),
                               str(payload.get("id") or "").strip().lower())
        if got.get("ok"):
            h.hub.worker.dirty.set()
        return h.send_json(got, status=code)

    if path == "/writeup/seen":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        # A `writing` one cannot be waved away: it is still being written, and
        # that is the fact the strip is reporting. `writeups.seen` refuses it.
        got = writeups.seen(repo.root, str(payload.get("id") or ""))
        h.hub.worker.dirty.set()
        return h.send_json({"ok": bool(got)})

    return NOT_MINE


def _writeup(h, repo):
    """A PAPER OR A DECK, ASKED FOR FROM ANY SITTING, WITHOUT CHANGING IT.

    **The want, and it was asked as a question:** *"at any point can I have a
    presentation or paper written up going through the things we talked about in
    that tutoring session? Can I do that in ANY tutoring session?"* The answer
    was no, twice over.

    A DOCUMENT IS AN ACTION, NOT A MODE. A paper or a deck is a PRODUCT any
    session can ask for: this changes no mode, archives nothing, replaces no
    tutor, and is therefore available everywhere, like everything else on this
    page.

    IT IS IN THIS FILE RATHER THAN BESIDE `/mode`, because every rule that makes
    it safe is this file's: no card, no sitting, no `state.json`. The document
    lands in the library and the library's own loop corrects it.

    AND NOTHING GOES IN THE TRANSCRIPT, which is the one place this differs from
    `/mode` and `/handover`. Both of those put the tap in as a turn of the
    student's, because a card is coming back and a transcript that opens with the
    answer reads as the tutor deciding something on its own. Here no card is
    coming: a student turn with no reply is what sets `awaitingReply`, and the
    board would sit waiting for a card that this turn is told not to write. So
    what says it is happening is the RECORD -- `tutorboard/writeups.py` -- which
    the board paints in the strip and which survives a closed lid, and the reply
    carries its id.

    THE SCOPE IS THE EVENING UNLESS THEY SAID OTHERWISE. A box tapped on the map
    already opens a make sitting scoped to that box; the ask with no route at all
    was *"write up the four things we just covered"*, so that is the default and
    `sense.writeup_sense` says how to read the lesson back for it.

    AND IT CAN BE COMMISSIONED FROM THE FRONT DOOR, AGAINST A WORKSPACE NOBODY
    IS LOOKING AT. Asked for in these words: *"the ability to write a paper or a
    slide deck should just be an option on the homescreen, and from there I want
    to be able to specify which projects/course, and which sections/results."*
    So `repo` names the workspace and `scope` names what it is over -- a key
    from `POST /writeup/scopes`, resolved through `tutorboard/scopes.py` against
    the TARGET's root and never joined onto a path. A scope beats a free-text
    `about`, because one of them was picked off a list of what is really there
    and the other was typed.

    THE DOCUMENT THEN LANDS IN THAT WORKSPACE'S LIBRARY, WHICH IS NOT THE BOARD
    THAT COMMISSIONED IT. Nothing on this board changes and nothing appears in
    its library: the record, the inbox line and the finished document are all
    written over there, and the way back to them is that workspace's own
    library page. The reply says which workspace it went to for exactly that
    reason -- an ask whose product appears somewhere else has to say where.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    makes = writeups.clean_makes(payload.get("makes"))
    if not makes:
        # Named rather than defaulted. Which of the two is known at the moment of
        # tapping -- there are two controls for exactly that reason -- so a
        # request that does not say has gone wrong somewhere worth hearing about.
        return h.send_json({"ok": False, "error": "paper or slides"}, status=400)

    # WHICH WORKSPACE THE DOCUMENT IS FOR, and it is this one unless the request
    # says otherwise. `/elsewhere` and `/switch` resolve a name the same way:
    # matched against what the walk already found, with the ROOT taken off the
    # match rather than rebuilt out of the name, because the same name can sit
    # under two families.
    #
    # THE BOARD'S OWN WORKSPACE ANSWERS TO ITS OWN NAME WHETHER OR NOT THE WALK
    # CAN SEE IT, and it is answered for FIRST. A board serves exactly one root,
    # it was handed the `Repo` for it, and building a second object for the
    # directory it is already sitting in is two objects that can disagree about
    # one lesson.
    want = str(payload.get("repo") or "").strip()
    match = None
    if want and want not in (os.path.basename(os.path.realpath(repo.root)),
                             atlas.identify(repo.root)):
        for c in machines.workspaces(repo):
            if want in (c["repo"], c["id"]):
                match = c
                break
        if not match:
            return h.send_json({"ok": False, "error": "unknown workspace"},
                               status=404)
    # THE ROOT NOW, THE `Repo` ONLY ONCE THE ASK IS ALLOWED. Constructing one
    # is not a read: `Repo.__init__` calls `ensure_dirs`, which makes `live/`
    # and its eight subdirectories, and it does that because a long-lived board
    # has to put back what git removed under it. Here it would mean a REFUSED
    # request -- an unknown scope, an assistant already busy -- leaving a live
    # directory behind in a workspace that was never written in, which is the
    # opposite of what the two comments below promise.
    root = match["root"] if match else repo.root
    where_dir = match["repo"] if match else os.path.basename(
        os.path.realpath(repo.root))
    where_name = ((match["course"] or match["repo"]) if match
                  else (config.read_config(repo.root)["name"] or where_dir))

    about = str(payload.get("about") or "").strip()[:writeups.ABOUT_CHARS]
    key = str(payload.get("scope") or "").strip()
    if key:
        # A KEY, LOOKED UP IN THE TARGET'S OWN LIST. Resolved against the
        # workspace the document is FOR, not against this one: the chapters on
        # offer are that course's chapters, and a key resolved here would answer
        # with the wrong sentence or with none. Nothing is written before this
        # answers -- a scope nobody recognises is a document about the wrong
        # thing, which is worse than a refusal.
        found = scopes.find(root, key)
        if not found:
            return h.send_json({"ok": False, "error": "no such scope"},
                               status=400)
        # AND IT BEATS FREE TEXT. One of the two was picked off a list of what
        # that workspace really has and the other was typed; where both arrived,
        # the request has two minds and the list is the one to trust. Clamped
        # like the typed one: the record stores `about[:ABOUT_CHARS]` either
        # way, and a sentence that goes to the assistant whole while the record
        # and the strip carry it cut is one ask described two ways.
        about = found["about"][:writeups.ABOUT_CHARS]

    got = _dispatch_writeup(h, repo, match, makes, about)
    if not isinstance(got, dict):
        return got
    return h.send_json({"ok": True, "id": got["id"], "makes": makes,
                        "about": got["rec"].get("about") or "", "state": "writing",
                        "repo": where_dir, "where": where_name,
                        "session": got.get("session"),
                        "detail": (("It is being written in %s and will appear "
                                    "in THAT workspace's library rather than "
                                    "this one. Nothing on this board changes."
                                    % where_name) if match else
                                   ("It is being written now and will appear in "
                                    "the library. That turn is not part of the "
                                    "lesson: it writes no card and leaves the "
                                    "sitting on the board alone."))})


def _dispatch_writeup(h, repo, match, makes, about, line=None, prepare=None,
                      ask=None):
    """Ask for a document in the workspace `match` names -- or this one, where
    `match` is None -- and return `{id, rec, root}`, or the refusal already sent.

    `/writeup`'s own body. `line` is the inbox line where the caller has its
    own, and `prepare` is called with the target Repo and the ask's id once the
    ask is allowed and before it is recorded -- the meeting deck writes its
    brief there, so a refusal leaves nothing behind and a recorded ask always
    has its brief. A dict it returns may name the artifact (`doc_dir`) the ask
    is judged by.
    """
    got, err = dispatch(repo, match, makes, about, line=line, prepare=prepare,
                        ask=ask)
    if err:
        return h.send_json(err[0], status=err[1])
    if got.get("woke"):
        h.note("nothing was reading the board; starting a tutor to write it")
    h.hub.worker.dirty.set()
    return got


class _Refusal(Exception):
    """A write-up refused once its target was known: `(payload, status)`."""

    def __init__(self, payload, status):
        Exception.__init__(self, payload.get("error") or "")
        self.payload, self.status = payload, status


def dispatch(repo, match, makes, about, line=None, prepare=None, ask=None):
    """`_dispatch_writeup` without a request: `({id, rec, root, woke}, None)`,
    or `(None, (payload, status))` for a refusal. The meeting deck is asked for
    from the command line through this as well as from the front door, so the
    two entry points are one order of things.

    THE ASK GOES TO THE SESSION'S OWN TUTOR only when it is for the session's
    own subject. One for another subject (`match`), or made with no session
    at all (a sessionless Repo: the front door, the library page), goes
    through `registry.runner_route`, which picks the session it lands in.
    Nothing is written until the target is known, so a refusal leaves nothing
    behind.
    """
    made = {}

    def ready(target, wid):
        """Make what the ask needs in `target`, and return the inbox text."""
        doc_dir, text = None, line
        if line is None and prepare is None:
            # A PLAIN ASK MAKES ITS ARTIFACT FIRST, so the strip is judged by
            # its doc.json and the turn is told the exact file.
            try:
                art = artifacts.create(
                    target.root,
                    about[:80] or ("Slides" if makes == "slides" else "Paper"),
                    session=target.live if target.stored else None,
                    ext=".tex" if makes == "slides" else ".md")
            except (ValueError, OSError) as exc:
                raise _Refusal({"ok": False, "error": "no document could be made "
                                "here: %s" % exc}, 409)
            doc_dir = art["rel"]
            src = "%s/%s" % (art["rel"], art["source"])
            text = ("[writeup] " + sense.writeup_sense(makes, about)
                    + " THE FILE FOR THIS ONE IS `%s`, that name exactly, and it "
                      "outranks `writeups/<slug>/` above: the board finds the "
                      "document by it. %s Build it with `board build %s`."
                    % (src, "It is a beamer `.tex`." if makes == "slides" else
                       "It is Markdown.", src))
        if prepare:
            try:
                got = prepare(target, wid)
            except Exception as exc:                         # noqa: BLE001
                raise _Refusal({"ok": False,
                                "error": "nothing could be prepared: %s" % exc}, 500)
            if isinstance(got, dict) and got.get("doc_dir"):
                doc_dir = got["doc_dir"]
        made["rec"] = writeups.ask(target.root, wid, makes, about,
                                   agent=config.sitting_agent(target.root) or "",
                                   doc_dir=doc_dir,
                                   session=(os.path.basename(target.live)
                                            if target.stored else None))
        return {"text": text or ("[writeup] " + sense.writeup_sense(makes, about))}

    record = {"rev": 0, "kind": "text", "answers": None, "from": "student",
              "signal": "writeup", "read": False}
    if match or registry.is_sessionless(repo):
        subject = match["id"] if match else registry.subject_of(repo)
        try:
            got = registry.runner_route(
                subject, record, base=registry.base_of(repo), before=ready,
                ask=ask or ("a deck" if makes == "slides" else "a paper"))
        except LookupError:
            return None, ({"ok": False, "error": "unknown workspace"}, 404)
        except _Refusal as no:
            return None, (no.payload, no.status)
        except OSError as exc:
            return None, ({"ok": False,
                           "error": "nothing could be asked: %s" % exc}, 500)
        return {"id": got["id"], "rec": made["rec"], "root": got["repo"].root,
                "session": got["session"], "woke": False}, None

    # An id from the same series the lesson's turns use, so nothing in the
    # inbox has to be told apart by shape. NOT written into `turns.jsonl`; see
    # `_writeup`.
    wid = turns.next_turn_id(repo)
    try:
        record.update(ready(repo, wid))
    except _Refusal as no:
        return None, (no.payload, no.status)
    record.update(id=wid, t=time.time(), iso=time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        return None, ({"ok": False,
                       "error": "nothing could be asked: %s" % exc}, 500)
    # Queued on the runner, the same as `/say` and `_revise`.
    woke = bool(runner.wake(repo))
    return {"id": wid, "rec": made["rec"], "root": repo.root, "woke": woke}, None


SUBJECT_ID = re.compile(r"\A(?:courses|projects|research|practice)/[A-Za-z0-9._-]+\Z")


def delete_doc(repo, subject, ident):
    """`POST /doc/delete`: `(payload, status)`.

    AN ID AND A SUBJECT ID, NEVER A PATH. The subject is this board's own, or
    a qualified id matched against `subjects.find`; the document is matched
    against what the library found there. A fenced name anywhere in either is
    403 before anything is looked up, and `artifacts.delete` refuses a fenced
    path again on its own.
    """
    served = (subjects.find(repo.root) or {}).get("id") or ""
    if fenced.refused(subject) or fenced.refused("%s/%s" % (artifacts.DOCS, ident)):
        return {"ok": False, "error": "that is under a fence"}, 403
    if not subject or subject == served:
        root = repo.root
    elif SUBJECT_ID.match(subject):
        found = subjects.find(subject)
        if not found or found["id"] != subject:
            return {"ok": False, "error": "no such subject"}, 404
        root = found["root"]
    else:
        return {"ok": False, "error": "no such subject"}, 404
    if not ident or not writing.ANN_DOC.match("doc/%s/p1" % ident):
        return {"ok": False, "error": "no such document"}, 404
    library.forget()
    doc = library.find(root, ident)
    if not doc or not doc.get("artifact"):
        return {"ok": False, "error": (
            "no such document" if not doc else
            "%s has no doc.json, so it is not the board's to delete"
            % doc["title"])}, 404
    if fenced.refused(doc["artifact"]):
        return {"ok": False, "error": "that is under a fence"}, 403
    from ... import sessions                        # local: a cycle through artifacts
    ink = [os.path.join(root, sessions.INK)]
    if paths.same_dir(root, repo.root):
        ink.append(repo.notes)
    got = artifacts.delete(root, os.path.join(root, *doc["artifact"].split("/")),
                           idents=library.mark_idents(root, doc), ink_dirs=ink)
    library.forget()
    if got.get("fenced"):
        return {"ok": False, "error": got["said"]}, 403
    got.pop("trash", None)
    return dict(got, id=doc["id"], title=doc["title"]), (200 if got["ok"] else 500)


def _pages(got):
    """Page numbers off a request, or []. Anything that is not one is dropped."""
    if not isinstance(got, list):
        return []
    out = []
    for x in got[:200]:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.append(n)
    return out


def _strings(payload, key):
    """A list of strings off a request, or []. Nothing else from it is read."""
    got = payload.get(key)
    if not isinstance(got, list):
        return []
    return [str(x) for x in got if isinstance(x, (str, int))][:500]


def ask_meeting(repo, base, since_ts, human, want=None):
    """Ask for THE MEETING DECK: `({id, host, where, dir, record}, None)`, or
    `(None, (payload, status))`.

    The period and the subjects choose what the brief holds
    (`briefs.blocks_for`). The ask goes through `dispatch` to projects/Meetings,
    whose newest open session takes it (`runner_route`); `briefs.replace` runs
    once the session is chosen and before the ask is recorded, so a refusal
    leaves the last deck standing.
    """
    blocks, every, why = briefs.blocks_for(base, want, since_ts)
    if why:
        return None, ({"ok": False, "detail": why}, 400)
    if not blocks:
        return None, ({"ok": False, "detail": (
            "Nothing landed in %s in %s, so there is nothing to present. "
            "Choose a longer period." % (human, ", ".join(
                s["id"] for s in every) or "any subject"))}, 400)
    if not briefs.meetings_root(base):
        return None, ({"ok": False, "detail": (
            "%s is missing; `board bind %s --create --phi yes` makes it"
            % (briefs.MEETINGS, briefs.MEETINGS))}, 409)
    period = briefs.period_text(since_ts)
    rel = briefs.deck_rel()
    about = ("the meeting deck for %s, briefed in %s/%s"
             % (period, rel, briefs.BRIEF_MD))[:writeups.ABOUT_CHARS]
    line = "[writeup] " + sense.writeup_sense("slides", sense.meeting_about(
        rel, period, "%s/%s" % (briefs.MEETINGS, rel)))
    made = {}

    def prepare(target, wid):
        made["rec"] = briefs.replace(
            base, blocks, since_ts, human,
            session=os.path.basename(target.live) if target.stored else None,
            ink=briefs.ink_dirs(base, repo))
        return made["rec"]

    got, err = dispatch(repo, {"id": briefs.MEETINGS}, "slides", about, line=line,
                        prepare=prepare, ask="the meeting deck")
    if err:
        payload = dict(err[0])
        payload.setdefault("detail", payload.get("error") or "")
        return None, (payload, err[1])
    brief = made.get("rec", {}).get("brief") or {}
    return {"id": got["id"], "host": briefs.MEETINGS, "where": "Meetings",
            "dir": "%s/%s" % (briefs.MEETINGS, rel), "record": brief,
            "woke": got.get("woke"), "session": got.get("session")}, None


def meeting_deck(h, repo, base, since_ts, human, want=None):
    """`POST /meeting`: the meeting deck asked for, and the page told it is
    being written. The page then watches `/meeting/deck.json`."""
    got, err = ask_meeting(repo, base, since_ts, human, want=want)
    if err:
        return h.send_json(err[0], status=err[1])
    h.hub.worker.dirty.set()
    rec = got["record"]
    return h.send_json({
        "ok": True, "id": got["id"], "name": "meeting", "state": "being written",
        "host": got["host"], "where": got["where"], "dir": got["dir"],
        "session": got.get("session"),
        "workspaces": rec.get("subjects") or [],
        "names": rec.get("names") or {}, "since": human,
        "period": rec.get("period") or "",
        "detail": ("The assistant is writing it in Meetings. It takes several "
                   "minutes, and this sheet says when it is ready. It replaces "
                   "the deck before it.")})


def rework_refused(repo, doc):
    """Why this document may not be overhauled from here, or "".

    TWO REFUSALS, AND EACH NAMES WHAT IS IN THE WAY. `worktree.busy_reason`
    is the shape: this runs where nobody is reading a terminal, so it says what
    is in the way, changes nothing, and leaves a sentence the board can paint.

    THE SOURCE HAS TO BE COMMITTED. An overhaul replaces a whole document and
    git is the only undo there is; committed as it stands, the whole overhaul is
    one diff and reverting it costs nothing. The board refuses rather than
    committing on somebody's behalf -- a commit of a half-finished edit is a
    worse undo than none, because the state they would revert to is one they
    never chose.
    """
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


def _revise(h, repo, doc, note_rel, ask="revise", purpose="", ledger_rel="",
            ids=()):
    """Ask for the revision: a `[revise]` line in the inbox and a turn woken on it.

    Every document is revised the same way, whoever wrote it. That turn runs
    FRESH and writes no card; see `HEADLESS_REVISE_PROMPT` in `runner/prompts.py` for
    why a resumed one would drag the lesson into the document. The line names
    the source, and the turn rebuilds it with `board build`.

    `ask` is which of the two the person tapped, and it changes the signal, the
    prompt that turn is woken with and how long it gets -- see `turn_plan` and
    `doing_now` in `runner/turn.py`.

    `ledger_rel` and `ids` are the round's requests (`course/ledger.py`). The
    turn is told to answer every id in that file.
    """
    # AN OVERHAUL IS A DIFFERENT SIGNAL AND A DIFFERENT PROMPT, and it names the
    # SOURCE rather than the rendering: that is the file whose committed state
    # was just checked, and it is the file the turn edits.
    #
    # A DECK WITH A BRIEF BESIDE IT (the meeting deck) carries it, and the
    # line says where it is: that is the file saying what the deck covers, and
    # an addition asked for in ink is read against it rather than refused as a
    # widening. Found by looking beside the document, never from the page.
    brief = ""
    if library.from_sittings(repo.root, doc):
        brief = "%s/%s" % (doc["dir"], library.DECK_BRIEF)
    if ask == "rework":
        line = "[rework] " + sense.rework_sense(doc.get("source") or doc["rel"],
                                                note_rel, purpose, brief=brief,
                                                ledger=ledger_rel, ids=ids,
                                                source=doc.get("source") or "")
    else:
        line = "[revise] " + sense.revise_sense(doc["rel"], note_rel,
                                                brief=brief, ledger=ledger_rel,
                                                ids=ids,
                                                source=doc.get("source") or "")
    record = {
        "rev": 0, "kind": "text", "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": line, "signal": ask, "read": False,
    }
    if registry.is_sessionless(repo):
        # FROM THE LIBRARY PAGE, which no session is behind: the subject's
        # tutor is asked through `runner_route`, which picks the session.
        try:
            got = registry.runner_route(registry.subject_of(repo), record,
                                        base=registry.base_of(repo),
                                        ask="%s %s" % (ask, doc.get("title") or ""))
        except (LookupError, OSError) as exc:
            return {"revise": "board", "asked": False,
                    "detail": "the note is written but nothing could be asked: %s"
                              % exc}
        h.hub.worker.dirty.set()
        return {"revise": "board", "asked": True, "session": got["session"],
                "detail": ("The tutor has been asked to %s it, in the newest "
                           "session on this subject." % ask)}
    # An id from the same series the lesson's turns use, so nothing in the
    # inbox has to be told apart by shape. It is NOT written into
    # `turns.jsonl`: the transcript is the lesson's, and this is not part of
    # the lesson.
    record["id"] = turns.next_turn_id(repo)
    try:
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        return {"revise": "board", "asked": False,
                "detail": "the note is written but nothing could be asked: %s" % exc}
    runner.wake(repo)
    h.hub.worker.dirty.set()
    return {"revise": "board", "asked": True,
            "detail": ("The tutor has been asked to rework it, and an overhaul "
                       "takes longer than a correction. That turn is not part "
                       "of the lesson: it writes no card and leaves the sitting "
                       "on the board alone."
                       if ask == "rework" else
                       "The tutor has been asked to revise it. That turn is not "
                       "part of the lesson: it writes no card and leaves the "
                       "sitting on the board alone.")}
