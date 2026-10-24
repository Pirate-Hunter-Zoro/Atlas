#!/usr/bin/env python3
"""`board pull` and `board cost`, on fixtures.

    python3 test/commands.py

PULL. A bare origin stands in for GitHub. A laptop pushes a course file;
`board pull --atlas <mac clone>` fast-forwards the Mac, leaving the tree
clean. A diverged clone is refused with exit 1 and its work kept. An Atlas
or an ai-config with no origin has nothing to pull, exit 0.

COST. A fixture Atlas with three sessions: two bound to courses/Topology with a
`cost.jsonl` each, and one that never billed. `board cost` lists the ones that
billed, `board cost <id>` reports one, `board cost Topology` lists the subject's,
and an unknown name is exit 1.

Neither command reads the real Atlas: both are pointed at the fixture with
`--atlas`, and the config home is a temp dir.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BOARD = os.path.join(ROOT, "bin", "board")
sys.path.insert(0, ROOT)

work = tempfile.mkdtemp(prefix="commands-")
ENV = dict(os.environ, XDG_CONFIG_HOME=os.path.join(work, "xdg"),
           BOARD_STATE_DIR=os.path.join(work, "state"))
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_COURSES"):
    ENV.pop(k, None)

from tutorboard import sessions                               # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def ident(root):
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")


def board(*args, cwd=None):
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=cwd or work,
                       env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=120)
    return p.returncode, p.stdout


try:
    # =======================================================================
    # board pull
    # =======================================================================
    origin = os.path.join(work, "atlas.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    seed = os.path.join(work, "atlas-seed")
    subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
    ident(seed)
    write(os.path.join(seed, "README.md"), "atlas\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    mac = os.path.join(work, "mac")
    laptop = os.path.join(work, "laptop")
    for dest in (mac, laptop):
        subprocess.run(["git", "clone", "-q", origin, dest], check=True, env=ENV)
        ident(dest)

    # The laptop commits a course file, and pushes.
    write(os.path.join(laptop, "courses", "Topology", "notes.md"), "a proof\n")
    git(laptop, "add", "-A")
    git(laptop, "commit", "-qm", "laptop: a proof")
    git(laptop, "push", "-q")

    code, out = board("pull", "--atlas", mac)
    check("`board pull` fast-forwards Atlas to origin",
          code == 0 and git(mac, "rev-parse", "HEAD") == git(laptop, "rev-parse", "HEAD")
          and os.path.isfile(os.path.join(mac, "courses", "Topology", "notes.md")), out)
    check("and leaves the tree clean",
          git(mac, "status", "--porcelain") == "",
          git(mac, "status", "--porcelain"))

    code, out = board("pull", "--quiet", "--atlas", mac)
    check("a pull with nothing new is exit 0", code == 0, out)

    write(os.path.join(laptop, "README.md"), "elsewhere\n")
    git(laptop, "commit", "-qam", "elsewhere")
    git(laptop, "push", "-q")
    write(os.path.join(mac, "README.md"), "here, at the same time\n")
    git(mac, "commit", "-qam", "here")
    code, out = board("pull", "--atlas", mac)
    check("a diverged Atlas is refused with exit 1, and says why",
          code == 1 and "not synced" in out, out)
    check("and its own work is kept",
          open(os.path.join(mac, "README.md")).read() == "here, at the same time\n")

    plain = os.path.join(work, "plain")
    os.makedirs(plain)
    subprocess.run(["git", "init", "-q", plain], check=True)
    code, out = board("pull", "--atlas", plain)
    check("an Atlas with no origin has nothing to pull, and is not an error",
          code == 0 and "nothing to pull" in out, out)

    subprocess.run(["git", "init", "-q", os.path.join(plain, "ai-config")],
                   check=True)
    code, out = board("pull", "--atlas", plain)
    check("nor is an ai-config with no origin, and it says so",
          code == 0 and "nothing to pull: %s has no origin"
          % os.path.join(plain, "ai-config") in out, out)
    code, out = board("pull", "--quiet", "--atlas", plain)
    check("and --quiet says nothing of it", code == 0 and not out.strip(), out)

    # =======================================================================
    # board cost
    # =======================================================================
    atlas = os.path.join(work, "atlas")
    os.makedirs(os.path.join(atlas, "courses", "Topology"))
    os.makedirs(os.path.join(atlas, "board"))
    made = []
    for n in range(3):
        rec = sessions.new(title="s%d" % n, base=atlas, now=1700000000 + n)
        made.append(rec["id"])
    for sid in made[:2]:
        sessions.bind(sid, "courses/Topology", base=atlas)
    for sid, tokens in zip(made[:2], (1000, 3000)):
        write(os.path.join(atlas, "sessions", sid, "cost.jsonl"),
              "".join(json.dumps({"iso": "2026-10-09 10:0%d:00" % i, "turn": i + 1,
                                  "agent": "claude", "requests": 2,
                                  "tokens": tokens, "usd": 0.5}) + "\n"
                      for i in range(2)))

    code, out = board("cost", "--atlas", atlas)
    check("`board cost` lists every session that billed, one line each",
          code == 0 and made[0] in out and made[1] in out and made[2] not in out,
          out)
    check("with its turns and its total", "8.0k tokens across 4 turn(s)" in out, out)

    code, out = board("cost", made[1], "--atlas", atlas)
    check("`board cost <session id>` reports that session alone",
          code == 0 and made[1] in out and made[0] not in out, out)

    code, out = board("cost", made[0], "--turns", "--atlas", atlas)
    check("and --turns lists every turn", code == 0
          and "2026-10-09 10:00:00" in out and "2026-10-09 10:01:00" in out, out)

    code, out = board("cost", "Topology", "--atlas", atlas)
    check("`board cost <subject>` lists the sessions bound to it",
          code == 0 and made[0] in out and made[1] in out, out)

    code, out = board("cost", "Nowhere", "--atlas", atlas)
    check("an unknown session or subject is exit 1, in words",
          code == 1 and "no session or subject" in out, out)

    empty = os.path.join(work, "empty")
    os.makedirs(os.path.join(empty, "board"))
    code, out = board("cost", "--atlas", empty)
    check("an Atlas where nothing billed says so", code == 0
          and "no turn has reported a cost" in out, out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "board pull and board cost work on fixtures")
sys.exit(1 if fails else 0)
