#!/usr/bin/env python3
"""The two caches every session shares, and serve.py on a Slurm host.

  1. TikZ: one compiler, one cache at `sessions/.tikz/`, keyed by the source
     and the subject's macros. Two sessions in different subjects whose macros
     differ get two figures from one cache; a second session on a subject
     reuses the first one's figure.
  2. PDF pages: one cache at `paths.PAGES`, one `<digest>/` per build, served
     at `/paper/` with or without a session prefix.
  3. serve.py exits non-zero on a Slurm host: `TUTOR_SLURM=1`, or `sbatch` on
     PATH even with `TUTOR_SLURM=0`.
"""

import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-caches-")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")

import threading                                              # noqa: E402

from tutorboard import paths, sessions                        # noqa: E402
from tutorboard.course import paper, repo as course_repo      # noqa: E402
from tutorboard.server import app, spawn, tikz                # noqa: E402
from tutorboard.runner import service as runner_service  # noqa: E402

paths.PAGES = os.path.join(tmp, "pages")
runner_service.wake = lambda repo: False

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# the fixture: two subjects whose macros define one command two ways
# ---------------------------------------------------------------------------
atlas = os.path.join(tmp, "Atlas")
SUBJECT = {"A": "courses/Alpha", "B": "projects/Beta"}
# A run of length 1 in Alpha and 6 in Beta: the same source, two pictures.
LENGTH = {"A": "1", "B": "6"}
for who, rel in SUBJECT.items():
    write(os.path.join(atlas, rel, "tutorboard.json"),
          json.dumps({"name": os.path.basename(rel), "phi": False}))
    write(os.path.join(atlas, rel, "latex", "coursemacros.sty"),
          "\\ProvidesPackage{coursemacros}\n\\newcommand{\\runlen}{%s}\n" % LENGTH[who])

CARD = ("---\ntitle: a figure\n---\n\nHere it is.\n\n```tikz\n"
        "\\draw (0,0) -- (\\runlen,0);\n```\n")


def session(title, subject, n):
    rec = sessions.new(title, base=atlas, now=1.7e9 + n)
    where = sessions.path(rec["id"], atlas)
    course_repo.Repo(atlas, session=where, create=False).set_state(subject=subject)
    write(os.path.join(where, "cards", "0001-figure.md"), CARD)
    return rec["id"], where


SID = {}
DIR = {}
for n, who in enumerate(("A", "B")):
    SID[who], DIR[who] = session("session " + who, SUBJECT[who], n)

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def ask(path):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    conn.request("GET", path)
    r = conn.getresponse()
    out = r.status, r.read()
    conn.close()
    return out


FIGURE = re.compile(r"@@FIGURE:([0-9a-f]+):(\w+)@@")


def figure(sid):
    """`(digest, status)` of the one figure on the session's card."""
    status, body = ask("/s/%s/board.json" % sid)
    if status != 200:
        return None, None
    for card in json.loads(body.decode("utf-8")).get("cards") or []:
        m = FIGURE.search(card.get("body") or "")
        if m:
            return m.group(1), m.group(2)
    return None, None


# ---------------------------------------------------------------------------
# 1. TikZ
# ---------------------------------------------------------------------------
print("\n-- one TikZ cache, keyed by source and macros --")
CACHE = os.path.join(atlas, "sessions", ".tikz")
got = {who: figure(SID[who]) for who in ("A", "B")}
check("both sessions' cards carry a figure", all(got[w][0] for w in got))
check("the same source in two subjects with different macros is two figures",
      got["A"][0] != got["B"][0])
check("each digest is the source keyed by its own subject's macros",
      got["A"][0] == tikz.digest("tikz", "\\draw (0,0) -- (\\runlen,0);\n",
                                 os.path.join(atlas, SUBJECT["A"]))
      and got["B"][0] == tikz.digest("tikz", "\\draw (0,0) -- (\\runlen,0);\n",
                                     os.path.join(atlas, SUBJECT["B"])))
check("every stored session's Repo caches in sessions/.tikz",
      all(os.path.realpath(course_repo.Repo(os.path.join(atlas, SUBJECT[w]),
                                            session=DIR[w], create=False).tikz)
          == os.path.realpath(CACHE) for w in DIR))
check("there is one compiler for the process",
      tikz.compiler() is tikz.compiler())

have_tex = shutil.which("latex") and shutil.which("dvisvgm")
if have_tex:
    deadline = time.time() + 120
    want = [os.path.join(CACHE, got[w][0] + ".svg") for w in ("A", "B")]
    while time.time() < deadline and not all(os.path.exists(p) for p in want):
        time.sleep(0.3)
    check("both figures compile into the one cache",
          all(os.path.exists(p) for p in want))
    check("and nothing lands in either session's directory",
          not any(os.path.exists(os.path.join(DIR[w], "tikzcache")) for w in DIR))

    def width(path):
        with open(path, encoding="utf-8") as fh:
            m = re.search(r"<svg[^>]*\swidth=['\"]([\d.]+)", fh.read())
        return float(m.group(1)) if m else 0.0

    wa, wb = width(want[0]), width(want[1])
    check("each figure was drawn with its own subject's macros (%.1f < %.1f)" % (wa, wb),
          0 < wa < wb)
    for who in ("A", "B"):
        deadline = time.time() + 20
        while time.time() < deadline and figure(SID[who])[1] != "ready":
            time.sleep(0.3)
        check("session %s's card says its figure is ready" % who,
              figure(SID[who])[1] == "ready")
        status, body = ask("/s/%s/figure/%s.svg" % (SID[who], got[who][0]))
        check("session %s serves its figure out of the shared cache" % who,
              status == 200 and body.startswith((b"<?xml", b"<svg")))
else:
    print("skip the compile: no latex or dvisvgm on this machine")

# A second session on Alpha reuses Alpha's figure: ready at once, no new file.
before = sorted(os.listdir(CACHE))
sid2, _dir2 = session("second on Alpha", SUBJECT["A"], 5)
again = figure(sid2)
check("a second session on a subject gets that subject's figure",
      again[0] == got["A"][0])
if have_tex:
    check("ready at once, out of the cache, with nothing compiled again",
          again[1] == "ready" and sorted(os.listdir(CACHE)) == before)

# Changing a subject's macros changes its figures' names.
write(os.path.join(atlas, SUBJECT["A"], "latex", "coursemacros.sty"),
      "\\ProvidesPackage{coursemacros}\n\\newcommand{\\runlen}{2}\n% changed\n")
check("a changed macro file is a new digest",
      tikz.digest("tikz", "\\draw (0,0) -- (\\runlen,0);\n",
                  os.path.join(atlas, SUBJECT["A"])) != got["A"][0])


# ---------------------------------------------------------------------------
# 2. PDF pages
# ---------------------------------------------------------------------------
print("\n-- one page cache, outside the tree --")
check("the page cache is paths.PAGES", paper.cache_dir() == paths.PAGES)
digest = "0123456789abcdef"
write(os.path.join(paths.PAGES, digest, digest + "-1.png"), "page one")
check("a page name maps into its build's directory",
      paper.page_file(digest + "-1.png")
      == os.path.join(paths.PAGES, digest, digest + "-1.png"))
check("and no other name maps anywhere",
      all(paper.page_file(n) is None
          for n in ("../x-1.png", "zzz-1.png", digest + "-1.png.txt", "")))
check("cached lists a build's pages", paper.cached(digest) == [digest + "-1.png"])
status, body = ask("/paper/%s-1.png" % digest)
check("/paper/ answers unprefixed, out of the shared cache",
      status == 200 and body == b"page one")
status, body = ask("/s/%s/paper/%s-1.png" % (SID["B"], digest))
check("and the same page under a session", status == 200 and body == b"page one")
check("an unprefixed /paper/ name that is not a page is 404",
      ask("/paper/state.json")[0] == 404 and ask("/paper/..%2fx-1.png")[0] == 404)


# ---------------------------------------------------------------------------
# 3. serve.py refuses a Slurm host
# ---------------------------------------------------------------------------
print("\n-- serve.py on a Slurm host --")
SERVE = os.path.join(ROOT, "serve.py")


def serve(env):
    try:
        p = subprocess.run([sys.executable, SERVE, "--port", "0", "--atlas", atlas],
                           env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=30)
    except subprocess.TimeoutExpired:
        return None, "still serving after 30 s"
    return p.returncode, p.stdout.decode("utf-8", "replace")


code, out = serve(dict(os.environ, TUTOR_SLURM="1"))
check("TUTOR_SLURM=1 serve.py --port 0 exits non-zero, saying why",
      code not in (None, 0) and "Slurm" in out)

fake = os.path.join(tmp, "bin")
write(os.path.join(fake, "sbatch"), "#!/bin/sh\nexit 0\n")
os.chmod(os.path.join(fake, "sbatch"), 0o755)
code, out = serve(dict(os.environ, TUTOR_SLURM="0",
                       PATH=fake + os.pathsep + os.environ.get("PATH", "")))
check("sbatch on PATH refuses too, whatever TUTOR_SLURM says",
      code not in (None, 0) and "Slurm" in out)

httpd.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print("%d failed" % len(fails))
    sys.exit(1)
print("one TikZ cache and one page cache serve every session, and no board runs "
      "on a Slurm host")
