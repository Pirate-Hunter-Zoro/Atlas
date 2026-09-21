#!/usr/bin/env python3
"""The daemon's side of a hop, with a fake client and no cluster.

`carry.py` guards the DECISIONS -- `carry_verdict`, `thaw`, the walk and the
claim -- as pure functions off a record and a clock. This guards the two things
that only happen when a process actually runs:

1. `run_turn`, which is the one place a turn is killed. `coli-code` is a shell
   that runs `srun`, so killing the direct child orphans the step and the client
   goes on answering on the serving node -- and the next turn is then a second
   client on one KV slot, which is the one outcome worse than the hop.
2. `take_hop`, driven three passes with a stub client that exits 75, then 76,
   then 0, which is a chain hop followed by a chain gap followed by the work
   finishing. What is asserted across the three is what the guarantee rests on:
   no failure is ever stamped, the hops are counted, the gap costs neither a hop
   nor a stall, and the record is clean at the end.

The daemon's own loop is not run here -- `headless` starts a board, binds a port
and pushes a git branch. The branch that wires these two together is read out of
the file as source instead, at the bottom.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard import missions                              # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
_spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(_spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def script(path, body):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/bash\n" + body)
    os.chmod(path, 0o755)
    return path


base = tempfile.mkdtemp(prefix="tutor-hopping-")
try:
    # -----------------------------------------------------------------------
    # A. run_turn kills the GROUP, not the child
    # -----------------------------------------------------------------------
    kid = os.path.join(base, "kid.pid")
    stub = script(os.path.join(base, "slow"),
                  'sleep 300 &\necho $! > %s\nwait\n' % kid)
    logpath = os.path.join(base, "turn.log")
    with open(logpath, "w", encoding="utf-8") as log:
        began = time.time()
        rc, timed_out = tutor.run_turn([stub], base, log, 1)
    check("a turn that runs past its cap is cut, and says so rather than "
          "wearing an exit code",
          timed_out and time.time() - began < 30)

    with open(kid, encoding="utf-8") as fh:
        child = int(fh.read().strip())
    gone = False
    for _ in range(50):
        try:
            os.kill(child, 0)
        except OSError:
            gone = True
            break
        time.sleep(0.1)
    check("and the srun it launched goes with it, because a client left "
          "answering on the serving node is a second client on one KV slot",
          gone)

    rc, timed_out = None, None
    with open(logpath, "a", encoding="utf-8") as log:
        rc, timed_out = tutor.run_turn(
            [script(os.path.join(base, "quick"), 'exit 75\n')], base, log, 30)
    check("and a turn that ends on its own is reported by its code, with "
          "nothing cut", rc == 75 and not timed_out)

    # -----------------------------------------------------------------------
    # B. three passes of a stub client: 75, then 76, then 0
    # -----------------------------------------------------------------------
    # `coli-code` stubbed to a two-line script, so the exit codes the client
    # promises are the exit codes this sees. The mission record is real and so
    # is every helper the daemon calls on it.
    ws = os.path.join(base, "PSYCH-ASR")
    os.makedirs(os.path.join(ws, "live", "cards"), exist_ok=True)
    seen = os.path.join(base, "argv.log")
    client = script(os.path.join(base, "coli-code"),
                    'printf "%%s\\n" "${COLI_SESSION_ID:-none}" >> %s\n'
                    'read -r RC < %s\n'
                    'exit "$RC"\n' % (seen, os.path.join(base, "rc")))

    def code(n):
        with open(os.path.join(base, "rc"), "w", encoding="utf-8") as fh:
            fh.write("%d\n" % n)

    real_status = tutor.colibri.status
    tutor.colibri.status = lambda fresh=False: {"state": "warm", "left": 32000,
                                                "job": "1", "node": "c1"}
    try:
        missions.dispatch(ws, "repair the diarization", "t0100", agent="colibri")
        spec = {"headless_first": [client, "--yes", "{prompt}"],
                "headless": [client, "--yes", "--continue", "{prompt}"]}

        pending, carries, stalls, errors = None, [], [], []
        launched = []
        for rc_code in (75, 76, 0):
            code(rc_code)
            out = pending or "[2026-09-21 09:00:00] repair the diarization"
            pending = None
            this_signal = tutor.turn_signal(out)
            use, template, fresh = tutor.turn_plan(spec, 0, 1, this_signal)
            mrec, env = tutor.mission_turn(ws, renew=fresh)
            launched.append((list(use), template))
            with open(logpath, "a", encoding="utf-8") as log:
                got, timed_out = tutor.run_turn(
                    [a.replace("{prompt}", "p") for a in use], ws, log, 60,
                    env=env)
                err = None if got == 0 else "exit %d" % got
                if tutor.reads_as_wait(err):
                    pending = tutor.carry_line(out)
                elif tutor.reads_as_carry(err):
                    mine, pending = tutor.take_hop(ws, log, out, this_signal,
                                                   600.0, "the node went")
                elif err:
                    errors.append(err)
                else:
                    missions.turn_over(ws, mrec, 600.0)
            now = missions.stored(ws)[0]
            carries.append(now["carries"])
            stalls.append(now["stalls"])

        check("three passes and not one failure is written, because a hop and "
              "a chain gap are neither of them a task that failed",
              errors == [])
        check("the hop is counted and the gap is not, so the budget pays for "
              "pick-ups rather than for waiting",
              carries == [1, 1, 1])
        check("and no pass produced nothing, so nothing is stalled",
              stalls == [0, 0, 0])
        check("the pass after the hop resumes the conversation rather than "
              "reopening it, which is the whole cost argument",
              "--continue" in launched[1][0]
              and launched[1][1] is tutor.HEADLESS_CARRY_PROMPT
              and "--continue" not in launched[0][0])
        check("and so does the pass after the gap, because the gap did not "
              "end the session either",
              "--continue" in launched[2][0]
              and launched[2][1] is tutor.HEADLESS_CARRY_PROMPT)
        check("the turn is cleared when the work ends on its own terms, so a "
              "finished mission is not picked up for ever",
              missions.stored(ws)[0]["turn_at"] == 0.0)
        with open(seen, encoding="utf-8") as fh:
            ids = [l.strip() for l in fh if l.strip()]
        check("and every launch was told WHICH conversation, one id across all "
              "three, so a hand-run client in the same workspace between a hop "
              "and the pick-up cannot be resumed by mistake",
              len(ids) == 3 and len(set(ids)) == 1 and ids[0] != "none"
              and ids[0] == missions.stored(ws)[0]["session"])

        # AND A FRESH TURN IS A NEW CONVERSATION. The client refuses
        # `--session-id` for an id that already has one and exits 1, so a
        # fresh launch handed the id the last turn opened dies -- and
        # `session_turns` is 1, which makes every mission turn that is not a
        # `[carry]` fresh.
        held = missions.stored(ws)[0]["session"]
        _, again = tutor.mission_turn(ws, renew=True)
        check("a fresh turn opens a conversation of its own rather than the "
              "one the turn before it opened, which the client refuses",
              again["COLI_SESSION_ID"] != held
              and missions.stored(ws)[0]["session"] == again["COLI_SESSION_ID"])
        _, kept = tutor.mission_turn(ws, renew=False)
        check("and a pick-up keeps the id, because the conversation it is "
              "resuming is the one that was cut off",
              kept["COLI_SESSION_ID"] == again["COLI_SESSION_ID"])

        # THE GAP COSTS NO HOP EVEN WHERE THE PICK-UP ITSELF HITS ONE. A
        # `[carry]` turn that exits 76 is the case: it is a pick-up, so the
        # stall rule would otherwise fire on a turn that never ran.
        before = missions.stored(ws)[0]
        check("a pick-up that finds no generation to step into is not a "
              "pick-up that produced nothing",
              tutor.reads_as_wait("exit 76")
              and before["stalls"] == 0 and before["carries"] == 1)

        # AND THE CLAIM. Two boards deciding the same hop is owed is ordinary;
        # both waking a turn is not.
        race = os.path.join(base, "TRD-EHR")
        os.makedirs(os.path.join(race, "live"), exist_ok=True)
        missions.dispatch(race, "do it", "t0200", agent="colibri")
        with open(logpath, "a", encoding="utf-8") as log:
            first = tutor.take_hop(race, log, "[x] do it", "", 600.0, "gone")
            # The second board reads the record as it was BEFORE the first
            # claim, which is what a race is.
            missions.write(race, dict(missions.stored(race)[0], carries=0))
            second = tutor.take_hop(race, log, "[x] do it", "", 600.0, "gone")
        check("one board takes the hop and re-queues the work",
              first[0] and first[1] and "[carry]" in first[1])
        check("and the one that loses the exclusive create writes no line, "
              "because two clients on one conversation is worse than the hop",
              second[0] and second[1] is None)

        # AND THE HOP IS CHARGED TO THE MISSION THE TURN WAS WORKING. A second
        # mission dispatched into the same workspace mid-turn is allowed, and
        # the newest open record is then the wrong one: charging it burns a
        # budget that has not been spent and leaves the cut-off mission owed,
        # which is the same work queued twice.
        two = os.path.join(base, "TRD-EHR-two")
        os.makedirs(os.path.join(two, "live"), exist_ok=True)
        older = missions.dispatch(two, "do it", "t0300", agent="colibri")
        time.sleep(0.01)
        missions.dispatch(two, "and this too", "t0301", agent="colibri")
        with open(logpath, "a", encoding="utf-8") as log:
            mine, line = tutor.take_hop(two, log, "[x] do it", "", 600.0,
                                        "gone", rec=older)
        by_id = {r["id"]: r for r in missions.stored(two)}
        check("a mission dispatched while a turn is running does not pay for "
              "that turn's hop, and the turn's own mission does",
              mine and line and by_id["t0300"]["carries"] == 1
              and by_id["t0301"]["carries"] == 0
              and not by_id["t0301"]["carry"])

        # A SITTING THAT IS NOT A MISSION HAS NOTHING TO CARRY, and falls
        # through to the ordinary failure handling rather than looping.
        plain = os.path.join(base, "Galois-Theory")
        os.makedirs(os.path.join(plain, "live"), exist_ok=True)
        with open(logpath, "a", encoding="utf-8") as log:
            check("a workspace with no colibri mission is not carried at all",
                  tutor.take_hop(plain, log, "[x] do it", "", 6.0, "gone")
                  == (False, None))

        # AND THE STOPPING CONDITION, read off the record so the daemon and
        # the board give up on the same mission at the same moment. Without it
        # a chain that never comes back is a turn every five minutes for ever.
        done_in = os.path.join(base, "SPENT")
        os.makedirs(os.path.join(done_in, "live"), exist_ok=True)
        missions.dispatch(done_in, "do it", "t0300", agent="colibri")
        missions.write(done_in, dict(missions.stored(done_in)[0],
                                     carries=missions.CARRY_HOPS))
        with open(logpath, "a", encoding="utf-8") as log:
            check("a mission with its pick-ups spent is not carried again, so "
                  "the turn is reported as the failure it looks like",
                  tutor.carry_spent(done_in, missions.stored(done_in)[0])
                  and tutor.take_hop(done_in, log, "[x] do it", "", 600.0,
                                     "gone") == (False, None))
        missions.write(done_in, dict(missions.stored(done_in)[0], carries=0,
                                     ended="failed", ended_at=time.time(),
                                     reason="exit 1"))
        check("and neither is one a board has already frozen, whatever the "
              "budget still says",
              tutor.carry_spent(done_in, {"id": "t0300"}))
        check("while a mission with budget left and no ending is carried, or "
              "the stop would be the whole of it",
              not tutor.carry_spent(ws, missions.stored(ws)[0]))
    finally:
        tutor.colibri.status = real_status
finally:
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------------------
# C. the branch that wires those two together, read as source
# ---------------------------------------------------------------------------
SRC = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
check("the daemon runs every turn through `run_turn`, including the retry, or "
      "one of the two paths leaves an orphan behind",
      SRC.count("tutor.run_turn") == 0 and SRC.count("= run_turn(") == 2
      and "subprocess.run(cmd, cwd=root, stdout=log" not in
      SRC.split("def headless")[-1].split("handoff ===")[0])
check("a chain gap waits under `CARRY_BACKOFF` rather than asking squeue in a "
      "tight loop for an hour",
      "missions.CARRY_BACKOFF" in SRC and "reads_as_wait(err)" in SRC)
check("and it stops waiting where the record's budget stops, because a chain "
      "that never comes back is not a thing a daemon repairs by asking again",
      "if reads_as_wait(err) and not carry_spent(root, mrec):" in SRC)
check("a turn cut at its cap is carried like a hop, because nine hours of "
      "work does not fit in one turn and a cut turn is not a failed one",
      "if reads_as_carry(err) or timed_out:" in SRC)
check("the colibri recipe's cap is eight hours, under a nine-hour generation, "
      "so the generation's own end is the cut",
      tutor.DEFAULT_CONFIG["agents"]["colibri"]["timeout"] == 28800)
check("the daemon renews the conversation id on exactly the turns that open "
      "one, so a fresh launch is never handed an id the client has already "
      "seen",
      "mission_turn(root, log, renew=fresh)" in SRC
      and "mission_turn(root, log)" not in SRC)

print("%d FAILURES" % len(fails) if fails
      else "the client dies, the work does not, and nothing is left answering")
sys.exit(1 if fails else 0)
