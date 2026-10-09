"""Subjects: every directory directly under `courses/` or `projects/`.

The kind is the parent directory. `create(ident, phi)` makes the directory,
tutorboard.json and a TUTOR.md skeleton (plus the PHI ignore stanza for a
patient-data project) in one gitops commit; `delete` moves one to the trash.

The constraint: no registry and no marker file, so `mkdir projects/X` is a
project; a file that must be edited when a directory is made is the registry
this system refuses. Runs on the cluster's python3 (3.7): no walrus, no
`match`, no builtin generics at runtime.
"""

import json
import os
import re
import shutil

from . import paths


# Parent directory -> kind, in the order subjects are listed.
DIRS = (
    ("courses", "course"),
    ("projects", "project"),
)
KINDS = ("course", "project")

# Where `create` makes a subject.
CREATE = DIRS

# TUTOR.md's sections, in order. `board memo <section>` writes one of them.
TUTOR_SECTIONS = ("Where things are", "Now", "Open decisions", "Done recently")

# A patient-data project's own .gitignore: what never leaves the machine.
PHI_IGNORE = ("/phi/", "/results/", ".env")


class Refused(ValueError):
    """A subject that cannot be made as asked; the message says why."""


def root():
    """The Atlas root, the parent of `board/`; `TUTORBOARD_COURSES` overrides
    it for tests."""
    said = os.environ.get("TUTORBOARD_COURSES")
    if said:
        return os.path.realpath(os.path.expanduser(said))
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.realpath(__file__))))


def _base(base):
    return os.path.realpath(os.path.expanduser(base)) if base else root()


def _name(where, slug):
    """`name` from tutorboard.json, else the slug with dashes as spaces."""
    from .course import config                               # local: a cycle
    try:
        said = config.read_config(where).get("name")
    except Exception:                                        # noqa: BLE001
        said = None
    return str(said) if said else slug.replace("-", " ")


def walk(base=None):
    """`(parent, kind, slug, root)` for every subject, reading no file."""
    base = _base(base)
    out = []
    for parent, kind in DIRS:
        here = os.path.join(base, parent)
        try:
            names = sorted(os.listdir(here))
        except OSError:
            continue
        for slug in names:
            if slug.startswith("."):
                continue
            where = os.path.join(here, slug)
            if os.path.isdir(where):
                out.append((parent, kind, slug, where))
    return out


def all(base=None):                                          # noqa: A001
    """Every subject, as `{id, kind, slug, name, root}`.

    `id` is `<parent>/<slug>`, `kind` is `course` or `project`, `slug` is the
    directory name, `root` its path. Ordered by `DIRS`, then by name.
    """
    return [_record(*one) for one in walk(base)]


def _record(parent, kind, slug, where):
    return {"id": "%s/%s" % (parent, slug), "kind": kind, "slug": slug,
            "name": _name(where, slug), "root": where}


def find(ident, base=None):
    """One subject by qualified id, slug or root, else None. Matched only
    against `walk()`; `<parent>/<slug>` under any other parent finds nothing."""
    if not ident:
        return None
    ident = str(ident).strip().rstrip("/")
    every = walk(base)
    for one in every:
        if "%s/%s" % (one[0], one[2]) == ident.lstrip("/"):
            return _record(*one)
    for one in every:
        if one[2] == ident or paths.same_dir(one[3], ident):
            return _record(*one)
    return None


def roots(base=None):
    """Every subject's directory, in `walk` order."""
    return [one[3] for one in walk(base)]


def identify(path, base=None):
    """`<parent>/<slug>` for a directory directly under `courses/` or
    `projects/`, whether or not it still exists; else its bare name."""
    real = os.path.realpath(path).rstrip(os.sep)
    parent = os.path.dirname(real)
    name = os.path.basename(real)
    fam = os.path.basename(parent)
    if fam in dict(DIRS) and paths.same_dir(os.path.dirname(parent),
                                            _base(base)):
        return "%s/%s" % (fam, name)
    return name


def prefix(path, base=None):
    """What leads a commit message made from `path`: the subject's slug (the
    directory's name) for a subject, else the bare name `identify` gives."""
    return identify(path, base).split("/")[-1]


def kind_of(path, base=None):
    """`course` or `project` for a path inside a subject, else ""."""
    base = _base(base)
    try:
        rel = os.path.relpath(os.path.realpath(path), base)
    except ValueError:
        return ""
    parts = rel.replace(os.sep, "/").split("/")
    if len(parts) < 2 or parts[0] == ".." or not parts[1] \
            or parts[1].startswith("."):
        return ""
    return dict(DIRS).get(parts[0], "")


def slugify(name):
    """A directory name from a subject's name: letters and digits, with one
    dash for every run of anything else. Case is kept (`Galois-Theory`)."""
    return re.sub(r"[^A-Za-z0-9]+", "-", str(name or "")).strip("-")


def _tutor_md(name):
    out = ["# %s" % name, ""]
    for section in TUTOR_SECTIONS:
        out += ["## %s" % section, ""]
    return "\n".join(out)


def create(ident, phi=None, base=None):
    """Make the subject `ident` (`courses/<name>` or `projects/<name>`) and
    commit it. `(record, ok, said)`, `record` as `all()` gives it.

    Refused: an absolute path, `.` or `..`, anything but exactly
    `<courses|projects>/<name>`, a taken slug, a course holding patient data,
    a project with no `phi` answer. tutorboard.json holds {name, phi}; `phi`
    true also writes `PHI_IGNORE`. A failed commit removes the directory, so
    asking twice is safe.
    """
    from . import gitops                                     # local: light here
    base = _base(base)
    raw = str(ident or "").strip()
    if not raw:
        raise Refused("name the subject: courses/<name> or projects/<name>")
    if os.path.isabs(raw) or raw.startswith("~"):
        raise Refused("%s: a subject is courses/<name> or projects/<name>, "
                      "never an absolute path" % raw)
    parts = raw.replace("\\", "/").rstrip("/").split("/")
    if any(p in ("..", ".") for p in parts):
        raise Refused("%s: no `..` or `.` in a subject's name" % raw)
    if len(parts) != 2 or not parts[1].strip():
        raise Refused("%s: a subject is courses/<name> or projects/<name>" % raw)
    kinds = dict(CREATE)
    if parts[0] not in kinds:
        raise Refused("%s: subjects are made only under courses/ or projects/"
                      % raw)
    kind = kinds[parts[0]]
    name = parts[1].strip()
    slug = slugify(name)
    if not slug:
        raise Refused("%s: the name has no letter or digit to name a "
                      "directory by" % raw)
    for one in walk(base):
        if one[2].lower() == slug.lower():
            raise Refused("%s/%s already exists: a slug names one subject"
                          % (one[0], one[2]))
    if kind == "course":
        if phi:
            raise Refused("a course holds no patient data; make it a project")
        phi = False
    elif phi is None:
        raise Refused("does %s hold patient data? say --phi yes or --phi no"
                      % name)
    phi = bool(phi)

    rel = "%s/%s" % (parts[0], slug)
    where = os.path.join(base, parts[0], slug)
    if os.path.lexists(where):
        raise Refused("%s already exists" % rel)
    os.makedirs(os.path.join(base, parts[0]), exist_ok=True)
    os.mkdir(where)
    made = []

    def put(fname, text):
        with open(os.path.join(where, fname), "w", encoding="utf-8") as fh:
            fh.write(text)
        made.append("%s/%s" % (rel, fname))

    try:
        put("tutorboard.json",
            json.dumps({"name": name, "phi": phi}, indent=2) + "\n")
        if phi:
            put(".gitignore", "\n".join(PHI_IGNORE) + "\n")
        put("TUTOR.md", _tutor_md(name))
    except OSError:
        shutil.rmtree(where, ignore_errors=True)
        raise
    ok, said = gitops.commit(base, made, "%s: a new %s%s" % (
        rel, kind, " that holds patient data" if phi else ""))
    if not ok:
        gitops._git(base, "reset", "-q", "--", *made)
        shutil.rmtree(where, ignore_errors=True)
        return None, False, said
    return _record(parts[0], kind, slug, where), True, said


# ---------------------------------------------------------------------------
# delete, from the iPad
# ---------------------------------------------------------------------------
class Busy(Refused):
    """A delete refused for what the subject is or holds now (409, not 400)."""


def head_phi(base, ident):
    """`phi` as tutorboard.json says it at HEAD: True, False, None for a
    file with no `phi` key, or "" when there is no such file at HEAD."""
    from . import gitops                                     # local: light here
    code, out = gitops._git(base, "show", "HEAD:%s/tutorboard.json" % ident)
    if code != 0:
        return ""
    try:
        said = json.loads(out)
    except ValueError:
        return None
    return said.get("phi") if isinstance(said, dict) else None


def delete_blocker(found, base=None):
    """Why the subject `found` (an `all()` record) may not be deleted now, or
    "". D23: tutorboard.json at HEAD must say `"phi": false` literally. And
    no open session is bound to it, no session holds a coding session on it,
    and no request under it waits for a terminal report."""
    from . import sessions                                   # local: a cycle
    base = _base(base)
    ident = found["id"]
    phi = head_phi(base, ident)
    if phi is not False:
        return ("%s: tutorboard.json at HEAD does not say \"phi\": false (%s), "
                "so it is removed only through a cluster runbook"
                % (ident, "no tutorboard.json at HEAD" if phi == ""
                   else "no phi key" if phi is None else "phi is %s" % json.dumps(phi)))
    for rec in sessions.all(base):
        code = rec.get("code")
        held = isinstance(code, dict) and code.get("subject") == ident
        if rec.get("subject") == ident and not rec.get("ended"):
            return "%s: session %s is open on it; end it first" % (ident, rec["id"])
        if code and (held or rec.get("subject") == ident):
            return ("%s: session %s holds a coding session on it; end that "
                    "first (board code --end)" % (ident, rec["id"]))
    from . import jobs                                       # local: heavy
    try:
        waiting = jobs.outstanding(found["root"])
    except Exception as exc:                                 # noqa: BLE001
        return "%s: its requests could not be read (%s)" % (ident, exc)
    if waiting:
        return ("%s: request %s has no terminal report yet"
                % (ident, waiting[0].get("request") or "?"))
    return ""


def delete(ident, typed, base=None, now=None):
    """Delete the subject `ident` from the iPad: `typed` must equal its slug,
    and `delete_blocker` must allow it. The directory moves to the trash and
    its tracked files leave in one commit; a failed commit puts it back.
    `(trash path, said)`.
    """
    from . import gitops, sessions                           # local: a cycle
    base = _base(base)
    raw = str(ident or "").strip()
    found = None
    for one in walk(base):
        if "%s/%s" % (one[0], one[2]) == raw:
            found = _record(*one)
    if not found:
        raise Refused("no subject %r: name it as courses/<name> or "
                      "projects/<name>" % raw)
    if str(typed or "") != found["slug"]:
        raise Refused("type %s exactly to delete it" % found["slug"])
    why = delete_blocker(found, base)
    if why:
        raise Busy(why)
    rel = found["id"]
    code, out = gitops._git(base, "ls-files", "--", rel)
    tracked = code == 0 and bool(out.strip())
    dest = sessions.trash(rel.replace("/", "-"), now)
    shutil.move(found["root"], dest)
    if not tracked:
        return dest, "moved %s to the trash; nothing of it was tracked" % rel
    ok, said = gitops.commit(base, [rel], "%s: deleted from the iPad" % rel)
    if not ok:
        gitops._git(base, "reset", "-q", "--", rel)
        shutil.move(dest, found["root"])
        raise Refused("not committed, so not deleted: %s" % said)
    return dest, said


# A material: any file under `<subject>/materials/` (ignored, D1).
MATERIALS = "materials"


def materials(root):
    """`[{name, size, at}]` for every file under `<root>/materials/`, newest
    first; `name` is its path below `materials/`. Dot files and anything
    reached through a link that leaves the directory are not listed."""
    top = os.path.join(root, MATERIALS)
    real = os.path.realpath(top)
    out = []
    for here, dirs, files in os.walk(top):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in files:
            if f.startswith("."):
                continue
            p = os.path.join(here, f)
            if not os.path.realpath(p).startswith(real + os.sep):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append({"name": os.path.relpath(p, top).replace(os.sep, "/"),
                        "size": st.st_size, "at": st.st_mtime})
    out.sort(key=lambda m: (-m["at"], m["name"]))
    return out


def delete_material(root, name, idents=(), now=None):
    """Move the material `name` (one of `materials(root)`'s names) and its
    ink to the trash. Its ink is every `.ink/` file keyed on its ink id
    (`sessions.ink_ident`) or on one of `idents`. Nothing is committed for an
    ignored file; one tracked anyway leaves in one commit. `(trash path,
    said)`, or `Refused` for a name that is not one."""
    from . import gitops, sessions                           # local: a cycle
    from .artifacts import ink_files                          # local: a cycle
    name = str(name or "")
    if name not in [m["name"] for m in materials(root)]:
        raise Refused("no material %r here" % name)
    rel = "%s/%s" % (MATERIALS, name)
    full = os.path.join(root, *rel.split("/"))
    dest = sessions.trash(os.path.basename(full), now)
    keys = set(idents or ()) | {sessions.ink_ident(rel)}
    ink = ink_files(os.path.join(root, sessions.INK), keys)
    top = gitops._git(root, "rev-parse", "--show-toplevel")
    top = os.path.realpath(top[1]) if top[0] == 0 and top[1] else ""
    tracked = False
    if top:
        code, out = gitops._git(top, "ls-files", "--", os.path.relpath(full, top))
        tracked = code == 0 and bool(out.strip())
    shutil.move(full, dest)
    if ink:
        keep = os.path.join(os.path.dirname(dest), ".ink")
        os.makedirs(keep, exist_ok=True)
        for p in ink:
            shutil.move(p, os.path.join(keep, os.path.basename(p)))
    said = "moved %s to the trash%s" % (rel, " with %d ink file%s" % (
        len(ink), "" if len(ink) == 1 else "s") if ink else "")
    if tracked:
        ok, out = gitops.commit(top, [os.path.relpath(full, top)],
                                "%s: delete %s" % (prefix(root, top), rel))
        said += "\n" + out
        if not ok:
            raise Refused(said)
    return dest, said
