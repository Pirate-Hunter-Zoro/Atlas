"""The session store: `sessions/<YYYYMMDD-HHMMSS>/` under the Atlas root.

    new(title=None)   a fresh session, unbound, in teach mode
    end(id)           set `ended`, and commit what the session leaves behind
    reopen(id)        clear `ended`
    delete(id)        move the directory to the trash
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

import json
import os
import re
import shutil
import time

from . import gitops, paths, subjects
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
    """Directories under `<subject>/docs/` whose doc.json lists this session,
    relative to the Atlas root."""
    docs = os.path.join(base, subject, "docs")
    try:
        names = sorted(os.listdir(docs))
    except OSError:
        return []
    out = []
    for name in names:
        doc = course_repo._read_json(os.path.join(docs, name, "doc.json"))
        listed = doc.get("sessions")
        if isinstance(listed, list) and sid in listed:
            out.append("%s/docs/%s" % (subject, name))
    return out


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


def current():
    """The id of the session `TUTORBOARD_SESSION` names, or ""."""
    said = os.environ.get("TUTORBOARD_SESSION") or ""
    if said and course_repo.is_stored(said):
        return os.path.basename(os.path.normpath(said))
    return ""


def show(rec):
    """session.json as the CLI prints it."""
    return json.dumps(rec, indent=2)
