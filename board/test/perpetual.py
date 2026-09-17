#!/usr/bin/env python3
"""The board keeps itself up, and keeps hold of the machine it is up on.

Two failures this had no answer for. A process dies -- `serve.py` on an
exception, the tutor daemon on an OOM -- and the record on disk goes on naming a
pid that is gone until somebody logs in, because a login was the only moment
anything looked. And the allocation ends, which takes the node, both processes
and `tailscaled` with it and leaves nothing anywhere to notice.

`tutor watch` answers the first: a loop inside the allocation, which repairs what
is down within one poll. `tutor serve` answers the second: a batch job that
queues its own successor with `--dependency=afterany:<itself>` before it does
anything else, so the queue always holds the next machine and the chain outlives
any one allocation.

What is asserted here is mostly what the watchdog REFUSES to do, because a
watchdog that starts things nobody asked for is worse than no watchdog at all:
it must not revive a tutor a person stopped, must not touch a board on a node
that is still an allocation of yours, must not fight a restart that is already in
flight, and must not resurrect a two-day-old record it found lying about.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

from tutorboard import machine, paths, processes, supervise

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


tmp = tempfile.mkdtemp(prefix="tutor-perpetual-")
conf = tempfile.mkdtemp(prefix="tutor-perpetual-conf-")
state = tempfile.mkdtemp(prefix="tutor-perpetual-state-")
# Nothing here may write the real state directory: `serve.json`, `watch.json` and
# the stop flag are how a live chain is driven, and a test that wrote them would
# cancel somebody's board or resurrect one they had stopped.
tutor.CONFIG_DIR = conf
paths.CONFIG_DIR = conf
paths.CONFIG = os.path.join(conf, "config.json")
paths.CHOSEN = os.path.join(conf, "chosen.json")
tutor.CHOSEN = paths.CHOSEN
paths.STATE_DIR = state
supervise.RECORD = os.path.join(state, "serve.json")
supervise.WATCH = os.path.join(state, "watch.json")
supervise.STOP = os.path.join(state, "serve-stopped")

HOST = "compute301"
GONE = "compute999"
now = time.time()


def make_workspace(name, board=None, agent=None):
    root = os.path.join(tmp, name)
    os.makedirs(os.path.join(root, "live"), exist_ok=True)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": name, "mode": "math"}, fh)
    if board is not None:
        with open(os.path.join(root, "live", ".board.json"), "w", encoding="utf-8") as fh:
            json.dump(board, fh)
    if agent is not None:
        with open(os.path.join(root, "live", "agent.json"), "w", encoding="utf-8") as fh:
            json.dump(agent, fh)
    return root


try:
    # =======================================================================
    # What is wrong here, if anything
    # =======================================================================
    check("no record at all is nothing to repair -- `board stop` removes it, and "
          "that is a person saying no",
          supervise.board_verdict(None, HOST, False, False, 9) == "none")
    check("a board record naming another node is that node's business, because "
          "the pid in it cannot be read from here",
          supervise.board_verdict({"node": GONE, "pid": 5}, HOST, True, True, 0)
          == "elsewhere")
    check("a board whose pid is gone is revived",
          supervise.board_verdict({"node": HOST, "pid": 5}, HOST, False, False, 0)
          == "revive")
    check("a board that is up and answering is left alone",
          supervise.board_verdict({"node": HOST, "pid": 5}, HOST, True, True, 0)
          == "ok")
    # A board writing a large slate PNG can be a second late. One miss is not a
    # diagnosis; the state that has no other symptom -- alive, holding the port,
    # answering nothing -- needs two.
    check("one missed health probe waits",
          supervise.board_verdict({"node": HOST, "pid": 5}, HOST, True, False, 1)
          == "waiting")
    check("two in a row is a wedged board, which needs stopping before starting",
          supervise.board_verdict({"node": HOST, "pid": 5}, HOST, True, False, 2)
          == "hung")
    check("and the number of misses that means it is a named constant, not a 2",
          supervise.HEALTH_MISSES == 2)

    check("a tutor a person stopped is never started again",
          supervise.tutor_verdict({"host": HOST, "state": "stopped",
                                   "last_seen": now}, HOST, False) == "stopped")
    check("a tutor whose pid is gone with no such record is revived",
          supervise.tutor_verdict({"host": HOST, "state": "listening",
                                   "last_seen": now}, HOST, False) == "revive")
    check("a tutor that is listening is left alone",
          supervise.tutor_verdict({"host": HOST, "state": "listening"}, HOST, True)
          == "ok")
    # `tutor restart --tutors` writes `restarting` and a `stopped_at` before it
    # signals, precisely so a bounce can be told from a death. Two processes
    # trying to start the same daemon is how a lesson ends up with two tutors.
    check("a restart in flight is not a death, and the watchdog waits it out",
          supervise.tutor_verdict({"host": HOST, "restarting": True,
                                   "stopped_at": now}, HOST, False) == "reattaching")
    check("but a restart that never came back eventually is one",
          supervise.tutor_verdict({"host": HOST, "restarting": True,
                                   "stopped_at": now - 4000}, HOST, False) == "revive")
    check("a start still on its way up is not a death either",
          supervise.tutor_verdict({"host": HOST, "state": "waking",
                                   "waking_at": now}, HOST, False) == "waking")
    check("and an interactive session is somebody's terminal, not a daemon",
          supervise.tutor_verdict({"host": HOST, "mode": "interactive",
                                   "state": "attached"}, HOST, True)
          == "somebody's")

    # THE ONE THAT COST A REAL RECORD. `live/agent.json` is never swept -- it is
    # kept so the board can say "tutor stopped" rather than "no tutor here" -- so
    # a record saying `listening` on a node whose allocation ended two days ago
    # reads exactly like one from a node that died a minute ago. Measured while
    # this was written: TRD-EHR, `listening` on compute300, 42 hours stale.
    check("a record from a node that went two days ago is a fossil, not a lesson",
          not supervise.left_behind({"state": "listening",
                                     "last_seen": now - 42 * 3600}))
    check("one from a node that went a minute ago is a lesson to pick back up",
          supervise.left_behind({"state": "listening", "last_seen": now - 60}))
    check("a handover is not a stop: the walltime's own stop is picked back up",
          supervise.left_behind({"state": "stopped", "handover": "now",
                                 "last_seen": now - 60}))
    check("a person's stop leaves no handover flag, so it is never picked up",
          not supervise.left_behind({"state": "stopped", "last_seen": now - 60}))
    # A single-node partition -- which c3_accel is -- hands over to ITSELF more
    # often than not, so the flag has to be honoured without a change of node.
    check("a handover is honoured on the same node too",
          supervise.tutor_verdict({"host": HOST, "state": "stopped",
                                   "handover": "now", "last_seen": now},
                                  HOST, False) == "revive")
    check("and a stale handover flag does not resurrect anything for ever",
          supervise.tutor_verdict({"host": HOST, "state": "stopped",
                                   "handover": "then", "last_seen": now - 99999},
                                  HOST, False) == "stopped")

    check("a repair that failed waits longer each time, and the wait is capped",
          supervise.next_try(0) == 0
          and supervise.next_try(1) < supervise.next_try(3)
          and supervise.next_try(50) == supervise.next_try(500) == max(supervise.BACKOFF))

    # =======================================================================
    # One pass of the loop, with nothing allowed to start a process
    # =======================================================================
    make_workspace("Up", board={"node": HOST, "pid": 101, "port": 9001},
                   agent={"host": HOST, "pid": 102, "state": "listening",
                          "agent": "claude", "last_seen": now})
    make_workspace("DeadBoard", board={"node": HOST, "pid": 201, "port": 9002},
                   agent={"host": HOST, "pid": 202, "state": "listening",
                          "agent": "claude", "last_seen": now})
    make_workspace("Elsewhere", board={"node": HOST + "b", "pid": 301, "port": 9003})
    make_workspace("Stopped", board={"node": HOST, "pid": 401, "port": 9004},
                   agent={"host": HOST, "state": "stopped", "agent": "claude",
                          "last_seen": now})
    make_workspace("HandedOver", agent={"host": GONE, "state": "stopped",
                                        "handover": "now", "agent": "claude",
                                        "last_seen": now})

    cfg = {"courses_dir": tmp, "default_agent": "claude",
           "agents": {"claude": {"cmd": ["claude"], "prompt": "argv",
                                 "headless": ["claude", "-p", "{prompt}"]}},
           "hosts": {}}

    calls = {"board": [], "agent": [], "link": []}

    def fake_board(root, *args):
        calls["board"].append((os.path.basename(root), args[0]))
        return 0, "board up (pid 1)"

    def fake_agent_start(cfg_, course, name, session=None):
        calls["agent"].append((course["dir"], name))
        return 0, "%s starting in %s" % (name, course["dir"])

    alive = {101, 102, 202}          # DeadBoard's board pid is not in here

    tutor.board = fake_board
    tutor.agent_start = fake_agent_start
    tutor.link = lambda root: calls["link"].append(os.path.basename(root))
    processes.board_is_running = lambda pid, root: pid in alive
    processes.pid_alive = lambda pid, needle=None: pid in alive
    supervise.answering = lambda port, timeout=3.0: True
    machine.slurm_nodes = lambda: {HOST, HOST + "b"}

    memo = {}
    did = tutor.watch_once(cfg, HOST, memo, lambda line: None)

    check("the dead board is started, and the live one is not touched",
          ("DeadBoard", "start") in calls["board"]
          and ("Up", "start") not in calls["board"])
    check("a board on another node that is STILL one of your allocations is left "
          "exactly where it is",
          ("Elsewhere", "start") not in calls["board"]
          and ("Elsewhere", "stop") not in calls["board"])
    check("a board that comes back gets the tailnet link back too -- one on "
          "loopback with no link is one the iPad cannot reach, and on a node "
          "that has just taken the serving over there is no link yet",
          calls["link"] == [w for w, act in calls["board"] if act == "start"]
          and "DeadBoard" in calls["link"])
    check("a tutor that is listening is not restarted",
          ("Up", "claude") not in calls["agent"])
    check("a tutor a person stopped is not restarted",
          ("Stopped", "claude") not in calls["agent"])
    check("a tutor left behind by a machine that went is picked back up here",
          ("HandedOver", "claude") in calls["agent"])
    check("and the handover flag is cleared on the way, so the next stop of it "
          "reads as a person's",
          not (json.load(open(os.path.join(tmp, "HandedOver", "live",
                                           "agent.json"))).get("handover")))
    check("what it repaired is reported rather than done silently",
          any("DeadBoard" in line for line in did))

    # A start that fails must not be retried on the very next pass: a tutor with
    # no allowance left, or a command that is not on this machine's path, would
    # otherwise be started every twenty seconds for seven days.
    calls["board"] = []

    def failing_board(root, *args):
        calls["board"].append((os.path.basename(root), args[0]))
        return 1, "port 9002 was busy"

    tutor.board = failing_board
    memo = {}
    tutor.watch_once(cfg, HOST, memo, lambda line: None)
    first = len([c for c in calls["board"] if c[0] == "DeadBoard"])
    tutor.watch_once(cfg, HOST, memo, lambda line: None)
    second = len([c for c in calls["board"] if c[0] == "DeadBoard"])
    check("a repair that failed is not tried again immediately",
          first >= 1 and second == first)

    # A wedged board -- alive, holding its port, answering nothing -- has to be
    # stopped before it is started, or the new one cannot have the port.
    calls["board"] = []
    tutor.board = fake_board
    supervise.answering = lambda port, timeout=3.0: False
    memo = {}
    for _ in range(supervise.HEALTH_MISSES):
        tutor.watch_once(cfg, HOST, memo, lambda line: None)
    check("a wedged board is stopped and then started, in that order",
          calls["board"].index(("Up", "stop")) < calls["board"].index(("Up", "start")))
    supervise.answering = lambda port, timeout=3.0: True

    # =======================================================================
    # Which boards the machine that just went was serving
    # =======================================================================
    machine.slurm_nodes = lambda: {HOST}
    was = [c["dir"] for c in tutor.previously_serving(cfg, HOST)]
    check("the boards on the node that went are known, so a handover brings back "
          "every lesson rather than the one somebody last chose",
          "Elsewhere" in was)
    check("and a board on a node that is still yours is not one of them",
          not any(d == "Up" for d in was))
    machine.slurm_nodes = lambda: None
    check("with no Slurm to ask, nothing is claimed from anywhere",
          tutor.previously_serving(cfg, HOST) == [])
    machine.slurm_nodes = lambda: {HOST, HOST + "b"}

    # =======================================================================
    # The chain
    # =======================================================================
    sent = {"argv": None}

    class Done:
        returncode = 0
        stdout = b"2073999\n"

    def fake_run(argv, **kw):
        sent["argv"] = argv
        sent["env"] = kw.get("env") or {}
        return Done()

    import subprocess as _sp
    real_run = _sp.run
    supervise.subprocess.run = fake_run
    try:
        job, err = supervise.submit("c3_accel", "7-00:00:00", 2, "8G",
                                    after="2073998", chdir=tmp)
    finally:
        supervise.subprocess.run = real_run
    argv = sent["argv"] or []
    line = " ".join(argv)
    check("a generation is submitted with the id sbatch prints and nothing else",
          job == "2073999" and err is None and "--parsable" in argv)
    check("the successor waits on ANYTHING happening to its predecessor, not on "
          "it succeeding -- a generation that crashed is when the next one is "
          "most needed",
          "--dependency" in argv and "afterany:2073998" in argv)
    check("every generation carries the one job name the chain is found, refused "
          "and cancelled by",
          supervise.JOB_NAME in argv)
    check("a node failure requeues the chain rather than ending it, and the log "
          "survives that",
          "--requeue" in argv and "--open-mode" in argv and "append" in argv)
    check("the batch shell is warned before the walltime, so the handoffs can be "
          "written while there is still a machine to write them on",
          "B:USR1@%d" % supervise.HANDOVER_WARNING in line)
    check("the log goes somewhere that still exists after the node does -- /tmp "
          "on a compute node is not a place anybody can read afterwards",
          state in line and "%j" in line)
    check("and where the tool is checked out is handed over in the environment, "
          "because Slurm runs a COPY of the script and $0 points at that",
          sent["env"].get("TUTOR_BOARD_TOOL") == paths.TOOL)

    rows = [{"id": "2073998", "state": "RUNNING", "node": "compute306",
             "dependency": "", "left": "6-23:00:00", "partition": "c3_accel"},
            {"id": "2073999", "state": "PENDING", "node": "",
             "dependency": "afterany:2073998(unfulfilled)", "left": "7-00:00:00",
             "partition": "c3_accel"}]
    check("the successor is recognised by the dependency it carries, so a "
          "requeued generation does not queue a second one",
          (supervise.successor_of("2073998", rows) or {}).get("id") == "2073999")
    check("and nothing running is ever mistaken for one",
          supervise.successor_of("2073999", rows) is None)

    supervise.serve_jobs = lambda user=None: rows
    said = []
    check("with a successor already queued, nothing is submitted",
          tutor.ensure_successor(cfg, "2073998", said.append) == "2073999")
    supervise.serve_jobs = lambda user=None: None
    check("and when squeue does not answer, nothing is submitted either -- an "
          "unreachable controller is not an empty queue",
          tutor.ensure_successor(cfg, "2073998", said.append) is None)

    # A chain that survives being cancelled is the correct behaviour for a
    # walltime and the wrong one for a person who wants it to stop. So a stop is
    # a file first: it is what the next successor submission asks.
    supervise.serve_jobs = lambda user=None: []
    supervise.mark_stopped("a test")
    check("a stop is a flag on disk, and no generation queues a successor while "
          "it is set",
          supervise.stopped()
          and tutor.ensure_successor(cfg, "2073998", said.append) is None)
    supervise.clear_stopped()
    check("and starting the chain again clears it", not supervise.stopped())

    # =======================================================================
    # The job script itself
    # =======================================================================
    script = open(supervise.SCRIPT, encoding="utf-8").read()
    check("the job script exists where the submitter looks for it, and runs",
          os.path.exists(supervise.SCRIPT) and os.access(supervise.SCRIPT, os.X_OK))
    check("it finds the checkout without trusting $0, which inside a batch job "
          "is Slurm's own copy of the script",
          "TUTOR_BOARD_TOOL" in script and "scontrol show job" in script)
    check("it says out loud when it cannot, because that is the one failure that "
          "ends the chain silently",
          "the chain ends here" in script)
    check("and it hands the job's batch shell straight to the tool, so the "
          "walltime signal reaches the thing that acts on it",
          "exec python3" in script and "serve inside" in script)
    check("the defaults in it are a seven-day generation, on the one partition "
          "nothing on this cluster can suspend",
          "--time=7-00:00:00" in script and "--partition=c3_accel" in script)

    src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
    check("the successor is queued BEFORE the code is caught up and before a "
          "single board is started, because everything after that line can fail "
          "and the chain must not",
          src.index("successor = ensure_successor") < src.index("tool_sync(cfg, quiet=True)"))
    check("a login repairs the chain too -- a generation that fell over in its "
          "first second never reached the line that queues its successor",
          "chain_repair(cfg, say)" in src)
    check("and a login does not submit one where nobody ever asked for a chain",
          'if not rec.get("job") or supervise.stopped():' in src)
    check("the watch loop cannot die of the thing it is watching",
          "A WATCHDOG MAY NOT DIE OF THE THING IT IS WATCHING" in src)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(conf, ignore_errors=True)
    shutil.rmtree(state, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "the board repairs itself, and the allocation under it renews itself")
sys.exit(1 if fails else 0)
