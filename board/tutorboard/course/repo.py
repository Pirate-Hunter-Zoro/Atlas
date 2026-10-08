"""A workspace on disk, its session directory, and the paths inside it.

Everything the board reads or writes during a lesson hangs off one of these,
so a directory layout that changes changes here and nowhere else. The session
directory is `<root>/live` unless a caller names another one; `session_dir`
and `session_path` are the same answer for code that holds only a root.

A session directory holding `session.json` is a stored session
(`tutorboard/sessions.py`): its state is session.json, its uploads sit at its
top, and its root is the bound subject's, or the Atlas root while unbound.

Runs on the cluster's python3 (3.7) through jobs.py: no walrus, no `match`.
"""

import json
import os
import re


# A CLI process runs on one session, bound by `resolve`. Code that holds only
# the workspace root then reaches the same directory the Repo object does.
_BOUND = {}


# The one place that knows a workspace keeps its session in `live/`.
def session_dir(root):
    """The session directory of the workspace at `root`: the one `resolve`
    bound for it in this process, else `<root>/live`."""
    if _BOUND:
        said = _BOUND.get(os.path.realpath(root))
        if said:
            return said
    return os.path.join(root, "live")


def session_path(root, *parts):
    """A path inside the session directory of the workspace at `root`."""
    return os.path.join(session_dir(root), *parts)


SESSION_JSON = "session.json"

# The keys every session.json carries; `set_state` writes None into these as
# null rather than dropping them.
SESSION_KEYS = ("id", "title", "subject", "mode", "opened", "ended", "writeup",
                "seen", "code", "view")


def is_stored(session):
    """Is `session` a stored session, `sessions/<id>/` with its session.json?"""
    return os.path.isfile(os.path.join(session, SESSION_JSON))


def session_state(root):
    """The state of the session bound to `root`: what `Repo.state()` says,
    and always a dict."""
    said = Repo(root, create=False).state()
    return said if isinstance(said, dict) else {}


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def _write_json(path, data):
    """Whole or not at all: a reader never sees half a file."""
    tmp = "%s.tmp-%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def _is_set_source(rel):
    """Is `rel`, relative to a subject root, where a homework set lives?"""
    from fnmatch import fnmatch
    from . import homework                                   # local: light
    rel = rel.replace(os.sep, "/")
    return any(fnmatch(rel, pat.replace(os.sep, "/")) for pat in homework.LAYOUTS)


# ---------------------------------------------------------------------------
# which workspace a command runs in
# ---------------------------------------------------------------------------
class NoWorkspace(SystemExit):
    """Raised instead of answering with the Atlas root: a CLI that lets it
    propagate exits 1 with the message, having created nothing."""


# This checkout's root: the parent of `board/`, from this file's own path.
ATLAS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__)))))


def is_atlas_root(d):
    """Is `d` the root of an Atlas checkout, this one or another?"""
    real = os.path.realpath(d)
    return real == ATLAS or os.path.isfile(os.path.join(real, "board", "bin", "board"))


def _marked(d):
    return (os.path.exists(os.path.join(d, ".git"))
            or os.path.isfile(os.path.join(d, "tutorboard.json"))
            or os.path.isfile(os.path.join(d, "AI_INSTRUCTIONS.md")))


def nearest(start=None):
    """The nearest ancestor of `start` (default: the cwd) that is a workspace,
    or None. The Atlas root is never one: the walk stops there."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        if is_atlas_root(d):
            return None
        if _marked(d):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def find_repo(start=None):
    """The workspace a command run in `start` (default: the cwd) is about.

    The nearest ancestor holding .git, tutorboard.json or AI_INSTRUCTIONS.md;
    with none, `start` itself. Never the Atlas root: from there, or from
    anywhere whose walk reaches it first, NoWorkspace is raised.
    """
    start = os.path.abspath(start or os.getcwd())
    found = nearest(start)
    if found:
        return found
    if is_atlas_root(start) or any(is_atlas_root(a) for a in _ancestors(start)):
        raise NoWorkspace(
            "%s is not a workspace: run this inside a course or project, pass "
            "--repo, or set TUTORBOARD_SESSION" % start)
    return start


def _ancestors(d):
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return
        yield parent
        d = parent


def resolve(root=None, create=True):
    """The Repo a CLI command works on. One resolver for both CLIs.

    `TUTORBOARD_SESSION` names the session directory when set; the workspace
    is then `root`, else the nearest one above the cwd, else the Atlas root.
    Without it, the workspace is `root` or `find_repo()`, and the session is
    its `live/`. With it, `session_dir` of that workspace answers the session
    for the rest of the process.
    """
    said = os.environ.get("TUTORBOARD_SESSION")
    if said:
        session = os.path.abspath(os.path.expanduser(said))
        if root:
            where = os.path.abspath(root)
        elif is_stored(session):
            where = stored_root(session)
        else:
            where = nearest() or ATLAS
        _BOUND.clear()
        _BOUND[os.path.realpath(where)] = session
        return Repo(where, session=session, create=create)
    return Repo(find_repo(root), create=create)


def stored_root(session):
    """The root a stored session works in: its bound subject's directory,
    or the Atlas root that holds `sessions/` while it is unbound."""
    atlas = os.path.dirname(os.path.dirname(os.path.abspath(session)))
    subject = _read_json(os.path.join(session, SESSION_JSON)).get("subject")
    if subject:
        where = os.path.abspath(os.path.join(atlas, str(subject)))
        inside = os.path.relpath(os.path.realpath(where), os.path.realpath(atlas))
        if os.path.isdir(where) and not inside.startswith(".."):
            return where
    return atlas


# ---------------------------------------------------------------------------
# repository paths
# ---------------------------------------------------------------------------
class Repo:
    """`create` makes every directory the board writes into; False makes none,
    and `ensure_dirs(cli=True)` makes the set a CLI command writes into."""

    def __init__(self, root, session=None, create=True):
        self.root = os.path.abspath(root)
        self.session = os.path.abspath(session) if session else session_dir(self.root)
        # A stored session (`sessions/<id>/`), as against a workspace's live/.
        self.stored = is_stored(self.session)
        # The Atlas root holding `sessions/`, for a stored session.
        self.atlas = (os.path.dirname(os.path.dirname(self.session))
                      if self.stored else None)
        # The name every caller used before the session could live elsewhere.
        self.live = self.session
        self.cards = os.path.join(self.live, "cards")
        self.inbox = os.path.join(self.live, "inbox")
        self.uploads = (os.path.join(self.live, "uploads") if self.stored
                        else os.path.join(self.inbox, "uploads"))
        self.tikz = os.path.join(self.live, "tikzcache")
        self.archive = os.path.join(self.live, "archive")
        self.slate = os.path.join(self.live, "slate")
        # What the student actually handed in, frozen at the moment they sent
        # it. The slate is a working surface and gets written over; a transcript
        # cannot be built out of a surface that changes underneath it.
        self.answers = os.path.join(self.live, "answers")
        # Marks written on top of the tutor's own cards. Kept per card, because
        # a card is the thing an annotation is about and the only anchor that
        # survives the lesson reflowing at a different type size.
        self.notes = os.path.join(self.live, "annotations")
        # Typed answers, drafted per question the way the slate drafts per page,
        # so switching from typing to writing and back does not lose the sentence.
        self.text = os.path.join(self.live, "text")
        if create:
            self.ensure_dirs()

    # Every directory the board writes into, re-asserted. Not only at startup:
    # a board is a long-lived process and these directories are inside a git
    # repository that something else pulls. git removes a directory when it
    # removes the last tracked file in it, and `live/text/` holds one file per
    # question in progress -- so the transcript beat committing "the student
    # sent it, the draft is gone" on the other machine, pulled here, takes the
    # directory with it. The board went on holding the path it made when it
    # started, and every keystroke in the answer box then arrived as a 500 with
    # a FileNotFoundError behind it. On the iPad that is a typed answer that
    # will not save, with nothing on screen saying why.
    #
    # It is every one of them, not just `text`: `answers`, `annotations`,
    # `slate`, `inbox/uploads` and `cards` are all tracked, all routinely go
    # empty, and all are written to by a request that arrives whenever the
    # student happens to act.
    #
    # `cli=True` leaves out `annotations` and `text`: a board creates them when
    # it starts, and a CLI command that only ever reads them should not leave
    # one behind in a workspace nobody has opened a board in.
    def ensure_dirs(self, cli=False):
        dirs = [self.live, self.cards, self.inbox, self.uploads, self.tikz,
                self.slate, self.answers]
        # A stored session has no archive: only End ends it.
        if not self.stored:
            dirs.append(self.archive)
        if not cli:
            dirs += [self.notes, self.text]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def path(self, *parts):
        return os.path.join(self.live, *parts)

    def info(self):
        """The running board's record, `.board.json`, or None."""
        try:
            with open(self.path(".board.json"), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def set_state(self, **kw):
        """Merge `kw` into the state file; a None value clears its key.

        In a stored session, `hw` is written as `writeup` (the set's source,
        relative to the Atlas root), and the keys session.json always carries
        are cleared to null rather than dropped.
        """
        if self.stored:
            return self._set_session(kw)
        s = self.state()
        for k, v in kw.items():
            if v is None:
                s.pop(k, None)
            else:
                s[k] = v
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump(s, fh, indent=2)
        return s

    def _set_session(self, kw):
        s = _read_json(self.state_path)
        for k, v in kw.items():
            if k == "hw":
                k, v = "writeup", self._writeup_for(v)
            if v is None and k not in SESSION_KEYS:
                s.pop(k, None)
            else:
                s[k] = v
        _write_json(self.state_path, s)
        return self.state()

    def _writeup_for(self, hw):
        """A legacy `hw` value -- a set's path under the root, or its name --
        as session.json's `writeup`: that source relative to the Atlas root."""
        if not hw:
            return None
        hw = str(hw)
        if not hw.endswith(".tex"):
            from . import homework                           # local: light
            for one in homework.sets(self.root):
                if one["name"] == hw:
                    hw = one["rel"]
                    break
        full = os.path.abspath(os.path.join(self.root, hw))
        return os.path.relpath(full, self.atlas).replace(os.sep, "/")

    def card_names(self):
        return sorted(n for n in os.listdir(self.cards) if re.match(r"^\d{4}[-_.]", n))

    def next_index(self):
        names = self.card_names()
        return (int(names[-1][:4]) + 1) if names else 1

    @property
    def state_path(self):
        return os.path.join(self.live, SESSION_JSON if self.stored else "state.json")

    @property
    def messages_path(self):
        return os.path.join(self.inbox, "messages.jsonl")

    @property
    def turns_path(self):
        return os.path.join(self.live, "turns.jsonl")

    def state(self):
        """The session's state. A stored session's is its session.json, with
        the legacy `hw` key added when `writeup` is a homework set under the
        root, so `board hw` works on the session's writeup."""
        if not self.stored:
            try:
                with open(self.state_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                return {}
        s = _read_json(self.state_path)
        said = s.get("writeup")
        if said and not s.get("hw"):
            rel = os.path.relpath(os.path.join(self.atlas, str(said)), self.root)
            if not rel.startswith("..") and _is_set_source(rel):
                s["hw"] = rel
        return s
