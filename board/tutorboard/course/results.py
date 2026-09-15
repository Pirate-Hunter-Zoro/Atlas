"""results.py -- the figures a pipeline made, so one can go on the glass.

`reading.py` finds the documents a project was WRITTEN with: a deck, a
walkthrough, a paper. This is the other thing a working project has, and it had
no route to the board at all.

    `results/counterfactual_pipeline/<contrast>/propensity_by_arm.png` exists
    and cannot be put in a card. `reading.py` offers PDFs only and refuses
    `results` by name. `routes/pages.py` serves the web directory, a compiled
    TikZ figure, the lesson inbox and the answers -- nothing serves an image out
    of the workspace. So the only route a figure had to a lesson was somebody
    copying it into `live/inbox/uploads/`, which is a second copy of a file that
    is rebuilt by the next job.

A FIGURE IS NOT A `figure`. On this board `/figure/` is TikZ the tutor wrote and
the board compiled; this is output somebody's pipeline produced. Two different
things, two names, and the reason to be strict about it is that they are served
by adjacent routes.

Four constraints, and they are the design rather than decoration.

**An id, never a path.** `reading.find`'s rule: what arrives from a browser is
compared against what discovery found, and a miss is a miss. A query parameter
carrying a repo-relative path is a traversal waiting to be written, and it buys
nothing -- the board already knows where every figure is.

**An allowlist, with the fence behind it.** `fenced.RESULT_DIRS` is where a
workspace keeps output; `fenced.NEVER` is what nothing may look inside. The
second is checked on top of the first, which is what makes adding a name to the
allowlist safe.

**Bounded.** TRD-EHR's results tree holds 676 PNGs. A drawer is not a file
manager and a payload is not a directory listing.

**Not cached by the service worker.** A figure is rebuilt at the SAME name by
the next job, so a cached one served under that name is last week's result
wearing this week's label. `sw.js` sends this route to the network always, for
the same reason it does `/download/`, `/view/` and `/paper/`.

Standard library only, like everything else.
"""

import hashlib
import os
import re
import time

from .. import fenced

# Where to look, and nowhere else. The allowlist, in the order a person would
# look in them.
LOOK_IN = fenced.RESULT_DIRS

# What a figure is. RASTER ONLY, and deliberately: the board's vector path is
# `/figure/`, which compiles TikZ the tutor wrote and is served as
# `image/svg+xml`. An SVG out of a workspace would be a second thing to reason
# about on a route whose whole job is to show a picture, and every figure these
# pipelines write is a PNG.
SUFFIXES = (".png", ".jpg", ".jpeg")

# A 300-byte PNG is an axis and no data -- a plot that failed, or a spacer.
MIN_BYTES = 1000

# A drawer is not a file manager. `reading.MAX_DOCS` is 24 for this reason and a
# figure drawer needs it more, not less.
MAX_FIGURES = 24

# How deep under a result directory to look. `results/counterfactual_pipeline/
# bupropion_vs_ssri/propensity_by_arm.png` is three, and a figure buried deeper
# than that is an intermediate rather than a result.
MAX_DEPTH = 3

# And a stop on the walk itself, because the cap above is a cap on what is
# OFFERED. A tree with a hundred thousand files in it must not be walked four
# times a second, or once, and the payload is not the place to find that out.
MAX_SEEN = 5000

# The payload is rebuilt on every change and polled four times a second. Same
# rule as `reading.documents`, `walk.units` and `plan.steps`, and the same
# reason: a job writes a figure when it finishes, which is not on a
# quarter-second boundary.
CACHE_SECONDS = 30
_cache = {}


def _pretty(rel):
    """What to call a figure in a drawer.

    The filename, unpunctuated -- `propensity_by_arm.png` becomes `propensity by
    arm`, which is what its author calls it out loud.
    """
    stem = os.path.splitext(os.path.basename(rel))[0]
    return re.sub(r"[_-]+", " ", stem).strip() or "figure"


def _where(rel):
    """The directory a figure sits in, as a person would say it.

    THE HALF THAT TELLS THREE OF THEM APART. A pipeline writes
    `propensity_by_arm.png` once per contrast, under the same name every time, so
    the filename alone offers three identical rows in a drawer and no way to
    know which arm pair each one is about.
    """
    parts = rel.replace("\\", "/").split("/")[:-1]
    return "/".join(parts[1:]) if len(parts) > 1 else "/".join(parts)


# How long an id may be, and how much of one is the digest below. Long enough
# that a real path fits whole -- `counterfactual_pipeline/bupropion_vs_ssri/
# propensity_by_arm.png` is 59 characters of slug -- because the id is what a
# tutor reads in its briefing and writes into a card.
MAX_ID = 80
STAMP = 8


def ident(rel):
    """A short, stable name for one figure, safe to put in a URL.

    FROM THE WHOLE PATH, AND WITH A DIGEST OF IT ON THE END. Two properties are
    wanted and the obvious id has neither.

    It has to be UNIQUE. The filename is the one thing that is not unique here:
    a pipeline writes `propensity_by_arm.png` once per contrast, under the same
    name each time, so an id from the basename would be one id naming three
    figures -- two a card cannot address and one it addresses by accident.

    And it has to be STABLE, because a card is kept, exported and read again
    next month. So no counter and no positional suffix: `-2` handed out by
    walking a directory in date order is a different figure once a fourth
    contrast lands. The digest is of the path, which is what the figure IS, so
    the answer does not depend on what else was found beside it -- and a long
    path that has to be trimmed for length is still uniquely named afterwards.

    The result-directory name is dropped from the front: it is one of five, the
    drawer shows it under `where`, and the characters are better spent on the
    part that says which figure this is.
    """
    rel = rel.replace("\\", "/")
    stamp = hashlib.sha1(rel.encode("utf-8", "replace")).hexdigest()[:STAMP]
    parts = os.path.splitext(rel)[0].split("/")
    said = "/".join(parts[1:]) if len(parts) > 1 else rel
    out = re.sub(r"[^a-z0-9]+", "-", said.lower()).strip("-")
    # Trimmed from the FRONT when it has to be trimmed at all: the figure's own
    # name is at the end of the path, and the directories above it are the part
    # a reader can lose. The digest is what keeps the trimmed id unique.
    out = out[-(MAX_ID - STAMP - 1):].strip("-")
    return "%s-%s" % (out, stamp) if out else "figure-%s" % stamp


def _walk(root):
    """Every figure under this workspace's result directories. Bounded, twice.

    The allowlist decides which trees are walked at all, `fenced.refused`
    decides which directories inside them are descended into, and `MAX_SEEN`
    stops the walk whatever either of them says -- because the first two are
    judgements about a tree and the third is the promise that a payload returns.
    """
    found, seen = [], 0
    root = os.path.realpath(root)
    for name in LOOK_IN:
        if fenced.refused(name):
            continue
        top = os.path.join(root, name)
        if not os.path.isdir(top):
            continue
        for here, dirs, files in os.walk(top):
            rel_dir = os.path.relpath(here, top)
            depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
            if depth >= MAX_DEPTH:
                dirs[:] = []
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and not fenced.refused(d))
            for f in sorted(files):
                seen += 1
                if seen > MAX_SEEN:
                    return found
                if f.startswith(".") or not f.lower().endswith(SUFFIXES):
                    continue
                path = os.path.join(here, f)
                rel = os.path.relpath(path, root)
                if fenced.refused(rel):
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size < MIN_BYTES:
                    continue
                found.append((rel.replace(os.sep, "/"), st.st_mtime, st.st_size))
    return found


def _figures(root):
    """NEWEST FIRST, which is the ordering a results tree actually wants.

    `reading.documents` leads with what the README names, because a document is
    chosen. A figure is not: it is what the last job produced, and the one
    somebody is asking about is the one that has just changed.
    """
    rows = sorted(_walk(root), key=lambda r: (-r[1], r[0]))
    seen, out = set(), []
    for rel, at, size in rows:
        got = ident(rel)
        if got in seen:
            # Two paths with one id, which takes a sha1 collision in eight hex
            # characters. Dropped rather than aliased: an id that names two
            # figures is a card showing the wrong one.
            continue
        seen.add(got)
        out.append({
            "id": got,
            "name": _pretty(rel),
            "where": _where(rel),
            "rel": rel,
            "at": at,
            "size": size,
        })
        if len(out) >= MAX_FIGURES:
            break
    return out


def figures(root):
    """Every figure this workspace can be shown, newest first. Remembered 30s."""
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        got = _figures(key)
    except OSError:
        got = []
    _cache[key] = (time.time(), got)
    return got


def find(root, ident_wanted):
    """The figure with this id, as `(path, name)`, or `(None, None)`.

    The whole check, and it is `reading.find`'s: nothing constructs a path from
    a request. An id is compared against the ids of the figures this workspace
    actually offers, the path is the one discovery already found, and the fence
    is asked once more before the file is opened -- because this is the function
    that turns a name from a browser into bytes.
    """
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    root = os.path.realpath(root)
    for fig in figures(root):
        if fig["id"] != wanted:
            continue
        if fenced.refused(fig["rel"]):
            return None, None
        target = os.path.realpath(os.path.join(root, fig["rel"]))
        if not target.startswith(root + os.sep) or not os.path.isfile(target):
            return None, None
        label = fig["name"]
        if fig["where"]:
            label = "%s — %s" % (label, fig["where"])
        return target, label
    return None, None


def status(repo):
    """What the board shows in the drawer, and nothing more.

    None for a workspace with no results, so the drawer does not offer an empty
    group -- the same answer `reading.status` gives a course with no documents.
    """
    try:
        found = figures(repo.root)
    except Exception:                                        # noqa: BLE001
        return None
    if not found:
        return None
    out = []
    for fig in found:
        one = dict(fig)
        one.pop("rel", None)          # the board addresses a figure by its id
        one["iso"] = time.strftime("%Y-%m-%d", time.localtime(fig["at"])) \
            if fig["at"] else ""
        out.append(one)
    return {"figures": out}
