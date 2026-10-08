"""The Atlas tree: its families, and shims over `subjects`.

`subjects` is the one answer to "which courses and projects exist": every
non-dot directory directly under `courses/` or `projects/` (and, until T29,
`research/` and `practice/`), with no marker and no registry. `workspaces`,
`find`, `family_of` and `identify` here are shims over it that keep the record
shape their importers read, `{id, family, family_name, dir, root}`. T50
deletes this module.

`FAMILIES` names and orders the parent directories and marks the vendor and
tool ones. It is code, not a file: there is no per-machine list to edit.
"""

import os

from . import paths, subjects


# The families, in the order the front door draws them. `vendor` marks
# somebody else's trees, read and never taught in; `tool` marks the board's own
# source.
FAMILIES = (
    {"id": "courses", "name": "Courses",
     "blurb": "Graduate coursework, taught chapter by chapter."},
    {"id": "research", "name": "Research",
     "blurb": "The projects that become papers."},
    {"id": "projects", "name": "Projects",
     "blurb": "Infrastructure the research runs on, and the tools that write "
              "it up."},
    {"id": "practice", "name": "Practice",
     "blurb": "Kept sharp: algorithms, and proofs a machine checks."},
    {"id": "board", "name": "The board", "tool": True,
     "blurb": "The tool that maps, teaches and writes up everything above."},
    {"id": "vendor", "name": "Vendor", "vendor": True,
     "blurb": "Pulled, not written. Tracked by pointer at a commit."},
)


def root():
    """The Atlas root: `subjects.root()`, the parent of `board/`.

    `TUTORBOARD_COURSES` overrides it; that is how a test says "this tree".
    """
    return subjects.root()


def families(base=None):
    """The families, in the order the front door draws them.

    `base` is for the one caller that has an explicit root rather than this
    machine's: `tutor`'s `courses_dir` configuration key. Everything else asks
    `root()`.

    A tree holding none of the family directories -- the old flat layout, or a
    test's fake -- has ONE nameless family whose directory is the root itself,
    so every loop below works unchanged against both shapes.
    """
    base = _base(base)
    if not any(os.path.isdir(os.path.join(base, f["id"]))
               for f in FAMILIES if not f.get("tool")):
        return [{"id": "", "name": "", "blurb": "", "vendor": False,
                 "tool": False, "dir": base}]
    return [{"id": f["id"], "name": f["name"], "blurb": f["blurb"],
             "vendor": bool(f.get("vendor")),
             "tool": bool(f.get("tool")), "dir": os.path.join(base, f["id"])}
            for f in FAMILIES]


def _base(base):
    return os.path.realpath(os.path.expanduser(base)) if base else root()


def _record(parent, slug, where, names):
    """A subject in the record shape `workspaces` has always returned."""
    return {"id": "%s/%s" % (parent, slug), "family": parent,
            "family_name": names.get(parent)
            or parent.replace("-", " ").title(),
            "dir": slug, "root": where}


# The flat layout: a tree with no family directory, its workspaces directly
# under it and marked by one of these. Only bin/tutor's `courses_dir` and the test
# fixtures built for it are shaped so; this goes with atlas.py (T50).
FLAT_MARKERS = ("tutorboard.json", "AI_INSTRUCTIONS.md", "live")


def _flat(base):
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    out = []
    for name in names:
        here = os.path.join(base, name)
        if (name.startswith(".") or not os.path.isdir(here)
                or paths.same_dir(here, paths.TOOL)
                or not any(os.path.exists(os.path.join(here, m))
                           for m in FLAT_MARKERS)):
            continue
        out.append({"id": name, "family": "", "family_name": "", "dir": name,
                    "root": here})
    return out


def workspaces(base=None):
    """Every subject, in `FAMILIES` order, then by name.

    Shim over `subjects.walk`, in the record shape importers read: `id`
    (`family/name`), `family` (the parent directory), `family_name`, `dir`
    (the bare directory name) and `root`. A flat tree reads as `_flat`.
    """
    base = _base(base)
    fams = families(base)
    if not fams[0]["id"]:
        return _flat(base)
    order = dict((f["id"], i) for i, f in enumerate(fams))
    names = dict((f["id"], f["name"]) for f in fams if f["id"])
    found = subjects.walk(base)
    found.sort(key=lambda one: order.get(one[0], len(order)))
    return [_record(parent, slug, where, names)
            for parent, _kind, slug, where in found]


# ---------------------------------------------------------------------------
# the other list: source that is read and never handed in to
# ---------------------------------------------------------------------------
def trees(base=None):
    """Every vendor tree -- somebody else's repository, read but never taught in.

    A SECOND LIST rather than a flag on `workspaces`, and that is the whole
    decision: grading and tracing are different claims. A vendor tree is NOT a workspace -- nothing is handed in
    to it, no board serves it, no card, write-up, homework or push belongs to
    it, and `workspaces` still skips the family outright, which is what several
    callers depend on. It IS source, and source can be walked through and
    drawn: `course/walk.units` and `course/map.shape` take a root and neither
    of them asks whether anybody is graded on it.

    The shape of a record is the shape `workspaces` returns, so a caller that
    only wants a name and a root does not care which list it came from.
    """
    out = []
    for fam in families(base):
        if not fam["vendor"]:
            continue
        try:
            names = sorted(os.listdir(fam["dir"]))
        except OSError:
            continue
        for name in names:
            if name.startswith("."):
                continue
            here = os.path.join(fam["dir"], name)
            if not os.path.isdir(here):
                continue
            try:
                # A submodule nobody has pulled is an empty directory, and an
                # empty directory drawn as a tree is a card with nothing behind
                # it.
                if not os.listdir(here):
                    continue
            except OSError:
                continue
            out.append({
                "id": ("%s/%s" % (fam["id"], name)) if fam["id"] else name,
                "family": fam["id"],
                "family_name": fam["name"],
                "dir": name,
                "root": here,
            })
    return out


def find_tree(ident, base=None):
    """One vendor tree, by `vendor/name` or by bare directory name -- or None.

    The same rule as `find` and for the same reason: a name arriving from a
    request is looked up in what discovery found and is never constructed into
    a path. A miss is a miss.
    """
    if not ident:
        return None
    ident = str(ident).strip().strip("/")
    here = trees(base)
    for t in here:
        if t["id"] == ident:
            return t
    for t in here:
        if t["dir"] == ident or paths.same_dir(t["root"], ident):
            return t
    return None


def find(ident, base=None):
    """One workspace by `family/name`, bare directory name or root, or None.

    Shim over `subjects.find`, including its fallback from a moved qualified
    id to its slug.
    """
    base = _base(base)
    if not families(base)[0]["id"]:
        ident = str(ident).strip().strip("/")
        here = _flat(base)
        for w in here:
            if w["dir"] == ident or paths.same_dir(w["root"], ident):
                return w
        return None
    hit = subjects.find(ident, base)
    if not hit:
        return None
    parent = hit["id"].split("/", 1)[0]
    names = dict((f["id"], f["name"]) for f in families(base) if f["id"])
    return _record(parent, hit["slug"], hit["root"], names)


def family_of(path, base=None):
    """The subject parent directory a path sits directly in, or ""."""
    base = _base(base)
    parent = os.path.dirname(os.path.realpath(path).rstrip(os.sep))
    fam = os.path.basename(parent)
    if fam in dict(subjects.DIRS) and paths.same_dir(os.path.dirname(parent),
                                                      base):
        return fam
    return ""


def identify(path):
    """The `family/name` of a directory, whether or not it still exists.

    `find` asks what the repository HAS; this asks what a path IS, so a board
    running in a renamed or removed workspace can still say where it is.
    """
    real = os.path.realpath(path)
    fam = family_of(real)
    name = os.path.basename(real.rstrip(os.sep))
    return ("%s/%s" % (fam, name)) if fam else name


def forget():
    """Nothing is cached any more; kept for the tests that call it."""
