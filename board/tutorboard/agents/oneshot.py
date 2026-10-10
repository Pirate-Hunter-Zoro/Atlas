"""One prompt, to whichever provider can take it: AI use outside the board.

A tool that is not a board turn (Paper-Writer's daemon, a script) calls `run`
instead of a vendor's CLI, so it uses the same table the board does
(`recipes.load_config`) and walks the same order (`recipes.chain`): a provider
that is missing, unkeyed, out of allowance or failing hands the prompt to the
next. Adding or removing a provider in the config adds or removes it here too.

Each attempt is the recipe's `headless_first`, run the way `board doctor` runs
one: its own environment (`turn.turn_environment`), nothing on stdin, a time
cap. A prompt too long for argv is written to a file under `cwd`, and the
agent is told to read it.
"""

import os
import tempfile

from tutorboard.agents import recipes, usage
from tutorboard.runner import turn as runturn

# Beyond this many characters the prompt goes in a file: argv is capped, and
# every agentic CLI can read a file in its own directory.
ARGV_PROMPT = 60000

FROM_FILE = ("Your full instructions are in the file %s, in this directory. "
             "Read all of it, then do exactly what it says.")


def chain(cfg=None, names=None):
    """The recipes to try, in order: `names` if given, else the config's."""
    cfg = cfg or recipes.load_config()
    return list(names) if names else recipes.chain(cfg)


def _attempt(cfg, name, prompt, cwd, timeout):
    """`(text, why)`: the agent's final text, or why it gave none."""
    spec = cfg["agents"][name]
    argv = [a.replace("{prompt}", prompt) for a in runturn.fresh_recipe(spec)]
    cmd = usage.with_usage(spec, argv)
    box = tempfile.mkdtemp(prefix="atlas-oneshot-")
    logpath = os.path.join(box, "turn.log")
    try:
        with open(logpath, "w") as log:
            rc, capped = runturn.run_turn(
                cmd, cwd, log, timeout,
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
           else ("exit %d" % rc) if rc
           else usage.result_object_error(said))
    if err:
        return "", usage.failure_reason(said, err)
    return usage.turn_text(said), None


def run(prompt, cwd, timeout=1200, cfg=None, names=None, done=None):
    """Send `prompt` from `cwd` down the chain until one provider answers.

    `done(name)` judges an answer beyond a clean exit (Paper-Writer: did the
    artifact land?); False moves on to the next provider. Returns
    `{ok, name, text, tried}`, `tried` a list of `(name, why)` for every
    provider passed over.
    """
    cfg = cfg or recipes.load_config()
    tried = []
    spill = None
    if len(prompt) > ARGV_PROMPT:
        fd, spill = tempfile.mkstemp(prefix=".atlas-prompt-", suffix=".md",
                                     dir=cwd)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        prompt = FROM_FILE % os.path.basename(spill)
    try:
        for name in chain(cfg, names):
            why = recipes.unavailable(cfg, name)
            if why:
                tried.append((name, why))
                continue
            text, why = _attempt(cfg, name, prompt, cwd, timeout)
            if why is None and done is not None and not done(name):
                why = "it exited cleanly but did not do the work"
            if why is None:
                return {"ok": True, "name": name, "text": text,
                        "tried": tried}
            tried.append((name, why))
        return {"ok": False, "name": None, "text": "", "tried": tried}
    finally:
        if spill:
            try:
                os.remove(spill)
            except OSError:
                pass
