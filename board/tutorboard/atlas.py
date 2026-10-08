"""The Atlas tree: its families, and shims over `subjects`.

`subjects` is the one answer to "which courses and projects exist": every
non-dot directory directly under `courses/` or `projects/` (and, until T29,
`research/` and `practice/`), with no marker and no registry. `workspaces`,
`find`, `family_of` and `identify` here are shims over it that keep the record
shape their importers read, `{id, family, family_name, dir, root}`. T50
deletes this module.

`families`, `trees` and `find_tree` still read `atlas.json`, which names and
orders the families and marks the vendor and tool ones.
"""

import json
import os

from . import paths, subjects


# `atlas.json` is read on nearly every payload and the payload is polled four
# times a second. It is a few hundred bytes and it changes about once a year.
_CACHE = {"key": None, "root": None, "families": {}}

def root():
    """The repository root -- the directory holding `atlas.json`.

    Three answers, in order, and the last two are the same answer for two
    different layouts:

    1. `TUTORBOARD_COURSES`, which is how a test says "this tree, not this
       machine's". One variable, one meaning, everywhere -- it used to mean
       "the directory the courses are siblings in" and it now means "the
       repository root", which is the same sentence about a different shape.
    2. Whichever ancestor of the tool holds `atlas.json`. The tool lives at
       `Atlas/board`, so this is one step up, but it is walked rather than
       assumed: nothing should break if the board is ever vendored deeper.
    3. The tool's parent directory. That is the OLD flat layout, where courses
       were siblings of Tutor-Board, and it is the fallback rather than an
       error because a machine that has not pulled the move yet should keep
       teaching rather than stop.
    """
    said = os.environ.get("TUTORBOARD_COURSES")
    key = said or ""
    if _CACHE["key"] == key and _CACHE["root"]:
        return _CACHE["root"]
    if said:
        found = os.path.realpath(os.path.expanduser(said))
    else:
        found = None
        here = paths.TOOL
        for _ in range(6):
            if os.path.isfile(os.path.join(here, "atlas.json")):
                found = here
                break
            up = os.path.dirname(here)
            if up == here:
                break
            here = up
        if not found:
            found = os.path.dirname(paths.TOOL)
    _CACHE["key"] = key
    _CACHE["root"] = found
    return found


def families(base=None):
    """The families, in the order the front door draws them.

    `base` is for the one caller that has an explicit root rather than this
    machine's: `tutor`'s `courses_dir` configuration key, which a person may
    legitimately point somewhere else. Everything else asks `root()`.

    A tree with no `atlas.json` -- the old flat layout, or a test's fake --
    has ONE nameless family whose directory is the root itself. That is not a
    special case bolted on; it is what makes every loop below work unchanged
    against both shapes, so there is one discovery path to get right rather
    than two to keep in step.
    """
    base = os.path.realpath(os.path.expanduser(base)) if base else root()
    hit = _CACHE["families"].get(base)
    if hit is not None:
        return hit
    out = []
    try:
        with open(os.path.join(base, "atlas.json"), "r", encoding="utf-8") as fh:
            said = (json.load(fh) or {}).get("families") or []
    except (OSError, ValueError):
        said = []
    for fam in said:
        if not isinstance(fam, dict) or not fam.get("id"):
            continue
        ident = str(fam["id"])
        out.append({
            "id": ident,
            "name": fam.get("name") or ident.replace("-", " ").title(),
            "blurb": fam.get("blurb") or "",
            # WHAT A SITTING IN THIS FAMILY IS FOR when nothing below it says
            # otherwise. Carried through as written and checked where it is used
            # -- `course/config.aim_for` owns the precedence and is the only
            # thing that decides what an unrecognised word means.
            "aim": str(fam.get("aim") or ""),
            "vendor": bool(fam.get("vendor")),
            "tool": bool(fam.get("tool")),
            "dir": os.path.join(base, ident),
        })
    if not out:
        out = [{"id": "", "name": "", "blurb": "", "aim": "", "vendor": False,
                "tool": False, "dir": base}]
    _CACHE["families"][base] = out
    return out


def _base(base):
    return os.path.realpath(os.path.expanduser(base)) if base else root()


def _record(parent, slug, where, names):
    """A subject in the record shape `workspaces` has always returned."""
    return {"id": "%s/%s" % (parent, slug), "family": parent,
            "family_name": names.get(parent)
            or parent.replace("-", " ").title(),
            "dir": slug, "root": where}


# The flat layout: a tree with no `atlas.json`, its workspaces directly under
# it and marked by one of these. Only bin/tutor's `courses_dir` and the test
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
    """Every subject, in `atlas.json` family order, then by name.

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
    decision. `atlas.json`'s prose used to make one claim out of two: the
    family was skipped *because* nothing in it is the person's to be graded on.
    Grading and tracing are different claims, and conflating them made reading
    how colibrì works impossible for a reason that was about homework.

    So they are split. A vendor tree is NOT a workspace -- nothing is handed in
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
    """Drop the cache. For a test that moves the tree under the process."""
    _CACHE["key"] = None
    _CACHE["root"] = None
    _CACHE["families"] = {}
