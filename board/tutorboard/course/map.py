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

import json
import os
import re
import time

from . import homework, plan, reading, review, symbols, syllabus, walk
# `paths` as `toolpaths`, because this package already has a module by that name
# in spirit -- `course/plan.py` defines a public `paths(root)` and had to do
# exactly this. Same trap, same answer: the module keeps its name and the import
# moves.
from .. import paths as toolpaths

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

# How many boxes ONE LEVEL DOWN may be drawn at once. `MAX_NODES` is the cap on
# the picture and this is the cap on an expansion, and the second is the one
# that binds: a symbol-level diagram of a real project is hundreds of boxes, and
# four hundred boxes on a plane is the ugly grid again with more effort. Same
# answer as `MAX_NODES` gives at the top level -- draw the level, say it was
# capped, and never silently truncate.
MAX_INSIDE = 40

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
    for d in _documents(root)[:MAX_LOOSE_DOCS]:
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


# ---------------------------------------------------------------------------
# three depths: the package, the module, the symbol
# ---------------------------------------------------------------------------
# The top-level picture draws DIRECTORIES, and a directory is not a moving part.
# *"Just looking at it should communicate everything one needs to know to
# understand how the project works, and when we work on a TODO, it's obvious
# what moving parts we'll be affecting."* The things that move are the modules
# and, inside them, the classes and functions.
#
# EXPANDING IS A NEW PICTURE, NOT A BIGGER ONE. Splicing a package's twelve
# modules into a diagram that already has forty boxes on it produces the grid
# the whole complaint was about; opening the package as its own picture, with a
# way back up, keeps every depth legible. So this returns one level: the boxes
# inside one box, the arrows among them, and the arrows that LEAVE rolled up to
# the sibling box they land in -- which is what "the arrows rolled up to
# whatever depth is showing" means when the depth showing is one box's inside.
#
# IT IS DERIVED ON A TAP AND NEVER ON A PAYLOAD. The board payload is rebuilt
# four times a second and `_from_code` already reads the head of every source
# file in the repository for it. Parsing them whole on that clock is not
# affordable and is not needed: nobody is looking inside a box until they ask.
#
# `symbols.py` owns the other half -- what one file defines and what each
# definition uses -- because reading a file's definitions is a different job
# from drawing a repository, and `ast` belongs with the first one.
def _module_id(taken, rel):
    return _unique(taken, _slug("in-" + rel, "module"))


def _symbol_id(taken, rel, name):
    return _unique(taken, _slug("at-" + rel + "-" + name, "symbol"))


def _children(built):
    """Every module box the whole picture could open into, by its id.

    Built the same way every time it is asked -- boxes in the order `status`
    returned them, files in the order the box carries them -- so the id a
    browser was handed is the id this finds. Nothing is remembered between
    calls and nothing is constructed from a request.
    """
    taken, out = set(), {}
    for node in built["nodes"]:
        for rel in node.get("files") or []:
            out[_module_id(taken, rel)] = (node, rel)
    return out


def _file_index(built):
    """Every file on the picture, mapped to the box that owns it."""
    out = {}
    for node in built["nodes"]:
        for rel in node.get("files") or []:
            out[rel.replace("\\", "/")] = node
    return out


def _lands_in(target, files, by_file, dirs):
    """Which box an imported path lands in: a file here, a file there, or a box.

    Returns (rel, node) where `rel` is a file in `files` -- an arrow that stays
    inside the box being opened -- or (None, node) for one that leaves it, or
    (None, None) for a path this repository does not have. An import that
    resolves to nothing is not an arrow; that rule is the whole reason the top
    level is trustworthy and it does not change one depth down.
    """
    p = str(target or "").strip("/").replace("\\", "/")
    if not p:
        return (None, None)
    for cand in [p] + [p + ext for ext in (".py", ".go", ".js", ".mjs", ".ts",
                                           ".rs", ".sh", ".lean")]:
        if cand in files:
            return (cand, None)
        hit = by_file.get(cand)
        if hit is not None:
            return (None, hit)
    return (None, dirs.get(p))


def _import_path(rel, where):
    """The repository path a Python import names, from the file that makes it.

    The same arithmetic `_module_paths` does for a whole file, asked about one
    import: one leading dot is this file's own directory, two is the parent.
    """
    where = str(where or "")
    if not where:
        return ""
    if where.startswith("."):
        dots = len(where) - len(where.lstrip("."))
        up = os.path.dirname(rel)
        for _ in range(dots - 1):
            up = os.path.dirname(up)
        mod = where.lstrip(".")
        return os.path.join(up, *mod.split(".")) if mod else up
    return os.path.join(*where.split("."))


def _outside(nodes, seen, node):
    """A sibling box, drawn once, as the thing an arrow leaves towards.

    It keeps its own name -- which for a written map is the name a PERSON gave
    it, *the typist* rather than `psych_asr/asr` -- and is marked so the drawing
    can show it as a wall rather than as part of what is being read.
    """
    if node["id"] in seen:
        return node["id"]
    seen.add(node["id"])
    nodes.append(_node(node["id"], node["name"], node["kind"],
                       also=node.get("also") or "", does=node.get("does") or "",
                       status=node.get("status") or "unknown", outside=True))
    return node["id"]


def _modules(root, node, built):
    """One box opened: the files in it, and what they import."""
    files = [f.replace("\\", "/") for f in (node.get("files") or [])]
    shown = files[:MAX_INSIDE]
    by_file = _file_index(built)
    dirs = {}
    for other in built["nodes"]:
        if other.get("dir"):
            dirs[other["dir"].replace("\\", "/")] = other

    taken = set()
    for other in built["nodes"]:
        taken.add(other["id"])
    ids, nodes, read = {}, [], {}
    for rel in shown:
        text = ""
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8",
                      errors="replace") as fh:
                text = fh.read(HEAD_BYTES)
        except OSError:
            text = ""
        read[rel] = text
        nid = _module_id(taken, rel)
        ids[rel] = nid
        nodes.append(_node(
            nid, os.path.basename(rel), "module",
            also=os.path.dirname(rel), dir=os.path.dirname(rel), files=[rel],
            does=_doc_of(rel, text) or _count(len(text.splitlines()), "line"),
            # WHETHER THIS ONE WOULD BE PARSED OR ONLY GREPPED, said before
            # anybody taps it. A box whose inside will be approximate has to
            # say so rather than look identical to one that will not.
            exact=symbols.exact(root, rel)))

    seen, found = set(), {}
    for rel in shown:
        for target in _module_paths(rel, read[rel]):
            here, there = _lands_in(target, set(shown), by_file, dirs)
            if here and here != rel:
                found[(ids[rel], ids[here])] = found.get((ids[rel], ids[here]), 0) + 1
            elif there is not None and there["id"] != node["id"]:
                to = _outside(nodes, seen, there)
                found[(ids[rel], to)] = found.get((ids[rel], to), 0) + 1

    return {
        "of": node["id"], "name": node["name"], "depth": "module",
        "kind": node["kind"], "up": "",
        "nodes": nodes,
        "edges": [{"from": a, "to": b, "weight": n, "label": ""}
                  for (a, b), n in sorted(found.items())],
        "exact": True,
        "total": len(files), "capped": len(files) > MAX_INSIDE,
        "why": "The files in %s, and what they import." % (node["name"],),
    }


def _symbol_map(root, rel, node, built, nid):
    """One module opened: what it defines, and what each definition uses."""
    said = symbols.of(root, rel)
    by_file = _file_index(built)
    dirs = {}
    for other in built["nodes"]:
        if other.get("dir"):
            dirs[other["dir"].replace("\\", "/")] = other

    taken = set(other["id"] for other in built["nodes"])
    nodes, ids = [], {}
    for d in said["defines"]:
        nid = _symbol_id(taken, rel, d["name"])
        ids[d["name"]] = nid
        nodes.append(_node(nid, d["name"], "symbol", also=d["kind"],
                           dir=os.path.dirname(rel), files=[rel],
                           does=d["does"], line=d["line"],
                           symbol=d["name"], exact=said["exact"]))

    # WHAT A USE OF SOMETHING IMPORTED POINTS AT, and it is the FILE where the
    # file is known rather than the box that holds it. `grade` using `tidy` from
    # `labels.py` next door is a fact about `labels.py`; rolling it up to
    # `evaluate` would draw an arrow from a symbol to the box the symbol is
    # already inside, which says nothing. The box is the fallback for an import
    # this repository owns but cannot pin to one file.
    walls = {}
    seen, found = set(), {}
    for d in said["defines"]:
        mine = ids[d["name"]]
        for used in list(d.get("bases") or []) + list(d.get("uses") or []):
            if used in ids and ids[used] != mine:
                found[(mine, ids[used])] = found.get((mine, ids[used]), 0) + 1
                continue
            where = (said.get("imports") or {}).get(used)
            if not where:
                continue
            there_rel, there = _lands_in(_import_path(rel, where[0]),
                                         set(by_file), by_file, dirs)
            to = ""
            if there_rel and there_rel != rel:
                if there_rel not in walls:
                    walls[there_rel] = _unique(
                        taken, _slug("in-" + there_rel, "module"))
                    nodes.append(_node(walls[there_rel],
                                       os.path.basename(there_rel), "module",
                                       also=os.path.dirname(there_rel),
                                       dir=os.path.dirname(there_rel),
                                       files=[there_rel], outside=True))
                to = walls[there_rel]
            elif there is not None and not there_rel:
                to = _outside(nodes, seen, there)
            if to:
                found[(mine, to)] = found.get((mine, to), 0) + 1

    return {
        "of": nid, "name": os.path.basename(rel),
        "depth": "symbol", "kind": "module", "up": node["id"],
        "nodes": nodes,
        "edges": [{"from": a, "to": b, "weight": n, "label": ""}
                  for (a, b), n in sorted(found.items())],
        # THE ONE FIELD A READER HAS TO BE TOLD. A Lean box found by a
        # line-anchored pattern must not be trusted as far as a Python box read
        # by `ast`, and the only way it cannot be is if the picture says so.
        "exact": said["exact"],
        "total": len(said["defines"]), "capped": bool(said.get("capped")),
        "why": said.get("why") or ("What %s defines, and what each definition "
                                   "uses." % (os.path.basename(rel),)),
    }


def inside(root, node_id, state=None, archived=None):
    """The picture one level below one box, or None.

    Two depths answer here, and which one is decided by what the id IS rather
    than by anything the caller says: a box on the top-level picture opens into
    its modules, and a module opens into its symbols. An id that is neither is
    a miss, and a miss is a miss -- the same rule as `find`, `walk.resolve` and
    `reading.find`.
    """
    built = status(root, state, archived)
    if not built:
        return None
    want = str(node_id or "").strip()
    if not want:
        return None
    for node in built["nodes"]:
        if node["id"] == want:
            if not (node.get("files") or []):
                return None
            return _modules(root, node, built)
    hit = _children(built).get(want)
    if not hit:
        return None
    node, rel = hit
    return _symbol_map(root, rel, node, built, want)


def of_tree(root, name, ident):
    """A vendor tree's picture, shaped like the inside of a box.

    THE BOARD HAS ONE MAP RENDERER AND THIS DOES NOT ADD A SECOND. `inside`
    already answers with a picture that is not the workspace's own -- a name, a
    depth, nodes, edges and a way back up -- and somebody else's repository is
    exactly that shape. So a tree is drawn by the surface that is already there,
    one level SIDEWAYS rather than one level down.

    No state and no plan. Nothing in a pulled repository is working, next, later
    or done, because none of it is work this side has taken on; every box comes
    back `unknown`, which is the honest answer rather than a missing one.

    `ident` is how `atlas.trees` spells the tree, and it is carried on the
    picture because a scope taken off a box here has to be spelt with the tree
    in it -- `walk.tree_label`. A foreign box whose scope was spelt the way a
    local one is would open a walkthrough over a path this workspace has not
    got.
    """
    built = status(root)
    if not built:
        return None
    return {
        "of": "", "name": name, "depth": "tree", "kind": "tree", "up": "",
        "tree": ident,
        "nodes": built["nodes"], "edges": built["edges"],
        "exact": True, "total": built["total"], "capped": False,
        # THE RULE ON THE PICTURE, where somebody is looking at it, rather than
        # only in the prompt of a sitting they have not opened yet.
        "why": ("%s is pulled and not written here: read it and trace it, and "
                "change nothing in it. %s" % (name, built["why"])),
    }


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


# ---------------------------------------------------------------------------
# the written map
# ---------------------------------------------------------------------------
# STRUCTURE IS DERIVED FROM DISK. MEANING IS WRITTEN BY THE TUTOR. NEITHER IS
# GUESSED.
#
# Everything above this line is honest and none of it is enough. Discovery can
# see that `psych_asr/asr` exists, that it imports `psych_asr/transcript`, and
# that a plan step names it. It cannot see that the box is called *the typist*,
# that it runs one candidate model and never compares them, or that the scorer
# below it is blocked on a seam that does not exist yet. Those are the sentences
# the owner of the project actually uses, and they are not derivable from a
# directory listing at any price.
#
# So a workspace may carry `live/map.json`: nodes that are STAGES OF THE WORK
# rather than directories, each carrying the files it is made of, with the three
# fields nothing else sets -- `blockedBy`, `doc` and `slide` -- and edges that
# say what flows along them.
#
# **It is merged against discovery on every read and never echoed back.** A node
# naming a file that has gone drops the file; a node whose files have all gone
# drops out; an edge naming an id that is not there is not an edge. Same rule as
# `walk.scope` and `review.scope`, and the same reason:
#
#     A FACT CANNOT GO STALE. A DECLARATION CAN. So a declaration is checked
#     against the facts every time it is read.
#
# Where a written map exists it REPLACES the derived one rather than being added
# to it -- two sets of boxes saying the same thing in two vocabularies is a
# picture nobody can read. The derived map stays the fallback for every
# workspace nobody has drawn, which is most of them.
#
# This is the one exception to "nothing is registered", alongside `atlas.json`'s
# family names, and it earns it by carrying judgement no file contains. Even it
# is re-resolved on every read.

WRITTEN_VERSION = 1

# An id is what everything keys off, including `localStorage`'s memory of which
# box the person was last looking at, so it is narrow and it is stable.
ID_RE = re.compile(r"^[a-z0-9-]{1,40}$")

# And a `doc` is an id too -- the one `reading.ident` gives a document, in the
# same alphabet for the same reason. Checked for SHAPE here because the natural
# mistake is to write the path instead, and a path and an id fail differently:
# an id that is not one of ours resolves to nothing, and a path would be
# resolved. `_resolve_written` silently blanks a `doc` that does not resolve,
# which is the right thing on a payload and the wrong thing to be told nothing
# about.
DOC_RE = re.compile(r"^[a-z0-9-]{1,40}$")

KINDS = ("part", "doc", "chapter", "set")

# An edge label is read on the arrow, at whatever zoom the plane is at. `words`,
# `turns`, `a graded transcript` -- what FLOWS, not a sentence about it.
EDGE_LABEL = 24

# A box blocked on nine things is a box nobody can act on, and the picture is
# for acting on.
MAX_BLOCKED = 8

# Long enough for a real name, short enough to sit in a box on a tablet.
MAX_NAME = 60
MAX_ALSO = 60


def written_path(root):
    """Where a workspace's written map lives. Tracked, unlike the rest of `live/`."""
    return os.path.join(root, "live", "map.json")


def _text(value, limit):
    out = str(value or "").strip()
    return out[:limit]


def validate(raw):
    """`(clean, problems)` -- and a written map with any problem is not written.

    REFUSED LOUDLY AND WHOLE, never half-applied. A map is one picture; a
    half-valid one is a picture with a hole in it, and the hole is exactly where
    the person made the mistake they would like to be told about. `board map`
    prints every problem at once, because fixing them one round trip at a time
    is how a five-minute job becomes an evening.

    Nothing in here touches the filesystem. What exists is `_resolve_written`'s
    question and it is asked again on every read; this one only asks whether the
    document says something a map could mean.
    """
    problems = []

    if not isinstance(raw, dict):
        return None, ["the top level must be an object, not a %s"
                      % type(raw).__name__]

    version = raw.get("version")
    if version != WRITTEN_VERSION:
        problems.append("version must be %d, not %r -- the shape of this file "
                        "is allowed to change and the number is how a reader "
                        "knows which shape it is looking at"
                        % (WRITTEN_VERSION, version))

    nodes_in = raw.get("nodes")
    if not isinstance(nodes_in, list) or not nodes_in:
        problems.append("`nodes` must be a non-empty list; a map with no boxes "
                        "on it is a blank plane between somebody and their work")
        nodes_in = []

    nodes, seen = [], {}
    for i, one in enumerate(nodes_in):
        where = "node %d" % (i + 1)
        if not isinstance(one, dict):
            problems.append("%s is not an object" % where)
            continue
        nid = str(one.get("id") or "").strip()
        if not ID_RE.match(nid):
            problems.append("%s: id %r must be 1-40 characters of a-z, 0-9 and "
                            "hyphen. Everything keys off it, including which box "
                            "the browser reopens on." % (where, nid))
            continue
        where = "node `%s`" % nid
        if nid in seen:
            problems.append("%s appears twice; an id names one box" % where)
            continue
        seen[nid] = True

        name = _text(one.get("name"), MAX_NAME)
        if not name:
            problems.append("%s has no `name`. THE PLAIN NAME LEADS -- *the "
                            "typist*, not `faster-whisper`; the real identifier "
                            "goes in `also`." % where)
        kind = str(one.get("kind") or "part").strip()
        if kind not in KINDS:
            problems.append("%s: kind %r is not one of %s"
                            % (where, kind, ", ".join(KINDS)))
            kind = "part"
        status_in = str(one.get("status") or "unknown").strip()
        if status_in not in STATUSES:
            problems.append("%s: status %r is not one of %s"
                            % (where, status_in, ", ".join(STATUSES)))
            status_in = "unknown"

        does = str(one.get("does") or "").strip()
        if len(does) > DOES:
            problems.append("%s: `does` is %d characters and the cap is %d. It "
                            "is read inside a box on a tablet, so it is one "
                            "sentence about what the thing does."
                            % (where, len(does), DOES))

        files = one.get("files") or []
        if not isinstance(files, list):
            problems.append("%s: `files` must be a list" % where)
            files = []
        clean_files = []
        for f in files:
            rel = str(f or "").strip().replace("\\", "/").lstrip("/")
            if not rel or rel == "." or ".." in rel.split("/"):
                problems.append("%s: %r is not a path inside this workspace"
                                % (where, f))
                continue
            clean_files.append(rel)

        d = str(one.get("dir") or "").strip().replace("\\", "/").strip("/")
        if ".." in d.split("/"):
            problems.append("%s: `dir` %r is not inside this workspace"
                            % (where, one.get("dir")))
            d = ""

        doc = str(one.get("doc") or "").strip()
        if doc and not DOC_RE.match(doc):
            problems.append("%s: `doc` %r is not a document id. It is the short "
                            "name `reading.py` gives a document -- lower case, "
                            "digits and hyphens, as `board read` lists them -- "
                            "and never a path. `board read` prints the ids."
                            % (where, one.get("doc")))
            doc = ""

        slide = one.get("slide")
        if slide is not None:
            if not isinstance(slide, int) or isinstance(slide, bool) or slide < 1:
                problems.append("%s: `slide` must be a page number from 1, not %r"
                                % (where, slide))
                slide = None

        blocked = one.get("blockedBy") or []
        if not isinstance(blocked, list):
            problems.append("%s: `blockedBy` must be a list of node ids" % where)
            blocked = []
        blocked = [str(b or "").strip() for b in blocked][:MAX_BLOCKED]

        nodes.append({
            "id": nid, "name": name, "also": _text(one.get("also"), MAX_ALSO),
            "kind": kind, "status": status_in, "does": does[:DOES],
            "files": clean_files[:MAX_FILES], "dir": d,
            "doc": doc,
            "slide": slide, "blockedBy": [b for b in blocked if b],
            "note": _text(one.get("note"), DOES),
            "chapter": _text(one.get("chapter"), MAX_NAME),
        })

    if len(nodes) > MAX_NODES:
        problems.append("%d boxes, and past %d it is not a picture any more. "
                        "Roll some of them up into the stage they belong to."
                        % (len(nodes), MAX_NODES))

    edges_in = raw.get("edges") or []
    if not isinstance(edges_in, list):
        problems.append("`edges` must be a list")
        edges_in = []
    edges = []
    for i, one in enumerate(edges_in):
        where = "edge %d" % (i + 1)
        if not isinstance(one, dict):
            problems.append("%s is not an object" % where)
            continue
        a = str(one.get("from") or "").strip()
        b = str(one.get("to") or "").strip()
        if a not in seen or b not in seen:
            problems.append("%s: %r -> %r names a box this file does not "
                            "declare" % (where, a, b))
            continue
        if a == b:
            problems.append("%s: %r points at itself" % (where, a))
            continue
        weight = one.get("weight", 1)
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
            weight = 1
        label = _text(one.get("label"), EDGE_LABEL)
        edges.append({"from": a, "to": b, "label": label, "weight": weight})

    # A node that says it is blocked by a box no edge and no node knows about is
    # a typo, and a typo in a `blockedBy` is invisible on the picture -- the box
    # simply never says why it is stuck.
    for node in nodes:
        for b in node["blockedBy"]:
            if b not in seen:
                problems.append("node `%s` is blockedBy `%s`, which this file "
                                "does not declare" % (node["id"], b))

    if problems:
        return None, problems

    return {
        "version": WRITTEN_VERSION,
        "title": _text(raw.get("title"), 90),
        "nodes": nodes,
        "edges": edges,
    }, []


def read_written(root):
    """What is on disk, validated. `(clean, problems)`; `(None, [])` if none.

    A file that is not there is not a problem -- most workspaces have no written
    map and the derived one is the right answer for them. A file that is there
    and is broken IS a problem, and it is reported rather than silently ignored,
    because a map somebody wrote and cannot see is worse than no map at all.
    """
    path = written_path(root)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError:
        return None, []
    except ValueError as exc:
        return None, ["%s is not valid JSON: %s" % (path, exc)]
    return validate(raw)


def write_written(root, raw):
    """Validate and store. `(problems, path)` -- nothing is written if any."""
    clean, problems = validate(raw)
    if problems:
        return problems, written_path(root)
    path = written_path(root)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".new"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        return ["could not write %s: %s" % (path, exc)], path
    _cache.pop(os.path.realpath(root), None)
    return [], path


def _here(root, rel):
    """Does this workspace really hold that path, and is it really inside it?"""
    if not rel:
        return False
    target = os.path.join(root, rel)
    if not toolpaths.within(target, root):
        return False
    return os.path.exists(target)


def _resolve_written(root, clean):
    """The written map, checked against the tree, every time it is read.

    This is the whole of why a written map is allowed to exist. What comes back
    is never what is on disk: it is what is on disk INTERSECTED with what is
    still there, so a map written in March is either true in September or
    visibly smaller.
    """
    nodes, dropped = [], set()
    for node in clean["nodes"]:
        node = dict(node)
        declared = list(node["files"])
        node["files"] = [f for f in declared if _here(root, f)]
        if declared and not node["files"]:
            # Every file it was made of has gone. The box is not a box any more.
            dropped.add(node["id"])
            continue
        if node["dir"] and not os.path.isdir(os.path.join(root, node["dir"])):
            node["dir"] = ""
        if node["doc"]:
            found, _name = reading.find(root, node["doc"])
            if not found:
                node["doc"] = ""
                node["slide"] = None
        nodes.append(node)

    alive = set(n["id"] for n in nodes)
    for node in nodes:
        node["blockedBy"] = [b for b in node["blockedBy"] if b in alive]

    edges = [dict(e) for e in clean["edges"]
             if e["from"] in alive and e["to"] in alive]

    return nodes, edges, dropped


def _from_written(root):
    """A repository whose owner has drawn it. Replaces the derived picture."""
    clean, problems = read_written(root)
    if not clean or problems:
        return None
    nodes, edges, _dropped = _resolve_written(root, clean)
    if not nodes:
        return None

    # THE DOCUMENTS NO BOX CLAIMS ARE BOXES OF THEIR OWN.
    #
    # A derived map builds one per document automatically -- TRD-EHR's carries
    # three, and tapping one offers *Show me the document*. A written map took
    # `doc` only from what its author typed on a node, so PSYCH-ASR's two
    # walkthrough decks -- the documents `reading.py` was written for -- were on
    # no box at all and reachable from the ⋯ menu and nowhere else. The
    # workspace's own `live/map.json` leaves every `doc` empty, which is what a
    # person writing a diagram of their pipeline does.
    #
    # So the map shows them without anybody hand-wiring each one, and `check`
    # names every one it added -- because a box the author did not draw on their
    # own diagram is something they should be told about and be able to claim.
    # Claiming it is one field: put the id in `doc` on the box it belongs to and
    # this stops adding it.
    #
    # They depend on nothing and nothing depends on them, so they stand apart
    # rather than being wired into the graph -- the same as on a derived map.
    added = _loose_docs(root, nodes)
    nodes += added

    # The plan's steps land on written boxes the same way they land on derived
    # ones, by the paths the step NAMES -- so a box called *the typist* still
    # collects the step that talks about `psych_asr.cli.run_asr`. Its files and
    # its directory are both what it answers to.
    by_dir = {}
    for node in nodes:
        owned = list(node["files"])
        if node["dir"]:
            owned.append(node["dir"])
        by_dir[node["id"]] = owned
    on, loose = _attach(_plan_steps(root), by_dir)
    for node in nodes:
        node["steps"] = on.get(node["id"], [])[:MAX_CHIPS]

    return {
        "title": clean["title"],
        "nodes": nodes,
        "edges": edges,
        "loose": loose,
        "why": "Drawn by hand in live/map.json, and re-checked against the "
               "tree on every read."
               + ("" if not added else
                  " One document is on no box in it, so the map shows it as one "
                  "of its own." if len(added) == 1 else
                  " %d documents are on no box in it, so the map shows each as "
                  "one of its own." % len(added)),
        "written": True,
    }


# How many unclaimed documents may become boxes. `_from_code`'s own limit, and
# for the same reason: a reference library is thirty PDFs and a picture is not.
MAX_LOOSE_DOCS = 8


def _loose_docs(root, nodes):
    """A box per document this workspace offers that no written box claims.

    `also` says `document` and `does` says what it is, which is how a person
    reading their own diagram can tell which boxes they drew -- and `check`
    lists every one of these by name so the answer is not only on the picture.
    """
    claimed = set(n["doc"] for n in nodes if n.get("doc"))
    taken = set(n["id"] for n in nodes)
    # Past `MAX_NODES` it is not a picture, and that is true of a box the map
    # added as much as of one the author drew.
    room = min(MAX_LOOSE_DOCS, max(0, MAX_NODES - len(nodes)))
    out = []
    for d in _documents(root):
        if len(out) >= room:
            break
        if d["id"] in claimed:
            continue
        nid = _unique(taken, _slug("doc-" + d["id"], "doc"))
        out.append(_node(nid, d["name"], "doc", also="document",
                         doc=d["id"], blockedBy=[],
                         does="Written about how this works."))
    return out


def _documents(root):
    try:
        return reading.documents(root)
    except Exception:                                        # noqa: BLE001
        return []


def check(root, documents=True):
    """What has gone stale in the written map. The list `board map --check` prints.

    `documents=False` leaves out the documents no box claims, which is what
    `written_status` counts. A deck nobody has placed is worth saying once and
    it is not the map having gone stale: it never clears unless the author
    decides to claim it, and a permanent 2 on a briefing is a number that stops
    being read.

    Everything here is something the resolver would silently SWALLOW on the next
    read -- a file dropped, a box dropped, an edge dropped -- plus the one thing
    it cannot see, which is a box claiming to be `done` while the plan still has
    an open step sitting on it. Silent correctness is right for a payload painted
    four times a second and wrong for a person asking what needs attention.
    """
    clean, problems = read_written(root)
    if problems:
        return problems
    if not clean:
        return []

    out = []
    nodes, edges, dropped = _resolve_written(root, clean)
    alive = set(n["id"] for n in nodes)

    for node in clean["nodes"]:
        gone = [f for f in node["files"] if not _here(root, f)]
        if node["id"] in dropped:
            out.append("`%s` (%s) is gone from the picture: every file it was "
                       "made of has been moved or deleted -- %s"
                       % (node["id"], node["name"], ", ".join(gone[:4])))
            continue
        for f in gone:
            out.append("`%s` names %s, which is not there any more"
                       % (node["id"], f))
        if node["dir"] and not os.path.isdir(os.path.join(root, node["dir"])):
            out.append("`%s` sits in %s/, which is not there any more"
                       % (node["id"], node["dir"]))
        if node["doc"]:
            found, _name = reading.find(root, node["doc"])
            if not found:
                out.append("`%s` points at the document `%s`, which this "
                           "workspace does not offer any more"
                           % (node["id"], node["doc"]))
        for b in node["blockedBy"]:
            if b not in alive:
                out.append("`%s` is blocked by `%s`, which is no longer on the "
                           "picture" % (node["id"], b))

    for e in clean["edges"]:
        if e["from"] not in alive or e["to"] not in alive:
            out.append("the arrow %s -> %s has lost an end"
                       % (e["from"], e["to"]))

    # A DOCUMENT NO BOX CLAIMS. Reported rather than left to be noticed: the map
    # puts it on the picture as a box of its own, which is right for a deck
    # nobody has placed and wrong for one that belongs on a stage the author has
    # already drawn. Both are one field apart, and this is the line that says
    # which boxes on the picture the author did not draw.
    claimed = set(n["doc"] for n in clean["nodes"] if n.get("doc"))
    for d in (_documents(root) if documents else []):
        if d["id"] not in claimed:
            out.append("the document `%s` (%s) is on no box, so the map shows "
                       "it as one of its own. Put its id in `doc` on the box it "
                       "belongs to if it belongs on one." % (d["id"], d["rel"]))

    # A box that says `done` with an open step on it. The plan is the fact and
    # the status is the declaration, so the plan wins and the person is told.
    on, _loose = _attach(_plan_steps(root),
                         dict((n["id"], list(n["files"])
                               + ([n["dir"]] if n["dir"] else []))
                              for n in nodes))
    for node in nodes:
        if node["status"] == "done" and on.get(node["id"]):
            steps = ", ".join(s["label"] for s in on[node["id"]][:3])
            out.append("`%s` is marked done, but the plan still has %s on it"
                       % (node["id"], steps))

    return out


def written_status(root):
    """Whether this workspace has a written map, and when it was written.

    `board brief` shows it so a tutor knows whether it is looking at somebody's
    own words or at a directory listing, and the atlas shows the title. A tutor
    that cannot tell the two apart will believe a derived map is what the person
    thinks, which is the one thing this whole section exists to prevent.
    """
    path = written_path(root)
    try:
        when = os.path.getmtime(path)
    except OSError:
        return {"has": False, "title": "", "written": 0, "nodes": 0,
                "stale": 0, "problems": []}
    clean, problems = read_written(root)
    if problems or not clean:
        return {"has": True, "title": "", "written": when, "nodes": 0,
                "stale": 0, "problems": problems or ["unreadable"]}
    nodes, _edges, _dropped = _resolve_written(root, clean)
    return {"has": True, "title": clean["title"], "written": when,
            "nodes": len(nodes), "stale": len(check(root, documents=False)),
            "problems": []}


def _shape(root):
    """The picture, with no judgement in it yet.

    THE WRITTEN MAP IS TRIED FIRST AND IT REPLACES THE DERIVED ONE. Not merged
    with it: `psych_asr/asr` and *the typist* on one picture is the same thing
    said twice in two vocabularies, and the person reading it has to work out
    that they are the same thing before they can use either. Where somebody has
    drawn their project, that drawing IS the map; the three derivations below
    are the fallback for every workspace nobody has drawn, which is most of them.
    """
    for build in (_from_written, _from_chapters, _from_code, _from_parts):
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
        # WHETHER THERE IS ANYTHING UNDER THIS BOX, said on the box rather than
        # discovered by tapping it and getting nothing. A chapter and a
        # document have no inside; a part does, and so does a hand-drawn box
        # that claims real files -- which is how the derived structure appears
        # INSIDE a name a person chose rather than replacing it.
        node["inside"] = len(node.get("files") or [])
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
        # WHOSE WORDS THESE ARE. A tutor handed a derived map and a written one
        # with no way to tell them apart will read a directory listing as what
        # the person thinks about their own project, which is the single thing
        # this distinction exists to prevent.
        "written": bool(found.get("written")),
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


def scoped(root):
    """Is a sitting in this workspace ABOUT a box, or about a chapter?

    A COURSE IS CHAPTERS AND A PROJECT IS COMPONENTS, and the difference is not
    a preference about how to work -- it is what the workspace is. A lecture on
    Chapter 4 of Galois Theory has no component to be scoped to: the chapter IS
    the scope, and asking which box it belongs to is a question with no answer.
    A sitting in a repository made of parts does have one, and a sitting that
    has not got it is working on whatever it happened to read first.

    So the rule is a property of the SHAPE rather than of the whole board, and
    the shape is already decided here. A `part` is a piece of the repository
    somebody can work IN; a `chapter`, a `set` and a `doc` are things to work
    FROM. One `part` on the picture makes this a workspace where a box is the
    scope -- including a hand-drawn map, whose author chose the word.
    """
    found = shape(root)
    if not found:
        return False
    return any(n.get("kind") == "part" for n in found["nodes"])


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
