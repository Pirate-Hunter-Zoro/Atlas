#!/usr/bin/env python3
"""The briefing sees what was done on a laptop -- and never claims it.

    "I want to be able to pop open my laptop and code up something and have the
     tutor see that if it pertains to whatever project we're in."

Every turn is a cold turn, so the briefing is the only place this can go. The
checks are the two rules, and the second is the one that matters.

  * SCOPED TO THE WORKSPACE. One repository holds nine of them and `git log` at
    its root answers about all nine. A turn about Galois Theory told about
    PSYCH-ASR's afternoon is a turn that will try to teach it.
  * NAMED AS THE PERSON'S WORK, NEVER THE TUTOR'S. A turn that mistakes a commit
    somebody made on their laptop for something it did itself will report having
    done work it has not done -- invisible from the outside, confidently stated,
    and it makes every other thing the tutor says worth less. Whose work it is
    has to be unmissable.
  * NOT THE DIFF. A briefing is about 22k tokens and it stays that way.
  * SILENT WHEN THERE IS NOTHING. A heading over "no changes" is forty tokens of
    nothing, on every turn, for ever.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import atlas, brief                                   # noqa: E402
from tutorboard.course import repo as course_repo                     # noqa: E402
from tutorboard.lesson import git as lesson_git                       # noqa: E402

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


def git(base, *args):
    return subprocess.run(["git"] + list(args), cwd=base,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=30)


base = tempfile.mkdtemp(prefix="tutor-beside-")
try:
    write(os.path.join(base, "atlas.json"), json.dumps(
        {"families": [{"id": "courses", "name": "Courses"},
                      {"id": "research", "name": "Research"}]}))
    mine = os.path.join(base, "courses", "Galois-Theory")
    other = os.path.join(base, "research", "PSYCH-ASR")
    for r in (mine, other):
        write(os.path.join(r, "tutorboard.json"), json.dumps({"name": "X"}))
        os.makedirs(os.path.join(r, "live", "cards"), exist_ok=True)
    write(os.path.join(mine, "notes", "ch04.tex"), "one\n")
    write(os.path.join(other, "psych_asr", "asr.py"), "one\n")

    git(base, "init", "-q", "-b", "main")
    git(base, "config", "user.email", "t@example.com")
    git(base, "config", "user.name", "Tester")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "everything, to start from")

    repo = course_repo.Repo(mine)
    them = course_repo.Repo(other)

    # The tutor's knowledge stops at the newest card it wrote.
    write(os.path.join(repo.cards, "0001-a-card.md"),
          "---\nkind: lesson\n---\n\nSomething the tutor said.\n")
    time.sleep(1.1)

    # Then the person opens a laptop and does some work, in ONE workspace.
    write(os.path.join(mine, "notes", "ch04.tex"), "one\ntwo\n")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "worked through the tower law by hand")
    write(os.path.join(other, "psych_asr", "asr.py"), "one\ntwo\n")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "the typist emits the seam's contract")
    # And leaves something uncommitted.
    write(os.path.join(mine, "notes", "ch05.tex"), "started\n")
    # The board's own scratch changes constantly while a sitting runs.
    write(os.path.join(repo.live, "state.json"),
          json.dumps({"course": "Galois", "chapter": "Ch 4"}))

    lesson_git._BESIDE.clear()
    rec = lesson_git.beside_the_lesson(repo)
    check("what the person committed to THIS workspace is seen",
          any("tower law" in c["subject"] for c in rec["commits"]))
    check("and what they committed to ANOTHER workspace is not",
          not any("typist" in c["subject"] for c in rec["commits"]))

    lesson_git._BESIDE.clear()
    theirs = lesson_git.beside_the_lesson(them)
    check("each workspace sees its own, and only its own",
          any("typist" in c["subject"] for c in theirs["commits"])
          and not any("tower law" in c["subject"] for c in theirs["commits"]))

    check("an uncommitted file is named",
          any(n.endswith("ch05.tex") for n in rec["uncommitted"]))
    check("and named relative to the WORKSPACE, not to the repository root",
          all(not n.startswith("courses" + os.sep) for n in rec["uncommitted"]))
    check("the lesson's own live/ is not reported as somebody's work",
          not any(n.startswith("live") for n in rec["uncommitted"]))
    check("and the count is of the same files as the list",
          rec["files"] == len(rec["uncommitted"]))

    # NOT THE DIFF, ever. A briefing is 22k tokens and it stays that way.
    src = open(os.path.join(ROOT, "tutorboard", "lesson", "git.py"),
               encoding="utf-8").read()
    beside_src = src.split("def beside_the_lesson")[1]
    check("the diff itself is never asked for",
          '"diff"' not in beside_src and "-p" not in beside_src.split("pretty")[0][-80:])
    check("subjects are capped, so an afternoon of commits is a count",
          lesson_git.BESIDE_COMMITS <= 12 and lesson_git.BESIDE_FILES <= 20)

    # --- the wording, which IS the feature ---------------------------------
    said = brief.beside_sense(repo)
    check("the briefing says it", "tower law" in said)
    for must in ("PERSON", "YOU DID NOT DO ANY OF IT", "not"):
        check("and says whose work it is: %r" % must, must in said)
    check("it is said in the heading too",
          "what THEY did" in said)
    check("and the turn is told what to do with it",
          "teach THAT" in said or "open it" in said)
    # Every "you did" in it is inside a PROHIBITION. The instruction "do not
    # describe it as something you did" contains the phrase and is the opposite
    # of the failure; what must never appear is an affirmative claim.
    low = said.lower()
    import re as _re
    # The negation can fall on either side: "do not describe it as something you
    # did" puts it before, and "YOU DID NOT DO ANY OF IT" puts it after.
    claims = [m.start() for m in _re.finditer(r"you (?:did|wrote|built|made)", low)
              if "not" not in low[max(0, m.start() - 30):m.end() + 16]]
    check("every mention of the tutor doing it is a prohibition, never a claim",
          not claims)

    # --- silent when there is nothing --------------------------------------
    quiet = os.path.join(base, "courses", "Quiet")
    write(os.path.join(quiet, "tutorboard.json"), json.dumps({"name": "Q"}))
    os.makedirs(os.path.join(quiet, "live", "cards"), exist_ok=True)
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "a quiet workspace")
    q = course_repo.Repo(quiet)
    # A SECOND, because git compares whole seconds and `--since` is given an
    # integer. A card written in the same second as the commit that made the
    # workspace would leave that commit inside the window -- which errs toward
    # telling the tutor, and is right, but is not what this check is about.
    time.sleep(1.1)
    write(os.path.join(q.cards, "0001-x.md"), "---\nkind: lesson\n---\n\nhi\n")
    lesson_git._BESIDE.clear()
    check("a workspace where nothing happened says nothing at all",
          brief.beside_sense(q) == "")

    # --- a workspace that is not in git at all ------------------------------
    loose = tempfile.mkdtemp(prefix="tutor-loose-")
    os.makedirs(os.path.join(loose, "live", "cards"), exist_ok=True)
    write(os.path.join(loose, "tutorboard.json"), json.dumps({"name": "L"}))
    lesson_git._BESIDE.clear()
    check("and one that is not a git repository is not an error",
          brief.beside_sense(course_repo.Repo(loose)) == "")
    shutil.rmtree(loose, ignore_errors=True)

    # --- cached, because the payload is polled four times a second ----------
    lesson_git._BESIDE.clear()
    t0 = time.time()
    for _ in range(40):
        lesson_git.beside_the_lesson(repo)
    check("forty asks cost one pair of git calls (%dms)"
          % int((time.time() - t0) * 1000), time.time() - t0 < 2.0)

finally:
    atlas.forget()
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the tutor is told what they did, and never that it did it")
