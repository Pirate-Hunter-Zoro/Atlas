"""`board doctor`'s checks: one real DeepSeek turn, the way the runner sends
it, and one look through the vision route.

    board doctor        one turn, then one witness-strip probe of the vision route
    board doctor --dry  neither: whether a turn could run, its argv, and the route

The turn is the recipe's `headless_first` in a scratch directory, with its own
environment (`turn_environment`), nothing on stdin, `DOCTOR_TURN_SECONDS` at
most. The prompt asks for a code word that is in the prompt and nowhere else,
so an answer that says it back came from the model. Exit 1 when the turn could
not run or did not answer, or the probe failed. Nothing outside the scratch
directory is written: no limit mark, no cost line in a session.

The vision probe sends `seeing.ask` the witness strip alone: one small call,
which passes only when the six digits drawn in the strip come back, so a
text-only model fails here rather than in a lesson.
"""

import os
import random
import shutil
import tempfile
import time

from tutorboard.agents import recipes, usage
from tutorboard.runner import turn as runturn

DOCTOR_TURN_SECONDS = 300

DOCTOR_PROMPT = (
    "This is a one-turn check of the tutoring harness, run by `board doctor`. "
    "Reply with the code word %(word)s and nothing else. Do not read or write "
    "any file and run no command.")

NAME = recipes.NAME


def smoke(timeout=DOCTOR_TURN_SECONDS):
    """One turn. `(ok, line)`: the line names what happened."""
    why = recipes.ready()
    if why:
        return False, "FAIL %-9s cannot take a turn here: %s" % (NAME, why)
    spec = recipes.spec()
    word = "doctor-%06d" % random.randint(0, 999999)
    argv = recipes.argv(DOCTOR_PROMPT % {"word": word}, spec)
    box = tempfile.mkdtemp(prefix="tutor-doctor-")
    logpath = os.path.join(box, "turn.log")
    began = time.time()
    try:
        with open(logpath, "w") as log:
            rc, capped = runturn.run_turn(
                argv, box, log, timeout,
                env=runturn.at_root(box, runturn.turn_environment(spec)))
        said = usage.turn_output(logpath, 0)
    except OSError as exc:
        return False, "FAIL %-9s did not run: %s" % (NAME, exc)
    finally:
        took = time.time() - began
        shutil.rmtree(box, ignore_errors=True)
    err = (("timed out after %d s" % timeout) if capped
           else ("exit %d" % rc) if rc else None)
    if err:
        why = usage.failure_reason(said, err)
        tail = [l.strip() for l in (said or "").splitlines() if l.strip()]
        if why == err and tail:
            why = "%s: %s" % (err, tail[-1][:200])
        return False, "FAIL %-9s %s" % (NAME, why)
    if word not in usage.turn_text(said):
        return False, ("FAIL %-9s exited 0 without the code word: %s"
                       % (NAME, " ".join(usage.turn_text(said).split())[:200]))
    return True, "ok   %-9s answered in %.1f s (%s)" % (NAME, took, argv[0])


def dry_line():
    """`(ok, line)` without a turn: can one run here, and what would run."""
    why = recipes.ready()
    if why:
        return False, "FAIL %-9s cannot take a turn here: %s" % (NAME, why)
    return True, "dry  %-9s would run: %s" % (NAME, recipes.spec()["headless_first"][0])


VISION_PROMPT = (
    "This is a one-image check of the vision route, run by `board doctor`. "
    "There is no other image and no question.")


def vision(dry=False):
    """`(ok, line)` for reading an image: with `dry`, the route `board see`
    takes; else one witness-strip probe of it."""
    from tutorboard import seeing
    got = seeing.route()
    where = "%s %s" % (seeing.route_host(got), got.get("model") or "")
    if dry:
        return True, "dry  %-9s would ask %s" % ("vision", where)
    try:
        seeing.ask(got, [], VISION_PROMPT)
    except seeing.Refused as exc:
        return False, ("FAIL %-9s %s cannot see: %s"
                       % ("vision", where, " ".join(str(exc).split())[:300]))
    return True, "ok   %-9s %s read the witness strip" % ("vision", where)


def cmd_doctor(dry=False):
    """The smoke turn and the vision probe (`dry`: neither). Exit 0 or 1."""
    good, line = dry_line() if dry else smoke()
    print(line, flush=True)
    seen, line = vision(dry=dry)
    print(line)
    return 0 if good and seen else 1
