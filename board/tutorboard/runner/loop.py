"""The tutor daemon's loop: wait for a message, take a turn, settle what it owes.

`headless` is the daemon: it comes up, blocks on `board wait`, and hands each
message to `take_turn`, which runs one turn and says whether the message is
still owed. When the daemon is stopped it runs the wrap-up turn that writes
HANDOFF.md.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time

from tutorboard import gitops, handoff, jobs, keys, limits, seeing, stamp
from tutorboard.agents import recipes, usage
from tutorboard.course import threads as course_threads
from tutorboard.lesson import cards as lesson_cards, git as lesson_git
from tutorboard.net import egress
from tutorboard.runner import daemon, prompts, turn
from tutorboard.course import repo as course_repo

def unfinished_line(out, card):
    """The inbox line that wakes a turn to write the report it left owed.

    Tagged `[unfinished]` where `turn_signal` reads it, naming the placeholder,
    with the message the turn was answering kept below it.
    """
    return ("[%s] [unfinished] The turn before this one exited with %s still "
            "the placeholder. Write the report over it.\n\nIt was answering:\n\n%s"
            % (time.strftime("%Y-%m-%d %H:%M:%S"), card, (out or "").strip()))


def owed_thread(root):
    """`(thread id, its paths)` for the sitting open here, or `("", [])`.

    The paths are what the thread file says the thread is: its files, outputs
    and write-up files. A sitting on no thread, or a workspace with no valid
    thread file, has none, and the stopped card lists the whole workspace.
    """
    try:
        with open(course_repo.session_path(root, "state.json"), "r",
                  encoding="utf-8") as fh:
            st = json.load(fh) or {}
    except (OSError, ValueError):
        st = {}
    tid = str(st.get("thread") or "").strip()
    clean, problems = course_threads.read(root)
    t = course_threads.thread(clean, tid) if tid and clean and not problems else None
    if not t:
        return "", []
    paths = list(t["files"]) + list(t["outputs"]) + [w["file"] for w in t["writes"]]
    return tid, [p for p in dict.fromkeys(paths) if p]


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


def report_owed(root, this_signal, out, log=None):
    """What a turn owes once it exits with its newest card `pending`, or None.

    The first time, the `[unfinished]` line that wakes it once more. After an
    `[unfinished]` turn that also left it pending, nothing more is woken: the
    card is replaced by a `stopped` one listing what is uncommitted under the
    work, so the board never shows a placeholder for a turn that has ended.
    On a thread, the card lists that thread's paths (`owed_thread`) and badges
    its box; it always names the jobs registered since the placeholder was
    written, which is when the work began.
    """
    path, meta = lesson_cards.newest(course_repo.session_path(root, "cards"))
    if not path or not lesson_cards.is_pending(meta):
        return None
    rel = os.path.relpath(path, root)
    if this_signal != "unfinished":
        if log:
            log.write("-- the turn exited with %s still pending; waking it once "
                      "more to report\n" % rel)
        return unfinished_line(out, rel)
    tid, paths = owed_thread(root)
    everything = lesson_git.uncommitted(root) or []
    changed = (lesson_git.uncommitted(root, paths) or []) if paths else everything
    try:
        since = os.path.getmtime(path)
    except OSError:
        since = 0.0
    wrote = lesson_cards.write_stopped(
        path, changed, jobs_since(root, since), thread=tid,
        elsewhere=len(set(everything) - set(changed)))
    if log:
        log.write("-- %s is still pending after [unfinished]; %s\n"
                  % (rel, "replaced it with what is on disk" if wrote
                     else "could not replace it"))
    return None

def for_this_turn(cfg, course, running, carried, signal, log=None):
    """Who writes the next card. `(cfg, agent_name, spec, why)`.

    THE ASSISTANT IS RE-RESOLVED EVERY TURN. This re-reads the config and the
    sitting's own `state.json` at the top of each one and asks `resolve_agent`
    again, so a tap on the front door and a sitting rewritten from the iPad both
    land on the next card. Where the answer has not changed -- which is nearly
    always -- nothing happens and nothing is paid.

    What makes that cheap is `session_turns`, which is 1: a hosted turn holds no
    conversation worth protecting and reconstructs the evening off disk whoever
    takes it.

    THREE GUARDS, AND THEY ARE THE WHOLE OF WHAT MUST NOT MOVE:

      - not while `carried > 0`. That is the one case where the agent's own
        session genuinely holds something, and swapping throws it away;
      - not under an `[unfinished]`, whose report belongs to the session that
        did the work -- `turn_plan`'s resume branch is the same test;
      - never into or out of a `private` recipe. It is the fence flag: the only
        assistant allowed to read `phi`, whose cards must not reach a remote. A
        swap in is a hosted model in a fenced workspace; a swap out is that
        workspace's tutor replaced by one that cannot open its files.
    """
    cfg = recipes.load_config()
    fresh = dict(course)
    fresh.update(recipes.read_course(course["root"]))
    fresh["root"] = course["root"]
    switched = []
    wanted = recipes.resolve_agent(cfg, fresh, say=lambda m: log and log.write("-- %s\n" % m),
                                   why=switched)
    wanted = wanted or running
    # AND WHETHER THE ONE BEING ASKED FOR CAN BE REACHED AT ALL, before a turn
    # is spent finding out. Free for a recipe that talks to the machine's own
    # provider, which is nearly all of them; see `probe_before_turn`.
    recipes.probe_before_turn(cfg, wanted, log)
    # Then the allowance, which is the other half and belongs to the agent.
    name, said = recipes.choose_agent(cfg, wanted)
    if name == running:
        # AND IT GOES ON SAYING WHY FOR AS LONG AS IT IS TRUE, which is the
        # difference between a climb-down and a silence. `agent_why` is rewritten
        # on every turn precisely so it cannot outlive the swap it describes --
        # so returning None here because nothing MOVED this turn wipes it on the
        # first turn after the daemon came up on the substitute. Measured on the
        # shape that started this: the sitting asks for `deepseek`, the daemon
        # probes it dark and comes up as `claude` with the sentence on the
        # record, and one turn later the record says `claude` and nothing else.
        # The student chose a provider, is being taught by another, and the
        # board has stopped mentioning it.
        #
        # What settles it is WANTED rather than RUNNING: the sitting's own
        # choice against the one taking the turn. They differ for exactly as
        # long as the stand-down or the allowance lasts, and `choose_agent`'s
        # sentence already names the host and the hour.
        # And the switch's own line for as long as it overrules what the
        # sitting or workspace asked for, so a greyed-out claude on the strip
        # is explained by the line that greyed it.
        return cfg, running, cfg["agents"].get(running) or {}, (
            said if name != wanted else (switched[0] if switched else None))
    holding = (cfg["agents"].get(running) or {}).get("private")
    taking = (cfg["agents"].get(name) or {}).get("private")
    why = None
    if recipes.only_bars(cfg, running) and not taking:
        # A RECIPE THE SWITCH BARS TAKES NO FURTHER TURN, whatever its session
        # holds: the switch is a promise about which provider is called, and
        # the guards below protect a conversation, not a provider.
        pass
    elif carried > 0:
        why = "this agent's own session is carrying %d turn(s)" % carried
    elif signal == "unfinished":
        why = "an unfinished report belongs to the session that did the work"
    elif holding or taking:
        why = "one of the two is the fenced reader, and that is nobody's automatic choice"
    if why is None:
        said = said or (switched[0] if switched else None) or (
            "the sitting now asks for '%s'" % name)
        if log:
            log.write("-- %s\n" % said)
        return cfg, name, cfg["agents"].get(name) or {}, said
    if log:
        log.write("-- staying on '%s' rather than '%s': %s\n" % (running, name, why))
    return cfg, running, cfg["agents"].get(running) or {}, None

class Ctx(object):
    """One daemon's state across its turns. `take_turn` reads and rebinds it.

    `cfg`, `agent_name`, `spec` and `recipe` are THIS turn's answer to who
    writes, re-asked at the top of every turn by `for_this_turn`. `carried` is
    how many turns the agent's own session holds, `turns` how many this daemon
    has taken, `striking` the last failure and how often it repeated, and
    `taught_chapter` the chapter the handoff is stamped with.
    """

    def __init__(self, **kw):
        self.__dict__.update(kw)


# AN OWED MESSAGE LIVES ON DISK, NOT IN THIS PROCESS. `pending` is the
# daemon's promise to re-answer a student message whose turn fell over, and
# `board wait` has already rewritten `live/inbox/messages.jsonl` with
# `read: true` before the turn ran -- so the inbox will not hand it over
# again and this variable is the only copy. Measured on 23 September: a turn
# failed at 17:43:05, the message was re-queued here, the daemon was
# signalled three seconds later, and the student's work went with the
# process. `live/cards/` stayed empty, the next daemon's `board wait` found
# nothing unread, and nothing was answered until the person sent it again
# two and a half hours later.
#
# So every assignment goes through `owe`, which writes it into `agent.json`
# as well, and the loop starts by draining whatever the daemon before it
# left owed. That covers a signal, a walltime handover, a `tutor restart`
# and a lost node, which are four ways to lose the same thing.
def owe(ctx, msg):
    daemon.agent_state(ctx.live, owed=msg or None)
    return msg


def take_turn(ctx, message):
    """Run one turn on `message`. `{"owed": message or None, "error": ...}`.

    `owed` is the message the next turn must answer again -- this one, after a
    failure the daemon repairs itself -- or the `[unfinished]` line that wakes
    the turn to write the report it left owed, or None. `error` is why the turn
    failed, or None.
    """
    out = message
    root, live, log, logpath = ctx.root, ctx.live, ctx.log, ctx.logpath
    pending = None
    # A MESSAGE IS OWED FROM THE MOMENT IT IS TAKEN, NOT FROM THE MOMENT A
    # TURN FAILS. `board wait` has already rewritten `live/inbox/messages.jsonl`
    # with `read: true`, so from here until something answers it, this record
    # is the only copy of it anywhere -- and a turn is minutes long. The
    # failure paths below all re-owe it, which covered a turn that came back;
    # it did not cover a daemon signalled, a node lost or a walltime handover
    # WHILE the turn was running, and those land in the same three minutes.
    # Written here rather than flushed from `bye`, because a signal handler
    # that has to reach the filer to save a student's work is a promise made
    # at the worst possible moment.
    owe(ctx, out)
    ctx.turns += 1
    this_signal, turn_repairs = turn.woken_for(root, out)
    # `turn_started` is the daemon's clock, and the board needs it: its own
    # measure of how long a turn has been going starts when it first SEES
    # the working state, which on a reload or a second device is nowhere
    # near when the turn began.
    # AND THE LAST FAILURE STAYS ON THE RECORD WHILE THIS ONE RUNS. Clearing
    # it here would retire a failure on the strength of a turn STARTING,
    # which settles nothing: a daemon killed or a node lost mid-turn would
    # leave `working`, no error and no card -- the empty record, one state
    # along. A turn that GOES THROUGH clears it, below. What stops the board
    # painting an old failure over a running turn is
    # `lesson.state._failure`, which does not report one older than the turn
    # in flight.
    daemon.agent_state(live, state="working", turns=ctx.turns,
                       turn_started=time.time(), turn_signal=this_signal,
                       turn_repairs=turn_repairs)
    log.write("\n=== %s turn %d ===\n%s\n" % (time.strftime("%H:%M:%S"), ctx.turns, out))

    # Keep saying so while the turn runs. The heartbeat used to be written
    # only at these boundaries, so a turn that took longer than the board's
    # two-minute window -- which a turn that reads a chapter and writes a
    # card routinely does -- showed on the iPad as "assistant not
    # responding" while the assistant was in the middle of teaching.
    beating = threading.Event()

    def beat():
        while not beating.wait(30.0):
            daemon.agent_state(live, state="working", turns=ctx.turns)

    ticker = threading.Thread(target=beat, daemon=True)
    ticker.start()

    # The first turn of a session has no conversation to continue, and a
    # resume flag against nothing is an immediate failure. After that the
    # agent's own session is worth keeping: without it every turn pays for
    # re-reading the contract, the method and the lesson before it can write
    # a word, which is most of what a turn costs.
    # A fresh session when there is nothing to resume, and again once the
    # one we have has carried enough turns to be more expensive than
    # starting over. Everything a fresh session needs is on disk: the
    # contract, the method, and `board recap` for the lesson.
    # WHO WRITES THIS ONE. Asked now rather than when the daemon started,
    # so a tap on the front door lands on the next card rather than the next
    # sitting, and so an allowance that ran out is climbed down from and
    # later climbed back to. See `for_this_turn`.
    ctx.cfg, next_agent, next_spec, moved = for_this_turn(
        ctx.cfg, ctx.course, ctx.agent_name, ctx.carried, this_signal, log)
    # The config was re-read, so everything taken off it is too.
    ctx.recycle = int(ctx.cfg.get("session_turns", 12) or 0)
    if moved:
        ctx.agent_name, ctx.spec = next_agent, next_spec
        ctx.recipe = ctx.spec.get("headless")
    # WHO IS WRITING, AND WHY IF IT CHANGED, BEFORE THE TURN RATHER THAN
    # AFTER IT. The strip paints both off this record, and `agent_why` is
    # written on EVERY turn rather than only on a swap: written once it
    # would outlive the swap it describes, and the board would go on
    # explaining a climb-down that had long since climbed home.
    # AND THE LAST FAILURE GOES WITH THE AGENT IT BELONGS TO. The board says
    # "<agent>'s last turn failed -- <reason>" out of these two fields
    # together, so a climb-down that left the old provider's reason behind
    # would blame the new one for it. See `not_this_agents_failure`.
    daemon.agent_state(live, agent=ctx.agent_name, agent_why=moved or None,
                       **daemon.not_this_agents_failure(live, ctx.agent_name))
    first = ctx.spec.get("headless_first") or ctx.recipe
    use, template, fresh = turn.turn_plan(ctx.spec, ctx.carried, ctx.recycle, this_signal)
    if fresh and ctx.carried:
        log.write("-- starting a fresh session after %d turn(s); the lesson "
                  "is read back with `board recap`\n" % ctx.carried)
    # A script agent builds its own context, so it gets the raw inbox rather
    # than the instruction prompt the interactive agents expect -- its whole
    # state is on disk and it re-reads what it needs.
    ctx.taught_chapter[0] = turn.chapter_now(root) or ctx.taught_chapter[0]
    fill = {"inbox": out.strip(),
            # Only the chapter that is open. A handoff about another one is
            # parked as this is read, so a tutor is never handed the last
            # chapter's unfinished business as though it were this one's.
            "handoff": turn.handoff_clause(root)}
    prompt = out.strip() if ctx.spec.get("raw_prompt") else template % fill
    cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompt) for a in use])
    # Where this turn's own words begin, so that if it fails we can read
    # back what it said rather than guess at why.
    mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
    turn_env = turn.turn_environment(ctx.spec)
    timed_out = False
    cap = turn.turn_timeout(ctx.cfg, root, ctx.spec,
                            jobs.REPAIR if turn_repairs else this_signal)
    try:
        rc, timed_out = turn.run_turn(cmd, root, log, cap, env=turn_env)
        err = None if rc == 0 else ("timed out" if timed_out
                                    else "exit %d" % rc)
        # A resume that finds nothing to resume is not a broken turn; it is a
        # first turn wearing the wrong recipe. Try it once as one. Not where
        # the cap cut it: that keeps the session, and retrying it fresh
        # pays a whole preamble and eats the signal that says what happened.
        if err and use is not first and not timed_out:
            # A fresh session holds nothing, so the resume prompt -- which
            # says "you already have the contract, the method and the lesson"
            # -- would produce a card written against no contract at all.
            # Retry as what it actually is: a first turn.
            log.write("!! resume failed, retrying as a fresh turn\n")
            cold = (prompts.HEADLESS_UNFINISHED_PROMPT if this_signal == "unfinished"
                    else prompts.HEADLESS_FIRST_PROMPT)
            cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", cold % fill)
                                              for a in first])
            rc, timed_out = turn.run_turn(cmd, root, log, cap, env=turn_env)
            err = None if rc == 0 else ("timed out" if timed_out
                                        else "exit %d" % rc)
            fresh = True
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
    usage.record_cost(live, log, ctx.turns, ctx.agent_name, fresh,
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

            # AND THEN THE NEXT TURN CLIMBS DOWN. `for_this_turn` runs at
            # the top of the loop and `choose_agent` will not offer this one
            # again until its expiry passes, so the message we just failed
            # to answer is handed to the next provider that is installed,
            # keyed and unlimited -- and the lesson loses nothing, because a
            # turn is cold and reads the evening back off disk.
            #
            # Where there is no such provider, `choose_agent` hands the turn
            # back to this one and it fails where it is visible, which is
            # exactly what this did before there was a second: the failure is
            # on the card stream with its reason, `/health` publishes the
            # limit, and `board limit` says until when.
            nxt, _ = recipes.choose_agent(recipes.load_config(), ctx.agent_name)
            if nxt != ctx.agent_name:
                log.write("-- the next turn goes to '%s'\n" % nxt)
            else:
                log.write("!! nothing else here can take it; turns will "
                          "fail until the allowance returns -- `board "
                          "limit` says when\n")
            return {"owed": pending, "error": err}

        # Not a limit. Ask the network, rather than guess -- and ask about
        # THIS PROVIDER before asking about the machine, because the two
        # have different answers and only the narrow one is ever true here.
        # A filter that drops one hostname leaves the rest of the internet
        # reachable, so the machine-wide probe reports a healthy network
        # over a recipe whose every turn dies in the TLS handshake, and the
        # board says `exit 1` about a fault no tutor can fix.
        #
        # Only when a turn has actually failed. Probing on every turn would
        # add a round trip to the internet to every card the student waits
        # for, to answer a question that is almost always yes.
        own = recipes.agent_probe_urls(ctx.spec)
        if own and not egress.egress_ok(urls=own) and egress.egress_ok(
                also=recipes.provider_probe_urls(ctx.cfg)):
            host = recipes.probe_host(own)
            until = time.time() + egress.UNREACHABLE_WINDOW
            egress.mark_unreachable(ctx.agent_name, host, until)
            log.write("!! '%s' cannot reach %s from here, and everything "
                      "else on the network answers; standing it down until "
                      "%s\n" % (ctx.agent_name, host,
                                time.strftime("%H:%M", time.localtime(until))))
            # `retrying` for the same reason as the allowance above: the
            # message is put back below and the next turn answers it.
            daemon.agent_state(live, state="listening",
                               last_error="cannot reach %s" % host,
                               failed_at=time.time(), failed_agent=ctx.agent_name,
                               retrying=True)
            # The student sent something and got nothing, and the next turn
            # climbs down exactly as it does for an allowance: `choose_agent`
            # will not offer this recipe again until the expiry passes, and
            # a cold turn reads the evening back off disk whoever takes it.
            pending = owe(ctx, out)
            nxt, _ = recipes.choose_agent(recipes.load_config(), ctx.agent_name)
            if nxt != ctx.agent_name:
                log.write("-- the next turn goes to '%s'\n" % nxt)
            else:
                log.write("!! nothing else here can take it; every turn "
                          "will fail until %s answers from this machine\n"
                          % host)
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
        # LOUD IS NOT THE SAME AS RECOVERABLE, and this is where the
        # difference is paid. The two causes above both climb down: an
        # exhausted allowance and a dark host each stand the recipe aside
        # and hand the message to whoever can take it. Everything else --
        # the provider renaming the model the recipe pins, the key being
        # rejected, the endpoint answering 404 to every request -- reaches
        # the board in the provider's own words and then happens again on
        # the next message, and the next, for ever, a wasted turn each time.
        # So a recipe that fails the same way twice is stood down on the
        # same terms, and `choose_agent` gives the lesson to something that
        # can write a card. `board agents` says until when.
        if ctx.striking[0] == ctx.agent_name and ctx.striking[1] == why:
            ctx.striking[2] += 1
        else:
            ctx.striking = [ctx.agent_name, why, 1]
        if ctx.striking[2] >= 2 and not egress.stood_down(ctx.agent_name):
            egress.mark_failing(ctx.agent_name, why)
            until = (egress.stood_down(ctx.agent_name) or {}).get("until", 0)
            log.write("!! '%s' has failed the same way twice (%s); standing "
                      "it down until %s\n"
                      % (ctx.agent_name, why,
                         time.strftime("%H:%M", time.localtime(until))))
            pending = owe(ctx, out)
            nxt, _ = recipes.choose_agent(recipes.load_config(), ctx.agent_name)
            if nxt != ctx.agent_name:
                log.write("-- the next turn goes to '%s'\n" % nxt)
            else:
                log.write("!! nothing else here can take it; turns will "
                          "fail until this recipe is repaired\n")
        daemon.agent_state(live, state="listening", last_error=why,
                           failed_at=time.time(), failed_agent=ctx.agent_name,
                           retrying=pending is not None)
    else:
        ctx.carried = turn.carry_after(this_signal, fresh, ctx.carried)
        # A turn that went through on this agent is proof of THIS agent's
        # allowance, whatever the record still says. The reset time a
        # provider hands out is a promise; this is a measurement. Per agent,
        # because clearing the lot would un-limit a provider nothing has
        # heard from since it ran out.
        if limits.limited_until(ctx.agent_name):
            log.write("-- a turn went through on '%s'; its allowance is "
                      "back\n" % ctx.agent_name)
            limits.clear_limited(ctx.agent_name)
        # And the same argument for a provider that was dark: the expiry is
        # a guess about when a filter might lift, a card written through it
        # is a measurement, and the measurement wins.
        if egress.stood_down(ctx.agent_name):
            log.write("-- a turn went through on '%s'; it is not stood "
                      "down any more\n" % ctx.agent_name)
            egress.clear_unreachable(ctx.agent_name)
        ctx.striking = [None, None, 0]
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
        pending = report_owed(root, this_signal, out, log)
    owe(ctx, pending)
    return {"owed": pending, "error": err}


def headless(cfg, course, agent_name, session):
    spec = cfg["agents"].get(agent_name) or {}
    recipe = spec.get("headless")
    if not recipe:
        print("'%s' has no headless recipe in %s.\n"
              "Add one: a command that takes a prompt, does the work, and exits."
              % (agent_name, recipes.CONFIG), file=sys.stderr)
        return 1
    gone = recipes.missing_command(recipe)
    if gone:
        print("'%s' needs `%s`, which is not on the path on %s.\n"
              "Install it, or name another in %s -- `tutor --agents` lists what "
              "this machine can actually run."
              % (agent_name, gone, recipes.this_host(), recipes.CONFIG),
              file=sys.stderr)
        return 1
    # AND THE SAME REFUSAL FOR A KEY, because the failure is the same failure.
    # A daemon that starts unkeyed shows on the iPad as an assistant listening
    # and then fails every turn into a log -- which is precisely the shape
    # `missing_command` exists to prevent, one layer along. The file is named
    # because nobody can guess it and putting the line in takes ten seconds.
    need = keys.unkeyed(spec)
    if need:
        print("'%s' needs the key %s, which is not in %s.\n"
              "Put `%s=...` in that file, one NAME=value a line.%s"
              % (agent_name, need, keys.store(), need,
                 ("\n" + keys.why_not()) if keys.why_not() else ""),
              file=sys.stderr)
        return 1

    # NO `git status` BEFORE A TURN'S FIRST WORD. Claude Code runs one at start
    # to put a snapshot in its system prompt, synchronously, in the course --
    # and an NFS open can hang it in state `D`, so the turn sits "writing" with
    # no model call made until its cap. Measured 27 September 2026 in Galois
    # Theory: seven minutes in `nfs_set_open_stateid_locked`. A turn has no use
    # for the snapshot; this variable drops it. Every turn inherits it from here.
    os.environ["CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"] = "1"

    root = course["root"]
    live = course_repo.session_dir(root)
    os.makedirs(live, exist_ok=True)
    # Before the board, the sitting and the catch-up -- all of which
    # take time the person holding the iPad is already watching. With a real pid
    # this time, so a start that dies is noticed by the pid test rather than
    # having to wait out the grace.
    daemon.mark_waking(live, agent_name, pid=os.getpid())
    # Moved here from `agent_start`, so the request that asks for a tutor does
    # not wait on a remote. Every session still begins by catching up; it just
    # does it where there is nobody watching the clock.
    gitops.pull(root, quiet=True)
    logpath = os.path.join(live, "agent.log")
    log = open(logpath, "a", buffering=1)
    host = recipes.this_host()
    # WHICH ASSISTANT IS WRITING IS A PER-TURN QUESTION, and it is asked at the
    # top of each one by `for_this_turn`: the config and the sitting's own
    # `state.json` are re-read, the allowance is checked, and where the answer
    # has moved the recipe is re-bound. `agent_name` and `spec` below are this
    # turn's answer rather than the daemon's, and they change under the loop.

    daemon.board(root, "start")
    if session:
        daemon.board(root, "open", course.get("name") or course["dir"], "session", "--" + session)

    # AND WHETHER THE PROVIDER THIS SITTING NAMES ANSWERS FROM HERE AT ALL,
    # ASKED BEFORE THE PERSON SENDS ANYTHING RATHER THAN AFTER. The probe costs
    # 0.17 s -- 0.07 s for the reset from a filtered host, 0.10 s for the 401
    # from one that answers -- and it replaces a first turn that spends about
    # three minutes retrying and writes no card. Cached in `probe_before_turn`
    # for `PROBE_TTL`, and skipped entirely for a recipe with no provider of its
    # own, so an ordinary sitting pays nothing for it.
    #
    # The climb-down is then taken HERE rather than at the top of the first
    # turn, so the board comes up saying who is actually teaching. A student
    # watching a chip that says `deepseek` over a hostname this machine cannot
    # open has been told nothing, and the whole of what the swap is worth is
    # that somebody is told.
    recipes.probe_before_turn(cfg, agent_name, log)
    took, why_took = recipes.choose_agent(cfg, agent_name)
    if took != agent_name:
        log.write("-- %s\n" % (why_took or "'%s' is taking this sitting" % took))
        agent_name = took
        spec = cfg["agents"].get(took) or {}
        recipe = spec.get("headless") or spec.get("headless_first")
    # `last_error` and `failed_at` are not cleared here either: see
    # `mark_waking`. Coming up is not evidence that the turn that fell over
    # before it went well.
    daemon.agent_state(live, host=host, agent=agent_name, pid=os.getpid(),
                       started=time.time(), state="listening", turns=0, waking_at=0,
                       agent_why=why_took or None, code=stamp.LOADED,
                       **daemon.not_this_agents_failure(live, agent_name))
    print("%s is listening in %s. Send from the board; nothing here needs a keyboard."
          % (agent_name, course["dir"]))
    print("stop with: tutor headless --stop\n")

    running = {"go": True, "waiter": None}

    def bye(*_):
        running["go"] = False
        # Kill the blocking `board wait` too, or shutting down takes as long as
        # its timeout -- five minutes of a course that has already been left.
        #
        # THE WHOLE GROUP, AND SIGKILL. A waiter stuck on the filer cannot act
        # on a polite signal, and a restart that walks away leaving one behind
        # is a daemon nobody can replace: the record says a bounce is in flight,
        # the old process holds the workspace, and the new one never starts.
        w = running["waiter"]
        if w and w.poll() is None:
            turn.drop_waiter(w)
    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)

    # No job poll here. The cluster's relay polls every registered job on its
    # five-minute pass (`tutor relay`), and an ending it drops in the inbox is
    # picked up by the `board wait` below like any other line.

    turns = 0
    # Which chapter this daemon has actually been teaching, refreshed each turn.
    # Not read at the end: by then the board may have opened the next one, and
    # the handoff would be stamped with a chapter it says nothing about.
    taught_chapter = [turn.chapter_now(root)]
    carried = 0          # turns the agent's current session is carrying
    # An inbox whose turn failed for a reason that has since been repaired. The
    # student sent something and got nothing back; `board wait` will not hand it
    # over twice, so it is carried here rather than waiting for them to give up
    # and send again. See `owe`.
    pending = daemon.owed_message(live)
    if pending:
        log.write("-- the daemon before this one owed an answer to a message; "
                  "it is the first turn\n")
    # THE SAME FAILURE TWICE IS A BROKEN RECIPE, NOT A BAD MINUTE. `(agent,
    # reason, count)` for whatever the last turn failed of, so a provider that
    # answers every turn with the same fault -- a model that has been renamed, a
    # key the provider now rejects -- is stood down and the lesson climbs down to
    # something that can teach it. Two, because one is a blip and the second
    # identical one is a pattern; and the reason has to MATCH, so two unrelated
    # faults do not add up to a verdict. In the process rather than on disk: it
    # is about this run of turns, and the stand-down it buys is what persists.
    striking = [None, None, 0]
    recycle = int(cfg.get("session_turns", 12) or 0)
    ctx = Ctx(cfg=cfg, course=course, root=root, live=live, log=log,
              logpath=logpath, agent_name=agent_name, spec=spec,
              recipe=recipe, carried=carried, turns=turns,
              striking=striking, taught_chapter=taught_chapter,
              recycle=recycle)
    while running["go"]:
        if pending is not None:
            out, pending = pending, None
            log.write("-- answering the message whose turn failed before\n")
        else:
            # `--force`, because `board wait` now refuses a caller that is
            # inside a headless turn -- and this is the one caller that is not.
            # The guard reads `agent.json`, which still says `working` from the
            # turn that just finished at the moment this starts, so the daemon
            # cannot be told apart from its own turn by state alone.
            running["waiter"] = subprocess.Popen(
                [sys.executable, daemon.BOARD, "wait",
                 "--timeout", str(turn.WAIT_TIMEOUT), "--force"],
                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                start_new_session=True)
            try:
                raw = running["waiter"].communicate(timeout=turn.WAIT_CEILING)[0]
                code = running["waiter"].returncode
            except subprocess.TimeoutExpired:
                # It is past its own deadline and did not enforce it, so it is
                # wedged rather than slow. See `drop_waiter`.
                turn.drop_waiter(running["waiter"], log)
                raw, code = b"", 2
            out = raw.decode("utf-8", "replace")
            running["waiter"] = None
            if not running["go"]:
                break
            if code != 0:
                daemon.agent_state(live, state="listening")     # timed out; still alive
                continue
        got = take_turn(ctx, out)
        pending = got["owed"]

    # The last turn, and the only one the student never sees.
    #
    # WHO WRITES IT IS RE-ASKED HERE, AND IT IS NOT AUTOMATICALLY WHOEVER JUST
    # FAILED. `agent_name`, `spec` and `recipe` are the LOOP's, rebound only by
    # `for_this_turn` at the top of a turn -- and a session whose last turn
    # stood its own provider down never takes another turn, so the loop falls
    # out of the bottom with the dead recipe still bound. Measured on 23
    # September: the log said `-- the next turn goes to 'claude'` at 17:43:05,
    # and the wrap-up three seconds later printed DeepSeek's own
    # unrecognised-model line, ran on DeepSeek's `ANTHROPIC_BASE_URL`, died
    # `ECONNRESET` after 179 seconds, was billed to DeepSeek, and wrote nothing.
    # The one turn that must not be skipped was spent on the one recipe that
    # could not take it.
    #
    # AND IT IS SKIPPED RATHER THAN SPENT WHEN NOTHING HERE CAN WRITE ONE.
    # Three minutes of known-dead retries is worse than no handoff, because the
    # `finish_restart` window is burned along with them and the next daemon is
    # kept waiting behind a turn that was never going to answer.
    stuck = None
    if ctx.turns:
        ctx.cfg = recipes.load_config()
        took, why_took = recipes.choose_agent(ctx.cfg, ctx.agent_name)
        if took != ctx.agent_name:
            log.write("-- the handoff goes to '%s': %s\n"
                      % (took, why_took or "it is what can write one here"))
            ctx.agent_name = took
            ctx.spec = ctx.cfg["agents"].get(took) or {}
            ctx.recipe = ctx.spec.get("headless") or ctx.spec.get("headless_first")
        stuck = recipes.agent_unavailable(ctx.cfg, ctx.agent_name)
        if stuck:
            log.write("\n=== %s handoff ===\n!! no handoff was attempted: %s, "
                      "and nothing else on this machine can write one. "
                      "HANDOFF.md is whatever the last session left; the "
                      "transcript is what the next one reads.\n"
                      % (time.strftime("%H:%M:%S"), stuck))
    if ctx.turns and not stuck:
        daemon.agent_state(live, state="wrapping up")
        log.write("\n=== %s handoff ===\n" % time.strftime("%H:%M:%S"))
        # The handoff is the one turn that must not be skipped -- it is the only
        # continuity the next session has -- and a tutor stopped because its
        # allowance ran out cannot write it. It is attempted anyway and the
        # failure is logged like any other: a session that ends with no handoff
        # is a session the next one has to reconstruct from the cards, which is
        # worse than the transcript but is not nothing.
        # A script agent may have its own way to write the handoff; default to the
        # ordinary turn recipe otherwise.
        wrap = ctx.spec.get("handoff") or ctx.recipe
        cmd = usage.with_usage(ctx.spec, [a.replace("{prompt}", prompts.HANDOFF_PROMPT) for a in wrap])
        mark = os.path.getsize(logpath) if os.path.exists(logpath) else 0
        landing = os.path.join(root, "HANDOFF.md")
        try:
            before = os.path.getmtime(landing)
        except OSError:
            before = 0
        try:
            # Nothing on stdin, for `run_turn`'s reason: `opencode run` reads a
            # stdin that is not a terminal into the prompt and waits for it.
            done = subprocess.run(cmd, cwd=root, stdout=log,
                                  stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL,
                                  env=turn.at_root(root, turn.turn_environment(ctx.spec)),
                                  timeout=ctx.cfg.get("handoff_timeout", 600))
            # The wrap-up is a turn and it is billed like one, so it is counted
            # like one. It used to be the most expensive turn of the session --
            # it re-read the cards, the contract and the old handoff before
            # writing a word -- and nothing would have shown that.
            usage.record_cost(live, log, ctx.turns + 1, ctx.agent_name, False,
                              usage.read_turn_usage(logpath, mark, ctx.spec.get("usage"), ctx.spec))
            # WHETHER THIS TURN WROTE ONE, WHICH IS NOT THE SAME QUESTION AS
            # WHETHER THE FILE IS THERE. A handoff from a previous session is
            # always there, so existence proved nothing: a wrap-up that died on
            # the wire was logged as `handoff written` and then had LAST week's
            # file re-stamped with the chapter this session taught -- a stale
            # note claiming to be this evening's, which is the one lie the
            # handoff must not tell, since it is all the next session gets.
            # Three facts and all three have to hold: the turn exited 0, it did
            # not report its own failure, and the file is newer than the turn.
            said = usage.turn_output(logpath, mark)
            failed = (done.returncode != 0 and ("exit %d" % done.returncode)) \
                or (usage.result_object_error(said) and
                    "the agent reported a failure and exited 0")
            try:
                wrote = not failed and os.path.getmtime(landing) > before
            except OSError:
                wrote = False
            # Say which chapter it is about, now, while this is the only process
            # that knows. The wrap-up is a model call and takes as long as it
            # takes; by the time anybody reads the file the board may already
            # have opened the next chapter, and an unstamped handoff would then
            # be read as though it belonged to it.
            if wrote:
                handoff.stamp_handoff(root, ctx.taught_chapter[0])
                log.write("handoff written\n")
            elif failed:
                log.write("!! the handoff turn failed (%s); HANDOFF.md is "
                          "whatever the last session left, and is left saying "
                          "so\n" % usage.failure_reason(said, failed))
            else:
                log.write("!! no HANDOFF.md was written\n")
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.write("!! handoff failed: %s\n" % exc)

    # Keep the record and say what happened to it. Deleting it makes the board
    # say "no tutor attached", which is the same thing it says when a course
    # never had one -- and the two want different things from the person reading
    # it. `state: stopped` reads on the board as "tutor stopped, nothing is
    # reading the board", which is the truth and is actionable.
    #
    # AND IT DOES NOT SAY WHY, BECAUSE IT DOES NOT KNOW WHY.
    #
    # This wrote `restarting: False`, and `restarting` is the one field that
    # says whether somebody asked for this daemon back. It is written by the
    # ASKER -- `tutor restart --tutors`, before it signals -- precisely so that
    # a bounce can be told from a death, and the daemon receiving the signal
    # cannot tell the two apart. Erasing it on the way out turned every abandoned
    # bounce into a record identical to a person's `tutor agent stop`, which
    # `supervise.tutor_verdict` reads as "a person said no" and never revives.
    #
    # Measured, in Galois Theory: a ship's restart wrote the flag and signalled;
    # the handoff turn took 97 seconds and the restart gives it 90, so it printed
    # "still writing its handoff; run this again in a minute" and returned
    # WITHOUT starting anything. The daemon then exited through this line, wiped
    # the flag, and the watch loop revived that course's
    # BOARD and refused its TUTOR -- fifteen hours of a board that served
    # perfectly with nothing reading it, and a `turn_signal` still naming an
    # answer that had been handed in. From the iPad: the app works and the tutor
    # is down.
    #
    # Nothing clears the flag here because nothing here has earned the right to.
    # `mark_waking` clears it, and it is written by both halves of a start, so
    # the flag lives exactly as long as the restart it describes is unfinished --
    # and a restart nobody finished is one the watchdog now finishes, after
    # `REATTACH_GRACE`.
    #
    # AND IT IS WRITTEN ONLY WHERE THIS PROCESS IS STILL THE ONE ON THE RECORD.
    # See `record_is_ours`: a bounce that has already brought the successor up
    # leaves two daemons alive for a moment, and this line landing on the new
    # one's record retires a tutor that is listening. Nothing is written at all
    # in that case -- the successor's own `listening` is the truth, and the only
    # thing this process has left to say about the file is nothing.
    if daemon.record_is_ours(live):
        daemon.agent_state(live, state="stopped", stopped_at=time.time())
    else:
        log.write("-- another daemon already holds this record; its state is "
                  "left alone\n")
    print("stopped after %d turn(s)" % ctx.turns)
    return 0
