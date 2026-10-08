"""Every commit, push and pull the board makes, in one place.

    commit(root, paths, message, refuse=None)   named paths only, no trailers
    push(root)                                  fetch, merge, push; never forced
    pull(root)                                  fast-forward only, guarded
    save(root, paths, message)                  commit, then push
    hear_pass()                                 the Mac's timed pull, then hearing

`board/scripts/save-and-push.sh` is a thin CLI over `save`. relay.py and
holds.py keep their own cluster-side git until T38c replaces them.

Nothing here commits into an operation somebody started in a terminal: a
rebase, a merge, a cherry-pick, a revert, a bisect or a detached HEAD all mean
a person has their own plan for the next commit (`worktree.busy_reason`).

Runs on the cluster's python3 too (relay path): no walrus, no `match`.
"""

import os
import subprocess
import sys
import time

from tutorboard import worktree

# A network step that waits longer than this is a credential prompt nobody can
# see, or a remote that is down. Either way the answer is to stop and say so.
NET_TIMEOUT = 120
LOCAL_TIMEOUT = 60
# A commit runs the hooks, and Atlas's pre-commit gate reads the staged diff.
COMMIT_TIMEOUT = 180

_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false"}


def _git(root, *args, **kw):
    """`(code, output)` of one git command in `root`, stdout and stderr
    together. Never raises: a timeout is code 124, a missing git 127."""
    env = dict(os.environ, **_ENV)
    try:
        p = subprocess.run(["git"] + list(args), cwd=root, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=kw.get("timeout", LOCAL_TIMEOUT))
    except subprocess.TimeoutExpired:
        return 124, "git %s timed out" % args[0]
    except OSError as exc:
        return 127, str(exc)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def _lines(text):
    return sorted(set(l for l in text.splitlines() if l.strip()))


def _hooks(root):
    """Turn on a repository's own `.githooks/` when `core.hooksPath` is unset,
    so the attribution stripper and the commit-time gate run from its first
    commit. A repository without `.githooks/` is left as it is: a hook path
    pointing into another repository would run that repository's gate here."""
    if not os.path.isdir(os.path.join(root, ".githooks")):
        return None
    code, now = _git(root, "config", "core.hooksPath")
    if code == 0 and now:
        return None
    _git(root, "config", "core.hooksPath", ".githooks")
    return "enabled .githooks for this clone"


def commit(root, paths, message, refuse=None):
    """Commit the named `paths` (relative to `root`) and nothing else.
    `(ok, said)`; nothing to commit is ok.

    `git add -A -- paths`, then a commit of exactly those paths: whatever else
    is staged stays staged and out of this commit. The message goes in as
    given, with no trailers. `refuse(paths)` may return a reason, and then
    nothing is committed.

    `--only` is used only when something outside the paths is staged. It takes
    each path from the working tree, so it drops a staged removal of a file
    still on disk (`git rm --cached`); that case is named, never silent.
    """
    paths = [p for p in (paths or []) if p]
    if not paths:
        return False, "no paths named, so nothing was committed"
    if refuse is not None:
        why = refuse(list(paths))
        if why:
            return False, why
    code, _ = _git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return False, "not a git repository: %s" % root
    busy = worktree.busy_reason(root)
    if busy:
        return False, ("nothing was committed: %s in this repository. Nothing "
                       "has been lost -- finish or abort it, then save again."
                       % busy)
    said = []
    hooked = _hooks(root)
    if hooked:
        said.append(hooked)
    code, out = _git(root, "add", "-A", "--", *paths)
    if code != 0:
        return False, "git add failed: %s" % out
    _, staged = _git(root, "diff", "--cached", "--name-only")
    _, mine = _git(root, "diff", "--cached", "--name-only", "--", *paths)
    if not mine.strip():
        said.append("nothing to commit")
        return True, "\n".join(said)
    if _lines(staged) == _lines(mine):
        cmd = ["commit", "-q", "-m", message]
    else:
        cmd = ["commit", "-q", "--only", "-m", message, "--"] + paths
        _, gone = _git(root, "diff", "--cached", "--name-only",
                       "--diff-filter=D", "--", *paths)
        kept = [f for f in _lines(gone) if os.path.exists(os.path.join(root, f))]
        if kept:
            said.append(
                "NOT UNTRACKED: %s\n  staged for removal, still on disk, and "
                "something outside the pathspec is staged -- so this commit "
                "uses --only, which takes those paths from the working tree "
                "and drops the removal.\n  Nothing has been lost. Commit the "
                "removal by itself: stage only it and commit with no pathspec."
                % " ".join(kept))
    code, out = _git(root, *cmd, timeout=COMMIT_TIMEOUT)
    if code != 0:
        said.append("git commit failed: %s" % out)
        return False, "\n".join(said)
    said.append("committed: %s" % (message.splitlines() or [""])[0])
    return True, "\n".join(said)


def push(root, timeout=NET_TIMEOUT):
    """Push the current branch to origin. `(ok, said)`. Never forced.

    With an upstream: fetch it, merge it in when it is ahead (a merge, so
    nothing committed here is rewritten), then push. A conflict only in
    generated `build/` output keeps this machine's copy; any other conflict
    abandons the merge and pushes nothing. With no upstream: `push -u`.
    """
    code, _ = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return True, "committed locally; no 'origin' remote to push to"
    code, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or branch == "HEAD":
        return False, "HEAD is detached, so there is no branch to push"
    code, up = _git(root, "rev-parse", "--abbrev-ref", "@{upstream}")
    said = []
    if code == 0 and up:
        _, ahead = _git(root, "rev-list", "--count", "@{upstream}..HEAD")
        if ahead.strip() == "0":
            return True, "already up to date"
        code, out = _git(root, "fetch", "origin", branch, timeout=timeout)
        if code != 0:
            return False, ("could not fetch origin/%s, so nothing was pushed:\n%s"
                           % (branch, "\n".join(out.splitlines()[-5:])))
        _, behind = _git(root, "rev-list", "--count", "HEAD..@{upstream}")
        _, dirty = _git(root, "status", "--porcelain")
        if behind.strip() not in ("", "0") and dirty.strip():
            said.append("origin/%s is ahead and this tree has uncommitted work "
                        "outside the commit, so it was not merged in; the push "
                        "may be rejected. Save the rest, then push again." % branch)
        elif behind.strip() not in ("", "0"):
            ok, why = _merge(root, branch)
            if not ok:
                return False, why
            said.append(why)
        code, out = _git(root, "push", timeout=timeout)
    else:
        code, out = _git(root, "push", "-u", "origin", branch, timeout=timeout)
    if code != 0:
        said.append("push failed:\n%s" % "\n".join(out.splitlines()[-5:]))
        return False, "\n".join(said)
    said.append("pushed %s to origin" % branch)
    return True, "\n".join(said)


def _merge(root, branch):
    """Merge `@{upstream}` in. `(ok, said)`; a failed merge is abandoned,
    never left standing, because a repository left mid-merge refuses every
    later save."""
    code, _ = _git(root, "merge", "--no-edit", "@{upstream}")
    if code == 0:
        return True, "merged origin/%s" % branch
    _, out = _git(root, "diff", "--name-only", "--diff-filter=U")
    conflicts = _lines(out)
    real = [f for f in conflicts
            if not (f.startswith("build/") or "/build/" in f)]
    if real:
        _git(root, "merge", "--abort")
        return False, ("merge conflicts outside build output; resolve by hand:\n"
                       + "\n".join(real))
    for f in conflicts:
        _git(root, "checkout", "--ours", "--", f)
        _git(root, "add", "--", f)
    code, _ = _git(root, "commit", "--no-edit")
    if code != 0:
        _git(root, "merge", "--abort")
        return False, ("the merge could not be completed, so it was abandoned "
                       "and nothing was pushed. The commit above is safe here. "
                       "Merge by hand.")
    return True, "merged origin/%s; kept this machine's build output" % branch


def save(root, paths, message, refuse=None):
    """`commit`, then `push` when the commit did not fail. `(ok, said)`."""
    ok, said = commit(root, paths, message, refuse=refuse)
    if not ok:
        return False, said
    ok, pushed = push(root)
    return ok, "%s\n%s" % (said, pushed)


def _vendor_moved(root, before, after):
    """True when a gitlink under `vendor/` differs between two commits."""
    code, out = _git(root, "diff", "--raw", "--no-renames", before, after,
                     "--", "vendor")
    if code != 0:
        return False
    for line in out.splitlines():
        modes = line.split()[:2]
        if any(m.lstrip(":") == "160000" for m in modes):
            return True
    return False


def pull(root, quiet=False, timeout=60, say=None):
    """Fast-forward `root` to its upstream. True when it ran, False when it was
    refused or failed, None where there is nothing to pull (no repository, no
    origin). Never raises.

    Refused, changing nothing, during a rebase, merge, cherry-pick, revert or
    bisect and on a detached HEAD. A pull that moved a gitlink under `vendor/`
    then runs `git submodule update --init -- vendor`, so this machine's vendor
    checkouts stay clean; only the cluster relay bumps vendor pointers.

    `timeout` bounds the pull. `say`, where given, hears every line `quiet`
    would otherwise drop.
    """
    def tell(msg):
        if say is not None:
            say(msg.strip())
        elif not quiet:
            print(msg)
    if not worktree.git_dir(root):
        return None
    busy = worktree.busy_reason(root)
    if busy:
        tell("  not synced: %s here, so the repository is left exactly as it is"
             % busy)
        return False
    # A lock a killed git left behind stops a pull as surely as a commit; one
    # somebody is holding is left, and the pull below fails and says so.
    cleared = worktree.clear_stale_lock(root)
    if cleared:
        tell("  " + cleared)
    code, _ = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return None
    _, before = _git(root, "rev-parse", "HEAD")
    code, out = _git(root, "pull", "--ff-only", timeout=timeout)
    if code in (124, 127):
        tell("  could not reach the remote; working with what is here")
        return False
    if code != 0:
        last = out.splitlines()
        tell("  not synced: %s" % (last[-1] if last else "pull failed"))
        if say is None:
            tell("  the session will start anyway, on what is here")
        return False
    _, after = _git(root, "rev-parse", "HEAD")
    if before != after:
        _, n = _git(root, "rev-list", "--count", "%s..%s" % (before, after))
        tell("  pulled %s commit(s) from another machine" % n)
        if _vendor_moved(root, before, after):
            code, out = _git(root, "submodule", "update", "--init", "--",
                             "vendor", timeout=max(timeout, NET_TIMEOUT))
            if code != 0:
                last = out.splitlines()
                tell("  vendor checkouts not updated: %s"
                     % (last[-1] if last else "submodule update failed"))
            else:
                tell("  vendor checkouts moved to the pulled pointers")
    return True


# ---------------------------------------------------------------------------
# the Mac's ear: the hear pull
# ---------------------------------------------------------------------------
# On a machine without Slurm the cluster's reports arrive by pull, every
# `jobs.PULL_EVERY` seconds. The timer runs `tutor pull --hear` every twenty
# seconds and `hear_pass` decides; every run then hears every workspace,
# because a hand pull may have moved HEAD in between.
HEAR_STAMP = os.path.join(os.path.expanduser("~"), ".local", "state",
                          "tutor-pull.heard")

# ai-config is the one private repository nested inside Atlas and ignored by
# it. bootstrap.sh carries the same URL.
AI_CONFIG = "ai-config"
AI_CONFIG_URL = "https://github.com/Pirate-Hunter-Zoro/ai-config.git"


def adopt_private(base, quiet=True, run=subprocess.run):
    """Clone or adopt ai-config when this checkout lacks its repository,
    through `bootstrap.sh --private-only`. True if it ran."""
    if os.path.exists(os.path.join(base, AI_CONFIG, ".git")):
        return False
    script = os.path.join(base, "board", "bootstrap.sh")
    if not os.path.isfile(script):
        return False
    try:
        p = run(["bash", script, "--private-only"], cwd=base,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=600,
                env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.SubprocessError):
        return False
    if not quiet:
        print((p.stdout or "").rstrip())
    return True


def hear_pass(base=None, stamp=None, now=None, force=False, quiet=True,
              pull=None):
    """Pull Atlas when due, then hear every workspace's reports.

    `(pulled, interval, heard)`: `pulled` is None where the relay owns pulls
    here (Slurm), True where the pull ran, False where it was not due or
    failed. Never raises.
    """
    from tutorboard import atlas, holds, jobs
    if jobs.has_slurm():
        return None, 0, []
    stamp = stamp or HEAR_STAMP
    now = time.time() if now is None else float(now)
    try:
        base = base or atlas.root()
        roots = [w["root"] for w in atlas.workspaces(base)]
    except Exception:                                        # noqa: BLE001
        return False, 0, []
    interval = jobs.PULL_EVERY
    try:
        with open(stamp, "r", encoding="utf-8") as fh:
            last = float(fh.read().strip() or 0)
    except (OSError, ValueError):
        last = 0
    pulled = False
    if force or jobs.pull_due(last, now, interval):
        adopt_private(base, quiet=quiet)
        try:
            pulled = (pull or globals()["pull"])(base, quiet=quiet) is True
        except Exception:                                    # noqa: BLE001
            pulled = False
        try:
            os.makedirs(os.path.dirname(stamp), exist_ok=True)
            with open(stamp, "w", encoding="utf-8") as fh:
                fh.write("%f\n" % now)
        except OSError:
            pass
    heard = []
    for root in roots:
        for rec in jobs.hear(root, now=now):
            heard.append(dict(rec, workspace=atlas.identify(root) or root))
        try:
            woke = holds.wake(root, now=now)
        except Exception:                                    # noqa: BLE001
            woke = []
        for rep in woke:
            heard.append({"request": rep.get("id"), "state": "coach",
                          "thread": rep.get("thread"),
                          "workspace": atlas.identify(root) or root})
    return pulled, interval, heard


def main(argv=None):
    """`save-and-push.sh "message" -- <paths>`: commit the named paths of the
    repository the working directory is in, then push. Paths are relative to
    that repository's root. Exit 0 on success or nothing to commit."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv or argv.index("--") > 1 or argv[-1] == "--":
        print('usage: save-and-push.sh ["message"] -- <path>...  '
              "(a commit carries named paths only)")
        return 2
    cut = argv.index("--")
    message = argv[0] if cut == 1 and argv[0] else "lesson complete"
    paths = argv[cut + 1:]
    code, top = _git(os.getcwd(), "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        print("not a git repository: %s" % os.getcwd())
        return 1
    ok, said = save(top, paths, message)
    print(said)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
