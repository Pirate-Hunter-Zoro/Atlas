#!/usr/bin/env python3
"""One resolver: which workspace and session a CLI command runs on.

1. `TUTORBOARD_SESSION`, when set, is the session directory.
2. Otherwise the session is `find_repo()` plus `live/`.
3. `find_repo` never answers with the Atlas root: `board status` there exits
   non-zero and creates nothing.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = os.path.dirname(ROOT)
BOARD = os.path.join(ROOT, "bin", "board")
sys.path.insert(0, ROOT)

from tutorboard.course import repo as course_repo              # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def listing(top):
    """The Atlas root's own entries: where a stray live/ would appear. Not a
    deep walk, because other suites write below it while this one runs."""
    return set(os.listdir(top))


def run(args, cwd, session=None):
    env = dict(os.environ)
    env.pop("TUTORBOARD_SESSION", None)
    if session:
        env["TUTORBOARD_SESSION"] = session
    p = subprocess.run([sys.executable, BOARD] + args, cwd=cwd, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


base = tempfile.mkdtemp(prefix="resolver-")
was = os.environ.pop("TUTORBOARD_SESSION", None)
try:
    ws = os.path.join(base, "ws")
    os.makedirs(os.path.join(ws, "notes"))
    with open(os.path.join(ws, "tutorboard.json"), "w") as fh:
        fh.write('{"name": "ws"}')

    check("session paths hang off the workspace's live/",
          course_repo.session_path(ws, "cards") == os.path.join(ws, "live", "cards"))
    check("find_repo walks up to the nearest workspace",
          course_repo.find_repo(os.path.join(ws, "notes")) == ws)

    r = course_repo.resolve(ws, create=False)
    check("without the variable the session is <root>/live",
          r.root == ws and r.session == os.path.join(ws, "live") and r.live == r.session)
    check("and create=False makes nothing", not os.path.exists(r.session))

    sess = os.path.join(base, "sessions", "20261008-120000")
    os.environ["TUTORBOARD_SESSION"] = sess
    r = course_repo.resolve(ws)
    check("TUTORBOARD_SESSION is the session directory",
          r.session == sess and r.cards == os.path.join(sess, "cards")
          and os.path.isdir(os.path.join(sess, "cards")))
    check("and the workspace's own live/ is left alone",
          not os.path.exists(os.path.join(ws, "live")))
    check("code holding only the root reaches the same session",
          course_repo.session_path(ws, "turns.jsonl") == os.path.join(sess, "turns.jsonl"))
    os.environ.pop("TUTORBOARD_SESSION")
    course_repo._BOUND.clear()

    for where in (ATLAS, ROOT):
        try:
            course_repo.find_repo(where)
            got = "returned"
        except course_repo.NoWorkspace as exc:
            got = exc.code
        check("find_repo refuses %s" % os.path.relpath(where, ATLAS),
              isinstance(got, str) and "not a workspace" in got)

    before = listing(ATLAS)
    code, out = run(["status"], ATLAS)
    check("`board status` at the Atlas root exits non-zero",
          code != 0 and "not a workspace" in out)
    check("and creates nothing", listing(ATLAS) == before)

    proc = subprocess.run([sys.executable, BOARD, "write", "note", "probe"],
                          cwd=ATLAS, input=b"what the next turn needs\n",
                          env=dict(os.environ, TUTORBOARD_SESSION=sess),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=120)
    check("with TUTORBOARD_SESSION a write at the Atlas root lands in the session",
          proc.returncode == 0 and any(
              n.endswith("probe.md") for n in os.listdir(os.path.join(sess, "cards"))))
    check("and still creates nothing there", listing(ATLAS) == before)
finally:
    os.environ.pop("TUTORBOARD_SESSION", None)
    if was is not None:
        os.environ["TUTORBOARD_SESSION"] = was
    shutil.rmtree(base, ignore_errors=True)


print("%d FAILURES" % len(fails) if fails
      else "a command runs on one session directory, and never on the Atlas root")
sys.exit(1 if fails else 0)
