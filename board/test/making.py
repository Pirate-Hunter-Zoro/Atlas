#!/usr/bin/env python3
"""A deck or a paper on demand, from any session (`POST /artifact`).

    python3 test/making.py

A real server (`serve.py --port 0`) on a temp Atlas with git, and a fake
provider that does what a `[writeup]` turn is told: it reads the file its line
names, writes it, and runs `board build` on it. What is checked:

  * a paper ask makes doc.json with source `<slug>.md` first, and its line
    names that file from the Atlas root, Markdown and `board build`; a deck's
    names a `.tex` and beamer;
  * the strip says writing, and the fake turn's write and build flip it to
    done; the paper yields a .docx, the deck a PDF;
  * an unbound session is refused and makes nothing; from a subject's row
    (`?subject=`) the ask lands in the newest open session on it and needs a
    line; an ended session refuses it;
  * `/writeup` and `/writeup/scopes` are gone.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
sys.path.insert(0, BOARD)

box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-making-"))
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["TUTORBOARD_PAGES"] = os.path.join(box, "pages")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
          "TUTORBOARD_CLUSTER", "TUTORBOARD_FRESH"):
    os.environ.pop(k, None)
for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"),
             ("GIT_COMMITTER_NAME", "t"), ("GIT_COMMITTER_EMAIL", "t@t")):
    os.environ[k] = v

from tutorboard import artifacts, sessions  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:600]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# the fake provider: a [writeup] turn writes the named file and builds it
# ---------------------------------------------------------------------------
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys, time
prompt = sys.argv[-1]
rec = {"sid": os.path.basename(os.environ.get("TUTORBOARD_SESSION", "")),
       "cwd": os.getcwd(), "prompt": prompt}
def log(**kw):
    rec.update(kw)
    with open(%(calls)r, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
if "[writeup]" not in prompt:
    log(kind="other")
    sys.exit(0)
m = re.search(r"board build ([^`\s]+)`", prompt)
src = m.group(1) if m else ""
time.sleep(2.5)
if src.endswith(".md"):
    text = "# How the warmth model works\n\nA paper, written by the fake.\n\n## One\n\nText.\n"
else:
    text = ("\\documentclass{beamer}\n\\begin{document}\n"
            "\\begin{frame}{One}\nA deck, written by the fake.\n\\end{frame}\n"
            "\\end{document}\n")
os.makedirs(os.path.dirname(src) or ".", exist_ok=True)
with open(src, "w") as fh:
    fh.write(text)
p = subprocess.run(["board", "build", src], stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, universal_newlines=True)
log(kind="writeup", src=src, rc=p.returncode, out=p.stdout[-1500:])
''' % {"calls": CALLS})
os.chmod(FAKE, 0o755)
write(os.path.join(CONFIG_HOME, "tutor-board", "config.json"), json.dumps({
    "provider": "fake", "vision_agent": "fake", "concurrency": 2,
    "headless_timeout": 180, "doing_timeout": 240, "handoff_timeout": 60,
    "agents": {"fake": {"cmd": [FAKE], "label": "Fake",
                        "headless_first": [FAKE, "{prompt}"],
                        "usage": "none"}},
}))


def calls(kind=None):
    out = []
    try:
        with open(CALLS) as fh:
            for line in fh:
                r = json.loads(line)
                if kind is None or r.get("kind") == kind:
                    out.append(r)
    except OSError:
        pass
    return out


# ---------------------------------------------------------------------------
# a temp Atlas: one project
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "atlas")
beta = os.path.join(atlas, "projects", "Beta")
write(os.path.join(beta, "tutorboard.json"), json.dumps({"name": "Beta", "phi": False}))
write(os.path.join(atlas, ".gitignore"), "/sessions/\n")
subprocess.run(["git", "init", "-q", "-b", "main", atlas], check=True)
subprocess.run(["git", "-C", atlas, "add", "-A"], check=True)
subprocess.run(["git", "-C", atlas, "-c", "commit.gpgsign=false", "commit", "-qm",
                "fixture"], check=True)


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

    def ask(self, method, path, body=None):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path),
            data=None if body is None else json.dumps(body).encode(), method=method,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                status = r.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        try:
            return status, json.loads(raw.decode("utf-8"))
        except ValueError:
            return status, {}

    def stop(self):
        try:
            os.killpg(self.p.pid, 15)
        except OSError:
            pass
        try:
            self.p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(self.p.pid, 9)


def until(cond, timeout=90.0, step=0.2):
    end = time.time() + timeout
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(step)
    return cond()


def inbox(sid):
    path = os.path.join(atlas, "sessions", sid, "inbox", "messages.jsonl")
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


def docs():
    try:
        return sorted(os.listdir(os.path.join(beta, "docs")))
    except OSError:
        return []


srv = Server()
try:
    check("the server is up", srv.port)

    status, made = srv.ask("POST", "/sessions/new", {})
    SID = made.get("id") or ""
    check("a new session opens", status == 200 and SID)

    # ---- an unbound session makes nothing ---------------------------------
    status, got = srv.ask("POST", "/s/%s/artifact" % SID, {"make": "paper"})
    check("an unbound session is refused, and told to bind first",
          status == 409 and "bind" in (got.get("error") or ""), got)
    check("and nothing was made", docs() == [] and not inbox(SID))
    status, got = srv.ask("POST", "/s/%s/artifact" % SID, {"make": "essay"})
    check("a product that is neither is refused by name",
          status == 400 and "deck or paper" in (got.get("error") or ""), got)

    status, got = srv.ask("POST", "/s/%s/bind" % SID, {"subject": "projects/Beta"})
    check("the session binds to projects/Beta", status == 200 and got.get("ok"), got)

    # ---- a paper ------------------------------------------------------------
    status, got = srv.ask("POST", "/s/%s/artifact" % SID,
                          {"make": "paper", "about": "the warmth model"})
    check("a paper is asked for", status == 200 and got.get("ok") is True
          and got.get("make") == "paper" and got.get("session") == SID, got)
    slug = got.get("doc") or ""
    art = os.path.join(beta, "docs", slug)
    doc = artifacts.read(art) or {}
    check("the doc.json was made first, with source <slug>.md, listing this session",
          slug and doc.get("source") == slug + ".md" and doc.get("sessions") == [SID]
          and doc.get("asked_at"), doc)
    src = "projects/Beta/docs/%s/%s.md" % (slug, slug)
    check("the reply names the source from the Atlas root", got.get("source") == src, got)
    lines = [m for m in inbox(SID) if m.get("signal") == "writeup"]
    line = lines[-1].get("text", "") if lines else ""
    check("a [writeup] line is queued, named for that exact source",
          line.startswith("[writeup]") and ("THE FILE IS `%s`" % src) in line, line[:300])
    check("and it says a paper is Markdown and to run board build on it",
          "A PAPER IS MARKDOWN" in line and ("`board build %s`" % src) in line)
    check("about what they said, not the session",
          "the warmth model" in line and "THE CONCEPTS THIS SITTING COVERED" not in line)

    def strip(make=None):
        _, b = srv.ask("GET", "/s/%s/board.json" % SID)
        rows = b.get("writeups") or []
        return [r for r in rows if make is None or r.get("makes") == make]

    writing = until(lambda: [r for r in strip("paper") if r.get("state") == "writing"], 10)
    check("the strip says a paper is being written", writing, strip())
    done = until(lambda: [r for r in strip("paper") if r.get("state") == "done"], 120)
    built = calls("writeup")
    check("the fake turn wrote the source and built it",
          built and built[0].get("src") == src and built[0].get("rc") == 0,
          built[0].get("out") if built else srv.lines[-20:])
    check("the strip flips from writing to done, naming the document",
          done and done[0].get("doc") == slug, strip())
    check("and the paper yields a .docx beside its source",
          os.path.isfile(os.path.join(art, slug + ".docx")))
    check("the turn ran in the Atlas root",
          built and os.path.realpath(built[0].get("cwd") or "") == os.path.realpath(atlas))

    # ---- a deck --------------------------------------------------------------
    status, got = srv.ask("POST", "/s/%s/artifact" % SID, {"make": "deck"})
    dslug = got.get("doc") or ""
    dart = os.path.join(beta, "docs", dslug)
    ddoc = artifacts.read(dart) or {}
    dsrc = "projects/Beta/docs/%s/%s.tex" % (dslug, dslug)
    check("a deck is asked for, with doc.json naming a .tex",
          status == 200 and dslug and ddoc.get("source") == dslug + ".tex"
          and got.get("source") == dsrc, (got, ddoc))
    lines = [m for m in inbox(SID) if m.get("signal") == "writeup"]
    line = lines[-1].get("text", "") if lines else ""
    check("its line names the .tex, says beamer, and names board build",
          ("THE FILE IS `%s`" % dsrc) in line and "BEAMER" in line
          and ("`board build %s`" % dsrc) in line)
    check("with nothing named, its scope is this session",
          "THE CONCEPTS THIS SITTING COVERED" in line and "board recap --all" in line)
    done = until(lambda: [r for r in strip("slides") if r.get("state") == "done"], 150)
    check("the deck is written and built, and the strip says done",
          done and os.path.isfile(os.path.join(dart, dslug + ".pdf"))
          and artifacts.type_of(os.path.join(dart, dslug + ".tex")) == "deck",
          [c.get("out") for c in calls("writeup")][-1:])

    # ---- from a subject's row ------------------------------------------------
    status, got = srv.ask("POST", "/artifact?subject=projects/Beta", {"make": "deck"})
    check("from a subject's row, a line is required: there is no session to default to",
          status == 400 and "about" in (got.get("error") or ""), got)
    n = len(inbox(SID))
    status, got = srv.ask("POST", "/artifact?subject=projects/Beta",
                          {"make": "paper", "about": "a paper from home"})
    check("from a subject's row, the router hands it to the newest open session on it",
          status == 200 and got.get("session") == SID and len(inbox(SID)) == n + 1
          and "a paper from home" in inbox(SID)[-1].get("text", ""), got)
    check("and its doc.json lists that session",
          SID in (artifacts.read(os.path.join(beta, "docs", got.get("doc") or "-")) or {})
          .get("sessions", []))
    status, _ = srv.ask("POST", "/artifact", {"make": "paper", "about": "x"})
    check("unprefixed with no subject named is refused", status == 400)

    # ---- what is gone --------------------------------------------------------
    status, _ = srv.ask("POST", "/writeup/scopes", {"repo": "projects/Beta"})
    check("/writeup/scopes is gone", status == 404)
    status, _ = srv.ask("POST", "/s/%s/writeup" % SID, {"makes": "paper"})
    check("and /writeup with it", status == 404)
    check("scopes.py is gone",
          not os.path.exists(os.path.join(BOARD, "tutorboard", "scopes.py")))

    # ---- an ended session ----------------------------------------------------
    until(lambda: len(calls("writeup")) >= 3, 120)
    status, _ = srv.ask("POST", "/s/%s/end" % SID, {})
    check("the session ends", status == 200)
    status, got = srv.ask("POST", "/s/%s/artifact" % SID, {"make": "paper"})
    check("an ended session refuses a new document", status == 409, got)
finally:
    srv.stop()
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a deck or a paper is asked for from any session, made first, written, built "
      "and said done")
