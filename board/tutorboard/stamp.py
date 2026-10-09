"""Which code a long-lived process is running, and which code the tree has.

A stamp is a short hash of the git trees a process loads (`serve.py` and
`tutorboard/`), read at start (`LOADED`) and compared with HEAD. `web/` is
out (`sw.js` VERSION moves the shell) and `bin/board` is out (a fresh CLI
every call). `moved()` is the server's freshness check; the server then exits
0 once no turn runs and launchd restarts it on the new code.

The constraint: a process reads its stamp before importing `tutorboard`, so
the stamp never names newer code than it runs; this module is therefore a
leaf (os, subprocess, hashlib, time only).
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
    """Twelve hex characters naming the stamped trees at HEAD, or None;
    `cached` False asks git now."""
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
    """Why the tree must not be deployed now (a rebase or detached HEAD, per
    `worktree.busy_reason`), or None."""
    from . import worktree                      # lazily: this module is a leaf
    return worktree.busy_reason(tool)


def imports(tool=TOOL, timeout=30):
    """Does the tree at `tool` compile `serve.py` and import the server and
    runner? `(ok, last line)`, run once per new stamp so launchd never
    restarts into a server that dies at once. `ok` None means the check could
    not run (timeout, OSError): try again rather than mark the tree bad.
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
    """Why this process should give way to the tree's committed code, or None:
    None while the stamp is unchanged, board/ has uncommitted edits, a rebase
    or detached HEAD is under way, or the new tree does not import.
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
