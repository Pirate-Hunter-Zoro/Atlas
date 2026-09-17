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

from tutorboard import manuscript
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

# A piece of a document is not a document.
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

check("a piece of a document is not offered as a document",
      not [d for d in found if "parts" in (d["dir"] or "")])
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
check("the note says which pages were marked and where the pictures are",
      "page 2, 4 strokes" in said and found[0]["png"] in said)
check("and tells whoever reads it to open the image rather than guess",
      "OPEN THE IMAGE" in said)
check("marks handed over this way are recorded as sent, so the board stops "
      "offering them as unsent ink",
      all(lesson_notes.load_notes_sent(repo).get(m["key"]) for m in found))
check("and the payload says a document has been drawn on",
      [d["marks"] for d in library.status(repo)["documents"]
       if d["id"] == marked["id"]] == [{"pages": 2, "strokes": 6}])

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

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a workspace's documents are one list, and feedback lands beside one of them")
