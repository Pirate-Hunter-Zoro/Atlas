#!/usr/bin/env python3
"""Delete from the iPad, against a real server: a subject (its name typed,
D23's `"phi": false` at HEAD, no open session, coding session or outstanding
request), a material and a session (each after a second tap on the page,
which is `test/uploads.js`'s and `test/home.js`'s), and the trash pruned
after 30 days.

One server on an ephemeral port over a temp Atlas tree with git, and a trash
of its own (TUTORBOARD_TRASH).
"""

import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-deleting-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
TRASH = os.path.join(tmp, ".trash")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = TRASH
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")
for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"),
             ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v

from tutorboard import sessions                               # noqa: E402
from tutorboard.server import app                             # noqa: E402
from tutorboard.server.routes import writing                  # noqa: E402
from tutorboard.runner import service as runner_service       # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


runner_service.wake = lambda repo: False


def put(rel, text):
    p = os.path.join(atlas, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def git(*args):
    return subprocess.run(["git", "-C", atlas] + list(args), check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True).stdout


def commits():
    return int(git("rev-list", "--count", "HEAD").strip())


put(".gitignore", "/sessions/\nmaterials/\n.ink/\n")
for slug in ("Gone", "Open", "Pending", "Coded", "Keep"):
    put("courses/%s/tutorboard.json" % slug, json.dumps({"name": slug, "phi": False}))
    put("courses/%s/TUTOR.md" % slug, "# %s\n" % slug)
put("courses/Gone/hw/set1.tex", "\\documentclass{article}\n")
put("courses/Gone/materials/book.pdf", "%PDF-1.4 not really\n")      # ignored residue
put("projects/Secret/tutorboard.json", json.dumps({"name": "Secret", "phi": True}))
put("projects/NoKey/tutorboard.json", json.dumps({"name": "NoKey"}))
put("projects/Flipped/tutorboard.json", json.dumps({"name": "Flipped", "phi": True}))
put("courses/Pending/relay/requests/r1.json", json.dumps({"id": "r1", "kind": "job"}))
subprocess.run(["git", "init", "-q", atlas], check=True)
git("add", "-A")
git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture")
# The working tree says false; HEAD does not.
put("projects/Flipped/tutorboard.json", json.dumps({"name": "Flipped", "phi": False}))

open_one = sessions.new("open on Open", base=atlas)
sessions.bind(open_one["id"], "courses/Open", base=atlas)
coded = sessions.new("coding on Coded", base=atlas)
sessions.bind(coded["id"], "courses/Coded", base=atlas)
sessions.end(coded["id"], base=atlas)
rec = sessions.get(coded["id"], atlas)
rec["code"] = {"subject": "courses/Coded", "ref": "code/%s" % coded["id"]}
with open(os.path.join(sessions.path(coded["id"], atlas), "session.json"), "w") as fh:
    json.dump(rec, fh)

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def ask(method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    conn.request(method, path, body=data,
                 headers={"Content-Type": "application/json"} if data else {})
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    try:
        return r.status, json.loads(raw.decode("utf-8"))
    except ValueError:
        return r.status, {}


def listed():
    return [s["id"] for s in ask("GET", "/subjects.json")[1].get("subjects", [])]


def gone(subject, typed):
    return ask("POST", "/subject/delete", {"subject": subject, "typed": typed})


# ---------------------------------------------------------------------------
# a subject
# ---------------------------------------------------------------------------
n = commits()
status, got = gone("../x", "x")
check("../x gets 400", status == 400)
status, _ = gone("courses/../courses/Gone", "Gone")
check("a path that only resolves to a subject gets 400", status == 400)
status, got = gone("courses/Gone", "gone")
check("a typed name that is not the slug gets 400, naming the slug",
      status == 400 and "Gone" in got.get("error", ""))
status, got = gone("projects/Secret", "Secret")
check('"phi": true gets 409, with the reason',
      status == 409 and "phi" in got.get("error", ""))
status, got = gone("projects/NoKey", "NoKey")
check("no phi key gets 409", status == 409 and "no phi key" in got.get("error", ""))
status, got = gone("projects/Flipped", "Flipped")
check('"phi": false in the working tree but not at HEAD gets 409', status == 409)
status, got = gone("courses/Open", "Open")
check("an open session on it gets 409, naming the session",
      status == 409 and open_one["id"] in got.get("error", ""))
status, got = gone("courses/Coded", "Coded")
check("a session holding a coding session on it gets 409",
      status == 409 and "coding" in got.get("error", ""))
status, got = gone("courses/Pending", "Pending")
check("a request with no terminal report gets 409, naming it",
      status == 409 and "r1" in got.get("error", ""))
check("nothing refused moved or committed",
      commits() == n and all(os.path.isdir(os.path.join(atlas, s)) for s in (
          "projects/Secret", "projects/NoKey", "courses/Open", "courses/Coded",
          "courses/Pending")) and not os.path.isdir(TRASH))
put("courses/Pending/relay/reports/r1.json",
    json.dumps({"id": "r1", "state": "completed"}))
status, _ = gone("courses/Pending", "Pending")
check("once the report is terminal, it goes", status == 200)

n = commits()
status, got = gone("courses/Gone", "Gone")
check("a fixture subject is deleted", status == 200 and got.get("ok"))
check("in one commit", commits() == n + 1)
check("its tracked files left git",
      git("ls-files", "--", "courses/Gone").strip() == "")
check("the commit holds only its files",
      all(l.startswith("courses/Gone/") for l in
          git("show", "--name-only", "--format=", "HEAD").split()))
check("and it is off /subjects.json",
      "courses/Gone" not in listed() and "courses/Keep" in listed())
stamped = [os.path.join(TRASH, d) for d in sorted(os.listdir(TRASH))]
residue = [os.path.join(d, "courses-Gone", "materials", "book.pdf") for d in stamped]
check("its ignored residue went to the trash with the rest",
      any(os.path.isfile(p) for p in residue) and
      not os.path.exists(os.path.join(atlas, "courses", "Gone")))
check("a session can bind to it no longer",
      ask("POST", "/s/%s/bind" % open_one["id"], {"subject": "courses/Gone"})[0] == 400)

# ---------------------------------------------------------------------------
# a material
# ---------------------------------------------------------------------------
put("courses/Keep/materials/book.pdf", "%PDF-1.4 a book\n")
put("courses/Keep/materials/notes/week1.pdf", "%PDF-1.4 notes\n")
ident = sessions.ink_ident("materials/book.pdf")
ink = put("courses/Keep/.ink/%s.json" % writing.ann_file("doc/%s/p1" % ident),
          json.dumps({"card": "doc/%s/p1" % ident, "strokes": []}))
status, got = ask("GET", "/materials.json?subject=courses/Keep")
names = [m["name"] for m in got.get("materials", [])]
check("/materials.json lists a subject's materials, nested ones by path",
      status == 200 and sorted(names) == ["book.pdf", "notes/week1.pdf"])
status, _ = ask("GET", "/s/%s/materials.json" % open_one["id"])
check("and a session's own subject's, under /s/<id>/", status == 200)
n = commits()
status, _ = ask("POST", "/material/delete?subject=courses/Keep", {"name": "../TUTOR.md"})
check("a material delete of ../TUTOR.md is 404", status == 404 and
      os.path.isfile(os.path.join(atlas, "courses", "Keep", "TUTOR.md")))
status, got = ask("POST", "/material/delete?subject=courses/Keep",
                  {"subject": "courses/Keep", "name": "book.pdf"})
check("a material goes to the trash", status == 200 and not os.path.exists(
    os.path.join(atlas, "courses", "Keep", "materials", "book.pdf")))
check("with its ink", not os.path.exists(ink) and any(
    os.path.isfile(os.path.join(TRASH, d, ".ink", os.path.basename(ink)))
    for d in os.listdir(TRASH)))
check("and no commit, the file being ignored", commits() == n)
status, _ = ask("POST", "/material/delete?subject=courses/Keep", {"name": "book.pdf"})
check("asked again it is 404", status == 404)

# ---------------------------------------------------------------------------
# a session
# ---------------------------------------------------------------------------
doomed = sessions.new("doomed", base=atlas)
status, _ = ask("GET", "/s/%s/board" % doomed["id"])
check("a session's board answers", status == 200)
status, got = ask("POST", "/session/delete", {"id": doomed["id"]})
check("a session is deleted", status == 200 and got.get("ok"))
check("to the trash", not sessions.path(doomed["id"], atlas) and any(
    os.path.isdir(os.path.join(TRASH, d, doomed["id"])) for d in os.listdir(TRASH)))
check("and its board is gone with it",
      ask("GET", "/s/%s/board" % doomed["id"])[0] == 404)
check("no such session is 404",
      ask("POST", "/session/delete", {"id": doomed["id"]})[0] == 404
      and ask("POST", "/session/delete", {"id": "../x"})[0] == 404)
check("under /s/<id>/ the delete routes are not served",
      ask("POST", "/s/%s/session/delete" % open_one["id"],
          {"id": open_one["id"]})[0] == 404
      and sessions.path(open_one["id"], atlas))


class Busy(object):
    def busy(self, sid=None):
        return sid == open_one["id"]


runner_service.RUNNER = Busy()
status, _ = ask("POST", "/session/delete", {"id": open_one["id"]})
check("a session whose turn runs gets 409", status == 409
      and sessions.path(open_one["id"], atlas))
runner_service.RUNNER = None

# ---------------------------------------------------------------------------
# the trash, pruned at 30 days
# ---------------------------------------------------------------------------
now = time.time()
old = time.strftime(sessions.STAMP, time.localtime(now - 31 * 86400))
young = time.strftime(sessions.STAMP, time.localtime(now - 29 * 86400))
for name in (old, old + "-2", young, "not-a-stamp"):
    os.makedirs(os.path.join(TRASH, name, "x"))
pruned = sessions.prune_trash(now=now)
check("the trash drops entries older than 30 days",
      sorted(pruned) == [old, old + "-2"]
      and not os.path.exists(os.path.join(TRASH, old)))
check("and keeps younger ones, and anything it did not make",
      os.path.isdir(os.path.join(TRASH, young))
      and os.path.isdir(os.path.join(TRASH, "not-a-stamp")))
src = open(os.path.join(ROOT, "tutorboard", "server", "app.py")).read()
check("the server prunes it at startup", "sessions.prune_trash()" in src)

httpd.shutdown()
if fails:
    print("\n%d failed" % len(fails))
    sys.exit(1)
print("\nall passed")
