"""Where this machine keeps what it knows about itself.

Everything reads its state through these names, so a test can move the lot by
assigning to them; state a test can reach is state a test will corrupt.
"""

import os


HOME = os.path.expanduser("~")

# The tool itself, derived from this file so either spelling of the home
# directory works.
TOOL = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
WEB = os.path.join(TOOL, "web")

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config")),
    "tutor-board")
CONFIG = os.path.join(CONFIG_DIR, "config.json")
# Provider credentials, outside the public tree; only `keys.py` opens it.
KEYS = os.path.join(CONFIG_DIR, "keys.env")

# The one port the board listens on, unless config.json says `port`.
PORT = 8778


def config():
    """config.json as a dict; {} when it is missing or unreadable."""
    try:
        import json
        with open(CONFIG, "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def port():
    """config.json's `port`, else PORT."""
    try:
        said = int(config().get("port") or PORT)
    except (TypeError, ValueError):
        return PORT
    return said if 0 < said < 65536 else PORT


# Deleted things, one `<stamp>/` per delete, kept 30 days.
# `TUTORBOARD_TRASH` moves it for tests.
TRASH = (os.environ.get("TUTORBOARD_TRASH")
         or os.path.join(HOME, ".local", "share", "tutor-board", "trash"))

# The shared PDF page cache (`course/paper.py`), outside the tree so a PHI
# page can never be committed. `TUTORBOARD_PAGES` moves it.
PAGES = (os.environ.get("TUTORBOARD_PAGES")
         or os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"),
                         "tutor-board", "pages"))

# What the hub stats each second in a session directory. A directory counts
# its entries too, since rewriting a file in place leaves its mtime alone.
SESSION_WATCHED = ("cards", "turns.jsonl", "inbox/messages.jsonl", "state.json",
                   "session.json", "agent.json", "annotations", "slate", "push.json",
                   "export.json", "hw.json")


def same_dir(a, b):
    """Are these two paths the same directory, however spelled? A home
    directory can be reachable by two mount paths."""
    if not a or not b:
        return False
    try:
        return os.path.realpath(a) == os.path.realpath(b)
    except OSError:
        return os.path.abspath(a) == os.path.abspath(b)


# What this machine has worked out about itself (pinned name, known-good exit
# node, usage limits): nobody's to edit. `BOARD_STATE_DIR` moves it for tests.
STATE_DIR = os.environ.get("BOARD_STATE_DIR") or \
    os.path.join(HOME, ".local", "state", "tutor-board")


# ---------------------------------------------------------------------------
# What lives OUTSIDE the repository, on purpose
# ---------------------------------------------------------------------------
# Directories outside the tree on purpose, because they cannot go in a public
# repository: PHI (identifiable session audio) and ARTIFACTS (large job
# output). Never symlinked in, since a tracked symlink maps the way to PHI.
# Named here so "which directories may a path from a file reach" has one
# answer.
PHI = os.environ.get("TUTORBOARD_PHI") or os.path.join(HOME, "phi")
ARTIFACTS = os.environ.get("TUTORBOARD_ARTIFACTS") or os.path.join(HOME, "artifacts")


def outside_tree():
    """The directories a path out of a file may reach that are not the repository."""
    return (os.path.realpath(PHI), os.path.realpath(ARTIFACTS))


def within(target, *roots):
    """Is `target` inside one of `roots`? By realpath; a root counts as
    itself. The one containment test every path-from-a-file check uses."""
    try:
        target = os.path.realpath(target)
    except OSError:
        target = os.path.abspath(target)
    for r in roots:
        if not r:
            continue
        try:
            r = os.path.realpath(r)
        except OSError:
            r = os.path.abspath(r)
        if target == r or target.startswith(r + os.sep):
            return True
    return False


# A `results/` path missing locally is read from `exports/results/`, so one
# path works on both machines. Nothing else falls back.
EXPORTS = "exports"


def exported(rel):
    """The `exports/` twin of a workspace-relative `results/` path, or ""."""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    return EXPORTS + "/" + rel if rel.startswith("results/") else ""


def present(root, rel):
    """Where `rel` really is in this workspace: itself or its exported copy,
    absolute; "" where neither exists or either would leave the workspace."""
    if not rel:
        return ""
    for cand in (rel, exported(rel)):
        if not cand:
            continue
        target = os.path.join(root, cand)
        if within(target, root) and os.path.exists(target):
            return target
    return ""
