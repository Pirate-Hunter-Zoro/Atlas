#!/usr/bin/env python3
"""A ship takes effect on whichever node is serving.

The checkout is on the shared filesystem, so a ship puts the new files in front
of every node the moment it commits, and no node ever sees a pull move HEAD.
What is stale is the processes: a board read `serve.py` when it started. So each
process records the code stamp it loaded, the serving node's watch compares it
with the tree's on every beat, and `tutor restart --wait` reads the records to
say where a ship landed -- with no ssh, from any machine.

What is asserted is mostly what the beat must NOT do: touch another node's
board, bounce anything for a lesson commit, bounce a tutor mid-turn, move the
address, run twice at once, retry a board that failed on the same stamp, or
bounce anything onto a tree that does not import.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

state = tempfile.mkdtemp(prefix="tutor-shipped-state-")
os.environ["BOARD_STATE_DIR"] = state

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

from tutorboard import machine, missions, paths, processes, stamp, supervise  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


tmp = tempfile.mkdtemp(prefix="tutor-shipped-")
conf = tempfile.mkdtemp(prefix="tutor-shipped-conf-")
gitdir = tempfile.mkdtemp(prefix="tutor-shipped-git-")
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
THERE = "compute303"
LOCK = os.path.join(state, "restart.lock")


def make_workspace(name, board=None, agent=None):
    root = os.path.join(tmp, name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(os.path.join(root, "live"), exist_ok=True)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": name, "mode": "math"}, fh)
    if board is not None:
        write_json(os.path.join(root, "live", ".board.json"), board)
    if agent is not None:
        write_json(os.path.join(root, "live", "agent.json"), agent)
    return root


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def rec_of(name):
    return read_json(os.path.join(tmp, name, "live", ".board.json")) or {}


def git(*args):
    return subprocess.run(["git", "-C", gitdir] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=True)


def commit_file(rel, text):
    path = os.path.join(gitdir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel)
    stamp.forget()
    return stamp.tree(gitdir)


try:
    # =======================================================================
    # 1. The stamp moves on a ship and not on a lesson commit
    # =======================================================================
    git("init", "-q")
    commit_file("bin/tutor", "one\n")
    commit_file("serve.py", "one\n")
    first = commit_file("tutorboard/a.py", "one\n")
    check("a tree with the three stamped paths has a stamp", bool(first)
          and len(first) == 12)
    same = [commit_file("courses/x/answer.txt", "homework\n"),
            commit_file("web/board.js", "shell\n"),
            commit_file("test/t.py", "suite\n"),
            commit_file("bin/board", "cli\n")]
    check("a lesson commit, a shell file, a test and `bin/board` do not move it",
          same == [first] * 4)
    moved = [commit_file("tutorboard/a.py", "two\n"),
             commit_file("bin/tutor", "two\n"),
             commit_file("serve.py", "two\n")]
    check("`tutorboard/`, `bin/tutor` and `serve.py` each move it",
          len(set([first] + moved)) == 4)
    stamp.forget()
    check("and a directory that is not a checkout has no stamp at all",
          stamp.tree(tmp) is None)
    check("the stamp is read before the package is imported, in both entry "
          "points, or HEAD can move between the two and never be bounced",
          open(os.path.join(ROOT, "serve.py"), encoding="utf-8").read().index(
              "stamp.mark_loaded()")
          < open(os.path.join(ROOT, "serve.py"), encoding="utf-8").read().index(
              "from tutorboard.server.app import main")
          and tutor.stamp.__name__ == "tutorboard.stamp")
    src_tutor = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
    check("and the daemon's is read before the big import too",
          src_tutor.index("stamp.mark_loaded()")
          < src_tutor.index("from tutorboard import (atlas"))
    check("a waking record drops the last daemon's stamp",
          "host=this_host(), code=None," in src_tutor)

    # The import check, on a real tree and a broken one.
    ok, _ = stamp.imports(ROOT)
    check("the board's own tree imports", ok)
    commit_file("tutorboard/__init__.py", "")
    commit_file("tutorboard/server/__init__.py", "")
    commit_file("tutorboard/server/app.py", "def (:\n")
    ok, line = stamp.imports(gitdir)
    check("a tree that does not import says so, with the reason",
          not ok and "SyntaxError" in line)
    check("and the check writes nothing into the tree",
          not any("__pycache__" in d for d, _, _ in os.walk(gitdir))
          and not os.path.exists(os.path.join(gitdir, "bin", "tutorc")))

    # The lock, which is node-local.
    with stamp.restart_lock(True, LOCK) as a:
        with stamp.restart_lock(False, LOCK) as b:
            pass
    with stamp.restart_lock(False, LOCK) as c:
        pass
    check("a second restart does not get the lock while one holds it, and does "
          "once it is let go", a and not b and c)

    # =======================================================================
    # 2. The beat
    # =======================================================================
    cfg = {"courses_dir": tmp, "default_agent": "claude",
           "agents": {"claude": {"cmd": ["claude"], "prompt": "argv",
                                 "headless": ["claude", "-p", "{prompt}"]}},
           "hosts": {}}
    tree = {"now": "T"}
    calls = {"board": [], "kill": [], "handed": [], "imports": 0}
    holding = {"port": "9001"}
    refuse_start = set()
    on_start = {}
    ports = {"Up": 9001, "Along": 9002, "Current": 9003, "There": 9004}

    def fake_board(root, *args):
        name = os.path.basename(root)
        calls["board"].append((name, " ".join(args[:2])))
        if args[0] == "vpn":
            if args[1:2] == ("serve",):
                holding["port"] = str(ports[name])
            return 0, holding["port"]
        path = os.path.join(root, "live", ".board.json")
        if args[0] == "stop":
            # A board going down leaves the name on nothing, and the next one
            # up takes it -- which is the whole reason the holder is restored.
            if holding["port"] == str(ports[name]):
                holding["port"] = "9002"
            return 0, "stopped"
        if args[0] == "start":
            if name in on_start:
                on_start.pop(name)()
            if name in refuse_start:
                return 1, "board: port %d is taken\n" % ports[name]
            rec = read_json(path) or {}
            rec.update(code=tree["now"], started=time.time(), node=HOST)
            write_json(path, rec)
            return 0, "board up (pid 1)"
        return 0, ""

    def fake_imports(tool=None, timeout=30):
        calls["imports"] += 1
        return imports_ok["now"]
    imports_ok = {"now": (True, "")}

    real_kill = os.kill
    tutor.board = fake_board
    tutor.this_host = lambda: HOST
    tutor.stamp.tree = lambda tool=None: tree["now"]
    tutor.stamp.blocked = lambda tool=None: blocked["now"]
    blocked = {"now": None}
    tutor.stamp.imports = fake_imports
    real_lock = stamp.restart_lock
    tutor.stamp.restart_lock = lambda wait=True, path=None: real_lock(wait, LOCK)
    tutor.handed_off = lambda cfg_, course, name: (
        calls["handed"].append((course["dir"], name))
        or "it comes back on its own the moment that turn ends")
    tutor.os.kill = lambda pid, sig: calls["kill"].append(pid)
    tutor.agent_live = lambda root: (
        tutor.agent_record(root)
        if (tutor.agent_record(root) or {}).get("host") == HOST else None)
    processes.board_is_running = lambda pid, root: bool(pid)
    machine.slurm_nodes = lambda: {HOST, THERE}
    running_missions = {}
    tutor.missions.of = lambda root: running_missions.get(os.path.basename(root), [])

    make_workspace("Up", board={"node": HOST, "pid": 11, "port": 9001,
                                "code": "OLD"})
    make_workspace("Along", board={"node": HOST, "pid": 12, "port": 9002,
                                   "code": "T"})
    make_workspace("There", board={"node": THERE, "pid": 13, "port": 9004,
                                   "code": "OLD"})

    memo = {}
    said = tutor.ship_beat(cfg, HOST, memo, lambda line: None)
    check("a board here whose stamp is not the tree's is restarted by one beat",
          ("Up", "stop") in calls["board"] and ("Up", "start") in calls["board"]
          and "Up: board restarted on T" in said)
    check("a board already on the tree is not touched",
          not any(w == "Along" and a in ("stop", "start") for w, a in calls["board"]))
    check("and a board on another node is not touched by this node's beat",
          not any(w == "There" for w, a in calls["board"]))
    check("the address holder is the same course before and after -- the stop "
          "moved it and the beat gave it back",
          holding["port"] == "9001" and ("Up", "vpn serve") in calls["board"])
    ship = read_json(os.path.join(state, "ship-%s.json" % HOST)) or {}
    check("the beat says what it did where another machine can read it",
          ship.get("tree") == "T" and ship.get("host") == HOST
          and ship.get("boards", {}).get("Up") == "restarted on T"
          and time.time() - ship.get("at", 0) < 60)

    calls["board"] = []
    said = tutor.ship_beat(cfg, HOST, memo, lambda line: None)
    check("with every record on the tree, a beat does nothing at all",
          calls["board"] == [] and said == [])
    check("and the import check ran once for that stamp, not once a beat",
          calls["imports"] == 1)

    # A board that would not come back is not retried on the same stamp.
    make_workspace("Refuses", board={"node": HOST, "pid": 14, "port": 9005,
                                     "code": "OLD"})
    ports["Refuses"] = 9005
    refuse_start.add("Refuses")
    calls["board"] = []
    said = tutor.ship_beat(cfg, HOST, memo, lambda line: None)
    check("a board that will not restart says why",
          any(l.startswith("Refuses: board would not restart on T")
              and "port 9005 is taken" in l for l in said))
    calls["board"] = []
    tutor.ship_beat(cfg, HOST, memo, lambda line: None)
    check("and is not tried again on that stamp, every twenty seconds, for ever",
          not any(w == "Refuses" for w, a in calls["board"]))
    ship = read_json(os.path.join(state, "ship-%s.json" % HOST)) or {}
    check("and a later beat's record still carries why, for a machine that "
          "reads it after the beat that said so",
          "port 9005 is taken" in (ship.get("boards") or {}).get("Refuses", ""))
    refuse_start.discard("Refuses")
    tree["now"] = "T2"
    calls["board"] = []
    tutor.ship_beat(cfg, HOST, memo, lambda line: None)
    check("but is once the tree moves", ("Refuses", "start") in calls["board"])
    shutil.rmtree(os.path.join(tmp, "Refuses"))

    # A lesson commit: the stamp stays where it was, so nothing moves.
    tree["now"] = "T3"
    for w in ("Up", "Along"):
        rec = rec_of(w)
        rec["code"] = "T3"
        write_json(os.path.join(tmp, w, "live", ".board.json"), rec)
    calls["board"] = []
    said = tutor.ship_beat(cfg, HOST, {}, lambda line: None)
    check("a commit that did not move the stamp restarts nothing",
          calls["board"] == [] and said == [])

    # Guarded: the lock, an import failure, a busy checkout.
    tree["now"] = "T4"
    calls["board"] = []
    with real_lock(True, LOCK):
        said = tutor.ship_beat(cfg, HOST, {}, lambda line: None)
    check("with another restart holding the lock, a beat does nothing and does "
          "not wait", calls["board"] == [] and said == [])
    imports_ok["now"] = (False, "SyntaxError: invalid syntax")
    calls["imports"] = 0
    m2 = {}
    said = tutor.ship_beat(cfg, HOST, m2, lambda line: None)
    tutor.ship_beat(cfg, HOST, m2, lambda line: None)
    check("a tree that does not import bounces nothing, and says so once",
          calls["board"] == [] and calls["imports"] == 1
          and any("does not import" in l and "everything stays" in l for l in said))
    ship = read_json(os.path.join(state, "ship-%s.json" % HOST)) or {}
    check("and the landing record carries the reason for another machine",
          "does not import" in (ship.get("broken") or ""))
    # A check that could not run is not a broken tree, and is not remembered.
    tree["now"] = "T4b"
    imports_ok["now"] = (None, "Command timed out after 30 seconds")
    calls["imports"], calls["board"] = 0, []
    m4 = {}
    said = tutor.ship_beat(cfg, HOST, m4, lambda line: None)
    ship = read_json(os.path.join(state, "ship-%s.json" % HOST)) or {}
    check("an import check that timed out bounces nothing and is not called a "
          "broken tree", calls["board"] == [] and not ship.get("broken")
          and "did not finish" in (ship.get("unchecked") or ""))
    imports_ok["now"] = (True, "")
    tutor.ship_beat(cfg, HOST, m4, lambda line: None)
    check("and the next beat checks again, and lands",
          calls["imports"] == 2 and ("Up", "start") in calls["board"])
    calls["board"] = []
    blocked["now"] = "a rebase is in progress"
    said = tutor.ship_beat(cfg, HOST, {}, lambda line: None)
    check("a checkout in the middle of a rebase is not deployed from",
          calls["board"] == [] and any("rebase" in l for l in said))
    blocked["now"] = None
    check("the real guard answers a detached HEAD as well as a rebase",
          "detached" in open(os.path.join(ROOT, "tutorboard", "worktree.py"),
                             encoding="utf-8").read())

    # =======================================================================
    # 3. A tutor mid-turn is deferred, and bounced on a later beat
    # =======================================================================
    tree["now"] = "T5"
    for w in ("Up", "Along"):
        rec = rec_of(w)
        rec["code"] = "T5"
        write_json(os.path.join(tmp, w, "live", ".board.json"), rec)
    make_workspace("Tut", agent={"host": HOST, "pid": 4242, "state": "working",
                                 "agent": "codex", "code": "OLD",
                                 "last_seen": time.time()})
    calls["kill"], calls["handed"] = [], []
    m3 = {}
    said = tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("a tutor mid-turn is not signalled and nothing is spawned for it",
          calls["kill"] == [] and calls["handed"] == []
          and "Tut: tutor mid-turn; restarted on a later beat" in said)
    said = tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("and the deferral is said once, not every beat",
          not any("Tut" in l for l in said))
    live = os.path.join(tmp, "Tut", "live")
    tutor.agent_state(live, state="listening")
    said = tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    rec = read_json(os.path.join(live, "agent.json")) or {}
    check("once it is listening, a later beat bounces it without blocking",
          calls["kill"] == [4242] and rec.get("restarting") is True
          and any(l.startswith("Tut: tutor restarting on T5") for l in said))
    check("and it comes back as the agent it was, not whatever the default is",
          calls["handed"] == [("Tut", "codex")])
    calls["kill"] = []
    tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("a tutor already restarting is not signalled again", calls["kill"] == [])

    # A TUTOR THAT STARTS A TURN WHILE THE BEAT RESTARTS BOARDS IS LEFT ALONE.
    make_workspace("Race", agent={"host": HOST, "pid": 4545,
                                  "state": "listening", "agent": "claude",
                                  "code": "OLD", "last_seen": time.time()})
    make_workspace("Racer", board={"node": HOST, "pid": 16, "port": 9006,
                                   "code": "OLD"})
    ports["Racer"] = 9006
    on_start["Racer"] = lambda: tutor.agent_state(
        os.path.join(tmp, "Race", "live"), state="working")
    calls["kill"] = []
    said = tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    rec = read_json(os.path.join(tmp, "Race", "live", "agent.json")) or {}
    check("a tutor listening when the beat began and mid-turn by its turn in "
          "the loop is not signalled, and not marked restarting",
          ("Racer", "start") in calls["board"] and 4545 not in calls["kill"]
          and not rec.get("restarting")
          and any(l.startswith("Race: tutor mid-turn") for l in said))
    tutor.agent_state(os.path.join(tmp, "Race", "live"), state="listening")
    tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("and is bounced once that turn is over", 4545 in calls["kill"])
    for w in ("Race", "Racer"):
        shutil.rmtree(os.path.join(tmp, w))

    make_workspace("Mission", agent={"host": HOST, "pid": 4343,
                                     "state": "listening", "agent": "claude",
                                     "code": "OLD", "last_seen": time.time()})
    running_missions["Mission"] = [{"id": "t1", "state": "running"}]
    calls["kill"] = []
    said = tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("a tutor on a mission is deferred the same way",
          calls["kill"] == [] and any(l.startswith("Mission: tutor mid-turn")
                                      for l in said))
    running_missions.clear()
    tutor.ship_beat(cfg, HOST, m3, lambda line: None)
    check("and bounced once the mission ends", calls["kill"] == [4343])
    for w in ("Tut", "Mission"):
        shutil.rmtree(os.path.join(tmp, w))

    # =======================================================================
    # 3b. What `tutor restart` says about a tutor here it did not bounce
    # =======================================================================
    import contextlib
    import io
    real_sleep = time.sleep

    def restart(args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tutor.cmd_restart(cfg, args)
        return buf.getvalue()

    make_workspace("Busy", agent={"host": HOST, "pid": 4646, "state": "working",
                                  "agent": "claude", "code": "OLD",
                                  "last_seen": time.time()})
    write_json(os.path.join(state, "ship-%s.json" % HOST),
               {"host": HOST, "at": time.time(), "tree": tree["now"]})
    out = restart(["--tutors", "--stale"])
    check("a tutor mid-turn here, with this node's watch running the beat, is "
          "named as restarted after the turn rather than left alone",
          "Busy: mid-turn; this node's watch restarts it after the turn" in out
          and "left alone: Busy" not in out)
    os.remove(os.path.join(state, "ship-%s.json" % HOST))
    out = restart(["--tutors", "--stale"])
    check("and with no watch here, it says nobody will",
          "left alone: Busy (mid-turn; no watch here will restart it)" in out)

    # A handoff that overruns ninety seconds, with no --wait: no waiting at all.
    tutor.agent_state(os.path.join(tmp, "Busy", "live"), state="listening")
    waited = []
    real_await = tutor.await_elsewhere
    tutor.await_elsewhere = lambda *a: waited.append(a) or 0
    tutor.time.sleep = lambda s: None
    out = restart(["--tutors"])
    tutor.time.sleep = real_sleep
    tutor.await_elsewhere = real_await
    check("a --tutors restart without --wait whose handoff overran never waits "
          "on another node", "still writing its handoff" in out and waited == [])
    shutil.rmtree(os.path.join(tmp, "Busy"))

    # =======================================================================
    # 4. `tutor restart --wait` says where the ship landed, on every node
    # =======================================================================
    tree["now"] = "T6"
    for w in ("Up", "Along"):
        rec = rec_of(w)
        rec["code"] = "T6"
        write_json(os.path.join(tmp, w, "live", ".board.json"), rec)
    tutor.SHIP_WAIT = 3

    def fresh_ship():
        write_json(os.path.join(state, "ship-%s.json" % THERE),
                   {"host": THERE, "at": time.time(), "tree": "T6",
                    "boards": {}, "tutors": {}})

    def lands(_s):
        rec = rec_of("There")
        rec.update(code="T6", started=time.time())
        write_json(os.path.join(tmp, "There", "live", ".board.json"), rec)

    fresh_ship()
    tutor.time.sleep = lands
    calls["board"] = []
    out = restart(["--stale", "--wait"])
    check("a board on another node is reported restarted on the new stamp once "
          "that node's watch has done it",
          "There on %s: restarted on T6" % THERE in out)
    check("and nothing that was then restarted is reported as left alone",
          "left alone" not in out)
    check("boards here already on the tree are not bounced by --stale",
          not any(a in ("stop", "start") for w, a in calls["board"])
          and "already on T6" in out)

    tutor.time.sleep = lambda s: real_sleep(0.05)
    rec = rec_of("There")
    rec["code"] = "OLD"
    write_json(os.path.join(tmp, "There", "live", ".board.json"), rec)
    os.remove(os.path.join(state, "ship-%s.json" % THERE))
    out = restart(["--stale", "--wait"])
    check("a node with no watch running the beat is named as such",
          "There on %s: not restarted -- no watch there runs the ship beat"
          % THERE in out)
    fresh_ship()
    machine.slurm_nodes = lambda: {HOST}
    out = restart(["--stale", "--wait"])
    check("a record on a node that is no longer yours is called a leftover",
          "There on %s: not restarted -- that node is no longer yours" % THERE
          in out)
    machine.slurm_nodes = lambda: {HOST, THERE}
    tutor.SHIP_WAIT = 0.3
    fresh_ship()
    out = restart(["--stale", "--wait"])
    check("and a node whose watch never got to it says it timed out, on which "
          "stamp", "There on %s: not restarted -- still on OLD" % THERE in out)
    write_json(os.path.join(state, "ship-%s.json" % THERE),
               {"host": THERE, "at": time.time(), "tree": "T6",
                "broken": "the tree does not import (SyntaxError)"})
    out = restart(["--stale", "--wait"])
    check("and a reason that node's beat recorded is passed on",
          "not restarted -- the tree does not import" in out)
    os.remove(os.path.join(state, "ship-%s.json" % THERE))
    out = restart(["--stale"])
    check("without --wait, a node with no watch beating is not promised a restart",
          "There on %s: not restarted -- no watch there runs the ship beat"
          % THERE in out)
    write_json(os.path.join(state, "ship-%s.json" % THERE),
               {"host": THERE, "at": time.time(), "tree": "T6"})
    out = restart(["--stale"])
    check("without --wait, another node's board is named with who restarts it",
          "There on %s: that node's watch restarts it on its next beat" % THERE
          in out and "left alone" not in out)

    # WHEN THE SHIP BEGAN decides "restarted" from "already on".
    tutor.SHIP_WAIT = 3
    fresh_ship()
    t0 = time.time() - 20
    rec = rec_of("There")
    rec.update(code="T6", started=t0)
    write_json(os.path.join(tmp, "There", "live", ".board.json"), rec)
    out = restart(["--stale", "--wait", "--since", str(t0 - 5)])
    check("a board that node's watch restarted during the push, before this "
          "command began, is still this ship's restart",
          "There on %s: restarted on T6" % THERE in out)
    out = restart(["--stale", "--wait"])
    check("and one that was on the tree before the ship began is already on it",
          "There on %s: already on T6" % THERE in out)

    # The tutors over there are waited for too, not read once.
    far = os.path.join(tmp, "Far", "live")
    make_workspace("Far", agent={"host": THERE, "pid": 77, "state": "listening",
                                 "agent": "claude", "code": "OLD",
                                 "started": t0, "last_seen": time.time()})
    steps = [lambda: tutor.agent_state(far, state="waking", code=None, pid=None),
             lambda: tutor.agent_state(far, state="listening", code="T6",
                                       pid=78, started=time.time())]
    tutor.time.sleep = lambda s: steps.pop(0)() if steps else real_sleep(0.05)
    out = restart(["--stale", "--wait", "--since", str(t0)])
    check("a tutor over there is waited for through waking, and reported "
          "restarted once it listens on the stamp",
          "Far's tutor on %s: restarted on T6" % THERE in out
          and "not restarted yet" not in out)
    tutor.time.sleep = lambda s: real_sleep(0.05)
    out = restart(["--stale", "--wait", "--since", str(time.time())])
    check("and a tutor over there already on the stamp is not called restarted",
          "Far's tutor on %s: already on T6" % THERE in out)
    tutor.agent_state(far, state="waking", code=None, pid=None)
    tutor.SHIP_WAIT = 0.3
    out = restart(["--stale", "--wait"])
    check("a tutor still waking when the wait runs out is coming back, not "
          "unrestarted", "Far's tutor on %s: coming back on T6" % THERE in out)
    tutor.agent_state(far, state="working", code="OLD", pid=79)
    out = restart(["--stale", "--wait"])
    check("and one mid-turn says its watch restarts it after the turn",
          "Far's tutor on %s: mid-turn; its watch restarts it after the turn"
          % THERE in out)
    shutil.rmtree(os.path.join(tmp, "Far"))
    tutor.time.sleep = real_sleep

    ship_src = open(os.path.join(ROOT, "scripts", "ship.sh"), encoding="utf-8").read()
    push_src = open(os.path.join(ROOT, "scripts", "save-and-push.sh"),
                    encoding="utf-8").read()
    check("ship.sh waits on the stamps rather than reaching over ssh",
          "tutor restart --tutors --stale --wait --since" in ship_src
          and ship_src.index('SINCE="$(date +%s)"')
          < ship_src.index("save-and-push.sh\" \"$MSG\"")
          and "ssh" not in ship_src.split("tutor restart")[-1])
    check("and a commit to the tool that loaded no new code bounces nothing",
          "tutor restart --stale" in push_src)
    check("the beat runs inside the watch pass, before the address is checked",
          src_tutor.index("did += ship_beat(cfg, host, memo, say)")
          < src_tutor.index("# --- THE ADDRESS, EVERY PASS")
          and src_tutor.index("def ship_beat(") < src_tutor.index("def watch_once("))

    # =======================================================================
    # 5. The glass can see a stale process
    # =======================================================================
    from tutorboard.course import repo as course_repo
    from tutorboard.server.handler import Handler
    from tutorboard.server.hub import Hub
    from tutorboard.server.tikz import TikzWorker
    from http.server import ThreadingHTTPServer
    course = make_workspace("Glass")
    repo = course_repo.Repo(course)
    hub = Hub(repo, TikzWorker(repo))
    hub.payload = json.dumps({})
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    httpd.repo = repo
    httpd.hub = hub
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    stamp.LOADED = "aaaaaaaaaaaa"
    stamp.tree = lambda tool=None: "bbbbbbbbbbbb"

    def get(path):
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path),
                                    timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    plain = get("/health")
    asked = get("/health?code=1")
    check("plain /health carries no stamp, because it is polled all the time",
          plain.get("ok") and "code" not in plain)
    check("/health?code=1 names the code running and the tree's",
          asked.get("code", {}).get("running") == "aaaaaaaaaaaa"
          and asked["code"].get("tree") == "bbbbbbbbbbbb"
          and "tutor" in asked["code"])
    httpd.shutdown()

    # =======================================================================
    # The watch loop puts itself on the tree's code too
    # =======================================================================
    said = []
    memo = {}
    stamp.LOADED = "aaaaaaaaaaaa"
    stamp.tree = lambda tool=None: "aaaaaaaaaaaa"
    blocked["now"] = None
    imports_ok["now"] = (True, "")
    check("a watch loop on the tree's stamp stays as it is",
          tutor.watch_stale(memo, said.append) is False)
    stamp.tree = lambda tool=None: "cccccccccccc"
    blocked["now"] = "a rebase is in progress"
    check("a watch loop behind a busy checkout waits for the next pass",
          tutor.watch_stale(memo, said.append) is False)
    blocked["now"] = None
    imports_ok["now"] = (False, "SyntaxError")
    check("a watch loop stays on its code when the tree does not import",
          tutor.watch_stale(memo, said.append) is False)
    memo = {}
    imports_ok["now"] = (True, "")
    check("a watch loop behind a tree that imports restarts itself, and says so",
          tutor.watch_stale(memo, said.append) is True
          and any("cccccccccccc" in l for l in said))
    stamp.LOADED = None
    check("a watch loop that never learned its own stamp is left alone",
          tutor.watch_stale({}, said.append) is False)
finally:
    try:
        os.kill = real_kill
    except NameError:
        pass
    for d in (tmp, conf, state, gitdir):
        shutil.rmtree(d, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "a ship lands on whichever node is serving, and says where it landed")
sys.exit(1 if fails else 0)
