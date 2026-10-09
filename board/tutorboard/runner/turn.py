"""One turn: its environment, its plan, its clock, and the process that runs it.

`turn_plan` picks the recipe and the prompt for what the turn was woken for
(`turn_signal`, `woken_for`), `turn_timeout` its cap (`doing_now`),
`turn_environment` and `at_root` what it runs with, and `run_turn` runs it to
completion or to the cap, killing its whole process group. The functions that
read a session take its Repo (`as_repo` also accepts a workspace root, whose
session is its `live/`).
"""

import os
import re
import signal
import subprocess

from tutorboard import handoff, jobs, keys
from tutorboard.course import config
from tutorboard.runner import prompts
from tutorboard.course import repo as course_repo

def turn_environment(spec, base=None):
    """What one turn runs with: this process's environment, plus the recipe's.

    A RECIPE'S `env` IS HOW A PROVIDER IS POINTED SOMEWHERE ELSE, and it is the
    one part of a turn that must not reach argv. `with_usage` appends flags to
    the command because flags are public; a key on a command line is in `ps`
    output for anything on the machine to read, which is the whole reason
    `ai-config/policy/credentials.txt` exists. So routing goes here.

    `{NAME}` in a value is substituted from `tutorboard/keys.py`. A value naming
    a key the store has not got is DROPPED rather than passed through with the
    braces still on it -- see `keys.fill`. The recipe should not have been
    offered at all in that case, which is what `unkeyed` on `--agents --json`
    is for; this is the second guard behind it.

    `base` is what the caller already built, merged here so the two land in
    one dict rather than in two places that fight. Otherwise a turn inherits
    the daemon's environment.

    EVERY TURN CARRIES `TUTORBOARD_TURN=1`. `.githooks/pre-commit` reads it: a
    turn may not commit RULES.md, which is the owner's, or change an existing
    tutorboard.json's `phi` or `relay.exports`.
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
    """`where` as a Repo: a Repo is itself; a root is its own `live/` session.

    The runner passes the session's Repo, so nothing here goes through the
    per-process binding `course_repo.resolve` makes for a CLI.
    """
    if hasattr(where, "state"):
        return where
    return course_repo.Repo(where, create=False)


def state_of(where):
    said = as_repo(where).state()
    return said if isinstance(said, dict) else {}


def chapter_now(where):
    """Which chapter is open, according to the session's own state."""
    return state_of(where).get("chapter") or ""

def doing_now(where, signal=""):
    """Is this turn one whose product is a change, not a card?

    True when the session is in do mode (`config.mode_of`), and for the turns
    whose signal says so whatever the mode: a step handed over (`handover`), a
    rework, a ship, a writeup, an unfinished doing turn, a repair. Each of those
    writes code or a document, and a doing turn on a teaching turn's clock is a
    turn killed with the work half done. A plain revision is not here: it is
    over in a minute.
    """
    if signal in ("handover", "rework", "ship", "writeup", "unfinished",
                  "repair"):
        return True
    try:
        return config.mode_of(state_of(where)) == "do"
    except Exception:
        return False


def turn_timeout(cfg, where, spec=None, signal=""):
    """How long this turn gets, by what kind of turn it is AND which agent runs it.

    The two numbers in the configuration are about the SITTING: a teaching turn
    writes a card and stops, a turn that was asked to write the code stages
    models and runs a suite. Both were measured against a hosted model that
    starts answering in seconds.

    An agent may be slower than either by an order of magnitude, and one is: a
    colibri turn spends two to three hours in prefill before it emits its first
    token, so every one of its turns died at the cap and was painted as a turn
    that FAILED rather than one that was interrupted. A `timeout` on the recipe
    is taken as a FLOOR, so the existing numbers stay exactly as they are for
    every other agent and the slow one carries its own.

    `signal` is what the inbox line says this turn is for, and it reaches here
    because one kind of turn is not the kind of turn its sitting is -- see
    `doing_now`.
    """
    plain = int(cfg.get("headless_timeout", 900) or 900)
    if doing_now(where, signal):
        plain = max(plain, int(cfg.get("doing_timeout", 3600) or 3600))
    try:
        floor = int((spec or {}).get("timeout") or 0)
    except (TypeError, ValueError):
        floor = 0
    return max(plain, floor)

def handoff_clause(where):
    """What to tell a tutor about the handoff -- including that there is none."""
    repo = as_repo(where)
    return (prompts.HANDOFF_CLAUSE if handoff.handoff_applies(repo.root, chapter_now(repo))
            else prompts.NO_HANDOFF_CLAUSE)

def at_root(root, env=None):
    """A turn's environment with `PWD` saying where the turn actually runs.

    `cwd=` moves the process and leaves `PWD` naming wherever the daemon was
    started. OpenCode takes its directory from `PWD`, measured: a turn started
    with `cwd` set to a course wrote its files into the daemon's directory and
    filed its session there, so `--continue` resumed the wrong conversation.
    """
    env = dict(env if env is not None else os.environ)
    env["PWD"] = os.path.abspath(root)
    return env


def run_turn(cmd, cwd, log, timeout, env=None, on_start=None):
    """Run one turn to completion or to its cap. `(returncode, timed_out)`.

    `cwd` is where the turn runs: the Atlas root for every session. The turn
    is a group of its own (`start_new_session`), so the cap -- and the runner's
    recovery after a server that died mid-turn -- kills everything it started:
    SIGTERM, fifteen seconds, then SIGKILL. `on_start(process)` runs once the
    process exists, so its group can be recorded before the turn does anything.

    Nothing on stdin: a client that reads a stdin that is not a terminal
    appends it to the prompt and blocks until it closes (`codex exec`).
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
    process with a fresh conversation, and reads the lesson back off disk.

    The signal picks the prompt: a revision, a rework, a ship and a document
    asked for mid-session are not part of the lesson and get their own; an
    `[unfinished]` report gets the prompt that reads `git status` and the
    placeholder card; a `[code]` step from the cluster gets the prompt that
    reads the step's diff; everything else is a lesson turn.
    """
    prompt = {
        "revise": prompts.HEADLESS_REVISE_PROMPT,
        "rework": prompts.HEADLESS_REWORK_PROMPT,
        "ship": prompts.HEADLESS_SHIP_PROMPT,
        "writeup": prompts.HEADLESS_WRITEUP_PROMPT,
        "unfinished": prompts.HEADLESS_UNFINISHED_PROMPT,
        "code": prompts.HEADLESS_CODE_PROMPT,
    }.get(signal, prompts.HEADLESS_FIRST_PROMPT)
    return fresh_recipe(spec), prompt


def context_plan(signal=""):
    """`(brief, recap)`: what a turn woken for `signal` is handed above its
    prompt. A lesson turn gets both; an `[unfinished]` report the recap, which
    shows the placeholder it owes; a revision, rework, ship or write-up is not
    part of the lesson and gets neither, as its prompt says.
    """
    if signal in ("revise", "rework", "ship", "writeup"):
        return False, False
    if signal == "unfinished":
        return False, True
    return True, True


# WHAT A TURN WAS WOKEN FOR, so the board can say it while the turn runs.
#
# `board inbox` prints a message as `[<iso>] [<signal>] <text>`, and the signal
# is the one word that says what kind of work this turn is. The board needs it
# for exactly one reason and it is a reported one: a direction change wakes a
# turn that rewrites the plan, and that turn OPENS with a card saying it is
# re-planning. The strip's rule is "a card landed, so stop talking", so the
# indicator went away in the first ten seconds of a job that takes minutes --
# "I got left hanging for a bit while it was thinking and modifying the plan".
#
# Anchored at the start of the message rather than searched for, because a
# student who writes "[help]" in the middle of a sentence has not sent a signal.
_SIGNAL_TAG = re.compile(r"^\[[^\]\n]*\]\s*\[([a-z]+)\]")


# Lines that wake nothing (`"wake": false`) and ride in front of the line that
# did: a bind, a mode change, an upload, a filing, a coding session's ref
# gone. They say nothing about what the turn is.
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


# A BATCH WITH A [repair] IN IT IS A REPAIR TURN, wherever in the batch the line
# sits. `board inbox` hands a turn every unread message at once, and the first
# one's signal is what `turn_signal` reads; a failed job's line behind a
# student's message would otherwise be briefed as a lesson. The signals kept are
# the ones whose own machinery the turn needs -- an owed report, a step handed
# over, a rework, a ship, a write-up -- and all of them are doing
# turns already. `turn_repairs` names every [repair] request in the batch, so
# `board brief` names each.
REPAIR_KEEPS = ("unfinished", "handover", "rework", "revise", "ship", "writeup")


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
