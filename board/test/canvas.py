#!/usr/bin/env python3
"""A blank canvas: written on with no tutor, filed, handed over, ended (item 12).

    python3 test/canvas.py

A real server (`serve.py --port 0`) on a temp Atlas holding Random lessons
(`courses/Random`), and a fake provider standing in for claude: a turn handed
a `[canvas]` line writes one card that reads every page, and a wrap-up writes
TUTOR.md with `board memo`.

  1. `/sessions/new {view: slate}` and unsent `/slate/save`s write no waking
     line and queue no turn.
  2. "Save to…" (`/bind`) files the inked pages into
     `docs/<slug>/handwritten/page-NN.png` beside a notes.md with one image
     link per page and a doc.json naming the session, commits nothing, ends
     nothing and wakes nothing.
  3. `/canvas.pdf` starts `%PDF-` and has one page per inked page.
  4. `/give` writes one `[canvas]` line listing pages 1..N and queues one
     turn; an empty canvas is 400, a session that is no canvas is 400.
  5. End `{transcribe: false}` on a taught canvas commits the filed pages and
     runs the wrap-up, which writes TUTOR.md (`_wrap`); on an untaught one it
     queues nothing and commits `docs/<slug>/notes.md` with
     `handwritten/page-*.png`; a page erased after filing loses its picture
     and its section of notes.md, and a stored `canvas.dir` not this
     session's is not written into; with no subject and no transcription it
     commits nothing. `/give` on an ended canvas reopens it and wakes one turn; that
     canvas ended from its board (no `transcribe`) gets its wrap-up and no
     transcription.
  6. The brief of a canvas names its pages and `board slate --all`.
"""

import base64
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

box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-canvas-"))
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT"):
    os.environ.pop(k, None)

from tutorboard import brief, sense, sessions  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:900]) if detail else ""))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(data, bytes) else "w") as fh:
        fh.write(data)


# ---------------------------------------------------------------------------
# the fake provider
# ---------------------------------------------------------------------------
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys
prompt = sys.argv[-1]
sid = os.path.basename(os.environ.get("TUTORBOARD_SESSION", ""))
rec = {"sid": sid, "prompt": prompt}
def run(args, stdin=""):
    p = subprocess.run(["board"] + args, input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout
if "This session is ending now" in prompt:
    rec["kind"] = "wrapup"
    rec["memo"] = run(["memo", "Done recently"], "- read a canvas of handwriting\n")
elif "This notes session is ending now" in prompt:
    rec["kind"] = "notes"
else:
    rec["kind"] = "turn"
    rec["pages"] = re.findall(r"page (\d+): (\S+)", prompt)
    rec["card"] = run(["write", "lesson", "canvas"], "I read all of your canvas.\n")
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


def calls(sid, kind=None):
    try:
        with open(CALLS) as fh:
            got = [r for r in map(json.loads, fh) if r["sid"] == sid]
    except OSError:
        return []
    return [r for r in got if kind is None or r.get("kind") == kind]


# ---------------------------------------------------------------------------
# a temp Atlas: Random lessons, and the root's ignore rules
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "atlas")


def git(*args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "commit.gpgsign=false"] + list(args), cwd=atlas,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


write(os.path.join(atlas, "courses", "Random", "tutorboard.json"),
      json.dumps({"name": "Random lessons"}))
write(os.path.join(atlas, "courses", "Random", "TUTOR.md"),
      "# Random lessons\n\n## Where things are\n\n## Now\n\n## Open decisions\n\n"
      "## Done recently\n")
shutil.copyfile(os.path.join(ROOT, ".gitignore"), os.path.join(atlas, ".gitignore"))
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-qm", "fixture")
random_dir = os.path.join(atlas, "courses", "Random")


def png_data():
    """An 8-bit RGB PNG as a data URL, as a slate save carries one."""
    w, h = 30, 20
    row = b"\x00" + bytes((255, 255, 255)) * w

    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff))
    raw = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(raw).decode()


PNG = png_data()


def stroke(n):
    return {"c": "#e0b45c", "w": 2.4, "hl": False,
            "pts": [[10 * n, 10, 0.5], [40 + n, 60, 0.6], [90, 20 + n, 0.5]]}


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

    def call(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path), data=data,
            method="POST" if data is not None else "GET",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers

    def js(self, path, body=None):
        status, raw, _h = self.call(path, body)
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


def inbox(sid):
    try:
        with open(os.path.join(atlas, "sessions", sid, "inbox", "messages.jsonl")) as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def waking(sid):
    return [l for l in inbox(sid) if l.get("wake") is not False]


def head():
    return git("rev-parse", "HEAD").stdout.strip()


def committed_since(sha):
    return git("diff", "--name-only", sha, "HEAD").stdout.split()


def write_pages(server, sid, n):
    for page in range(1, n + 1):
        status, got = server.js("/s/%s/slate/save" % sid, {
            "page": page, "w": 800, "h": 600, "png": PNG, "strokes": [stroke(page)]})
        check("canvas page %d is saved, not sent" % page,
              status == 200 and "turn" not in got, got)


def queued(server):
    return (server.js("/health")[1].get("turns") or {})


server = None
try:
    server = Server()
    check("serve.py comes up on an ephemeral port", server.port, "".join(server.lines))

    # -----------------------------------------------------------------------
    # 1. writing never wakes a tutor
    # -----------------------------------------------------------------------
    status, got = server.js("/sessions/new", {"view": "slate", "title": "Canvas 2026-10-24"})
    sid = got.get("id", "")
    check("/sessions/new {view: slate} makes a canvas, opened at its slate",
          status == 200 and got.get("url") == "/s/%s/slate" % sid)
    write_pages(server, sid, 3)
    time.sleep(1.0)
    turns = queued(server)
    check("unsent /slate/saves write no waking line and queue no turn",
          not waking(sid) and sid not in (turns.get("running") or [])
          and sid not in (turns.get("queued") or {}) and not calls(sid),
          (inbox(sid), turns))

    # -----------------------------------------------------------------------
    # 2. Save to…: bound, filed, nothing committed, nothing woken
    # -----------------------------------------------------------------------
    before = head()
    status, got = server.js("/s/%s/bind" % sid, {"subject": "courses/Random"})
    rec = sessions.get(sid, atlas)
    slug = ((rec or {}).get("canvas") or {}).get("dir", "")
    d = os.path.join(random_dir, *slug.split("/")) if slug else ""
    check("\"Save to\" binds it (POST /bind) and records where its pages are filed",
          status == 200 and rec.get("subject") == "courses/Random"
          and slug == "docs/canvas-2026-10-24", (got, rec))
    check("its inked pages are filed as docs/<slug>/handwritten/page-NN.png",
          d and sorted(os.listdir(os.path.join(d, "handwritten")))
          == ["page-01.png", "page-02.png", "page-03.png"])
    notes = open(os.path.join(d, "notes.md")).read() if d else ""
    check("beside a notes.md with one image link per page, in order",
          [m for m in re.findall(r"!\[page (\d+)\]\(handwritten/page-(\d+)\.png\)", notes)]
          == [("1", "01"), ("2", "02"), ("3", "03")], notes)
    doc = json.load(open(os.path.join(d, "doc.json"))) if d else {}
    check("and a doc.json naming the session", doc.get("sessions") == [sid]
          and doc.get("source") == "notes.md", doc)
    check("it commits nothing, ends nothing and wakes nothing",
          head() == before and not rec.get("ended") and not waking(sid) and not calls(sid))
    write_pages(server, sid, 4)
    server.js("/s/%s/bind" % sid, {"subject": "courses/Random"})
    check("a page written after is filed at the next filing, into the same directory",
          os.path.isfile(os.path.join(d, "handwritten", "page-04.png"))
          and "handwritten/page-04.png" in open(os.path.join(d, "notes.md")).read()
          and len(os.listdir(os.path.join(random_dir, "docs"))) == 1)

    # -----------------------------------------------------------------------
    # 3. the PDF
    # -----------------------------------------------------------------------
    status, raw, headers = server.call("/s/%s/canvas.pdf" % sid)
    check("/canvas.pdf starts %PDF- and has one page per inked page (4)",
          status == 200 and raw[:5] == b"%PDF-"
          and len(re.findall(rb"/Type /Page[^s]", raw)) == 4
          and "attachment" in (headers.get("Content-Disposition") or ""),
          (status, raw[:60]))
    check("drawn as vector ink: no image in it",
          b"/Subtype /Image" not in raw and b"/XObject" not in raw)
    empty = server.js("/sessions/new", {"view": "slate"})[1]["id"]
    check("a canvas with no ink has no PDF (404)",
          server.call("/s/%s/canvas.pdf" % empty)[0] == 404)

    # -----------------------------------------------------------------------
    # 4. Give to the tutor
    # -----------------------------------------------------------------------
    status, got = server.js("/s/%s/give" % empty, {})
    check("/give on an empty canvas answers 400, waking nothing",
          status == 400 and not waking(empty), got)
    board_sid = server.js("/sessions/new", {"title": "a lesson"})[1]["id"]
    check("/give on a session that is no canvas answers 400",
          server.js("/s/%s/give" % board_sid, {})[0] == 400)
    status, got = server.js("/s/%s/give" % sid, {})
    lines = waking(sid)
    check("/give writes one waking [canvas] line",
          status == 200 and got.get("pages") == 4 and got.get("url") == "/s/%s/board" % sid
          and len(lines) == 1 and lines[0]["text"].startswith("[canvas]"), (got, lines))
    listed = re.findall(r"page (\d+): (\S+)", lines[0]["text"]) if lines else []
    check("listing pages 1..N in order, each its picture",
          [n for n, _p in listed] == ["1", "2", "3", "4"]
          and [os.path.basename(p) for _n, p in listed]
          == ["page-01.png", "page-02.png", "page-03.png", "page-04.png"], listed)
    until(lambda: calls(sid, "turn"), 60)
    turn = calls(sid, "turn")
    check("and queues one turn, which reads every page",
          len(turn) == 1 and [n for n, _p in turn[0]["pages"]][:4] == ["1", "2", "3", "4"],
          turn)
    check("the canvas opens at its board once given",
          [r["url"] for r in server.js("/sessions.json")[1]["sessions"]
           if r["id"] == sid] == ["/s/%s/board" % sid])
    until(lambda: os.listdir(os.path.join(atlas, "sessions", sid, "cards")), 30)

    # -----------------------------------------------------------------------
    # 5. End, three ways
    # -----------------------------------------------------------------------
    until(lambda: not server.js("/health")[1].get("turns", {}).get("running"), 60)
    before = head()
    status, got = server.js("/s/%s/end" % sid, {"transcribe": False})
    check("End on a taught canvas, keeping the pages, queues its wrap-up",
          status == 200 and got.get("wrapup") is True, got)
    until(lambda: calls(sid, "wrapup"), 60)
    until(lambda: "courses/Random/TUTOR.md" in committed_since(before), 60)
    check("_wrap on a canvas with cards writes TUTOR.md, and it is committed",
          "read a canvas of handwriting" in open(os.path.join(random_dir, "TUTOR.md")).read()
          and "courses/Random/TUTOR.md" in committed_since(before)
          and not calls(sid, "notes"), committed_since(before))
    check("End commits the filed pages, notes.md and doc.json",
          {"courses/Random/docs/canvas-2026-10-24/notes.md",
           "courses/Random/docs/canvas-2026-10-24/doc.json",
           "courses/Random/docs/canvas-2026-10-24/handwritten/page-01.png"}
          <= set(committed_since(before)), committed_since(before))

    # An untaught canvas, ended with its pages kept: no turn at all.
    s2 = server.js("/sessions/new", {"view": "slate", "title": "Lecture 9"})[1]["id"]
    write_pages(server, s2, 2)
    before = head()
    status, got = server.js("/s/%s/end" % s2, {"subject": "courses/Random",
                                               "transcribe": False})
    time.sleep(1.5)
    check("End {subject, transcribe: false} queues nothing",
          status == 200 and got.get("wrapup") is False and not calls(s2)
          and not waking(s2), got)
    check("and commits docs/<slug>/notes.md with handwritten/page-*.png",
          {"courses/Random/docs/lecture-9/notes.md",
           "courses/Random/docs/lecture-9/handwritten/page-01.png",
           "courses/Random/docs/lecture-9/handwritten/page-02.png"}
          <= set(committed_since(before)), committed_since(before))

    # A page erased after "Save to": its picture and its section of
    # notes.md go, and End commits neither.
    s4 = server.js("/sessions/new", {"view": "slate", "title": "Erased"})[1]["id"]
    write_pages(server, s4, 3)
    server.js("/s/%s/bind" % s4, {"subject": "courses/Random"})
    e_dir = os.path.join(random_dir, "docs", "erased")
    e_notes = os.path.join(e_dir, "notes.md")
    with open(e_notes, "w") as fh:
        fh.write("# Erased\n\n![page 1](handwritten/page-01.png)\n\nfirst words\n\n"
                 "![page 2](handwritten/page-02.png)\n\nsecond words\n\n"
                 "![page 3](handwritten/page-03.png)\n\nthird words\n")
    server.js("/s/%s/slate/save" % s4, {"page": 3, "w": 800, "h": 600,
                                         "png": PNG, "strokes": []})
    before = head()
    status, got = server.js("/s/%s/end" % s4, {"transcribe": False})
    kept = open(e_notes).read()
    check("a page erased after filing loses its picture at End",
          status == 200 and sorted(os.listdir(os.path.join(e_dir, "handwritten")))
          == ["page-01.png", "page-02.png"], got)
    check("and its section of notes.md, the others' words kept",
          "page-03" not in kept and "third words" not in kept
          and "first words" in kept and "second words" in kept, kept)
    check("End commits no erased page",
          "courses/Random/docs/erased/handwritten/page-02.png" in committed_since(before)
          and "courses/Random/docs/erased/handwritten/page-03.png"
          not in committed_since(before), committed_since(before))

    # A stored canvas.dir is used only while its doc.json lists the session.
    s5 = server.js("/sessions/new", {"view": "slate", "title": "Elsewhere"})[1]["id"]
    write_pages(server, s5, 1)
    server.js("/s/%s/bind" % s5, {"subject": "courses/Random"})
    before_notes = open(e_notes).read()
    rec5 = sessions.get(s5, atlas)
    rec5["canvas"] = {"subject": "courses/Random", "dir": "docs/erased"}
    sessions._save(sessions.path(s5, atlas), rec5)
    got = sessions.file_canvas(s5, atlas)
    check("a canvas.dir whose doc.json names another session is not written into",
          got and got != "docs/erased" and open(e_notes).read() == before_notes
          and json.load(open(os.path.join(e_dir, "doc.json"))).get("sessions") == [s4],
          got)
    for bad in ("docs/../docs/erased", "docs/erased/handwritten"):
        rec5 = sessions.get(s5, atlas)
        rec5["canvas"] = {"subject": "courses/Random", "dir": bad}
        sessions._save(sessions.path(s5, atlas), rec5)
        check("a canvas.dir of %r is not used" % bad,
              sessions.file_canvas(s5, atlas) != bad)

    # Keep it unfiled: nothing committed, nothing queued, the pages stay.
    s3 = server.js("/sessions/new", {"view": "slate", "title": "Loose"})[1]["id"]
    write_pages(server, s3, 2)
    before = head()
    status, got = server.js("/s/%s/end" % s3, {"transcribe": False})
    time.sleep(1.5)
    check("End with no subject and no transcription commits nothing and queues nothing",
          status == 200 and got.get("wrapup") is False and head() == before
          and not calls(s3)
          and len(sessions.slate_pages(s3, atlas)) == 2, got)

    # Given days later: an ended canvas reopens and wakes one turn.
    status, got = server.js("/s/%s/give" % s3, {})
    check("/give on an ended canvas reopens it and wakes one turn",
          status == 200 and not (sessions.get(s3, atlas) or {}).get("ended")
          and len(waking(s3)) == 1, got)
    until(lambda: calls(s3, "turn"), 60)
    check("one turn ran", len(calls(s3, "turn")) == 1, calls(s3))

    # Ended from its board, as board.js does: no `transcribe` key, so the
    # wrap-up runs and no transcription turn runs before it.
    until(lambda: os.listdir(os.path.join(atlas, "sessions", s3, "cards")), 30)
    until(lambda: not server.js("/health")[1].get("turns", {}).get("running"), 60)
    status, got = server.js("/s/%s/end" % s3, {"subject": "courses/Random"})
    check("a given canvas ended from its board queues its wrap-up",
          status == 200 and got.get("wrapup") is True, got)
    until(lambda: calls(s3, "wrapup"), 60)
    check("and no transcription: an End without `transcribe` asks for none",
          calls(s3, "wrapup") and not calls(s3, "notes"), calls(s3))

    # -----------------------------------------------------------------------
    # 6. the brief knows the canvas exists
    # -----------------------------------------------------------------------
    repo = sessions.repo(s2, atlas)
    said = brief.briefing(repo, sense)
    check("a canvas's brief names its pages and `board slate --all`",
          "canvas:" in said and "board slate --all" in said
          and "page 1:" in said and "page 2:" in said, said[:1500])
finally:
    if server is not None:
        server.stop()
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails else
      "a canvas is written with no tutor, filed, handed over in one turn, and ended three ways")
sys.exit(1 if fails else 0)
