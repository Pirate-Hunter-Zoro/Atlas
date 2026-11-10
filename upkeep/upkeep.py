#!/usr/bin/python3
"""upkeep.py -- install everything a clone's Mac needs, and keep it current.

    upkeep install --repo ROOT    register ROOT, copy upkeep in, load the agents
    upkeep run [--force] [--dry-run]
                                  the hourly tick; --force skips the gate
    upkeep opencode [--dry-run]   the opencode phase alone, for a repo's setup
    upkeep doctor                 the one-minute opencode tick
    upkeep status                 what the last run found; exit 1 on a problem
    upkeep off | on               stop or restart every run and doctor tick
    upkeep settle                 internal: reload the upkeep job once a run ends

Every repo that carries upkeep/ carries the same bytes. The installed copy is
~/.local/share/upkeep (copied, so deleting a repo breaks nothing); each run
first copies in the registered repo whose upkeep/VERSION is highest. README.md
beside this file lists the phases, files and rules. Stdlib only; runs under
/usr/bin/python3 (3.9), because a run upgrades brew's python.
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
import time
from datetime import datetime, timedelta

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.realpath(__file__))

LABEL = "com.mikeyferguson.upkeep"
DOCTOR_LABEL = "com.mikeyferguson.opencode-doctor"
LEGACY_BREW = "com.mikeyferguson.brewupgrade"
LEGACY_DOCTOR = "com.mikeyferguson.opencodedoctor"
RETIRED = ("atlas.brew-upgrade",)

MIN_INTERVAL_H = 20
WINDOW = range(3, 8)                 # 03:00-07:59 local
OVERDUE_H = 48
STALE_H = 72
MIN_BATTERY_PCT = 40
IDLE_MIN_S = 1200
CASK_DEFER_HOLD = 3
RECHECK_MIN = 50
LEGACY_LOCK_H = 6
LOG_MAX = 2000000
PRUNE_DAYS = 7

T_PROBE = 60
T_UPDATE = 1800
T_OUTDATED = 600
T_FORMULAE = 10800
T_CASK = 5400
T_BUNDLE = 3600
T_NPM = 1800
T_SDK = 3600
T_SIMULATOR = 3 * 3600
T_FLUTTER = 1800
T_HOOK_LIST = 300
T_HOOK_WORK = 7200
T_PARITY = 900
T_CLEANUP = 1800

NPM_PACKAGE = "opencode-ai"
STUB_MARK = "postinstall script was not run"
# OpenCode 2's package. OpenCode 1's upgrade prompt swaps it in for opencode-ai, and
# npm's allow-scripts leaves it npm's placeholder. These Macs stay on OpenCode 1.
NPM_SUCCESSORS = ("@opencode/cli",)
# While an opencode runs, a broken binary is repaired only once it has stayed
# broken this long, so the doctor never races an upgrade somebody is running.
BROKEN_GRACE = 300
CODER_TEMPLATE = ("#!/bin/bash\n"
                  "# 'coder' == opencode, with permissions auto-approved (--auto).\n"
                  "exec opencode --auto \"$@\"\n")
OPENCODE_SCHEMA = "https://opencode.ai/config.json"
MANAGED_BEGIN = "# >>> upkeep >>>"
MANAGED_END = "# <<< upkeep <<<"
TERMINAL_DOMAIN = "com.apple.Terminal"
FLUTTER_EXTENSION = "Dart-Code.flutter"

DRY = False
ECHO_INDENT = ""
_locks = {}


def configure(env=None):
    """Every path, from HOME and the overrides. Called at import and by tests."""
    global HOME, SHARE, CONFIG_DIR, STATE_DIR, STATE, DOCTOR_STATE, LOG, LOCK
    global DOCTOR_LOCK, OFF_FILE, REPOS, LINK, AGENTS_DIR, APPS, ROOT_STATUS
    global ZPROFILE, SDK, BROKEN_MARK
    env = os.environ if env is None else env
    HOME = env.get("HOME") or os.path.expanduser("~")
    SHARE = env.get("UPKEEP_HOME") or os.path.join(HOME, ".local", "share", "upkeep")
    CONFIG_DIR = os.path.join(HOME, ".config", "upkeep")
    STATE_DIR = env.get("UPKEEP_STATE_DIR") or os.path.join(HOME, ".local", "state",
                                                            "upkeep")
    STATE = os.path.join(STATE_DIR, "state.json")
    DOCTOR_STATE = os.path.join(STATE_DIR, "doctor.json")
    LOG = os.path.join(STATE_DIR, "upkeep.log")
    LOCK = os.path.join(STATE_DIR, "upkeep.lock")
    DOCTOR_LOCK = os.path.join(STATE_DIR, "doctor.lock")
    BROKEN_MARK = os.path.join(STATE_DIR, "opencode-broken")
    OFF_FILE = os.path.join(CONFIG_DIR, "off")
    REPOS = os.path.join(CONFIG_DIR, "repos.json")
    LINK = os.path.join(HOME, ".local", "bin", "upkeep")
    AGENTS_DIR = os.path.join(HOME, "Library", "LaunchAgents")
    APPS = env.get("UPKEEP_APPLICATIONS") or "/Applications"
    ROOT_STATUS = env.get("UPKEEP_ROOT_STATUS") or \
        "/Library/Application Support/upkeep-root/status.json"
    ZPROFILE = os.path.join(HOME, ".zprofile")
    SDK = os.path.join(HOME, "Library", "Android", "sdk")


configure()


# ------------------------------------------------------------------- basics

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


def tilde(path):
    return path.replace(HOME, "~", 1) if path.startswith(HOME) else path


def log(msg):
    """One stamped line in upkeep.log, echoed on a terminal. A dry run only
    echoes."""
    line = "[%s] %s" % (now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    if DRY or sys.stdout.isatty():
        print(ECHO_INDENT + (msg if DRY else line), flush=True)
    if DRY:
        return
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def log_tail(out, tag, n=12):
    for line in [l for l in (out or "").splitlines() if l.strip()][-n:]:
        log("    [%s] %s" % (tag, line))


def last_line(*outs):
    for out in outs:
        lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
        if lines:
            return lines[-1][:300]
    return ""


def trim_log():
    """Over LOG_MAX, keep the newer half: a job that runs for years must not
    fill the disk."""
    if DRY:
        return
    try:
        if os.path.getsize(LOG) <= LOG_MAX:
            return
        with open(LOG, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        with open(LOG + ".tmp", "w", encoding="utf-8") as fh:
            fh.writelines(lines[len(lines) // 2:])
        os.replace(LOG + ".tmp", LOG)
    except OSError:
        pass


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def write_text(path, text, mode=None):
    """Atomic: a crash leaves the old file or the new one, never half."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".upkeep-tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode is not None:
        os.chmod(tmp, mode)
    elif os.path.exists(path):
        os.chmod(tmp, os.stat(path).st_mode & 0o7777)
    os.replace(tmp, path)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data
    except (OSError, ValueError):
        return None


def write_json(path, data):
    write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_state():
    data = read_json(STATE)
    return data if isinstance(data, dict) else {}


def save_state(state):
    if DRY:
        return
    try:
        write_json(STATE, state)
    except OSError as exc:
        log("! could not write %s: %s" % (STATE, exc))


def version_of(upkeep_dir):
    try:
        with open(os.path.join(upkeep_dir, "VERSION"), encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return -1


# ------------------------------------------------------------------ running

def search_path():
    """The caller's PATH first, then brew's and the system's directories."""
    path = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]
    for d in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
              "/usr/sbin", "/sbin"):
        if d not in path:
            path.append(d)
    return os.pathsep.join(path)


def which(name):
    return shutil.which(name, path=search_path())


def run(argv, timeout, mutating=False, env=None, cwd=None, stdin_text=None):
    """(code, stdout, stderr). Never raises: a timeout is 124, a missing
    program 127. A mutating call under --dry-run is described, not run. No
    call has a terminal, so a sudo inside one fails at once."""
    argv = [str(a) for a in argv]
    if mutating and DRY:
        log("[dry-run] would run %s" % " ".join(argv))
        return 0, "", ""
    full = dict(os.environ)
    full["PATH"] = search_path()
    if env:
        full.update(env)
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           input=stdin_text,
                           stdin=None if stdin_text is not None else subprocess.DEVNULL,
                           universal_newlines=True, timeout=timeout, env=full,
                           cwd=cwd, start_new_session=True)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ds" % timeout
    except (OSError, ValueError) as exc:
        return 127, "", str(exc)


def brew_path():
    return which("brew")


def brew_prefix():
    """The prefix brew lives in (/opt/homebrew), read off its path unresolved:
    bin/brew is a link into Homebrew/."""
    b = brew_path()
    return os.path.dirname(os.path.dirname(b)) if b else None


def brew_env():
    return {"HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_INSTALL_CLEANUP": "1",
            "HOMEBREW_NO_ENV_HINTS": "1", "HOMEBREW_NO_ANALYTICS": "1",
            "HOMEBREW_NO_COLOR": "1"}


def brew(args, timeout, mutating=False):
    b = brew_path()
    if not b:
        return 127, "", "no brew"
    return run([b] + list(args), timeout, mutating=mutating, env=brew_env())


def npm_path():
    """brew's npm, beside brew; any npm when that one is missing."""
    prefix = brew_prefix()
    if prefix and os.path.exists(os.path.join(prefix, "bin", "npm")):
        return os.path.join(prefix, "bin", "npm")
    return which("npm")


# ------------------------------------------------------------------- locks

def take_lock(path):
    """flock, held for the process's life: the kernel drops it on exit."""
    if DRY:
        return True
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    os.ftruncate(fd, 0)
    os.write(fd, ("%d\n" % os.getpid()).encode())
    _locks[path] = fd
    return True


def drop_lock(path):
    fd = _locks.pop(path, None)
    if fd is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            pass


def lock_holder(path):
    """The pid holding the lock (0 when it wrote none), or None when free."""
    if path in _locks:
        return os.getpid()
    try:
        fd = os.open(path, os.O_RDONLY)
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
    """The owner ran `upkeep off` mid-run."""


def check_off():
    if not DRY and os.path.exists(OFF_FILE):
        raise Stopped()


# ------------------------------------------------------------------- JSONC

_PUNCT = "{}[]:,"


def _tokens(text):
    """[(kind, start, end)] of JSONC: 's' string, 'p' punctuation, 'l' a bare
    literal. Whitespace and // and /* */ comments are skipped."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n﻿":
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise ValueError("an unterminated comment at %d" % i)
            i = j + 2
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise ValueError("an unterminated string at %d" % i)
            out.append(("s", i, j + 1))
            i = j + 1
        elif c in _PUNCT:
            out.append(("p", i, i + 1))
            i += 1
        else:
            j = i
            while j < n and text[j] not in _PUNCT + ' \t\r\n"/':
                j += 1
            if j == i:
                raise ValueError("an unexpected %r at %d" % (c, i))
            out.append(("l", i, j))
            i = j
    return out


def jsonc_load(text):
    """JSONC (comments, trailing commas) to a value. Raises ValueError."""
    toks = _tokens(text)
    parts = []
    for k, (kind, a, b) in enumerate(toks):
        piece = text[a:b]
        if piece == "," and k + 1 < len(toks) and text[toks[k + 1][1]] in "}]":
            continue
        parts.append(piece)
    return json.loads(" ".join(parts))


def _members(text, toks):
    """[(key, value_start, value_end)] of the top-level object, plus the
    index of its closing brace token."""
    if not toks or text[toks[0][1]] != "{":
        raise ValueError("not an object")
    members, depth, k = [], 0, 0
    key = vstart = None
    last_end = None
    close = None
    while k < len(toks):
        kind, a, b = toks[k]
        ch = text[a] if kind == "p" else None
        if ch in ("{", "["):
            depth += 1
            if depth == 2 and vstart is None and key is not None:
                vstart = a
        elif ch in ("}", "]"):
            if depth == 1:
                if key is not None and vstart is not None:
                    members.append((key, vstart, last_end))
                close = k
                break
            depth -= 1
        elif depth == 1 and ch == ",":
            if key is not None and vstart is not None:
                members.append((key, vstart, last_end))
            key = vstart = None
        elif depth == 1 and ch == ":":
            pass
        elif depth == 1 and key is None and kind == "s":
            key = json.loads(text[a:b])
        elif depth == 1 and vstart is None and key is not None:
            vstart = a
        last_end = b
        k += 1
    if close is None:
        raise ValueError("an unclosed object")
    return members, close


def jsonc_set(text, key, value):
    """`text` with the top-level `key` set to `value`. Comments, order and
    every other key are kept; a missing key goes last, in the file's own
    indentation and comma style."""
    jsonc_load(text)
    toks = _tokens(text)
    members, close = _members(text, toks)
    new = json.dumps(value, ensure_ascii=False)
    hits = [m for m in members if m[0] == key]
    if hits:
        for _k, a, b in sorted(hits, key=lambda m: -m[1]):
            text = text[:a] + new + text[b:]
        return text
    indent = "  "
    if members:
        first = [t for t in toks if t[1] < members[0][1] and t[0] == "s"][-1]
        line_start = text.rfind("\n", 0, first[1]) + 1
        lead = text[line_start:first[1]]
        if line_start and not lead.strip():
            indent = lead
    member = "%s: %s" % (json.dumps(key, ensure_ascii=False), new)
    cpos = toks[close][1]
    prev = toks[close - 1]
    if text[prev[1]] == "{" and prev[0] == "p":
        return text[:cpos] + "\n" + indent + member + "\n" + text[cpos:]
    trailing = text[prev[1]:prev[2]] == ","
    nl = text.rfind("\n", prev[2], cpos)
    if nl < 0:
        return text[:cpos] + (" " if trailing else ", ") + member + text[cpos:]
    text = (text[:nl + 1] + indent + member + ("," if trailing else "") + "\n"
            + text[nl + 1:])
    if not trailing:
        text = text[:prev[2]] + "," + text[prev[2]:]
    return text


# ------------------------------------------------------------------- repos

def registered():
    """Every root in repos.json. One whose directory is gone is dropped from
    the file; one that exists stays, with or without upkeep/ right now (a
    checkout mid-switch is not a repo that left)."""
    data = read_json(REPOS)
    roots = [r for r in data if isinstance(r, str)] if isinstance(data, list) else []
    keep = [r for r in roots if os.path.isdir(r)]
    if keep != roots and not DRY:
        for gone in [r for r in roots if r not in keep]:
            log("dropped %s from the registry: it no longer exists" % gone)
        try:
            write_json(REPOS, keep)
        except OSError:
            pass
    return keep


def load_repos():
    """The registered repo roots that carry upkeep/ now."""
    return [r for r in registered()
            if os.path.isfile(os.path.join(r, "upkeep", "upkeep.py"))]


def register(root):
    roots = registered()
    if root not in roots:
        roots.append(root)
        write_json(REPOS, roots)


def copy_in(src):
    """Copy the upkeep/ at `src` over the installed copy, by a rename."""
    new, old = SHARE + ".new", SHARE + ".old"
    for d in (new, old):
        shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(src, new, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.dirname(SHARE), exist_ok=True)
    if os.path.exists(SHARE):
        os.rename(SHARE, old)
    os.rename(new, SHARE)
    shutil.rmtree(old, ignore_errors=True)
    for name in ("upkeep.py", "setup-mac.sh"):
        p = os.path.join(SHARE, name)
        if os.path.exists(p):
            os.chmod(p, 0o755)


def best_repo():
    """(version, upkeep dir) of the registered repo carrying the highest
    VERSION, or None."""
    found = [(version_of(os.path.join(r, "upkeep")), os.path.join(r, "upkeep"))
             for r in load_repos()]
    found = [f for f in found if f[0] >= 0]
    return max(found) if found else None


def self_update():
    """Copy in the highest registered VERSION when it beats the installed one.
    True when the installed copy changed."""
    best = best_repo()
    if not best or best[0] <= version_of(SHARE):
        return False
    if DRY:
        log("[dry-run] would copy upkeep %d in from %s" % best)
        return False
    copy_in(best[1])
    log("self-update: upkeep %d copied in from %s" % best)
    return True


def hook_path(root):
    p = os.path.join(root, "upkeep.d", "hook")
    return p if os.path.isfile(p) and os.access(p, os.X_OK) else None


def hook(root, phase, timeout):
    """(code, lines) of `upkeep.d/hook <phase>`; (0, []) with no hook."""
    p = hook_path(root)
    if not p:
        return 0, []
    env = {"UPKEEP_STATE_DIR": STATE_DIR, "UPKEEP_LOG": LOG,
           "UPKEEP_DRY_RUN": "1" if DRY else ""}
    code, out, err = run([p, phase], timeout, env=env, cwd=root)
    if code != 0:
        log("! %s %s exited %d" % (tilde(p), phase, code))
        log_tail(out + "\n" + err, "hook", 8)
    lines = [l.strip() for l in out.splitlines()
             if l.strip() and not l.strip().startswith("#")]
    return code, lines


def protected_casks(r, state):
    """(names, known) the registered repos' hooks protect. Fails closed: a
    repo whose hook gives no answer (not executable, a crash, a timeout, gone
    after it named casks) keeps the list it gave last time, recorded in
    state["protected_by"]; with nothing on record `known` is False, and no
    cask upgrades this run. A repo that never had a hook protects nothing."""
    record = state.get("protected_by")
    record = dict(record) if isinstance(record, dict) else {}
    roots = registered()
    record = dict((k, v) for k, v in record.items() if k in roots)
    names, known = set(), True
    for root in roots:
        name = os.path.basename(root.rstrip("/"))
        if hook_path(root):
            code, lines = hook(root, "protected-casks", T_HOOK_LIST)
            if code == 0:
                record[root] = sorted(set(lines))
                names.update(lines)
                continue
            why = "upkeep.d/hook protected-casks exited %d" % code
        elif not os.path.lexists(os.path.join(root, "upkeep.d", "hook")) \
                and not record.get(root):
            record[root] = []
            continue
        else:
            why = "upkeep.d/hook is missing or not executable"
        step = "hook %s protected-casks" % name
        if isinstance(record.get(root), list):
            names.update(record[root])
            r.fail(step, "%s; the casks it named last time stay put (%s)"
                   % (why, ", ".join(record[root]) or "none"))
        else:
            known = False
            r.fail(step, "%s, and it has never named its protected casks; no cask "
                   "upgrades until it does" % why)
    state["protected_by"] = record
    return names, known


# ------------------------------------------------------------ launchctl

def domain():
    return "gui/%d" % os.getuid()


def launchctl_print(label):
    return run(["launchctl", "print", "%s/%s" % (domain(), label)], T_PROBE)


def loaded(label):
    return launchctl_print(label)[0] == 0


def templates():
    """[(label, template path)] of every LaunchAgent this copy loads: launchd/
    and the parity layer's (opencode/launchd/, or opencode/ itself)."""
    out = []
    for d in (os.path.join(SHARE, "launchd"), os.path.join(SHARE, "opencode", "launchd"),
              os.path.join(SHARE, "opencode")):
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            if name.endswith(".plist"):
                out.append((name[:-6], os.path.join(d, name)))
    return out


def render(template):
    with open(template, "rb") as fh:
        data = plistlib.load(fh)
    prefix = brew_prefix() or "/opt/homebrew"
    subs = {"@HOME@": HOME, "@UPKEEP@": SHARE, "@PREFIX@": prefix,
            "@PATH@": ":".join([os.path.join(HOME, ".local", "bin"),
                                os.path.join(prefix, "bin"), "/usr/local/bin",
                                "/usr/bin", "/bin", "/usr/sbin", "/sbin"])}

    def sub(v):
        if isinstance(v, str):
            for k, x in subs.items():
                v = v.replace(k, x)
            return v
        if isinstance(v, list):
            return [sub(x) for x in v]
        if isinstance(v, dict):
            return dict((k, sub(x)) for k, x in v.items())
        return v
    return plistlib.dumps(sub(data))


def reload_job(label, path):
    run(["launchctl", "bootout", "%s/%s" % (domain(), label)], T_PROBE)
    if not os.path.exists(path):
        return 0, ""
    code, out, err = run(["launchctl", "bootstrap", domain(), path], T_PROBE)
    return code, last_line(err, out) or str(code)


def inside_job():
    return os.environ.get("XPC_SERVICE_NAME") == LABEL


def spawn_settle():
    """`settle` detached, so this run ending and the job's bootout leave it."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as out:
            subprocess.Popen([sys.executable, os.path.join(SHARE, "upkeep.py"), "settle"],
                             stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                             start_new_session=True, close_fds=True)
        return True
    except OSError as exc:
        log("! could not start settle: %s" % exc)
        return False


def ensure_agents(force_load=False):
    """Render every template; write and reload only what changed or is not
    loaded. The upkeep job itself, mid-run, reloads once the run ends; the
    doctor while its tick holds its lock waits for the next run. Lines said."""
    said = []
    if DRY:
        return said
    os.makedirs(AGENTS_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)     # launchd logs there, makes no dir
    for label, template in templates():
        dest = os.path.join(AGENTS_DIR, label + ".plist")
        try:
            body = render(template)
        except Exception as exc:                             # noqa: BLE001
            said.append("! could not render %s: %s" % (template, exc))
            continue
        try:
            with open(dest, "rb") as fh:
                changed = fh.read() != body
        except OSError:
            changed = True
        if changed:
            with open(dest + ".tmp", "wb") as fh:
                fh.write(body)
            os.replace(dest + ".tmp", dest)
        if not changed and not force_load and loaded(label):
            continue
        if label == LABEL and (inside_job() or lock_holder(LOCK) is not None):
            spawn_settle()
            said.append("%s: reloads once this run ends" % label)
            continue
        if label == DOCTOR_LABEL and lock_holder(DOCTOR_LOCK) is not None:
            said.append("%s: a tick is under way; the next run reloads it" % label)
            continue
        if not changed and loaded(label):
            continue
        code, why = reload_job(label, dest)
        said.append("%s: %s" % (label, "loaded" if code == 0
                                else "launchctl bootstrap failed: %s" % why))
    return said


def retire():
    """Boot out and remove the retired jobs' plists."""
    said = []
    for label in RETIRED:
        path = os.path.join(AGENTS_DIR, label + ".plist")
        if not os.path.exists(path) and not loaded(label):
            continue
        if DRY:
            log("[dry-run] would retire %s" % label)
            continue
        run(["launchctl", "bootout", "%s/%s" % (domain(), label)], T_PROBE)
        try:
            os.remove(path)
        except OSError:
            pass
        said.append("%s retired: booted out, its plist removed" % label)
        log(said[-1])
    return said


def shell_block():
    upkeep_sh = os.path.join(SHARE, "opencode", "shell.zsh")
    jbr = os.path.join(APPS, "Android Studio.app", "Contents", "jbr", "Contents", "Home")
    return "\n".join([
        MANAGED_BEGIN,
        "# Written by upkeep install; edits between these lines are replaced.",
        'export JAVA_HOME="%s"' % jbr,
        'export ANDROID_HOME="$HOME/Library/Android/sdk"',
        'export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:'
        '$ANDROID_HOME/emulator:$PATH"',
        'export PATH="$HOME/bin:$PATH"',
        '[ -f "%s" ] && source "%s"' % (upkeep_sh.replace(HOME, "$HOME", 1),
                                        upkeep_sh.replace(HOME, "$HOME", 1)),
        MANAGED_END]) + "\n"


def ensure_shell_block():
    """The managed block in ~/.zprofile, replaced between its markers only.
    True when the file changed."""
    text = read_text(ZPROFILE)
    text = "" if text is None else text
    block = shell_block()
    a, b = text.find(MANAGED_BEGIN), text.find(MANAGED_END)
    if a >= 0 and b > a:
        end = b + len(MANAGED_END)
        if text[end:end + 1] == "\n":
            end += 1
        new = text[:a] + block + text[end:]
    else:
        new = text + ("\n" if text and not text.endswith("\n") else "") + block
    if new == text or DRY:
        return False
    write_text(ZPROFILE, new)
    return True


# ---------------------------------------------------------------- legacy

def legacy_dir(label, said):
    """The legacy job's WorkingDirectory, from `launchctl print`, else from
    its plist."""
    m = re.search(r"^\s*working directory = (.+?)\s*$", said, re.M)
    if m:
        return m.group(1)
    try:
        with open(os.path.join(AGENTS_DIR, label + ".plist"), "rb") as fh:
            return str(plistlib.load(fh).get("WorkingDirectory") or "") or None
    except Exception:                                        # noqa: BLE001
        return None


def legacy_brew():
    """None when the legacy brew job is not loaded, else {label, dir,
    last_success, lock_fresh}."""
    code, out, _ = launchctl_print(LEGACY_BREW)
    if code != 0:
        return None
    wd = legacy_dir(LEGACY_BREW, out)
    rec = {"label": LEGACY_BREW, "dir": wd, "last_success": None, "lock_fresh": False}
    if wd:
        data = read_json(os.path.join(wd, "state", "brew_upgrade.json"))
        if isinstance(data, dict):
            rec["last_success"] = data.get("last_success")
        try:
            age = time.time() - os.path.getmtime(os.path.join(wd, "state",
                                                              "brew_upgrade.lock"))
            rec["lock_fresh"] = age < LEGACY_LOCK_H * 3600
        except OSError:
            pass
    return rec


def brew_running():
    code, out, _ = run(["pgrep", "-f", r"/Library/Homebrew/brew\.(rb|sh)"], T_PROBE)
    return code == 0 and bool(out.strip())


def legacy_skip(legacy):
    """Why phases 2-4 are left to the legacy job this run, or None. --force
    changes nothing here: the legacy job knows casks upkeep does not (MO's
    protected ones), so a forced run never upgrades beside it."""
    if not legacy:
        return None
    if legacy["lock_fresh"]:
        return "%s holds its lock" % LEGACY_BREW
    if brew_running():
        return "a brew is running"
    last = parse_ts(legacy.get("last_success"))
    if hours_since(last) < MIN_INTERVAL_H:
        return "%s succeeded at %s" % (LEGACY_BREW, legacy["last_success"])
    return None


# ------------------------------------------------------------------ gate

def battery():
    """(has_battery, on_ac, percent or None)."""
    code, out, _ = run(["pmset", "-g", "batt"], T_PROBE)
    if code != 0:
        return False, True, None
    has = "InternalBattery" in out
    m = re.search(r"(\d+)%", out)
    return has, "Battery Power" not in out, (int(m.group(1)) if m and has else None)


def idle_seconds():
    code, out, _ = run(["ioreg", "-c", "IOHIDSystem"], T_PROBE)
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out) if code == 0 else None
    return int(m.group(1)) / 1e9 if m else None


def network_ok():
    return run(["curl", "-sfI", "--max-time", "10", "https://formulae.brew.sh/"],
               30)[0] == 0


def gate(state):
    """(go, why). A refusal stamps nothing, so the next hour asks again."""
    since = hours_since(parse_ts(state.get("last_attempt")))
    if since < MIN_INTERVAL_H:
        return False, "attempted %.1fh ago (every %dh)" % (since, MIN_INTERVAL_H)
    base = parse_ts(state.get("last_success")) or parse_ts(state.get("first_seen"))
    overdue = hours_since(base) >= OVERDUE_H
    has, ac, pct = battery()
    if now().hour not in WINDOW:
        if not has:
            return False, "outside 03:00-07:59 (a Mac with no battery runs only then)"
        if not overdue:
            return False, "outside 03:00-07:59 and not overdue"
        if not ac:
            return False, "overdue, but on battery"
        idle = idle_seconds()
        if idle is None or idle < IDLE_MIN_S:
            return False, "overdue, but in use"
    if not ac and pct is not None and pct < MIN_BATTERY_PCT:
        return False, "on battery at %d%% (need %d%%)" % (pct, MIN_BATTERY_PCT)
    if not network_ok():
        return False, "formulae.brew.sh unreachable"
    return True, ("overdue" if overdue else "due") + (", on AC" if ac else
                                                      ", on battery at %s%%" % pct)


def hold_awake():
    if DRY:
        return
    c = which("caffeinate")
    if c:
        try:
            subprocess.Popen([c, "-i", "-s", "-w", str(os.getpid())],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


# -------------------------------------------------------------- the run

class Run(object):
    """What one run (or one recheck) found."""

    def __init__(self, report_only=False):
        self.report_only = report_only
        self.failed = {}
        self.held = {}
        self.protected = {}
        self.problems = []
        self.hooks = {}
        self.phases = {}
        self.changes = []

    def problem(self, line):
        if line not in self.problems:
            self.problems.append(line)
            log("problem: %s" % line)

    def fail(self, step, why):
        self.failed[step] = why or "failed"
        log("! %s: %s" % (step, why))


def phase(r, name, fn, *args):
    """Run one phase; a failure is recorded and the run goes on."""
    check_off()
    try:
        fn(r, *args)
        r.phases.setdefault(name, "ok")
    except Stopped:
        raise
    except Exception as exc:                                 # noqa: BLE001
        r.phases[name] = "failed: %r" % exc
        r.fail(name, repr(exc)[:300])


def outdated(args=()):
    """brew's outdated JSON. A query that names formulae or casks exits 1
    when any of them is outdated -- Homebrew sets its failure flag for named
    arguments -- so a parseable answer is the answer, whatever the exit code."""
    code, out, err = brew(["outdated", "--json=v2"] + list(args), T_OUTDATED)
    try:
        data = json.loads(out)
    except (ValueError, AttributeError) as exc:
        if code != 0:
            return [], [], "exit %d: %s" % (code, last_line(err, out))
        return [], [], "unparseable: %s" % exc
    if not isinstance(data, dict):
        return [], [], "unparseable: not an object"
    formulae = data.get("formulae") or []
    casks = data.get("casks") or []
    if not isinstance(formulae, list) or not isinstance(casks, list):
        return [], [], "unparseable: formulae or casks is not a list"
    return ([f for f in formulae if isinstance(f, dict) and f.get("name")],
            [c for c in casks if isinstance(c, dict) and c.get("name")], None)


def versions(rec):
    inst = rec.get("installed_versions") or [""]
    return (str(inst[-1] if isinstance(inst, list) and inst else inst),
            str(rec.get("current_version") or ""))


def cask_info(names):
    if not names:
        return []
    code, out, _ = brew(["info", "--cask", "--json=v2"] + list(names), T_OUTDATED)
    if code != 0:
        return []
    try:
        return [c for c in json.loads(out).get("casks") or [] if isinstance(c, dict)]
    except (ValueError, AttributeError):
        return []


def cask_apps(names):
    """{cask: [app name without .app]}."""
    apps = {}
    for c in cask_info(names):
        got = []
        for art in c.get("artifacts") or []:
            if not isinstance(art, dict) or "app" not in art:
                continue
            for item in art["app"]:
                if isinstance(item, str):
                    got.append(item)
                elif isinstance(item, dict) and item.get("target") and got:
                    got[-1] = os.path.basename(str(item["target"]))
        apps[c.get("token") or c.get("name")] = [g[:-4] if g.endswith(".app") else g
                                                for g in got]
    return apps


def app_running(app):
    code, out, _ = run(["pgrep", "-f", "/Applications/%s\\.app/Contents/MacOS/"
                        % re.escape(app)], T_PROBE)
    return code == 0 and bool(out.strip())


def greedy_casks():
    text = read_text(os.path.join(HERE, "greedy-casks")) or ""
    return [l.split("#")[0].strip() for l in text.splitlines()
            if l.split("#")[0].strip()]


def installed_casks():
    code, out, _ = brew(["list", "--cask", "-1"], T_OUTDATED)
    return set(l.strip() for l in out.splitlines() if l.strip()) if code == 0 else set()


def phase_brew(r, state):
    """brew update, then formulae and casks, never greedy except greedy-casks."""
    if DRY:
        log("index not refreshed (dry-run)")
    else:
        code, out, err = brew(["update"], T_UPDATE, mutating=True)
        if code != 0:
            r.fail("brew update", last_line(err, out) or "exit %d" % code)
    formulae, casks, bad = outdated()
    if bad:
        r.fail("brew outdated", bad)
        return
    greedy = [c for c in greedy_casks() if c in installed_casks()]
    gcasks = []
    if greedy:
        _f, gcasks, gbad = outdated(["--cask", "--greedy-auto-updates"] + greedy)
        if gbad:
            r.fail("brew outdated (greedy casks)", gbad)
            gcasks = []
        names = set(c["name"] for c in casks)
        gcasks = [c for c in gcasks if c["name"] not in names]
    protected, known = protected_casks(r, state)
    defers = dict(state.get("cask_defers") or {})
    every = set(c["name"] for c in casks + gcasks)
    defers = dict((k, v) for k, v in defers.items() if k in every)
    for f in formulae:
        inst, latest = versions(f)
        if f.get("pinned"):
            r.held[f["name"]] = {"installed": inst, "latest": latest,
                                 "why": "pinned; brew unpin %s to let it move" % f["name"]}
        elif f["name"] in protected:
            r.protected[f["name"]] = {"installed": inst, "latest": latest}
    apps = cask_apps(sorted(every))
    plain, greedy_run = [], []
    for c in casks + gcasks:
        name = c["name"]
        inst, latest = versions(c)
        if name in protected or not known:
            r.protected[name] = {"installed": inst, "latest": latest}
            continue
        running = [a for a in apps.get(name, []) if app_running(a)]
        if running:
            defers[name] = int(defers.get(name) or 0) + 1
            if defers[name] >= CASK_DEFER_HOLD:
                r.held[name] = {"installed": inst, "latest": latest,
                                "why": "%s.app was running at every upgrade; quit it, "
                                       "then upkeep run --force" % running[0]}
            else:
                log("%s.app is running; cask %s waits (%d of %d)"
                    % (running[0], name, defers[name], CASK_DEFER_HOLD))
            continue
        (greedy_run if c in gcasks else plain).append(name)
    names = sorted(f["name"] for f in formulae
                   if f["name"] not in r.held and f["name"] not in r.protected)
    log("outdated: %d formula(e), %d cask(s), %d held, %d left to a repo's hook"
        % (len(formulae), len(casks) + len(gcasks), len(r.held), len(r.protected)))
    if names:
        check_off()
        log("upgrading formulae: %s" % ", ".join(names))
        code, out, err = brew(["upgrade", "--formula"] + names, T_FORMULAE, mutating=True)
        log_tail(out + "\n" + err, "brew")
        if code != 0:
            r.fail("formulae", last_line(err, out) or "exit %d" % code)
    for name in sorted(plain) + sorted(greedy_run):
        check_off()
        args = ["upgrade", "--cask"] + (["--greedy-auto-updates"]
                                        if name in greedy_run else []) + [name]
        code, out, err = brew(args, T_CASK, mutating=True)
        if code == 0:
            defers.pop(name, None)
            log("upgraded cask %s" % name)
        else:
            r.fail("cask " + name, last_line(err, out) or "exit %d" % code)
            log_tail(out + "\n" + err, "cask " + name, 8)
    state["cask_defers"] = defers


# A Brewfile is Ruby that `brew bundle` runs, and an option such as
# postinstall: runs a shell command. So a line joins the union only as a bare
# `tap "x"`, `brew "x"` or `cask "x"`, written again from its kind and name.
# The registered repos' Brewfiles use no options, so none is allowed.
BREWFILE_LINE = re.compile(r'(tap|brew|cask)[ \t]+"([^"]*)"', re.ASCII)
# A formula or cask name, and each part of a tap's owner/repo.
BREW_NAME = re.compile(r"[a-z0-9][a-z0-9+._@-]*", re.ASCII)


def brewfile_entry(kind, name, taps):
    """Is `name` a `kind` entry? A tap is owner/repo. A formula or cask is a
    BREW_NAME, or owner/repo/<name> for a tap in `taps`."""
    parts = name.split("/")
    if not all(BREW_NAME.fullmatch(p) for p in parts):
        return False
    if kind == "tap":
        return len(parts) == 2
    return len(parts) == 1 or (len(parts) == 3 and "/".join(parts[:2]) in taps)


def brewfile_groups():
    """[[path]]: upkeep's own Brewfile, then each registered repo's Brewfiles
    (its hook's `brewfiles`)."""
    groups = [[os.path.join(HERE, "Brewfile")]]
    for root in load_repos():
        code, lines = hook(root, "brewfiles", T_HOOK_LIST)
        if code == 0 and lines:
            groups.append(lines)
    return groups


def union_text():
    """The upkeep Brewfile joined with every repo's, taps first, one line per
    entry, comments dropped. Each entry is rebuilt from a BREWFILE_LINE that
    passes brewfile_entry, where a tapped name needs a `tap` line from the
    same repo. Any other line is left out and logged, never run."""
    seen, taps, rest = set(), [], []
    for group in brewfile_groups():
        lines = []
        for path in group:
            for raw in (read_text(path) or "").split("\n"):
                line = raw.split("#")[0].strip(" \t\r")
                if line:
                    lines.append((path, line, BREWFILE_LINE.fullmatch(line)))
        tapped = set(m.group(2) for _, _, m in lines
                     if m and m.group(1) == "tap" and brewfile_entry("tap", m.group(2), ()))
        for path, line, m in lines:
            if not m or not brewfile_entry(m.group(1), m.group(2), tapped):
                log("! %s: left out a line that is not a bare tap, brew or cask: %s"
                    % (tilde(path), line[:120].encode("ascii", "backslashreplace")
                       .decode("ascii")))
                continue
            key = (m.group(1), m.group(2))
            if key in seen:
                continue
            seen.add(key)
            (taps if key[0] == "tap" else rest).append('%s "%s"' % key)
    return "# Written by upkeep: the union of every registered Brewfile.\n" + \
        "\n".join(taps + rest) + "\n"


def unmanaged(text):
    """({cask: [font files]}, {cask: app path}) for each cask in the union
    not yet installed whose files are already there by hand: font files in
    ~/Library/Fonts (moved aside, then the cask installed with --force), and
    apps in /Applications (left alone, and left out of the bundle, which
    would fail on them every run)."""
    want = re.findall(r'^cask "([^"]+)"', text, re.M)
    if not want:
        return {}, {}
    have = installed_casks()
    fonts_dir = os.path.join(HOME, "Library", "Fonts")
    fonts, apps = {}, {}
    for c in cask_info([w for w in want if w not in have]):
        token = c.get("token")
        for art in c.get("artifacts") or []:
            if not isinstance(art, dict):
                continue
            if "font" in art and token.startswith("font-"):
                src = art["font"][0] if art["font"] else ""
                name = os.path.basename(str(art.get("target") or src))
                path = os.path.join(fonts_dir, name)
                if name and os.path.isfile(path) and not os.path.islink(path):
                    fonts.setdefault(token, []).append(path)
            if "app" in art:
                for item in art["app"]:
                    name = os.path.basename(str(item.get("target") if isinstance(item, dict)
                                                else item) or "")
                    if name.endswith(".app") and os.path.exists(os.path.join(APPS, name)):
                        apps[token] = os.path.join(APPS, name)
    return fonts, apps


def phase_bundle(r):
    text = union_text()
    fonts, apps = unmanaged(text)
    for cask, app in sorted(apps.items()):
        log("cask %s: %s is there, installed by hand; brew bundle leaves it" % (cask, app))
        text = re.sub(r'^cask "%s".*\n' % re.escape(cask), "", text, flags=re.M)
    union = os.path.join(STATE_DIR, "Brewfile.all")
    if not DRY and read_text(union) != text:
        write_text(union, text)
    target = union
    if DRY:
        target = os.path.join(STATE_DIR, "Brewfile.dry")
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
    try:
        code, out, err = brew(["bundle", "check", "--no-upgrade", "--file=" + target],
                              T_BUNDLE)
        if code == 0:
            log("Brewfile: satisfied")
            return
        if r.report_only:
            r.problem("the Brewfile is not satisfied (%s); upkeep run --force"
                      % (last_line(out, err) or "a miss"))
            return
        for cask, files in sorted(fonts.items()):
            aside = os.path.join(HOME, "Library", "Fonts", ".before-upkeep")
            moved = []
            for f in files:
                if DRY:
                    log("[dry-run] would move %s to %s" % (tilde(f), tilde(aside)))
                    continue
                os.makedirs(aside, exist_ok=True)
                shutil.move(f, os.path.join(aside, os.path.basename(f)))
                moved.append(f)
                log("moved hand-copied %s aside for cask %s" % (tilde(f), cask))
            code, out, err = brew(["install", "--cask", "--force", cask], T_CASK,
                                  mutating=True)
            if code != 0:
                r.fail("cask " + cask, last_line(err, out) or "exit %d" % code)
                # The faces stay usable until a later run installs the cask.
                for f in moved:
                    if not os.path.exists(f):
                        shutil.move(os.path.join(aside, os.path.basename(f)), f)
                        log("put hand-copied %s back: cask %s did not install"
                            % (tilde(f), cask))
        check_off()
        code, out, err = brew(["bundle", "install", "--no-upgrade", "--file=" + target],
                              T_BUNDLE, mutating=True)
        log_tail(out + "\n" + err, "bundle", 8)
        if code != 0:
            r.fail("brew bundle", last_line(err, out) or "exit %d" % code)
    finally:
        if DRY:
            try:
                os.remove(target)
            except OSError:
                pass


def phase_npm(r):
    npm = npm_path()
    if not npm:
        r.problem("no npm (brew install node)")
        return
    ensure_npm_allow_scripts()
    code, out, err = run([npm, "update", "-g"], T_NPM, mutating=True, env=brew_env())
    if code != 0:
        r.fail("npm globals", last_line(err, out) or "exit %d" % code)
        log_tail(out + "\n" + err, "npm", 8)


# ------------------------------------------------------------ opencode doctor

def opencode_bin():
    prefix = brew_prefix() or "/opt/homebrew"
    return os.path.join(prefix, "bin", "opencode")


def opencode_pkg():
    prefix = brew_prefix() or "/opt/homebrew"
    return os.path.join(prefix, "lib", "node_modules", NPM_PACKAGE)


def opencode_running():
    """An opencode process is alive, matched by `ps` command name."""
    code, out, _ = run(["ps", "-axo", "comm="], 10)
    return code == 0 and any(os.path.basename(l.strip()) == "opencode"
                             for l in out.splitlines())


def is_placeholder():
    try:
        with open(os.path.realpath(opencode_bin()), "rb") as fh:
            return STUB_MARK.encode() in fh.read(4096)
    except OSError:
        return False


def foreign_owner():
    """The global npm package, other than opencode-ai, that `opencode` links
    into (OpenCode 2's, after its upgrade prompt), or ''."""
    real = os.path.realpath(opencode_bin())
    marker = os.sep + "node_modules" + os.sep
    if marker not in real or real.startswith(opencode_pkg() + os.sep):
        return ""
    parts = real.split(marker, 1)[1].split(os.sep)
    return "/".join(parts[:2]) if parts[0].startswith("@") else parts[0]


def binary_state():
    """(works, why not). OpenCode 2 counts as broken: these Macs run 1."""
    exe = opencode_bin()
    if not os.path.exists(exe):
        return False, "no binary"
    owner = foreign_owner()
    if owner:
        return False, "opencode links into %s, not %s" % (owner, NPM_PACKAGE)
    code, out, err = run([exe, "--version"], 30)
    if code == 0 and out.strip():
        return True, ""
    if is_placeholder():
        return False, "npm's placeholder: %s" % STUB_MARK
    if code == 124:
        return False, "--version hung past 30 s"
    said = " ".join((out + " " + err).split())
    return False, "exit %d: %s" % (code, said[:160] or "no output")


def run_postinstall():
    post = os.path.join(opencode_pkg(), "postinstall.mjs")
    if not os.path.exists(post):
        return False
    code, _, err = run(["node", post], 600, mutating=True, cwd=opencode_pkg())
    log("  ran postinstall.mjs -> exit %d" % code)
    return code == 0


def broken_for():
    """Seconds the binary has been seen broken while an opencode ran. The
    first sighting starts the clock in BROKEN_MARK."""
    try:
        return time.time() - os.stat(BROKEN_MARK).st_mtime
    except OSError:
        if not DRY:
            write_text(BROKEN_MARK, stamp() + "\n")
        return 0


def clear_broken():
    try:
        os.remove(BROKEN_MARK)
    except OSError:
        pass


def reinstall():
    npm = npm_path()
    for args in (["config", "set", "ignore-scripts", "false"],
                 ["uninstall", "-g"] + list(NPM_SUCCESSORS),
                 ["uninstall", "-g", NPM_PACKAGE],
                 ["cache", "clean", "--force"],
                 ["install", "-g", NPM_PACKAGE, "--foreground-scripts",
                  "--allow-scripts=" + NPM_PACKAGE]):
        code, _, err = run([npm] + args, 900, mutating=True)
        log("  $ npm %s -> exit %d" % (" ".join(args), code))
        if code == 127:
            log("  ! could not run npm: %s" % err)
            return
    run_postinstall()


def ensure_npm_allow_scripts():
    """npm's user allow-scripts names opencode-ai, keeping every other entry,
    so an npm update keeps the real binary rather than the placeholder."""
    npm = npm_path()
    if not npm:
        return False
    code, out, _ = run([npm, "config", "get", "allow-scripts", "--location=user"], 60)
    current = out.strip()
    if code != 0 or current == "undefined":
        return False
    names = [n.strip() for n in current.split(",") if n.strip() and n.strip() != "null"]
    if any(n in (NPM_PACKAGE, NPM_PACKAGE + "@", NPM_PACKAGE + "@*") for n in names):
        return False
    names.append(NPM_PACKAGE)
    code, _, _ = run([npm, "config", "set", "allow-scripts=" + ",".join(names),
                      "--location=user"], 60, mutating=True)
    if code != 0:
        log("  ! npm config set allow-scripts -> exit %d" % code)
        return False
    log("  repaired npm allow-scripts (now %s): an npm update keeps the opencode "
        "binary" % ",".join(names))
    return True


def coder_template():
    for d in (os.path.join(SHARE, "opencode"), os.path.join(HERE, "opencode")):
        text = read_text(os.path.join(d, "coder"))
        if text:
            return text, True
    return CODER_TEMPLATE, False


def ensure_coder():
    """~/bin/coder is upkeep/opencode/coder, byte for byte (or, with no
    parity layer, a wrapper that execs opencode --auto)."""
    path = os.path.join(HOME, "bin", "coder")
    want, exact = coder_template()
    current = read_text(path) or ""
    ok = current == want if exact else "exec opencode --auto" in current
    if not ok:
        if DRY:
            log("[dry-run] would rewrite ~/bin/coder")
            would_write(path)
            return True
        write_text(path, want, 0o755)
        log("  repaired ~/bin/coder")
        return True
    if not os.access(path, os.X_OK) and not DRY:
        os.chmod(path, 0o755)
    return False


def remove_stale_aliases():
    changed = False
    for name in (".zshrc", ".bashrc"):
        rc = os.path.join(HOME, name)
        text = read_text(rc)
        if text is None:
            continue
        lines = text.splitlines()
        kept = [l for l in lines if not re.match(r"^\s*alias\s+coder\b", l)]
        if len(kept) != len(lines) and not DRY:
            write_text(rc, "\n".join(kept) + ("\n" if kept else ""))
            log("  removed stale coder alias from %s" % name)
            changed = True
    return changed


def permission_ok(value):
    return value == "allow" or (isinstance(value, dict) and value.get("*") == "allow")


def ensure_config():
    """opencode.jsonc carries $schema and allows by default. It is JSONC: a
    file that does not parse is left alone and named, never replaced."""
    path = os.path.join(HOME, ".config", "opencode", "opencode.jsonc")
    text = read_text(path)
    if text is None or not text.strip():
        if os.path.exists(path) and text is None:
            return ["opencode.jsonc could not be read; left as is"]
        text = "{}\n"
    try:
        data = jsonc_load(text)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except ValueError as exc:
        log("! opencode.jsonc does not parse (%s); left as is" % exc)
        return ["opencode.jsonc does not parse (%s); fix it by hand, upkeep leaves "
                "it alone" % exc]
    new = text
    if not data.get("$schema"):
        new = jsonc_set(new, "$schema", OPENCODE_SCHEMA)
    # OpenCode 1's update notice offers OpenCode 2, which these Macs do not run.
    if data.get("autoupdate") is not False:
        new = jsonc_set(new, "autoupdate", False)
    perm = data.get("permission")
    if not permission_ok(perm):
        if isinstance(perm, dict):
            perm = dict(perm)
            perm["*"] = "allow"
            new = jsonc_set(new, "permission", perm)
        else:
            new = jsonc_set(new, "permission", "allow")
    if new != text:
        if DRY:
            would_write(path)
        else:
            write_text(path, new)
            log("  repaired opencode.jsonc (permission allows, no update check)")
    return []


def upgrade_holds():
    """A run holds upkeep's lock, or the legacy brew job's lock is fresh:
    node and npm may be moving."""
    if lock_holder(LOCK) is not None:
        return True
    legacy = legacy_brew()
    return bool(legacy and legacy["lock_fresh"])


def doctor_pass(in_run=False):
    """The doctor's checks and repairs; its problems, as lines. Outside a run
    it leaves everything while an upgrade moves node and npm, and while an
    opencode runs a broken binary waits BROKEN_GRACE before its repair. A run
    or a repo's setup repairs at once."""
    if not in_run and upgrade_holds():
        return None
    problems = []
    if not npm_path():
        problems.append("no npm, so opencode cannot be installed (brew install node)")
    else:
        running = opencode_running()
        if not running:
            ensure_npm_allow_scripts()
        ok, why = binary_state()
        if ok:
            clear_broken()
        elif in_run or not running or broken_for() >= BROKEN_GRACE:
            state = "broken and not running"
            if running:
                ensure_npm_allow_scripts()
                state = ("broken while an opencode runs" if in_run else
                         "broken while an opencode runs, for %d s or more" % BROKEN_GRACE)
            if DRY:
                would_write(os.path.realpath(opencode_bin()))
            if STUB_MARK in why:
                log("opencode binary %s; repairing with its postinstall (%s)"
                    % (state, why))
                if run_postinstall():
                    ok, why = binary_state()
            if not ok:
                log("opencode binary %s; reinstalling (%s)" % (state, why))
                reinstall()
                ok, why = binary_state()
                if not ok:
                    log("  ! still broken after reinstall (%s); will retry next pass"
                        % why)
                    problems.append("opencode is broken after a reinstall (%s)" % why)
            if ok:
                clear_broken()
    ensure_coder()
    remove_stale_aliases()
    problems += ensure_config()
    return problems


# --------------------------------------------------------------- DeepSeek key

def key_places():
    return {"file": os.path.join(HOME, ".config", "api-keys", "deepseek_key"),
            "keys.env": os.path.join(HOME, ".config", "tutor-board", "keys.env"),
            "auth.json": os.path.join(HOME, ".local", "share", "opencode", "auth.json")}


KEYS_ENV_LINE = re.compile(r"^\s*(?:export\s+)?DEEPSEEK_API_KEY\s*=\s*(.*?)\s*$")


def keys_env_value(text):
    for line in (text or "").splitlines():
        m = KEYS_ENV_LINE.match(line)
        if m:
            return m.group(1).strip("'\"")
    return ""


def auth_value(text):
    try:
        rec = (json.loads(text or "{}") or {}).get("deepseek") or {}
        return str(rec.get("key") or "") if isinstance(rec, dict) else ""
    except (ValueError, AttributeError):
        return ""


def key_sync(r):
    """DEEPSEEK_API_KEY, else ~/.config/api-keys/deepseek_key, else keys.env,
    else opencode's auth.json, written to the others. No key is ever logged."""
    p = key_places()
    found = [("env", os.environ.get("DEEPSEEK_API_KEY", "").strip()),
             ("file", (read_text(p["file"]) or "").strip()),
             ("keys.env", keys_env_value(read_text(p["keys.env"]))),
             ("auth.json", auth_value(read_text(p["auth.json"])))]
    source = [(k, v) for k, v in found if v]
    if not source:
        r.problem("no DeepSeek key: put it in ~/.config/api-keys/deepseek_key")
        return
    where, key = source[0]
    have = dict(found)
    wrote = []
    if r.report_only or DRY:
        due = [k for k in ("file", "keys.env", "auth.json") if have[k] != key
               and (k == "file" or os.path.isdir(os.path.dirname(p[k])))]
        if due:
            log("deepseek key: %s differ(s) from %s; the next run writes them"
                % (", ".join(due), where))
            r.changes += ["write the DeepSeek key to %s" % tilde(p[k]) for k in due]
            for k in due:
                would_write(p[k])
        return
    if have["file"] != key:
        os.makedirs(os.path.dirname(p["file"]), mode=0o700, exist_ok=True)
        write_text(p["file"], key + "\n", 0o600)
        wrote.append(tilde(p["file"]))
    if have["keys.env"] != key and os.path.isdir(os.path.dirname(p["keys.env"])):
        text = read_text(p["keys.env"]) or ""
        lines = text.splitlines()
        out, done = [], False
        for line in lines:
            if KEYS_ENV_LINE.match(line):
                if not done:
                    out.append("DEEPSEEK_API_KEY=%s" % key)
                    done = True
                continue
            out.append(line)
        if not done:
            out.append("DEEPSEEK_API_KEY=%s" % key)
        write_text(p["keys.env"], "\n".join(out) + "\n", 0o600)
        wrote.append(tilde(p["keys.env"]))
    if have["auth.json"] != key and os.path.isdir(os.path.dirname(p["auth.json"])):
        try:
            data = json.loads(read_text(p["auth.json"]) or "{}")
            data = data if isinstance(data, dict) else {}
        except ValueError:
            data = None
        if data is None:
            r.problem("opencode's auth.json does not parse; the DeepSeek key was not "
                      "written there")
        else:
            data["deepseek"] = {"type": "api", "key": key}
            write_text(p["auth.json"], json.dumps(data, indent=2) + "\n", 0o600)
            wrote.append(tilde(p["auth.json"]))
    if wrote:
        log("deepseek key: wrote %s (from %s)" % (", ".join(wrote), where))
        r.changes += ["wrote the DeepSeek key to %s" % w for w in wrote]


def parity_install(r):
    script = None
    for d in (os.path.join(SHARE, "opencode"), os.path.join(HERE, "opencode")):
        if os.path.isfile(os.path.join(d, "install.py")):
            script = os.path.join(d, "install.py")
            break
    if not script:
        log("no parity layer (upkeep/opencode/install.py): skipped")
        r.phases["opencode parity"] = "skipped: absent"
        return
    argv = [sys.executable, script] + (["--dry-run"] if DRY or r.report_only else [])
    code, out, err = run(argv, T_PARITY)
    log_tail(out + "\n" + err, "parity", 20)
    if code != 0:
        r.problem("the opencode parity layer reports %d problem(s); see %s"
                  % (code, tilde(LOG)))
    changes = parity_changes(out)
    if changes is None and code == 0:
        r.problem("opencode/install.py printed no `changed: N` line; see %s" % tilde(LOG))
    r.changes += changes or []
    if DRY or r.report_only:
        for path in said_paths(out):
            would_write(path)
    plugin_sdk(r)


PARITY_SAID_NOTHING = "opencode parity layer up to date"


def parity_changes(out):
    """The changes install.py printed (made, or under --dry-run due), by its
    closing `changed: N` line: [] when N is 0, else every line it printed but
    a problem and capabilities.md, which the plugin re-reads live. None when
    it printed no count, so its output says nothing reliable."""
    said = []
    count = None
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("would: "):
            line = line[len("would: "):]
        m = re.match(r"^changed: (\d+)$", line)
        if m:
            count = int(m.group(1))
        elif line and not line.startswith("problem:") and line != PARITY_SAID_NOTHING \
                and not line.endswith("/capabilities.md"):
            said.append(line)
    if count is None:
        return None
    return said if count else []


def said_paths(out):
    """The absolute path that ends each change line install.py printed
    ("install <path>", "merge managed keys into <path>", ...)."""
    paths = []
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("would: "):
            line = line[len("would: "):]
        if line.startswith("problem:") or line == PARITY_SAID_NOTHING:
            continue
        at = line.rfind(" /")
        if at >= 0:
            paths.append(line[at + 1:])
    return paths


WOULD = []


def would_write(path):
    """Under --dry-run (or a report), a path the opencode phase would write."""
    path = os.path.abspath(path)
    if path not in WOULD:
        WOULD.append(path)


def plugin_sdk(r):
    """The plugin's pinned packages in ~/.config/opencode/node_modules:
    `npm install` there only when one is missing or at another version."""
    cfg = os.path.join(HOME, ".config", "opencode")
    pins = (read_json(os.path.join(cfg, "package.json")) or {}).get("dependencies")
    if not isinstance(pins, dict) or not pins:
        return
    off = [n for n, v in sorted(pins.items())
           if (read_json(os.path.join(cfg, "node_modules", n, "package.json")) or {})
           .get("version") != v]
    if not off:
        return
    npm = npm_path()
    if not npm:
        r.problem("no npm, so the plugin's packages (%s) cannot be installed"
                  % ", ".join(off))
        return
    r.changes.append("install the plugin's packages (%s) in %s" % (", ".join(off),
                                                                   tilde(cfg)))
    if r.report_only or DRY:
        for n in off:
            would_write(os.path.join(cfg, "node_modules", n, "package.json"))
    if r.report_only:
        return
    code, out, err = run([npm, "install", "--prefix", cfg, "--no-fund", "--no-audit",
                          "--silent"], T_NPM, mutating=True)
    if code != 0:
        r.fail("plugin packages", last_line(err, out) or "exit %d" % code)


def server_reads():
    """A test: does the OpenCode server read this file (or files under this
    directory) at start? ~/.config/opencode, but not node_modules, lockfiles,
    dotfiles, backups or capabilities.md, which the plugin re-reads on each
    change; the plugin's pinned packages; auth.json; the binary. One rule for
    a run's snapshot and a dry run's forecast."""
    cfg = os.path.join(HOME, ".config", "opencode")
    pins = (read_json(os.path.join(cfg, "package.json")) or {}).get("dependencies")
    named = set(os.path.join(cfg, "node_modules", n, "package.json")
                for n in (pins if isinstance(pins, dict) else {}))
    named |= {key_places()["auth.json"], os.path.realpath(opencode_bin())}
    live = os.path.join(cfg, "capabilities.md")

    def reads(path):
        path = os.path.abspath(path)
        if path in named:
            return True
        rel = os.path.relpath(path, cfg)
        if rel == ".":
            return True
        parts = rel.split(os.sep)
        return not (parts[0] in ("..", "node_modules")
                    or any(p.startswith(".") for p in parts)
                    or parts[-1].endswith((".upkeep-tmp", ".before-upkeep"))
                    or parts[-1] in ("package-lock.json", "bun.lock", "bun.lockb")
                    or path == live)
    return reads, sorted(named)


def opencode_files():
    """{path: (size, mtime, mode)} of every file the server reads at start
    (server_reads). Every writer here writes only on a difference, so a stat
    that moved is a file that changed."""
    cfg = os.path.join(HOME, ".config", "opencode")
    reads, named = server_reads()
    paths = list(named)
    for dirpath, dirnames, filenames in os.walk(cfg):
        dirnames[:] = [d for d in dirnames if d != "node_modules" and not d.startswith(".")]
        paths += [os.path.join(dirpath, f) for f in filenames]
    out = {}
    for path in paths:
        if not reads(path):
            continue
        try:
            st = os.stat(path)
        except OSError:
            continue
        out[path] = (st.st_size, st.st_mtime_ns, st.st_mode)
    return out


def phase_opencode(r):
    if loaded(LEGACY_DOCTOR):
        r.phases["opencode doctor"] = "skipped: %s is loaded" % LEGACY_DOCTOR
    elif not r.report_only:
        for line in doctor_pass(in_run=True) or []:
            r.problem(line)
    elif read_json(DOCTOR_STATE):
        for line in (read_json(DOCTOR_STATE) or {}).get("problems") or []:
            r.problem(line)
    key_sync(r)
    parity_install(r)


# ------------------------------------------------------------- Android, Flutter

def jbr():
    return os.path.join(APPS, "Android Studio.app", "Contents", "jbr", "Contents", "Home")


def android_env():
    sdk_paths = [os.path.join(SDK, "cmdline-tools", "latest", "bin"),
                 os.path.join(SDK, "platform-tools"), os.path.join(SDK, "emulator")]
    return {"JAVA_HOME": jbr(), "ANDROID_HOME": SDK, "ANDROID_SDK_ROOT": SDK,
            "PATH": os.pathsep.join(sdk_paths + [search_path()])}


def sdkmanager():
    own = os.path.join(SDK, "cmdline-tools", "latest", "bin", "sdkmanager")
    return own if os.access(own, os.X_OK) else which("sdkmanager")


def sdk_packages(out):
    """(installed, available) package ids from `sdkmanager --list`."""
    installed, available, part = set(), set(), None
    for line in out.splitlines():
        s = line.strip()
        low = s.lower()
        if low.startswith("installed packages"):
            part = installed
            continue
        if low.startswith("available packages"):
            part = available
            continue
        if low.startswith("available updates"):
            part = None
            continue
        if part is None or "|" not in s:
            continue
        pkg = s.split("|")[0].strip()
        if pkg and not pkg.startswith("-") and pkg.lower() != "path" and " " not in pkg:
            part.add(pkg)
    return installed, available


def newest(pkgs, pattern):
    best = None
    for p in pkgs:
        m = re.match(pattern, p)
        if m:
            key = tuple(int(g or 0) for g in m.groups())
            if best is None or key > best[0]:
                best = (key, p)
    return best[1] if best else None


def flutter_settings_ok():
    data = read_json(os.path.join(HOME, ".config", "flutter", "settings"))
    data = data if isinstance(data, dict) else {}
    return data.get("android-sdk") == SDK and data.get("jdk-dir") == jbr()


DOCTOR_HEAD = re.compile(r"^\[(.)\]\s+(.+?)\s*$")


def flutter_doctor_problems(out):
    """Each flutter doctor section not [✓], with its first ✗ or ! line."""
    found, cur = [], None
    for line in out.splitlines():
        m = DOCTOR_HEAD.match(line)
        if m:
            cur = None
            if m.group(1) != "✓":
                cur = [m.group(1), m.group(2), ""]
                found.append(cur)
            continue
        s = line.strip()
        if cur is not None and not cur[2] and s[:1] in ("✗", "!"):
            cur[2] = s[1:].strip()
    return ["flutter doctor: [%s] %s%s" % (a, b, ": " + c if c else "")
            for a, b, c in found]


def phase_android(r, state):
    flutter = which("flutter")
    env = android_env()
    if not os.path.isdir(jbr()):
        r.problem("Android Studio is not installed, so there is no JDK for Android "
                  "(brew install --cask android-studio)")
    if not r.report_only:
        sdkm = sdkmanager()
        if not sdkm:
            r.problem("no sdkmanager (brew install --cask android-commandlinetools)")
        else:
            root = "--sdk_root=" + SDK
            os.makedirs(SDK, exist_ok=True)
            code, out, err = run([sdkm, root, "--update"], T_SDK, mutating=True, env=env)
            if code != 0:
                r.fail("sdkmanager --update", last_line(err, out) or "exit %d" % code)
            code, out, err = run([sdkm, root, "--list"], T_SDK, env=env)
            if code != 0:
                r.fail("sdkmanager --list", last_line(err, out) or "exit %d" % code)
            else:
                have, avail = sdk_packages(out)
                want = [p for p in ("platform-tools", "cmdline-tools;latest")
                        if p not in have]
                plat = newest(avail | have, r"^platforms;android-(\d+)(?:\.(\d+))?$")
                tools = newest(avail | have, r"^build-tools;(\d+)\.(\d+)\.(\d+)$")
                want += [p for p in (plat, tools) if p and p not in have]
                yes = "y\n" * 100
                run([sdkm, root, "--licenses"], T_SDK, mutating=True, env=env,
                    stdin_text=yes)
                if want:
                    log("installing Android packages: %s" % ", ".join(want))
                    code, out, err = run([sdkm, root] + want, T_SDK, mutating=True,
                                         env=env, stdin_text=yes)
                    if code != 0:
                        r.fail("sdkmanager install", last_line(err, out)
                               or "exit %d" % code)
                    run([sdkm, root, "--licenses"], T_SDK, mutating=True, env=env,
                        stdin_text=yes)
    if not flutter:
        r.problem("flutter is not installed (brew install --cask flutter)")
        return
    if not flutter_settings_ok():
        if r.report_only:
            r.problem("flutter is not configured for the Android SDK and Android "
                      "Studio's JDK; upkeep run --force")
        else:
            code, out, err = run([flutter, "config", "--android-sdk", SDK,
                                  "--jdk-dir", jbr()], T_FLUTTER, mutating=True, env=env)
            if code != 0:
                r.fail("flutter config", last_line(err, out) or "exit %d" % code)
    if not r.report_only:
        code, out, _ = run([flutter, "--version", "--machine"], T_FLUTTER, env=env)
        try:
            ver = json.loads(out).get("frameworkVersion") if code == 0 else None
        except (ValueError, AttributeError):
            ver = None
        if ver and ver != state.get("flutter_version"):
            code, out, err = run([flutter, "precache"], T_FLUTTER, mutating=True, env=env)
            if code != 0:
                r.fail("flutter precache", last_line(err, out) or "exit %d" % code)
            elif not DRY:
                state["flutter_version"] = ver
    code, out, err = run([flutter, "doctor", "-v"], T_FLUTTER, env=env)
    found = flutter_doctor_problems(out)
    if not found and code != 0:
        found = ["flutter doctor failed: %s" % (last_line(err, out) or "exit %d" % code)]
    for line in found:
        r.problem(line)
    if not found:
        log("flutter doctor: all green")


# ------------------------------------------------------------------- Xcode

def root_hint():
    repos = load_repos()
    where = os.path.join(repos[0], "upkeep") if repos else SHARE
    return "sudo bash %s" % tilde(os.path.join(where, "root", "install.sh"))


def defaults_read(domain_or_path, key):
    code, out, _ = run(["defaults", "read", domain_or_path, key], T_PROBE)
    return out.strip() if code == 0 else None


def ios_runtime(r):
    """An iOS simulator runtime for the iOS SDK this Xcode ships: an Xcode update
    brings a new SDK, and flutter doctor goes red until its runtime is here."""
    code, out, _ = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], T_PROBE)
    sdk = out.strip() if code == 0 else ""
    if not sdk:
        r.problem("Xcode has no iOS simulator SDK: xcodebuild -downloadPlatform iOS")
        return
    code, out, _ = run(["xcrun", "simctl", "list", "runtimes", "--json"], T_PROBE)
    try:
        runtimes = json.loads(out).get("runtimes") or [] if code == 0 else []
    except (ValueError, AttributeError):
        runtimes = []
    want = ".".join(sdk.split(".")[:2])
    for rt in runtimes:
        if (isinstance(rt, dict) and rt.get("platform") == "iOS" and rt.get("isAvailable")
                and ".".join(str(rt.get("version", "")).split(".")[:2]) == want):
            return
    if r.report_only:
        r.problem("no iOS %s simulator runtime: upkeep run --force" % want)
        return
    log("downloading the iOS %s simulator runtime" % want)
    code, out, err = run(["xcodebuild", "-downloadPlatform", "iOS"], T_SIMULATOR,
                         mutating=True)
    if code != 0:
        r.fail("xcodebuild -downloadPlatform iOS", last_line(err, out) or "exit %d" % code)


def phase_xcode(r, state):
    xcode = os.path.join(APPS, "Xcode.app")
    if not os.path.isdir(xcode):
        r.problem("Xcode is not installed: App Store, or sudo mas get 497799835")
    else:
        code, out, _ = run(["xcode-select", "-p"], T_PROBE)
        if code != 0 or not out.strip().startswith(xcode):
            r.problem("xcode-select points at %s, not Xcode: %s"
                      % (out.strip() or "nothing", root_hint()))
        elif run(["xcodebuild", "-checkFirstLaunchStatus"], T_PROBE)[0] != 0:
            r.problem("Xcode needs its first launch: %s" % root_hint())
        elif run(["xcodebuild", "-license", "check"], T_PROBE)[0] != 0:
            r.problem("Xcode's license is not accepted: %s" % root_hint())
        else:
            ios_runtime(r)
    for where, key in (("/Library/Preferences/com.apple.commerce", "AutoUpdate"),
                       ("/Library/Preferences/com.apple.SoftwareUpdate",
                        "AutomaticallyInstallAppUpdates")):
        if defaults_read(where, key) in ("0", "false", "NO"):
            r.problem("App Store automatic updates are off: System Settings, App Store, "
                      "or %s" % root_hint())
            break
    status = read_json(ROOT_STATUS)
    if not isinstance(status, dict):
        r.problem("the root helper is not installed: %s" % root_hint())
    elif hours_since(parse_ts(status.get("at"))) > STALE_H:
        r.problem("the root helper has not reported since %s: %s"
                  % (status.get("at") or "ever", root_hint()))
    elif status.get("result") != "ok":
        r.problem("the root helper says: %s" % (status.get("detail")
                                                or status.get("result")))
    if which("mas"):
        code, out, _ = run(["mas", "outdated"], T_PROBE * 2)
        if code == 0 and not DRY:
            state["app_store_outdated"] = [l.strip() for l in out.splitlines()
                                           if l.strip()]


# --------------------------------------------------------------- appearance

def vscode_settings_path():
    return os.path.join(HOME, "Library", "Application Support", "Code", "User",
                        "settings.json")


def appearance_vscode(r):
    want = read_json(os.path.join(HERE, "appearance", "vscode.json"))
    path = vscode_settings_path()
    if not isinstance(want, dict):
        return
    if not os.path.exists(path) and not os.path.isdir(os.path.dirname(path)) \
            and not os.path.isdir(os.path.join(APPS, "Visual Studio Code.app")):
        log("VS Code is not here: its settings skipped")
        return
    text = read_text(path)
    text = "{}\n" if text is None or not text.strip() else text
    try:
        have = jsonc_load(text)
        if not isinstance(have, dict):
            raise ValueError("not an object")
    except ValueError as exc:
        r.problem("VS Code's settings.json does not parse (%s); left as is" % exc)
        return
    new = text
    for key, value in sorted(want.items()):
        if have.get(key) != value or key not in have:
            new = jsonc_set(new, key, value)
    if new == text:
        return
    if r.report_only:
        r.problem("VS Code's font settings differ from upkeep/appearance/vscode.json; "
                  "upkeep run --force")
        return
    if not DRY:
        write_text(path, new)
    log("VS Code: font settings written")


def terminal_profile():
    for name in sorted(os.listdir(os.path.join(HERE, "appearance"))):
        if name.endswith(".terminal"):
            with open(os.path.join(HERE, "appearance", name), "rb") as fh:
                prof = plistlib.load(fh)
            return str(prof.get("name") or name[:-9]), prof
    return None, None


def appearance_terminal(r):
    name, prof = terminal_profile()
    if not prof:
        return
    code, out, _ = run(["defaults", "export", TERMINAL_DOMAIN, "-"], T_PROBE)
    try:
        prefs = plistlib.loads(out.encode("utf-8")) if code == 0 and out.strip() else {}
    except Exception:                                        # noqa: BLE001
        prefs = None
    if prefs is None:
        r.problem("Terminal's preferences could not be read; its profile left alone")
        return
    ws = dict(prefs.get("Window Settings") or {})
    if ws.get(name) == prof and prefs.get("Default Window Settings") == name \
            and prefs.get("Startup Window Settings") == name:
        return
    if r.report_only:
        r.problem("Terminal's default profile is not %s; upkeep run --force" % name)
        return
    ws[name] = prof
    prefs["Window Settings"] = ws
    prefs["Default Window Settings"] = name
    prefs["Startup Window Settings"] = name
    body = plistlib.dumps(prefs).decode("utf-8")
    code, out, err = run(["defaults", "import", TERMINAL_DOMAIN, "-"], T_PROBE,
                         mutating=True, stdin_text=body)
    if code != 0:
        r.fail("Terminal profile", last_line(err, out) or "exit %d" % code)
    else:
        log("Terminal: %s installed as the default and startup profile" % name)


def code_cli():
    c = which("code")
    if c:
        return c
    c = os.path.join(APPS, "Visual Studio Code.app", "Contents", "Resources", "app",
                     "bin", "code")
    return c if os.access(c, os.X_OK) else None


def appearance_extensions(r):
    c = code_cli()
    if not c or r.report_only:
        return
    code, out, _ = run([c, "--list-extensions"], T_PROBE * 2)
    if code != 0:
        return
    if FLUTTER_EXTENSION.lower() in [l.strip().lower() for l in out.splitlines()]:
        return
    code, out, err = run([c, "--install-extension", FLUTTER_EXTENSION], T_PROBE * 5,
                         mutating=True)
    log("VS Code: %s %s" % (FLUTTER_EXTENSION, "installed" if code == 0
                            else "did not install: %s" % last_line(err, out)))


def phase_appearance(r):
    appearance_vscode(r)
    appearance_terminal(r)
    appearance_extensions(r)


# -------------------------------------------------------------------- pull

T_GIT = 300
BREW_FILE = re.compile(r"(^|/)Brewfile[^/]*$")
MISE_FILE = re.compile(r"(^|/)(\.?mise(\.[\w-]+)?\.(toml|lock)|\.tool-versions)$")


def opted_in(root):
    """A repo asks to be fast-forwarded hourly by carrying upkeep.d/pull."""
    return os.path.isfile(os.path.join(root, "upkeep.d", "pull"))


def git(root, args, timeout=T_PROBE, mutating=False):
    code, out, err = run(["git", "-C", root] + list(args), timeout, mutating=mutating,
                         env={"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
    return code, out.strip(), err.strip()


def pull_clone(root):
    """(what happened, the paths that moved). Fast-forwards the clone to its
    upstream only on its remote's default branch, with a clean working tree
    and index (ignored files aside), and only when that is a fast-forward.
    Anything else is a skip, said why. A dry run fetches nothing."""
    code, branch, _ = git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if code != 0 or not branch:
        return "skipped: HEAD is detached", []
    code, remote, _ = git(root, ["config", "--get", "branch.%s.remote" % branch])
    if code != 0 or not remote or remote == ".":
        remote = "origin"
    code, head, _ = git(root, ["symbolic-ref", "--quiet", "--short",
                               "refs/remotes/%s/HEAD" % remote])
    default = head[len(remote) + 1:] if code == 0 and head.startswith(remote + "/") else ""
    if not default:
        return ("skipped: %s's default branch is unknown (git remote set-head %s --auto)"
                % (remote, remote)), []
    if branch != default:
        return "skipped: on %s, not %s" % (branch, default), []
    code, up, _ = git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name",
                             "@{upstream}"])
    if code != 0 or up != "%s/%s" % (remote, default):
        return "skipped: %s does not track %s/%s" % (branch, remote, default), []
    code, dirty, err = git(root, ["status", "--porcelain"])
    if code != 0:
        return "skipped: git status failed: %s" % last_line(err), []
    if [l for l in dirty.splitlines() if not l.startswith("??")]:
        return "skipped: tracked files or the index have changes", []
    if dirty:
        return "skipped: untracked files in the working tree", []
    if not DRY:
        code, out, err = git(root, ["fetch", "--quiet", remote, default], T_GIT)
        if code != 0:
            return "skipped: the fetch failed: %s" % (last_line(err, out) or code), []
    code, counts, _ = git(root, ["rev-list", "--left-right", "--count",
                                 "HEAD...@{upstream}"])
    parts = counts.split()
    if code != 0 or len(parts) != 2 or not all(x.isdigit() for x in parts):
        return "skipped: git rev-list could not compare HEAD with %s" % up, []
    ahead, behind = int(parts[0]), int(parts[1])
    if ahead:
        return "skipped: %d local commit(s) not on %s, so not a fast-forward" % (ahead, up), []
    if not behind:
        return "up to date", []
    # -z: paths as they are, never C-quoted (core.quotePath).
    code, names, _ = git(root, ["diff", "-z", "--name-only", "HEAD", "@{upstream}"])
    files = [f for f in names.split("\0") if f] if code == 0 else []
    if DRY:
        return "would fast-forward %d commit(s) from %s, as last fetched" % (behind, up), files
    code, out, err = git(root, ["merge", "--ff-only", "--no-autostash",
                                "--no-overwrite-ignore", "--quiet", "@{upstream}"],
                         T_GIT, mutating=True)
    if code != 0:
        return "skipped: the fast-forward was refused: %s" % (last_line(err, out) or code), []
    return "fast-forwarded %d commit(s) from %s" % (behind, up), files


def pull_repos(state):
    """Fast-forward every registered repo that opted in. (brew due, [roots
    whose mise files moved]): what the narrow install owes."""
    said, brew_due, mise_due = {}, False, []
    for root in load_repos():
        if not opted_in(root):
            continue
        try:
            line, files = pull_clone(root)
        except Exception as exc:                             # noqa: BLE001
            line, files = "skipped: %r" % exc, []
        log("pull %s: %s" % (tilde(root), line))
        said[root] = line
        brew_due = brew_due or any(BREW_FILE.search(f) for f in files)
        if any(MISE_FILE.search(f) for f in files):
            mise_due.append(root)
    if said:
        state["pulls"] = {"at": stamp(), "said": said}
        save_state(state)
    return brew_due, mise_due


def narrow_install(state, brew_due, mise_due):
    """After a pull that moved a Brewfile or a mise file, on an hour the gate
    refuses: `brew bundle --no-upgrade` over the union, and the repo's hook
    `locked-install`, which installs its pinned tools at their locked
    versions. Nothing upgrades, locks or prunes: the full run does that."""
    if not brew_due and not mise_due:
        return
    log("a pull moved %s: the narrow install" % " and ".join(
        (["a Brewfile"] if brew_due else []) + (["a mise file"] if mise_due else [])))
    r = Run()
    try:
        if brew_due:
            skip = legacy_skip(legacy_brew())
            if skip:
                log("the Brewfile waits for %s: %s" % (LEGACY_BREW, skip))
            else:
                phase(r, "bundle", phase_bundle)
        for root in mise_due:
            check_off()
            code, _ = hook(root, "locked-install", T_HOOK_WORK)
            if code != 0:
                r.fail("hook %s locked-install" % os.path.basename(root.rstrip("/")),
                       "exit %d; see %s" % (code, tilde(LOG)))
    except Stopped:
        return
    if r.failed or r.problems:
        failed = dict(state.get("failed") or {})
        failed.update(r.failed)
        state["failed"] = failed
        state["problems"] = list(state.get("problems") or []) + \
            [p for p in r.problems if p not in (state.get("problems") or [])]
        save_state(state)
        notify(state)


# ---------------------------------------------------------------- worktrees

WORKTREE_IDLE_H = 24
WORKTREE_PARENT = re.compile(r"(-wt|^worktrees)$")


def worktree_list(root):
    """The repo's worktrees, main first: dicts with path, head, branch (a
    short name, None when detached), locked, prunable. None when git cannot
    list them."""
    code, out, _ = git(root, ["worktree", "list", "--porcelain", "-z"])
    if code != 0:
        return None
    trees = []
    for block in out.split("\0\0"):
        rec = {"path": None, "head": None, "branch": None, "locked": False,
               "prunable": False}
        for field in block.split("\0"):
            key, _, value = field.partition(" ")
            if key == "worktree":
                rec["path"] = value
            elif key == "HEAD":
                rec["head"] = value
            elif key == "branch":
                rec["branch"] = value[len("refs/heads/"):] \
                    if value.startswith("refs/heads/") else value
            elif key in ("locked", "prunable"):
                rec[key] = True
        if rec["path"]:
            trees.append(rec)
    return trees


def default_branches(root):
    """(default branch names, their tip commits): local main and master, and
    the branch origin/HEAD names."""
    names, tips = [], []
    refs = ["refs/heads/main", "refs/heads/master"]
    code, head, _ = git(root, ["symbolic-ref", "--quiet", "--short",
                               "refs/remotes/origin/HEAD"])
    if code == 0 and head.startswith("origin/"):
        names.append(head[len("origin/"):])
        refs.append("refs/remotes/origin/HEAD")
    for ref in refs:
        code, sha, _ = git(root, ["rev-parse", "--verify", "--quiet", ref + "^{commit}"])
        if code == 0 and sha:
            tips.append(sha)
            if ref.startswith("refs/heads/"):
                names.append(ref[len("refs/heads/"):])
    return names, tips


def idle_hours(path):
    """Hours since the worktree last moved: the newest mtime of its directory,
    each top-level entry (its .git file among them), and its admin dir in the
    common git dir (worktrees/<name>/ and its HEAD, index, ORIG_HEAD,
    logs/HEAD), which a checkout, add or commit touches. An edit deeper down
    makes the tree dirty, which keeps it anyway. None when unreadable."""
    stamps = []
    try:
        stamps.append(os.lstat(path).st_mtime)
        for entry in os.scandir(path):
            stamps.append(entry.stat(follow_symlinks=False).st_mtime)
    except OSError:
        return None
    code, admin, _ = git(path, ["rev-parse", "--absolute-git-dir"])
    if code != 0 or not admin:
        return None
    for rel in ("", "HEAD", "index", "ORIG_HEAD", os.path.join("logs", "HEAD")):
        try:
            stamps.append(os.lstat(os.path.join(admin, rel)).st_mtime)
        except OSError:
            pass
    return (time.time() - max(stamps)) / 3600.0


def inside(path, top):
    """path is top or below it, both resolved."""
    path, top = os.path.realpath(path), os.path.realpath(top)
    return path == top or path.startswith(top.rstrip(os.sep) + os.sep)


def raise_it(exc):
    raise exc


def nested_git(path):
    """Why path holds a .git (a repo, clone or worktree) that git status cannot
    see, being in an ignored directory, or None. git worktree remove would
    delete it with the rest; an untracked one shows in git status already."""
    code, out, err = git(path, ["ls-files", "-z", "--others", "--ignored",
                                "--exclude-standard", "--directory"])
    if code != 0:
        return "git ls-files failed: %s" % (last_line(err) or code)
    for rel in (e for e in out.split("\0") if e):
        top = os.path.join(path, rel.rstrip("/"))
        if not os.path.lexists(top):
            return "ignored path %s cannot be found" % rel
        if os.path.basename(top) == ".git":
            found = top
        elif os.path.islink(top) or not os.path.isdir(top):
            continue
        else:
            try:
                found = next((os.path.join(d, ".git") for d, dirs, files
                              in os.walk(top, onerror=raise_it)
                              if ".git" in dirs or ".git" in files), None)
            except OSError as exc:
                return "ignored path %s cannot be read: %s" % (rel, exc.strerror or exc)
        if found:
            return "a git repo or worktree is in an ignored directory: %s" % \
                os.path.relpath(found, path)
    return None


PER_WORKTREE_REFS = ("refs/worktree/", "refs/bisect/", "refs/rewritten/")
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}


def merged(main, sha, tips):
    """sha is an ancestor of one of the default branch tips."""
    return any(git(main, ["merge-base", "--is-ancestor", sha, tip])[0] == 0
               for tip in tips)


IN_PROGRESS = (("BISECT_START", "a bisect"), ("rebase-merge", "a rebase"),
               ("rebase-apply", "a rebase or git am"), ("REBASE_HEAD", "a rebase"),
               ("sequencer", "a cherry-pick or revert"), ("MERGE_HEAD", "a merge"),
               ("MERGE_AUTOSTASH", "a merge"), ("CHERRY_PICK_HEAD", "a cherry-pick"),
               ("REVERT_HEAD", "a revert"))


def in_progress(path):
    """Why an operation is under way in the worktree, or None. Its state, and
    the autostash of a rebase or merge, live in worktrees/<name>/. A file
    there names it, or, for the *_HEAD ones, a ref in the reftable."""
    args = ["rev-parse", "--path-format=absolute"]
    for name, _ in IN_PROGRESS:
        args += ["--git-path", name]
    code, out, err = git(path, args)
    paths = out.splitlines()
    if code != 0 or len(paths) != len(IN_PROGRESS):
        return "git rev-parse failed: %s" % (last_line(err) or code)
    heads = [n for n, _ in IN_PROGRESS if n.endswith("_HEAD")]
    code, out, err = run(["git", "-C", path, "cat-file", "--batch-check=%(objectname)"],
                         T_PROBE, env=GIT_ENV, stdin_text="\n".join(heads) + "\n")
    found = out.splitlines()
    if code != 0 or len(found) != len(heads):
        return "git cat-file failed: %s" % (last_line(err) or code)
    named = {n for n, line in zip(heads, found) if not line.endswith(" missing")}
    for (name, what), where in zip(IN_PROGRESS, paths):
        if name in named or os.path.lexists(where):
            return "%s is in progress" % what
    return None


def reflog_commits(main, path):
    """(the commits the worktree's HEAD reflog names that still exist, None),
    or (None, why not). git worktree remove deletes this reflog. git reflog
    reads it under either ref backend; the files backend's logs/HEAD adds
    each entry's old commit, which git reflog does not print."""
    code, out, err = git(path, ["reflog", "show", "--format=%H", "HEAD", "--"])
    if code != 0:
        return None, "git reflog failed: %s" % (last_line(err) or code)
    lines = out.splitlines()
    code, log_path, err = git(path, ["rev-parse", "--path-format=absolute",
                                     "--git-path", "logs/HEAD"])
    if code != 0 or not log_path:
        return None, "git rev-parse failed: %s" % (last_line(err) or code)
    try:
        with open(log_path, errors="replace") as fh:
            lines += [w for l in fh.read().splitlines() for w in l.split(" ")[:2]]
    except FileNotFoundError:
        pass
    except OSError as exc:
        return None, "its HEAD reflog cannot be read: %s" % (exc.strerror or exc)
    shas = []
    for sha in lines:
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha) and sha.strip("0") \
                and sha not in shas:
            shas.append(sha)
    if not shas:
        return [], None
    code, out, err = run(["git", "-C", main, "cat-file",
                          "--batch-check=%(objectname) %(objecttype)"], T_PROBE,
                         env=GIT_ENV, stdin_text="\n".join(shas) + "\n")
    if code != 0:
        return None, "git cat-file failed: %s" % (last_line(err) or code)
    return [l.split()[0] for l in out.splitlines() if l.endswith(" commit")], None


def worktree_history_keep(main, path, branch, tips):
    """Why commits only this worktree's admin dir reaches (an operation under
    way, its per-worktree refs, its HEAD reflog) keep it, or None. git worktree
    remove deletes worktrees/<name>/, and with it the only way back to them."""
    busy = in_progress(path)
    if busy:
        return busy
    code, out, err = git(path, ["for-each-ref", "--format=%(refname)"])
    if code != 0:
        return "git for-each-ref failed: %s" % (last_line(err) or code)
    for ref in (r for r in out.splitlines() if r.startswith(PER_WORKTREE_REFS)):
        code, sha, _ = git(path, ["rev-parse", "--verify", "--quiet", ref + "^{commit}"])
        if code != 0 or not sha:
            return "its per-worktree ref %s names no commit" % ref
        if not merged(main, sha, tips):
            return "its per-worktree ref %s is not merged into the default branch" % ref
    commits, why = reflog_commits(main, path)
    if why:
        return why
    if not commits:
        return None
    own = "refs/heads/%s" % branch if branch else None
    code, out, err = git(main, ["for-each-ref", "--format=%(refname)"])
    if code != 0:
        return "git for-each-ref failed: %s" % (last_line(err) or code)
    others = [r for r in out.splitlines()
              if r != own and not r.startswith(PER_WORKTREE_REFS)]
    code, out, err = run(["git", "-C", main, "rev-list", "--stdin", "--max-count=1"],
                         T_GIT, env=GIT_ENV,
                         stdin_text="\n".join(commits + ["--not"] + list(tips) + others)
                         + "\n")
    if code != 0:
        return "git rev-list failed: %s" % (last_line(err) or code)
    if out.strip():
        return ("its HEAD reflog holds commit %s, on neither the default branch nor "
                "any other ref" % out.strip()[:12])
    return None


def worktree_keep(main, tree, names, tips, roots, trees=()):
    """Why this linked worktree stays, or None when it is merged, clean and
    idle, and may go."""
    path = tree["path"]
    if tree["locked"]:
        return "locked"
    if not os.path.isdir(path):
        return "its directory is gone (moved or unmounted?); repair or prune it by hand"
    if any(inside(r, path) for r in roots):
        return "a registered repo is in it"
    held = [t["path"] for t in trees if t["path"] != path and inside(t["path"], path)]
    if held:
        return "worktree %s is in it" % tilde(held[0])
    if inside(HERE, path):
        return "upkeep runs from it"
    if tree["branch"] and tree["branch"] in names:
        return "it holds the default branch %s" % tree["branch"]
    if not tree["head"] or not tips:
        return "no default branch to compare with"
    if not merged(main, tree["head"], tips):
        return "%s is not merged into the default branch" % (
            tree["branch"] or "its detached HEAD")
    history = worktree_history_keep(main, path, tree["branch"], tips)
    if history:
        return history
    code, dirty, err = git(path, ["status", "--porcelain", "--ignored=no",
                                  "--untracked-files=all"])
    if code != 0:
        return "git status failed: %s" % (last_line(err) or code)
    if dirty:
        return "it has changes or untracked files"
    code, listed, err = git(path, ["ls-files", "-v", "-z"])
    if code != 0:
        return "git ls-files failed: %s" % (last_line(err) or code)
    if any(e[:1] == "S" or e[:1].islower() for e in listed.split("\0") if e):
        return "files flagged skip-worktree or assume-unchanged hide changes from git status"
    nested = nested_git(path)
    if nested:
        return nested
    idle = idle_hours(path)
    if idle is None:
        return "its files cannot be read"
    if idle < WORKTREE_IDLE_H:
        return "touched %.1f h ago, under %d h" % (idle, WORKTREE_IDLE_H)
    return None


def remove_parent(parent, removed, roots):
    """A dedicated worktree directory (named <repo>-wt, or worktrees) goes once
    only .DS_Store is left; never HOME, ~/Developer, or one holding a
    registered repo."""
    real = os.path.realpath(parent)
    if not WORKTREE_PARENT.search(os.path.basename(real)) \
            or any(inside(p, real) for p in [HOME, os.path.join(HOME, "Developer")]
                   + list(roots)):
        return
    try:
        left = [n for n in os.listdir(real)
                if n != ".DS_Store" and os.path.join(real, n) not in removed]
    except OSError:
        return
    if left:
        return
    if DRY:
        log("[dry-run] would remove %s, then empty" % tilde(real))
        return
    try:
        found = os.listdir(real)
        stray = sorted(n for n in found if n != ".DS_Store")
        if stray:
            log("worktrees: %s kept, not empty: %s" % (tilde(real), ", ".join(stray)))
            return
        if ".DS_Store" in found:
            os.remove(os.path.join(real, ".DS_Store"))
        os.rmdir(real)
        log("worktrees: removed %s, now empty" % tilde(real))
    except OSError as exc:
        log("worktrees: %s left: %s" % (tilde(real), exc))


def prune_admin(main):
    """git worktree prune, only while no linked worktree is prunable: it drops
    the admin dir of every worktree whose directory is missing, unmerged commits
    and all, and a moved or unmounted worktree is not ours to judge."""
    trees = worktree_list(main) or []
    missing = [t["path"] for t in trees[1:] if t["prunable"]]
    if missing:
        log("worktrees: git worktree prune skipped, directory gone: %s"
            % ", ".join(tilde(p) for p in missing))
        return
    git(main, ["worktree", "prune"], T_GIT, mutating=True)


def prune_repo(root, roots):
    """{worktree path: what happened} for one repo's linked worktrees."""
    trees = worktree_list(root)
    if not trees:
        return {}
    main = trees[0]["path"]
    names, tips = default_branches(main)
    said, removed = {}, []
    for tree in trees[1:]:
        path = tree["path"]
        why = worktree_keep(main, tree, names, tips, roots, trees)
        if why:
            said[path] = "kept: " + why
            continue
        code, out, err = git(main, ["worktree", "remove", path], T_GIT, mutating=True)
        if code != 0:
            said[path] = "kept: git worktree remove refused: %s" % (
                last_line(err, out) or code)
            continue
        removed.append(os.path.realpath(path))
        line = "would be removed" if DRY else "removed"
        if tree["branch"]:
            code, out, err = git(main, ["branch", "-d", tree["branch"]], T_GIT,
                                 mutating=True)
            line += "; branch %s %s" % (tree["branch"], "deleted" if code == 0 else
                                        "kept: %s" % (last_line(err, out) or code))
        said[path] = line
    if removed:
        prune_admin(main)
    for parent in sorted(set(os.path.dirname(p) for p in removed)):
        remove_parent(parent, removed, roots)
    return said


def prune_worktrees(state):
    """Every registered repo's merged, clean, idle linked worktrees go: git
    worktree remove (never --force), git branch -d (never -D), git worktree
    prune, then an emptied <repo>-wt. Anything else stays, said why."""
    roots = registered()
    said, seen = {}, set()
    for root in roots:
        code, common, _ = git(root, ["rev-parse", "--git-common-dir"])
        if code != 0 or not common:
            continue
        common = os.path.realpath(os.path.join(root, common))
        if common in seen:
            continue
        seen.add(common)
        try:
            got = prune_repo(root, roots)
        except Exception as exc:                             # noqa: BLE001
            got = {root: "skipped: %r" % exc}
        for path, line in sorted(got.items()):
            log("worktree %s: %s" % (tilde(path), line))
        said.update(got)
    if said or state.pop("worktrees", None) is not None:
        if said:
            state["worktrees"] = {"at": stamp(), "said": said}
        save_state(state)


# -------------------------------------------------------------------- hooks

def phase_hooks(r):
    for root in load_repos():
        if not hook_path(root):
            continue
        name = os.path.basename(root.rstrip("/"))
        if not r.report_only:
            for ph in ("after-brew", "toolchain"):
                check_off()
                code, _ = hook(root, ph, T_HOOK_WORK)
                if code != 0:
                    r.fail("hook %s %s" % (name, ph), "exit %d; see %s"
                           % (code, tilde(LOG)))
        code, lines = hook(root, "status", T_HOOK_LIST)
        if code != 0:
            lines = lines + ["%s's upkeep.d/hook status exited %d" % (name, code)]
        r.hooks[root] = lines


def phase_cleanup(r):
    if brew_running():
        log("brew cleanup waits for the next run: a brew is running (a hook's own "
            "upgrade, perhaps), and cleanup deletes the downloads in flight")
        return
    code, out, err = brew(["cleanup", "--prune=%d" % PRUNE_DAYS], T_CLEANUP,
                          mutating=True)
    if code != 0:
        log("! brew cleanup exited %d" % code)
        log_tail(out + "\n" + err, "cleanup", 3)


# ------------------------------------------------------------------- notify

def problem_lines(state, doctor=None):
    """Every line the owner should see: failures, holds, problems, hook and
    doctor lines."""
    out = []
    for step, why in sorted((state.get("failed") or {}).items()):
        out.append("upkeep: %s failed: %s" % (step, why))
    for name, h in sorted((state.get("held") or {}).items()):
        h = h if isinstance(h, dict) else {}
        out.append("upkeep: %s %s -> %s is held: %s" % (
            name, h.get("installed") or "?", h.get("latest") or "?", h.get("why") or ""))
    for line in state.get("problems") or []:
        out.append("upkeep: %s" % line)
    for root, lines in sorted((state.get("hooks") or {}).items()):
        for line in lines or []:
            out.append("%s: %s" % (os.path.basename(root.rstrip("/")), line))
    doctor = read_json(DOCTOR_STATE) if doctor is None else doctor
    for line in ((doctor or {}).get("problems") or []) if isinstance(doctor, dict) else []:
        if "upkeep: " + line not in out:
            out.append("upkeep: %s" % line)
    return out


def notify(state):
    """Each new problem line once, as a notification, on every machine."""
    if DRY:
        return
    seen = set(state.get("notified") or [])
    keep = []
    for line in problem_lines(state):
        h = hashlib.sha1(line.encode("utf-8")).hexdigest()
        keep.append(h)
        if h in seen:
            continue
        text = line.replace("\\", "\\\\").replace('"', '\\"')
        run(["osascript", "-e", 'display notification "%s" with title "Upkeep"' % text],
            T_PROBE)
    state["notified"] = keep
    save_state(state)


# ---------------------------------------------------------------- commands

def full_run(state, why, force):
    trim_log()
    started = now()
    log("=== upkeep run (%s) ===" % why)
    state["last_attempt"] = stamp(started)
    save_state(state)
    r = Run()
    stopped = False
    legacy = legacy_brew()
    skip = legacy_skip(legacy)
    try:
        if skip:
            for name in ("brew", "bundle", "npm"):
                r.phases[name] = "skipped: %s" % skip
            log("brew, the Brewfile and npm left to %s this run: %s" % (LEGACY_BREW, skip))
        else:
            phase(r, "brew", phase_brew, state)
            phase(r, "bundle", phase_bundle)
            phase(r, "npm", phase_npm)
        phase(r, "opencode", phase_opencode)
        phase(r, "android", phase_android, state)
        phase(r, "xcode", phase_xcode, state)
        phase(r, "appearance", phase_appearance)
        phase(r, "hooks", phase_hooks)
        if not skip:
            phase(r, "cleanup", phase_cleanup)
    except Stopped:
        stopped = True
        log("off by owner: the run stops here, before its next step")
    done = now()
    ok = not stopped and not r.failed
    state.update({"last_result": "stopped" if stopped else "ok" if ok else "partial",
                  "last_duration_seconds": int((done - started).total_seconds()),
                  "failed": r.failed, "held": r.held, "protected": r.protected,
                  "problems": r.problems,
                  "hooks": r.hooks, "phases": r.phases, "checked_at": stamp(done),
                  "version": version_of(HERE),
                  "brew_by": LEGACY_BREW if skip else "upkeep"})
    if ok:
        state["last_success"] = stamp(done)
    save_state(state)
    log("=== %s in %ds (%s) ===" % ("dry run done" if DRY else "done",
                                   state["last_duration_seconds"], state["last_result"]))
    notify(state)
    return 0


def recheck(state):
    """Problems recorded are probed again, report only, hourly until clear."""
    recorded = problem_lines({"problems": state.get("problems"),
                              "hooks": state.get("hooks")}, {})
    if not recorded:
        return 0
    if hours_since(parse_ts(state.get("checked_at"))) * 60 < RECHECK_MIN:
        return 0
    log("re-checking %d recorded problem(s)" % len(recorded))
    r = Run(report_only=True)
    try:
        for name, fn, args in (("bundle", phase_bundle, ()),
                               ("opencode", phase_opencode, ()),
                               ("android", phase_android, (state,)),
                               ("xcode", phase_xcode, (state,)),
                               ("appearance", phase_appearance, ()),
                               ("hooks", phase_hooks, ())):
            if name == "bundle" and state.get("brew_by") == LEGACY_BREW:
                continue
            phase(r, name, fn, *args)
    except Stopped:
        return 0
    state.update({"problems": r.problems, "hooks": r.hooks, "checked_at": stamp()})
    save_state(state)
    notify(state)
    return 0


def busy():
    if brew_running():
        return "a brew is running"
    code, out, _ = run(["pgrep", "-lf", "brew[-_]upgrade"], T_PROBE)
    for line in out.splitlines() if code == 0 else []:
        parts = line.split()
        if len(parts) > 2 and re.match(r"^(python[\d.]*|bash|sh|zsh)$",
                                       os.path.basename(parts[1]), re.I) \
                and re.search(r"brew[-_]upgrade\.(py|sh)\b", " ".join(parts[2:])) \
                and "scripts/brew-upgrade.py" not in line \
                and not parts[2].startswith("-c"):
            return "another brew upgrader is running (%s)" % line.strip()[:120]
    return None


def cmd_run(force=False):
    if os.path.exists(OFF_FILE):
        if not DRY:
            return 0
        log("off by owner (%s); a real tick does nothing" % OFF_FILE)
    if not os.environ.get("UPKEEP_REEXEC") and self_update():
        os.environ["UPKEEP_REEXEC"] = "1"
        script = os.path.join(SHARE, "upkeep.py")
        args = ["run"] + (["--force"] if force else []) + (["--dry-run"] if DRY else [])
        os.execv(sys.executable, [sys.executable, script] + args)
    for line in retire() + ensure_agents():
        log(line)
    if ensure_shell_block():
        log("~/.zprofile: the upkeep block written")
    if not brew_path():
        log("no brew: install Homebrew (bash upkeep/setup-mac.sh)")
        return 0
    why_busy = busy()
    if why_busy:
        log("skipped: %s; the next hour asks again" % why_busy)
        if not DRY:
            return 0
    if not take_lock(LOCK):
        log("another run holds the lock")
        return 0
    try:
        state = load_state()
        if not state.get("first_seen"):
            state["first_seen"] = stamp()
            save_state(state)
        brew_due, mise_due = pull_repos(state)
        prune_worktrees(state)
        if DRY:
            go, why = gate(state)
            log("gate: %s (%s)" % ("would run" if go else "would skip", why))
            why = "dry run"
        elif force:
            why = "forced"
        else:
            go, why = gate(state)
            if not go:
                narrow_install(state, brew_due, mise_due)
                return recheck(state)
        hold_awake()
        return full_run(state, why, force)
    finally:
        drop_lock(LOCK)


def cmd_doctor():
    if os.path.exists(OFF_FILE) or loaded(LEGACY_DOCTOR):
        return 0
    if not take_lock(DOCTOR_LOCK):
        return 0
    try:
        problems = doctor_pass()
        if problems is None:
            return 0
        old = read_json(DOCTOR_STATE)
        if not isinstance(old, dict) or old.get("problems") != problems:
            write_json(DOCTOR_STATE, {"checked_at": stamp(), "problems": problems})
        return 0
    finally:
        drop_lock(DOCTOR_LOCK)


OPENCODE_SERVE = "com.mikeyferguson.opencode-serve"


def serve_started():
    """When the OpenCode server's running process started (epoch seconds),
    from its pid in `launchctl print`; None when it is not running."""
    code, out, _ = launchctl_print(OPENCODE_SERVE)
    m = re.search(r"^\s*pid = (\d+)\s*$", out, re.M) if code == 0 else None
    if not m:
        return None
    code, out, _ = run(["ps", "-o", "lstart=", "-p", m.group(1)], T_PROBE,
                       env={"LC_ALL": "C"})
    try:
        return time.mktime(time.strptime(" ".join(out.split()), "%a %b %d %H:%M:%S %Y"))
    except ValueError:
        return None


def cmd_opencode():
    """The opencode phase alone (the doctor, the key, the parity layer and its
    packages), for a repo's setup. Prints each change, each problem, then
    `changed: N`, the files the OpenCode server reads at start that changed
    (under --dry-run, those it would write; server_reads is the one rule for
    both). While the server runs it also prints `stale: M`, the files it reads
    at start that are newer than its process (an hourly run installs without
    restarting it). A caller restarts the server when N or M is above 0. Log
    lines it echoes are indented, so only its own lines start with
    `problem:`, `changed:` or `stale:`. Exit status: the problems."""
    global ECHO_INDENT
    ECHO_INDENT = "  "
    if not take_lock(LOCK):
        print("problem: an upkeep run holds %s and does this phase itself; run this "
              "again when it ends" % tilde(LOCK))
        print("changed: 0")
        return 1
    try:
        before = opencode_files()
        r = Run()
        try:
            phase_opencode(r)
        except Exception as exc:                             # noqa: BLE001
            r.fail("opencode", repr(exc)[:300])
        if DRY:
            reads, _ = server_reads()
            changed = ["would change %s" % tilde(path) for path in WOULD if reads(path)]
        else:
            after = opencode_files()
            changed = ["changed %s" % tilde(path) for path in sorted(set(before) | set(after))
                       if before.get(path) != after.get(path)]
        for line in changed:
            print(line)
        bad = ["%s: %s" % kv for kv in sorted(r.failed.items())] + r.problems
        for line in bad:
            print("problem: %s" % line)
        print("changed: %d" % len(changed))
        started = serve_started()
        if started is not None:
            # lstart has whole seconds; a file is newer only past the next one.
            print("stale: %d" % len([p for p, st in opencode_files().items()
                                     if st[1] / 1e9 >= started + 1]))
        return min(len(bad), 100)
    finally:
        drop_lock(LOCK)


def same_tree(a, b):
    """Do two upkeep/ copies hold the same files, byte for byte?"""
    def files(root):
        out = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for f in filenames:
                if not f.endswith(".pyc"):
                    full = os.path.join(dirpath, f)
                    out[os.path.relpath(full, root)] = full
        return out
    fa, fb = files(a), files(b)
    if sorted(fa) != sorted(fb):
        return False
    for rel in fa:
        try:
            with open(fa[rel], "rb") as x, open(fb[rel], "rb") as y:
                if x.read() != y.read():
                    return False
        except OSError:
            return False
    return True


def cmd_install(repo):
    root = os.path.realpath(os.path.expanduser(repo))
    src = os.path.join(root, "upkeep")
    if not os.path.isfile(os.path.join(src, "upkeep.py")):
        print("%s carries no upkeep/upkeep.py" % root)
        return 1
    os.makedirs(STATE_DIR, exist_ok=True)
    register(root)
    mine, installed = version_of(src), version_of(SHARE)
    if mine == installed and same_tree(src, SHARE):
        print("upkeep %d is already at %s" % (mine, tilde(SHARE)))
    elif mine >= installed:
        copy_in(src)
        print("upkeep %d copied to %s" % (mine, tilde(SHARE)))
    else:
        print("upkeep %d stays at %s (%s carries %d)"
              % (installed, tilde(SHARE), root, mine))
    os.makedirs(os.path.dirname(LINK), exist_ok=True)
    target = os.path.join(SHARE, "upkeep.py")
    if os.path.islink(LINK) and os.readlink(LINK) != target:
        os.remove(LINK)
    if not os.path.lexists(LINK):
        os.symlink(target, LINK)
    if ensure_shell_block():
        print("~/.zprofile: the upkeep block written")
    for line in retire():
        print(line)
    bad = 0
    for line in ensure_agents():
        print(line)
        bad += "failed" in line or line.startswith("!")
    print("registered: %s" % ", ".join(load_repos()))
    if os.path.exists(OFF_FILE):
        print("off by owner (upkeep on)")
    return 1 if bad else 0


def cmd_off():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    write_text(OFF_FILE, "off since %s; upkeep on undoes it\n" % stamp())
    holder = lock_holder(LOCK)
    print("upkeep is off: runs and doctor ticks do nothing%s"
          % ("; the run under way (pid %s) stops before its next step" % holder
             if holder is not None else ""))
    return 0


def cmd_on():
    try:
        os.remove(OFF_FILE)
    except OSError:
        pass
    print("upkeep is on")
    return 0


def cmd_settle():
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as exc:
        log("! settle: %s" % exc)
        return 1
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        code, why = reload_job(LABEL, os.path.join(AGENTS_DIR, LABEL + ".plist"))
        log("settle: the run ended; %s" % ("reloaded" if code == 0
                                           else "bootstrap failed: %s" % why))
        return 0 if code == 0 else 1
    finally:
        os.close(fd)


def next_window(state):
    earliest = now()
    la = parse_ts(state.get("last_attempt"))
    if la and la + timedelta(hours=MIN_INTERVAL_H) > earliest:
        earliest = la + timedelta(hours=MIN_INTERVAL_H)
    if earliest.hour in WINDOW:
        return earliest
    start = earliest.replace(hour=WINDOW[0], minute=0, second=0, microsecond=0)
    return start if start > earliest else start + timedelta(days=1)


def summary(state):
    """One line: the last run and its counts."""
    if not state.get("last_attempt"):
        return "no run yet"
    return "%s %s; %d held, %d failed, %d problems" % (
        state.get("last_result") or "?", state.get("last_attempt"),
        len(state.get("held") or {}), len(state.get("failed") or {}),
        len(problem_lines({"problems": state.get("problems"),
                           "hooks": state.get("hooks")}, {})))


def cmd_status():
    state = load_state()
    print("upkeep:    %s at %s" % (version_of(SHARE) if version_of(SHARE) >= 0
                                   else "not installed", tilde(SHARE)))
    print("repos:     %s" % (", ".join(load_repos()) or "none"))
    for label in (LABEL, DOCTOR_LABEL) + tuple(l for l, _ in templates()
                                               if l not in (LABEL, DOCTOR_LABEL)):
        print("%-9s  %s" % ("agent:", "%s %s" % (label, "loaded" if loaded(label)
                                                 else "NOT LOADED")))
    print("off:       %s" % ("yes (upkeep on)" if os.path.exists(OFF_FILE) else "no"))
    print("last run:  %s" % summary(state))
    print("success:   %s" % (state.get("last_success") or "never"))
    print("next:      %s" % next_window(state).strftime("%a %b %d %H:%M"))
    if state.get("brew_by") == LEGACY_BREW:
        print("brew:      left to %s" % LEGACY_BREW)
    pulls = state.get("pulls") if isinstance(state.get("pulls"), dict) else {}
    for root, line in sorted((pulls.get("said") or {}).items()):
        print("pull:      %s %s (%s)" % (tilde(root), line, pulls.get("at") or "?"))
    trees = state.get("worktrees") if isinstance(state.get("worktrees"), dict) else {}
    for path, line in sorted((trees.get("said") or {}).items()):
        print("worktree:  %s %s (%s)" % (tilde(path), line, trees.get("at") or "?"))
    for line in state.get("app_store_outdated") or []:
        print("APP STORE %s" % line)
    lines = problem_lines(state)
    base = parse_ts(state.get("last_success")) or parse_ts(state.get("first_seen"))
    if base and hours_since(base) > STALE_H:
        lines.append("upkeep: no successful run since %s" % stamp(base))
    for line in lines:
        print("PROBLEM   %s" % line)
    return 1 if lines else 0


def cmd_storage(flags):
    """`upkeep storage`: the daily storage tick's own program, with its flags."""
    path = os.path.join(SHARE, "storage.py")
    try:
        return subprocess.call([sys.executable, path] + list(flags))
    except OSError as exc:
        print("! could not run %s: %s" % (path, exc), file=sys.stderr)
        return 1


USAGE = ("usage: upkeep install --repo ROOT | run [--force] [--dry-run] "
         "| opencode [--dry-run] | doctor | status | off | on "
         "| storage [run [--dry-run] [--force] | status]")


def main(argv):
    global DRY
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, flags = argv[0], argv[1:]
    if cmd == "install":
        if len(flags) != 2 or flags[0] != "--repo":
            print(USAGE, file=sys.stderr)
            return 2
        return cmd_install(flags[1])
    if cmd == "storage":
        return cmd_storage(flags)
    allowed = {"run": ("--dry-run", "--force"), "opencode": ("--dry-run",)}
    if cmd not in ("run", "opencode", "doctor", "status", "off", "on", "settle") \
            or any(f not in allowed.get(cmd, ()) for f in flags):
        print(USAGE, file=sys.stderr)
        return 2
    DRY = "--dry-run" in flags
    if cmd == "run":
        return cmd_run(force="--force" in flags)
    return {"opencode": cmd_opencode, "doctor": cmd_doctor, "status": cmd_status,
            "off": cmd_off, "on": cmd_on, "settle": cmd_settle}[cmd]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
