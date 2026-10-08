#!/usr/bin/env python3
"""`tutor resume` brings the board back on the Mac, and is a stub on the cluster.

Boards run on the Mac and nowhere else. On a Slurm host `tutor resume` says so,
exits 0 and starts nothing, so an old login hook costs one line. On the Mac it
revives a board whose process died, catches the chosen course up, starts its
board and attaches its tutor.
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)
from tutorboard.runner import daemon  # noqa: E402
from tutorboard import gitsync  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard import relay  # noqa: E402

from tutorboard import paths, processes

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


tmp = tempfile.mkdtemp(prefix="tutor-resume-")
calls = {"start": [], "agent": [], "sync": []}

# Nothing here may touch the config of whoever is running it. `cmd_resume`
# records a course that was named on the command line, and this file names one
# in nearly every case -- the first version of this test wrote its temporary
# course names into a real ~/.config/tutor-board/chosen.json.
conf = tempfile.mkdtemp(prefix="tutor-resume-conf-")
recipes.CONFIG_DIR = conf
# The record of what a person chose is one file with one reader, in boardlib --
# the launcher writes it, the board writes it when the hub is tapped, and the
# and the hub writes it when a course is tapped. Point that one place at the
# sandbox.
paths.CONFIG_DIR = conf
paths.CHOSEN = os.path.join(conf, "chosen.json")


def make_course(name, node=None, pid=1, when=None):
    root = os.path.join(tmp, name)
    os.makedirs(os.path.join(root, "live"), exist_ok=True)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": name, "mode": "math"}, fh)
    if node:
        rec = os.path.join(root, "live", ".board.json")
        with open(rec, "w", encoding="utf-8") as fh:
            json.dump({"node": node, "pid": pid, "port": 8787, "root": root}, fh)
        if when:
            os.utime(rec, (when, when))
    return root


try:
    make_course("Older", node="compute999", pid=11, when=1000)
    make_course("Newer", node="compute999", pid=22, when=9000)
    make_course("NeverRan")

    cfg = {"courses_dir": tmp, "default_agent": "claude",
           "agents": {"claude": {"cmd": ["claude"], "prompt": "argv",
                                 "headless": ["claude", "-p", "{prompt}"]}}}

    # --- what "the course you were last in" means ---------------------------
    picked = daemon.last_board(cfg)
    check("the most recently started board is the one to bring back",
          picked and picked["dir"] == "Newer")

    # `board stop` DELETES .board.json. A course you stopped cleanly is the one
    # you were most likely just using, and looking only at that record made it
    # invisible -- so the next login quietly resumed a different course and took
    # the tailnet name with it. Found by stopping a board and watching the wrong
    # one come back.
    stopped = os.path.join(tmp, "Stopped")
    os.makedirs(os.path.join(stopped, "live", "cards"), exist_ok=True)
    with open(os.path.join(stopped, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "Stopped", "mode": "math"}, fh)
    with open(os.path.join(stopped, "live", "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"course": "Stopped", "session": "lecture"}, fh)
    os.utime(os.path.join(stopped, "live", "state.json"), (20000, 20000))
    picked = daemon.last_board(cfg)
    check("a course whose board was stopped cleanly is still the one you were in",
          picked and picked["dir"] == "Stopped")
    shutil.rmtree(stopped)

    # A course nobody has ever opened is not a candidate, whatever else is there.
    check("and a course with nothing in its live/ is never picked",
          daemon.last_used(os.path.join(tmp, "NeverRan")) == 0)

    # Naming a course is a decision, and it has to outrank file times -- because
    # resuming a course TOUCHES its files, so "most recently used" is
    # self-reinforcing. Resume the wrong one once and it goes on being the most
    # recently used one for ever, quietly, taking the tailnet name each time.
    # That is not hypothetical: it happened, twice in a row, on a live board.
    try:
        check("with nothing named, the newest files decide",
              daemon.last_board(cfg)["dir"] == "Newer")
        daemon.remember_course({"dir": "Older", "root": os.path.join(tmp, "Older")})
        check("a course named just now beats one used an hour ago",
              daemon.last_board(cfg)["dir"] == "Older")
        # ...but not for ever: an afternoon in another course is newer than a
        # name given last week.
        import json as _json
        rec = _json.load(open(paths.CHOSEN))
        rec["at"] = 500
        _json.dump(rec, open(paths.CHOSEN, "w"))
        check("and an old name does not outrank a course worked in since",
              daemon.last_board(cfg)["dir"] == "Newer")
        # A name pointing at something that is no longer there is ignored.
        _json.dump({"dir": "Deleted", "root": "/nowhere", "at": 9e9},
                   open(paths.CHOSEN, "w"))
        check("a name pointing at a course that no longer exists is ignored",
              daemon.last_board(cfg)["dir"] == "Newer")
    finally:
        try:
            os.remove(paths.CHOSEN)      # back to "nothing has been named"
        except OSError:
            pass

    # --- stubs: nothing here may actually start a process -------------------
    def fake_board(root, *args):
        if args[0] == "start":
            calls["start"].append(os.path.basename(root))
            return 0, "board up (pid 1)"
        return 0, ""

    daemon.board = fake_board
    gitsync.sync = lambda root, quiet=False: calls["sync"].append(os.path.basename(root))
    relay.pull_vendor = lambda quiet=False: None
    daemon.agent_live = lambda root: None
    daemon.agent_start = lambda cfg, course, name: (
        calls["agent"].append(course["dir"]) or (0, "started"))
    recipes.this_host = lambda: "mac-mini"
    was_slurm = os.environ.get("TUTOR_SLURM")
    os.environ["TUTOR_SLURM"] = "0"          # this machine is the Mac

    def reset():
        for k in calls:
            calls[k] = []

    # --- a named course: caught up, started, and given a tutor --------------
    processes.board_is_running = lambda pid, root: False
    reset()
    tutor.cmd_resume(cfg, ["Newer", "--quiet"])
    check("a named course whose board is down is started here",
          calls["start"] == ["Newer"])
    check("and the course is caught up first, so a handoff is not missed",
          calls["sync"] == ["Newer"])
    check("and a tutor is attached, or the iPad has a board and nobody on it",
          calls["agent"] == ["Newer"])

    reset()
    tutor.cmd_resume(cfg, ["Newer", "--quiet", "--no-agent"])
    check("--no-agent brings the board up and leaves the tutor to you",
          calls["start"] == ["Newer"] and not calls["agent"])

    # --- already serving here: the common case, and it must be cheap --------
    try:
        os.remove(paths.CHOSEN)
    except OSError:
        pass
    processes.board_is_running = lambda pid, root: True
    make_course("Here", node="mac-mini", pid=33, when=9500)
    reset()
    tutor.cmd_resume(cfg, ["--quiet"])
    check("a board already running here is not restarted", not calls["start"])
    check("and it is still caught up, so a warm board never goes stale",
          calls["sync"] == ["Here"])

    # --- a board that DIED, on a machine nobody is sitting at ---------------
    make_course("Crashed", node="mac-mini", pid=44, when=200)
    processes.board_is_running = lambda pid, root: pid != 44
    reset()
    tutor.cmd_resume(cfg, ["--quiet"])
    check("a board whose process is gone is started again, without being asked",
          "Crashed" in calls["start"])
    check("a course nobody has ever opened is not started",
          "NeverRan" not in calls["start"])
    check("and neither is a board recorded on another machine",
          "Newer" not in calls["start"] and "Older" not in calls["start"])
    processes.board_is_running = lambda pid, root: True
    reset()
    tutor.cmd_resume(cfg, ["--quiet"])
    check("and a machine with nothing wrong with it starts nothing at all",
          not calls["start"])
    shutil.rmtree(os.path.join(tmp, "Crashed"), ignore_errors=True)

    # --- a machine where nothing has ever run -------------------------------
    empty = tempfile.mkdtemp(prefix="tutor-resume-empty-")
    try:
        os.makedirs(os.path.join(empty, "Fresh", "live"))
        with open(os.path.join(empty, "Fresh", "tutorboard.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"name": "Fresh", "mode": "math"}, fh)
        reset()
        code = tutor.cmd_resume(dict(cfg, courses_dir=empty), ["--quiet"])
        check("a machine where no board has ever run starts nothing",
              code == 0 and not calls["start"])
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    # --- on the cluster: a stub that starts nothing --------------------------
    os.environ["TUTOR_SLURM"] = "1"
    reset()
    code = tutor.cmd_resume(cfg, ["Newer"])
    check("on a Slurm host resume exits 0 and starts nothing",
          code == 0 and not calls["start"] and not calls["agent"]
          and not calls["sync"])
    if was_slurm is None:
        os.environ.pop("TUTOR_SLURM", None)
    else:
        os.environ["TUTOR_SLURM"] = was_slurm

    # The whole command, as a process, with a fake `squeue` on PATH and nothing
    # else changed: it must say boards run on the Mac, exit 0, and start no
    # `serve.py`.
    import subprocess  # noqa: E402
    farm = tempfile.mkdtemp(prefix="tutor-resume-squeue-")
    try:
        fake = os.path.join(farm, "squeue")
        with open(fake, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho compute301\n")
        os.chmod(fake, 0o755)
        env = dict(os.environ, PATH=farm + os.pathsep + os.environ.get("PATH", ""),
                   HOME=farm, XDG_CONFIG_HOME=os.path.join(farm, "cfg"),
                   BOARD_STATE_DIR=os.path.join(farm, "state"),
                   TUTORBOARD_COURSES=tmp)
        env.pop("TUTOR_SLURM", None)
        before = subprocess.run(["pgrep", "-f", "serve.py --root " + tmp],
                                stdout=subprocess.PIPE).stdout
        got = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "tutor"),
                              "resume", "Newer"], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=120)
        after = subprocess.run(["pgrep", "-f", "serve.py --root " + tmp],
                               stdout=subprocess.PIPE).stdout
        said = got.stdout.decode("utf-8", "replace")
        check("with a fake squeue on PATH, `tutor resume` exits 0",
              got.returncode == 0)
        check("and says boards run on the Mac", "boards run on the Mac" in said)
        check("and starts no serve.py", before == after == b"")
    finally:
        shutil.rmtree(farm, ignore_errors=True)

    # --- the old login hook comes out ----------------------------------------
    home = tempfile.mkdtemp(prefix="tutor-resume-home-")
    try:
        rc = os.path.join(home, ".bashrc")
        with open(rc, "w", encoding="utf-8") as fh:
            fh.write("# something the user already had\nexport KEEP_ME=1\n\n"
                     "# >>> tutor-board resume >>>\n"
                     "\"$HOME/.local/bin/tutor\" resume --quiet\n"
                     "# <<< tutor-board resume <<<\n")
        env = dict(os.environ, HOME=home)
        script = os.path.join(ROOT, "scripts", "install-autostart.sh")
        run = subprocess.run(["bash", script, "--login-hook"], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=60)
        check("install-autostart installs nothing any more",
              run.returncode != 0
              and open(rc, encoding="utf-8").read().count("resume --quiet") == 1)
        subprocess.run(["bash", script, "--uninstall"], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
        after = open(rc, encoding="utf-8").read()
        check("and --uninstall takes the old hook out cleanly",
              "tutor-board resume" not in after and "resume --quiet" not in after)
        check("leaving the file otherwise as it was", "KEEP_ME" in after)
    finally:
        shutil.rmtree(home, ignore_errors=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(conf, ignore_errors=True)

print()
# A restart must survive a broken agent record.
#
# `os.kill(None, ...)` raises TypeError, not OSError, so a half-written
# `agent.json` -- which is what a daemon killed with its state directory pulled
# out from under it leaves -- took the whole restart down, every course after it
# included. Found by wiping the boards while one was running.
src_t = open(os.path.join(ROOT, "tutorboard", "runner", "watch.py"),
             encoding="utf-8").read()
check("a restart skips a record with no pid rather than dying on it",
      "if not was:" in src_t and '"%s (no pid in its record)"' in src_t)

# One command to put a machine right.
#
# A machine nobody is sitting at never restarts the processes holding the old
# code, so every fix shipped from elsewhere sits on its disk -- two kinds of
# process and two kinds of repository, and remembering that list is not
# somebody's job.
script = os.path.join(ROOT, "scripts", "catch-up.sh")
check("there is a script that catches a machine up in one command",
      os.path.isfile(script))
src_c = open(script, encoding="utf-8").read()
check("it pulls the repository first and re-runs itself on what arrived, since "
      "everything below it reads this repository",
      'git -C "$COURSES" pull --ff-only' in src_c and "exec bash" in src_c)
check("and moves vendor/colibri forward with it, because a login is the one "
      "moment a compute node gets",
      "submodule update --init --remote --merge vendor/colibri" in src_c)
check("but never vendor/colibri-build, which is pinned: a build tree that moves "
      "underneath a build is the failure it exists to avoid",
      "--remote --merge vendor/colibri-build" not in src_c)

# ELEVEN repositories became ONE, and most of this script went with them. It
# used to fetch, stash, tag and `reset --hard` each course onto its origin --
# machinery that existed because eleven working trees could each be in the wrong
# place independently. There is one working tree now and one `--ff-only` pull,
# which CANNOT rewrite anything: the worst it does is decline.
#
# So the tag and the stash are not guards that were removed. They were the
# safety rails on a cliff, and the cliff is gone. What is asserted here is the
# stronger property that replaced them.
check("it cannot reset or force anything -- a pull that will not fast-forward "
      "says so and changes nothing, which is what removed the need to tag first",
      "reset --hard" not in src_c and "--force" not in src_c
      and "stash push" not in src_c)
check("it still refuses to touch a repository somebody is part-way through, "
      "because that is what holds the one index and the one HEAD",
      "rebase-merge rebase-apply MERGE_HEAD" in src_c
      and "left exactly as it is" in src_c)
check("and still refuses a detached HEAD, where origin/HEAD reads as a branch "
      "name and walked somebody onto the remote's default branch once",
      '--abbrev-ref HEAD 2>/dev/null)" = "HEAD"' in src_c)
check("it walks TWO levels, a family then a workspace, not one",
      '"$COURSES"/*/*/' in src_c)
check("and does not count the board's own scratch as somebody's uncommitted "
      "work, which made every workspace with a board on it look like it needed "
      "rescuing",
      "grep -Ev '(^|/)live/'" in src_c)
check("it restarts the boards and the tutors",
      'restart --tutors' in src_c)
check("and then says what is actually true: what is running, and how to reach "
      "each board directly",
      "how to reach each of them" in src_c)
check("with a --report mode that changes nothing",
      "--report) REPORT=1" in src_c)

print("%d FAILURES" % len(fails) if fails
      else "the board comes back on the Mac, and the cluster starts none")
sys.exit(1 if fails else 0)
