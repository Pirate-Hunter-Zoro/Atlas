#!/usr/bin/env python3
"""Brew upkeep: scripts/brew-upgrade.py, the atlas.brew-upgrade LaunchAgent.

    python3 test/brew_upgrade.py

The script is loaded as a module with HOME, the XDG directories and the
board's state directory in a temp dir, and every tool it could reach is a
shim first on the PATH; the suite refuses to run when one resolves anywhere
else. Its `run` is stubbed for the package work, so nothing is ever upgraded:
the stub answers brew, pgrep, pmset, ioreg and the rest, and records each call
with its env. Brew's prefix is a fake Cellar, Caskroom and node_modules tree,
the LaunchAgent directories it scans are temp dirs, and a stub HTTP server is
the board. `install`, `off`, `on` and `status` run the real `run` against a
launchctl shim that keeps its loaded agents in a file.

  - THE GATE: the interval, the window, the host never upgrading outside it, a
    coding laptop only when overdue on AC and idle, the battery floor,
    first_seen, and an unreachable network that stamps nothing.
  - DEFER: another upgrader's plist means no upgrade call at all; a tailscale
    brew service and our own label are not one; the baseline tick acts on
    nothing; a moved fingerprint repairs the broken venv only; an unchanged
    one writes nothing.
  - BUSY and THE LOCK skip a tick with no call.
  - OUTDATED, HOLDS, A CASK FAILURE, THE ORDER, update-tools, DRY-RUN, R1.
  - THE PLIST, install, off, on, status, and brewcare's lines and summary.
"""

import contextlib
import importlib.util
import io
import json
import os
import plistlib
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ATLAS_REAL = os.path.dirname(BOARD)
SCRIPT = os.path.join(ATLAS_REAL, "scripts", "brew-upgrade.py")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:2000]) if detail else ""))


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


# Not "brew-upgrade-": a temp path that matched the upgrader pattern would make
# every plist here look like another upgrader.
work = os.path.realpath(tempfile.mkdtemp(prefix="atlas-bu-"))
home = os.path.join(work, "home")
shims = os.path.join(work, "shims")
CALLS = os.path.join(work, "calls.log")
LOADED = os.path.join(work, "loaded")
SYSTEM = ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
os.environ.update({
    "HOME": home, "PATH": os.pathsep.join([shims] + SYSTEM),
    "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
    "XDG_CONFIG_HOME": os.path.join(home, ".config"),
    "BOARD_STATE_DIR": os.path.join(work, "state"),
    "BREWTEST_CALLS": CALLS, "BREWTEST_LOADED": LOADED})
for k in ("TUTORBOARD_COURSES", "TUTORBOARD_SESSION", "TUTORBOARD_TURN"):
    os.environ.pop(k, None)

EXE = stat.S_IRWXU
LOGLINE = 'echo "$(basename "$0") $*" >>"$BREWTEST_CALLS"\n'
TOOLS = ("brew", "launchctl", "pmset", "ioreg", "pgrep", "pkill", "npm", "uv", "curl",
         "tailscale", "caffeinate", "osascript", "kpsewhich")
for tool in TOOLS:
    write(os.path.join(shims, tool), "#!/bin/bash\n" + LOGLINE + "exit 1\n", EXE)
write(os.path.join(shims, "launchctl"), "#!/bin/bash\n" + LOGLINE + """\
touch "$BREWTEST_LOADED"
case "$1" in
  print) grep -qx "${2##*/}" "$BREWTEST_LOADED" ;;
  bootout) grep -vx "${2##*/}" "$BREWTEST_LOADED" >"$BREWTEST_LOADED.new"
           mv "$BREWTEST_LOADED.new" "$BREWTEST_LOADED" ;;
  bootstrap) b="${3##*/}"; echo "${b%.plist}" >>"$BREWTEST_LOADED" ;;
esac
""", EXE)
for exe in ("latex", "pdflatex", "dvisvgm", "latexmk"):
    write(os.path.join(shims, exe), "#!/bin/bash\nexit 0\n", EXE)

for tool in TOOLS:
    where = shutil.which(tool)
    if where != os.path.join(shims, tool):
        print("REFUSED: %s resolves to %s, not the shim; nothing was run" % (tool, where))
        shutil.rmtree(work, ignore_errors=True)
        sys.exit(1)


# --- the board, a stub server: /health's turns and / -----------------------
BOARD_SAYS = {"running": [], "queued": {}}


class Board(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"turns": BOARD_SAYS}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


httpd = HTTPServer(("127.0.0.1", 0), Board)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_port
write(os.path.join(home, ".config", "tutor-board", "config.json"),
      json.dumps({"port": PORT}))

spec = importlib.util.spec_from_file_location("brew_upgrade_under_test", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
real_run = mod.run

# --- brew's prefix, the agent dirs, a fake Atlas ------------------------------
prefix = os.path.join(work, "prefix")
for d in ("Cellar/node/24.1", "Cellar/python@3.15/3.15.0", "Caskroom/foo-app/1.0"):
    os.makedirs(os.path.join(prefix, d))
write(os.path.join(prefix, "lib", "node_modules", "opencode-ai", "package.json"),
      json.dumps({"version": "1.0.0"}))
write(os.path.join(prefix, "lib", "node_modules", "@scope", "tool", "package.json"),
      json.dumps({"version": "2.0.0"}))
os.makedirs(os.path.join(prefix, "bin"))
for exe in ("brew", "npm"):
    shutil.copy(os.path.join(shims, exe), os.path.join(prefix, "bin", exe))
mod.PREFIX = prefix
agents = os.path.join(home, "Library", "LaunchAgents")
sys_agents = os.path.join(work, "LibraryLaunchAgents")
sys_daemons = os.path.join(work, "LibraryLaunchDaemons")
mod.AGENT_DIRS = [agents, sys_agents, sys_daemons]
mod.CAFFEINATE = os.path.join(shims, "caffeinate")
mod.tex_dirs = lambda: [shims]
atlas = os.path.join(work, "atlas")
mod.ATLAS = atlas
write(os.path.join(atlas, "Brewfile"), 'brew "uv"\n')
write(os.path.join(atlas, "projects", "A", "pyproject.toml"),
      '[project]\nname = "a"\n\n[project.optional-dependencies]\ntest = ["pytest"]\n')
write(os.path.join(atlas, "projects", "A", ".venv", "bin", "python"), "")
write(os.path.join(atlas, "projects", "B", "pyproject.toml"), '[project]\nname = "b"\n')
write(os.path.join(atlas, "projects", "B", ".venv", "bin", "python"), "")
write(os.path.join(atlas, "courses", "C", "notes.md"), "no python here\n")
TOOLS_SCRIPT = os.path.join(atlas, "ai-config", "scripts", "update-tools")
write(TOOLS_SCRIPT, "exit 0\n")
write(os.path.join(atlas, "ai-config", "scripts", "install-clis.sh"), "exit 0\n")
os.makedirs(os.path.join(home, ".local", "share", "uv", "python",
                         "cpython-3.11.17-macos-aarch64-none"))
STATE = mod.STATE
LOG = mod.LOG
VENV_A = os.path.join(atlas, "projects", "A", ".venv", "bin", "python")
VENV_B = os.path.join(atlas, "projects", "B", ".venv", "bin", "python")

MUTATING = (("brew", "update"), ("brew", "upgrade"), ("brew", "cleanup"),
            ("brew", "autoremove"), ("brew", "bundle", "install"), ("npm", "update"),
            ("uv", "sync"), ("uv", "python", "upgrade"), ("bash",), ("osascript",))


def nice(argv):
    """`brew upgrade --formula a`, with brew's and npm's path dropped."""
    first = os.path.basename(argv[0])
    rest = [os.path.relpath(a, atlas) if a.startswith(atlas + os.sep) else a
            for a in argv[1:]]
    return " ".join([first] + rest)


class Fake(object):
    """mod.run: canned answers, each call recorded."""

    def __init__(self):
        self.calls = []
        self.outdated = (0, json.dumps({"formulae": [], "casks": []}), "")
        self.info = {"casks": []}
        self.fail = set()
        self.brew_running = False
        self.other_running = ""
        self.apps_running = set()
        self.pmset = "Now drawing from 'AC Power'\n"
        self.idle_ns = 30 * 60 * 10 ** 9
        self.curl = 0
        self.bundle_ok = True
        self.broken = set()
        self.serve = "https://mini.tail.ts.net (tailnet only)\n|-- / proxy http://127.0.0.1:%d\n" % PORT
        self.pids = ""

    def __call__(self, argv, timeout, mutating=False, env=None, cwd=None):
        argv = [str(a) for a in argv]
        self.calls.append({"argv": argv, "s": nice(argv), "mutating": mutating,
                           "env": dict(env or {}), "cwd": cwd, "dry": mod.DRY})
        if mutating and mod.DRY:
            mod.log("[dry-run] would run %s" % " ".join(argv))
            return 0, "", ""
        s = nice(argv)
        prog = os.path.basename(argv[0])
        if prog == "brew":
            if argv[1:3] == ["outdated", "--json=v2"]:
                return self.outdated
            if argv[1:3] == ["info", "--cask"]:
                return 0, json.dumps(self.info), ""
            if argv[1:3] == ["bundle", "check"]:
                return (0, "The Brewfile's dependencies are satisfied.\n", "") \
                    if self.bundle_ok else (1, "", "brew bundle can't satisfy your Brewfile\n")
            for key in self.fail:
                if s.startswith(key):
                    return 1, "", "Error: %s went wrong\n" % key
            return 0, "", ""
        if prog == "pgrep":
            pat = argv[-1]
            if "Homebrew/brew" in pat:
                return (0, "4242\n", "") if self.brew_running else (1, "", "")
            if pat == "brew[-_]?upgrade":
                return (0, self.other_running, "") if self.other_running else (1, "", "")
            if pat == "scripts/brew-upgrade.py":
                return (0, self.pids, "") if self.pids else (1, "", "")
            for app in self.apps_running:
                if app in pat.replace("\\", ""):
                    return 0, "777\n", ""
            return 1, "", ""
        if prog == "pmset":
            return 0, self.pmset, ""
        if prog == "ioreg":
            return 0, '  |   "HIDIdleTime" = %d\n' % self.idle_ns, ""
        if prog == "curl":
            return self.curl, "", ""
        if prog == "python":
            return (1, "", "dyld: missing") if argv[0] in self.broken else (0, "", "")
        if prog == "kpsewhich":
            return 0, "".join("/tex/%s\n" % a for a in argv[1:]), ""
        if prog == "tailscale":
            return 0, self.serve, ""
        if prog == "launchctl":
            return 0, "", ""
        for key in self.fail:
            if s.startswith(key):
                return 1, "", "%s failed\n" % key
        return 0, "", ""

    def said(self, start=""):
        return [c["s"] for c in self.calls if c["s"].startswith(start)]

    def first(self, start):
        for i, c in enumerate(self.calls):
            if c["s"].startswith(start):
                return i
        return -1


def at(hour, day=12, minute=10):
    return datetime(2026, 10, day, hour, minute, 0)


def reset(hour=4, role="host", state=None, fake=None):
    for p in (STATE, LOG, mod.LOCK, mod.OFF_FILE, mod.ROLE_FILE, LOADED, CALLS):
        try:
            os.remove(p)
        except OSError:
            pass
    for d in mod.AGENT_DIRS:
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    if role == "coding":
        write(mod.ROLE_FILE, "coding\n")
    if state is not None:
        write(STATE, json.dumps(state))
    BOARD_SAYS.update({"running": [], "queued": {}})
    mod.now = lambda: at(hour)
    f = fake or Fake()
    mod.run = f
    good_board_agent()
    return f


def good_board_agent():
    with open(os.path.join(agents, "tutor-board.plist"), "wb") as fh:
        plistlib.dump({"Label": "tutor-board",
                       "ProgramArguments": [sys.executable, "serve.py"]}, fh)


def plist(dirpath, name, label, args):
    with open(os.path.join(dirpath, name), "wb") as fh:
        plistlib.dump({"Label": label, "ProgramArguments": args}, fh)


def state():
    try:
        return json.loads(read(STATE))
    except ValueError:
        return {}


def outdated(formulae=(), casks=()):
    return (0, json.dumps({
        "formulae": [dict({"name": n, "installed_versions": ["1.0"],
                           "current_version": "1.1", "pinned": False}, **extra)
                     for n, extra in formulae],
        "casks": [{"name": n, "installed_versions": ["1.0"], "current_version": "2.0"}
                  for n in casks]}), "")


UPGRADES = ("brew update", "brew upgrade", "brew bundle install", "brew cleanup",
            "npm", "bash ai-config/scripts/update-tools", "uv python upgrade",
            "bash ai-config/scripts/install-clis.sh")


def upgrade_calls(f):
    return [c["s"] for c in f.calls if c["s"].startswith(UPGRADES)]


try:
    # =======================================================================
    # the gate
    # =======================================================================
    f = reset(4)
    T = at(4)
    check("in the window, a day after the last attempt, on AC: go",
          mod.gate({"last_attempt": (T - timedelta(hours=21)).isoformat(),
                    "first_seen": (T - timedelta(days=5)).isoformat()}, "host")[0])
    go, why = mod.gate({"last_attempt": (T - timedelta(hours=19)).isoformat()}, "host")
    check("19 hours after the last attempt: no", not go and "19.0h ago" in why, why)
    mod.now = lambda: at(14)
    seen = {"first_seen": (at(14) - timedelta(days=5)).isoformat()}
    go, why = mod.gate(dict(seen), "host")
    check("the host, 5 days overdue at 14:00, is refused", not go and "window" in why, why)
    f.pmset = "Now drawing from 'AC Power'\n"
    f.idle_ns = 30 * 60 * 10 ** 9
    check("a coding laptop overdue at 14:00, on AC and idle 30 min: go",
          mod.gate(dict(seen), "coding")[0])
    f.idle_ns = 600 * 10 ** 9
    check("idle 10 minutes: no", not mod.gate(dict(seen), "coding")[0])
    f.idle_ns = 30 * 60 * 10 ** 9
    f.pmset = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t90%; discharging\n"
    check("on battery: no, outside the window", not mod.gate(dict(seen), "coding")[0])
    fresh = {"first_seen": (at(14) - timedelta(hours=2)).isoformat()}
    f.pmset = "Now drawing from 'AC Power'\n"
    go, why = mod.gate(dict(fresh), "coding")
    check("first_seen makes a fresh install wait for the window",
          not go and "not overdue" in why, why)
    mod.now = lambda: at(4)
    for text, want in (("Now drawing from 'AC Power'\n", True),
                       ("Now drawing from 'Battery Power'\n -Int\t39%; discharging\n", False),
                       ("Now drawing from 'Battery Power'\n -Int\t40%; discharging\n", True),
                       ("Now drawing from 'Battery Power'\n -Int\tcharge unknown\n", True)):
        f.pmset = text
        check("battery: %s -> %s" % (text.strip().splitlines()[-1].strip(), want),
              mod.gate({}, "host")[0] is want)
    f.pmset = "Now drawing from 'AC Power'\n"

    f = reset(4)
    f.curl = 22
    code = mod.main(["run"])
    st = state()
    check("an unreachable network skips without stamping last_attempt",
          code == 0 and "first_seen" in st and "last_attempt" not in st
          and not upgrade_calls(f), st)
    f = reset(4)
    mod.main(["run"])
    check("a fresh install in the window runs", state().get("last_result") == "ok"
          and "brew update" in f.said(), f.said())
    f = reset(14, state={"first_seen": (at(14) - timedelta(hours=1)).isoformat()})
    mod.main(["run"])
    check("and at 14:00 does not", not upgrade_calls(f) and "last_attempt" not in state(),
          f.said())

    # =======================================================================
    # defer
    # =======================================================================
    f = reset(4)
    plist(agents, "homebrew.mxcl.tailscale.plist", "homebrew.mxcl.tailscale",
          [os.path.join(prefix, "opt", "tailscale", "bin", "tailscaled")])
    plist(agents, "atlas.brew-upgrade.plist", "atlas.brew-upgrade",
          ["/usr/bin/python3", "/x/scripts/brew-upgrade.py", "run"])
    check("a tailscale brew service and our own label are not another upgrader",
          mod.other_upgrader() is None)
    write(os.path.join(sys_daemons, "broken.plist"), "not a plist")
    check("and an unreadable plist is skipped", mod.other_upgrader() is None)

    f = reset(4)
    plist(agents, "com.example.brewupgrade.plist", "com.example.brewupgrade",
          ["/Users/x/Media/run_brew_upgrade.sh"])
    check("another upgrader's plist is found",
          mod.other_upgrader() == ("com.example.brewupgrade",
                                   os.path.join(agents, "com.example.brewupgrade.plist")))
    f.broken = {VENV_A}
    f.bundle_ok = False
    mod.main(["run"])
    st = state()
    check("defer: no brew update, upgrade, bundle install, cleanup, npm, update-tools, "
          "uv python upgrade or install-clis", not upgrade_calls(f), upgrade_calls(f))
    check("the baseline tick acts on nothing and records the fingerprint",
          not f.said("uv sync") and not f.said("bash") and st.get("mode") == "defer"
          and st.get("fingerprint") == mod.fingerprint()
          and st["deferred_to"]["label"] == "com.example.brewupgrade", st)
    check("and reports what it saw",
          any("projects/A" in p["what"] for p in st.get("problems", []))
          and any("Brewfile" in p["what"] for p in st.get("problems", [])),
          st.get("problems"))
    before = read(STATE)
    f.calls = []
    os.utime(STATE, (1, 1))
    mod.main(["run"])
    check("an unchanged fingerprint writes no state",
          read(STATE) == before and os.stat(STATE).st_mtime == 1
          and not [c for c in f.calls if not c["s"].startswith("pgrep")], f.said())
    os.makedirs(os.path.join(prefix, "Cellar", "node", "24.2"))
    f.calls = []
    mod.main(["run"])
    st = state()
    check("a moved fingerprint runs uv sync for the broken venv only",
          f.said("uv sync") == ["uv sync --locked --extra test"]
          and [c["cwd"] for c in f.calls if c["s"].startswith("uv sync")]
          == [os.path.join(atlas, "projects", "A")]
          and not upgrade_calls(f) and st.get("fingerprint") == mod.fingerprint(),
          f.said())
    check("and leaves the Brewfile to setup", not f.said("brew bundle install")
          and any(p["fix"] == "bash scripts/setup.sh" for p in st["problems"]),
          st["problems"])
    shutil.rmtree(os.path.join(prefix, "Cellar", "node", "24.2"))

    # =======================================================================
    # busy, and the lock
    # =======================================================================
    for what, setup in (("a brew is running", lambda f: setattr(f, "brew_running", True)),
                        ("Media's brew_upgrade.py is running",
                         lambda f: setattr(f, "other_running",
                                           "999 /usr/bin/python3 /x/brew_upgrade.py\n")),
                        ("the board has a turn running",
                         lambda f: BOARD_SAYS.update({"running": ["s1"]}))):
        f = reset(4)
        setup(f)
        mod.main(["run", "--force"])
        check("busy (%s): the tick does nothing and stamps nothing" % what,
              not upgrade_calls(f) and not os.path.exists(STATE), f.said())
    f = reset(4, role="coding")
    f.other_running = "%d /usr/bin/python3 /a/scripts/brew-upgrade.py run\n" % os.getpid()
    BOARD_SAYS.update({"running": ["s1"]})
    mod.main(["run", "--force"])
    check("a coding laptop ignores the board, and this script is not another upgrader",
          "brew update" in f.said(), f.said())

    f = reset(4)
    os.makedirs(os.path.dirname(mod.LOCK), exist_ok=True)
    holder = subprocess.Popen([sys.executable, "-c",
                               "import fcntl,sys,time\n"
                               "fh=open(sys.argv[1],'a')\n"
                               "fcntl.flock(fh,fcntl.LOCK_EX)\n"
                               "print('held',flush=True)\n"
                               "time.sleep(60)\n", mod.LOCK],
                              stdout=subprocess.PIPE, universal_newlines=True)
    holder.stdout.readline()
    code = mod.main(["run", "--force"])
    holder.kill()
    holder.wait()
    check("a second process holding the lock: exit 0 and no work",
          code == 0 and not upgrade_calls(f) and not os.path.exists(STATE)
          and "another run holds the lock" in read(LOG), f.said())

    # =======================================================================
    # outdated
    # =======================================================================
    f = reset(4)
    f.outdated = (0, outdated([("wget", {})])[1],
                  "Warning: some tap is deprecated\n")
    mod.main(["run"])
    check("stderr warnings beside valid stdout JSON parse",
          "brew upgrade --formula wget" in f.said() and state()["last_result"] == "ok",
          f.said())
    for label, answer in (("a nonzero exit", (1, "", "Error: no network\n")),
                          ("bad JSON", (0, "Warning: {not json", ""))):
        f = reset(4)
        f.outdated = answer
        mod.main(["run"])
        st = state()
        check("brew outdated with %s: partial, no upgrade, no success, never "
              "\"everything is current\"" % label,
              st["last_result"] == "partial" and "last_success" not in st
              and not f.said("brew upgrade") and "brew outdated" in st["failed"]
              and "everything is current" not in read(LOG), (st, f.said()))

    # =======================================================================
    # holds
    # =======================================================================
    f = reset(4)
    f.outdated = outdated([("wget", {}), ("node", {"pinned": True}),
                           ("tailscale", {})])
    plist(sys_daemons, "homebrew.mxcl.tailscale.plist", "homebrew.mxcl.tailscale",
          ["/opt/homebrew/opt/tailscale/bin/tailscaled"])
    mod.main(["run"])
    st = state()
    check("a pinned formula and a brew-service tailscale on the host are held, "
          "the rest named", f.said("brew upgrade") == ["brew upgrade --formula wget"]
          and "brew unpin node" in st["held"]["node"]["why"]
          and "tailnet" in st["held"]["tailscale"]["why"], (f.said(), st.get("held")))
    f = reset(4, role="coding")
    f.outdated = outdated([("tailscale", {})])
    plist(sys_daemons, "homebrew.mxcl.tailscale.plist", "homebrew.mxcl.tailscale",
          ["/opt/homebrew/opt/tailscale/bin/tailscaled"])
    mod.main(["run"])
    check("a coding laptop upgrades it", "brew upgrade --formula tailscale" in f.said(),
          f.said())
    f = reset(4)
    f.outdated = outdated([("tailscale", {})])
    mod.main(["run"])
    check("and so does a host with no brew service",
          "brew upgrade --formula tailscale" in f.said(), f.said())

    f = reset(4)
    f.outdated = outdated(casks=["foo-app", "bar"])
    f.info = {"casks": [{"token": "foo-app", "artifacts": [{"app": ["Foo App.app"]}]},
                        {"token": "bar", "artifacts": [{"app": ["Bar.app"]}]}]}
    f.apps_running = {"Foo App"}
    for n in (1, 2, 3):
        f.calls = []
        mod.main(["run", "--force"])
        st = state()
        if n < 3:
            check("tick %d: a running app's cask waits, the rest upgrade" % n,
                  "brew upgrade --cask foo-app" not in f.said()
                  and "brew upgrade --cask bar" in f.said()
                  and st["cask_defers"].get("foo-app") == n
                  and "foo-app" not in st["held"], (f.said(), st))
    check("tick 3: it is held, named", "foo-app" in st["held"]
          and "Foo App.app was running at every upgrade" in st["held"]["foo-app"]["why"]
          and "brew upgrade --cask foo-app" not in f.said(), st.get("held"))
    f.apps_running = set()
    f.calls = []
    mod.main(["run", "--force"])
    st = state()
    check("and once it is quit, it upgrades and the count resets",
          "brew upgrade --cask foo-app" in f.said() and "foo-app" not in st["cask_defers"]
          and "foo-app" not in st["held"], (f.said(), st))

    f = reset(4)
    f.outdated = outdated(casks=["bar", "baz"])
    f.fail = {"brew upgrade --cask bar"}
    mod.main(["run"])
    st = state()
    check("a cask that fails: partial, named, and the next one still upgrades",
          st["last_result"] == "partial" and "bar" in st["failed"]
          and "brew upgrade --cask baz" in f.said(), (st, f.said()))

    # =======================================================================
    # the order, and the brew env
    # =======================================================================
    f = reset(4)
    f.outdated = outdated([("wget", {})])
    f.bundle_ok = False
    mod.main(["run"])
    order = [f.first(k) for k in ("brew upgrade --formula", "brew bundle install",
                                  "npm update -g", "bash ai-config/scripts/update-tools",
                                  "uv python upgrade", "python -c pass",
                                  "brew cleanup --prune=7")]
    check("formulae, bundle, npm, update-tools, uv, repairs, then cleanup last",
          -1 not in order and order == sorted(order)
          and f.calls[-1]["s"] == "brew cleanup --prune=7", f.said())
    check("no autoremove anywhere", not [s for s in f.said() if "autoremove" in s])
    brews = [c for c in f.calls if os.path.basename(c["argv"][0]) in ("brew", "npm")]
    check("every brew and npm call has NO_AUTO_UPDATE and NO_INSTALL_CLEANUP",
          brews and all(c["env"].get("HOMEBREW_NO_AUTO_UPDATE") == "1"
                        and c["env"].get("HOMEBREW_NO_INSTALL_CLEANUP") == "1"
                        for c in brews), brews[:2])
    check("update-tools runs through bash",
          f.said("bash ai-config/scripts/update-tools") == [
              "bash ai-config/scripts/update-tools"], f.said("bash"))
    check("no call names claude or codex",
          not [s for s in f.said() if "claude" in s or "codex" in s])
    os.rename(TOOLS_SCRIPT, TOOLS_SCRIPT + ".away")
    f = reset(4)
    mod.main(["run"])
    check("without update-tools nothing calls it",
          not [s for s in f.said() if "update-tools" in s], f.said())
    os.rename(TOOLS_SCRIPT + ".away", TOOLS_SCRIPT)

    # =======================================================================
    # dry-run
    # =======================================================================
    f = reset(4)
    f.outdated = outdated([("wget", {})], ["bar"])
    f.bundle_ok = False
    f.broken = {VENV_A}
    big = "line of an old log\n" * (mod.LOG_MAX // 18 + 10)
    write(LOG, big)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["run", "--dry-run"])
    out = buf.getvalue()
    real = [c for c in f.calls if c["mutating"] and not c["dry"]]
    sneaky = [c["s"] for c in f.calls if not c["mutating"]
              and c["s"].startswith(UPGRADES + ("uv sync",))]
    check("dry-run: no state, no lock, the log untrimmed",
          code == 0 and not os.path.exists(STATE) and not os.path.exists(mod.LOCK)
          and read(LOG) == big, out)
    check("and every mutating call is only described",
          not real and not sneaky and not f.said("brew update")
          and "[dry-run] would run" in out and "brew upgrade --formula wget" in out
          and "brew upgrade --cask bar" in out and "uv sync" in out
          and "index not refreshed (dry-run)" in out, (sneaky, out))
    check("and it prints the mode, the gate and each probe",
          "mode: own" in out and "gate: would run" in out and "probe venv" in out
          and "probe tex" in out, out)
    os.remove(LOG)
    mod.DRY = True
    code, o, e = real_run([os.path.join(prefix, "bin", "brew"), "upgrade"], 10,
                          mutating=True)
    mod.DRY = False
    check("the real run() under dry-run executes nothing mutating",
          (code, o, e) == (0, "", "") and "brew upgrade" not in read(CALLS))

    # =======================================================================
    # R1: the board's interpreter
    # =======================================================================
    f = reset(4)
    with open(os.path.join(agents, "tutor-board.plist"), "wb") as fh:
        plistlib.dump({"Label": "tutor-board",
                       "ProgramArguments": [os.path.join(work, "gone", "python3.15"),
                                            "serve.py"]}, fh)
    mod.main(["run"])
    check("a missing board interpreter runs board/install.sh on the host",
          "bash board/install.sh" in f.said(), f.said("bash"))
    f = reset(4)
    mod.main(["run"])
    check("a present one does not", "bash board/install.sh" not in f.said())
    f = reset(4, role="coding")
    with open(os.path.join(agents, "tutor-board.plist"), "wb") as fh:
        plistlib.dump({"Label": "tutor-board",
                       "ProgramArguments": ["/gone/python3"]}, fh)
    mod.main(["run"])
    check("a coding laptop never runs it", "bash board/install.sh" not in f.said()
          and not f.said("tailscale"), f.said())

    # =======================================================================
    # notifications, a coding laptop's
    # =======================================================================
    f = reset(4, role="coding")
    f.outdated = outdated(casks=["bar"])
    f.fail = {"brew upgrade --cask bar"}
    mod.main(["run"])
    first = f.said("osascript")
    f.calls = []
    mod.main(["run", "--force"])
    check("a coding laptop hears a failure once",
          len(first) == 1 and "bar did not upgrade" in first[0]
          and not f.said("osascript"), (first, f.said("osascript")))
    f = reset(4)
    f.outdated = outdated(casks=["bar"])
    f.fail = {"brew upgrade --cask bar"}
    mod.main(["run"])
    check("the host is never notified", not f.said("osascript"))

    # =======================================================================
    # the plist
    # =======================================================================
    mod.run = real_run
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main(["plist"])
    rendered = buf.getvalue()
    pl = plistlib.loads(rendered.encode())
    paths_in = [v for v in (pl["ProgramArguments"] + [pl["WorkingDirectory"],
                                                      pl["StandardOutPath"],
                                                      pl["StandardErrorPath"]])
                if v != "run"]
    check("the plist: absolute paths, its label, no RunAtLoad, hourly, system python",
          pl["Label"] == "atlas.brew-upgrade" and pl["RunAtLoad"] is False
          and pl["StartInterval"] == 3600
          and pl["ProgramArguments"][0] == "/usr/bin/python3"
          and pl["ProgramArguments"][1:] == [os.path.join(atlas, "scripts",
                                                          "brew-upgrade.py"), "run"]
          and all(os.path.isabs(p) for p in paths_in) and "@" not in rendered
          and pl["EnvironmentVariables"]["HOME"] == home, pl)
    if shutil.which("plutil", path="/usr/bin"):
        rp = os.path.join(work, "rendered.plist")
        write(rp, rendered)
        lint = subprocess.run(["/usr/bin/plutil", "-lint", rp], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)
        check("plutil -lint passes on it", lint.returncode == 0, lint.stdout)
    else:
        print("skip plutil -lint: no plutil here")

    # =======================================================================
    # install, off, on, status
    # =======================================================================
    reset(4)
    mod.run = real_run
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        c1 = mod.main(["install"])
        c2 = mod.main(["install"])
    out = buf.getvalue()
    boots = [l for l in read(CALLS).splitlines() if l.startswith("launchctl bootstrap")]
    check("install twice: one bootstrap, the link, the own-mode line",
          c1 == c2 == 0 and len(boots) == 1 and "atlas.brew-upgrade" in read(LOADED).split()
          and os.path.realpath(mod.LINK) == os.path.realpath(SCRIPT)
          and "upgrades brew daily 03:00-07:59" in out, (out, read(CALLS)))
    plist(agents, "com.example.brewupgrade.plist", "com.example.brewupgrade", ["/x/y"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main(["install"])
    check("with another upgrader it says it defers",
          "defers to com.example.brewupgrade (repairs only)" in buf.getvalue(),
          buf.getvalue())

    f = Fake()
    victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)",
                               "scripts/brew-upgrade.py"])
    f.pids = "%d\n%d\n" % (victim.pid, os.getpid())

    def off_run(argv, timeout, mutating=False, env=None, cwd=None):
        if os.path.basename(argv[0]) == "pgrep":
            return f(argv, timeout, mutating, env, cwd)
        return real_run(argv, timeout, mutating, env, cwd)
    mod.run = off_run
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["off"])
    try:
        victim.wait(timeout=10)
        killed = victim.returncode == -signal.SIGTERM
    except subprocess.TimeoutExpired:
        victim.kill()
        killed = False
    check("off: booted out, the plist gone, the off switch written, the lock holder "
          "stopped", code == 0 and "atlas.brew-upgrade" not in read(LOADED).split()
          and not os.path.exists(mod.AGENT) and os.path.exists(mod.OFF_FILE) and killed,
          (buf.getvalue(), read(CALLS)))
    mod.run = real_run
    open(CALLS, "w").close()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["install"])
    check("and a later install loads nothing", code == 0
          and "off by owner (atlas-brew on)" in buf.getvalue()
          and not read(CALLS) and not os.path.exists(mod.AGENT), buf.getvalue())
    f = Fake()
    mod.run = f
    mod.now = lambda: at(4)
    mod.main(["run", "--force"])
    check("and a tick does nothing", not f.calls and not os.path.exists(STATE))
    mod.run = real_run
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["on"])
    check("on: the switch removed, loaded again", code == 0
          and not os.path.exists(mod.OFF_FILE)
          and "atlas.brew-upgrade" in read(LOADED).split(), buf.getvalue())

    write(STATE, json.dumps({"mode": "own", "last_attempt": "2026-10-12T03:30:00",
                             "last_result": "ok", "held": {}, "failed": {},
                             "problems": []}))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        clean = mod.main(["status"])
    write(STATE, json.dumps({"mode": "own", "problems": [{"what": "x", "fix": "y"}]}))
    with contextlib.redirect_stdout(buf):
        bad = mod.main(["status"])
    check("status exits 0 clean and 1 with a problem, saying it",
          clean == 0 and bad == 1 and "PROBLEM   x; y" in buf.getvalue()
          and "loaded:    yes" in buf.getvalue(), buf.getvalue())
    check("an unknown command exits 2", mod.main(["upgrade"]) == 2
          and mod.main(["run", "--greedy"]) == 2)

    # =======================================================================
    # brewcare
    # =======================================================================
    sys.path.insert(0, BOARD)
    from tutorboard import brewcare                          # noqa: E402
    sd = os.path.join(work, "care")
    os.makedirs(sd)
    N = datetime(2026, 10, 12, 9, 0)

    def care(st):
        write(os.path.join(sd, "brew.json"), json.dumps(st))
        return brewcare.lines(sd, N), brewcare.summary(sd)

    check("no brew.json: no lines, no summary",
          brewcare.lines(sd, N) == [] and brewcare.summary(sd) is None)
    write(os.path.join(sd, "brew.json"), "{broken")
    check("a broken one: the same", brewcare.lines(sd, N) == []
          and brewcare.summary(sd) is None)
    l, s = care({"mode": "own", "last_attempt": "2026-10-12T03:31:00",
                 "last_success": "2026-10-12T03:31:00", "last_result": "ok",
                 "held": {}, "failed": {}, "problems": []})
    check("own and ok: no lines, the summary",
          l == [] and s == "own, ok Oct 12 03:31; 0 held, 0 failed, 0 problems", (l, s))
    l, s = care({"mode": "own", "last_attempt": "2026-10-12T03:31:00",
                 "last_success": "2026-10-08T03:31:00", "last_result": "partial",
                 "failed": {"bar": "Error: x"},
                 "held": {"node": {"installed": "24.1", "latest": "24.2",
                                   "why": "pinned; brew unpin node to let it move"}},
                 "problems": [{"what": "TeX is missing preview.sty",
                               "fix": "tlmgr install preview"}]})
    check("own with trouble: failed, held, problem, stale, in that order",
          l == ["brew: bar did not upgrade: Error: x",
                "brew: node 24.1 -> 24.2 is held: pinned; brew unpin node to let it move",
                "brew: TeX is missing preview.sty; tlmgr install preview",
                "brew: no successful upgrade since Oct 8 03:31"]
          and s == "own, partial Oct 12 03:31; 1 held, 1 failed, 1 problems", (l, s))
    l, s = care({"mode": "own", "first_seen": "2026-10-01T10:00:00"})
    check("own with no success counts from first_seen",
          l == ["brew: no successful upgrade since Oct 1 10:00"]
          and s == "own, no run yet; 0 held, 0 failed, 0 problems", (l, s))
    l, s = care({"mode": "defer", "first_seen": "2026-01-01T00:00:00",
                 "deferred_to": {"label": "com.example.brewupgrade", "path": "/x"},
                 "problems": [{"what": "a", "fix": "b"}]})
    check("defer never yields a stale line",
          l == ["brew: a; b"] and s == "defers to com.example.brewupgrade; 1 problems",
          (l, s))
finally:
    httpd.shutdown()
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("brew upkeep upgrades in its window, defers to another upgrader, and repairs "
      "only what broke")
