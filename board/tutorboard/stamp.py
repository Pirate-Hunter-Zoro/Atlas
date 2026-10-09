"""Which code a long-lived process is running, and which code the tree has.

The board server reads its code once, when it starts. What tells a stale
process from a fresh one is a stamp: a short hash of the git trees the process
loads, read when it starts (`LOADED`) and compared against what HEAD holds now.

THE STAMP COVERS WHAT A PROCESS LOADS AND NOTHING ELSE: `serve.py` and
`tutorboard/`. HEAD moves every time a course
saves its homework, and a bounce per answer is a lesson nobody can finish.
`web/` is out because the shell is served from disk and `sw.js`'s VERSION
already moves it; `bin/board` is out because it is a fresh CLI on every call.

`moved()` is the server's freshness check: the stamp at HEAD differs from
`LOADED`, nothing under board/ is uncommitted, no rebase or detached HEAD is
under way, and the new tree imports. The server then exits 0 once no turn
runs, and launchd starts it on the new code (`server/app.py`).

A PROCESS READS ITS STAMP BEFORE IT IMPORTS `tutorboard`. Read after, HEAD can
move between the two and the stamp then names newer code than the process is
running, which is a stale process nothing will ever bounce. Read first, the
worst case is one bounce too many.

A leaf module: os, subprocess, hashlib, time and nothing of this package, so it
can be imported before the package it stamps.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import time

TOOL = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STAMPED = ("serve.py", "tutorboard")

# `/health?code=1` asks too, so a burst of it does not become a burst of git.
CACHE_FOR = 10.0
_cache = {}

# What this process loaded, set once by `mark_loaded` before the import.
LOADED = None


def tree(tool=TOOL, cached=True):
    """Twelve hex characters naming the stamped trees at HEAD, or None.

    A stamped path HEAD does not have is left out. `cached` False asks git
    now."""
    now = time.time()
    hit = _cache.get(tool)
    if cached and hit and now - hit[0] < CACHE_FOR:
        return hit[1]
    try:
        p = subprocess.run(
            ["git", "-C", tool, "ls-tree", "HEAD", "--"] + list(STAMPED),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        lines = p.stdout.decode("utf-8", "replace").strip()
        if p.returncode != 0 or not lines:
            got = None
        else:
            got = hashlib.sha1(lines.encode("utf-8")).hexdigest()[:12]
    except (OSError, subprocess.SubprocessError):
        got = None
    _cache[tool] = (now, got)
    return got


def forget():
    """Drop the cache, for a caller that has just moved HEAD itself."""
    _cache.clear()


def mark_loaded():
    """Remember the tree this process is about to import. Once per process."""
    global LOADED
    if LOADED is None:
        LOADED = tree()
    return LOADED


def blocked(tool=TOOL):
    """Why the tree must not be deployed from right now, or None.

    A rebase walks HEAD through several commits and a detached HEAD is nobody's
    idea of what is shipped, so a beat in either state waits for the next one.
    `worktree.busy_reason` answers both.
    """
    from . import worktree                      # lazily: this module is a leaf
    return worktree.busy_reason(tool)


def imports(tool=TOOL, timeout=30):
    """Does the tree at `tool` compile `serve.py` and import the server and
    the runner?

    Returns (ok, last line). Run once per new stamp before the server gives
    way to it, because a tree that does not import would otherwise leave
    launchd restarting a server that dies at once. Writes nothing into the tree.

    `ok` is None when the check could not run -- a timeout or an OSError, which
    is a slow filer rather than a broken tree -- so a caller can try again
    instead of remembering a good tree as a bad one.
    """
    with tempfile.TemporaryDirectory(prefix="tutor-stamp-") as scratch:
        sources = [s for s in ("serve.py",)
                   if os.path.isfile(os.path.join(tool, s))]
        code = ("import os, py_compile, sys; "
                "[py_compile.compile(s, cfile=os.path.join(%r, '%%d.pyc' %% n), "
                "doraise=True) for n, s in enumerate(%r)]; "
                "sys.path.insert(0, '.'); import tutorboard.server.app, "
                "tutorboard.runner.service" % (scratch, sources))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            p = subprocess.run([sys.executable, "-B", "-c", code], cwd=tool,
                               env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            return None, str(exc)
    said = [l.strip() for l in p.stdout.decode("utf-8", "replace").splitlines()
            if l.strip()]
    return p.returncode == 0, (said[-1] if said else "")


def dirty(tool=TOOL):
    """Is anything under `tool` uncommitted -- modified, staged or untracked?
    True when git cannot say."""
    try:
        p = subprocess.run(["git", "-C", tool, "status", "--porcelain", "--", "."],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return True
    return p.returncode != 0 or bool(p.stdout.strip())


# Each new stamp's import check, once: {stamp: ok}.
_imported = {}


def moved(tool=TOOL):
    """Why this process should give way to the tree's committed code, or None.

    None while the stamp at HEAD is the one loaded, while anything under
    board/ is uncommitted (an edit in progress is nobody's release), during a
    rebase or on a detached HEAD, and when the new tree does not import. A
    process whose stamp could not be read at start takes the first one it
    reads as its own.
    """
    global LOADED
    now = tree(tool, cached=False)
    if now is None:
        return None
    if LOADED is None:
        LOADED = now
        return None
    if now == LOADED or dirty(tool) or blocked(tool):
        return None
    if now not in _imported:
        ok, _line = imports(tool)
        if ok is None:
            return None
        _imported[now] = ok
    if not _imported[now]:
        return None
    return "committed board code moved from %s to %s" % (LOADED, now)
