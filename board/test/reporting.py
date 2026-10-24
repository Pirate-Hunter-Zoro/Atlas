#!/usr/bin/env python3
"""A turn ends on a report.

A doing turn writes a `pending` card first and its report over it. A turn that
exits with the newest card still `pending` is woken once more with
`[unfinished]`; if that turn also leaves it pending, the card is replaced by a
`stopped` one listing what is uncommitted under the work.

Guarded here: the placeholder's kind at the door (`board write pending`), the
daemon's decision as a function with no daemon (`report_owed`), the turn the
`[unfinished]` line buys (`turn_plan`, `doing_now`), the wiring in the loop as
source, the prompts that tell a turn to name what it left uncommitted, and the
board not reading a placeholder as an answer.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import sense                                # noqa: E402
from tutorboard.lesson import cards, git as lesson_git      # noqa: E402

from tutorboard.runner import prompts  # noqa: E402
from tutorboard.runner import loop as runloop  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402

BOARD = [sys.executable, os.path.join(ROOT, "bin", "board")]

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false"] + list(args),
                          cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60)


def board_write(ws, body, *args):
    p = subprocess.run(BOARD + ["write"] + list(args) + ["--repo", ws],
                       env=dict(os.environ, TUTORBOARD_SESSION=os.path.join(ws, "live")),
                       input=body.encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


base = tempfile.mkdtemp(prefix="tutor-reporting-")
try:
    # A repository holding two workspaces, so the listing is shown to be about
    # this one.
    git(base, "init", "-q")
    ws = os.path.join(base, "projects", "W")
    other = os.path.join(base, "projects", "V")
    for d in (ws, other):
        os.makedirs(os.path.join(d, "live", "cards"))
        with open(os.path.join(d, "tutorboard.json"), "w") as fh:
            fh.write("{}\n")
        with open(os.path.join(d, "kept.py"), "w") as fh:
            fh.write("x = 1\n")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "start")
    room = os.path.join(ws, "live", "cards")
    # This process reads the session the way a turn's `board` does: bound.
    from tutorboard.course import repo as course_repo        # noqa: E402
    os.environ["TUTORBOARD_SESSION"] = os.path.join(ws, "live")
    course_repo.resolve(ws, create=False)
    del os.environ["TUTORBOARD_SESSION"]

    # -- the placeholder at the door ---------------------------------------
    print("\n-- the placeholder is written `pending` --")
    code, path = board_write(ws, "Fitting the sweep now.\n", "pending", "start")
    check("`board write pending` writes a card", code == 0 and os.path.isfile(path))
    meta, _ = cards.parse_front_matter(open(path, encoding="utf-8").read())
    check("and its kind is pending", cards.is_pending(meta))
    got, gmeta = cards.newest(room)
    check("it is the newest card", got == path and cards.is_pending(gmeta))

    # -- a turn that exits on it is woken once ------------------------------
    print("\n-- a turn that exits with it pending is woken once more --")
    out = "[2026-10-01 10:00:00] [aim] write the sweep\n"
    line = runloop.report_owed(ws, "aim", out)
    check("the daemon owes an [unfinished] turn", bool(line))
    check("which turn_signal reads as unfinished",
          runturn.turn_signal(line) == "unfinished")
    check("and which names the placeholder", os.path.relpath(path, ws) in line)
    check("and keeps the message it was answering", "write the sweep" in line)

    use, prompt = runturn.turn_plan({"headless": ["r"], "headless_first": ["f"]},
                                    "unfinished")
    check("an unfinished turn is a fresh process like every other, reading "
          "what the work changed off disk",
          use == ["f"])
    check("and is told to write the report over the card",
          prompt is prompts.HEADLESS_UNFINISHED_PROMPT and "--over" in prompt
          and "uncommitted" in prompt)
    check("it runs on a doing turn's clock", runturn.doing_now(ws, "unfinished"))

    # -- a report written over it settles it ---------------------------------
    print("\n-- a report written over it is not owed anything --")
    code, _ = board_write(ws, "Fitted it; `fit.py` is uncommitted.\n", "--over", path)
    check("the report goes over the placeholder", code == 0)
    _, rmeta = cards.newest(room)
    check("and is no longer pending", not cards.is_pending(rmeta))
    check("so nothing is owed", runloop.report_owed(ws, "aim", out) is None)

    # -- a second exit on a placeholder gets the stopped card -----------------
    print("\n-- an [unfinished] turn that also leaves it pending --")
    code, path2 = board_write(ws, "Running the suite.\n", "pending", "suite")
    with open(os.path.join(ws, "fit.py"), "w") as fh:
        fh.write("y = 2\n")
    with open(os.path.join(ws, "kept.py"), "a") as fh:
        fh.write("z = 3\n")
    with open(os.path.join(other, "kept.py"), "a") as fh:
        fh.write("elsewhere\n")
    check("uncommitted lists this workspace's changes, relative to it",
          sorted(lesson_git.uncommitted(ws) or []) == ["fit.py", "kept.py"])
    check("and can be narrowed to a thread's paths",
          lesson_git.uncommitted(ws, ["fit.py"]) == ["fit.py"])
    again = runloop.report_owed(ws, "unfinished", line)
    check("nothing more is woken", again is None)
    body = open(path2, encoding="utf-8").read()
    smeta, sbody = cards.parse_front_matter(body)
    check("the placeholder is replaced by a stopped card",
          smeta.get("kind") == cards.STOPPED)
    check("which says the turn stopped without reporting",
          "stopped without reporting" in sbody)
    check("and names what is uncommitted here",
          "`fit.py`" in sbody and "`kept.py`" in sbody)
    check("and nothing from the other workspace", "elsewhere" not in sbody
          and "V/kept.py" not in sbody)
    check("and the board's own scratch is not listed", "live/" not in sbody)
    check("a stopped card is not pending, so the next exit owes nothing",
          runloop.report_owed(ws, "aim", out) is None)
    check("no part file is left behind",
          not [n for n in os.listdir(room) if n.startswith(".")])

    # -- a stopped card names the jobs registered since the work began -------
    print("\n-- a stopped card lists the jobs the work registered --")
    code, path3 = board_write(ws, "Fitting again.\n", "pending", "again")
    began = os.path.getmtime(path3)
    with open(os.path.join(ws, "live", "jobs.jsonl"), "w") as fh:
        fh.write(json.dumps({"thread": "fit", "jobid": "11", "cmd": "sbatch old.sbatch",
                             "submitted": began - 3600}) + "\n")
        fh.write(json.dumps({"thread": "fit", "jobid": "12", "cmd": "sbatch sweep.sbatch",
                             "submitted": began + 1}) + "\n")
    runloop.report_owed(ws, "unfinished", line)
    tmeta, tbody = cards.parse_front_matter(open(path3, encoding="utf-8").read())
    check("the placeholder is replaced by a stopped card naming no thread",
          tmeta.get("kind") == cards.STOPPED and not tmeta.get("thread"))
    check("which lists what is uncommitted in the workspace",
          "`fit.py`" in tbody and "`kept.py`" in tbody)
    check("and names the job registered since the work began, not an older one",
          "`12`" in tbody and "sweep.sbatch" in tbody and "`11`" not in tbody)
finally:
    shutil.rmtree(base, ignore_errors=True)

# -- the wiring, read as source ----------------------------------------------
print("\n-- the loop settles a turn on its report --")
src = open(os.path.join(ROOT, "tutorboard", "runner", "loop.py"),
           encoding="utf-8").read()
loop = src.split("def take_turn(")[-1].split("wrap-up ===")[0]
check("the loop asks report_owed where nothing else is owed",
      "if pending is None:\n        pending = report_owed(" in loop)
check("before the debt is written down", loop.index("report_owed(") <
      loop.index("owe(ctx, pending)\n    return"))
check("the assistant is not swapped under an unfinished turn",
      'signal == "unfinished"' in src.split("def for_this_turn(")[1].split("\ndef ")[0])

print("\n-- the turn is told to name what it left uncommitted --")
check("a doing turn opens with `board write pending`",
      "`board write pending`" in sense.DOING_SENSE)
check("and its report names uncommitted files",
      "left uncommitted" in sense.DOING_SENSE)

print("\n-- the board does not read a placeholder as an answer --")
js = open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read()
newest = js.split("function newestCard(data) {")[1].split("\n}")[0]
check("newestCard skips a pending card", 'c.kind !== "pending"' in newest)
check("a stopped card carries its own badge",
      'stopped: "stopped without a report"' in js)

print()
if fails:
    print("%d failed" % len(fails))
    sys.exit(1)
print("a turn ends on a report, and the card says what is on disk when it does not")
