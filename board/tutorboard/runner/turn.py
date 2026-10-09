"""One turn: its environment, its plan, its clock, and the process that runs it.

A turn runs in its own process group, so the cap kills everything it started.
"""

import os
import re
import signal
import subprocess

from tutorboard import jobs, keys
from tutorboard.course import config
from tutorboard.runner import prompts
from tutorboard.course import repo as course_repo

def turn_environment(spec, base=None):
    """What one turn runs with: this process's environment, plus the recipe's.

    A recipe's `env` carries keys, which must not reach argv: argv is readable
    in `ps` (`ai-config/policy/credentials.txt`).
    `{NAME}` values come from `keys.fill`; a value naming a missing key is
    dropped rather than passed with its braces. Every turn carries
    `TUTORBOARD_TURN=1`, which `.githooks/pre-commit` reads to refuse RULES.md
    and a `phi` or `relay.exports` change.
    """
    extra = (spec or {}).get("env") or {}
    env = dict(base if base is not None else os.environ)
    for name, value in extra.items():
        filled = keys.fill(value)
        if filled is not None:
            env[str(name)] = filled
    env["TUTORBOARD_TURN"] = "1"
    return env

def as_repo(where):
    """`where` as a Repo: a Repo is itself; a root is the session a CLI
    process bound for it, else sessionless."""
    if hasattr(where, "state"):
        return where
    bound = course_repo.session_dir(where)
    if bound:
        return course_repo.Repo(where, bound, create=False)
    return course_repo.sessionless(where)


def state_of(where):
    said = as_repo(where).state()
    return said if isinstance(said, dict) else {}


def doing_now(where, signal=""):
    """Is this turn's product a change rather than a card? True in do mode,
    and for a handover, rework, writeup, unfinished or repair turn whatever
    the mode, because those need the doing clock."""
    if signal in ("handover", "rework", "writeup", "unfinished", "repair"):
        return True
    try:
        return config.mode_of(state_of(where)) == "do"
    except Exception:
        return False


def turn_timeout(cfg, where, spec=None, signal=""):
    """How long this turn gets, by its kind and its agent.

    A recipe's `timeout` is a floor, because a slow agent (Colibri prefills
    for hours) would otherwise die at the cap of every turn.
    """
    plain = int(cfg.get("headless_timeout", 900) or 900)
    if doing_now(where, signal):
        plain = max(plain, int(cfg.get("doing_timeout", 3600) or 3600))
    try:
        floor = int((spec or {}).get("timeout") or 0)
    except (TypeError, ValueError):
        floor = 0
    return max(plain, floor)

def at_root(root, env=None):
    """A turn's environment with `PWD` naming where it runs, because OpenCode
    takes its directory from `PWD`, not the process cwd."""
    env = dict(env if env is not None else os.environ)
    env["PWD"] = os.path.abspath(root)
    return env


def run_turn(cmd, cwd, log, timeout, env=None, on_start=None):
    """Run one turn to completion or to its cap. `(returncode, timed_out)`.

    The turn is its own process group, so the cap kills all of it: SIGTERM,
    15 s, SIGKILL. `on_start(process)` runs before the turn does anything.
    Stdin is closed because `codex exec` blocks reading a non-terminal stdin.
    """
    p = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL,
                         start_new_session=True, env=at_root(cwd, env))
    if on_start:
        try:
            on_start(p)
        except Exception:                                    # noqa: BLE001
            pass
    try:
        return p.wait(timeout), False
    except subprocess.TimeoutExpired:
        pass
    for sig, grace in ((signal.SIGTERM, 15), (signal.SIGKILL, None)):
        try:
            os.killpg(os.getpgid(p.pid), sig)
        except OSError:
            pass
        try:
            p.wait(grace)
            break
        except subprocess.TimeoutExpired:
            continue
    return p.returncode, True


def fresh_recipe(spec):
    """The recipe that starts a new conversation: `headless_first`, else
    `headless`. Every session shares the Atlas root as its cwd, so a turn
    never resumes (`--continue` would pick up another session's)."""
    return (spec or {}).get("headless_first") or (spec or {}).get("headless")


def turn_plan(spec, signal=""):
    """`(recipe, prompt)` for a turn woken for `signal`. Every turn is a fresh
    process with a fresh conversation; the signal picks the prompt."""
    prompt = {
        "revise": prompts.HEADLESS_REVISE_PROMPT,
        "rework": prompts.HEADLESS_REWORK_PROMPT,
        "writeup": prompts.HEADLESS_WRITEUP_PROMPT,
        "unfinished": prompts.HEADLESS_UNFINISHED_PROMPT,
        "code": prompts.HEADLESS_CODE_PROMPT,
    }.get(signal, prompts.HEADLESS_FIRST_PROMPT)
    return fresh_recipe(spec), prompt


def context_plan(signal=""):
    """`(brief, recap)`: what a turn woken for `signal` is handed above its
    prompt. Revisions, reworks and write-ups get neither; `[unfinished]` gets
    the recap only."""
    if signal in ("revise", "rework", "writeup"):
        return False, False
    if signal == "unfinished":
        return False, True
    return True, True


# The second bracket of `[<iso>] [<signal>] <text>`, so the board can say what
# a turn is doing. Anchored at the start: "[help]" mid-sentence is not a signal.
_SIGNAL_TAG = re.compile(r"^\[[^\]\n]*\]\s*\[([a-z]+)\]")


# Non-waking lines that ride in front of the one that woke the turn.
QUIET_SIGNALS = ("bind", "mode", "uploaded", "filed", "unheld")


def turn_signal(out):
    """The signal the inbox message carries, or "": the first line's tag,
    passing over the quiet lines in front of it. Never raises."""
    for line in (out or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SIGNAL_TAG.match(line)
        if m and m.group(1) in QUIET_SIGNALS:
            continue
        return m.group(1) if m else ""
    return ""


# A batch with a [repair] line anywhere is a repair turn, unless its signal is
# one whose own machinery the turn needs.
REPAIR_KEEPS = ("unfinished", "handover", "rework", "revise", "writeup")


def woken_for(root, out, inbox=None):
    """`(signal, repair request ids)` for the batch `out`, read against the
    session's inbox file `inbox` (else the one `root` resolves to). Never
    raises."""
    signal = turn_signal(out)
    try:
        repairs = jobs.batch_repairs(root, out, inbox)
    except Exception:                                        # noqa: BLE001
        repairs = []
    if repairs and signal not in REPAIR_KEEPS:
        signal = jobs.REPAIR
    return signal, repairs
