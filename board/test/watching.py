#!/usr/bin/env python3
"""`tutor watch` keeps the boards and tutors up, and refuses what nobody asked for.

A process dies -- `serve.py` on an exception, the tutor daemon on an OOM -- and
the record on disk goes on naming a pid that is gone. `tutor watch` repairs it
within one poll. On the Mac the `tutor-board.tutor-watch` LaunchAgent runs it.

What is asserted here is mostly what the watchdog REFUSES to do, because a
watchdog that starts things nobody asked for is worse than no watchdog at all:
it must not revive a tutor a person stopped, must not touch a board on a node
that is still an allocation of yours, must not fight a restart that is already in
flight, and must not resurrect a two-day-old record it found lying about.
"""


import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tutorboard.runner import daemon  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import watch as runwatch  # noqa: E402
from tutorboard import stamp  # noqa: E402
from tutorboard.net import tailscale  # noqa: E402

from tutorboard import choice, machine, paths, processes, supervise

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


top = tempfile.mkdtemp(prefix="tutor-watching-")
tmp = os.path.join(top, "courses")
os.makedirs(tmp)
conf = tempfile.mkdtemp(prefix="tutor-watching-conf-")
state = tempfile.mkdtemp(prefix="tutor-watching-state-")
# Nothing here may write the real state directory: `watch.json` and the stop
# flag drive a live watch loop, and a test that wrote them would stand it down.
recipes.CONFIG_DIR = conf
paths.CONFIG_DIR = conf
paths.CONFIG = os.path.join(conf, "config.json")
paths.CHOSEN = os.path.join(conf, "chosen.json")
paths.STATE_DIR = state
supervise.WATCH = os.path.join(state, "watch.json")
supervise.STOP = os.path.join(state, "watch-stopped")

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

    # There is no adopting a tutor from another machine: a record naming
    # another host is that host's, whatever it says.
    check("a tutor recorded on another machine is left to it",
          supervise.tutor_verdict({"host": GONE, "state": "listening",
                                   "last_seen": now - 60}, HOST, False)
          == "elsewhere" and not hasattr(supervise, "left_behind"))
    # A machine that hands over to ITSELF -- a reboot, a `tutor down` and a
    # start -- honours the flag.
    check("a handover is honoured on the same node",
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
    make_workspace("HandedOver", agent={"host": HOST, "state": "stopped",
                                        "handover": "now", "agent": "claude",
                                        "last_seen": now})

    cfg = {"courses_dir": top, "provider": "claude",
           "agents": {"claude": {"cmd": ["claude"], "prompt": "argv",
                                 "headless": ["claude", "-p", "{prompt}"]}}}

    calls = {"board": [], "agent": [], "link": []}

    # The port the HTTPS name is proxying to. A number the tests move about,
    # because which board the name is on is the whole question the address pass
    # asks; 9001 is Up's, which is the healthy answer.
    holding = {"port": "9001"}
    # And whether the tailnet takes the claim. `tailscaled` runs on a node that
    # is not logged in, so a refusal is an ordinary answer and the exit code is
    # the only thing carrying it.
    refuses = {"serve": False}

    def fake_board(root, *args):
        calls["board"].append((os.path.basename(root), " ".join(args[:2])))
        if args[:3] == ("vpn", "serve", "--if-free"):
            calls["link"].append(os.path.basename(root))
            return 0, ""
        if args[0] == "vpn":
            if args[1:2] == ("serve",) and refuses["serve"]:
                return 1, "tailscale: not logged in\n"
            # `vpn holder` answers with the port the HTTPS name is proxying to,
            # and nothing else -- that is the contract the loop reads.
            return 0, holding["port"]
        return 0, "board up (pid 1)"

    def fake_agent_start(cfg_, course, name, session=None):
        calls["agent"].append((course["dir"], name))
        return 0, "%s starting in %s" % (name, course["dir"])

    alive = {101, 102, 202}          # DeadBoard's board pid is not in here

    daemon.board = fake_board
    daemon.agent_start = fake_agent_start
    processes.board_is_running = lambda pid, root: pid in alive
    processes.pid_alive = lambda pid, needle=None: pid in alive
    supervise.answering = lambda port, timeout=3.0: True
    machine.slurm_nodes = lambda: {HOST, HOST + "b"}
    # The tailnet link is up and the address points at a board that answers,
    # unless a case below says otherwise.
    tailscale.daemon_running = lambda: True
    # No code stamp, so the ship beat is inert in every pass that is not about
    # it; the one section that is sets a tree and puts this back. `test/shipped.py`
    # is the beat's own suite.
    stamp.tree = lambda tool=None: None

    memo = {}
    did = runwatch.watch_once(cfg, HOST, memo, lambda line: None)

    check("the dead board is started, and the live one is not touched",
          ("DeadBoard", "start") in calls["board"]
          and ("Up", "start") not in calls["board"])
    check("a board on another node that is STILL one of your allocations is left "
          "exactly where it is",
          ("Elsewhere", "start") not in calls["board"]
          and ("Elsewhere", "stop") not in calls["board"])
    check("a board that comes back is started and nothing more: `board start` "
          "offers it the address itself",
          "DeadBoard" not in calls["link"])

    # A BOARD WHOSE `/health` NEVER ANSWERS IS BACKED OFF, not bounced forever.
    # A clean start that clears the repair count lets a route that raises on
    # every probe restart all five boards every 55 seconds -- measured: 2,500
    # times in a night, with the iPad saying disconnected throughout.
    supervise.answering = lambda port, timeout=3.0: int(port) != 9001
    calls["board"] = []
    memo = {}
    for _ in range(6):
        runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("a board that is hung again straight after a clean start waits out "
          "the backoff rather than being restarted every other pass",
          calls["board"].count(("Up", "start")) == 1
          and memo["Up"]["board_tries"] >= 1)
    supervise.answering = lambda port, timeout=3.0: True
    runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("and the count clears once it answers",
          memo["Up"]["board_tries"] == 0)

    # THE ADDRESS IS CHECKED EVERY PASS, not only after a board starts. `link`
    # used to be called on a start alone, so a link that failed while a
    # board was coming up was never retried: on compute306 every process
    # was healthy, both boards answered on loopback, and the glass stayed white.
    def addr_lines(said):
        return [l for l in said if "the address was offered to" in l]

    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("with the link up and the address on a board that answers, the loop "
          "leaves the address alone",
          not addr_lines(said))
    tailscale.daemon_running = lambda: False
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("with no link on this node the address is offered to a board, even "
          "though no board needed starting",
          len(addr_lines(said)) == 1)
    # And it backs off like every other repair, so a node that cannot link does
    # not spend seven days trying every twenty seconds.
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("and a link that will not come up is not retried on the next pass",
          not addr_lines(said))
    tailscale.daemon_running = lambda: True

    # WHICH COURSE THE ONE ADDRESS IS FOR, which is the other half of keeping it
    # alive and the half that was wrong. Reported in the words it happened in:
    # "the address is not pointing at a board that answers, so the link was
    # brought up for Galois-Theory", while `chosen.json` said Probability and a
    # person was mid-homework in it. A second live board here, sorting first, is
    # that Galois-Theory.
    make_workspace("Alongside", board={"node": HOST, "pid": 601, "port": 9006})
    alive.add(601)

    def served(dirs):
        return [c for c in calls["board"] if c == (dirs, "vpn serve")]

    choice.remember_chosen("Up", os.path.join(tmp, "Up"))
    # AND THE FILES SAY OTHERWISE, which is the shape the fault arrived in. A
    # tutor writes cards and transcript pushes into its own course every few
    # minutes, so `live/` in whatever course is busiest is newer than the choice
    # within minutes of the choice being made, and a resolver that blends the
    # two has the busiest course outvote the person. Alongside is that course
    # here; the checks below are what has to fail if the address ever reads file
    # times again.
    newer = time.time() + 600
    os.utime(os.path.join(tmp, "Alongside", "live", ".board.json"),
             (newer, newer))
    holding["port"] = "9006"          # the name has ended up on the other board
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("a board that answers is not the test: the address on a course nobody "
          "chose is a fault, even though the glass is not white",
          any("nobody chose" in l for l in said))
    check("and it is taken back for the chosen course by the forced claim, since "
          "`link` asks first and another live board never says yes",
          served("Up") and "Up" not in calls["link"])
    check("the course somebody chose beats the newest files on disk, which is "
          "every course a tutor is running in",
          not served("Alongside"))

    # A WEDGED CHOSEN BOARD IS NOT WORTH THE NAME. Membership of `here` is a pid
    # and a node, which a wedged board passes: alive, holding its port,
    # answering nothing. Claiming for it trades a wrong lesson somebody can read
    # for a white screen, and the board half of the same pass is already fixing
    # the board -- so the name waits one pass rather than moving onto nothing.
    supervise.answering = lambda port, timeout=3.0: int(port) != 9001
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("the name is not pulled off a board that answers and onto the chosen "
          "course's own board that does not",
          not served("Up"))
    check("and standing still is said out loud, because a watchdog that holds "
          "the wrong course silently is the first fault wearing the other coat",
          any("left where it is" in l for l in said))
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("said on the way in and not once every pass for as long as it lasts",
          not any("left where it is" in l for l in said))
    # AND A PASS WITH NO BOARD UP HERE IS NOT THE STATE ENDING. An empty `here`
    # is what a restart looks like, which is the moment the address
    # is most likely to be stuck; a flag left set across it silences the line on
    # the way back in, for the rest of the episode.
    running = processes.board_is_running
    processes.board_is_running = lambda pid, root: False
    runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    processes.board_is_running = running
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("and said again after a pass with nothing up here at all, which is "
          "the state being left rather than the state ending",
          any("left where it is" in l for l in said))
    supervise.answering = lambda port, timeout=3.0: True

    # A CLAIM THE TAILNET REFUSED IS NOT A REPAIR. The gate is `tailscaled`
    # running, which is true on a node that is not logged in, and the forced
    # claim never runs `board vpn up` first: the exit code is the only thing
    # that knows whether the name moved.
    refuses["serve"] = True
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("a claim the tailnet refused is reported as refused, not as the "
          "address being back where it belongs",
          served("Up") and any("would not go through" in l for l in said)
          and not any("pointed back at" in l for l in said))
    refuses["serve"] = False

    holding["port"] = "9001"          # back on Up, which is the chosen course
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("with the address on the chosen course's own board, nothing is claimed",
          not served("Up") and "Up" not in calls["link"]
          and not addr_lines(said))

    # NOBODY HAS CHOSEN, so the first board here is a guess, and a guess may keep
    # the address alive but may never move it off a board that is answering --
    # that is the whole of why `link` asks before it takes.
    os.remove(paths.CHOSEN)
    holding["port"] = "9006"
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("with no choice standing, the alphabet does not get to move the "
          "address off a board that is answering",
          not served("Alongside") and not served("Up")
          and "Alongside" not in calls["link"])

    # ANSWERING IS NOT OWNING, and a guess is not the exception to it either. A
    # board an ended process left behind answers exactly like a live one and
    # is named by no record, so the answering test alone calls the name resting
    # on it healthy for as long as that process lives -- but it still draws, and
    # the alphabet is no better an answer for a leftover than for a live board.
    holding["port"] = "9098"
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("with nobody having chosen, a leftover holding the name is left "
          "holding it rather than traded for whichever course sorts first",
          not served("Alongside") and not served("Up")
          and "Alongside" not in calls["link"])

    # And with a choice standing, the chosen board's own port is what takes the
    # name off the leftover -- the same test as drift, because a leftover's port
    # is not the chosen board's port either.
    choice.remember_chosen("Up", os.path.join(tmp, "Up"))
    calls["board"], calls["link"] = [], []
    memo = {}
    said = runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("and a choice standing takes the name off the leftover, onto the "
          "board a record here actually names",
          served("Up") and any("nobody chose" in l for l in said))
    os.remove(paths.CHOSEN)
    holding["port"] = "9006"

    choice.remember_chosen("Elsewhere", os.path.join(tmp, "Elsewhere"))
    calls["board"], calls["link"] = [], []
    memo = {}
    runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("and a choice whose board is on another node is not this node's to "
          "honour either",
          not served("Alongside") and not served("Up")
          and "Alongside" not in calls["link"])
    os.remove(paths.CHOSEN)
    holding["port"] = "9001"

    check("a tutor that is listening is not restarted",
          ("Up", "claude") not in calls["agent"])
    check("a tutor a person stopped is not restarted",
          ("Stopped", "claude") not in calls["agent"])
    check("a tutor whose own stop was a handover is picked back up",
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

    daemon.board = failing_board
    memo = {}
    runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    first = len([c for c in calls["board"] if c[0] == "DeadBoard"])
    runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    second = len([c for c in calls["board"] if c[0] == "DeadBoard"])
    check("a repair that failed is not tried again immediately",
          first >= 1 and second == first)

    # A wedged board -- alive, holding its port, answering nothing -- has to be
    # stopped before it is started, or the new one cannot have the port.
    calls["board"] = []
    daemon.board = fake_board
    supervise.answering = lambda port, timeout=3.0: False
    memo = {}
    for _ in range(supervise.HEALTH_MISSES):
        runwatch.watch_once(cfg, HOST, memo, lambda line: None)
    check("a wedged board is stopped and then started, in that order",
          calls["board"].index(("Up", "stop")) < calls["board"].index(("Up", "start")))
    supervise.answering = lambda port, timeout=3.0: True

    # =======================================================================
    # A ship lands on this node's boards, through this same pass
    # =======================================================================
    # The checkout is shared, so this node has the new files the moment
    # a ship commits; what is stale is the process. One pass restarts a board
    # here whose recorded stamp is not the tree's, and leaves another node's.
    make_workspace("Shipped", board={"node": HOST, "pid": 701, "port": 9007,
                                     "code": "OLD"})
    make_workspace("ShippedThere", board={"node": HOST + "b", "pid": 702,
                                          "port": 9008, "code": "OLD"})
    alive.update({701, 702})
    real_board = daemon.board

    def shipping_board(root, *args):
        got = real_board(root, *args)
        if args[:1] == ("start",):
            path = os.path.join(root, "live", ".board.json")
            with open(path, encoding="utf-8") as fh:
                rec = json.load(fh)
            rec["code"] = "T"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rec, fh)
        return got
    daemon.board = shipping_board
    stamp.tree = lambda tool=None: "T"
    stamp.blocked = lambda tool=None: None
    stamp.imports = lambda tool=None, timeout=30: (True, "")
    stamp.LOCK = os.path.join(state, "restart.lock")
    real_lock = stamp.restart_lock
    stamp.restart_lock = (lambda wait=True, path=None:
                                real_lock(wait, os.path.join(state, "restart.lock")))
    # Nothing here may signal or spawn: the tutors in these workspaces are
    # fixtures, and their pids are somebody's real processes.
    real_live, real_host = daemon.agent_live, recipes.this_host
    daemon.agent_live = lambda root: None
    recipes.this_host = lambda: HOST
    calls["board"], calls["link"] = [], []
    said = runwatch.watch_once(cfg, HOST, {}, lambda line: None)
    daemon.agent_live, recipes.this_host = real_live, real_host
    check("a board whose stamp is not the tree's is restarted by one pass of "
          "the watch on its own node",
          ("Shipped", "stop") in calls["board"]
          and ("Shipped", "start") in calls["board"]
          and any("Shipped: board restarted on T" in l for l in said))
    check("and a board on another node is not touched by this node's pass",
          not any(w == "ShippedThere" and act in ("stop", "start")
                  for w, act in calls["board"]))
    daemon.board = real_board
    stamp.tree = lambda tool=None: None
    stamp.restart_lock = real_lock
    for w in ("Shipped", "ShippedThere"):
        shutil.rmtree(os.path.join(tmp, w), ignore_errors=True)
    alive.difference_update({701, 702})

    # --- `tutor down`, which hands a machine's boards over ---
    src_tutor = open(os.path.join(ROOT, "tutorboard", "runner", "watch.py"),
                     encoding="utf-8").read()
    check("`tutor down` exists to be the other half of `tutor resume`, and it "
          "waits for the handoff rather than dropping the lesson",
          "def cmd_down(" in src_tutor and "agent_stop(c, wait=True)" in src_tutor)
    check("it marks the stop as a handover, so whoever takes the workspace over "
          "knows to pick the tutor back up",
          src_tutor.index("def cmd_down(") < src_tutor.index("handover=time.strftime")
          < src_tutor.index("agent_stop(c, wait=True)"))
    check("it never reaches for a board that belongs to another node: `board "
          "stop` cannot stop one and DELETES the record, which leaves the "
          "process serving with nothing naming it and the next tutor start "
          "putting a second board on a fallback port",
          'if on and on != host:' in src_tutor
          and "left alone" in src_tutor)
    check("and it lets go of the tailnet link only when no single workspace was "
          "named, because the link belongs to the machine",
          'if not named:' in src_tutor and '"vpn", "down"' in src_tutor)
    check("the watch loop cannot die of the thing it is watching",
          "A WATCHDOG MAY NOT DIE OF THE THING IT IS WATCHING" in src_tutor)
finally:
    shutil.rmtree(top, ignore_errors=True)
    shutil.rmtree(conf, ignore_errors=True)
    shutil.rmtree(state, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "the board repairs itself, and leaves alone what nobody asked for")
sys.exit(1 if fails else 0)
