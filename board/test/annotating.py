#!/usr/bin/env python3
"""The notes canvas, and annotating a PDF (T40).

    python3 test/annotating.py

A real server (`serve.py --port 0`) on a temp Atlas with one course, and a fake
provider standing in for claude: it records its prompt and, for a notes
canvas's End, does what the prompt asks -- binds the session, starts notes.md
with `board writeup new --md`, writes it, and runs `board build`.

  1. A notes canvas is a session with `view: slate`, opened at its slate. Two
     pages saved there are both read back (a reload). End queues the wrap-up,
     whose prompt names notes.md, `board writeup new --md` and `board build`;
     the transcript lands in docs/<slug>/ and the End commits it.
  2. An uploaded slides.pdf renders in the reader, its ink persists, the
     marked copy holds the ink and sits beside the PDF as slides-marked.pdf,
     the upload wakes nothing, and after `board file` the PDF is in materials/
     and its ink follows. The start screen's way, `POST /file` with a subject
     bound, does the same.
"""

import json
import os
import re
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

box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-annotating-"))
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT"):
    os.environ.pop(k, None)

from tutorboard import sessions  # noqa: E402
from tutorboard.course import burn, paper  # noqa: E402
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


def git(*args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "commit.gpgsign=false"] + list(args), cwd=atlas,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


# ---------------------------------------------------------------------------
# the fake provider
# ---------------------------------------------------------------------------
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys
prompt = sys.argv[-1]
sid = os.path.basename(os.environ.get("TUTORBOARD_SESSION", ""))
rec = {"sid": sid, "prompt": prompt, "cwd": os.getcwd()}
def run(*a):
    p = subprocess.run(["board"] + list(a), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout
if "This notes session is ending now" in prompt:
    rec["bind"] = run("bind", "courses/Demo")
    title = re.search(r'board writeup new --md "([^"]*)"', prompt).group(1)
    rec["new"] = run("writeup", "new", "--md", title)
    src = rec["new"][1].strip().split()[-1]
    with open(src, "a") as fh:
        fh.write("Transcribed: $a^2 + b^2 = c^2$.\n")
    rec["src"] = src
    rec["build"] = run("build", src)
with open(%(calls)r, "a") as fh:
    fh.write(json.dumps(rec) + "\n")
''' % {"calls": CALLS})
os.chmod(FAKE, 0o755)
write(os.path.join(CONFIG_HOME, "tutor-board", "config.json"), json.dumps({
    "provider": "fake", "vision_agent": "fake", "concurrency": 2,
    "headless_timeout": 120, "doing_timeout": 180, "handoff_timeout": 60,
    "agents": {"fake": {"cmd": [FAKE], "label": "Fake",
                        "headless_first": [FAKE, "{prompt}"], "usage": "none"}},
}))


def calls(sid):
    try:
        with open(CALLS) as fh:
            return [r for r in map(json.loads, fh) if r["sid"] == sid]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# a temp Atlas: one course, the root's ignore rules
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "atlas")
write(os.path.join(atlas, "courses", "Demo", "tutorboard.json"),
      json.dumps({"name": "Demo", "phi": False}))
write(os.path.join(atlas, "courses", "Demo", "TUTOR.md"), "# Demo\n")
shutil.copyfile(os.path.join(ROOT, ".gitignore"), os.path.join(atlas, ".gitignore"))
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-qm", "fixture")
demo = os.path.join(atlas, "courses", "Demo")


def png(path, w=120, h=160, rgb=(250, 250, 245)):
    """An 8-bit RGB PNG, plain enough for `burn._png_parts`."""
    row = b"\x00" + bytes(rgb) * w
    raw = zlib.compress(row * h)

    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff))
    write(path, b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(
        ">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b""))
    return path


def a_pdf(path):
    """A one-page PDF, written by the burner itself from a plain picture."""
    pic = png(os.path.join(box, "page.png"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    burn._write_pdf(path, [(pic, 120, 160, b"", 360.0, 480.0)])
    return path


def streams(pdf):
    """Every stream of a PDF, inflated where it inflates."""
    with open(pdf, "rb") as fh:
        raw = fh.read()
    out = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", raw, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except zlib.error:
            out.append(m.group(1))
    return out


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

    def call(self, path, body=None, raw=None, headers=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path), data=data,
            method="POST" if data is not None else "GET",
            headers=headers or {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers

    def js(self, path, body=None, **kw):
        status, raw, _h = self.call(path, body, **kw)
        try:
            return status, json.loads(raw.decode("utf-8"))
        except ValueError:
            return status, {}

    def stop(self):
        try:
            self.p.send_signal(signal.SIGTERM)
            self.p.wait(30)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()


def until(cond, timeout=60.0):
    end = time.time() + timeout
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(0.1)
    return cond()


def upload(server, sid, name, data):
    b = "----annotating"
    body = ("--%s\r\nContent-Disposition: form-data; name=\"f0\"; filename=\"%s\"\r\n"
            "Content-Type: application/pdf\r\n\r\n" % (b, name)).encode() + data
    body += ("\r\n--%s--\r\n" % b).encode()
    return server.js("/s/%s/upload" % sid, raw=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % b})


def stroke(y):
    p = []
    for i in range(12):
        p += [0.2 + 0.05 * i, y]
    return {"c": "#d01010", "w": 3.0, "p": p, "pr": [0.6] * 12, "pg": 1}


def inbox(sid):
    try:
        with open(os.path.join(atlas, "sessions", sid, "inbox", "messages.jsonl")) as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


server = None
try:
    server = Server()
    check("serve.py comes up on an ephemeral port", server.port, "".join(server.lines))

    # -----------------------------------------------------------------------
    # 1. the notes canvas
    # -----------------------------------------------------------------------
    status, got = server.js("/sessions/new", {"view": "slate", "title": "Notes 2026-10-09"})
    sid = got.get("id", "")
    check("POST /sessions/new {view: slate} makes a notes canvas, opened at its slate",
          status == 200 and got.get("url") == "/s/%s/slate" % sid
          and got["session"].get("view") == "slate"
          and got["session"].get("subject") is None, got)
    status, _ = server.js("/sessions/new", {"view": "map"})
    check("a view that is not one is refused", status == 400)
    status, page, _h = server.call("/s/%s/slate" % sid)
    check("its slate page is served", status == 200 and b'id="notes-end"' in page)
    listed = [s for s in server.js("/sessions.json")[1].get("sessions", [])
              if s["id"] == sid]
    check("and the start screen's row opens it there",
          listed and listed[0]["url"] == "/s/%s/slate" % sid, listed)

    pic = open(png(os.path.join(box, "ink.png"), 40, 30, (20, 20, 20)), "rb").read()
    import base64
    data = "data:image/png;base64," + base64.b64encode(pic).decode()
    for n in (1, 2):
        status, got = server.js("/s/%s/slate/save" % sid, {
            "page": n, "w": 800, "h": 600, "png": data,
            "strokes": [{"c": "#fff", "w": 2, "pts": [[10 * n, 10, 0.5], [40, 40, 0.5]]}]})
        check("page %d is saved" % n, status == 200 and got.get("page") == n, got)
    status, state = server.js("/s/%s/slate/state" % sid)
    pages = state.get("pages") or []
    check("both pages are read back, as a reload reads them",
          [p.get("page") for p in pages] == [1, 2]
          and all(p.get("strokes") for p in pages), pages)
    check("and their pictures are what the End transcribes",
          [os.path.basename(p) for p in sessions.slate_pages(sid, atlas)]
          == ["page-01.png", "page-02.png"])

    status, got = server.js("/s/%s/end" % sid, {})
    check("End ends the canvas and queues its wrap-up",
          status == 200 and got.get("session", {}).get("ended") and got.get("wrapup"), got)
    until(lambda: calls(sid), 60)
    one = (calls(sid) or [{}])[0]
    prompt = one.get("prompt", "")
    check("the wrap-up's prompt names notes.md and `board build`",
          "notes.md" in prompt and "board build" in prompt
          and 'board writeup new --md "Notes 2026-10-09"' in prompt, prompt)
    check("and every page picture, in order",
          prompt.find("page-01.png") >= 0
          and prompt.find("page-01.png") < prompt.find("page-02.png"), prompt)
    check("and says the session is bound to nothing yet, so the tutor binds it",
          "no course or project yet" in prompt and "board bind" in prompt)
    check("the turn ran in the Atlas root",
          os.path.realpath(one.get("cwd", "")) == os.path.realpath(atlas))
    src = one.get("src") or ""
    check("`board writeup new --md` starts docs/<slug>/notes.md beside a doc.json",
          (one.get("new") or [1])[0] == 0
          and src == "courses/Demo/docs/notes-2026-10-09/notes.md"
          and os.path.isfile(os.path.join(demo, "docs", "notes-2026-10-09", "doc.json")),
          one)
    doc = json.load(open(os.path.join(demo, "docs", "notes-2026-10-09", "doc.json")))
    check("its doc.json lists the session", doc.get("sessions") == [sid]
          and doc.get("source") == "notes.md", doc)
    until(lambda: "notes-2026-10-09/notes.md" in git("log", "--name-only",
                                                    "--format=").stdout, 30)
    check("and the End commits notes.md once the turn is done",
          "courses/Demo/docs/notes-2026-10-09/notes.md"
          in git("log", "-1", "--name-only", "--format=").stdout,
          git("log", "-2", "--stat").stdout)
    if shutil.which("pandoc"):
        check("the transcript builds (`board build`)", (one.get("build") or [1])[0] == 0,
              one.get("build"))
    s2 = server.js("/sessions/new", {"view": "slate"})[1]["id"]
    server.js("/s/%s/end" % s2, {})
    time.sleep(1.5)
    check("a canvas ended with no ink runs no turn", not calls(s2))

    # -----------------------------------------------------------------------
    # 2. annotating a PDF
    # -----------------------------------------------------------------------
    if not paper.renderer(paper.raster_env()):
        print("-- no pdftoppm and no Ghostscript here; the PDF half is skipped")
        raise SystemExit
    status, got = server.js("/sessions/new", {"title": "Annotate slides.pdf"})
    sa = got["id"]
    with open(a_pdf(os.path.join(box, "in", "slides.pdf")), "rb") as fh:
        original = fh.read()
    status, got = upload(server, sa, "slides.pdf", original)
    check("an uploaded slides.pdf lands in the session's uploads/, with the id the "
          "reader opens it as",
          status == 200 and got.get("files") == [{"name": "slides.pdf",
                                                  "size": len(original),
                                                  "doc": "uploads-slides"}], got)
    lines = inbox(sa)
    check("the upload wakes nothing: one [uploaded] line, wake false",
          len(lines) == 1 and lines[0]["text"].startswith("[uploaded] slides.pdf (")
          and lines[0]["wake"] is False, lines)
    state = server.js("/s/%s/board.json" % sa)[1]
    check("the session drawer lists it as a readable PDF",
          [u.get("doc") for u in state.get("uploads", [])] == ["uploads-slides"])

    status, view = server.js("/s/%s/view/doc/uploads-slides" % sa)
    check("it renders in the reader", status == 200 and view.get("ok")
          and len(view.get("pages") or []) == 1, view)
    key = "doc/uploads-slides/p1"
    status, _ = server.js("/s/%s/annotate/save" % sa, {"card": key,
                                                      "strokes": [stroke(0.5)]})
    check("ink on its page is saved", status == 200)
    view = server.js("/s/%s/view/doc/uploads-slides" % sa)[1]
    check("and comes back with the pages, as a reload asks for them",
          (view.get("ink") or {}).get(key) == [stroke(0.5)], view.get("ink"))

    status, kept = server.js("/s/%s/annotate/burn" % sa, {"kind": "doc/uploads-slides",
                                                         "mode": "new"})
    copy = os.path.join(atlas, "sessions", sa, "uploads", "slides-marked.pdf")
    check("Keep a marked copy writes slides-marked.pdf beside the PDF",
          status == 200 and kept.get("name") == "slides-marked.pdf"
          and os.path.isfile(copy), kept)
    with open(os.path.join(atlas, "sessions", sa, "uploads", "slides.pdf"), "rb") as fh:
        check("never over it", fh.read() == original)
    check("the marked copy holds the ink",
          kept.get("marks") == 1
          and any(b"0.8157 0.0627 0.0627 RG" in s for s in streams(copy)))
    status, raw, headers = server.call("/s/%s%s" % (sa, kept.get("url") or "/x"))
    check("and is handed over as an attachment",
          status == 200 and raw[:5] == b"%PDF-"
          and "attachment" in (headers.get("Content-Disposition") or ""))
    check("git would not carry it", git("check-ignore", "-q", "courses/Demo/x/slides-marked.pdf")
          .returncode == 0)
    check("no turn ran for any of it", not calls(sa))

    sessions.bind(sa, "courses/Demo", base=atlas)
    p = subprocess.run([sys.executable, os.path.join(BOARD, "bin", "board"), "file",
                        "slides.pdf", "--session", sa], cwd=atlas,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, env=dict(os.environ,
                                                         TUTORBOARD_COURSES=atlas))
    check("`board file` puts the PDF in materials/",
          p.returncode == 0
          and os.path.isfile(os.path.join(demo, "materials", "slides.pdf")), p.stdout)
    status, lib = server.js("/library.json?subject=courses/Demo")
    mats = [d for d in lib.get("documents", []) if d.get("group") == "material"]
    check("the library lists it as a material", [d["id"] for d in mats]
          == ["materials-slides"], [d.get("id") for d in lib.get("documents", [])])
    view = server.js("/s/%s/view/doc/materials-slides" % sa)[1]
    check("and its ink follows, under the id the library gives it",
          (view.get("ink") or {}).get("doc/materials-slides/p1") == [stroke(0.5)]
          and key not in (view.get("ink") or {}), view.get("ink"))
    status, mj = server.js("/s/%s/materials.json" % sa)
    check("the drawer's materials row opens it in the reader",
          [m.get("doc") for m in mj.get("materials", [])] == ["materials-slides"], mj)
    lv = server.js("/library/view/materials-slides?subject=courses/Demo")[1]
    check("and the library's reader shows the same ink",
          (lv.get("ink") or {}).get("doc/materials-slides/p1") == [stroke(0.5)])
    status, kept2 = server.js("/annotate/burn?subject=courses/Demo",
                              {"kind": "library/materials-slides", "mode": "new"})
    check("the library keeps a marked copy beside the material, outside a session",
          status == 200 and kept2.get("path") == "materials/slides-marked.pdf"
          and server.call(kept2.get("url", "/x") + "?subject=courses/Demo")[0] == 200,
          kept2)
    lib = server.js("/library.json?subject=courses/Demo")[1]
    check("and a marked copy is not offered as a document of its own",
          "materials-slides-marked" not in [d["id"] for d in lib.get("documents", [])])
    check("still no waking line in the session",
          not [l for l in inbox(sa) if l.get("wake") is not False] and not calls(sa),
          inbox(sa))

    # The start screen's way: bound first, then POST /file.
    sb = server.js("/sessions/new", {"title": "Annotate deck.pdf"})[1]["id"]
    server.js("/s/%s/bind" % sb, {"subject": "courses/Demo"})
    upload(server, sb, "deck.pdf", original)
    server.js("/s/%s/annotate/save" % sb, {"card": "doc/uploads-deck/p1",
                                          "strokes": [stroke(0.3)]})
    status, filed = server.js("/s/%s/file" % sb, {"upload": "deck.pdf"})
    check("POST /file files the upload into materials/ and names its new id",
          status == 200 and filed.get("doc") == "materials-deck"
          and filed.get("to") == "materials/deck.pdf", filed)
    check("and the ink drawn while bound followed it",
          os.path.isfile(writing.ann_path(type("R", (), {"doc_ink": os.path.join(
              demo, ".ink"), "notes": ""}), "doc/materials-deck/p1")))
    status, _ = server.js("/s/%s/file" % sb, {"upload": "deck.pdf"})
    check("a second filing of it is refused", status == 400)
except SystemExit:
    pass
finally:
    if server is not None:
        server.stop()
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails else
      "a notes canvas is transcribed on End, and a PDF is written on, kept and filed")
sys.exit(1 if fails else 0)
