"""Which code a long-lived process is running, and which code the tree holds.

A board and a tutor daemon read their code once, when they start. The checkout
is on the shared filesystem, so a ship puts the new files in front of every node
at once and no node ever sees a pull move HEAD. What tells a stale process from
a fresh one is therefore a stamp: a short hash of the git trees the processes
load, written into their records when they start and compared on every watch
beat against what the tree holds now.

THE STAMP COVERS WHAT A PROCESS LOADS AND NOTHING ELSE: `bin/tutor`, `serve.py`
and `tutorboard/`. HEAD moves every time a course saves its homework, and a
bounce per answer is a lesson nobody can finish. `web/` is out because the shell
is served from disk and `sw.js`'s VERSION already moves it; `bin/board` is out
because it is a fresh CLI on every call.

A PROCESS READS ITS STAMP BEFORE IT IMPORTS `tutorboard`. Read after, HEAD can
move between the two and the record then names newer code than the process is
running, which is a stale process nothing will ever bounce. Read first, the
worst case is one bounce too many.

A leaf module: os, subprocess, hashlib, time and nothing of this package, so it
can be imported before the package it stamps.
"""

import contextlib
import hashlib
import os
import subprocess
import sys
import tempfile
import time

TOOL = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STAMPED = ("bin/tutor", "serve.py", "tutorboard")

# `/health?code=1` asks too, so a burst of it does not become a burst of git.
CACHE_FOR = 10.0
_cache = {}

# What this process loaded, set once by `mark_loaded` before the import.
LOADED = None


def tree(tool=TOOL):
    """Twelve hex characters naming the stamped trees at HEAD, or None."""
    now = time.time()
    hit = _cache.get(tool)
    if hit and now - hit[0] < CACHE_FOR:
        return hit[1]
    try:
        p = subprocess.run(
            ["git", "-C", tool, "rev-parse"] + ["HEAD:./" + s for s in STAMPED],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        hashes = p.stdout.decode("ascii", "replace").split()
        if p.returncode != 0 or len(hashes) != len(STAMPED):
            got = None
        else:
            lines = "".join("%s %s\n" % (s, h) for s, h in zip(STAMPED, hashes))
            got = hashlib.sha1(lines.encode("ascii")).hexdigest()[:12]
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
    """Does the tree at `tool` compile `bin/tutor` and import the server and
    the tutor daemon's modules?

    Returns (ok, last line). Run once per new stamp before anything is bounced,
    because a ship that does not import would otherwise take down every board on
    the serving node. Writes nothing into the tree.

    `ok` is None when the check could not run -- a timeout or an OSError, which
    is a slow filer rather than a broken tree -- so a caller can try again
    instead of remembering a good tree as a bad one.
    """
    with tempfile.TemporaryDirectory(prefix="tutor-stamp-") as scratch:
        code = ("import py_compile, sys; "
                "py_compile.compile('bin/tutor', cfile=%r, doraise=True); "
                "sys.path.insert(0, '.'); import tutorboard.server.app, "
                "tutorboard.runner.loop, tutorboard.runner.watch, "
                "tutorboard.agents.doctor"
                % os.path.join(scratch, "tutor.pyc"))
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


LOCK = "/tmp/tutor-restart-%d.lock" % os.getuid()


@contextlib.contextmanager
def restart_lock(wait=True, path=None):
    """One restart of this node's boards at a time. Yields whether it is held.

    Node-local on purpose: `/tmp` is this machine's, and the boards a restart
    stops are this machine's too. A lesson save, a ship and a watch beat can all
    reach for the same board together, and two of them stopping and starting it
    at once is a board on a fallback port.
    """
    import fcntl
    fh = open(path or LOCK, "a")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    finally:
        fh.close()
