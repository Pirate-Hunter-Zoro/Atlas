"""fenced.py -- the directories nothing in this tool may look inside, by name.

`projects/PSYCH-ASR/phi/` is session content (identifiable therapy audio and
transcripts), fenced from assistants by `ai-config/policy/phi.py` by
directory name. Every module that walks a workspace and hands what it found
to something else reads its fence from this one list, because two lists
drift. `refused` asks of a path without touching the filesystem; `holds`
asks of a workspace by listing it.

The constraint: matched on the directory name at any depth, never by
prefix, depth or size floor, because a document that reaches a tutor has
been read and that is one-way.
"""

import os
import time


# Never these, whatever else changes: `phi` is session content; `data`,
# `raw` and `audio` feed it; `stage1`/`stage2` hold both; `inbox` is where
# content arrives unsorted. `test/showing.py` fails if one stops being refused.
NEVER = ("phi", "data", "inbox", "stage1", "stage2", "raw", "audio")

# Where a workspace keeps output worth showing. An allowlist, and it must
# stay one: a blocklist would hand over whatever a workspace grows next.
RESULT_DIRS = ("results", "figures", "tables", "artifacts", "analysis")


def in_fence(rel):
    """Is any lower-cased component of this path a name in `NEVER`?
    Backslashes are normalised first, since a path from a file may use them."""
    parts = [x.lower() for x in str(rel or "").replace("\\", "/").split("/")]
    return any(x in NEVER for x in parts)


# The same question under the name its older callers use.
refused = in_fence


# ---------------------------------------------------------------------------
# Does this WORKSPACE hold a fence, and is that sayable before a tap
# ---------------------------------------------------------------------------
# Whether a workspace holds a fence, asked before anything is chosen (e.g.
# a chooser labelling it). One level deep by rule: a fence is a top-level
# directory of the workspace. Cached, because the hub asks on every build.
SEEN_TTL = 60.0
_SEEN = {}


def holds(root):
    """The fenced directories this workspace has, as a sorted tuple; empty
    for none, and for a root that cannot be listed."""
    root = str(root or "")
    if not root:
        return ()
    now = time.time()
    hit = _SEEN.get(root)
    if hit and now - hit[0] < SEEN_TTL:
        return hit[1]
    try:
        found = tuple(sorted(
            n for n in os.listdir(root)
            if n.lower() in NEVER and os.path.isdir(os.path.join(root, n))))
    except OSError:
        found = ()
    _SEEN[root] = (now, found)
    return found


def forget():
    """Drop the cache. For a test, and for a walk that has just made one."""
    _SEEN.clear()


# ---------------------------------------------------------------------------
# Is this PATH inside its workspace's fence
# ---------------------------------------------------------------------------
# A path a command was pointed at is checked against its workspace's
# top-level fence, because the board's own `live/inbox/uploads/` is not
# PSYCH-ASR's `inbox`. `phi` keeps its any-depth refusal unconditionally, and
# a path outside the workspace falls back to `refused`.
ALWAYS = ("phi",)


def refused_in(root, path):
    """Is this path inside `root`'s fence? The reason (naming the directory),
    or None."""
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    parts = [x.lower() for x in path.replace("\\", "/").split("/")]
    hit = next((x for x in parts if x in ALWAYS), None)
    if hit:
        return hit
    root = os.path.abspath(os.path.expanduser(str(root or "")))
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        rel = ".."
    if rel.startswith(".."):
        # Not in this workspace: the any-depth rule answers.
        return next((x for x in parts if x in NEVER), None)
    top = rel.replace("\\", "/").split("/")[0].lower()
    return top if top in NEVER else None
