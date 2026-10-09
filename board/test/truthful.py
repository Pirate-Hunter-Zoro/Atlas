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

This file makes no claim about prose that is merely out of date. It checks the
things a machine can check, and the rest stays a job for a reader.
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


# Every tracked path matching `pattern`, relative to ROOT. Every course is
# Atlas's own content, so Atlas's index is the whole of it.
def ls_files(pattern):
    out = subprocess.run(
        ["git", "-C", ROOT, "ls-files", pattern],
        capture_output=True, text=True, check=True).stdout
    return [rel for rel in out.split("\n") if rel]


def tracked_markdown():
    for rel in ls_files("*.md"):
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
    "~/PSYCH-ASR": "projects/PSYCH-ASR",
    "~/TRD-EHR": "projects/TRD-EHR",
    "~/libr-local-llm": "projects/libr-local-llm",
    "~/Paper-Writer": "projects/Paper-Writer",
    "~/Research-Journey": "projects/PSYCH-ASR/docs",
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


# ---- 2. A setting a document describes and the code does not read ----------
#
# `mode` is the case this is written from and it is the shape of the class: a
# key sat in seven `tutorboard.json` files and in seven contracts saying what
# the board did about it, and `read_config` pops it and reads nothing. A
# document describing a switch that does nothing is worse than one describing
# nothing, because an assistant obeys it -- four of those contracts told one to
# expect three signal buttons that are not on the page.
#
# Both halves are checked: the key is not in a config, and no document writes
# it as a setting. A sentence that NAMES the key while saying it is dropped is
# fine -- the pattern here is the JSON spelling, which is a document asserting
# the file contains it.
DEAD_KEYS = ("mode",)

carried = []
for rel in ls_files("*tutorboard.json"):
    if not rel or "/live/" in rel:
        continue
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            said = json.load(fh)
    except (OSError, ValueError):
        continue
    for key in DEAD_KEYS:
        if isinstance(said, dict) and key in said:
            carried.append("%s carries `%s`" % (rel, key))

for rel, text in tracked_markdown():
    for n, line in enumerate(text.split("\n"), 1):
        for key in DEAD_KEYS:
            if re.search(r'"%s"\s*:\s*"' % key, line):
                carried.append("%s:%d writes `%s` as a setting" % (rel, n, key))

check("no config and no document carries a key the board drops on read",
      not carried, "\n".join(carried))


# ---- 3. The core documents' links and anchors resolve ----------------------
#
# The three documents an assistant reads first. A relative link names a file
# that exists, and a `#fragment` names a heading in it, spelled the way GitHub
# slugs headings. Fenced blocks and inline code are not links. The subject
# documents are left out: a manuscript links figures that live only on the
# cluster, under its ignored `results/`.
CORE = ("README.md", "board/README.md", "board/TEACHING.md")

FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def prose_lines(text):
    """The document's lines, with every fenced line blanked."""
    out, fenced = [], False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return out


def slug(heading):
    """The anchor GitHub gives a heading."""
    heading = heading.replace("`", "").strip().lower()
    return re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")


def anchors(path):
    seen, out = {}, set()
    with open(path, encoding="utf-8") as fh:
        lines = prose_lines(fh.read())
    for line in lines:
        m = HEADING_RE.match(line)
        if not m:
            continue
        s = slug(m.group(1))
        n = seen.get(s, 0)
        seen[s] = n + 1
        out.add(s if n == 0 else "%s-%d" % (s, n))
    return out


def core_texts():
    for rel in CORE:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            yield rel, fh.read()


broken, links = [], 0
for rel, text in core_texts():
    here = os.path.dirname(os.path.join(ROOT, rel))
    for n, line in enumerate(prose_lines(text), 1):
        for m in LINK_RE.finditer(re.sub(r"`[^`]*`", "", line)):
            target = m.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            links += 1
            path, _, frag = target.partition("#")
            dest = (os.path.normpath(os.path.join(here, path)) if path
                    else os.path.join(ROOT, rel))
            if not os.path.exists(dest):
                broken.append("%s:%d  %s: no such file" % (rel, n, target))
            elif frag and dest.endswith(".md") and frag.lower() not in anchors(dest):
                broken.append("%s:%d  %s: no such heading" % (rel, n, target))

check("every relative link and anchor in the core documents resolves (%d links)"
      % links, links and not broken, "\n".join(broken))


# ---- 4. Every `board` command the core documents name exists ---------------
#
# Read off `COMMANDS` in bin/board as text, so this suite imports no CLI. A
# command in `GONE` is refused by the CLI, so naming it is as wrong as naming
# one that never was.
with open(os.path.join(TOOL, "bin", "board"), encoding="utf-8") as fh:
    cli = fh.read()
table = cli[cli.index("\nCOMMANDS = {"):]
table = table[:table.index("\n}\n")]
commands = set(re.findall(r'"([a-z][a-z-]*)":\s*cmd_', table))
# `board help` is answered by `main` before the table is read.
commands.add("help")

unknown = []
for rel, text in core_texts():
    for n, line in enumerate(text.split("\n"), 1):
        for name in re.findall(r"`board ([a-z][a-z-]*)", line):
            if name not in commands:
                unknown.append("%s:%d  board %s" % (rel, n, name))

check("every `board` command the core documents name is in COMMANDS (%d commands)"
      % len(commands), len(commands) >= 20 and not unknown, "\n".join(unknown))


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
