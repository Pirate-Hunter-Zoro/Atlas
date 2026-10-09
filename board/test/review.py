#!/usr/bin/env python3
"""A test review: revision over a scope the student chose.

The board already had two kinds of sitting and both of them decide the problem
list somewhere the student is not: a lecture's is the tutor's to pick, a
homework's was set on a sheet. Revising for a test is neither — the student is
the only one who knows what is on the paper — so the scope is chosen on the
board, from what the repository actually has, and the tutor is told it and told
not to widen it.

What is guarded here is everything that could let a name nobody chose reach the
filesystem or the tutor's prompt, and the two shapes of repository: a course has
chapters, a project has parts, and neither is invented for the other.
"""

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import review   # noqa: E402
from tutorboard import sense
from tutorboard.course import repo as course_repo
from tutorboard.lesson import archive
from tutorboard.server import handler
from tutorboard.server import hub
from tutorboard.server import tikz
from http.server import ThreadingHTTPServer

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# --- what a repository can be reviewed over -----------------------------------
# Discovered, never registered: the same rule as course discovery and problem-set
# discovery, and for the same reason -- an index is a thing that goes stale.
book = tempfile.mkdtemp(prefix="tutor-rev-book-")
proj = tempfile.mkdtemp(prefix="tutor-rev-proj-")
flat = tempfile.mkdtemp(prefix="tutor-rev-flat-")
bare = tempfile.mkdtemp(prefix="tutor-rev-bare-")
try:
    with open(os.path.join(book, "chapters.tsv"), "w", encoding="utf-8") as fh:
        fh.write("01\t1\t9\tch01-a\tGroups, fields and vector spaces\n"
                 "02\t10\t19\tch02-b\tThe Euclidean algorithm\n"
                 "07\t60\t70\tch07-c\tSplitting fields\n")

    units = review.units(book)
    check("a course offers its own chapters", len(units) == 3)
    check("and they are chapters, not parts",
          review.kind(book) == "chapters" and units[0]["kind"] == "chapter")
    check("in the order the course puts them in",
          [u["short"] for u in units] == ["Ch 01", "Ch 02", "Ch 07"])

    for d in ("web", "scripts", "bin", "live", "node_modules", "__pycache__", ".git"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)
    with open(os.path.join(proj, "serve.py"), "w") as fh:
        fh.write("x\n")
    names = [u["name"] for u in review.units(proj)]
    check("a project with no chapters offers its own parts instead",
          review.kind(proj) == "parts" and names == ["bin", "scripts", "web"])
    # Nobody revises their build output or somebody else's library, and the
    # board's own working directory is not part of the project at all.
    check("and never build output, dependencies or the board's own live/",
          not ({"live", "node_modules", "__pycache__", ".git"} & set(names)))

    for f in ("main.py", "util.py", "README.md"):
        with open(os.path.join(flat, f), "w") as fh:
            fh.write("x\n")
    check("a flat project falls back to its own source files",
          [u["name"] for u in review.units(flat)] == ["main.py", "util.py"])

    check("a repository with neither says so rather than inventing one",
          review.units(bare) == [] and review.status(bare, {}) is None)

    # --- a name from a request is checked, never trusted -----------------------
    chosen, unknown = review.resolve(book, ["Ch 07 — Splitting fields", "ch01"])
    check("a chapter can be named by its label or by its number",
          [u["short"] for u in chosen] == ["Ch 01", "Ch 07"])
    check("and the scope comes back in the course's order, not the tapping order",
          [u["short"] for u in chosen] == ["Ch 01", "Ch 07"])
    check("a name this course does not have is reported, not dropped",
          review.resolve(book, ["ch99"])[1] == ["ch99"])
    check("naming the same chapter twice reviews it once",
          len(review.resolve(book, ["7", "ch07", "Ch 07"])[0]) == 1)
    # `chapters.tsv` writes 07 and a chapter directory writes 7. Both are the
    # course's own way of saying the same thing.
    check("padded and unpadded chapter numbers both find it",
          review.resolve(book, ["7"])[0] and review.resolve(book, ["07"])[0])

    # --- the scope is re-resolved, never echoed back --------------------------
    state = {"review": ["Ch 01 — Groups, fields and vector spaces",
                        "Ch 99 — deleted since"]}
    scope = review.scope(book, state)
    check("a scope naming something that no longer exists drops it",
          [u["short"] for u in scope] == ["Ch 01"])

    check("a short scope is named in the sitting label",
          review.sitting_label(review.resolve(book, ["1", "7"])[0])
          == "Test review — Ch 01, Ch 07")
    check("and a long one is counted instead of listed",
          review.sitting_label(review.resolve(book, ["1", "2", "7"])[0]
                               + [{"short": "Ch 08"}], "chapters")
          == "Test review — 4 chapters")
finally:
    for d in (proj, flat, bare):
        shutil.rmtree(d, ignore_errors=True)

# --- the sitting itself, through the real handler -----------------------------
tmp = tempfile.mkdtemp(prefix="tutor-rev-")
json.dump({"name": "Galois Theory", "mode": "math"},
          open(os.path.join(tmp, "tutorboard.json"), "w"))
shutil.copy(os.path.join(book, "chapters.tsv"), os.path.join(tmp, "chapters.tsv"))
repo = course_repo.Repo(tmp)
open(os.path.join(repo.cards, "0001-mid-lesson.md"), "w", encoding="utf-8").write(
    "---\nkind: lesson\ntitle: A card\n---\n\nwork in progress\n")

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
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


try:
    payload = board.build()
    check("the board is told what can be reviewed before any review exists",
          payload.get("review") and len(payload["review"]["units"]) == 3)
    check("and that nothing is being reviewed yet",
          payload["review"]["scope"] == [])

    # A review is a method the tutor picks in teach mode, not a sitting kind.
    status, _ = post("/session", {
        "session": "review",
        "over": ["Ch 01 — Groups, fields and vector spaces"]})
    check("the board no longer opens a review sitting", status == 400)
    check("and the lesson it would have interrupted is untouched",
          not archive.list_archive(repo) and len(os.listdir(repo.cards)) == 1)
    line = sense.session_sense(repo)
    check("teach mode names a review among the methods the tutor picks",
          "a review over a scope they name" in line)
    check("and a lecture prompt is a lecture's", "manageable few" in line)
finally:
    httpd.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

# --- a project is taught with the one method ----------------------------------
tmp2 = tempfile.mkdtemp(prefix="tutor-rev-code-")
try:
    json.dump({"name": "TRD-EHR"},
              open(os.path.join(tmp2, "tutorboard.json"), "w"))
    for d in ("loader", "pipeline"):
        os.makedirs(os.path.join(tmp2, d))
    repo2 = course_repo.Repo(tmp2)
    st = repo2.state()
    st.update({"session": "lecture", "mode": "do"})
    json.dump(st, open(repo2.state_path, "w"))
    line = sense.session_sense(repo2)
    check("an ordinary sitting in a project is the one method",
          "THE LESSON IS EXERCISES" in line)
    check("and is told where to look, since there is no book here",
          "does not follow a book" in line and "TUTOR.md" in line
          and "README.md" not in line)
    check("and not to invent chapters out of what it finds",
          "manufacture a curriculum" in line)
    check("and do mode says to write the code", "IN DO MODE" in line)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)
    shutil.rmtree(book, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails
      else "a review covers what the student chose and nothing else")
sys.exit(1 if fails else 0)
