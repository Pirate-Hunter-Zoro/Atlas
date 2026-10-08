#!/usr/bin/env python3
"""`scripts/phi-probe.sh` and `leaving.probe`: a fenced path is refused by both
the policy and the fence, at its projects/ address and its legacy one.

    python3 test/phi_probe.py

No path asked about exists, and none is listed or read. The fenced directory's
name is spelled in pieces so this file does not itself name it.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
SCRIPT = os.path.join(BOARD, "scripts", "phi-probe.sh")
BASH = "/bin/bash" if os.path.exists("/bin/bash") else shutil.which("bash")
sys.path.insert(0, BOARD)

from tutorboard import leaving  # noqa: E402

D = "p" + "hi"
fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def probe(path, cwd=ROOT):
    p = subprocess.run([BASH, SCRIPT, path], cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode() + p.stderr.decode()


if not os.path.isfile(os.path.join(ROOT, leaving.POLICY)):
    print("skip  %s is absent, so there is no policy to probe" % leaving.POLICY)
    sys.exit(0)

for rel in ("projects/PSYCH-ASR/%s/x" % D, "research/PSYCH-ASR/%s/x" % D,
            "projects/TRD-EHR/%s/deep/y.json" % D):
    code, out = probe(rel)
    check("refused by policy and fence: %s" % rel.replace(D, "<fence>"),
          code == 0 and out.count("refuses") == 2, out)

code, out = probe(os.path.join(ROOT, "projects", "PSYCH-ASR", D, "x"))
check("an absolute path inside the tree is refused the same way", code == 0, out)

code, out = probe(os.path.join("PSYCH-ASR", D, "x"),
                  cwd=os.path.join(ROOT, "projects"))
check("and a path relative to another directory is placed in the tree",
      code == 0, out)

for rel in ("projects/PSYCH-ASR/notes.md", "projects/TRD-EHR/README.md",
            "board/tutorboard/leaving.py"):
    code, out = probe(rel)
    check("an ordinary file passes, exit 1: %s" % rel, code == 1, out)

code, out = probe("")
check("no path is a usage error, exit 2", code == 2, out)

empty = tempfile.mkdtemp(prefix="tutor-probe-")
try:
    said = leaving.probe("projects/X/%s/x" % D, empty)
    check("a tree with no policy says so rather than passing",
          said[0] is None and said[1] == D, said)
finally:
    shutil.rmtree(empty, ignore_errors=True)

if fails:
    print("\n%d failed" % len(fails))
    sys.exit(1)
print("\nphi-probe: all green")
