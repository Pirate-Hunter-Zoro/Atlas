#!/usr/bin/env python3
"""TUTOR.md is quiet: it rides with End or real work, never alone.

    python3 test/quiet.py

  * `board memo` writes TUTOR.md and commits nothing.
  * A `board push` or a save-button save whose only change is TUTOR.md
    commits nothing, and says so. End commits it.
  * A save with real work carries TUTOR.md along, and with no message says
    `save: <changed files>` under the subject's prefix.
  * `gitops.is_save` reads the old save strings and `save:` back as saves,
    bare or under the subject's own prefix, and nothing else: a `board: ` or
    `HANDOFF: ` commit is work. The beside-the-lesson filter asks it.

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) with no origin.
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

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n     " + str(detail)[:600]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-quiet-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-quiet-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import gitops, sessions                               # noqa: E402
from tutorboard.lesson import git as lesson_git                       # noqa: E402


def git(*args):
    return subprocess.run(["git", "-C", base] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, timeout=60)


def head():
    return git("rev-parse", "HEAD").stdout.strip()


def board(args, session, stdin=""):
    env = dict(os.environ, TUTORBOARD_SESSION=session)
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=base, env=env,
                       input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True,
                       timeout=120)
    return p.returncode, p.stdout


try:
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    write(os.path.join(base, ".gitignore"), "/sessions/\n")
    proj = os.path.join(base, "projects", "Probe")
    write(os.path.join(proj, "tutorboard.json"),
          json.dumps({"name": "Probe"}))
    write(os.path.join(proj, "TUTOR.md"),
          "# Probe\n\n## Where things are\n\nsrc/\n\n## Now\n\nthe loader\n\n"
          "## Open decisions\n\n## Done recently\n")
    write(os.path.join(proj, "notes.md"), "first\n")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")

    # ---- a lesson that changes only TUTOR.md --------------------------------
    sid = sessions.new(base=base)["id"]
    sess = sessions.path(sid, base)
    sessions.bind(sid, "projects/Probe", base=base)
    start = head()

    code, out = board(["memo", "Now"], sess, "wire the loader to the split\n")
    check("`board memo` writes TUTOR.md", code == 0 and "wire the loader" in
          open(os.path.join(proj, "TUTOR.md"), encoding="utf-8").read(), out)
    check("and commits nothing on its own", head() == start)

    code, out = board(["push"], sess)
    check("a `board push` whose only change is TUTOR.md commits nothing",
          code == 0 and head() == start, out)
    check("and says it waits for End or real work", lesson_git.QUIET in out, out)

    code, out = board(["push", "the tutor's notes"], sess)
    check("nor with a message of its own", code == 0 and head() == start, out)

    rec = lesson_git.run_push(sessions.repo(sid, base))
    check("a save-button save whose only change is TUTOR.md commits nothing",
          rec.get("ok") is True and head() == start, rec)
    check("and push.json says why",
          lesson_git.QUIET in (rec.get("detail") or ""), rec)
    check("so the lesson has left no commit",
          git("rev-list", "--count", "%s..HEAD" % start).stdout.strip() == "0")

    rec, ok, said = sessions.end(sid, base=base)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("End commits it, in one commit",
          ok and git("rev-list", "--count", "%s..HEAD" % start).stdout.strip()
          == "1" and files == ["projects/Probe/TUTOR.md"], (said, files))

    # ---- TUTOR.md rides with real work --------------------------------------
    sid2 = sessions.new(base=base)["id"]
    sess2 = sessions.path(sid2, base)
    sessions.bind(sid2, "projects/Probe", base=base)
    code, out = board(["memo", "Done recently"], sess2, "- the loader\n")
    write(os.path.join(proj, "notes.md"), "first\nsecond\n")
    before = head()
    rec = lesson_git.run_push(sessions.repo(sid2, base))
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    subject = git("log", "-1", "--format=%s").stdout.strip()
    check("a save with real work commits, TUTOR.md riding along",
          rec.get("ok") is True and head() != before
          and set(files) == {"projects/Probe/notes.md",
                             "projects/Probe/TUTOR.md"}, (rec, files))
    check("and with no message says `save: <changed files>` under the prefix",
          subject in ("Probe: save: TUTOR.md, notes.md",
                      "Probe: save: notes.md, TUTOR.md"), subject)

    # ---- reading a save back ---------------------------------------------
    own = ("Probe",)
    saves = ("Probe: save: notes.md", "save: a, b and 3 more",
             "projects/Probe: " + gitops.SAVE, "Lesson complete.",
             "stopping point", "Probe: lesson transcript", "lesson transcript")
    work = ("Probe: saved the loader", "Probe: knn", "fix: save button",
            "save the plot", "", "Other: save: x", "board: lesson complete",
            "board: HANDOFF drops the TUTOR.md commit decision -- the runner's "
            "wrap-up runs sessions.end again, which commits the edit",
            "research/Cohort-Study: the handoff says what is applied and what the "
            "lab still owes", "HANDOFF: the owner's answers",
            "handoff: item 6", "galois handoff", "Probe: hand-off")
    check("`gitops.is_save` reads every save message as a save, bare or under "
          "the subject's prefix",
          all(gitops.is_save(m, own) for m in saves),
          [m for m in saves if not gitops.is_save(m, own)])
    check("and anything else as work, whatever its head",
          not any(gitops.is_save(m, own) for m in work),
          [m for m in work if gitops.is_save(m, own)])
    check("`gitops.save_message` names three and counts the rest",
          gitops.save_message(["a", "b", "c", "d", "e"])
          == "save: a, b, c and 2 more"
          and gitops.save_message(["a"]) == "save: a")

    for name, msg in (("w1", "board: HANDOFF drops the commit decision"),
                      ("w2", "HANDOFF: the owner's answers"),
                      ("s1", "Probe: lesson transcript"),
                      ("s2", "lesson transcript"),
                      ("s3", "projects/Probe: save: notes.md")):
        write(os.path.join(proj, name + ".md"), name + "\n")
        git("add", "-A")
        git("commit", "-q", "-m", msg)
    write(os.path.join(proj, "src.py"), "x = 1\n")
    git("add", "-A")
    git("commit", "-q", "-m", "Probe: the owner's loader")
    beside = lesson_git.beside_the_lesson(sessions.repo(sid2, base)) or {}
    said = [c["subject"] for c in beside.get("commits") or []]
    check("beside the lesson, the owner's commits are listed and the board's "
          "saves are not",
          {"Probe: the owner's loader",
           "board: HANDOFF drops the commit decision",
           "HANDOFF: the owner's answers"} <= set(said)
          and not {"Probe: lesson transcript", "lesson transcript",
                   "projects/Probe: save: notes.md"} & set(said), said)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("TUTOR.md rides with End or real work, and never commits alone")
