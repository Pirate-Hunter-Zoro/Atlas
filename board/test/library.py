#!/usr/bin/env python3
"""Everything a workspace has written, grouped, and feedback on one of them.

Nothing showed a workspace's documents together. The ⋯ menu offers the two the
BOARD makes -- the exported lesson and the compiled write-up -- and the contents
drawer offers what `reading.py` found, as pages to put on a card. Neither is
"every paper and presentation in this project", and there was nowhere at all to
say what was wrong with one.

The shape is discovered rather than registered, and the two layouts that already
exist in this repository have to satisfy it without moving: a flat pair of
`.tex`/`.pdf` walkthroughs in a `docs/` directory, and four stems -- manuscript,
supplement, cover letter, checklist -- sharing one `paperN-*` directory in three
formats each.

What is guarded here is that, the fence around it, and the write: a note lands
where the document is, dated and versioned, and the reply says which machinery
was asked to act on it.

AND THE THREE THINGS THAT MADE A CORRECTION SILENT. The page had no way to know
a revision had landed, no way to read what the turn said it changed, and no way
to ask for an overhaul rather than a correction. So: a STAMP that moves when a
PDF is rebuilt and not when a note is filed, a round of feedback readable
through a route that takes a NAME out of what discovery found, and a `[rework]`
ask that costs a purpose and is refused against an uncommitted source -- because
an overhaul replaces the whole document and git is the only undo it has.
"""

import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import manuscript, sense
from tutorboard.course import library, reading
from tutorboard.course import repo as course_repo
from tutorboard.lesson import archive
from tutorboard.lesson import notes as lesson_notes
from tutorboard.server import handler, hub, spawn, tikz

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---------------------------------------------------------------------------
# a workspace in both of the shapes that already exist
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-library-")
with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Test Workspace"}, fh)


def put(rel, text="", size=0):
    where = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(where), exist_ok=True)
    with open(where, "w", encoding="utf-8") as fh:
        fh.write(text or ("x" * size))
    return where


# PSYCH-ASR's shape: a beamer source and its PDF, in `docs/`.
put("docs/stage1_pipeline_walkthrough.tex",
    "\\documentclass[aspectratio=169]{beamer}\n\\usetheme{Boadilla}\n"
    "\\title{How Audio Becomes a Transcript}\n")
put("docs/stage1_pipeline_walkthrough.pdf", size=40000)
# A second document in the same directory, whose source is newer than its PDF.
put("docs/stage2_reference_walkthrough.pdf", size=40000)
time.sleep(0.02)
put("docs/stage2_reference_walkthrough.tex",
    "\\documentclass[aspectratio=169]{beamer}\n"
    "\\title{Did the Computer Hear It Right?}\n")

# TRD-EHR's shape: four stems in one directory, three formats each.
for stem, title in (("manuscript", "TRD prediction from EHR text"),
                    ("supplement", "Supplement M1. Source data"),
                    ("cover_letter", "Cover letter"),
                    ("tripod_ai_checklist", "Completed TRIPOD+AI checklist")):
    put("paper1-trd/%s.md" % stem, "<!-- built, not edited -->\n\n# %s\n" % title)
    put("paper1-trd/%s.pdf" % stem, size=30000)
    put("paper1-trd/%s.docx" % stem, size=30000)

# A piece of a document: one section, cut from the manuscript above.
put("paper1-trd/parts/manuscript/04-methods.md", "# Methods\n")
put("paper1-trd/parts/manuscript/04-methods.docx", size=30000)

# AND THE TWO DIRECTORIES NOTHING MAY OFFER. `phi/` is session content -- 308 MB
# of identifiable therapy audio and the transcripts joined to it -- and
# `references/` is papers by other people. A document that reaches a person's
# library is a document they may then hand to a turn.
put("phi/stage1/Audio Transcription.pdf", size=60000)
put("phi/stage1/Audio Transcription.tex", "\\title{Session 1042}\n")
put("references/e_value_ann_intern_med.pdf", size=60000)

library.forget()
found = library.documents(tmp)
by_id = {d["id"]: d for d in found}
where = sorted(set(d["dir"] for d in found))


def one(title):
    for d in found:
        if d["title"] == title:
            return d
    return None


check("the flat pair in docs/ is two documents, not four files",
      len([d for d in found if d["dir"] == "docs"]) == 2)
check("and the four stems in one directory are four documents, not twelve",
      len([d for d in found if d["dir"] == "paper1-trd"]) == 4)
check("a document carries every format it has",
      sorted(one("TRD prediction from EHR text")["formats"])
      == ["docx", "md", "pdf"])

# NOTHING IS DECLARED. The title and the kind come out of the source.
check("a beamer source is a deck", one("How Audio Becomes a Transcript")["kind"] == "deck")
check("and anything else is a paper",
      one("TRD prediction from EHR text")["kind"] == "paper")
check("the title comes from the .tex rather than from the filename",
      bool(one("Did the Computer Hear It Right?")))
check("and from the first heading of a .md, past the comment above it",
      bool(one("Completed TRIPOD+AI checklist")))
check("a document whose source names no title is called after its file",
      library._from_source("", "fleet_walkthrough")[0] == "fleet walkthrough")

# STALE IS ARITHMETIC, not a record.
check("a source newer than its PDF is reported stale",
      one("Did the Computer Hear It Right?")["stale"] is True)
check("and one older than its PDF is not",
      one("How Audio Becomes a Transcript")["stale"] is False)

# A PIECE IS OFFERED, so a section can be read alone -- tagged, after every
# whole, and naming the whole it was cut from.
pieces = [d for d in found if "parts" in (d["dir"] or "")]
check("a piece of a document is offered as a piece of the one it was cut from",
      len(pieces) == 1 and pieces[0]["piece"] is True
      and pieces[0]["whole"] == one("TRD prediction from EHR text")["id"])
check("and it comes after every whole document",
      found.index(pieces[0]) == len(found) - 1)
check("and it is not counted among the documents of its directory's parent",
      len([d for d in found if d["dir"] == "paper1-trd"]) == 4)
check("THE FENCE HOLDS: nothing in phi/ is in the library",
      not [d for d in found if "phi" in (d["dir"] or "")])
check("and somebody else's reference library is not either",
      not [d for d in found if "references" in (d["dir"] or "")])
check("the fence is the one list, read from fenced.py",
      "phi" in reading.fenced.NEVER)

# AN ID, NEVER A PATH.
ident = one("How Audio Becomes a Transcript")["id"]
check("a document is found by the id it was given",
      (library.find(tmp, ident) or {}).get("title")
      == "How Audio Becomes a Transcript")
for bad in ("docs/stage1_pipeline_walkthrough.pdf", "../../etc/passwd",
            "phi-stage1-audio-transcription", ""):
    check("a name that is not one of ours resolves to nothing: %r" % bad,
          library.find(tmp, bad) is None)
check("every id is distinct, so two documents never answer to one name",
      len(by_id) == len(found))

# ---------------------------------------------------------------------------
# feedback, written where the document is
# ---------------------------------------------------------------------------
# A note is written against the REPO rather than the root: the marks on a
# document's pages live in the board's own drawer, and a note carries them.
repo = course_repo.Repo(tmp)
flat = one("TRD prediction from EHR text")
put("writeups/serve-harness/serve-harness.tex",
    "\\documentclass{article}\n\\title{How the serve harness works}\n")
put("writeups/serve-harness/serve-harness.pdf", size=30000)
library.forget()
found = library.documents(tmp)
mine = one("How the serve harness works")
check("a document the board made in writeups/ is found the same way", bool(mine))

first = library.next_note(tmp, flat)
check("a note on a flat layout carries the stem, because four share a directory",
      os.path.basename(first).startswith("manuscript-")
      and os.path.dirname(first).endswith(os.path.join("paper1-trd", "feedback")))
check("a note on a writeups/ document does not, because it has its own directory",
      os.path.basename(library.next_note(tmp, mine))[0].isdigit())
check("and it is dated and versioned, never stamped with the time",
      first.endswith("-v1.md") and time.strftime("%Y-%m-%d") in first)

rec = library.write_note(repo, flat["id"], "Section 3 is about the wrong split.",
                         page=14)
check("a note is written", rec.get("ok") and os.path.isfile(rec["path"]))
said = open(rec["path"], encoding="utf-8").read()
check("it names the document it is about", flat["rel"] in said)
check("and the page, because the reader was looking at one", "page 14" in said)
check("and it carries their words rather than a summary of them",
      "wrong split" in said)
again = library.write_note(repo, flat["id"], "And the abstract overclaims.")
check("a second round the same day is v2, not an overwrite",
      again["rel"].endswith("-v2.md") and os.path.isfile(rec["path"]))
library.forget()
check("the document then says how many rounds it has had",
      len(library.find(tmp, flat["id"])["notes"]) == 2)
check("a note about a document nobody has is refused",
      library.write_note(repo, "not-a-document", "x").get("ok") is False)
check("and a note with nothing in it, on a document nobody marked, is refused",
      library.write_note(repo, flat["id"], "   ").get("ok") is False)
check("a feedback note is not offered back as a document of its own",
      not [d for d in library.documents(tmp) if "feedback" in (d["dir"] or "")])

# ---------------------------------------------------------------------------
# feedback made of MARKS
# ---------------------------------------------------------------------------
# A ring round a figure is a complaint. It was already storable -- the viewer
# gives every page a box and `annotate.js` saves the strokes against
# `doc/<ident>/p<n>` -- and nothing read it where the textarea is read.
from tutorboard.server.routes import writing as writing_route          # noqa: E402


def ink(key, strokes=3, png=True):
    """Marks on one page, saved exactly the way `/annotate/save` saves them."""
    stem = writing_route.ann_file(key)
    with open(os.path.join(repo.notes, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"card": key, "sent": False,
                   "strokes": [{"p": [[0.1, 0.1], [0.2, 0.2]]}] * strokes}, fh)
    if png:
        with open(os.path.join(repo.notes, stem + ".png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")


check("every id is short enough to be an annotation key",
      all(len(d["id"]) <= library.IDENT_MAX for d in library.documents(tmp)))

marked = one("How the serve harness works")
idents = library.mark_idents(tmp, marked)
check("a document can be marked under its library name",
      marked["id"] in idents)
check("and under the drawer's name for the same file, which is where marking "
      "works today",
      reading.ident(tmp, library.path_of(tmp, marked, ".pdf")) in idents)

ink("doc/%s/p2" % marked["id"], strokes=4)
ink("doc/%s/p5" % idents[-1], strokes=2, png=False)
found = library.marks(repo, marked)
check("both are read back, in page order",
      [(m["page"], m["strokes"]) for m in found] == [(2, 4), (5, 2)])
check("and the picture of the page is named where one was saved",
      found[0]["png"].startswith("live/annotations/")
      and found[1]["png"] == "")

library.forget()
inked = library.write_note(repo, marked["id"], "   ")
check("a note with nothing typed is accepted once there is ink on the document",
      inked.get("ok") is True and inked.get("marks") == 2)
said = open(inked["path"], encoding="utf-8").read()
check("the note says which pages were marked and where the pictures are -- the "
      "round's own copy, which the wipe after it lands does not take",
      "page 2, 4 strokes" in said and "/feedback/%s/marked-p2.png"
      % os.path.basename(inked["path"])[:-3] in said)
check("and tells whoever reads it to open the image rather than guess",
      "OPEN THE IMAGE" in said)
check("marks handed over this way are recorded as sent, so the board stops "
      "offering them as unsent ink",
      all(lesson_notes.load_notes_sent(repo).get(m["key"]) for m in found))
check("and the payload says a document has been drawn on",
      [d["marks"] for d in library.status(repo)["documents"]
       if d["id"] == marked["id"]] == [{"pages": 2, "strokes": 6, "waiting": 2,
                                        "dir": {"pages": 0, "strokes": 0}}])
# A DOCUMENT NOT MADE FROM SITTINGS SENDS ALL ITS INK EVERY ROUND, as it always
# has: `waiting` is every marked page. Only a deck with a brief beside it keeps
# ink an earlier round delivered behind -- test/sittings.py.

# THE INK COMES BACK WITH THE PAGES. The library page opens no sitting and reads
# no `state.json`, so it holds no live payload to restore marks out of -- the
# pages it asks for carry their own. Under BOTH names the document has, for the
# same reason `marks` asks under both: it is one document and its ink is its ink.
back = library.ink(repo, marked)
check("the pages of a document carry the strokes already on them",
      sorted(back) == sorted(["doc/%s/p2" % marked["id"],
                              "doc/%s/p5" % idents[-1]]))
check("as coordinates, which is what puts them back in the same place",
      len(back["doc/%s/p2" % marked["id"]]) == 4)
check("and a document nobody has drawn on carries none, rather than somebody "
      "else's marks",
      library.ink(repo, [d for d in library.documents(tmp)
                         if d["title"] == "How Audio Becomes a Transcript"][0])
      == {})

# ---------------------------------------------------------------------------
# a machine with no poppler on it
# ---------------------------------------------------------------------------
# HOW MANY PAGES is asked of `pdfinfo`, because a modern PDF keeps its page tree
# in a compressed object stream and counting `/Type /Page` in the bytes finds
# nothing at all. A machine without poppler therefore has to show NO count
# rather than a wrong one -- and every other thing the library knows about a
# document comes off the source file, so nothing else may go with it.
from tutorboard.course import paper as course_paper                   # noqa: E402

# One document with a REAL PDF beside it, because the question is whether a
# count that exists on a machine with poppler goes MISSING on one without --
# and every other fixture here is a file full of padding, which pdfinfo answers
# nothing about whether it is installed or not.
ONE_PAGE = (b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
            b"trailer<</Root 1 0 R/Size 4>>\n%%EOF\n")
os.makedirs(os.path.join(tmp, "writeups", "one-page"), exist_ok=True)
with open(os.path.join(tmp, "writeups", "one-page", "one-page.tex"), "w",
          encoding="utf-8") as fh:
    fh.write("\\documentclass{article}\n\\title{A document of one page}\n")
with open(os.path.join(tmp, "writeups", "one-page", "one-page.pdf"), "wb") as fh:
    fh.write(ONE_PAGE)

real_env = course_paper.raster_env
course_paper.raster_env = lambda: dict(os.environ, PATH="/nonexistent")
library.forget()
blind = library.documents(tmp)
course_paper.raster_env = real_env
library.forget()
sighted = library.documents(tmp)

check("with no poppler on the machine, every document is still listed",
      len(blind) == len(sighted) and len(blind) >= 7)
check("and every one of them still has its title, its kind and its formats",
      [(d["title"], d["kind"], d["formats"]) for d in blind]
      == [(d["title"], d["kind"], d["formats"]) for d in sighted])
counted = {d["title"]: d["pages"] for d in sighted}
check("a machine WITH poppler counts the pages of a document that has some",
      counted.get("A document of one page") == 1)
check("and what is missing without it is the count, missing rather than wrong",
      all(d["pages"] == 0 for d in blind))
check("and staleness still works, because it is arithmetic on two mtimes",
      [d["stale"] for d in blind] == [d["stale"] for d in sighted])

# ---------------------------------------------------------------------------
# HAS ANYTHING MOVED? -- the cheap question the page asks every few seconds
# ---------------------------------------------------------------------------
# `/library.json` walks the workspace, reads a title out of every source and
# runs `pdfinfo` per PDF, which is why it is cached. The stamp is stats only, so
# it can be asked often -- and the two rules it lives or dies by are that it
# MOVES when a document is rebuilt and does NOT move when a note is filed,
# because a page that redraws on its own feedback is a page in a loop.
library.forget()
one_stamp = library.stamp(tmp)
check("the stamp hands out the same ids the list does",
      set(one_stamp["documents"]) == set(d["id"] for d in library.documents(tmp)))
check("and one hash over all of it, for the page to compare",
      bool(one_stamp["stamp"]) and one_stamp["ok"] is True)
check("asked twice with nothing touched, it is the same answer",
      library.stamp(tmp) == one_stamp)

library.write_note(repo, flat["id"], "A third round, filed.")
library.forget()
check("FILING A NOTE DOES NOT MOVE IT -- otherwise the page redraws on its own "
      "feedback, for ever",
      library.stamp(tmp)["stamp"] == one_stamp["stamp"])

time.sleep(0.02)
put("writeups/serve-harness/serve-harness.pdf", size=30001)
library.forget()
rebuilt = library.stamp(tmp)
check("rebuilding a PDF moves the whole stamp",
      rebuilt["stamp"] != one_stamp["stamp"])
check("and moves that document's own, which is what says WHICH one to re-draw",
      rebuilt["documents"][mine["id"]] != one_stamp["documents"][mine["id"]])
check("while every other document's is untouched, so a 33-page deck is not "
      "re-drawn because something else was built",
      [i for i in one_stamp["documents"]
       if i != mine["id"] and rebuilt["documents"].get(i)
       != one_stamp["documents"][i]] == [])

time.sleep(0.02)
put("docs/stage1_pipeline_walkthrough.tex",
    "\\documentclass[aspectratio=169]{beamer}\n"
    "\\title{How Audio Becomes a Transcript}\n% edited\n")
library.forget()
sourced = library.stamp(tmp)
check("editing a SOURCE moves it too, because that document is stale now and "
      "the row says so",
      sourced["documents"][ident] != rebuilt["documents"][ident])

# ---------------------------------------------------------------------------
# what a round of feedback actually said
# ---------------------------------------------------------------------------
# The turn writes `## What was changed` at the bottom of the feedback file, and
# that is the answer to *did it do what I asked* -- while `notes` returns names,
# sizes and dates and not a word of the contents. So the record lived in a file
# the iPad cannot open.
library.forget()
rounds = library.find(tmp, flat["id"])["notes"]
first_round = rounds[0]["name"]
with open(os.path.join(library.feedback_dir(tmp, flat), first_round), "a",
          encoding="utf-8") as fh:
    fh.write("\n## What was changed\n\nSection 3 now names the held-out split.\n")
got = library.note_text(tmp, flat, first_round)
check("a round of feedback can be read back", got.get("ok") is True)
check("it carries what the person wrote", "wrong split" in got["text"])
check("and what the turn said it changed, which is the whole point of reading it",
      "## What was changed" in got["text"] and "held-out split" in got["text"])
check("and says which file it is, so the words on the glass have a home",
      got["rel"].endswith(first_round))
for bad in ("", "../../../etc/passwd", "2026-01-01-v9.md",
            os.path.join("feedback", first_round)):
    check("a name that is not one of this document's is refused: %r" % bad,
          library.note_text(tmp, flat, bad).get("ok") is False)
check("and a round belonging to a DIFFERENT document is refused as well, "
      "because the names are matched per document",
      library.note_text(tmp, library.find(tmp, mine["id"]),
                        first_round).get("ok") is False)

# ---------------------------------------------------------------------------
# the second ask: an overhaul rather than a correction
# ---------------------------------------------------------------------------
# "that presentation needs an overhaul now that we plan to use colibri" is not a
# correction, and the prompt a correction is woken with says outright *do not
# start it again and do not widen it*. So there are two asks, and the new one
# costs a sentence saying what the document is FOR now.
check("anything unrecognised is read as a correction, never as an overhaul",
      [library.clean_ask(x) for x in ("", None, "REWORK", "rewrite", "revise")]
      == ["revise", "revise", "rework", "revise", "revise"])

refused = library.write_note(repo, mine["id"], "", ask="rework",
                             purpose="make it better")
check("an overhaul with no real purpose in it is refused rather than started",
      refused.get("ok") is False and "FOR now" in refused["error"])

PURPOSE = ("a fifteen-minute briefing for the lab meeting on what colibri does "
           "to a transcript, for people who have never seen the pipeline")
worked = library.write_note(repo, mine["id"], "", ask="rework", purpose=PURPOSE)
check("with one, it is written -- and with nothing typed, which a correction "
      "would refuse", worked.get("ok") is True and worked["ask"] == "rework")
said = open(worked["path"], encoding="utf-8").read()
check("the file says which ask it was, so a round read back is not ambiguous",
      "- ask: rework" in said and said.startswith("# Rework of"))
check("and carries the purpose as its own section, which is what the turn works "
      "to", "What this document is FOR now" in said and PURPOSE in said)
check("a correction is still a correction in the same file",
      "- ask: revise" in open(rec["path"], encoding="utf-8").read())

# ---------------------------------------------------------------------------
# which machinery revises which
# ---------------------------------------------------------------------------
put("manuscripts/manuscript.md", "# A delivered manuscript\n")
put("manuscripts/manuscript.pdf", size=30000)
library.forget()
delivered = None
for d in library.documents(tmp):
    if d["dir"] == manuscript.LANDING:
        delivered = d
check("a manuscript delivered into manuscripts/ is the factory's to revise",
      delivered and delivered["made"] == "paper-writer")
check("and a document the board compiled is the board's",
      library.find(tmp, mine["id"])["made"] == "board")

# ---------------------------------------------------------------------------
# the route, over real HTTP
# ---------------------------------------------------------------------------
woken = []
spawn.wake_tutor = lambda r: woken.append(r) or True
spawn.fresh_tutor = lambda root, course: fails.append("a tutor was replaced")

worker = tikz.TikzWorker(repo)
worker.start()
board = hub.Hub(repo, worker)
board.payload = json.dumps(board.build())

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()

httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = board
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % port


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, method="POST",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


try:
    with open(repo.state_path, "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Workspace", "session": "lecture",
                   "chapter": "Ch 2 — the estimator"}, fh)
    with open(os.path.join(repo.cards, "0001-lesson.md"), "w",
              encoding="utf-8") as fh:
        fh.write("---\nkind: lesson\n---\nSomebody is mid-proof.\n")
    state_before = open(repo.state_path, encoding="utf-8").read()

    status, body = get("/library.json")
    check("the page can ask what this workspace has written",
          status == 200 and len(body.get("documents") or []) >= 7)
    check("and is told where a new document goes",
          body.get("writeups") == "writeups")

    status, body = post("/library/feedback",
                        {"document": mine["id"],
                         "text": "The batch-size arithmetic is out by a factor of two.",
                         "page": 3})
    check("feedback on a board-made document is accepted",
          status == 200 and body.get("ok") is True)
    check("it is filed beside the document",
          body["rel"].startswith("writeups/serve-harness/feedback/"))
    check("and the board is asked to revise it",
          body.get("revise") == "board" and body.get("asked") is True)
    check("a turn is woken for it", bool(woken))

    # THE LESSON IS NOT TOUCHED. This is the whole reason the library is a
    # surface rather than a sitting: somebody mid-proof on an iPad is not
    # interrupted by somebody correcting a deck.
    check("state.json is byte-identical",
          open(repo.state_path, encoding="utf-8").read() == state_before)
    check("no card was written",
          [n for n in sorted(os.listdir(repo.cards)) if n.endswith(".md")]
          == ["0001-lesson.md"])
    check("and the lesson was not filed away", not archive.list_archive(repo))

    with open(repo.messages_path, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1]
    check("the inbox carries a revision, marked as one",
          line.get("signal") == "revise" and line["text"].startswith("[revise]"))
    check("it names the document and the feedback file",
          mine["rel"] in line["text"] and body["rel"] in line["text"])
    check("and says outright that this is not part of the lesson",
          "NOT PART OF THE LESSON" in line["text"]
          and "no card" in line["text"].lower())
    check("nothing about it is in the lesson's own transcript",
          not os.path.isfile(repo.turns_path)
          or not [t for t in open(repo.turns_path, encoding="utf-8")
                  if "revise" in t])

    status, body = post("/library/feedback",
                        {"document": "not-a-document", "text": "x"})
    check("feedback on a document nobody has is refused", status == 404)
    status, body = post("/library/feedback",
                        {"document": flat["id"], "text": "  "})
    check("and feedback with nothing in it, on a document nobody drew on, "
          "is refused", status == 400)
    status, body = post("/library/feedback", {"document": mine["id"], "text": ""})
    check("while the same empty note on a document that HAS been marked up "
          "sends the ink",
          status == 200 and body.get("ok") is True and body.get("marks") == 2)

    status, body = get("/library/view/" + mine["id"])
    check("asking for the pages of a document reaches the renderer",
          status == 200 and "ok" in body)
    status, body = get("/library/view/not-a-document")
    check("and a name that is not one of ours draws nothing",
          status == 200 and body.get("ok") is False and body.get("why") == "none")

    # THE STAMP, OVER THE WIRE. Asked every few seconds while the page is in
    # front of somebody, so it is the one route here that has to be cheap.
    status, body = get("/library/stamp")
    check("the page can ask whether anything has moved",
          status == 200 and body.get("ok") is True and bool(body.get("stamp")))
    check("and is told per document as well as overall, so it re-draws the one "
          "that changed",
          mine["id"] in (body.get("documents") or {}))
    check("nothing about a title, a page count or a round of feedback is in it",
          not [k for k in body if k not in ("ok", "stamp", "documents")])

    # WHAT A ROUND SAID, over the wire, by id and name.
    library.forget()
    named = library.find(repo.root, flat["id"])["notes"][0]["name"]
    status, body = get("/library/note/%s/%s" % (flat["id"], named))
    check("a round of feedback can be read on the glass",
          status == 200 and body.get("ok") is True
          and "wrong split" in body.get("text", ""))
    status, body = get("/library/note/%s/%s" % (flat["id"], "2026-01-01-v9.md"))
    check("a name that is not one of that document's is refused", status == 404)
    status, body = get("/library/note/not-a-document/%s" % named)
    check("and a document nobody has has no rounds to read", status == 404)

    # THE SECOND ASK, over the wire. A rework in this fixture is not refused for
    # git: there is no repository over the temporary directory, and refusing
    # there would make the ask unavailable rather than safe.
    status, body = post("/library/feedback",
                        {"document": mine["id"], "ask": "rework",
                         "purpose": PURPOSE, "text": ""})
    check("an overhaul is accepted from the panel",
          status == 200 and body.get("ok") is True and body.get("ask") == "rework")
    with open(repo.messages_path, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    line = lines[-1]
    check("the inbox carries an overhaul, marked as one, not as a revision",
          line.get("signal") == "rework" and line["text"].startswith("[rework]"))
    check("it carries the purpose, so the board can say what is being written "
          "while the turn runs", PURPOSE in line["text"])
    check("and it names the SOURCE rather than the rendering, because that is "
          "the file the turn edits",
          mine["source"] in line["text"] and mine["source"].endswith(".tex"))
    check("THE DO-NOT-WIDEN SENTENCE IS NOT IN IT -- that is the whole "
          "difference between the two asks",
          "do not widen" not in line["text"].lower())
    check("and the lesson is still nobody else's business",
          "NOT PART OF THE LESSON" in line["text"]
          and open(repo.state_path, encoding="utf-8").read() == state_before)

    status, body = post("/library/feedback",
                        {"document": mine["id"], "ask": "rework",
                         "purpose": "make it nicer"})
    check("an overhaul with no real purpose in it is refused over the wire too",
          status == 400 and body.get("ok") is False)

    # AN OVERHAUL OF A DELIVERED MANUSCRIPT IS NOT ASKED FOR HERE. The factory
    # holds its evidence, its terminology lock and its venue, and "restructure,
    # cut and rewrite" is what every one of those gates exists to refuse.
    status, body = post("/library/feedback",
                        {"document": delivered["id"], "ask": "rework",
                         "purpose": PURPOSE})
    check("and an overhaul of a delivered manuscript is refused by name",
          status == 409 and "manuscript factory" in (body.get("error") or ""))

    # A SECTION IS CORRECTED THROUGH ITS WHOLE. The note stays on the section it
    # was written on; the revision names the manuscript the section is re-cut
    # from, because an edit made to the piece is lost on the next cut.
    piece = [d for d in library.documents(tmp) if d["piece"]][0]
    whole = library.find(tmp, piece["whole"])
    status, body = post("/library/feedback",
                        {"document": piece["id"], "ask": "rework",
                         "purpose": PURPOSE})
    check("an overhaul of one section alone is refused, naming the whole",
          status == 409 and whole["title"] in (body.get("error") or ""))
    status, body = post("/library/feedback",
                        {"document": piece["id"],
                         "text": "This paragraph repeats the abstract."})
    with open(repo.messages_path, encoding="utf-8") as fh:
        line = [json.loads(l) for l in fh if l.strip()][-1]
    check("a correction on a section is filed beside the section",
          status == 200 and "/parts/" in body.get("rel", ""))
    check("and asks for the revision of the whole it was cut from",
          line.get("signal") == "revise" and whole["rel"] in line["text"]
          and piece["rel"] not in line["text"].split(body["rel"])[0])
finally:
    httpd.shutdown()

# ---------------------------------------------------------------------------
# AN OVERHAUL AGAINST AN UNCOMMITTED SOURCE, and this one needs a real
# repository over it: the refusal is git's answer about one path.
# ---------------------------------------------------------------------------
# An overhaul replaces the whole document and git is the only undo it has.
# Committed as it stands, the whole overhaul is one diff and reverting it costs
# nothing -- so the board refuses rather than committing somebody's
# half-finished edit, because the state they would revert to is one they never
# chose.
import subprocess as _sp                                              # noqa: E402

from tutorboard.server.routes import library as library_route         # noqa: E402

repo_tmp = tempfile.mkdtemp(prefix="tutor-library-git-")


def _git(*args):
    return _sp.run(["git"] + list(args), cwd=repo_tmp, stdout=_sp.DEVNULL,
                   stderr=_sp.DEVNULL).returncode


with open(os.path.join(repo_tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Git Workspace"}, fh)
os.makedirs(os.path.join(repo_tmp, "writeups", "deck"), exist_ok=True)
deck_tex = os.path.join(repo_tmp, "writeups", "deck", "deck.tex")
with open(deck_tex, "w", encoding="utf-8") as fh:
    fh.write("\\documentclass{beamer}\n\\title{A deck to overhaul}\n")
with open(os.path.join(repo_tmp, "writeups", "deck", "deck.pdf"), "wb") as fh:
    fh.write(ONE_PAGE)

if _git("init", "-q") == 0:
    _git("config", "user.email", "t@example.invalid")
    _git("config", "user.name", "Test")
    _git("add", "-A")
    _git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "the deck as it stands")
    git_repo = course_repo.Repo(repo_tmp)
    library.forget()
    deck = [d for d in library.documents(repo_tmp) if d["stem"] == "deck"][0]
    check("with the source committed as it stands, an overhaul is allowed",
          library_route.rework_refused(git_repo, deck) == "")
    with open(deck_tex, "a", encoding="utf-8") as fh:
        fh.write("% an edit nobody has committed\n")
    library.forget()
    deck = [d for d in library.documents(repo_tmp) if d["stem"] == "deck"][0]
    stop = library_route.rework_refused(git_repo, deck)
    check("and against an uncommitted source it is refused, by name",
          bool(stop) and deck["source"] in stop
          and "nothing has committed" in stop)
    check("the refusal says nothing was written, because nothing was",
          "Nothing has been written" in stop)
    check("and names a TAP rather than a git command, because a refusal whose "
          "remedy is a terminal has sent somebody to a keyboard to get past "
          "this board's own guard",
          "save on the board" in stop and "git commit" not in stop)
    check("a correction is NOT refused for the same tree -- it changes what the "
          "note names and does not replace the document",
          library.write_note(git_repo, deck["id"], "The title is wrong.")
          .get("ok") is True)
else:
    print("skip  no git on this machine, so the uncommitted-source refusal is "
          "not exercised")

# ---------------------------------------------------------------------------
# THE EDIT LEDGER: what each request was, and what was done about it
# ---------------------------------------------------------------------------
# "I need some nifty way to keep track of what each edit request was, and what
# was done to address it, so that I don't have to read the whole paper again."
# So a round is filed as numbered requests, the turn answers each id, the board
# validates the answers and places each one on the new pages.
from tutorboard.course import ledger                                  # noqa: E402
from tutorboard.course import paper as course_paper                   # noqa: E402


def pdf_lines(pages):
    """A real PDF whose pages carry these lines of Helvetica, one under the
    next -- so a phrase can be broken across a line, hyphen and all."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Count %d /Kids [%s] >>"
            % (len(pages), " ".join("%d 0 R" % (4 + 2 * i) for i in range(len(pages)))),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, lines in enumerate(pages):
        body = ("BT /F1 18 Tf 72 760 Td 22 TL "
                + " ".join("(%s) Tj T*" % l for l in lines) + " ET")
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                    "/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
                    % (5 + 2 * i))
        objs.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(body), body))
    out, offs = b"%PDF-1.4\n", []
    for n, obj in enumerate(objs, start=1):
        offs.append(len(out))
        out += ("%d 0 obj\n" % n).encode() + obj.encode() + b"\nendobj\n"
    start = len(out)
    out += ("xref\n0 %d\n" % (len(objs) + 1)).encode() + b"0000000000 65535 f \n"
    for off in offs:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, start)).encode()
    return out


led_tmp = tempfile.mkdtemp(prefix="tutor-ledger-")
with open(os.path.join(led_tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Ledger Workspace"}, fh)
os.makedirs(os.path.join(led_tmp, "writeups", "led"))
led_tex = os.path.join(led_tmp, "writeups", "led", "led.tex")
led_pdf = os.path.join(led_tmp, "writeups", "led", "led.pdf")
BEFORE = ("\\documentclass{article}\n\\title{A paper with requests}\n"
          "\\begin{document}\nThe first page says hello.\n\n"
          "We found that the model was significant at the end.\n"
          "\\end{document}\n")
with open(led_tex, "w", encoding="utf-8") as fh:
    fh.write(BEFORE)
with open(led_pdf, "wb") as fh:
    fh.write(pdf_lines([["The first page says hello."],
                        ["We found that the model was significant", "at the end."]]))
lrepo = course_repo.Repo(led_tmp)
library.forget()
ldoc = [d for d in library.documents(led_tmp) if d["stem"] == "led"][0]
digest0 = course_paper._digest(led_pdf, course_paper.PAGE_WIDTH)


def led_ink(page, strokes, png=True):
    key = "doc/%s/p%d" % (ldoc["id"], page)
    stem = writing_route.ann_file(key)
    with open(os.path.join(lrepo.notes, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"card": key, "sent": False, "strokes": strokes,
                   "build": {"digest": digest0, "at": 1, "pages": 2}}, fh)
    if png:
        with open(os.path.join(lrepo.notes, stem + ".png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    return stem


# THREE INKED REGIONS: a ring and the arrow out of it near the top of page 1
# (one request), a tick at the bottom of page 1, and a ring on page 2.
S = lambda pts: {"c": "#e8746c", "w": 3, "pg": 1, "p": pts}         # noqa: E731
p1_stem = led_ink(1, [S([0.10, 0.10, 0.20, 0.12, 0.15, 0.14]),
                      S([0.21, 0.12, 0.30, 0.16]),
                      S([0.70, 0.80, 0.75, 0.85])])
p2_stem = led_ink(2, [S([0.10, 0.08, 0.60, 0.08, 0.60, 0.14, 0.10, 0.14])], png=False)

library.forget()
split = ledger.preview(lrepo, library.carried(lrepo, ldoc, library.marks(lrepo, ldoc)),
                       "The abstract overclaims.\n\nSay considered, not significant.")
check("the filing panel is shown the split before anything is sent: three "
      "inked regions and two paragraphs are five requests",
      [(i["kind"], i["page"]) for i in split]
      == [("ink", 1), ("ink", 1), ("ink", 2), ("text", 0), ("text", 0)])
merged = ledger.preview(lrepo, library.carried(lrepo, ldoc, library.marks(lrepo, ldoc)),
                        "", merge=[1])
check("and 'those marks on page 1 are one request' is one tap: merged, the "
      "page is one request",
      [(i["kind"], i["page"]) for i in merged] == [("ink", 1), ("ink", 2)])
check("nothing was written by showing the split",
      not os.path.isdir(os.path.join(led_tmp, "writeups", "led", "feedback")))

r1 = library.write_note(lrepo, ldoc["id"],
                        "The abstract overclaims.\n\nSay considered, not significant.",
                        page=2)
note1 = r1["path"]
led1 = json.load(open(ledger.ledger_path(note1), encoding="utf-8"))
where1 = ledger.round_dir(note1)
check("a filed round with three inked regions and two paragraphs writes five "
      "requests, each with an id",
      r1.get("ok") and [i["id"] for i in led1["items"]]
      == ["R1.1", "R1.2", "R1.3", "R1.4", "R1.5"]
      and r1["ids"] == ["R1.1", "R1.2", "R1.3", "R1.4", "R1.5"])
check("the ledger sits beside the note, where no scanner lists it as a round",
      os.path.basename(ledger.ledger_path(note1)).endswith(".ledger.json")
      and len(library.notes(led_tmp, ldoc)) == 1)
crops = sorted(f for f in os.listdir(where1) if f.endswith(".svg"))
check("each inked request keeps a crop of its ink, in the round's own directory",
      crops == ["R1.1.svg", "R1.2.svg", "R1.3.svg"]
      and [i.get("crop") for i in led1["items"][:3]]
      == ["writeups/led/feedback/%s/%s" % (os.path.basename(where1), c) for c in crops])
svg = open(os.path.join(where1, "R1.1.svg"), encoding="utf-8").read()
check("and the crop is that region of the page with the ink over it",
      "<image" in svg and svg.count("<polyline") == 2)
check("the two strokes of one ring-and-arrow are one request, not two",
      led1["items"][0]["strokes"] == 2 and led1["items"][1]["strokes"] == 1)
check("the typed paragraphs are requests too, in their own words",
      led1["items"][3]["text"] == "The abstract overclaims."
      and led1["items"][4]["page"] == 2)
said1 = open(note1, encoding="utf-8").read()
check("the note lists every request under its id, for a person and a turn",
      all("### R1.%d" % n in said1 for n in range(1, 6))
      and "R1.1.svg" in said1)
check("and names the ledger it is answered in",
      os.path.basename(ledger.ledger_path(note1)) in said1)
check("the source is snapshot as the turn found it, so the old wording is exact",
      open(os.path.join(where1, "before.tex"), encoding="utf-8").read() == BEFORE)
check("a round nobody has answered is not landed, so nothing is wiped",
      not library.last_round_landed(led_tmp, ldoc)
      and os.path.isfile(os.path.join(lrepo.notes, p1_stem + ".json")))
waiting = ledger.view(lrepo, ldoc)["rounds"][0]["items"]
check("and its requests are WAITING rather than not answered, while the turn runs",
      [i["status"] for i in waiting] == ["waiting"] * 5)

line = sense.revise_sense(ldoc["rel"], r1["rel"], ledger=r1["ledger"], ids=r1["ids"])
check("the turn is woken with the ledger's path and every id in it",
      r1["ledger"] in line and "R1.1, R1.2, R1.3, R1.4, R1.5" in line
      and "Answer EVERY id" in line)

# THE TURN ANSWERS -- all but one, and one it answers badly. It edits the
# source and rebuilds.
time.sleep(0.02)
AFTER = BEFORE.replace("was significant at the end",
                       "was considered significant at the end")
with open(led_tex, "w", encoding="utf-8") as fh:
    fh.write(AFTER)
with open(led_pdf, "wb") as fh:
    fh.write(pdf_lines([["The first page says hello."],
                        ["We found that the model was consi-",
                         "dered significant at the end.", "Another line here."]]))
led1["answers"] = {
    "R1.1": {"disposition": "done", "did": "Reworded the greeting.",
             "new": "The first page says hello."},
    "R1.2": {"disposition": "pushed back", "did": "The tick marks a correct line."},
    "R1.3": {"disposition": "partly", "did": "Tightened it."},
    "R1.4": {"disposition": "Done", "did": "Said considered.",
             "new": "We found that the model was considered significant at the end."},
    "R9.9": {"disposition": "done", "did": "Something nobody asked for."},
}
with open(ledger.ledger_path(note1), "w", encoding="utf-8") as fh:
    json.dump(led1, fh)
library.forget()
ldoc = [d for d in library.documents(led_tmp) if d["stem"] == "led"][0]
got = ledger.view(lrepo, ldoc)
rows = {i["id"]: i for i in got["rounds"][0]["items"]}
check("a round whose ledger has answers in it has landed",
      library.last_round_landed(led_tmp, ldoc) and got["rounds"][0]["landed"])
check("a turn's ledger with one id missing shows that id as NOT ANSWERED",
      rows["R1.5"]["status"] == "not answered" and rows["R1.5"]["answer"] is None)
check("while the ids it did answer are answered, in the four words",
      [rows["R1.%d" % n]["answer"]["disposition"] for n in range(1, 5)]
      == ["done", "pushed back", "partly", "done"])
check("an answer that says partly with no new wording is flagged, not trusted",
      any("no new wording" in p for p in rows["R1.3"]["problems"]))
check("an id nobody asked about is reported rather than shown as a request",
      got["rounds"][0]["unknown"] == ["R9.9"])
check("the old wording comes from the snapshot, exactly, not from the turn",
      rows["R1.4"]["answer"]["old"]
      == "We found that the model was significant at the end."
      and rows["R1.4"]["answer"]["old_from"] == "before")
check("and the source as it landed is kept beside it",
      open(os.path.join(where1, "after.tex"), encoding="utf-8").read() == AFTER)
pin = rows["R1.4"]["placed"]
check("a placement finds a phrase across a line break -- and a hyphen -- in "
      "the new PDF",
      pin and pin["by"] == "text" and pin["page"] == 2 and pin["box"]
      and pin["box"][1] < 0.1 < pin["box"][3])
digest1 = course_paper._digest(led_pdf, course_paper.PAGE_WIDTH)
check("and it is cached by the build's digest, the key the reader's pages carry",
      os.path.isfile(os.path.join(where1, "placed-%s.json" % digest1))
      and got["digest"] == digest1)
_words = ledger.words
ledger.words = lambda pdf: (_ for _ in ()).throw(AssertionError("re-read"))
try:
    again = ledger.view(lrepo, ldoc)
    check("a second look at the same build reads the cache, not the PDF",
          {i["id"]: i["placed"] for i in again["rounds"][0]["items"]}["R1.4"] == pin)
except AssertionError:
    check("a second look at the same build reads the cache, not the PDF", False)
finally:
    ledger.words = _words
check("an answer with no wording to find keeps its page and says so",
      rows["R1.2"]["placed"] == {"page": 1, "box": None, "by": "page"})
said1 = open(note1, encoding="utf-8").read()
check("the board writes `## What was changed` from the ledger, not the turn",
      "## What was changed" in said1 and "4 of 5 requests answered" in said1
      and "**R1.5**" in said1 and "NOT ANSWERED" in said1)
check("so a round that answers nothing in particular is never a silent one",
      said1.count("## What was changed") == 1)

# THE EVIDENCE OUTLIVES THE WIPE.
gone = library.wipe_delivered(lrepo, ldoc)
check("once the round has landed its delivered marks are wiped from live/",
      len(gone) == 2 and not os.path.isfile(os.path.join(lrepo.notes, p1_stem + ".png")))
check("but wipe_delivered keeps the crops and the page pictures the requests "
      "point at",
      all(os.path.isfile(os.path.join(where1, f))
          for f in ("R1.1.svg", "R1.2.svg", "R1.3.svg", "marked-p1.png"))
      and ledger.evidence(led_tmp, ldoc, os.path.basename(note1), "R1.1.svg"))
check("and a name that is not in the round is no file at all",
      not ledger.evidence(led_tmp, ldoc, os.path.basename(note1), "../led.tex")
      and not ledger.evidence(led_tmp, ldoc, "2020-01-01-v1.md", "R1.1.svg"))

# CLOSING ITEMS, NOT ROUNDS.
n1 = os.path.basename(note1)
check("a request can be accepted", ledger.set_state(
    led_tmp, ldoc, n1, "R1.1", "accepted").get("ok"))
check("a reopen with no line of why is refused",
      ledger.set_state(led_tmp, ldoc, n1, "R1.5", "reopened", "").get("ok") is False)
check("and with one, the request is reopened",
      ledger.set_state(led_tmp, ldoc, n1, "R1.5", "reopened",
                       "the abstract still says 'proves'").get("ok"))
check("the document's row says how many requests are still open",
      ledger.summary(led_tmp, ldoc) == {"rounds": 1, "items": 5, "open": 4,
                                        "reopened": 1})
r2 = library.write_note(lrepo, ldoc["id"], "")
check("a round of nothing but a reopened request can be filed",
      r2.get("ok") is True and r2["ids"] == ["R1.5"])
said2 = open(r2["path"], encoding="utf-8").read()
check("a reopened request carries its id into the next round's note, with why",
      "### R1.5 -- REOPENED from %s" % n1 in said2
      and "the abstract still says 'proves'" in said2
      and "Say considered, not significant." in said2)
check("and into the next round's ledger, with its last answer",
      [(i["id"], i["kind"]) for i in json.load(open(
          ledger.ledger_path(r2["path"]), encoding="utf-8"))["items"]]
      == [("R1.5", "reopened")])
check("the first round now says the request rides the second",
      ledger.states_of(note1)["R1.5"].get("carried") == os.path.basename(r2["path"])
      and not ledger.reopened(led_tmp, ldoc))
check("so it is counted once, in the round it rides",
      ledger.summary(led_tmp, ldoc)["open"] == 4)
check("and the first round is landed by the second having been filed",
      ledger.check(led_tmp, ldoc, note1, later=True)["landed"])

# THE MANUSCRIPT FACTORY'S ANSWER: what its editor APPLIED, one per issue.
fac_items = [{"id": "R2.1"}, {"id": "R2.2"}, {"id": "R2.3"}]
fac, extra = ledger.from_factory(fac_items, {"edits": [
    {"issue": "[R2.1] the abstract overclaims", "find": "proves", "replace": "suggests",
     "applied": True},
    {"issue": "[R2.2] wrong split", "find": "80/20", "replace": "70/30",
     "applied": False, "why": "MISSING"},
    {"issue": "TERMINOLOGY: a gate's own fix", "find": "a", "replace": "b",
     "applied": True}]})
check("a factory edit that applied answers its request as done, with old and new",
      fac["R2.1"]["disposition"] == "done" and fac["R2.1"]["old"] == "proves"
      and fac["R2.1"]["new"] == "suggests")
check("one that did not apply is not done, saying why",
      fac["R2.2"]["disposition"] == "not done" and "MISSING" in fac["R2.2"]["did"])
check("a request no edit names is not answered, and the factory's own edits "
      "are listed rather than dropped",
      "R2.3" not in fac and len(extra) == 1)

# AND WHEN THE FACTORY'S RECORD LANDS BESIDE A ROUND, the board turns it into
# that round's answers -- in the ledger, which is the contract whoever answered.
with open(ledger.factory_path(r2["path"]), "w", encoding="utf-8") as fh:
    json.dump({"version": 1, "edits": [
        {"issue": "[R1.5] 'significant' said without the test", "applied": True,
         "find": "was significant", "replace": "was considered significant"}]}, fh)
fac_check = ledger.check(led_tmp, ldoc, r2["path"])
check("a round the manuscript factory answered has landed, its answers taken "
      "from what the editor applied",
      fac_check["landed"] and fac_check["items"]["R1.5"]["status"] == "answered"
      and fac_check["items"]["R1.5"]["answer"]["by"] == "paper-writer")
check("and they are written into the ledger itself",
      json.load(open(ledger.ledger_path(r2["path"]), encoding="utf-8"))["answers"]
      ["R1.5"]["disposition"] == "done")

# OVER THE WIRE.
lworker = tikz.TikzWorker(lrepo)
lworker.start()
lboard = hub.Hub(lrepo, lworker)
lboard.payload = json.dumps(lboard.build())
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
lport = sock.getsockname()[1]
sock.close()
lhttpd = ThreadingHTTPServer(("127.0.0.1", lport), handler.Handler)
lhttpd.daemon_threads = True
lhttpd.repo = lrepo
lhttpd.hub = lboard
threading.Thread(target=lhttpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % lport
try:
    status, body = get("/library/ledger/" + ldoc["id"])
    check("the glass can ask for a document's requests, newest round first",
          status == 200 and body.get("ok") and [r["note"] for r in body["rounds"]]
          == [os.path.basename(r2["path"]), n1])
    first_round = body["rounds"][1]["items"]
    crop_url = [i for i in first_round if i["id"] == "R1.1"][0]["crop"]
    with urllib.request.urlopen(BASE + crop_url, timeout=30) as resp:
        ctype = resp.headers.get("Content-Type")
        blob = resp.read()
    check("a request's crop is served by id, round and name",
          ctype == "image/svg+xml" and b"<polyline" in blob)
    status, _ = get("/library/evidence/%s/%s/%s" % (ldoc["id"], n1, "..%2Fled.tex"))
    check("and nothing else is", status == 404)
    status, body = get("/library/ledger/not-a-document")
    check("a document nobody has has no requests", status == 404)
    status, body = post("/library/ledger/state", {"document": ldoc["id"], "note": n1,
                                                  "id": "R1.4", "state": "accepted"})
    check("a request is accepted from the glass",
          status == 200 and body.get("ok") and body.get("state") == "accepted")
    status, body = get("/library.json")
    row = [d for d in body["documents"] if d["id"] == ldoc["id"]][0]
    check("and the row says how many are still open", row["ledger"]["open"] == 3)
    led_ink(1, [S([0.1, 0.1, 0.2, 0.2]), S([0.8, 0.8, 0.9, 0.9])])
    status, body = post("/library/ledger/preview",
                        {"document": ldoc["id"], "text": "One more thing."})
    check("the panel's split, over the wire, numbers the next round",
          status == 200 and [i["id"] for i in body["items"]]
          == ["R3.1", "R3.2", "R3.3"] and body["items"][0]["together"] == 2)
    status, body = post("/library/feedback", {"document": ldoc["id"],
                                              "text": "One more thing.",
                                              "merge": [1]})
    check("and a round filed with a page merged has that page as one request",
          status == 200 and body.get("ids") == ["R3.1", "R3.2"]
          and body.get("ledger", "").endswith(".ledger.json"))
    with open(lrepo.messages_path, encoding="utf-8") as fh:
        wake = [json.loads(l) for l in fh if l.strip()][-1]["text"]
    check("the revision is woken naming the round's ledger and its ids",
          body["ledger"] in wake and "R3.1, R3.2" in wake)
finally:
    lhttpd.shutdown()

# THE AFTER-COPY IS TAKEN ONCE. A later round's edit, and a re-validation the
# ledger's stat forced (a checkout, a clone, a touch), must not rewrite what
# round 1 changed.
with open(led_tex, "w", encoding="utf-8") as fh:
    fh.write(AFTER.replace("was considered significant", "was deemed significant"))
os.utime(ledger.ledger_path(note1), None)
again1 = ledger.check(led_tmp, ldoc, note1, later=True)
check("a re-validation of a landed round keeps its after-copy as it landed",
      open(os.path.join(where1, "after.tex"), encoding="utf-8").read() == AFTER
      and again1["items"]["R1.4"]["answer"]["old"]
      == "We found that the model was significant at the end.")

# A ROUND NOBODY WAS ASKED TO ANSWER COUNTS NOWHERE, so a retry after a failed
# ask does not count its requests twice.
newest = library.notes(led_tmp, ldoc)[-1]["name"]
check("a request on a round still waiting for its revision is neither accepted "
      "nor reopened",
      ledger.set_state(led_tmp, ldoc, newest, "R3.1", "accepted").get("ok") is False
      and ledger.set_state(led_tmp, ldoc, newest, "R3.1", "reopened",
                           "not yet").get("ok") is False)
newest_path = os.path.join(library.feedback_dir(led_tmp, ldoc), newest)
with open(os.path.join(ledger.round_dir(newest_path), "states.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"R3.1": {"state": "reopened", "why": "written by hand"}}, fh)
check("and a reopen on a waiting round is not carried into the next one",
      not [i for i in ledger.reopened(led_tmp, ldoc) if i["id"] == "R3.1"])
os.remove(os.path.join(ledger.round_dir(newest_path), "states.json"))
ledger.set_state(led_tmp, ldoc, n1, "R1.2", "reopened", "the tick was right after all")
count0 = ledger.summary(led_tmp, ldoc)
failed = library.write_note(lrepo, ldoc["id"], "", hand_over=False)
ledger.mark_unsent(failed["path"], "nothing could be asked")
retry = library.write_note(lrepo, ldoc["id"], "", hand_over=True)
check("a retry after a failed ask carries the reopened request under its id",
      failed["ids"][-1] == "R1.2" and retry["ids"][-1] == "R1.2")
# The ink still on the page goes with both (nothing has landed to wipe it), so
# the retry adds its fresh requests once and the reopened one not at all.
fresh = len(retry["ids"]) - 1
count1 = ledger.summary(led_tmp, ldoc)
check("and each request is counted once: the round whose ask failed counts "
      "nowhere",
      count1["items"] == count0["items"] + fresh
      and count1["open"] == count0["open"] + fresh
      and os.path.basename(failed["path"]) not in
      [r["note"] for r in ledger.view(lrepo, ldoc)["rounds"]])
check("the round numbers go past the unsent one, never back",
      failed["ids"] and json.load(open(ledger.ledger_path(retry["path"]),
                                       encoding="utf-8"))["round"]
      == json.load(open(ledger.ledger_path(failed["path"]),
                        encoding="utf-8"))["round"] + 1)

# A NOTE DELETED DOES NOT HAND ITS NUMBER ON.
high = json.load(open(ledger.ledger_path(retry["path"]), encoding="utf-8"))["round"]
os.remove(failed["path"])
check("a round's number is past every round there has been, a deleted note's "
      "included",
      ledger.next_round(led_tmp, ldoc) == high + 1)

# TYPED WORDS ARE WRITTEN ONCE, so a long round still fits what the factory
# reads of a note.
paras = ["Paragraph %d says %s." % (n, "something long " * 60) for n in range(5)]
long_note = library.write_note(lrepo, ldoc["id"], "\n\n".join(paras), hand_over=False)
ledger.mark_unsent(long_note["path"])
body_long = open(long_note["path"], encoding="utf-8").read()
check("a typed paragraph appears in the note once, under its id",
      all(body_long.count(p) == 1 for p in paras)
      and len(body_long) < len("".join(paras)) + 2500)

# A STRUCTURAL EDIT -- a section moved -- applied, with no new wording.
struct_ans, _ = ledger.from_factory([{"id": "R1.2"}], {"edits": [
    {"issue": "[R1.2] move the methods", "find": "The first page says hello.",
     "replace": "", "applied": True}]})
check("a factory edit that restructured is done, and anchored on what it moved",
      struct_ans["R1.2"]["disposition"] == "done" and not struct_ans["R1.2"]["new"]
      and struct_ans["R1.2"]["anchor"] == "The first page says hello.")
with open(ledger.factory_path(retry["path"]), "w", encoding="utf-8") as fh:
    json.dump({"version": 1, "edits": [
        {"issue": "[R1.2] move the methods", "find": "The first page says hello.",
         "replace": "", "applied": True}]}, fh)
sc = ledger.check(led_tmp, ldoc, retry["path"])
check("and it is not flagged for new wording it never had",
      sc["items"]["R1.2"]["status"] == "answered"
      and not sc["items"]["R1.2"]["problems"])
sp = ledger.placements(lrepo, ldoc, retry["path"], led_pdf, "struct", sc,
                       ledger.items_of(retry["path"]))
check("and it is pinned where it restructured, saying so",
      sp["R1.2"]["page"] == 1 and sp["R1.2"]["by"] == "anchor")

# A PERCENT SIGN IN MARKDOWN IS A PERCENT SIGN.
pct_pdf = os.path.join(led_tmp, "pct.pdf")
with open(pct_pdf, "wb") as fh:
    fh.write(pdf_lines([["Table 5"], ["Of the cohort, 5% were excluded because",
                                      "their records were incomplete."]]))
check("in Markdown a percent sign is not a comment",
      "incomplete" in ledger.plain("5% were excluded, records incomplete.", tex=False)
      and "incomplete" not in ledger.plain("5% were excluded, records incomplete."))
pp = ledger.place(pct_pdf, "Of the cohort, 5% were excluded because their records "
                  "were incomplete.", hint=1, tex=False)
check("so a Markdown sentence with a percent in it is placed on its own words",
      pp and pp["page"] == 2 and pp["by"] == "text")

# ---------------------------------------------------------------------------
# A ROUND AS PAIRS: what was written, and what was done
# ---------------------------------------------------------------------------
# "Think of a slicker feature to show the most recent round of feedback and
# corresponding revision, where when I tap on each such pair ... it'll take me
# to that part of the paper." Every route that answers ink on a document files
# a round first (`board round`); the words under the ink are kept at filing so
# the ink re-anchors to its text on any later build; and each row of `view` is
# a pair -- its number in document order, where its pip goes, the ink and
# where it is now, the word diff, or the reply.
import subprocess                                                     # noqa: E402

pr_tmp = tempfile.mkdtemp(prefix="tutor-pairs-")
with open(os.path.join(pr_tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Pairs Workspace"}, fh)
os.makedirs(os.path.join(pr_tmp, "writeups", "pairs"))
pr_tex = os.path.join(pr_tmp, "writeups", "pairs", "pairs.tex")
pr_pdf = os.path.join(pr_tmp, "writeups", "pairs", "pairs.pdf")
PR_BEFORE = ("\\documentclass{article}\n\\title{Pairs}\n\\begin{document}\n"
             "Alpha bravo charlie delta.\n\nEcho foxtrot golf hotel.\n"
             "India juliet kilo lima.\n\\end{document}\n")
with open(pr_tex, "w", encoding="utf-8") as fh:
    fh.write(PR_BEFORE)
PAGE1 = ["Alpha bravo charlie delta.", "Echo foxtrot golf hotel."]
with open(pr_pdf, "wb") as fh:
    fh.write(pdf_lines([PAGE1, ["India juliet kilo lima."]]))
prepo = course_repo.Repo(pr_tmp)
library.forget()
pdoc = [d for d in library.documents(pr_tmp) if d["stem"] == "pairs"][0]
pdig0 = course_paper._digest(pr_pdf, course_paper.PAGE_WIDTH)
sizes0, words0 = ledger.words(pr_pdf)
echo = [w for w in words0 if w[5] == "echo"][0]
ey0, ey1 = echo[2] / sizes0[0][1], echo[4] / sizes0[0][1]


def pr_ink(page, strokes):
    key = "doc/%s/p%d" % (pdoc["id"], page)
    stem = writing_route.ann_file(key)
    with open(os.path.join(prepo.notes, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"card": key, "sent": False, "strokes": strokes,
                   "build": {"digest": pdig0, "at": 1, "pages": 2}}, fh)
    return stem


# A ring round "foxtrot" on the second line, and a tick in the margin beside
# the page-2 line.
ring = S([0.30, ey0, 0.42, ey0, 0.42, ey1, 0.30, ey1])
pr_stem = pr_ink(1, [ring])
pr_ink(2, [S([0.03, 0.09, 0.05, 0.10])])
check("the drawer's name for a document finds it too (`find_any`)",
      library.find_any(pr_tmp, library.mark_idents(pr_tmp, pdoc)[-1])["id"] == pdoc["id"]
      and library.find_any(pr_tmp, "no-such-thing") is None)
said_doc = writing_route.ann_says("doc/%s/p1" % pdoc["id"], False)[1]
check("a turn handed ink on a document is told to file it as a round",
      "board round %s" % pdoc["id"] in said_doc)

BOARD = os.path.join(ROOT, "bin", "board")


def board_round(*args):
    p = subprocess.run([sys.executable, BOARD, "round"] + list(args) + ["--repo", pr_tmp],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")


code, out = board_round(pdoc["id"])
library.forget()
pnotes = library.notes(pr_tmp, pdoc)
pnote = os.path.join(library.feedback_dir(pr_tmp, pdoc), pnotes[-1]["name"]) if pnotes else ""
check("`board round` files the ink on a document as a round and prints its ledger "
      "and ids", code == 0 and pnote and ".ledger.json" in out and "R1.1, R1.2" in out)
sent_now = lesson_notes.load_notes_sent(prepo)
check("and hands the ink over, as a note does once its revision is asked",
      all(sent_now.get(k) for k in ("doc/%s/p1" % pdoc["id"], "doc/%s/p2" % pdoc["id"])))
code2, out2 = board_round(pdoc["id"])
library.forget()
check("asked again before the round is answered, it prints that round rather than "
      "filing the same ink twice",
      code2 == 0 and "not answered yet" in out2 and len(library.notes(pr_tmp, pdoc)) == 1)
pitems = ledger.items_of(pnote) if pnote else []
under1 = (pitems[0].get("under") or {}) if pitems else {}
check("the words under the ink are kept at filing: the whole line it rings",
      under1.get("text") == "echo foxtrot golf hotel" and under1.get("page") == 1)
check("and ink in the margin keeps the line level with it",
      (pitems[1].get("under") or {}).get("text") == "india juliet kilo lima")

# THE TURN ANSWERS AND REBUILDS: a line added above, so the ringed words move.
time.sleep(0.02)
PR_AFTER = PR_BEFORE.replace("Echo foxtrot golf hotel.", "Echo foxtrot golf hotel indeed.")
with open(pr_tex, "w", encoding="utf-8") as fh:
    fh.write(PR_AFTER)
with open(pr_pdf, "wb") as fh:
    fh.write(pdf_lines([["A new opening line."] + [PAGE1[0], "Echo foxtrot golf hotel indeed."],
                        ["India juliet kilo lima."]]))
pled = json.load(open(ledger.ledger_path(pnote), encoding="utf-8"))
pled["answers"] = {
    "R1.1": {"disposition": "done", "did": "Said indeed.",
             "new": "Echo foxtrot golf hotel indeed."},
    "R1.2": {"disposition": "pushed back", "did": "The tick marks a line that is right."},
}
with open(ledger.ledger_path(pnote), "w", encoding="utf-8") as fh:
    json.dump(pled, fh)
library.forget()
pdoc = [d for d in library.documents(pr_tmp) if d["stem"] == "pairs"][0]
pv = ledger.view(prepo, pdoc)
prow = {i["id"]: i for i in pv["rounds"][0]["items"]}
p1 = prow["R1.1"]
check("a pair carries the ink as filed", p1["ink"] and p1["ink"]["page"] == 1
      and p1["ink"]["strokes"] and p1["ink"]["drawn_on"] == pdig0)
check("on a rebuilt PDF the ink follows its words, shifted by how far they moved",
      p1["ink_at"]["by"] == "text" and p1["ink_at"]["page"] == 1
      and p1["ink_at"]["dy"] > 0.01 and abs(p1["ink_at"]["dx"]) < 0.01)
check("and its pip is where the answer was found, in fractions of the page",
      p1["at"]["by"] == "answer" and p1["at"]["page"] == 1
      and p1["at"]["box"] == p1["placed"]["box"] and 0 < p1["at"]["y"] < 1)
check("the revision is a word diff: what came in is marked",
      p1["diff"] == [["=", "Echo foxtrot golf"], ["-", "hotel."], ["+", "hotel indeed."]])
check("a pushed-back pair carries the turn's sentence as its reply",
      prow["R1.2"]["reply"] == "The tick marks a line that is right." and not prow["R1.2"]["diff"])
check("pairs are numbered in document order, the number the pip carries",
      p1["n"] == 1 and prow["R1.2"]["n"] == 2)
check("a landed round says how many pairs are open and is not done",
      pv["rounds"][0]["open"] == 2 and not pv["rounds"][0]["done"])
# Page 1's flag lost (a hand-over that never got written), page 2 drawn on
# again since the round was filed.
pr_ink(1, [ring])
pr_ink(2, [S([0.03, 0.09, 0.05, 0.10]), S([0.5, 0.5, 0.6, 0.6])])
gone = library.wipe_delivered(prepo, pdoc)
check("once answered, the ink a round filed leaves the page, flag or no flag, "
      "while it is the same strokes on the same build (the archive keeps them)",
      gone == ["doc/%s/p1" % pdoc["id"]]
      and not os.path.isfile(os.path.join(prepo.notes, pr_stem + ".json"))
      and ledger.items_of(pnote)[0]["strokes"])
check("and ink drawn since stays for the next round",
      os.path.isfile(os.path.join(prepo.notes, writing_route.ann_file(
          "doc/%s/p2" % pdoc["id"]) + ".json")))
os.remove(os.path.join(prepo.notes, writing_route.ann_file("doc/%s/p2" % pdoc["id"]) + ".json"))
pr_dig_same = ledger.ink_where(pr_pdf, pdig0, dict(pitems[0]))
check("on the build it was drawn on the ink sits where it was drawn",
      pr_dig_same["by"] == "same" and pr_dig_same["dx"] == 0)

# A RECOMPILE THAT CUTS THE LINE: the anchor vanished, and the pair says so.
time.sleep(0.02)
with open(pr_pdf, "wb") as fh:
    fh.write(pdf_lines([["Something else entirely now."], ["Nothing in common here."]]))
library.forget()
pdoc = [d for d in library.documents(pr_tmp) if d["stem"] == "pairs"][0]
gv = {i["id"]: i for i in ledger.view(prepo, pdoc)["rounds"][0]["items"]}
check("where the words under the ink are gone and nothing was placed, the pair "
      "says so", gv["R1.1"]["ink_at"] == {"by": "gone"} and gv["R1.1"]["gone"]
      and gv["R1.2"]["gone"])
check("and with no answer found it still keeps its page, at the top",
      gv["R1.1"]["at"] and gv["R1.1"]["at"]["by"] == "page" and gv["R1.1"]["at"]["page"] == 1)

# THE LINE THE INK WAS ABOUT REWRITTEN, ITS NEIGHBOUR KEPT, a line put above
# both: the ink follows the line that is still there, not the answer's box.
part_pdf = os.path.join(pr_tmp, "part.pdf")
with open(part_pdf, "wb") as fh:
    fh.write(pdf_lines([["Alpha bravo charlie delta echo foxtrot.",
                         "Golf hotel india juliet kilo lima."]]))
part_under = ledger.under(part_pdf, 1, [0.1, 0.05, 0.9, 0.12])
with open(part_pdf, "wb") as fh:
    fh.write(pdf_lines([["A line put above.", "Alpha bravo charlie delta echo foxtrot.",
                         "Something new said here instead."]]))
part_at = ledger.ink_where(part_pdf, "another-build",
                           {"strokes": [ring], "page": 1, "drawn_on": "old",
                            "under": part_under})
check("words edited rather than gone: the ink follows the half of them still "
      "there, shifted by how far that half moved",
      part_under and len(part_under["text"].split()) == 12
      and part_at["by"] == "part" and part_at["page"] == 1
      and 0.02 < part_at["dy"] < 0.04)
stale = ledger.ink_where(part_pdf, "another-build",
                         {"strokes": [ring], "page": 1, "drawn_on": "old",
                          "box": [0.3, 0.2, 0.4, 0.3]})
check("ink filed off an older build, with no words kept, sits where it was drawn "
      "rather than being called gone",
      stale["by"] == "drawn" and stale["box"] == [0.3, 0.2, 0.4, 0.3] and stale["dy"] == 0)
check("a diff keeps the math a sentence reads with, and its stop on the word",
      ledger.word_diff("flat past $k=300$.", "flat past $k=295$ for $\\alpha=1$.")
      == [["=", "flat past"], ["-", "k=300."], ["+", "k=295 for α=1."]])

# FINE ON EVERY PAIR: the round is done.
pn = os.path.basename(pnote)
ledger.set_state(pr_tmp, pdoc, pn, "R1.1", "accepted")
ledger.set_state(pr_tmp, pdoc, pn, "R1.2", "accepted")
dv = ledger.view(prepo, pdoc)["rounds"][0]
check("a round with every pair said fine is done", dv["done"] and dv["open"] == 0)

# THE DIFF ITSELF.
long_same = " ".join("w%d" % i for i in range(30))
dd = ledger.word_diff(long_same + " old end.", long_same + " new end.", tex=False)
check("a long unchanged run is trimmed to its last few words before a change",
      dd[0][0] == "=" and dd[0][1].startswith("… ") and len(dd[0][1].split()) == 7
      and dd[1:] == [["-", "old"], ["+", "new"], ["=", "end."]])
mid = ledger.word_diff("a " + long_same + " b", "x " + long_same + " y", tex=False)
check("and one between two changes keeps both ends",
      mid[2][0] == "=" and " … " in mid[2][1] and len(mid[2][1].split()) == 13)
foc = ledger.word_diff("One old. Two old.", "One new. Two new.", tex=False, focus="Two new.")
check("a diff focused on the passage a request quoted shows only its own change",
      foc == [["=", "Two"], ["-", "old."], ["+", "new."]])

# TWO KINDS OF INK ON ONE PAGE. A stroke drawn with the reader's toggle on
# directions carries `dir: 1`: it is never a request, a fix's wipe leaves it,
# and its picture is its own file.
D = lambda pts: dict(S(pts), dir=1)                                  # noqa: E731
mixed = "doc/%s/p1" % pdoc["id"]
mstem = os.path.join(prepo.notes, writing_route.ann_file(mixed))
dstroke = D([0.60, 0.60, 0.70, 0.70])


def mixed_page(sent, build=True):
    rec = {"card": mixed, "sent": sent, "strokes": [ring, dstroke]}
    if build:
        rec["build"] = {"digest": pdig0, "at": 1, "pages": 2}
    with open(mstem + ".json", "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    for ext in (".png", ".dir.png"):
        with open(mstem + ext, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n")


mixed_page(False)
library.forget()
mk = library.marks(prepo, pdoc)
check("a page carrying both kinds is a fix page of one stroke, with the fix picture",
      [(m["page"], m["strokes"]) for m in mk] == [(1, 1)]
      and mk[0]["png"].endswith(".png") and not mk[0]["png"].endswith(".dir.png"))
dk = library.marks(prepo, pdoc, kind="dir")
check("and a direction page of one stroke, with its own picture",
      [(m["page"], m["strokes"]) for m in dk] == [(1, 1)]
      and dk[0]["png"].endswith(".dir.png"))
pv_items = ledger.preview(prepo, library.carried(prepo, pdoc, mk), "")
split_items = ledger.split(prepo, mk, "")
check("the filing panel's split makes no request out of direction ink",
      [(i["kind"], i["page"], i["count"]) for i in pv_items] == [("ink", 1, 1)]
      and [len(i["strokes"]) for i in split_items] == [1]
      and not any(s.get("dir") for s in split_items[0]["strokes"]))
st_marks = [d["marks"] for d in library.status(prepo)["documents"]
            if d["id"] == pdoc["id"]][0]
# `status` wipes first: the round has landed, and the fix stroke on page 1 is
# the one it filed on the build it was filed against, so it went.
check("the row counts fixes and directions apart, after the wipe took the "
      "delivered fix",
      st_marks["pages"] == 0 and st_marks["strokes"] == 0
      and st_marks["dir"] == {"pages": 1, "strokes": 1})
with open(mstem + ".json", encoding="utf-8") as fh:
    left = json.load(fh)
check("the filed-ink check counts fix strokes only: a landed round's ring goes "
      "though a direction was drawn beside it",
      left["strokes"] == [dstroke] and left["sent"] is False
      and left.get("build", {}).get("digest") == pdig0)
check("and the wipe deletes the fix picture and keeps the direction's",
      not os.path.isfile(mstem + ".png") and os.path.isfile(mstem + ".dir.png"))
mixed_page(True, build=False)
gone = library.wipe_delivered(prepo, pdoc)
with open(mstem + ".json", encoding="utf-8") as fh:
    left = json.load(fh)
check("a delivered fix page loses its fixes and keeps its directions, now unsent",
      gone == [mixed] and left["strokes"] == [dstroke] and left["sent"] is False)

code3, out3 = board_round(pdoc["id"])
check("with no ink and nothing reopened, `board round` refuses and says why -- "
      "direction ink is nothing to file",
      code3 == 1 and "nothing to file" in out3)
check("and the direction ink is left where it was",
      os.path.isfile(mstem + ".json") and os.path.isfile(mstem + ".dir.png"))
check("a page whose last ink is stripped goes whole, both pictures",
      library.strip_kind(prepo, mixed, "dir")
      and not os.path.isfile(mstem + ".json") and not os.path.isfile(mstem + ".dir.png"))

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a workspace's documents are one list, and feedback lands beside one of them")
