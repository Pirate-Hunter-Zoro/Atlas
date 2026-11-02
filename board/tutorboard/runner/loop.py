"""One turn, and the wrap-up: what the runner (`runner/service.py`) runs.

`take_turn(ctx, message)` runs one turn and says whether the message is still
owed; `wrap_up(ctx)` runs the End turn that updates TUTOR.md, and writes up a
session sent to its subject only at End. Each is a fresh DeepSeek process
(OpenCode) in the Atlas root. The owed message lives on disk (`agent.json`), so
a server dying mid-turn loses nothing.
"""

import os
import threading
import time

from tutorboard import brief, limits, seeing, subjects
from tutorboard.agents import recipes, usage
from tutorboard.lesson import cards as lesson_cards, git as lesson_git
from tutorboard.net import egress
from tutorboard.runner import daemon, prompts, turn

def unfinished_line(out, card):
    """The inbox line that wakes a turn to write the report it left owed.

    Tagged `[unfinished]` where `turn_signal` reads it, naming the placeholder,
    with the message the turn was answering kept below it.
    """
    return ("[%s] [unfinished] The turn before this one exited with %s still "
            "the placeholder. Write the report over it.\n\nIt was answering:\n\n%s"
            % (time.strftime("%Y-%m-%d %H:%M:%S"), card, (out or "").strip()))


def report_owed(where, this_signal, out, log=None):
    """What a turn owes once it exits with its newest card `pending`, or None:
    first an `[unfinished]` line waking it once more; after that, a `stopped`
    card listing what is uncommitted, so no placeholder outlives its turn."""
    repo = turn.as_repo(where)
    root = repo.root
    path, meta = lesson_cards.newest(repo.cards)
    if not path or not lesson_cards.is_pending(meta):
        return None
    rel = os.path.relpath(path, root)
    if this_signal != "unfinished":
        if log:
            log.write("-- the turn exited with %s still pending; waking it once "
                      "more to report\n" % rel)
        return unfinished_line(out, rel)
    changed = lesson_git.uncommitted(root, session=repo.session) or []
    wrote = lesson_cards.write_stopped(path, changed)
    if log:
        log.write("-- %s is still pending after [unfinished]; %s\n"
                  % (rel, "replaced it with what is on disk" if wrote
                     else "could not replace it"))
    return None

def handed(prompt, context):
    """The prompt with `context` (the brief, the recap) above it."""
    return context + "\n\n" + prompt if context else prompt


class Ctx(object):
    """One turn's state, built by the runner. `take_turn` reads and rebinds it.

    `repo` is the session's Repo, `root` its subject's root (the Atlas root
    while unbound), `cwd` the Atlas root, `live` the session directory, `env`
    the base environment, `on_start(process)` a hook. `cfg` and `spec` are
    re-read per turn.
    """

    def __init__(self, **kw):
        self.env = None
        self.on_start = None
        self.__dict__.update(kw)


# The owed message is rewritten into `agent.json` on every path out of a turn,
# so a successor server re-queues it (`service.Runner.recover`).
def owe(ctx, msg):
    daemon.agent_state(ctx.live, owed=msg or None)
    return msg


def take_turn(ctx, message):
    """Run one turn on `message`. `{"owed": message or None, "error": ...}`.
    `owed` is what the next turn must answer: this message after a failure
    the runner retries, or the `[unfinished]` line."""
    out = message
    root, live, log, logpath = ctx.root, ctx.live, ctx.log, ctx.logpath
    pending = None
    owe(ctx, out)
    ctx.turns += 1
    this_signal = turn.turn_signal(out)
    # `turn_started` is the runner's clock, which the board needs on reload.
    # The last failure stays recorded; `lesson.state._failure` ignores one
    # older than the turn in flight.
    daemon.agent_state(live, state="working", turns=ctx.turns,
                       turn_started=time.time(), turn_signal=this_signal)
    log.write("\n=== %s turn %d ===\n%s\n" % (time.strftime("%H:%M:%S"), ctx.turns, out))

    # Heartbeat: a turn routinely outlasts the board's two-minute window.
    beating = threading.Event()

    def beat():
        while not beating.wait(30.0):
            daemon.agent_state(live, state="working", turns=ctx.turns)

    ticker = threading.Thread(target=beat, daemon=True)
    ticker.start()

    # Re-read per turn, so a config edit lands without a restart.
    ctx.cfg, ctx.spec = recipes.load_config(), recipes.spec()
    why = recipes.ready()
    if why:
        # It cannot run here now: the message stays owed and the board says why.
        beating.set()
        log.write("!! %s\n" % why)
        daemon.agent_state(live, state="listening", last_error=why,
                           failed_at=time.time(), retrying=False)
        return {"owed": owe(ctx, out), "error": why}
    daemon.agent_state(live, agent=recipes.NAME)
    template = turn.turn_prompt(this_signal)
    prompt = template % {"inbox": out.strip()}
    # The brief and recap ride in the prompt, saving the turn two round trips.
    wants_brief, wants_recap = turn.context_plan(this_signal)
    context = ""
    if wants_recap:
        context = brief.turn_context(ctx.repo, this_signal, brief=wants_brief)
        log.write("-- handed %s, %d characters, above the prompt\n" % (
            "the brief and the recap" if wants_brief else "the recap",
            len(context)))
    cmd = recipes.argv(handed(prompt, context), ctx.spec)
    # Where this turn's words begin, to read back why it failed.
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    turn_env = turn.turn_environment(ctx.spec, base=ctx.env)
    timed_out = False
    cap = turn.turn_timeout(ctx.cfg, ctx.repo, this_signal)
    try:
        rc, timed_out = turn.run_turn(cmd, ctx.cwd, log, cap, env=turn_env,
                                      on_start=ctx.on_start)
        err = None if rc == 0 else ("timed out" if timed_out
                                    else "exit %d" % rc)
    except OSError as exc:
        err = str(exc)
    finally:
        beating.set()

    said = usage.turn_output(logpath, mark)

    # DeepSeek's "image never arrived" placeholder anywhere in the model's
    # words fails the turn, since the model then marks unseen handwriting
    # fluently. Read from what the model said, not tool output, which quotes
    # files; the wording list is `seeing`'s, not a copy.
    if not err:
        blind = seeing.blind_answer(usage.turn_text(said))
        if blind:
            err = ("the page never reached the model -- it answered around "
                   "%s, so anything it said about the handwriting is "
                   "invented" % blind)

    # Cost is recorded whether or not the turn worked.
    usage.record_cost(live, log, ctx.turns, True,
                      usage.read_turn_usage(logpath, mark, ctx.spec))

    if err:
        log.write("!! %s\n" % err)
        # Three causes, one symptom: the allowance ran out (asked first, and
        # proof DeepSeek was reached), the machine cannot reach DeepSeek, or
        # the agent failed.
        until = limits.reads_as_usage_limit(said)
        if until:
            limits.mark_limited(until)
            log.write("!! DeepSeek is out of allowance here until %s; the "
                      "message waits for it -- `board limit` says when\n"
                      % time.strftime("%H:%M", time.localtime(until)))
            # `retrying` stops the board telling them to send again: the
            # message stays owed and the next turn answers it.
            daemon.agent_state(live, state="listening", last_error="out of allowance",
                               failed_at=time.time(), limited=until, retrying=True)
            return {"owed": owe(ctx, out), "error": err}

        # Kept, because the reason below would overwrite "no egress" with the
        # exit code (`failWord` in board.js has a case for it).
        dark_machine = False
        if not egress.egress_ok():
            dark_machine = True
            log.write("!! DeepSeek cannot be reached from here; the turn may "
                      "not be the tutor's fault\n")
            daemon.agent_state(live, state="listening", last_error="no egress",
                               failed_at=time.time())
            fixed, detail = egress.rotate_exit_node(
                log=lambda m: log.write("   %s\n" % m))
            if fixed:
                log.write("-- egress repaired via %s; retrying the turn\n" % detail)
                # Re-queue the same inbox so they need not send again.
                pending = owe(ctx, out)
            else:
                log.write("!! egress still broken (%s); turns will keep "
                          "failing until the network is fixed\n" % detail)
        # Stamped, so the board tells a fresh failure from an old one; in
        # words, not an exit code (`failure_reason`).
        why = "no egress" if dark_machine else usage.failure_reason(said, err)
        daemon.agent_state(live, state="listening", last_error=why,
                           failed_at=time.time(), retrying=pending is not None)
    else:
        # A turn that went through proves the allowance and the route.
        if limits.limited_until():
            log.write("-- a turn went through; DeepSeek's allowance is back\n")
            limits.clear_limited()
        egress.clear_unreachable()
        daemon.agent_state(live, state="listening", last_error=None,
                           failed_at=0, retrying=False)

    # The debt is settled here, once: `pending` is None where the turn went
    # through or failed beyond retry; re-queueing branches `continue` past
    # this. A turn ending on the `pending` placeholder is woken once more with
    # `[unfinished]` (`report_owed`).
    if pending is None:
        pending = report_owed(ctx.repo, this_signal, out, log)
    owe(ctx, pending)
    return {"owed": pending, "error": err}


def wrap_up(ctx, sent=None):
    """The End turn: TUTOR.md brought up to date with `board memo`.
    `(wrote, why)`. Only End queues it. Skipped when DeepSeek cannot take a
    turn here now (`recipes.ready`).
    `sent` names the subject of a session sent there only at End: the turn
    writes up its agreed answers first (`WRAPUP_SENT_PROMPT`), on the doing
    timeout.
    """
    log, logpath, root = ctx.log, ctx.logpath, ctx.root
    ctx.cfg, ctx.spec = recipes.load_config(), recipes.spec()
    why_not = recipes.ready()
    if why_not:
        log.write("\n=== %s wrap-up ===\n!! no wrap-up was attempted: %s\n"
                  % (time.strftime("%H:%M:%S"), why_not))
        return False, why_not
    daemon.agent_state(ctx.live, state="wrapping up")
    log.write("\n=== %s wrap-up ===\n" % time.strftime("%H:%M:%S"))
    said = prompts.WRAPUP_PROMPT
    if sent:
        log.write("-- sent to %s at End: its answers are written up first\n" % sent)
        said += "\n\n" + prompts.WRAPUP_SENT_PROMPT % {"subject": sent}
    cmd = recipes.argv(handed(said, brief.turn_context(ctx.repo)), ctx.spec)
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    landing = os.path.join(root, "TUTOR.md")
    try:
        before = os.path.getmtime(landing)
    except OSError:
        before = 0
    why = None
    try:
        rc, timed_out = turn.run_turn(
            cmd, ctx.cwd, log,
            ctx.cfg.get("doing_timeout", 3600) if sent
            else ctx.cfg.get("handoff_timeout", 600),
            env=turn.turn_environment(ctx.spec, base=ctx.env), on_start=ctx.on_start)
        usage.record_cost(ctx.live, log, ctx.turns + 1, True,
                          usage.read_turn_usage(logpath, mark, ctx.spec))
        # Wrote it: exit 0 and the file is newer than the turn.
        said = usage.turn_output(logpath, mark)
        failed = rc != 0 and ("timed out" if timed_out else "exit %d" % rc)
        try:
            wrote = not failed and os.path.getmtime(landing) > before
        except OSError:
            wrote = False
        if wrote:
            log.write("TUTOR.md written\n")
        elif failed:
            why = usage.failure_reason(said, failed)
            log.write("!! the wrap-up turn failed (%s); TUTOR.md is whatever "
                      "the last turn left\n" % why)
        else:
            why = "TUTOR.md was not touched"
            log.write("!! %s\n" % why)
    except OSError as exc:
        wrote, why = False, str(exc)
        log.write("!! the wrap-up failed: %s\n" % exc)
    daemon.agent_state(ctx.live, state="listening", turn_pid=None)
    return wrote, why


def notes_up(ctx, pages, title, subject):
    """The End turn of a notes canvas: bind if unbound (to Random lessons,
    `subjects.SCRATCH`, unless the pages plainly belong elsewhere), transcribe `pages`
    into `docs/<slug>/notes.md` (`board writeup new --md`), `board build` it.
    `(ok, why)`. No brief or recap: the pages are the whole session."""
    log, logpath = ctx.log, ctx.logpath
    ctx.cfg, ctx.spec = recipes.load_config(), recipes.spec()
    why_not = recipes.ready()
    if why_not:
        log.write("\n=== %s notes ===\n!! no transcript was attempted: %s\n"
                  % (time.strftime("%H:%M:%S"), why_not))
        return False, why_not
    daemon.agent_state(ctx.live, state="wrapping up")
    log.write("\n=== %s notes ===\n" % time.strftime("%H:%M:%S"))
    prompt = prompts.NOTES_PROMPT % {
        "pages": "\n".join("- page %d: %s" % (i, p)
                           for i, p in enumerate(pages, start=1)),
        "title": str(title or "Notes").replace('"', "'"),
        "subject": subject or "no course or project yet",
        "scratch": subjects.SCRATCH}
    cmd = recipes.argv(prompt, ctx.spec)
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    why = None
    try:
        rc, timed_out = turn.run_turn(
            cmd, ctx.cwd, log, ctx.cfg.get("doing_timeout", 3600),
            env=turn.turn_environment(ctx.spec, base=ctx.env), on_start=ctx.on_start)
        usage.record_cost(ctx.live, log, ctx.turns + 1, True,
                          usage.read_turn_usage(logpath, mark, ctx.spec))
        said = usage.turn_output(logpath, mark)
        failed = rc != 0 and ("timed out" if timed_out else "exit %d" % rc)
        if failed:
            why = usage.failure_reason(said, failed)
            log.write("!! the notes turn failed (%s)\n" % why)
        else:
            log.write("notes transcribed\n")
    except OSError as exc:
        why = str(exc)
        log.write("!! the notes turn failed: %s\n" % exc)
    daemon.agent_state(ctx.live, state="listening", turn_pid=None)
    return why is None, why

