"""The repository underneath a lesson, which somebody else may be working in.

The owner also works in these repositories from a terminal, and the board
writes git unattended, so: commit only against an explicit pathspec with
`--only`, which leaves the rest of the index alone; and never write history
into a repository mid-operation (rebase, merge, cherry-pick, revert, bisect,
detached HEAD) but wait and say why. A killed git's stale `index.lock` is
told from a live one and cleared.

The constraint: no `git` calls here; everything is read off the files git
keeps, so it is cheap on every beat and cannot hang on a lock.
"""

import os
import time


def git_dir(root):
    """The `.git` of the repository this directory is in, or None.

    Walks up to the nearest enclosing repository, because subjects live inside
    Atlas and a guard looking only in the workspace would see nothing to
    guard. Reads a `.git` file (`gitdir: ...`) as well as a directory, for
    worktrees and submodules.
    """
    here = os.path.realpath(root)
    for _ in range(40):
        found = os.path.join(here, ".git")
        if os.path.isdir(found):
            return found
        if os.path.isfile(found):
            try:
                with open(found, "r", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("gitdir:"):
                            path = line.split(":", 1)[1].strip()
                            if not os.path.isabs(path):
                                path = os.path.join(here, path)
                            return os.path.normpath(path)
            except OSError:
                return None
            return None
        up = os.path.dirname(here)
        if up == here:
            return None
        here = up
    return None


# Names git leaves in its directory while an operation is unfinished: the
# next commit is a person's.
BUSY_MARKERS = (
    ("rebase-merge", "a rebase is in progress"),
    ("rebase-apply", "a rebase or an `am` is in progress"),
    ("MERGE_HEAD", "a merge is in progress"),
    ("CHERRY_PICK_HEAD", "a cherry-pick is in progress"),
    ("REVERT_HEAD", "a revert is in progress"),
    ("BISECT_LOG", "a bisect is in progress"),
)


def busy_reason(root):
    """Why this repository must be left alone, or None: on a branch with no
    operation outstanding, the only state for an unattended commit."""
    gd = git_dir(root)
    if not gd:
        return None                      # not a repository; nothing to protect
    for name, why in BUSY_MARKERS:
        if os.path.exists(os.path.join(gd, name)):
            return why
    # A detached HEAD: a commit there would be reachable from nothing.
    try:
        with open(os.path.join(gd, "HEAD"), "r", encoding="utf-8") as fh:
            head = fh.read().strip()
    except OSError:
        return None
    if head and not head.startswith("ref:"):
        return "HEAD is detached, so a commit here would be reachable from nothing"
    return None


# ---------------------------------------------------------------------------
# The lock a killed git leaves behind.
#
# A git killed mid-operation leaves an empty `index.lock` that closes every
# route to a commit, and its own advice cannot be followed from an iPad. A
# lock is either held by a running git (seconds) or rubbish; telling those
# apart is what follows.
# ---------------------------------------------------------------------------

# Above every git timeout in this tool, so an older unheld lock is rubbish.
LOCK_STALE_AFTER = 300.0

# Grace for the instant between creating a lock and opening it.
LOCK_GRACE = 5.0


def index_lock(root):
    """This repository's `.git/index.lock`, or None if there is not one."""
    gd = git_dir(root)
    if not gd:
        return None
    path = os.path.join(gd, "index.lock")
    return path if os.path.exists(path) else None


def _lock_holder(path):
    """Whether a live process holds this file open: True, False, or None when
    it cannot be asked (the caller then uses age). Scans `/proc/<pid>/fd` on
    Linux, `lsof` on a Mac."""
    if not os.path.isdir("/proc"):
        return _lsof_holder(path)
    try:
        want = os.path.realpath(path)
    except OSError:
        return None
    seen_any = False
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fd_dir = os.path.join("/proc", pid, "fd")
        try:
            names = os.listdir(fd_dir)
        except OSError:
            continue                     # not ours, or gone between two calls
        seen_any = True
        for name in names:
            try:
                target = os.readlink(os.path.join(fd_dir, name))
            except OSError:
                continue
            if target == want or target == path:
                return True
    return False if seen_any else None


def _lsof_holder(path):
    """`_lock_holder` where there is no `/proc`: ask `lsof`, or None."""
    import shutil
    import subprocess
    exe = shutil.which("lsof") or ("/usr/sbin/lsof" if os.path.exists("/usr/sbin/lsof") else None)
    if not exe:
        return None
    try:
        p = subprocess.run([exe, "-t", "--", path], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    # Exit 1 with nothing printed is lsof's "nobody has it open".
    return bool(p.stdout.strip())


def lock_reason(root):
    """What `.git/index.lock` means here, as (verdict, sentence): `None` (no
    lock), `"held"` (git is running now) or `"stale"` (clear it). The sentence
    is for a person reading a board."""
    path = index_lock(root)
    if not path:
        return None, None
    try:
        age = max(0.0, time.time() - os.path.getmtime(path))
    except OSError:
        return None, None                # went away while we were looking
    holder = _lock_holder(path)
    if holder is True:
        return "held", ("a git command is running in this repository right now, "
                        "so the index is locked. Nothing has been lost -- press "
                        "save again in a moment.")
    if holder is False and age > LOCK_GRACE:
        return "stale", ("cleared a lock file a git command left behind when it "
                         "was interrupted %d seconds ago" % int(age))
    if holder is None and age > LOCK_STALE_AFTER:
        # Without `/proc`, age is the evidence; the threshold exceeds every
        # timeout here.
        return "stale", ("cleared a lock file left behind %d minutes ago by a git "
                         "command that did not finish" % int(age / 60))
    if holder is None:
        return "held", ("the git index is locked in this repository, and this "
                        "machine cannot tell whether the command holding it is "
                        "still running. Nothing has been lost -- press save "
                        "again in a few minutes and it will be cleared.")
    return "held", ("a git command is running in this repository right now, so "
                    "the index is locked. Nothing has been lost -- press save "
                    "again in a moment.")


def clear_stale_lock(root):
    """Remove a lock this module judged rubbish, and say what was done, or
    None. A running git is never pulled out from under itself."""
    verdict, sentence = lock_reason(root)
    if verdict != "stale":
        return None
    path = index_lock(root)
    if not path:
        return None
    try:
        os.remove(path)
    except OSError:
        return None
    return sentence
