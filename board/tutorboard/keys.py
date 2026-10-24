"""The credentials a turn is handed, and the one file they live in.

    ~/.config/tutor-board/keys.env

`NAME=value`, one a line, `#` comments, no shell and no expansion; outside
the tree because this repository is public. A recipe names its key with
`needs_key` and spends it through `env` (`{NAME}`); nothing puts a value on
a command line, because argv is visible in `ps`. A world-readable file is
refused; a group-readable one is not, because this home's NFSv4 server
reports every file as mode 770 whatever `chmod` says. Cached, since
`--agents --json` is polled.
"""

import os
import re
import stat
import time

from . import paths


TTL = 900.0
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CACHE = {"at": 0.0, "was": None, "path": None, "why": None}


def store():
    """Where the keys live. Read through `paths` so a test can move it."""
    return paths.KEYS


def _read(path):
    """`(mapping, why-it-is-empty)`. Never raises: a lesson does not stop here."""
    try:
        st = os.stat(path)
    except OSError:
        return {}, "there is no %s" % path
    # Other-readable or other-writable only; see the module docstring.
    if st.st_mode & (stat.S_IROTH | stat.S_IWOTH):
        return {}, ("%s is readable by every account on this machine "
                    "(mode %o); `chmod o-rwx` it and the keys in it will be "
                    "read again" % (path, st.st_mode & 0o777))
    got = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                name = name.strip()
                # Quotes wrapping the whole value are stripped; others are kept.
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]
                if name:
                    got[name] = value
    except OSError as exc:
        return {}, "%s could not be read: %s" % (path, exc)
    return got, None


def _all():
    path = store()
    now = time.time()
    if (_CACHE["was"] is not None and _CACHE["path"] == path
            and now - _CACHE["at"] <= TTL):
        return _CACHE["was"]
    got, why = _read(path)
    _CACHE.update({"at": now, "was": got, "path": path, "why": why})
    return got


def have(name):
    """Is there a key of this name, with something in it?"""
    return bool(str(name or "") and _all().get(str(name), ""))


def get(name):
    """The key, or None. Never the empty string, which reads as a key in an
    `if` and is not one."""
    return _all().get(str(name or "")) or None


def why_not():
    """Why the store is empty, in one sentence for the glass, or None."""
    _all()
    return _CACHE["why"]


def forget():
    """Drop the cache. For a test, and for a key just put in the file."""
    _CACHE.update({"at": 0.0, "was": None, "path": None, "why": None})


# ---------------------------------------------------------------------------
# `{NAME}` in a recipe's `env`
# ---------------------------------------------------------------------------
def fill(value):
    """Substitute `{NAME}` from the store. None where a named key is absent,
    never the literal braces (an opaque auth failure). Only a bare `{NAME}`
    is a key: `{env:NAME}` and other braces pass through untouched.
    """
    text = str(value)
    out = []
    i = 0
    while True:
        a = text.find("{", i)
        if a < 0:
            out.append(text[i:])
            return "".join(out)
        b = text.find("}", a + 1)
        if b < 0:
            out.append(text[i:])
            return "".join(out)
        name = text[a + 1:b]
        if not _NAME.match(name):
            out.append(text[i:a + 1])
            i = a + 1
            continue
        got = get(name)
        if got is None:
            return None
        out.append(text[i:a])
        out.append(got)
        i = b + 1


def unkeyed(spec):
    """The key this recipe needs and this machine lacks, or None: drawable on
    a button before it is tapped."""
    wanted = (spec or {}).get("needs_key")
    if not wanted:
        return None
    return None if have(wanted) else str(wanted)
