"""Subjects: every directory directly under `courses/` or `projects/`.

Two kinds, and the kind is the parent directory. There is no registry and no
marker file: `mkdir projects/X` is a project, empty or not, because a file that
must be edited when a directory is made is the registry this system refuses.
Dot directories are skipped.

`research/` and `practice/` are the legacy parents, merged into `projects/`.
No subject is listed there; `find` still resolves a legacy id to its slug.

`create(ident, phi)` makes a subject: the directory, tutorboard.json and a
TUTOR.md skeleton (plus the PHI ignore stanza for a patient-data project), in
one gitops commit.

Runs on the cluster's python3 (3.7): no walrus, no `match`, no builtin
generics at runtime.
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

# The parents merged into `projects/`. A qualified id under one of them
# (`research/PSYCH-ASR`) still finds its subject by slug (shim; T55 removes it).
LEGACY = ("research", "practice")

# TUTOR.md's sections, in order. `board memo <section>` writes one of them.
TUTOR_SECTIONS = ("Where things are", "Now", "Open decisions", "Done recently")

# A patient-data project's own .gitignore: what never leaves the machine.
PHI_IGNORE = ("/phi/", "/results/", ".env")


class Refused(ValueError):
    """A subject that cannot be made as asked; the message says why."""


def root():
    """The Atlas root: the parent of `board/`, from this file's own path.

    `TUTORBOARD_COURSES` overrides it; that is how a test says "this tree".
    """
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
    """`(parent, kind, slug, root)` for every subject, without reading a file.

    The cheap listing under `all()`, for callers polled often that need no name.
    """
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
    """One subject by qualified id, slug or root, else None.

    Matched only against `walk()`, the listing under `all()`; nothing is
    built from `ident`. A qualified id (`<parent>/<slug>`, parent one of
    `DIRS` or `LEGACY`) that does not exist falls back to its slug, so
    `research/PSYCH-ASR` finds `projects/PSYCH-ASR` (shim; T55 removes it).
    """
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
    parts = ident.split("/")
    if len(parts) == 2 and parts[1] and (parts[0] in dict(DIRS)
                                         or parts[0] in LEGACY):
        for one in every:
            if one[2] == parts[1]:
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
    commit it. `(record, ok, said)`: `record` is the `all()` record.

    The name is slugified into the directory. Refused (`Refused`): an
    absolute path, a `..` or `.` component, anything but exactly
    `<courses|projects>/<name>`, a slug some subject already has, a course
    asked to hold patient data, and a project with no answer for `phi`.

    tutorboard.json holds {name, phi}: `false` for a course; the owner's
    answer for a project, whose `true` also writes a .gitignore with
    `PHI_IGNORE`. TUTOR.md is the skeleton of `TUTOR_SECTIONS`. One gitops
    commit holds all of it; a commit that fails takes the directory away
    again, so asking twice is safe.
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
