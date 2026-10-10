#!/usr/bin/env python3
"""A page's error report reaches the server's log: POST /client-error.

A request the proxy dropped never reached the server, so no request line
shows it; the page that missed a script says so itself.

  - ONE LINE, `client: <page> <what> <src> <msg>`, through the handler's
    `note`, unprefixed and under `/s/<id>/` alike; the reply is {ok: true}.
  - EACH FIELD ON ONE LINE AND CUT to 300 characters, the stack and the
    user agent after the four.
  - A BODY OVER 8 KB IS 413 and unread; one that is not a JSON object is 400.
  - RATE-LIMITED per process: past 20 a minute a report is counted, not
    written, and the next minute's first line says how many went unlogged.

One server on an ephemeral port over a temp Atlas tree.
"""

import http.client
import json
import os
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-client-errors-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.makedirs(atlas)
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard import sessions                               # noqa: E402
from tutorboard.server import app                             # noqa: E402
from tutorboard.server.handler import Handler                 # noqa: E402
from tutorboard.server.routes import machines                 # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


NOTES = []
Handler.note = lambda self, line: NOTES.append(line)

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def ask(path, body, raw=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    data = raw if raw is not None else json.dumps(body).encode("utf-8")
    conn.request("POST", path, body=data, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    got = r.read()
    conn.close()
    try:
        return r.status, json.loads(got.decode("utf-8"))
    except ValueError:
        return r.status, {}


def reports():
    return [n for n in NOTES if n.startswith("client:")]


REPORT = {"page": "home", "what": "resource", "src": "/static/home.js",
          "msg": "502 from the proxy"}

status, got = ask("/client-error", REPORT)
check("unprefixed, a report answers {ok: true}", status == 200 and got == {"ok": True})
check("and is one line: client: <page> <what> <src> <msg>",
      reports() == ["client: home resource /static/home.js 502 from the proxy"],
      reports())
check("and no request line beside it, which would double every report",
      not [n for n in NOTES if not n.startswith("client:")], NOTES)

rec = sessions.new("a lesson", base=atlas)
del NOTES[:]
status, got = ask("/s/%s/client-error" % rec["id"],
                  dict(REPORT, page="board", stack="TypeError at\n  board.js:12",
                       ua="iPad"))
check("under /s/<id>/ too", status == 200 and got.get("ok"))
check("with the stack on the same line, and the user agent after it",
      reports() == ["client: board resource /static/home.js 502 from the proxy"
                    " | stack TypeError at board.js:12 | ua iPad"], reports())

del NOTES[:]
ask("/client-error", {"page": "home", "what": "error", "src": "x" * 2000, "msg": ""})
line = (reports() or [""])[0]
check("a long field is cut to 300 characters, and an empty one is -",
      line == "client: home error %s -" % ("x" * machines.CLIENT_FIELD), line[:120])

del NOTES[:]
status, _ = ask("/client-error", None, raw=b"{" + b" " * (machines.CLIENT_BODY + 10) + b"}")
check("a body over 8 KB is 413 and logs nothing", status == 413 and not reports())
status, _ = ask("/client-error", [1, 2])
check("a body that is not a JSON object is 400", status == 400 and not reports())
status, _ = ask("/client-error", None, raw=b"not json")
check("and so is one that is not JSON", status == 400)

# The rate: a fresh window, then more than CLIENT_PER_MINUTE in it.
machines._client.update(window=0.0, count=0, dropped=0)
del NOTES[:]
for n in range(machines.CLIENT_PER_MINUTE + 5):
    ask("/client-error", dict(REPORT, msg="burst %d" % n))
check("past %d a minute a report is not written" % machines.CLIENT_PER_MINUTE,
      len(reports()) == machines.CLIENT_PER_MINUTE, len(reports()))
status, got = ask("/client-error", dict(REPORT, msg="still answered"))
check("and is still answered ok", status == 200 and got.get("ok"))
machines._client["window"] -= 61
del NOTES[:]
ask("/client-error", dict(REPORT, msg="next minute"))
check("the next minute's first line says how many went unlogged, then the report",
      reports() == ["client: 6 more reports in the minute before this one went unlogged",
                    "client: home resource /static/home.js next minute"], reports())

httpd.shutdown()
print("%d FAILURES" % len(fails) if fails
      else "a page's error report reaches the log, cut and rate-limited")
sys.exit(1 if fails else 0)
