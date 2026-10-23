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
  - DEFER: a plist whose job is not loaded is no upgrader; a recorded problem
    is re-probed, report only, an hour on.
  - BUSY and THE LOCK skip a tick with no call; a busy tick logs why, and an
    editor, a pager or a `tail` of the log is not busy.
  - OUTDATED, HOLDS, A CASK FAILURE, THE ORDER, update-tools, OFF MID-RUN,
    R3 (only a CLI the run removed is put back), DRY-RUN, R1.
  - COVER: the other job's last success (a partial run is none) over 26
    hours old; its record as this Mac's job writes it, today partial; a full
    upgrade that excludes nothing of the other job's (a cask it protects, a
    formula and a cask it holds all upgrade; a pinned formula stays held); a
    cask whose installer wants a password is recorded as failed, and no call
    has a stdin or a terminal;
    overdue counted from the newer of the two jobs' runs; a brew or the other
    job starting mid-cover stops it before its next brew step, unstamped and
    keeping its tool failures. AFTER ITS TURN: the cover and the toolchain
    phase wait while the other job is due, go once it has run or after
    WAIT_H, and the toolchain phase yields to it, to be run later that day.
  - THE TOOLCHAIN PHASE: mise with MISE_YES and the Atlas tree trusted, an
    install named by the subject's own tools, a prune of only the pinned
    tools, `mise outdated` in mise 2026.10's own JSON shape, a CLI failure read from update-tools'
    log, a planted failing descriptor, the pins behind; and THE UNION the
    Brewfile probe checks, from a temp file under --dry-run.
  - THE PLIST, install, off, on, status, and brewcare's lines and summary.
    `off` and `install` during a run boot nothing out; the detached `settle`
    does it once the lock is free, and no process is killed by name.
"""

import contextlib
import importlib.util
import io
import json
import os
import plistlib
import shutil
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

sys.path.insert(0, BOARD)
from tutorboard import brewcare                              # noqa: E402

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
        self.not_loaded = set()
        self.clis = []
        self.on_call = None
        self.mise_outdated = (0, "{}", "")
        self.real_tools = False

    def __call__(self, argv, timeout, mutating=False, env=None, cwd=None):
        argv = [str(a) for a in argv]
        self.calls.append({"argv": argv, "s": nice(argv), "mutating": mutating,
                           "env": dict(env or {}), "cwd": cwd, "dry": mod.DRY})
        if mutating and mod.DRY:
            mod.log("[dry-run] would run %s" % " ".join(argv))
            return 0, "", ""
        s = nice(argv)
        prog = os.path.basename(argv[0])
        if self.on_call:
            self.on_call(s)
        if s == "bash ai-config/scripts/install-clis.sh --list":
            missing = self.clis.pop(0) if self.clis else []
            return 0, "".join("  --    %s is missing; would run: curl x | bash\n" % m
                              for m in missing) + "  ok    Claude Code is installed\n", ""
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
            for app in self.apps_running:
                if app in pat.replace("\\", ""):
                    return 0, "777\n", ""
            return 1, "", ""
        if prog == "mise":
            if argv[1:2] == ["outdated"]:
                return self.mise_outdated
            for key in self.fail:
                if s.startswith(key):
                    return 1, "", "mise: %s failed\n" % key
            return 0, "", ""
        if self.real_tools and s.startswith("bash scripts/tools.sh"):
            return real_run(argv, timeout, cwd=cwd, env=env)
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
            if argv[1] == "print" and argv[2].split("/")[-1] in self.not_loaded:
                return 113, "", "Could not find service"
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


def plist(dirpath, name, label, args, **extra):
    with open(os.path.join(dirpath, name), "wb") as fh:
        plistlib.dump(dict({"Label": label, "ProgramArguments": args}, **extra), fh)


OTHER_DIR = os.path.join(work, "other")


def upgrader(ok_at=None, held=None, log_ok=None, log_partial=None,
             attempt=None, log_start=None):
    """Another upgrader, loaded, with its own record: a state JSON whose
    last_success is `ok_at` (two hours before 04:10 by default; False: none),
    whose last_attempt is `attempt` (none by default) and which holds `held`,
    and a log whose last `done (ok)` line is `log_ok`, last `done (partial)`
    line `log_partial` and last `run (...)` line `log_start`. Its plist runs
    a launcher that execs brew_upgrade.py beside it, which protects the
    casks jelly and fusey as the real one does."""
    shutil.rmtree(OTHER_DIR, ignore_errors=True)
    os.makedirs(os.path.join(OTHER_DIR, "state"))
    write(os.path.join(OTHER_DIR, "run_brew_upgrade.sh"),
          '#!/bin/bash\nexec /usr/bin/python3 "$(dirname "$0")/brew_upgrade.py"\n')
    write(os.path.join(OTHER_DIR, "brew_upgrade.py"),
          'raise SystemExit("never run")\n\nPROTECTED_CASKS = {\n'
          '    "jelly": "a server it restarts",\n'
          '    "fusey": "its installer needs the admin password",\n}\n')
    if ok_at is not False:
        doc = {"last_success": (ok_at or at(2)).isoformat(), "held": held or {}}
        if attempt:
            doc["last_attempt"] = attempt.isoformat()
        write(os.path.join(OTHER_DIR, "state", "brew_upgrade.json"), json.dumps(doc))
    lines = ["[2026-10-01 03:00:00] === done in 5s (ok) ===",
             "[2026-10-10 03:00:00] === done in 7s (partial) ===",
             "[2026-10-10 05:00:00] === done in 9s (stopped) ==="]
    for when, how in ((log_ok, "done in 9s (ok)"), (log_partial, "done in 9s (partial)"),
                      (log_start, "brew upgrade run (due, on AC power)")):
        if when:
            lines.append("[%s] === %s ===" % (when.strftime("%Y-%m-%d %H:%M:%S"), how))
    write(os.path.join(OTHER_DIR, "BrewUpgrade.log"), "\n".join(sorted(lines)) + "\n")
    plist(agents, "com.example.brewupgrade.plist", "com.example.brewupgrade",
          [os.path.join(OTHER_DIR, "run_brew_upgrade.sh")],
          WorkingDirectory=OTHER_DIR,
          StandardOutPath=os.path.join(OTHER_DIR, "BrewUpgrade.log"))
    return ("com.example.brewupgrade",
            os.path.join(agents, "com.example.brewupgrade.plist"))


TOOLCHAIN = ("bash ai-config/scripts/update-tools", "uv python upgrade", "mise",
             "bash scripts/tools.sh")


def brew_calls(f):
    """upgrade_calls without the toolchain phase's."""
    return [s for s in upgrade_calls(f) if not s.startswith(TOOLCHAIN)]


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
    return [c["s"] for c in f.calls if c["s"].startswith(UPGRADES)
            and not c["s"].endswith("--list")]


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
    f = reset(14, state={"first_seen": (at(14) - timedelta(hours=1)).isoformat(),
                         "probed_at": (at(14) - timedelta(hours=10)).isoformat(),
                         "problems": [{"what": "projects/B has no .venv",
                                       "fix": "bash scripts/setup.sh"}]})
    mod.main(["run"])
    st = state()
    check("own mode outside the window re-probes a recorded problem, report only",
          st["problems"] == [] and st["probed_at"] == at(14).isoformat()
          and not upgrade_calls(f) and not f.said("uv sync"), (st, f.said()))

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
    want = upgrader()
    check("another upgrader's plist is found", mod.other_upgrader() == want)
    f.broken = {VENV_A}
    f.bundle_ok = False
    mod.main(["run"])
    st = state()
    check("defer: no brew update, upgrade, bundle install, cleanup, npm or install-clis",
          not brew_calls(f), upgrade_calls(f))
    check("but the toolchain phase runs: update-tools, then uv python upgrade",
          upgrade_calls(f) == ["bash ai-config/scripts/update-tools", "uv python upgrade"]
          and st.get("toolchain_attempt") == at(4).isoformat()
          and st.get("toolchain_success") == at(4).isoformat(), upgrade_calls(f))
    check("the baseline tick acts on nothing and records the fingerprint",
          not f.said("uv sync") and not [s for s in f.said("bash")
                                         if not s.startswith(TOOLCHAIN)]
          and st.get("mode") == "defer"
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
          and not [c for c in f.calls if not c["s"].startswith(("pgrep", "launchctl print"))],
          f.said())
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
    f.broken = set()
    f.bundle_ok = True
    f.calls = []
    mod.main(["run"])
    check("a problem fixed by hand stays up while the hour has not passed",
          [p["what"] for p in state()["problems"]] == ["the Brewfile is not satisfied"]
          and not f.said("python") and not f.said("brew bundle"), state()["problems"])
    mod.now = lambda: at(5)
    f.calls = []
    mod.main(["run"])
    st = state()
    check("an hour later it is re-probed, report only, and clears",
          st["problems"] == [] and st["probed_at"] == at(5).isoformat()
          and f.said("python -c pass") and not f.said("uv sync")
          and not upgrade_calls(f), (st, f.said()))
    f.calls = []
    mod.now = lambda: at(7)
    mod.main(["run"])
    check("and with none left nothing is re-probed",
          not [c for c in f.calls if not c["s"].startswith(("pgrep", "launchctl"))],
          f.said())

    shutil.rmtree(os.path.join(prefix, "Cellar", "node", "24.2"))

    f = reset(4)
    plist(agents, "com.example.brewupgrade.plist", "com.example.brewupgrade",
          ["/Users/x/Media/run_brew_upgrade.sh"])
    f.not_loaded = {"com.example.brewupgrade"}
    check("another upgrader's plist whose job is not loaded is no upgrader",
          mod.other_upgrader() is None)
    mod.main(["run"])
    check("and the tick upgrades here", state().get("mode") == "own"
          and "brew update" in f.said(), f.said())
    f = reset(4)
    plist(sys_daemons, "com.example.brew-autoupdate.plist", "com.example.brew-autoupdate",
          ["/x/brew_autoupdate"])
    found = mod.other_upgrader()
    check("a LaunchDaemon's job is asked of the system domain",
          found and found[0] == "com.example.brew-autoupdate"
          and "launchctl print system/com.example.brew-autoupdate" in f.said(), f.said())

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
        check("busy (%s): the tick does nothing, stamps nothing, and logs why" % what,
              not upgrade_calls(f) and not os.path.exists(STATE)
              and "skipped: " + what.replace("Media's brew_upgrade.py",
                                             "another brew upgrader") in read(LOG),
              (f.said(), read(LOG)))
    for line in ("501 tail -f /Users/x/.local/state/atlas-setup/brew-upgrade.log",
                 "502 less brew-upgrade.log",
                 "503 vim board/test/brew_upgrade.py",
                 "504 /bin/zsh -c tail -n 20 ~/.local/state/atlas-setup/brew-upgrade.log",
                 "505 /usr/bin/python3 -c import x # brew_upgrade"):
        f = reset(4)
        f.other_running = line + "\n"
        mod.main(["run", "--force"])
        check("not busy: %s" % line.split(None, 1)[1][:40],
              "brew update" in f.said(), (f.said(), read(LOG)))
    for line in ("601 /Library/Developer/CommandLineTools/Library/Frameworks/Python3."
                 "framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python "
                 "/Users/x/Media/brew_upgrade.py",
                 "602 /bin/bash /Users/x/Media/run_brew_upgrade.sh",
                 "603 /opt/homebrew/bin/brew-autoupdate start"):
        check("busy: %s" % line.split()[1][-30:],
              mod.upgrader_line(line), line)
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
    # off mid-run
    # =======================================================================
    f = reset(4)
    f.outdated = outdated([("wget", {})], ["bar"])

    def owner_runs_off(s):
        if s.startswith("brew upgrade --formula"):
            write(mod.OFF_FILE, "off\n")
    f.on_call = owner_runs_off
    code = mod.main(["run"])
    st = state()
    check("off during a step: that step finishes, nothing after it runs",
          code == 0 and "brew upgrade --formula wget" in f.said()
          and not [s for s in upgrade_calls(f) + f.said("uv")
                   if not s.startswith("brew update")
                   and s != "brew upgrade --formula wget"]
          and st["last_result"] == "stopped" and "last_success" not in st
          and mod.lock_holder() is None and "off by owner" in read(LOG), (f.said(), st))
    f = reset(4)
    upgrader()
    f.broken = {VENV_A}
    write(STATE, json.dumps({"mode": "defer", "fingerprint": "old",
                             "deferred_to": {"label": "com.example.brewupgrade"}}))

    def off_in_defer(s):
        if s.startswith("python -c pass"):
            write(mod.OFF_FILE, "off\n")
    f.on_call = off_in_defer
    code = mod.main(["run"])
    check("and in defer mode the repair after it does not run",
          code == 0 and not f.said("uv sync") and mod.lock_holder() is None,
          (f.said(), read(LOG)))

    # =======================================================================
    # R3: a CLI the run removed, and only that
    # =======================================================================
    for label, lists, want_install, want_problem in (
            ("nothing missing before or after", [[], []], False, None),
            ("one removed by the run is put back", [[], ["Codex"]], True, None),
            ("one missing before stays missing", [["Gemini"], ["Gemini"]], False, None),
            ("one removed beside one kept off is reported, not installed",
             [["Gemini"], ["Codex", "Gemini"]], False,
             "Codex went missing in the upgrade")):
        f = reset(4)
        f.clis = [list(x) for x in lists]
        mod.main(["run"])
        probs = [p["what"] for p in state()["problems"]]
        check("CLIs: %s" % label,
              ("bash ai-config/scripts/install-clis.sh" in f.said()) is want_install
              and (want_problem in probs if want_problem else not probs),
              (f.said("bash"), state()["problems"]))
    check("and the reported one names what install-clis.sh would also install",
          "also installs Gemini" in state()["problems"][0]["fix"], state()["problems"])
    st = state()
    st["probed_at"] = at(2).isoformat()
    write(STATE, json.dumps(st))
    f = reset(5, state=st)
    f.clis = [["Codex", "Gemini"]]
    mod.main(["run"])
    check("an hour on, the re-probe keeps it while it is still gone",
          [p["what"] for p in state()["problems"]] == ["Codex went missing in the upgrade"]
          and not upgrade_calls(f), (state()["problems"], f.said()))
    st = state()
    st["probed_at"] = at(2).isoformat()
    f = reset(5, state=st)
    f.clis = [["Gemini"]]
    mod.main(["run"])
    check("and drops it once it is back", state()["problems"] == [], state()["problems"])

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
              and c["s"].startswith(UPGRADES + ("uv sync",))
              and not c["s"].endswith("--list")]
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
    # cover: the other upgrader's last finished run, over 26 hours old
    # =======================================================================
    f = reset(4)
    upgrader(ok_at=datetime(2026, 10, 11, 3, 0))
    mod.main(["run"])
    st = state()
    check("the other job succeeded 25 hours ago: no brew upgrade here, the toolchain "
          "phase runs", not brew_calls(f) and "uv python upgrade" in f.said()
          and "covered" not in st and st["mode"] == "defer", (f.said(), st))
    f = reset(4)
    upgrader(ok_at=datetime(2026, 10, 11, 1, 0),
             held={"jelly": {"installed": "1", "latest": "2", "why": "supervised"},
                   "wget": {"installed": "1", "latest": "2", "why": "it broke"}})
    f.outdated = outdated([("wget", {}), ("pinny", {"pinned": True})],
                          ["jelly", "bar", "fusey"])
    f.fail = {"brew upgrade --cask fusey"}
    mod.main(["run"])
    st = state()
    check("27 hours ago: it covers with its own brew upgrade",
          "brew update" in f.said() and "brew upgrade --formula wget" in f.said()
          and "brew bundle check --no-upgrade --file=%s" % os.path.join(
              mod.SETUP_DIR, "Brewfile.all") in f.said()
          and "brew cleanup --prune=7" in f.said(), f.said())
    check("excluding nothing of the other job's: the casks it protects and the "
          "formula and cask it holds upgrade too",
          f.said("brew upgrade --cask") == ["brew upgrade --cask bar",
                                            "brew upgrade --cask fusey",
                                            "brew upgrade --cask jelly"]
          and "wget" not in st["held"] and "jelly" not in st["held"]
          and "PROTECTED_CASKS" not in read(LOG) and "holds it" not in read(LOG),
          (f.said(), st.get("held"), read(LOG)[-800:]))
    check("only this job's own holds apply: a pinned formula stays",
          "pinny" in st["held"] and "pinny" not in " ".join(f.said("brew upgrade")),
          (f.said(), st.get("held")))
    check("a protected cask whose installer wants a password fails, recorded as "
          "failed, and the run goes on",
          "fusey" in st["failed"] and st["last_result"] == "partial"
          and "brew upgrade --cask jelly" in f.said(), (st, f.said()))
    check("and records that it covered, staying in defer mode",
          st["mode"] == "defer" and st["deferred_to"]["label"] == "com.example.brewupgrade"
          and st["covered"] == {"for": "com.example.brewupgrade", "at": at(4).isoformat(),
                                "other_success": "2026-10-11T01:00:00"}
          and "covered for com.example.brewupgrade, whose last success was "
              "2026-10-11T01:00:00" in read(LOG), (st, read(LOG)[-600:]))
    said = brewcare.lines(os.path.dirname(STATE), at(4))
    check("brewcare says so, on home and in doctor",
          "brew: com.example.brewupgrade last succeeded Oct 11 01:00, so "
          "atlas.brew-upgrade ran the brew upgrade itself Oct 12 04:10" in said
          and brewcare.summary(os.path.dirname(STATE)).startswith(
              "defers to com.example.brewupgrade, covered for it Oct 12 04:10 "
              "(partial); 1 failed"),
          (said, brewcare.summary(os.path.dirname(STATE))))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main(["status"])
    check("and atlas-brew status names the cover and the other's last run",
          "covered:   2026-10-12T04:10:00, for com.example.brewupgrade" in buf.getvalue()
          and "its last:  2026-10-11T01:00:00; this job covers" in buf.getvalue(),
          buf.getvalue())
    f.calls = []
    mod.now = lambda: at(6)
    mod.main(["run"])
    check("once that day: two hours on it upgrades nothing", not upgrade_calls(f),
          f.said())
    code, out, err = real_run([sys.executable, "-c",
                               "import sys\nprint(repr(sys.stdin.read()))\n"
                               "try:\n    open('/dev/tty')\n"
                               "except OSError:\n    print('no terminal')\n"], 10)
    check("no call has a stdin or a terminal, so a sudo inside brew cannot wait on "
          "a password", code == 0 and out.split() == ["''", "no", "terminal"],
          (code, out, err))
    upgrader(ok_at=at(5))
    mod.now = lambda: at(7)
    mod.main(["run"])
    check("and once the other job succeeds again, the cover line goes",
          "covered" not in state()
          and not [l for l in brewcare.lines(os.path.dirname(STATE), at(7))
                   if "ran the brew upgrade itself" in l], state())
    for label, kw, covers in (
            ("only its log, 3 hours ago: no cover",
             {"ok_at": False, "log_ok": datetime(2026, 10, 12, 1, 0)}, False),
            ("only its log, whose last ok is Oct 1: it covers",
             {"ok_at": False}, True),
            ("a partial run 3 hours ago is no success: it covers",
             {"ok_at": datetime(2026, 10, 1, 3, 0),
              "log_partial": datetime(2026, 10, 12, 1, 0)}, True)):
        f = reset(4)
        upgrader(**kw)
        mod.main(["run"])
        check(label, ("brew update" in f.said()) is covers, f.said())
    f = reset(14)
    upgrader(ok_at=datetime(2026, 10, 1, 3, 0))
    mod.main(["run"])
    check("the host never covers outside the window", not upgrade_calls(f), f.said())

    # A coding laptop at 14:00, on AC and idle: overdue counts from the newer
    # of the two jobs' last runs, not from this job's first_seen.
    for hours, covers in ((30, False), (50, True)):
        f = reset(14, role="coding", state={
            "first_seen": (at(14) - timedelta(days=7)).isoformat()})
        upgrader(ok_at=at(14) - timedelta(hours=hours))
        mod.main(["run"])
        check("a coding laptop at 14:00, the other job's last run %dh ago: %s"
              % (hours, "it covers" if covers else "no cover"),
              ("brew update" in f.said()) is covers, f.said())

    # The other job, or a brew, starting while the cover runs: it stops before
    # its next brew step, since brew does not wait on its lock.
    f = reset(4, state={"failed": {"tool:old": "it broke"},
                        "last_attempt": "2026-10-11T04:10:00",
                        "toolchain_attempt": "2026-10-11T04:10:00"})
    upgrader(ok_at=datetime(2026, 10, 11, 1, 0))
    f.outdated = outdated([("wget", {})])

    def other_starts(s):
        if s == "brew update":
            f.other_running = "991 /usr/bin/python3 /x/brew_upgrade.py\n"
    f.on_call = other_starts
    mod.main(["run"])
    st = state()
    check("the other job starting mid-cover: no brew step after it, yielded, not covered",
          "brew update" in f.said() and not f.said("brew upgrade")
          and not f.said("brew bundle install") and not f.said("brew cleanup")
          and st["last_result"] == "yielded" and "covered" not in st
          and st["mode"] == "defer" and "yielded: another brew upgrader is running"
          in read(LOG), (f.said(), st))
    check("and the next own-mode check is not a cover any more",
          mod.COVERING is False and mod.DEFERRING is False)
    check("a cover that yielded unstamps its attempts and keeps the tool failures "
          "it did not re-check",
          st["last_attempt"] == "2026-10-11T04:10:00"
          and st["toolchain_attempt"] == "2026-10-11T04:10:00"
          and st["failed"].get("tool:old") == "it broke", st)
    f.calls, f.on_call, f.other_running = [], None, ""
    upgrader(ok_at=datetime(2026, 10, 11, 1, 0), attempt=at(4, minute=5))
    mod.now = lambda: at(5)
    mod.main(["run"])
    check("so once the other job has run, a later tick that day covers",
          "brew upgrade --formula wget" in f.said() and "covered" in state()
          and "uv python upgrade" in f.said(), (f.said(), state()))

    # =======================================================================
    # after its turn: the day's work waits while the other job is due
    # =======================================================================
    # This Mac's job as it writes its record today: its last success 33 hours
    # back, a partial run since, started 03:37 and done 03:55.
    real = os.path.join(work, "real-other")
    os.makedirs(os.path.join(real, "state"))
    write(os.path.join(real, "state", "brew_upgrade.json"), json.dumps({
        "first_seen": "2026-09-05T20:16:36", "last_attempt": "2026-10-23T03:37:00",
        "last_success": "2026-10-22T03:36:01", "last_result": "partial",
        "last_duration_seconds": 1114, "held": {"jellyfin": {
            "installed": "12.2", "latest": "12.3", "why": "the supervised upgrade "
            "failed"}}}))
    write(os.path.join(real, "BrewUpgrade.log"), "\n".join([
        "[2026-10-22 03:29:28] === brew upgrade run (due, on AC power) ===",
        "[2026-10-22 03:36:01] === done in 392s (ok) ===",
        "[2026-10-23 03:37:00] === brew upgrade run (due, on AC power) ===",
        "[2026-10-23 03:55:35]     [brew cleanup] ==> freed 46.1MB",
        "[2026-10-23 03:55:35] === done in 1114s (partial) ===",
        "[2026-10-23 09:00:00] === dry run; nothing was changed ==="]) + "\n")
    plist(agents, "com.real.brewupgrade.plist", "com.real.brewupgrade",
          [os.path.join(real, "run_brew_upgrade.sh")], WorkingDirectory=real,
          StandardOutPath=os.path.join(real, "BrewUpgrade.log"))
    rec = mod.other_record(("com.real.brewupgrade",
                            os.path.join(agents, "com.real.brewupgrade.plist")))
    check("the record this Mac's job writes: its last success Oct 22 03:36, not the "
          "partial run; its last start 03:37, not a dry run",
          rec == (datetime(2026, 10, 22, 3, 36, 1), datetime(2026, 10, 23, 3, 37)), rec)
    os.remove(os.path.join(agents, "com.real.brewupgrade.plist"))

    # Its last success 33 hours back and its turn taken today: it covers.
    f = reset(4)
    upgrader(ok_at=at(4, day=11) - timedelta(hours=9), attempt=at(3, minute=37),
             log_partial=at(3, minute=55))
    f.outdated = outdated([("wget", {})])
    mod.main(["run"])
    check("its last success 33h old, its partial run done today: it covers",
          "brew upgrade --formula wget" in f.said() and "covered" in state(),
          (f.said(), read(LOG)[-600:]))

    # Due (its last start a day back), and this job's tick comes first.
    def due_tick(hour, minute=10, **kw):
        f.calls = []
        mod.now = lambda: at(hour, minute=minute)
        mod.main(["run"] + kw.get("args", []))
        return state()

    for label, ok_at in (("a cover", at(4, day=10)), ("the toolchain phase",
                                                       at(3, day=11, minute=37))):
        f = reset(3)
        upgrader(ok_at=ok_at, attempt=at(3, day=11, minute=37))
        f.outdated = outdated([("wget", {})])
        st = due_tick(3)
        check("%s waits while the other job is due: nothing runs, nothing stamped"
              % label, not upgrade_calls(f) and not f.said("mise")
              and "last_attempt" not in st and "toolchain_attempt" not in st
              and st.get("other_due_seen") == at(3).isoformat()
              and "waiting: com.example.brewupgrade last started a run "
                  "2026-10-11T03:37:00 and is due; this job goes after it, or by "
                  "04:40 if it does not start" in read(LOG),
              (f.said(), st, read(LOG)[-400:]))
        st = due_tick(4)
        check("%s: an hour on, still due, still waiting" % label,
              not upgrade_calls(f) and "toolchain_attempt" not in st, f.said())
        upgrader(ok_at=ok_at, attempt=at(4, minute=37), log_partial=at(4, minute=50))
        st = due_tick(5)
        check("%s runs once the other job has had its turn" % label,
              "uv python upgrade" in f.said() and "other_due_seen" not in st
              and ("brew upgrade --formula wget" in f.said()) is (label == "a cover"),
              (f.said(), st))
    f = reset(3)
    upgrader(ok_at=at(4, day=10), attempt=at(3, day=11, minute=37))
    f.outdated = outdated([("wget", {})])
    due_tick(3)
    due_tick(4)
    due_tick(4, minute=45)
    check("an upgrader that never starts: waited for 1.5h, then covered for",
          "brew upgrade --formula wget" in f.said(), (f.said(), read(LOG)[-400:]))
    f = reset(3, state={"other_due_seen": at(3, day=11).isoformat()})
    upgrader(ok_at=at(4, day=10), attempt=None, log_start=at(3, day=11, minute=37))
    st = due_tick(3)
    check("a wait from another stretch awake starts over; its log's run line is a start",
          not upgrade_calls(f) and st["other_due_seen"] == at(3).isoformat(),
          (f.said(), st))
    st = due_tick(3, args=["--force"])
    check("and --force does not wait", "brew update" in f.said(), f.said())

    # The toolchain phase alone, the other job starting under it: it yields
    # before its next step, keeps the failures, and runs later that day.
    f = reset(4, state={"failed": {"tool:old": "it broke"},
                        "toolchain_attempt": "2026-10-11T04:10:00"})
    upgrader(ok_at=at(3), attempt=at(3))

    def starts_under_tools(s):
        if s == "bash ai-config/scripts/update-tools":
            f.other_running = "991 /usr/bin/python3 /x/brew_upgrade.py\n"
    f.on_call = starts_under_tools
    mod.main(["run"])
    st = state()
    check("the toolchain phase yields to the other job starting under it",
          "bash ai-config/scripts/update-tools" in f.said()
          and not f.said("uv python upgrade") and not f.said("bash scripts/tools.sh")
          and st["toolchain_attempt"] == "2026-10-11T04:10:00"
          and st["failed"] == {"tool:old": "it broke"} and "toolchain_success" not in st
          and "yielded: another brew upgrader is running" in read(LOG)
          and mod.DEFERRING is False, (f.said(), st))
    f.calls, f.on_call, f.other_running = [], None, ""
    mod.now = lambda: at(5)
    mod.main(["run"])
    check("and a later tick that day runs it", "uv python upgrade" in f.said()
          and "tool:old" not in (state().get("failed") or {}), (f.said(), state()))

    # =======================================================================
    # the toolchain phase: mise, the descriptors, the pins, the failures
    # =======================================================================
    MISE = os.path.join(atlas, "projects", "M")
    write(os.path.join(MISE, "mise.toml"),
          '[tools]\nnode = "20.0.0"  # the pin\n"npm:prettier" = "3.0.0"\n'
          '[tools.python]\nversion = "3.12"\n[env]\nNOT_A_TOOL = "1"\n')
    write(os.path.join(MISE, "mise.lock"), "lock\n")

    def mise_rec(name, requested, current, bump, latest, src):
        """One record of `mise outdated --json --bump --local`, as mise
        2026.10.17 prints it."""
        return {"name": name, "requested": requested, "current": current, "bump": bump,
                "latest": latest, "release_url": "https://example.invalid/%s" % latest,
                "source": {"type": "mise.toml", "path": src}}
    # node is behind; python's request (a minor) already reaches its newest
    # release, so bump is null; prettier is not installed yet (current null),
    # pinned at its newest; shfmt comes from the parent directory's config.
    MISE_OUTDATED = (0, json.dumps({
        "node": mise_rec("node", "20.0.0", "20.0.0", "22.1.0", "22.1.0",
                         os.path.join(MISE, "mise.toml")),
        "python": mise_rec("python", "3.12", "3.12.9", None, "3.14.0",
                           os.path.join(MISE, "mise.toml")),
        "npm:prettier": mise_rec("npm:prettier", "3.0.0", None, None, "3.0.0",
                                 os.path.join(MISE, "mise.toml")),
        "shfmt": mise_rec("shfmt", "3.8.0", "3.8.0", "3.12.0", "3.12.0",
                          os.path.join(atlas, "projects", "mise.toml"))}, indent=2), "")
    write(os.path.join(atlas, "scripts", "tools.sh"), "exit 0\n")
    f = reset(4)
    upgrader()
    f.mise_outdated = MISE_OUTDATED
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["run", "--dry-run", "--force"])
    out = buf.getvalue()
    check("atlas-brew run --dry-run --force in defer mode lists the toolchain phase",
          code == 0 and "mode: defer -> com.example.brewupgrade" in out
          and "toolchain gate: would run" in out and "toolchain phase" in out
          and "would run bash %s" % TOOLS_SCRIPT in out
          and "uv python upgrade" in out and "would run mise install --locked node npm:prettier python\n" in out
          and "would run mise prune --yes --tools node npm:prettier python\n" in out
          and "would run bash %s update" % os.path.join(atlas, "scripts", "tools.sh") in out
          and "pin behind: projects/M node 20.0.0 -> 22.1.0" in out
          and "brew upgrade" not in out and not os.path.exists(STATE), out)
    f = reset(4)
    upgrader()
    f.mise_outdated = MISE_OUTDATED
    mod.main(["run"])
    tj = json.loads(read(os.path.join(os.path.dirname(STATE), "tools.json")) or "{}")
    check("mise install --locked of the subject's own tools in it, mise prune, "
          "tools.sh update, mise outdated --local, in order",
          [c["cwd"] for c in f.calls
           if c["s"] == "mise install --locked node npm:prettier python"] == [MISE]
          and f.first("mise install") < f.first("mise prune --yes --tools")
          < f.first("bash scripts/tools.sh update")
          < f.first("mise outdated --json --bump --local"), f.said())
    mises = [c for c in f.calls if c["argv"][0] == "mise"]
    check("every mise call answers no prompt and trusts the Atlas tree's configs",
          len(mises) == 3 and all(c["env"].get("MISE_YES") == "1"
                                  and c["env"].get("MISE_TRUSTED_CONFIG_PATHS") == atlas
                                  for c in mises), mises)
    check("mise prune names the tools the subjects pin, never a bare prune",
          f.said("mise prune") == ["mise prune --yes --tools node npm:prettier python"],
          f.said("mise"))
    check("a pin behind goes into tools.json and onto home as a pin behind line; a null "
          "bump and another directory's config are not this one's",
          tj.get("pins") == [{"subject": "projects/M", "tool": "node",
                              "pinned": "20.0.0", "latest": "22.1.0", "dir": MISE}]
          and "tools: pin behind: projects/M node 20.0.0 -> 22.1.0"
          in brewcare.lines(os.path.dirname(STATE), at(4)), tj)
    check("and nothing bumps it", not [s for s in f.said()
                                       if "upgrade" in s and "mise" in s
                                       or "use" in s.split()[:2]], f.said())
    AI_LOG = os.path.join(home, ".local", "state", "ai-tools-update.log")
    write(AI_LOG, "2026-10-11 04:10:00   opencode 1.0: update failed (exit 9); left "
                  "where it was\n")

    def cli_fails(s):
        if s == "bash ai-config/scripts/update-tools":
            with open(AI_LOG, "a") as fh:
                fh.write("2026-10-12 04:10:01   claude 2.1.3: update failed (exit 1); "
                         "left where it was\n2026-10-12 04:10:02   codex 0.1 -> 0.2\n")
    f = reset(4)
    upgrader()
    f.on_call = cli_fails
    mod.main(["run"])
    check("update-tools exits 0 whatever happens: a CLI's failure is read from the "
          "lines it adds to its log",
          (state().get("failed") or {}) == {
              "tool:claude": "update failed (exit 1); see ~/.local/state/"
                             "ai-tools-update.log"}, state())
    os.remove(AI_LOG)
    f = reset(4)
    upgrader()
    f.fail = {"mise install", "bash ai-config/scripts/update-tools"}
    mod.main(["run"])
    st = state()
    check("toolchain failures enter failed as tool:<name>, in defer mode",
          sorted(st.get("failed") or {}) == ["tool:mise:projects/M", "tool:update-tools"]
          and "toolchain_success" not in st, st)
    os.makedirs(os.path.join(prefix, "Cellar", "node", "24.3"))
    f.fail = set()
    mod.now = lambda: at(5)
    mod.main(["run"])
    check("and stay through a defer tick that repairs", "tool:update-tools"
          in (state().get("failed") or {}), state())
    shutil.rmtree(os.path.join(prefix, "Cellar", "node", "24.3"))

    # A planted failing descriptor, through the real tools.sh.
    os.remove(os.path.join(atlas, "scripts", "tools.sh"))
    shutil.copy(os.path.join(ATLAS_REAL, "scripts", "tools.sh"),
                os.path.join(atlas, "scripts", "tools.sh"))
    os.symlink(BOARD, os.path.join(atlas, "board"))
    write(os.path.join(atlas, "projects", "T", "tools", "planted.sh"),
          'T_NAME="planted"\nT_BIN="planted"\nT_BIN_DIR="$HOME/.planted/bin"\n'
          'T_ROLES="host coding"\nT_INSTALL=""\nT_MANUAL="fetch it by hand"\n'
          'T_UPDATE="exit 3"\nT_VERSION="planted --version"\nT_CHECK="planted"\n'
          'T_EVERY_DAYS=1\nT_STALE_DAYS=14\n')
    write(os.path.join(home, ".planted", "bin", "planted"),
          "#!/bin/sh\necho planted 0.1.0\n", EXE)
    f = reset(4)
    f.real_tools = True
    mod.main(["run"])
    st = state()
    check("a planted failing descriptor: brew.json failed names tool:planted",
          st["failed"].get("tool:planted") == "T_UPDATE exited 3"
          and st["mode"] == "own", st.get("failed"))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["status"])
    check("and atlas-brew status shows it, exit 1",
          code == 1 and "FAILED    tool:planted: T_UPDATE exited 3" in buf.getvalue(),
          buf.getvalue())
    said = brewcare.lines(os.path.dirname(STATE), at(4))
    check("brewcare names it once",
          [l for l in said if "planted" in l]
          == ["tools: planted did not update: T_UPDATE exited 3"], said)
    doc = subprocess.run([sys.executable, os.path.join(BOARD, "bin", "board"),
                          "doctor", "--dry"], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True,
                         timeout=180, cwd=work,
                         env=dict(os.environ, BOARD_NO_TAILNET="1"))
    check("and board doctor prints a tools: line naming it",
          "tools:    1 declared, 1 failed" in doc.stdout
          and "tools: planted did not update: T_UPDATE exited 3" in doc.stdout,
          doc.stdout[-1500:])
    shutil.rmtree(MISE)
    shutil.rmtree(os.path.join(atlas, "projects", "T"))
    os.remove(os.path.join(atlas, "board"))
    os.remove(os.path.join(atlas, "scripts", "tools.sh"))
    os.remove(os.path.join(os.path.dirname(STATE), "tools.json"))

    # =======================================================================
    # the Brewfile union: the probe checks what setup.sh bundles
    # =======================================================================
    UNION = os.path.join(mod.SETUP_DIR, "Brewfile.all")
    write(os.path.join(atlas, "projects", "A", "Brewfile"), 'brew "ripgrep"\nbrew "uv"\n')
    f = reset(4)
    f.bundle_ok = False
    mod.main(["repair"])
    check("the probe checks and installs the union, root and subject Brewfiles in one",
          f.said("brew bundle") == [
              "brew bundle check --no-upgrade --file=" + UNION,
              "brew bundle install --no-upgrade --file=" + UNION]
          and [l for l in read(UNION).splitlines() if not l.startswith("#")]
          == ['brew "ripgrep"', 'brew "uv"'], (f.said("brew bundle"), read(UNION)))
    written = os.stat(UNION).st_mtime_ns
    write(os.path.join(atlas, "projects", "B", "Brewfile"), 'brew "jq"\n')
    f = reset(4)
    seen = {}

    def keep_union(s):
        if s.startswith("brew bundle check"):
            path = s.split("--file=", 1)[1]
            seen["path"], seen["text"] = path, read(path)
    f.on_call = keep_union
    with contextlib.redirect_stdout(io.StringIO()):
        mod.main(["repair", "--dry-run"])
    check("a dry run checks the changed union from a temp file, removed after, and "
          "leaves Brewfile.all alone",
          seen.get("path") not in (None, UNION) and 'brew "jq"' in seen.get("text", "")
          and not os.path.exists(seen.get("path") or UNION + ".none")
          and os.stat(UNION).st_mtime_ns == written and 'brew "jq"' not in read(UNION),
          seen)
    os.remove(os.path.join(atlas, "projects", "A", "Brewfile"))
    os.remove(os.path.join(atlas, "projects", "B", "Brewfile"))

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
    check("the plist: absolute paths, its label, no RunAtLoad, hourly, system python, "
          "its children abandoned to finish",
          pl["Label"] == "atlas.brew-upgrade" and pl["RunAtLoad"] is False
          and pl["StartInterval"] == 3600 and pl["AbandonProcessGroup"] is True
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
    upgrader()
    with open(LOADED, "a") as fh:
        fh.write("com.example.brewupgrade\n")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main(["install"])
    check("with another upgrader it says it defers",
          "defers to com.example.brewupgrade (repairs and the toolchain phase" in buf.getvalue(),
          buf.getvalue())

    def hold_lock():
        """A run under way: a process holding the lock with its pid in it."""
        p = subprocess.Popen([sys.executable, "-c",
                              "import fcntl,os,sys,time\n"
                              "fd=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT)\n"
                              "fcntl.flock(fd,fcntl.LOCK_EX)\n"
                              "os.write(fd,b'%d\\n'%os.getpid())\n"
                              "print('held',flush=True)\n"
                              "time.sleep(60)\n", mod.LOCK],
                             stdout=subprocess.PIPE, universal_newlines=True)
        p.stdout.readline()
        return p

    def until(cond, secs=15):
        end = time.time() + secs
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.1)
        return cond()

    os.makedirs(os.path.dirname(mod.LOCK), exist_ok=True)
    holder = hold_lock()
    check("lock_holder names the run's pid while it holds the lock",
          mod.lock_holder() == holder.pid, mod.lock_holder())
    open(CALLS, "w").close()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["off"])
    off_said = buf.getvalue()
    check("off during a run: the switch written and the plist gone, but no bootout "
          "while it runs", code == 0 and os.path.exists(mod.OFF_FILE)
          and not os.path.exists(mod.AGENT)
          and "atlas.brew-upgrade" in read(LOADED).split()
          and "launchctl bootout" not in read(CALLS)
          and "pid %d" % holder.pid in off_said and "unloads once it ends" in off_said,
          (off_said, read(CALLS)))
    holder.kill()
    holder.wait()
    check("and once the run ends, settle unloads it",
          until(lambda: "atlas.brew-upgrade" not in read(LOADED).split())
          and until(lambda: "settle: the run ended; unloaded" in read(LOG)),
          (read(LOADED), read(LOG)))
    check("lock_holder is None once no run holds it", mod.lock_holder() is None)

    mod.run = real_run
    os.remove(mod.OFF_FILE)
    mod.main(["install"])
    bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)",
                                  "scripts/brew-upgrade.py"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["off"])
    time.sleep(0.3)
    alive = bystander.poll() is None
    bystander.kill()
    bystander.wait()
    check("off with no run: booted out, the plist gone, the off switch written, and a "
          "process that only names the script left alone",
          code == 0 and "atlas.brew-upgrade" not in read(LOADED).split()
          and not os.path.exists(mod.AGENT) and os.path.exists(mod.OFF_FILE) and alive,
          (buf.getvalue(), read(CALLS)))
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

    write(mod.AGENT, "an older template\n")
    holder = hold_lock()
    open(CALLS, "w").close()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["install"])
    check("install with a changed plist during a run: written, not booted out",
          code == 0 and read(mod.AGENT) != "an older template\n"
          and "launchctl bootout" not in read(CALLS)
          and "reloads once it ends" in buf.getvalue(), (buf.getvalue(), read(CALLS)))
    holder.kill()
    holder.wait()
    check("and once the run ends, settle reloads it",
          until(lambda: "settle: the run ended; reloaded" in read(LOG))
          and "launchctl bootout" in read(CALLS)
          and "atlas.brew-upgrade" in read(LOADED).split(), (read(CALLS), read(LOG)))

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
          l == ["brew: a; b"]
          and s == "defers to com.example.brewupgrade; 0 failed, 1 problems",
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
