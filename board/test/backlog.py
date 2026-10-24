#!/usr/bin/env python3
"""The listener holds a burst of connections: none of them is reset.

Tailscale's proxy opens about 8 connections at once for a page load and over
40 for a service-worker install. Every connection past the listen backlog is
reset by the kernel, the proxy answers it 502, and the server never sees it to
log it; a 502 on home.js is an empty home screen.

  - FORTY SIMULTANEOUS CONNECTS TO A REAL `make_server()`, made while nothing
    accepts, so only the backlog decides: every one connects.
  - THEN EVERY ONE IS SERVED once the server runs: forty answers to
    GET /health, and not one reset.
"""

import os
import socket
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-backlog-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.makedirs(atlas)
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard.server import app                             # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


BURST = 40

httpd = app.make_server(atlas, 0, start=False)
PORT = httpd.server_port
check("the backlog is at least 128, not socketserver's 5",
      httpd.request_queue_size >= 128, httpd.request_queue_size)

# Nothing accepts yet: whatever the backlog cannot hold is reset now.
socks, refused = [], []
barrier = threading.Barrier(BURST)
lock = threading.Lock()


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    barrier.wait()
    try:
        s.connect(("127.0.0.1", PORT))
    except OSError as exc:
        s.close()
        with lock:
            refused.append(repr(exc))
        return
    with lock:
        socks.append(s)


threads = [threading.Thread(target=connect) for _ in range(BURST)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check("%d simultaneous connects, nothing accepting: none is reset" % BURST,
      not refused and len(socks) == BURST, refused[:3])

threading.Thread(target=httpd.serve_forever, daemon=True).start()
answered, broken = 0, []
for s in socks:
    try:
        s.sendall(b"GET /health HTTP/1.1\r\nHost: board\r\nConnection: close\r\n\r\n")
        got = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            got += chunk
        if got.startswith(b"HTTP/1.1 200"):
            answered += 1
        else:
            broken.append(got[:80])
    except OSError as exc:
        broken.append(repr(exc))
    finally:
        s.close()
check("and once it serves, every one of them is answered",
      answered == len(socks) and not broken, broken[:3])
httpd.shutdown()
httpd.server_close()

print("%d FAILURES" % len(fails) if fails
      else "a burst of connections is held, not reset")
sys.exit(1 if fails else 0)
