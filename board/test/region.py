#!/usr/bin/env python3
"""Every workspace's map carries its documents, and a tap on one reads it.

Asked for in these words: *"I should be able to access ANY AND ALL papers and
presentations relevant to a project/course IN that project/course. When I'm on
the map of a course, part of that map should show all papers/presentations
pertaining to that project/course."*

What the checks are about:

  * EVERY FAMILY. A course, a research workspace, a project and a practice
    workspace each have a region, derived map or written.
  * EVERYTHING. No cap: a workspace with more documents than the drawer's old
    twenty-four carries every one of them.
  * A TAP RESOLVES TO THE READER. Every id in the region is one the library
    finds, which is what `/library?doc=<id>` asks.
  * A SECTION IS READ ALONE AND CORRECTED THROUGH ITS WHOLE. The pieces of a
    manuscript are in the region, under their own group, each naming the
    document it was cut from.
"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import library, plan, reading, walk            # noqa: E402
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


def pdf(path):
    write(path, "%PDF-1.4\n" + ("%% filler line to clear the size floor\n" * 900))


def fresh():
    mapping._cache.clear()
    plan._cache.clear()
    walk._cache.clear()
    reading._cache.clear()
    library.forget()


PAD = "\n" + ("# padding, to clear the size floor on a walkable file\n" * 12)

tmp = tempfile.mkdtemp(prefix="region-")
try:
    # A COURSE: chapters and a compiled homework.
    course = os.path.join(tmp, "courses", "Galois")
    for n, slug in ((1, "groups"), (2, "fields")):
        os.makedirs(os.path.join(course, "chapters", "ch%02d-%s" % (n, slug)))
    write(os.path.join(course, "homework", "hw01", "hw01.tex"),
          "\\title{Homework one}\n" + "x" * 3000)
    pdf(os.path.join(course, "homework", "hw01", "hw01.pdf"))

    # A RESEARCH WORKSPACE, derived from its code, with no `live/map.json` --
    # and more documents than `reading.MAX_DOCS`, pieces included.
    research = os.path.join(tmp, "projects", "TRD")
    write(os.path.join(research, "trd", "__init__.py"), '"""The model."""' + PAD)
    write(os.path.join(research, "trd", "fit.py"), "import trd" + PAD)
    write(os.path.join(research, "paper1", "manuscript.md"), "# Title page\n")
    pdf(os.path.join(research, "paper1", "manuscript.pdf"))
    for i in range(30):
        write(os.path.join(research, "paper1", "parts", "manuscript",
                           "%02d-section.md" % i), "# Section %d\n" % i)
        pdf(os.path.join(research, "paper1", "parts", "manuscript",
                         "%02d-section.pdf" % i))
    write(os.path.join(research, "writeups", "deck-1", "deck-1.tex"),
          "\\documentclass{beamer}\n\\title{The k sweep}\n" + "x" * 3000)
    pdf(os.path.join(research, "writeups", "deck-1", "deck-1.pdf"))

    # A PROJECT and A PRACTICE WORKSPACE, one document each.
    project = os.path.join(tmp, "projects", "Factory")
    write(os.path.join(project, "factory", "__init__.py"), '"""Papers."""' + PAD)
    pdf(os.path.join(project, "docs", "how_it_works.pdf"))
    practice = os.path.join(tmp, "projects", "Algo")
    write(os.path.join(practice, "solutions", "__init__.py"), '"""Sols."""' + PAD)
    pdf(os.path.join(practice, "notes", "dp_notes.pdf"))

    fresh()
    for name, root in (("a course", course), ("a research workspace", research),
                       ("a project", project), ("a practice workspace", practice)):
        m = mapping.status(root)
        region = (m or {}).get("documents") or {}
        ids = [d["id"] for g in region.get("groups", []) for d in g["docs"]]
        check("%s has a documents region on its map" % name,
              bool(m) and region.get("total", 0) >= 1 and len(ids) == region["total"])
        check("and no document is a box on its graph",
              bool(m) and not [n for n in m["nodes"] if n["kind"] == "doc"])
        check("and every id in it resolves to the reader",
              all(library.find(root, i) for i in ids))
        rels = set(d["rel"] for d in library.documents(root))
        check("and every document the drawer offers is in it",
              all(d["rel"] in rels for d in reading.documents(root)))

    m = mapping.status(research)
    region = m["documents"]
    groups = dict((g["key"], g) for g in region["groups"])
    check("EVERYTHING: 32 documents, past the drawer's cap of %d" % reading.MAX_DOCS,
          region["total"] == 32)
    check("grouped: papers, decks and section parts",
          sorted(groups) == ["decks", "papers", "parts"]
          and len(groups["parts"]["docs"]) == 30)
    check("a paper is called what its author calls it, not its first heading",
          groups["papers"]["docs"][0]["file"] == "manuscript"
          and groups["papers"]["docs"][0]["name"] == "Title page")
    check("a beamer source is a deck", groups["decks"]["docs"][0]["name"] == "The k sweep")

    whole = library.find(research, groups["papers"]["docs"][0]["id"])
    piece = library.find(research, groups["parts"]["docs"][0]["id"])
    check("a section is a piece, and names the whole it was cut from",
          piece["piece"] is True and piece["whole"] == whole["id"]
          and whole["piece"] is False)
    check("wholes come before pieces in the library",
          [d["piece"] for d in library.documents(research)]
          == sorted(d["piece"] for d in library.documents(research)))

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("every workspace's map carries its documents")
