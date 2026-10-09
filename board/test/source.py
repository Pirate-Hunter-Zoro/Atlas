#!/usr/bin/env python3
"""GET /source/<path>?from=&to=: the read-only source viewer.

It serves a file only when `walk.resolve` finds it, nothing on its way is
fenced or private, and git tracks it; as a page with every line numbered and
the asked range marked. Everything else is 404: untracked, fenced, `..`,
hidden, private, absolute, missing.
"""

import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

tmp = tempfile.mkdtemp(prefix="tutor-source-")
atlas = os.path.join(os.path.realpath(tmp), "Atlas")
os.environ["BOARD_STATE_DIR"] = os.path.join(tmp, ".state")
os.environ["TUTORBOARD_TRASH"] = os.path.join(tmp, ".trash")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
os.environ["TUTORBOARD_COURSES"] = atlas
os.environ["TUTORBOARD_PAGES"] = os.path.join(tmp, ".pages")

from tutorboard import sessions                               # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.server import app                             # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(rel, text):
    path = os.path.join(atlas, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# The fixture: the board's own holds.py and code.py, a subject with its own
# source, and the files that must never be served.
for name in ("holds.py", "code.py"):
    os.makedirs(os.path.join(atlas, "board", "tutorboard"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "tutorboard", name),
                os.path.join(atlas, "board", "tutorboard", name))
BODY = "def solve(x):\n    return x < 2 and '<b>'\n" + "# padding line\n" * 20
write("projects/Beta/tutorboard.json", json.dumps({"name": "Beta", "phi": False}))
write("projects/Beta/src/model.py", "# beta-own-model\n" + BODY)
write("projects/Beta/phi/leak.py", "# phi-secret\n" + BODY)
write("projects/Beta/stage1/run.py", "# stage-secret\n" + BODY)
write("projects/Beta/src/.hidden.py", "# hidden-secret\n" + BODY)
write("ai-config/policy/x.py", "# private-secret\n" + BODY)
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
subprocess.run(["git", "init", "-q", atlas], check=True)
write(".gitignore", "/sessions/\n")
subprocess.run(GIT + ["-C", atlas, "add", "-A"], check=True)
# Tracked or not, a fenced, hidden or private path is refused by name.
subprocess.run(GIT + ["-C", atlas, "add", "-f", "--", "projects/Beta/phi/leak.py",
                      "projects/Beta/src/.hidden.py"], check=True)
subprocess.run(GIT + ["-C", atlas, "commit", "-q", "-m", "fixture"], check=True)
write("projects/Beta/src/untracked.py", "# untracked-secret\n" + BODY)
write("outside.py", "# outside-secret\n" + BODY)
os.makedirs(os.path.join(tmp, "elsewhere"), exist_ok=True)
with open(os.path.join(tmp, "elsewhere", "far.py"), "w") as fh:
    fh.write("# far-secret\n" + BODY)

rec = sessions.new("on Beta", base=atlas, now=1.7e9)
course_repo.Repo(atlas, session=sessions.path(rec["id"], atlas),
                 create=False).set_state(subject="projects/Beta")
SID = rec["id"]

httpd = app.make_server(atlas, 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port


def get(path):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
    conn.request("GET", path)
    r = conn.getresponse()
    out = r.status, r.getheader("Content-Type") or "", r.read().decode("utf-8", "replace")
    conn.close()
    return out


try:
    # holds.py, unprefixed over the Atlas root, lines 40 to 58.
    status, ctype, page = get("/source/board/tutorboard/holds.py?from=40&to=58")
    held = open(os.path.join(ROOT, "tutorboard", "holds.py"), encoding="utf-8").read()
    n = len(held.rstrip("\n").split("\n"))
    check("a tracked file the Atlas root resolves is served as html",
          status == 200 and ctype.startswith("text/html"))
    check("every line is numbered", page.count('class="line') == n
          and 'data-n="1" id="L1"' in page and 'data-n="%d"' % n in page)
    marked = [i for i in range(1, n + 1)
              if '<span class="line mark" data-n="%d"' % i in page]
    check("lines 40 to 58 are the marked range", marked == list(range(40, 59)))
    check("it is read-only and highlighted by the vendored highlight.js",
          "read-only" in page and "/static/vendor/highlight/highlight.min.js" in page
          and 'data-lang="python"' in page and "/static/codeview.js" in page)
    status, _, page = get("/source/board/tutorboard/code.py?from=12")
    check("one line asked for marks that one line",
          status == 200 and page.count("line mark") == 1
          and '<span class="line mark" data-n="12"' in page)

    # Under a session bound to Beta: its own source, and Atlas's.
    status, _, page = get("/s/%s/source/src/model.py?from=2&to=3" % SID)
    check("in a session, the subject's own tracked source is served, escaped",
          status == 200 and "beta-own-model" in page and "&lt;b&gt;" in page
          and "<b>" not in page)
    status, _, page = get("/s/%s/source/board/tutorboard/holds.py" % SID)
    check("and a path under the Atlas root as well", status == 200)
    status, _, page = get("/source/src/model.py?subject=projects/Beta")
    check("unprefixed, ?subject= names the subject", status == 200
          and "beta-own-model" in page)

    refused = [
        "/source/projects/Beta/src/untracked.py",
        "/s/%s/source/src/untracked.py" % SID,
        "/source/outside.py",
        "/source/projects/Beta/phi/leak.py",
        "/s/%s/source/phi/leak.py" % SID,
        "/source/projects/Beta/PHI/leak.py",
        "/source/projects/Beta/stage1/run.py",
        "/source/projects/Beta/src/.hidden.py",
        "/source/ai-config/policy/x.py",
        "/source/../elsewhere/far.py",
        "/source/projects/Beta/../../../elsewhere/far.py",
        "/source/board/tutorboard/../tutorboard/holds.py",
        "/s/%s/source/../../../elsewhere/far.py" % SID,
        "/source/%2e%2e/elsewhere/far.py",
        "/source//etc/passwd",
        "/source/" + os.path.join(tmp, "elsewhere", "far.py").lstrip("/"),
        "/source/board/tutorboard/nope.py",
        "/source/",
    ]
    for path in refused:
        status, _, page = get(path)
        check("%s is 404 and says nothing of it" % path, status == 404
              and "secret" not in page)
finally:
    httpd.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d FAILURES" % len(fails) if fails else "\nall source checks passed")
sys.exit(1 if fails else 0)
