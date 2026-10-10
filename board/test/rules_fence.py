#!/usr/bin/env python3
"""PSYCH-ASR's committed RULES.md reaches a bound session's brief with its
data-fence rule.

Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = os.path.dirname(ROOT)
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


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-fence-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = os.path.realpath(
    tempfile.mkdtemp(prefix="tutor-fence-trash-"))
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)

from tutorboard import brief, sense, sessions                        # noqa: E402

try:
    real = os.path.join(ATLAS, "projects", "PSYCH-ASR", "RULES.md")
    psych = os.path.join(base, "projects", "PSYCH-ASR")
    write(os.path.join(psych, "tutorboard.json"),
          json.dumps({"name": "PSYCH-ASR", "phi": True}))
    shutil.copy(real, os.path.join(psych, "RULES.md"))
    write(os.path.join(base, ".gitignore"), "/sessions/\n")
    for argv in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                  "-m", "fixture"]):
        subprocess.run(["git", "-C", base] + argv, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sid = sessions.new(base=base)["id"]
    sessions.bind(sid, "projects/PSYCH-ASR", base=base)
    said = brief.briefing(sessions.repo(sid, base, create=True), sense)
    check("PSYCH-ASR's brief carries its data-fence rule from HEAD",
          "Never read anything under phi/" in said
          and "LOCAL-MODELS.md" in said, said[-1500:])
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(os.environ["TUTORBOARD_TRASH"], ignore_errors=True)

print("\n%d failure(s)" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
