"""One turn, and the wrap-up: what the runner (`runner/service.py`) runs.

`take_turn(ctx, message)` runs one turn on a session and says whether the
message is still owed; `wrap_up(ctx)` runs the End turn that writes the
handoff. Both run a fresh provider process in the Atlas root. `ctx` is a `Ctx`
the runner builds per turn: the session's Repo, the cwd, the log, the
environment, and who takes the turn.
"""

import os
import threading
import time

from tutorboard import brief, handoff, jobs, limits, seeing
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
    """What a turn owes once it exits with its newest card `pending`, or None.

    The first time, the `[unfinished]` line that wakes it once more. After an
    `[unfinished]` turn that also left it pending, nothing more is woken: the
    card is replaced by a `stopped` one listing what is uncommitted under the
    work, so the board never shows a placeholder for a turn that has ended.
    It always names the jobs registered since the placeholder was written,
    which is when the work began.
    """
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
    changed = lesson_git.uncommitted(root) or []
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
    """Who writes the next card: `(cfg, name, spec, why)`.

    The config is re-read every turn, so `/default-agent` lands on the next
    card with nothing restarted. `recipes.resolve` decides: the provider, else
    the fallback with `why` saying so, else nobody (`name` None). An
    `[unfinished]` report stays with the recipe that did the work while that
    one can still take a turn.
    """
    cfg = recipes.load_config()
    if (signal == "unfinished" and running
            and not recipes.unavailable(cfg, running)):
        return cfg, running, cfg["agents"].get(running) or {}, None
    name, why = recipes.resolve(cfg)
    if log and why:
        log.write("-- %s\n" % why)
    return cfg, name, (cfg["agents"].get(name) or {}) if name else {}, why

def handed(spec, prompt, context):
    """`(prompt, extra argv)` with `context` handed to the provider.

    A recipe with `system_args` (claude's `--append-system-prompt {system}`)
    takes it as system prompt, so the prompt stays the turn's own; any other
    provider reads it prepended to the prompt. Either way it comes first, and
    the prompts say it is "above". The global CLAUDE.md still loads: this
    appends to the system prompt rather than replacing it.
    """
    if not context:
        return prompt, []
    system = (spec or {}).get("system_args")
    if system:
        return prompt, [a.replace("{system}", context) for a in system]
    return context + "\n\n" + prompt, []


class Ctx(object):
    """One turn's state, built by the runner. `take_turn` reads and rebinds it.

    `repo` is the session's Repo and `root` its subject's root (the Atlas root
    while unbound); `cwd` is where the provider runs, the Atlas root; `live`
    the session directory; `env` the environment every turn gets before its
    recipe's own; `on_start(process)` runs once the provider exists. `cfg`,
    `agent_name` and `spec` are THIS turn's answer to who writes, re-asked by
    `for_this_turn`. `turns` counts the session's turns.
    """

    def __init__(self, **kw):
        self.env = None
        self.on_start = None
        self.__dict__.update(kw)


# AN OWED MESSAGE LIVES ON DISK, NOT IN THIS PROCESS. The runner writes it
# into `agent.json` before it marks the inbox lines read, and every path out
# of a turn rewrites it through `owe` with what is still owed. A server that
# dies mid-turn therefore loses nothing: its successor reads `owed` back and
# queues it (`service.Runner.recover`).
def owe(ctx, msg):
    daemon.agent_state(ctx.live, owed=msg or None)
    return msg


def take_turn(ctx, message):
    """Run one turn on `message`. `{"owed": message or None, "error": ...}`.

    `owed` is the message the next turn must answer again -- this one, after a
    failure the runner repairs itself -- or the `[unfinished]` line that wakes
    the turn to write the report it left owed, or None. `error` is why the turn
    failed, or None.
    """
    out = message
    root, live, log, logpath = ctx.root, ctx.live, ctx.log, ctx.logpath
    pending = None
    owe(ctx, out)
    ctx.turns += 1
    this_signal, turn_repairs = turn.woken_for(
        root, out, ctx.repo.messages_path if getattr(ctx, "repo", None) else None)
    # `turn_started` is the runner's clock, and the board needs it: its own
    # measure of how long a turn has been going starts when it first SEES
    # the working state, which on a reload or a second device is nowhere
    # near when the turn began.
    # AND THE LAST FAILURE STAYS ON THE RECORD WHILE THIS ONE RUNS. A turn that
    # GOES THROUGH clears it, below. What stops the board painting an old
    # failure over a running turn is `lesson.state._failure`, which does not
    # report one older than the turn in flight.
    daemon.agent_state(live, state="working", turns=ctx.turns,
                       turn_started=time.time(), turn_signal=this_signal,
                       turn_repairs=turn_repairs)
    log.write("\n=== %s turn %d ===\n%s\n" % (time.strftime("%H:%M:%S"), ctx.turns, out))

    # Keep saying so while the turn runs: a turn that reads a chapter and
    # writes a card routinely outlasts the board's two-minute window.
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
        # Nobody here can take it. The message stays owed for the next wake,
        # and the board says why in the resolver's own sentence.
        beating.set()
        log.write("!! %s\n" % moved)
        daemon.agent_state(live, state="listening", last_error=moved,
                           failed_at=time.time(), failed_agent=ctx.agent_name,
                           retrying=False)
        return {"owed": owe(ctx, out), "error": moved}
    ctx.agent_name, ctx.spec = name, spec
    # WHO IS WRITING, AND WHY WHEN IT IS THE FALLBACK, before the turn. The
    # strip paints both off this record, and `board write` stamps the card.
    daemon.agent_state(live, agent=ctx.agent_name, agent_why=moved or None,
                       **daemon.not_this_agents_failure(live, ctx.agent_name))
    use, template = turn.turn_plan(ctx.spec, this_signal)
    # A script agent builds its own context, so it gets the raw inbox rather
    # than the instruction prompt the interactive agents expect.
    fill = {"inbox": out.strip(),
            # Only the chapter that is open. A handoff about another one is
            # parked as this is read, so a tutor is never handed the last
            # chapter's unfinished business as though it were this one's.
            "handoff": turn.handoff_clause(ctx.repo)}
    prompt = out.strip() if ctx.spec.get("raw_prompt") else template % fill
    # THE BRIEF AND THE RECAP RIDE IN THE PROMPT, rendered here rather than
    # fetched by the turn: two round trips fewer, each resending the whole
    # conversation. A script agent builds its own context and gets neither.
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
    # Where this turn's own words begin, so that if it fails we can read
    # back what it said rather than guess at why.
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

    # WHAT THE TURN SAID, READ BEFORE THE EXIT CODE IS BELIEVED. An exit
    # code is the agent summarising itself, and an agent that writes
    # `is_error` into its own result object and then exits 0 has failed the
    # turn whatever the number says: no card is written, and a board that
    # took the number would go back to `listening` with nothing to show and
    # nothing to say -- the one state this tool must never present as
    # normal. The words win. See `result_object_error`.
    said = usage.turn_output(logpath, mark)
    if not err and usage.result_object_error(said):
        err = "the agent reported a failure and exited 0"

    # AND THE PAGE THAT NEVER ARRIVED, WHICH EXITS 0 AND READS AS A LESSON.
    # `board see` refuses an answer carrying one of these -- `blind_answer`
    # in `tutorboard/seeing.py` -- but a tutor whose model can see is told by
    # the turn prompt to open the PNG itself, so the slate goes through the
    # binary's own Read tool and never passes that guard. An endpoint that
    # cannot take the image block substitutes the placeholder INTO THE
    # CONVERSATION and answers 200, so the model marks handwriting it was
    # never shown, confidently, and the exit code agrees with it. That is
    # the one failure on this board a person cannot catch by reading the
    # card, because the card is fluent.
    #
    # The list is imported rather than repeated: a second copy of a
    # provider's placeholder wording is a table that goes stale in the file
    # nobody is looking at. Asked of everything the model said this turn,
    # not of a card, because the substitution happens wherever the image
    # was handed over -- and not of the tools' output, which quotes files.
    if not err:
        blind = seeing.blind_answer(usage.turn_text(said))
        if blind:
            err = ("the page never reached the model -- it answered around "
                   "%s, so anything it said about the handwriting is "
                   "invented" % blind)

    # WHAT IT COST, WHETHER OR NOT IT WORKED. A turn that died on its last
    # round trip is billed for the ones before it, and a failure that is
    # missing from `cost.jsonl` is a provider whose bad evening is invisible
    # in the one place the money is counted. Nothing is written where the
    # turn said nothing: `read_turn_usage` returns {} and `record_cost`
    # stops there.
    usage.record_cost(live, log, ctx.turns, ctx.agent_name, True,
                      usage.read_turn_usage(logpath, mark, ctx.spec.get("usage"), ctx.spec))

    if err:
        log.write("!! %s\n" % err)
        # A failed turn has three very different causes wearing one symptom,
        # and they need telling apart. The model refusing, or the agent
        # falling over, is nothing this can fix. The machine being unable to
        # reach the provider at all is. And the allowance having run out is
        # neither: nothing is broken, and the same turn will succeed later
        # with not one thing changed.
        #
        # The allowance is asked about first because it is the one the turn
        # itself answers -- the agent said so in its output, and a provider
        # that could say so is a provider we plainly reached, which settles
        # the egress question at the same time and for free.
        until = limits.reads_as_usage_limit(said)
        if until:
            # THIS AGENT, NOT THIS MACHINE. Claude running out says nothing
            # about DeepSeek, and a machine-wide mark would take the
            # fallback out along with the thing it is falling back from.
            limits.mark_limited(until, agent=ctx.agent_name)
            log.write("!! '%s' is out of allowance here until %s\n"
                      % (ctx.agent_name,
                         time.strftime("%H:%M", time.localtime(until))))
            # `retrying`, BECAUSE THE DAEMON IS. The strip reads exactly
            # this field: without it the board says "send again to carry
            # on", and a student who obeys queues a second copy of their
            # work behind a turn this loop was about to take itself. The
            # message is re-queued four lines down; that is what retrying
            # means.
            daemon.agent_state(live, state="listening", last_error="out of allowance",
                               failed_at=time.time(), failed_agent=ctx.agent_name,
                               limited=until, retrying=True)
            # The student sent something and got nothing. Whoever ends up
            # answering it, it is the same message.
            pending = owe(ctx, out)

            # AND THE NEXT TURN GOES TO THE FALLBACK: `recipes.resolve`
            # will not offer this one again until the expiry passes. With no
            # fallback able to take it, the message stays owed and the board
            # says why.
            nxt, _ = recipes.resolve(recipes.load_config())
            if nxt and nxt != ctx.agent_name:
                log.write("-- the next turn goes to '%s'\n" % nxt)
            else:
                log.write("!! nothing else here can take it; turns wait "
                          "until the allowance returns -- `board limit` "
                          "says when\n")
            return {"owed": pending, "error": err}

        # AND WHETHER IT WAS THE MACHINE, kept, because the sentence below
        # recomputes the reason from the turn's own words and would write
        # `exit 1` over the top of it. `failWord` in `board.js` has a case
        # for this one -- "this machine cannot reach the internet" -- and it
        # never once fired, because by the time the board read the record
        # the reason had been replaced by the exit code.
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
                # The student sent something and got nothing. Put the same
                # inbox back so the next pass answers it rather than waiting
                # for them to send again.
                pending = owe(ctx, out)
            else:
                log.write("!! egress still broken (%s); turns will keep "
                          "failing until the network is fixed\n" % detail)
        # Stamped, so the board can tell a failure that just happened from
        # one an hour ago -- and can say so at all, which it could not. A
        # student whose working was handed in and answered by nothing is the
        # one state this tool must never present as normal.
        # In words, not as an exit code. See `failure_reason`.
        why = "no egress" if dark_machine else usage.failure_reason(said, err)
        daemon.agent_state(live, state="listening", last_error=why,
                           failed_at=time.time(), failed_agent=ctx.agent_name,
                           retrying=pending is not None)
    else:
        # A turn that went through on this agent is proof of THIS agent's
        # allowance, whatever the record still says. The reset time a
        # provider hands out is a promise; this is a measurement. Per agent,
        # because clearing the lot would un-limit a provider nothing has
        # heard from since it ran out.
        if limits.limited_until(ctx.agent_name):
            log.write("-- a turn went through on '%s'; its allowance is "
                      "back\n" % ctx.agent_name)
            limits.clear_limited(ctx.agent_name)
        daemon.agent_state(live, state="listening", last_error=None,
                           failed_at=0, failed_agent=None, retrying=False)

    # AND THE DEBT IS SETTLED HERE, ONCE, BY WHAT THE TURN LEFT BEHIND.
    # `pending` is this loop's own answer to "is the same message still
    # owed": None where the turn went through, and None where it failed for
    # something no retry repairs -- the model refused, the recipe is wrong --
    # which is the case the board tells the student to send again for. The
    # branches that DO re-queue it set `pending` and then `continue` past
    # this, so nothing here can un-owe a message the daemon has promised to
    # answer. Every path out of a turn therefore leaves the record saying the
    # truth about it, rather than every path having to remember to.
    #
    # AND A TURN ENDS ON A REPORT. Where nothing else is owed and the newest
    # card is still the `pending` placeholder, the turn is woken once more
    # with `[unfinished]`; after that, the card is replaced by what is on
    # disk. See `report_owed`.
    if pending is None:
        pending = report_owed(ctx.repo, this_signal, out, log)
    owe(ctx, pending)
    return {"owed": pending, "error": err}


def wrap_up(ctx):
    """The End turn: the handoff, piped to `board handoff`. `(wrote, why)`.

    Only End queues it (`POST /s/<id>/end`); a server stopping, or a turn
    recovered after one died, never does. Who writes it is asked again here,
    so a provider the last turn stood down does not get the one turn that must
    not be wasted; with nobody able to, it is skipped and says so.
    """
    log, logpath, root = ctx.log, ctx.logpath, ctx.root
    ctx.cfg = recipes.load_config()
    took, why_took = recipes.resolve(ctx.cfg)
    if not took:
        log.write("\n=== %s handoff ===\n!! no handoff was attempted: %s\n"
                  % (time.strftime("%H:%M:%S"), why_took))
        return False, why_took
    if took != ctx.agent_name:
        log.write("-- the handoff goes to '%s'%s\n"
                  % (took, (": " + why_took) if why_took else ""))
    ctx.agent_name, ctx.spec = took, ctx.cfg["agents"].get(took) or {}
    daemon.agent_state(ctx.live, state="wrapping up")
    log.write("\n=== %s handoff ===\n" % time.strftime("%H:%M:%S"))
    chapter = turn.chapter_now(ctx.repo)
    wrap = ctx.spec.get("handoff") or turn.fresh_recipe(ctx.spec) or []
    prompt, extra = handed(ctx.spec, prompts.HANDOFF_PROMPT,
                           brief.turn_context(ctx.repo, brief=False))
    cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompt) for a in wrap]
                           + extra)
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    landing = os.path.join(root, "HANDOFF.md")
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
        # WHETHER THIS TURN WROTE ONE, which is not whether the file is there:
        # the turn exited 0, did not report its own failure, and the file is
        # newer than the turn. Only then is it stamped with its chapter.
        said = usage.turn_output(logpath, mark)
        failed = ((rc != 0 and ("timed out" if timed_out else "exit %d" % rc))
                  or (usage.result_object_error(said)
                      and "the agent reported a failure and exited 0"))
        try:
            wrote = not failed and os.path.getmtime(landing) > before
        except OSError:
            wrote = False
        if wrote:
            handoff.stamp_handoff(root, chapter)
            log.write("handoff written\n")
        elif failed:
            why = usage.failure_reason(said, failed)
            log.write("!! the handoff turn failed (%s); HANDOFF.md is whatever "
                      "the last session left\n" % why)
        else:
            why = "no HANDOFF.md was written"
            log.write("!! %s\n" % why)
    except OSError as exc:
        wrote, why = False, str(exc)
        log.write("!! handoff failed: %s\n" % exc)
    daemon.agent_state(ctx.live, state="listening", turn_pid=None)
    return wrote, why
