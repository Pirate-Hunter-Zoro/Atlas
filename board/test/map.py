#!/usr/bin/env python3
"""Every repository gets a map, and none of it is invented.

A course used to open on an empty board. It opens on a picture of its working
parts now, and the property that makes that safe to ship into ten repositories
at once is the one this file guards: **the map falls back rather than refusing.**
A book course draws its chapters, a project draws the steps it has written down,
and anything else draws its own top-level parts -- so there is no repository
that opens on a blank plane and no repository that has to be configured first.

Three failures are what the checks are actually about:

  * A BOOK COURSE THAT ALSO HAS A TODO must still draw its chapters. Galois
    Theory and Probability are the two repositories on this board that were
    already painless, and a map that showed them a task list instead of their
    chapters would be a regression dressed as a feature.
  * A NODE ID ARRIVING FROM A BROWSER must be looked up in what discovery found,
    never constructed. Same rule as `walk.resolve` and `reading.find`: a miss is
    a miss.
  * A DERIVED STATUS MUST NOT CLAIM MORE THAN IS KNOWN. `unknown` is the honest
    answer for most of a skeleton, and painting a box as finished because a file
    under it was edited this morning would make the map agree with whatever was
    touched last rather than with what is true.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import homework, plan, review, syllabus, walk   # noqa: E402
from tutorboard.course import map as mapping                          # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def fresh():
    """Every discovery underneath this remembers itself for half a minute."""
    mapping._cache.clear()
    plan._cache.clear()
    walk._cache.clear()


TODO = """PROJECT — REMAINING WORK

>>> NEXT ACTION (start here in a fresh session) <<<
  STEP 1. THE TYPIST BAKE-OFF — VARY THE ASR MODEL. (Added 2026-09-09.)
    Grade each candidate's words against the corrected reference.
  STEP 2. THE STOPWATCH — AND THE REFERENCE RTTM IT UNBLOCKS. (Added 2026-09-09.)
    Re-align the corrected words to the waveform.
  STEP 3. THE GRID, WHICH IS A CUBE. (Added 2026-09-09.)
    4 x 2 x 5 = 40 cells, from 13 jobs.
"""

home = tempfile.mkdtemp(prefix="tutor-map-home-")
proj = os.path.join(home, "PSYCH-ASR")
book = os.path.join(home, "Galois-Theory")
flat = os.path.join(home, "Algo-Solutions")
bare = os.path.join(home, "Nothing-Here")

try:
    # --- a project: its plan, in one lane, with source under its parts -------
    write(os.path.join(proj, "PSYCH-ASR_TODO.txt"), TODO)
    write(os.path.join(proj, "README.md"),
          "# PSYCH-ASR\n\nThe live task list is `PSYCH-ASR_TODO.txt`.\n")
    write(os.path.join(proj, "psych_asr", "transcript", "corrections.py"),
          "def apply_corrections(words):\n    " + "return words\n" + "# pad\n" * 40)
    fresh()

    m = mapping.status(proj, {}, [])
    check("a project with a plan gets a node for every step it wrote down",
          m and len(m["nodes"]) == 3)
    check("in the plan's own order, never re-sorted",
          [n["step"] for n in m["nodes"]] == ["1", "2", "3"])
    check("and the box is named the way the plan names it",
          m["nodes"][0]["name"] == "THE TYPIST BAKE-OFF — VARY THE ASR MODEL")
    # The heading is already written across the top of the box in bold. A `does`
    # that opens with the same words spends the whole box saying it twice.
    check("what a box says it does is not its own name again",
          not m["nodes"][0]["does"].upper().startswith("THE TYPIST BAKE-OFF"))
    check("and the date stamp a reader of the plan wants is not in the box",
          "Added" not in m["nodes"][0]["does"])
    check("a plan lists what is LEFT, so the first step is next and the rest later",
          [n["status"] for n in m["nodes"]] == ["next", "later", "later"])
    check("and the map says where it was drawn from",
          m["fallback"] and "PSYCH-ASR_TODO.txt" in m["why"])

    # A step is opened by the label the plan gives it, which is what the drawer
    # already files a sitting under. Two spellings of one step would file two
    # lessons for the same piece of work.
    check("a node carries the label a sitting over it would be filed under",
          m["nodes"][0]["chapter"] == "1. THE TYPIST BAKE-OFF — VARY THE ASR MODEL")

    # --- the sitting that is open right now is the one being worked on -------
    fresh()
    here = {"chapter": "2. THE STOPWATCH — AND THE REFERENCE RTTM IT UNBLOCKS"}
    m = mapping.status(proj, here, [])
    check("the sitting open right now is the box being worked on",
          [n["status"] for n in m["nodes"]] == ["next", "working", "later"])

    # --- a hub holds three projects' plans and owns none of them -------------
    hub = os.path.join(home, "Research-Journey")
    write(os.path.join(hub, "planning", "A-PROJECT_TODO.txt"),
          "STEP 1. FIRST THING.\n  For A.\n")
    write(os.path.join(hub, "planning", "B-PROJECT_TODO.txt"),
          "STEP 1. OTHER THING.\n  For B.\n")
    write(os.path.join(hub, "README.md"),
          "# Research-Journey\n\nIt holds `planning/A-PROJECT_TODO.txt` and\n"
          "`planning/B-PROJECT_TODO.txt`.\n")
    fresh()
    m = mapping.status(hub, {}, [])
    check("a hub's map is one lane per project it holds the plan for",
          m and m["lanes"] == ["A-PROJECT", "B-PROJECT"])
    check("and every step is in the lane of the project it belongs to",
          sorted(set(n["lane"] for n in m["nodes"])) == ["A-PROJECT", "B-PROJECT"])

    # --- a book course, and the one that also has a task list ----------------
    write(os.path.join(book, "chapters.tsv"),
          "1\t1\t20\tgroups\tGroups, fields and vector spaces\n"
          "2\t21\t40\trings\tRings\n"
          "3\t41\t60\tfields\tField extensions\n")
    write(os.path.join(book, "homework", "hw01", "hw01.tex"),
          "\\begin{problem}{1}\n\\end{problem}\n")
    fresh()
    m = mapping.status(book, {}, [])
    check("a book course gets a node per chapter",
          m and len([n for n in m["nodes"] if n["lane"] == "chapters"]) == 3)
    check("and its problem sets in a lane beside them",
          [n["name"] for n in m["nodes"] if n["lane"] == "problem sets"] == ["hw01"])
    check("a book is read in order, and the map says so",
          len(m["edges"]) == 2
          and m["edges"][0]["from"] == "ch-1" and m["edges"][0]["to"] == "ch-2")

    # THE REGRESSION THIS EXISTS TO PREVENT. Galois Theory and Probability were
    # the two repositories that already worked well. A README that happens to
    # name a TODO must not take their chapters away from them.
    write(os.path.join(book, "TODO.md"), "- [ ] typeset chapter four\n")
    write(os.path.join(book, "README.md"),
          "# Galois Theory\n\nWhat is left is in `TODO.md`.\n")
    fresh()
    check("a book course with a task list still draws its chapters",
          [n["lane"] for n in mapping.status(book, {}, [])["nodes"]][0] == "chapters")

    # --- what the board genuinely knows about a chapter ----------------------
    fresh()
    m = mapping.status(book, {"chapter": "Ch 2 — Rings"},
                       [{"chapter": "Ch 1 — Groups, fields and vector spaces"}])
    by = dict((n["id"], n) for n in m["nodes"])
    check("a chapter with a lesson already filed against it is done",
          by["ch-1"]["status"] == "done")
    check("the chapter open right now is the one being worked on",
          by["ch-2"]["status"] == "working")
    check("and a chapter nobody has touched says so rather than guessing",
          by["ch-3"]["status"] == "unknown")

    # --- anything else: the repository's own parts ---------------------------
    write(os.path.join(flat, "leetcode", "two_sum.go"),
          "package main\n\nfunc twoSum() {}\n" + "// pad\n" * 40)
    write(os.path.join(flat, "helpermath", "gcd.go"),
          "package main\n\nfunc gcd() {}\n" + "// pad\n" * 40)
    fresh()
    m = mapping.status(flat, {}, [])
    check("a repository with neither chapters nor a plan draws its own parts",
          m and sorted(n["name"] for n in m["nodes"]) == ["helpermath/", "leetcode/"])
    check("and each part carries the source under it, for the sitting a tap opens",
          dict((n["name"], n["files"]) for n in m["nodes"])["helpermath/"]
          == [os.path.join("helpermath", "gcd.go")])
    check("a part with one file does not say it has one files",
          dict((n["name"], n["does"]) for n in m["nodes"])["leetcode/"]
          == "1 source file")

    # --- a repository with nothing in it is not an empty plane ---------------
    os.makedirs(bare, exist_ok=True)
    fresh()
    check("a repository with nothing in it returns no map rather than an empty one",
          mapping.status(bare, {}, []) is None)

    # --- a name from a browser is looked up, never constructed ---------------
    fresh()
    check("a node is found by the id discovery gave it",
          (mapping.find(flat, "leetcode") or {}).get("name") == "leetcode/")
    for made_up in ("../../etc/passwd", "leetcode/", "LEETCODE", "",
                    "nothing-of-the-sort", None):
        check("an id that matches nothing resolves to nothing: %r" % (made_up,),
              mapping.find(flat, made_up) is None)

    # --- the shape of every node, so nothing downstream has to guess ---------
    fresh()
    every = mapping.status(proj, {}, [])["nodes"] + mapping.status(book, {}, [])["nodes"]
    check("every node has every field, always",
          all(set(["id", "name", "also", "lane", "does", "status", "files",
                   "step", "doc", "slide", "note"]).issubset(n) for n in every))
    check("and a status the board knows how to paint",
          all(n["status"] in mapping.STATUSES for n in every))
    check("an id is short, stable, and made only of what an id may contain",
          all(n["id"] and len(n["id"]) <= 40
              and all(c.islower() or c.isdigit() or c == "-" for c in n["id"])
              for n in every))
    check("and no two boxes share one",
          len(set(n["id"] for n in every)) == len(every))

    # An edge naming a box that is not on the map is not an edge. The renderer
    # drops it, and so does this: a picture with an arrow to nowhere in it is a
    # picture somebody will read a dependency out of.
    fresh()
    m = mapping.status(book, {}, [])
    ids = set(n["id"] for n in m["nodes"])
    check("every edge joins two boxes that are actually on the map",
          all(e["from"] in ids and e["to"] in ids for e in m["edges"]))

    # --- one sentence in a box, and it fits ---------------------------------
    check("what a box says it does fits in a box",
          all(len(n["does"]) <= mapping.DOES + 1 for n in every))

    # --- the payload is rebuilt four times a second -------------------------
    # Everything under this is a directory walk. A map that re-derived itself on
    # every poll would be a walk of the repository four times a second on a
    # shared filesystem. Same rule as `walk.units` and `plan.steps`.
    fresh()
    mapping.status(flat, {}, [])
    mapping._cache[os.path.realpath(flat)] = (mapping.time.time(),
                                              {"title": "cached", "lanes": ["x"],
                                               "nodes": [], "edges": [],
                                               "why": ""})
    check("the shape is remembered rather than re-derived on every payload",
          mapping.shape(flat)["title"] == "cached")
    check("and the cache is short enough that a plan edited this evening lands",
          mapping.CACHE_SECONDS <= 60)

    # --- a map is not a thing to be configured ------------------------------
    src = open(os.path.join(ROOT, "tutorboard", "course", "map.py"),
               encoding="utf-8").read()
    check("nothing here registers, indexes or declares anything",
          "discovery" in src.lower() and "registr" not in src.lower())

finally:
    shutil.rmtree(home, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("every repository gets a map, and none of it is invented")
