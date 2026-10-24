#!/usr/bin/env python3
"""The problem on their screen: posed before it is taught, and switched from the panel.

    python3 test/posing.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) with its own git
repository. Nothing touches the real `sessions/`.

  * `homework.pose` writes a statement only where the label is absent, a
    `\\todo` or empty, lays an empty region under a problem with none, and
    never touches a region or a transcribed statement (a region-only label
    is stated; a problem missing its `\\end{problem}` is refused); an
    unchanged file is not rewritten.
  * `homework.current` is the pinned label, else the next problem to write up
    once it is stated.
  * `board writeup pose <label>` pins session.json `problem`.
  * `POST /problem` switches it among the set's problems with a non-waking
    `[problem]` line, refuses a label the set lacks, and clears it.
  * A stored session on a bound set gets the homework sitting (session.json
    has no `session`), told to pose and which problem is on screen; a docs/
    write-up is no set; the teach brief carries the pose rule.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-posing-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-posing-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)
os.environ.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                  GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

from tutorboard import brief, sense, sessions                      # noqa: E402
from tutorboard.course import homework                             # noqa: E402
from tutorboard.lesson import inbox                                # noqa: E402
from tutorboard.runner import service as runner_service            # noqa: E402
from tutorboard.server import handler, hub, tikz                   # noqa: E402

SHEET = r"""\documentclass{article}
\newenvironment{problem}[1]{\par Problem #1.}{\par}
\providecommand{\todo}[1]{#1}
\begin{document}
\begin{problem}{1}
A transcribed statement.
\end{problem}
% ===== SOLUTION 1 =====
Their argument.
% ===== END SOLUTION 1 =====

\begin{problem}{2}
\todo{statement not yet transcribed}
\end{problem}
% ===== SOLUTION 2 =====
% ===== END SOLUTION 2 =====

\begin{problem}{3}
Stated, with no region yet.
\end{problem}

\end{document}
"""

woken = []
runner_service.wake = lambda r: woken.append(r) or True
httpd = None
try:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=base, check=True)
    write(os.path.join(base, ".gitignore"), "/sessions/\nlive/\n")
    course = os.path.join(base, "courses", "Markov-Lab")
    write(os.path.join(course, "tutorboard.json"),
          json.dumps({"name": "Markov Lab", "phi": False}))
    tex = os.path.join(course, "homework", "hw01", "hw01.tex")
    write(tex, SHEET)

    # --- homework.pose ---------------------------------------------------------
    said, why = homework.pose(tex, "1", "A different statement.")
    check("a transcribed statement and its region are kept, and the file not rewritten",
          said == {"label": "1", "statement": "kept", "region": "kept"}
          and read(tex) == SHEET, (said, why))
    said, _ = homework.pose(tex, "2", "Show that $P$ is a transition matrix.")
    text = read(tex)
    check("a \\todo statement is written, and its empty region left as it is",
          said["statement"] == "written" and said["region"] == "kept"
          and "Show that $P$ is a transition matrix." in text
          and "statement not yet transcribed" not in text
          and "% ===== SOLUTION 2 =====\n% ===== END SOLUTION 2 =====" in text, said)
    said, _ = homework.pose(tex, "3", "")
    text = read(tex)
    check("a stated problem with no region gets an empty marker pair under it",
          said == {"label": "3", "statement": "kept", "region": "added"}
          and "Stated, with no region yet.\n\\end{problem}\n% ===== SOLUTION 3 =====\n"
              "% ===== END SOLUTION 3 =====" in text, said)
    said, _ = homework.pose(tex, "4", "Find $E[X_3]$.")
    text = read(tex)
    check("an absent label is appended before \\end{document}, statement and empty region",
          said == {"label": "4", "statement": "written", "region": "added"}
          and text.index("\\begin{problem}{4}") < text.index("\\end{document}")
          and "Find $E[X_3]$.\n\\end{problem}\n% ===== SOLUTION 4 =====\n"
              "% ===== END SOLUTION 4 =====" in text, said)
    check("and the region still reads as not written",
          [p["label"] for p in homework.problems(tex) if not p["written"]]
          == ["2", "3", "4"])
    check("their argument in region 1 is untouched", "Their argument." in text)
    said, why = homework.pose(tex, "../x", "S")
    check("a label that is not a label is refused", said is None and "label" in why)
    prose = os.path.join(course, "homework", "hw01", "prose.tex")
    PROSE = ("\\begin{document}\nProblem 7. Stated in prose.\n% ===== SOLUTION 7 =====\n"
             "% ===== END SOLUTION 7 =====\n\\end{document}\n")
    write(prose, PROSE)
    said, why = homework.pose(prose, "7", "Another statement.")
    check("a label with a region and no problem environment is stated, and left alone",
          said == {"label": "7", "statement": "kept", "region": "kept"}
          and read(prose) == PROSE, (said, why, read(prose)))
    OPEN = ("\\begin{document}\n\\begin{problem}{5}\n\\todo{statement not yet transcribed}\n"
            "\\begin{problem}{6}\nProblem six, transcribed.\n\\end{problem}\n"
            "\\end{document}\n")
    write(prose, OPEN)
    said, why = homework.pose(prose, "5", "Problem five.")
    check("a problem with no \\end{problem} of its own never borrows the next one's",
          said is None and "end{problem}" in why and read(prose) == OPEN, (said, why))
    said, why = homework.add(prose, "5", "Problem five.", "An argument.")
    check("and add refuses it too, writing nothing",
          said is None and "end{problem}" in why and read(prose) == OPEN, (said, why))
    os.remove(prose)

    # --- homework.current ------------------------------------------------------
    probs = homework.problems(tex)
    check("current is the pinned label when the set has it",
          homework.current(probs, "4") == "4")
    check("else the next to write up, once it is stated",
          homework.current(probs, None) == "2" and homework.current(probs, "99") == "2")
    check("and nothing when the next is not yet stated",
          homework.current([{"label": "a", "stated": False, "written": False}], None)
          is None)
    write(tex, SHEET)

    # --- board writeup pose ----------------------------------------------------
    rec = sessions.new("Markov homework", base=base)
    where = sessions.path(rec["id"], base)
    sessions.bind(rec["id"], "courses/Markov-Lab", base=base)
    env = dict(os.environ, TUTORBOARD_SESSION=where)
    p = subprocess.run([sys.executable, BOARD, "writeup", "use", "hw01"], cwd=base,
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    p = subprocess.run([sys.executable, BOARD, "writeup", "pose", "2"], cwd=base,
                       env=env, input="Show that every row sums to one.\n",
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    st = sessions.get(rec["id"], base)
    check("board writeup pose writes the statement and pins the label",
          p.returncode == 0 and st.get("problem") == "2"
          and "Show that every row sums to one." in read(tex), p.stdout)
    check("session.json carries the problem key from birth",
          "problem" in sessions.new("Another", base=base))

    # --- the sitting ------------------------------------------------------------
    repo = sessions.repo(rec["id"], base)
    said = sense.session_sense(repo)
    check("a stored session on a bound set is a homework sitting",
          "HOMEWORK sitting on hw01" in said, said[-400:])
    check("told to pose each problem, and which one is on their screen",
          "Pose each problem" in said and "Problem 2 is on their screen" in said)
    check("the teach brief carries the pose rule",
          "board writeup pose <label>" in sense.WRITEUP_SENSE
          and sense.WRITEUP_SENSE in brief.briefing(repo, sense))
    check("and the brief's write-up line names the problem on screen",
          "problem 2 is on their screen" in brief.briefing(repo, sense))
    check("a skip in a homework sitting defers the problem",
          "still assigned" in sense.skip_sense(repo))
    plain = sessions.new("A lesson", base=base)
    sessions.bind(plain["id"], "courses/Markov-Lab", base=base)
    docs = os.path.join(course, "docs", "a-lesson", "writeup.tex")
    write(docs, SHEET)
    sessions.repo(plain["id"], base).set_state(hw="docs/a-lesson/writeup.tex")
    prepo = sessions.repo(plain["id"], base)
    check("a session's own docs/ write-up is no homework set",
          homework.bound(prepo.root, prepo.state())
          and homework.assigned(prepo.root, prepo.state()) is None
          and "HOMEWORK sitting" not in sense.session_sense(prepo))

    # --- POST /problem, over real HTTP -----------------------------------------
    worker = tikz.TikzWorker(repo)
    the_hub = hub.Hub(repo, worker)
    the_hub.payload = json.dumps({})
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = repo
    httpd.hub = the_hub
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def post(path, body):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                     method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8") or "{}")

    before = len(inbox.unread(repo))
    status, body = post("/problem", {"label": "3"})
    lines = inbox.unread(repo)[before:]
    check("POST /problem switches the problem on their screen",
          status == 200 and body.get("changed") is True
          and sessions.get(rec["id"], base).get("problem") == "3", body)
    check("with one non-waking [problem] line, and no turn woken",
          len(lines) == 1 and lines[0]["text"].startswith("[problem]")
          and "problem 3 of hw01" in lines[0]["text"]
          and lines[0].get("wake") is False and not inbox.waiting(repo) and not woken,
          lines)
    status, body = post("/problem", {"label": "3"})
    check("the same label again writes nothing",
          status == 200 and body.get("changed") is False
          and len(inbox.unread(repo)) == before + 1)
    status, body = post("/problem", {"label": "9"})
    check("a label the set does not have is refused",
          status == 400 and sessions.get(rec["id"], base).get("problem") == "3", body)
    status, body = post("/problem", {"label": ""})
    check("an empty label clears it",
          status == 200 and sessions.get(rec["id"], base).get("problem") is None, body)
finally:
    if httpd is not None:
        httpd.shutdown()
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a problem is posed before it is taught, and the panel switches it")
