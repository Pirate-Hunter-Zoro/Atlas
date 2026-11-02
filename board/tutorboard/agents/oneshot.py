"""One prompt to DeepSeek through OpenCode: AI use outside the board.

A tool that is not a board turn (a script, a daemon) calls `run` instead of
running opencode itself, so it gets the board's recipe, key and readiness
check (`recipes.ready`).

The attempt is the recipe's `headless_first`, run the way `board doctor` runs
one: its own environment (`turn.turn_environment`), nothing on stdin, a time
cap. A prompt too long for argv is written to a file under `cwd`, and the
agent is told to read it.
"""

import os
import tempfile

from tutorboard.agents import recipes, usage
from tutorboard.runner import turn as runturn

# Beyond this many characters the prompt goes in a file: argv is capped, and
# opencode can read a file in its own directory.
ARGV_PROMPT = 60000

FROM_FILE = ("Your full instructions are in the file %s, in this directory. "
             "Read all of it, then do exactly what it says.")


def _attempt(prompt, cwd, timeout):
    """`(text, why)`: the agent's final text, or why it gave none."""
    spec = recipes.spec()
    box = tempfile.mkdtemp(prefix="atlas-oneshot-")
    logpath = os.path.join(box, "turn.log")
    try:
        with open(logpath, "w") as log:
            rc, capped = runturn.run_turn(
                recipes.argv(prompt, spec), cwd, log, timeout,
                env=runturn.at_root(cwd, runturn.turn_environment(spec)))
        said = usage.turn_output(logpath, 0)
    except OSError as exc:
        return "", "did not run: %s" % exc
    finally:
        try:
            os.remove(logpath)
            os.rmdir(box)
        except OSError:
            pass
    err = (("timed out after %d s" % timeout) if capped
           else ("exit %d" % rc) if rc else None)
    if err:
        return "", usage.failure_reason(said, err)
    return usage.turn_text(said), None


def run(prompt, cwd, timeout=1200, done=None):
    """Send `prompt` to DeepSeek from `cwd`.

    `done()` judges an answer beyond a clean exit (did the artifact land?).
    Returns `{ok, text, why}`, `why` None when it worked.
    """
    why = recipes.ready()
    if why:
        return {"ok": False, "text": "", "why": why}
    spill = None
    if len(prompt) > ARGV_PROMPT:
        fd, spill = tempfile.mkstemp(prefix=".atlas-prompt-", suffix=".md",
                                     dir=cwd)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        prompt = FROM_FILE % os.path.basename(spill)
    try:
        text, why = _attempt(prompt, cwd, timeout)
        if why is None and done is not None and not done():
            why = "it exited cleanly but did not do the work"
        return {"ok": why is None, "text": text if why is None else "",
                "why": why}
    finally:
        if spill:
            try:
                os.remove(spill)
            except OSError:
                pass
