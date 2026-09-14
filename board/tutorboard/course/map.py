"""map.py -- what the repository IS, as a diagram you can work from.

Not a task list. The first version of this drew the plan -- twelve steps in a
column -- and a column of steps is a list wearing a diagram's clothes. It was
rejected in those terms, and rightly: *"I don't want just a list of all the
TODOs. I want a map of the CONTENT in the repository."*

So the boxes are the repository's own parts and the arrows are what actually
depends on what -- an entity-relationship diagram of a working system, which is
the picture somebody holds in their head when they understand a codebase and
does not have when they do not. The outstanding work is drawn ON that picture:
each step of the plan is a numbered chip on the box it is about, coloured by
where it falls in the order, so "what is left" and "where it lives" are one
thing you look at rather than two lists you hold together.

**None of it is declared.** Three discoveries, all of them re-read from disk:

    the parts        every directory of this repository that holds source
    the arrows       every import from one of those directories into another
    the work         every step of the plan, matched to the part it names

A part's one-line purpose is its own package docstring, which is a sentence
somebody already wrote about their own code and is therefore true. Where there
is none the box says what it is made of instead. Nothing here asks a model what
a module is for.

A book course has no imports and no packages; its content is its chapters, and
the arrow between two of them is the order they are read in.

Standard library only, like everything else.
"""

import os
import re
import time

from . import homework, plan, reading, review, syllabus, walk

# What a node's state of completion may be, and there are six of them. A
# seventh would be a distinction nobody can hold in their head while looking at
# a picture, and the picture is the point.
STATUSES = ("done", "working", "next", "later", "blocked", "unknown")

# How long a box's one-line purpose may be. It is read on a tablet, inside a
# box, at whatever zoom the person left the plane at.
DOES = 110

# A picture with more boxes on it than this is not a picture. Past it the parts
# are rolled up to their parent directory, which is the same repository drawn
# at a coarser grain rather than a truncated one.
MAX_NODES = 44

# Files carried by one box, for the sitting a tap opens.
MAX_FILES = 40

# How many files in one directory are read to find its imports, and how much of
# each. THE PAYLOAD IS REBUILT FOUR TIMES A SECOND, and this is the only
# discovery on this board that opens files rather than listing them: reading all
# 177 solutions in Algo-Solutions whole took 3.8 seconds, in the thread that
# paints every board. An import is at the top of a file and a directory of a
# hundred files does not have a hundred different dependencies, so a sample of
# the head of each is the same answer for a hundredth of the work.
MAX_SCAN = 24
HEAD_BYTES = 8000

# How many steps of the plan may sit on one box before it stops being legible.
MAX_CHIPS = 6

# The whole shape is derived on every payload otherwise, four times a second,
# and this one reads the head of every source file in the repository. Same rule
# as `walk.units` and `plan.steps`.
CACHE_SECONDS = 30
_cache = {}


# ---------------------------------------------------------------------------
# names and ids
# ---------------------------------------------------------------------------
def _slug(text, fallback="node"):
    """A node id: short, stable, and made only of what an id may contain.

    Derived from the thing's own path rather than from a counter, so the id of
    the evaluation package is the same id tomorrow and a remembered box is still
    that box after a payload.
    """
    out = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (out or fallback)[:40]


def _unique(taken, want):
    """`want`, or `want-2`, `want-3`... A duplicate id is a box that vanishes."""
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
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" ,;:.") + "…"


def _count(n, thing):
    """`1 file`, `6 files`. A count and a plural that disagree read as a bug."""
    if not n:
        return ""
    return "%d %s%s" % (n, thing, "" if n == 1 else "s")


# ---------------------------------------------------------------------------
# the parts: every directory of this repository that holds source
# ---------------------------------------------------------------------------
def _parts(units):
    """Group the repository's source files by the directory they live in.

    A directory rather than a file, because a file is a page and a directory is
    a part: `psych_asr/evaluate` is a thing its owner talks about and
    `psych_asr/evaluate/labels.py` is a thing inside it. Fifty boxes is not a
    picture; six is.
    """
    by_dir = {}
    for u in units:
        by_dir.setdefault(u["dir"] or ".", []).append(u["path"])
    return by_dir


def _rollup(by_dir, limit):
    """Too many parts: draw the same repository one level coarser.

    Never by dropping boxes. A map missing the directory somebody is looking for
    is worse than a map drawn at a grain they did not choose, because nothing on
    it says anything is missing.
    """
    while len(by_dir) > limit:
        depth = max(d.count(os.sep) for d in by_dir)
        if depth == 0:
            break
        rolled = {}
        for d, files in by_dir.items():
            up = os.path.dirname(d) if d.count(os.sep) == depth else d
            rolled.setdefault(up or ".", []).extend(files)
        if len(rolled) == len(by_dir):
            break
        by_dir = rolled
    return by_dir


# What a directory is FOR, in the words of whoever wrote it. A module docstring
# is a sentence somebody already committed about their own code; nothing here
# invents one.
PY_DOC = re.compile(r'^\s*(?:#[^\n]*\n|\s)*?(?:"""|\'\'\')(.*?)(?:"""|\'\'\')',
                    re.DOTALL)
# `// Package foo does bar.` and `/* ... */` at the top of a Go or C file.
SLASH_DOC = re.compile(r"^\s*(?://[^\n]*\n)+")


def _scan(root, files):
    """The head of the files worth reading in one directory, in the order to try.

    Read ONCE and used twice -- for the directory's purpose and for its imports
    -- because the alternative is opening every source file in the repository
    twice on a shared filesystem. The order is the order a package announces
    itself in: its marker first, then a file named after the directory, then the
    biggest thing in it.
    """
    here = os.path.dirname(files[0]) if files else ""
    markers = ("__init__.py", "index.js", "index.ts", "mod.rs", "lib.rs",
               os.path.basename(here) + ".py", os.path.basename(here) + ".go")
    # THE MARKER IS PROBED ON DISK, not looked for among the walkable files.
    # `walk.units` leaves `__init__.py` out on purpose -- it is a namespace
    # rather than a thing that does anything, and offering forty of them in a
    # picker buries the files that do. But it is exactly where a Python package
    # writes the sentence saying what it is for, so a map built only from what
    # the picker offers never finds a single package docstring. It is read here
    # and is still not offered as a file to walk through.
    order = []
    for name in markers:
        rel = os.path.join(here, name) if here else name
        if rel not in order and os.path.isfile(os.path.join(root, rel)):
            order.append(rel)
    known = set(order)
    rest = sorted((f for f in files if f not in known),
                  key=lambda f: _size(root, f), reverse=True)
    out = []
    for rel in (order + rest)[:MAX_SCAN]:
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8",
                      errors="replace") as fh:
                out.append((rel, fh.read(HEAD_BYTES)))
        except OSError:
            continue
    return out


def _purpose(heads):
    """The first sentence of the package's own docstring, if it has one."""
    for rel, head in heads[:4]:
        said = _doc_of(rel, head)
        if said:
            return said
    return ""


def _size(root, rel):
    try:
        return os.path.getsize(os.path.join(root, rel))
    except OSError:
        return 0


def _doc_of(path, head):
    """The first sentence of a file's leading comment or docstring."""
    said = ""
    m = PY_DOC.match(head) if path.endswith(".py") else None
    if m:
        said = m.group(1)
    else:
        m = SLASH_DOC.match(head)
        if m:
            said = re.sub(r"^\s*//+\s?", "", m.group(0), flags=re.MULTILINE)
    said = re.sub(r"\s+", " ", said or "").strip()
    if not said:
        return ""
    # These files open `evaluate.py -- what a candidate is graded against.`, so
    # the filename at the front is a header rather than a sentence.
    said = re.sub(r"^[\w./-]+\.(?:py|go|js|rs|sh)\s*[-–—:]+\s*", "", said)
    first = re.split(r"(?<=[.!?])\s+", said, maxsplit=1)[0]
    return _short(first)


# ---------------------------------------------------------------------------
# the arrows: what imports what
# ---------------------------------------------------------------------------
# A Python import of something in this repository, absolute or relative.
PY_IMPORT = re.compile(
    r"^\s*(?:from\s+(?P<dots>\.*)(?P<mod>[\w.]*)\s+import|import\s+(?P<plain>[\w.]+))",
    re.MULTILINE)
# A Go or JavaScript import of a path. Only quoted paths, so a word in a comment
# is not an edge.
PATH_IMPORT = re.compile(r"""(?:from|import|require)\s*\(?\s*["'](?P<p>[^"']+)["']""")


def _module_paths(rel, text):
    """Every repository-relative path this file imports, as best as a grep can.

    A grep and not a parser, and that is a decision rather than a shortcut:
    parsing five languages to answer "does this package use that one" is a
    dependency and a maintenance burden for a question a person answers by
    looking at the same lines. What it must never do is invent an edge, which is
    why everything it produces is checked against files that actually exist
    before it becomes an arrow.
    """
    here = os.path.dirname(rel)
    out = []
    if rel.endswith(".py"):
        for m in PY_IMPORT.finditer(text):
            dots = m.group("dots") or ""
            mod = m.group("mod") or m.group("plain") or ""
            if dots:
                # `from ..artifacts.naming import x`, read from this file's own
                # directory: one dot is here, two is the parent, and so on.
                up = here
                for _ in range(len(dots) - 1):
                    up = os.path.dirname(up)
                out.append(os.path.join(up, *mod.split(".")) if mod else up)
            elif mod:
                out.append(os.path.join(*mod.split(".")))
        return out
    for m in PATH_IMPORT.finditer(text):
        p = m.group("p")
        if p.startswith("."):
            out.append(os.path.normpath(os.path.join(here, p)))
        else:
            # A Go import is a module path whose tail is a directory in this
            # repository, when it is this repository's at all.
            bits = p.split("/")
            for i in range(len(bits)):
                out.append(os.path.join(*bits[i:]))
    return out


def _owner(path, dirs, by_path):
    """Which box owns this path -- as a directory, or as a file inside one."""
    p = str(path or "").strip("/").replace("\\", "/")
    if not p:
        return None
    if p in dirs:
        return p
    hit = by_path.get(p)
    if hit:
        return hit
    for ext in (".py", ".go", ".js", ".mjs", ".ts", ".rs", ".sh", ".lean"):
        hit = by_path.get(p + ext)
        if hit:
            return hit
    return None


def _edges(by_dir, heads):
    """Every import from one part of this repository into another.

    Counted, so an arrow carrying eleven imports can be drawn differently from
    one carrying a single mention -- and deduplicated, because forty files
    importing one helper is one relationship and not forty.
    """
    dirs = set(by_dir)
    by_path = {}
    for d, files in by_dir.items():
        for f in files:
            by_path[f.replace("\\", "/")] = d
    found = {}
    for d, read in heads.items():
        for rel, text in read:
            for target in _module_paths(rel, text):
                owner = _owner(target, dirs, by_path)
                if not owner or owner == d:
                    continue
                found[(d, owner)] = found.get((d, owner), 0) + 1
    return [{"from": a, "to": b, "weight": n, "label": ""}
            for (a, b), n in sorted(found.items())]


# ---------------------------------------------------------------------------
# the work: the plan's steps, on the boxes they are about
# ---------------------------------------------------------------------------
# A token in a plan that could name a module or a file. Deliberately loose here
# and checked hard afterwards: nothing becomes a chip until the path it names is
# on disk.
MENTION = re.compile(r"[\w][\w./]*(?:\.(?:py|go|js|mjs|ts|rs|sh|lean|R|jl)|"
                     r"(?:\.[a-z_][\w]*){1,4})")


def _mentions(text):
    out = []
    for m in MENTION.finditer(text or ""):
        tok = m.group(0).strip(".")
        if len(tok) > 3 and tok not in out:
            out.append(tok)
    return out[:40]


def _step_text(step, seen, until=None):
    """Everything the plan says about one step, not the blurb a drawer shows.

    `plan.steps` trims a step to 240 characters, because a drawer wants enough to
    tell two steps apart and no more. That is exactly the wrong length here: the
    module names that say WHICH PART of the repository a step is about are in the
    body, three sentences down, and with the blurb alone not one step in PSYCH-ASR
    matched a box -- every chip fell into the tray.

    So the step is read back out of the plan it came from, between its own line
    and the next step's. One read of one file per plan, remembered across the
    steps that share it.
    """
    target = step.get("file")
    line = step.get("line")
    if not target or not line:
        return (step.get("title") or "") + " " + (step.get("summary") or "")
    if target not in seen:
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as fh:
                seen[target] = fh.read().splitlines()
        except OSError:
            seen[target] = []
    lines = seen[target]
    # AS FAR AS THE NEXT STEP, and not a line further.
    #
    # A fixed number of lines was the first try and it is wrong in the way that
    # matters: step 1's window ran over steps 2 and 3, so step 1 was matched
    # against every module the whole plan mentions and landed on boxes it says
    # nothing about. A chip on the wrong box is a claim about where the work is.
    #
    # Capped as well, because the last step of a plan has no next step and a
    # standing-context section after it is not part of it.
    end = len(lines) if until is None else max(line, until - 1)
    return " ".join(lines[line - 1:min(end, line - 1 + 120)])


def _attach(steps, by_dir):
    """Put each step of the plan on the box it names, and say which name nothing.

    A step that names `psych_asr.cli.grade_arms` is about the `cli` box, and the
    match is the path existing rather than the words looking similar -- a chip on
    the wrong box is worse than a chip in the tray, because a chip on a box is
    read as a claim about where the work is.

    Everything unmatched comes back rather than being dropped. A person choosing
    what to do next must be able to see every step there is, in order, whether or
    not this module could work out where it belongs.
    """
    dirs = set(by_dir)
    by_path = {}
    for d, files in by_dir.items():
        for f in files:
            by_path[f.replace("\\", "/")] = d
    # Where each step stops: the line the next step of the SAME plan starts on.
    # A hub holds three plans, and step 1 of the second is not the end of step 4
    # of the first.
    until = []
    for i, step in enumerate(steps):
        stop = None
        for later in steps[i + 1:]:
            if later.get("file") == step.get("file") and later.get("line"):
                stop = later["line"]
                break
        until.append(stop)

    on, loose, seen = {}, [], {}
    for i, step in enumerate(steps):
        text = _step_text(step, seen, until[i])
        votes = {}
        for tok in _mentions(text):
            owner = _owner(tok.replace(".", "/"), dirs, by_path) \
                or _owner(tok, dirs, by_path)
            if owner:
                votes[owner] = votes.get(owner, 0) + 1
        chip = {
            "num": step.get("num") or str(i + 1),
            "title": step.get("title") or "",
            "label": step.get("label") or step.get("title") or "",
            "summary": step.get("summary") or "",
            "order": i + 1,
            "from": step.get("from") or "",
        }
        if not votes:
            loose.append(chip)
            continue
        # The two boxes it talks about most. A step that touches six modules is
        # a step about the two it keeps naming; pinning it to all six would put
        # the same work in six places and none of them would mean anything.
        best = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        for owner, _n in best:
            on.setdefault(owner, []).append(chip)
    return on, loose


# ---------------------------------------------------------------------------
# building one
# ---------------------------------------------------------------------------
def _node(nid, name, kind, **rest):
    """One box. Every field it can have, always, so nothing downstream guesses."""
    node = {
        "id": nid, "name": name, "also": "", "kind": kind, "lane": "",
        "does": "", "status": "unknown", "files": [], "dir": "",
        "steps": [], "doc": "", "slide": None, "note": "", "chapter": "",
    }
    node.update(rest)
    return node


def _from_code(root):
    """A repository made of code: its parts, and what depends on what."""
    try:
        units = walk.units(root)
    except Exception:                                        # noqa: BLE001
        units = []
    if not units:
        return None
    by_dir = _rollup(_parts(units), MAX_NODES)
    if not by_dir:
        return None

    heads = {}
    for d in sorted(by_dir):
        by_dir[d] = sorted(by_dir[d])
        heads[d] = _scan(root, by_dir[d])

    taken = set()
    ids = {}
    nodes = []
    for d in sorted(by_dir):
        files = by_dir[d]
        nid = _unique(taken, _slug(d if d != "." else "top level", "part"))
        ids[d] = nid
        nodes.append(_node(
            nid,
            os.path.basename(d) if d not in (".", "") else "top level",
            "part",
            also="" if d in (".", "") else d,
            dir=d,
            does=_purpose(heads[d]) or _count(len(files), "source file"),
            files=files[:MAX_FILES]))

    edges = []
    for e in _edges(by_dir, heads):
        if e["from"] in ids and e["to"] in ids:
            edges.append({"from": ids[e["from"]], "to": ids[e["to"]],
                          "weight": e["weight"], "label": ""})

    # The documents somebody already wrote are content too, and the map is where
    # you would look for them. They depend on nothing and nothing depends on
    # them, so they stand apart rather than being wired into the graph.
    try:
        docs = reading.documents(root)
    except Exception:                                        # noqa: BLE001
        docs = []
    for d in docs[:8]:
        nid = _unique(taken, _slug("doc-" + d["id"], "doc"))
        nodes.append(_node(nid, d["name"], "doc", also="document",
                           doc=d["id"], does="Written about how this works."))

    on, loose = _attach(_plan_steps(root), by_dir)
    for node in nodes:
        if node["dir"] in on:
            node["steps"] = on[node["dir"]][:MAX_CHIPS]

    return {"title": "", "nodes": nodes, "edges": edges, "loose": loose,
            "why": "Drawn from this repository's own source and what it imports."}


def _plan_steps(root):
    try:
        return plan.steps(root)
    except Exception:                                        # noqa: BLE001
        return []


def _from_chapters(root):
    """A book course: its chapters, in the order they are read, and its sets.

    The one shape on this board that was already painless, and the map must not
    make it worse. A chapter points at the next because a book is read in that
    order, which is the only relationship a table of contents actually asserts
    -- and asserting it is the difference between a picture and a list.
    """
    chapters = syllabus.chapters(root)
    if not chapters:
        return None
    taken = set()
    nodes, edges = [], []
    last = None
    for c in chapters[:MAX_NODES]:
        full = syllabus.label(c)
        if not full:
            continue
        num = str(c.get("num") or "").strip()
        nid = _unique(taken, _slug("ch-" + num if num else full, "chapter"))
        nodes.append(_node(nid, full, "chapter",
                           also=("Chapter %s" % num) if num else "",
                           chapter=full))
        if last:
            edges.append({"from": last, "to": nid, "weight": 1, "label": ""})
        last = nid

    for x in homework.sets(root)[: max(0, MAX_NODES - len(nodes))]:
        nid = _unique(taken, _slug("hw-" + x["name"], "set"))
        node = _node(nid, x["name"], "set", also="problem set", hw=x["name"])
        nodes.append(node)
        # A set belongs beside the chapter it is for, where the course numbers
        # them that way -- `ch07` beside chapter 7 -- and beside nothing where
        # it does not.
        m = re.match(r"ch0*(\d+)", x["name"])
        if m:
            want = _slug("ch-" + m.group(1), "")
            if any(n["id"] == want for n in nodes):
                edges.append({"from": want, "to": nid, "weight": 1, "label": ""})
    return {"title": "", "nodes": nodes, "edges": edges, "loose": [],
            "why": "Drawn from this course's own chapter table."}


def _from_parts(root):
    """Neither code nor a book: the repository's own top-level pieces."""
    parts = review.units(root)
    if not parts:
        return None
    taken = set()
    nodes = []
    for u in parts[:MAX_NODES]:
        nid = _unique(taken, _slug(u["name"], "part"))
        nodes.append(_node(nid, u["label"], "part", dir=u["name"].rstrip("/")))
    on, loose = _attach(_plan_steps(root),
                        dict((n["dir"], []) for n in nodes))
    for node in nodes:
        node["steps"] = on.get(node["dir"], [])[:MAX_CHIPS]
    return {"title": "", "nodes": nodes, "edges": [], "loose": loose,
            "why": "Drawn from this repository's own top-level parts."}


def _shape(root):
    """The picture, with no judgement in it yet."""
    for build in (_from_chapters, _from_code, _from_parts):
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
    """The status of one box, and never more than is actually known.

    `unknown` is the honest answer for most of a derived map and it is the one
    to give. What the board can point at:

      * the sitting open right now is `working` -- somebody is in it;
      * a box carrying the first step of the plan is where the work goes `next`,
        and a box carrying any other step is `later`; a plan lists what is left,
        so a box with a step on it cannot be finished;
      * a chapter with a lesson already filed against it is `done`.

    Recency is deliberately absent. A box whose files changed this morning has
    been touched, which is not progressed, and painting the two the same way
    would make the map agree with whatever was edited last.
    """
    state = state or {}
    if (state.get("node") or "").strip() == node["id"]:
        return "working"
    here = (state.get("chapter") or "").strip()
    mine = (node.get("chapter") or node.get("hw") or "").strip()
    if mine and here and mine == here:
        return "working"
    if here and any(s["label"] == here for s in node.get("steps") or []):
        return "working"
    if node.get("steps"):
        return "next" if any(s["order"] == 1 for s in node["steps"]) else "later"
    if mine and mine in filed:
        return "done"
    return "unknown"


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
    # Every step there is, counted once. A step that names two parts sits on
    # two boxes -- that is the truth about it -- and counting it twice in the
    # bar would say the plan has more in it than it does.
    placed = set()
    for n in nodes:
        for x in n["steps"]:
            placed.add(x["label"])
    total = len(found["loose"]) + len(placed)
    return {
        "version": 2,
        "title": found["title"],
        "nodes": nodes,
        "edges": found["edges"],
        # Every step of the plan this module could not place. Offered rather
        # than dropped: what to do next is the person's choice, and a choice
        # they cannot see is not one.
        "loose": found["loose"],
        "steps": total,
        "why": found["why"],
        "total": len(nodes),
    }


def find(root, node_id, state=None, archived=None):
    """One box, by the id a browser sent -- or None.

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
