#!/usr/bin/env python3
"""A save commits only its own workspace.

Atlas holds the tool and every workspace. A save tapped in one -- the save
button, `board push`, `board finish`'s offer -- commits that
workspace's directory and nothing else: never `board/`, never another
workspace, never an `.nfs*` file the NFS client left behind. `board push "msg"
-- <paths>` narrows it further, which is how a turn commits the work it did
under a message naming the thread.

Run against a real repository laid out the way Atlas is, with a bare origin and
Atlas's real root .gitignore. The fixture workspace is projects/Alpha.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import paths                                  # noqa: E402
from tutorboard.course import repo as course_repo             # noqa: E402
from tutorboard.lesson import git as lesson_git               # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True,
                       text=True)
    return p.returncode, p.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def committed(repo):
    return set(git(repo, "show", "--name-only", "--format=", "HEAD")[1].split())


def dirty(repo):
    out = subprocess.run(["git", "-C", repo, "status", "--porcelain", "-uall"],
                         capture_output=True, text=True).stdout
    return {line[3:] for line in out.splitlines() if line.strip()}


work = tempfile.mkdtemp(prefix="scoped-")
try:
    origin = os.path.join(work, "atlas.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    repo = os.path.join(work, "atlas")
    alpha = os.path.join(repo, "projects", "Alpha")
    beta = os.path.join(repo, "projects", "Beta")
    write(os.path.join(alpha, "tutorboard.json"), "{}\n")
    write(os.path.join(alpha, "live", "slate", "page-01.json"), "{}\n")
    write(os.path.join(alpha, "src", "a.py"), "a = 1\n")
    write(os.path.join(beta, "tutorboard.json"), "{}\n")
    write(os.path.join(beta, "y.py"), "y = 1\n")
    write(os.path.join(repo, "board", "x.py"), "x = 1\n")
    # The real root .gitignore, because that is what keeps `.nfs*` out.
    shutil.copy(os.path.join(os.path.dirname(ROOT), ".gitignore"),
                os.path.join(repo, ".gitignore"))
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "first")
    git(repo, "remote", "add", "origin", origin)
    git(repo, "push", "-q", "-u", "origin", "main")

    # --- the save button ---------------------------------------------------
    write(os.path.join(alpha, "notes.md"), "tonight\n")
    write(os.path.join(alpha, "live", "slate", "page-02.json"), "{}\n")
    write(os.path.join(alpha, ".nfs0000000000abcd00000001"), "litter\n")
    write(os.path.join(beta, "y.py"), "y = 2\n")
    write(os.path.join(repo, "board", "x.py"), "x = 2\n")

    rec = lesson_git.run_push(course_repo.Repo(alpha), "lesson complete")
    got = committed(repo)
    check("a save from one workspace commits and pushes", rec.get("ok") is True)
    check("its work and its transcript go in the commit",
          {"projects/Alpha/notes.md",
           "projects/Alpha/live/slate/page-02.json"} <= got)
    check("board/ does not", not any(f.startswith("board/") for f in got))
    check("another workspace does not",
          not any(f.startswith("projects/Beta/") for f in got))
    check("an .nfs file does not", not any(".nfs" in f for f in got))
    left = dirty(repo)
    check("and the other two are still uncommitted, untouched",
          {"board/x.py", "projects/Beta/y.py"} <= left)
    check("and the .nfs file is still on disk, ignored rather than tracked",
          os.path.exists(os.path.join(alpha, ".nfs0000000000abcd00000001"))
          and not git(repo, "ls-files", "projects/Alpha/.nfs*")[1])
    check("the subject names the workspace",
          git(repo, "log", "-1", "--format=%s")[1].endswith(
              "Alpha: lesson complete"))
    check("and push.json says it saved, with no claim about other workspaces",
          json.load(open(os.path.join(alpha, "live", "push.json")))["ok"] is True
          and "also" not in rec)

    # --- a turn commits its own work, naming the thread ---------------------
    write(os.path.join(alpha, "src", "a.py"), "a = 2\n")
    write(os.path.join(alpha, "src", "b.py"), "b = 1\n")

    def board(*args):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=alpha,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    code, out = board("push", "knn thread: weight by LR", "--no-build",
                      "--", "src/a.py")
    check("`board push msg -- <paths>` commits those paths", code == 0
          and committed(repo) == {"projects/Alpha/src/a.py"})
    check("under a message naming the thread",
          git(repo, "log", "-1", "--format=%s")[1].endswith(
              "knn thread: weight by LR"))
    check("and leaves the rest of the workspace for its own commit",
          "projects/Alpha/src/b.py" in dirty(repo))

    head = git(repo, "rev-parse", "HEAD")[1]
    code, out = board("push", "reach", "--", "../../board/x.py")
    check("a path outside the workspace is refused, and nothing is committed",
          code != 0 and "not in this workspace" in out
          and git(repo, "rev-parse", "HEAD")[1] == head)

    code, out = board("push", "everything", "--no-build")
    got = committed(repo)
    check("a bare `board push` is the same scope as the save button",
          code == 0 and "projects/Alpha/src/b.py" in got
          and not any(f.startswith(("board/", "projects/Beta/")) for f in got)
          and not any(".nfs" in f for f in got))

    # --- the pathspec itself --------------------------------------------------
    # A workspace that holds the tool (the repository root in a single-clone
    # layout) still never commits it.
    top = os.path.dirname(paths.TOOL)
    specs, refused = lesson_git.save_pathspec(top, top)
    check("a workspace containing the tool excludes it",
          ":(exclude)%s" % os.path.basename(paths.TOOL) in specs
          and specs[0] == "." and refused == [])
    # A wildcard exclude, or one outside the paths it narrows, makes git 2.52's
    # `add -A` add no untracked file at all.
    check("and no exclude is a wildcard", not any("*" in s for s in specs))
    specs, _ = lesson_git.save_pathspec(
        os.path.join(top, "courses", "Nowhere"), top)
    check("a workspace holding nothing nested gets no exclude at all",
          specs == ["courses/Nowhere"])
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a save commits its own workspace and nothing else")
