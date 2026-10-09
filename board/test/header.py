#!/usr/bin/env python3
"""The session header against a real server: the chip binds, the toggle flips
`mode`, End ends, and an ended session refuses what would write to it.

One server on an ephemeral port over a temp Atlas tree with git. The board's
side of the same controls (four of them, a second tap for End, the chip
updated without a reload) is `test/link.js`'s.
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

tmp = tempfile.mkdtemp(prefix="tutor-header-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")
for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"),
             ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v

from tutorboard import sessions                               # noqa: E402
from tutorboard.server import app                             # noqa: E402
from tutorboard.runner import service as runner_service       # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# No turn is ever started here.
WOKEN = []
runner_service.wake = lambda repo: WOKEN.append(repo.live) or False

os.makedirs(os.path.join(atlas, "projects", "Beta"))
with open(os.path.join(atlas, "projects", "Beta", "tutorboard.json"), "w") as fh:
    json.dump({"name": "Beta", "phi": False}, fh)
with open(os.path.join(atlas, ".gitignore"), "w") as fh:
    fh.write("/sessions/\n")
subprocess.run(["git", "init", "-q", atlas], check=True)
subprocess.run(["git", "-C", atlas, "add", "-A"], check=True)
subprocess.run(["git", "-C", atlas, "-c", "commit.gpgsign=false", "commit", "-q",
                "-m", "fixture"], check=True)

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


def record(sid):
    return sessions.get(sid, atlas)


def board_state(sid):
    return ask("GET", "/s/%s/board.json" % sid)[1].get("state") or {}


def until(fn, seconds=8.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        got = fn()
        if got:
            return got
        time.sleep(0.1)
    return fn()


class Stream(object):
    """The board's event stream, read on a thread: every frame's state."""

    def __init__(self, sid):
        self.states = []
        self.conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
        self.conn.request("GET", "/s/%s/events" % sid)
        self.resp = self.conn.getresponse()
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        try:
            while True:
                line = self.resp.fp.readline()
                if not line:
                    return
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    try:
                        frame = json.loads(line[len("data: "):])
                    except ValueError:
                        continue
                    if isinstance(frame, dict) and isinstance(frame.get("state"), dict):
                        self.states.append(frame["state"])
        except Exception:                                     # noqa: BLE001
            return


# ---------------------------------------------------------------------------
# a new session, unbound, in teach
# ---------------------------------------------------------------------------
status, made = ask("POST", "/sessions/new", {})
SID = made.get("id")
check("a new session opens", status == 200 and SID)
st = until(lambda: board_state(SID).get("id") and board_state(SID))
check("its payload says unbound and teach",
      st.get("subject") is None and st.get("mode") == "teach" and not st.get("ended"))

stream = Stream(SID)
until(lambda: stream.states)
check("the board's stream is open", bool(stream.states))

# ---------------------------------------------------------------------------
# the chip: make a course, then bind to it
# ---------------------------------------------------------------------------
status, got = ask("POST", "/subjects/new", {"kind": "course", "name": "Linear Algebra"})
check("the chip's + new course makes and commits it",
      status == 200 and got.get("subject", {}).get("id") == "courses/Linear-Algebra")
status, got = ask("POST", "/s/%s/bind" % SID, {"subject": "courses/Linear-Algebra"})
check("POST /s/<id>/bind binds it (%d)" % status,
      status == 200 and got.get("changed") is True
      and got.get("subject", {}).get("name") == "Linear Algebra")
check("session.json says so", record(SID).get("subject") == "courses/Linear-Algebra")
with open(os.path.join(sessions.path(SID, atlas), "inbox", "messages.jsonl")) as fh:
    lines = [json.loads(x) for x in fh if x.strip()]
check("with one non-waking [bind] line",
      [x["text"] for x in lines if x.get("signal") == "bind"] == ["[bind] courses/Linear-Algebra"]
      and all(x.get("wake") is False for x in lines if x.get("signal") == "bind"))
check("and no turn woken", not WOKEN)
entry = httpd.registry.get(SID)
check("the hub now serves the subject's root",
      os.path.realpath(entry.hub.repo.root)
      == os.path.realpath(os.path.join(atlas, "courses", "Linear-Algebra")))
check("the open stream carries the bound subject and its name, so no reload is needed",
      until(lambda: any(s.get("subject") == "courses/Linear-Algebra"
                        and s.get("course") == "Linear Algebra" for s in stream.states)))

status, got = ask("POST", "/s/%s/bind" % SID, {"subject": "courses/Linear-Algebra"})
check("binding again changes nothing", status == 200 and got.get("changed") is False)
for bad in ("../x", "/etc", "courses/Nowhere", ""):
    status, got = ask("POST", "/s/%s/bind" % SID, {"subject": bad})
    check("binding to %r is refused (%d)" % (bad, status), status == 400)
check("and the session stays bound", record(SID).get("subject") == "courses/Linear-Algebra")
status, got = ask("POST", "/s/%s/bind" % SID, {"subject": "projects/Beta"})
check("rebinding to another subject is allowed",
      status == 200 and record(SID).get("subject") == "projects/Beta")
status, _ = ask("POST", "/bind", {"subject": "projects/Beta"})
check("unprefixed, /bind is no route (%d)" % status, status == 404)

# ---------------------------------------------------------------------------
# the toggle
# ---------------------------------------------------------------------------
status, got = ask("POST", "/s/%s/mode" % SID, {"mode": "do"})
check("the toggle's POST /mode do is taken", status == 200 and got.get("mode") == "do")
check("session.json mode is do", record(SID).get("mode") == "do")
check("and the stream says do",
      until(lambda: any(s.get("mode") == "do" for s in stream.states)))
status, got = ask("POST", "/s/%s/mode" % SID, {"mode": "teach"})
check("and back to teach", status == 200 and record(SID).get("mode") == "teach")

# ---------------------------------------------------------------------------
# End, and read-only after it
# ---------------------------------------------------------------------------
status, got = ask("POST", "/s/%s/end" % SID, {})
check("End ends it (%d)" % status, status == 200 and record(SID).get("ended"))
check("and the stream says ended", until(lambda: any(s.get("ended") for s in stream.states)))
for path, body in (("/say", {"text": "hello"}), ("/mode", {"mode": "do"}),
                   ("/bind", {"subject": "courses/Linear-Algebra"}),
                   ("/slate/save", {"page": 1, "w": 10, "h": 10, "strokes": []}),
                   ("/handover", {"card": "0001"})):
    status, got = ask("POST", "/s/%s%s" % (SID, path), body)
    check("an ended session refuses %s (%d)" % (path, status),
          status == 409 and "read-only" in (got.get("error") or ""))
check("its mode and subject are untouched",
      record(SID).get("mode") == "teach" and record(SID).get("subject") == "projects/Beta")
status, _ = ask("GET", "/s/%s/board.json" % SID)
check("it still reads", status == 200)
status, got = ask("POST", "/s/%s/end" % SID, {})
check("and a second End only retries the commit", status == 200 and got.get("ok"))

httpd.shutdown()
if fails:
    print("\n%d FAILURES" % len(fails))
    sys.exit(1)
print("\nheader: the chip binds, the toggle flips mode, End ends, and an ended "
      "session is read-only")
