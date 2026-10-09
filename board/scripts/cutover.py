#!/usr/bin/env python3
"""The cutover: the old per-workspace system off, the overhaul merged into
main, the one LaunchAgent on, and the way back.

    cutover.sh --plan                     what --run would do here; changes nothing
    cutover.sh --rehearse <scratch>       steps 1-10 on a copy, then --rollback
    cutover.sh --run                      steps 1-11 on this Mac
    cutover.sh --rollback <manifest>      undo a run that has not pushed

Options: --atlas <dir> (default: the main checkout of the repository this
script sits in), --ref <rev> (default `overhaul`), --keep (rehearse: keep
the scratch directory after a pass).

The steps, in order (HANDOFF T26): 1 preflight, 2 stop the old system,
3 snapshot, 4 info/exclude, 5 import every live/, 6 course repositories,
7 merge, 8 residue, 9 install, 10 start and prove, 11 push. Every change is
recorded first in `<archive>/cutover-manifest.json` (the archive is
`~/Archive/atlas-migration/<date>/`), so `--rollback` can undo exactly what
happened. `--run` rolls back by itself when a step fails before the push.

The rehearsal runs the same code against a copy: a clone of the Atlas with a
bare clone as origin, copies of every live/ and course directory, dummy
residue, fake old daemons and boards under rehearsal launchd labels, a fake
provider, port 8779, and a printed tailscale plan instead of changes.

Standard library only. Runs on the Mac.
"""

import argparse
import errno
import filecmp
import json
import os
import plistlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)

LABEL = "tutor-board"
OLD_LABELS = ("tutor-board.tutor-watch", "tutor-board.tutor-pull")
PORT = 8778
REHEARSE_PORT = 8779
REF = "overhaul"
MERGE_MSG = "overhaul: one server, sessions, courses and projects"
CHECK_SAY = "cutover check: reply with one short card"
ARCHIVE_ROOT = os.path.expanduser("~/Archive/atlas-migration")
MANIFEST = "cutover-manifest.json"
EXCLUDE_LINES = ("/sessions/", ".ink/")
UV_PROJECTS = ("projects/TRD-EHR", "projects/PSYCH-ASR", "projects/libr-local-llm",
               "projects/Paper-Writer")
WORKSPACE_PARENTS = ("courses", "research", "practice", "projects")
MIN_FREE = 5 * 1024 ** 3
DAEMON_WAIT = 600          # a tutor mid-turn gets ten minutes to finish it
BOARD_TERM_WAIT = 10       # SIGTERM, then SIGKILL
ANSWER_WAIT = 300          # the cutover check's card
OLD_NAMES = re.compile(r"serve\.py|tutor headless|board wait|tutor-pull|tutor watch")
# Never moved, listed or swept by a rollback: tutorboard/fenced.py NEVER.
FENCED = ("phi", "data", "inbox", "stage1", "stage2", "raw", "audio")
# What a rehearsal's comparison ignores: logs and caches.
COMPARE_SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store)(/|$)|\.log$|\.pyc$")


class Abort(Exception):
    """A failed check: --run stops here and rolls back."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def run(argv, cwd=None, env=None, timeout=None, stdin=None):
    """`(rc, combined output)`. A missing program or a timeout is rc 127/124."""
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, timeout=timeout,
                           input=stdin, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        return p.returncode, p.stdout
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out + "\n(timed out after %ss)" % timeout


def git(root, *args, **kw):
    # No opportunistic index refresh: a status must not rewrite a course's
    # .git/index between the snapshot and a comparison.
    env = dict(kw.pop("env", None) or os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return run(["git", "-C", root] + list(args), env=env, **kw)


def git_ok(root, *args, **kw):
    rc, out = git(root, *args, **kw)
    if rc != 0:
        raise Abort("git %s failed in %s:\n%s" % (" ".join(args), root, out.strip()[-1500:]))
    return out


def write_json(path, doc):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def fenced(rel):
    return any(p.lower() in FENCED for p in rel.replace(os.sep, "/").split("/"))


def has_files(top):
    for _, _, files in os.walk(top):
        if files:
            return True
    return False


def dirs_of(top):
    """Every directory under `top`, relative, parents first."""
    out = []
    for here, dirs, _ in os.walk(top):
        for d in sorted(dirs):
            out.append(os.path.relpath(os.path.join(here, d), top))
    return out


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def http(port, path, body=None, timeout=30):
    """`(status, json or {})`, or `(0, {})` when nothing answers."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data,
                                 method="POST" if data is not None else "GET",
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (OSError, ValueError):
        return 0, {}
    try:
        return status, json.loads(raw.decode("utf-8") or "{}")
    except ValueError:
        return status, {}


def until(cond, timeout, step=1.0):
    end = time.time() + timeout
    while True:
        got = cond()
        if got or time.time() >= end:
            return got
        time.sleep(step)


# ---------------------------------------------------------------------------
# processes
# ---------------------------------------------------------------------------
class Proc(object):
    def __init__(self, pid, pgid, ppid, stat, cmd):
        self.pid, self.pgid, self.ppid, self.stat, self.cmd = pid, pgid, ppid, stat, cmd

    def __repr__(self):
        return "%d %s" % (self.pid, self.cmd[:160])


def processes():
    rc, out = run(["ps", "-axww", "-o", "pid=,pgid=,ppid=,stat=,command="])
    procs = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        try:
            pid, pgid, ppid = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue
        if "Z" in parts[3]:
            continue                     # a zombie is gone; only a reap is owed
        procs.append(Proc(pid, pgid, ppid, parts[3], parts[4]))
    return procs


def matching(pattern, scope=None, procs=None):
    """Live processes whose command line matches `pattern` (and holds `scope`,
    when given), never this process or its ancestors."""
    mine = set()
    pid = os.getpid()
    table = procs if procs is not None else processes()
    parent = dict((p.pid, p.ppid) for p in table)
    while pid and pid not in mine:
        mine.add(pid)
        pid = parent.get(pid, 0)
    rx = re.compile(pattern) if isinstance(pattern, str) else pattern
    return [p for p in table if p.pid not in mine and rx.search(p.cmd)
            and (scope is None or scope in p.cmd)]


def alive(pid):
    for p in processes():
        if p.pid == pid:
            return True
    return False


def argv_value(cmd, flag):
    m = re.search(r"(?:^|\s)%s(?:=|\s+)(\S+)" % re.escape(flag), cmd)
    return m.group(1) if m else None


def kill_group(proc, sig):
    """Signal the process group, never our own."""
    try:
        if proc.pgid > 1 and proc.pgid != os.getpgid(0):
            os.killpg(proc.pgid, sig)
        else:
            os.kill(proc.pid, sig)
    except OSError as exc:
        if exc.errno != errno.ESRCH:
            raise


# ---------------------------------------------------------------------------
# launchd
# ---------------------------------------------------------------------------
def domain():
    return "gui/%d" % os.getuid()


def loaded(label):
    return run(["launchctl", "print", "%s/%s" % (domain(), label)], timeout=30)[0] == 0


def bootout(label):
    rc, out = run(["launchctl", "bootout", "%s/%s" % (domain(), label)], timeout=60)
    until(lambda: not loaded(label), 15, 0.5)
    return not loaded(label), out


def bootstrap(plist, label):
    rc, out = run(["launchctl", "bootstrap", domain(), plist], timeout=60)
    return until(lambda: loaded(label), 15, 0.5), out


def launchctl_count(needle):
    rc, out = run(["launchctl", "list"], timeout=30)
    return sum(1 for line in out.splitlines() if needle in line)


# ---------------------------------------------------------------------------
# tailscale: the capture, the plan, the check
# ---------------------------------------------------------------------------
def ts_targets(status):
    """Every `(kind, listen port, target)` a `serve status --json` holds."""
    out = []
    status = status or {}
    tcp = status.get("TCP") or {}
    for port, rec in sorted(tcp.items()):
        rec = rec or {}
        if rec.get("TCPForward"):
            out.append(("tls-terminated-tcp" if rec.get("TerminateTLS") else "tcp",
                        str(port), rec["TCPForward"], "/"))
    for hostport, web in sorted((status.get("Web") or {}).items()):
        port = hostport.rsplit(":", 1)[-1]
        kind = "http" if (tcp.get(port) or {}).get("HTTP") else "https"
        for path, h in sorted(((web or {}).get("Handlers") or {}).items()):
            h = h or {}
            target = h.get("Proxy") or h.get("Path") or h.get("Text") or ""
            out.append((kind, port, target, path))
    return out


def ts_restore(status):
    """The commands that put a captured serve config back, reset first."""
    cmds = [["tailscale", "serve", "reset"]]
    for kind, port, target, path in ts_targets(status):
        cmd = ["tailscale", "serve", "--bg", "--yes", "--%s=%s" % (kind, port)]
        if kind in ("tcp", "tls-terminated-tcp"):
            if "://" not in target:
                target = "tcp://" + target
        elif path and path != "/":
            cmd += ["--set-path", path]
        cmds.append(cmd + [target])
    return cmds


def ts_publish(port):
    """Every old mapping off, then HTTPS on 443 to the one server."""
    return [["tailscale", "serve", "reset"],
            ["tailscale", "serve", "--bg", "--yes", "--https=443",
             "http://127.0.0.1:%d" % port]]


def ts_only(status, port):
    """What, in a serve config, is anything other than `port`. Empty is good."""
    targets = ts_targets(status)
    wrong = [t for t in targets if not re.search(r":%d(/|$)" % port, t[2])]
    if not targets:
        return ["nothing is published"]
    return ["%s %s -> %s" % (k, p, t) for k, p, t, _ in wrong]


# ---------------------------------------------------------------------------
# where things are
# ---------------------------------------------------------------------------
def workspaces(atlas):
    """`[(rel, path)]` of every workspace holding a live/ directory."""
    out = []
    for parent in WORKSPACE_PARENTS:
        top = os.path.join(atlas, parent)
        if not os.path.isdir(top):
            continue
        for name in sorted(os.listdir(top)):
            ws = os.path.join(top, name)
            if os.path.isdir(os.path.join(ws, "live")) and not os.path.islink(ws):
                out.append(("%s/%s" % (parent, name), ws))
    return out


def post_merge(rel):
    """The subject id a workspace has after the merge."""
    parent, name = rel.split("/", 1)
    return ("courses/" if parent == "courses" else "projects/") + name


def course_repos(atlas):
    top = os.path.join(atlas, "courses")
    if not os.path.isdir(top):
        return []
    return [n for n in sorted(os.listdir(top))
            if os.path.isdir(os.path.join(top, n, ".git"))]


def course_dirs(atlas):
    top = os.path.join(atlas, "courses")
    if not os.path.isdir(top):
        return []
    return [n for n in sorted(os.listdir(top))
            if os.path.isdir(os.path.join(top, n)) and not n.startswith(".")]


def status_entries(atlas, *extra):
    """`[(code, path)]` from `git status --porcelain`, paths as git prints
    them (a directory with a trailing slash)."""
    out = git_ok(atlas, "status", "--porcelain", "-z", *extra)
    entries = []
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        item = parts[i]
        i += 1
        if len(item) < 4:
            continue
        code, path = item[:2], item[3:]
        if code[0] in "RC":
            i += 1                      # the rename's source follows
        entries.append((code, path))
    return entries


def untracked_set(atlas):
    """Every untracked or ignored entry, directories collapsed."""
    return sorted(set(p for c, p in status_entries(
        atlas, "--ignored=traditional", "--untracked-files=normal") if c in ("??", "!!")))


# ---------------------------------------------------------------------------
# the drift check: courses/X against what the fold took
# ---------------------------------------------------------------------------
def itemized(lines):
    """The paths an `rsync -n -i --checksum` listing says differ in content.
    Directories and time-only lines are not drift."""
    out = []
    for line in lines.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("*deleting"):
            out.append(("gone", line[len("*deleting"):].strip()))
            continue
        code, _, path = line.partition(" ")
        path = path.strip()
        if len(code) < 2 or code[1] == "d" or not path or path.endswith("/"):
            continue
        if code[0] in "<>":
            out.append(("new" if "+++" in code else "changed", path))
    return out


def fold_commit(atlas, ref, rel):
    """The commit on `ref`, not on main, that first carried `rel`."""
    out = git_ok(atlas, "rev-list", "--reverse", "HEAD..%s" % ref, "--", rel).split()
    return out[0] if out else None


def blobs(root, rev, prefix=""):
    out = git_ok(root, "ls-tree", "-r", "-z", rev, *([prefix] if prefix else []))
    got = {}
    for item in out.split("\0"):
        if not item or "\t" not in item:
            continue
        meta, path = item.split("\t", 1)
        if prefix:
            path = path[len(prefix):]
        got[path] = meta.split()[2]
    return got


def course_drift(atlas, ref, name, excludes, scratch):
    """What in courses/<name> differs from the fold that put it on `ref`,
    beyond the files the fold itself rewrote. `[]` is no drift."""
    rel = "courses/%s" % name
    course = os.path.join(atlas, rel)
    fold = fold_commit(atlas, ref, rel)
    if not fold:
        return ["%s is not carried by %s" % (rel, ref)]
    msg = git_ok(atlas, "log", "-1", "--format=%B", fold)
    snap = None
    for tok in re.findall(r"\b[0-9a-f]{7,40}\b", msg):
        rc, full = git(course, "rev-parse", "--verify", "-q", tok + "^{commit}")
        if rc == 0 and full.strip():
            snap = full.strip()
            break
    if not snap:
        return ["the fold commit %s names no commit of %s's repository" % (fold[:8], rel)]
    problems = []
    folded = blobs(atlas, fold, rel + "/")
    had = blobs(course, snap)
    rewritten = set(p for p in set(folded) | set(had) if folded.get(p) != had.get(p))
    # Commits since the fold are drift only where they touch what the fold
    # carried; the old board's own commits of live/ are not.
    since = git_ok(course, "diff", "--name-only", "-z", snap, "HEAD").split("\0")
    for path in since:
        if path and path in folded:
            problems.append("%s/%s committed since the fold took %s" % (rel, path, snap[:8]))
    dest = os.path.join(scratch, name)
    os.makedirs(dest)
    rc, out = run(["sh", "-c", 'git -C "$1" archive "$2" "$3" | tar -x -C "$4"', "sh",
                   atlas, fold, rel, dest])
    if rc != 0:
        return ["could not export %s at %s: %s" % (rel, fold[:8], out.strip()[-300:])]
    rc, out = run(["rsync", "-rn", "--checksum", "--delete", "--itemize-changes",
                   "--exclude-from=%s" % excludes, course + "/",
                   os.path.join(dest, rel) + "/"])
    if rc != 0:
        return ["rsync failed on %s: %s" % (rel, out.strip()[-300:])]
    for what, path in itemized(out):
        if path not in rewritten and not any(path in p for p in problems):
            problems.append("%s/%s %s since the fold" % (rel, path, what))
    return problems


# ---------------------------------------------------------------------------
# the context: everything a step needs, saved in the manifest
# ---------------------------------------------------------------------------
class Ctx(object):
    FIELDS = ("mode", "atlas", "archive", "ref", "label", "old_labels", "port",
              "scope", "agents_dir", "bin_dir", "env", "tailscale", "python",
              "fake_capture")

    def __init__(self, **kw):
        self.mode = kw.get("mode", "run")
        self.atlas = os.path.realpath(kw["atlas"])
        self.archive = os.path.realpath(kw["archive"])
        self.ref = kw.get("ref", REF)
        self.label = kw.get("label", LABEL)
        self.old_labels = list(kw.get("old_labels", OLD_LABELS))
        self.port = int(kw.get("port", PORT))
        self.scope = kw.get("scope")
        self.agents_dir = kw.get("agents_dir", os.path.expanduser("~/Library/LaunchAgents"))
        self.bin_dir = kw.get("bin_dir", os.path.expanduser("~/.local/bin"))
        self.env = dict(kw.get("env") or {})
        self.tailscale = kw.get("tailscale", "real")
        self.python = kw.get("python", sys.executable)
        self.fake_capture = kw.get("fake_capture")
        self.manifest_path = os.path.join(self.archive, MANIFEST)
        self.m = kw.get("manifest")
        self.log_path = os.path.join(self.archive, "cutover.log")

    def environ(self, **extra):
        env = dict(os.environ)
        env.update(self.env)
        env.update(extra)
        for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT"):
            env.pop(k, None)
        return env

    def params(self):
        return dict((k, getattr(self, k)) for k in self.FIELDS)

    # -- the manifest ---------------------------------------------------------
    def begin(self):
        os.makedirs(self.archive, exist_ok=True)
        old = read_json(self.manifest_path)
        if old:
            if old.get("pushed") or not old.get("rolled_back"):
                raise Abort("%s holds a cutover that was neither rolled back nor "
                            "abandoned; roll it back or move it aside first"
                            % self.manifest_path)
            os.replace(self.manifest_path, self.manifest_path.replace(
                ".json", ".%s.json" % time.strftime("%Y%m%d-%H%M%S")))
        self.m = {"version": 1, "ctx": self.params(), "started": time.time(),
                  "steps": [], "moves": [], "booted_out": [], "killed": [],
                  "old_boards": [], "tars": {}, "bundles": [], "exclude_added": [],
                  "imports": [], "removed_trees": [], "restored_tracked": [],
                  "residue_logs": [], "uv": [], "before": None, "merged": False,
                  "installed": None, "bootstrapped": False, "tailscale_changed": False,
                  "saved_agents": [], "pushed": False, "rolled_back": False,
                  "pre": None, "ref_sha": None, "tools": None,
                  "import_manifest": os.path.join(self.archive, "import-manifest.jsonl")}
        self.save()

    def save(self):
        write_json(self.manifest_path, self.m)

    def put(self, key, value):
        self.m[key] = value
        self.save()

    def add(self, key, value):
        self.m.setdefault(key, []).append(value)
        self.save()

    def step(self, n, name, state):
        self.m["steps"].append({"n": n, "name": name, "state": state, "at": time.time()})
        self.save()

    def say(self, *parts):
        line = " ".join(str(p) for p in parts)
        print(line, flush=True)
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
        except OSError:
            pass

    def rel(self, path):
        return os.path.relpath(path, self.atlas)

    def tools(self):
        return self.m.get("tools") or BOARD


# ---------------------------------------------------------------------------
# 1. preflight
# ---------------------------------------------------------------------------
def step_preflight(ctx):
    G = ctx.atlas
    if git(G, "rev-parse", "--show-toplevel")[1].strip() != G:
        raise Abort("%s is not the top of a git checkout" % G)
    branch = git(G, "symbolic-ref", "--short", "-q", "HEAD")[1].strip()
    if branch != "main":
        raise Abort("%s is on %r, not main" % (G, branch or "a detached HEAD"))
    gitdir = git_ok(G, "rev-parse", "--absolute-git-dir").strip()
    for busy in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD"):
        if os.path.exists(os.path.join(gitdir, busy)):
            raise Abort("a %s is in progress in %s" % (busy, G))
    dirty = git_ok(G, "status", "--porcelain", "--untracked-files=no").strip()
    if dirty:
        raise Abort("tracked changes in %s:\n%s" % (G, dirty[:2000]))
    pre = git_ok(G, "rev-parse", "HEAD").strip()
    ctx.put("pre", pre)
    rc, ref_sha = git(G, "rev-parse", "--verify", "-q", ctx.ref + "^{commit}")
    if rc != 0:
        raise Abort("there is no %s to merge" % ctx.ref)
    ctx.put("ref_sha", ref_sha.strip())
    if git(G, "merge-base", "--is-ancestor", ctx.ref, "HEAD")[0] == 0:
        raise Abort("main already holds %s" % ctx.ref)
    ctx.say("  PRE %s, %s %s" % (pre[:12], ctx.ref, ref_sha.strip()[:12]))
    rc, out = git(G, "merge-tree", "--write-tree", "--name-only", "HEAD", ctx.ref)
    if rc == 1:
        raise Abort("%s does not merge into main cleanly:\n%s" % (ctx.ref, out[-2000:]))
    for name in course_repos(G):
        # live/ is the running board's, tracked by its own commits and tarred
        # with the course; the rest must be committed.
        out = git_ok(os.path.join(G, "courses", name), "status", "--porcelain", "--",
                     ".", ":(exclude)live").strip()
        if out:
            raise Abort("courses/%s has uncommitted work:\n%s" % (name, out[:1500]))
    out = git_ok(G, "status", "--porcelain", "--", "research", "practice").strip()
    if out:
        raise Abort("research/ or practice/ has changes:\n%s" % out[:1500])
    # The overhaul's own tools, as they will be merged: import-live, the
    # excludes, and the code a rollback reverses an import with.
    tools = os.path.join(ctx.archive, "overhaul-tree")
    if os.path.isdir(tools):
        shutil.rmtree(tools)
    os.makedirs(tools)
    rc, out = run(["sh", "-c", 'git -C "$1" archive "$2" board | tar -x -C "$3"', "sh",
                   G, ctx.ref, tools])
    if rc != 0 or not os.path.isfile(os.path.join(tools, "board", "scripts", "import-live.py")):
        raise Abort("could not extract board/ from %s: %s" % (ctx.ref, out[-500:]))
    ctx.put("tools", os.path.join(tools, "board"))
    excludes = os.path.join(ctx.tools(), "scripts", "fold-excludes.txt")
    if not os.path.isfile(excludes):
        raise Abort("%s has no board/scripts/fold-excludes.txt" % ctx.ref)
    carried = sorted(set(os.path.basename(p.rstrip("/")) for p in git_ok(
        G, "ls-tree", "-d", "--name-only", ctx.ref, "courses/").split()))
    here = course_dirs(G)
    if sorted(here) != carried:
        raise Abort("courses here %s, courses on %s %s" % (here, ctx.ref, carried))
    scratch = tempfile.mkdtemp(prefix="cutover-drift-")
    try:
        for name in here:
            if not os.path.isdir(os.path.join(G, "courses", name, ".git")):
                raise Abort("courses/%s has no repository to compare" % name)
            drift = course_drift(G, ctx.ref, name, excludes, scratch)
            if drift:
                raise Abort("courses/%s drifted from the fold:\n  %s"
                            % (name, "\n  ".join(drift[:40])))
            ctx.say("  courses/%s matches the fold" % name)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    stray = os.path.join(G, "live")
    if os.path.isdir(stray) and has_files(stray):
        raise Abort("the stray %s holds files; it is expected to be empty" % stray)
    tree = set(git_ok(G, "ls-tree", "-d", "--name-only", ctx.ref, "projects/").split())
    for rel, _ in workspaces(G):
        subject = post_merge(rel)
        if rel.split("/")[0] != "courses" and subject not in tree:
            raise Abort("%s has a live/, but %s is not on %s" % (rel, subject, ctx.ref))
    free = shutil.disk_usage(G).free
    if free < MIN_FREE:
        raise Abort("%.1f GB free; the cutover wants 5" % (free / 1024.0 ** 3))
    ctx.say("  %.0f GB free" % (free / 1024.0 ** 3))


# ---------------------------------------------------------------------------
# 2. stop the old system
# ---------------------------------------------------------------------------
def daemon_home(ctx, proc):
    """The workspace of a `tutor headless` daemon: its agent.json names its
    pid, else its name is the workspace's."""
    homes = workspaces(ctx.atlas)
    for rel, ws in homes:
        rec = read_json(os.path.join(ws, "live", "agent.json")) or {}
        if rec.get("pid") == proc.pid:
            return rel, ws
    m = re.search(r"tutor headless\s+(\S+)", proc.cmd)
    for rel, ws in homes:
        if m and os.path.basename(ws) == m.group(1):
            return rel, ws
    return None, None


def step_stop(ctx):
    for label in ctx.old_labels:
        if loaded(label):
            # Recorded first: a half-done bootout is still undone by a rollback.
            ctx.add("booted_out", label)
            gone, out = bootout(label)
            if not gone:
                raise Abort("%s is still loaded after bootout: %s" % (label, out.strip()))
            ctx.say("  booted out %s" % label)
    for proc in matching(r"tutor headless", ctx.scope):
        rel, ws = daemon_home(ctx, proc)
        if not ws:
            raise Abort("no workspace for the daemon %r" % proc)
        agent = os.path.join(ws, "live", "agent.json")

        def idle():
            rec = read_json(agent) or {}
            return rec.get("state") == "listening" and not rec.get("owed")
        if not idle():
            ctx.say("  waiting for %s's tutor to finish its turn" % rel)
        if not until(idle, DAEMON_WAIT, 2):
            raise Abort("%s's tutor did not come to rest in %d s" % (rel, DAEMON_WAIT))
        children = [p for p in processes() if p.ppid == proc.pid and "board wait" in p.cmd]
        ctx.add("killed", {"pid": proc.pid, "cmd": proc.cmd, "workspace": rel, "at": time.time(),
                           "children": [c.pid for c in children]})
        # SIGKILL: SIGTERM would start the old wrap-up turn, a model call.
        kill_group(proc, signal.SIGKILL)
        for c in children:
            kill_group(c, signal.SIGKILL)
        if not until(lambda: not any(alive(p) for p in [proc.pid] + [c.pid for c in children]), 10, 0.2):
            raise Abort("the daemon %d or its waiter outlived SIGKILL" % proc.pid)
        ctx.say("  killed %s's tutor (%d) and %d waiter(s)" % (rel, proc.pid, len(children)))
    # A waiter that timed out and was replaced between the listing and the
    # kill is an orphan now; every `board wait` is the old system's.
    strays = matching(r"board wait", ctx.scope)
    for p in strays:
        ctx.add("killed", {"pid": p.pid, "cmd": p.cmd, "workspace": None, "at": time.time(),
                           "children": []})
        kill_group(p, signal.SIGKILL)
    if strays:
        until(lambda: not any(alive(p.pid) for p in strays), 10, 0.2)
        ctx.say("  killed %d orphaned waiter(s)" % len(strays))
    boards =matching(r"serve\.py.*\s--root\b", ctx.scope)
    for proc in boards:
        root = argv_value(proc.cmd, "--root")
        port = argv_value(proc.cmd, "--port")
        ctx.add("old_boards", {"pid": proc.pid, "root": root,
                               "port": int(port) if port and port.isdigit() else None,
                               "cmd": proc.cmd})
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except OSError:
            pass
    if boards:
        until(lambda: not any(alive(p.pid) for p in boards), BOARD_TERM_WAIT, 0.5)
        for proc in boards:
            if alive(proc.pid):
                ctx.say("  board %d ignored SIGTERM; SIGKILL" % proc.pid)
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
        until(lambda: not any(alive(p.pid) for p in boards), 5, 0.2)
        ctx.say("  stopped %d board(s)" % len(boards))
    left = matching(OLD_NAMES, ctx.scope)
    if left:
        raise Abort("still running:\n  %s" % "\n  ".join(map(repr, left)))


# ---------------------------------------------------------------------------
# 3. snapshot
# ---------------------------------------------------------------------------
def tar_dir(ctx, src, dest):
    """Tar `src` (named by its basename) into `dest` and list it back."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    rc, out = run(["tar", "-cf", dest, "-C", os.path.dirname(src), os.path.basename(src)])
    if rc != 0:
        raise Abort("tar of %s failed: %s" % (src, out.strip()[-500:]))
    rc, out = run(["tar", "-tf", dest])
    if rc != 0 or not out.strip():
        raise Abort("the tar of %s does not read back" % src)
    ctx.m["tars"][ctx.rel(src)] = dest
    ctx.save()


def bundle(ctx, repo, dest):
    rc, out = git(repo, "bundle", "create", dest, "--all")
    if rc != 0:
        raise Abort("bundle of %s failed: %s" % (repo, out.strip()[-500:]))
    rc, out = git(repo, "bundle", "verify", dest)
    if rc != 0:
        raise Abort("the bundle of %s does not verify: %s" % (repo, out.strip()[-500:]))
    ctx.add("bundles", dest)


def step_snapshot(ctx):
    G, A = ctx.atlas, ctx.archive
    if ctx.tailscale == "real":
        rc, out = run(["tailscale", "serve", "status", "--json"], timeout=45)
        if rc != 0:
            raise Abort("tailscale serve status failed (rc %d): %s" % (rc, out.strip()[-300:]))
        try:
            capture = json.loads(out) if out.strip() else {}
        except ValueError:
            raise Abort("tailscale serve status --json printed no JSON: %s" % out[:300])
    else:
        capture = ctx.fake_capture or {}
    write_json(os.path.join(A, "tailscale-serve.json"), capture)
    ctx.put("tailscale", capture)
    ctx.say("  tailscale: %d mapping(s) captured" % len(ts_targets(capture)))
    # What install.sh deletes: the old agents' plists and the pull launcher.
    saved = os.path.join(A, "launchagents")
    os.makedirs(saved, exist_ok=True)
    for label in ctx.old_labels:
        src = os.path.join(ctx.agents_dir, label + ".plist")
        if os.path.isfile(src):
            dst = os.path.join(saved, label + ".plist")
            shutil.copy2(src, dst)
            ctx.add("saved_agents", {"from": dst, "to": src, "label": label})
    pull = os.path.join(ctx.bin_dir, "tutor-pull")
    if os.path.islink(pull):
        ctx.put("saved_pull", {"link": os.readlink(pull), "to": pull})
    elif os.path.isfile(pull):
        shutil.copy2(pull, os.path.join(saved, "tutor-pull"))
        ctx.put("saved_pull", {"file": os.path.join(saved, "tutor-pull"), "to": pull})
    bundle(ctx, G, os.path.join(A, "Atlas.bundle"))
    for name in course_repos(G):
        bundle(ctx, os.path.join(G, "courses", name), os.path.join(A, name + ".bundle"))
    ctx.say("  %d bundle(s) verified" % len(ctx.m["bundles"]))
    for rel, ws in workspaces(G):
        arch = os.path.join(ws, "live", "archive")
        if os.path.isdir(arch):
            tar_dir(ctx, arch, os.path.join(A, "live-archive", rel.replace("/", "-") + ".tar"))
    for name in course_dirs(G):
        course = os.path.join(G, "courses", name)
        tr = os.path.join(course, "transcripts")
        if os.path.isdir(tr):
            tar_dir(ctx, tr, os.path.join(A, "transcripts", name + ".tar"))
        tar_dir(ctx, course, os.path.join(A, "courses", name + ".tar"))
    ctx.say("  %d tar(s) written and read back" % len(ctx.m["tars"]))


# ---------------------------------------------------------------------------
# 4. info/exclude
# ---------------------------------------------------------------------------
def exclude_file(atlas):
    path = git_ok(atlas, "rev-parse", "--git-path", "info/exclude").strip()
    return path if os.path.isabs(path) else os.path.join(atlas, path)


def step_exclude(ctx):
    path = exclude_file(ctx.atlas)
    # Everything untracked or ignored now: a rollback sweeps aside what
    # was not here.
    ctx.put("before", untracked_set(ctx.atlas))
    try:
        with open(path, encoding="utf-8") as fh:
            have = fh.read()
    except OSError:
        have = ""
    lines = have.splitlines()
    add = [l for l in EXCLUDE_LINES if l not in lines]
    if not add:
        return
    ctx.put("exclude_added", add)
    ctx.put("exclude_had_newline", have.endswith("\n") or not have)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        if have and not have.endswith("\n"):
            fh.write("\n")
        for l in add:
            fh.write(l + "\n")
    ctx.say("  %s += %s" % (ctx.rel(path), ", ".join(add)))


# ---------------------------------------------------------------------------
# 5. import every live/
# ---------------------------------------------------------------------------
def step_import(ctx):
    G = ctx.atlas
    script = os.path.join(ctx.tools(), "scripts", "import-live.py")
    env = ctx.environ(TUTORBOARD_COURSES=G)
    for rel, ws in workspaces(G):
        subject = post_merge(rel)
        rec = {"workspace": rel, "subject": subject, "session": None}
        ctx.add("imports", rec)
        rc, out = run([ctx.python, script, "--atlas", G, "--workspace", ws,
                       "--subject", subject, "--manifest", ctx.m["import_manifest"]],
                      cwd=G, env=env, timeout=600)
        ctx.say("  " + out.strip().replace("\n", "\n  "))
        if rc != 0:
            raise Abort("import of %s failed" % rel)
        m = re.search(r"-> session (\S+)", out)
        rec["session"] = m.group(1) if m else None
        ctx.save()
        live = os.path.join(ws, "live")
        arch = os.path.join(live, "archive")
        if os.path.isdir(arch):
            if ctx.rel(arch) not in ctx.m["tars"]:
                raise Abort("%s was never tarred" % ctx.rel(arch))
            ctx.add("removed_trees", {"path": arch, "tar": ctx.m["tars"][ctx.rel(arch)]})
            shutil.rmtree(arch)
        if os.path.isdir(live):
            if os.listdir(live):
                raise Abort("%s still holds %s after the import" % (ctx.rel(live), os.listdir(live)))
            ctx.add("removed_trees", {"path": live, "dirs": []})
            os.rmdir(live)
    stray = os.path.join(G, "live")
    if os.path.isdir(stray):
        if has_files(stray):
            raise Abort("%s holds files" % stray)
        ctx.add("removed_trees", {"path": stray, "dirs": dirs_of(stray)})
        shutil.rmtree(stray)
    # The sessions as imported: the new server writes into them (read marks,
    # turns), and a rollback reverses the import from this copy.
    if os.path.isdir(os.path.join(G, "sessions")):
        tar_dir(ctx, os.path.join(G, "sessions"), os.path.join(ctx.archive, "sessions-imported.tar"))
    # What the import moved out of the tracked tree comes back, so the tree
    # is clean for the merge; the merge then deletes it.
    gone = [p for c, p in status_entries(G, "--untracked-files=no") if "D" in c]
    if gone:
        ctx.put("restored_tracked", gone)
        for i in range(0, len(gone), 200):
            git_ok(G, "checkout", "--", *gone[i:i + 200])
        ctx.say("  restored %d tracked file(s) the import moved" % len(gone))
    left = git_ok(G, "status", "--porcelain", "--untracked-files=no").strip()
    if left:
        raise Abort("tracked changes after the import:\n%s" % left[:2000])


# ---------------------------------------------------------------------------
# 6. course repositories
# ---------------------------------------------------------------------------
def move(ctx, src, dst, kind):
    if os.path.lexists(dst):
        raise Abort("%s is already there" % dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    ctx.add("moves", {"kind": kind, "from": src, "to": dst, "done": False})
    os.rename(src, dst)
    ctx.m["moves"][-1]["done"] = True
    ctx.save()


def step_courses(ctx):
    for name in course_repos(ctx.atlas):
        course = os.path.join(ctx.atlas, "courses", name)
        move(ctx, os.path.join(course, ".git"),
             os.path.join(ctx.archive, "courses-git", name + ".git"), "course-git")
        tr = os.path.join(course, "transcripts")
        if os.path.isdir(tr):
            if ctx.rel(tr) not in ctx.m["tars"]:
                raise Abort("%s was never tarred" % ctx.rel(tr))
            ctx.add("removed_trees", {"path": tr, "tar": ctx.m["tars"][ctx.rel(tr)]})
            shutil.rmtree(tr)
        ctx.say("  courses/%s: .git archived, transcripts removed" % name)


# ---------------------------------------------------------------------------
# 7. merge
# ---------------------------------------------------------------------------
def step_merge(ctx):
    G = ctx.atlas
    ctx.put("merging", True)
    rc, out = git(G, "-c", "core.hooksPath=%s" % os.path.join(G, ".githooks"),
                  "merge", "--no-ff", "-m", MERGE_MSG, ctx.ref, env=ctx.environ())
    if rc != 0:
        gitdir = git_ok(G, "rev-parse", "--absolute-git-dir").strip()
        if os.path.exists(os.path.join(gitdir, "MERGE_HEAD")):
            git(G, "merge", "--abort")
        raise Abort("the merge failed:\n%s" % out.strip()[-3000:])
    ctx.put("merged", git_ok(G, "rev-parse", "HEAD").strip())
    ctx.say("  merged: %s" % ctx.m["merged"][:12])


# ---------------------------------------------------------------------------
# 8. residue
# ---------------------------------------------------------------------------
def step_residue(ctx):
    G = ctx.atlas
    for code, path in status_entries(G):
        if code == "??" and path.startswith("courses/"):
            move(ctx, os.path.join(G, path.rstrip("/")),
                 os.path.join(ctx.archive, "pre-fold", path.rstrip("/")), "pre-fold")
            ctx.say("  pre-fold: %s" % path)
    script = os.path.join(G, "board", "scripts", "move-residue.sh")
    for parent in ("research", "practice"):
        top = os.path.join(G, parent)
        if not os.path.isdir(top):
            continue
        for name in sorted(os.listdir(top)):
            old = os.path.join(top, name)
            if not os.path.isdir(old) or os.path.islink(old):
                continue
            new = os.path.join(G, "projects", name)
            if not os.path.isdir(new):
                raise Abort("%s has no projects/%s to move into" % (ctx.rel(old), name))
            rc, out = run(["bash", script, old, new], cwd=G, env=ctx.environ())
            dry = os.path.join(ctx.archive, "residue", "%s-%s.dry.log" % (parent, name))
            os.makedirs(os.path.dirname(dry), exist_ok=True)
            with open(dry, "w", encoding="utf-8") as fh:
                fh.write(out)
            if rc != 0:
                raise Abort("move-residue refused %s:\n%s" % (ctx.rel(old), out.strip()[-1500:]))
            log = os.path.join(ctx.archive, "residue", "%s-%s.log" % (parent, name))
            ctx.add("residue_logs", {"log": log, "old": old, "new": new})
            with open(log, "w", encoding="utf-8") as fh:
                p = subprocess.run(["bash", script, old, new, "--apply"], cwd=G,
                                   env=ctx.environ(), stdout=fh, stderr=subprocess.PIPE,
                                   universal_newlines=True)
            if p.returncode != 0:
                raise Abort("move-residue --apply failed on %s: %s"
                            % (ctx.rel(old), p.stderr.strip()[-1500:]))
            ctx.say("  %s -> projects/%s (%s)" % (ctx.rel(old), name, p.stderr.strip()
                                                  or open(log).read().strip().splitlines()[-1:]))
    for rel in UV_PROJECTS:
        d = os.path.join(G, rel)
        if not os.path.isfile(os.path.join(d, "pyproject.toml")):
            continue
        ctx.add("uv", rel)
        rc, out = run(["uv", "sync"], cwd=d, env=ctx.environ(), timeout=1800)
        if rc != 0:
            raise Abort("uv sync failed in %s:\n%s" % (rel, out.strip()[-1500:]))
        ctx.say("  uv sync: %s" % rel)
    mig = os.path.join(G, "board", "scripts", "migrate-artifacts.py")
    if os.path.isfile(mig):
        for how in ("--apply-ink", "--rebuild"):
            rc, out = run([ctx.python, mig, how, G], cwd=G, env=ctx.environ(), timeout=3600)
            with open(os.path.join(ctx.archive, "migrate-artifacts%s.log" % how), "w") as fh:
                fh.write(out)
            if rc != 0:
                raise Abort("migrate-artifacts %s failed:\n%s" % (how, out.strip()[-1500:]))
            ctx.say("  migrate-artifacts %s: %s" % (how, (out.strip().splitlines() or ["ok"])[-1]))
    left = git_ok(G, "status", "--porcelain").strip()
    if left:
        raise Abort("git status is not empty after the residue:\n%s" % left[:2000])


# ---------------------------------------------------------------------------
# 9. install
# ---------------------------------------------------------------------------
def render_plist(ctx):
    """The rehearsal's LaunchAgent: install.sh's own rendering, on port 8779,
    under the rehearsal's label and HOME."""
    env = ctx.environ(TUTORBOARD_LABEL=ctx.label, PYTHON=ctx.python,
                      TUTORBOARD_LOG=os.path.join(ctx.archive, "server.log"))
    rc, out = run(["bash", os.path.join(ctx.atlas, "board", "install.sh"), "--plist",
                   "--port", str(ctx.port)], env=env)
    if rc != 0:
        raise Abort("install.sh --plist failed: %s" % out[-500:])
    job = plistlib.loads(out.encode("utf-8"))
    job["EnvironmentVariables"].update(dict((k, v) for k, v in ctx.env.items()
                                            if k != "PATH"))
    if "PATH" in ctx.env:
        job["EnvironmentVariables"]["PATH"] = ctx.env["PATH"]
    dst = os.path.join(ctx.agents_dir, ctx.label + ".plist")
    os.makedirs(ctx.agents_dir, exist_ok=True)
    with open(dst, "wb") as fh:
        plistlib.dump(job, fh)
    return dst


def ts_apply(ctx, cmds, what):
    for cmd in cmds:
        if ctx.tailscale != "real":
            ctx.say("  tailscale plan (%s): %s" % (what, " ".join(cmd)))
            continue
        rc, out = run(cmd, timeout=60)
        ctx.say("  %s -> rc %d %s" % (" ".join(cmd), rc, out.strip()[-200:]))
        if rc != 0:
            raise Abort("%s failed: %s" % (" ".join(cmd), out.strip()[-300:]))


WAITING = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from tutorboard import sessions
from tutorboard.lesson import inbox
from tutorboard.runner import daemon
out = {}
for sid in sys.argv[3:]:
    st = daemon.agent_record_at(sessions.path(sid, sys.argv[2])) or {}
    out[sid] = bool(isinstance(st.get("owed"), str)
                    or inbox.waiting(sessions.repo(sid, sys.argv[2])))
print(json.dumps(out))
"""


def baseline(ctx):
    """Before anything serves: each imported session's cards, its log's
    length, and whether it holds a message the server will answer at once
    (the runner's own test in `recover`)."""
    sids = [r["session"] for r in ctx.m["imports"] if r.get("session")]
    rc, out = run([ctx.python, "-c", WAITING, os.path.join(ctx.atlas, "board"), ctx.atlas]
                  + sids, cwd=ctx.atlas, env=ctx.environ(TUTORBOARD_COURSES=ctx.atlas))
    try:
        waiting = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Abort("could not read the imported sessions' inboxes: %s" % out[-800:])
    ctx.put("baseline", dict((s, {"cards": len(cards_of(ctx, s)), "log": log_size(ctx, s),
                                  "waiting": bool(waiting.get(s))}) for s in sids))


def step_install(ctx):
    G = ctx.atlas
    baseline(ctx)
    if ctx.mode == "run":
        ctx.put("installed", os.path.join(ctx.agents_dir, ctx.label + ".plist"))
        rc, out = run(["bash", os.path.join(G, "board", "install.sh")], cwd=G,
                      env=ctx.environ(), timeout=600)
        with open(os.path.join(ctx.archive, "install.log"), "w") as fh:
            fh.write(out)
        ctx.say("  " + "\n  ".join(l for l in out.splitlines() if l.strip().startswith(("ok", "----"))))
        if rc != 0:
            raise Abort("install.sh failed:\n%s" % out[-1500:])
    else:
        ctx.put("installed", render_plist(ctx))
        ctx.say("  rendered %s" % ctx.m["installed"])
    for t in ts_targets(ctx.m.get("tailscale")):
        ctx.say("  tailscale: removing %s %s -> %s" % (t[0], t[1], t[2]))
    ctx.put("tailscale_changed", True)
    ts_apply(ctx, ts_publish(ctx.port), "publish")
    if ctx.tailscale == "real":
        rc, out = run(["tailscale", "serve", "status", "--json"], timeout=45)
        try:
            now = json.loads(out) if out.strip() else {}
        except ValueError:
            now = None
        wrong = ts_only(now, ctx.port) if now is not None else ["no JSON: %s" % out[:200]]
        if rc != 0 or wrong:
            raise Abort("tailscale serve does not list only %d: %s" % (ctx.port, wrong))
        ctx.say("  tailscale serves only %d" % ctx.port)


# ---------------------------------------------------------------------------
# 10. start and prove
# ---------------------------------------------------------------------------
def cards_of(ctx, sid):
    d = os.path.join(ctx.atlas, "sessions", sid, "cards")
    try:
        return sorted(n for n in os.listdir(d) if n.endswith(".md"))
    except OSError:
        return []


def log_size(ctx, sid):
    try:
        return os.path.getsize(os.path.join(ctx.atlas, "sessions", sid, "agent.log"))
    except OSError:
        return 0


def wrapups_since(ctx, sid, offset):
    """Any wrap-up the session wrote since `offset` in its agent.log."""
    found = []
    try:
        with open(os.path.join(ctx.atlas, "sessions", sid, "agent.log"), "rb") as fh:
            fh.seek(offset)
            tail = fh.read().decode("utf-8", "replace")
        if re.search(r"=== .* handoff ===", tail):
            found.append("agent.log")
    except OSError:
        pass
    if os.path.isdir(os.path.join(ctx.atlas, "sessions", sid, "handoffs")):
        found.append("handoffs/")
    return found


def server_procs(ctx):
    return matching(r"serve\.py", ctx.scope)


def own_servers(ctx):
    """This Atlas's new server processes: never an old --root board, and in a
    real run never another checkout's test server."""
    return [p for p in server_procs(ctx) if "--root" not in p.cmd
            and (ctx.scope is not None or os.path.join(ctx.atlas, "board", "serve.py") in p.cmd)]


def step_prove(ctx):
    if not loaded(ctx.label):
        ctx.put("bootstrapped", True)
        ok, out = bootstrap(ctx.m["installed"], ctx.label)
        if not ok:
            raise Abort("%s did not load: %s" % (ctx.label, out.strip()))
    ctx.put("bootstrapped", True)
    if not until(lambda: http(ctx.port, "/health")[0] == 200, 120, 1):
        raise Abort("/health on %d did not answer in 120 s" % ctx.port)
    ctx.say("  /health answers on %d" % ctx.port)
    until(lambda: len(server_procs(ctx)) == 1, 20, 1)
    procs = server_procs(ctx)
    if len(procs) != 1:
        raise Abort("%d serve.py processes, not 1: %s" % (len(procs), procs))
    labels = launchctl_count(ctx.label)
    if labels != 1:
        raise Abort("launchctl list shows %d %s label(s), not 1" % (labels, ctx.label))
    ctx.say("  one serve.py, one %s label" % ctx.label)
    status, listing = http(ctx.port, "/sessions.json")
    have = set(s.get("id") for s in (listing.get("sessions") or []))
    want = [r["session"] for r in ctx.m["imports"] if r.get("session")]
    missing = [s for s in want if s not in have]
    if status != 200 or missing:
        raise Abort("/sessions.json (%s) lacks imported session(s) %s" % (status, missing))
    ctx.say("  /sessions.json lists all %d imported session(s)" % len(want))
    base = ctx.m["baseline"]
    offsets = dict((s, base[s]["log"]) for s in want)
    before = dict((s, base[s]["cards"]) for s in want)
    owed = [s for s in want if base[s]["waiting"]]
    if owed:
        targets = owed
        ctx.say("  waiting for the unread message(s) in %s" % ", ".join(owed))
    else:
        prob = [r["session"] for r in ctx.m["imports"]
                if r.get("session") and r["subject"] == "courses/Probability"]
        targets = prob[:1] or want[:1]
        if not targets:
            raise Abort("no imported session to send the cutover check to")
        before[targets[0]] = len(cards_of(ctx, targets[0]))
        status, got = http(ctx.port, "/s/%s/say" % targets[0], {"text": CHECK_SAY})
        if status != 200:
            raise Abort("/say to %s answered %s %s" % (targets[0], status, got))
        ctx.say("  asked %s: %r" % (targets[0], CHECK_SAY))
    for sid in targets:
        if not until(lambda: len(cards_of(ctx, sid)) > before[sid], ANSWER_WAIT, 2):
            raise Abort("no new card in %s within %d s" % (sid, ANSWER_WAIT))
    time.sleep(8)
    for sid in want:
        grew = len(cards_of(ctx, sid)) - before[sid]
        if grew != (1 if sid in targets else 0):
            raise Abort("%s gained %d card(s)" % (sid, grew))
        wrap = wrapups_since(ctx, sid, offsets[sid])
        if wrap:
            raise Abort("%s wrote a wrap-up (%s)" % (sid, ", ".join(wrap)))
    ctx.say("  answered with one card; no duplicate and no wrap-up")
    rc, out = run([ctx.python, os.path.join(ctx.atlas, "board", "test", "run.py"),
                   "--guards"], cwd=ctx.atlas, env=ctx.environ(), timeout=1800)
    with open(os.path.join(ctx.archive, "guards.log"), "w") as fh:
        fh.write(out)
    if rc != 0:
        raise Abort("the guards failed:\n%s" % out[-2000:])
    ctx.say("  guards: %s" % (out.strip().splitlines() or ["passed"])[-1])


# ---------------------------------------------------------------------------
# 11. push
# ---------------------------------------------------------------------------
def step_push(ctx):
    code = ("import sys; sys.path.insert(0, %r); from tutorboard import gitops; "
            "ok, said = gitops.push(%r); print(said); sys.exit(0 if ok else 1)"
            % (os.path.join(ctx.atlas, "board"), ctx.atlas))
    rc, out = run([ctx.python, "-c", code], cwd=ctx.atlas, env=ctx.environ(), timeout=600)
    ctx.say("  " + out.strip())
    if rc != 0:
        return False
    ctx.put("pushed", True)
    return True


STEPS = [(1, "preflight", step_preflight), (2, "stop the old system", step_stop),
         (3, "snapshot", step_snapshot), (4, "info/exclude", step_exclude),
         (5, "import", step_import), (6, "course repositories", step_courses),
         (7, "merge", step_merge), (8, "residue", step_residue),
         (9, "install", step_install), (10, "start and prove", step_prove)]


def cutover(ctx):
    """Steps 1-10. `None`, or the failure's text."""
    for n, name, fn in STEPS:
        ctx.say("== %d. %s" % (n, name))
        ctx.step(n, name, "started")
        try:
            fn(ctx)
        except Abort as exc:
            ctx.step(n, name, "failed")
            ctx.put("failure", "%d. %s: %s" % (n, name, exc))
            return "step %d (%s): %s" % (n, name, exc)
        except Exception as exc:                         # noqa: BLE001
            ctx.step(n, name, "failed")
            ctx.put("failure", "%d. %s: %r" % (n, name, exc))
            return "step %d (%s) raised %r" % (n, name, exc)
        ctx.step(n, name, "done")
    return None


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------
def reverse_residue(log_path, old, new):
    """Undo one move-residue.sh --apply log, bottom-up. Problems as a list."""
    problems = []
    try:
        with open(log_path, encoding="utf-8") as fh:
            lines = [l.rstrip("\n").split("\t") for l in fh if "\t" in l]
    except OSError:
        return []
    old_l, new_l = old, new
    for parts in reversed(lines):
        op = parts[0]
        if op == "moved" and len(parts) == 3:
            src, dst = parts[1], parts[2]
            if os.path.lexists(dst) and not os.path.lexists(src):
                os.makedirs(os.path.dirname(src), exist_ok=True)
                os.rename(dst, src)
            elif not os.path.lexists(src):
                problems.append("residue %s is at neither end" % src)
        elif op == "env" and len(parts) == 3:
            # The file is back at its old path by now only if its `moved`
            # line came after; env lines follow their move, so it is at dst.
            path, key = parts[1], parts[2]
            for f in (path, path.replace(new, old, 1)):
                if os.path.isfile(f):
                    unenv(f, key, new, old)
        elif op == "rmdir" and len(parts) == 2:
            os.makedirs(parts[1], exist_ok=True)
    return problems


def unenv(path, key, new, old):
    """Swap `new` back to `old` at the start of `key`'s value."""
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    out = []
    for line in text.splitlines(True):
        m = re.match(r"^((?:export )?%s=)(['\"]?)(.*)$" % re.escape(key), line.rstrip("\r\n"))
        if m:
            body = m.group(3)
            if body.startswith(new) and (len(body) == len(new) or body[len(new)] in "/'\""):
                end = line[len(line.rstrip("\r\n")):]
                line = m.group(1) + m.group(2) + old + body[len(new):] + end
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(out))


def reverse_import(ctx, problems):
    path = ctx.m.get("import_manifest")
    if not path or not os.path.isfile(path):
        return
    recs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                recs.append(json.loads(line))
            except ValueError:
                pass
    pre = ctx.m.get("pre")
    tracked = set()
    if pre:
        tracked = set(git(ctx.atlas, "ls-tree", "-r", "--name-only", pre)[1].splitlines())
    # A file the import moved that git restored before the merge is in the
    # way of its own way back: it is tracked at PRE, so the reset returns it.
    for rec in recs:
        if rec.get("op") == "move":
            src, dst = rec.get("from"), rec.get("to")
            if (src and dst and os.path.isfile(src) and os.path.lexists(dst)
                    and ctx.rel(src) in tracked):
                os.remove(src)
    env = ctx.environ(TUTORBOARD_COURSES=ctx.atlas)
    rc, out = run([ctx.python, os.path.join(ctx.tools(), "scripts", "import-live.py"),
                   "--reverse", path], env=env, timeout=600)
    ctx.say("  " + out.strip().replace("\n", "\n  "))
    for line in out.splitlines():
        if "problem:" in line and "is not empty; left in place" not in line:
            problems.append(line.strip())


def sweep(ctx, problems):
    """Anything untracked or ignored that was not here before the cutover
    goes to <archive>/rollback-leftovers/, never deleted."""
    before = ctx.m.get("before")
    if before is None:
        return
    before = set(before)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for path in untracked_set(ctx.atlas):
        if path in before:
            continue
        if any(path.startswith(b) for b in before if b.endswith("/")):
            continue
        if any(b.startswith(path) for b in before):
            problems.append("left in place, it holds what was here before: %s" % path)
            continue
        if fenced(path):
            problems.append("left in place, fenced: %s" % path)
            continue
        src = os.path.join(ctx.atlas, path.rstrip("/"))
        dst = os.path.join(ctx.archive, "rollback-leftovers", stamp, path.rstrip("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.rename(src, dst)
            ctx.say("  leftover moved aside: %s" % path)
        except OSError as exc:
            problems.append("could not move aside %s: %s" % (path, exc))


def rollback(ctx):
    """Undo what the manifest records. `[]`, or the problems left."""
    m = ctx.m
    if m.get("pushed"):
        raise Abort("main was pushed; a rollback is no longer valid")
    G = ctx.atlas
    problems = []
    ctx.say("== rollback")
    # R1. the new agent off
    if m.get("installed") or m.get("bootstrapped") or loaded(ctx.label):
        if loaded(ctx.label):
            gone, out = bootout(ctx.label)
            if not gone:
                problems.append("%s is still loaded: %s" % (ctx.label, out.strip()))
        if m.get("installed") and os.path.isfile(m["installed"]):
            os.remove(m["installed"])
        until(lambda: not own_servers(ctx), 15, 0.5)
        for p in own_servers(ctx):
            try:
                os.kill(p.pid, signal.SIGKILL)
            except OSError:
                pass
        ctx.say("  %s booted out" % ctx.label)
    # R2. tailscale
    if m.get("tailscale_changed"):
        try:
            ts_apply(ctx, ts_restore(m.get("tailscale") or {}), "restore")
        except Abort as exc:
            problems.append(str(exc))
    # R3. residue, newest first, and what step 8 set aside
    for rec in reversed(m.get("residue_logs") or []):
        problems += reverse_residue(rec["log"], rec["old"], rec["new"])
    for rec in reversed(m.get("moves") or []):
        if rec["kind"] == "pre-fold" and os.path.lexists(rec["to"]) \
                and not os.path.lexists(rec["from"]):
            os.makedirs(os.path.dirname(rec["from"]), exist_ok=True)
            os.rename(rec["to"], rec["from"])
    # R4. the sessions as imported, the import reversed from them, then git
    # back to PRE. What the new server wrote is kept aside.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    snap = (m.get("tars") or {}).get("sessions")
    top = os.path.join(G, "sessions")
    if snap and os.path.isdir(top):
        aside = os.path.join(ctx.archive, "rollback-leftovers", stamp, "sessions-served")
        os.makedirs(os.path.dirname(aside), exist_ok=True)
        os.rename(top, aside)
        rc, out = run(["tar", "-xpf", snap, "-C", G])
        if rc != 0:
            problems.append("restore of sessions/ as imported failed: %s" % out.strip())
        ctx.say("  sessions/ put back as imported; the served copy is in %s" % aside)
    reverse_import(ctx, problems)
    gitdir = git(G, "rev-parse", "--absolute-git-dir")[1].strip()
    if os.path.exists(os.path.join(gitdir, "MERGE_HEAD")):
        git(G, "merge", "--abort")
    if m.get("pre"):
        rc, out = git(G, "reset", "--hard", m["pre"])
        if rc != 0:
            problems.append("git reset --hard %s: %s" % (m["pre"], out.strip()))
        else:
            ctx.say("  main reset to %s" % m["pre"][:12])
    # R5. each course from its tar, .git and transcripts included
    for rel, tar in sorted((m.get("tars") or {}).items()):
        if not (rel.startswith("courses/") and rel.count("/") == 1):
            continue
        course = os.path.join(G, rel)
        if os.path.lexists(course):
            aside = os.path.join(ctx.archive, "rollback-replaced", stamp, rel)
            os.makedirs(os.path.dirname(aside), exist_ok=True)
            os.rename(course, aside)
        rc, out = run(["tar", "-xpf", tar, "-C", os.path.dirname(course)])
        if rc != 0:
            problems.append("restore of %s failed: %s" % (rel, out.strip()))
        else:
            ctx.say("  %s restored from its tar" % rel)
    for rec in m.get("moves") or []:
        if rec["kind"] == "course-git" and os.path.lexists(rec["to"]) \
                and not os.path.lexists(rec["from"]):
            os.rename(rec["to"], rec["from"])
    # R6. live/archive (and the empty trees) back
    for rec in reversed(m.get("removed_trees") or []):
        path = rec["path"]
        if os.path.lexists(path):
            continue
        if rec.get("tar"):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            rc, out = run(["tar", "-xpf", rec["tar"], "-C", os.path.dirname(path)])
            if rc != 0:
                problems.append("restore of %s failed: %s" % (path, out.strip()))
        else:
            os.makedirs(path, exist_ok=True)
            for d in rec.get("dirs") or []:
                os.makedirs(os.path.join(path, d), exist_ok=True)
    # What the new system made and nothing above took back.
    sweep(ctx, problems)
    # R7. info/exclude
    added = m.get("exclude_added") or []
    if added:
        path = exclude_file(G)
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines(True)
        for l in added:
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].rstrip("\n") == l:
                    del lines[i]
                    break
        text = "".join(lines)
        if not m.get("exclude_had_newline", True) and text.endswith("\n"):
            text = text[:-1]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    # R8. the old agents, and the old boards they bring back
    for rec in m.get("saved_agents") or []:
        if not os.path.isfile(rec["to"]):
            shutil.copy2(rec["from"], rec["to"])
    pull = m.get("saved_pull")
    if pull and not os.path.lexists(pull["to"]):
        if pull.get("link"):
            os.symlink(pull["link"], pull["to"])
        elif pull.get("file"):
            shutil.copy2(pull["file"], pull["to"])
    for label in m.get("booted_out") or []:
        if not loaded(label):
            plist = os.path.join(ctx.agents_dir, label + ".plist")
            ok, out = bootstrap(plist, label)
            if not ok:
                problems.append("%s did not load again: %s" % (label, out.strip()))
            else:
                ctx.say("  %s loaded again" % label)
    ports = [b["port"] for b in m.get("old_boards") or [] if b.get("port")]
    if ports:
        up = until(lambda: all(http(p, "/health", timeout=5)[0] == 200 for p in ports),
                   180, 2)
        if up:
            ctx.say("  the old boards answer on %s" % ", ".join(map(str, ports)))
        else:
            problems.append("old boards not answering: %s" % [
                p for p in ports if http(p, "/health", timeout=5)[0] != 200])
    # R9. the environments uv re-synced at the new paths, back at the old
    if m.get("uv") and m.get("residue_logs"):
        for rec in m["residue_logs"]:
            old = rec["old"]
            if os.path.isfile(os.path.join(old, "pyproject.toml")) and \
                    os.path.isdir(os.path.join(old, ".venv")):
                rc, out = run(["uv", "sync"], cwd=old, env=ctx.environ(), timeout=1800)
                ctx.say("  uv sync at %s: rc %d" % (ctx.rel(old), rc))
    m["rolled_back"] = time.time()
    m["rollback_problems"] = problems
    ctx.save()
    for p in problems:
        ctx.say("  PROBLEM: %s" % p)
    return problems


# ---------------------------------------------------------------------------
# --plan
# ---------------------------------------------------------------------------
def plan(ctx):
    G = ctx.atlas
    say = print
    pre = git(G, "rev-parse", "HEAD")[1].strip()
    ref = git(G, "rev-parse", "--verify", "-q", ctx.ref)[1].strip()
    say("cutover plan for %s (nothing is changed)" % G)
    say("  main %s; merges %s %s; archive %s" % (pre[:12], ctx.ref, ref[:12] or "(missing)",
                                                 ctx.archive))
    say("1. preflight: tracked tree clean, course repos clean (%s), research/ and "
        "practice/ clean, courses match the fold, %s GB free"
        % (", ".join(course_repos(G)) or "none", int(shutil.disk_usage(G).free / 1024 ** 3)))
    procs = processes()
    say("2. stop: bootout %s; SIGKILL %d tutor daemon(s) and their waiters after each "
        "is listening with nothing owed; SIGTERM %d board(s)"
        % (", ".join(l for l in ctx.old_labels if loaded(l)) or "(none loaded)",
           len(matching(r"tutor headless", ctx.scope, procs)),
           len(matching(r"serve\.py.*\s--root\b", ctx.scope, procs))))
    for p in matching(OLD_NAMES, ctx.scope, procs):
        say("     %r" % p)
    say("3. snapshot: tailscale serve status --json; bundles of Atlas and %s; tars of "
        "every live/archive, transcripts and course directory" % (", ".join(course_repos(G)) or "-"))
    say("4. info/exclude += %s" % ", ".join(EXCLUDE_LINES))
    say("5. import:")
    for rel, _ in workspaces(G):
        say("     %s/live -> session bound to %s" % (rel, post_merge(rel)))
    if os.path.isdir(os.path.join(G, "live")):
        say("     the stray live/ is removed")
    say("6. courses/*/.git -> %s/courses-git/; transcripts/ removed" % ctx.archive)
    say("7. git merge --no-ff -m %r %s" % (MERGE_MSG, ctx.ref))
    say("8. residue: untracked courses/ leftovers -> pre-fold/; move-residue.sh for %s; "
        "uv sync in %s; migrate-artifacts --apply-ink, --rebuild"
        % (", ".join("%s/%s" % (p, n) for p in ("research", "practice")
                     if os.path.isdir(os.path.join(G, p))
                     for n in sorted(os.listdir(os.path.join(G, p)))) or "-",
           ", ".join(UV_PROJECTS)))
    say("9. install.sh; tailscale: %s" % "; ".join(" ".join(c) for c in ts_publish(ctx.port)))
    say("10. %s up; /health on %d; one serve.py; every imported session listed; the "
        "cutover check answered once; --guards" % (ctx.label, ctx.port))
    say("11. push main with gitops, never forced")
    say("rollback: --rollback %s" % ctx.manifest_path)
    return 0


# ---------------------------------------------------------------------------
# the rehearsal's fakes
# ---------------------------------------------------------------------------
FAKE_BOARD = r'''#!/usr/bin/env python3
# A stand-in for an old per-workspace board: serve.py --root <ws> --port <n>.
import json, os, signal, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
try:
    os.setsid()
except OSError:
    pass
root = sys.argv[sys.argv.index("--root") + 1]
port = int(sys.argv[sys.argv.index("--port") + 1])
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "root": root}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
HTTPServer(("127.0.0.1", port), H).serve_forever()
'''

FAKE_TUTOR = r'''#!/usr/bin/env python3
# A stand-in for bin/tutor: `tutor headless <name>` (with a `board wait`
# child), `tutor watch <boards.json>` (brings the boards up), never more.
import json, os, socket, subprocess, sys, time
try:
    os.setsid()
except OSError:
    pass
here = os.path.dirname(os.path.abspath(__file__))
def spawn(argv):
    subprocess.Popen(["/bin/sh", "-c", '"$@" >/dev/null 2>&1 &', "sh"] + argv).wait()
if sys.argv[1] == "headless":
    # The waiter is this daemon's child in a group of its own, as the old one was.
    subprocess.Popen([sys.executable, os.path.join(here, "board"), "wait", "--timeout",
                      "300"], start_new_session=True, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    while True:
        time.sleep(60)
elif sys.argv[1] == "watch":
    boards = json.load(open(sys.argv[2]))
    while True:
        for b in boards:
            s = socket.socket()
            try:
                s.connect(("127.0.0.1", b["port"]))
            except OSError:
                spawn([sys.executable, b["serve"], "--root", b["root"], "--port", str(b["port"])])
                time.sleep(1)
            finally:
                s.close()
        time.sleep(1)
'''

FAKE_WAIT = r'''#!/usr/bin/env python3
# A stand-in for `board wait`, and `tutor-pull`: it waits.
import time
while True:
    time.sleep(60)
'''

FAKE_UV = r'''#!/bin/sh
# A stand-in for uv: records the call.
echo "$(pwd) $*" >> "%(calls)s"
exit 0
'''

FAKE_PROVIDER = r'''#!/usr/bin/env python3
# The rehearsal's provider: writes one card for a message, writes and builds
# the meeting deck for its [writeup], and records every call.
import json, os, subprocess, sys, time
prompt = sys.argv[-1]
sid = os.path.basename(os.environ.get("TUTORBOARD_SESSION", ""))
rec = {"sid": sid, "t": time.time(), "cwd": os.getcwd(), "prompt": prompt[-4000:]}
def log(**kw):
    rec.update(kw)
    with open(%(calls)r, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
if "This session is ending now" in prompt:
    log(kind="handoff")
    sys.exit(0)
if "[writeup]" in prompt and "projects/Meetings/docs/meeting" in prompt:
    tex = os.path.join("projects", "Meetings", "docs", "meeting", "meeting.tex")
    with open(tex, "w") as fh:
        fh.write("\\documentclass{beamer}\n\\begin{document}\n"
                 "\\begin{frame}{The week}\nThe cutover rehearsal.\n\\end{frame}\n"
                 "\\end{document}\n")
    p = subprocess.run(["board", "build", tex], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    log(kind="meeting", rc=p.returncode, out=p.stdout[-1500:])
    sys.exit(0)
said = prompt.split("They just sent this:", 1)[-1].strip().splitlines()
p = subprocess.run(["board", "write", "lesson", "reply"],
                   input="Answer to %%s\n" %% (said[0][:120] if said else "?"),
                   universal_newlines=True, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT)
log(kind="turn", rc=p.returncode, out=p.stdout[-1500:])
'''


def write_exec(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o755)


def launch_detached(argv, log=os.devnull):
    """Start `argv` orphaned (no zombie of ours when it is killed)."""
    subprocess.Popen(["/bin/sh", "-c", '"$@" >>"$0" 2>&1 &', log] + argv,
                     start_new_session=True).wait()


def agent_plist(path, label, argv, keepalive):
    job = {"Label": label, "ProgramArguments": argv, "RunAtLoad": True,
           "KeepAlive": keepalive, "AbandonProcessGroup": True}
    with open(path, "wb") as fh:
        plistlib.dump(job, fh)
    return path


def clone_copy(src, dst):
    """A copy-on-write copy where APFS allows it, a plain one otherwise."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rc, out = run(["cp", "-Rpc", src, dst])
    if rc != 0:
        rc, out = run(["cp", "-Rp", src, dst])
    if rc != 0:
        raise Abort("copy of %s failed: %s" % (src, out.strip()[-300:]))


def copy_tree_into(src, dst):
    """Copy `src`'s entries into the existing `dst`, never a fenced name."""
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if name.lower() in FENCED and name != "inbox":
            continue
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.isdir(s) and not os.path.islink(s) and os.path.isdir(d):
            copy_tree_into(s, d)
        else:
            if os.path.lexists(d):
                if os.path.isdir(d) and not os.path.islink(d):
                    shutil.rmtree(d)
                else:
                    os.remove(d)
            clone_copy(s, d)


def compare_trees(a, b, skip_top=(".git",)):
    """Differences between two trees: `diff -r` with logs and caches
    ignored, symlinks compared as links."""
    out = []

    def walk(rel):
        pa, pb = os.path.join(a, rel), os.path.join(b, rel)
        na = set(os.listdir(pa)) if os.path.isdir(pa) else set()
        nb = set(os.listdir(pb)) if os.path.isdir(pb) else set()
        for name in sorted(na | nb):
            r = os.path.join(rel, name) if rel else name
            if not rel and name in skip_top:
                continue
            if COMPARE_SKIP.search(r):
                continue
            x, y = os.path.join(a, r), os.path.join(b, r)
            if name not in na or name not in nb:
                out.append("only in %s: %s" % ("rehearsal" if name in na else "pristine", r))
            elif os.path.islink(x) or os.path.islink(y):
                if not (os.path.islink(x) and os.path.islink(y)
                        and os.readlink(x) == os.readlink(y)):
                    out.append("link differs: %s" % r)
            elif os.path.isdir(x) and os.path.isdir(y):
                walk(r)
            elif os.path.isdir(x) or os.path.isdir(y):
                out.append("type differs: %s" % r)
            elif not filecmp.cmp(x, y, shallow=False):
                out.append("differs: %s" % r)
    walk("")
    return out


class Rehearsal(object):
    """A copy of this Mac's Atlas with fakes for everything that is not."""

    def __init__(self, real, scratch, ref, keep=False):
        self.real = os.path.realpath(real)
        self.scratch = os.path.realpath(scratch)
        self.ref = ref
        self.keep = keep
        self.prefix = "tutor-board-rehearse-%d" % os.getpid()
        self.atlas = os.path.join(self.scratch, "Atlas")
        self.pristine = os.path.join(self.scratch, "pristine")
        self.home = os.path.join(self.scratch, "home")
        self.fake = os.path.join(self.scratch, "fake")
        self.agents = os.path.join(self.scratch, "LaunchAgents")
        self.calls = os.path.join(self.scratch, "provider-calls.jsonl")
        self.uv_calls = os.path.join(self.scratch, "uv-calls.txt")
        self.results = []

    def check(self, name, ok, detail=""):
        self.results.append((name, bool(ok)))
        print("%s %s%s" % ("ok  " if ok else "FAIL", name,
                           ("\n       " + str(detail)[:3000]) if (detail and not ok) else ""),
              flush=True)
        return ok

    # -- the copy ---------------------------------------------------------------
    def build(self):
        if os.path.exists(self.scratch) and os.listdir(self.scratch):
            raise Abort("%s is not empty" % self.scratch)
        # 8779, unless a test elsewhere holds it: then any free port.
        self.port = REHEARSE_PORT if port_free(REHEARSE_PORT) else free_port()
        if self.port != REHEARSE_PORT:
            print("   port %d is in use; the rehearsal serves on %d" % (REHEARSE_PORT, self.port))
        os.makedirs(self.scratch, exist_ok=True)
        print("== building the copy in %s" % self.scratch, flush=True)
        origin = os.path.join(self.scratch, "origin.git")
        git_ok(self.scratch, "clone", "-q", "--bare", self.real, origin)
        sha = git_ok(self.real, "rev-parse", self.ref + "^{commit}").strip()
        git_ok(origin, "update-ref", "refs/heads/overhaul", sha)
        git_ok(self.scratch, "clone", "-q", "-b", "main", origin, self.atlas)
        git_ok(self.atlas, "branch", "overhaul", "origin/overhaul")
        name = git(self.real, "config", "user.name")[1].strip() or "Rehearsal"
        email = git(self.real, "config", "user.email")[1].strip() or "rehearsal@localhost"
        git_ok(self.atlas, "config", "user.name", name)
        git_ok(self.atlas, "config", "user.email", email)
        # The worktree protocol's private links, excluded as in the real one.
        for rel in ("ai-config", "board/node_modules"):
            src = os.path.join(self.real, rel)
            if os.path.isdir(src):
                os.symlink(src, os.path.join(self.atlas, rel))
        with open(exclude_file(self.atlas), "a") as fh:
            fh.write("/ai-config\n/board/node_modules\n")
        # Every live/ and every course directory, as they are on this Mac.
        for rel, ws in workspaces(self.real):
            copy_tree_into(os.path.join(ws, "live"), os.path.join(self.atlas, rel, "live"))
        stray = os.path.join(self.real, "live")
        if os.path.isdir(stray):
            copy_tree_into(stray, os.path.join(self.atlas, "live"))
        for name in course_dirs(self.real):
            copy_tree_into(os.path.join(self.real, "courses", name),
                           os.path.join(self.atlas, "courses", name))
        # Residue: small dummies where the real ones are large or private.
        A = self.atlas
        dummies = {
            "research/TRD-EHR/.venv/pyvenv.cfg": "home = /usr/bin\n",
            "research/TRD-EHR/.env": "TRD_DATA=%s/research/TRD-EHR/data-root\nTOKEN_NAME=x\n" % A,
            "research/TRD-EHR/results/dummy.txt": "not patient data\n",
            "research/PSYCH-ASR/.venv/pyvenv.cfg": "home = /usr/bin\n",
            "research/PSYCH-ASR/phi/README": "a dummy; nothing real is ever copied\n",
            "practice/Lean-Theorem-Proving/.lake/build/dummy.olean": "x\n",
            "projects/libr-local-llm/.venv/pyvenv.cfg": "home = /usr/bin\n",
        }
        for rel, text in dummies.items():
            if os.path.isdir(os.path.join(A, rel.split("/")[0], rel.split("/")[1])):
                p = os.path.join(A, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w") as fh:
                    fh.write(text)
        # The fakes.
        write_exec(os.path.join(self.fake, "serve.py"), FAKE_BOARD)
        write_exec(os.path.join(self.fake, "bin", "tutor"), FAKE_TUTOR)
        write_exec(os.path.join(self.fake, "bin", "board"), FAKE_WAIT)
        write_exec(os.path.join(self.fake, "bin", "tutor-pull"), FAKE_WAIT)
        write_exec(os.path.join(self.fake, "uvbin", "uv"), FAKE_UV % {"calls": self.uv_calls})
        provider = os.path.join(self.fake, "provider")
        write_exec(provider, FAKE_PROVIDER % {"calls": self.calls})
        conf = os.path.join(self.home, ".config", "tutor-board", "config.json")
        os.makedirs(os.path.dirname(conf))
        write_json(conf, {"provider": "fake", "vision_agent": "fake", "concurrency": 2,
                          "headless_timeout": 120, "doing_timeout": 180,
                          "handoff_timeout": 60,
                          "agents": {"fake": {"cmd": [provider], "label": "Fake",
                                              "headless_first": [provider, "{prompt}"],
                                              "usage": "none"}}})
        hb = os.path.join(self.home, ".local", "bin")
        os.makedirs(hb)
        os.symlink(os.path.join(A, "board", "bin", "board"), os.path.join(hb, "board"))
        os.symlink(os.path.join(A, "board", "bin", "tutor"), os.path.join(hb, "tutor"))
        os.symlink(os.path.join(self.fake, "bin", "tutor-pull"), os.path.join(hb, "tutor-pull"))
        # The old system: two agents, three boards, three tutor daemons.
        os.makedirs(self.agents)
        self.boards = []
        for rel in ("courses/Galois-Theory", "courses/Probability", "research/TRD-EHR"):
            if os.path.isdir(os.path.join(A, rel, "live")):
                self.boards.append({"root": os.path.join(A, rel), "port": free_port(),
                                    "serve": os.path.join(self.fake, "serve.py")})
        with open(os.path.join(self.fake, "boards.json"), "w") as fh:
            json.dump(self.boards, fh)
        py = sys.executable
        watch = agent_plist(os.path.join(self.agents, self.prefix + ".tutor-watch.plist"),
                            self.prefix + ".tutor-watch",
                            [py, os.path.join(self.fake, "bin", "tutor"), "watch",
                             os.path.join(self.fake, "boards.json")], True)
        pull = agent_plist(os.path.join(self.agents, self.prefix + ".tutor-pull.plist"),
                           self.prefix + ".tutor-pull",
                           [py, os.path.join(self.fake, "bin", "tutor-pull")], False)
        for plist, label in ((watch, self.prefix + ".tutor-watch"),
                             (pull, self.prefix + ".tutor-pull")):
            ok, out = bootstrap(plist, label)
            if not ok:
                raise Abort("could not load %s: %s" % (label, out))
        up = until(lambda: all(http(b["port"], "/health", timeout=3)[0] == 200
                               for b in self.boards), 60, 1)
        if not up:
            raise Abort("the fake old boards did not come up")
        for b in self.boards:
            name = os.path.basename(b["root"])
            launch_detached([py, os.path.join(self.fake, "bin", "tutor"), "headless", name,
                             "--agent", "fake", "--respawn"])
        def daemons():
            got = matching(r"tutor headless", self.scratch)
            return len(got) == len(self.boards) and got
        found = until(daemons, 20, 0.5) or []
        for proc in found:
            name = re.search(r"tutor headless\s+(\S+)", proc.cmd).group(1)
            for b in self.boards:
                if os.path.basename(b["root"]) == name:
                    agent = os.path.join(b["root"], "live", "agent.json")
                    rec = read_json(agent) or {}
                    rec.update({"pid": proc.pid, "state": "listening", "owed": None})
                    write_json(agent, rec)
        until(lambda: len(matching(r"board wait", self.scratch)) == len(self.boards), 20, 0.5)
        # The owner's unread /say in the Probability copy: the old tutor is at
        # rest with it unanswered, and the new server must answer it.
        inbox = os.path.join(A, "courses", "Probability", "live", "inbox", "messages.jsonl")
        if os.path.isdir(os.path.dirname(inbox)):
            now = time.time()
            with open(inbox, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": "t9999", "rev": 0, "kind": "text", "answers": None,
                                     "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S",
                                                                    time.localtime(now)),
                                     "from": "student", "text": CHECK_SAY,
                                     "signal": None}) + "\n")
        clone_copy(self.atlas, self.pristine)
        print("   %d live/ copied, %d course(s), %d fake board(s) and daemon(s)"
              % (len(workspaces(A)), len(course_dirs(A)), len(self.boards)), flush=True)

    def ctx(self):
        path = os.pathsep.join([os.path.join(self.fake, "uvbin"),
                                os.path.join(self.home, ".local", "bin"),
                                "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
                                "/usr/sbin", "/sbin"])
        capture = {"TCP": {"443": {"HTTPS": True}},
                   "Web": {"mac.example.ts.net:443": {"Handlers": {"/": {
                       "Proxy": "http://127.0.0.1:%d" % self.boards[0]["port"]}}}}}
        for b in self.boards:
            capture["TCP"][str(b["port"])] = {"TCPForward": "127.0.0.1:%d" % b["port"]}
        # The copy's own .git/config names the committer; HOME is the
        # rehearsal's, so nothing reads this Mac's ~/.gitconfig.
        return Ctx(mode="rehearse", atlas=self.atlas,
                   archive=os.path.join(self.scratch, "archive"), ref="overhaul",
                   label=self.prefix, old_labels=[self.prefix + ".tutor-watch",
                                                  self.prefix + ".tutor-pull"],
                   port=self.port, scope=self.scratch, agents_dir=self.agents,
                   bin_dir=os.path.join(self.home, ".local", "bin"),
                   env={"HOME": self.home, "PATH": path, "BOARD_NO_TAILNET": "1"},
                   tailscale="print", fake_capture=capture)

    # -- what only a rehearsal checks ------------------------------------------
    def provider_calls(self):
        try:
            with open(self.calls) as fh:
                return [json.loads(l) for l in fh if l.strip()]
        except OSError:
            return []

    def extras(self, ctx):
        A = self.atlas
        left = [rel for rel, _ in workspaces(A)] + (["live"] if os.path.isdir(
            os.path.join(A, "live")) else [])
        self.check("no live/ remains", not left, left)
        prob = [r["session"] for r in ctx.m["imports"] if r["subject"] == "courses/Probability"]
        turns = [c for c in self.provider_calls() if c.get("kind") == "turn"
                 and prob and c.get("sid") == prob[0]]
        grew = (len(cards_of(ctx, prob[0])) - ctx.m["baseline"][prob[0]]["cards"]) if prob else 0
        self.check("the unread /say queued in the Probability copy is answered by the fake "
                   "provider, once, with one card",
                   len(turns) == 1 and turns[0].get("rc") == 0
                   and CHECK_SAY in turns[0].get("prompt", "") and grew == 1,
                   (grew, [dict(c, prompt=c.get("prompt", "")[-300:]) for c in turns]))
        others = [c for c in self.provider_calls() if c.get("kind") == "turn"
                  and c.get("sid") not in prob]
        waiting = [s for s, b in ctx.m["baseline"].items() if b["waiting"] and s not in prob]
        self.check("every other session with an unread line got one turn, no more",
                   sorted(c["sid"] for c in others) == sorted(waiting), (others, waiting))
        status, got = http(ctx.port, "/meeting", {"since": "30d", "items": []}, timeout=120)
        self.check("POST /meeting asks for the deck", status == 200 and got.get("ok"), got)

        def ready():
            s, lib = http(ctx.port, "/library.json?subject=projects/Meetings")
            rec = lib.get("meeting") or {}
            return rec if rec.get("state") in ("ready", "did not land") else None
        rec = until(ready, 300, 3) or {}
        meet = [c for c in self.provider_calls() if c.get("kind") == "meeting"]
        self.check("a meeting deck builds end to end with the fake provider",
                   rec.get("state") == "ready" and rec.get("ready")
                   and os.path.isfile(os.path.join(A, "projects", "Meetings", "docs",
                                                   "meeting", "meeting.pdf")),
                   (rec, meet))
        before = [p.pid for p in server_procs(ctx)]
        rc, out = run(["bash", os.path.join(A, "board", "scripts", "ship.sh"),
                       "rehearsal ship"], cwd=A,
                      env=ctx.environ(TUTORBOARD_LABEL=ctx.label), timeout=300)
        time.sleep(3)
        back = until(lambda: http(ctx.port, "/health")[0] == 200
                     and len(server_procs(ctx)) == 1 and server_procs(ctx), 90, 1) or []
        self.check("ship.sh afterwards leaves one serve.py, restarted",
                   rc == 0 and len(back) == 1 and back[0].pid not in before,
                   (rc, out[-1500:], before, back))
        self.check("no wrap-up turn ran",
                   not [c for c in self.provider_calls() if c.get("kind") == "handoff"],
                   self.provider_calls())

    def compare(self, ctx):
        diff = compare_trees(self.atlas, self.pristine)
        self.check("the rollback restores the copy: diff -r against the pristine copy, "
                   "logs and caches ignored, is empty", not diff, "\n".join(diff[:80]))
        pre = ctx.m.get("pre")
        head = git(self.atlas, "rev-parse", "HEAD")[1].strip()
        status = git(self.atlas, "status", "--porcelain")[1].strip()
        # Branches and tags: ship.sh pushed to the copy's own bare origin, so
        # its remote-tracking ref moved, as it should.
        refs = lambda r: sorted(git(r, "for-each-ref", "--format=%(refname) %(objectname)",
                                    "refs/heads", "refs/tags")[1].splitlines())
        ex_a = open(exclude_file(self.atlas)).read()
        ex_b = open(exclude_file(self.pristine)).read()
        self.check("main is back at PRE, clean, every ref and info/exclude as before",
                   head == pre and not status and refs(self.atlas) == refs(self.pristine)
                   and ex_a == ex_b, (head, pre, status[:500]))
        for name in course_dirs(self.pristine):
            a = os.path.join(self.atlas, "courses", name)
            b = os.path.join(self.pristine, "courses", name)
            self.check("courses/%s's repository is back, at its HEAD, its status as before"
                       % name,
                       git(a, "rev-parse", "HEAD")[1] == git(b, "rev-parse", "HEAD")[1]
                       and git(a, "status", "--porcelain")[1] == git(b, "status", "--porcelain")[1])
        self.check("the fake old boards answer",
                   all(http(b["port"], "/health", timeout=5)[0] == 200 for b in self.boards))

    def clean(self):
        for label in (self.prefix, self.prefix + ".tutor-watch", self.prefix + ".tutor-pull"):
            if loaded(label):
                bootout(label)
        for p in matching(r".", self.scratch):
            kill_group(p, signal.SIGKILL)
        if self.keep or not all(ok for _, ok in self.results):
            print("scratch kept: %s" % self.scratch)
        else:
            shutil.rmtree(self.scratch, ignore_errors=True)


def rehearse(real, scratch, ref, keep=False):
    r = Rehearsal(real, scratch, ref, keep)
    try:
        try:
            r.build()
        except Abort as exc:
            r.check("the rehearsal copy is built", False, exc)
            return 1
        ctx = r.ctx()
        ctx.begin()
        failure = cutover(ctx)
        r.check("steps 1-10 pass on the copy", failure is None, failure)
        if failure is None:
            r.extras(ctx)
        problems = rollback(ctx)
        r.check("--rollback reports no problem", not problems, problems)
        r.compare(ctx)
    finally:
        r.clean()
    bad = [n for n, ok in r.results if not ok]
    print()
    print("rehearsal %s: %d check(s), %d failed" % ("FAILED" if bad else "passed",
                                                     len(r.results), len(bad)))
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def default_atlas():
    rc, out = git(HERE, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if rc == 0 and out.strip():
        return os.path.dirname(out.strip().rstrip("/"))
    return os.path.dirname(BOARD)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cutover.sh", description=__doc__.split("\n\n")[0])
    how = ap.add_mutually_exclusive_group(required=True)
    how.add_argument("--plan", action="store_true")
    how.add_argument("--rehearse", metavar="SCRATCH")
    how.add_argument("--run", action="store_true")
    how.add_argument("--rollback", metavar="MANIFEST")
    ap.add_argument("--atlas", default=None)
    ap.add_argument("--ref", default=REF)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)
    atlas = os.path.realpath(args.atlas or default_atlas())
    archive = os.path.join(ARCHIVE_ROOT, time.strftime("%Y-%m-%d"))

    if args.plan:
        return plan(Ctx(atlas=atlas, archive=archive, ref=args.ref))
    if args.rehearse:
        return rehearse(atlas, args.rehearse, args.ref, keep=args.keep)
    if args.rollback:
        m = read_json(args.rollback)
        if not m or "ctx" not in m:
            print("cutover: %s is not a cutover manifest" % args.rollback, file=sys.stderr)
            return 2
        ctx = Ctx(manifest=m, **m["ctx"])
        try:
            problems = rollback(ctx)
        except Abort as exc:
            print("cutover: %s" % exc, file=sys.stderr)
            return 1
        return 1 if problems else 0
    # --run
    if os.uname()[0] != "Darwin":
        print("cutover: --run is for the Mac", file=sys.stderr)
        return 2
    ctx = Ctx(mode="run", atlas=atlas, archive=archive, ref=args.ref)
    try:
        ctx.begin()
    except Abort as exc:
        print("cutover: %s" % exc, file=sys.stderr)
        return 1
    failure = cutover(ctx)
    if failure:
        ctx.say("FAILED at %s; rolling back" % failure)
        problems = rollback(ctx)
        ctx.say("rolled back%s; manifest %s" % (
            " with %d problem(s)" % len(problems) if problems else "", ctx.manifest_path))
        return 1
    ctx.say("== 11. push")
    if not step_push(ctx):
        ctx.say("the push failed. The cutover stands and nothing reached GitHub; push "
                "main again, or roll back with --rollback %s" % ctx.manifest_path)
        return 1
    ctx.say("cutover done; manifest %s" % ctx.manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
