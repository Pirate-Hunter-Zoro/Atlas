#!/usr/bin/env python3
"""Typeset givens on the slate: the server's half.

    python3 test/placing.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) holding a copy of the
tracked hw04 write-up. Nothing touches the real `sessions/`.

  * Each given in the payload's `problem` names its figure, `fig`, the digest
    of `server/tikz.py`'s kind-latex figure of it; the hub queues the ones
    not yet compiled, and a compiled one is an SVG and, with dvipng, a PNG,
    both served under /figure/.
  * `POST /slate/save` keeps a page's `objects`, field by field, and keeps
    the stored ones when a save has no `objects` key; a send freezes them
    with the answer and its `[slate]` line names them as the problem's data,
    not their working.
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
ATLAS = os.path.dirname(BOARD_DIR)
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


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-placing-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-placing-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import sessions, tex                               # noqa: E402
from tutorboard.course import givens                               # noqa: E402
from tutorboard.lesson import inbox, slate, state                  # noqa: E402
from tutorboard.runner import service as runner_service            # noqa: E402
from tutorboard.server import handler, hub, tikz                   # noqa: E402

HW04 = os.path.join(ATLAS, "courses", "Probability", "homework", "hw04", "hw04.tex")
runner_service.wake = lambda r: True
httpd = None
try:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=base, check=True)
    write(os.path.join(base, ".gitignore"), "/sessions/\nlive/\n")
    course = os.path.join(base, "courses", "Markov-Lab")
    write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Markov Lab"}))
    os.makedirs(os.path.join(course, "homework", "hw04"))
    shutil.copyfile(HW04, os.path.join(course, "homework", "hw04", "hw04.tex"))
    rec = sessions.new("hw04", base=base)
    sessions.bind(rec["id"], "courses/Markov-Lab", base=base)
    repo = sessions.repo(rec["id"], base)
    repo.set_state(hw="homework/hw04/hw04.tex", problem="5")
    repo = sessions.repo(rec["id"], base)

    # --- each given names its figure, and the hub queues it ------------------
    got = state.load_problem(repo)
    P = (got or {}).get("givens", [{}])[0]
    want = tikz.digest("latex", givens.figure_source(P.get("tex", "")), repo.root)
    check("each given names its kind-latex figure by digest",
          P.get("id") == "P" and P.get("fig") == want
          and all(g.get("fig") for g in got["givens"]), got and got.get("givens"))
    jobs = state.figure_jobs(repo, got)
    check("the figures not yet compiled are compile jobs",
          [j[0] for j in jobs] == [g["fig"] for g in got["givens"]]
          and all(j[1] == "latex" for j in jobs))
    worker = tikz.TikzWorker(repo)
    the_hub = hub.Hub(repo, worker)
    data = the_hub.build()
    check("and the hub queues them when it builds the payload",
          set(j[0] for j in worker.held) >= set(g["fig"] for g in got["givens"])
          and data["problem"]["givens"][0]["fig"] == want)

    if tex.have_tex() and shutil.which("dvisvgm"):
        tikz.compile_figure(repo.tikz, repo.root, want, "latex",
                            givens.figure_source(P["tex"]))
        svg = os.path.join(repo.tikz, want + ".svg")
        png = os.path.join(repo.tikz, want + ".png")
        check("a given's figure compiles to an SVG as narrow as the given",
              os.path.isfile(svg) and "width='" in open(svg).read(400)
              and float(open(svg).read(600).split("width='")[1].split("pt")[0]) < 200)
        check("and to a PNG where dvipng is installed",
              os.path.isfile(png) or not shutil.which("dvipng"))
        check("and needs no compiling again", not state.figure_jobs(repo, got)[:1]
              or state.figure_jobs(repo, got)[0][0] != want)
    else:
        print("skip LaTeX or dvisvgm is not installed; the figure is not compiled here")
        os.makedirs(repo.tikz, exist_ok=True)
        write(os.path.join(repo.tikz, want + ".svg"), "<svg/>")
        with open(os.path.join(repo.tikz, want + ".png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nfake")

    # --- over HTTP ------------------------------------------------------------
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

    def ask(path, body=None):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (port, path),
            method="POST" if body is not None else "GET",
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), ""

    status, body, kind = ask("/figure/%s.png" % want)
    check("/figure/<digest>.png serves the PNG", status == 200 and body[:4] == b"\x89PNG"
          and "png" in kind, (status, kind))
    status, body, kind = ask("/figure/%s.svg" % want)
    check("and .svg the SVG, as before", status == 200 and b"<svg" in body, status)

    placed = {"id": "P", "kind": "tex", "tex": P["tex"], "fig": want,
              "x": 120.5, "y": 80, "w": 134, "h": 75}
    junk = [{"id": "Q", "kind": "tex", "tex": "Q", "fig": "../../etc", "x": 1, "y": 1,
             "w": 1, "h": 1},
            {"id": "R", "kind": "img", "fig": want, "x": 1, "y": 1, "w": 1, "h": 1},
            {"id": "S", "kind": "tex", "fig": want, "x": "nope", "y": 1, "w": 1, "h": 1},
            "not an object"]
    stroke = {"c": "#000", "w": 3, "pts": [[1, 1, 0.5], [9, 9, 0.5]]}
    status, _b, _k = ask("/slate/save", {"page": 1, "w": 900, "h": 500,
                                         "strokes": [stroke], "objects": [placed] + junk})
    page = json.load(open(os.path.join(repo.slate, "page-01.json")))
    check("a save keeps the page's typeset givens, and only well-formed ones",
          status == 200 and page.get("objects") == [placed], page.get("objects"))
    ask("/slate/save", {"page": 1, "w": 900, "h": 500, "strokes": [stroke, stroke]})
    page = json.load(open(os.path.join(repo.slate, "page-01.json")))
    check("a save with no `objects` key keeps the stored ones",
          page.get("objects") == [placed] and len(page.get("strokes")) == 2)
    check("and the slate's state hands them back",
          slate.read_slate_pages(repo)[0].get("objects") == [placed])
    before = len(inbox.unread(repo))
    status, b, _k = ask("/slate/save", {"page": 1, "w": 900, "h": 500, "send": True,
                                        "strokes": [stroke],
                                        "objects": [placed, dict(placed, x=300)],
                                        "png": "data:image/png;base64,iVBORw0KGgo="})
    reply = json.loads(b.decode("utf-8"))
    frozen = json.load(open(os.path.join(repo.answers, "%s-r%d.json"
                                         % (reply["turn"], reply["rev"]))))
    check("a send freezes the givens with the answer",
          len(frozen.get("objects") or []) == 2 and frozen["objects"][0] == placed)
    line = (inbox.unread(repo)[before:] or [{}])[-1].get("text", "")
    check("and its [slate] line names them once, as data and not their working",
          line.startswith("[slate]") and "typeset given (P) was placed" in line
          and "not their working" in line, line)
    ask("/slate/save", {"page": 2, "w": 900, "h": 500, "send": True, "strokes": [stroke],
                        "objects": []})
    line = (inbox.unread(repo) or [{}])[-1].get("text", "")
    check("a page with none says nothing of them", "typeset" not in line, line)
finally:
    if httpd is not None:
        httpd.shutdown()
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a typeset given is compiled, kept with its page, and named as data")
