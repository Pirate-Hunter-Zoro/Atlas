#!/usr/bin/env python3
"""The tick carries the session only: the newest cards, then deltas.

    python3 test/tick.py

A temp Atlas holds one course and a stored session bound to it with 500
cards, ink on a card inside the window and one outside it, ink on a document
page, a pinned write-up, a slate page, a draft and the course's macros.

  * With `os.walk`, `glob.glob` and `glob.iglob` patched to raise, `build()`
    builds, and none of them was called.
  * The payload carries the newest 40 cards, how many are older, the ink of
    the cards it carries and no other, the pinned write-up's progress and the
    macros. Map, plan, reading, direction, news and missions are null; sets,
    results, jobs and Colibri are not on it. Its size stays under SIZE_CAP.
  * The first tick pushes; an unchanged tick pushes nothing. A new card is
    one delta naming that card and the keys that moved and no others. An
    edit is a changed card, a deleted file a removed one, and a card that
    only slides out of the window is neither. Ink alone pushes nothing, the
    whole payload still carries it, and the next delta does too.
  * `/cards?before=<n>` (`older_cards`) serves the 40 below n, with their ink
    and the count still older. `/subject.json` (`subject_info`) carries the
    subject's problem sets, results, jobs and Colibri.
  * A document's ink comes with its pages (`notes.doc_ink`).
  * The brief of an unbound session tells the tutor to ask what it is for; a
    bound one does not.
"""

import glob
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
sys.path.insert(0, BOARD_DIR)

fails = []

# The whole payload of a 500-card session, in bytes. Forty cards of about
# 300 bytes, the turns and the rest; it must not grow with the session.
SIZE_CAP = 48 * 1024


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-tick-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-tick-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import brief, sense, sessions                      # noqa: E402
from tutorboard.lesson import notes                                # noqa: E402
from tutorboard.server import hub                                  # noqa: E402
from tutorboard.server.tikz import TikzWorker                      # noqa: E402

N = 500

try:
    course = os.path.join(base, "courses", "Topology")
    write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Topology"}))
    write(os.path.join(course, "latex", "coursemacros.sty"),
          "\\newcommand{\\Top}{\\mathcal{T}}\n")
    write(os.path.join(course, "homework", "hw01", "hw01.tex"),
          "\\begin{problem}{1.1}Show it.\\end{problem}\n"
          "% ===== SOLUTION 1.1 =====\nDone.\n% ===== END SOLUTION 1.1 =====\n"
          "\\begin{problem}{1.2}And this.\\end{problem}\n"
          "% ===== SOLUTION 1.2 =====\n% ===== END SOLUTION 1.2 =====\n")
    write(os.path.join(course, "homework", "hw02", "hw02.tex"),
          "\\begin{problem}{2.1}Later.\\end{problem}\n")

    rec = sessions.new("Topology", base=base)
    sid = rec["id"]
    repo = sessions.repo(sid, base, create=True)
    repo.set_state(subject="courses/Topology",
                   writeup="courses/Topology/homework/hw01/hw01.tex")
    repo = sessions.repo(sid, base, create=True)
    repo.ensure_dirs()
    for i in range(1, N + 1):
        write(os.path.join(repo.cards, "%04d-card.md" % i),
              "---\nkind: %s\ntitle: Card %d\n---\n\nCard %d says $\\Top$ is a "
              "topology, and something about open sets that runs to a sentence "
              "or two of ordinary length.\n" % ("question" if i % 5 == 0 else "lesson",
                                                i, i))
    with open(repo.turns_path, "w", encoding="utf-8") as fh:
        for i in range(1, 41):
            fh.write(json.dumps({"id": "t%04d" % i, "rev": 1, "kind": "text",
                                 "answers": "%04d" % (i * 5), "t": time.time(),
                                 "from": "student", "text": "answer %d" % i}) + "\n")
    stroke = [{"p": [0.1, 0.2, 0.3, 0.4], "w": 2}]
    for key in ("0490", "0010"):
        write(os.path.join(repo.notes, key + ".json"),
              json.dumps({"card": key, "strokes": stroke, "sent": key == "0010"}))
    doc_dir = repo.doc_ink or repo.notes
    write(os.path.join(doc_dir, "doc-notes-p1-abcdef12.json"),
          json.dumps({"card": "doc/notes/p1", "strokes": stroke, "sent": False}))
    write(os.path.join(repo.text, "0500.txt"), "half a sentence")
    with open(os.path.join(repo.slate, "page-01.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")

    worker = TikzWorker(repo)
    board = hub.Hub(repo, worker)

    # ---- nothing walks or globs ----------------------------------------
    called = []

    def refuse(name):
        def run(*a, **k):
            called.append(name)
            raise RuntimeError("%s during build()" % name)
        return run

    saved = (os.walk, glob.glob, glob.iglob)
    os.walk, glob.glob, glob.iglob = (refuse("os.walk"), refuse("glob.glob"),
                                      refuse("glob.iglob"))
    try:
        try:
            data = board.build()
            built = True
        except Exception as e:                               # noqa: BLE001
            data, built = {}, e
    finally:
        os.walk, glob.glob, glob.iglob = saved
    check("with os.walk and glob patched to raise, build() still builds",
          built is True, built)
    check("and nothing in it walked or globbed", not called, called)

    # ---- what the payload carries --------------------------------------
    ids = [c["id"] for c in data.get("cards") or []]
    check("the newest 40 cards, in order",
          ids == ["%04d" % i for i in range(N - 39, N + 1)], ids[:3])
    check("and how many are older", data.get("cards_older") == N - 40,
          data.get("cards_older"))
    check("map, plan, reading, direction, news and missions are null",
          all(k in data and data[k] is None
              for k in ("map", "plan", "reading", "direction", "news", "missions")))
    check("sets, results, jobs, Colibri and the save count are not on it",
          not [k for k in ("sets", "results", "jobs", "colibri", "unsaved",
                           "assistants", "fenced", "contents", "review", "walk")
               if k in data])
    check("the ink of a card in the window rides with it",
          (data.get("notes") or {}).get("0490") == stroke)
    check("and the ink of a card outside it, or of a document page, does not",
          sorted(data.get("notes") or {}) == ["0490"], sorted(data.get("notes") or {}))
    hw = data.get("hw") or {}
    check("the pinned write-up's progress, from its one file",
          hw.get("name") == "hw01" and hw.get("total") == 2 and hw.get("written") == 1
          and hw.get("next") == "1.2", hw)
    check("the subject's macros", "Top" in json.dumps(data.get("macros")))
    check("the session's draft and slate",
          (data.get("text_drafts") or {}).get("0500") == "half a sentence"
          and data.get("slate"))
    check("state is session.json, bound and in teach",
          data["state"].get("subject") == "courses/Topology"
          and data["state"].get("mode") == "teach"
          and data["state"].get("course") == "Topology")

    # ---- deltas ----------------------------------------------------------
    q, cv = board.subscribe()
    board.tick()
    whole = json.loads(board.payload)
    size = len(board.payload.encode("utf-8"))
    check("the whole payload of a %d-card session stays under %d bytes (%d)"
          % (N, SIZE_CAP, size), size < SIZE_CAP)
    check("the first tick pushes, and the whole payload carries its seq",
          len(q) == 1 and whole.get("seq") == 1 and len(whole["cards"]) == 40)
    first = json.loads(q[0])
    check("and the push is a delta holding the window",
          first.get("delta") is True and len(first["cards_changed"]) == 40)
    del q[:]
    board.tick()
    check("an unchanged tick pushes nothing", not q)

    write(os.path.join(repo.cards, "%04d-new.md" % (N + 1)),
          "---\nkind: lesson\ntitle: New\n---\n\nA new card.\n")
    board.tick()
    got = json.loads(q[-1]) if len(q) == 1 else {}
    check("a new card is one delta", len(q) == 1)
    check("naming that card only",
          [c["id"] for c in got.get("cards_changed", [])] == ["%04d" % (N + 1)]
          and got.get("cards_removed") == [], got.get("cards_changed"))
    check("with the keys that moved and none that did not",
          got.get("cards_older") == N - 39 and "turns" not in got
          and "state" not in got and "macros" not in got,
          sorted(got))
    check("and a card that slid out of the window is not removed",
          "%04d" % (N - 39) not in got.get("cards_removed", []))
    del q[:]

    path = os.path.join(repo.cards, "0480-card.md")
    write(path, "---\nkind: lesson\ntitle: Card 480\n---\n\nRewritten.\n")
    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + 5))
    board.tick()
    got = json.loads(q[-1]) if q else {}
    check("an edited card is a changed card",
          [c["id"] for c in got.get("cards_changed", [])] == ["0480"]
          and "Rewritten" in got["cards_changed"][0]["body"])
    del q[:]

    os.remove(os.path.join(repo.cards, "0490-card.md"))
    board.tick()
    got = json.loads(q[-1]) if q else {}
    check("a deleted card file is a removed card",
          got.get("cards_removed") == ["0490"], got.get("cards_removed"))
    del q[:]

    write(os.path.join(repo.notes, "0495.json"),
          json.dumps({"card": "0495", "strokes": stroke + stroke, "sent": False}))
    board.tick()
    check("ink alone pushes nothing", not q)
    check("but the whole payload carries it",
          len(json.loads(board.payload)["notes"].get("0495") or []) == 2)
    write(os.path.join(repo.text, "0495.txt"), "typed")
    board.tick()
    got = json.loads(q[-1]) if q else {}
    check("and the next delta does too",
          len((got.get("notes") or {}).get("0495") or []) == 2
          and (got.get("text_drafts") or {}).get("0495") == "typed", sorted(got))
    check("deltas count up from the whole payload's seq",
          got.get("seq") == json.loads(board.payload)["seq"] == 5)
    board.unsubscribe((q, cv))

    # ---- older cards and the subject, on demand -----------------------
    older = hub.older_cards(repo, None, N - 38)
    check("/cards?before=n serves the 40 cards below n",
          [c["id"] for c in older["cards"]] == ["%04d" % i for i in range(N - 78, N - 38)],
          [c["id"] for c in older["cards"]][:2])
    check("with how many are older still", older["older"] == N - 79, older["older"])
    far = hub.older_cards(repo, None, 41)
    check("and the ink of the cards it serves",
          far["notes"].get("0010") == stroke and far["notes_sent"].get("0010") is True
          and len(far["cards"]) == 40 and far["older"] == 0)
    info = hub.subject_info(repo)
    check("/subject.json carries the subject's problem sets",
          [s["name"] for s in info["sets"]] == ["hw01", "hw02"], info["sets"])
    check("and results, jobs and Colibri",
          all(k in info for k in ("results", "jobs", "colibri")) and info["ok"])

    marks, sent = notes.doc_ink(repo, "notes")
    check("a document's ink comes with its pages",
          marks.get("doc/notes/p1") == stroke and sent.get("doc/notes/p1") is False)

    # ---- the brief of a session about nothing yet ------------------------
    loose = sessions.new("Loose", base=base)
    lrepo = sessions.repo(loose["id"], base, create=True)
    said = brief.briefing(lrepo, sense)
    check("an unbound session's brief tells the tutor to ask what it is for",
          "subject: none" in said and "ask the owner what this session is for" in said
          and "board bind" in said)
    check("and a bound one's does not",
          "subject: none" not in brief.briefing(repo, sense))
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILED" % len(fails))
    sys.exit(1)
print("the tick carries the session only: the newest cards, then what changed")
