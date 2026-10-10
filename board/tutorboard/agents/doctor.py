"""`board doctor`'s turns: one real turn per provider, the way the runner sends it.

    board doctor              the configured `provider` and its `fallback`
    board doctor codex ...    the recipes named instead
    board doctor --dry        no turn: whether each could take one, and its argv

Each recipe gets one fresh turn in a scratch directory: its `headless_first`
argv with the usage flags, its own environment (`turn_environment`), nothing on
stdin, `DOCTOR_TURN_SECONDS` at most. The prompt asks for a code word that is
in the prompt and nowhere else, so an answer that says it back came from the
model. One line per recipe; exit 1 when any of them could not take a turn or
did not answer. Nothing outside the scratch directory is written: no limit
mark, no cost line in a session.
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


def smoke(cfg, name, timeout=DOCTOR_TURN_SECONDS):
    """One turn on recipe `name`. `(ok, line)`: the line names what happened."""
    why = recipes.unavailable(cfg, name)
    if why:
        return False, "FAIL %-9s cannot take a turn here: %s" % (name, why)
    spec = cfg["agents"][name]
    word = "doctor-%06d" % random.randint(0, 999999)
    argv = [a.replace("{prompt}", DOCTOR_PROMPT % {"word": word})
            for a in runturn.fresh_recipe(spec)]
    cmd = usage.with_usage(spec, argv)
    box = tempfile.mkdtemp(prefix="tutor-doctor-")
    logpath = os.path.join(box, "turn.log")
    began = time.time()
    try:
        with open(logpath, "w") as log:
            rc, capped = runturn.run_turn(
                cmd, box, log, timeout,
                env=runturn.at_root(box, runturn.turn_environment(spec)))
        said = usage.turn_output(logpath, 0)
    except OSError as exc:
        return False, "FAIL %-9s did not run: %s" % (name, exc)
    finally:
        took = time.time() - began
        shutil.rmtree(box, ignore_errors=True)
    err = (("timed out after %d s" % timeout) if capped
           else ("exit %d" % rc) if rc
           else usage.result_object_error(said))
    if err:
        why = usage.failure_reason(said, err)
        tail = [l.strip() for l in (said or "").splitlines() if l.strip()]
        if why == err and tail:
            why = "%s: %s" % (err, tail[-1][:200])
        return False, "FAIL %-9s %s" % (name, why)
    if word not in usage.turn_text(said):
        return False, ("FAIL %-9s exited 0 without the code word: %s"
                       % (name, " ".join(usage.turn_text(said).split())[:200]))
    return True, "ok   %-9s answered in %.1f s (%s)" % (name, took, " ".join(argv[:1]))


def dry_line(cfg, name):
    """`(ok, line)` for a recipe without a turn: can it take one here, and
    what would run."""
    why = recipes.unavailable(cfg, name)
    if why:
        return False, "FAIL %-9s cannot take a turn here: %s" % (name, why)
    argv = runturn.fresh_recipe(cfg["agents"][name])
    return True, "dry  %-9s would run: %s" % (name, " ".join(argv[:1]))


def cmd_doctor(cfg, args, dry=False):
    """A smoke turn per provider (`dry`: none, only whether each could take
    one). Exit 0 or 1."""
    cfg = cfg or recipes.load_config()
    names = [a for a in args if not a.startswith("-")]
    if not names:
        names = [n for n in (recipes.provider(cfg), recipes.fallback(cfg)) if n]
    if not names:
        print("FAIL nobody: no provider or fallback is configured")
        return 1
    ok = True
    for name in dict.fromkeys(names):
        good, line = dry_line(cfg, name) if dry else smoke(cfg, name)
        print(line)
        ok = ok and good
    return 0 if ok else 1
