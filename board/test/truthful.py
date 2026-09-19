#!/usr/bin/env python3
"""A document that names a path is checked against the tree it names.

`tracked.py` audits what git carries and `teaching.py` audits where a rule is
written down. Neither reads a claim about the code and then goes and checks it,
which is why a fleet reading every document by hand found over a hundred false
sentences in one afternoon and nothing in the suite had ever flinched.

Most of them were one class. A workspace moved into this repository and its
documents went on naming the place it used to be: `~/Tutor-Board`, `~/colibri`,
`~/PSYCH-ASR`. That class is mechanical -- a retired address is a fixed string,
and a document containing one is wrong however the sentence around it reads --
so it is checked here rather than remembered.

The other class is a number that lives in two places. A count of suites, of
tests, of families: each has one true value in the code and a copy in prose,
and the copy is what goes stale. Every number in here is re-derived and
compared, so the document cannot drift without the suite saying so.

This file makes no claim about prose that is merely out of date. It checks the
two things a machine can check, and the rest stays a job for a reader.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOL)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)
        if detail:
            for line in str(detail).splitlines():
                print("       " + line)


def tracked_markdown():
    out = subprocess.run(
        ["git", "-C", ROOT, "ls-files", "*.md"],
        capture_output=True, text=True, check=True).stdout
    for rel in out.split("\n"):
        if not rel or rel.startswith("vendor/"):
            continue
        # A lesson card is a transcript of something somebody said at the time.
        # It is a record, not a description of the code, so it is not audited.
        if "/live/" in rel or rel.startswith("live/"):
            continue
        path = os.path.join(ROOT, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                yield rel, fh.read()
        except (OSError, UnicodeDecodeError):
            continue


# ---- 1. Addresses that no longer exist -------------------------------------
#
# Each of these was a clone in $HOME before this tree became one repository.
# The value is where the thing actually is, and it goes in the failure line so
# nobody has to go and look it up.
RETIRED = {
    "~/Tutor-Board": "board/",
    "~/colibri-build": "vendor/colibri-build",
    "~/colibri": "vendor/colibri",
    "~/PSYCH-ASR": "research/PSYCH-ASR",
    "~/TRD-EHR": "research/TRD-EHR",
    "~/libr-local-llm": "projects/libr-local-llm",
    "~/Paper-Writer": "projects/Paper-Writer",
    "~/Research-Journey": "research/PSYCH-ASR/docs",
    "~/Galois-Theory": "courses/Galois-Theory",
    "~/Probability": "courses/Probability",
    "~/.config/tutor-board/courses.txt": "nothing -- workspaces are discovered",
}

found = []
for rel, text in tracked_markdown():
    for old, now in RETIRED.items():
        for n, line in enumerate(text.split("\n"), 1):
            if old not in line:
                continue
            # A sentence saying a path is gone has to be able to name it.
            if re.search(r"\b(used to|no longer|was at|it is (?:not|now)|moved|"
                         r"does not exist|never|retired|stale)\b", line, re.I):
                continue
            found.append("%s:%d  %s -> %s" % (rel, n, old, now))

check("no document names a directory that moved into this repository",
      not found, "\n".join(found[:40]))


# ---- 2. Counts that exist twice --------------------------------------------

def suites_in(script):
    """How many rows `all.sh` actually prints: the loop plus the singles."""
    with open(script, encoding="utf-8") as fh:
        text = fh.read()
    loop = re.search(r'^SUITES="([^"]+)"', text, re.M)
    n = len(loop.group(1).split()) if loop else 0
    # Every other row is its own `printf '%-12s '` with a literal name. The
    # loop's own `"$t"` is not one of them -- it is the rows already counted.
    n += len([m for m in re.findall(r"printf '%-12s ' \"([^\"]+)\"", text)
              if m != "$t"])
    return n


real_suites = suites_in(os.path.join(TOOL, "test", "all.sh"))
claimed = []
for rel, text in tracked_markdown():
    for n, line in enumerate(text.split("\n"), 1):
        m = re.search(r"\b(\d+)\s+suites\b", line)
        if m and int(m.group(1)) != real_suites:
            claimed.append("%s:%d  says %s, all.sh runs %d"
                           % (rel, n, m.group(1), real_suites))
check("every document that counts the suites counts %d of them" % real_suites,
      not claimed, "\n".join(claimed))


def factory_tests():
    """Paper-Writer's own count, taken from Paper-Writer."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=os.path.join(ROOT, "projects", "Paper-Writer"),
        capture_output=True, text=True)
    m = re.search(r"Ran (\d+) tests", proc.stderr)
    return int(m.group(1)) if m else None


real_factory = factory_tests()
stale = []
if real_factory:
    for rel, text in tracked_markdown():
        for n, line in enumerate(text.split("\n"), 1):
            m = re.search(r"Paper-Writer's (\d+) tests", line)
            if m and int(m.group(1)) != real_factory:
                stale.append("%s:%d  says %s, the suite runs %d"
                             % (rel, n, m.group(1), real_factory))
check("every document that counts Paper-Writer's tests counts %s of them"
      % real_factory, real_factory and not stale, "\n".join(stale))


with open(os.path.join(ROOT, "atlas.json"), encoding="utf-8") as fh:
    families = len(json.load(fh)["families"])
WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
miscount = []
for rel, text in tracked_markdown():
    for n, line in enumerate(text.split("\n"), 1):
        m = re.search(r"\b(\w+)\s+famil(?:y|ies)\b", line, re.I)
        if not m:
            continue
        word = m.group(1).lower()
        said = WORDS.get(word, int(word) if word.isdigit() else None)
        if said is not None and said != families:
            miscount.append("%s:%d  says %s, atlas.json names %d"
                            % (rel, n, m.group(1), families))
check("every document that counts the families counts %d of them" % families,
      not miscount, "\n".join(miscount))


# ---- What is deliberately NOT checked here ---------------------------------
#
# Whether every source file a document names exists. It was written, it fired
# three times, and all three sentences were TRUE: `board/README.md` names a
# course's `scripts/build.sh` while sitting in the board's own directory, and
# PSYCH-ASR names `slurm_jobs/stage1_whisperx.sbatch` in the paragraph saying
# it was deleted. A check that cannot tell our module from somebody else's
# library, or a live path from an obituary, reports true sentences as false --
# and an auditor nobody believes is worse than no auditor, because the next
# person silences it rather than reading it. Reading a document for that class
# is still a reader's job.

print()
print("%d FAILURES" % len(fails) if fails
      else "every document is checked against the tree it describes")
sys.exit(1 if fails else 0)
