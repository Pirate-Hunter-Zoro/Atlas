"""Artifacts: a directory holding `doc.json` = {title, source, sessions, asked_at}.

    create(subject, title, session, ext)   a new one at `<subject>/docs/<slug>/`
                                           (`source=` names its file)
    place(dir, source, title)              doc.json written in place, in an existing tree
    list(root), get(root, id)              every artifact of a subject; one by id
    status(dir)                            writing | done | failed, from mtimes
    delete(root, dir, ...)                 to the trash, its ink with it, one commit

`source` is relative to the artifact's directory. `sessions` lists the session
ids that asked for it. `asked_at` is local `YYYY-MM-DD HH:MM:SS`, or null for a
document placed in a tree nobody asked anything of.

Type comes from the source: a `.tex` whose class is beamer is a deck, any other
`.tex` an article, a `.md` a paper.

Ids. An artifact at `docs/<slug>/` has the id `<slug>`. One placed in place
keeps the id the library's walk gives its source (`library._ident`), so ink
keyed `doc/<id>/p<n>` on it still finds it.
"""

import builtins
import json
import os
import re
import shutil
import time

from . import fenced, gitops, paths, subjects

DOCS = "docs"
DOC_JSON = "doc.json"
WHEN = "%Y-%m-%d %H:%M:%S"
STAMP = "%Y%m%d-%H%M%S"
EXTS = (".tex", ".md")

# `writing.ANN_DOC` allows 40 characters in an id, so a slug longer than that
# is a document nobody can write on.
SLUG_MAX = 40
SLUG_RE = re.compile(r"\A[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?\Z")

# How long an asking session's turn must have been over, with nothing moving,
# before an artifact with no output is "failed".
QUIET = 120

# What built output sits beside a source, by the source's extension.
OUTPUTS = {".tex": (".pdf",), ".md": (".docx", ".pdf")}

# Directories the in-place walk never enters, beyond dot directories, the
# fence and `reading.IGNORE`: a subject's uploads, the sessions store and the
# new artifacts, which are read directly.
SKIP = ("materials", "sessions", DOCS)
MAX_DEPTH = 4


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def _when(said):
    """`asked_at` as epoch seconds, or 0."""
    if isinstance(said, (int, float)):
        return float(said)
    try:
        return time.mktime(time.strptime(str(said or ""), WHEN))
    except (ValueError, OverflowError):
        return 0


def slugify(title):
    """A directory name and an id out of a title: lower case, dashes, 40 at most."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(title or "").lower()).strip("-")
    slug = slug[:SLUG_MAX].strip("-") or "document"
    # A slug that is a fenced name would be a directory the fence refuses.
    if slug in fenced.NEVER:
        slug += "-doc"
    return slug


def _session_id(session):
    """A session id out of an id or a session directory, or None."""
    if not session:
        return None
    said = str(session).rstrip("/")
    return os.path.basename(said) if os.sep in said else said


def subject_root(subject, base=None):
    """The directory of `subject`: a subject id, slug or path. ValueError when
    it is none of those, is the Atlas root, or sits under the fence."""
    if subject and os.path.isdir(str(subject)):
        root = os.path.realpath(str(subject))
    else:
        found = subjects.find(subject, base)
        if not found:
            raise ValueError("no subject %r" % (subject,))
        root = os.path.realpath(found["root"])
    if os.path.isfile(os.path.join(root, "board", "bin", "board")):
        raise ValueError("the Atlas root is not a subject; bind one first")
    if fenced.refused(root):
        raise ValueError("%s is under a fence" % root)
    return root


def type_of(source):
    """`deck`, `article` or `paper`, from the source's extension and class."""
    ext = os.path.splitext(str(source or ""))[1].lower()
    if ext == ".md":
        return "paper"
    from . import build                                  # local: TeX helpers
    return "deck" if build.document_class(source) == "beamer" else "article"


def read(d):
    """doc.json of the artifact at directory `d`, or None."""
    return _read_json(os.path.join(d, DOC_JSON))


def create(subject, title, session=None, ext=".md", base=None, now=None,
           source=None):
    """Make `<subject>/docs/<slug>/doc.json` and return the artifact.

    The source is `<slug><ext>`, or `source` (a file name, such as a session
    write-up's `writeup.tex`), and does not exist yet: whoever asked for it
    writes it. A slug already taken takes `-2`, `-3`, ...; `os.mkdir` claims
    it, so two callers never share one.
    """
    if source is not None:
        source = str(source)
        if os.path.basename(source) != source or source.startswith("."):
            raise ValueError("an artifact's source is a file name, not %r" % source)
        ext = os.path.splitext(source)[1]
    ext = "." + str(ext or "").lstrip(".").lower()
    if ext not in EXTS:
        raise ValueError("an artifact's source is .tex or .md, not %s" % ext)
    root = subject_root(subject, base)
    top = os.path.join(root, DOCS)
    os.makedirs(top, exist_ok=True)
    stem = slugify(title)
    slug, n = stem, 1
    while True:
        try:
            os.mkdir(os.path.join(top, slug))
            break
        except FileExistsError:
            n += 1
            tail = "-%d" % n
            slug = stem[:SLUG_MAX - len(tail)].rstrip("-") + tail
    now = time.time() if now is None else now
    sid = _session_id(session)
    rec = {"title": str(title or "").strip() or slug, "source": source or slug + ext,
           "sessions": [sid] if sid else [],
           "asked_at": time.strftime(WHEN, time.localtime(now))}
    where = os.path.join(top, slug)
    _write_json(os.path.join(where, DOC_JSON), rec)
    return _entry(root, where, rec, slug)


def place(d, source, title, session=None):
    """Write doc.json in place in an existing tree, so the document keeps its
    directory and its id. `source` is a path inside `d`, absolute or relative
    to it. An existing doc.json keeps its sessions and asked_at."""
    d = os.path.realpath(d)
    full = source if os.path.isabs(str(source)) else os.path.join(d, str(source))
    full = os.path.realpath(full)
    rel = os.path.relpath(full, d)
    if rel.startswith("..") or os.path.isabs(rel):
        raise ValueError("%s is not inside %s" % (source, d))
    if os.path.splitext(full)[1].lower() not in EXTS:
        raise ValueError("an artifact's source is .tex or .md, not %s" % source)
    rec = read(d) or {}
    sessions = rec.get("sessions") if isinstance(rec.get("sessions"), builtins.list) else []
    sid = _session_id(session)
    if sid and sid not in sessions:
        sessions.append(sid)
    out = {"title": str(title or "").strip() or os.path.splitext(
               os.path.basename(full))[0],
           "source": rel.replace(os.sep, "/"), "sessions": sessions,
           "asked_at": rec.get("asked_at")}
    _write_json(os.path.join(d, DOC_JSON), out)
    return out


def _own(root, d):
    """Is `d` a new artifact's own directory, `<root>/docs/<slug>/`?"""
    rel = os.path.relpath(d, root).replace(os.sep, "/").split("/")
    return len(rel) == 2 and rel[0] == DOCS


def _entry(root, d, rec, ident=None):
    source = str(rec.get("source") or "")
    path = os.path.normpath(os.path.join(d, source)) if source else ""
    own = _own(root, d)
    if ident is None:
        if own:
            ident = os.path.basename(d)
        else:
            from .course import library                 # local: library imports this
            src_rel = os.path.relpath(os.path.dirname(path), root) if path else "."
            ident = library._ident(src_rel, os.path.splitext(
                os.path.basename(path))[0], set())
    sessions = rec.get("sessions")
    return {"id": ident, "dir": d,
            "rel": os.path.relpath(d, root).replace(os.sep, "/"),
            "title": str(rec.get("title") or ident), "source": source,
            "path": path, "sessions": sessions if isinstance(sessions, builtins.list) else [],
            "asked_at": rec.get("asked_at"), "own": own,
            "type": type_of(path) if path else ""}


def list(root):                                              # noqa: A001
    """Every artifact of the subject at `root`: `docs/*/` by name, then the
    ones placed in place, in walk order. Fenced paths are never listed."""
    from .course import reading                          # local: a heavy import
    root = os.path.realpath(root)
    out = []
    top = os.path.join(root, DOCS)
    try:
        names = sorted(os.listdir(top))
    except OSError:
        names = []
    for name in names:
        d = os.path.join(top, name)
        if not SLUG_RE.match(name) or fenced.refused(name):
            continue
        rec = read(d)
        if rec:
            out.append(_entry(root, d, rec))
    for here, dirs, files in os.walk(root):
        rel = os.path.relpath(here, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = sorted(x for x in dirs if not x.startswith(".")
                         and x not in reading.IGNORE and not fenced.refused(x)
                         and not (depth == 0 and x in SKIP))
        if depth >= MAX_DEPTH:
            dirs[:] = []
        if rel == "." or DOC_JSON not in files or fenced.refused(rel):
            continue
        rec = read(here)
        if rec and rec.get("source"):
            out.append(_entry(root, here, rec))
    return out


def get(root, ident):
    """The artifact with this id, or None. An id, never a path."""
    ident = str(ident or "").strip().lower()
    if not SLUG_RE.match(ident):
        return None
    d = os.path.join(os.path.realpath(root), DOCS, ident)
    rec = read(d) if not fenced.refused(ident) else None
    if rec:
        return _entry(os.path.realpath(root), d, rec)
    for one in list(root):
        if one["id"] == ident:
            return one
    return None


def for_session(root, sid):
    """The artifacts of the subject at `root` whose doc.json lists `sid`."""
    return [a for a in list(root) if sid in a["sessions"]]


def outputs(path):
    """The built files beside a source that exist, newest first."""
    stem, ext = os.path.splitext(path)
    got = [stem + o for o in OUTPUTS.get(ext.lower(), ()) if os.path.isfile(stem + o)]
    return sorted(got, key=_mtime, reverse=True)


def _running(session_dir):
    """Is a turn running or queued in this session? agent.json saying
    `working` or owing a message, or an unread inbox line."""
    agent = _read_json(os.path.join(session_dir, "agent.json")) or {}
    if agent.get("state") == "working" or agent.get("owed"):
        return True
    try:
        with open(os.path.join(session_dir, "inbox", "messages.jsonl"), "r",
                  encoding="utf-8") as fh:
            for line in fh:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if isinstance(m, dict) and m.get("read") is False:
                    return True
    except OSError:
        pass
    return False


def status(d, now=None, base=None, session_dir=None):
    """`writing`, `done` or `failed` for the artifact at `d`, or "" without one.

    done     the source and its newest built output are both newer than asked_at
    failed   not done, the asking session's turn is over, and nothing in the
             artifact or that session's agent.json moved for `QUIET` seconds
    writing  otherwise

    Nothing asked (asked_at null) is done. `session_dir` stands in for the
    asking session when doc.json names none (a workspace's `live/`).
    """
    rec = read(d)
    if not rec:
        return ""
    asked = _when(rec.get("asked_at"))
    if not asked:
        return "done"
    source = os.path.join(d, str(rec.get("source") or ""))
    built = outputs(source)
    if _mtime(source) > asked and built and _mtime(built[0]) > asked:
        return "done"
    now = time.time() if now is None else now
    asking = [s for s in (rec.get("sessions") or []) if isinstance(s, str)]
    last = asked
    where = session_dir
    if asking:
        from . import sessions                          # local: sessions imports this
        where = sessions.path(asking[-1], base) or where
    if where and os.path.isdir(where):
        if _running(where):
            return "writing"
        last = max(last, _mtime(os.path.join(where, "agent.json")))
    for here, _, files in os.walk(d):
        for n in files:
            last = max(last, _mtime(os.path.join(here, n)))
    return "failed" if now - last >= QUIET else "writing"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
def ink_files(ink_dir, idents):
    """The files in `ink_dir` holding ink keyed `doc/<id>/p<n>` for an id in
    `idents` (`sessions._ink_of`, which checks each name against
    `writing.ann_file`)."""
    from . import sessions                              # local: sessions imports this
    out = []
    for ident in sorted(set(idents or [])):
        out += [os.path.join(ink_dir, name)
                for name, _key, _ext in sessions._ink_of(ink_dir, ident)]
    return out


def _trash(now, name):
    stamp = time.strftime(STAMP, time.localtime(now))
    dest = os.path.join(paths.TRASH, stamp, name)
    n = 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(paths.TRASH, "%s-%d" % (stamp, n), name)
    os.makedirs(dest)
    return dest


def _git_top(path):
    code, out = gitops._git(path, "rev-parse", "--show-toplevel")
    return os.path.realpath(out) if code == 0 and out else ""


def delete(root, d, idents=None, ink_dirs=None, now=None):
    """Delete the artifact at `d` in the subject at `root`.

    Its own directory (`docs/<slug>/`) goes to the trash whole. One placed in
    place shares its directory with other work, so only doc.json and the
    files named after its source's stem go. The ink keyed on any of `idents`
    (default: the artifact's id) in each of `ink_dirs` (default:
    `<root>/.ink`) goes with it, into the same trash directory. The tracked
    files that left are removed in one gitops commit.

    `{ok, said, trash, ink, committed}`. A fenced path is refused before
    anything moves, with `fenced` set.
    """
    root = os.path.realpath(root)
    d = os.path.realpath(d)
    rel = os.path.relpath(d, root)
    if rel.startswith("..") or rel == ".":
        return {"ok": False, "said": "%s is not an artifact of %s" % (d, root)}
    if fenced.refused(rel) or fenced.refused(root):
        return {"ok": False, "fenced": True,
                "said": "%s is under a fence; nothing was deleted" % rel}
    rec = read(d)
    if not rec:
        return {"ok": False, "said": "%s holds no doc.json" % rel}
    art = _entry(root, d, rec)
    now = time.time() if now is None else now
    top = _git_top(root)
    if art["own"]:
        leaving = [d]
    else:
        stem = os.path.splitext(os.path.basename(art["path"]))[0]
        here = os.path.dirname(art["path"]) or d
        leaving = [os.path.join(d, DOC_JSON)] + sorted(
            os.path.join(here, n) for n in os.listdir(here)
            if os.path.splitext(n)[0] == stem
            and os.path.isfile(os.path.join(here, n)))
    tracked = []
    if top:
        rels = [os.path.relpath(p, top) for p in leaving]
        code, out = gitops._git(top, "ls-files", "--", *rels)
        tracked = sorted(set(l for l in out.splitlines() if l.strip())) if code == 0 else []
    dest = _trash(now, art["rel"].replace("/", "-"))
    for p in leaving:
        shutil.move(p, os.path.join(dest, os.path.basename(p)))
    gone = []
    from . import sessions                              # local: sessions imports this
    dirs = ink_dirs if ink_dirs is not None else [os.path.join(root, sessions.INK)]
    for ink_dir in dirs:
        found = ink_files(ink_dir, idents or [art["id"]])
        if found:
            keep = os.path.join(dest, ".ink")
            os.makedirs(keep, exist_ok=True)
            for p in found:
                shutil.move(p, os.path.join(keep, os.path.basename(p)))
            gone += found
    said = ["moved %s to %s" % (art["rel"], dest)]
    if gone:
        said.append("took %d ink file%s with it" % (len(gone), "" if len(gone) == 1 else "s"))
    committed = False
    ok = True
    if tracked:
        subject = os.path.relpath(root, top).replace(os.sep, "/")
        ok, out = gitops.commit(top, tracked, "%s: delete %s" % (subject, art["rel"]))
        committed = ok and "committed:" in out
        said.append(out)
    return {"ok": ok, "said": "\n".join(said), "trash": dest, "ink": len(gone),
            "committed": committed, "id": art["id"]}
