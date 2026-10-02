#!/usr/bin/env python3
"""The map draws deliverables and threads.

What the checks are about:

  * EACH DELIVERABLE IS A FRAME. The payload carries the deliverables, every
    box names the one it sits in, and a course's one deliverable is its book.
  * CODE IS NEVER A BOX. Nothing opens a level down under a thread; its files
    are rows on its sheet.
  * A THREAD'S SHEET LISTS WHAT IT HOLDS: files, outputs, write-up anchors,
    jobs, past sittings by thread id, documents, and the kind its last sitting
    was.
  * EVERY PAPER IS ON THE MAP. A deliverable's document heads the documents
    region, built or not.
  * THE ATLAS CARD'S NEXT LINE is the first open task of the first thread not
    blocked, and it names the thread.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import machines                                     # noqa: E402
from tutorboard.course import library, map as mapping, plan, threads  # noqa: E402
from tutorboard.lesson import archive                               # noqa: E402
from tutorboard.server.routes import lesson                         # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def fresh():
    threads._cache.clear()
    mapping._cache.clear()
    plan._cache.clear()
    library._cache.clear()


FILE = {
    "version": 1,
    "deliverables": [
        {"id": "paper1", "title": "Paper 1", "doc": "paper/manuscript.md"},
        {"id": "deck", "title": "The deck", "doc": "deck/slides.md"},
    ],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Weighted neighbours",
         "question": "Does weighting beat cosine?",
         "files": ["scripts/knn.py", "scripts/lib"],
         "outputs": ["results/knn.csv", "results/missing.csv"],
         "writes": [{"file": "paper/manuscript.md",
                     "anchor": "## Nearest-neighbour retrieval"},
                    {"file": "paper/manuscript.md", "anchor": "## Not written"}],
         "tasks": [{"text": "Run the sweep", "done": True},
                   {"text": "Draw the figure", "done": False},
                   {"text": "Write the section", "done": False}],
         "decisions": [{"q": "How to count dimensions", "rule": None},
                       {"q": "Which k", "rule": "The best k per encoder"}]},
        {"id": "tripod", "deliverable": "paper1", "title": "TRIPOD checklist",
         "tasks": [{"text": "Fill row 23a", "done": False}],
         "blockedBy": ["knn"]},
        {"id": "slides", "deliverable": "deck", "title": "The slides",
         "tasks": [{"text": "Draft the slides", "done": False}]},
    ],
}


class Repo(object):
    def __init__(self, root):
        self.root = root
        self.archive = os.path.join(root, "live", "archive")
        self.turns_path = os.path.join(root, "live", "turns.jsonl")

    def state(self):
        return {}


class H(object):
    def __init__(self):
        self.said = None
        self.status = 200

    def send_json(self, obj, status=200):
        self.said, self.status = obj, status
        return True


home = tempfile.mkdtemp(prefix="tutor-threadmap-")
try:
    ws = os.path.join(home, "proj")
    write(os.path.join(ws, "threads.json"), json.dumps(FILE))
    write(os.path.join(ws, "scripts", "knn.py"), '"""Weighted neighbours."""\n')
    write(os.path.join(ws, "scripts", "lib", "util.py"), '"""Helpers."""\n')
    write(os.path.join(ws, "results", "knn.csv"), "k,auc\n1,0.6\n")
    write(os.path.join(ws, "paper", "manuscript.md"),
          "# Paper 1\n\n## Nearest-neighbour retrieval\n\nText.\n")
    write(os.path.join(ws, "live", "jobs.jsonl"),
          json.dumps({"thread": "knn", "jobid": "42", "cmd": "sbatch sweep.sbatch",
                      "produces": ["results/knn.csv"], "submitted": 1}) + "\n"
          + json.dumps({"jobid": "42", "state": "COMPLETED"}) + "\n"
          + json.dumps({"thread": "slides", "jobid": "43", "cmd": "x"}) + "\n")
    fresh()

    # --- the frames ---------------------------------------------------------
    built = mapping.status(ws)
    check("the payload carries every deliverable, as a frame",
          [d["id"] for d in built["deliverables"]] == ["paper1", "deck"])
    check("every box names the deliverable it sits in",
          dict((n["id"], n["deliverable"]) for n in built["nodes"])
          == {"knn": "paper1", "tripod": "paper1", "slides": "deck"})
    knn = [n for n in built["nodes"] if n["id"] == "knn"][0]
    check("a box carries its open decisions and open tasks as counts",
          knn["decisions"] == 1 and knn["tasks"] == 2)
    check("a box carries its open tasks as chips, in the file's order",
          [s["title"] for s in knn["steps"]] == ["Draw the figure",
                                                 "Write the section"])
    check("blockedBy is an arrow",
          {"from": "knn", "to": "tripod", "label": "", "weight": 1}
          in built["edges"])

    # --- code is never a box ------------------------------------------------
    check("nothing opens a level down under a thread",
          mapping.inside(ws, "knn") is None
          and mapping.inside(ws, "in-knn-py") is None)

    # --- the documents region -----------------------------------------------
    groups = built["documents"]["groups"]
    check("the deliverables head the documents region",
          groups and groups[0]["key"] == "deliverables")
    rows = dict((r["deliverable"], r) for r in groups[0]["docs"])
    man = mapping.library_doc(library.documents(ws), "paper/manuscript.md")
    check("a deliverable whose document exists opens it in the library",
          man is not None and rows["paper1"]["id"] == man["id"])
    check("a deliverable not written yet is still on the map, unbuilt",
          rows["deck"]["id"] == "" and rows["deck"]["pdf"] is False
          and rows["deck"]["rel"] == "deck/slides.md")
    check("and the manuscript is in the papers group as well",
          any(d["id"] == man["id"] for g in groups if g["key"] == "papers"
              for d in g["docs"]))

    # --- the sheet ----------------------------------------------------------
    archived = [
        {"id": "2026-09-30-a", "chapter": "Weighted neighbours", "node": "knn",
         "aim": "coach", "opened": "2026-09-30T10:00", "cards": 4},
        {"id": "2026-09-29-b", "chapter": "Weighted neighbours", "thread": "knn",
         "kind": "learn", "opened": "2026-09-29T10:00", "cards": 2},
        {"id": "2026-09-28-c", "chapter": "elsewhere", "node": "slides",
         "aim": "build"},
    ]
    sheet = mapping.thread_sheet(ws, "knn", {}, archived)
    check("a thread's sheet lists its files, directories said as such",
          sheet["files"] == [{"path": "scripts/knn.py", "dir": False},
                             {"path": "scripts/lib", "dir": True}])
    check("its outputs, and which of them exist",
          sheet["outputs"] == [{"path": "results/knn.csv", "there": True},
                               {"path": "results/missing.csv", "there": False}])
    check("its write-up anchors, and which are found",
          [w["found"] for w in sheet["writes"]] == [True, False])
    check("its jobs, a later line for a job id overriding",
          [(j["jobid"], j["state"]) for j in sheet["jobs"]]
          == [("42", "COMPLETED")])
    check("its past sittings, by thread id or the node before it, newest first",
          [s["id"] for s in sheet["sittings"]] == ["2026-09-30-a", "2026-09-29-b"]
          and [s["kind"] for s in sheet["sittings"]] == ["coach", "learn"])
    check("its kind is the kind of its last sitting", sheet["kind"] == "coach")
    check("the open sitting on the thread outranks the archive",
          mapping.thread_sheet(ws, "knn", {"node": "knn", "aim": "build"},
                               archived)["kind"] == "build")
    check("a thread never sat on offers learn first",
          mapping.thread_sheet(ws, "tripod", {}, archived)["kind"] == "learn")
    check("its documents: the file it is written up in",
          [d["id"] for d in sheet["documents"]] == [man["id"]])
    labels = [s["label"] for s in plan.steps(ws) if s.get("thread") == "knn"]
    check("each open task carries the label `/session` looks it up by",
          [t["label"] for t in sheet["tasks"]] == [""] + labels)
    check("its decisions, open and decided",
          [d["rule"] for d in sheet["decisions"]]
          == [None, "The best k per encoder"])
    check("a thread the file does not declare has no sheet",
          mapping.thread_sheet(ws, "ghost", {}, []) is None)
    from tutorboard import missions
    check("with no mission out, the sheet offers one", sheet["mission"] is None)
    real = missions.live_mission
    missions.live_mission = lambda root, now=None: {
        "id": "t0042", "agent": "colibri", "task": "Rerun the sweep", "thread": "knn"}
    try:
        check("a mission out on the thread is on its sheet",
              mapping.thread_sheet(ws, "knn", {}, archived)["mission"]
              == {"id": "t0042", "agent": "colibri", "task": "Rerun the sweep"})
        check("and not on another thread's",
              mapping.thread_sheet(ws, "tripod", {}, archived)["mission"] is None)
    finally:
        missions.live_mission = real

    # --- the route ------------------------------------------------------------
    repo = Repo(ws)
    h = H()
    lesson.get(h, repo, "/map/thread/knn")
    check("GET /map/thread/<id> answers with the sheet",
          h.status == 200 and h.said.get("ok") and h.said["id"] == "knn")
    h = H()
    lesson.get(h, repo, "/map/thread/..%2Fghost")
    check("and a miss is a 404", h.status == 404)

    # --- the archive says which thread and kind -------------------------------
    folder = os.path.join(repo.archive, "2026-09-30-a")
    write(os.path.join(folder, "state.json"),
          json.dumps({"course": "proj", "node": "knn", "aim": "coach",
                      "chapter": "Weighted neighbours"}))
    listed = archive.list_archive(repo)
    check("an archived sitting says its thread, node, aim and kind",
          listed and listed[0]["node"] == "knn" and listed[0]["aim"] == "coach"
          and "thread" in listed[0] and "kind" in listed[0])

    # --- the atlas card's next line -------------------------------------------
    first, task = machines._next_thread_task(ws)
    check("next is the first open task of the first thread not blocked",
          first["id"] == "knn" and task["text"] == "Draw the figure")
    clean = threads.validate(FILE)[0]
    clean["threads"][0]["closed"] = True
    first, task = threads.next_task(threads.resolve(ws, clean))
    check("a closed thread is skipped, and what it blocked is unblocked",
          first["id"] == "tripod" and task["text"] == "Fill row 23a")
    clean = threads.validate(FILE)[0]
    for x in clean["threads"][0]["tasks"]:
        x["done"] = True
    first, task = threads.next_task(threads.resolve(ws, clean))
    check("a thread still blocked is passed over for the next one",
          first["id"] == "slides")
    clean["threads"] = clean["threads"][:2]
    check("and nothing left is nothing",
          threads.next_task(threads.resolve(ws, clean)) == (None, None))

    # --- a course: the frame is the book --------------------------------------
    course = os.path.join(home, "Book-Course")
    write(os.path.join(course, "chapters.tsv"),
          "1\t1\t20\tch01-groups\tGroups\n2\t21\t40\tch02-rings\tRings\n")
    fresh()
    book = mapping.status(course)
    check("a course's one deliverable is its book",
          len(book["deliverables"]) == 1
          and book["deliverables"][0]["id"] == mapping.BOOK
          and book["deliverables"][0]["title"])
    check("and its boxes are the chapters, inside it",
          [n["kind"] for n in book["nodes"]] == ["chapter", "chapter"]
          and all(n["deliverable"] == mapping.BOOK for n in book["nodes"]))

    # --- a workspace with neither has no frames --------------------------------
    bare = os.path.join(home, "bare")
    write(os.path.join(bare, "pkg", "a.py"), '"""A."""\n')
    fresh()
    derived = mapping.status(bare)
    check("a derived picture has no frames and no deliverables group",
          derived and derived["deliverables"] == []
          and all(g["key"] != "deliverables"
                  for g in derived["documents"]["groups"]))
finally:
    shutil.rmtree(home, ignore_errors=True)

if fails:
    print("\n%d check(s) failed" % len(fails))
    sys.exit(1)
print("\na deliverable is a frame, a thread is a box, and code is a row on its sheet")
