#!/usr/bin/env python3
"""The hub rebuilds the payload only when something changed.

Three things say it did: a route's dirty mark, the 1 s sentinel over the
session files, and the 30 s slow rebuild. An idle board builds nothing between
them. Driven through the real handler and the real poll loop, with `board
write` run as the tutor runs it.
"""

import http.client
import inspect
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import paths
from tutorboard.course import repo as course_repo
from tutorboard.server import handler, hub, spawn, tikz

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


tmp = tempfile.mkdtemp(prefix="tutor-rebuild-")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
ws = os.path.join(tmp, "ws")
os.makedirs(ws)
with open(os.path.join(ws, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "Rebuild Course"}, fh)
repo = course_repo.Repo(ws)

worker = tikz.TikzWorker(repo)
worker.start()
board = hub.Hub(repo, worker)
board.payload = json.dumps(board.build())

builds = []
real_build = board.build


def counted():
    builds.append(time.time())
    return real_build()


board.build = counted

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = board
threading.Thread(target=httpd.serve_forever, daemon=True).start()
threading.Thread(target=board.poll_loop, daemon=True).start()

events = []


def listen():
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    conn.request("GET", "/events")
    resp = conn.getresponse()
    while True:
        line = resp.readline()
        if not line:
            return
        line = line.decode("utf-8")
        if line.startswith("data: "):
            events.append((time.time(), json.loads(line[6:])))


threading.Thread(target=listen, daemon=True).start()


def wait_for(cond, limit):
    end = time.time() + limit
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


try:
    # ---- the first pass, then nothing -------------------------------------
    check("the loop builds once at start and pushes it",
          wait_for(lambda: builds and events and events[-1][1].get("seq") == 1, 3))
    time.sleep(0.5)
    before = len(builds)
    time.sleep(3.5)
    check("an idle board builds nothing between the 30 s passes (%d builds in 3.5 s)"
          % (len(builds) - before), len(builds) == before)

    # ---- a card written by the tutor reaches /events within 1.5 s ---------
    pushed = len(events)
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "board"), "write", "lesson",
         "Sentinel card", "--repo", ws],
        input="The derivative of x squared is 2x.\n",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=60)
    wrote = time.time()
    check("board write writes the card (%s)" % p.stderr.strip()[:200],
          p.returncode == 0)

    def landed():
        for at, data in events[pushed:]:
            if any("Sentinel card" in json.dumps(c) for c in data.get("cards") or []):
                return at
        return None

    wait_for(lambda: landed() is not None, 5)
    at = landed()
    check("the card reaches /events within 1.5 s of the write (%s s)"
          % ("%.2f" % (at - wrote) if at else "never"),
          at is not None and at - wrote <= 1.5)

    # ---- ink autosave is rebuilt but not pushed ---------------------------
    time.sleep(1.5)
    pushed = len(events)
    before = len(builds)
    body = json.dumps({"card": "1", "strokes": [[[0, 0], [10, 10]]]}).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    conn.request("POST", "/annotate/save", body, {"Content-Type": "application/json"})
    status = conn.getresponse().status
    check("an ink autosave is accepted", status == 200)
    wait_for(lambda: len(builds) > before, 2.5)
    time.sleep(1.0)
    check("and the payload is rebuilt with it", len(builds) > before)
    check("but nothing is pushed for ink alone", len(events) == pushed)
    payload = json.loads(board.payload)
    check("while the payload a reload reads carries the ink",
          bool((payload.get("notes") or {}).get("1")))

    # ---- a dirty mark rebuilds at once -----------------------------------
    time.sleep(0.5)
    before = len(builds)
    marked = time.time()
    worker.dirty.set()
    check("a route's dirty mark rebuilds within 0.3 s",
          wait_for(lambda: len(builds) > before, 0.3))

    # ---- the slow pass ----------------------------------------------------
    time.sleep(0.5)
    hub.SLOW_SECONDS = 1.5
    before = len(builds)
    time.sleep(3.6)
    check("the slow pass rebuilds with nothing marked or changed (%d in 3.6 s)"
          % (len(builds) - before), len(builds) - before >= 2)
    hub.SLOW_SECONDS = 30.0
finally:
    httpd.shutdown()

# ---- the sentinel sees a rewrite in place -----------------------------------
first = hub.sentinel(repo.live)
time.sleep(0.01)
note = os.path.join(repo.notes, "0001.json")
with open(note, "w", encoding="utf-8") as fh:
    fh.write('{"card": "1", "strokes": []}')
check("the sentinel sees a file rewritten in place inside a watched directory",
      hub.sentinel(repo.live) != first)
check("and every session file the hub promises to watch is in its list",
      set(paths.SESSION_WATCHED) >= {"cards", "turns.jsonl", "inbox/messages.jsonl",
                                     "state.json", "agent.json", "annotations",
                                     "slate"})

# ---- the shape of it ----------------------------------------------------------
src = open(os.path.join(ROOT, "tutorboard", "server", "hub.py"), encoding="utf-8").read()
check("the hub holds no lock", "Lock(" not in src and "self.lock" not in src)
loop = inspect.getsource(hub.Hub.poll_loop)
check("and its loop walks no missions",
      "missions" not in loop and "spawn" not in loop)
sweep = inspect.getsource(spawn.sweep_missions)
check("the ship walk runs on its own thread, and there is no carry or "
      "release walk any more",
      "ship_missions" in sweep and "carry_missions" not in sweep
      and "release_missions" not in sweep)
app = open(os.path.join(ROOT, "tutorboard", "server", "app.py"), encoding="utf-8").read()
check("and serve.py starts that thread", "target=spawn.sweep_missions" in app)

shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("the hub builds when something changed, and only then")
