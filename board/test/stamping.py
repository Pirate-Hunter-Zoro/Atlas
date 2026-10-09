#!/usr/bin/env python3
"""The code stamp: what tells the board server its committed code moved.

    python3 test/stamping.py

`stamp.tree` hashes `serve.py` and `tutorboard/` at HEAD. A lesson commit, a
shell file, a test and `bin/board` do not move it; each stamped path does.
`stamp.imports` proves a new tree imports before the freshness thread gives
way to it, and writes nothing into the tree. `serve.py` reads its stamp before
it imports the package. `test/hearing.py` runs the freshness thread itself.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import stamp                                  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


gitdir = tempfile.mkdtemp(prefix="stamp-git-")
plain = tempfile.mkdtemp(prefix="stamp-plain-")


def git(*args):
    return subprocess.run(["git", "-C", gitdir] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=True)


def commit_file(rel, text):
    path = os.path.join(gitdir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel)
    stamp.forget()
    return stamp.tree(gitdir)


try:
    git("init", "-q")
    commit_file("serve.py", "one\n")
    first = commit_file("tutorboard/a.py", "one\n")
    check("a tree with the stamped paths has a stamp", bool(first) and len(first) == 12)
    same = [commit_file("courses/x/answer.txt", "homework\n"),
            commit_file("web/board.js", "shell\n"),
            commit_file("test/t.py", "suite\n"),
            commit_file("bin/board", "cli\n")]
    check("a lesson commit, a shell file, a test and `bin/board` do not move it",
          same == [first] * 4)
    moved = [commit_file("tutorboard/a.py", "two\n"),
             commit_file("serve.py", "two\n")]
    check("`tutorboard/` and `serve.py` each move it",
          len(set([first] + moved)) == 3)
    check("the old launcher is no stamped path: it does not exist",
          stamp.STAMPED == ("serve.py", "tutorboard")
          and not os.path.exists(os.path.join(ROOT, "bin", "tutor")))
    stamp.forget()
    check("and a directory that is not a checkout has no stamp at all",
          stamp.tree(plain) is None)
    serve_src = open(os.path.join(ROOT, "serve.py"), encoding="utf-8").read()
    check("serve.py reads the stamp before it imports the package, or HEAD can "
          "move between the two and never be bounced",
          serve_src.index("stamp.mark_loaded()")
          < serve_src.index("from tutorboard.server.app import main"))

    ok, _ = stamp.imports(ROOT)
    check("the board's own tree imports", ok)
    commit_file("tutorboard/__init__.py", "")
    commit_file("tutorboard/server/__init__.py", "")
    commit_file("tutorboard/server/app.py", "def (:\n")
    ok, line = stamp.imports(gitdir)
    check("a tree that does not import says so, with the reason",
          not ok and "SyntaxError" in line, line)
    check("and the check writes nothing into the tree",
          not any("__pycache__" in d for d, _, _ in os.walk(gitdir)))
finally:
    shutil.rmtree(gitdir, ignore_errors=True)
    shutil.rmtree(plain, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "the stamp moves on a ship and on nothing else")
sys.exit(1 if fails else 0)
