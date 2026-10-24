#!/usr/bin/python3
"""brew-upgrade.py -- keep this Mac's Homebrew current, and repair what a move breaks.

    atlas-brew run [--dry-run] [--force]   the hourly launchd tick
    atlas-brew repair [--dry-run]          the probes and repairs, now
    atlas-brew status                      what the last run did; exit 1 on a problem
    atlas-brew install | off | on | plist  the LaunchAgent, atlas.brew-upgrade
    atlas-brew settle                      internal: reload or unload once a run ends

`atlas-brew` is ~/.local/bin/atlas-brew, a link to this file. setup-mac.sh's
step 7 runs `install` on both roles. State is $BOARD_STATE_DIR/brew.json (else
~/.local/state/tutor-board/brew.json); board/tutorboard/brewcare.py reads it for
/sync.json and `board doctor`. The log is ~/.local/state/atlas-setup/brew-upgrade.log.

The rules, each with its reason:

  * DEFER TO ANOTHER UPGRADER. When a LaunchAgent or LaunchDaemon whose label or
    program matches `brew.?(upgrade|autoupdate)|homebrew-autoupdate` is
    installed and loaded, this job leaves brew's daily upgrade to it and probes
    and repairs on the tick after brew's tree moves, because two upgraders
    fight over brew's lock. A plist left installed but not loaded is no
    upgrader: it upgrades nothing, so this job does.
  * COVER FOR IT. When that job's last success is over 26 hours old, or no
    record of one is found, this job runs its own brew upgrade that day and
    records that it covered. A success is a `last_success` in a JSON in the
    other job's working directory's or program's `state/` (or beside it), or
    a `=== done ... (ok) ===` line in the log its plist names, all read naming
    no vendor; a partial run is no success. The cover's gate is the usual
    one, measured from the newer of the two jobs' last successes. The cover
    is a full brew upgrade: formulae, every cask, the Brewfile union and npm.
    It excludes nothing of that job's, neither the casks it protects nor what
    its state holds; only this job's own HOLDS apply. A cask whose installer
    needs the admin password fails and is recorded as failed, because no call
    has a stdin or a terminal to prompt on. Brew takes its lock without
    waiting, so a second brew fails rather than queues: the cover starts only when no brew
    and no other upgrader is running (BUSY), checks again before each brew
    step, and stops when either has started.
  * AFTER ITS TURN. In defer mode the day's work, a cover or the toolchain
    phase alone, waits while the other job is due: its last start (a
    `last_attempt` in that JSON, or a `=== ... run ... ===` line in its log)
    is MIN_INTERVAL_H or more old. It goes once that job has started and
    ended, or after WAIT_H of ticks in which it never started, so the two
    jobs' brew, npm and CLI updates do not overlap. Every step of a defer-mode
    run, not only a brew step, stops when the other job has started, since
    it updates the same CLIs and npm globals. A run that yields before its
    toolchain phase is done unstamps its attempt, so a later tick that day
    runs it, and keeps the tool failures it did not re-check.
  * THE TOOLCHAIN PHASE RUNS IN BOTH MODES, once a day under the same gate:
    ai-config's update-tools, `uv python upgrade`, `mise install --locked
    <tools>` in every subject directory holding a mise.toml, then `mise prune
    --tools` of the tools those files name, and `scripts/tools.sh update`,
    because none of it takes brew's lock; in defer mode it runs after the
    other job's turn (AFTER ITS TURN). Install names the directory's own
    tools because --locked fails on any tool without a mise.lock entry, and
    the owner's global config has none; the prune is named because a bare one
    removes every version no tracked config uses, Atlas's or not, and without
    --tools it also forgets the owner's trusted configs. A failure enters
    brew.json `failed` as `tool:<name>`; update-tools never exits non-zero, so
    an assistant CLI's failure is read from the lines it adds to its log. Then
    `mise outdated --json --bump --local` names each pin behind (a non-null
    `bump`) in tools.json, and that subject's sessions are briefed to propose
    the bump; a pin moves only by a commit of mise.toml and mise.lock, never
    from here.
  * HOURLY, GATED TO ONCE A DAY IN 03:00-07:59. A sleeping machine misses a
    calendar job; an hourly tick catches up. The host never upgrades outside the
    window, because the owner may be in a lesson. A coding laptop upgrades
    outside it only when 48 hours overdue, on AC and idle 20 minutes, because a
    laptop is shut at night.
  * BUSY MEANS NEXT HOUR. A running brew, another upgrader running (an
    interpreter whose script's name matches, never an editor or a `tail` of the
    log), or a board turn running or queued skips the tick, logs why, and
    stamps nothing.
  * NEVER GREEDY. `brew outdated --json=v2` is asked without --greedy, so it
    leaves out every cask marked auto_updates or versioned :latest, even while
    brew's record of one is behind the cask's current version. Such a cask is
    never upgraded here: the app updates itself, and its stale record is not
    read as outdated.
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
    is gone is reinstalled; a miss in the Brewfile union (the root Brewfile
    and every subject's, ~/.local/state/atlas-setup/Brewfile.all, the file
    setup.sh bundles) is installed in own mode, never with --cleanup; an
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
import glob
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
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
TOOLS_JSON = os.path.join(os.path.dirname(STATE), "tools.json")
TOOLS_SH = os.path.join("scripts", "tools.sh")
# update-tools' own log: it always exits 0, so a failed CLI is read from here.
AI_TOOLS_LOG = os.path.join(HOME, ".local", "state", "ai-tools-update.log")
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
COVER_H = 26                         # the other upgrader's last success, at most
WAIT_H = 1.5                         # the other job, due, is waited for this long
WAIT_RESET_H = 3                     # a wait older than this began another stretch
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
T_MISE = 3600
T_UVPY = 1800
T_UVSYNC = 1800
T_CLEANUP = 1800
T_BCHECK = 300
T_BINSTALL = 3600
T_PROBE = 60

DRY = False
_lock_fd = None
COVERING = False                     # a cover run's brew steps yield to any brew
DEFERRING = False                    # a defer-mode run yields to the other upgrader


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
    caller's PATH comes first, then brew's and the system's directories. No
    call has a stdin or a controlling terminal, so a sudo inside one (a cask's
    installer) fails at once rather than waiting on a password prompt."""
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
                           timeout=timeout, env=full, cwd=cwd,
                           start_new_session=True)
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


def brew_busy():
    """A running brew or another upgrader at work, as a reason, or None."""
    code, out, _ = run(["pgrep", "-f", r"/Library/Homebrew/brew\.(rb|sh)"], T_PROBE)
    if code == 0 and out.strip():
        return "a brew is running"
    return upgrader_busy()


def upgrader_busy():
    """Another upgrader at work, as a reason, or None."""
    code, out, _ = run(["pgrep", "-lf", "brew[-_]?upgrade"], T_PROBE)
    if code == 0:
        for line in out.splitlines():
            if upgrader_line(line):
                return "another brew upgrader is running (%s)" % line.strip()[:120]
    return None


def busy(role):
    """Why this tick must not work now, or None."""
    why = brew_busy()
    if why:
        return why
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


class Yielded(Stopped):
    """A cover run met a brew or the other upgrader at work."""


def check_off(brew_step=False):
    """Between steps: stop when `off` has been run since this run began. A
    defer-mode run also stops when the other upgrader has started, and a
    cover, before a brew step, when any brew has: brew does not wait on its
    lock, so the second brew would fail."""
    if not DRY and os.path.exists(OFF_FILE):
        raise Stopped()
    if DRY:
        return
    why = brew_busy() if COVERING and brew_step else \
        upgrader_busy() if DEFERRING else None
    if why:
        raise Yielded(why)


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


def brewfile_union():
    """(path, temporary) of the Brewfile union setup.sh bundles: the root
    Brewfile and every subject's, sorted and deduplicated by
    `toolplan.write_union` into Brewfile.all, which is rewritten only when it
    changed. Under --dry-run a changed union goes to a temp file, since a dry
    run writes nothing. The root Brewfile alone when toolplan cannot answer."""
    plan = board_import("toolplan")
    dest = os.path.join(SETUP_DIR, "Brewfile.all")
    try:
        if plan is None:
            raise ValueError("no toolplan")
        if not DRY:
            plan.write_union(ATLAS, dest)
            return dest, False
        text = plan.union_text(ATLAS)
        try:
            with open(dest, encoding="utf-8") as fh:
                if fh.read() == text:
                    return dest, False
        except OSError:
            pass
        fd, tmp = tempfile.mkstemp(prefix="Brewfile.all.")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return tmp, True
    except Exception:                                        # noqa: BLE001
        root = os.path.join(ATLAS, "Brewfile")
        return (root if os.path.isfile(root) else None), False


def probe_brewfile(own, acting):
    """R5: everything the Brewfile union names is installed. Own mode installs
    a miss, which is how a new python minor version lands; nothing is ever
    removed, so no --cleanup."""
    if not PREFIX:
        return []
    bf, temp = brewfile_union()
    if not bf:
        return []
    try:
        return _probe_brewfile(own, acting, bf)
    finally:
        if temp:
            try:
                os.remove(bf)
            except OSError:
                pass


def _probe_brewfile(own, acting, bf):
    fix = "brew bundle install --no-upgrade --file=" + bf.replace(HOME, "~", 1)
    code, out, err = brew(["bundle", "check", "--no-upgrade", "--file=" + bf], T_BCHECK)
    if code == 0:
        log("probe Brewfile: ok")
        return []
    log("probe Brewfile: %s" % (last_line(out, err) or "a miss"))
    if not own:
        return [problem("the Brewfile is not satisfied", "bash scripts/setup.sh")]
    if not acting:
        return [problem("the Brewfile is not satisfied", fix)]
    code, out, err = brew(["bundle", "install", "--no-upgrade", "--file=" + bf],
                          T_BINSTALL, mutating=True)
    if DRY:
        return [problem("the Brewfile is not satisfied", fix)]
    log_tail(out + "\n" + err, "bundle", 8)
    if code == 0:
        log("repaired: brew bundle install")
        return []
    return [problem("brew bundle install failed: %s" % last_line(err, out), fix)]


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


# ------------------------------------------------------------ the toolchain

def mise_env():
    """mise answers no prompt here, and trusts the Atlas tree's own configs
    for this call only; setup.sh trusts them for good."""
    return {"MISE_YES": "1", "MISE_TRUSTED_CONFIG_PATHS": ATLAS}


def tool_failures():
    """{tool:<name>: why} for each tool tools.json says failed."""
    try:
        with open(TOOLS_JSON, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return {}
    tools = doc.get("tools") if isinstance(doc, dict) else None
    return dict(("tool:" + name, str(rec.get("failed")))
                for name, rec in sorted((tools or {}).items())
                if isinstance(rec, dict) and rec.get("failed"))


CLI_FAILED = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\s+(\S+) \S+: "
                        r"update failed \(exit (\d+)\)")


def log_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def cli_failures(since):
    """{tool:<cli>: why} from the lines update-tools added to its log past
    byte `since` (from the start, when the log is now shorter)."""
    out = {}
    try:
        with open(AI_TOOLS_LOG, "rb") as fh:
            if log_size(AI_TOOLS_LOG) >= since:
                fh.seek(since)
            added = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return out
    for line in added:
        m = CLI_FAILED.match(line)
        if m:
            out["tool:" + m.group(1)] = ("update failed (exit %s); see %s"
                                         % (m.group(2), AI_TOOLS_LOG.replace(HOME, "~", 1)))
    return out


def toolchain(failed):
    """The toolchain phase, the same in own and defer mode: none of it takes
    brew's lock. Each failure goes into `failed` as tool:<name>; each pin
    behind into tools.json. A pin is never moved from here."""
    log("toolchain phase")
    for k in [k for k in failed if k.startswith("tool:")]:
        del failed[k]

    # 1. the assistant CLIs, by ai-config's own updater (ai-tools-update)
    tools = os.path.join(ATLAS, "ai-config", "scripts", "update-tools")
    check_off()
    if os.path.isfile(tools):
        since = log_size(AI_TOOLS_LOG)
        code, out, err = run(["bash", tools], T_TOOLS, mutating=True)
        if code != 0:
            failed["tool:update-tools"] = last_line(err, out) or "exit %d" % code
            log("! update-tools exited %d" % code)
            log_tail(out + "\n" + err, "update-tools", 8)
        if not DRY:
            for name, why in sorted(cli_failures(since).items()):
                failed[name] = why
                log("! %s: %s" % (name[5:], why))

    # 2. uv's own Pythons
    uv = shutil.which("uv", path=os.environ.get("PATH", "") + os.pathsep
                      + os.path.join(PREFIX or "/opt/homebrew", "bin"))
    try:
        pythons = [n for n in os.listdir(UV_PYTHONS) if n.startswith("cpython-")]
    except OSError:
        pythons = []
    check_off()
    if uv and pythons:
        code, out, err = run([uv, "python", "upgrade"], T_UVPY, mutating=True)
        if code != 0:
            failed["tool:uv-python"] = last_line(err, out) or "exit %d" % code
            log("! uv python upgrade exited %d" % code)
            log_tail(out + "\n" + err, "uv", 8)

    # 3. each subject's pinned toolchains, as locked, then the versions of
    # those tools that no tracked config uses. Both named: --locked fails on a
    # tool with no mise.lock entry, which every tool of the owner's global
    # config is, and a bare prune would touch tools only some other project
    # of the owner's uses.
    plan = board_import("toolplan")
    try:
        dirs = [(i, d, plan.pinned_in(d)) for i, d in plan.mise_dirs(ATLAS)] \
            if plan else []
        pinned = plan.mise_tools(ATLAS) if plan else []
    except Exception:                                        # noqa: BLE001
        dirs, pinned = [], []
    for ident, where, names in dirs:
        if not names:
            continue
        check_off()
        code, out, err = run(["mise", "install", "--locked"] + names, T_MISE,
                             mutating=True, cwd=where, env=mise_env())
        if code != 0:
            failed["tool:mise:" + ident] = last_line(err, out) or "exit %d" % code
            log("! mise install in %s exited %d" % (ident, code))
            log_tail(out + "\n" + err, "mise", 8)
    if pinned:
        check_off()
        code, out, err = run(["mise", "prune", "--yes", "--tools"] + pinned, T_MISE,
                             mutating=True, env=mise_env())
        if code != 0:
            failed["tool:mise-prune"] = last_line(err, out) or "exit %d" % code
            log("! mise prune exited %d" % code)

    # 4. the subjects' tool descriptors
    sh = os.path.join(ATLAS, TOOLS_SH)
    check_off()
    if os.path.isfile(sh):
        code, out, err = run(["bash", sh, "update"], T_TOOLS, mutating=True)
        if code != 0:
            log("! tools.sh update exited %d" % code)
            log_tail(out + "\n" + err, "tools.sh", 8)
        if not DRY:
            said = tool_failures()
            failed.update(said)
            if code != 0 and not said:
                failed["tool:tools.sh"] = last_line(out, err) or "exit %d" % code

    # 5. the pins behind, named and never moved. --local leaves out the
    # owner's global config; pins_of keeps only this directory's own.
    pins = []
    for ident, where, _names in dirs:
        code, out, err = run(["mise", "outdated", "--json", "--bump", "--local"],
                             T_PROBE * 5, cwd=where, env=mise_env())
        if code == 0 and plan is not None:
            pins += plan.pins_of(out, ident, where)
        elif code != 0:
            log("! mise outdated in %s exited %d" % (ident, code))
    for p in pins:
        log("pin behind: %s %s %s -> %s" % (p["subject"], p["tool"], p["pinned"],
                                            p["latest"]))
    if plan is not None and not DRY:
        try:
            plan.write_pins(pins)
        except Exception as exc:                             # noqa: BLE001
            log("! could not write tools.json: %s" % exc)


def toolchain_run(state, role, why):
    """Defer mode's daily work when there is nothing to cover: the toolchain
    phase alone. brew.json keeps only its tool:<name> failures; a phase that
    did not finish keeps the ones it had. One that yielded to the other job
    unstamps its attempt, so a later tick that day runs it."""
    global DEFERRING
    DEFERRING = True
    started = now()
    log("=== toolchain run (%s) ===" % why)
    before = state.get("toolchain_attempt")
    state["toolchain_attempt"] = stamp(started)
    save_state(state)
    prior = dict((k, v) for k, v in (state.get("failed") or {}).items()
                 if k.startswith("tool:"))
    failed = dict(prior)
    done = yielded = False
    try:
        toolchain(failed)
        done = True
    except Yielded as exc:
        yielded = True
        log("yielded: %s; the toolchain phase stops here and runs on a later tick"
            % exc)
    except Stopped:
        log("off by owner: the run stops here, before its next step")
    except Exception as exc:                                 # noqa: BLE001
        prior["tool:brew-upgrade.py"] = repr(exc)[:300]
        log("! the toolchain phase stopped on %r" % exc)
    finally:
        DEFERRING = False
        if not done:
            failed = prior
        if yielded:
            unstamp(state, "toolchain_attempt", before)
        state["failed"] = failed
        if done and not failed:
            state["toolchain_success"] = stamp()
        save_state(state)
        log("=== toolchain %s (%d failed) ===" % ("dry run done" if DRY else "done",
                                                 len(failed)))
        notify(state)
    return 0


# ------------------------------------------------------------ the other job

DONE = re.compile(r"^\[(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d)\].*\bdone\b.*\(ok\)")
STARTED = re.compile(r"^\[(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d)\]\s*===\s+(?!dry\b)"
                     r"[^=]*\brun\b[^=]*===\s*$")


def unstamp(state, key, before):
    """Put `key` back to `before`, its value when the run began."""
    if before is None:
        state.pop(key, None)
    else:
        state[key] = before


def other_dirs(data):
    """The other job's working directory and its program's directories,
    from its plist's `data`."""
    dirs = []
    prog = data.get("ProgramArguments") or [data.get("Program") or ""]
    for v in [data.get("WorkingDirectory")] + list(prog if isinstance(prog, list) else []):
        if isinstance(v, str) and os.path.isabs(v):
            d = v if os.path.isdir(v) else os.path.dirname(v)
            if d not in dirs and d != "/":
                dirs.append(d)
    return dirs


def other_record(other):
    """(last success, last start) of the other upgrader, read from its own
    record and naming no vendor: a JSON holding `last_success` (and
    `last_attempt`) in its working directory's or program's
    directory or their `state/`, and the newest `=== done ... (ok) ===` and
    `=== ... run ... ===` lines of the log its plist names. A partial run is
    no success: that job itself counts only ok. Each the newer of the two;
    None when neither says."""
    data = read_plist(other[1]) or {}
    dirs = other_dirs(data)
    best, began = None, None
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "state", "*.json"))
                           + glob.glob(os.path.join(d, "*.json"))):
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict):
                continue
            when = parse_ts(doc.get("last_success"))
            if when and (best is None or when > best):
                best = when
            tried = parse_ts(doc.get("last_attempt"))
            if tried and (began is None or tried > began):
                began = tried
    for key in ("StandardOutPath", "StandardErrorPath"):
        path = data.get(key)
        if not isinstance(path, str):
            continue
        try:
            with open(path, "rb") as fh:
                fh.seek(max(0, os.path.getsize(path) - 524288))
                tail = fh.read().decode("utf-8", "replace").splitlines()
        except OSError:
            continue
        ok = start = None
        for line in reversed(tail):
            if ok is None:
                m = DONE.match(line)
                ok = parse_ts(m.group(1).replace(" ", "T")) if m else None
            if start is None:
                m = STARTED.match(line)
                start = parse_ts(m.group(1).replace(" ", "T")) if m else None
            if ok and start:
                break
        if ok and (best is None or ok > best):
            best = ok
        if start and (began is None or start > began):
            began = start
    return best, began


def its_turn(state, other, began, force):
    """Why defer mode's daily work waits for the other upgrader's, or None.
    It waits while that job is due (its last start MIN_INTERVAL_H or more
    old), and for WAIT_H at most, counted from the first tick that found it
    due in this stretch awake: an upgrader that does not start in that long
    is not coming. With no record of a start, nothing is waited for."""
    if force or began is None or hours_since(began) < MIN_INTERVAL_H:
        if state.pop("other_due_seen", None) is not None:
            save_state(state)
        return None
    seen = parse_ts(state.get("other_due_seen"))
    waited = hours_since(seen)
    if waited < 0 or waited > WAIT_RESET_H:
        state["other_due_seen"] = stamp()
        save_state(state)
        waited = 0.0
    if waited >= WAIT_H:
        return None
    return ("%s last started a run %s and is due; this job goes after it, or by "
            "%s if it does not start" % (
                other[0], stamp(began),
                (now() + timedelta(hours=WAIT_H - waited)).strftime("%H:%M")))


def defer_upkeep(state, role, other, force):
    """Defer mode's daily work, under own mode's gate: a brew upgrade when
    the other upgrader's last success is over COVER_H hours old or
    unknown (covering for it), else the toolchain phase alone; either waits
    for the other job's turn (its_turn). The cover's
    gate counts overdue from the newer of the two jobs' last runs, so a
    laptop is not upgraded outside the window while the other job's run is
    under OVERDUE_H hours old."""
    last, began = other_record(other)
    stale = last is None or hours_since(last) >= COVER_H
    cover = state.get("covered") if isinstance(state.get("covered"), dict) else None
    if cover and last and parse_ts(cover.get("at")) and last > parse_ts(cover["at"]):
        state.pop("covered", None)
        save_state(state)
    if DRY:
        log("%s %s: %s" % (
            other[0], "last succeeded %s" % stamp(last) if last
            else "has no success on any record found",
            "this job covers with its own brew upgrade" if stale
            else "brew is its; this job runs the toolchain phase"))
    if stale:
        view = dict(state)
        mine = parse_ts(state.get("last_success"))
        if last and (mine is None or last > mine):
            view["last_success"] = stamp(last)
        go, why = gated(view, role, force, "gate")
        if go and wait_turn(state, other, began, force):
            return 0
        if go:
            hold_awake()
            return own_run(state, role, "covering for %s, %s" % (other[0], why),
                           cover=(other, last))
    view = {"last_attempt": state.get("toolchain_attempt"),
            "last_success": state.get("toolchain_success"),
            "first_seen": state.get("first_seen")}
    go, why = gated(view, role, force, "toolchain gate")
    if not go or wait_turn(state, other, began, force):
        return 0
    hold_awake()
    return toolchain_run(state, role, why)


def wait_turn(state, other, began, force):
    """True when the day's work waits for the other job's turn (its_turn),
    logged; a dry run says so and goes."""
    why = its_turn(state, other, began, force)
    if why is None:
        return False
    log("%s: %s" % ("a real tick waits" if DRY else "waiting", why))
    return not DRY


def gated(state, role, force, label):
    """`gate`, except that --force goes; --dry-run says what the gate would
    do and goes."""
    if DRY:
        go, why = gate(state, role)
        log("%s: %s (%s)" % (label, "would run" if go else "would skip", why))
        return True, "dry run"
    if force:
        return True, "forced"
    return gate(state, role)


def own_run(state, role, why, cover=None):
    """One upgrade run. Saves state at the end whatever happened. `cover` is
    (other, its last success) when this run covers for another upgrader: a
    full upgrade of formulae and every cask that excludes nothing of that
    job's (its holds and the casks it protects upgrade too; only this job's
    own holds apply), each brew step first checks that no brew and not that
    job has started, and the state stays in defer mode with `covered` saying
    so."""
    global COVERING, DEFERRING
    COVERING = DEFERRING = bool(cover)
    trim_log()
    started = now()
    log("=== brew upgrade run (%s) ===" % why)
    before = (state.get("last_attempt"), state.get("toolchain_attempt"))
    prior = dict((k, v) for k, v in (state.get("failed") or {}).items()
                 if k.startswith("tool:"))
    state["last_attempt"] = stamp(started)
    state["toolchain_attempt"] = stamp(started)
    save_state(state)
    ok = True
    tools_done = False
    failed, held = {}, {}
    defers = dict(state.get("cask_defers") or {})
    found = []
    stopped = yielded = False
    try:
        clis_before = clis_missing()
        # 1. the index
        check_off(brew_step=True)
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
                if name in held:
                    continue
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
            check_off(brew_step=True)
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
                check_off(brew_step=True)
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
        check_off(brew_step=True)
        bf = probe_brewfile(True, True)
        if bf:
            ok = False
            found += bf

        # 7. brew's npm globals
        npm = os.path.join(PREFIX, "bin", "npm")
        check_off(brew_step=True)
        if os.path.exists(npm):
            code, out, err = run([npm, "update", "-g"], T_NPM, mutating=True,
                                 env=brew_env())
            if code != 0:
                failed["npm globals"] = last_line(err, out) or "exit %d" % code
                log("! npm update -g exited %d" % code)
                log_tail(out + "\n" + err, "npm", 8)

        # 8-12. the toolchain phase: update-tools, uv's Pythons, mise,
        # the descriptors, the pins
        toolchain(failed)
        tools_done = True

        # 13. repairs
        found += repairs(role, True, True, brewfile=False, clis_before=clis_before)

        # 14. cleanup, last
        check_off(brew_step=True)
        code, out, err = brew(["cleanup", "--prune=%d" % PRUNE_DAYS], T_CLEANUP,
                              mutating=True)
        if code != 0:
            log("! brew cleanup exited %d" % code)
            log_tail(out + "\n" + err, "cleanup", 3)
    except Yielded as exc:
        ok, stopped, yielded = False, True, True
        log("yielded: %s; the cover stops here, before its next brew step" % exc)
    except Stopped:
        ok, stopped = False, True
        log("off by owner: the run stops here, before its next step")
    except Exception as exc:                                 # noqa: BLE001
        ok = False
        failed["brew-upgrade.py"] = repr(exc)[:300]
        log("! the run stopped on %r" % exc)
    finally:
        COVERING = DEFERRING = False
        drop_lock()
        done = now()
        if not tools_done:
            # The phase did not finish: what it had found stands until it does.
            for k in [k for k in failed if k.startswith("tool:")]:
                del failed[k]
            failed.update(prior)
            if yielded:
                # Met the other job before its upgrade was done: a later tick
                # that day may cover, and run the toolchain phase, after it.
                unstamp(state, "last_attempt", before[0])
                unstamp(state, "toolchain_attempt", before[1])
        state["last_result"] = ("yielded" if yielded else "stopped" if stopped
                                else "ok" if ok else "partial")
        if ok:
            state["last_success"] = stamp(done)
        if tools_done and not [k for k in failed if k.startswith("tool:")]:
            state["toolchain_success"] = stamp(done)
        state["last_duration_seconds"] = int((done - started).total_seconds())
        state.update({"held": held, "failed": failed, "cask_defers": defers,
                      "mode": "defer" if cover else "own", "role": role,
                      "problems": found, "fingerprint": fingerprint(),
                      "probed_at": stamp(done)})
        if cover:
            state["deferred_to"] = {"label": cover[0][0], "path": cover[0][1]}
            if not yielded:
                state["covered"] = {"for": cover[0][0], "at": stamp(done),
                                    "other_success": stamp(cover[1]) if cover[1]
                                    else None}
        else:
            state.pop("deferred_to", None)
            state.pop("covered", None)
        save_state(state)
        log("=== %s in %ds (%s) ===" % ("dry run done" if DRY else "done",
                                       state["last_duration_seconds"],
                                       state["last_result"]))
        if cover and not yielded:
            log("covered for %s, whose last success was %s" % (
                cover[0][0], stamp(cover[1]) if cover[1] else "never recorded"))
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
    """Defer mode: probe and repair once brew's tree moves; upgrade nothing.
    A tool:<name> failure stays: the toolchain phase is this job's in either
    mode."""
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
    for k in ("held", "cask_defers"):
        state.pop(k, None)
    state["failed"] = dict((k, v) for k, v in (state.get("failed") or {}).items()
                           if k.startswith("tool:"))
    if not state["failed"]:
        state.pop("failed")
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
        if repair_only:
            return defer_tick(state, role, other, forced=True)
        if not state.get("first_seen"):
            state["first_seen"] = stamp()
        defer_tick(state, role, other)
        return defer_upkeep(state, role, other, force)
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
        print("%s loaded; defers to %s (repairs and the toolchain phase; a brew "
              "upgrade of its own when that job has not succeeded in %d hours)"
              % (LABEL, other[0], COVER_H))
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
        last, _ = other_record(other)
        print("its last:  %s%s" % (stamp(last) if last else "no record of a success",
                                   "" if last and hours_since(last) < COVER_H
                                   else "; this job covers its brew upgrade"))
    else:
        print("mode:      own")
    cover = state.get("covered") if isinstance(state.get("covered"), dict) else {}
    if other and cover.get("at"):
        print("covered:   %s, for %s (its last success %s)" % (
            cover["at"], cover.get("for"), cover.get("other_success") or "never recorded"))
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
    care = board_import("brewcare")
    tools = []
    if care is not None:
        try:
            doc = care.read_tools(os.path.dirname(STATE))
            skip = set(k[5:] for k in failed if k.startswith("tool:"))
            tools = care.tool_lines_of(doc, now(), skip=skip) if doc else []
        except Exception:                                    # noqa: BLE001
            tools = []
    for line in tools:
        print("TOOLS     %s" % line[len("tools: "):])
    return 1 if (held or failed or problems
                 or [l for l in tools if "pin behind" not in l]) else 0


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
