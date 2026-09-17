#!/usr/bin/env python3
"""What this repository is allowed to carry.

    python3 test/tracked.py

This repository is PUBLIC, and the rule it is built on is one sentence:

    If it cannot go into a public repository, it does not live in the
    repository. It lives outside the tree and something inside the tree says
    where.

That rule is worth nothing written down. Written down, it is obeyed for about
three weeks and then somebody runs `git add -A` in a directory they have not
looked in, and a 308 MB therapy recording, or a model dump, or another author's
book goes to GitHub -- where deleting it afterwards is not a fix, because it
was public for a while and git remembers.

So it is a test, and it runs in `test/all.sh` with everything else. A rule
nobody can break by accident beats a rule written down.

Every check below is a NUMBER rather than an opinion, and each one is here
because the thing it checks for was actually found in one of the eleven
repositories this one was made from.
"""

import os
import subprocess
import sys


# The whole REPOSITORY, not the tool. This test lives in the board's own
# test directory because that is where `test/all.sh` runs from, but what it
# guards is every file in Atlas -- the courses, the research, the vendor
# pointers. Asked of git rather than derived by counting `..`, so it is still
# right if the board is ever vendored somewhere deeper.
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


# GitHub refuses any file over 100 MB and warns above 50. This is far under
# both on purpose: the limit that matters is the one that stops a habit, not
# the one that stops a push. The largest legitimate tracked file in here is a
# manuscript at 3.5 MB.
MAX_BYTES = 25 * 1024 * 1024

# PHI, by the shape of the filename. The same shapes `block-phi.py` fences, for
# the same reason: PSYCH-ASR's session recordings are identifiable, and the
# filenames themselves carry participant IDs.
PHI_SUFFIXES = (".m4a", ".wav", ".mp3", ".flac", ".mp4", ".mov",
                ".rttm", ".srt", ".vtt")

# Job output that a command regenerates, and that nobody reads. `results/` is
# 1.5 GB of it in TRD-EHR alone.
ARTIFACT_SUFFIXES = (".joblib", ".pkl", ".pickle", ".ckpt", ".pt", ".pth",
                     ".safetensors", ".gguf", ".h5", ".parquet")

# Other people's published work. The INDEXES of a citation library are tracked
# -- README.md, CITATION_MAP.md, the role-grouped manifests -- so a clone
# arrives with the bibliography described but not carried. The PDFs are not.
def other_peoples_work(rel):
    parts = rel.lower().split("/")
    if "references" in parts and rel.lower().endswith(".pdf"):
        return "a reference library PDF"
    if "textbook" in parts and rel.lower().endswith(".pdf"):
        return "a set textbook"
    # `scripts/split-textbook.sh` cuts the book into chapters/chNN-slug/reading/
    # and says of its own output "they are derived artifacts and git-ignored".
    if "reading" in parts and os.path.basename(rel).lower().startswith("ch"):
        if rel.lower().endswith((".pdf", ".txt")):
            return "an excerpt cut out of a set textbook"
    return None


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

for rel in files:
    checked += 1
    low = rel.lower()
    base = os.path.basename(low)
    full = os.path.join(HERE, rel)

    # ---- nothing enormous -------------------------------------------------
    try:
        size = os.path.getsize(full)
    except OSError:
        size = 0            # deleted in the working tree; the index is the test
    if size > MAX_BYTES:
        fail("%s is %d MB. Nothing tracked here may be over %d MB -- a file "
             "that big is output, and output lives outside the tree with a "
             "path to it in the workspace README."
             % (rel, size // (1024 * 1024), MAX_BYTES // (1024 * 1024)))

    # ---- no PHI, by filename shape ---------------------------------------
    if low.endswith(PHI_SUFFIXES):
        fail("%s is audio or a transcript artifact. PSYCH-ASR's session data is "
             "identifiable, its filenames carry participant IDs, and it lives "
             "in `research/PSYCH-ASR/phi/`, which git is blind to. Nothing of "
             "that shape may be TRACKED anywhere in here." % rel)

    # A participant identifier in a tracked filename, which is how the audio
    # was named: a two-or-three letter prefix and a number, then `_session`.
    if "_session" in base and any(c.isdigit() for c in base):
        fail("%s looks like a session file named after a participant. If it is "
             "not, rename it; if it is, it belongs in `research/PSYCH-ASR/phi/`." % rel)

    # ---- no regenerable artifacts ----------------------------------------
    if low.endswith(ARTIFACT_SUFFIXES):
        fail("%s is a model dump or a serialized result. It is output of a job "
             "that can be run again, so it lives in its workspace's own ignored "
             "`results/`, which the README explains. The figures and tables derived "
             "from it are small, and THOSE are tracked." % rel)

    # ---- no build directories --------------------------------------------
    if "/.lake/" in "/" + low or low.startswith(".lake/"):
        fail("%s is inside Lean's .lake/ -- 14 GB of compiled Mathlib that "
             "`lake build` recreates. It never leaves the machine." % rel)
    if "/node_modules/" in "/" + low:
        fail("%s is inside node_modules/." % rel)
    if "__pycache__" in low or low.endswith(".pyc"):
        fail("%s is a compiled Python cache." % rel)

    # ---- no other people's papers or books -------------------------------
    what = other_peoples_work(rel)
    if what:
        fail("%s is %s. Somebody else wrote it and this repository is public. "
             "It stays on disk and out of git; what the person wrote ABOUT it "
             "is tracked." % (rel, what))

    # ---- no machine-local configuration ----------------------------------
    if base in ("settings.local.json", "settings.local.json.bak"):
        fail("%s is this machine's own permission allowlist. It names real "
             "paths on lab storage and it is not the same on two machines. "
             "`.claude/settings.json` is the shared one and is tracked." % rel)
    # ---- no assistant configuration --------------------------------------
    # `ai-config/` sits INSIDE this tree and is tracked by its own git. The
    # only thing keeping it out of this one is a `/ai-config/` line in the root
    # `.gitignore`, which is exactly the kind of guard this file exists because
    # somebody deletes by accident. What it holds names real paths on lab
    # storage and describes what the PHI fence is guarding, so it is private
    # for the same reason TRD-EHR's `.env` had to go.
    if low.startswith("ai-config/"):
        fail("%s is the assistant configuration. It lives inside this tree and "
             "is tracked by its OWN git -- `ai-config/README.md` says how. Its "
             "settings name real paths on lab storage and its policy describes "
             "what the PHI fence guards, so this public repository carries none "
             "of it. Something has removed `/ai-config/` from the root "
             ".gitignore; put it back." % rel)

    if base == ".env":
        fail("%s is a .env. TRD-EHR's enumerated the on-disk locations of "
             "identifiable patient data, which is exactly what a public "
             "repository must not publish. Track a .env.example with the keys "
             "and no values instead." % rel)


# ---- the two directories that live inside the tree and must stay invisible -
#
# THESE USED TO BE FORBIDDEN HERE and they are not any more. Until 14 September
# 2026 this block failed if either directory existed at all, on the reasoning
# that an ignore rule is a guard somebody deletes by accident. The owner
# decided the other way -- a project's data belongs with the project -- so the
# rule changed shape rather than being dropped: they may be here, and git must
# not be able to see one byte of either.
#
# Which turns a guard that was an assertion about the filesystem into one that
# asks GIT ITSELF the question. `git status --porcelain --untracked-files=all`
# over the directory is the whole test: it lists every file git would offer to
# add, ignored ones excluded, so an empty answer is git saying it is blind to
# the tree. That is stronger than reading `.gitignore` and believing it -- the
# pattern that once swallowed `psych_asr/artifacts/` was in the file and read
# perfectly well, and only asking git would have caught it.
#
# It is also the only check in here that fails BEFORE anything is committed
# rather than after, which for 308 MB of identifiable therapy audio in a public
# repository is the difference that matters. A thing that is public for an hour
# has been published.
for held, what in (
        ("research/PSYCH-ASR/phi", "308 MB of identifiable therapy session audio"),
        ("research/TRD-EHR/results", "1.5 GB of regenerable job output")):
    checked += 1
    path = os.path.join(HERE, held)
    if os.path.islink(path):
        fail("%s is a SYMLINK. Whatever it points at, a symlink is a tracked "
             "file standing in for it, and it hands the next reader of this "
             "public repository a map straight to the real thing. It was a "
             "real directory; put it back." % held)
        continue
    if not os.path.isdir(path):
        # Not an error. A fresh clone has neither -- one is PHI that never
        # leaves this machine and the other regenerates from a job -- and the
        # workspace README of each says where it comes from.
        continue
    seen = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", held],
        cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    listed = [l for l in seen.stdout.decode("utf-8", "replace").split("\n") if l.strip()]
    if seen.returncode != 0:
        fail("could not ask git whether it can see %s." % held)
    elif listed:
        fail("GIT CAN SEE %s -- %d path(s), starting %s. It is %s and it sits "
             "inside a public repository, so the ignore rule is the only thing "
             "between it and a push. Something has broken that rule. Do not "
             "commit anything until `git status --porcelain "
             "--untracked-files=all -- %s` is empty."
             % (held, len(listed), listed[0].strip()[:80], what, held))


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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil                                                # noqa: E402
import tempfile                                              # noqa: E402

from tutorboard import atlas, fenced, leaving                 # noqa: E402


def ok(msg):
    print("ok   " + msg)


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


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

    # A repository with no policy promises nothing, and this must not invent one.
    os.remove(os.path.join(tmp, leaving.POLICY))
    leaving._POLICY["root"] = None
    if leaving.reason(psych, tmp) is None:
        ok("a repository with no policy file refuses nothing, rather than "
           "deciding for itself what session content is")
    else:
        fail("a tree with no policy was refused by a rule from somewhere else")
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
