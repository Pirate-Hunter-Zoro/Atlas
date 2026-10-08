"""The session store: `sessions/<YYYYMMDD-HHMMSS>/` under the Atlas root.

    new(title=None)   a fresh session, unbound, in teach mode
    end(id)           set `ended`, and commit what the session leaves behind
    reopen(id)        clear `ended`
    delete(id)        move the directory to the trash
    bind(id, subject) set `subject`, with a non-waking `[bind]` line
    file(id, upload)  move an upload into the bound subject, ink and all
    all(), get(id), path(id), repo(id)

A session is Mac-only and ignored (`/sessions/` in .gitignore, and the audit
refuses any path under it). It persists until the owner ends it: nothing but
`end` sets `ended`. An id is matched against `ID_RE` and never joined onto a
path unchecked.

session.json = {id, title, subject, mode, opened, ended, writeup, seen, code,
view}. `subject` is a subject id (`courses/X`, `projects/Y`) or null;
`writeup` is a source path relative to the Atlas root, or null. Times are
local `YYYY-MM-DD HH:MM:SS`.
"""

import hashlib
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


def new(title=None, base=None, now=None):
    """Create a session and return its session.json.

    The id is the local time to the second; a clash takes `-2`, `-3`, ...
    `os.mkdir` claims the name, so two callers in one second get two
    sessions and neither touches the other.
    """
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
           "writeup": None, "seen": 0, "code": None, "view": "board"}
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


def delete(sid, base=None, now=None):
    """Move session `sid` to `<trash>/<stamp>/<id>` and return that path."""
    where = _need(sid, base)
    now = time.time() if now is None else now
    stamp = time.strftime(STAMP, time.localtime(now))
    dest = os.path.join(paths.TRASH, stamp, os.path.basename(where))
    n = 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(paths.TRASH, "%s-%d" % (stamp, n), os.path.basename(where))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(where, dest)
    return dest


def _line(where, text, signal, now=None, **extra):
    """Append a line to the session's inbox that wakes nothing: it is written
    already read, so `board wait` never hands it to a turn, while `board inbox
    --all` and the recap still show it."""
    now = time.time() if now is None else now
    rec = {"t": now, "iso": time.strftime(WHEN, time.localtime(now)),
           "from": "board", "text": text, "signal": signal, "read": True}
    rec.update(extra)
    inbox = os.path.join(where, "inbox")
    os.makedirs(inbox, exist_ok=True)
    with open(os.path.join(inbox, "messages.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


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


# ---------------------------------------------------------------------------
# filing an upload, and the ink that follows it
# ---------------------------------------------------------------------------
INK_FILE = re.compile(r"\Adoc-(.+)-p(\d{1,4})-[0-9a-f]{8}\Z")
INK_EXTS = (".dir.png", ".png", ".json", ".gone")


def ink_ident(rel):
    """The ink id of a file at `rel`, its path relative to where it is kept:
    `uploads/<name>` in a session, `materials/<name>` (or any path) in a
    subject. Lower-case letters, digits and dashes, at most 40, so a key
    `doc/<id>/p<n>` passes `writing.ANN_DOC`. A path too long for that keeps
    31 characters and a digest of the whole path, so two paths never share
    an id."""
    rel = str(rel or "").replace(os.sep, "/").strip("/")
    stem = os.path.splitext(rel)[0]
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "doc"
    if len(slug) <= 40:
        return slug
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8]
    return "%s-%s" % (slug[:31].rstrip("-"), digest)


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

    The upload's ink moves with it, from the session's `annotations/` to
    `<subject>/.ink/`, re-keyed from the upload's ink id to the new path's
    (`ink_ident`). Refused: an unbound session, an upload not in `uploads/`,
    a destination outside the subject, hidden or fenced, or already taken,
    and ink already in `.ink/` under the new keys. Nothing is committed: a
    filed upload is third-party or the owner's raw material (D1).

    Returns {from, to, subject, keys}: `to` is relative to the subject, and
    `keys` maps each old ink key to its new one.
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

    notes = os.path.join(where, "annotations")
    ink = os.path.join(found["root"], INK)
    old, new = ink_ident("uploads/" + name), ink_ident(rel)
    from .server.routes import writing                 # local: avoids a cycle
    moves = []
    for fname, key, ext in _ink_of(notes, old):
        page = key.rsplit("/p", 1)[1]
        nkey = "doc/%s/p%s" % (new, page)
        target = os.path.join(ink, writing.ann_file(nkey) + ext)
        if os.path.lexists(target):
            raise Refused("%s already holds ink for %s; it belongs to no file "
                          "there now -- delete it, or file under another name"
                          % (target, nkey))
        moves.append((os.path.join(notes, fname), target, key, nkey, ext))

    os.makedirs(os.path.dirname(full), exist_ok=True)
    shutil.move(src, full)
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
    return {"from": "uploads/" + name, "to": rel, "subject": found["id"],
            "keys": keys}


def current():
    """The id of the session `TUTORBOARD_SESSION` names, or ""."""
    said = os.environ.get("TUTORBOARD_SESSION") or ""
    if said and course_repo.is_stored(said):
        return os.path.basename(os.path.normpath(said))
    return ""


def show(rec):
    """session.json as the CLI prints it."""
    return json.dumps(rec, indent=2)
