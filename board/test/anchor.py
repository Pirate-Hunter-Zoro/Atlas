#!/usr/bin/env python3
"""A mark can be anchored to a page of a document, not only to a card.

`annotate.js` was written for cards and every line of it works unchanged for
anything else that can hold a rectangle of ink. What made it card-only was one
assumption spelled eleven times -- that the thing being annotated is found by
`[data-card="…"]`. Widening that is §2.4's first half, and these are the checks
that say it was widened rather than duplicated.

  * THE KEY IS THE TAIL OF A §2.1 ADDRESS, so the tutor is told where a mark is
    in the same words a link uses, and the place it names can be opened.
  * A NAME FROM A BROWSER NEVER REACHES A FILESYSTEM. The record used to be
    written to `<notes>/<card>.json`, which was safe only because a card is four
    digits. A key with a slash in it is the oldest hole there is, so the key is
    validated against known shapes and the filename is DERIVED from it.
  * A CARD'S RECORD KEEPS ITS OLD NAME. Every mark already on disk has to be
    found exactly where it was, or widening the target costs somebody their ink.
  * A MARK ON A DOCUMENT ANSWERS NO CARD. Claiming one files the turn under a
    card it has nothing to do with.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.server.routes import writing                          # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# --- what may be written on ------------------------------------------------
for good in ("0", "7", "0007", "9999",
             "doc/stage2-deck/p1", "doc/a/p9999", "doc/a-b-c-1/p12"):
    check("an anchor: %r" % good, writing.ann_ok(good))

for bad in ("", "../../etc/passwd", "doc/../x/p1", "doc/X/p1", "doc/a/p",
            "doc/a/p0x", "doc//p1", "doc/a/b/p1", "00007", "card/0007",
            "doc/" + "x" * 41 + "/p1", "code/x.py", "doc/a/p1/../..",
            "doc/a/p1\n", " 0007"):
    check("refused: %r" % bad, not writing.ann_ok(bad))

# --- and where its record goes ---------------------------------------------
check("a card's record keeps the name it has always had",
      writing.ann_file("0007") == "0007")

flat = writing.ann_file("doc/stage2-deck/p3")
check("a document's record has no separator left in it to be a directory",
      "/" not in flat and ".." not in flat and os.path.basename(flat) == flat)
check("and it says what it is, so the directory is readable by eye",
      flat.startswith("doc-stage2-deck-p3"))
check("two different anchors never flatten onto one file",
      writing.ann_file("doc/a-b/p1") != writing.ann_file("doc/a/b-p1"))
check("and the same anchor always gives the same file",
      writing.ann_file("doc/a/p1") == writing.ann_file("doc/a/p1"))

# --- what the tutor is told -------------------------------------------------
lead, how = writing.ann_says("0007", False)
check("a card is described as a card", "card 0007" in lead)
lead, how = writing.ann_says("0007", True)
check("and a mark on the open question is called an answer",
      "ANSWER" in lead)
lead, how = writing.ann_says("doc/stage2-deck/p3", False)
check("a page is described as a page of a named document",
      "page 3" in lead and "stage2-deck" in lead)
check("and the tutor is given the address of that page, in §2.1 terms",
      "#/w/" in how and "doc/stage2-deck/p3" in how)

# --- the client half --------------------------------------------------------
js = open(os.path.join(ROOT, "web", "annotate.js"), encoding="utf-8").read()
check("the ink layer finds its target by KEY, not by a card selector",
      'querySelector(\'[data-card="\'' not in js)
check("and it accepts either attribute",
      "[data-card],[data-ann]" in js)
check("nothing in the ink layer parses the key -- it is opaque",
      "dataset.ann" in js and js.count("dataset.ann") == 1)

board = open(os.path.join(ROOT, "web", "board.js"), encoding="utf-8").read()
check("a document page is given its own box to anchor ink to",
      'class = "paper-page"' in board.replace("className", "class"))
check("and the box is keyed by the address of that page",
      'dataset.ann = "doc/"' in board)
check("the pen is reachable while a document is open",
      "paper-ink" in board)

css = open(os.path.join(ROOT, "web", "board.css"), encoding="utf-8").read()
check("the page box is positioned, or the layer hangs off the scroller",
      re.search(r"\.paper-page\s*{[^}]*position:\s*relative", css) is not None)
check("and the pen's toolbar rises above the document panel",
      re.search(r"body\.papering \.annbar\s*{[^}]*z-index:\s*9[6-9]", css)
      is not None)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("ink is anchored to whatever it was put on, and the anchor is an address")
