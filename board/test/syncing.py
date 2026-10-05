#!/usr/bin/env python3
"""Timely sync, both ways: the cluster commits the owner's edits where a
workspace opts in, and the Mac pulls before every turn.

What the checks are about:

  * NO OPT-IN, NO CHANGE. An edit in a workspace without `relay.sync: true`
    skips the pass, naming the path, exactly as before.
  * A SYNCED WORKSPACE IS COMMITTED AND PUSHED. Its tracked edits and
    untracked files go up as `<workspace>: cluster sync`, past the PHI check
    `board push` uses; what that refuses, a path the policy names, an ignored
    file and a held file stay uncommitted, the refusals named in
    `relay/state.json`.
  * OUTSIDE EVERY WORKSPACE STILL SKIPS.
  * A CONFLICT IS NAMED, NEVER FORCED. Origin and the owner both changed a
    file: it stays dirty, origin keeps its version, the path is named. A
    refused push undoes the sync commit into edits again.
  * THE MAC PULLS BEFORE A TURN, bounded and logged, and not under a merge,
    a held thread's edits, or an edit the pull would change.

Git is real (a bare origin and two clones); Slurm is a stub.
"""

import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard import atlas, fenced, jobs, leaving, relay             # noqa: E402

TUTOR = os.path.join(ROOT, "bin", "tutor")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace").strip()


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


class Done:
    def __init__(self, code=0, out=""):
        self.returncode, self.stdout, self.stderr = code, out, ""


def slurm(argv, **kw):
    return Done(0, "")


_loader = importlib.machinery.SourceFileLoader("tutorcli_syncing", TUTOR)
_spec = importlib.util.spec_from_loader("tutorcli_syncing", _loader)
tutorcli = importlib.util.module_from_spec(_spec)
_loader.exec_module(tutorcli)

POLICY = ("import re\n\ndef names_phi(text):\n"
          "    return bool(re.search(r'SESSION-\\d+', str(text)))\n")

base = tempfile.mkdtemp(prefix="tutor-syncing-")
saved_env = dict(os.environ)
# --- the repository's default, a workspace's word over it ---------------------
_box = tempfile.mkdtemp(prefix="relayopts-")
try:
    write(os.path.join(_box, "atlas.json"), json.dumps(
        {"families": [], "relay": {"sync": True, "colibri": True}}))
    for _ws, _cfg in (("a/one", {}), ("a/two", {"relay": {"sync": False}}),
                      ("a/three", {"relay": {"colibri": True}})):
        write(os.path.join(_box, _ws, "tutorboard.json"), json.dumps(_cfg))
    _o = lambda ws: jobs.relay_opts(os.path.join(_box, ws))
    check("atlas.json's relay.sync is every workspace's default",
          _o("a/one").get("sync") is True and _o("a/three").get("sync") is True)
    check("a workspace's own sync: false overrides it",
          _o("a/two").get("sync") is False)
    check("colibri is never inherited from atlas.json; only a workspace says it",
          "colibri" not in _o("a/one") and _o("a/three").get("colibri") is True)
finally:
    shutil.rmtree(_box, ignore_errors=True)

try:
    os.environ["COLI_QUEUE_ROOT"] = os.path.join(base, "queue")
    os.makedirs(os.environ["COLI_QUEUE_ROOT"])
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(base, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        git(seed, "config", k, v)
    write(os.path.join(seed, "atlas.json"),
          json.dumps({"families": [{"id": "research"}]}))
    write(os.path.join(seed, ".gitignore"),
          "**/relay/state/\n/relay/state.json\n/relay/.lock\nai-config/\n")
    proj = os.path.join(seed, "research", "Proj")
    write(os.path.join(proj, "tutorboard.json"), json.dumps({"name": "Proj"}))
    write(os.path.join(proj, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(proj, ".gitignore"), "live/\nresults/\nphi/\n*.tmp\n")
    write(os.path.join(proj, "src", "fit.py"), "print('fit')\n")
    write(os.path.join(proj, "src", "shared.py"), "x = 1\n")
    write(os.path.join(proj, "src", "held.py"), "h = 1\n")
    write(os.path.join(proj, "jobs.jsonl"), "")
    write(os.path.join(seed, "NOTICE.md"), "a root file\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        where = os.path.join(base, name)
        git(base, "clone", "-q", origin, where)
        for k, v in (("user.email", "%s@example.com" % name),
                     ("user.name", name)):
            git(where, "config", k, v)
        return where

    mac, cluster = clone("mac"), clone("cluster")
    mws = os.path.join(mac, "research", "Proj")
    cws = os.path.join(cluster, "research", "Proj")
    write(os.path.join(cluster, "ai-config", "policy", "phi.py"), POLICY)
    state_path = os.path.join(cluster, "relay", "state.json")

    def run_pass():
        os.environ["TUTOR_SLURM"] = "1"
        atlas.forget()
        return relay.run_pass(cluster, run=slurm)

    def opt_in(on):
        """The owner's decision, made on the Mac and pushed."""
        git(mac, "pull", "-q", "--rebase")
        cfg = {"name": "Proj"}
        if on:
            cfg["relay"] = {"sync": True}
        write(os.path.join(mws, "tutorboard.json"), json.dumps(cfg))
        git(mac, "commit", "-q", "-am", "Proj: relay sync %s" % on)
        git(mac, "push", "-q")
        git(cluster, "pull", "-q", "--ff-only")

    def origin_file(rel):
        return git(origin, "show", "main:" + rel)

    # --- without the opt-in, nothing changes -----------------------------------
    check("no workspace opts in by default",
          relay.sync_spaces(relay.spaces(cluster)) == []
          and "sync" not in jobs.relay_opts(cws))
    write(os.path.join(cws, "src", "fit.py"), "print('fit, edited')\n")
    got = run_pass()
    st = load(state_path)
    check("without the opt-in an owner's edit skips the pass, naming it",
          "research/Proj/src/fit.py" in got["skipped"]
          and "research/Proj/src/fit.py" in st["skipped"]
          and st["synced"] == [] and st["sync_left"] == [])
    check("and nothing is committed",
          "fit, edited" not in origin_file("research/Proj/src/fit.py")
          and git(cluster, "status", "--porcelain")
          == "M research/Proj/src/fit.py")
    git(cluster, "checkout", "--", "research/Proj/src/fit.py")

    # --- with it, a dirty workspace is synced -----------------------------------
    opt_in(True)
    check("relay_opts reads the opt-in",
          jobs.relay_opts(cws).get("sync") is True
          and relay.sync_spaces(relay.spaces(cluster)) == ["research/Proj"])
    from tutorboard import colibri as _colibri, holds as _holds, missions as _missions
    _owned, _qroot, _tasks = _holds.owned, _colibri.queue_root, _missions.tasks
    try:
        def _broken(root):
            raise OSError("holds unreadable")
        _holds.owned = _broken
        check("a pass that cannot read the holds syncs nothing",
              relay.sync_spaces(relay.spaces(cluster)) == [])
        _holds.owned = _owned
        _colibri.queue_root = lambda: cluster
        _missions.tasks = lambda root: [{"queue": "failed",
                                          "workspace": cws}]
        check("a workspace whose Colibri task the queue gave up on is not synced",
              relay.sync_spaces(relay.spaces(cluster)) == [])
        def _gone(root):
            raise OSError("queue unreadable")
        _missions.tasks = _gone
        check("nor is any workspace when the queue cannot be read",
              relay.sync_spaces(relay.spaces(cluster)) == [])
    finally:
        _holds.owned, _colibri.queue_root, _missions.tasks = _owned, _qroot, _tasks
    write(os.path.join(cws, "src", "fit.py"), "print('fit, edited')\n")
    write(os.path.join(cws, "notes", "idea.md"), "a new file\n")
    write(os.path.join(cws, "notes", "SESSION-3.md"), "named for a session\n")
    write(os.path.join(cws, "scratch.tmp"), "ignored\n")
    write(os.path.join(cws, "notes", "rows.csv"), "id,value\nA1,3\n")
    write(os.path.join(cws, "notes", "dump.txt"), "a record\n")
    os.makedirs(os.path.join(cws, "phi"))
    fenced._SEEN.clear()
    leaving._POLICY["root"] = None
    write(os.path.join(cws, "src", "quote.py"), "# from SESSION-9 verbatim\n")
    hold = {"id": "h1", "label": "held", "files": ["src/held.py"],
            "check": None, "held": 1}
    write(os.path.join(cws, "relay", "holds", "h1.json"), json.dumps(hold))
    git(cluster, "add", "research/Proj/relay/holds/h1.json")
    git(cluster, "commit", "-q", "-m", "h1: hold")
    write(os.path.join(cws, "src", "held.py"), "h = 2  # the owner, mid-step\n")
    got = run_pass()
    st = load(state_path)
    left = dict((r["path"], r["why"]) for r in st["sync_left"])
    check("the pass is not skipped and the edits are synced",
          not got["skipped"] and not got["error"]
          and sorted(got["synced"]) == ["research/Proj/notes/idea.md",
                                        "research/Proj/src/fit.py"])
    check("committed as `<workspace>: cluster sync`, with no trailer",
          "research/Proj: cluster sync" in git(cluster, "log", "--format=%s")
          and "Co-Authored" not in git(cluster, "log", "--format=%B"))
    check("and pushed: origin has the edit and the untracked file",
          "fit, edited" in origin_file("research/Proj/src/fit.py")
          and origin_file("research/Proj/notes/idea.md") == "a new file")
    check("relay/state.json lists what it synced",
          sorted(st["synced"]) == sorted(got["synced"]))
    check("a path the PHI policy names is left uncommitted and named",
          "research/Proj/notes/SESSION-3.md" in left
          and "PHI" in left["research/Proj/notes/SESSION-3.md"]
          and origin_file("research/Proj/notes/SESSION-3.md").startswith(
              "fatal"))
    check("so is a file the `board push` check refuses by its content",
          "board push" in left.get("research/Proj/src/quote.py", "")
          and origin_file("research/Proj/src/quote.py").startswith("fatal")
          and os.path.isfile(os.path.join(cws, "src", "quote.py")))
    check("a new table or text file stays on the cluster, named: it may hold data",
          all("by hand" in left.get("research/Proj/notes/%s" % f, "")
              and origin_file("research/Proj/notes/%s" % f).startswith("fatal")
              for f in ("rows.csv", "dump.txt")))
    check("an ignored file is not added, and not named",
          "research/Proj/scratch.tmp" not in left
          and origin_file("research/Proj/scratch.tmp").startswith("fatal"))
    check("a held file stays the owner's: uncommitted, not named",
          "research/Proj/src/held.py" not in left
          and "mid-step" not in origin_file("research/Proj/src/held.py")
          and "mid-step" in read(os.path.join(cws, "src", "held.py")))
    os.remove(os.path.join(cws, "notes", "SESSION-3.md"))
    os.remove(os.path.join(cws, "notes", "rows.csv"))
    os.remove(os.path.join(cws, "notes", "dump.txt"))
    os.remove(os.path.join(cws, "src", "quote.py"))
    git(cluster, "checkout", "--", "research/Proj/src/held.py")
    git(cluster, "rm", "-q", "research/Proj/relay/holds/h1.json")
    git(cluster, "commit", "-q", "-m", "h1: release")
    git(cluster, "push", "-q")

    # --- outside every workspace still skips -------------------------------------
    write(os.path.join(cluster, "NOTICE.md"), "a root edit\n")
    write(os.path.join(cws, "src", "fit.py"), "print('fit, again')\n")
    got = run_pass()
    check("a path outside every workspace still skips the whole pass",
          "NOTICE.md" in got["skipped"] and got["synced"] == []
          and "again" not in origin_file("research/Proj/src/fit.py"))
    git(cluster, "checkout", "--", "NOTICE.md")
    git(cluster, "checkout", "--", "research/Proj/src/fit.py")

    # --- a conflict is reported, never forced -----------------------------------
    git(mac, "pull", "-q", "--rebase")
    write(os.path.join(mws, "src", "shared.py"), "x = 'mac'\n")
    git(mac, "commit", "-q", "-am", "the Mac changes shared.py")
    git(mac, "push", "-q")
    write(os.path.join(cws, "src", "shared.py"), "x = 'cluster'\n")
    got = run_pass()
    st = load(state_path)
    left = dict((r["path"], r["why"]) for r in st["sync_left"])
    check("a file both sides changed is named in the pass's error",
          "research/Proj/src/shared.py" in got["error"]
          and "research/Proj/src/shared.py" in st["last_error"])
    check("and in sync_left, as origin's to merge, nothing forced",
          "origin changes it too" in left.get("research/Proj/src/shared.py",
                                               ""))
    check("the owner's edit stays dirty, and origin keeps the Mac's version",
          read(os.path.join(cws, "src", "shared.py")) == "x = 'cluster'\n"
          and origin_file("research/Proj/src/shared.py") == "x = 'mac'"
          and "the Mac changes shared.py" in git(origin, "log", "--format=%s"))
    check("no rebase is left half done",
          not os.path.exists(os.path.join(cluster, ".git", "rebase-merge"))
          and not os.path.exists(os.path.join(cluster, ".git", "rebase-apply")))
    git(cluster, "checkout", "--", "research/Proj/src/shared.py")
    got = run_pass()
    check("once the owner settles it, the next pass pulls and is clean",
          not got["error"] and not got["skipped"]
          and read(os.path.join(cws, "src", "shared.py")) == "x = 'mac'\n")

    # --- a refused push undoes the sync commit ----------------------------------
    flag = os.path.join(base, "reject")
    hook = os.path.join(origin, "hooks", "pre-receive")
    write(hook, "#!/bin/sh\nif [ -e %s ]; then echo rejected >&2; exit 1; fi\n"
          % flag)
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC)
    write(flag, "")
    head = git(cluster, "rev-parse", "HEAD")
    write(os.path.join(cws, "src", "fit.py"), "print('fit, refused')\n")
    got = run_pass()
    st = load(state_path)
    left = dict((r["path"], r["why"]) for r in st["sync_left"])
    check("a refused push leaves the edit uncommitted again, and says so",
          "refused" in left.get("research/Proj/src/fit.py", "")
          and got["synced"] == []
          and git(cluster, "rev-parse", "HEAD") == head
          and git(cluster, "status", "--porcelain",
                  "research/Proj/src/fit.py") == "M research/Proj/src/fit.py")
    os.remove(flag)
    got = run_pass()
    check("and the next pass pushes it",
          got["synced"] == ["research/Proj/src/fit.py"]
          and "refused" in origin_file("research/Proj/src/fit.py"))

    # --- a sync a killed pass left unpushed --------------------------------------
    write(os.path.join(cws, "src", "fit.py"), "print('fit, killed')\n")
    git(cluster, "commit", "-q", "-am", "research/Proj: cluster sync")
    got = run_pass()
    check("an unpushed sync commit does not skip the next pass, which pushes "
          "it", not got["skipped"] and not got["error"]
          and "killed" in origin_file("research/Proj/src/fit.py"))
    write(os.path.join(cws, "src", "fit.py"), "print('fit, unwound')\n")
    git(cluster, "commit", "-q", "-am", "research/Proj: cluster sync")
    back = relay._unwind(cluster, "origin/main", ["research/Proj"])
    check("_unwind turns a sync commit back into an unstaged edit",
          back == ["research/Proj/src/fit.py"]
          and git(cluster, "rev-parse", "HEAD") == git(cluster, "rev-parse",
                                                       "origin/main")
          and git(cluster, "status", "--porcelain")
          == "M research/Proj/src/fit.py")
    check("and never touches a commit that is not one",
          relay._unwind(cluster, "origin/main", ["research/Other"]) == [])
    git(cluster, "checkout", "--", "research/Proj/src/fit.py")
    opt_in(False)

    # --- the Mac pulls before every turn ----------------------------------------
    os.environ["TUTOR_SLURM"] = "0"
    check("the Mac's idle pull is every five minutes",
          jobs.PULL_IDLE == 300 and jobs.PULL_BUSY == 120)
    src = read(TUTOR)
    loop = src.split("\ndef headless(")[1].split("\ndef ")[0]
    check("the daemon pulls once at the top of every turn, before the client",
          "turn_pull(root, log)" in loop
          and loop.index("=== %s turn %d ===") < loop.index("turn_pull(root, log)")
          < loop.index("run_turn(cmd, root, log, cap"))
    git(mac, "reset", "-q", "--hard", "origin/main")
    write(os.path.join(cws, "src", "fit.py"), "print('fit, from the cluster')\n")
    git(cluster, "commit", "-q", "-am", "the cluster moves on")
    git(cluster, "push", "-q")
    log = io.StringIO()
    check("a turn pulls what the cluster pushed",
          tutorcli.turn_pull(mws, log) is True
          and "from the cluster" in read(os.path.join(mws, "src", "fit.py"))
          and "pulled 1 commit(s)" in log.getvalue())

    seen = {}

    def fake_pull(root, quiet=False, timeout=None, say=None):
        seen["timeout"] = timeout
        say("could not reach the remote; working with what is here")
        return False
    log = io.StringIO()
    check("the pull is bounded and a dead remote is one logged line",
          tutorcli.turn_pull(mws, log, pull=fake_pull) is False
          and seen["timeout"] == tutorcli.TURN_PULL_SECONDS <= 30
          and "could not reach the remote" in log.getvalue())
    url = git(mac, "remote", "get-url", "origin")
    git(mac, "remote", "set-url", "origin", os.path.join(base, "gone.git"))
    log = io.StringIO()
    check("an unreachable remote does not stop the turn",
          tutorcli.turn_pull(mws, log) is False
          and "not synced" in log.getvalue())
    git(mac, "remote", "set-url", "origin", url)

    write(os.path.join(cws, "src", "shared.py"), "x = 'cluster again'\n")
    git(cluster, "commit", "-q", "-am", "the cluster changes shared.py")
    git(cluster, "push", "-q")
    write(os.path.join(mws, "src", "shared.py"), "x = 'mac, unsaved'\n")
    log = io.StringIO()
    check("an edit here the pull would change: nothing moves, logged",
          tutorcli.turn_pull(mws, log) is False
          and read(os.path.join(mws, "src", "shared.py")) == "x = 'mac, unsaved'\n"
          and "not synced" in log.getvalue())
    git(mac, "checkout", "--", "research/Proj/src/shared.py")

    merge_head = os.path.join(mac, ".git", "MERGE_HEAD")
    write(merge_head, git(mac, "rev-parse", "HEAD") + "\n")
    before = git(mac, "rev-parse", "HEAD")
    log = io.StringIO()
    check("never mid-merge (worktree.busy_reason)",
          tutorcli.turn_pull(mws, log) is False
          and git(mac, "rev-parse", "HEAD") == before
          and "merge is in progress" in log.getvalue())
    os.remove(merge_head)

    write(os.path.join(cws, "relay", "holds", "h2.json"), json.dumps(
        dict(hold, id="h2")))
    git(cluster, "add", "-A")
    git(cluster, "commit", "-q", "-m", "h2: hold")
    git(cluster, "push", "-q")
    tutorcli.turn_pull(mws, io.StringIO())
    write(os.path.join(mws, "src", "held.py"), "h = 3  # typed on the Mac\n")
    before = git(mac, "rev-parse", "HEAD")
    write(os.path.join(cws, "AI_INSTRUCTIONS.md"), "# contract, v2\n")
    git(cluster, "commit", "-q", "-am", "the cluster moves again")
    git(cluster, "push", "-q")
    log = io.StringIO()
    check("never inside a held thread's edits (holds.refusal)",
          tutorcli.turn_pull(mws, log) is False
          and git(mac, "rev-parse", "HEAD") == before
          and "held thread" in log.getvalue())
    os.environ["TUTOR_SLURM"] = "1"
    check("where Slurm is, the relay pulls and a turn does not",
          tutorcli.turn_pull(mws, io.StringIO()) is None)
finally:
    os.environ.clear()
    os.environ.update(saved_env)
    shutil.rmtree(base, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "a synced workspace is committed and pushed, a conflict is named, "
           "and every turn starts from origin")
sys.exit(1 if fails else 0)
