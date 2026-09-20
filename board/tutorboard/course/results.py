"""results.py -- what a pipeline produced, on the glass and on a page.

TWO QUESTIONS, ONE WALK. `figures`/`find`/`status` answer *which figure goes in
this card*: the newest two dozen, pictures only, flat. `produced`/`browse`/
`table` answer *show me what this workspace has made*: every result directory as
a group, the tables beside the figures, and a table read back as rows for a page
that cannot open a file. The allowlist, the fence, the depth, the stop and the
id are shared, because two walks of one tree are two answers that will disagree.

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

**Bounded, at every surface, and each one says what it dropped.** TRD-EHR's
results tree holds 628 figures and 233 tables across 98 directories. A drawer is
not a file manager, a payload is not a directory listing, and a cap that says
nothing reads as *this is all there is*.

**Not cached by the service worker.** A figure is rebuilt at the SAME name by
the next job, so a cached one served under that name is last week's result
wearing this week's label. `sw.js` sends this route to the network always, for
the same reason it does `/download/`, `/view/` and `/paper/`.

Standard library only, like everything else.
"""

import csv
import hashlib
import json
import os
import re
import time

from .. import atlas, fenced

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


def _walk(root, suffixes=SUFFIXES, min_bytes=MIN_BYTES):
    """Every figure under this workspace's result directories. Bounded, twice.

    `suffixes` and `min_bytes` are arguments because the browse surface below
    wants the same tree with the tables in it, and ONE WALK IS THE POINT: the
    allowlist, the fence and the stop are decided here and nowhere else. A
    second copy of this loop for a second kind of file is the drift
    `fenced.py`'s own docstring is about.

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
                if f.startswith(".") or not f.lower().endswith(suffixes):
                    continue
                path = os.path.join(here, f)
                rel = os.path.relpath(path, root)
                if fenced.refused(rel):
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size < min_bytes:
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

    AGAINST THE INDEX RATHER THAN THE DRAWER'S TWO DOZEN. `MAX_FIGURES` is a cap
    on what is OFFERED to a drawer; the library's results page offers hundreds
    out of the same walk, and a route that resolved only the drawer's slice
    would serve the newest 24 and 404 the rest of a page it is painting.
    """
    return _bytes_of(root, ident_wanted, "figure")


def _bytes_of(root, ident_wanted, kind):
    wanted = str(ident_wanted or "").strip().lower()
    if not wanted:
        return None, None
    root = os.path.realpath(root)
    rec = index(root).get(wanted)
    if not rec or rec["kind"] != kind:
        return None, None
    if fenced.refused(rec["rel"]):
        return None, None
    target = os.path.realpath(os.path.join(root, rec["rel"]))
    if not target.startswith(root + os.sep) or not os.path.isfile(target):
        return None, None
    label = rec["name"]
    if rec["where"]:
        label = "%s — %s" % (label, rec["where"])
    return target, label


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


# ---------------------------------------------------------------------------
# BROWSING THEM -- a different question from putting one in a card
# ---------------------------------------------------------------------------
# The drawer above answers *which figure goes on the glass in this card*, and
# its numbers are that question's: the newest two dozen, pictures only, in one
# flat list. This answers *show me what this workspace has produced*, and every
# one of those numbers is wrong for it.
#
#     "figure `neighbor_count_sweep.png` and four tables are in
#     `RESULTS_DIR/neighbor_count_sweep/`, mirrored into `results/`."
#
# That is a finished mission's card. The figure is named, the tables are named,
# and the only way to look at any of it was a terminal -- which is the one thing
# this board exists so that nobody has to open.
#
# THREE THINGS DIFFER FROM THE DRAWER, AND NOTHING ELSE DOES. The allowlist, the
# fence, the depth, the stop on the walk and the id are `_walk` and `ident`
# above, unchanged and shared.
#
# **The tables come too.** Four of the five artifacts that mission wrote are
# tables, and a surface that shows the picture and hides the numbers has shown
# the smaller half. What a table is on disk is what these pipelines really write
# -- `sweep_curve.csv`, `sweep_summary.json` -- rather than a format anybody
# chose.
#
# **The DIRECTORY is the group.** `scopes._results` already groups this way and
# says why: a pipeline writes `propensity_by_arm.png` once per contrast under
# the same name every time, so the directory is what tells three of them apart
# and is what somebody means when they say *this result*. Sixty-eight groups
# read; six hundred rows do not.
#
# **It is capped where it is read, and it SAYS what it dropped.** A silent cap
# reads as *this is all there is*, which is `scopes.offered`'s reason for
# carrying its own count and is the same reason here.

# What a table is, in the order a person would look in them. Read, never
# executed and never parsed as anything but text: `.json` is loaded to be
# re-printed and nothing acts on what is in it.
TABLES = (".csv", ".json", ".md", ".txt")

# An empty file is not a table. One byte, because a table's floor is *it has
# something in it* -- `MIN_BYTES` above is a judgement about a PNG that turned
# out to be an empty axis, and there is no equivalent for a CSV.
MIN_TABLE_BYTES = 1

# How many result directories are offered, and how many rows inside one.
# TRD-EHR's tree holds 68 directories and 628 figures, so the first of these is
# above what really exists and the second is well below it: a directory of
# thirty ROC curves is a list somebody scrolls, and a page that tried to draw
# six hundred pictures at once is a page an iPad gives up on.
MAX_GROUPS = 120
MAX_IN_GROUP = 60

# What a table is read back as. Rows first, because `sweep_curve.csv` is 2.9 MB
# and a hundred thousand rows -- read to the cap and stopped, never loaded.
MAX_ROWS = 300
MAX_COLS = 40
MAX_CELL = 200

# How far past the cap the count goes before it gives up and says *at least*.
# A stream costs one row of memory whatever the file is, but it still costs the
# read: a million rows is a fifth of a second and a billion is not.
MAX_SCAN = 200000

# And a floor under the file itself, for the kinds that have to be read whole
# before anything can be said about them. A JSON document is `json.load`ed; a
# markdown one is shown as it stands.
MAX_TEXT_BYTES = 2000000
MAX_TEXT_CHARS = 200000

_made = {}


def _record(rel, at, size):
    """One result, as a row: what it is, what it is called, where it came from."""
    ext = os.path.splitext(rel)[1].lower()
    pic = ext in SUFFIXES
    return {
        "id": ident(rel),
        "name": _pretty(rel),
        "where": _where(rel),
        "rel": rel,
        "at": at,
        "size": size,
        "kind": "figure" if pic else "table",
        "format": ext.lstrip("."),
        "iso": time.strftime("%Y-%m-%d", time.localtime(at)) if at else "",
        # The filename as it stands, because the CARD NAMES IT. A mission that
        # ends "figure `neighbor_count_sweep.png` is in ..." has told the reader
        # a string, and the row they are looking for is the one that string is
        # in -- `_pretty` has already taken the underscores and the suffix out.
        "file": os.path.basename(rel),
    }


def _produced(root):
    """Every result here, indexed by id and grouped by directory.

    `(index, payload)`. The index is everything the walk found, which is what
    `find` resolves an id against; the payload is what a page is offered, which
    is capped. They are built together because they are one walk, and a second
    walk to answer the same question twice is how two answers start disagreeing
    about which figures exist.
    """
    rows = sorted(_walk(root, SUFFIXES + TABLES, MIN_TABLE_BYTES),
                  key=lambda r: (-r[1], r[0]))
    index, groups, order = {}, {}, []
    figs = tabs = 0
    for rel, at, size in rows:
        pic = os.path.splitext(rel)[1].lower() in SUFFIXES
        # The size floor is per KIND, which is why the walk was given the lower
        # of the two: a 300-byte PNG is a plot that failed, and a 300-byte CSV
        # is three rows of numbers.
        if pic and size < MIN_BYTES:
            continue
        rec = _record(rel, at, size)
        if rec["id"] in index:
            # One id naming two files, which takes a sha1 collision in eight hex
            # characters. Dropped rather than aliased, for `_figures`' reason.
            continue
        index[rec["id"]] = rec
        where = rec["where"]
        if where not in groups:
            groups[where] = []
            order.append(where)
        groups[where].append(rec)
        figs += 1 if pic else 0
        tabs += 0 if pic else 1

    out, dropped = [], 0
    for where in order[:MAX_GROUPS]:
        rows_here = groups[where]
        # Newest first is right for the GROUPS -- the result somebody is asking
        # about is the one that just landed. Inside one, it is wrong: a job
        # writes its whole directory in the same few seconds, so mtime order
        # there is arbitrary and a name is not.
        kept = sorted(rows_here, key=lambda r: (r["kind"] != "figure",
                                                r["name"]))[:MAX_IN_GROUP]
        out.append({
            "where": where or "results",
            "at": max(r["at"] for r in rows_here),
            "iso": max(rows_here, key=lambda r: r["at"])["iso"],
            "figures": [_said(r) for r in kept if r["kind"] == "figure"],
            "tables": [_said(r) for r in kept if r["kind"] == "table"],
            "more": max(0, len(rows_here) - len(kept)),
        })
    dropped = max(0, len(order) - MAX_GROUPS)
    return index, {"groups": out, "more": dropped,
                   "figures": figs, "tables": tabs}


def _said(rec):
    """One row, as the page is allowed to see it -- never with the path in it.

    `status` drops `rel` for the drawer's rows and this is the same rule: the
    board addresses a result by its id, so a page that was handed a path has
    been handed a thing it must never send back.
    """
    one = dict(rec)
    one.pop("rel", None)
    return one


def _both(root):
    key = os.path.realpath(root)
    hit = _made.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        got = _produced(key)
    except OSError:
        got = ({}, {"groups": [], "more": 0, "figures": 0, "tables": 0})
    _made[key] = (time.time(), got)
    return got


def index(root):
    """Every result this workspace has, by id. Remembered for `CACHE_SECONDS`."""
    return _both(root)[0]


def produced(root):
    """What the library's results page draws: groups, and what was left off."""
    return _both(root)[1]


def forget():
    """Drop both caches. For a test, and for a job that has just written one."""
    _cache.clear()
    _made.clear()


def browse(repo):
    """The results page's whole payload, or a sentence saying there are none.

    A WORKSPACE WITH NO RESULTS SAYS SO. An empty list painted as an empty box
    is a page that looks broken, and the two reasons it can be empty are
    different enough to be worth telling apart: a course has no results
    directory at all, and a research workspace whose output is fenced has one
    that nothing may look inside.
    """
    root = repo.root
    try:
        got = produced(root)
    except Exception:                                        # noqa: BLE001
        got = {"groups": [], "more": 0, "figures": 0, "tables": 0}
    out = dict(got)
    out["ok"] = True
    out["workspace"] = atlas.identify(root)
    # WHERE IT LOOKED, SAID OUT LOUD. "Nothing here" is only useful beside the
    # list of places that were looked in, and the allowlist is that list.
    out["looked"] = [n for n in LOOK_IN
                     if os.path.isdir(os.path.join(root, n))]
    # AND WHAT IT REFUSED TO LOOK IN, BY NAME. A workspace holding session
    # content must not be able to look like a workspace holding nothing.
    out["fenced"] = list(fenced.holds(root))
    if not out["groups"]:
        out["why"] = _nothing(out)
    return out


def _nothing(out):
    """Why this workspace's results page is empty.

    WHERE IT LOOKED FIRST, AND WHAT IT REFUSED SECOND, because they are
    different facts and a page that gives only one of them is misleading either
    way round. "No results directory" said about a workspace holding a fenced
    one reads as *there is nothing here*; the fence said on its own reads as
    *that is the only reason*, which is wrong for a workspace that also simply
    has not run anything yet.
    """
    if not out["looked"]:
        said = ("This workspace has no results directory. A job that writes "
                "one into %s appears here, with no registration of any kind."
                % ", ".join("`%s/`" % n for n in LOOK_IN))
    else:
        said = ("There is a %s directory here, and nothing in it yet that this "
                "board can show: a figure has to be a %s of at least %d bytes, "
                "and a table one of %s."
                % (", ".join("`%s/`" % n for n in out["looked"]),
                   " or ".join(SUFFIXES), MIN_BYTES, " or ".join(TABLES)))
    if out["fenced"]:
        said += (" %s also holds %s. Nothing on this board looks inside it -- "
                 "it is session content, and the refusal is by name in "
                 "`tutorboard/fenced.py` -- so nothing in there is listed here "
                 "or anywhere else."
                 % (out["workspace"],
                    ", ".join("`%s/`" % n for n in out["fenced"])))
    return said


# ---------------------------------------------------------------------------
# reading one table back, for a page that cannot open a file
# ---------------------------------------------------------------------------
# A FIGURE IS BYTES AND A TABLE IS NOT. `/result/<id>` hands a PNG straight to
# an `<img>` and there is nothing to decide. A CSV handed to a browser the same
# way is a download an iPad puts somewhere nobody can find, so the numbers are
# read HERE, to the cap, and sent as rows the page draws.
#
# READ TO THE CAP RATHER THAN LOADED. `sweep_curve.csv` is 2.9 MB and a hundred
# thousand rows. `csv.reader` over an open handle stops where it is told to; a
# `read()` first does not.
def table(root, ident_wanted):
    """One table, read back as rows or as text.

    An id, never a path -- `_bytes_of` is the same lookup `/result/` uses, with
    the kind it will answer for changed. A miss is a miss.
    """
    target, label = _bytes_of(root, ident_wanted, "table")
    if not target:
        return {"ok": False, "why": "none",
                "detail": "This workspace has no result by that name."}
    rec = index(os.path.realpath(root)).get(
        str(ident_wanted or "").strip().lower()) or {}
    out = {"ok": True, "id": rec.get("id") or "", "label": label,
           "name": rec.get("name") or "", "where": rec.get("where") or "",
           "file": rec.get("file") or "", "format": rec.get("format") or "",
           "size": rec.get("size") or 0, "iso": rec.get("iso") or ""}
    try:
        if out["format"] == "csv":
            out.update(_rows(target))
        else:
            out.update(_text(target))
    except (OSError, UnicodeError, ValueError) as exc:
        return {"ok": False, "why": "unreadable",
                "detail": "%s could not be read: %s" % (out["file"], exc)}
    return out


def _rows(path):
    """The head of a CSV, as columns and rows. Nothing is loaded whole.

    `csv.reader` over an open handle is a stream, so the memory is one row
    whatever the file is. The BOUND is on how far it reads: the rest of the file
    is counted rather than kept, because "300 of 101,889 rows" is the sentence
    that stops somebody wondering what they are looking at -- and the count
    stops at `MAX_SCAN`, past which the page says *at least*.
    """
    columns, rows, more, capped = [], [], 0, False
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        for n, row in enumerate(csv.reader(fh)):
            if n == 0:
                columns = [str(c)[:MAX_CELL] for c in row[:MAX_COLS]]
                continue
            if len(rows) >= MAX_ROWS:
                more += 1
                if more >= MAX_SCAN:
                    capped = True
                    break
                continue
            rows.append([str(c)[:MAX_CELL] for c in row[:MAX_COLS]])
    return {"shape": "rows", "columns": columns, "rows": rows,
            "more": more, "capped": capped}


def _text(path):
    """A JSON, markdown or plain-text table, as text. Bounded twice."""
    size = os.path.getsize(path)
    if size > MAX_TEXT_BYTES:
        return {"shape": "text", "text": "", "more": 0,
                "why": "big",
                "detail": ("This file is %.1f MB, which is too much to put on "
                           "a page. It is at the path the row shows."
                           % (size / 1000000.0))}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        said = fh.read(MAX_TEXT_CHARS + 1)
    more = max(0, len(said) - MAX_TEXT_CHARS)
    said = said[:MAX_TEXT_CHARS]
    if path.lower().endswith(".json") and not more:
        # Re-printed rather than reformatted: a pipeline's JSON is already
        # indented, and one that is not is unreadable as one line. Nothing acts
        # on what is in it -- this is `json.dumps` of what `json.loads` read.
        try:
            said = json.dumps(json.loads(said), indent=2, sort_keys=False)
        except ValueError:
            pass
    return {"shape": "text", "text": said, "more": more}
