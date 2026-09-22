#!/usr/bin/env python3
"""Every document in a workspace, under the box on the map its source lives in.

The owner could not find their own homework, and every part of why was
measured. The menu's documents panel listed exactly two -- the last lesson
exported and the last write-up compiled -- which is a record of the last thing
BUILT rather than an inventory. The map of a book course drew no document boxes
at all. And `library.documents` on a course with forty-four compiled PDFs
reported three, because a course keeps its sources in `homework/` and `notes/`
and its PDFs one directory away in `build/`, and `build` is in `reading.IGNORE`.

So this checks the three claims the drawer rests on, and they are claims about
DERIVATION rather than about a record anybody keeps:

  * THE SOURCE AND THE PDF IT BUILDS INTO ARE ONE DOCUMENT. The pairing adds no
    document and renames none: an id is what ink is anchored on, and a walk that
    starts handing out different ones puts last week's marks on a different
    page. Taking `build` out of `IGNORE` is the answer that looks simpler and
    does exactly that, which is why it is not the answer.
  * WHICH BOX IS READ OFF THE PATH, EVERY TIME. Nothing is registered: no index
    file, no sidecar. A document that moves belongs to a different box on the
    next read and one that is deleted stops existing.
  * AN ID IS LOOKED UP, NEVER CONSTRUCTED. `shelf.find` compares what arrived
    against the ids it handed out, and a miss is a miss -- the same rule as
    `reading.find` and `walk.resolve`.

And one trap of its own. `map.py:872` rebuilds a chapter's node id from a
regex -- `ch0*(\\d+)` on `ch04` gives `4`, the node is `ch-04` -- and ten of
twenty-one set boxes in Galois Theory lost their edge to their chapter that way.
The fixture here is built to fail the same way if this module ever reconstructs
an id: the tsv keeps its leading zeros, so the nodes are `ch-04` and `ch-05`,
and the directories are `ch04` and `ch005`. Every string a regex could build
from one is absent from the other.
"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard.course import homework, library, reading, shelf     # noqa: E402
from tutorboard.course import map as mapping                        # noqa: E402
from tutorboard.course import repo as course_repo                   # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text, pad=0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + ("x" * pad))


# A PDF has to be big enough to be a document rather than an exported figure --
# `reading.MIN_BYTES` -- and only where nobody here wrote the source. Padding
# every one of them past it keeps the fixture honest either way.
def pdf(path):
    write(path, "%PDF-1.4\n% a fixture, not a document\n",
          reading.MIN_BYTES + 1000)


def fresh():
    """Three caches, all on the same half-minute clock."""
    library.forget()
    shelf.forget()
    mapping._cache.clear()


def sids(root):
    return dict((r["sid"], r["rel"]) for r in shelf.documents(root))


def by_rel(root):
    return dict((r["rel"], r) for r in shelf.documents(root))


def book(root):
    """A course that follows a book, in the shape the real ones are in.

    THE NUMBERS ARE PADDED AND THEY DISAGREE WITH EACH OTHER, deliberately. The
    table says `04` and `05`, so the nodes are `ch-04` and `ch-05`; the
    directories are `ch04-...` and `ch005-...`. A join on an id rebuilt from
    either one misses.
    """
    write(os.path.join(root, "chapters.tsv"),
          "04\t1\t20\tfields\tField extensions\n"
          "05\t21\t40\tgalois\tGalois groups\n")

    ch4 = os.path.join(root, "chapters", "ch04-field-extensions")
    # The write-up and the PDF the course's own build script leaves one
    # directory across from it. This is the pair the library could not see.
    write(os.path.join(ch4, "homework", "ch04-homework.tex"),
          "\\title{Chapter 4 homework}\n")
    pdf(os.path.join(ch4, "build", "ch04-homework.pdf"))
    # Written and never compiled.
    write(os.path.join(ch4, "notes", "ch04-notes.tex"),
          "\\title{Chapter 4 notes}\n")
    # Somebody else's: the textbook split for this chapter, under the directory
    # name `reading.NOT_OURS` hides.
    pdf(os.path.join(ch4, "reading", "garling-ch4.pdf"))

    ch5 = os.path.join(root, "chapters", "ch005-galois-groups")
    write(os.path.join(ch5, "homework", "ch05-homework.tex"),
          "\\title{Chapter 5 homework}\n")
    pdf(os.path.join(ch5, "build", "ch05-homework.pdf"))
    write(os.path.join(ch5, "notes", "ch05-notes.tex"),
          "\\title{Chapter 5 notes}\n")

    hw1 = os.path.join(root, "homework", "hw01")
    write(os.path.join(hw1, "hw01.tex"), "\\title{Set one}\n")
    pdf(os.path.join(hw1, "build", "hw01.pdf"))
    # The sheet the professor handed out, under the set's own directory.
    pdf(os.path.join(hw1, "assignment", "sheet.pdf"))

    # Two files sharing a filename, which is the only thing that makes a sid
    # need a suffix at all.
    write(os.path.join(ch4, "notes", "worksheet.tex"), "\\title{A worksheet}\n")
    write(os.path.join(root, "docs", "worksheet.tex"), "\\title{Another}\n")

    # WORKSHEETS OUTSIDE `chapters/`, which is the whole reason a set has to be
    # able to say which chapter it is for. Three routes and three outcomes.
    #   `fields` is chapter 4's own slug in chapters.tsv -> placed by the slug.
    ws1 = os.path.join(root, "homework", "worksheet-fields")
    write(os.path.join(ws1, "worksheet-fields.tex"),
          "%  Worksheet --- Field Extensions and the Ring F[x]\n"
          "\\title{Worksheet --- Field Extensions and the Ring F[x]}\n")
    pdf(os.path.join(ws1, "build", "worksheet-fields.pdf"))
    #   names two chapters' slugs and therefore neither -- a wrong chapter is
    #   worse than none, so this one stays on its own box.
    ws2 = os.path.join(root, "homework", "worksheet-fields-galois")
    write(os.path.join(ws2, "worksheet-fields-galois.tex"),
          "%  Worksheet --- Both At Once\n"
          "\\title{Worksheet --- Both At Once}\n")
    pdf(os.path.join(ws2, "build", "worksheet-fields-galois.pdf"))
    #   says so itself, which is the escape hatch for a slug that says nothing.
    ws3 = os.path.join(root, "homework", "extra-problems")
    write(os.path.join(ws3, "extra-problems.tex"),
          "%  Extra Problems\n% chapter: 5\n"
          "\\title{Extra Problems}\n")
    pdf(os.path.join(ws3, "build", "extra-problems.pdf"))

    # In no box: the plan, and the book itself.
    write(os.path.join(root, "docs", "plan-of-attack.tex"), "\\title{The plan}\n")
    pdf(os.path.join(root, "textbook", "a-course-in-galois-theory.pdf"))


def code(root):
    """A repository of Python, which must gain nothing from any of this."""
    write(os.path.join(root, "psych_asr", "evaluate", "grade.py"),
          "from psych_asr.artifacts import naming\n")
    write(os.path.join(root, "psych_asr", "artifacts", "naming.py"), "X = 1\n")
    # The shapes the three `THEIRS` globs name, spelled in a code tree. None of
    # them is under `chapters/` or `homework/`, so none of them may be caught.
    pdf(os.path.join(root, "docs", "stage1-walkthrough.pdf"))
    pdf(os.path.join(root, "psych_asr", "reading", "someone-else.pdf"))
    write(os.path.join(root, "docs", "stage1-walkthrough.tex"), "\\title{Stage 1}\n")


home = tempfile.mkdtemp(prefix="shelf-test-")
try:
    course = os.path.join(home, "Galois-Theory")
    plain = os.path.join(home, "PSYCH-ASR")
    os.makedirs(course)
    os.makedirs(plain)

    # ---------------------------------------------------------------- 1
    # THE SOURCE PAIRED WITH THE PDF ONE DIRECTORY AWAY, and the pairing costs
    # no id. The tree is built twice: once with the `build/` output deleted, to
    # take the ids the library hands out when it can see only sources, and then
    # again with it there.
    book(course)
    builds = [os.path.join(course, "chapters", "ch04-field-extensions", "build"),
              os.path.join(course, "chapters", "ch005-galois-groups", "build"),
              os.path.join(course, "homework", "hw01", "build")]
    kept = {}
    for d in builds:
        for name in os.listdir(d):
            with open(os.path.join(d, name), "rb") as fh:
                kept[os.path.join(d, name)] = fh.read()
        shutil.rmtree(d)

    fresh()
    before = dict((r["id"], r["rel"]) for r in library.documents(course))
    unbuilt = set(r["id"] for r in library.documents(course) if not r["pdf"])

    for path, data in kept.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
    fresh()
    after = dict((r["id"], r["rel"]) for r in library.documents(course))
    got = dict((r["id"], r) for r in library.documents(course))
    # BY WHAT IT IS, NOT BY THE ID IT WAS GIVEN. An id is truncated to the forty
    # characters `writing.ANN_DOC` allows, so writing one out here would be
    # asserting the length of a slug rather than the pairing.
    ch04hw = [r for r in got.values()
              if r["source"] == "chapters/ch04-field-extensions/homework/"
                                "ch04-homework.tex"][0]

    check("a source in a unit's homework/ pairs with the PDF in its build/",
          ch04hw["pdf"] and ch04hw["rel"]
          == "chapters/ch04-field-extensions/build/ch04-homework.pdf")
    check("and the pairing adds no document and loses none (%d)" % len(after),
          set(before) == set(after))
    check("and changes no id: what the ink is anchored on does not move",
          sorted(before) == sorted(after))
    moved = [i for i in after if before[i] != after[i]]
    check("what it changes is where each one points -- %d of them, from the "
          "source to the compiled PDF" % len(moved),
          sorted(moved) == sorted(i for i in unbuilt if got[i]["pdf"])
          and len(moved) == 3)
    check("a source with no PDF anywhere is still a document, and says it has "
          "none",
          by_rel(course)["chapters/ch04-field-extensions/notes/ch04-notes.tex"]
          ["pdf"] is False)
    check("and `/library/view` can reach a paired PDF, which it could not when "
          "it built the path from the source's own directory",
          library.path_of(course, ch04hw, ".pdf")
          == os.path.join(course, "chapters", "ch04-field-extensions",
                          "build", "ch04-homework.pdf"))

    # ---------------------------------------------------------------- 2
    # WHICH BOX, READ OFF THE PATH.
    fresh()
    nodes = dict((n["id"], n) for n in mapping.status(course, {}, [])["nodes"])
    shelved = by_rel(course)

    check("a set's compiled write-up lands on the set's own box",
          shelved["chapters/ch04-field-extensions/build/ch04-homework.pdf"]
          ["node"] == "hw-ch04")
    check("and so does a sheet sitting inside the set's directory",
          shelved["homework/hw01/assignment/sheet.pdf"]["node"] == "hw-hw01")
    check("a chapter's notes land on the chapter's box",
          shelved["chapters/ch04-field-extensions/notes/ch04-notes.tex"]["node"]
          == "ch-04")
    check("and the box is named on the record, so the drawer heads a group "
          "without asking the map",
          shelved["chapters/ch04-field-extensions/notes/ch04-notes.tex"]["box"]
          == nodes["ch-04"]["name"])

    # THE ZERO-PADDING TRAP. `ch04` under a node called `ch-04`, and `ch005`
    # under a node called `ch-05`: the join is on the integer the syllabus
    # record carries, so both land. A reconstructed id -- `"ch-" + "4"`, or
    # `"ch-" + "005"` -- is a string that is not on this map at all, and the
    # assertion below is that no such string is.
    check("a chapter directory joins its box on the NUMBER, through a leading "
          "zero on either side",
          shelved["chapters/ch005-galois-groups/notes/ch05-notes.tex"]["node"]
          == "ch-05")
    check("and the id was looked up rather than rebuilt: nothing a regex could "
          "have built from the directory is a box on this map",
          not set(["ch-4", "ch-005", "ch-5", "ch-0004"]) & set(nodes))

    check("a document in no box is unfiled rather than dropped",
          shelved["docs/plan-of-attack.tex"]["node"] == ""
          and shelved["textbook/a-course-in-galois-theory.pdf"]["node"] == "")

    # ---------------------------------------------------------------- 3
    # THE GROUPS THE DRAWER DRAWS.
    grouped = shelf.grouped(course_repo.Repo(course))
    check("grouped() answers ok, with a total and a group per box that has one",
          grouped["ok"] and grouped["total"] == len(shelf.documents(course))
          and len(grouped["groups"]) >= 4)
    check("the groups run in the map's own order",
          [g["node"] for g in grouped["groups"] if g["node"]]
          == [n["id"] for n in mapping.status(course, {}, [])["nodes"]
              if n["id"] in set(g["node"] for g in grouped["groups"])])
    check("and Unfiled is last",
          grouped["groups"][-1]["node"] == ""
          and grouped["groups"][-1]["box"] == "Unfiled")
    check("every group's node is a real box on the map",
          all(g["node"] in nodes for g in grouped["groups"] if g["node"]))
    every = [d for g in grouped["groups"] for d in g["docs"]]
    check("and a row carries exactly what the drawer reads and no path to a "
          "route", all(set(d) == set(["sid", "title", "kind", "pages", "at",
                                      "iso", "size", "pdf", "stale", "theirs",
                                      "rel", "set"]) for d in every))

    tally = shelf.counts(course)
    want = {}
    for rec in shelf.documents(course):
        # A badge says what its box opens, and a set's write-up opens from the
        # set AND from the chapter it was written for -- so it is counted on
        # both. `total` is the distinct count and is checked above.
        for box in (rec["node"], rec["under"]):
            if box:
                want[box] = want.get(box, 0) + 1
    check("counts() keys are all real boxes, and every document is counted on "
          "every box that opens it",
          set(tally) <= set(nodes) and tally == want)
    check("and the map payload carries the count on the box, never the list",
          nodes["hw-hw01"]["docs"] == 2 and nodes["ch-04"]["docs"] == 5
          and all(isinstance(n["docs"], int) for n in nodes.values())
          and tally == dict((i, n["docs"]) for i, n in nodes.items() if n["docs"]))

    # ---------------------------------------------------------------- 3b
    # A SET IS FOUND UNDER THE CHAPTER IT IS FOR, wherever it is filed. The
    # complaint this answers is "there are two chapter 4 sets I need, one from a
    # worksheet and one from book problems" -- one of which lives outside
    # `chapters/` entirely and so can be joined by nothing in its path.
    drawn = mapping.status(course, {}, [])
    edges = set((e["from"], e["to"]) for e in drawn.get("edges", []))
    under = dict((g["node"], [d["title"] for d in g["docs"]])
                 for g in grouped["groups"])
    ch4 = under.get("ch-04", [])
    check("a chapter's group holds the book problems AND the worksheet written "
          "for that chapter, though only one of them is filed under it",
          any(x == "Chapter 4 homework" for x in ch4)
          and any(x.startswith("Worksheet") and "Field Extensions" in x
                  for x in ch4))
    check("and each keeps its own box, so a badge opens that set and no other",
          shelf.counts(course).get("hw-ch04") == 1
          and shelf.counts(course).get("hw-worksheet-fields") == 1)
    check("a slug naming two chapters places the set under neither, because a "
          "wrong chapter is worse than none",
          any(g["node"] == "hw-worksheet-fields-galois"
              for g in grouped["groups"])
          and not any(x.startswith("Worksheet") and "Both At Once" in x
                      for g in grouped["groups"] if g["node"] == "ch-04"
                      for x in [d["title"] for d in g["docs"]]))
    check("and a set that declares its chapter in its own source is placed by "
          "the declaration",
          any(x.startswith("Extra Problems") for x in under.get("ch-05", [])))
    check("a set named after its chapter is called after the number rather "
          "than after the chapter's whole title",
          any(n["name"] == "Ch 04 homework"
              for n in drawn["nodes"] if n["kind"] == "set"))
    check("and the edge from a chapter to its set survives a leading zero on "
          "either side, which an id rebuilt by regex does not",
          ("ch-04", "hw-ch04") in edges and ("ch-05", "hw-ch005") in edges)
    check("a worksheet filed outside chapters/ is drawn against its chapter "
          "too",
          ("ch-04", "hw-worksheet-fields") in edges)

    # ---------------------------------------------------------------- 4
    # SOMEBODY ELSE'S MATERIAL, by three globs shaped like a course.
    check("a textbook split under a chapter's reading/ is found and tagged as "
          "theirs",
          shelved["chapters/ch04-field-extensions/reading/garling-ch4.pdf"]
          ["theirs"] is True)
    check("and so is the assignment sheet the set was handed",
          shelved["homework/hw01/assignment/sheet.pdf"]["theirs"] is True)
    check("what this course wrote itself is not tagged",
          not any(shelved[r]["theirs"] for r in
                  ["chapters/ch04-field-extensions/build/ch04-homework.pdf",
                   "docs/plan-of-attack.tex",
                   "textbook/a-course-in-galois-theory.pdf"]))
    check("and nothing was taken out of the shared lists to do it: `build` is "
          "still ignored and `reading` is still not ours",
          "build" in reading.IGNORE and "reading" in reading.NOT_OURS)

    # ---------------------------------------------------------------- 5
    # A SID IS STABLE. This is the one that catches a dedupe done in walk
    # order: a file added at the top of the walk renumbers everything a
    # collision touched, and ink anchored on `doc/<sid>/p<n>` lands on a
    # different document.
    fresh()
    first = sids(course)
    check("two files sharing a filename get one sid each, suffixed by path "
          "order rather than by walk order",
          first.get("worksheet") == "chapters/ch04-field-extensions/notes/"
                                    "worksheet.tex"
          and first.get("worksheet-2") == "docs/worksheet.tex")

    write(os.path.join(course, "chapters", "ch001-preliminaries", "notes",
                       "aardvark-notes.tex"), "\\title{Aardvarks}\n")
    fresh()
    again = sids(course)
    renamed = [s for s in first if again.get(s) != first[s]]
    check("and an alphabetically-earlier file added to the tree renames none "
          "of them", not renamed)
    check("the new one is simply there as well",
          "aardvark-notes" in again and len(again) == len(first) + 1)

    # ---------------------------------------------------------------- 6
    # AN ID IS LOOKED UP, NEVER CONSTRUCTED.
    fresh()
    target, stem = shelf.find(course, "ch04-homework")
    check("find() resolves a sid this module handed out to the file it names",
          target == os.path.join(course, "chapters", "ch04-field-extensions",
                                 "build", "ch04-homework.pdf")
          and stem == "ch04-homework")
    check("a sid that is not one of ours resolves to nothing",
          shelf.find(course, "not-a-document") == (None, None))
    check("and neither does a path, however it is spelled",
          shelf.find(course, "../../etc/passwd") == (None, None)
          and shelf.find(course, "chapters/ch04-field-extensions/build/"
                                 "ch04-homework.pdf") == (None, None)
          and shelf.find(course, "") == (None, None))
    check("a document with no compiled PDF refuses to be opened, rather than "
          "handing over its source",
          shelf.find(course, "ch04-notes") == (None, None))

    # ---------------------------------------------------------------- 7
    # A CODE WORKSPACE GAINS NOTHING FROM ANY OF THIS.
    #
    # It has no chapters and no problem sets, so two of the three rules cannot
    # fire in it at all and what is left is the plain one: a document under a
    # box's own directory belongs to that box. The three globs are shaped like
    # a course on purpose -- `reading.NOT_OURS` is shared with every code
    # workspace on this machine and must not move -- so a `reading/` directory
    # inside a package stays hidden, which is the whole reason that list
    # exists.
    code(plain)
    fresh()
    theirs = shelf.documents(plain)
    boxes = dict((n["id"], n) for n in mapping.status(plain, {}, [])["nodes"])
    check("a repository of code has no chapter and no set for a document to "
          "land on",
          theirs and not [n for n in boxes.values()
                          if n["kind"] in ("chapter", "set")])
    check("so what it places, it places by the directory the box already is",
          all(not r["node"]
              or r["rel"].startswith(boxes[r["node"]]["dir"].strip("/") + "/")
              for r in theirs))
    check("and none of the three course-shaped globs caught anything in it",
          not any(r["theirs"] for r in theirs))
    check("its counts are boxes on its own map and nothing else",
          set(shelf.counts(plain)) <= set(boxes))
    check("and the sheet in its own reading/ is still hidden, which is what "
          "that list is for",
          not any(r["rel"].endswith("someone-else.pdf") for r in theirs))
finally:
    shutil.rmtree(home, ignore_errors=True)

print()
if fails:
    print("%d failed" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("every document is under the box its source lives in")
