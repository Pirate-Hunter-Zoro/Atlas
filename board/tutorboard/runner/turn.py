"""One turn: its environment, its plan, its clock, and the process that runs it.

`turn_plan` picks the recipe and the prompt for what the turn was woken for
(`turn_signal`, `woken_for`), `turn_timeout` its cap (`doing_now`),
`turn_environment` and `at_root` what it runs with, and `run_turn` runs it to
completion or to the cap, killing its whole process group.
"""

import json
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

def chapter_now(root):
    """Which chapter is open, according to the board's own state."""
    try:
        with open(course_repo.session_path(root, "state.json"), "r", encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("chapter") or ""
    except (OSError, ValueError):
        return ""

def doing_now(root, signal=""):
    """Is the sitting that is open one whose product is a change, not a card?

    ASKED OF `course/config.py`, WHICH IS THE ONE ANSWER. This function used to
    hold its own copy of the aims that write -- a third list of the same three
    words, beside `sense`'s and the browser's -- and it read `tutorboard.json` by
    hand as well, so a family's default style reached the prompt
    and not the clock. A doing turn on a teaching turn's timeout is a turn killed
    at fifteen minutes with eight files changed and nothing committed.

    AND THREE TURNS ANSWER IT WITHOUT THE SITTING. A step handed over -- `POST
    /handover` -- is a doing turn inside a coaching sitting, and the sitting is
    left saying `coach` on purpose, because the next card is a coach card again.
    A ship is not part of the sitting at all. And a document asked for mid-
    sitting -- `POST /writeup` -- is deliberately not an aim change: a paper is a
    product rather than a style, so the sitting still says `drill` or `trace`
    while this turn writes one and compiles it. So the state says `teach` and is
    right about the evening; only the signal this turn was woken with says what
    THIS turn does. A REPAIR answers it the same way: a failed cluster job,
    fixed, checked, shipped and rerun, whatever its workspace teaches under
    (`jobs.relay_sense`).
    """
    if signal in ("handover", "rework", "ship", "writeup", "unfinished",
                  "repair"):
        # An UNFINISHED turn finishes a doing turn's report, on its clock.
        # A step handed over writes code. A ship reads a diff, judges it and
        # runs a push against a remote over a tailnet -- neither is a card, and
        # a doing turn on a teaching turn's clock is a turn killed with the work
        # half done. A REWORK is the same arithmetic on a document: thirty-three
        # pages rewritten and a LaTeX build at the end of it, which a teaching
        # turn's fifteen minutes kills with the deck half replaced. A WRITEUP is
        # that arithmetic from nothing: a paper drafted whole and built, which is
        # the longest of the four. A plain revision is not here on purpose -- it
        # changes what a note names and is over in a minute.
        return True
    try:
        with open(course_repo.session_path(root, "state.json"), "r", encoding="utf-8") as fh:
            st = json.load(fh) or {}
    except (OSError, ValueError):
        return False
    if st.get("session") == "make":
        return True
    try:
        # The sitting's own aim first, whatever kind of sitting it is: somebody
        # who asked for a deck about the machinery they were walking through has
        # asked for work to be done, and the kind of sitting does not say so.
        mine = config.clean_aim(st.get("aim"))
        if mine:
            return config.AIM_STANCE.get(mine) == "do"
        if (st.get("session") or "lecture") not in ("lecture", "homework"):
            return False
        return config.stance_for(root, st) == "do"
    except Exception:
        return False


def turn_timeout(cfg, root, spec=None, signal=""):
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
    if doing_now(root, signal):
        plain = max(plain, int(cfg.get("doing_timeout", 3600) or 3600))
    try:
        floor = int((spec or {}).get("timeout") or 0)
    except (TypeError, ValueError):
        floor = 0
    return max(plain, floor)

def handoff_clause(root):
    """What to tell a tutor about the handoff -- including that there is none."""
    return (prompts.HANDOFF_CLAUSE if handoff.handoff_applies(root, chapter_now(root))
            else prompts.NO_HANDOFF_CLAUSE)

# HOW LONG THE DAEMON WAITS FOR A MESSAGE, AND HOW LONG IT WAITS FOR THE THING
# THAT IS WAITING. Two numbers, and the second one exists because the first is a
# promise `board wait` cannot always keep.
#
# `cmd_wait` polls a file every quarter second and checks its own deadline
# between polls. A poll is an `open()` on a filer, and an NFS open can block in
# the kernel UNINTERRUPTIBLY -- state `D`, where no Python of that process runs
# again until the filer answers. Its deadline is therefore never reached, and
# nothing inside that command can fix it: a timeout enforced by the thing that
# might hang is not a timeout.
#
# Measured on 23 September 2026, in Probability: one waiter stuck 71 minutes in
# `nfs_set_open_stateid_locked` with `--timeout 300` on its command line. The
# daemon was healthy, its process alive, and it wrote no heartbeat and took no
# turn for the whole of it -- so the board said the tutor had not picked the
# message up, which was true and unactionable. A restart could not clear it
# either: the daemon was inside `communicate()` with no bound, so the signal was
# accepted and nothing acted on it.
#
# So the PARENT bounds the child. `WAIT_CEILING` is a margin over the deadline
# the child was given rather than a number of its own: past it, the child is not
# coming back, and a fresh one costs nothing. Both stay well inside
# `processes.AWAY_SILENCE`, which is what decides whether a board calls this
# daemon dead.
WAIT_TIMEOUT = 300
WAIT_CEILING = 420


def drop_waiter(p, log=None):
    """SIGKILL a `board wait` that is not coming back. Never blocks.

    SIGKILL RATHER THAN SIGTERM, and that is the safety property rather than
    impatience. A wedged waiter is inside a syscall; a signal to it is queued
    and delivered when the filer answers, which may be an hour later. On SIGTERM
    it would then run Python again -- and the next thing `cmd_wait` does on
    finding a message is `cmd_inbox`, which MARKS IT READ and prints it down a
    pipe nobody is holding any more. That is the student's message consumed and
    lost. SIGKILL cannot be caught, so no further line of that process runs.

    The group, because `start_new_session` put it in one, for the reason
    `run_turn` does it. And it is not waited on: reaping a process in
    uninterruptible sleep is the same hang one level up.
    """
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except OSError:
        pass
    if log:
        log.write("!! the wait for a message did not come back in %d s and has "
                  "been killed; asking again\n" % WAIT_CEILING)

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


def run_turn(cmd, root, log, timeout, env=None):
    """Run one turn to completion or to its cap. `(returncode, timed_out)`.

    THE WHOLE PROCESS GROUP, because `coli-code` is a shell that runs `srun`,
    and killing the shell alone orphans the step: the client goes on answering
    on the serving node, and the next turn is a second client on one KV slot.
    `start_new_session` puts the turn in a group of its own so there is a group
    to signal, and SIGTERM is given fifteen seconds before SIGKILL so a client
    that can close its transcript does.
    """
    # AND NOTHING ON STDIN. A client that reads stdin when it is not a terminal
    # appends whatever it finds to the prompt and BLOCKS until the far end
    # closes -- `codex exec` prints "Reading additional input from stdin..." and
    # waits, which for a `tutor headless` started from a terminal is for ever.
    # The turn then dies at its cap having said nothing, and on the board that
    # is indistinguishable from a model thinking for fifteen minutes. The
    # spawned daemon already passes DEVNULL to itself; this is the same answer
    # one level down, where it covers every way a turn is started.
    p = subprocess.Popen(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL,
                         start_new_session=True, env=at_root(root, env))
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

def turn_plan(spec, carried, recycle, signal=""):
    """Which recipe and which prompt this turn gets, and whether it is fresh.

    `carried` is how many turns the agent's current session already holds; 0
    means there is nothing to resume. `recycle` is `session_turns` from the
    config -- 0 resumes for ever. `signal` is what the inbox line says this turn
    is for, which matters for exactly one of them.

    Resuming saves re-reading the contract, the method and the lesson. It is not
    free: a resumed turn resends the whole conversation as input, so turn twenty
    pays for nineteen turns of history. Past a point a fresh session that reads
    the contract once and the lesson back through `board recap` is cheaper than
    carrying everything, so this is where the two are traded off.

    A REVISION IS ALWAYS FRESH, whatever is there to resume. It is not part of
    the lesson -- see `HEADLESS_REVISE_PROMPT` -- and resuming one into a lesson
    drags the lesson into the document and the document back into the lesson. A
    SHIP is the same: it reads a diff and pushes it, and a lesson resumed into
    that is a tutor that thinks the evening was about git.
    """
    recipe = spec.get("headless")
    first = spec.get("headless_first") or recipe
    if signal == "revise":
        return first, prompts.HEADLESS_REVISE_PROMPT, True
    # An overhaul is a revision's louder twin and runs fresh for the same
    # reason. What differs is only what it is allowed to do to the document.
    if signal == "rework":
        return first, prompts.HEADLESS_REWORK_PROMPT, True
    # A ship is the same shape: its own session, nothing of the lesson in it,
    # and nothing of it left in the lesson afterwards.
    if signal == "ship":
        return first, prompts.HEADLESS_SHIP_PROMPT, True
    # And a document asked for mid-sitting. Fresh for the revision's reason
    # rather than the ship's: the lesson resumed into it is exactly the narration
    # a write-up must not be, and this is the one turn whose product is that
    # document.
    if signal == "writeup":
        return first, prompts.HEADLESS_WRITEUP_PROMPT, True
    # AN UNFINISHED REPORT RESUMES: the turn that did the work holds what
    # it did, and the report is about exactly that. The prompt also works
    # cold, off `git status` and the card, for a client that cannot resume.
    if signal == "unfinished":
        return recipe, prompts.HEADLESS_UNFINISHED_PROMPT, False
    fresh = carried == 0 or bool(recycle) and carried >= recycle
    return (first if fresh else recipe,
            prompts.HEADLESS_FIRST_PROMPT if fresh else prompts.HEADLESS_RESUME_PROMPT,
            fresh)


def carry_after(signal, fresh, carried):
    """How many turns the agent's session carries once this turn has finished.

    Ordinarily: one if it started a new session, one more if it resumed. The
    exceptions are a revision, an overhaul, a ship and a document asked for
    mid-sitting, and they are the reason this is a function rather than an
    expression. A revision runs FRESH, so the agent's current conversation is now
    about a document -- and leaving the count at one would make the next turn of
    the LESSON resume into it, which is exactly the drag the revision was made
    fresh to avoid. Zero, so the next lesson turn starts its own session and
    reads the lesson back with `board recap`.
    """
    if signal in ("revise", "rework", "ship", "writeup"):
        return 0
    return 1 if fresh else carried + 1


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


def turn_signal(out):
    """The signal the inbox message carries, or "". Never raises."""
    for line in (out or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SIGNAL_TAG.match(line)
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


def woken_for(root, out):
    """`(signal, repair request ids)` for the batch `out`. Never raises."""
    signal = turn_signal(out)
    try:
        repairs = jobs.batch_repairs(root, out)
    except Exception:                                        # noqa: BLE001
        repairs = []
    if repairs and signal not in REPAIR_KEEPS:
        signal = jobs.REPAIR
    return signal, repairs
