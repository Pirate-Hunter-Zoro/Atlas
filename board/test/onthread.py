#!/usr/bin/env python3
"""A sitting belongs to a thread, and it is one of three kinds.

What the checks are about:

  * `live/state.json` CARRIES `thread` AND `kind`. A box of a thread file is a
    thread, so a map tap or `board open --thread` writes `thread`, not `node`,
    and the sitting is named after the thread.
  * A KIND IS AN AIM. learn, coach and build name `teach`, `coach` and `build`,
    and the stance follows from the aim; with nothing said, a teach sitting on
    a thread whose files are code is a coach sitting.
  * THE BRIEFING OPENS WITH THE THREAD: its question, open tasks and
    decisions, outputs, and what the last sitting on it reported.
  * A RETHINK IS ABOUT THE CURRENT THREAD. It does not write DIRECTION.md, the
    woken turn is told to rewrite that thread's tasks, and the new sitting keeps
    the thread's name.
  * TEACHING.md HAS A COACH SECTION, and its rule is that the tutor writes no
    code for an estimator or a validation design.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import brief, direction, sense                       # noqa: E402
from tutorboard.course import config, plan, threads                  # noqa: E402
from tutorboard.course import map as mapping                         # noqa: E402
from tutorboard.course import repo as course_repo                    # noqa: E402
from tutorboard.lesson import archive                                # noqa: E402
from tutorboard.server import handler, hub, spawn, tikz              # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
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


def run(cwd, *args):
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=cwd,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def fresh():
    threads._cache.clear()
    mapping._cache.clear()
    plan._cache.clear()


def state(root):
    with open(os.path.join(root, "live", "state.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


FILE = {
    "version": 1,
    "deliverables": [{"id": "paper1", "title": "Paper 1 -- predicting TRD",
                      "doc": "paper/manuscript.md"}],
    "threads": [
        {"id": "knn", "deliverable": "paper1", "title": "Weighted neighbours",
         "question": "Does weighting beat cosine on every embedder?",
         "files": ["scripts/knn.py"],
         "outputs": ["results/knn.csv", "results/missing.csv"],
         "writes": [{"file": "paper/manuscript.md", "anchor": "## Retrieval"}],
         "tasks": [{"text": "Run the sweep", "done": True},
                   {"text": "Draw the scatter", "done": False}],
         "decisions": [{"q": "How to count dimensions", "rule": None},
                       {"q": "Which k", "rule": "The best k on validation"}],
         "blockedBy": [], "closed": False},
        {"id": "estimand", "deliverable": "paper1", "title": "The estimand",
         "question": "What does the counterfactual compare?",
         "files": ["notes/estimand.md"], "outputs": [], "writes": [],
         "tasks": [{"text": "Write the estimand down", "done": False}],
         "decisions": [], "blockedBy": [], "closed": False},
    ],
}

tmp = tempfile.mkdtemp(prefix="tutor-onthread-")
write(os.path.join(tmp, "tutorboard.json"), json.dumps({"name": "Proj"}))
write(os.path.join(tmp, "scripts", "knn.py"), "print('knn')\n")
write(os.path.join(tmp, "notes", "estimand.md"), "# estimand\n")
write(os.path.join(tmp, "results", "knn.csv"), "k,auc\n")
write(os.path.join(tmp, "paper", "manuscript.md"), "# Paper\n")
write(os.path.join(tmp, "threads.json"), json.dumps(FILE))
fresh()

# ---------------------------------------------------------------------------
# a kind is an aim
# ---------------------------------------------------------------------------
check("the three kinds are learn, coach and build",
      config.KINDS == ("learn", "coach", "build"))
check("each names an aim, and the aim names the stance",
      [config.AIM_STANCE[config.KIND_AIM[k]] for k in config.KINDS]
      == ["teach", "teach", "do"])
check("a build sitting asked for as a paper stays a paper",
      config.kind_aim("build", "paper") == "paper")
check("a kind that contradicts the aim wins",
      config.kind_aim("learn", "build") == "teach")
check("an explicit kind is the kind",
      config.kind_for(tmp, {"kind": "coach", "thread": "estimand"}) == "coach")
check("an aim answers a sitting with no kind",
      config.kind_for(tmp, {"aim": "build", "thread": "knn"}) == "build")
check("a do stance with no aim is a build",
      config.kind_for(tmp, {"stance": "do", "thread": "knn"}) == "build")
check("a teach sitting on a thread whose files are code is a coach sitting",
      config.kind_for(tmp, {"thread": "knn"}, ["scripts/knn.py"]) == "coach")
check("and one whose files are prose is a learn sitting",
      config.kind_for(tmp, {"thread": "estimand"}, ["notes/estimand.md"]) == "learn")
check("a directory of code counts as code",
      config.kind_for(tmp, {"thread": "knn"}, ["scripts"]) == "coach")
check("the box of a sitting is its thread before its node",
      config.sitting_box({"thread": "knn", "node": "x"}) == "knn"
      and config.sitting_box({"node": "x"}) == "x")

# ---------------------------------------------------------------------------
# board open
# ---------------------------------------------------------------------------
code, out = run(tmp, "open", "Proj", "--thread", "knn", "--kind", "coach")
st = state(tmp)
check("board open --thread opens a sitting on the thread",
      code == 0 and st.get("thread") == "knn")
check("it carries the kind, and the aim the kind names",
      st.get("kind") == "coach" and st.get("aim") == "coach")
check("and no node", "node" not in st)
check("the sitting is named after the thread", st.get("chapter") == "Weighted neighbours")
check("and says so", "thread: knn" in out)

code, out = run(tmp, "open", "Proj", "--node", "estimand")
st = state(tmp)
check("a box of a thread file named as a node is a thread",
      st.get("thread") == "estimand" and "node" not in st)
check("with its kind derived when none was chosen: prose is learn",
      st.get("kind") == "learn")

code, out = run(tmp, "open", "Proj", "--thread", "nope")
st = state(tmp)
check("an unknown thread is ignored aloud, never carried through",
      "no thread called" in out and "thread" not in st)
check("and opening a sitting on no thread clears the kind", "kind" not in st)

run(tmp, "open", "Proj", "--thread", "knn", "--kind", "learn")
code, out = run(tmp, "aim", "build")
st = state(tmp)
check("changing the aim mid-sitting changes the kind",
      st.get("aim") == "build" and st.get("kind") == "build")
code, out = run(tmp, "aim", "coach")
check("and a kind word is accepted as the aim",
      state(tmp).get("kind") == "coach" and state(tmp).get("aim") == "coach")

# ---------------------------------------------------------------------------
# the briefing opens with the thread
# ---------------------------------------------------------------------------
repo = course_repo.Repo(tmp)
# A filed sitting on the thread, whose last card is its report.
old = os.path.join(repo.archive, "20260101-090000-weighted-neighbours")
write(os.path.join(old, "state.json"),
      json.dumps({"course": "Proj", "thread": "knn", "kind": "build",
                  "opened": "2026-01-01 09:00"}))
write(os.path.join(old, "0001-lesson.md"), "---\nkind: lesson\n---\nFirst card.\n")
write(os.path.join(old, "0002-report.md"),
      "---\nkind: report\n---\nThe sweep ran on four embedders; bge-small peaks at k=64.\n")
other = os.path.join(repo.archive, "20260102-090000-elsewhere")
write(os.path.join(other, "state.json"),
      json.dumps({"course": "Proj", "thread": "estimand"}))
write(os.path.join(other, "0001-lesson.md"), "---\nkind: lesson\n---\nNot this one.\n")

last = archive.last_on_thread(repo, "knn")
check("the last sitting on a thread is found by thread id",
      last and last["id"].startswith("20260101") and last["kind"] == "build")
check("and its report is its last card",
      last and "peaks at k=64" in last["report"])
check("the archive lists say which thread each sitting was on",
      any(a.get("thread") == "knn" for a in archive.list_archive(repo)))

fresh()
text = brief.briefing(repo, sense)
lines = text.splitlines()
check("the briefing opens with the thread, right under the title",
      len(lines) > 2 and "the thread this sitting is on: Weighted neighbours"
      in lines[2] and not lines[1].strip())
check("it names the kind", "a COACH sitting" in text)
check("it carries the question",
      "Does weighting beat cosine on every embedder?" in text)
check("the open tasks, numbered as `board thread done` counts them",
      "  2. Draw the scatter" in text and "Run the sweep" not in text)
check("the open decisions, and not the decided ones",
      "How to count dimensions" in text and "Which k" not in text.split(
          "the method, and what this sitting is")[0])
check("the outputs, and which exist",
      "results/knn.csv (there)" in text and "results/missing.csv (not yet)" in text)
check("and the last sitting's report", "peaks at k=64" in text)
check("and that the thread is the scope, not the README",
      "Do not read the project's README or plan" in text)
check("the thread comes before the method",
      text.index("the thread this sitting is on")
      < text.index("the method, and what this sitting is"))
check("the method itself sends a thread sitting to the thread, not the plan",
      "the thread is the scope" in sense.where_sense(None, tmp, {"thread": "knn"})
      and "README.md at the root" not in sense.where_sense(
          None, tmp, {"thread": "knn"}))

# ---------------------------------------------------------------------------
# the board's own requests
# ---------------------------------------------------------------------------
replaced = []
spawn.fresh_tutor = lambda root, course: replaced.append((root, course))
spawn.wake_tutor = lambda repo: False
repo = course_repo.Repo(tmp)
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


def post(path, body):
    req = urllib.request.Request(BASE + path, method="POST",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


try:
    fresh()
    status, body = post("/session", {"session": "lecture", "node": "knn",
                                     "kind": "build"})
    st = repo.state()
    check("a map tap on a thread's box opens a sitting on the thread",
          status == 200 and st.get("thread") == "knn" and "node" not in st)
    check("with the kind chosen on the sheet, written as its aim",
          st.get("kind") == "build" and st.get("aim") == "build")
    check("and named after the thread", st.get("chapter") == "Weighted neighbours")

    status, body = post("/session", {"session": "lecture", "thread": "knn",
                                     "kind": "build"})
    check("tapping the thread already open goes back into it",
          status == 200 and body.get("resumed") is True)

    status, body = post("/aim", {"kind": "learn"})
    check("the kind changes mid-sitting through the aim",
          status == 200 and repo.state().get("kind") == "learn"
          and repo.state().get("aim") == "teach")

    status, body = post("/session", {"session": "lecture", "thread": "nope"})
    check("an unknown thread is refused", status == 400)

    # A rethink, on the thread the sitting is on.
    SAID = "Drop the scatter; report the dimension counts as a table instead."
    status, body = post("/direction", {"text": SAID})
    st = repo.state()
    check("a rethink is accepted", status == 200 and body.get("thread") == "knn")
    check("it does not write the workspace's direction",
          direction.read(tmp)[0] == "")
    check("the sitting stays on the thread and keeps its name",
          st.get("thread") == "knn" and st.get("chapter") == "Weighted neighbours")
    check("and keeps its kind", st.get("kind") == "learn")
    check("their sentence is attached to the sitting on the thread",
          st.get("rethink") == SAID)
    with open(repo.messages_path, "r", encoding="utf-8") as fh:
        line = [json.loads(l) for l in fh if l.strip()][-1].get("text", "")
    check("the woken turn is told to rewrite that thread's tasks",
          "RETHOUGHT THE THREAD" in line and "`knn`" in line
          and "board thread" in line and SAID in line)
    check("and to propose a new question as a thread rather than add it",
          "Propose it" in line and "board thread add" in line)
    check("the lesson is still archived and the tutor still replaced",
          len(replaced) >= 1)
    fresh()
    text = brief.briefing(repo, sense)
    check("the briefing carries the rethink in the thread's section",
          SAID in text.split("the method, and what this sitting is")[0])
    run(tmp, "open", "Proj", "--thread", "estimand")
    check("the rethink belongs to its sitting and is cleared by the next",
          "rethink" not in state(tmp))
finally:
    httpd.shutdown()

# ---------------------------------------------------------------------------
# the method
# ---------------------------------------------------------------------------
with open(os.path.join(ROOT, "TEACHING.md"), "r", encoding="utf-8") as fh:
    METHOD = fh.read()
for phrase, why in (
        ("## A coach sitting", "coach mode has a section of its own"),
        ("One step per card", "one step per card"),
        ("Imports first, in prose", "imports come first, in prose"),
        ("You write the plumbing yourself", "the tutor writes the plumbing"),
        ("run the check yourself", "the tutor runs the check"),
        ("You write no code for an estimator or a validation design",
         "no code for estimators or validation design"),
        ("a rethink is about the thread the sitting", "a rethink is the thread's")):
    check("TEACHING.md: " + why, phrase in METHOD)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a sitting belongs to a thread, and it is one of three kinds")
