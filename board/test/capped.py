#!/usr/bin/env python3
"""A turn past its cap is cut, and its whole process group goes with it.

`run_turn` is the one place a turn is killed. A client that runs a child of its
own -- `srun`, a language server, a shell -- leaves that child answering if
only the direct child is killed, and the next turn is then a second client on
the same work. So the turn runs in a group of its own and the group is killed.

The daemon's own loop is not run here -- `headless` starts a board, binds a port
and pushes a git branch -- so the wiring is read out of the file as source.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
_spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(_spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def script(path, body):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/bash\n" + body)
    os.chmod(path, 0o755)
    return path


base = tempfile.mkdtemp(prefix="tutor-hopping-")
try:
    # -----------------------------------------------------------------------
    # A. run_turn kills the GROUP, not the child
    # -----------------------------------------------------------------------
    kid = os.path.join(base, "kid.pid")
    stub = script(os.path.join(base, "slow"),
                  'sleep 300 &\necho $! > %s\nwait\n' % kid)
    logpath = os.path.join(base, "turn.log")
    with open(logpath, "w", encoding="utf-8") as log:
        began = time.time()
        rc, timed_out = tutor.run_turn([stub], base, log, 1)
    check("a turn that runs past its cap is cut, and says so rather than "
          "wearing an exit code",
          timed_out and time.time() - began < 30)

    with open(kid, encoding="utf-8") as fh:
        child = int(fh.read().strip())
    gone = False
    for _ in range(50):
        try:
            os.kill(child, 0)
        except OSError:
            gone = True
            break
        time.sleep(0.1)
    check("and the child it launched goes with it, because a client left "
          "answering is a second client on the same work",
          gone)

    rc, timed_out = None, None
    with open(logpath, "a", encoding="utf-8") as log:
        rc, timed_out = tutor.run_turn(
            [script(os.path.join(base, "quick"), 'exit 3\n')], base, log, 30)
    check("and a turn that ends on its own is reported by its code, with "
          "nothing cut", rc == 3 and not timed_out)

finally:
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------------------
# B. the daemon runs every turn through `run_turn`, read as source
# ---------------------------------------------------------------------------
SRC = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
# The daemon's own body: `tutor doctor` runs turns through `run_turn` too.
DAEMON = SRC.split("\ndef headless(")[1].split("\ndef ")[0]
check("the daemon runs every turn through `run_turn`, including the retry, or "
      "one of the two paths leaves an orphan behind",
      SRC.count("tutor.run_turn") == 0
      and DAEMON.count("= run_turn(") == 2
      and "subprocess.run(cmd, cwd=root, stdout=log" not in
      SRC.split("def headless")[-1].split("handoff ===")[0])
check("and there is no hop, no pick-up and no chain-gap wait left in it",
      "reads_as_carry" not in SRC
      and "reads_as_wait" not in SRC and "mission_turn" not in SRC)

print("%d FAILURES" % len(fails) if fails
      else "a turn past its cap is cut, and nothing is left answering")
sys.exit(1 if fails else 0)
