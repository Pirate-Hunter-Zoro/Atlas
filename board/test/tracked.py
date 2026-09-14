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
             "at ~/phi/PSYCH-ASR/ -- outside every repository. Nothing of that "
             "shape may be tracked anywhere in here." % rel)

    # A participant identifier in a tracked filename, which is how the audio
    # was named: a two-or-three letter prefix and a number, then `_session`.
    if "_session" in base and any(c.isdigit() for c in base):
        fail("%s looks like a session file named after a participant. If it is "
             "not, rename it; if it is, it belongs at ~/phi/." % rel)

    # ---- no regenerable artifacts ----------------------------------------
    if low.endswith(ARTIFACT_SUFFIXES):
        fail("%s is a model dump or a serialized result. It is output of a job "
             "that can be run again, so it lives at ~/artifacts/ and the "
             "workspace README names the path. The figures and tables derived "
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
    if base == ".env":
        fail("%s is a .env. TRD-EHR's enumerated the on-disk locations of "
             "identifiable patient data, which is exactly what a public "
             "repository must not publish. Track a .env.example with the keys "
             "and no values instead." % rel)


# ---- the two directories that must not exist inside the tree at all -------
# Not "must not be tracked" -- must not BE here. A `.gitignore` entry is a
# guard somebody can delete by accident, and the failure it guards against is
# 308 MB of therapy audio inside a repository that is about to be pushed.
for gone, what, where in (
        ("research/PSYCH-ASR/data", "308 MB of identifiable therapy session audio",
         "~/phi/PSYCH-ASR/"),
        ("research/TRD-EHR/results", "1.5 GB of regenerable job output",
         "~/artifacts/TRD-EHR/results/")):
    checked += 1
    path = os.path.join(HERE, gone)
    if os.path.islink(path):
        fail("%s is a SYMLINK. A symlink is a tracked file pointing at the "
             "thing it is standing in for, which hands the next reader of this "
             "repository a map straight to it. The pipeline takes a path; give "
             "it the real one, and name it in the workspace README." % gone)
    elif os.path.isdir(path):
        fail("%s exists inside the repository. It is %s and it belongs at %s. "
             "An ignore rule is not a good enough guard for this one."
             % (gone, what, where))


print()
if fails:
    print("%d tracked-file rule(s) broken, over %d files checked" % (len(fails), checked))
    sys.exit(1)
print("%d tracked files, and every one of them may be public" % checked)
