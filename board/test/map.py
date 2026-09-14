#!/usr/bin/env python3
"""The map is of the CONTENT, and none of it is invented.

The first version of this drew the plan: twelve steps in a column. It was
rejected in those terms -- *"I don't want just a list of all the TODOs. I want a
map of the CONTENT in the repository"* -- and rightly, because a column of steps
is a list wearing a diagram's clothes. So the boxes are the repository's own
parts, the arrows are what actually imports what, and the outstanding work is
numbered chips drawn ON that picture.

What the checks are actually about, in the order they cost something:

  * AN ARROW IS A CLAIM. Every edge has to come from an import that is really in
    a file, resolving to a directory that really exists. An arrow drawn between
    two boxes that have nothing to do with each other is worse than no diagram,
    because somebody will believe it.
  * A CHIP IS A CLAIM ABOUT WHERE THE WORK IS. A step goes on a box only when it
    names something in that box -- and a step that names nothing comes back in
    the tray rather than being dropped, because what to do next is the person's
    choice and a choice they cannot see is not one.
  * THE PAYLOAD IS REBUILT FOUR TIMES A SECOND. This is the only discovery on
    the board that opens files rather than listing them, and reading all 177
    solutions in Algo-Solutions whole took 3.8 seconds in the thread that paints
    every board.
  * A BOOK COURSE MUST NOT BE MADE WORSE. Galois Theory and Probability already
    worked; their content is chapters, and a README that happens to name a TODO
    must not take them away.
  * A NODE ID FROM A BROWSER IS LOOKED UP, NEVER CONSTRUCTED. Same rule as
    `walk.resolve` and `reading.find`: a miss is a miss.
"""

import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import config, plan, walk                      # noqa: E402
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


PAD = "\n" + ("# padding, to clear the size floor on a walkable file\n" * 12)


def by_name(m):
    return dict((n["name"], n) for n in m["nodes"])


def by_id(m):
    return dict((n["id"], n) for n in m["nodes"])


TODO = """PROJECT — REMAINING WORK

>>> NEXT ACTION (start here in a fresh session) <<<
  STEP 1. THE TYPIST BAKE-OFF — VARY THE ASR MODEL. (Added 2026-09-09.)
    The user's call, and it is first. Grade each candidate's words against the
    corrected reference, and report WER separately from the counts that matter.
    The entry point is psych_asr.cli.grade_arms and the grading itself is
    psych_asr/evaluate/grade.py.
  STEP 2. THE STOPWATCH. (Added 2026-09-09.)
    Re-align the corrected words to the waveform. Lives in psych_asr/asr/align.py.
  STEP 3. BUY A BIGGER DESK.
    Nothing in this repository. There is no file to put this on and it must not
    be put on one anyway.
"""

home = tempfile.mkdtemp(prefix="tutor-map-home-")
proj = os.path.join(home, "PSYCH-ASR")
book = os.path.join(home, "Galois-Theory")
flat = os.path.join(home, "Algo-Solutions")
bare = os.path.join(home, "Nothing-Here")

try:
    # --- a repository made of code: its parts, and what depends on what ------
    write(os.path.join(proj, "PSYCH-ASR_TODO.txt"), TODO)
    write(os.path.join(proj, "README.md"),
          "# PSYCH-ASR\n\nThe live task list is `PSYCH-ASR_TODO.txt`.\n")
    write(os.path.join(proj, "psych_asr", "artifacts", "__init__.py"),
          '"""artifacts.py -- the Stage 1 filename convention, in one place."""\n' + PAD)
    write(os.path.join(proj, "psych_asr", "artifacts", "naming.py"),
          "def stem(x):\n    return x\n" + PAD)
    write(os.path.join(proj, "psych_asr", "evaluate", "__init__.py"),
          '"""Grading a machine transcript the way the annotator graded the first."""\n' + PAD)
    write(os.path.join(proj, "psych_asr", "evaluate", "grade.py"),
          "from ..artifacts.naming import stem\n\ndef grade(a, b):\n    return stem(a)\n" + PAD)
    write(os.path.join(proj, "psych_asr", "asr", "__init__.py"),
          '"""Stage 1a: Whisper transcription, then forced alignment."""\n' + PAD)
    write(os.path.join(proj, "psych_asr", "asr", "align.py"),
          "from ..artifacts import naming\n\ndef align(w):\n    return w\n" + PAD)
    write(os.path.join(proj, "psych_asr", "cli", "grade_arms.py"),
          "from ..evaluate.grade import grade\nfrom ..asr.align import align\n"
          "\ndef main():\n    return grade, align\n" + PAD)
    # A cycle, which real imports have and a depth that ran away on one would
    # push off the edge of the picture.
    write(os.path.join(proj, "psych_asr", "artifacts", "back.py"),
          "from ..evaluate import grade\n\ndef back():\n    return grade\n" + PAD)
    fresh()

    m = mapping.status(proj, {}, [])
    seen = by_name(m)
    check("the boxes are the repository's own parts, not its task list",
          m and set(["artifacts", "asr", "cli", "evaluate"]).issubset(seen))
    check("and a part says what it is in its own words, off its own docstring",
          seen["evaluate"]["does"].startswith("Grading a machine transcript"))
    check("a part with no docstring says what it is made of instead",
          seen["cli"]["does"] == "1 source file")
    check("and a box knows the files it is made of, for the sitting a tap opens",
          seen["evaluate"]["files"] == [os.path.join("psych_asr", "evaluate", "grade.py")])

    # --- the arrows are real imports ----------------------------------------
    ids = by_id(m)
    arrows = set((ids[e["from"]]["name"], ids[e["to"]]["name"]) for e in m["edges"])
    check("an arrow is an import that is really in a file",
          ("cli", "evaluate") in arrows and ("evaluate", "artifacts") in arrows)
    check("a relative import is followed from the file that makes it",
          ("asr", "artifacts") in arrows)
    check("and nothing is joined to something it never mentions",
          ("asr", "evaluate") not in arrows and ("artifacts", "asr") not in arrows)
    check("every arrow joins two boxes that are actually on the map",
          all(e["from"] in ids and e["to"] in ids for e in m["edges"]))
    check("a cycle is drawn rather than hidden: real imports go round in circles",
          ("artifacts", "evaluate") in arrows)
    check("an arrow says how much it carries, so a heavy one can be drawn heavy",
          all(isinstance(e["weight"], int) and e["weight"] >= 1 for e in m["edges"]))

    # --- the work, on the box it is about ------------------------------------
    check("a step goes on the box it names",
          [s["order"] for s in seen["evaluate"]["steps"]] == [1]
          or [s["order"] for s in seen["cli"]["steps"]] == [1])
    check("and step 2 lands on the part it actually names",
          [s["order"] for s in seen["asr"]["steps"]] == [2])
    check("a step naming nothing in the repository is not put on a box anyway",
          not any(s["order"] == 3 for n in m["nodes"] for s in n["steps"]))
    check("it comes back in the tray instead, so the choice is still offered",
          [s["order"] for s in m["loose"]] == [3])
    check("a chip carries its number, its title and where it falls in the order",
          m["loose"][0]["num"] == "3" and m["loose"][0]["title"]
          and m["loose"][0]["label"])
    check("and the map counts every step there is, placed or not",
          m["steps"] == 3)

    # THE DEFECT THIS EXISTS TO PREVENT. `plan.steps` trims a step to 240
    # characters for a drawer, and the module names that say which part a step is
    # about are further down the body than that -- with the blurb alone, not one
    # step in PSYCH-ASR matched a box and every chip fell into the tray.
    steps = plan.steps(proj)
    check("a step is matched against the whole of what the plan says about it",
          len(steps[0]["summary"]) <= plan.SUMMARY + 1
          and "grade.py" in mapping._step_text(steps[0], {}))

    # --- a box carrying the first step is where the work goes next -----------
    check("the box carrying step 1 is where the work goes next",
          any(n["status"] == "next" for n in m["nodes"]))
    check("a box carrying a later step says later",
          seen["asr"]["status"] == "later")
    check("and a box with no outstanding work does not claim any",
          seen["artifacts"]["status"] == "unknown")
    fresh()
    m2 = mapping.status(proj, {"node": by_name(m)["asr"]["id"]}, [])
    check("the box this sitting is about is the one being worked on",
          by_name(m2)["asr"]["status"] == "working")

    # --- a book course, and the one that also has a task list ----------------
    write(os.path.join(book, "chapters.tsv"),
          "1\t1\t20\tgroups\tGroups, fields and vector spaces\n"
          "2\t21\t40\trings\tRings\n"
          "3\t41\t60\tfields\tField extensions\n")
    write(os.path.join(book, "homework", "hw01", "hw01.tex"),
          "\\begin{problem}{1}\n\\end{problem}\n")
    fresh()
    m = mapping.status(book, {}, [])
    ids = by_id(m)
    check("a book course's content is its chapters",
          len([n for n in m["nodes"] if n["kind"] == "chapter"]) == 3)
    check("and its problem sets are content too",
          [n["name"] for n in m["nodes"] if n["kind"] == "set"] == ["hw01"])
    check("a book is read in order, and the map says so",
          ("ch-1", "ch-2") in set((e["from"], e["to"]) for e in m["edges"]))

    # THE REGRESSION THIS EXISTS TO PREVENT. Galois Theory and Probability were
    # the two repositories that already worked well.
    write(os.path.join(book, "TODO.md"), "- [ ] typeset chapter four\n")
    write(os.path.join(book, "README.md"),
          "# Galois Theory\n\nWhat is left is in `TODO.md`.\n")
    fresh()
    check("a book course with a task list still draws its chapters",
          mapping.status(book, {}, [])["nodes"][0]["kind"] == "chapter")

    fresh()
    m = mapping.status(book, {"chapter": "Ch 2 — Rings"},
                       [{"chapter": "Ch 1 — Groups, fields and vector spaces"}])
    ids = by_id(m)
    check("a chapter with a lesson already filed against it is done",
          ids["ch-1"]["status"] == "done")
    check("the chapter open right now is the one being worked on",
          ids["ch-2"]["status"] == "working")
    check("and a chapter nobody has touched says so rather than guessing",
          ids["ch-3"]["status"] == "unknown")

    # --- neither code nor a book --------------------------------------------
    write(os.path.join(flat, "notes", "a.txt"), "not source\n")
    os.makedirs(os.path.join(flat, "puzzles"), exist_ok=True)
    write(os.path.join(flat, "puzzles", "keep.md"), "not source\n")
    fresh()
    m = mapping.status(flat, {}, [])
    check("a repository with neither draws its own top-level parts",
          m and sorted(n["name"] for n in m["nodes"]) == ["notes/", "puzzles/"])

    # --- a repository with nothing in it is not an empty plane ---------------
    os.makedirs(bare, exist_ok=True)
    fresh()
    check("a repository with nothing in it returns no map rather than an empty one",
          mapping.status(bare, {}, []) is None)

    # --- a name from a browser is looked up, never constructed ---------------
    fresh()
    known = mapping.status(proj, {}, [])["nodes"][0]["id"]
    check("a box is found by the id discovery gave it",
          (mapping.find(proj, known) or {}).get("id") == known)
    for made_up in ("../../etc/passwd", "psych_asr/cli", "PSYCH-ASR-CLI", "",
                    "nothing-of-the-sort", None):
        check("an id that matches nothing resolves to nothing: %r" % (made_up,),
              mapping.find(proj, made_up) is None)

    # --- the shape of every node, so nothing downstream has to guess ---------
    fresh()
    every = (mapping.status(proj, {}, [])["nodes"]
             + mapping.status(book, {}, [])["nodes"])
    check("every box has every field, always",
          all(set(["id", "name", "also", "kind", "does", "status", "files",
                   "dir", "steps", "doc", "slide", "note"]).issubset(n)
              for n in every))
    check("and a status the board knows how to paint",
          all(n["status"] in mapping.STATUSES for n in every))
    check("an id is short, stable, and made only of what an id may contain",
          all(n["id"] and len(n["id"]) <= 40
              and all(c.islower() or c.isdigit() or c == "-" for c in n["id"])
              for n in every))
    check("and no two boxes share one",
          len(set(n["id"] for n in every)) == len(every))
    check("what a box says it does fits in a box",
          all(len(n["does"]) <= mapping.DOES + 1 for n in every))

    # --- the payload is rebuilt four times a second --------------------------
    fresh()
    started = time.time()
    mapping.status(proj, {}, [])
    cold = time.time() - started
    check("a cold build is fast enough to sit in the payload loop (%.0fms)"
          % (cold * 1000), cold < 1.0)
    check("a directory of a hundred files is sampled, not read whole",
          mapping.MAX_SCAN <= 40 and mapping.HEAD_BYTES <= 20000)
    mapping._cache[os.path.realpath(proj)] = (time.time(),
                                              {"title": "", "nodes": [], "edges": [],
                                               "loose": [], "why": "cached"})
    check("the shape is remembered rather than re-derived on every payload",
          mapping.shape(proj)["why"] == "cached")
    check("and the cache is short enough that an edit this evening lands",
          mapping.CACHE_SECONDS <= 60)

    # --- what a sitting opened from a box is FOR -----------------------------
    check("an aim from a request is one of the ways to work, or nothing",
          config.clean_aim("BUILD ") == "build"
          and config.clean_aim("whatever") is None)
    check("and every aim says in writing what it asks the tutor to do",
          all(config.AIM_MEANS.get(a) for a in config.AIMS))

    # --- a map is not a thing to be configured -------------------------------
    src = open(os.path.join(ROOT, "tutorboard", "course", "map.py"),
               encoding="utf-8").read()
    check("nothing here registers, indexes or declares anything",
          "discover" in src.lower() and "registr" not in src.lower())

finally:
    shutil.rmtree(home, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the map is of the content, and none of it is invented")
