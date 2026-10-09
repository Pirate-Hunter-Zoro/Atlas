#!/usr/bin/env python3
"""The meeting deck in the one reader: the Meetings library, end to end.

    python3 test/meeting.py

A real server (`serve.py --port 0`) on a temp Atlas whose projects/Meetings
holds a built deck, with a fake provider standing in for claude. The deck is
read where every document is read -- the Meetings library -- and:

  * `/library.json?subject=projects/Meetings` carries the deck's own record
    (`meeting`): ready, which deck it is, what no source supports.
  * Ink on a slide is saved into Meetings, stamped with its deck; a save
    stamped with another deck is let go (`gone`).
  * A mark plus "say what is wrong" (`/library/feedback`) writes the round
    beside the deck and queues ONE `[revise]` turn in a session bound to
    projects/Meetings, which the fake provider runs once.
  * The meeting page and its routes are gone.

Nothing here touches a real session, port or provider.
"""

import glob
import json
import os
import shutil
import signal
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

box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-meeting-"))
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["TUTORBOARD_PAGES"] = os.path.join(box, "pages")
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
             "TUTORBOARD_CLUSTER"):
    os.environ.pop(name, None)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)


def git(*args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"]
                          + list(args), cwd=atlas, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


def until(cond, timeout=60.0, step=0.1):
    end = time.time() + timeout
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(step)
    return cond()


# ---------------------------------------------------------------------------
# the fake provider: records what it was handed, and nothing else
# ---------------------------------------------------------------------------
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, sys, time
with open(%(calls)r, "a") as fh:
    fh.write(json.dumps({"sid": os.path.basename(os.environ.get("TUTORBOARD_SESSION", "")),
                         "prompt": sys.argv[-1], "t": time.time()}) + "\n")
''' % {"calls": CALLS})
os.chmod(FAKE, 0o755)
write(os.path.join(CONFIG_HOME, "tutor-board", "config.json"), json.dumps({
    "provider": "fake", "vision_agent": "fake", "concurrency": 2,
    "headless_timeout": 120, "doing_timeout": 180, "handoff_timeout": 60,
    "agents": {"fake": {"cmd": [FAKE], "label": "Fake",
                        "headless_first": [FAKE, "{prompt}"], "usage": "none"}},
}))


def calls():
    try:
        with open(CALLS) as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# a temp Atlas: projects/Meetings with a built deck, and one other subject
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "Atlas")
MEET = os.path.join(atlas, "projects", "Meetings")
DECK = os.path.join(MEET, "docs", "meeting")
ASKED = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3600))
write(os.path.join(MEET, "tutorboard.json"), json.dumps({"name": "Meetings", "phi": True}))
write(os.path.join(MEET, "TUTOR.md"), "# Meetings\n\n## Now\n\n- the deck\n")
write(os.path.join(atlas, "projects", "TRD", "tutorboard.json"),
      json.dumps({"name": "TRD-EHR", "phi": False}))
write(os.path.join(DECK, "doc.json"), json.dumps({
    "title": "Meeting deck: the last week", "source": "meeting.tex", "sessions": [],
    "asked_at": ASKED}))
write(os.path.join(DECK, "meeting.tex"),
      "\\documentclass{beamer}\n\\begin{document}\n\\begin{frame}{Findings}\n"
      "AUC 0.602.\n\\end{frame}\n\\end{document}\n")
write(os.path.join(DECK, "meeting.pdf"), b"%PDF-1.4\n%%EOF\n")
write(os.path.join(DECK, "_brief.md"), "# Brief\n\nAUC 0.602 at k = 50.\n")
write(os.path.join(DECK, "_brief.json"), json.dumps({
    "subjects": ["projects/TRD"], "names": {"projects/TRD": "TRD-EHR"},
    "period": "the last week", "human": "the last week", "figures": []}))
write(os.path.join(atlas, ".gitignore"),
      "/sessions/\n**/.ink/\n*.pdf\n_brief.*\n_provenance.json\nfigures/\n")
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-qm", "fixture")


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
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path), data=data, method=method,
            headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        try:
            return status, json.loads(raw.decode() or "{}")
        except ValueError:
            return status, {}

    def stop(self):
        try:
            os.killpg(self.p.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            self.p.wait(30)
        except subprocess.TimeoutExpired:
            self.p.kill()


def sessions_on(subject):
    out = []
    for path in sorted(glob.glob(os.path.join(atlas, "sessions", "*", "session.json"))):
        with open(path) as fh:
            rec = json.load(fh)
        if rec.get("subject") == subject:
            out.append(rec["id"])
    return out


def inbox(sid):
    try:
        with open(os.path.join(atlas, "sessions", sid, "inbox", "messages.jsonl")) as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except OSError:
        return []


Q = "?subject=projects/Meetings"
server = None
try:
    server = Server()
    check("the server started on a temp Atlas", server.port is not None,
          "".join(server.lines[-20:]))

    # ---- the deck is a document of the Meetings library, with its record ------
    status, lib = server.ask("GET", "/library.json" + Q)
    rows = [d for d in lib.get("documents", []) if d.get("meeting")]
    rec = lib.get("meeting") or {}
    check("the Meetings library lists the deck, id `meeting`, with its own record",
          status == 200 and len(rows) == 1 and rows[0]["id"] == "meeting"
          and rows[0]["pdf"] and rec.get("state") == "ready" and rec.get("ready")
          and rec.get("deck") == ASKED and rec.get("subjects") == ["TRD-EHR"], lib)
    status, other = server.ask("GET", "/library.json?subject=projects/TRD")
    check("and no other subject's library carries one", "meeting" not in other)

    # ---- a mark on a slide, stamped with its deck ------------------------------
    stroke = {"c": "#e8746c", "w": 2, "p": [0.1, 0.1, 0.3, 0.4]}
    status, got = server.ask("POST", "/annotate/save" + Q, {
        "card": "doc/meeting/p1", "strokes": [stroke], "deck": ASKED, "send": False})
    ink = glob.glob(os.path.join(MEET, ".ink", "doc-meeting-p1*.json"))
    check("a mark on slide 1 is kept in the Meetings subject", status == 200
          and got.get("ok") and len(ink) == 1, (status, got))
    status, got = server.ask("POST", "/annotate/save" + Q, {
        "card": "doc/meeting/p2", "strokes": [stroke], "deck": "an older deck"})
    check("a mark stamped with another deck is let go, not kept",
          status == 409 and got.get("gone")
          and not glob.glob(os.path.join(MEET, ".ink", "doc-meeting-p2*")), got)

    # ---- say what is wrong: one round, one [revise] turn ---------------------
    before = sessions_on("projects/Meetings")
    status, got = server.ask("POST", "/library/feedback" + Q, {
        "document": "meeting", "text": "Slide 1 needs the ROC curve.", "page": 1})
    check("say what is wrong is filed and asks the Meetings tutor",
          status == 200 and got.get("ok") and got.get("asked")
          and got.get("marks") == 1, got)
    notes = glob.glob(os.path.join(DECK, "feedback", "*.md"))
    said = open(notes[0]).read() if notes else ""
    check("the round is written beside the deck, with the words and the mark",
          len(notes) == 1 and "ROC curve" in said and "page 1" in said.lower(), said[:600])
    made = [s for s in sessions_on("projects/Meetings") if s not in before]
    check("in a session bound to projects/Meetings, made because the owner asked",
          len(made) == 1 and got.get("session") == made[0], (made, got))
    sid = made[0] if made else ""
    revise = [m for m in inbox(sid) if str(m.get("text", "")).startswith("[revise]")]
    check("one [revise] line, naming the deck's source and its brief",
          len(revise) == 1 and "docs/meeting/meeting.tex" in revise[0]["text"]
          and "docs/meeting/_brief.md" in revise[0]["text"], inbox(sid))
    ran = until(lambda: [c for c in calls() if c["sid"] == sid], timeout=90)
    check("the fake provider runs that one turn, handed the [revise] line",
          len(ran) == 1 and "[revise]" in ran[0]["prompt"], ran or calls())
    time.sleep(1.5)
    check("and nothing else is woken", len(calls()) == 1, calls())

    # ---- the meeting page is gone --------------------------------------------
    gone = [p for p in ("/meeting", "/meeting/view", "/meeting/deck.json", "/meeting/pdf")
            if server.ask("GET", p)[0] != 404]
    check("the meeting page and its routes are not served", not gone, gone)
    web = os.path.join(BOARD, "web")
    check("meeting.html and meeting.js are gone",
          not os.path.exists(os.path.join(web, "meeting.html"))
          and not os.path.exists(os.path.join(web, "meeting.js")))
finally:
    if server:
        server.stop()
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the meeting deck is read and revised in the Meetings library, in the one reader")
