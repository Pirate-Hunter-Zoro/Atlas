"""map.py -- the picture of a repository, which is the way into it.

Every course opened on an empty board. The drawer that shipped before this one
lists what a repository holds -- steps, files, documents -- and a list is a fine
index and a poor front door: it has no relationships in it. It cannot say that
the grid depends on a seam that does not exist yet, or that one box is where
five of six error labels come from. The difficulty this is for is not finding a
name. It is holding a system in your head, reported in those words: *"Honestly
I'm so lost in all of this."*

So a course opens on a diagram of its own working parts, and every part on it is
something you can tap to start work on.

**Structure is derived from disk. Meaning is written by the tutor. Neither is
guessed.** A model asked to draw the whole map on every turn is expensive,
non-deterministic and will disagree with itself between turns; a map derived
purely from the filesystem is honest and useless, because nothing on disk knows
that a stage is half-built. The written half is `live/map.json` and it is not
this module's yet.

What IS this module's, and all of it, is the half that cannot go stale: **every
repository gets a map, whether or not anybody has drawn one.** That is the
compatibility requirement -- *"this kind of design feels like it should work in
all repositories"* -- and it is met by falling back rather than by refusing:

    a book course          one node per chapter, and its problem sets beside them
    a project with a plan  one node per step, in one lane per plan file
    anything else          the repository's own top-level parts

Chapters come first, and that is a decision rather than an accident. No
repository here has both, but one could -- a book course whose README happens to
name a TODO -- and the rest of this board already answers "chapters, or failing
that parts" everywhere it asks the same question. A course whose chapters are
sitting right there should not be shown a task list instead of them.

A fallback map says so, quietly, once: it is a skeleton somebody can replace
with the real thing, and a skeleton that pretended to be a drawing would be
worse than no drawing at all.

Standard library only, like everything else.
"""

import os
import re
import time

from . import homework, plan, review, syllabus, walk

# What a node's state of completion may be, and there are six of them. A
# seventh would be a distinction nobody can hold in their head while looking at
# a picture, and the picture is the point.
STATUSES = ("done", "working", "next", "later", "blocked", "unknown")

# How long a node's one-line purpose may be. It is read on a tablet, inside a
# box, at whatever zoom the person left the plane at. A sentence that does not
# fit is not a shorter sentence; it is a box with the end of the sentence
# missing, and the end is where the verb usually is.
DOES = 120

# A picture with more boxes on it than this is not a picture. The caps are
# generous -- Galois Theory has twenty chapters and twenty problem sets -- and
# exist so that a repository nobody anticipated cannot produce a plane that
# takes a second to lay out.
MAX_NODES = 80
MAX_LANES = 8

# Files carried by one node, for the sitting a tap will eventually open. A
# walkthrough over forty files is not a walkthrough.
MAX_FILES = 12

# The whole shape is derived on every payload otherwise, four times a second.
# Everything underneath is itself cached or a directory listing, but the join is
# not free and the answer changes when somebody edits a plan, not when somebody
# writes a card. Same rule as `walk.units` and `plan.steps`.
CACHE_SECONDS = 30
_cache = {}


def _slug(text, fallback="node"):
    """A node id: short, stable, and made only of what an id may contain.

    Derived from the thing's own name rather than from a counter, so the id of
    the chapter on Galois correspondence is the same id tomorrow. A name that
    reduces to nothing -- punctuation, or another alphabet -- falls back rather
    than producing an empty id that two nodes could share.
    """
    out = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (out or fallback)[:40]


def _unique(taken, want):
    """`want`, or `want-2`, `want-3`... A duplicate id is a node that vanishes."""
    if want not in taken:
        taken.add(want)
        return want
    n = 2
    while "%s-%d" % (want[:37], n) in taken:
        n += 1
    got = "%s-%d" % (want[:37], n)
    taken.add(got)
    return got


def _short(text, limit=DOES):
    text = re.sub(r"\s+", " ", str(text or "").strip())
    if len(text) <= limit:
        return text
    # At a word boundary, and never mid-word: a box ending "the correcti…" reads
    # as a rendering fault rather than as an abbreviation.
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:.") + "…"


def _count(n, thing):
    """`1 source file`, `6 source files`. A count and a plural that disagree read
    as a bug, and this one is printed inside every box on the map."""
    if not n:
        return ""
    return "%d %s%s" % (n, thing, "" if n == 1 else "s")


def _purpose(step):
    """What a plan step says it involves, without repeating its own name.

    `plan.steps` builds a summary out of the heading plus the lines under it,
    because a drawer wants enough to tell two steps apart. A box on the map
    already has the heading written across the top of it in bold, so a `does`
    that opens with the same words again spends the whole box saying it twice
    and loses the half that says what the work actually is.
    """
    summary = re.sub(r"\s+", " ", str(step.get("summary") or "").strip())
    title = re.sub(r"\s+", " ", str(step.get("title") or "").strip())
    if title and summary.lower().startswith(title.lower()):
        summary = summary[len(title):]
    # And the date stamp, which is provenance for a reader of the plan file and
    # noise in a box three inches wide.
    summary = re.sub(r"^\s*[.:;,-]*\s*\((?:Added|Updated|Corrected)[^)]*\)", "",
                     summary)
    return _short(summary.lstrip(" .:;,-"))


def _node(nid, name, lane, **rest):
    """One box. Every field it can have, always, so nothing downstream guesses."""
    node = {
        "id": nid,
        "name": name,
        "also": "",
        "lane": lane,
        "does": "",
        "status": "unknown",
        "files": [],
        "step": "",
        "doc": "",
        "slide": None,
        "note": "",
    }
    node.update(rest)
    return node


# ---------------------------------------------------------------------------
# the three fallbacks
# ---------------------------------------------------------------------------
def _from_chapters(root):
    """A book course: its chapters in order, and its problem sets beside them.

    The one shape on this board that was already painless, and the map must not
    make it worse. Chapter *n* points at chapter *n+1* because a book is read in
    that order, which is the only relationship a table of contents actually
    asserts -- and asserting it is the whole difference between a picture and a
    list.
    """
    chapters = syllabus.chapters(root)
    if not chapters:
        return None
    taken = set()
    nodes, edges = [], []
    lanes = ["chapters"]
    last = None
    for c in chapters[:MAX_NODES]:
        full = syllabus.label(c)
        if not full:
            continue
        num = str(c.get("num") or "").strip()
        nid = _unique(taken, _slug("ch-" + num if num else full, "chapter"))
        nodes.append(_node(nid, full, "chapters",
                           also=("Chapter %s" % num) if num else "",
                           chapter=full))
        if last:
            edges.append({"from": last, "to": nid, "label": ""})
        last = nid

    sets = homework.sets(root)
    if sets:
        lanes.append("problem sets")
        for x in sets[: max(0, MAX_NODES - len(nodes))]:
            nid = _unique(taken, _slug("hw-" + x["name"], "set"))
            nodes.append(_node(nid, x["name"], "problem sets",
                               also=x.get("rel") or "", hw=x["name"]))
    return {
        "title": "The course, chapter by chapter",
        "lanes": lanes,
        "nodes": nodes,
        "edges": edges,
        "why": "Drawn from this course's own chapter table.",
    }


def _from_plan(root):
    """A project: the steps it has written down, one lane per plan.

    A narrative hub holds three projects' plans and owns none of them, and
    `plan.steps` already labels each step with the project it came from. That
    label is the lane -- so a hub's map is three columns of work rather than
    twelve boxes in a row with nothing saying which is which, which is exactly
    the failure that made `plan.paths` return a list in the first place.
    """
    steps = plan.steps(root)
    if not steps:
        return None
    taken = set()
    nodes = []
    lanes = []
    for x in steps[:MAX_NODES]:
        lane = (x.get("from") or "what's next").strip() or "what's next"
        if lane not in lanes:
            if len(lanes) >= MAX_LANES:
                continue
            lanes.append(lane)
        num = str(x.get("num") or "").strip()
        nid = _unique(taken, _slug("%s-%s" % (lane, num or x.get("title")), "step"))
        nodes.append(_node(nid, x.get("title") or x.get("label") or "step",
                           lane,
                           also=("Step %s" % num) if num else "",
                           does=_purpose(x),
                           step=num,
                           # What `board open` files the sitting under, which is
                           # the plan's own label and not the node's name: the
                           # drawer already opens steps by it, and two spellings
                           # of one step would file two lessons.
                           chapter=x.get("label") or x.get("title") or ""))
    where = "; ".join(_where(root, p) for p in plan.paths(root))
    return {
        "title": "What this project says comes next",
        "lanes": lanes or ["what's next"],
        "nodes": nodes,
        "edges": [],
        "why": "Drawn from %s." % (where or "this project's plan"),
    }


def _where(root, target):
    """A plan's path as a person would write it. `plan._short`, without reaching
    into another module's private half."""
    return plan.where(root) if len(plan.paths(root)) == 1 else os.path.basename(target)


def _from_parts(root):
    """Anything else: the repository's own top-level parts.

    A repository says what its parts are by being made of them, and
    `review.units` already answers exactly this question for the review picker.
    Each part carries the source files under it, so a tap on one has something
    to open a walkthrough over -- which is free here, because `walk.units` is
    read on every payload anyway and remembers itself for half a minute.
    """
    parts = review.units(root)
    if not parts:
        return None
    try:
        source = walk.units(root)
    except Exception:                                        # noqa: BLE001
        source = []
    taken = set()
    nodes = []
    for u in parts[:MAX_NODES]:
        nid = _unique(taken, _slug(u["name"], "part"))
        here = u["name"].rstrip("/")
        files = [s["path"] for s in source
                 if s["path"] == here or s["path"].startswith(here + "/")]
        nodes.append(_node(nid, u["label"], "parts",
                           files=files[:MAX_FILES],
                           does=_count(len(files), "source file"),
                           part=u["name"]))
    return {
        "title": "What this repository is made of",
        "lanes": ["parts"],
        "nodes": nodes,
        "edges": [],
        "why": "Drawn from this repository's own top-level parts.",
    }


def _shape(root):
    """The skeleton: lanes, nodes and edges, with no judgement in it yet."""
    for build in (_from_chapters, _from_plan, _from_parts):
        try:
            found = build(root)
        except Exception:                                    # noqa: BLE001
            found = None
        if found and found["nodes"]:
            return found
    return None


def shape(root):
    """`_shape`, remembered for a little while. See `CACHE_SECONDS`."""
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = _shape(root)
    _cache[key] = (time.time(), found)
    return found


# ---------------------------------------------------------------------------
# what the board genuinely knows about a box
# ---------------------------------------------------------------------------
def _stamp(node, state, filed):
    """The status of one fallback node, and never more than is actually known.

    `unknown` is the honest answer for most of a derived map and it is the one
    to give. The three exceptions are things the board can point at:

      * the sitting open right now is `working` -- it is being worked on, by
        definition, because somebody is in it;
      * a chapter or a step with a lesson already filed against it is `done`,
        which is the only record of finished work this board keeps;
      * a step that is still IN the plan cannot be done, so the first one is
        `next` and the rest are `later`. A plan lists what is left.

    Recency is deliberately not here. A node whose files changed this morning is
    touched, not progressed, and painting the two the same way would make the
    map agree with whatever was edited last rather than with what is true.
    """
    state = state or {}
    here = (state.get("chapter") or "").strip()
    mine = (node.get("chapter") or node.get("hw") or node.get("part") or "").strip()

    if mine and here and mine == here:
        return "working"
    if node.get("hw") and (state.get("hw") or "").strip() == node["hw"]:
        return "working"
    if node.get("part") and node["part"] in (state.get("review") or []):
        return "working"
    if mine and mine in filed:
        return "done"
    return node.get("status") or "unknown"


def _order(nodes):
    """`next` for the first unfinished step in each lane, `later` for the rest.

    Only for a map built from a plan, where the order in the file is a claim
    about what comes first and the board already makes it: the drawer says
    "what's next" over the top of that same list.
    """
    seen = set()
    for node in nodes:
        if not node.get("step") or node["status"] not in ("unknown",):
            continue
        if node["lane"] in seen:
            node["status"] = "later"
        else:
            seen.add(node["lane"])
            node["status"] = "next"


def _filed(archived):
    """Every chapter label a past lesson was filed under."""
    out = set()
    for a in archived or []:
        label = (a.get("chapter") or "").strip()
        if label:
            out.add(label)
    return out


def status(root, state=None, archived=None):
    """The map block the board paints, or None for a repository with nothing in it.

    None is a real answer -- an empty repository has no working parts -- and it
    is different from an empty node list, which would draw an empty plane and
    say nothing about why.
    """
    found = shape(root)
    if not found:
        return None
    filed = _filed(archived)
    nodes = []
    for node in found["nodes"]:
        node = dict(node)
        node["status"] = _stamp(node, state, filed)
        if node["status"] not in STATUSES:
            node["status"] = "unknown"
        nodes.append(node)
    if any(n.get("step") for n in nodes):
        _order(nodes)
    return {
        "version": 1,
        "title": found["title"],
        "lanes": found["lanes"],
        "nodes": nodes,
        "edges": found["edges"],
        # Said once, quietly, on the map itself: this is a skeleton derived from
        # what is on disk, and somebody can draw the real one.
        "fallback": True,
        "why": found["why"],
        "total": len(nodes),
    }


def find(root, node_id, state=None, archived=None):
    """One node, by the id a browser sent -- or None.

    A name arriving from a request is never constructed into anything; it is
    looked up in what discovery found, the same rule as `walk.resolve` and
    `reading.find`. A miss is a miss.
    """
    built = status(root, state, archived)
    if not built:
        return None
    want = str(node_id or "").strip()
    for node in built["nodes"]:
        if node["id"] == want:
            return node
    return None
