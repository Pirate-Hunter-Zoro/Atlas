"""The session store: `sessions/<YYYYMMDD-HHMMSS>/` under the Atlas root.

    new(title=None, view="board")   a fresh session, unbound, in teach mode;
                      `view` slate is a notes canvas
    end(id)           set `ended`, and commit what the session leaves behind
    reopen(id)        clear `ended`
    delete(id)        move the directory to the trash
    prune_trash()     drop trash entries older than 30 days (server start)
    bind(id, subject) set `subject`, with a non-waking `[bind]` line
    set_code(id, code) record or clear the session's cluster coding session
    coding()          {id: code} for every session with `code` set
    file(id, upload)  move an upload into the bound subject, ink and all
    all(), get(id), path(id), repo(id)
    import_live(atlas, workspace, subject)   a workspace's live/ becomes one
                      open session, every move in a manifest; reverse_import
                      undoes it (the cutover, board/scripts/import-live.py)

A session is Mac-only and ignored (`/sessions/` in .gitignore, and the audit
refuses any path under it). It persists until the owner ends it: nothing but
`end` sets `ended`. An id is matched against `ID_RE` and never joined onto a
path unchecked.

session.json = {id, title, subject, mode, opened, ended, writeup, seen, code,
view}. `view` is `board`, or `slate` for a notes canvas (VIEWS). `subject` is a subject id (`courses/X`, `projects/Y`) or null;
`writeup` is a source path relative to the Atlas root, or null. Times are
local `YYYY-MM-DD HH:MM:SS`.

`code` is null, or the session's coding session at the cluster as the Mac
last heard it (`cluster.Ear`): {ref, sha, paths, step, subject, prev, seen,
at}. `ref` is `refs/heads/code/<id>`, `sha` its tip, `paths` the held paths
(repository-relative), `prev` the tip before, and `seen` the commit whose held
files this checkout's working tree has. While it is set, `gitops.commit`
refuses commits to the held paths on main and `board push` from the session
goes to the ref.
"""

import json
import os
import re
import shutil
import time

from . import fenced, gitops, paths, subjects
from .course import repo as course_repo

STORE = "sessions"
ID_RE = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")
STAMP = "%Y%m%d-%H%M%S"
WHEN = "%Y-%m-%d %H:%M:%S"

# The directories every session has from the start (section 2's layout).
# Files -- turns.jsonl, inbox/messages.jsonl, agent.json -- appear when written.
LAYOUT = ("cards", "slate", "answers", "inbox", "uploads", "text", "annotations")


class NoSession(LookupError):
    """No session by that id in this store."""


class Refused(ValueError):
    """A bind or a filing that cannot be done as asked; the message says why."""


# A subject's document ink, ignored: `<subject>/.ink/`, keyed `doc/<id>/p<n>`.
INK = ".ink"
# The default home of a filed upload, ignored: `<subject>/materials/`.
MATERIALS = "materials"


def store(base=None):
    """`<Atlas root>/sessions`."""
    return os.path.join(base or subjects.root(), STORE)


def path(sid, base=None):
    """The directory of session `sid`, or None when there is no such session."""
    sid = str(sid or "").strip()
    if not ID_RE.match(sid):
        return None
    where = os.path.join(store(base), sid)
    return where if course_repo.is_stored(where) else None


def _need(sid, base):
    where = path(sid, base)
    if not where:
        raise NoSession("no session %r in %s" % (sid, store(base)))
    return where


def get(sid, base=None):
    """session.json of `sid`, or None."""
    where = path(sid, base)
    if not where:
        return None
    return course_repo._read_json(os.path.join(where, course_repo.SESSION_JSON))


def all(base=None):                                          # noqa: A001
    """Every session's session.json, newest first."""
    top = store(base)
    try:
        names = os.listdir(top)
    except OSError:
        return []
    out = []
    for sid in sorted((n for n in names if ID_RE.match(n)), reverse=True):
        one = get(sid, base)
        if one:
            out.append(one)
    return out


def repo(sid, base=None, create=False):
    """A Repo serving session `sid`: its root is the bound subject's, or the
    Atlas root while unbound."""
    where = _need(sid, base)
    return course_repo.Repo(course_repo.stored_root(where), session=where,
                            create=create)


def _save(where, rec):
    course_repo._write_json(os.path.join(where, course_repo.SESSION_JSON), rec)


# How a session is shown: the board, or the full slate of a notes canvas,
# whose End has the tutor transcribe its pages into notes.md.
VIEWS = ("board", "slate")


def new(title=None, base=None, now=None, view="board"):
    """Create a session and return its session.json.

    The id is the local time to the second; a clash takes `-2`, `-3`, ...
    `os.mkdir` claims the name, so two callers in one second get two
    sessions and neither touches the other. `view` is one of VIEWS.
    """
    if view not in VIEWS:
        raise Refused("a session's view is board or slate, not %r" % (view,))
    now = time.time() if now is None else now
    top = store(base)
    os.makedirs(top, exist_ok=True)
    stem = time.strftime(STAMP, time.localtime(now))
    sid, n = stem, 1
    while True:
        try:
            os.mkdir(os.path.join(top, sid))
            break
        except FileExistsError:
            n += 1
            sid = "%s-%d" % (stem, n)
    where = os.path.join(top, sid)
    rec = {"id": sid, "title": title or None, "subject": None, "mode": "teach",
           "opened": time.strftime(WHEN, time.localtime(now)), "ended": None,
           "writeup": None, "seen": 0, "code": None, "view": view}
    _save(where, rec)
    for d in LAYOUT:
        os.makedirs(os.path.join(where, d), exist_ok=True)
    return rec


def _artifacts(base, subject, sid):
    """The directories of the subject's artifacts whose doc.json lists this
    session -- new ones under `docs/` and ones placed in place -- relative to
    the Atlas root."""
    from . import artifacts                              # local: artifacts imports this
    return ["%s/%s" % (subject, a["rel"])
            for a in artifacts.for_session(os.path.join(base, subject), sid)]


def end(sid, base=None, now=None):
    """End session `sid`: set `ended`, then commit through gitops the bound
    subject's TUTOR.md and every artifact whose doc.json lists the session.

    `(record, ok, said)`. Ending an ended session keeps its time and retries
    the commit, so a commit that failed once can be had again.
    """
    base = base or subjects.root()
    where = _need(sid, base)
    rec = get(sid, base)
    if not rec.get("ended"):
        now = time.time() if now is None else now
        rec["ended"] = time.strftime(WHEN, time.localtime(now))
        _save(where, rec)
    found = subjects.find(rec.get("subject"), base) if rec.get("subject") else None
    if not found:
        return rec, True, "ended; the session is bound to no subject, so nothing was committed"
    subject = found["id"]
    keep = []
    if os.path.isfile(os.path.join(base, subject, "TUTOR.md")):
        keep.append("%s/TUTOR.md" % subject)
    keep += _artifacts(base, subject, rec["id"])
    if not keep:
        return rec, True, "ended; nothing of %s to commit" % subject
    ok, said = gitops.commit(base, keep, "%s: session %s ended" % (subject, rec["id"]))
    return rec, ok, said


def reopen(sid, base=None):
    """Clear `ended`. A cluster report for an ended session reopens it."""
    where = _need(sid, base)
    rec = get(sid, base)
    if rec.get("ended"):
        rec["ended"] = None
        _save(where, rec)
    return rec


def trash(name, now=None):
    """A fresh `<trash>/<stamp>[-n]/` directory for one delete, and the path
    `name` takes inside it (not yet made)."""
    now = time.time() if now is None else now
    stamp = time.strftime(STAMP, time.localtime(now))
    dest = os.path.join(paths.TRASH, stamp, name)
    n = 1
    while os.path.lexists(dest):
        n += 1
        dest = os.path.join(paths.TRASH, "%s-%d" % (stamp, n), name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    return dest


# How long a delete stays in the trash before the server's startup prunes it.
TRASH_DAYS = 30


def prune_trash(now=None, days=TRASH_DAYS):
    """Remove every `<trash>/<stamp>[-n]/` older than `days`, judged by the
    stamp in its name. Anything else in the trash is left alone. Returns the
    names removed."""
    now = time.time() if now is None else now
    try:
        names = sorted(os.listdir(paths.TRASH))
    except OSError:
        return []
    gone = []
    for name in names:
        m = re.match(r"\A(\d{8}-\d{6})(?:-\d+)?\Z", name)
        if not m:
            continue
        try:
            at = time.mktime(time.strptime(m.group(1), STAMP))
        except (ValueError, OverflowError):
            continue
        if now - at < days * 86400:
            continue
        shutil.rmtree(os.path.join(paths.TRASH, name), ignore_errors=True)
        gone.append(name)
    return gone


def delete(sid, base=None, now=None):
    """Move session `sid` to `<trash>/<stamp>/<id>` and return that path."""
    where = _need(sid, base)
    dest = trash(os.path.basename(where), now)
    shutil.move(where, dest)
    return dest


def quiet_line(messages_path, text, signal, now=None, **extra):
    """Append a line to an inbox that wakes nothing: `"wake": false`, so the
    runner queues no turn for it, and the next turn takes it with the rest
    (`lesson/inbox.py`)."""
    now = time.time() if now is None else now
    rec = {"t": now, "iso": time.strftime(WHEN, time.localtime(now)),
           "from": "board", "text": text, "signal": signal, "read": False,
           "wake": False}
    rec.update(extra)
    os.makedirs(os.path.dirname(messages_path), exist_ok=True)
    with open(messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def _line(where, text, signal, now=None, **extra):
    """`quiet_line` into the inbox of the session at `where`."""
    return quiet_line(os.path.join(where, "inbox", "messages.jsonl"), text,
                      signal, now=now, **extra)


def bind(sid, subject, base=None, now=None):
    """Bind session `sid` to `subject`, matched against `subjects.all()`.

    `(record, changed)`. Sets `subject` to the subject's id and appends a
    non-waking `[bind] <id>` line. Nothing is filed (D21) and nothing moves:
    uploads stay in the session until `file` puts each one somewhere.
    Binding to the subject already bound changes nothing and says nothing.
    """
    base = base or subjects.root()
    where = _need(sid, base)
    found = subjects.find(subject, base) if subject else None
    if not found:
        raise Refused("no subject %r: name one of courses/<name> or "
                      "projects/<name>, or make it with --create" % subject)
    rec = get(sid, base)
    if rec.get("subject") == found["id"]:
        return rec, False
    rec["subject"] = found["id"]
    _save(where, rec)
    _line(where, "[bind] %s" % found["id"], "bind", now=now,
          subject=found["id"])
    return rec, True


def set_code(sid, code, base=None):
    """Set session `sid`'s `code` to `code` (a dict), or clear it (None).
    The record."""
    where = _need(sid, base)
    rec = get(sid, base)
    rec["code"] = dict(code) if code else None
    _save(where, rec)
    return rec


def coding(base=None):
    """`{id: code}` for every session in the store with `code` set, ended or
    not: a coding session at the cluster outlives the Mac session's End."""
    out = {}
    for rec in all(base):
        code = rec.get("code")
        if isinstance(code, dict) and code.get("ref") and rec.get("id"):
            out[rec["id"]] = code
    return out


# ---------------------------------------------------------------------------
# filing an upload, and the ink that follows it
# ---------------------------------------------------------------------------
INK_FILE = re.compile(r"\Adoc-(.+)-p(\d{1,4})-[0-9a-f]{8}\Z")
INK_EXTS = (".dir.png", ".png", ".json", ".gone")


def ink_ident(rel):
    """The ink id of a file at `rel`, its path relative to where it is kept:
    `uploads/<name>` in a session, `materials/<name>` (or any path) in a
    subject. The library's id rule (`library._ident`), so the reader keys ink
    on the id the library lists the file under: lower-case letters, digits and
    dashes, at most 40, which `writing.ANN_DOC` takes. Where two files share
    one, the library numbers the later; `file` asks it (`library.ident_map`)."""
    from .course import library                        # local: a cycle
    rel = str(rel or "").replace(os.sep, "/").strip("/")
    where, name = os.path.split(rel)
    return library._ident(where, os.path.splitext(name)[0], ())


def _ink_of(folder, ident):
    """`[(filename, key, ext)]`: every ink file in `folder` keyed on a page of
    document `ident`. The key is recovered from the name and kept only when
    `writing.ann_file` derives that very name from it."""
    from .server.routes import writing                 # local: avoids a cycle
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    out = []
    for name in names:
        ext = next((e for e in INK_EXTS if name.endswith(e)), None)
        if not ext:
            continue
        stem = name[:-len(ext)]
        m = INK_FILE.match(stem)
        if not m or m.group(1) != ident:
            continue
        key = "doc/%s/p%d" % (ident, int(m.group(2)))
        if writing.ann_file(key) == stem:
            out.append((name, key, ext))
    return out


def _upload(where, upload):
    """The upload's path inside the session's `uploads/`, or Refused."""
    top = os.path.realpath(os.path.join(where, "uploads"))
    said = str(upload or "").strip()
    if not said:
        raise Refused("name the upload to file")
    if os.path.isabs(said):
        full = os.path.realpath(said)
    else:
        bare = said[len("uploads/"):] if said.startswith("uploads/") else said
        full = os.path.realpath(os.path.join(top, bare))
    if os.path.dirname(full) != top or not os.path.isfile(full):
        raise Refused("%s is not an upload of this session (%s)" % (said, top))
    return full


def _dest(home, name, dest):
    """`(relpath, full path)` of where an upload named `name` is filed inside
    the subject at `home`, or Refused."""
    said = str(dest or MATERIALS).strip()
    if os.path.isabs(said) or said.startswith("~"):
        raise Refused("%s: file into a path inside the subject, not an "
                      "absolute one" % said)
    rel = said.replace("\\", "/")
    if rel.endswith("/") or rel in (".", MATERIALS) \
            or os.path.isdir(os.path.join(home, rel)):
        rel = "%s/%s" % (rel.rstrip("/"), name)
    rel = os.path.normpath(rel).replace(os.sep, "/")
    parts = rel.split("/")
    if rel.startswith("../") or rel == ".." or any(p == ".." for p in parts):
        raise Refused("%s leaves the subject" % said)
    if any(p.startswith(".") for p in parts):
        raise Refused("%s: not into a hidden directory (.git, .ink, ...)" % said)
    if fenced.in_fence(rel) or parts[0] == "results":
        raise Refused("%s: nothing is filed under a fenced directory" % said)
    full = os.path.join(home, rel)
    inside = os.path.relpath(os.path.realpath(os.path.dirname(full)),
                             os.path.realpath(home))
    if inside == ".." or inside.startswith("../"):
        raise Refused("%s leaves the subject" % said)
    if os.path.lexists(full):
        raise Refused("%s already exists in the subject; name another path" % rel)
    return rel, full


def file(sid, upload, dest=None, base=None, now=None):           # noqa: A001
    """Move `upload` from session `sid`'s `uploads/` into its bound subject:
    `materials/` by default, or `dest`, a path inside the subject (a
    directory, or the file's new name).

    The upload's ink moves with it, from the session's `annotations/` or
    `<subject>/.ink/` to `<subject>/.ink/`, re-keyed from the upload's ink id
    to the id the library lists the file under in its new place. Refused: an unbound session, an upload not in `uploads/`,
    a destination outside the subject, hidden or fenced, or already taken,
    and ink already in `.ink/` under the new keys. Nothing is committed: a
    filed upload is third-party or the owner's raw material (D1).

    Returns {from, to, subject, keys, doc}: `to` is relative to the subject,
    `keys` maps each old ink key to its new one, and `doc` is the file's ink
    id where it is now.
    """
    base = base or subjects.root()
    where = _need(sid, base)
    rec = get(sid, base)
    found = subjects.find(rec.get("subject"), base) if rec.get("subject") else None
    if not found:
        raise Refused("this session is bound to no subject, so an upload has "
                      "nowhere to go: bind it first (board bind <subject>)")
    src = _upload(where, upload)
    name = os.path.basename(src)
    rel, full = _dest(found["root"], name, dest)

    from .course import library                        # local: a cycle
    from .server.routes import writing                 # local: avoids a cycle
    notes = os.path.join(where, "annotations")
    ink = os.path.join(found["root"], INK)
    old = next((u["id"] for u in library.uploads(repo(sid, base))
                if u["name"] == name), "") or ink_ident("uploads/" + name)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    shutil.move(src, full)
    # The id the library lists the file under in its new place, asked once it
    # is there; a file the library offers no document for keeps the rule's.
    new = library.ident_map(found["root"]).get(os.path.realpath(full)) \
        or ink_ident(rel)
    moves = []
    try:
        # Ink drawn while the session was bound is already in `.ink/` (the
        # server routes document keys there); ink drawn before the bind is in
        # the session's annotations. `.ink/` first, so it wins a key held in
        # both.
        for folder in (ink, notes):
            for fname, key, ext in _ink_of(folder, old):
                page = key.rsplit("/p", 1)[1]
                nkey = "doc/%s/p%s" % (new, page)
                target = os.path.join(ink, writing.ann_file(nkey) + ext)
                if nkey == key or any(m[1] == target for m in moves):
                    continue
                if os.path.lexists(target):
                    raise Refused("%s already holds ink for %s; it belongs to no "
                                  "file there now -- delete it, or file under "
                                  "another name" % (target, nkey))
                moves.append((os.path.join(folder, fname), target, key, nkey, ext))
    except Refused:
        shutil.move(full, src)
        raise
    keys = {}
    if moves:
        os.makedirs(ink, exist_ok=True)
    for path_from, path_to, key, nkey, ext in moves:
        got = course_repo._read_json(path_from) if ext in (".json", ".gone") else {}
        if got.get("card") == key:
            got["card"] = nkey
            course_repo._write_json(path_to, got)
            os.remove(path_from)
        else:
            shutil.move(path_from, path_to)
        keys[key] = nkey
    shown = "%s/%s" % (found["id"], rel)
    _line(where, "[filed] uploads/%s -> %s" % (name, shown), "filed", now=now,
          files=[shown])
    library.forget()
    return {"from": "uploads/" + name, "to": rel, "subject": found["id"],
            "keys": keys, "doc": new}


def current():
    """The id of the session `TUTORBOARD_SESSION` names, or ""."""
    said = os.environ.get("TUTORBOARD_SESSION") or ""
    if said and course_repo.is_stored(said):
        return os.path.basename(os.path.normpath(said))
    return ""


def url(rec):
    """Where a session opens: its board, or the slate of a notes canvas."""
    return "/s/%s/%s" % (rec.get("id"),
                         "slate" if rec.get("view") == "slate" else "board")


def slate_pages(sid, base=None):
    """The page pictures of session `sid`'s slate with ink on them, in page
    order: what a notes canvas's End has the tutor transcribe."""
    from .lesson import slate as lesson_slate               # local: heavy
    where = _need(sid, base)

    class _At(object):
        slate = os.path.join(where, "slate")
    out = []
    for page in lesson_slate.read_slate_pages(_At):
        png = os.path.join(_At.slate, "page-%02d.png" % page["page"])
        if page.get("strokes") and os.path.isfile(png):
            out.append(png)
    return out


def show(rec):
    """session.json as the CLI prints it."""
    return json.dumps(rec, indent=2)


def summary(rec, base=None):
    """What the home screen shows of a session beyond session.json:
    `{last_card: {id, title} or None, new_cards}`.

    `new_cards` counts the cards written after `seen` (epoch seconds; the
    board's POST /seen sets it). Only the newest card's file is opened, for
    its title; the rest are a listdir and a stat each.
    """
    from .lesson import cards as lesson_cards               # local: heavy
    out = {"last_card": None, "new_cards": 0}
    where = path(rec.get("id"), base)
    if not where:
        return out
    folder = os.path.join(where, "cards")
    try:
        names = sorted(n for n in os.listdir(folder)
                       if lesson_cards.CARD_RE.match(n))
    except OSError:
        return out
    try:
        seen = float(rec.get("seen") or 0)
    except (TypeError, ValueError):
        seen = 0.0
    fresh = 0
    for name in names:
        try:
            if os.stat(os.path.join(folder, name)).st_mtime > seen:
                fresh += 1
        except OSError:
            continue
    out["new_cards"] = fresh
    if names:
        last = names[-1]
        title = ""
        try:
            with open(os.path.join(folder, last), "r", encoding="utf-8") as fh:
                meta, _ = lesson_cards.parse_front_matter(fh.read(2000))
            title = (meta.get("title") or "").strip()[:120]
        except (OSError, ValueError, UnicodeDecodeError):
            title = ""
        out["last_card"] = {"id": last[:4], "title": title}
    return out


# ---------------------------------------------------------------------------
# import_live: a workspace's live/ becomes one open session (the cutover)
# ---------------------------------------------------------------------------
# `{old workspace id: session id}`: which workspaces were imported, and as
# what, so a second import of one is refused.
IMPORTED = ".imported.json"
# The default manifest of every move an import made, JSON lines.
MANIFEST = ".import-manifest.jsonl"
CARRIED = "Carried over"

# live/ entries that become the session's under the same name.
SAME_DIRS = ("cards", "slate", "answers", "text")
SAME_FILES = ("turns.jsonl", ".turnseq", "cost.jsonl", "agent.log", "export.json")
# Dropped, and not migrated (D15): set aside beside the manifest, so a
# reverse can put them back.
DROPPED = ("hw.json", "tikzcache", "paper", "push.json", ".board.json",
           "board.log", "BRIEF.md", "TEACHING.md", "directions")
# The subject's runtime state, moved by `jobs.migrate_state`.
JOB_STATE = ("jobs.jsonl", "jobs.reported", "missions", "coach.woken")
POST_MERGE = re.compile(r"\A(courses|projects)/[A-Za-z0-9][A-Za-z0-9._ -]*\Z")
CARD_NAME = re.compile(r"\A(\d{4})[-_.].*\.(md|markdown|tex)\Z")
CARD_INK = re.compile(r"\A\d{1,4}\.(json|png|gone)\Z")
OLD_CARD_LINK = re.compile(r"#/w/([^/\s()\[\]<>\"'`]+)/([^/\s()\[\]<>\"'`]+)"
                           r"/card/(\d{4})")


class _Mover(object):
    """Every change an import makes, made and then appended to the manifest
    as one JSON line `{op, from, to}`, so `reverse_import` undoes it bottom-up:

        move   `from` was renamed to `to`            back: rename `to` to `from`
        make   `to` was created (a file, or a tree   back: remove the file, or
               of directories)                             the tree if it is empty
        rmdir  the emptied directory `from` went     back: make it again
        kept   `to` is a copy of `from` as it was    back: `from` := `to`
        entry  `key` was added to the map at `to`    back: drop the key

    With `apply` False nothing changes and nothing is written: the records
    are the plan.
    """

    def __init__(self, manifest, apply):
        self.manifest = manifest
        self.apply = apply
        self.records = []
        self._made = set()

    def _log(self, op, src, dst, **extra):
        rec = {"op": op, "from": src, "to": dst}
        rec.update(extra)
        self.records.append(rec)
        if self.apply:
            os.makedirs(os.path.dirname(self.manifest), exist_ok=True)
            with open(self.manifest, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return rec

    def exists(self, p):
        return os.path.lexists(p) or p in self._made

    def mkdirs(self, d):
        if self.exists(d):
            return
        top = d
        while not self.exists(os.path.dirname(top)):
            top = os.path.dirname(top)
        if self.apply:
            os.makedirs(d)
        p = d
        while True:
            self._made.add(p)
            if p == top:
                break
            p = os.path.dirname(p)
        self._log("make", None, top)

    def move(self, src, dst):
        if self.exists(dst):
            raise Refused("%s is already there; nothing was moved onto it" % dst)
        self.mkdirs(os.path.dirname(dst))
        if self.apply:
            shutil.move(src, dst)
        self._made.add(dst)
        self._log("move", src, dst)

    def write(self, dst, text):
        if self.exists(dst):
            raise Refused("%s is already there; nothing was written over it" % dst)
        self.mkdirs(os.path.dirname(dst))
        if self.apply:
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(text)
        self._made.add(dst)
        self._log("make", None, dst)

    def made(self, dst):
        """Record a file something else just created."""
        self._made.add(dst)
        self._log("make", None, dst)

    def keep(self, src, dst):
        """A copy of `src` as it is now, at `dst`."""
        self.mkdirs(os.path.dirname(dst))
        if self.apply:
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst)
        self._made.add(dst)
        self._log("kept", src, dst)

    def rmdir(self, d):
        if self.apply:
            os.rmdir(d)
        self._made.discard(d)
        self._log("rmdir", d, None)

    def entry(self, where, key, value):
        if self.apply:
            have = course_repo._read_json(where)
            have[key] = value
            os.makedirs(os.path.dirname(where), exist_ok=True)
            course_repo._write_json(where, have)
        self._log("entry", None, where, key=key, value=value)


def _listing(d):
    try:
        return sorted(os.listdir(d))
    except OSError:
        return []


def _drain(mv, src, dst, clash):
    """Move everything in the directory `src` into `dst`, merging directories
    present in both; a file already at its destination goes to `clash(rel)`
    instead. `src` is then removed, emptied. The rel paths sent to `clash`."""
    sent = []

    def walk(s, d, rel):
        for name in _listing(s):
            one, two = os.path.join(s, name), os.path.join(d, name)
            r = "%s/%s" % (rel, name) if rel else name
            if not mv.exists(two):
                mv.move(one, two)
            elif os.path.isdir(one) and os.path.isdir(two) \
                    and not os.path.islink(one):
                walk(one, two, r)
            else:
                mv.move(one, clash(r))
                sent.append(r)
        mv.rmdir(s)

    mv.mkdirs(dst)
    walk(src, dst, "")
    return sent


def _workspace_id(atlas, ws):
    rel = os.path.relpath(os.path.realpath(ws), os.path.realpath(atlas))
    if rel.startswith(".."):
        rel = "/".join(os.path.normpath(ws).split(os.sep)[-2:])
    return rel.replace(os.sep, "/")


def _subject_name(home, ws, subject):
    for where in (home, ws):
        said = course_repo._read_json(os.path.join(where, "tutorboard.json"))
        if said.get("name"):
            return str(said["name"])
    return subject.split("/", 1)[1].replace("-", " ")


def _stance(state, home, ws):
    """"do" or "teach": the sitting's stance, else the workspace's."""
    for said in (state,
                 course_repo._read_json(os.path.join(ws, "tutorboard.json")),
                 course_repo._read_json(os.path.join(home, "tutorboard.json"))):
        if said.get("stance"):
            return "do" if str(said["stance"]).lower() == "do" else "teach"
    return "teach"


def _jsonl(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({})
    except OSError:
        pass
    return out


def _has_lesson(live):
    """Cards, turns or messages: anything that makes the live/ a session."""
    if any(CARD_NAME.match(n) for n in _listing(os.path.join(live, "cards"))):
        return True
    return bool(_jsonl(os.path.join(live, "turns.jsonl"))
                or _jsonl(os.path.join(live, "inbox", "messages.jsonl")))


def _opened(state, live, now):
    said = str(state.get("opened") or "").strip()
    for fmt in (WHEN, "%Y-%m-%d %H:%M"):
        try:
            return time.strftime(WHEN, time.strptime(said, fmt))
        except ValueError:
            continue
    first = []
    for name in ("turns.jsonl", os.path.join("inbox", "messages.jsonl")):
        for r in _jsonl(os.path.join(live, name)):
            try:
                first.append(float(r.get("t") or 0))
            except (TypeError, ValueError):
                pass
    first = [t for t in first if t > 0]
    if not first:
        cards = os.path.join(live, "cards")
        first = [os.path.getmtime(os.path.join(cards, n)) for n in _listing(cards)
                 if CARD_NAME.match(n)]
    return time.strftime(WHEN, time.localtime(min(first) if first else now))


def _writeup(state, ws, subject):
    """The bound homework set's source, relative to the Atlas root, or None."""
    hw = str(state.get("hw") or "").strip()
    if not hw:
        return None
    rel = hw
    if not hw.endswith(".tex"):
        from .course import homework                     # local: light
        rel = next((s["rel"] for s in homework.sets(ws) if s["name"] == hw), "")
    rel = os.path.normpath(rel).replace(os.sep, "/") if rel else ""
    if not rel or rel.startswith("../") or rel == ".." or os.path.isabs(rel):
        return None
    return "%s/%s" % (subject, rel)


def _title(name, state):
    what = state.get("chapter") or state.get("hw") or state.get("session")
    if what and state.get("hw") == what:
        what = os.path.splitext(os.path.basename(str(what)))[0]
    return "%s: %s" % (name, what or "imported")


def _relink(text, ws_id, sid):
    """Old-grammar links to a card of this workspace, `#/w/<family>/<ws>/
    card/NNNN`, as `#/s/<sid>/card/NNNN`. Links to other workspaces stay."""
    from urllib.parse import unquote
    fam, _, name = ws_id.partition("/")

    def one(m):
        if unquote(m.group(1)).lower() == fam.lower() \
                and unquote(m.group(2)) == name:
            return "#/s/%s/card/%s" % (sid, m.group(3))
        return m.group(0)
    return OLD_CARD_LINK.sub(one, text)


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _carried(live):
    """NEXT.md and handoffs/*.md as the body of one note card, or ""."""
    parts = []
    said = _read_text(os.path.join(live, "NEXT.md")).strip()
    if said:
        parts.append("**From NEXT.md**\n\n" + said)
    hand = os.path.join(live, "handoffs")
    for name in _listing(hand):
        if name.endswith(".md"):
            said = _read_text(os.path.join(hand, name)).strip()
            if said:
                parts.append("**From handoffs/%s**\n\n%s" % (name, said))
    return "\n\n".join(parts)


def _agent(live):
    """agent.json as the session keeps it: idle, nobody's pid, `owed` kept."""
    rec = course_repo._read_json(os.path.join(live, "agent.json"))
    rec.update({"state": "idle", "pid": None, "waking_at": 0,
                "turn_started": 0, "restarting": False, "retrying": False})
    return json.dumps(rec, indent=2) + "\n"


def _tree(top):
    """Every path under `top`, relative, directories marked with a slash."""
    out = set()
    for here, dirs, files in os.walk(top):
        rel = os.path.relpath(here, top)
        for d in dirs:
            out.add(os.path.normpath(os.path.join(rel, d)) + "/")
        for f in files:
            out.add(os.path.normpath(os.path.join(rel, f)))
    return out


def _import_jobs(mv, live, home, keep):
    """The registry, claims and Colibri tasks of `live` into the subject's
    `relay/state/`, by `jobs.migrate_state`. What it consumes is kept first
    and what it makes is recorded, so a reverse undoes it. The number of
    paths it moved."""
    from . import jobs                                   # local: heavy
    present = [n for n in JOB_STATE if os.path.lexists(os.path.join(live, n))]
    if not present:
        return 0
    state = os.path.join(home, jobs.STATE)
    mv.mkdirs(state)
    for n in present:
        mv.keep(os.path.join(live, n), os.path.join(keep, "jobs", n))
    for rel in (os.path.join(jobs.STATE, jobs.NAME), jobs.OLD_RELAY_CLAIMS,
                jobs.NAME):
        if os.path.lexists(os.path.join(home, rel)):
            mv.keep(os.path.join(home, rel), os.path.join(keep, "subject", rel))
    if not mv.apply:
        return len(present)
    before = _tree(state)
    moved = jobs.migrate_state(home, live=live)
    new = sorted(_tree(state) - before, key=lambda r: (r.count("/"), r))
    for rel in new:
        if rel.endswith("/"):
            mv.made(os.path.join(state, rel.rstrip("/")))
    for rel in new:
        if not rel.endswith("/"):
            mv.made(os.path.join(state, rel))
    return moved


def _prune(mv, live):
    """Remove the emptied directories of `live`, and `live` itself when
    nothing is left: `archive/` is the caller's."""
    def walk(d, top):
        for name in _listing(d):
            one = os.path.join(d, name)
            if top and name == "archive":
                continue
            if os.path.isdir(one) and not os.path.islink(one):
                walk(one, False)
        if not top and not _listing(d):
            mv.rmdir(d)
    if mv.apply:
        walk(live, True)
        if not _listing(live):
            mv.rmdir(live)


def import_live(atlas, workspace, subject, manifest=None, dry_run=False,
                now=None):
    """Turn the workspace's `live/` into one open session bound to `subject`.

    `subject` is the post-merge id (`research/X` and `practice/X` become
    `projects/X`), and need not exist yet: the cutover imports before the
    merge. Every live/ entry has a destination (HANDOFF T14):

        state.json, .seen.json      session.json (title, mode, writeup, seen)
        cards/ slate/ answers/ text/ turns.jsonl .turnseq cost.jsonl
        agent.log export.json      the same names in the session; card text
                                    has this workspace's old links rewritten
        inbox/messages.jsonl        the same, read marks and all
        inbox/uploads/              uploads/
        annotations/                card records stay in the session, document
                                    records go to `<subject>/.ink/`
        NEXT.md, handoffs/*.md      one `note` card, "Carried over"
        marked/                     `<subject>/materials/marked/`
        jobs.*, missions/, coach.woken/
                                    `<subject>/relay/state/` (jobs.migrate_state)
        agent.json                  the same, idle, with `owed` kept
        archive/                    left where it is, for the caller
        dropped and not-migrated    set aside under `<manifest>.kept/`
        anything else               `imported/` in the session

    A live/ with no cards, no turns and no messages makes no session; its job
    state still moves. Every change is appended to `manifest` (default
    `sessions/.import-manifest.jsonl`) for `reverse_import`, and
    `sessions/.imported.json` maps the workspace id to the session's.

    Returns {workspace, subject, session, imported, kept, jobs, left, manifest,
    plan}. Refused: no live/, a subject id that is not post-merge, or a
    workspace already imported.
    """
    now = time.time() if now is None else now
    atlas = os.path.realpath(os.path.expanduser(atlas))
    ws = os.path.abspath(os.path.expanduser(workspace))
    live = os.path.join(ws, "live")
    if os.path.basename(ws) == "live" and not os.path.isdir(live):
        live, ws = ws, os.path.dirname(ws)
    if not os.path.isdir(live):
        raise Refused("%s has no live/ to import" % ws)
    subject = str(subject or "").strip().strip("/")
    if not POST_MERGE.match(subject) or ".." in subject.split("/"):
        raise Refused("%r is not a post-merge subject id: courses/<name> or "
                      "projects/<name>" % subject)
    home = os.path.join(atlas, subject)
    ws_id = _workspace_id(atlas, ws)
    top = store(atlas)
    mapping = os.path.join(top, IMPORTED)
    if ws_id in course_repo._read_json(mapping):
        raise Refused("%s is already imported, as session %s"
                      % (ws_id, course_repo._read_json(mapping)[ws_id]))
    manifest = os.path.abspath(manifest or os.path.join(top, MANIFEST))
    stem = os.path.splitext(manifest)[0] + ".kept"
    keep = os.path.join(stem, ws_id.replace("/", "-"))
    n = 1
    while _listing(keep):
        n += 1
        keep = os.path.join(stem, "%s-%d" % (ws_id.replace("/", "-"), n))

    mv = _Mover(manifest, not dry_run)
    if mv.apply:
        # Before any record: a manifest kept in `sessions/` must not be what
        # makes `sessions/`, or a reverse could never remove it.
        os.makedirs(os.path.dirname(manifest), exist_ok=True)
    out = {"workspace": ws_id, "subject": subject, "session": None,
           "imported": [], "kept": [], "jobs": 0, "left": [],
           "manifest": manifest, "plan": mv.records}

    if not _has_lesson(live):
        out["jobs"] = _import_jobs(mv, live, home, keep)
        _prune(mv, live)
        out["left"] = [n for n in _listing(live) if n != "archive"]
        return out

    state = course_repo._read_json(os.path.join(live, "state.json"))
    seen = course_repo._read_json(os.path.join(live, ".seen.json")).get("at") or 0
    try:
        seen = float(seen) if seen else 0
    except (TypeError, ValueError):
        seen = 0
    rec = {"title": _title(_subject_name(home, ws, subject), state),
           "subject": subject, "mode": _stance(state, home, ws),
           "opened": _opened(state, live, now), "ended": None,
           "writeup": _writeup(state, ws, subject), "seen": seen,
           "code": None, "view": "board"}

    mv.mkdirs(top)
    if mv.apply:
        made = new(rec["title"], base=atlas, now=now)
        sid = made["id"]
        where = os.path.join(top, sid)
        mv._log("make", None, where)
        made.update(rec)
        _save(where, made)
        mv.made(os.path.join(where, course_repo.SESSION_JSON))
    else:
        sid = time.strftime(STAMP, time.localtime(now))
        where = os.path.join(top, sid)
        mv._log("make", None, where)
        mv._made.add(where)
        for d in LAYOUT:
            mv._made.add(os.path.join(where, d))
    out["session"] = sid
    imported = os.path.join(where, "imported")

    def aside(rel):
        out["imported"].append(rel)
        return os.path.join(imported, rel)

    def kept(name):
        out["kept"].append(name)
        mv.move(os.path.join(live, name), os.path.join(keep, name))

    carried = _carried(live)
    last = 0
    for name in _listing(live):
        src = os.path.join(live, name)
        isdir = os.path.isdir(src) and not os.path.islink(src)
        if name == "archive" or (name in JOB_STATE and name != "missions"):
            continue
        if name in ("state.json", ".seen.json", "NEXT.md", "handoffs",
                    "agent.json") or name in DROPPED:
            kept(name)
        elif name == "cards" and isdir:
            for card in _listing(src):
                one = os.path.join(src, card)
                m = CARD_NAME.match(card)
                if m:
                    last = max(last, int(m.group(1)))
                text = _read_text(one) if m and os.path.isfile(one) else ""
                fixed = _relink(text, ws_id, sid) if text else ""
                if text and fixed != text:
                    mv.move(one, os.path.join(keep, "cards", card))
                    mv.write(os.path.join(where, "cards", card), fixed)
                else:
                    mv.move(one, os.path.join(where, "cards", card))
            mv.rmdir(src)
        elif name in SAME_DIRS and isdir:
            _drain(mv, src, os.path.join(where, name),
                   lambda r, n=name: aside("%s/%s" % (n, r)))
        elif name in SAME_FILES and not isdir:
            mv.move(src, os.path.join(where, name))
        elif name == "inbox" and isdir:
            for one in _listing(src):
                path_ = os.path.join(src, one)
                if one == "messages.jsonl":
                    mv.move(path_, os.path.join(where, "inbox", one))
                elif one == "uploads" and os.path.isdir(path_):
                    _drain(mv, path_, os.path.join(where, "uploads"),
                           lambda r: aside("inbox/uploads/" + r))
                else:
                    mv.move(path_, aside("inbox/" + one))
            mv.rmdir(src)
        elif name == "annotations" and isdir:
            for one in _listing(src):
                path_ = os.path.join(src, one)
                if one.endswith(".dir.png"):
                    mv.move(path_, os.path.join(keep, name, one))
                    out["kept"].append("%s/%s" % (name, one))
                elif CARD_INK.match(one):
                    mv.move(path_, os.path.join(where, name, one))
                elif one.startswith("doc-") and not mv.exists(
                        os.path.join(home, INK, one)):
                    mv.move(path_, os.path.join(home, INK, one))
                else:
                    mv.move(path_, aside("%s/%s" % (name, one)))
            mv.rmdir(src)
        elif name == "marked" and isdir:
            _drain(mv, src, os.path.join(home, MATERIALS, "marked"),
                   lambda r: aside("marked/" + r))
        elif name == "missions" and isdir:
            # Colibri task records and their flags are job state; any other
            # mission record is the session's.
            from . import jobs                           # local: heavy
            tasks = [t for _, t in jobs._old_tasks(ws, live=live)]
            for one in _listing(src):
                if any(one == t + ".json" or one.startswith(t + ".task.")
                       for t in tasks):
                    continue
                mv.move(os.path.join(src, one), aside("missions/" + one))
        else:
            mv.move(src, aside(name))

    if "agent.json" in out["kept"]:
        mv.write(os.path.join(where, "agent.json"),
                 _agent(keep if mv.apply else live))
    if carried:
        body = _relink(carried, ws_id, sid)
        mv.write(os.path.join(where, "cards", "%04d-carried-over.md" % (last + 1)),
                 "---\nkind: note\ntitle: %s\n---\n%s\n" % (CARRIED, body))
    out["jobs"] = _import_jobs(mv, live, home, keep)
    _prune(mv, live)
    mv.entry(mapping, ws_id, sid)
    out["left"] = [n for n in _listing(live) if n != "archive"] if mv.apply else []
    return out


def reverse_import(manifest):
    """Undo every change the manifest records, newest first. A manifest may
    hold several imports; all of them are undone. `(undone, problems)`."""
    recs = _jsonl(manifest)
    undone, problems = 0, []
    for rec in reversed(recs):
        op, src, dst = rec.get("op"), rec.get("from"), rec.get("to")
        try:
            if op == "move":
                if os.path.lexists(dst) and not os.path.lexists(src):
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
                    undone += 1
                else:
                    problems.append("move %s -> %s: cannot put it back" % (src, dst))
            elif op == "make":
                if os.path.isdir(dst) and not os.path.islink(dst):
                    # Only empty directories go: whatever was moved in has
                    # been moved out by the records after this one.
                    for here, dirs, _ in os.walk(dst, topdown=False):
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(here, d))
                            except OSError:
                                pass
                    try:
                        os.rmdir(dst)
                        undone += 1
                    except OSError:
                        problems.append("%s is not empty; left in place" % dst)
                elif os.path.lexists(dst):
                    os.remove(dst)
                    undone += 1
            elif op == "rmdir":
                os.makedirs(src, exist_ok=True)
                undone += 1
            elif op == "kept":
                if not os.path.lexists(dst):
                    problems.append("kept copy %s is gone" % dst)
                    continue
                if os.path.isdir(src) and not os.path.islink(src):
                    shutil.rmtree(src)
                elif os.path.lexists(src):
                    os.remove(src)
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst, src)
                undone += 1
            elif op == "entry":
                have = course_repo._read_json(dst)
                if have.pop(rec.get("key"), None) is not None:
                    if have:
                        course_repo._write_json(dst, have)
                    else:
                        os.remove(dst)
                undone += 1
        except OSError as exc:
            problems.append("%s %s -> %s: %s" % (op, src, dst, exc))
    return undone, problems
