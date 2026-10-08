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
  * A THREAD FILE IS A DECLARATION, AND A DECLARATION CAN GO STALE. So it is
    checked against the tree on every read: a file that has gone drops out of
    its thread, a document no longer offered is cleared, and `--check` says
    aloud what the file claims that the tree does not.
"""

import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import (config, library, plan, reading,      # noqa: E402
                               threads, walk)
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
    threads._cache.clear()
    plan._cache.clear()
    walk._cache.clear()
    reading._cache.clear()


def pdf(path):
    """Something big enough to be taken for a document, without a LaTeX run."""
    write(path, "%PDF-1.4\n" + ("%% filler line to clear the size floor\n" * 900))


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

    # --- A BOX WITH NO STEP ON IT IS KNOWN TO HAVE NONE ---------------------
    # Not silently empty, and the difference is what a hand-off spends. When a
    # sitting hands the work to another box, the card PROPOSES the step for it
    # if that box has not got one -- and it can only do that if "nothing is
    # planned here" is a fact the map states rather than the absence of one.
    check("every box says what work is on it, so none of them is silent about it",
          all(isinstance(n.get("steps"), list) for n in m["nodes"]))
    check("and a box nothing names says it has none rather than saying nothing",
          seen["artifacts"]["steps"] == []
          and any(n["steps"] for n in m["nodes"]))
    check("while the step that named nothing is in the tray, so no step is lost "
          "by any box being empty",
          len(m["loose"]) + sum(len(set(x["label"] for x in n["steps"]))
                                for n in m["nodes"]) >= m["steps"])

    # --- A COURSE IS CHAPTERS AND A PROJECT IS COMPONENTS -------------------
    # Which of the two a workspace is decides whether a sitting without a box is
    # an exception worth saying out loud. A chapter of a book already IS a
    # scope; a repository made of parts has one only if somebody tapped it.
    check("a repository made of code is a workspace where a box is the scope",
          mapping.scoped(proj) is True)

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

    # --- three depths: the package, the module, the symbol -------------------
    # The boxes above are DIRECTORIES, and a directory is not a moving part.
    # *"Just looking at it should communicate everything one needs to know to
    # understand how the project works, and when we work on a TODO, it's obvious
    # what moving parts we'll be affecting."* So a box opens into its files and a
    # file opens into what it defines.
    #
    # What has to hold one depth down is exactly what holds at the top: every
    # box traces to something on disk and every arrow to a real import or a real
    # use. And one thing that is new -- Python is PARSED and everything else is
    # GREPPED, so a picture that was grepped has to say so rather than looking
    # identical to one `ast` read.
    fresh()
    m = mapping.status(proj, {}, [])
    seen = by_name(m)
    check("a box says how much is inside it, so the tap is offered before it "
          "is taken", seen["evaluate"]["inside"] == 1
          and seen["artifacts"]["inside"] == 2)

    ins = mapping.inside(proj, seen["artifacts"]["id"])
    mods = dict((n["name"], n) for n in ins["nodes"] if not n.get("outside"))
    check("a box opens into the files in it, not into its subdirectories",
          ins["depth"] == "module" and sorted(mods) == ["back.py", "naming.py"])
    check("and a module says what it is in its own words where it has any",
          mods["naming.py"]["does"])
    check("a module box says whether its own inside will be parsed or grepped, "
          "before anybody taps it", mods["naming.py"]["exact"] is True)
    # AN ARROW THAT LEAVES IS ROLLED UP TO THE BOX IT LANDS IN. `back.py`
    # imports `evaluate`, which is not in the box being opened, so the sibling
    # is drawn as a wall keeping its own name rather than the arrow going
    # nowhere.
    walls = [n for n in ins["nodes"] if n.get("outside")]
    by = dict((n["id"], n) for n in ins["nodes"])
    leaves = set((by[e["from"]]["name"], by[e["to"]]["name"]) for e in ins["edges"])
    check("an arrow that leaves the box is drawn to the sibling it lands in, "
          "rolled up to the depth showing",
          [n["name"] for n in walls] == ["evaluate"]
          and ("back.py", "evaluate") in leaves)
    check("and the sibling is marked as elsewhere rather than drawn as part of "
          "what is being read", walls[0]["outside"] is True)

    # An arrow BETWEEN two files of the same box, which is the fact the
    # directory-level picture cannot show at all.
    write(os.path.join(proj, "psych_asr", "evaluate", "labels.py"),
          '"""What a label is."""\n\ndef tidy(x):\n    return x\n' + PAD)
    write(os.path.join(proj, "psych_asr", "evaluate", "grade.py"),
          "from ..artifacts.naming import stem\nfrom .labels import tidy\n\n"
          "class Finding:\n    \"\"\"One disagreement.\"\"\"\n    pass\n\n"
          "def grade(a, b):\n    \"\"\"Grade a candidate against the reference.\"\"\"\n"
          "    return Finding, tidy(stem(a))\n" + PAD)
    fresh()
    m = mapping.status(proj, {}, [])
    seen = by_name(m)
    ins = mapping.inside(proj, seen["evaluate"]["id"])
    by = dict((n["id"], n) for n in ins["nodes"])
    pairs = set((by[e["from"]]["name"], by[e["to"]]["name"]) for e in ins["edges"])
    check("one file importing another in the same box is an arrow the "
          "directory-level picture could not show",
          ("grade.py", "labels.py") in pairs)

    # --- the symbols, which is the depth the ask was actually about ----------
    mods = dict((n["name"], n) for n in ins["nodes"] if not n.get("outside"))
    sym = mapping.inside(proj, mods["grade.py"]["id"])
    kinds = dict((n["name"], n) for n in sym["nodes"] if not n.get("outside"))
    check("a module opens into what it defines: the classes and the functions",
          sym["depth"] == "symbol" and sorted(kinds) == ["Finding", "grade"])
    check("and a definition says which of the two it is",
          kinds["Finding"]["also"] == "class"
          and kinds["grade"]["also"] == "function")
    check("and what it is for, off its own docstring, which is a sentence "
          "somebody already wrote about their own code",
          kinds["grade"]["does"].startswith("Grade a candidate"))
    check("a symbol carries the file and the name a walkthrough is held over",
          kinds["grade"]["files"] == [os.path.join("psych_asr", "evaluate",
                                                   "grade.py")]
          and kinds["grade"]["symbol"] == "grade")
    by = dict((n["id"], n) for n in sym["nodes"])
    uses = set((by[e["from"]]["name"], by[e["to"]]["name"]) for e in sym["edges"])
    check("an arrow between two definitions is one really using the other",
          ("grade", "Finding") in uses)
    # ROLLED UP TO THE FILE IT CAME FROM, not to the box that holds it. `grade`
    # using `tidy` from `labels.py` next door is a fact about `labels.py`;
    # rolling it up to `evaluate` would draw an arrow from a symbol to the box
    # the symbol is already inside, which says nothing at all.
    check("and a use of something imported points at the file it came from",
          ("grade", "naming.py") in uses and ("grade", "labels.py") in uses)
    check("never at the box the symbol is already inside",
          ("grade", "evaluate") not in uses)
    check("and that file is a wall rather than part of what is being read, so "
          "it can be stepped into sideways",
          all(n.get("outside") for n in sym["nodes"]
              if n["name"].endswith(".py")))
    check("Python is parsed rather than grepped, and the picture says so",
          sym["exact"] is True)
    check("the way back up is on the answer, not remembered from the taps",
          sym["up"] == seen["evaluate"]["id"])

    # A LANGUAGE NOBODY CAN PARSE HERE. A line-anchored pattern is honest about
    # definitions and a liar about calls, so it reports the boxes, draws no
    # arrows, and says `exact` is false -- which is what stops a Lean box being
    # trusted as far as a Python one.
    write(os.path.join(proj, "proofs", "basic.lean"),
          "-- The group of order two.\ntheorem two_group : True := trivial\n"
          "def flip (x : Bool) : Bool := not x\n"
          + "\n".join("-- filler line to clear the size floor" for _ in range(14)))
    fresh()
    m = mapping.status(proj, {}, [])
    lean = by_name(m)["proofs"]
    ins = mapping.inside(proj, lean["id"])
    mods = dict((n["name"], n) for n in ins["nodes"] if not n.get("outside"))
    check("a file in a language nothing here parses says so before it is tapped",
          mods["basic.lean"]["exact"] is False)
    sym = mapping.inside(proj, mods["basic.lean"]["id"])
    check("and it still shows what it defines, found by pattern",
          sorted(n["name"] for n in sym["nodes"]) == ["flip", "two_group"])
    check("with the comment its author wrote above it, where there is one",
          [n for n in sym["nodes"]
           if n["name"] == "two_group"][0]["does"] == "The group of order two.")
    check("but no arrows at all, because a pattern is a liar about calls",
          sym["edges"] == [] and sym["exact"] is False)
    check("and the picture carries the reason, so nobody has to guess why it "
          "is emptier", "pattern" in sym["why"])

    # --- an id from a browser is looked up one depth down too ---------------
    for made_up in ("../../etc/passwd", "in-nothing", "at-made-up", "", None,
                    "psych_asr/evaluate"):
        check("an id that is neither a box nor a module of one resolves to "
              "nothing: %r" % (made_up,), mapping.inside(proj, made_up) is None)
    check("and a symbol is the leaf: there is nothing under a function",
          mapping.inside(proj, kinds["grade"]["id"]) is None)

    # THE WRITTEN MAP IS NOT REPLACED BY ANY OF THIS. A box a person drew and
    # named keeps its name, and the structure appears INSIDE it -- which is the
    # whole reason the derived layer is allowed to exist under the hand-drawn
    # one.
    fresh()

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
    check("and a book course is NOT a workspace where a box is the scope: the "
          "chapter already is one", mapping.scoped(book) is False)

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
    check("and its top-level pieces are components, so a sitting in it belongs "
          "to one", mapping.scoped(flat) is True)

    # --- a repository with nothing in it is not an empty plane ---------------
    os.makedirs(bare, exist_ok=True)
    fresh()
    check("a repository with nothing in it returns no map rather than an empty one",
          mapping.status(bare, {}, []) is None)
    check("and nothing claims a box is its scope when it has no boxes",
          mapping.scoped(bare) is False)

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


    # --- the thread file: the owner's own words, checked against the tree ----
    #
    # STRUCTURE IS DERIVED FROM DISK. MEANING IS WRITTEN. The derived map knows
    # `psych_asr/asr` exists; it cannot know the thread is called *the typist*
    # or that the scorer is blocked on the grader. That is what `threads.json`
    # is for, and it is re-checked on every single read.
    fresh()
    write(os.path.join(proj, "psych_asr", "evaluate", "score.py"),
          "def score():\n    return 1" + PAD)
    drawn = {
        "version": 1,
        "deliverables": [{"id": "stage1",
                          "title": "Stage 1 — a recording to a graded transcript"}],
        "threads": [
            {"id": "typist", "deliverable": "stage1", "title": "the typist",
             "question": "Turns the waveform into words.",
             "files": ["psych_asr/asr/align.py", "psych_asr/asr"]},
            {"id": "grader", "deliverable": "stage1", "title": "the grader",
             "files": ["psych_asr/evaluate/grade.py"]},
            {"id": "scorer", "deliverable": "stage1", "title": "the scorer",
             "files": ["psych_asr/evaluate/score.py"],
             "blockedBy": ["grader"]},
        ],
    }
    problems, _path = threads.write(proj, drawn)
    check("a valid thread file is accepted", not problems)

    fresh()
    m = mapping.status(proj)
    ids = by_id(m)
    check("and its threads REPLACE the derived picture rather than joining it",
          m["written"] is True
          and set(ids) == {"typist", "grader", "scorer"}
          and not any(n["id"].startswith("psych") for n in m["nodes"]))
    check("a thread's title is its box's name, its question the sentence",
          ids["typist"]["name"] == "the typist"
          and ids["typist"]["does"] == "Turns the waveform into words.")
    check("a directory in a thread's files is the box's directory",
          ids["typist"]["dir"] == "psych_asr/asr"
          and ids["typist"]["files"] == ["psych_asr/asr/align.py"])
    check("the title of the picture is the deliverable's",
          m["title"] == "Stage 1 — a recording to a graded transcript")
    check("and a blockedBy is an arrow from the blocker to what it blocks",
          ids["scorer"]["blockedBy"] == ["grader"]
          and {"from": "grader", "to": "scorer", "label": "", "weight": 1}
          in m["edges"])
    check("an old plan's steps still land on thread boxes by the paths they name",
          any(x["num"] == "1" for x in ids["grader"]["steps"])
          and any(x["num"] == "2" for x in ids["typist"]["steps"]))
    check("and a step that names nothing is still in the tray, not dropped",
          any("DESK" in (x["title"] or "").upper() for x in m["loose"]))
    check("every box carries its derived thread status",
          all(n["thread"] in threads.STAGES for n in m["nodes"]))

    # A declaration is checked against the facts EVERY TIME IT IS READ.
    os.remove(os.path.join(proj, "psych_asr", "evaluate", "grade.py"))
    fresh()
    m = mapping.status(proj)
    ids = by_id(m)
    check("a file that has gone drops out of its thread",
          ids["grader"]["files"] == [])
    check("and the thread is still there: a question survives its code moving",
          "grader" in ids and ids["scorer"]["blockedBy"] == ["grader"])
    stale = mapping.check(proj)
    check("and `board thread --check` says so out loud",
          any("grader" in line and "grade.py" in line for line in stale))
    write(os.path.join(proj, "psych_asr", "evaluate", "grade.py"), "x = 1" + PAD)

    # --- the thread file carries the workspace's documents too --------------
    pdf(os.path.join(proj, "docs", "stage1_pipeline_walkthrough.pdf"))
    pdf(os.path.join(proj, "docs", "stage2_reference_walkthrough.pdf"))
    fresh()
    library.forget()
    m = mapping.status(proj)
    inregion = [d["file"] for g in m["documents"]["groups"] for d in g["docs"]]
    check("a written map carries every document in its documents region",
          sorted(inregion) == ["stage1 pipeline walkthrough",
                               "stage2 reference walkthrough"])
    check("and none of them becomes a box nobody wrote",
          not [n for n in m["nodes"] if n["kind"] == "doc"])
    said = mapping.check(proj)
    check("`board thread --check` names every document no thread claims",
          len([x for x in said if "is on no thread" in x]) == 2)

    drawn["threads"][0]["doc"] = "stage2-reference-walkthrough"
    problems, _ = threads.write(proj, drawn)
    fresh()
    m = mapping.status(proj)
    check("and the thread that claimed one offers it",
          not problems
          and by_id(m)["typist"]["doc"] == "stage2-reference-walkthrough")
    check("and the one still unclaimed is the only one reported",
          len([x for x in mapping.check(proj) if "is on no thread" in x]) == 1)
    check("so the briefing's staleness count does not carry it",
          mapping.written_status(proj)["stale"]
          == len([x for x in mapping.check(proj) if "is on no thread" not in x]))
    drawn["threads"][0].pop("doc", None)
    threads.write(proj, drawn)

    # --- a closed thread is the one typed state, and the box says done ------
    drawn["threads"][1]["closed"] = True
    threads.write(proj, drawn)
    fresh()
    m = mapping.status(proj)
    check("a closed thread's box is done",
          by_id(m)["grader"]["status"] == "done"
          and by_id(m)["grader"]["thread"] == "done")
    check("and a closed blocker no longer blocks",
          by_id(m)["scorer"]["blockedBy"] == [])
    drawn["threads"][1]["closed"] = False
    threads.write(proj, drawn)

    # --- a workspace nobody has written threads for is unchanged ------------
    fresh()
    check("a workspace with no thread file still gets the derived map",
          mapping.status(book) and mapping.status(book)["written"] is False)
    check("and the briefing can tell the two apart",
          mapping.written_status(proj)["has"] is True
          and mapping.written_status(book)["has"] is False)

    # --- a map is not a thing to be configured -------------------------------
    src = open(os.path.join(ROOT, "tutorboard", "course", "map.py"),
               encoding="utf-8").read()
    check("nothing here registers, indexes or declares anything",
          "discover" in src.lower() and "registr" not in src.lower())

finally:
    shutil.rmtree(home, ignore_errors=True)

# --- the fence: no box is ever drawn over a directory in fenced.NEVER ---------
from tutorboard import fenced                                 # noqa: E402

fence = tempfile.mkdtemp(prefix="tutor-map-fence-")
real_units = walk.units
try:
    for rel in ("pkg/ok.py", "stage1/run.py", "raw/x.py", "phi/y.py"):
        write(os.path.join(fence, rel), "def f():\n    return 1\n" + PAD)
    fresh()

    def every_box(root):
        """Every node the top picture and each depth below it would draw."""
        top = mapping.status(root) or {"nodes": []}
        out, todo = list(top["nodes"]), [n["id"] for n in top["nodes"]]
        while todo:
            ins = mapping.inside(root, todo.pop())
            for n in (ins or {}).get("nodes") or []:
                if n["kind"] == "module" and not n.get("outside"):
                    todo.append(n["id"])
                out.append(n)
        return out

    def fenced_box(nodes):
        return [n for n in nodes
                if fenced.in_fence(n.get("dir") or "")
                or any(fenced.in_fence(f) for f in n.get("files") or [])]

    boxes = every_box(fence)
    check("map.inside draws no fenced box, at any depth",
          boxes and not fenced_box(boxes)
          and any("pkg/ok.py" in (n.get("files") or []) for n in boxes))

    # The second guard, on its own: a walker that forgot the fence still
    # cannot put a fenced path on the picture.
    def leaky(root):
        return [{"name": p, "label": p, "short": os.path.basename(p),
                 "dir": os.path.dirname(p), "kind": "file", "path": p,
                 "symbol": ""}
                for p in ("pkg/ok.py", "stage1/run.py", "phi/y.py")]
    walk.units = leaky
    fresh()
    boxes = every_box(fence)
    check("and map.py refuses fenced paths even when walk hands them over",
          boxes and not fenced_box(boxes))
finally:
    walk.units = real_units
    fresh()
    shutil.rmtree(fence, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the map is of the content, and none of it is invented")
