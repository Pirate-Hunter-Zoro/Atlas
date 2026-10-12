#!/usr/bin/python3
"""brew-upgrade.py -- keep this Mac's Homebrew current, and repair what a move breaks.

    atlas-brew run [--dry-run] [--force]   the hourly launchd tick
    atlas-brew repair [--dry-run]          the probes and repairs, now
    atlas-brew status                      what the last run did; exit 1 on a problem
    atlas-brew install | off | on | plist  the LaunchAgent, atlas.brew-upgrade
    atlas-brew settle                      internal: reload or unload once a run ends

`atlas-brew` is ~/.local/bin/atlas-brew, a link to this file. setup-mac.sh's
step 8 runs `install` on both roles. State is $BOARD_STATE_DIR/brew.json (else
~/.local/state/tutor-board/brew.json); board/tutorboard/brewcare.py reads it for
/relay.json and `board doctor`. The log is ~/.local/state/atlas-setup/brew-upgrade.log.

The rules, each with its reason:

  * DEFER TO ANOTHER UPGRADER. When a LaunchAgent or LaunchDaemon whose label or
    program matches `brew.?(upgrade|autoupdate)|homebrew-autoupdate` is
    installed and loaded, this job upgrades nothing and only probes and repairs,
    on the tick after brew's tree moves, because two upgraders fight over brew's
    lock. A plist left installed but not loaded is no upgrader: it upgrades
    nothing, so this job does.
  * HOURLY, GATED TO ONCE A DAY IN 03:00-07:59. A sleeping machine misses a
    calendar job; an hourly tick catches up. The host never upgrades outside the
    window, because the owner may be in a lesson. A coding laptop upgrades
    outside it only when 48 hours overdue, on AC and idle 20 minutes, because a
    laptop is shut at night.
  * BUSY MEANS NEXT HOUR. A running brew, another upgrader running (an
    interpreter whose script's name matches, never an editor or a `tail` of the
    log), or a board turn running or queued skips the tick, logs why, and
    stamps nothing.
  * NEVER GREEDY. Casks that update themselves are left to do so, and a stale
    record of one is never "upgraded" over the app.
  * HOLDS. A pinned formula, a tailscale run as a brew service on the host (it
    carries the board's tailnet), and a cask whose app is running at three ticks
    in a row are held and reported, never forced.
  * CLEANUP LAST, NO AUTOREMOVE. HOMEBREW_NO_INSTALL_CLEANUP keeps the old kegs
    until every step and repair has run, so nothing still running loses its
    files mid-run. `brew autoremove` is never run: it deletes formulae installed
    only as dependencies, such as a python@3.x Atlas calls directly, and makes
    nothing more current.
  * REPAIRS ACT ONLY ON BREAKAGE. A subject's .venv that cannot start is
    re-synced with `uv sync --locked`; the board's LaunchAgent whose interpreter
    is gone is reinstalled; a Brewfile miss is installed in own mode; an
    assistant CLI the run itself removed is put back, and one already missing
    before the run is left missing, because that is how the owner keeps one off
    a machine. TeX and the board's reachability are reported, never touched.
    A recorded problem is re-probed, report only, each hour until it clears.
  * OFF STOPS BETWEEN STEPS. `off` writes the off switch; a run sees it before
    its next step and stops. A job mid-run is never booted out: a detached
    `settle` waits on the run's lock and unloads (or, for `install`, reloads)
    the job once the run ends, and AbandonProcessGroup keeps launchd from
    killing a brew it started, because a brew killed mid-link leaves a keg
    unlinked.
  * SYSTEM PYTHON. The LaunchAgent runs /usr/bin/python3, because this job
    upgrades brew's python; this file is stdlib-only and 3.7-clean.
"""

import fcntl
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta

# board/'s modules are imported for the probes; nothing is written beside them.
sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.realpath(__file__))
ATLAS = os.path.dirname(HERE)
BOARD_DIR = os.path.join(ATLAS, "board")
SCRIPT = os.path.realpath(__file__)

STATE = os.path.join(os.environ.get("BOARD_STATE_DIR")
                     or os.path.join(HOME, ".local", "state", "tutor-board"),
                     "brew.json")
SETUP_DIR = os.path.join(os.environ.get("XDG_STATE_HOME")
                         or os.path.join(HOME, ".local", "state"), "atlas-setup")
LOG = os.path.join(SETUP_DIR, "brew-upgrade.log")
LOCK = os.path.join(SETUP_DIR, "brew-upgrade.lock")
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                          or os.path.join(HOME, ".config"), "tutor-board")
ROLE_FILE = os.path.join(CONFIG_DIR, "role")
OFF_FILE = os.path.join(CONFIG_DIR, "brew-upgrade.off")
BOARD_CONFIG = os.path.join(CONFIG_DIR, "config.json")

LABEL = "atlas.brew-upgrade"
LINK = os.path.join(HOME, ".local", "bin", "atlas-brew")
TEMPLATE = os.path.join(HERE, "launchd", LABEL + ".plist")
AGENT_DIRS = [os.path.join(HOME, "Library", "LaunchAgents"),
              "/Library/LaunchAgents", "/Library/LaunchDaemons"]
AGENT = os.path.join(AGENT_DIRS[0], LABEL + ".plist")
BOARD_AGENT = os.path.join(AGENT_DIRS[0], "tutor-board.plist")
UV_PYTHONS = os.path.join(HOME, ".local", "share", "uv", "python")
CAFFEINATE = "/usr/bin/caffeinate"

OTHER = re.compile(r"brew.?(upgrade|autoupdate)|homebrew-autoupdate", re.I)


def find_prefix():
    for p in ("/opt/homebrew", "/usr/local"):
        if os.path.isfile(os.path.join(p, "bin", "brew")):
            return p
    return None


PREFIX = find_prefix()

MIN_INTERVAL_H = 20
RECHECK_MIN = 50                     # a recorded problem is re-probed hourly
WINDOW = range(3, 8)                 # 03:00-07:59 local
OVERDUE_H = 48
STALE_H = 72
MIN_BATTERY_PCT = 40
IDLE_MIN_S = 1200
CASK_DEFER_HOLD = 3
LOG_MAX = 2000000
PRUNE_DAYS = 7
BOARD_PORT = 8778

T_UPDATE = 1800
T_OUTDATED = 600
T_FORMULAE = 10800
T_CASK = 5400
T_NPM = 1800
T_TOOLS = 1800
T_UVPY = 1800
T_UVSYNC = 1800
T_CLEANUP = 1800
T_BCHECK = 300
T_BINSTALL = 3600
T_PROBE = 60

DRY = False
_lock_fd = None


def brew_env():
    """Set on every brew and npm call: this job decides when brew updates and
    cleans, and nothing prints colour or hints into the log."""
    return {"HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_INSTALL_CLEANUP": "1",
            "HOMEBREW_NO_ENV_HINTS": "1", "HOMEBREW_NO_ANALYTICS": "1",
            "HOMEBREW_NO_COLOR": "1",
            "PATH": "%s/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                    % (PREFIX or "/opt/homebrew")}


def now():
    return datetime.now()


def stamp(when=None):
    return (when or now()).replace(microsecond=0).isoformat()


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def hours_since(when):
    return float("inf") if when is None else (now() - when).total_seconds() / 3600.0


# --------------------------------------------------------------------- running

def run(argv, timeout, mutating=False, env=None, cwd=None):
    """(code, stdout, stderr). Never raises: a timeout is 124, a missing
    program 127. A mutating call under --dry-run is described, not run. The
    caller's PATH comes first, then brew's and the system's directories."""
    argv = [str(a) for a in argv]
    if mutating and DRY:
        log("[dry-run] would run %s" % " ".join(argv))
        return 0, "", ""
    full = dict(os.environ)
    path = [d for d in full.get("PATH", "").split(os.pathsep) if d]
    for d in ((PREFIX or "/opt/homebrew") + "/bin", "/usr/local/bin", "/usr/bin",
              "/bin", "/usr/sbin", "/sbin"):
        if d not in path:
            path.append(d)
    full["PATH"] = os.pathsep.join(path)
    if env:
        full.update(env)
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, universal_newlines=True,
                           timeout=timeout, env=full, cwd=cwd)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ds" % timeout
    except (OSError, ValueError) as exc:
        return 127, "", str(exc)


def brew(args, timeout, mutating=False):
    return run([os.path.join(PREFIX, "bin", "brew")] + list(args), timeout,
               mutating=mutating, env=brew_env())


def log(msg):
    """One stamped line in the log. Echoed on a terminal; under --dry-run only
    echoed, since a dry run writes nothing."""
    line = "[%s] %s" % (now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    if DRY or sys.stdout.isatty():
        print(line if not DRY else msg, flush=True)
    if DRY:
        return
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def log_tail(out, tag, n=15):
    lines = [l for l in (out or "").splitlines() if l.strip()]
    for l in lines[-n:]:
        log("    [%s] %s" % (tag, l))


def last_line(*outs):
    for out in outs:
        lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
        if lines:
            return lines[-1][:300]
    return ""


def trim_log():
    """Over LOG_MAX, keep the last half of the lines: a job that runs for years
    must not be what fills the disk."""
    if DRY:
        return
    try:
        if os.path.getsize(LOG) <= LOG_MAX:
            return
        with open(LOG, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        tmp = LOG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.writelines(lines[len(lines) // 2:])
        os.replace(tmp, LOG)
    except OSError:
        pass


# ----------------------------------------------------------------------- state

def load_state():
    try:
        with open(STATE, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    if DRY:
        return
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, STATE)
    except OSError as exc:
        log("! could not write %s: %s" % (STATE, exc))


def read_role():
    try:
        with open(ROLE_FILE, encoding="utf-8") as fh:
            return "coding" if fh.read().strip() == "coding" else "host"
    except OSError:
        return "host"


def board_port():
    try:
        with open(BOARD_CONFIG, encoding="utf-8") as fh:
            port = int(json.load(fh).get("port") or BOARD_PORT)
        return port if 0 < port < 65536 else BOARD_PORT
    except (OSError, ValueError, TypeError, AttributeError):
        return BOARD_PORT


# ------------------------------------------------------------------------ mode

def read_plist(path):
    try:
        with open(path, "rb") as fh:
            data = plistlib.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:                                        # noqa: BLE001
        return None


def job_loaded(label, path):
    """Is the job `label`, from the plist at `path`, loaded? A LaunchDaemon is
    asked of the system domain, an agent of this user's."""
    where = "system" if os.path.dirname(path) == AGENT_DIRS[2] else domain()
    return run(["launchctl", "print", "%s/%s" % (where, label)], T_PROBE)[0] == 0


def other_upgrader():
    """(label, path) of another loaded brew upgrader, or None. Found from the
    plists, so no vendor is named and no other job's state is read; one whose
    job is not loaded upgrades nothing, so it is passed over."""
    for d in AGENT_DIRS:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            if not name.endswith(".plist"):
                continue
            path = os.path.join(d, name)
            data = read_plist(path)
            if data is None:
                continue
            label = str(data.get("Label") or "")
            if label == LABEL:
                continue
            prog = data.get("ProgramArguments") or [data.get("Program") or ""]
            if not isinstance(prog, list):
                prog = [str(prog)]
            text = " ".join([label] + [str(p) for p in prog])
            if OTHER.search(text) and job_loaded(label or name[:-6], path):
                return label or name, path
    return None


# ------------------------------------------------------------------------ busy

INTERPRETER = re.compile(r"^(python[\d.]*|ruby|perl|node|bash|sh|zsh|dash|ksh)$", re.I)


def upgrader_line(line):
    """Is this `pgrep -lf` line another brew upgrader at work? Only a program
    named like one, or an interpreter running a script named like one: an
    editor, a pager, a `tail -f` of the log or a shell's `-c` command that
    names the file is not, and neither is this script."""
    parts = line.strip().split()
    if len(parts) < 2 or not parts[0].isdigit() or int(parts[0]) == os.getpid():
        return False
    if "scripts/brew-upgrade.py" in line:
        return False
    prog, args = os.path.basename(parts[1]), parts[2:]
    if OTHER.search(prog):
        return True
    if not INTERPRETER.match(prog) or not args:
        return False
    if args[0].startswith("-") and "c" in args[0]:
        return False
    return bool(OTHER.search(" ".join(args)))


def busy(role):
    """Why this tick must not work now, or None."""
    code, out, _ = run(["pgrep", "-f", r"/Library/Homebrew/brew\.(rb|sh)"], T_PROBE)
    if code == 0 and out.strip():
        return "a brew is running"
    code, out, _ = run(["pgrep", "-lf", "brew[-_]?upgrade"], T_PROBE)
    if code == 0:
        for line in out.splitlines():
            if upgrader_line(line):
                return "another brew upgrader is running (%s)" % line.strip()[:120]
    if role == "host":
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % board_port(),
                                        timeout=5) as r:
                turns = (json.loads(r.read().decode("utf-8")) or {}).get("turns") or {}
            if turns.get("running") or turns.get("queued"):
                return "the board has a turn running or queued"
        except Exception:                                    # noqa: BLE001
            pass
    return None


def take_lock():
    """Held for the whole run, so it needs no staleness clock: the kernel drops
    it when the process ends."""
    global _lock_fd
    if DRY:
        return True
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    os.ftruncate(fd, 0)
    os.write(fd, ("%d\n" % os.getpid()).encode())
    _lock_fd = fd
    return True


def lock_holder():
    """The pid holding the run's lock (0 when it wrote none), or None when no
    run holds it."""
    try:
        fd = os.open(LOCK, os.O_RDONLY)
    except OSError:
        return None
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            said = os.read(fd, 32).decode("ascii", "replace").strip()
            return int(said) if said.isdigit() else 0
        fcntl.flock(fd, fcntl.LOCK_UN)
        return None
    finally:
        os.close(fd)


class Stopped(Exception):
    """The owner turned the job off mid-run."""


def check_off():
    """Between steps: stop when `off` has been run since this run began."""
    if not DRY and os.path.exists(OFF_FILE):
        raise Stopped()


def drop_lock():
    global _lock_fd
    if _lock_fd is not None:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
        except OSError:
            pass
        _lock_fd = None


# ------------------------------------------------------------------------ gate

def battery():
    """(on_ac, percent or None). A failed or batteryless pmset is AC."""
    code, out, _ = run(["pmset", "-g", "batt"], T_PROBE)
    if code != 0 or "Battery Power" not in out:
        return True, None
    m = re.search(r"(\d+)%", out)
    return False, (int(m.group(1)) if m else None)


def idle_seconds():
    code, out, _ = run(["ioreg", "-c", "IOHIDSystem"], T_PROBE)
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out) if code == 0 else None
    return int(m.group(1)) / 1e9 if m else None


def network_ok():
    code, _, _ = run(["curl", "-sfI", "--max-time", "10", "https://formulae.brew.sh/"],
                     30)
    return code == 0


def gate(state, role):
    """(go, why). Every refusal stamps nothing, so the next hour asks again."""
    t = now()
    since = hours_since(parse_ts(state.get("last_attempt")))
    if since < MIN_INTERVAL_H:
        return False, "attempted %.1fh ago (every %dh)" % (since, MIN_INTERVAL_H)
    base = parse_ts(state.get("last_success")) or parse_ts(state.get("first_seen"))
    overdue = hours_since(base) >= OVERDUE_H
    if t.hour not in WINDOW:
        if role == "host":
            return False, "outside 03:00-07:59 (the host upgrades only in the window)"
        if not overdue:
            return False, "outside 03:00-07:59 and not overdue"
        ac, _pct = battery()
        if not ac:
            return False, "overdue, but on battery"
        idle = idle_seconds()
        if idle is None or idle < IDLE_MIN_S:
            return False, "overdue, but in use"
    ac, pct = battery()
    if not ac and pct is not None and pct < MIN_BATTERY_PCT:
        return False, "on battery at %d%% (need %d%%)" % (pct, MIN_BATTERY_PCT)
    if not network_ok():
        return False, "formulae.brew.sh unreachable"
    why = "overdue" if overdue else "due"
    return True, why + (", on AC" if ac else ", on battery at %s%%" % pct)


def hold_awake():
    """caffeinate for as long as this process lives."""
    if DRY:
        return
    try:
        subprocess.Popen([CAFFEINATE, "-i", "-s", "-w", str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


# ----------------------------------------------------------------- fingerprint

def fingerprint():
    """sha1 over what brew, uv and npm have installed, from the directories
    alone: a move anywhere changes it, and computing it runs nothing."""
    names = []

    def ls(d):
        try:
            return sorted(os.listdir(d))
        except OSError:
            return []
    if PREFIX:
        for top in ("Cellar", "Caskroom"):
            for a in ls(os.path.join(PREFIX, top)):
                for b in ls(os.path.join(PREFIX, top, a)):
                    names.append("%s/%s/%s" % (top, a, b))
        mods = os.path.join(PREFIX, "lib", "node_modules")
        pkgs = []
        for a in ls(mods):
            if a.startswith("@"):
                pkgs.extend(os.path.join(a, b) for b in ls(os.path.join(mods, a)))
            else:
                pkgs.append(a)
        for p in pkgs:
            try:
                with open(os.path.join(mods, p, "package.json"), encoding="utf-8") as fh:
                    names.append("npm/%s@%s" % (p, json.load(fh).get("version")))
            except (OSError, ValueError, AttributeError):
                pass
    for a in ls(UV_PYTHONS):
        names.append("uv/" + a)
    return hashlib.sha1("\n".join(sorted(names)).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- repairs

def board_import(name):
    """A tutorboard module, from this checkout's board/, or None."""
    if BOARD_DIR not in sys.path:
        sys.path.insert(0, BOARD_DIR)
    try:
        return __import__("tutorboard." + name, fromlist=[name])
    except Exception:                                        # noqa: BLE001
        return None


def subject_list():
    """[(id, root)] of every subject, found the way the board finds them."""
    mod = board_import("subjects")
    if mod is None:
        return None
    try:
        return [(s["id"], s["root"]) for s in mod.all(base=ATLAS)]
    except Exception:                                        # noqa: BLE001
        return None


def tex_dirs():
    mod = board_import("tex")
    try:
        return mod.tex_bin_dirs() if mod else []
    except Exception:                                        # noqa: BLE001
        return []


def has_extra(pyproject, want):
    """Does pyproject.toml declare the optional extra `want`? setup.sh's
    has_extra, as a line scan."""
    inside = False
    try:
        with open(pyproject, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line.startswith("["):
                    inside = line == "[project.optional-dependencies]"
                    continue
                parts = line.split()
                if inside and len(parts) >= 2 and parts[0] == want and parts[1] == "=":
                    return True
    except OSError:
        pass
    return False


def act(argv, timeout, acting, cwd=None, env=None):
    """Run a repair. True when it ran and succeeded; None when it did not run
    (a baseline tick, or --dry-run, which still says what it would run)."""
    if not acting:
        return None
    check_off()
    code, out, err = run(argv, timeout, mutating=True, cwd=cwd, env=env)
    if DRY:
        return None
    if code != 0:
        log_tail(out + "\n" + err, os.path.basename(argv[0]), 8)
    return code == 0


def problem(what, fix):
    return {"what": what, "fix": fix}


def probe_board_agent(acting):
    """R1: the board's LaunchAgent names an interpreter that exists."""
    data = read_plist(BOARD_AGENT)
    if data is None:
        return [problem("no tutor-board LaunchAgent", "bash board/install.sh")]
    args = data.get("ProgramArguments") or []
    exe = str(args[0]) if args else ""
    if exe and os.path.exists(exe):
        log("probe board agent: ok (%s)" % exe)
        return []
    log("probe board agent: its interpreter %s is gone" % (exe or "(none)"))
    if act(["bash", os.path.join(ATLAS, "board", "install.sh")], T_BINSTALL, acting):
        log("repaired: board/install.sh re-rendered and reloaded tutor-board")
        return []
    return [problem("the tutor-board LaunchAgent's python %s is gone" % exe,
                    "bash board/install.sh")]


def probe_venvs(acting):
    """R2: every subject's .venv starts; a broken one is re-synced."""
    subs = subject_list()
    if subs is None:
        return [problem("the subjects could not be listed", "python3 board/bin/board doctor")]
    out = []
    for ident, root in subs:
        pyproject = os.path.join(root, "pyproject.toml")
        if not os.path.isfile(pyproject):
            continue
        venv = os.path.join(root, ".venv")
        if not os.path.isdir(venv):
            out.append(problem("%s has no .venv" % ident, "bash scripts/setup.sh"))
            continue
        code, _, _ = run([os.path.join(venv, "bin", "python"), "-c", "pass"], T_PROBE)
        if code == 0:
            log("probe venv %s: ok" % ident)
            continue
        log("probe venv %s: broken (exit %d)" % (ident, code))
        argv = ["uv", "sync", "--locked"]
        if has_extra(pyproject, "test"):
            argv += ["--extra", "test"]
        if act(argv, T_UVSYNC, acting, cwd=root):
            log("repaired: %s's .venv re-synced" % ident)
            continue
        out.append(problem("%s's .venv does not start" % ident,
                           "cd %s && %s" % (ident, " ".join(argv))))
    return out


CLIS = os.path.join("ai-config", "scripts", "install-clis.sh")


def clis_missing():
    """The assistant CLIs install-clis.sh would install, by its label, from its
    `--list`; None when it is not here or cannot say."""
    script = os.path.join(ATLAS, CLIS)
    if not os.path.isfile(script):
        return None
    code, out, _ = run(["bash", script, "--list"], T_PROBE * 2)
    if code != 0:
        return None
    return set(m.group(1) for m in
               (re.match(r"\s*--\s+(.+?) is missing; would run:", l)
                for l in out.splitlines()) if m)


def probe_clis(own, acting, before):
    """R3, own mode only: put back an assistant CLI this run removed. `before`
    is what was missing as the run began (None: not known, so nothing is put
    back). install-clis.sh installs every missing CLI, so it runs only when
    nothing was missing before; otherwise the gone one is reported. Defer mode
    leaves node and npm to the other upgrader."""
    if not own or before is None:
        return []
    after = clis_missing()
    gone = sorted((after or set()) - before)
    if not gone:
        return []
    log("probe CLIs: %s went missing in this run" % ", ".join(gone))
    if not before:
        if act(["bash", os.path.join(ATLAS, CLIS)], T_TOOLS, acting):
            log("repaired: install-clis.sh put back %s" % ", ".join(gone))
            return []
    return [cli_problem(gone, before)]


def cli_problem(gone, before):
    p = problem("%s went missing in the upgrade" % ", ".join(gone),
                "bash %s, which also installs %s" % (CLIS, ", ".join(sorted(before)))
                if before else "bash " + CLIS)
    p.update({"clis": list(gone), "kept_off": sorted(before)})
    return p


def probe_tex():
    """R4: TeX's programs and the packages the board's builds load. Report only."""
    dirs = tex_dirs()
    path = os.pathsep.join(dirs + [os.environ.get("PATH", "")])
    missing = [exe for exe in ("latex", "pdflatex", "dvisvgm", "latexmk")
               if not shutil.which(exe, path=path)]
    stys = ["standalone.sty", "varwidth.sty", "preview.sty", "needspace.sty"]
    kpse = shutil.which("kpsewhich", path=path)
    absent = list(stys)
    if kpse:
        _, out, _ = run([kpse] + stys, T_PROBE)
        found = set(os.path.basename(l.strip()) for l in out.splitlines() if l.strip())
        absent = [s for s in stys if s not in found]
    if not missing and not absent:
        log("probe tex: ok")
        return []
    log("probe tex: missing %s" % ", ".join(missing + absent))
    if missing or not kpse:
        return [problem("TeX is missing %s" % ", ".join(missing + absent),
                        "brew reinstall texlive")]
    return [problem("TeX is missing %s" % ", ".join(absent),
                    "tlmgr install %s" % " ".join(s[:-4] for s in absent))]


def probe_brewfile(own, acting):
    """R5: everything the Brewfile names is installed. Own mode installs a
    miss, which is how a new python minor version lands."""
    bf = os.path.join(ATLAS, "Brewfile")
    if not PREFIX or not os.path.isfile(bf):
        return []
    code, out, err = brew(["bundle", "check", "--no-upgrade", "--file=" + bf], T_BCHECK)
    if code == 0:
        log("probe Brewfile: ok")
        return []
    log("probe Brewfile: %s" % (last_line(out, err) or "a miss"))
    if not own:
        return [problem("the Brewfile is not satisfied", "bash scripts/setup.sh")]
    if not acting:
        return [problem("the Brewfile is not satisfied",
                        "brew bundle install --no-upgrade --file=Brewfile")]
    code, out, err = brew(["bundle", "install", "--no-upgrade", "--file=" + bf],
                          T_BINSTALL, mutating=True)
    if DRY:
        return [problem("the Brewfile is not satisfied",
                        "brew bundle install --no-upgrade --file=Brewfile")]
    log_tail(out + "\n" + err, "bundle", 8)
    if code == 0:
        log("repaired: brew bundle install")
        return []
    return [problem("brew bundle install failed: %s" % last_line(err, out),
                    "brew bundle install --no-upgrade --file=Brewfile")]


def probe_board_serve():
    """R6: the board answers and tailscale serves it. Report only; tailscale
    is never restarted from here."""
    port = board_port()
    out = []
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=10) as r:
            up = r.status == 200
    except Exception:                                        # noqa: BLE001
        up = False
    if not up:
        out.append(problem("the board does not answer on 127.0.0.1:%d" % port,
                           "see ~/.local/state/tutor-board/server.log"))
    code, said, _ = run(["tailscale", "serve", "status"], T_PROBE)
    if "127.0.0.1:%d" % port not in said:
        out.append(problem("tailscale does not serve the board",
                           "tailscale serve --bg --https=443 http://127.0.0.1:%d" % port))
    log("probe board: %s" % ("ok" if not out else "; ".join(p["what"] for p in out)))
    return out


def repairs(role, own, acting, brewfile=True, clis_before=None):
    """Every probe for this role; each repair acts only when `acting`. The
    problems found, as [{what, fix}]."""
    log("repairs (%s%s)" % ("own" if own else "defer",
                            "" if acting else ", report only"))
    found = []
    if role == "host":
        check_off()
        found += probe_board_agent(acting)
    check_off()
    found += probe_venvs(acting)
    found += probe_clis(own, acting, clis_before)
    found += probe_tex()
    if brewfile:
        check_off()
        found += probe_brewfile(own, acting)
    if role == "host":
        found += probe_board_serve()
    for p in found:
        log("problem: %s; %s" % (p["what"], p["fix"]))
    return found


# ---------------------------------------------------------------------- notify

def notify(state):
    """A coding laptop hears each new brew line once, as a notification."""
    if DRY or state.get("role") != "coding":
        return
    care = board_import("brewcare")
    if care is None:
        return
    try:
        lines = care.lines_of(state, now())
    except Exception:                                        # noqa: BLE001
        return
    seen = set(state.get("notified") or [])
    keep = []
    for line in lines:
        h = hashlib.sha1(line.encode("utf-8")).hexdigest()
        keep.append(h)
        if h in seen:
            continue
        text = line.replace("\\", "\\\\").replace('"', '\\"')
        run(["osascript", "-e",
             'display notification "%s" with title "Atlas brew"' % text], T_PROBE)
    state["notified"] = keep
    save_state(state)


# ------------------------------------------------------------------- the work

def outdated():
    """(formulae, casks, ok): records from `brew outdated --json=v2`, stdout
    only, since brew's warnings go to stderr."""
    code, out, err = brew(["outdated", "--json=v2"], T_OUTDATED)
    if code != 0:
        return [], [], "exit %d: %s" % (code, last_line(err, out))
    try:
        data = json.loads(out)
        formulae = [f for f in data.get("formulae") or [] if f.get("name")]
        casks = [c for c in data.get("casks") or [] if c.get("name")]
    except (ValueError, AttributeError) as exc:
        return [], [], "unparseable: %s" % exc
    return formulae, casks, None


def versions(rec):
    inst = rec.get("installed_versions") or [""]
    return str(inst[-1] if isinstance(inst, list) and inst else inst), \
        str(rec.get("current_version") or "")


def tailscale_service():
    return any(os.path.exists(os.path.join(d, "homebrew.mxcl.tailscale.plist"))
               for d in AGENT_DIRS)


def cask_apps(names):
    """{cask: [app name without .app]} from brew info."""
    if not names:
        return {}
    code, out, _ = brew(["info", "--cask", "--json=v2"] + list(names), T_OUTDATED)
    apps = {}
    if code != 0:
        return apps
    try:
        for c in json.loads(out).get("casks") or []:
            got = []
            for art in c.get("artifacts") or []:
                if not isinstance(art, dict) or "app" not in art:
                    continue
                for item in art["app"]:
                    if isinstance(item, str):
                        got.append(item)
                    elif isinstance(item, dict) and item.get("target") and got:
                        got[-1] = os.path.basename(str(item["target"]))
            apps[c.get("token") or c.get("name")] = [
                g[:-4] if g.endswith(".app") else g for g in got]
    except (ValueError, AttributeError, TypeError):
        pass
    return apps


def ere(text):
    return re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", text)


def app_running(app):
    code, out, _ = run(["pgrep", "-f", "/Applications/%s\\.app/Contents/MacOS/" % ere(app)],
                       T_PROBE)
    return code == 0 and bool(out.strip())


def own_run(state, role, why):
    """One upgrade run. Saves state at the end whatever happened."""
    trim_log()
    started = now()
    log("=== brew upgrade run (%s) ===" % why)
    state["last_attempt"] = stamp(started)
    save_state(state)
    ok = True
    failed, held = {}, {}
    defers = dict(state.get("cask_defers") or {})
    found = []
    stopped = False
    try:
        clis_before = clis_missing()
        # 1. the index
        check_off()
        if DRY:
            log("index not refreshed (dry-run)")
        else:
            code, out, err = brew(["update"], T_UPDATE, mutating=True)
            if code != 0:
                ok = False
                failed["brew update"] = last_line(err, out) or "exit %d" % code
                log("! brew update exited %d; upgrading against the old index" % code)
                log_tail(out + "\n" + err, "brew update")

        # 2. what is outdated
        formulae, casks, bad = outdated()
        if bad:
            ok = False
            failed["brew outdated"] = bad
            log("! brew outdated failed (%s); no upgrade this run" % bad)
        else:
            now_casks = set(c["name"] for c in casks)
            defers = dict((k, v) for k, v in defers.items() if k in now_casks)
            # 3. holds
            for f in formulae:
                name = f["name"]
                inst, latest = versions(f)
                if f.get("pinned"):
                    held[name] = {"installed": inst, "latest": latest,
                                  "why": "pinned; brew unpin %s to let it move" % name}
                elif name == "tailscale" and role == "host" and tailscale_service():
                    held[name] = {"installed": inst, "latest": latest,
                                  "why": "its daemon is a brew service carrying the "
                                         "board's tailnet; upgrade it by hand and "
                                         "restart it"}
            apps = cask_apps(sorted(c["name"] for c in casks))
            run_casks = []
            for c in casks:
                name = c["name"]
                running = [a for a in apps.get(name, []) if app_running(a)]
                if not running:
                    run_casks.append(name)
                    continue
                defers[name] = int(defers.get(name) or 0) + 1
                inst, latest = versions(c)
                if defers[name] >= CASK_DEFER_HOLD:
                    held[name] = {"installed": inst, "latest": latest,
                                  "why": "%s.app was running at every upgrade; quit it, "
                                         "then atlas-brew run --force" % running[0]}
                else:
                    log("%s.app is running; cask %s waits (%d of %d)"
                        % (running[0], name, defers[name], CASK_DEFER_HOLD))
            names = sorted(f["name"] for f in formulae if f["name"] not in held)
            if not formulae and not casks:
                log("everything is current")
            else:
                log("outdated: %d formula(e), %d cask(s)%s"
                    % (len(formulae), len(casks),
                       ", %d held" % len(held) if held else ""))
            for name, h in sorted(held.items()):
                log("HELD: %s %s -> %s: %s" % (name, h["installed"], h["latest"], h["why"]))

            # 4. formulae, named
            check_off()
            if names:
                log("upgrading formulae: %s" % ", ".join(names))
                code, out, err = brew(["upgrade", "--formula"] + names, T_FORMULAE,
                                      mutating=True)
                log_tail(out + "\n" + err, "brew")
                if code != 0:
                    ok = False
                    failed["formulae"] = last_line(err, out) or "exit %d" % code

            # 5. casks, one at a time
            for name in sorted(run_casks):
                check_off()
                code, out, err = brew(["upgrade", "--cask", name], T_CASK, mutating=True)
                if code == 0:
                    defers.pop(name, None)
                    if not DRY:
                        log("upgraded cask %s" % name)
                else:
                    ok = False
                    failed[name] = last_line(err, out) or "exit %d" % code
                    log("! cask %s exited %d" % (name, code))
                    log_tail(out + "\n" + err, "cask " + name, 8)

        # 6. the Brewfile
        check_off()
        bf = probe_brewfile(True, True)
        if bf:
            ok = False
            found += bf

        # 7. brew's npm globals
        npm = os.path.join(PREFIX, "bin", "npm")
        check_off()
        if os.path.exists(npm):
            code, out, err = run([npm, "update", "-g"], T_NPM, mutating=True,
                                 env=brew_env())
            if code != 0:
                failed["npm globals"] = last_line(err, out) or "exit %d" % code
                log("! npm update -g exited %d" % code)
                log_tail(out + "\n" + err, "npm", 8)

        # 8. the assistant CLIs, by ai-config's own updater
        tools = os.path.join(ATLAS, "ai-config", "scripts", "update-tools")
        check_off()
        if os.path.isfile(tools):
            code, out, err = run(["bash", tools], T_TOOLS, mutating=True)
            if code != 0:
                log("! update-tools exited %d" % code)
                log_tail(out + "\n" + err, "update-tools", 8)

        # 9. uv's own Pythons
        uv = shutil.which("uv", path=os.environ.get("PATH", "") + os.pathsep
                          + os.path.join(PREFIX, "bin"))
        try:
            pythons = [n for n in os.listdir(UV_PYTHONS) if n.startswith("cpython-")]
        except OSError:
            pythons = []
        check_off()
        if uv and pythons:
            code, out, err = run([uv, "python", "upgrade"], T_UVPY, mutating=True)
            if code != 0:
                log("! uv python upgrade exited %d" % code)
                log_tail(out + "\n" + err, "uv", 8)

        # 10. repairs
        found += repairs(role, True, True, brewfile=False, clis_before=clis_before)

        # 11. cleanup, last
        check_off()
        code, out, err = brew(["cleanup", "--prune=%d" % PRUNE_DAYS], T_CLEANUP,
                              mutating=True)
        if code != 0:
            log("! brew cleanup exited %d" % code)
            log_tail(out + "\n" + err, "cleanup", 3)
    except Stopped:
        ok, stopped = False, True
        log("off by owner: the run stops here, before its next step")
    except Exception as exc:                                 # noqa: BLE001
        ok = False
        failed["brew-upgrade.py"] = repr(exc)[:300]
        log("! the run stopped on %r" % exc)
    finally:
        drop_lock()
        done = now()
        state["last_result"] = "stopped" if stopped else "ok" if ok else "partial"
        if ok:
            state["last_success"] = stamp(done)
        state["last_duration_seconds"] = int((done - started).total_seconds())
        state.update({"held": held, "failed": failed, "cask_defers": defers,
                      "mode": "own", "role": role, "problems": found,
                      "fingerprint": fingerprint(), "probed_at": stamp(done)})
        state.pop("deferred_to", None)
        save_state(state)
        log("=== %s in %ds (%s) ===" % ("dry run done" if DRY else "done",
                                       state["last_duration_seconds"],
                                       state["last_result"]))
        notify(state)
    return 0


def recheck(state, role, own):
    """A recorded problem is probed again, report only, once RECHECK_MIN has
    passed: one fixed by its own fix (`tlmgr install`, setup.sh) moves nothing
    the fingerprint sees, and would otherwise stay up until the next move."""
    if not state.get("problems"):
        return 0
    last = parse_ts(state.get("probed_at"))
    if last and hours_since(last) * 60 < RECHECK_MIN:
        return 0
    log("re-probing %d recorded problem(s)" % len(state["problems"]))
    found = repairs(role, own, False)
    # What the run removed is known only to the run; keep what is still gone.
    clis = [p for p in state["problems"] if isinstance(p, dict) and p.get("clis")]
    missing = clis_missing() if clis else None
    for p in clis:
        still = [n for n in p["clis"] if n in (missing or set())]
        if still:
            found.append(cli_problem(still, set(p.get("kept_off") or [])))
    state.update({"problems": found, "probed_at": stamp()})
    save_state(state)
    notify(state)
    return 0


def defer_tick(state, role, other, forced=False):
    """Defer mode: probe and repair once brew's tree moves; upgrade nothing."""
    fp = fingerprint()
    stored = state.get("fingerprint")
    same = (stored == fp and state.get("mode") == "defer"
            and (state.get("deferred_to") or {}).get("label") == other[0])
    if DRY:
        log("fingerprint: %s" % ("no baseline yet" if not stored else
                                 "unchanged" if stored == fp else "moved"))
    if same and not forced and not DRY:
        return recheck(state, role, False)
    baseline = not stored and not forced
    if baseline:
        log("first tick: probes only, recording the baseline")
    found = repairs(role, False, not baseline)
    state.update({"mode": "defer", "role": role,
                  "deferred_to": {"label": other[0], "path": other[1]},
                  "fingerprint": fp, "probed_at": stamp(), "problems": found})
    for k in ("held", "failed", "cask_defers"):
        state.pop(k, None)
    save_state(state)
    notify(state)
    return 0


def cmd_run(force=False, repair_only=False):
    if os.path.exists(OFF_FILE) and not DRY:
        return 0
    if os.path.exists(OFF_FILE):
        log("off by owner (%s); a real tick does nothing" % OFF_FILE)
    if not PREFIX:
        log("no brew")
        return 0
    role = read_role()
    other = other_upgrader()
    mode = "defer" if other else "own"
    if DRY:
        log("mode: %s%s, role %s" % (mode, " -> %s (%s)" % other if other else "", role))
    why_busy = busy(role)
    if why_busy:
        if not DRY:
            log("skipped: %s; the next hour asks again" % why_busy)
            return 0
        log("busy: %s; a real tick would stop here" % why_busy)
    if not take_lock():
        log("another run holds the lock")
        return 0
    try:
        return work(role, other, force, repair_only)
    except Stopped:
        log("off by owner: stopped before the next step")
        return 0
    finally:
        drop_lock()


def work(role, other, force, repair_only):
    """cmd_run's body, under the lock."""
    state = load_state()
    if other:
        if DRY:
            log("gate: not used; defers to %s, so nothing is upgraded" % other[0])
        return defer_tick(state, role, other, forced=repair_only)
    if repair_only:
        found = repairs(role, True, True)
        state.update({"problems": found, "probed_at": stamp(), "role": role})
        save_state(state)
        notify(state)
        return 0
    if not state.get("first_seen"):
        state["first_seen"] = stamp()
        save_state(state)
    if DRY:
        go, why = gate(state, role)
        log("gate: %s (%s)" % ("would run" if go else "would skip", why))
        why = "dry run"
    elif force:
        why = "forced"
    else:
        go, why = gate(state, role)
        if not go:
            if why == "formulae.brew.sh unreachable" and now().hour in WINDOW:
                log("skipped: %s; the next hour retries" % why)
            return recheck(state, role, True)
    hold_awake()
    return own_run(state, role, why)


# ------------------------------------------------------------ the LaunchAgent

def render():
    with open(TEMPLATE, "rb") as fh:
        data = plistlib.load(fh)

    def sub(v):
        if isinstance(v, str):
            return v.replace("@HOME@", HOME).replace("@ATLAS@", ATLAS)
        if isinstance(v, list):
            return [sub(x) for x in v]
        if isinstance(v, dict):
            return dict((k, sub(x)) for k, x in v.items())
        return v
    return plistlib.dumps(sub(data))


def domain():
    return "gui/%d" % os.getuid()


def loaded():
    return run(["launchctl", "print", "%s/%s" % (domain(), LABEL)], T_PROBE)[0] == 0


def cmd_install():
    if os.path.exists(OFF_FILE):
        print("off by owner (atlas-brew on)")
        return 0
    try:
        body = render()
    except Exception as exc:                                 # noqa: BLE001
        print("could not render %s: %s" % (TEMPLATE, exc))
        return 1
    try:
        with open(AGENT, "rb") as fh:
            changed = fh.read() != body
    except OSError:
        changed = True
    try:
        if changed:
            os.makedirs(os.path.dirname(AGENT), exist_ok=True)
            with open(AGENT + ".tmp", "wb") as fh:
                fh.write(body)
            os.replace(AGENT + ".tmp", AGENT)
        # launchd writes its log there and makes no directory.
        os.makedirs(os.path.join(HOME, ".local", "state", "atlas-setup"), exist_ok=True)
    except OSError as exc:
        print("could not write %s: %s" % (AGENT, exc))
        return 1
    holder = lock_holder()
    is_loaded = loaded()
    if changed and is_loaded and holder is not None:
        spawn_settle()
        print("%s: a run (pid %s) is under way; the job reloads once it ends"
              % (LABEL, holder or "?"))
    elif changed or not is_loaded:
        code, why = reload_job()
        if code != 0:
            print("launchctl bootstrap failed: %s" % why)
            return 1
    try:
        os.makedirs(os.path.dirname(LINK), exist_ok=True)
        if os.path.islink(LINK) and os.readlink(LINK) != SCRIPT:
            os.remove(LINK)
        if not os.path.lexists(LINK):
            os.symlink(SCRIPT, LINK)
    except OSError as exc:
        print("could not link %s: %s" % (LINK, exc))
        return 1
    other = other_upgrader()
    if other:
        print("%s loaded; defers to %s (repairs only)" % (LABEL, other[0]))
    else:
        print("%s loaded; upgrades brew daily 03:00-07:59" % LABEL)
    return 0


def reload_job():
    """Boot the job out and, unless it is off or its plist is gone, back in.
    (code, why) of the bootstrap; (0, "") when there is none."""
    run(["launchctl", "bootout", "%s/%s" % (domain(), LABEL)], T_PROBE)
    if os.path.exists(OFF_FILE) or not os.path.exists(AGENT):
        return 0, ""
    code, out, err = run(["launchctl", "bootstrap", domain(), AGENT], T_PROBE)
    return code, (last_line(err, out) or str(code))


def spawn_settle():
    """Start `settle` detached, in its own session, so neither this command
    ending nor the job's bootout takes it down."""
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as out:
            subprocess.Popen([sys.executable, SCRIPT, "settle"], stdin=subprocess.DEVNULL,
                             stdout=out, stderr=out, start_new_session=True,
                             close_fds=True)
        return True
    except OSError as exc:
        print("could not start settle: %s" % exc)
        return False


def cmd_settle():
    """Wait for the run that holds the lock to end, then reload the job, or
    unload it when it is off. A bootout of a running job would stop the run
    between a keg's unlink and its link."""
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as exc:
        log("! settle: %s" % exc)
        return 1
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        code, why = reload_job()
        log("settle: the run ended; %s" % (
            "unloaded" if os.path.exists(OFF_FILE) or not os.path.exists(AGENT)
            else "reloaded" if code == 0 else "bootstrap failed: %s" % why))
        return 0 if code == 0 else 1
    finally:
        os.close(fd)


def cmd_off():
    os.makedirs(os.path.dirname(OFF_FILE), exist_ok=True)
    with open(OFF_FILE, "w", encoding="utf-8") as fh:
        fh.write("off since %s; atlas-brew on undoes it\n" % stamp())
    try:
        os.remove(AGENT)
    except OSError:
        pass
    holder = lock_holder()
    if holder is None:
        reload_job()
        print("%s is off: unloaded, its plist removed, %s written"
              % (LABEL, OFF_FILE))
        return 0
    spawn_settle()
    print("%s is off: %s written, its plist removed. The run under way (pid %s) "
          "stops before its next step, its current brew left to finish; the job "
          "unloads once it ends" % (LABEL, OFF_FILE, holder or "?"))
    return 0


def cmd_on():
    try:
        os.remove(OFF_FILE)
    except OSError:
        pass
    return cmd_install()


def next_window(state):
    earliest = now()
    la = parse_ts(state.get("last_attempt"))
    if la and la + timedelta(hours=MIN_INTERVAL_H) > earliest:
        earliest = la + timedelta(hours=MIN_INTERVAL_H)
    if earliest.hour in WINDOW:
        return earliest
    start = earliest.replace(hour=WINDOW[0], minute=0, second=0, microsecond=0)
    return start if start > earliest else start + timedelta(days=1)


def cmd_status():
    state = load_state()
    other = other_upgrader()
    if other:
        print("mode:      defer to %s (%s)" % other)
    else:
        print("mode:      own")
    print("role:      %s" % read_role())
    print("loaded:    %s" % ("yes" if loaded() else "no"))
    print("off:       %s" % ("yes (atlas-brew on)" if os.path.exists(OFF_FILE) else "no"))
    for k in ("last_attempt", "last_success", "last_result"):
        print("%-10s %s" % (k.replace("last_", "") + ":", state.get(k) or "never"))
    if state.get("last_duration_seconds") is not None:
        print("duration:  %ss" % state["last_duration_seconds"])
    print("probed:    %s" % (state.get("probed_at") or "never"))
    if not other:
        print("next:      %s" % next_window(state).strftime("%a %b %d %H:%M"))
    held = state.get("held") or {}
    failed = state.get("failed") or {}
    problems = state.get("problems") or []
    for name, h in sorted(held.items()):
        print("HELD      %s %s -> %s: %s" % (name, h.get("installed"), h.get("latest"),
                                             h.get("why")))
    for name, why in sorted(failed.items()):
        print("FAILED    %s: %s" % (name, why))
    for p in problems:
        print("PROBLEM   %s; %s" % (p.get("what"), p.get("fix")))
    return 1 if (held or failed or problems) else 0


USAGE = ("usage: atlas-brew run [--dry-run] [--force] | repair [--dry-run] | status "
         "| install | off | on | plist")


def main(argv):
    global DRY
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, flags = argv[0], argv[1:]
    allowed = {"run": ("--dry-run", "--force"), "repair": ("--dry-run",)}
    if cmd not in ("run", "repair", "status", "install", "off", "on", "plist",
                   "settle") \
            or any(f not in allowed.get(cmd, ()) for f in flags):
        print(USAGE, file=sys.stderr)
        return 2
    DRY = "--dry-run" in flags
    if cmd == "run":
        return cmd_run(force="--force" in flags or DRY)
    if cmd == "repair":
        return cmd_run(force=True, repair_only=True)
    if cmd == "status":
        return cmd_status()
    if cmd == "install":
        return cmd_install()
    if cmd == "off":
        return cmd_off()
    if cmd == "on":
        return cmd_on()
    if cmd == "settle":
        return cmd_settle()
    sys.stdout.write(render().decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
