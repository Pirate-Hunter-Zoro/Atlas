"""A workspace on disk, its session directory, and the paths inside it.

Every path the board reads or writes during a lesson hangs off a Repo, so a
layout change happens here only. A Repo is always handed its session
directory; a stored session (`sessions/<id>/` with session.json) has its
state in session.json and its root at the bound subject, or the Atlas root
while unbound.

The constraint: this runs on the cluster's python3 (3.7) through jobs.py,
so no walrus and no `match`.
"""

import json
import os
import re


# The session a CLI process bound (`resolve`), for code holding only a root.
_BOUND = {}


def session_dir(root):
    """The session directory `resolve` bound for the workspace at `root` in
    this process, else None."""
    return _BOUND.get(os.path.realpath(root))


def session_path(root, *parts):
    """A path inside the session directory bound for the workspace at
    `root`, else None."""
    said = session_dir(root)
    return os.path.join(said, *parts) if said else None


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
    and always a dict; {} where no session is bound."""
    where = session_dir(root)
    if not where:
        return {}
    said = Repo(root, where, create=False).state()
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
    """Is `rel`, relative to a subject root, where a write-up lives: a
    homework set, or a session's own `docs/<slug>/*.tex`?"""
    from fnmatch import fnmatch
    from . import homework                                   # local: light
    rel = rel.replace(os.sep, "/")
    return any(fnmatch(rel, pat.replace(os.sep, "/")) for pat in homework.PINNABLE)


# ---------------------------------------------------------------------------
# where a mark's record lives
# ---------------------------------------------------------------------------
DOC_KEY = "doc/"


def ink_dir(repo, key):
    """The directory holding the ink of annotation `key`: a card's in the
    session (`repo.notes`), a document page's (`doc/...`) in `repo.doc_ink`
    when the repo has one."""
    if str(key or "").startswith(DOC_KEY):
        return getattr(repo, "doc_ink", None) or repo.notes
    return repo.notes


def ink_dirs(repo):
    """Every directory `ink_dir` can answer for `repo`, session first."""
    out = [repo.notes]
    doc = getattr(repo, "doc_ink", None)
    if doc and doc != repo.notes:
        out.append(doc)
    return out


def ink_records(repo, suffix=".json"):
    """`(dir, name)` of every ink file ending in `suffix`, from the session
    for cards and `doc_ink` for document pages."""
    out = []
    for where in ink_dirs(repo):
        try:
            names = sorted(os.listdir(where))
        except OSError:
            continue
        out += [(where, n) for n in names if n.endswith(suffix)]
    return out


# ---------------------------------------------------------------------------
# which workspace a command runs in
# ---------------------------------------------------------------------------
class NoWorkspace(SystemExit):
    """Raised instead of answering with the Atlas root or with no session
    where one is needed; uncaught, the CLI exits 1 having created nothing."""


# A sessionless Repo's session directory: never created.
NONE = ".none"


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


def resolve(root=None, create=True, need_session=True):
    """The Repo a CLI command works on.

    With `TUTORBOARD_SESSION`, that session over `root`, else the nearest
    workspace above the cwd, else the Atlas root. Without it, a command
    needing a session raises NoWorkspace; others get `sessionless`.
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
    if need_session:
        raise NoWorkspace(
            "this command works on a session, and none is named: it runs "
            "inside a tutor turn, or with TUTORBOARD_SESSION set to "
            "sessions/<id>")
    return sessionless(find_repo(root))


def sessionless(root, atlas=None):
    """A Repo over `root` with no session; its session directory
    `<atlas>/sessions/.none` is never created, so writes fail loudly."""
    repo = Repo(root, os.path.join(atlas or ATLAS, "sessions", NONE),
                create=False)
    repo.sessionless = True
    return repo


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

    sessionless = False

    def __init__(self, root, session, create=True):
        if not session:
            raise ValueError("a Repo needs its session directory")
        self.root = os.path.abspath(root)
        self.session = os.path.abspath(session)
        # A stored session (`sessions/<id>/`) rather than a workspace's live/.
        self.stored = is_stored(self.session)
        # The Atlas root holding `sessions/`, for a stored session.
        self.atlas = (os.path.dirname(os.path.dirname(self.session))
                      if self.stored else None)
        # The legacy name for the session directory.
        self.live = self.session
        self.cards = os.path.join(self.live, "cards")
        self.inbox = os.path.join(self.live, "inbox")
        self.uploads = (os.path.join(self.live, "uploads") if self.stored
                        else os.path.join(self.inbox, "uploads"))
        # Compiled TikZ, keyed by source and subject macros (`server/tikz.py`).
        self.tikz = (os.path.join(os.path.dirname(self.session), ".tikz")
                     if self.stored else os.path.join(self.live, "tikzcache"))
        self.archive = os.path.join(self.live, "archive")
        self.slate = os.path.join(self.live, "slate")
        # What was handed in, frozen: the slate is written over.
        self.answers = os.path.join(self.live, "answers")
        # Ink on cards, per card: the anchor that survives reflow.
        self.notes = os.path.join(self.live, "annotations")
        # Typed answers drafted per question, kept across input switches.
        self.text = os.path.join(self.live, "text")
        # Document-page ink of a bound session lives in the subject's ignored
        # `.ink/`, shared by its sessions; elsewhere it stays in `notes`.
        self.doc_ink = None
        if self.stored and os.path.realpath(self.root) != os.path.realpath(self.atlas):
            self.doc_ink = os.path.join(self.root, ".ink")
        if create:
            self.ensure_dirs()

    # Re-asserted on every call, not only at startup: a pull can remove an
    # emptied tracked directory under a running board, and every write there
    # would then 500. `cli=True` skips `annotations` and `text`, which only a
    # board creates.
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
        """Merge `kw` into the state file; a None value clears its key. In a
        stored session `hw` is written as `writeup` (relative to the Atlas
        root), and the always-present keys are nulled, not dropped."""
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
        """The session's state: a stored session's session.json, plus the
        legacy `hw` key derived from `writeup` for `board writeup`."""
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
