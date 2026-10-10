#!/usr/bin/env python3
"""The board at /s/<id>/board, end to end: a real server, the page and its
scripts off it, and every answer the page writes landing in that session.

    python3 board/test/onesession.py                    a fixture subject, port 0
    python3 board/test/onesession.py --galois --port 8779
                                                        the rehearsal: a copy of
                                                        courses/Galois-Theory

The server runs in this process with every command it would start recorded
instead, so no tutor and no model runs. `sessionpage.js` loads the board in
jsdom against it, writes ink on the card, a page of the slate and a typed
answer, and reports every request it made. Then the disk is read: each answer
is in the session, a second session on the same subject is untouched, and so
is the subject.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

ap = argparse.ArgumentParser()
ap.add_argument("--galois", action="store_true",
                help="serve a copy of courses/Galois-Theory instead of a fixture")
ap.add_argument("--port", type=int, default=0)
args = ap.parse_args()

if not shutil.which("node"):
    print("skip  node is not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="tutor-onesession-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard import sessions                               # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.runner import service as runner_service      # noqa: E402
from tutorboard.server import app                             # noqa: E402
from tutorboard.net import tailscale                         # noqa: E402

# No tailnet here: `tailscale status` can take 20 s to give up when tailscaled
# is not answering, and /health asks for this machine's tailnet name.
tailscale._ts_status = lambda: {}

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


CALLS = []
runner_service.wake = lambda repo: CALLS.append(("wake", repo.live)) or False


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


SUBJECT = "courses/Galois-Theory"
MARK = "onesession-marker-5e1a"
real = os.path.join(os.path.dirname(ROOT), SUBJECT)
if args.galois:
    if not os.path.isdir(real):
        print("FAIL no %s to copy" % real)
        sys.exit(1)
    shutil.copytree(real, os.path.join(atlas, SUBJECT), symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "phi", "results"))
else:
    write(os.path.join(atlas, SUBJECT, "tutorboard.json"),
          json.dumps({"name": "Galois Theory", "phi": False}))
    write(os.path.join(atlas, SUBJECT, "TUTOR.md"), "# Galois Theory\n")
write(os.path.join(atlas, ".gitignore"), "/sessions/\n**/.ink/\n")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
subprocess.run(["git", "init", "-q", atlas], check=True)
subprocess.run(GIT + ["-C", atlas, "add", "-A"], check=True)
subprocess.run(GIT + ["-C", atlas, "commit", "-q", "-m", "fixture"], check=True)

SID, DIR = {}, {}
for n, who in enumerate(("A", "B")):
    rec = sessions.new("session " + who, base=atlas, now=1.7e9 + n)
    SID[who] = rec["id"]
    DIR[who] = sessions.path(rec["id"], atlas)
    course_repo.Repo(atlas, session=DIR[who], create=False).set_state(subject=SUBJECT)
    write(os.path.join(DIR[who], "cards", "0001-tower.md"),
          "---\nkind: question\ntitle: The tower law\n---\n\n"
          "Show that [L:K] = [L:M][M:K]. %s %s\n" % (who, MARK))


def tree(top):
    out = {}
    for d, dirs, files in os.walk(top):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            p = os.path.join(d, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, top)] = hashlib.sha1(fh.read()).hexdigest()
    return out


before_b = tree(DIR["B"])
before_subject = tree(os.path.join(atlas, SUBJECT))

httpd = app.make_server(atlas, args.port)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port
url = "http://127.0.0.1:%d/s/%s/board" % (PORT, SID["A"])
print("     serving %s on port %d, the board at %s" % (
    "a copy of " + SUBJECT if args.galois else "a fixture", PORT, url))

try:
    run = subprocess.run(["node", os.path.normpath(os.path.join(HERE, "./sessionpage.js")),
                          url, MARK],
                         cwd=ROOT, capture_output=True, text=True, timeout=180)
finally:
    httpd.shutdown()
line = (run.stdout.strip().splitlines() or ["{}"])[-1]
try:
    got = json.loads(line)
except ValueError:
    print(run.stdout)
    print(run.stderr)
    got = {}
if got.get("skip"):
    print("skip  " + got["skip"])
    sys.exit(0)

prefix = "/s/%s/" % SID["A"]
reqs = [r for r in got.get("requests", []) if not r.get("script")]
check("the page loaded with no error (%s)" % "; ".join(got.get("errors") or ["none"]),
      not got.get("errors"))
check("the card renders at /s/<id>/board", got.get("rendered") is True)
stray = [r["url"] for r in reqs if not r["url"].startswith(prefix)
         and not r["url"].startswith("/static/")]
check("every request is under %s or /static/ (%d requests)" % (prefix, len(reqs)),
      reqs and not stray)
if stray:
    print("     outside: " + " ".join(stray))
bad = ["%s %s -> %s" % (r["method"], r["url"], r.get("status")) for r in reqs
       if r.get("status") not in (200,)]
check("and the server answered each of them", not bad)
if bad:
    print("     " + "\n     ".join(bad))


def asked(path, method="POST"):
    return [r for r in reqs if r["url"] == prefix + path.lstrip("/") and r["method"] == method]


check("the stream is the session's", bool(asked("events", "STREAM")))

# Ink on the card.
notes = os.path.join(DIR["A"], "annotations")
inked = [f for f in os.listdir(notes) if f.endswith(".json")] if os.path.isdir(notes) else []
check("ink on the card saved through %sannotate/save" % prefix,
      bool(asked("annotate/save")) and bool(inked))
check("into the session's annotations/", any(
    "0001" in f and json.load(open(os.path.join(notes, f))).get("strokes") for f in inked))

# A page of the slate.
slate = os.path.join(DIR["A"], "slate")
pages = [f for f in os.listdir(slate) if f.endswith(".json")] if os.path.isdir(slate) else []
check("a slate page saved through %sslate/save" % prefix, bool(asked("slate/save")))
check("into the session's slate/", any(
    "220" in open(os.path.join(slate, f)).read() for f in pages))

# A typed answer: the draft, then the send.
draft = os.path.join(DIR["A"], "text", "0001.txt")
check("the typed draft saved through %stext/save" % prefix, bool(asked("text/save")))
inbox = os.path.join(DIR["A"], "inbox", "messages.jsonl")
said = open(inbox).read() if os.path.isfile(inbox) else ""
check("and the typed answer went through %ssay into the session's inbox" % prefix,
      bool(asked("say")) and ("typed " + MARK) in said)
check("and the draft was kept in the session's text/ until then",
      os.path.isfile(draft) or ("typed " + MARK) in said)

# Nothing anywhere else.
check("the other session on the same subject is untouched", tree(DIR["B"]) == before_b)
after_subject = tree(os.path.join(atlas, SUBJECT))
# `/seen` writes only the session's own `seen`: nothing in the subject moves.
check("and so is the subject", after_subject == before_subject)
if after_subject != before_subject:
    print("     changed: " + " ".join(sorted(k for k in set(after_subject) | set(before_subject)
                                             if after_subject.get(k) != before_subject.get(k))))
check("the tutor was woken for session A only",
      all(c[1] == DIR["A"] for c in CALLS if c[0] == "wake"))

shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the board under /s/<id>/ reads and writes only its own session")
