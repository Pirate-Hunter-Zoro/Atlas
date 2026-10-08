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
see any directory that must stay invisible. The second half of this file tests
the guards themselves, in temporary repositories.
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutorboard import atlas, audit, fenced, leaving          # noqa: E402


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


# ---- the directories that live inside the tree and must stay invisible -----
#
# A subject's phi/ and results/ belong with the subject, and a course's
# repository belongs where the course is, so these may be on disk here -- and
# git must not be able to see one byte of any of them. Found by discovery, so a
# new subject's phi/ is guarded the day it is made; none on disk is a fresh
# clone and is fine. Git is asked, rather than the ignore file believed.
_HELD = audit.held(HERE)
for held, what in _HELD:
    checked += 1
    said = audit.exposed(HERE, held, what)
    if said:
        fail(said)
_FOUND = [h for h, _ in _HELD if os.path.basename(h) in audit.HELD_NAMES]
if _FOUND:
    ok("%d phi/ or results/ directories found on disk by discovery, each one "
       "asked of git" % len(_FOUND))
else:
    ok("no phi/ or results/ directory on disk, so there is none to hide")

# Each course must carry its own `.git`: without one it is an orphan tree whose
# only protection is the ignore rule, and nothing pushes its work anywhere.
_COURSES = os.path.join(HERE, "courses")
for msg in audit.courses_without_git(HERE):
    fail(msg)

# ---- A MISSION'S PROGRESS TRAIL IS WORDS ABOUT FENCED WORK ----------------
#
# `progress.py` writes one file per mission under `live/missions/`, and what
# goes in it is the assistant's own sentences about what it just finished --
# written, in the one workspace that has a fence, by the one assistant allowed
# to read that fence. So it is exactly the kind of thing that must never become
# a tracked file, and it is not kept out by being small or by nobody thinking
# about it: `live/*` in every workspace excludes it.
#
# THAT IS NOT OBVIOUS AND IS WHY IT IS ASSERTED. A course lets some of `live/`
# back in -- `!live/cards/`, `!live/state.json`, `!live/turns.jsonl` -- so the
# question "is a path under `live/` ignored" has a different answer in each
# workspace and none of them is "yes, by construction".
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
        # A workspace with its own `.git` is asked in its own repository.
        # Asked from Atlas, `/courses/*/` ignores the whole course and the
        # answer is yes for every path, which tests nothing; the course's own
        # `live/*` rule is the one that decides whether its repository tracks
        # the trail.
        if os.path.exists(os.path.join(_root, ".git")):
            _ask, _where = _TRAIL, _root
        else:
            _ask, _where = _rel, HERE
        if subprocess.run(["git", "check-ignore", "-q", _ask], cwd=_where,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0:
            fail("GIT CAN SEE %s. That file is a mission's progress trail -- "
                 "the assistant's own sentences about work it did, written in "
                 "a workspace that may hold session content -- and one commit "
                 "from anywhere puts it in a repository. `live/*` is what "
                 "keeps it out; something has let a path under `live/` back "
                 "in without narrowing it." % _rel)


# ---- A COURSE REPOSITORY CARRIES ITS OWN IGNORE RULES -----------------------
#
# A nested repository never reads Atlas's root `.gitignore`. So every generic
# rule Atlas relies on -- relay state, NFS litter, the assistant's own
# `.claude/`, credentials, LaTeX droppings -- has to be in each course's own
# `.gitignore`, or the first save in that course commits it. Asked of git, on
# paths that do not exist, for the same reason as the trail above.
_COURSE_IGNORED = (
    os.path.join("relay", "state", "x.exit"),
    ".nfs0001",
    os.path.join(".claude", "settings.json"),
    "keys.env", ".env", "a.key",
    "x.aux", "x.synctex.gz")
for _c in sorted(os.listdir(_COURSES)) if os.path.isdir(_COURSES) else []:
    _croot = os.path.join(_COURSES, _c)
    if not os.path.exists(os.path.join(_croot, ".git")):
        continue                       # refused above, as an orphan tree
    for _p in _COURSE_IGNORED:
        checked += 1
        if subprocess.run(["git", "-C", _croot, "check-ignore", "-q", _p],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0:
            fail("courses/%s's own git can see %s. A course repository reads "
                 "only its own .gitignore, never Atlas's, so that rule has to "
                 "be in courses/%s/.gitignore." % (_c, _p, _c))


# ---------------------------------------------------------------------------
# AND THE SAME FAILURE ONE STEP EARLIER: SESSION CONTENT IN A DIFF
# ---------------------------------------------------------------------------
# Everything above is about a FILE. An ignore rule keeps the fenced directory
# out of the index and the checks above audit every tracked path, so a file
# cannot get out. CONTENT can: a test fixture cut out of a transcript, an
# example hard-coded from one, a docstring quoting a span -- written by the one
# assistant allowed to read that directory and pushed by a turn that is not.
#
# That matters now because a push here is unattended. `board finish` raises the
# offer, the tutor may push on its own, and a mission can be told to ship
# itself. `ai-config/policy/phi.py` is the lab's own rule, owned by the lab
# rather than by this tool, and `tutorboard/leaving.py` is the first thing that
# ever called it.
#
# A TEMPORARY TREE, unlike every check above, and for one reason: what is being
# checked is the guard's own behaviour, and the last thing this file may do is
# leave a fixture naming session content inside the real repository.
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
    ("ai-config/policy/phi.py", True),
    ("research/TRD-EHR/notes/lectures.md", False),
    ("projects/X/src/assignment.py", False),
    ("board/tutorboard/sessions.py", False),
    ("projects/X/docs/meeting/meeting.tex", False))
_wrong = [p for p, refused in _SHAPES if bool(audit.problems(p)) is not refused]
_keep = "courses/Probability/chapters/ch01-introduction/lectures/.gitkeep"
if audit.other_peoples_work(_keep):
    _wrong.append(_keep)
if _wrong:
    fail("the audit is the wrong shape for: %s" % ", ".join(_wrong))
else:
    ok("the audit refuses other people's work, sessions, ink, materials, PHI "
       "and artifact shapes, credentials and ai-config, and passes the owner's "
       "own files beside them")
if (audit.check(["big.bin"], size=lambda rel: 30 * 1024 * 1024)
        and not audit.check(["small.bin"], size=lambda rel: 1024)):
    ok("a 30 MB file is refused and a small one is not")
else:
    fail("the 25 MB cap does not hold")


# ---- discovery finds a held directory, and git seeing it is a failure -------
_box = tempfile.mkdtemp(prefix="tutor-held-")
try:
    git(_box, "init", "-q")
    for _d in ("projects/X/phi", "projects/X/a/b/results",
               "research/Y/data/phi", "projects/X/a/b/c/phi",
               "research/Y/exports/results"):
        os.makedirs(os.path.join(_box, _d))
        put(os.path.join(_box, _d, "f.txt"), "x\n")
    _found = [h for h, _ in audit.held(_box)]
    if _found == ["projects/X/a/b/results", "projects/X/phi"]:
        ok("discovery finds phi/ and results/ up to three levels under a "
           "subject, and never walks into a fenced directory or exports/")
    else:
        fail("discovery found %r" % _found)
    if audit.exposed(_box, "projects/X/phi", "test"):
        ok("a projects/X/phi that git can see is a failure")
    else:
        fail("a projects/X/phi that git can see was not caught")
    put(os.path.join(_box, ".gitignore"), "phi/\nresults/\n")
    if not any(audit.exposed(_box, h, w) for h, w in audit.held(_box)):
        ok("and once ignored, git is blind to it and the check passes")
    else:
        fail("an ignored phi/ was still reported as visible")
finally:
    shutil.rmtree(_box, ignore_errors=True)


FENCE = "phi"
SHAPE = ".rttm"
OLD_TREE = "data/stage1"

tmp = tempfile.mkdtemp(prefix="tutor-leaving-")
was = os.environ.get("TUTORBOARD_COURSES")
try:
    put(os.path.join(tmp, "atlas.json"),
        '{"families": [{"id": "research", "name": "Research"}, '
        '{"id": "courses", "name": "Courses"}]}')
    psych = os.path.join(tmp, "research", "PSYCH-ASR")
    galois = os.path.join(tmp, "courses", "Galois-Theory")
    for r in (psych, galois):
        put(os.path.join(r, "tutorboard.json"), "{}\n")
    # The fence is a DIRECTORY THAT EXISTS: `fenced.holds` is a listing, because
    # whether a workspace has one is a fact about what is on disk.
    os.makedirs(os.path.join(psych, FENCE), exist_ok=True)
    # The policy itself, copied rather than stubbed. Part of what is checked
    # here is that it is loaded out of the repository by path; a stub would be
    # testing the test.
    if HERE and os.path.isfile(os.path.join(HERE, leaving.POLICY)):
        os.makedirs(os.path.join(tmp, os.path.dirname(leaving.POLICY)),
                    exist_ok=True)
        shutil.copyfile(os.path.join(HERE, leaving.POLICY),
                        os.path.join(tmp, leaving.POLICY))
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=t@t", "-c", "user.name=t",
                  "commit", "-q", "-m", "start"]):
        subprocess.run(["git"] + args, cwd=tmp, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    os.environ["TUTORBOARD_COURSES"] = tmp
    atlas.forget()
    fenced.forget()
    leaving._POLICY["root"] = None

    if leaving.policy(tmp):
        ok("the rule comes out of the repository's own policy file, not a copy")
    else:
        fail("the repository's own policy could not be loaded, so nothing is "
             "checking a diff. ai-config/policy/phi.py is the rule.")

    if leaving.reason(psych, tmp) is None:
        ok("a clean tree is not refused")
    else:
        fail("a clean tree was refused a push")

    # THE CASE THIS EXISTS FOR. A fixture written by the assistant that could
    # read the directory it came out of, never tracked -- so no `git diff` sees
    # it at all and only `--untracked-files=all` finds it.
    fixture = os.path.join(psych, "tests", "fixtures", "turns.py")
    put(fixture,
        "# cut out of %s/session_03%s while checking the aligner\n"
        'SPAN = "SPEAKER session_03 1 12.40 3.10 spk_1"\n' % (FENCE, SHAPE))
    said = leaving.reason(psych, tmp) or ""
    if not said:
        fail("A FIXTURE REACHING FOR SESSION CONTENT WAS NOT REFUSED. That "
             "diff would have gone to a public remote with nobody watching.")
    elif "research/PSYCH-ASR/tests/fixtures/turns.py" not in said:
        fail("the refusal does not name the file: %s" % said[:200])
    else:
        ok("a fixture reaching for session content is refused, by name")

    # And the same words in a workspace that holds no fence are PROSE ABOUT a
    # fence rather than a hole in one. Checking everything was the alternative
    # and it is wrong in this direction: this repository's own documentation
    # names the fenced directory on nearly every page, including this file.
    os.remove(fixture)
    put(os.path.join(galois, "notes.md"),
        "The fence matches %s/ by name, at any depth.\n" % FENCE)
    if leaving.reason(galois, tmp) is None:
        ok("and a workspace with no fence is not, because prose about a fence "
           "is not a hole in one")
    else:
        fail("a workspace with no fence was refused for naming one in prose")

    # A TRACKED file, whose ADDED lines reach for it. What was already committed
    # is not read again; this is about the line that is new.
    put(os.path.join(psych, "notes.md"), "nothing here yet\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "notes"], cwd=tmp,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if leaving.reason(psych, tmp) is not None:
        fail("a committed tree was refused a push")
    put(os.path.join(psych, "notes.md"),
        "nothing here yet\nthe joined turns are under %s\n" % OLD_TREE)
    said = leaving.reason(psych, tmp) or ""
    if "research/PSYCH-ASR/notes.md" in said:
        ok("and a line added to a tracked file in there is refused the same way")
    else:
        fail("an added line naming the old data tree was not refused: %s"
             % said[:200])

    # A fence with no policy is refused loudly: a guard that switches itself
    # off when its rule goes missing is a guard nobody can trust.
    os.remove(os.path.join(tmp, leaving.POLICY))
    leaving._POLICY["root"] = None
    said = leaving.reason(psych, tmp)
    hit = leaving.refused(psych, ["research/PSYCH-ASR/notes.md"], tmp)
    if isinstance(said, str) and leaving.POLICY in said and isinstance(hit, str):
        ok("a fence with no policy file is refused, by name, by both reason "
           "and refused")
    else:
        fail("a fence with no policy was not refused: %r, %r" % (said, hit))

    # And a repository with no fence anywhere has nothing to guard.
    os.rmdir(os.path.join(psych, FENCE))
    fenced.forget()
    if leaving.reason(psych, tmp) is None and leaving.refused(psych, [], tmp) == []:
        ok("with no fence anywhere, a missing policy refuses nothing")
    else:
        fail("a tree with no fence was refused for having no policy")
finally:
    if was is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = was
    atlas.forget()
    fenced.forget()
    leaving._POLICY["root"] = None
    shutil.rmtree(tmp, ignore_errors=True)

# AND BOTH PUSHES MAKE THE CHECK. There are two of them -- the command line,
# which a tutor turn and a ship run, and the save button, which is a person
# tapping -- and a guard on one of them is a guard on neither.
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for what, rel in (("board push", os.path.join("bin", "board")),
                  ("the save button",
                   os.path.join("tutorboard", "lesson", "git.py"))):
    try:
        with open(os.path.join(TOOL, rel), encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        src = ""
    if "leaving.reason(" in src:
        ok("%s runs what it is about to commit past the rule first" % what)
    else:
        fail("%s pushes without checking the diff for session content" % what)


print()
if fails:
    print("%d tracked-file rule(s) broken, over %d files checked" % (len(fails), checked))
    sys.exit(1)
print("%d tracked files, and every one of them may be public" % checked)
