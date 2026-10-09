#!/usr/bin/env python3
"""What is left of a change of direction: `tutorboard/direction.py`.

The module still writes, reads and labels DIRECTION.md, and its sentences
still say what a woken turn does with one. The tap that drove it, `POST
/direction`, went with the map layer (T50); T30c deletes the module.
"""

import json
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import brief, direction, sense
from tutorboard.course import repo as course_repo
from tutorboard.server import handler, hub, tikz
from tutorboard.runner import service as runner_service  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---------------------------------------------------------------------------
# the file itself
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-direction-")
with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Test Course"}, fh)

SAID = ("Drop the model bake-off. This is now about calibrating the clinician "
        "ratings, and nothing else.")

check("nothing is in force in a workspace nobody has redirected",
      direction.read(tmp) == ("", ""))
check("and the briefing says nothing at all about it",
      direction.standing(tmp) == "")

kept, when = direction.write(tmp, SAID)
check("what they said is written at the root, where it crosses machines",
      os.path.isfile(os.path.join(tmp, "DIRECTION.md")))
check("it comes back as they wrote it", direction.read(tmp)[0] == SAID)
check("and stamped with when, because a direction is a thing they did on a day",
      bool(direction.read(tmp)[1]) and direction.read(tmp)[1] == when)
# The stamp is machinery and must never be part of what the tutor is handed.
check("the stamp is not part of their words", "<!--" not in direction.read(tmp)[0])

label = direction.label(SAID)
check("the sitting is named after the first thing they said",
      label.startswith("New direction") and "bake-off" in label)
check("and it fits the title bar", len(label) <= len("New direction — ") + 61)
check("a direction with no sentence-ending punctuation still gets a name",
      direction.label("rebuild the whole thing around consent").startswith("New direction"))

# ---------------------------------------------------------------------------
# what a turn is told
# ---------------------------------------------------------------------------
# This is the half that decides whether the tap did anything: a plan, a map and a
# handoff all written for the direction it replaced are worse than nothing, and a
# turn that reads the new direction LAST has already believed three of them.
said = direction.standing(tmp)
check("the standing direction quotes them rather than paraphrasing", SAID in said)
check("and says outright that it outranks the other documents",
      "outranks" in said)
check("and that bringing them true is the work rather than a separate job",
      "out of date" in said and "part of the work" in said)
check("and that the change is not to be argued with",
      "Do not argue" in said)

# The brief reads RULES.md and TUTOR.md only (T30a); the direction reaches the
# woken turn through the inbox line, and T30c deletes DIRECTION.md.
text = brief.briefing(course_repo.Repo(tmp), sense)
check("the brief no longer reads DIRECTION.md", SAID not in text)

check("the turn woken by the change is told to rewrite the plan, not to ask",
      "REWRITE THE PLAN" in direction.CHANGED
      and "Do not ask permission" in direction.CHANGED)
check("and to rewrite the threads with the command that writes them",
      "board thread" in direction.CHANGED)
check("and to put a sentence on the board before it starts, so it is not blank",
      "board write" in direction.CHANGED)
check("and to report over that sentence rather than writing a second card",
      "board write --over" in direction.CHANGED)
check("a plan handed back instead of the work is named as the failure",
      "hand back a plan" in direction.CHANGED)

# ---------------------------------------------------------------------------
# the whole round trip
# ---------------------------------------------------------------------------
direction.clear(tmp)
repo = course_repo.Repo(tmp)

# The one thing that must not actually happen in a test: a turn. What is
# checked is that one is QUEUED.
replaced = []
runner_service.wake = lambda r: replaced.append(r) or True

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
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {}


try:
    status, body = post("/direction", {"text": SAID})
    check("POST /direction is gone with the map layer (T50)",
          status == 404 and not os.path.exists(os.path.join(tmp, "DIRECTION.md"))
          and not replaced)
finally:
    httpd.shutdown()

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the direction is theirs to change, and everything under it is redone")
