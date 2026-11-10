#!/usr/bin/python3
"""storage.py -- the daily storage tick.

    storage.py run [--dry-run] [--force]   reclaim allowlisted caches and old files
    storage.py status                      the last tick, or "no tick yet"

What it touches, and nothing else: Homebrew's download cache, npm's cache,
Go's build cache, pip's wheel cache, Xcode DerivedData older than two weeks,
unavailable simulators, `__pycache__` older than a week under registered
repos, and log files older than two weeks under upkeep's state, the setup
log directory and each repo's sessions.

Every target is checked to sit under $HOME and is never followed through a
symlink. A file newer than its threshold is left alone. The global off switch
(`upkeep off`) stops it, and so does a running upkeep tick. It never removes
an installed app, a package, a session, an upload or a document. Stdlib only;
runs under /usr/bin/python3 (3.9), as every upkeep program does.
"""

import json
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
STATE_DIR = os.environ.get("UPKEEP_STATE_DIR") or os.path.join(
    HOME, ".local", "state", "upkeep")
STATE = os.path.join(STATE_DIR, "storage.json")
LOG = os.path.join(STATE_DIR, "storage.log")
OFF = os.path.join(HOME, ".config", "upkeep", "off")
UPKEEP_LOCK = os.path.join(STATE_DIR, "upkeep.lock")
REPOS = os.path.join(HOME, ".config", "upkeep", "repos.json")

LOG_MAX = 1000000
MIN_INTERVAL_H = 20
LOG_DAYS = 14
CACHE_DAYS = 7
DERIVED_DAYS = 14
NOTIFY_BYTES = 250 * 1024 * 1024

DRY = False


# ------------------------------------------------------------------- basics

def stamp(when=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(when or time.time()))


def parse_ts(value):
    try:
        return time.mktime(time.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return None


def log(msg):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (stamp(), msg))
    except OSError:
        pass
    print(("would: " if DRY else "") + msg)


def trim_log():
    try:
        if os.path.getsize(LOG) <= LOG_MAX:
            return
        with open(LOG, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[-2000:]
        with open(LOG, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    except OSError:
        pass


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except OSError as exc:
        log("! could not write %s: %s" % (path, exc))


def human(n):
    n = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return "%.1f%s" % (n, unit)
        n /= 1024.0


# ------------------------------------------------------------------ targeting

def inside_home(path):
    try:
        real = os.path.realpath(path)
        home = os.path.realpath(HOME)
        return real == home or real.startswith(home + os.sep)
    except OSError:
        return False


def size_of(path):
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            p = os.path.join(root, name)
            try:
                if not os.path.islink(p):
                    total += os.path.getsize(p)
            except OSError:
                pass
    return total


def age_days(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 86400.0
    except OSError:
        return 0.0


def remove(path, why):
    """Remove one file or directory, guarded to $HOME and never a symlink.
    Returns bytes reclaimed."""
    if not os.path.lexists(path):
        return 0
    if not inside_home(path):
        log("! refused (outside home): %s" % path)
        return 0
    size = size_of(path)
    if not DRY:
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        except OSError as exc:
            log("! could not remove %s: %s" % (path, exc))
            return 0
    log("%s %s (%s)" % (why, path, human(size)))
    return size


def command(argv, timeout):
    if DRY:
        return 0
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 127
    if p.returncode:
        tail = p.stdout.decode("utf-8", "replace").strip().splitlines()[-1:]
        log("! %s exited %d%s" % (os.path.basename(argv[0]), p.returncode,
                                  (": " + tail[0]) if tail else ""))
    return p.returncode


def tool(name):
    return shutil.which(name)


def upkeep_busy():
    try:
        return time.time() - os.path.getmtime(UPKEEP_LOCK) < 7200
    except OSError:
        return False


def registered_repos():
    repos = read_json(REPOS)
    if not isinstance(repos, list):
        return []
    return [r for r in repos if isinstance(r, str) and os.path.isdir(r)]


# ------------------------------------------------------------------ cleanups

def clean_brew(freed):
    brew = tool("brew")
    cache = os.path.join(HOME, "Library", "Caches", "Homebrew")
    if not brew:
        return
    before = size_of(cache)
    command([brew, "cleanup", "--prune=all"], 3600)
    freed["brew"] = max(0, before - (0 if DRY else size_of(cache)))


def clean_npm(freed):
    npm = tool("npm")
    cache = os.path.join(HOME, ".npm", "_cacache")
    if not npm or not os.path.isdir(cache):
        return
    before = size_of(cache)
    command([npm, "cache", "clean", "--force"], 1800)
    after = 0 if DRY else size_of(cache)
    freed["npm"] = max(0, before - after)


def clean_go(freed):
    go = tool("go")
    cache = os.path.join(HOME, "Library", "Caches", "go-build")
    if not go or not os.path.isdir(cache):
        return
    before = size_of(cache)
    command([go, "clean", "-cache"], 1800)
    after = 0 if DRY else size_of(cache)
    freed["go"] = max(0, before - after)


def clean_pip(freed):
    pip = tool("pip3") or tool("pip")
    dirs = [os.path.join(HOME, "Library", "Caches", "pip"),
            os.path.join(HOME, ".cache", "pip")]
    if not pip or not any(os.path.isdir(d) for d in dirs):
        return
    before = sum(size_of(d) for d in dirs)
    command([pip, "cache", "purge"], 1800)
    after = 0 if DRY else sum(size_of(d) for d in dirs)
    freed["pip"] = max(0, before - after)


def clean_derived(freed):
    root = os.path.join(HOME, "Library", "Developer", "Xcode", "DerivedData")
    if not os.path.isdir(root):
        return
    total = 0
    try:
        names = os.listdir(root)
    except OSError:
        return
    for name in names:
        path = os.path.join(root, name)
        if age_days(path) > DERIVED_DAYS:
            total += remove(path, "removed old DerivedData")
    freed["xcode"] = total


def clean_simulators(_freed):
    xcrun = tool("xcrun")
    if not xcrun:
        return
    command([xcrun, "simctl", "delete", "unavailable"], 600)


def clean_pycache(freed):
    total = 0
    for repo in registered_repos():
        for dirpath, dirnames, _files in os.walk(repo, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules",
                                                            ".venv", "venv")]
            if "__pycache__" in dirnames:
                path = os.path.join(dirpath, "__pycache__")
                if age_days(path) > CACHE_DAYS:
                    total += remove(path, "removed old __pycache__")
                dirnames.remove("__pycache__")
    freed["pycache"] = total


def clean_logs(freed):
    total = 0
    candidates = []
    try:
        for name in os.listdir(STATE_DIR):
            if name.endswith(".log") and name != "storage.log":
                candidates.append(os.path.join(STATE_DIR, name))
    except OSError:
        pass
    setup = os.path.join(HOME, ".local", "state", "atlas-setup")
    try:
        for name in os.listdir(setup):
            if name.endswith(".log"):
                candidates.append(os.path.join(setup, name))
    except OSError:
        pass
    for repo in registered_repos():
        sessions = os.path.join(repo, "sessions")
        try:
            names = os.listdir(sessions)
        except OSError:
            continue
        for name in names:
            if name.startswith("."):
                continue
            candidates.append(os.path.join(sessions, name, "agent.log"))
    for path in candidates:
        if os.path.isfile(path) and not os.path.islink(path) \
                and age_days(path) > LOG_DAYS:
            total += remove(path, "removed old log")
    freed["logs"] = total


def notify(total):
    if DRY or total < NOTIFY_BYTES:
        return
    text = "Storage: reclaimed %s" % human(total)
    try:
        subprocess.run(["osascript", "-e",
                        'display notification "%s" with title "Storage"' % text],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass


# ------------------------------------------------------------------ commands

def cmd_run(force=False):
    if os.path.exists(OFF):
        log("off by owner: nothing done")
        return 0
    state = read_json(STATE)
    last = parse_ts(state.get("last_success"))
    if not force and last and (time.time() - last) < MIN_INTERVAL_H * 3600:
        return 0
    if upkeep_busy():
        log("upkeep tick is running: skipped")
        return 0

    trim_log()
    log("=== storage tick (%s) ===" % ("forced" if force else "scheduled"))
    freed = {}
    clean_brew(freed)
    clean_npm(freed)
    clean_go(freed)
    clean_pip(freed)
    clean_derived(freed)
    clean_simulators(freed)
    clean_pycache(freed)
    clean_logs(freed)
    total = sum(freed.values())

    state["last_attempt"] = stamp()
    state["last_success"] = stamp()
    state["freed_bytes"] = total
    state["freed"] = freed
    write_json(STATE, state)
    log("done: reclaimed %s" % human(total))
    notify(total)
    return 0


def cmd_status():
    state = read_json(STATE)
    if not state.get("last_attempt"):
        print("storage:   no tick yet")
        return 1
    parts = state.get("freed") if isinstance(state.get("freed"), dict) else {}
    print("storage:   %s at %s, reclaimed %s" % (
        "ok", state.get("last_success") or "?", human(state.get("freed_bytes") or 0)))
    for name, size in sorted(parts.items()):
        print("  %-8s %s" % (name, human(size or 0)))
    return 0


USAGE = "usage: storage.py run [--dry-run] [--force] | status"


def main(argv):
    global DRY
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, flags = argv[0], argv[1:]
    if cmd == "run":
        if any(f not in ("--dry-run", "--force") for f in flags):
            print(USAGE, file=sys.stderr)
            return 2
        DRY = "--dry-run" in flags
        return cmd_run(force="--force" in flags)
    if cmd == "status" and not flags:
        return cmd_status()
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
