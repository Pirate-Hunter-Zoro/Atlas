#!/usr/bin/env python3
"""A card is whole or it is not on the board.

Reported from an iPad, mid-lesson: *"I just submitted a written response and the
next board showed up before the tutor response showed up - I thought we fixed
this? What gives?"* -- with the board's own trace attached, which is the reason
this suite exists rather than a fourth patch to the animation:

    723616  fresh   cards=0041 first=0
    723617  skip    card=0041 why=no units
    759666  fresh   cards=0041 first=0
    759667  type    card=0041 ms=4200 units=122 chars=1817
    763916  typed   card=0041 asked=4200 took=4249 stalled=0

Card 0041 arrived TWICE. The first time it had nothing in it, so there was
nothing to type, so `typeOut` skipped it -- and a skip takes no hold, so the
writing surface came down and the next board appeared. Thirty-six seconds later
the same card arrived with 1,817 characters in it and typed out, underneath a
board that was already there. Every part of the type-out worked; it was handed a
card that was not a card.

Where an empty card comes from: `open(path, "w")` TRUNCATES before it writes,
and the poll that builds the payload runs four times a second over a shared
network filesystem. A poll landing between those two moments sees a file that
exists and is empty. On this filer it then lasts, because the parse is cached
against `(mtime, size)` read through NFS attribute caching -- which is where
thirty-six seconds comes from for an operation that takes microseconds.

Two rules close it, and each would do alone:

  1. `board write` renames a complete file into place, so no reader ever sees a
     partial card. `os.replace` is atomic within a directory.
  2. A card with no body is not put on the board, whoever wrote the file -- an
     interactive tutor writes cards itself, and a shell redirect truncates the
     same way.
"""

import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard.lesson import cards as cardlib               # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


class Repo(object):
    """The two attributes `load_cards` asks for."""

    def __init__(self, base):
        self.cards = os.path.join(base, "cards")
        self.tikz = os.path.join(base, "tikz")
        os.makedirs(self.cards, exist_ok=True)
        os.makedirs(self.tikz, exist_ok=True)


def put(repo, name, text):
    with io.open(os.path.join(repo.cards, name), "w", encoding="utf-8") as fh:
        fh.write(text)


def ids(repo):
    return [c["id"] for c in cardlib.load_cards(repo, [])]


base = tempfile.mkdtemp(prefix="board-whole-")
repo = Repo(base)

# ---------------------------------------------------------------------------
# 1. what counts as a body
# ---------------------------------------------------------------------------
check("a card with prose in it has a body", cardlib.has_body("The kernel is normal."))
check("an empty one does not", not cardlib.has_body(""))
check("and neither does one that is only whitespace, which is what a partly "
      "flushed write looks like", not cardlib.has_body("\n\n   \n"))
check("and None is not a body either", not cardlib.has_body(None))

# ---------------------------------------------------------------------------
# 2. THE FAULT ITSELF. A card caught between the truncate and the content must
#    not reach the glass, because an empty card is one the type-out finishes
#    instantly -- and a card that finishes instantly releases the writing
#    surface and lets the next board down.
# ---------------------------------------------------------------------------
put(repo, "0001-a-real-card.md", "---\nkind: lesson\n---\nThe kernel is normal.\n")
put(repo, "0002-caught-mid-write.md", "")

check("a real card is on the board", "0001" in ids(repo))
check("and a card caught mid-write is NOT, which is the whole of this suite",
      "0002" not in ids(repo))

# Front matter written, body not yet: the shape a truncate-then-write actually
# passes through, rather than a zero-byte file.
put(repo, "0003-head-but-no-body.md", "---\nkind: lesson\ntitle: Nearly\n---\n")
check("nor is one whose front matter landed and whose body has not",
      "0003" not in ids(repo))

# ---------------------------------------------------------------------------
# 3. AND IT IS NOT CACHED AS EMPTY EITHER. The parse cache is keyed on
#    `(mtime, size)` read through this filer's attribute cache, so an empty
#    parse pinned there outlives the write that caused it by however long those
#    attributes take to refresh. Thirty-six seconds, measured.
# ---------------------------------------------------------------------------
put(repo, "0002-caught-mid-write.md", "---\nkind: lesson\n---\nHere it is.\n")
now = cardlib.load_cards(repo, [])
check("and the moment it has a body it is on the board, rather than waiting out "
      "a cache entry that should never have been written",
      "0002" in [c["id"] for c in now])
check("with the body it actually has",
      any(c["id"] == "0002" and "Here it is." in c["body"] for c in now))

# ---------------------------------------------------------------------------
# 4. A part file is not a card. `board write` renames into place; a crash
#    between the two steps leaves one behind, and the directory listing is what
#    the board reads.
# ---------------------------------------------------------------------------
put(repo, ".0004-half.md.1234.part", "---\nkind: lesson\n---\nNot yet.\n")
check("a writer's part file is not a card", "0004" not in ids(repo))

# ---------------------------------------------------------------------------
# 5. AND THE ROOT CAUSE, WHICH IS THAT A CARD IS NEVER TRUNCATED IN PLACE.
#    Driven, not read: the rule is about what is on disk during the write, and
#    a source check cannot see a rename that is never reached.
# ---------------------------------------------------------------------------
src = io.open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
write_fn = src[src.index("def cmd_write("):]
write_fn = write_fn[:write_fn.index("\ndef ", 1)]
check("`board write` renames a finished file into place",
      "os.replace(tmp, path)" in write_fn)
# Comments stripped: this function EXPLAINS the truncate at length, and the
# explanation is not the code.
code = "\n".join(l for l in write_fn.splitlines()
                 if not l.lstrip().startswith("#"))
check("and never opens the card's own path for writing, which is the truncate",
      'open(path, "w"' not in code)
check("into the same directory, because a rename across filesystems is a copy "
      "and is not atomic",
      "os.path.dirname(path)" in write_fn)

lesson = tempfile.mkdtemp(prefix="board-whole-live-")
env = dict(os.environ)
proc = subprocess.run(
    [sys.executable, os.path.join(ROOT, "bin", "board"), "write", "lesson",
     "a written card"],
    input="The kernel is normal.\n\nHere is why, in one line.\n",
    text=True, capture_output=True, cwd=lesson, env=env, timeout=120)
if proc.returncode == 0 and proc.stdout.strip():
    path = proc.stdout.strip().splitlines()[-1]
    room = os.path.dirname(path)
    left = [n for n in os.listdir(room) if n.startswith(".") and n.endswith(".part")]
    check("a real write leaves no part file behind", not left)
    check("and the card it wrote is whole",
          os.path.isfile(path)
          and "The kernel is normal." in io.open(path, encoding="utf-8").read())
    made = Repo(os.path.dirname(room))
    check("and the board reads it", len(cardlib.load_cards(made, [])) == 1)
else:
    check("a real write succeeds (%s)" % (proc.stderr.strip().splitlines()[-1:]
                                          or proc.returncode), False)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a card is whole or it is not on the board")
