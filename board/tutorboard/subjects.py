"""Subjects: every directory directly under `courses/` or `projects/`.

Two kinds, and the kind is the parent directory. There is no registry and no
marker file: `mkdir projects/X` is a project, empty or not, because a file that
must be edited when a directory is made is the registry this system refuses.
Dot directories are skipped.

`research/` and `practice/` still read as projects until they merge into
`projects/` (T29), which also drops them from `DIRS`.

Runs on the cluster's python3 (3.7): no walrus, no `match`, no builtin
generics at runtime.
"""

import os

from . import paths


# Parent directory -> kind, in the order subjects are listed.
DIRS = (
    ("courses", "course"),
    ("research", "project"),
    ("projects", "project"),
    ("practice", "project"),
)
KINDS = ("course", "project")


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
    `DIRS`) that no longer exists falls back to its slug, so
    `research/PSYCH-ASR` finds `projects/PSYCH-ASR` once it moved (shim; T55
    removes it).
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
    if len(parts) == 2 and parts[0] in dict(DIRS) and parts[1]:
        for one in every:
            if one[2] == parts[1]:
                return _record(*one)
    return None


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
