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

rec = library.write_note(tmp, flat["id"], "Section 3 is about the wrong split.",
                         page=14)
check("a note is written", rec.get("ok") and os.path.isfile(rec["path"]))
said = open(rec["path"], encoding="utf-8").read()
check("it names the document it is about", flat["rel"] in said)
check("and the page, because the reader was looking at one", "page 14" in said)
check("and it carries their words rather than a summary of them",
      "wrong split" in said)
again = library.write_note(tmp, flat["id"], "And the abstract overclaims.")
check("a second round the same day is v2, not an overwrite",
      again["rel"].endswith("-v2.md") and os.path.isfile(rec["path"]))
library.forget()
check("the document then says how many rounds it has had",
      len(library.find(tmp, flat["id"])["notes"]) == 2)
check("a note about a document nobody has is refused",
      library.write_note(tmp, "not-a-document", "x").get("ok") is False)
check("and a note with nothing in it is refused",
      library.write_note(tmp, flat["id"], "   ").get("ok") is False)
check("a feedback note is not offered back as a document of its own",
      not [d for d in library.documents(tmp) if "feedback" in (d["dir"] or "")])

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
repo = course_repo.Repo(tmp)
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
                        {"document": mine["id"], "text": "  "})
    check("and feedback with nothing in it is refused", status == 400)

    status, body = get("/library/view/" + mine["id"])
    check("asking for the pages of a document reaches the renderer",
          status == 200 and "ok" in body)
    status, body = get("/library/view/not-a-document")
    check("and a name that is not one of ours draws nothing",
          status == 200 and body.get("ok") is False and body.get("why") == "none")
finally:
    httpd.shutdown()

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a workspace's documents are one list, and feedback lands beside one of them")
