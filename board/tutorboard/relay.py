"""relay.py -- the cluster's half of the relay: one pass, every two minutes.

scrontab runs `board/scripts/relay-pass.sh`, which pulls in bash (so a pushed
fix lands even when this file cannot import), re-execs itself once when the
pull changed board/, then runs `board/bin/relay --once`, which is `run_pass`.

The Mac commits `relay/requests/<id>.json`; this pulls it, checks it again with
`jobs.check`, submits it through `jobs.submit_recipe`, polls it with
`jobs.poll`, and commits `relay/reports/<id>.json` and `exports/`. GitHub is
the only channel. HANDOFF.md's "The relay" is the contract.

ONE PASS, IN ORDER, UNDER ONE LOCK (`relay/.lock` at the repository root,
`flock`, so a second pass at once skips rather than waits):

1. Pull, fast-forward only. A tree with edits or unpushed commits outside the
   cluster's own paths is skipped, and `relay/state.json` says why. Then
   `pull_vendor` moves `vendor/colibri`.
2. Each request with no report is validated, then submitted or refused.
3. Unfinished jobs are polled with `jobs.poll`: `squeue` plus the wrapper's
   exit file, because `sacct` is refused here. An ended job's exports are
   copied and checked, and its report written.
4. A `colibri` request is queued as a task (`colibri.relay_file`), and
   `colibri.relay_pass` reports each task. A Colibri task is read-only
   analysis whose outputs go under the workspace's ignored `phi/`, so a
   finished one is checked (`check_task`): any change git can see in its
   workspace fails it, and nothing it wrote is committed. No model runs in
   the pass: a failed job prints `RELAY:` lines (the wrapper's fingerprint,
   board/cluster/lib), and the Mac repairs it.
5. Only what this pass wrote under `relay/reports/` and `exports/` is
   committed (`staged_paths`), with `relay/status.json` when it changed;
   anything else there is named in `relay/state.json`. The pass rebases onto
   origin under any edits (`pull_under`) and pushes. A rejected push is
   retried by the next pass. Never force. The pass never commits the owner's
   edits.

A coding session's held paths (`board code`) and a Colibri task's workspace
are the owner's edits, left uncommitted: neither skips the pass, and the pull
goes under them. A
task's changes stay so when the check fails it, for the owner to settle.
A request's report is named for its id where that is valid, else for its
file, so no payload names a path outside `relay/reports/`.

A REPORT IS PUBLIC. It carries state, the Slurm id, times, the exit code, which
`produces` paths exist, which exports landed, the lines the job printed behind
`RELAY:`, and the exception type of a crash. A log excerpt only where the
subject's phi is literally false (`log_excerpt`, `code.output_open`). Every
string in it goes through `public` first: absolute paths become `<path>`, and
the lab's `names_phi` policy withholds what it matches.

Standard library only.
"""

import fcntl
import getpass
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from . import exports, jobs, leaving, paths, subjects, worktree

LOCK = os.path.join("relay", ".lock")
STATE = os.path.join("relay", "state.json")
# The relay's public health, tracked at the Atlas root: what the Mac reads.
# `relay/state.json` beside it is the ignored, cluster-only detail.
STATUS = "relay/status.json"

# An export is at most this big.
CAP = 5 * 1024 * 1024
# What of a job's log reaches a report: `RELAY:` lines only, this many, this
# long, out of at most this much of the log's end.
MAX_LINES = 40
MAX_LINE = 200
READ_TAIL = 2 * 1024 * 1024
MAX_NOTE = 2000

# How often scrontab runs a pass, in minutes.
PASS_MINUTES = 2
# What the scrontab entry asks for. A pass is git and a few sbatch calls.
SCRON_PARTITION = "c3_short"
SCRON_TIME = "00:15:00"
SCRON_BEGIN = "# BEGIN tutor-relay"
SCRON_END = "# END tutor-relay"

GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false"}


# ---------------------------------------------------------------------------
# what is public
# ---------------------------------------------------------------------------
_PATH_RE = re.compile(r"(?<![\w.~:/-])(?:~/|/)(?:[^\s/:'\"]+/)*[^\s/:'\",;)]+")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def public(text, names_phi=None, limit=MAX_LINE):
    """`text` fit for a public report, or None where the PHI policy matches it.

    Control characters go, an absolute or home path becomes `<path>` (a path
    is where lab storage gets named), and it is cut to `limit`.
    """
    s = _CTRL_RE.sub("", str(text or "")).strip()
    s = _PATH_RE.sub("<path>", s)
    if names_phi is not None:
        try:
            if names_phi(s):
                return None
        except Exception:                                    # noqa: BLE001
            return None
    if len(s) > limit:
        s = s[:limit - 1].rstrip() + "…"
    return s


def relay_lines(text, names_phi=None):
    """The lines a job printed behind `RELAY:`, made public. The last
    `MAX_LINES` of them, prefix dropped; nothing else of the log."""
    out = []
    for line in (text or "").splitlines():
        if not line.startswith("RELAY:"):
            continue
        said = public(line[len("RELAY:"):], names_phi)
        if said:
            out.append(said)
    return out[-MAX_LINES:]


_EXC_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
                     r"(?::|$)")


def crash_type(text):
    """The exception type of the last Python traceback in `text`, or "".
    The type only: its message can print anything."""
    lines = (text or "").splitlines()
    starts = [i for i, l in enumerate(lines)
              if l.startswith("Traceback (most recent call last)")]
    if not starts:
        return ""
    for line in lines[starts[-1] + 1:]:
        if not line or line[0].isspace():
            continue
        m = _EXC_RE.match(line.strip())
        return m.group(1)[:80] if m else ""
    return ""


def _tail(path):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - READ_TAIL))
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _logs(rec):
    """`(stdout text, stderr text)` of a job, globbing an array's files."""
    import glob

    def read(p):
        if not p:
            return ""
        found = glob.glob(p) if "*" in p else [p]
        return "\n".join(_tail(f) for f in sorted(found))
    out = read(rec.get("log_path"))
    err = read(rec.get("err_path")) if rec.get("err_path") != rec.get(
        "log_path") else ""
    return out, err


# ---------------------------------------------------------------------------
# git, in the cluster checkout
# ---------------------------------------------------------------------------
def _git(base, *args, timeout=120, raw=False, env=None, input=None):
    try:
        p = subprocess.run(["git"] + list(args), cwd=base,
                           env=dict(os.environ, **dict(GIT_ENV, **(env or {}))),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL if raw else subprocess.STDOUT,
                           universal_newlines=True, timeout=timeout,
                           input=input)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout or "") if raw else (p.stdout or "").strip()


def _rel(base, path):
    return os.path.relpath(os.path.realpath(path), os.path.realpath(base))


def spaces(base):
    """`[(workspace root, its path relative to the repository)]`, for every
    subject: each one is Atlas's own content."""
    return [(where, _rel(base, where)) for where in subjects.roots(base)]


def coding(base):
    """Repository-relative paths an open coding session (`board code`) holds
    in this checkout. `[]` where none is registered or they cannot be read."""
    from . import code
    try:
        return code.held(base)
    except Exception:                                        # noqa: BLE001
        return []


HELD_UPSTREAM = "held path changed upstream"


def held_upstream(base, ref, held):
    """Held paths `HEAD...ref` changes: a pull would overwrite the owner's
    work in a coding session, so it does not happen. None where git fails."""
    if not held:
        return []
    code, out = _git(base, "-c", "core.quotePath=false", "diff", "--name-only",
                     "HEAD...%s" % ref, "--", *held)
    if code != 0:
        return None
    return sorted(l for l in out.splitlines() if l)


def colibri_busy(base):
    """Repository-relative workspace paths a Colibri task owns: one queued or
    running there, one finished and not yet checked (`check_task`), and one
    the queue failed, whose changes stay for the owner. Edits there are not
    the pass's to commit, and they do not skip it."""
    from . import colibri
    out = []
    try:
        root = colibri.queue_root()
        if not root:
            return []
        for rec in colibri.tasks(root):
            q = rec.get("queue")
            if q in ("queued", "running", "failed") or (
                    q == "done" and not rec.get("checked")):
                found = subjects.find(rec.get("workspace") or "")
                if found:
                    out.append(_rel(base, found["root"]))
    except Exception:                                        # noqa: BLE001
        return out
    return sorted(set(out))


def _under(rel, prefixes):
    return any(rel == p or rel.startswith(p + "/") for p in prefixes or ())


def owned(base, rel, where=None, held=None):
    """Is this repository-relative path one the cluster writes? A workspace's
    `relay/reports/` and `exports/`, `relay/status.json`, the
    `vendor/colibri` pointer the pass moves, and (`held`, from `coding`)
    the paths an open coding session holds open."""
    if rel in ("vendor/colibri", STATUS):
        return True
    for _, ws in where if where is not None else spaces(base):
        for mine in ("relay/reports/", "exports/"):
            if rel.startswith(ws + "/" + mine):
                return True
    return _under(rel, held)


def _dirty(base):
    """Repository-relative paths with tracked changes, staged or not."""
    code, out = _git(base, "status", "--porcelain", "-z", "--untracked-files=no",
                     "--ignore-submodules=dirty", raw=True)
    if code != 0:
        return None
    got, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1                       # the original path follows a rename
        got.append(entry[3:])
    return got


def upstream(base):
    """`(remote, branch, "remote/branch")`, or None without one."""
    code, branch = _git(base, "symbolic-ref", "--quiet", "--short", "HEAD")
    if code != 0 or not branch:
        return None
    code, remote = _git(base, "config", "branch.%s.remote" % branch)
    code2, merge = _git(base, "config", "branch.%s.merge" % branch)
    if code or code2 or not remote or not merge:
        return None
    theirs = merge.split("refs/heads/", 1)[-1]
    return remote, theirs, "%s/%s" % (remote, theirs)


def _count(base, spec):
    code, out = _git(base, "rev-list", "--count", spec)
    return int(out) if code == 0 and out.isdigit() else 0


# ---------------------------------------------------------------------------
# step 1: the pull
# ---------------------------------------------------------------------------
def _status(base, rel, strict=False):
    """Repository-relative paths under `rel` git sees as changed or new:
    tracked edits, both sides of a rename, untracked files not ignored.
    Where git fails, `[]`, or None when `strict`."""
    code, out = _git(base, "status", "--porcelain", "-z",
                     "--untracked-files=all", "--ignore-submodules=dirty",
                     "--", rel, raw=True)
    if code != 0:
        return None if strict else []
    got, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        got.append(entry[3:])
        if entry[0] in "RC" and i < len(fields):
            got.append(fields[i])
            i += 1
    return got


def _stashes(base):
    """How many entries `git stash list` holds, or None if git would not say."""
    code, out = _git(base, "stash", "list", timeout=20)
    if code != 0:
        return None
    return len([l for l in out.splitlines() if l.strip()])


def pull_under(base):
    """Bring the upstream in under the edits here. `(ok, said)`.

    `git rebase --autostash` onto the upstream: the edits (a coding session's
    held files, a Colibri task's workspace) are set aside, the local commits
    replayed on origin, and the edits put back. That is safe only because
    nothing upstream touches an edited path, so that is checked first: a path
    both edited here and changed upstream stops the pull with nothing moved. A
    rebase that fails anyway is aborted, which puts the tree back as it was."""
    busy = worktree.busy_reason(base)
    if busy:
        return False, "%s, so nothing was pulled" % busy
    code, up = _git(base, "rev-parse", "--abbrev-ref", "@{upstream}", timeout=10)
    if code != 0:
        return True, "no upstream to pull from"
    remote = up.strip().split("/", 1)[0]
    code, out = _git(base, "fetch", "--quiet", remote)
    if code != 0:
        return False, "could not fetch %s: %s" % (remote, out[-300:])
    if not _count(base, "HEAD..@{upstream}"):
        return True, "already current"
    code, out = _git(base, "diff", "--name-only", "-z", "HEAD...@{upstream}",
                     raw=True)
    if code != 0:
        return False, ("could not read what origin changes, so nothing was "
                       "pulled")
    incoming = set(x for x in out.split("\0") if x)
    dirty = _status(base, ".", strict=True)
    if dirty is None:
        return False, "git status failed, so nothing was pulled"
    clash = sorted(p for p in dirty if p in incoming)
    if clash:
        return False, ("origin changes %s, which %s uncommitted edits here, so "
                       "nothing was pulled"
                       % (", ".join(clash[:6]),
                          "has" if len(clash) == 1 else "have"))
    stashed = _stashes(base)
    code, out = _git(base, "rebase", "--autostash", "--quiet", "@{upstream}",
                     timeout=300)
    if code != 0:
        _git(base, "rebase", "--abort")
        return False, ("the rebase onto origin stopped, so it was undone and "
                       "the tree is as it was: %s" % out[-300:])
    code, left = _git(base, "diff", "--name-only", "--diff-filter=U")
    if code != 0 or left:
        return False, ("the edits set aside did not go back cleanly; they are "
                       "kept in `git stash list`: %s" % left)
    # The other way an autostash fails to go back: `stash apply` refuses (a
    # file changed while the rebase ran), git still exits 0 and leaves no
    # conflict, and the edits sit in the stash, gone from the tree.
    after = _stashes(base)
    if (stashed is None or after is None or after > stashed
            or "resulted in conflicts" in out):
        return False, ("the edits set aside did not go back; they are kept in "
                       "`git stash list` (stash@{0}), so put them back with "
                       "`git stash pop` before the next pull")
    return True, "pulled origin under the edits here"


def pull(base, where, pull_vendor=None):
    """Step 1. `(skip reason or "", error or "")`."""
    busy = worktree.busy_reason(base)
    if busy:
        return "%s in the repository" % busy, ""
    up = upstream(base)
    if not up:
        return "HEAD is detached or its branch has no upstream", ""
    remote, theirs, ref = up
    restore_status(base)
    dirty = _dirty(base)
    if dirty is None:
        return "git status failed", ""
    held = coding(base)
    busy_ws = colibri_busy(base)
    stray = [p for p in dirty
             if not owned(base, p, where, held) and not _under(p, busy_ws)]
    if stray:
        return ("the tree has edits outside the cluster's paths: %s"
                % ", ".join(stray[:5]) + (" and %d more" % (len(stray) - 5)
                                          if len(stray) > 5 else "")), ""
    code, out = _git(base, "fetch", "--quiet", remote, theirs)
    error = "" if code == 0 else "fetch from %s failed: %s" % (
        remote, out.splitlines()[-1] if out else "no output")
    ahead = _count(base, "%s..HEAD" % ref)
    if ahead:
        code, out = _git(base, "diff", "--name-only", "%s...HEAD" % ref)
        theirs_not = [p for p in out.splitlines() if p
                      and not owned(base, p, where, held)]
        if code != 0 or theirs_not:
            return ("the branch has commits origin lacks, outside the "
                    "cluster's paths: %s" % ", ".join(theirs_not[:5])), error
    # A coding session's paths are the owner's until `board code --end`:
    # origin changing one stops the pull rather than overwrite what is being
    # written. The pass still runs, at this HEAD, and says why.
    if not error and _count(base, "HEAD..%s" % ref):
        clash = held_upstream(base, ref, held)
        if clash is None:
            error = ("could not tell whether origin changes a coding "
                     "session's held paths, so nothing was pulled")
        elif clash:
            error = ("%s: %s. Nothing was pulled; `board code <session> --end` "
                     "refuses the same files until they are merged by hand"
                     % (HELD_UPSTREAM, ", ".join(clash[:5])))
    if not error and _count(base, "HEAD..%s" % ref):
        if ahead or dirty:
            # Commits of its own to replay, or the owner's edits (a coding
            # session's, a Colibri task's) to keep.
            ok, why = pull_under(base)
            if not ok:
                return "", "pull onto %s failed: %s" % (ref, why)
        else:
            code, out = _git(base, "merge", "--ff-only", "--quiet", ref)
            if code != 0:
                return "", "fast-forward to %s failed: %s" % (
                    ref, out.splitlines()[-1] if out else "")
    if pull_vendor is not None:
        try:
            pull_vendor(quiet=True)
        except Exception as exc:                             # noqa: BLE001
            error = error or "pull_vendor: %s" % exc
    return "", error


# What this pass wrote: every report and every landed export, absolute.
# `publish` commits exactly these, so a file that reached `exports/` or
# `relay/reports/` any other way (a task, a recipe writing there itself) is
# never published unchecked.
_WRITTEN = set()


def pull_vendor(quiet=False):
    """Move `vendor/colibri` forward, and COMMIT THE POINTER ITSELF.

        "Regarding some kind of external repo like colibri, I want to have that
         git pulled every time I salloc, just like tutoring becomes available
         every time I salloc. I want it tracked in our repo too."

    A submodule is exactly that: the repository tracks a POINTER to a commit in
    somebody else's repository, and the pointer is a tracked file like anything
    else. The relay's pass runs this on the cluster, the only machine that
    bumps vendor pointers; the Mac's `gitops.pull` only checks out the
    pointers it pulled. A timer is safe here only BECAUSE of the third
    rule below: it commits nothing when anything else in the tree is dirty, so
    it cannot sweep up an afternoon it arrived in the middle of.

    The third rule is the one that bites. A bumped pointer is a change in the
    working tree, so pulling colibri leaves the repository dirty every time
    colibri moves -- and `git.repo_dirty` is on the board, which means the
    person is shown "unsaved work" for something they did not do, on a file they
    have never heard of. So the pull commits the bump, with a fixed message
    naming the old commit and the new one.

    **That is the only commit anything in this system makes on its own**, so it
    is guarded three ways:

    * only when `vendor/colibri` is the ONLY dirty path. Anything else in the
      tree and this does nothing at all -- a commit that sweeps up somebody's
      afternoon because a vendored library moved is the exact failure the
      `--only` pathspec exists to prevent;
    * never when a merge or a rebase is outstanding, because a terminal in here
      has its own plan for the next commit;
    * never on a detached HEAD, where a commit is reachable from nothing.

    `vendor/colibri-build` is NOT pulled. It is the same upstream pinned at an
    older commit because it is a BUILD TREE, and a build tree that moves
    underneath a build is the failure it exists to avoid. Moving it forward is
    the person's to do, by hand.
    """
    base = subjects.root()
    sub = os.path.join(base, "vendor", "colibri")
    if not os.path.isdir(os.path.join(sub, ".git")) and \
       not os.path.isfile(os.path.join(sub, ".git")):
        return None                      # not a checkout here; nothing to do

    def say(msg):
        if not quiet:
            print("  " + msg)

    busy = worktree.busy_reason(base)
    if busy:
        say("colibri not pulled: %s in the repository" % busy)
        return False

    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")

    def git(*args, **kw):
        return subprocess.run(["git"] + list(args), cwd=kw.pop("cwd", base),
                              env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=kw.get("timeout", 90))

    try:
        before = git("rev-parse", "HEAD", cwd=sub).stdout.decode().strip()
        p = git("submodule", "update", "--remote", "--merge", "vendor/colibri")
        after = git("rev-parse", "HEAD", cwd=sub).stdout.decode().strip()
    except (OSError, subprocess.TimeoutExpired):
        say("could not reach colibri's remote; leaving it where it is")
        return False
    if p.returncode != 0:
        out = p.stdout.decode("utf-8", "replace").strip().splitlines()
        say("colibri not pulled: %s" % (out[-1] if out else "update failed"))
        return False
    if before == after:
        return True                      # already current, and silent about it

    # --- the pointer is now dirty. Commit it, or say why not. ---------------
    try:
        if git("rev-parse", "--abbrev-ref", "HEAD").stdout.decode().strip() == "HEAD":
            say("colibri moved, but HEAD is detached here, so the pointer is "
                "left uncommitted")
            return False
        status = git("status", "--porcelain").stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return False

    dirty = [l[3:].strip() for l in status.splitlines() if l.strip()]
    stray = [d for d in dirty if d.rstrip("/") != "vendor/colibri"]
    if stray:
        say("colibri moved to %s, and the pointer is left uncommitted because "
            "there is other uncommitted work here: %s"
            % (after[:8], ", ".join(stray[:3])))
        return False

    msg = ("vendor/colibri moves from %s to %s\n\n"
           "The pointer only. Written by `tutor resume` on login, which is the "
           "one moment a compute node gets, and committed here rather than left "
           "dirty -- an uncommitted pointer nobody touched shows on the board as "
           "unsaved work, which is a lie the person cannot act on."
           % (before[:8], after[:8]))
    try:
        git("commit", "--only", "-m", msg, "--", "vendor/colibri")
    except (OSError, subprocess.TimeoutExpired):
        return False
    say("colibri moved %s -> %s, pointer committed" % (before[:8], after[:8]))
    return True


def _changed(base, rels):
    """Repository-relative files under `rels` that git sees as new or changed."""
    if not rels:
        return []
    code, out = _git(base, "status", "--porcelain", "-z",
                     "--untracked-files=all", "--", *rels, raw=True)
    if code != 0:
        return []
    got, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1
        got.append(entry[3:])
    return got


def staged_paths(base, where):
    """`(paths to commit, paths left unpublished)`, repository-relative.

    The commit is what this pass wrote, plus a report for a request filed here
    that a pass killed before its commit left behind. Anything else changed
    under `exports/` or `relay/reports/` is left, and named."""
    written = set(_rel(base, p) for p in _WRITTEN)
    dirs = []
    for root, ws in where:
        for sub in ("relay/reports", "exports"):
            if os.path.isdir(os.path.join(root, sub)):
                dirs.append(ws + "/" + sub)
    changed = _changed(base, dirs)
    known = set()
    for root, ws in where:
        try:
            for req in jobs.requests(root):
                known.add("%s/relay/reports/%s.json" % (ws, request_id(req)))
        except Exception:                                    # noqa: BLE001
            continue
    take = [p for p in changed if p in written or p in known]
    left = [p for p in changed if p not in take]
    return sorted(take), sorted(left)


def publish(base, where, message, push=True):
    """Step 5. Commit the cluster's paths, rebase, push. `(sha, error)`."""
    mine, _ = staged_paths(base, where)
    if status_dirty(base):
        mine.append(STATUS)
        if mine == [STATUS]:
            message = "relay: status"
    if mine:
        code, out = _git(base, "add", "--", *mine)
        if code != 0:
            return "", "add failed: %s" % (out.splitlines() or [""])[-1]
        code, out = _git(base, "commit", "--quiet", "-m", message, "--",
                         *mine)
        if code != 0:
            return "", "commit failed: %s" % (out.splitlines() or [""])[-1]
    up = upstream(base)
    if not up or not push:
        return "", ""
    remote, theirs, ref = up
    if not _count(base, "%s..HEAD" % ref):
        return "", ""
    _git(base, "fetch", "--quiet", remote, theirs)
    clash = held_upstream(base, ref, coding(base))
    if clash:
        return "", "%s: %s; nothing was pushed" % (HELD_UPSTREAM,
                                                    ", ".join(clash[:5]))
    ok, why = pull_under(base)
    if not ok:
        return "", "rebase before the push failed: %s" % why
    if not _count(base, "%s..HEAD" % ref):
        return "", ""
    code, out = _git(base, "push", "--quiet", remote, "HEAD:%s" % theirs,
                     timeout=180)
    if code != 0:
        return "", "push rejected, retried next pass: %s" % (
            out.splitlines() or [""])[-1]
    return _git(base, "rev-parse", "HEAD")[1], ""


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------
def request_id(req):
    """The id a request's report is named and keyed by: its `id` where that
    is a valid one, else its file's own name, which no payload can make a
    path elsewhere."""
    rid = req.get("id") if isinstance(req, dict) else None
    if isinstance(rid, str) and jobs.REQUEST_ID_RE.match(rid):
        return rid
    stem = str((req or {}).get(jobs.FILE_KEY) or "")
    return stem if _SAFE_STEM.match(stem) else "unnamed"


_SAFE_STEM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def write_report(ws, rid, rep):
    """Write one report. Every report carries `ran_at`, the cluster's HEAD
    short sha: the one its job was submitted at where the caller kept it,
    else HEAD now."""
    rid = str(rid)
    if not _SAFE_STEM.match(rid):
        raise ValueError("a report id names a file in relay/reports/")
    rep = dict((k, v) for k, v in rep.items() if k != jobs.FILE_KEY)
    if not rep.get("ran_at"):
        rep["ran_at"] = jobs.head(ws, short=True) or "unknown"
    target = os.path.join(jobs.reports_dir(ws), rid + ".json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, target)
    _WRITTEN.add(os.path.realpath(target))
    return target


def _field(value, names_phi):
    return public(value, names_phi, 80) if isinstance(value, str) else None


def _base_report(req, state, now, names_phi=None):
    """A report's common fields. It echoes the request's `label` and
    `session`, so the Mac wakes the session that filed it; a `thread` an
    older request carries is not echoed."""
    rep = {"id": request_id(req), "kind": _field(req.get("kind"), names_phi),
           "state": state, "updated": round(float(now), 3)}
    for key in ("label", "session"):
        said = _field(req.get(key), names_phi)
        if said:
            rep[key] = said
    return rep


def refuse(ws, req, problems, now, names_phi=None):
    rep = _base_report(req, "refused", now, names_phi)
    rep["problems"] = [public(p, names_phi, 400) or "(withheld by the PHI "
                       "policy)" for p in problems]
    return write_report(ws, request_id(req), rep)


def export(ws, rec, allowed, names_phi=None):
    """Copy a finished job's exports into `exports/`. `(landed, refused)`.

    Each path is checked again here, in code, whatever the request said: under
    `results/`, an allowed extension, approved now by the subject's committed
    tutorboard.json `relay.exports` (`allowed`, `exports.approvals`), a
    regular file of at most 5 MB, a target git would track, and nothing the
    PHI policy matches in its path or, for text, its content.
    """
    landed, refused = [], []
    for rel in rec.get("export") or []:
        rel = exports.rel(rel)

        def no(why):
            refused.append({"path": rel, "why": why})
        if names_phi is None:
            no("the PHI guard's policy is not installed in this checkout")
            continue
        if not rel or not rel.startswith("results/"):
            no("not a path under results/")
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in exports.EXPORT_EXTS:
            no("not one of %s" % ", ".join(exports.EXPORT_EXTS))
            continue
        ok, why = exports.approved(allowed, rel)
        if not ok:
            no(why)
            continue
        if names_phi is not None and names_phi(rel):
            no("the PHI policy matches its path")
            continue
        src = os.path.join(ws, rel)
        if os.path.islink(src) or not os.path.isfile(src):
            no("not there as a regular file")
            continue
        size = os.path.getsize(src)
        if size > CAP:
            no("%.1f MB, over the %d MB cap" % (size / 1048576.0,
                                                CAP // 1048576))
            continue
        if ext in (".csv", ".json", ".svg") and names_phi is not None:
            with open(src, "r", encoding="utf-8", errors="replace") as fh:
                if names_phi(fh.read()):
                    no("the PHI policy matches its content")
                    continue
        dst_rel = "exports/" + rel
        if jobs.ignored(ws, dst_rel):
            no("git would ignore %s; the workspace's .gitignore needs "
               "`!exports/**`" % dst_rel)
            continue
        dst = os.path.join(ws, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst + ".tmp")
        os.replace(dst + ".tmp", dst)
        _WRITTEN.add(os.path.realpath(dst))
        landed.append(rel)
    return landed, refused


def finish(ws, rec, req, allowed, now, names_phi=None):
    """The report for a job that has ended."""
    state = "completed" if rec.get("state") == "COMPLETED" else "failed"
    rep = _base_report(req, state, now, names_phi)
    # The HEAD it was submitted at, not the one it ended at.
    ran_at = (rec.get("ran_at")
              or (jobs.reports(ws).get(request_id(req)) or {}).get("ran_at"))
    if ran_at:
        rep["ran_at"] = ran_at
    rep.update({"jobid": str(rec.get("jobid")),
                "submitted": rec.get("submitted"),
                "ended": rec.get("ended") or "",
                "exit": rec.get("exit") or ""})
    produces = list(req.get("produces") or [])
    rep["produced"] = [p for p in produces if paths.present(ws, p)]
    rep["missing"] = [p for p in produces if p not in rep["produced"]]
    out, err = _logs(rec)
    # Without the policy nothing the job printed is published.
    rep["relay"] = (relay_lines(out + "\n" + err, names_phi)
                    if names_phi is not None else [])
    crashed = crash_type(err) or crash_type(out)
    if crashed:
        rep["error"] = crashed
    rep.update(log_excerpt(ws, out, err, names_phi))
    if state == "completed":
        landed, refused = export(ws, dict(rec, export=req.get("export")),
                                 allowed, names_phi)
    else:
        landed = []
        refused = [{"path": p, "why": "the job did not complete"}
                   for p in req.get("export") or []]
    rep["exported"] = landed
    if refused:
        rep["export_refused"] = refused
    rep["note"] = recipe_note(rec, rep)
    return write_report(ws, request_id(req), rep)


def log_excerpt(ws, out, err, names_phi):
    """`{output, output_total, output_cut}` of a job's log, or {}.

    Only where `code.output_open` holds: the subject's tutorboard.json says
    `"phi": false` literally, on disk and at HEAD, it holds no fence, and the
    policy loaded. Then stdout and stderr go through `code.check_output`, as a
    `board code` step's do: paths made subject-relative, any other absolute
    path `<path>`, a line the policy flags withheld, the middle cut."""
    from . import code
    if names_phi is None or not code.output_open(ws, names_phi=names_phi):
        return {}
    text = out if not err else (out.rstrip("\n") + "\n" + err if out
                                else err)
    got = code.check_output(text, ws, names_phi, code.top_of(ws) or None)
    return dict((k, got[k]) for k in ("output", "output_total", "output_cut"))


def recipe_note(rec, rep):
    """One public sentence, written by code, saying how the job ended."""
    state = rec.get("state")
    if state == "DIED":
        head = ("It left the queue without writing its exit code: a time "
                "limit, a node failure or a cancel.")
    elif state == "COMPLETED":
        head = "It completed, exit 0."
    else:
        head = "It failed, exit %s." % (str(rec.get("exit") or "?")
                                        .split(":")[0])
    bits = [head]
    if rep.get("produced") or rep.get("missing"):
        bits.append("%d of %d outputs present." % (
            len(rep["produced"]), len(rep["produced"]) + len(rep["missing"])))
    if rep.get("exported") or rep.get("export_refused"):
        bits.append("%d exported, %d refused." % (
            len(rep.get("exported") or []), len(rep.get("export_refused") or [])))
    if state != "COMPLETED" and "output" in rep:
        bits.append("Its log, cut, is here too: the subject's phi is false.")
    elif state != "COMPLETED":
        bits.append("The log stays on the cluster; its RELAY: lines are what "
                    "it says here, and a diagnostic recipe asks it more.")
    return " ".join(bits)


# ---------------------------------------------------------------------------
# Colibri tasks: read-only analysis, checked when they finish
# ---------------------------------------------------------------------------
# A Colibri task reads the fenced data and writes what it makes under the
# workspace's ignored `phi/` (`colibri.TASK_PROMPT`). Its work is never
# tracked, so nothing of it needs a reviewer or a ship: the pass looks at the
# workspace once the task is done, and a change git can see there fails it.
CHANGED = ("a Colibri task changed tracked files; its work belongs in ignored "
           "locations")


def _stamp(full):
    """A file as it stands: size and modification time, or "gone"."""
    try:
        st = os.lstat(full)
    except OSError:
        return "gone"
    return "%d:%d" % (st.st_size, st.st_mtime_ns)


def workspace_changes(ws):
    """`{repository-relative path: _stamp}` for every change git can see under
    workspace `ws` -- tracked edits and untracked files it does not ignore --
    less what the cluster writes there: reports, and what this pass wrote. The job registry and the Colibri queue sit in the ignored
    `relay/state/`, which git does not see. None where git cannot say.

    `colibri.file` keeps this as a task's baseline, so the owner's edits from
    before the task are not the task's."""
    code, top = _git(ws, "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        return None
    base = os.path.realpath(top)
    rel = _rel(base, ws)
    got = _status(base, rel, strict=True)
    if got is None:
        return None
    prefix = "" if rel == "." else rel + "/"
    mine = [prefix + jobs.RELAY + "/reports"]
    written = set(_rel(base, p) for p in _WRITTEN)
    return dict((p, _stamp(os.path.join(base, p))) for p in got
                if not _under(p, mine) and p not in written)


def check_task(ws, rec, names_phi=None):
    """Did this finished task leave its workspace as git sees it? None where
    that cannot be read, so the task is checked again next pass; else
    `{"changed": count, "relay": lines}`.

    `changed` counts the paths changed since the task's baseline and never
    names them: they may sit beside the data. A task with no baseline counts
    every change. `relay` is the `RELAY:` lines of the client's output, made
    public; without the policy, none."""
    now = workspace_changes(ws)
    if now is None:
        return None
    before = rec.get("baseline")
    before = before if isinstance(before, dict) else {}
    changed = [p for p, stamp in now.items() if before.get(p) != stamp]
    lines = []
    out = rec.get("out")
    if names_phi is not None and isinstance(out, str) and out:
        lines = relay_lines(_tail(out), names_phi)
    return {"changed": len(changed), "relay": lines}


# ---------------------------------------------------------------------------
# relay/status.json: the relay's public health
# ---------------------------------------------------------------------------
# `{"skipped", "last_error", "push_pending", "outstanding", "colibri", "at"}`,
# every string through `public`. `outstanding` is `{subject: {request id:
# state}}` for each request the cluster has not ended; `colibri` is
# `colibri.relay_status`'s block, or null where this checkout has no queue.
# Neither names a node or a path. Computed at the end of every pass; written
# and committed only when a field other than `at` changed, so an idle relay
# makes no commits and the file is never left edited in the tree. A pass that
# runs commits it with its reports (`publish`). A skipped pass cannot touch the
# branch, so it commits the file on top of origin's tip through a temporary
# index and pushes that (`status_aside`): HEAD, the index and the tree stay as
# they were, and the next pull brings it in.
#
# The cluster is its only writer. A status commit is made only on a base that
# already holds every status commit origin has, so two never diverge and a
# rebase never meets one: a running pass writes it only when HEAD is not
# behind origin, and a skipped pass only when no unpushed commit carries it.
WITHHELD = "(withheld by the PHI policy)"


def status_doc(skipped, error, push_pending, at, names_phi=None,
               outstanding=None, colibri=None):
    def say(text):
        if not text:
            return ""
        said = public(_no_node(text), names_phi, 400)
        return said if said is not None else WITHHELD
    out = {}
    for subject, reqs in sorted((outstanding or {}).items()):
        name = public(subject, names_phi, 120)
        if not name or not reqs:
            continue
        out[name] = dict((rid, public(st, names_phi, 20) or "?")
                         for rid, st in sorted(reqs.items())
                         if jobs.REQUEST_ID_RE.match(str(rid)))
    return {"skipped": say(skipped), "last_error": say(error),
            "push_pending": bool(push_pending), "outstanding": out,
            "colibri": _colibri_status(colibri) if colibri else None,
            "at": int(at)}


def _colibri_status(block):
    """`colibri.relay_status`'s block, each field checked for its type: the
    status is public, so nothing but a state, numbers and a task id."""
    def num(v):
        return int(v) if isinstance(v, (int, float)) and not isinstance(
            v, bool) else None
    task = block.get("task")
    reason = block.get("reason")
    return {"state": str(block.get("state") or "unknown")[:12],
            "ends": num(block.get("ends")), "queue": num(block.get("queue")) or 0,
            "task": task if isinstance(task, str) and _TASK_RE.match(task)
            else None,
            "load_s": num(block.get("load_s")),
            "reason": reason if isinstance(reason, str)
            and re.match(r"^[A-Za-z]{1,40}$", reason) else ""}


_TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")


def _no_node(text):
    """`text` with this machine's own host name, whole or short, as
    `<node>`: the status names no node."""
    text = str(text)
    try:
        host = socket.gethostname() or ""
    except OSError:
        host = ""
    for name in sorted(set([host, host.split(".")[0]]), key=len, reverse=True):
        if len(name) >= 3:
            text = re.sub(r"(?<![\w.-])%s(?![\w-])" % re.escape(name),
                          "<node>", text)
    return text
ENDED = ("refused", "completed", "failed")


def outstanding(where):
    """`{subject: {request id: state}}`: every request in the tree whose
    report has not ended it, `requested` where it has no report."""
    out = {}
    for ws, rel in where:
        try:
            reps = jobs.reports(ws)
            for req in jobs.requests(ws):
                rid = request_id(req)
                st = str((reps.get(rid) or {}).get("state") or "requested")
                if st not in ENDED:
                    out.setdefault(rel, {})[rid] = st
        except Exception:                                    # noqa: BLE001
            continue
    return out


def colibri_block(base, st, now):
    """Colibri's block for `relay/status.json`, or None where this checkout
    has no queue. `st` is `relay/state.json`, whose `colibri` keeps what
    timing a load needs. Where it fails, HEAD's block stands."""
    from . import colibri
    prev = status_at(base).get("colibri")
    try:
        if not colibri.queue_root():
            return None
        memo = st.get("colibri") if isinstance(st.get("colibri"), dict) else {}
        got = colibri.relay_status(prev, memo, now)
        st["colibri"] = memo
        return got
    except Exception:                                        # noqa: BLE001
        return prev if isinstance(prev, dict) else None


def _same_status(a, b):
    def bare(d):
        return dict((k, v) for k, v in (d or {}).items() if k != "at")
    return bare(a) == bare(b)


def status_at(base, ref="HEAD"):
    """`relay/status.json` as `ref` has it, or {}."""
    code, out = _git(base, "show", "%s:%s" % (ref, STATUS), raw=True)
    if code != 0:
        return {}
    try:
        got = json.loads(out)
    except ValueError:
        return {}
    return got if isinstance(got, dict) else {}


def _status_text(doc):
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def read_status(base):
    """The tree's `relay/status.json`, or {}."""
    try:
        with open(os.path.join(base, STATUS), "r", encoding="utf-8") as fh:
            got = json.load(fh)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def write_status(base, doc):
    """Write `doc` into the tree when it differs from HEAD's beyond `at`.
    True when written, for `publish` to commit."""
    if _same_status(status_at(base), doc):
        return False
    path = os.path.join(base, STATUS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        fh.write(_status_text(doc))
    os.replace(path + ".tmp", path)
    return True


def status_dirty(base):
    """Does the tree's `relay/status.json` differ from HEAD's?"""
    code, out = _git(base, "status", "--porcelain", "--untracked-files=all",
                     "--", STATUS)
    return code == 0 and bool(out.strip())


def restore_status(base):
    """Put `relay/status.json` back as HEAD has it, or remove it where HEAD
    has none: a pass that wrote it and did not commit it leaves no edit."""
    if not status_dirty(base):
        return
    if _git(base, "cat-file", "-e", "HEAD:%s" % STATUS)[0] == 0:
        _git(base, "checkout", "-q", "HEAD", "--", STATUS)
    else:
        _git(base, "rm", "-q", "--cached", "--ignore-unmatch", "--", STATUS)
        try:
            os.remove(os.path.join(base, STATUS))
        except OSError:
            pass


def status_aside(base, doc):
    """A skipped pass's status, committed on origin's tip and pushed, with
    HEAD, the index and the tree untouched. "" or why not."""
    up = upstream(base)
    if not up:
        if _git(base, "rev-parse", "--verify", "--quiet",
                "refs/remotes/origin/main")[0] != 0:
            return "no upstream to push the status to"
        up = ("origin", "main", "origin/main")
    remote, theirs, ref = up
    code, out = _git(base, "fetch", "--quiet", remote, theirs, timeout=60)
    if code != 0:
        return "fetch from %s failed: %s" % (
            remote, out.splitlines()[-1] if out else "no output")
    code, tip = _git(base, "rev-parse", "--verify", "--quiet",
                     "%s^{commit}" % ref)
    if code != 0 or not tip:
        return "no %s to put the status on" % ref
    if _same_status(status_at(base, tip), doc):
        return ""
    code, carried = _git(base, "rev-list", "--max-count=1", "%s..HEAD" % tip,
                         "--", STATUS, raw=True)
    if code == 0 and carried.strip():
        return ("an unpushed commit here carries the status; the next pass "
                "that pushes publishes it")
    scratch = tempfile.mkdtemp(prefix="relay-status-")
    env = {"GIT_INDEX_FILE": os.path.join(scratch, "index")}
    try:
        code, blob = _git(base, "hash-object", "-w", "--stdin",
                          input=_status_text(doc))
        if code != 0:
            return "status commit failed: %s" % blob
        for args in (("read-tree", tip),
                     ("update-index", "--add", "--cacheinfo", "100644", blob,
                      STATUS)):
            code, out = _git(base, *args, env=env)
            if code != 0:
                return "status commit failed: %s" % (out.splitlines()
                                                     or [""])[-1]
        code, tree = _git(base, "write-tree", env=env)
        if code != 0:
            return "status commit failed: %s" % tree
        code, sha = _git(base, "commit-tree", tree, "-p", tip, "-m",
                         "relay: status")
        if code != 0:
            return "status commit failed: %s" % (sha.splitlines() or [""])[-1]
        code, out = _git(base, "push", "--quiet", remote,
                         "%s:refs/heads/%s" % (sha, theirs), timeout=180)
        if code != 0:
            return "status push rejected, retried next pass: %s" % (
                out.splitlines() or [""])[-1]
        return ""
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# the pass
# ---------------------------------------------------------------------------
def state_path(base):
    return os.path.join(base, STATE)


def read_state(base):
    try:
        with open(state_path(base), "r", encoding="utf-8") as fh:
            got = json.load(fh)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(base, st):
    path = state_path(base)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)


def sbatch_env():
    """The environment a submission runs in: this one, less the Slurm
    variables a pass inherits from its own scrontab job."""
    return dict((k, v) for k, v in os.environ.items()
                if not k.startswith(("SLURM_", "SBATCH_", "SRUN_")))


def run_pass(base=None, run=subprocess.run, now=None, pull_vendor=None,
             push=True):
    """One pass. Returns a summary dict; `relay/state.json` records it, and
    `relay/status.json` says the public part of it when that changed.

    `run` is how Slurm is asked (sbatch, scontrol, squeue), so a test can
    answer from a table; git is always the real one.
    """
    base = os.path.realpath(base or subjects.root())
    lock = os.path.join(base, LOCK)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    fh = open(lock, "a+")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return {"skipped": "another pass holds the lock"}
        return _locked_pass(base, run, now, pull_vendor, push)
    finally:
        fh.close()


def _locked_pass(base, run, now, pull_vendor, push):
    t0 = float(now or time.time())
    st = read_state(base)
    summary = {"submitted": [], "refused": [], "ended": [], "skipped": "",
               "error": ""}
    errors = []
    wrote = False
    _WRITTEN.clear()
    try:
        where = spaces(base)
        skip, err = pull(base, where, pull_vendor)
        if err:
            errors.append(err)
        if skip:
            summary["skipped"] = skip
            up = upstream(base)
            doc = status_doc(skip, "; ".join(errors), up and _count(
                base, "%s..HEAD" % up[2]), t0, leaving.policy(base),
                outstanding(where), colibri_block(base, st, t0))
            if push:
                err = status_aside(base, doc)
                if err:
                    errors.append(err)
        else:
            where = spaces(base)
            _work(base, where, run, t0, summary)
            errors.extend(summary.pop("errors", []))
            # Waiting to be pushed: what an earlier pass committed and could
            # not push. Written only where HEAD has all origin has.
            up = upstream(base)
            block = colibri_block(base, st, t0)
            if up and not _count(base, "HEAD..%s" % up[2]):
                wrote = write_status(base, status_doc(
                    "", "; ".join(errors), _count(base, "%s..HEAD" % up[2]),
                    t0, leaving.policy(base), outstanding(where), block))
            ids = summary["submitted"] + summary["refused"] + summary["ended"]
            msg = ("relay: %d report(s) -- %s" % (len(ids), ", ".join(ids[:6]))
                   if ids else "relay: reports")
            sha, err = publish(base, where, msg[:200], push=push)
            if err:
                errors.append(err)
            # Changed under exports/ or relay/reports/ and not written by a
            # pass: never committed, and named here for the owner.
            st["unpublished"] = staged_paths(base, where)[1][:50]
            if sha:
                st["last_pushed"] = sha
                st["pushed_at"] = time.time()
    except Exception as exc:                                 # noqa: BLE001
        errors.append("%s: %s" % (type(exc).__name__, exc))
    if wrote:
        restore_status(base)        # its commit failed: leave no edit behind
    summary["error"] = "; ".join(errors)
    st.update({"last_pass": t0, "host": socket.gethostname(),
               "skipped": summary["skipped"],
               "push_pending": any("push rejected" in e for e in errors),
               "counts": dict((k, len(summary[k])) for k in
                              ("submitted", "refused", "ended"))})
    if errors:
        st["last_error"] = summary["error"]
        st["error_at"] = t0
    _save_state(base, st)
    return summary


def _num(value):
    """A sortable number out of a request's `filed`, whatever it contains."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


NO_POLICY = ("the PHI guard's policy (ai-config/policy/phi.py) is not "
             "installed in this checkout, so no request runs here")


def _work(base, where, run, now, summary):
    from . import colibri
    names_phi = leaving.policy(base)
    env = sbatch_env()
    errors = summary.setdefault("errors", [])
    for ws, rel in where:
        # One workspace's trouble is that workspace's: the others, the
        # Colibri step and the publish still run.
        try:
            _work_space(ws, run, now, summary, names_phi, env)
        except Exception as exc:                             # noqa: BLE001
            errors.append("%s: %s: %s" % (rel, type(exc).__name__, exc))
    # --- 4. Colibri: each task checked once it is done, and reported -------
    try:
        _colibri_step(now, summary, names_phi, colibri)
    except Exception as exc:                                 # noqa: BLE001
        errors.append("colibri: %s: %s" % (type(exc).__name__, exc))


def _work_space(ws, run, now, summary, names_phi, env):
    from . import colibri
    reqs = jobs.requests(ws)
    if not reqs:
        # A workspace with no requests can still have jobs `board job`
        # submitted here directly; their endings wake its inbox.
        jobs.report(ws, run=run, now=now)
        return
    reps = jobs.reports(ws)
    by_id = dict((request_id(r), r) for r in reqs)
    # --- 2. requests with no report -----------------------------------------
    for req in sorted(reqs, key=lambda r: (_num(r.get("filed")),
                                           request_id(r))):
        rid = request_id(req)
        if rid in reps:
            continue
        try:
            _one_request(ws, req, rid, run, now, summary, names_phi, env,
                         colibri)
        except Exception as exc:                             # noqa: BLE001
            # Refused, so it is not tried again every pass for ever.
            refuse(ws, req, ["the relay failed on this request (%s)"
                             % type(exc).__name__], now, names_phi)
            summary["refused"].append(rid)
    # --- 3. poll ------------------------------------------------------------
    _poll(ws, by_id, run, now, summary, names_phi)


def _one_request(ws, req, rid, run, now, summary, names_phi, env, colibri):
    ok, problems = jobs.check(ws, req, mine=True)
    if problems:
        refuse(ws, req, problems, now, names_phi)
        summary["refused"].append(rid)
        return
    if names_phi is None:
        refuse(ws, req, [NO_POLICY], now)
        summary["refused"].append(rid)
        return
    if ok["kind"] == "colibri":
        got = colibri.relay_file(ws, ok)
        write_report(ws, rid, _colibri_public(got, rid, names_phi, now, req))
        summary["refused" if got.get("state") == "refused"
                else "submitted"].append(rid)
        return
    if ok["kind"] != "recipe":
        refuse(ws, req, ["the relay has no way to run a %s request"
                         % ok["kind"]], now, names_phi)
        summary["refused"].append(rid)
        return
    ran_at = jobs.head(ws, short=True) or "unknown"
    rec, why = jobs.submit_recipe(
        ws, ok.get("label"), ok["recipe"], env=ok["env"],
        produces=ok["produces"], export=ok["export"], key=rid,
        run=run, now=now, sbatch_env=env,
        extra={"request": rid, "kind": "recipe", "ran_at": ran_at})
    if not rec:
        refuse(ws, req, [why], now, names_phi)
        summary["refused"].append(rid)
        return
    rep = _base_report(req, "submitted", now, names_phi)
    rep.update({"jobid": rec["jobid"], "submitted": rec["submitted"],
                "ran_at": ran_at})
    write_report(ws, rid, rep)
    summary["submitted"].append(rid)


def _colibri_public(rep, rid, names_phi, now, req=None):
    """A Colibri task's report, every string in it made public. Its `label`
    and `session` are the request's (`_base_report`), never the task's."""
    out = dict((k, v) for k, v in rep.items()
               if k not in ("label", "session", "thread"))
    out.update(id=rid, kind="colibri", updated=round(float(now), 3))
    for key in ("label", "session"):
        said = _field((req or {}).get(key), names_phi)
        if said:
            out[key] = said
    if "note" in out:
        said = public(out.get("note"), names_phi, MAX_NOTE)
        out["note"] = (said if said is not None else
                       "The note was withheld: the PHI policy matched it.")
    if out.get("problems"):
        out["problems"] = [public(p, names_phi, 400) or "(withheld by the PHI "
                           "policy)" for p in out["problems"]]
    for key in ("task", "jobid"):
        if key in out:
            out[key] = _field(str(out[key]), names_phi)
    if "relay" in out:
        # Scrubbed when the task was checked, and again here: nothing in a
        # report is trusted to have been made public somewhere else.
        said = [public(l, names_phi) for l in out.get("relay") or []
                if isinstance(l, str)] if names_phi is not None else []
        out["relay"] = [l for l in said if l][-MAX_LINES:]
    return out


def _colibri_step(now, summary, names_phi, colibri):
    """Step 4. `colibri.relay_pass`, which checks each finished task with
    `check_task`, and the report of each task a request filed."""
    def check(ws, rec):
        return check_task(ws, rec, names_phi)

    for ws, rep in colibri.relay_pass(check=check, now=now):
        rid = rep.get("id")
        if not isinstance(rid, str) or not jobs.REQUEST_ID_RE.match(rid):
            continue
        req = next((r for r in jobs.requests(ws) if request_id(r) == rid),
                   None)
        if req is None:
            continue
        out = _colibri_public(rep, rid, names_phi, now, req)
        old = jobs.reports(ws).get(rid) or {}
        # The HEAD the task was queued at, which `write_report` stamped.
        if old.get("ran_at"):
            out["ran_at"] = old["ran_at"]
        same = dict((k, v) for k, v in old.items() if k != "updated")
        if same == dict((k, v) for k, v in out.items() if k != "updated"):
            continue
        write_report(ws, rid, out)
        if out.get("state") in ("completed", "failed"):
            summary["ended"].append(rid)


def _poll(ws, by_id, run, now, summary, names_phi):
    jobs.report(ws, run=run, now=now)
    ended = jobs.poll(ws, run=run, now=now, relay=True)
    reps = jobs.reports(ws)
    for rec in jobs.records(ws, relay=True).values():
        rid = rec.get("request")
        if rid not in by_id:
            continue
        rep = reps.get(rid) or {}
        if (not exports.finished(rec) and rec.get("state") == "RUNNING"
                and rep.get("state") == "submitted"):
            rep = dict(rep, state="running", updated=round(now, 3),
                       started=rec.get("seen") or now)
            write_report(ws, rid, rep)
    allowed = exports.approvals(ws)
    for rec in ended:
        rid = rec.get("request")
        req = by_id.get(rid)
        try:
            if not req:
                raise KeyError("request %s is gone" % rid)
            finish(ws, rec, req, allowed, now, names_phi)
        except Exception:                                    # noqa: BLE001
            # No report, so no claim: the next pass offers it again.
            jobs._unclaim(ws, rec["jobid"])
            continue
        jobs.append(ws, {"jobid": rec["jobid"], "request": rid,
                         "reported": float(now)})
        summary["ended"].append(rid)


# ---------------------------------------------------------------------------
# status, and where
# ---------------------------------------------------------------------------
def _ago(t, now=None):
    if not t:
        return "never"
    d = max(0, int(float(now or time.time()) - float(t)))
    if d < 120:
        return "%d s ago" % d
    if d < 7200:
        return "%d min ago" % (d // 60)
    return "%.1f h ago" % (d / 3600.0)


def where_line(base=None, now=None):
    """The relay's last pass in one line, or "" where it never ran."""
    st = read_state(os.path.realpath(base or subjects.root()))
    if not st.get("last_pass"):
        return ""
    said = "relay: last pass %s on %s" % (_ago(st["last_pass"], now),
                                          st.get("host") or "?")
    if st.get("skipped"):
        said += ", SKIPPED: %s" % st["skipped"]
    if st.get("last_pushed"):
        said += "; last pushed %s" % st["last_pushed"][:8]
    if st.get("push_pending"):
        said += "; a push is pending"
    if st.get("last_error"):
        said += "; last error %s: %s" % (_ago(st.get("error_at"), now),
                                         st["last_error"][:160])
    return said


def status(base=None, now=None):
    """What `tutor relay --status` prints: the last pass, and every
    workspace's requests by state."""
    base = os.path.realpath(base or subjects.root())
    lines = [where_line(base, now) or "relay: no pass has run here"]
    for ws, rel in spaces(base):
        reqs = jobs.requests(ws)
        if not reqs:
            continue
        reps = jobs.reports(ws)
        counts = {}
        for r in reqs:
            s = (reps.get(str(r.get("id"))) or {}).get("state") or "requested"
            counts[s] = counts.get(s, 0) + 1
        out = [j for j in jobs.records(ws, relay=True).values()
               if not exports.finished(j)]
        lines.append("  %-28s %s%s" % (rel, ", ".join(
            "%d %s" % (counts[k], k) for k in sorted(counts)),
            "; jobs out: %s" % ", ".join(
                "%s (%s)" % (j["jobid"], j.get("state") or "PENDING")
                for j in out) if out else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the Mac's view of the cluster: relay down, not synced, Colibri
# ---------------------------------------------------------------------------
# Read on the Mac from its own tree and `<state>/pull.json` only, never from
# Slurm (D27). A request whose commit origin has, with no report
# `DOWN_AFTER` seconds later, says the relay looks down: every pass reports
# every request it can see. A failed pull or ls-remote in pull.json
# (`cluster.Ear`) says "not synced". `health` is cached for `HEALTH_TTL`
# seconds because the board's payload asks on every build.
DOWN_AFTER = 15 * 60
HEALTH_TTL = 20.0
_HEALTH = {}


def forget():
    """Drop the cached health: something just changed it."""
    _HEALTH.clear()


def _filed_at(atlas, rel):
    """`(sha, commit time)` of the last commit touching `rel`, or `(None, 0)`."""
    code, out = _git(atlas, "log", "-1", "--format=%H %ct", "--", rel,
                     timeout=20)
    parts = out.split() if code == 0 else []
    if len(parts) != 2 or not parts[1].isdigit():
        return None, 0
    return parts[0], int(parts[1])


def stale_requests(atlas, now=None, after=DOWN_AFTER):
    """`[{subject, id, since}]`: each request with no report `after` seconds
    past the commit that filed it. One not committed, or committed and not
    on origin's main, is not the relay's to have seen."""
    now = float(now or time.time())
    on_origin = _git(atlas, "rev-parse", "--verify", "--quiet",
                     "refs/remotes/origin/main")[0] == 0
    out = []
    for ws in subjects.roots(atlas):
        reqs = jobs.requests(ws)
        if not reqs:
            continue
        reps = jobs.reports(ws)
        for req in reqs:
            rid = request_id(req)
            if rid in reps:
                continue
            rel = _rel(atlas, os.path.join(jobs.requests_dir(ws), "%s.json"
                                           % req.get(jobs.FILE_KEY)))
            sha, when = _filed_at(atlas, rel)
            if not sha or now - when < after:
                continue
            if on_origin and _git(atlas, "merge-base", "--is-ancestor", sha,
                                  "refs/remotes/origin/main")[0] != 0:
                continue
            out.append({"subject": _rel(atlas, ws), "id": rid, "since": when})
    out.sort(key=lambda r: (r["since"], r["id"]))
    return out


def pull_health(state_dir=None):
    """pull.json as the Mac's health: `{ok, said, step, at}`, `said` being
    "not synced: <git's words>" when the last pull or ls-remote failed; None
    where the cluster thread has written none."""
    from . import cluster
    path = os.path.join(state_dir or paths.STATE_DIR, cluster.PULL_STATE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict):
        return None
    if rec.get("ok") is not False:
        return {"ok": True, "said": "", "step": rec.get("step"),
                "at": rec.get("at")}
    said = str(rec.get("said") or "the %s failed" % (rec.get("step") or "pull"))
    if not said.startswith("not synced"):
        said = "not synced: " + said
    return {"ok": False, "said": said[:400], "step": rec.get("step"),
            "at": rec.get("at")}


def health(atlas, now=None, state_dir=None, fresh=False):
    """The cluster's health as the Mac sees it: `{down, stale, pull, status,
    lines}`. `lines` are the sentences to show, worst first; `[]` when all
    is well."""
    atlas = os.path.realpath(atlas)
    key = (atlas, state_dir)
    t = time.time()
    hit = _HEALTH.get(key)
    if not fresh and now is None and hit and t - hit[0] < HEALTH_TTL:
        return json.loads(hit[1])
    stale = stale_requests(atlas, now)
    pull_said = pull_health(state_dir)
    doc = read_status(atlas)
    lines = []
    if stale:
        lines.append("relay looks down: %s had no report %d minutes after "
                     "%s commit" % (
                         ", ".join("%s %s" % (r["subject"], r["id"])
                                   for r in stale[:3])
                         + (" and %d more" % (len(stale) - 3)
                            if len(stale) > 3 else ""),
                         DOWN_AFTER // 60,
                         "its" if len(stale) == 1 else "their"))
    if pull_said and not pull_said["ok"]:
        lines.append(pull_said["said"])
    if doc.get("skipped"):
        lines.append("the relay skipped its last pass: %s" % doc["skipped"])
    if doc.get("last_error"):
        lines.append("the relay's last error: %s" % doc["last_error"])
    if doc.get("push_pending"):
        lines.append("the relay has reports it has not pushed yet")
    out = {"down": bool(stale), "stale": stale, "pull": pull_said,
           "synced": not (pull_said and not pull_said["ok"]),
           "status": dict((k, doc.get(k)) for k in (
               "skipped", "last_error", "push_pending", "at")),
           "lines": lines}
    _HEALTH[key] = (t, json.dumps(out))
    return out


def panel(atlas, now=None, state_dir=None):
    """GET /relay.json: `health`, and Colibri as status.json says it, with
    the libr-local-llm tasks the panel lists and what filing one costs."""
    from . import colibri
    out = health(atlas, now, state_dir)
    st = colibri.status(atlas, now)
    found = subjects.find(colibri.WORKSPACE, base=atlas)
    out.update({"ok": True, "colibri": st,
                "colibri_subject": found["id"] if found else None,
                "colibri_tasks": colibri.tasks_on_mac(
                    found["root"], running=st.get("task"))
                if found else [],
                "estimate": colibri.estimate(st)})
    return out


# ---------------------------------------------------------------------------
# the scrontab entry
# ---------------------------------------------------------------------------
def scrontab_block(python=None, entry=None, log=None):
    """The entry, between markers so `install` can replace it.

    It runs `bash <entry>`, `board/scripts/relay-pass.sh` by default, with
    RELAY_PYTHON set to the interpreter that installed it: a scrontab job's
    PATH may find an older python3 first."""
    python = python or sys.executable
    entry = entry or os.path.join(paths.TOOL, "scripts", "relay-pass.sh")
    log = log or os.path.join(paths.STATE_DIR, "relay-scron.log")
    return "\n".join([
        SCRON_BEGIN + " (written by `relay --install`)",
        "#SCRON --partition=%s" % SCRON_PARTITION,
        "#SCRON --time=%s" % SCRON_TIME,
        "#SCRON --cpus-per-task=1",
        "#SCRON --mem=2G",
        "#SCRON --job-name=tutor-relay",
        "#SCRON --output=%s" % log,
        "#SCRON --open-mode=append",
        "*/%d * * * * RELAY_PYTHON=%s bash %s" % (PASS_MINUTES,
                                                  shlex.quote(python),
                                                  shlex.quote(entry)),
        SCRON_END,
    ]) + "\n"


def merged_crontab(old, block):
    """`old` with the relay's block replaced, or appended. Pure."""
    lines, out, inside = (old or "").splitlines(), [], False
    for line in lines:
        if line.startswith(SCRON_BEGIN):
            inside = True
            continue
        if inside:
            if line.startswith(SCRON_END):
                inside = False
            continue
        out.append(line)
    text = "\n".join(out).rstrip("\n")
    return (text + "\n" if text else "") + block


def install(run=subprocess.run):
    """Write the entry into this user's scrontab. `(ok, said)`."""
    p = run(["scrontab", "-l"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    old = p.stdout if p.returncode == 0 else ""
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    new = merged_crontab(old, scrontab_block())
    tmp = os.path.join(paths.STATE_DIR, "scrontab.%s" % getpass.getuser())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    q = run(["scrontab", tmp], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
    return q.returncode == 0, (q.stdout or "").strip()
