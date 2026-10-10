#!/usr/bin/env python3
"""Uploads (D21) against a real server in its own process: a 150 MB body
streams to the session's `uploads/` without the server's memory growing by
the file, each file appends a non-waking `[uploaded] <name> (<size>)` line,
and a body that is too big, cut short or sent to an ended session leaves
nothing behind. The page's side -- progress and an error line -- is
`test/uploads.js`'s.
"""

import hashlib
import http.client
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-uploads-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard import sessions                               # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.lesson import inbox                           # noqa: E402
from tutorboard.server import multipart                       # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


os.makedirs(os.path.join(atlas, "courses", "Alpha"))
with open(os.path.join(atlas, ".gitignore"), "w") as fh:
    fh.write("/sessions/\n")
subprocess.run(["git", "init", "-q", atlas], check=True)

sid = sessions.new("uploads", base=atlas)["id"]
ended = sessions.new("ended", base=atlas)["id"]
sessions.end(ended, base=atlas)
where = sessions.path(sid, atlas)
repo = course_repo.Repo(course_repo.stored_root(where), session=where, create=False)

# The server in a process of its own, so its memory is its own.
CHILD = """
import sys
sys.path.insert(0, %r)
from tutorboard.server import app
httpd = app.make_server(%r, 0)
print(httpd.server_port, flush=True)
httpd.serve_forever()
""" % (ROOT, atlas)
child = subprocess.Popen([sys.executable, "-c", CHILD], stdout=subprocess.PIPE,
                         stderr=open(os.path.join(tmp, "server.log"), "w"))
PORT = int(child.stdout.readline())


def rss():
    """The server's resident memory, in KB."""
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)],
                         stdout=subprocess.PIPE, universal_newlines=True).stdout
    return int(out.strip() or 0)


BOUNDARY = "----tutorupload7f3a"


def head(name, field="f0"):
    return ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
            "Content-Type: application/pdf\r\n\r\n" % (BOUNDARY, field, name)).encode()


TAIL = ("\r\n--%s--\r\n" % BOUNDARY).encode()


def send(path, pieces, length=None, close_early=False):
    """POST a body given as pieces (bytes, or callables yielding bytes), a
    chunk at a time; `(status, reply)`, or `(0, {})` when it was cut off."""
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=300)
    conn.putrequest("POST", path)
    conn.putheader("Content-Type", "multipart/form-data; boundary=" + BOUNDARY)
    total = length
    if total is None:
        total = sum(len(p) if isinstance(p, bytes) else p.size for p in pieces)
    conn.putheader("Content-Length", str(total))
    conn.endheaders()
    try:
        for p in pieces:
            for chunk in ([p] if isinstance(p, bytes) else p()):
                conn.send(chunk)
        if close_early:
            conn.close()
            return 0, {}
        r = conn.getresponse()
        raw = r.read()
    except (BrokenPipeError, ConnectionResetError):
        conn.close()
        return 0, {}
    conn.close()
    try:
        return r.status, json.loads(raw.decode("utf-8"))
    except ValueError:
        return r.status, {}


class Big(object):
    """`size` bytes of a repeating, position-dependent pattern, made a chunk
    at a time and hashed as it goes, so the test holds no copy either."""

    def __init__(self, size):
        self.size = size
        self.sha = hashlib.sha1()

    def __call__(self):
        block = 1 << 20
        sent = 0
        n = 0
        while sent < self.size:
            piece = (b"%08d" % n) * (block // 8)
            piece = piece[:min(block, self.size - sent)]
            self.sha.update(piece)
            sent += len(piece)
            n += 1
            yield piece


def lines():
    try:
        with open(repo.messages_path, "r", encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def leftovers():
    return [n for n in os.listdir(repo.uploads) if n.startswith(".")]


URL = "/s/%s/upload" % sid
time.sleep(0.3)
before = rss()

big = Big(150 * 1024 * 1024)
status, got = send(URL, [head("Lecture Notes.pdf"), big, TAIL])
after = rss()
check("a 150 MB upload is taken (%d)" % status, status == 200 and got.get("ok"))
name = (got.get("saved") or [""])[0]
path = os.path.join(repo.uploads, name)
check("into the session's uploads/, under its own name made safe",
      name == "Lecture-Notes.pdf" and os.path.isfile(path))
sha = hashlib.sha1()
with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        sha.update(chunk)
check("byte for byte", os.path.getsize(path) == big.size
      and sha.hexdigest() == big.sha.hexdigest())
grew = (after - before) / 1024.0
check("the server's RSS did not grow by the file size (grew %.1f MB of 150)" % grew,
      grew < 40)
got_lines = lines()
check("one [uploaded] <name> (<size>) line",
      len(got_lines) == 1 and got_lines[0]["text"] == "[uploaded] Lecture-Notes.pdf (150 MB)"
      and got_lines[0].get("files") == ["Lecture-Notes.pdf"])
check("and it wakes nothing", got_lines and got_lines[0].get("wake") is False
      and not inbox.waiting(repo))
check("no per-upload question: the reply is the saved file, its size, and "
      "for a PDF the id the reader opens it as",
      got.get("files") == [{"name": "Lecture-Notes.pdf", "size": big.size,
                            "doc": "uploads-lecture-notes"}])
os.remove(path)

# Two files and a plain field in one form, one name taken already.
with open(os.path.join(repo.uploads, "page.png"), "wb") as fh:
    fh.write(b"old")
field = ("--%s\r\nContent-Disposition: form-data; name=\"note\"\r\n\r\nhello"
         % BOUNDARY).encode()
status, got = send(URL, [field, b"\r\n", head("page.png", "f0"), b"\x89PNG one",
                         b"\r\n", head("../../etc/x.txt", "f1"), b"two\r\n--not",
                         TAIL])
check("several files in one form, a plain field skipped",
      status == 200 and got.get("saved") == ["page-2.png", "x.txt"])
with open(os.path.join(repo.uploads, "x.txt"), "rb") as fh:
    check("a part's data may hold what looks like a boundary's start",
          fh.read() == b"two\r\n--not")
check("a taken name gets -2, and a path in a name is dropped",
      os.path.isfile(os.path.join(repo.uploads, "page-2.png"))
      and not os.path.exists(os.path.join(atlas, "etc")))
check("a line per file, none waking", len(lines()) == 3
      and not inbox.waiting(repo))

n = len(lines())
status, got = send(URL, [head("cut.pdf"), b"x" * 5000], length=1 << 20,
                   close_early=True)
time.sleep(0.5)
check("a body cut off leaves no file and no line",
      not leftovers() and not os.path.exists(os.path.join(repo.uploads, "cut.pdf"))
      and len(lines()) == n)
status, got = send(URL, [head("huge.pdf")], length=multipart.MAX_UPLOAD + 1)
check("over 1 GB is 413 before a byte is read", status == 413
      and "1 GB" in got.get("error", "") and len(lines()) == n)
status, got = send("/s/%s/upload" % ended, [head("late.pdf"), b"x", TAIL])
check("an ended session refuses an upload with 409", status == 409)
status, got = send(URL, [b"not a form at all"])
check("a body that is not a form is 400, leaving nothing",
      status == 400 and not leftovers() and len(lines()) == n)

conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
conn.request("GET", "/s/%s/uploads/page-2.png" % sid)
r = conn.getresponse()
check("an upload reads back", r.status == 200 and r.read() == b"\x89PNG one")
conn.close()

# Past 8 MB a file goes back a chunk at a time, not read whole.
mid = Big(9 * 1024 * 1024)
status, got = send(URL, [head("scan.tif"), mid, TAIL])
conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
conn.request("GET", "/s/%s/uploads/scan.tif" % sid)
r = conn.getresponse()
back = hashlib.sha1()
for chunk in iter(lambda: r.read(1 << 20), b""):
    back.update(chunk)
check("a 9 MB upload reads back whole, streamed",
      status == 200 and r.status == 200
      and r.getheader("Content-Length") == str(mid.size)
      and back.hexdigest() == mid.sha.hexdigest())
conn.close()

child.terminate()
child.wait()
if fails:
    print("\n%d failed" % len(fails))
    sys.exit(1)
print("\nall passed")
