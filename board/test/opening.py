#!/usr/bin/env python3
"""Any PDF, from anywhere, into a session to write on (item 12).

    python3 test/opening.py

A real server (`serve.py --port 0`) on a temp Atlas holding Random lessons
(`courses/Random`) and one other course, and a local http.server standing in
for the web.

  1. `POST /s/<id>/fetch {url}` lands a PDF from the local server in the
     session's uploads/, answered as /upload answers, with a line that wakes
     nothing. It refuses file://, ftp://, a redirect off http, and a body that
     is not a PDF, leaving nothing behind; a name past 120 characters still
     ends .pdf, a server dripping bytes is refused at the deadline, and an
     ended session refuses it.
  2. `board open <file.pdf>` copies, never moves, the PDF into a new
     "Annotate <name>" session and prints the URL its board opens it at; with
     `--subject` the session is bound and the copy filed into materials/; a
     PDF with no extension is copied under a .pdf name.
  3. A send to Random lessons files a session's uploads into
     `courses/Random/materials/`.
"""

import http.server
import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
sys.path.insert(0, BOARD)

box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-opening-"))
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT"):
    os.environ.pop(k, None)

from tutorboard import sessions  # noqa: E402
from tutorboard.course import burn  # noqa: E402
from tutorboard.server.routes import writing  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:800]) if detail else ""))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(data, bytes) else "w") as fh:
        fh.write(data)


atlas = os.path.join(box, "atlas")


def git(*args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "commit.gpgsign=false"] + list(args), cwd=atlas,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


for slug, name in (("Random", "Random lessons"), ("Demo", "Demo")):
    write(os.path.join(atlas, "courses", slug, "tutorboard.json"),
          json.dumps({"name": name}))
    write(os.path.join(atlas, "courses", slug, "TUTOR.md"), "# %s\n" % name)
shutil.copyfile(os.path.join(ROOT, ".gitignore"), os.path.join(atlas, ".gitignore"))
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-qm", "fixture")
random_dir = os.path.join(atlas, "courses", "Random")


def a_pdf(path):
    """A one-page PDF, written by the burner from a plain picture."""
    w, h = 40, 50
    row = b"\x00" + bytes((250, 250, 245)) * w

    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff))
    pic = os.path.join(box, "page.png")
    write(pic, b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(
        ">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(row * h))
        + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    burn._write_pdf(path, [(pic, w, h, b"", 300.0, 375.0)])
    return path


# ---------------------------------------------------------------------------
# the web, standing in: a PDF, a text file, and redirects off http
# ---------------------------------------------------------------------------
web = os.path.join(box, "web")
paper = a_pdf(os.path.join(web, "papers", "slides.pdf"))
with open(paper, "rb") as fh:
    PAPER = fh.read()
write(os.path.join(web, "notes.txt"), "not a pdf at all\n")


class Web(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        http.server.SimpleHTTPRequestHandler.__init__(self, *a, directory=web, **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        hops = {"/to-file.pdf": "file:///etc/hosts",
                "/to-ftp.pdf": "ftp://127.0.0.1/slides.pdf",
                "/to-paper": "/papers/slides.pdf"}
        if self.path == "/long":
            # A Content-Disposition name longer than an upload's 120.
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition",
                             'attachment; filename="%s.pdf"' % ("a" * 130))
            self.send_header("Content-Length", str(len(PAPER)))
            self.end_headers()
            self.wfile.write(PAPER)
            return
        if self.path == "/drip.pdf":
            # A byte at a time, each well inside one read's timeout.
            self.send_response(200)
            self.send_header("Content-Length", "64")
            self.end_headers()
            self.wfile.write(b"%PDF-")
            self.wfile.flush()
            try:
                for _ in range(59):
                    time.sleep(0.1)
                    self.wfile.write(b" ")
                    self.wfile.flush()
            except OSError:
                pass
            return
        if self.path in hops:
            self.send_response(302)
            self.send_header("Location", hops[self.path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


site = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Web)
threading.Thread(target=site.serve_forever, daemon=True).start()
SITE = "http://127.0.0.1:%d" % site.server_address[1]


class Server(object):
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, os.path.join(BOARD, "serve.py"), "--port", "0",
             "--atlas", atlas], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            universal_newlines=True, start_new_session=True)
        self.port = None
        self.lines = []
        for line in self.p.stderr:
            self.lines.append(line)
            if "listening on http://" in line:
                self.port = int(line.split("http://", 1)[1].split("/")[0].split(":")[1])
                break
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self):
        for line in self.p.stderr:
            self.lines.append(line)

    def js(self, path, body=None, raw=None, headers=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path), data=data,
            method="POST" if data is not None else "GET",
            headers=headers or {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                status, got = r.status, r.read()
        except urllib.error.HTTPError as exc:
            status, got = exc.code, exc.read()
        try:
            return status, json.loads(got.decode("utf-8"))
        except ValueError:
            return status, {}

    def stop(self):
        try:
            self.p.send_signal(signal.SIGTERM)
            self.p.wait(30)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()


def inbox(sid):
    try:
        with open(os.path.join(atlas, "sessions", sid, "inbox", "messages.jsonl")) as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def uploads(sid):
    try:
        return sorted(os.listdir(os.path.join(atlas, "sessions", sid, "uploads")))
    except OSError:
        return []


def board(*args):
    return subprocess.run([sys.executable, os.path.join(BOARD, "bin", "board")] + list(args),
                          cwd=box, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True,
                          env=dict(os.environ, TUTORBOARD_COURSES=atlas))


server = None
try:
    server = Server()
    check("serve.py comes up on an ephemeral port", server.port, "".join(server.lines))

    # -----------------------------------------------------------------------
    # 1. a PDF from a URL
    # -----------------------------------------------------------------------
    sid = server.js("/sessions/new", {"title": "Annotate slides.pdf"})[1]["id"]
    status, got = server.js("/s/%s/fetch" % sid, {"url": SITE + "/papers/slides.pdf"})
    check("/fetch lands a PDF from a local http.server in the session's uploads/, "
          "answered as /upload answers",
          status == 200 and got.get("ok") and got.get("saved") == ["slides.pdf"]
          and got.get("files") == [{"name": "slides.pdf", "size": len(PAPER),
                                    "doc": "uploads-slides"}], got)
    with open(os.path.join(atlas, "sessions", sid, "uploads", "slides.pdf"), "rb") as fh:
        check("byte for byte", fh.read() == PAPER)
    lines = inbox(sid)
    check("with an [uploaded] line that wakes nothing",
          len(lines) == 1 and lines[0]["text"].startswith("[uploaded] slides.pdf (")
          and lines[0]["wake"] is False, lines)
    status, got = server.js("/s/%s/fetch" % sid, {"url": SITE + "/to-paper"})
    check("a redirect from http to http is followed, and a name taken takes -2",
          status == 200 and got.get("saved") == ["slides-2.pdf"], got)

    before = uploads(sid)
    for label, url in (("file://", "file:///etc/hosts"),
                       ("ftp://", "ftp://127.0.0.1/slides.pdf"),
                       ("a redirect to file://", SITE + "/to-file.pdf"),
                       ("a redirect to ftp://", SITE + "/to-ftp.pdf"),
                       ("a non-PDF", SITE + "/notes.txt"),
                       ("no address", "")):
        status, got = server.js("/s/%s/fetch" % sid, {"url": url})
        check("/fetch refuses %s with 400 and its reason" % label,
              status == 400 and got.get("ok") is False and got.get("error"), (status, got))
    check("and leaves nothing behind in uploads/ or beside it",
          uploads(sid) == before
          and not [n for n in os.listdir(os.path.join(atlas, "sessions", sid))
                   if n.startswith(".fetch-")])
    check("and no refusal wrote a line", len(inbox(sid)) == 2)
    status, got = server.js("/s/%s/fetch" % sid, {"url": SITE + "/missing.pdf"})
    check("a 404 there is said as the server's answer", status == 502
          and "404" in (got.get("error") or ""), got)

    status, got = server.js("/s/%s/fetch" % sid, {"url": SITE + "/long"})
    named = (got.get("saved") or [""])[0]
    check("a name past 120 characters still ends .pdf, and opens as a document",
          status == 200 and named.endswith(".pdf") and len(named) <= 120
          and (got.get("files") or [{}])[0].get("doc"), got)
    check("pdf_name: an extension added, a long name cut before it",
          writing.pdf_name("paper") == "paper.pdf"
          and writing.pdf_name("Slides.PDF") == "Slides.PDF"
          and writing.pdf_name("") == "fetched.pdf"
          and len(writing.pdf_name("b" * 200 + ".pdf")) == 120)

    began = time.monotonic()
    try:
        writing.fetch_pdf(SITE + "/drip.pdf", os.path.join(box, "dripped"),
                          timeout=5, deadline=1)
        refused = None
    except writing._Refused as exc:
        refused = exc
    check("a server dripping bytes is refused (504) once the download passes "
          "its deadline, though no one read times out",
          refused is not None and refused.status == 504
          and time.monotonic() - began < 4
          and not os.listdir(os.path.join(box, "dripped")), refused)

    server.js("/s/%s/end" % sid, {})
    status, got = server.js("/s/%s/fetch" % sid, {"url": SITE + "/papers/slides.pdf"})
    check("an ended session refuses /fetch (409)", status == 409, (status, got))

    # -----------------------------------------------------------------------
    # 2. board open: a PDF on this Mac
    # -----------------------------------------------------------------------
    mine = a_pdf(os.path.join(box, "desk", "Reading 3.pdf"))
    with open(mine, "rb") as fh:
        MINE = fh.read()
    p = board("open", mine)
    made = [r for r in sessions.all(atlas) if r.get("title") == "Annotate Reading 3.pdf"]
    one = made[0]["id"] if made else ""
    check("`board open <file.pdf>` makes a new \"Annotate <name>\" session, unbound",
          p.returncode == 0 and len(made) == 1 and made[0].get("subject") is None, p.stdout)
    check("copying the PDF into its uploads/, never moving it",
          uploads(one) == ["Reading-3.pdf"] and os.path.isfile(mine)
          and open(os.path.join(atlas, "sessions", one, "uploads", "Reading-3.pdf"),
                   "rb").read() == MINE)
    check("with an [uploaded] line that wakes nothing",
          [l.get("wake") for l in inbox(one)] == [False], inbox(one))
    check("and prints the URL its board opens the PDF at",
          ("/s/%s/board#/s/%s/doc/uploads-reading-3" % (one, one)) in p.stdout, p.stdout)
    status, view = server.js("/s/%s/view/doc/uploads-reading-3" % one)
    check("which the server reads as that session's document", status == 200
          and view.get("ok"), view)

    p = board("open", mine, "--subject", "courses/Random")
    made = [r for r in sessions.all(atlas) if r.get("title") == "Annotate Reading 3.pdf"
            and r.get("id") != one]
    two = made[0]["id"] if made else ""
    check("with --subject the session is bound to it",
          p.returncode == 0 and len(made) == 1 and made[0].get("subject") == "courses/Random",
          p.stdout)
    check("and the copy filed into its materials/, the original still in place",
          os.path.isfile(os.path.join(random_dir, "materials", "Reading-3.pdf"))
          and not uploads(two) and os.path.isfile(mine), p.stdout)
    check("the URL opens the material",
          ("/s/%s/board#/s/%s/doc/materials-reading-3" % (two, two)) in p.stdout, p.stdout)
    check("`board open` refuses a file that is not a PDF",
          board("open", os.path.join(web, "notes.txt")).returncode == 1)
    check("and a subject that does not exist, making no session",
          board("open", mine, "--subject", "courses/Nowhere").returncode == 1
          and len(sessions.all(atlas)) == 3)
    bare = os.path.join(box, "desk", "paper")
    shutil.copyfile(mine, bare)
    p = board("open", bare)
    made = [r for r in sessions.all(atlas) if r.get("title") == "Annotate paper"]
    three = made[0]["id"] if made else ""
    check("a PDF with no extension is copied in under a .pdf name its board opens",
          p.returncode == 0 and uploads(three) == ["paper.pdf"] and os.path.isfile(bare)
          and ("/s/%s/board#/s/%s/doc/uploads-paper" % (three, three)) in p.stdout,
          p.stdout)

    # -----------------------------------------------------------------------
    # 3. a send to Random lessons
    # -----------------------------------------------------------------------
    s3 = server.js("/sessions/new", {"title": "a free lecture"})[1]["id"]
    server.js("/s/%s/fetch" % s3, {"url": SITE + "/papers/slides.pdf"})
    status, got = server.js("/s/%s/send" % s3, {"subject": "courses/Random"})
    check("a send to Random lessons files the session's uploads into "
          "courses/Random/materials/",
          status == 200 and got.get("sent", {}).get("name") == "Random lessons"
          and os.path.isfile(os.path.join(random_dir, "materials", "slides.pdf"))
          and not uploads(s3), got)
finally:
    if server is not None:
        server.stop()
    site.shutdown()
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails else
      "a PDF from a URL or this Mac opens in a session, and a send files it in Random lessons")
sys.exit(1 if fails else 0)
