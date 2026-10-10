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

A session is Mac-only and ignored (`/sessions/`; the audit refuses any path
under it) and persists until `end`. session.json = {id, title, subject,
mode, opened, ended, writeup, seen, code, view}; `subject` is a subject id
or null, `writeup` a source path from the Atlas root or null, times local
`YYYY-MM-DD HH:MM:SS`. `code` is the cluster coding session as the Mac last
heard it ({ref, sha, paths, step, subject, prev, seen, at}); while set,
`gitops.commit` refuses the held paths on main and `board push` goes to the
ref.

The constraint: an id is matched against `ID_RE`, never joined onto a path
unchecked.
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

# Directories every session starts with; files appear when written.
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
    """Create a session and return its session.json. The id is the local
    second (`-2`, ... on a clash); `os.mkdir` claims it, so two callers never
    share one. `view` is one of VIEWS."""
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
    """End session `sid`: set `ended`, then commit the bound subject's
    TUTOR.md and every artifact listing the session. `(record, ok, said)`.
    Ending again keeps the time and retries the commit."""
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
    """Bind session `sid` to `subject` (matched against `subjects.all()`).
    `(record, changed)`. Appends a non-waking `[bind] <id>` line; nothing is
    filed or moved (D21). Rebinding the same subject is silent."""
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
    """The ink id of a file at `rel` (relative to where it is kept), by the
    library's id rule (`library._ident`), so ink keys match library ids;
    `file` asks `library.ident_map` where two files collide."""
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
    `materials/` by default, or `dest` inside the subject (a directory or a
    new name). Its ink moves to `<subject>/.ink/`, re-keyed to the file's
    new library id. Refused: unbound, not an upload, a destination outside
    the subject, hidden, fenced or taken, or ink already under the new keys.
    Nothing is committed (D1).

    Returns {from, to, subject, keys, doc}: `to` relative to the subject,
    `keys` old ink key to new, `doc` the file's ink id now.
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
    # The library's id for the file where it now is, else the rule's.
    new = library.ident_map(found["root"]).get(os.path.realpath(full)) \
        or ink_ident(rel)
    moves = []
    try:
        # Ink drawn while bound is already in `.ink/`, earlier ink in the
        # session; `.ink/` first, so it wins a key held in both.
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
    """What the home screen shows beyond session.json: `{last_card: {id,
    title} or None, new_cards}`, `new_cards` counted after `seen`. Only the
    newest card's file is opened."""
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
