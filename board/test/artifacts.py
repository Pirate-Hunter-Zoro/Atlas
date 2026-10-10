#!/usr/bin/env python3
"""Artifacts: doc.json = {title, source, sessions, asked_at}, and the library over them.

    python3 test/artifacts.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) with its own git
repository and a temp trash.

  * `create` makes `<subject>/docs/<slug>/doc.json` and reads "writing"; the
    source plus `board build` reads "done"; a quiet session whose turn ended
    with nothing built reads "failed".
  * Type: a beamer `.tex` is a deck, another `.tex` an article, a `.md` a paper.
  * The library lists artifacts first, legacy documents second with the ids
    they had before any doc.json existed, and `materials/*.pdf` last.
  * `delete` moves the directory to the trash, takes that document's ink keys
    and no other, and makes one commit; `POST /doc/delete` refuses a fenced
    path with 403.
  * `sessions.end` commits an in-place artifact that lists the session.
  * The payload and `/library.json` build with `library.stamp` patched to raise,
    and `writeups.waiting` judges an ask by its doc.json.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-artifacts-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-artifacts-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import artifacts, gitops, paths, sessions, writeups   # noqa: E402
from tutorboard.course import library                                 # noqa: E402
from tutorboard.course import repo as course_repo                     # noqa: E402
from tutorboard.server.routes import writing                          # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=base, env=ENV,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True).stdout.strip()


def commits():
    return int(git("rev-list", "--count", "HEAD") or 0)


os.environ.update({k: ENV[k] for k in ENV if k.startswith("GIT_")})
git("init", "-q")
root = os.path.join(base, "courses", "Topo")
write(os.path.join(root, "tutorboard.json"), json.dumps({"name": "Topo", "phi": False}))
# Two legacy documents and a material, in the shapes a course already has.
hw_dir = os.path.join(root, "chapters", "ch01-spaces", "homework")
write(os.path.join(hw_dir, "ch01-homework.tex"),
      "\\documentclass{article}\\title{Chapter 1 homework}\n")
write(os.path.join(hw_dir, "ch01-homework.pdf"), b"%PDF-1.4\n" + b"%" * 30000)
write(os.path.join(root, "notes", "intro.md"), "# An introduction\n\ntext\n")
write(os.path.join(root, "materials", "reading.pdf"), b"%PDF-1.4\n%small\n")
write(os.path.join(base, ".gitignore"), "/sessions/\n/courses/*/materials/\n.ink/\nlive/\n")
git("add", "-A")
git("commit", "-q", "-m", "fixture")

ok_pandoc = bool(shutil.which("pandoc"))

# ---------------------------------------------------------------------------
# legacy ids, before any doc.json exists
# ---------------------------------------------------------------------------
before = dict((d["rel"], d["id"]) for d in library._documents(root))
check("the fixture has its two legacy documents", len(before) >= 2, before)

# ---------------------------------------------------------------------------
# create, type, status
# ---------------------------------------------------------------------------
s1 = sessions.new("first", base=base)
art = artifacts.create("courses/Topo", "Compactness, explained", session=s1["id"],
                       ext="md", base=base)
check("create makes docs/<slug>/ with doc.json",
      art["rel"] == "docs/compactness-explained"
      and os.path.isfile(os.path.join(root, "docs", "compactness-explained", "doc.json")))
rec = artifacts.read(art["dir"])
check("doc.json holds exactly title, source, sessions and asked_at",
      sorted(rec) == ["asked_at", "sessions", "source", "title"]
      and rec["source"] == "compactness-explained.md"
      and rec["sessions"] == [s1["id"]] and rec["title"] == "Compactness, explained",
      rec)
check("a fresh artifact is being written", artifacts.status(art["dir"]) == "writing")
again = artifacts.create(root, "Compactness, explained", ext=".tex", base=base)
check("a second artifact with the same title takes -2",
      again["id"] == "compactness-explained-2")
try:
    artifacts.create(root, "x", ext="docx", base=base)
    refused = False
except ValueError:
    refused = True
check("an artifact's source is .tex or .md", refused)
check("a fenced name is never a slug", artifacts.slugify("Data") == "data-doc")

src = os.path.join(art["dir"], rec["source"])
# asked_at is to the second; the source is written after it.
time.sleep(1.1)
write(src, "# Compactness, explained\n\nEvery open cover has a finite subcover.\n")
check("a source with no build is still being written",
      artifacts.status(art["dir"]) == "writing")
if ok_pandoc:
    p = subprocess.run([sys.executable, BOARD, "build", src, "--format", "docx"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    check("board build builds it", p.returncode == 0, p.stdout)
    check("the source plus board build reads done",
          artifacts.status(art["dir"]) == "done")
else:
    print("skip  pandoc is not installed; the build half of status is untested")

check("type: a .md is a paper", art["type"] == "paper")
write(os.path.join(again["dir"], again["source"]),
      "\\documentclass[aspectratio=169]{beamer}\n\\title{Slides}\n")
check("type: a beamer .tex is a deck",
      artifacts.type_of(os.path.join(again["dir"], again["source"])) == "deck")
check("type: another .tex is an article",
      artifacts.type_of(os.path.join(hw_dir, "ch01-homework.tex")) == "article")

# failed: the asking session's turn is over, and nothing moved for QUIET.
s2 = sessions.new("second", base=base)
quiet_art = artifacts.create(root, "Nothing came", session=s2["id"], ext="md", base=base)
long_ago = time.time() - 600
rec = artifacts.read(quiet_art["dir"])
rec["asked_at"] = time.strftime(artifacts.WHEN, time.localtime(long_ago))
artifacts._write_json(os.path.join(quiet_art["dir"], "doc.json"), rec)
os.utime(os.path.join(quiet_art["dir"], "doc.json"), (long_ago, long_ago))
s2_dir = sessions.path(s2["id"], base)
write(os.path.join(s2_dir, "agent.json"), json.dumps({"state": "working"}), long_ago)
check("while the asking session's turn works, it is being written",
      artifacts.status(quiet_art["dir"]) == "writing")
write(os.path.join(s2_dir, "agent.json"), json.dumps({"state": "listening"}), long_ago)
check("once that turn is over and two quiet minutes passed, it failed",
      artifacts.status(quiet_art["dir"]) == "failed")
write(os.path.join(s2_dir, "inbox", "messages.jsonl"),
      json.dumps({"id": "t1", "text": "[writeup] x", "read": False}) + "\n")
check("an unread ask in that session's inbox is a queued turn, not a failure",
      artifacts.status(quiet_art["dir"]) == "writing")
os.remove(os.path.join(s2_dir, "inbox", "messages.jsonl"))

# ---------------------------------------------------------------------------
# place, and the library's order and ids
# ---------------------------------------------------------------------------
placed = artifacts.place(hw_dir, "ch01-homework.tex", "Chapter 1, written up",
                         session=s1["id"])
check("place writes doc.json in place with no asked_at",
      placed["source"] == "ch01-homework.tex" and placed["asked_at"] is None)
try:
    artifacts.place(hw_dir, "../../../notes/intro.md", "x")
    refused = False
except ValueError:
    refused = True
check("place refuses a source outside its directory", refused)

library.forget()
docs = library.documents(root)
after = dict((d["rel"], d["id"]) for d in docs if d["group"] != "artifact"
             or not d.get("own"))
check("LEGACY IDS DO NOT CHANGE, the placed one included",
      all(after.get(r) == i for r, i in before.items()), (before, after))
groups = [d["group"] for d in docs]
check("artifacts first, legacy second, materials last",
      groups == sorted(groups, key=["artifact", "legacy", "material"].index)
      and groups[0] == "artifact" and groups[-1] == "material", groups)
hw_doc = next(d for d in docs if d["rel"].endswith("ch01-homework.pdf"))
check("the placed document is an artifact under its old id, titled by doc.json",
      hw_doc["group"] == "artifact" and hw_doc["artifact"] == "chapters/ch01-spaces/homework"
      and hw_doc["title"] == "Chapter 1, written up" and hw_doc["status"] == "done")
mat = [d for d in docs if d["group"] == "material"]
check("a material PDF is listed and readable, however small",
      len(mat) == 1 and mat[0]["pdf"] and mat[0]["id"] == "materials-reading")
new_doc = library.find(root, "compactness-explained")
check("a new artifact's id is its slug, and it is found by it",
      new_doc and new_doc["own"] and new_doc["artifact"] == "docs/compactness-explained")
check("an artifact with no files yet is still listed",
      library.find(root, "nothing-came") is not None)
check("the stamp knows every id the list offers",
      set(library.stamp(root)["documents"]) == set(d["id"] for d in docs))
check("artifacts.get finds a new one and a placed one",
      artifacts.get(root, "compactness-explained")["own"]
      and artifacts.get(root, hw_doc["id"]) is not None)

# ---------------------------------------------------------------------------
# sessions.end commits the artifacts listing the session, in place too
# ---------------------------------------------------------------------------
sessions_rec = sessions.get(s1["id"], base)
sessions_rec["subject"] = "courses/Topo"
course_repo._write_json(os.path.join(sessions.path(s1["id"], base), "session.json"),
                        sessions_rec)
write(os.path.join(hw_dir, "ch01-homework.tex"),
      "\\documentclass{article}\\title{Chapter 1 homework}\n% an answer\n")
n0 = commits()
_, ok, said = sessions.end(s1["id"], base=base)
shown = git("show", "--name-only", "--format=", "HEAD").splitlines()
check("end commits the artifacts listing the session, in place and new",
      ok and commits() == n0 + 1
      and "courses/Topo/chapters/ch01-spaces/homework/ch01-homework.tex" in shown
      and "courses/Topo/chapters/ch01-spaces/homework/doc.json" in shown
      and "courses/Topo/docs/compactness-explained/compactness-explained.md" in shown
      and not any("nothing-came" in f for f in shown), (said, shown))

# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
ink = os.path.join(root, ".ink")
os.makedirs(ink)


def ink_for(key):
    for ext in (".json", ".png"):
        write(os.path.join(ink, writing.ann_file(key) + ext), "{}")


ink_for("doc/compactness-explained/p1")
ink_for("doc/compactness-explained/p12")
ink_for("doc/compactness-explained-2/p1")
ink_for("doc/materials-reading/p1")
n0 = commits()
got = artifacts.delete(root, art["dir"])
check("delete moves the directory to the trash",
      got["ok"] and not os.path.exists(art["dir"])
      and os.path.isfile(os.path.join(got["trash"], "compactness-explained", "doc.json")),
      got)
left = sorted(os.listdir(ink))
check("and takes that document's ink keys, and no other's",
      got["ink"] == 4 and len(left) == 4
      and all("compactness-explained-2" in n or "materials" in n for n in left), left)
check("in one commit that removes its tracked files",
      commits() == n0 + 1 and got["committed"]
      and not git("ls-files", "courses/Topo/docs/compactness-explained"))
n0 = commits()
got = artifacts.delete(root, quiet_art["dir"])
check("an untracked artifact leaves without a commit",
      got["ok"] and not got["committed"] and commits() == n0)

# ---------------------------------------------------------------------------
# the payload, the route, and the strip
# ---------------------------------------------------------------------------
from tutorboard.server import handler, hub, tikz            # noqa: E402
from tutorboard.runner import service as runner_service  # noqa: E402

repo = course_repo.Repo(root, os.path.join(root, "live"))
real_stamp = library.stamp


def refuse(*_a, **_k):
    raise RuntimeError("library.stamp was called")


library.stamp = refuse
try:
    library.forget()
    writeups.forget()
    status = library.status(repo)
    check("/library.json builds with library.stamp patched to raise",
          status["documents"] and status["subject"] == "courses/Topo")
    wid = "t0042"
    shown_art = artifacts.create(root, "A strip row", ext="md", base=base)
    writeups.ask(repo, wid, "paper", "a strip row", doc_dir=shown_art["rel"])
    worker = tikz.TikzWorker(repo)
    board = hub.Hub(repo, worker)
    rows = board.build().get("writeups") or []
    check("the payload builds with library.stamp patched to raise, and the "
          "strip reads the doc.json", len(rows) == 1 and rows[0]["state"] == "writing",
          rows)
    if ok_pandoc:
        time.sleep(1.1)
        s = os.path.join(shown_art["dir"], shown_art["source"])
        write(s, "# A strip row\n")
        subprocess.run([sys.executable, BOARD, "build", s, "--format", "docx"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        writeups.forget()
        rows = writeups.waiting(repo) or []
        check("built, the strip says done and names the document",
              rows and rows[0]["state"] == "done" and rows[0]["doc"] == "a-strip-row",
              rows)
finally:
    library.stamp = real_stamp

runner_service.wake = lambda r: True
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = board
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def post(path, body):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), method="POST",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


try:
    fenced_dir = os.path.join(root, "docs", "data")
    write(os.path.join(fenced_dir, "doc.json"),
          json.dumps({"title": "x", "source": "data.md", "sessions": [], "asked_at": None}))
    code, body = post("/doc/delete", {"subject": "courses/Topo", "id": "data"})
    check("a delete under a fenced path returns 403, and nothing moves",
          code == 403 and os.path.isdir(fenced_dir), (code, body))
    code, body = post("/doc/delete", {"subject": "projects/phi", "id": "x"})
    check("so does a fenced subject", code == 403, (code, body))
    code, body = post("/doc/delete", {"subject": "courses/Topo", "id": "no-such"})
    check("an id the library does not have is a miss", code == 404)
    code, body = post("/doc/delete", {"subject": "../../etc", "id": "x"})
    check("a subject that is a path is a miss", code == 404)
    legacy_id = before[next(r for r in before if r.startswith("notes/"))]
    code, body = post("/doc/delete", {"subject": "courses/Topo", "id": legacy_id})
    check("a legacy document with no doc.json is not the board's to delete",
          code == 404 and os.path.isfile(os.path.join(root, "notes", "intro.md")))
    ink_for("doc/%s/p2" % hw_doc["id"])
    n0 = commits()
    code, body = post("/doc/delete", {"subject": "courses/Topo", "id": hw_doc["id"]})
    check("the route deletes an artifact after the second tap",
          code == 200 and body.get("ok") and commits() == n0 + 1
          and not os.path.exists(os.path.join(hw_dir, "doc.json"))
          and not os.path.exists(os.path.join(hw_dir, "ch01-homework.tex")), body)
    check("an in-place delete leaves the rest of the directory alone",
          os.path.isdir(hw_dir) and not [n for n in os.listdir(ink) if hw_doc["id"] in n])
    check("the trash path never reaches the browser", "trash" not in body)
finally:
    httpd.shutdown()

shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(trash, ignore_errors=True)
if fails:
    print("\n%d FAILED" % len(fails))
    sys.exit(1)
print("\nall artifacts checks passed")
