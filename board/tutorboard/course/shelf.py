"""shelf.py -- every document in a workspace, and which box on the map it is under.

The map is where somebody looks for their own work, and until this existed the
map could not answer. The menu's documents panel offered exactly two -- the last
lesson exported and the last write-up compiled -- which is a record of the last
thing built rather than an inventory, and a course with forty compiled PDFs in
it had thirty-eight of them reachable from nothing.

So the inventory is `library.documents`, and this adds the one thing it does not
know: WHICH BOX. Three rules, all of them read off the path:

    a set        the document IS that set's compiled write-up, or sits inside
                 the set's own directory -- `homework.sets` says where that is
    a chapter    the path starts `chapters/chNN-...`, and NN matches the number
                 on a chapter the syllabus actually lists
    a part       the path starts with the box's own directory

**The join is derived and never written down.** There is no registry, no index
file and no sidecar: a document that moves belongs to a different box on the
next read, and one that is deleted stops existing rather than leaving a record
pointing at nothing. `reading.py` is the register for why -- a fact cannot go
stale and a declaration can, so nothing here is declared.

A document that matches no rule is UNFILED, and that is an answer rather than a
failure. In a code workspace it is every document: they live in `docs/` and
`writeups/`, which are not source boxes, and pretending otherwise would put a
manuscript inside a package that does not contain it.

COURSE MATERIAL THE LIBRARY WILL NOT SHOW. `reading.NOT_OURS` hides a directory
called `reading`, which is right -- it keeps a reference library of other
people's papers out -- and it also hides the twenty textbook splits a course
keeps one per chapter. Three narrow globs of this module's own put those back,
tagged `theirs`, and they are shaped like a course so a code workspace gains
nothing from them.

Standard library only, like everything else.
"""

import glob
import os
import re
import time

from . import homework, library, reading, syllabus
from . import map as course_map
from .. import atlas, fenced

# A shelf is longer than a drawer and it is still not a file manager. Above
# `library.MAX_DOCS` because the three globs below add a course's textbook
# splits and its professor's slides to what the library already found.
MAX_DOCS = 160

# The same clock `library.documents` and `map.shape` keep, and for the same
# reason: the map payload is rebuilt four times a second and this is a walk of a
# repository. A document appears when somebody compiles one, which is not on a
# quarter-second boundary.
CACHE_SECONDS = 30

# COURSE MATERIAL SOMEBODY ELSE WROTE, and exactly three shapes of it. Narrow on
# purpose: `reading.NOT_OURS` is shared with every code workspace on this
# machine and must not move, so what a course needs back is asked for here by a
# pattern only a course matches. A repository of Python gains nothing.
THEIRS = (
    os.path.join("chapters", "*", "reading", "*.pdf"),
    os.path.join("chapters", "*", "lectures", "*.pdf"),
    os.path.join("homework", "*", "assignment", "*.pdf"),
)

# What a document IS, beyond the two the library can tell apart. The library
# reads `\documentclass{beamer}` and calls everything else a paper, which is the
# right answer for a workspace of manuscripts and says nothing useful about a
# course. These are read off the path, which in a course is where the answer is.
KINDS = ("homework", "notes", "paper", "deck", "reading", "transcript",
         "textbook", "scan")

# Which directory name means which kind. First match along the path wins, read
# from the top, so `chapters/ch04-*/homework/handwritten/` is a scan and not a
# write-up.
BY_DIR = (("handwritten", "scan"), ("scans", "scan"), ("scan", "scan"),
          ("reading", "reading"), ("lectures", "reading"),
          ("transcripts", "transcript"), ("textbook", "textbook"),
          ("notes", "notes"))

# A chapter directory, and the number in it. The NUMBER is what this takes: the
# node's id is never rebuilt from it. `map.py:872` rebuilds one and gets it
# wrong -- `ch0*(\d+)` on `ch04` gives `4`, the node is `ch-04`, and ten of
# twenty-one set boxes lost their edge to their chapter. An integer compared
# against the syllabus record a node was made from cannot fail that way.
CHAPTER_DIR = re.compile(r"^chapters/ch0*(\d+)")


def _rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _kind(rel, stem, base, theirs):
    """What this document is, out of its path. One of `KINDS`.

    The set rule in `_place` overrides this with `homework` for a document that
    IS a set's write-up, because that is known rather than inferred.
    """
    if theirs:
        return "reading"
    if base == "deck":
        return "deck"
    parts = [p.lower() for p in rel.split("/")[:-1]]
    for name, kind in BY_DIR:
        if name in parts:
            return kind
    low = stem.lower()
    if "homework" in low or re.match(r"^hw\d", low):
        return "homework"
    if low.endswith("-notes") or low.endswith("_notes"):
        return "notes"
    if "transcript" in low:
        return "transcript"
    return "paper"


def _theirs(rel):
    """Is this one of the three course-shaped globs -- somebody else's sheet?"""
    parts = rel.split("/")
    if len(parts) != 4:
        return False
    head, _unit, folder, name = parts
    if not name.lower().endswith(".pdf"):
        return False
    return ((head == "chapters" and folder in ("reading", "lectures"))
            or (head == "homework" and folder == "assignment"))


# A textbook chapter split is named after the file it was cut into, and `ch04`
# is not a title. The chapter it belongs to is already the group it sits in, so
# what the row has to say is what KIND of thing it is.
_READING_STEM = re.compile(r"^ch0*(\d+)$", re.I)


def _says_the_same(one, two):
    """Whether two labels name the same thing, allowing for how each spells it.

    `Ch 04 homework` and `Chapter 04 Homework --- Field extensions` are one
    label written twice, and printing both on a row tells the reader nothing
    they did not have. Compared on letters and digits only, with the one
    abbreviation this course actually alternates between spelled out.
    """
    def flat(s):
        s = (s or "").lower().replace("chapter", "ch")
        return re.sub(r"[^a-z0-9]+", "", s)
    a, b = flat(one), flat(two)
    return bool(a) and (a in b or b in a)


def _titled(title, rel, kind):
    """The title as a row should carry it.

    LaTeX spells an em-dash with three hyphens and the library passes that
    through, which is right for a source file and wrong on glass. A textbook
    split gets called what it is, because its own filename says only its number
    and the reader is looking at the chapter's group already.
    """
    title = (title or "").replace("---", "—").replace("--", "–").strip()
    if kind == "reading":
        stem = os.path.splitext(os.path.basename(rel))[0]
        found = _READING_STEM.match(stem)
        if found:
            return "Textbook, chapter %d" % int(found.group(1))
    return title


def _from_library(rec):
    """One library record, as a shelf record. The inventory is not re-walked."""
    rel = rec.get("rel") or ""
    theirs = _theirs(rel)
    kind = _kind(rel, rec.get("stem") or "", rec.get("kind") or "", theirs)
    return {
        "rel": rel,
        "source": rec.get("source") or "",
        "title": _titled(rec.get("title") or reading._pretty(rel), rel, kind),
        "kind": kind,
        "pages": rec.get("pages") or 0,
        "at": rec.get("at") or 0,
        "size": rec.get("size") or 0,
        "pdf": bool(rec.get("pdf")),
        "stale": bool(rec.get("stale")),
        "theirs": theirs,
        # The library's own id, kept so a document reachable from both surfaces
        # can be followed back to the row the library page draws.
        "library": rec.get("id") or "",
    }


def _given(root, already):
    """The course material `reading.NOT_OURS` hides, by the three globs above.

    `already` is every path the library returned, so a course whose `lectures/`
    the library can already see does not arrive twice -- it is only re-tagged.
    """
    out = []
    for pattern in THEIRS:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            if not os.path.isfile(path) or fenced.refused(path):
                continue
            rel = _rel(root, path)
            if rel in already:
                continue
            at = library._mtime(path)
            out.append({
                "rel": rel,
                "source": "",
                "title": _titled(reading._pretty(path), rel, "reading"),
                "kind": "reading",
                "pages": library._pages(path),
                "at": at,
                "size": library._size(path),
                "pdf": True,
                # Nobody here built it, so there is no source to be newer
                # than it and nothing for it to be stale against.
                "stale": False,
                "theirs": True,
                "library": "",
            })
    return out


def _sids(root, recs):
    """A stable id per record, and the dedupe is by SORTED PATH.

    `reading.ident` slugs the FILENAME, which is what makes these legible --
    `ch04-homework`, `ch04-notes`, `ch04` -- and over the whole of a course it
    collides with nothing. Where two files in different directories do share a
    name, the suffix goes on the one whose path sorts later, NEVER on whichever
    the walk reached second: ink is anchored on `doc/<sid>/p<n>`, and an id that
    renumbers when a directory is added puts last week's marks on a different
    document.
    """
    taken = {}
    for rec in sorted(recs, key=lambda r: r["rel"]):
        base = reading.ident(root, rec["rel"] if rec["pdf"]
                             else (rec["source"] or rec["rel"]))
        n = taken.get(base, 0) + 1
        taken[base] = n
        rec["sid"] = base if n == 1 else "%s-%d" % (base[:36], n)


# ---------------------------------------------------------------------------
# the join: which box, derived from the path
# ---------------------------------------------------------------------------
def _sets(root):
    """`[(rel prefix, compiled pdf rel, set name, chapter number or None)]`."""
    out = []
    for s in homework.sets(root):
        built = homework.compiled_pdf(root, s["tex"])
        out.append((_rel(root, s["dir"]) + "/",
                    _rel(root, built) if built else "",
                    s["name"], s.get("chapter")))
    return out


def _chapter_nums(root, nodes):
    """`{chapter number: node id}`, joined on the label the node carries.

    NOT on a regex over the node's id. A chapter node is made from a syllabus
    record and carries that record's own label, so the label is the join and the
    number comes off the record rather than out of the id it produced.
    """
    nums = {}
    for c in syllabus.chapters(root):
        label = syllabus.label(c)
        try:
            num = int(str(c.get("num") or "").strip())
        except ValueError:
            continue
        if label and label not in nums:
            nums[label] = num
    out = {}
    for node in nodes:
        if node.get("kind") != "chapter":
            continue
        num = nums.get(node.get("chapter") or node.get("name") or "")
        if num is not None and num not in out:
            out[num] = node["id"]
    return out


def _place(root, recs, nodes):
    """Put `node` and `box` on every record. `""` and `Unfiled` for the rest."""
    label = dict((n["id"], n["name"]) for n in nodes)
    sets = _sets(root)
    by_set = dict((n.get("hw") or "", n["id"]) for n in nodes
                  if n.get("kind") == "set" and n.get("hw"))
    by_num = _chapter_nums(root, nodes)
    # Longest directory first, so a box inside another box gets its own files.
    dirs = sorted(((n["dir"].strip("/") + "/", n["id"]) for n in nodes
                   if n.get("dir")), key=lambda d: -len(d[0]))

    for rec in recs:
        rel, nid, under = rec["rel"], "", ""
        for prefix, built, name, chapter in sets:
            if name in by_set and (rel == built or rel.startswith(prefix)):
                nid = by_set[name]
                # A SET ROLLS UP TO ITS CHAPTER. The set box keeps the document
                # -- tapping `Ch 04 homework` shows the homework and nothing
                # else -- and the chapter it is for shows it too, because
                # somebody looking for "the chapter 4 sets" is looking for the
                # book problems and the worksheet and does not care that one of
                # them is filed outside `chapters/`.
                under = by_num.get(chapter, "") if chapter else ""
                if rel == built:
                    rec["kind"] = "homework"
                break
        if not nid:
            found = CHAPTER_DIR.match(rel)
            if found:
                nid = by_num.get(int(found.group(1)), "")
        if not nid:
            for prefix, box in dirs:
                if rel.startswith(prefix):
                    nid = box
                    break
        rec["node"] = nid
        rec["box"] = label.get(nid, "") if nid else "Unfiled"
        # Where the whole-workspace list files it, which is the chapter when
        # there is one and the box itself otherwise. Never the box's own id
        # when they are the same, so a group is never its own parent.
        rec["under"] = under if under and under != nid else ""
        rec["under_box"] = label.get(rec["under"], "") if rec["under"] else ""


# ---------------------------------------------------------------------------
# what anything else asks for
# ---------------------------------------------------------------------------
_cache = {}


def documents(root):
    """Every document in this workspace, with the box it belongs to on each.

    Cached the way `library.documents` is, because this is that walk plus a read
    of the map's shape -- and the map's shape is cached on the same clock.
    """
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    got = _documents(key)
    _cache[key] = (time.time(), got)
    return got


def _documents(root):
    try:
        found = library.documents(root)
    except Exception:                                        # noqa: BLE001
        found = []
    recs = [_from_library(r) for r in found]
    recs += _given(root, set(r["rel"] for r in recs))
    recs = recs[:MAX_DOCS]
    _sids(root, recs)
    try:
        shape = course_map.shape(root) or {}
    except Exception:                                        # noqa: BLE001
        shape = {}
    nodes = shape.get("nodes") or []
    _place(root, recs, nodes)
    order = dict((n["id"], i) for i, n in enumerate(nodes))
    # The map's own order, then the newest first inside a box. An unfiled
    # document sorts after every box, which is where its group goes.
    recs.sort(key=lambda r: (order.get(r["node"], len(order)), -(r["at"] or 0),
                             r["rel"]))
    for rec in recs:
        rec["iso"] = (time.strftime("%Y-%m-%d", time.localtime(rec["at"]))
                      if rec["at"] else "")
    return recs


def forget():
    """Drop the cache. For a test that writes a document under the process."""
    _cache.clear()


def counts(root):
    """`{node id: how many documents}`, for the map payload.

    THE COUNT AND NEVER THE LIST. Thin rows for a course's documents are some
    kilobytes and the payload carrying them is rebuilt four times a second; the
    list is fetched on a tap, which is the rule `routes/lesson.py` states.
    """
    out = {}
    for rec in documents(root):
        # BOTH BOXES, DELIBERATELY. A worksheet is one document and it is
        # reachable from two places; a badge says what that box opens, so the
        # chapter's badge counts it and the set's badge counts it. `total` in
        # `grouped` stays the number of distinct documents.
        for box in (rec["node"], rec.get("under")):
            if box:
                out[box] = out.get(box, 0) + 1
    return out


def find(root, sid_wanted):
    """The document with this sid, as `(path, stem)`, or `(None, None)`.

    A SID, NEVER A PATH. What arrives from the browser is compared against the
    sids this module handed out, and a miss is a miss -- `reading.find` is the
    rule and this is the same rule for a longer list. The fence is asked again
    on the file itself, because this is the last place it can be asked before
    the rasteriser opens it.
    """
    wanted = str(sid_wanted or "").strip().lower()
    if not wanted:
        return None, None
    for rec in documents(root):
        if rec["sid"] != wanted or not rec["pdf"]:
            continue
        target = os.path.realpath(os.path.join(root, *rec["rel"].split("/")))
        if fenced.refused(target) or not os.path.isfile(target):
            return None, None
        return target, os.path.splitext(os.path.basename(target))[0]
    return None, None


def grouped(repo):
    """Every document in the workspace, grouped by the box it is under.

    The groups are in the map's own order, because the drawer is read beside the
    picture and a list in a different order from the boxes above it is two
    orders to hold. `Unfiled` is last: it is where a document goes when no box
    contains it, which is most of them in a repository of code.
    """
    root = repo.root
    try:
        found = documents(root)
    except Exception as exc:                                 # noqa: BLE001
        return {"ok": False, "error": str(exc), "workspace": atlas.identify(root),
                "total": 0, "groups": []}
    groups, seen = [], {}
    for rec in found:
        # The chapter where the document has one, so the whole-workspace list
        # reads chapter by chapter; the set keeps its name on the row.
        key = rec.get("under") or rec["node"]
        name = rec.get("under_box") or rec["box"]
        if key not in seen:
            seen[key] = {"node": key, "box": name, "docs": []}
            groups.append(seen[key])
        row = dict((k, rec[k]) for k in
                   ("sid", "title", "kind", "pages", "at", "iso", "size",
                    "pdf", "stale", "theirs", "rel"))
        # Which set it came from, when that is not the group it is filed under
        # AND says something the title does not. A worksheet whose set is named
        # after the worksheet would otherwise print its own name twice.
        came = rec["box"] if rec.get("under") else ""
        row["set"] = "" if _says_the_same(came, row["title"]) else came
        seen[key]["docs"].append(row)
    # `_documents` already sorts the unfiled after every box; this is the
    # promise said out loud rather than left to a sort key.
    groups.sort(key=lambda g: 1 if not g["node"] else 0)
    return {"ok": True, "workspace": atlas.identify(root),
            "total": len(found), "groups": groups}
