"""One turn, and the wrap-up: what the runner (`runner/service.py`) runs.

`take_turn(ctx, message)` runs one turn and says whether the message is still
owed; `wrap_up(ctx)` runs the End turn that updates TUTOR.md. Each is a fresh
provider process in the Atlas root. The owed message lives on disk
(`agent.json`), so a server dying mid-turn loses nothing.
"""

import os
import threading
import time

from tutorboard import brief, jobs, limits, seeing
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


def jobs_since(root, since):
    """One line per job registered at or after `since`, oldest first."""
    out = []
    recs = sorted(jobs.records(root).values(),
                  key=lambda r: float(r.get("submitted") or 0))
    for r in recs:
        try:
            when = float(r.get("submitted") or 0)
        except (TypeError, ValueError):
            continue
        if when < since:
            continue
        out.append("`%s` on `%s`, %s: %s" % (
            r.get("jobid"), r.get("thread") or "no thread",
            str(r.get("state") or "PENDING").lower(),
            str(r.get("cmd") or "")[:160]))
    return out


def report_owed(where, this_signal, out, log=None):
    """What a turn owes once it exits with its newest card `pending`, or None:
    first an `[unfinished]` line waking it once more; after that, a `stopped`
    card listing what is uncommitted, so no placeholder outlives its turn.
    Either names the jobs registered since the placeholder."""
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
    try:
        since = os.path.getmtime(path)
    except OSError:
        since = 0.0
    wrote = lesson_cards.write_stopped(path, changed, jobs_since(root, since))
    if log:
        log.write("-- %s is still pending after [unfinished]; %s\n"
                  % (rel, "replaced it with what is on disk" if wrote
                     else "could not replace it"))
    return None

def for_this_turn(cfg, running, signal, log=None):
    """Who writes the next card: `(cfg, name, spec, why)`. The config is
    re-read every turn; `recipes.resolve` picks the provider, else the
    fallback (with `why`), else nobody. An `[unfinished]` report stays with
    the recipe that did the work while it can."""
    cfg = recipes.load_config()
    if (signal == "unfinished" and running
            and not recipes.unavailable(cfg, running)):
        return cfg, running, cfg["agents"].get(running) or {}, None
    name, why = recipes.resolve(cfg)
    if log and why:
        log.write("-- %s\n" % why)
    return cfg, name, (cfg["agents"].get(name) or {}) if name else {}, why

def handed(spec, prompt, context):
    """`(prompt, extra argv)` with `context` handed to the provider: as an
    appended system prompt where the recipe has `system_args` (the global
    CLAUDE.md still loads), else prepended to the prompt.
    """
    if not context:
        return prompt, []
    system = (spec or {}).get("system_args")
    if system:
        return prompt, [a.replace("{system}", context) for a in system]
    return context + "\n\n" + prompt, []


class Ctx(object):
    """One turn's state, built by the runner. `take_turn` reads and rebinds it.

    `repo` is the session's Repo, `root` its subject's root (the Atlas root
    while unbound), `cwd` the Atlas root, `live` the session directory, `env`
    the base environment, `on_start(process)` a hook. `cfg`, `agent_name` and
    `spec` are re-asked per turn by `for_this_turn`.
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
    the runner repairs, or the `[unfinished]` line."""
    out = message
    root, live, log, logpath = ctx.root, ctx.live, ctx.log, ctx.logpath
    pending = None
    owe(ctx, out)
    ctx.turns += 1
    this_signal, turn_repairs = turn.woken_for(
        root, out, ctx.repo.messages_path if getattr(ctx, "repo", None) else None)
    # `turn_started` is the runner's clock, which the board needs on reload.
    # The last failure stays recorded; `lesson.state._failure` ignores one
    # older than the turn in flight.
    daemon.agent_state(live, state="working", turns=ctx.turns,
                       turn_started=time.time(), turn_signal=this_signal,
                       turn_repairs=turn_repairs)
    log.write("\n=== %s turn %d ===\n%s\n" % (time.strftime("%H:%M:%S"), ctx.turns, out))

    # Heartbeat: a turn routinely outlasts the board's two-minute window.
    beating = threading.Event()

    def beat():
        while not beating.wait(30.0):
            daemon.agent_state(live, state="working", turns=ctx.turns)

    ticker = threading.Thread(target=beat, daemon=True)
    ticker.start()

    # WHO WRITES THIS ONE, asked per turn: the provider, else the fallback.
    ctx.cfg, name, spec, moved = for_this_turn(
        ctx.cfg, ctx.agent_name, this_signal, log)
    if not name:
        # Nobody can take it: the message stays owed and the board says why.
        beating.set()
        log.write("!! %s\n" % moved)
        daemon.agent_state(live, state="listening", last_error=moved,
                           failed_at=time.time(), failed_agent=ctx.agent_name,
                           retrying=False)
        return {"owed": owe(ctx, out), "error": moved}
    ctx.agent_name, ctx.spec = name, spec
    # Who writes, and why when it is the fallback, recorded before the turn.
    daemon.agent_state(live, agent=ctx.agent_name, agent_why=moved or None,
                       **daemon.not_this_agents_failure(live, ctx.agent_name))
    use, template = turn.turn_plan(ctx.spec, this_signal)
    # A script agent gets the raw inbox and builds its own context.
    fill = {"inbox": out.strip()}
    prompt = out.strip() if ctx.spec.get("raw_prompt") else template % fill
    # The brief and recap ride in the prompt, saving the turn two round trips.
    wants_brief, wants_recap = turn.context_plan(this_signal)
    context = ""
    if wants_recap and not ctx.spec.get("raw_prompt"):
        context = brief.turn_context(ctx.repo, this_signal, turn_repairs,
                                     brief=wants_brief)
        log.write("-- handed %s, %d characters, %s\n" % (
            "the brief and the recap" if wants_brief else "the recap",
            len(context), "as system prompt" if ctx.spec.get("system_args")
            else "above the prompt"))
    prompt, extra = handed(ctx.spec, prompt, context)
    cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompt) for a in use or []]
                           + extra)
    # Where this turn's words begin, to read back why it failed.
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    turn_env = turn.turn_environment(ctx.spec, base=ctx.env)
    # `board write` puts `by: <name>` on a card the fallback wrote.
    turn_env.pop("TUTORBOARD_FALLBACK", None)
    if moved:
        turn_env["TUTORBOARD_FALLBACK"] = ctx.agent_name
    timed_out = False
    cap = turn.turn_timeout(ctx.cfg, ctx.repo, ctx.spec,
                            jobs.REPAIR if turn_repairs else this_signal)
    try:
        if not use:
            raise OSError("'%s' has no headless recipe" % ctx.agent_name)
        rc, timed_out = turn.run_turn(cmd, ctx.cwd, log, cap, env=turn_env,
                                      on_start=ctx.on_start)
        err = None if rc == 0 else ("timed out" if timed_out
                                    else "exit %d" % rc)
    except OSError as exc:
        err = str(exc)
    finally:
        beating.set()

    # The turn's words beat its exit code: `is_error` in the result object
    # with exit 0 is a failed turn (`result_object_error`).
    said = usage.turn_output(logpath, mark)
    if not err and usage.result_object_error(said):
        err = "the agent reported a failure and exited 0"

    # A provider's "image never arrived" placeholder anywhere in the model's
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
    usage.record_cost(live, log, ctx.turns, ctx.agent_name, True,
                      usage.read_turn_usage(logpath, mark, ctx.spec.get("usage"), ctx.spec))

    if err:
        log.write("!! %s\n" % err)
        # Three causes, one symptom: the allowance ran out (asked first, and
        # proof the provider was reached), the machine cannot reach the
        # provider, or the agent failed.
        until = limits.reads_as_usage_limit(said)
        if until:
            # Per agent: one provider's limit says nothing of the fallback's.
            limits.mark_limited(until, agent=ctx.agent_name)
            log.write("!! '%s' is out of allowance here until %s\n"
                      % (ctx.agent_name,
                         time.strftime("%H:%M", time.localtime(until))))
            # `retrying` stops the board telling them to send again while this
            # loop re-queues the message itself.
            daemon.agent_state(live, state="listening", last_error="out of allowance",
                               failed_at=time.time(), failed_agent=ctx.agent_name,
                               limited=until, retrying=True)
            # The same message, whoever answers it.
            pending = owe(ctx, out)

            # The next turn goes to the fallback until the expiry passes.
            nxt, _ = recipes.resolve(recipes.load_config())
            if nxt and nxt != ctx.agent_name:
                log.write("-- the next turn goes to '%s'\n" % nxt)
            else:
                log.write("!! nothing else here can take it; turns wait "
                          "until the allowance returns -- `board limit` "
                          "says when\n")
            return {"owed": pending, "error": err}

        # Kept, because the reason below would overwrite "no egress" with the
        # exit code (`failWord` in board.js has a case for it).
        dark_machine = False
        if not egress.egress_ok(also=recipes.provider_probe_urls(ctx.cfg)):
            dark_machine = True
            log.write("!! nothing can get out from here; the turn may not be "
                      "the tutor's fault\n")
            daemon.agent_state(live, state="listening", last_error="no egress",
                               failed_at=time.time(), failed_agent=ctx.agent_name)
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
                           failed_at=time.time(), failed_agent=ctx.agent_name,
                           retrying=pending is not None)
    else:
        # A turn that went through proves this agent's allowance; cleared per
        # agent, never for all.
        if limits.limited_until(ctx.agent_name):
            log.write("-- a turn went through on '%s'; its allowance is "
                      "back\n" % ctx.agent_name)
            limits.clear_limited(ctx.agent_name)
        daemon.agent_state(live, state="listening", last_error=None,
                           failed_at=0, failed_agent=None, retrying=False)

    # The debt is settled here, once: `pending` is None where the turn went
    # through or failed beyond retry; re-queueing branches `continue` past
    # this. A turn ending on the `pending` placeholder is woken once more with
    # `[unfinished]` (`report_owed`).
    if pending is None:
        pending = report_owed(ctx.repo, this_signal, out, log)
    owe(ctx, pending)
    return {"owed": pending, "error": err}


def wrap_up(ctx):
    """The End turn: TUTOR.md brought up to date with `board memo`.
    `(wrote, why)`. Only End queues it. Who writes it is asked again, so a
    stood-down provider does not waste it; with nobody able, it is skipped.
    """
    log, logpath, root = ctx.log, ctx.logpath, ctx.root
    ctx.cfg = recipes.load_config()
    took, why_took = recipes.resolve(ctx.cfg)
    if not took:
        log.write("\n=== %s wrap-up ===\n!! no wrap-up was attempted: %s\n"
                  % (time.strftime("%H:%M:%S"), why_took))
        return False, why_took
    if took != ctx.agent_name:
        log.write("-- the wrap-up goes to '%s'%s\n"
                  % (took, (": " + why_took) if why_took else ""))
    ctx.agent_name, ctx.spec = took, ctx.cfg["agents"].get(took) or {}
    daemon.agent_state(ctx.live, state="wrapping up")
    log.write("\n=== %s wrap-up ===\n" % time.strftime("%H:%M:%S"))
    # The recipe key and timeout keep the name `handoff`, so configs still work.
    wrap = ctx.spec.get("handoff") or turn.fresh_recipe(ctx.spec) or []
    prompt, extra = handed(ctx.spec, prompts.WRAPUP_PROMPT,
                           brief.turn_context(ctx.repo))
    cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompt) for a in wrap]
                           + extra)
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    landing = os.path.join(root, "TUTOR.md")
    try:
        before = os.path.getmtime(landing)
    except OSError:
        before = 0
    why = None
    try:
        rc, timed_out = turn.run_turn(
            cmd, ctx.cwd, log, ctx.cfg.get("handoff_timeout", 600),
            env=turn.turn_environment(ctx.spec, base=ctx.env), on_start=ctx.on_start)
        usage.record_cost(ctx.live, log, ctx.turns + 1, ctx.agent_name, True,
                          usage.read_turn_usage(logpath, mark, ctx.spec.get("usage"), ctx.spec))
        # Wrote it: exit 0, no reported failure, and the file is newer than
        # the turn.
        said = usage.turn_output(logpath, mark)
        failed = ((rc != 0 and ("timed out" if timed_out else "exit %d" % rc))
                  or (usage.result_object_error(said)
                      and "the agent reported a failure and exited 0"))
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
    """The End turn of a notes canvas: bind if unbound, transcribe `pages`
    into `docs/<slug>/notes.md` (`board writeup new --md`), `board build` it.
    `(ok, why)`. No brief or recap: the pages are the whole session."""
    log, logpath = ctx.log, ctx.logpath
    ctx.cfg = recipes.load_config()
    took, why_took = recipes.resolve(ctx.cfg)
    if not took:
        log.write("\n=== %s notes ===\n!! no transcript was attempted: %s\n"
                  % (time.strftime("%H:%M:%S"), why_took))
        return False, why_took
    ctx.agent_name, ctx.spec = took, ctx.cfg["agents"].get(took) or {}
    daemon.agent_state(ctx.live, state="wrapping up")
    log.write("\n=== %s notes ===\n" % time.strftime("%H:%M:%S"))
    prompt = prompts.NOTES_PROMPT % {
        "pages": "\n".join("- page %d: %s" % (i, p)
                           for i, p in enumerate(pages, start=1)),
        "title": str(title or "Notes").replace('"', "'"),
        "subject": subject or "no course or project yet"}
    cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompt)
                                      for a in turn.fresh_recipe(ctx.spec) or []])
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    why = None
    try:
        rc, timed_out = turn.run_turn(
            cmd, ctx.cwd, log, ctx.cfg.get("doing_timeout", 3600),
            env=turn.turn_environment(ctx.spec, base=ctx.env), on_start=ctx.on_start)
        usage.record_cost(ctx.live, log, ctx.turns + 1, ctx.agent_name, True,
                          usage.read_turn_usage(logpath, mark, ctx.spec.get("usage"),
                                                ctx.spec))
        said = usage.turn_output(logpath, mark)
        failed = ((rc != 0 and ("timed out" if timed_out else "exit %d" % rc))
                  or (usage.result_object_error(said)
                      and "the agent reported a failure and exited 0"))
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

