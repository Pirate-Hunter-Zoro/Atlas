#!/usr/bin/env python3
"""A wait that never comes back, and the daemon that must not wait for it.

    python3 test/wedged.py

THE FAILURE THIS HOLDS OFF IS SILENT AND LOOKS EXACTLY LIKE A HEALTHY BOARD.
Measured on 23 September 2026 in Probability: `board wait --timeout 300` sat for
71 minutes in `nfs_set_open_stateid_locked` -- state `D`, uninterruptible sleep,
where the kernel runs no more of that process until the filer answers. The
daemon was alive and its process table entry was fine. It wrote no heartbeat and
took no turn for the whole of it, the student's message sat unread, and the
board said the tutor had not picked it up. A restart could not clear it either:
the daemon was inside `communicate()` with no bound, so it accepted the signal
and acted on nothing.

`cmd_wait` checks its deadline between polls and a poll is an `open()`, so the
deadline is exactly what an uninterruptible open skips. That is not fixable
there, and the rule this file exists to keep is the general one:

    A DEADLINE ENFORCED BY THE THING THAT MIGHT HANG IS NOT A DEADLINE.
    The parent bounds the child.

So what is asserted is the parent's behaviour against a child that ignores its
own timeout completely -- which is the only faithful stand-in for D state, since
a test cannot wedge a filer.
"""

import importlib.machinery
import importlib.util
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="wedged-state-"))
os.environ.setdefault("BOARD_NODE_NAME", "test-node")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# ---- the two numbers -------------------------------------------------------
check("the daemon's own ceiling is longer than the deadline it hands the child, "
      "so an ordinary slow wait is never cut short",
      tutor.WAIT_CEILING > tutor.WAIT_TIMEOUT)
from tutorboard import processes                               # noqa: E402
check("and both are well inside the silence that makes a board call this daemon "
      "dead -- a bound that outlives the heartbeat window buys nothing",
      tutor.WAIT_CEILING < processes.AWAY_SILENCE)

# ---- a child that ignores its deadline -------------------------------------
# The stand-in for uninterruptible sleep: a process that was given a timeout and
# does not honour it. A test cannot put a process in D state -- that needs a
# filer to stop answering -- so what is exercised is the parent's half, which is
# the half that was missing.
SLEEPER = ("import signal, time\n"
           "signal.signal(signal.SIGTERM, lambda *a: None)\n"   # deaf, like D
           "time.sleep(600)\n")

p = subprocess.Popen([sys.executable, "-c", SLEEPER],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     start_new_session=True)
began = time.time()
try:
    p.communicate(timeout=1.0)
    check("a child that ignores its deadline is not simply waited on", False)
except subprocess.TimeoutExpired:
    check("a child that ignores its deadline does not return on its own", True)

tutor.drop_waiter(p)
check("and dropping it does not block, whatever state it is in",
      time.time() - began < 5)
for _ in range(50):
    if p.poll() is not None:
        break
    time.sleep(0.1)
check("SIGKILL ends it even though it refuses SIGTERM -- a wedged waiter that "
      "woke on a catchable signal would run `cmd_inbox`, mark the student's "
      "message read, and print it down a pipe nobody holds",
      p.poll() is not None)
check("it is killed rather than asked, which is what makes that unreachable",
      "SIGKILL" in open(os.path.join(ROOT, "bin", "tutor"),
                        encoding="utf-8").read().split("def drop_waiter")[1][:900])

# A group, because that is what `start_new_session` on the waiter is for.
src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
loop = src.split('running["waiter"] = subprocess.Popen(')[1][:700]
check("the waiter is started in a session of its own, so there is a group to "
      "signal", "start_new_session=True" in loop)
check("the daemon bounds it rather than trusting the deadline it handed over",
      "communicate(timeout=WAIT_CEILING)" in loop)
check("a wait that was cut reads as 'nothing arrived', so the next pass asks "
      "again rather than treating it as a message", "raw, code = b\"\", 2" in loop)
check("and shutting down kills it the same way, or a restart leaves a daemon "
      "nobody can replace", "drop_waiter(w)" in src)

# ---- and the thing that must not be tried again ----------------------------
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("`board wait` says in its own docstring that its timeout is best effort, "
      "so the next person does not try to enforce it where it cannot be",
      "IS BEST EFFORT" in board_src and "uninterruptibly" in board_src)

print("%d FAILURES" % len(fails) if fails
      else "a deadline is enforced by the parent, because the child may be "
           "unable to keep it")
sys.exit(1 if fails else 0)
