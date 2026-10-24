#!/usr/bin/env python3
"""What this repository is allowed to carry.

    python3 test/tracked.py

This repository is PUBLIC, and the rule it is built on is one sentence:

    If it cannot go into a public repository, it does not live in the
    repository. It lives outside the tree and something inside the tree says
    where.

A rule written down is obeyed until somebody runs `git add -A` in a directory
they have not looked in. So the rule is code: `tutorboard/audit.py` holds it,
`.githooks/pre-commit` asks it of every staged path, and this file asks it of
the whole index on every run of the suite, then asks git itself whether it can
see what the ignore rules keep out. The second half of this file tests the
guards themselves, in temporary repositories.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutorboard import audit                           # noqa: E402


# The whole REPOSITORY, not the tool: asked of git rather than derived by
# counting `..`, so it is still right if the board is ever vendored deeper.
def repo_root():
    tool = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=tool,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").strip()


HERE = repo_root()

fails = []
checked = 0


def fail(msg):
    fails.append(msg)
    print("FAIL " + msg)


def ok(msg):
    print("ok   " + msg)


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"]
                          + list(args), cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


def tracked():
    p = subprocess.run(["git", "ls-files", "-z"], cwd=HERE,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        return None
    return [n for n in p.stdout.decode("utf-8", "replace").split("\0") if n]


files = tracked() if HERE else None
if files is None:
    print("skip  not a git repository")
    sys.exit(0)

# ---- every tracked path, through the one audit the pre-commit hook runs -----
checked += len(files)
for msg in audit.check(files, HERE):
    fail(msg)


# ---- A MISSION'S PROGRESS TRAIL STAYS ON DISK -----------------------------
#
# Cross-board missions are gone, but a workspace's `live/missions/` can still
# hold the trail files they wrote, one per mission: the assistant's own
# sentences about what it just finished. That is session detail, and it is not
# kept out by being small or by nobody thinking about it: `live/*` in every
# workspace excludes it.
#
# THAT IS NOT OBVIOUS AND IS WHY IT IS ASSERTED. A workspace may let some of
# `live/` back in -- `!live/cards/`, `!live/state.json`, `!live/turns.jsonl` --
# so the question "is a path under `live/` ignored" has a different answer in
# each workspace and none of them is "yes, by construction".
#
# GIT IS ASKED, and asked about a path that does not exist: `check-ignore`
# answers off the rules rather than off the filesystem, so this writes nothing
# into a workspace and can be run while a mission is going. Reading the ignore
# file and believing it is the mistake this whole file exists to avoid.
_TRAIL = os.path.join("live", "missions", "t0000.steps")
for _ws in sorted(os.listdir(HERE)) if HERE else []:
    _fam = os.path.join(HERE, _ws)
    if _ws.startswith(".") or not os.path.isdir(_fam):
        continue
    for _name in sorted(os.listdir(_fam)):
        _root = os.path.join(_fam, _name)
        if not os.path.isdir(os.path.join(_root, "live")):
            continue
        _rel = os.path.join(_ws, _name, _TRAIL)
        checked += 1
        if subprocess.run(["git", "check-ignore", "-q", _rel], cwd=HERE,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0:
            fail("GIT CAN SEE %s. That file is a mission's progress trail -- "
                 "the assistant's own sentences about work it did -- and one "
                 "commit from anywhere puts it in a public repository. `live/*` is what "
                 "keeps it out; something has let a path under `live/` back "
                 "in without narrowing it." % _rel)


# ---- A COURSE IS TRACKED CONTENT UNDER THE ROOT'S RULES ---------------------
#
# A course is a directory in Atlas like any project, so the root .gitignore is
# its whole ignore set: the assistant's `.claude/`,
# credentials and LaTeX droppings must be ignored inside one, and the owner's
# own write-ups must not be. Asked of git, on paths that do not exist, for the
# same reason as the trail above.
_COURSES = os.path.join(HERE, "courses")
_COURSE_IGNORED = (
    os.path.join(".claude", "settings.json"),
    "keys.env", ".env", "a.key",
    "x.aux", "x.synctex.gz", "x.pdf",
    os.path.join("textbook", "book.tex"),
    os.path.join("chapters", "ch01-x", "reading", "ch01.tex"),
    os.path.join("chapters", "ch01-x", "lectures", "deck.tex"),
    os.path.join("homework", "hw01", "assignment", "sheet.tex"))
_COURSE_KEPT = (
    os.path.join("chapters", "ch01-x", "homework", "ch01-homework.tex"),
    os.path.join("chapters", "ch01-x", "handwritten", "p1.png"),
    os.path.join("homework", "hw01", "hw01.tex"),
    "tutorboard.json")
for _c in sorted(os.listdir(_COURSES)) if os.path.isdir(_COURSES) else []:
    if _c.startswith(".") or not os.path.isdir(os.path.join(_COURSES, _c)):
        continue
    if os.path.exists(os.path.join(_COURSES, _c, ".git")):
        fail("courses/%s has a .git of its own. A course is plain content in "
             "Atlas; a nested repository hides it from every commit." % _c)
    for _p, _want in ([(p, True) for p in _COURSE_IGNORED]
                      + [(p, False) for p in _COURSE_KEPT]):
        checked += 1
        _rel = os.path.join("courses", _c, _p)
        _said = subprocess.run(["git", "check-ignore", "-q", "--no-index",
                                _rel], cwd=HERE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL).returncode == 0
        if _said != _want:
            fail("git %s %s. A course reads Atlas's root .gitignore and its "
                 "own, and that path should be %s."
                 % ("ignores" if _said else "can see", _rel,
                    "ignored" if _want else "trackable"))


# ---- A DOCUMENT'S FEEDBACK ROUNDS STAY ON DISK ------------------------------
#
# A round -- ink SVGs, crops, page renders, before/after copies, items.json,
# states.json, its ledger and its note -- is session detail. `ledger.py` reads
# it from disk, and the root .gitignore keeps it out of git. A tracked one
# fails, and so does a subject whose own .gitignore lets a round path back in,
# because a negation in a subject's file outranks the root's rule. Asked of
# git, on paths that do not exist.
ROUND = re.compile(r"(?:^|/)feedback/[^/]*[0-9]{4}-[0-9]{2}-[0-9]{2}-v[0-9]")
_rounds = [f for f in files if ROUND.search(f)]
if _rounds:
    fail("%d feedback-round file(s) are tracked, e.g. %s. Rounds stay on disk: "
         "untrack them in the main checkout with `git rm -r --cached`, and "
         "check each is still on disk." % (len(_rounds), ", ".join(_rounds[:3])))
else:
    ok("no feedback round is tracked")
_ROUND_PATHS = ("docs/feedback/x-2026-01-01-v1.md",
                "docs/feedback/x-2026-01-01-v1.ledger.json",
                "docs/feedback/x-2026-01-01-v1/items.json",
                "docs/feedback/x-2026-01-01-v1/states.json",
                "docs/feedback/x-2026-01-01-v1/R1.1.svg",
                "docs/talk/feedback/talk-2026-01-01-v2/after.tex",
                "chapters/ch01/feedback/notes-2026-01-01-v1.md")
_seen_rounds = 0
for _fam in ("courses", "projects"):
    _top = os.path.join(HERE, _fam)
    for _name in sorted(os.listdir(_top)) if os.path.isdir(_top) else []:
        if _name.startswith(".") or not os.path.isdir(os.path.join(_top, _name)):
            continue
        for _p in _ROUND_PATHS:
            checked += 1
            _seen_rounds += 1
            _rel = "/".join((_fam, _name, _p))
            if subprocess.run(["git", "check-ignore", "-q", "--no-index", _rel],
                              cwd=HERE, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode != 0:
                fail("GIT CAN SEE %s. A feedback round stays on disk; the root "
                     ".gitignore's feedback rule keeps it out, and something "
                     "(a negation in the subject's .gitignore?) lets it back "
                     "in." % _rel)
ok("%d feedback-round paths across every subject asked of git, and ignored"
   % _seen_rounds)


# ---- the audit's shape, on paths nobody has committed --------------------
#
# The scan above is over what Atlas tracks TODAY, which says nothing about a
# path that would be refused. These are the properties the rules are for.
_SHAPES = (
    ("courses/Galois-Theory/chapters/ch01-groups/lectures/Deck.pdf", True),
    ("courses/A-Course-Nobody-Has-Made-Yet/homework/hw01/assignment/sheet.docx", True),
    ("courses/X/chapters/ch01/homework/assignment-sheet/p.png", True),
    ("courses/X/textbook/a.pdf", True),
    ("projects/X/reading/ch01.txt", True),
    ("projects/X/references/paper.pdf", True),
    ("sessions/20261008-120000/session.json", True),
    ("projects/X/.ink/doc/a/p1.json", True),
    ("projects/X/materials/slides.pdf", True),
    ("x_session1.wav", True),
    ("projects/X/model.pkl", True),
    ("projects/X/keys.env", True),
    ("ai-config/policy/x.py", True),
    ("projects/TRD-EHR/notes/lectures.md", False),
    ("projects/X/src/assignment.py", False),
    ("board/tutorboard/sessions.py", False),
    ("projects/X/docs/talk/talk.tex", False))
_wrong = [p for p, refused in _SHAPES if bool(audit.problems(p)) is not refused]
_keep = "courses/Probability/chapters/ch01-introduction/lectures/.gitkeep"
if audit.other_peoples_work(_keep):
    _wrong.append(_keep)
if _wrong:
    fail("the audit is the wrong shape for: %s" % ", ".join(_wrong))
else:
    ok("the audit refuses other people's work, sessions, ink, materials, audio "
       "and artifact shapes, credentials and ai-config, and passes the owner's "
       "own files beside them")
if (audit.check(["big.bin"], size=lambda rel: 30 * 1024 * 1024)
        and not audit.check(["small.bin"], size=lambda rel: 1024)):
    ok("a 30 MB file is refused and a small one is not")
else:
    fail("the 25 MB cap does not hold")


# ---- a course's third-party shapes, forced past the ignore rules ------------
#
# `git add -f` walks past every ignore rule, so the audit is what stops a
# textbook or an assignment sheet. Both the commit-time gate and the scan of
# the index must refuse them, and pass the owner's write-up beside them.
_box = tempfile.mkdtemp(prefix="tutor-forced-")
try:
    git(_box, "init", "-q")
    shutil.copyfile(os.path.join(HERE, ".gitignore"),
                    os.path.join(_box, ".gitignore"))
    _forced = ("courses/X/textbook/a.pdf",
               "courses/X/chapters/ch01/homework/assignment-sheet/p.png")
    _own = "courses/X/chapters/ch01/homework/ch01-homework.tex"
    for _p in _forced + (_own,):
        put(os.path.join(_box, _p), "x\n")
    git(_box, "add", _own)
    if git(_box, "add", *_forced).returncode == 0:
        fail("the root .gitignore let a course textbook or assignment sheet "
             "be added without -f")
    git(_box, "add", "-f", *_forced)
    _gate = audit.gate(_box, _box, False)
    _miss = [p for p in _forced if not any(p in r for r in _gate)]
    if _miss or any(_own in r for r in _gate):
        fail("the commit-time gate did not refuse exactly the forced course "
             "shapes: %r" % _gate)
    else:
        ok("the commit-time gate refuses a forced textbook PDF and assignment "
           "sheet in a course, and passes the write-up beside them")
    git(_box, "commit", "-q", "--no-verify", "-m", "forced")
    _said = audit.check(git(_box, "ls-files").stdout.decode().split(), _box)
    if all(any(p in r for r in _said) for p in _forced) and \
            not any(_own in r for r in _said):
        ok("and once committed anyway, the index scan refuses both")
    else:
        fail("the index scan missed a forced course shape: %r" % _said)
finally:
    shutil.rmtree(_box, ignore_errors=True)


print()
if fails:
    print("%d tracked-file rule(s) broken, over %d files checked" % (len(fails), checked))
    sys.exit(1)
print("%d tracked files, and every one of them may be public" % checked)
