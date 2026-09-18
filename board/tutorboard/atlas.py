"""The one repository, its families, and the workspaces inside it.

Everything used to be a sibling of the tool: `os.path.dirname(paths.TOOL)` was
the whole of discovery, and a course was a directory sitting next to
Tutor-Board. Eleven repositories are now one, two levels deep -- a FAMILY
(`courses`, `research`, `projects`, `practice`) holding a WORKSPACE (one course
or one project, which the board treats identically, which is why there is one
word for both).

So one nested loop replaces one flat one, and this module is where that loop
lives. Every other module asks here rather than taking a `dirname`, because
there is now exactly one right answer to "where is the repository root" and it
is worth having exactly one place that knows it.

**Nothing is registered.** `atlas.json` names and orders the families, says
which of them are somebody else's work -- which decides whether work can be
handed in to them, not whether they can be read; `trees` is the other half --
and gives each a default style for a sitting nobody chose one for (`aim`; `course/config.aim_for` resolves it). It does NOT list the workspaces: a
second-level directory holding `tutorboard.json`, `AI_INSTRUCTIONS.md` or
`live/` IS one, found by looking. A file that has to be edited when a directory
is made is the registry this system refuses to have -- and the thing that makes
`mkdir courses/Topology` the whole of starting a new course.
"""

import json
import os

from . import paths


# `atlas.json` is read on nearly every payload and the payload is polled four
# times a second. It is a few hundred bytes and it changes about once a year.
_CACHE = {"key": None, "root": None, "families": {}}

# A directory is a workspace if it says so in one of three ways. Kept exactly as
# it was when they were siblings: a repository counts by what is IN it, not by
# what any list says about it.
MARKERS = ("tutorboard.json", "AI_INSTRUCTIONS.md")


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


def is_workspace(path):
    """Does this directory hold a course or a project?

    The same test the board has always used, unchanged: `tutorboard.json`,
    `AI_INSTRUCTIONS.md`, or a `live/` directory. The tool itself is excluded
    by realpath rather than by name -- this home is reachable under two
    spellings and a string comparison of two paths is a bug waiting to happen.
    """
    if not os.path.isdir(path):
        return False
    if paths.same_dir(path, paths.TOOL):
        return False
    if os.path.isdir(os.path.join(path, "live")):
        return True
    return any(os.path.isfile(os.path.join(path, m)) for m in MARKERS)


def workspaces(base=None):
    """Every workspace in the repository, in family order then alphabetical.

    Each is a dict with `id` (`family/name`, which is what the address grammar
    spells and what `chosen.json` records), `family`, `dir` (the bare directory
    name, which is what a port is derived from) and `root`.

    Vendor families are skipped outright, and that is a claim about HANDING
    WORK IN rather than about reading: `vendor/colibri` is somebody else's
    repository, pulled and not written, so nothing in it is the person's to be
    taught or graded on and no board serves it. It is still source, and `trees`
    is where it is listed for walking through and drawing. A `tool` family is
    skipped too -- the board is what does the offering, not one of the things
    offered.
    """
    out = []
    for fam in families(base):
        if fam["vendor"] or fam["tool"]:
            continue
        try:
            names = sorted(os.listdir(fam["dir"]))
        except OSError:
            continue
        for name in names:
            if name.startswith("."):
                continue
            here = os.path.join(fam["dir"], name)
            if not is_workspace(here):
                continue
            out.append({
                "id": ("%s/%s" % (fam["id"], name)) if fam["id"] else name,
                "family": fam["id"],
                "family_name": fam["name"],
                "dir": name,
                "root": here,
            })
    return out


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
    """One workspace, by `family/name`, by bare directory name, or by root path.

    A bare name is accepted because a port, a `.board.json` and four years of
    typing all spell a workspace by its directory alone, and the directory
    names are unique across the repository. Ambiguity is resolved in favour of
    the qualified spelling, so `courses/Probability` always beats a future
    `practice/Probability` when the qualified form is what was asked for.
    """
    if not ident:
        return None
    ident = str(ident).strip().strip("/")
    here = workspaces(base)
    for w in here:
        if w["id"] == ident:
            return w
    for w in here:
        if w["dir"] == ident or paths.same_dir(w["root"], ident):
            return w
    return None


def family_of(path, base=None):
    """Which family a directory sits in, or "" if it sits in none."""
    for fam in families(base):
        if not fam["id"]:
            continue
        try:
            if paths.same_dir(os.path.dirname(os.path.realpath(path)), fam["dir"]):
                return fam["id"]
        except OSError:
            continue
    return ""


def identify(path):
    """The `family/name` of a directory, whether or not it is discoverable.

    `find` asks what the repository HAS; this asks what a path IS, and the two
    differ for exactly one caller that matters: a board already running in a
    workspace that has since been renamed or removed still has to be able to
    say where it is.
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
