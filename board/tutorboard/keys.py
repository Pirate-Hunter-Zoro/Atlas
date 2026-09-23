"""The credentials a turn is handed, and the one file they live in.

    ~/.config/tutor-board/keys.env

`NAME=value`, one a line, `#` for a comment, no shell and no expansion. Beside
the `config.json` the launcher already reads, and OUTSIDE the tree for the same
reason `cost.jsonl` is machine-local: the account that pays for it belongs to
this machine, and this repository is public.

A recipe names the key it needs with `needs_key` and spends it through `env`,
where `{NAME}` is substituted from here. Nothing else reads this file, and
nothing ever puts a value from it on a command line -- argv is in `ps` output,
which is the whole reason `ai-config/policy/credentials.txt` exists.

WHAT IS CHECKED ABOUT THE FILE'S MODE, AND WHAT DELIBERATELY IS NOT. A
world-readable key file is refused: every account on the machine could read it
and there is nothing to argue about. A GROUP-readable one is not, and the
obvious rule that refuses it would be wrong here. Measured on this machine: the
home directory is NFSv4 and the server enforces the mode through its own ACLs,
so `chmod 600` reports success and `stat` comes back `770`, owner
`mferguson:domain users`; `setfacl` is ignored, there is no `nfs4_setfacl` and
there is no root. A refusal on the group bit would refuse every file in this
home, `~/.claude/.credentials.json` included, which has sat at exactly those
permissions for as long as this board has run. So the key is as protected as
everything else on this filer, tightening it is a storage request rather than a
line of Python, and this module says it once and carries on.

Cached, with the reasoning `assistants.TTL` carries: the answer changes only
when somebody edits a file, and a `--agents --json` four times a second must
not become a stat and a parse four times a second either.
"""

import os
import stat
import time

from . import paths


TTL = 900.0
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
    # Other-readable, or other-writable. The group bit is not asked about; see
    # the module docstring for the measurement that settles it.
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
                # No shell, so a quoted value is a value with quotes on it
                # unless they wrap the whole of it -- which is what somebody
                # copying a key out of a provider's page writes.
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
    """Why the store is empty, in one sentence, or None if it is not.

    For a message on the glass. A person told *the key is missing* can act; a
    person told *the turn failed* cannot.
    """
    _all()
    return _CACHE["why"]


def forget():
    """Drop the cache. For a test, and for a key just put in the file."""
    _CACHE.update({"at": 0.0, "was": None, "path": None, "why": None})


# ---------------------------------------------------------------------------
# `{NAME}` in a recipe's `env`
# ---------------------------------------------------------------------------
def fill(value):
    """Substitute `{NAME}` from the store. None where a named key is absent.

    None rather than the literal braces, and that is the whole point: a
    `{DEEPSEEK_API_KEY}` handed to a provider verbatim is an authentication
    failure in a log file, which is the least actionable thing the person
    holding the iPad could be given. Absent is a fact the chooser can draw.
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
        got = get(name)
        if got is None:
            return None
        out.append(text[i:a])
        out.append(got)
        i = b + 1


def unkeyed(spec):
    """The key this recipe needs and this machine has not got, or None.

    Asked of the recipe rather than of the turn, so the answer can be drawn on
    a button before it is tapped rather than found in a log after.
    """
    wanted = (spec or {}).get("needs_key")
    if not wanted:
        return None
    return None if have(wanted) else str(wanted)
