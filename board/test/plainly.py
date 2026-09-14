#!/usr/bin/env python3
"""A card that cannot be read on a tablet is not a card.

*"All tutor responses should be EASY to read. I never want to face a wall of
text."* `live/TEACHING.md` has asked for that since a card came back correct and
unreadable -- five headings, five hundred words, and the answer to *what did you
just do* nowhere in the first paragraph.

Asking is what `HANDOFF.md` was doing while it grew to eleven times its cap: a
prompt is a preference, every edit is reasonable on its own, and nobody notices
for a fortnight. So the shape of a card is a DOOR at the place a card is
written, and this is the suite that keeps it shut -- including keeping it open
for the things that are not prose and must never be refused.
"""

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import plain, sense

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def words(n, word="word"):
    return " ".join([word] * n)


# ---------------------------------------------------------------------------
# what counts as a wall
# ---------------------------------------------------------------------------
check("an ordinary card is a card",
      plain.wall("The kernel is normal.\n\nHere is why, in one line.") is None)

check("a card that has become a document is refused",
      (plain.wall(words(plain.CARD_WORDS + 40)) or ("", 0))[0] == "long")
check("one just inside the cap is not",
      plain.wall("\n\n".join([words(50)] * 8)) is None)

# The second shape, and it is the one somebody actually complains about: four
# hundred words in nine paragraphs is fine, two hundred in one block is not.
dense = "A first line.\n\n" + words(plain.PARAGRAPH_WORDS + 20)
check("one unbroken block of prose is refused even when the card is short",
      (plain.wall(dense) or ("", 0))[0] == "dense")
check("and the same words, broken up, are fine",
      plain.wall("A first line.\n\n" + "\n\n".join([words(40)] * 3)) is None)

# WHAT IS NOT PROSE IS NOT COUNTED. Refusing a traceback the person asked for,
# or a problem card carrying every definition it uses, would make the door a
# thing to be worked around rather than obeyed.
fenced = "Here is what it printed.\n\n```\n" + "\n".join(
    ["  File \"x.py\", line %d, in f" % i for i in range(120)]) + "\n```\n"
check("a fenced block is read rather than scanned, and is not counted",
      plain.wall(fenced) is None)
check("displayed mathematics is not counted either",
      plain.wall("The identity is this.\n\n$$ " + words(200, "x") + " $$\n") is None)
listed = "Everything this problem uses:\n\n" + "\n".join(
    "- **term %d** — %s" % (i, words(6)) for i in range(30))
check("a list of definitions is a list, counted line by line",
      plain.wall(listed) is None)
check("a table is not one long paragraph",
      plain.wall("| a | b |\n|---|---|\n" + "\n".join(
          "| %s | %s |" % (words(12), words(12)) for i in range(12))) is None)
check("the card's own front matter is not part of it",
      plain.wall("---\nkind: lesson\ntitle: %s\n---\nShort." % words(30)) is None)

# What it says when it refuses. A door that does not say how to get through it
# costs the same round trip twice.
long_why = plain.says_why("long", plain.CARD_WORDS + 40)
check("a refusal says nothing was written", "Nothing was written" in long_why)
check("and how to get through it", "--force" in long_why)
check("and what to do with what will not fit",
      "next turn's card" in long_why and "file in the repository" in long_why)
dense_why = plain.says_why("dense", plain.PARAGRAPH_WORDS + 20)
check("a dense one is told to break it up rather than to cut it",
      "Break it up" in dense_why and "blank line" in dense_why)

# ---------------------------------------------------------------------------
# the door itself, at the place a card is written
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-plainly-")
os.makedirs(os.path.join(tmp, "live", "cards"), exist_ok=True)
BOARD = [sys.executable, os.path.join(ROOT, "bin", "board")]


def write(body, *args):
    p = subprocess.run(BOARD + ["write", "lesson"] + list(args) + ["--repo", tmp],
                       input=body.encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=60)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def cards():
    room = os.path.join(tmp, "live", "cards")
    return sorted(n for n in os.listdir(room) if n.endswith(".md"))


code, out = write("The kernel is normal.\n\nOne line of why.\n")
check("a plain card is written", code == 0 and len(cards()) == 1)

code, out = write(words(plain.CARD_WORDS + 60))
check("a wall of text is refused at the door", code == 1)
check("and NOTHING is written -- there is no undo on a card", len(cards()) == 1)
check("the refusal says how many words it was",
      str(plain.CARD_WORDS + 60) in out)

code, out = write("A first line.\n\n" + words(plain.PARAGRAPH_WORDS + 30))
check("so is one unbroken block of it", code == 1 and len(cards()) == 1)

# The judgement is a heuristic, and a card that genuinely has to be long -- a
# problem restated in full, a listing they asked for -- must still be possible.
code, out = write(words(plain.CARD_WORDS + 60), "--force")
check("--force writes it anyway", code == 0 and len(cards()) == 2)

# A doing turn reports OVER the sentence it opened with, and that path has its
# own branch in `cmd_write`. A door on one and not the other is no door.
first = os.path.join(tmp, "live", "cards", cards()[0])
code, out = write(words(plain.CARD_WORDS + 60), "--over", first)
check("a report written over an opening sentence goes through the same door",
      code == 1)
check("and the card it would have replaced is untouched",
      "The kernel is normal." in open(first, encoding="utf-8").read())

# ---------------------------------------------------------------------------
# and the turn is told the numbers before it hits them
# ---------------------------------------------------------------------------
# A refusal costs a round trip. Discovering the cap from one, every time, is the
# same waste the briefing exists to prevent.
check("every briefing says the door is a door",
      "DOOR, NOT A REQUEST" in sense.PLAIN_SENSE)
check("and names both numbers, from the module that owns them",
      str(plain.CARD_WORDS) in sense.PLAIN_SENSE
      and str(plain.PARAGRAPH_WORDS) in sense.PLAIN_SENSE)
check("and says what is not counted, so nothing is mangled to get under it",
      "fenced code" in sense.PLAIN_SENSE and "list" in sense.PLAIN_SENSE)

method = " ".join(open(os.path.join(ROOT, "TEACHING.md"),
                       encoding="utf-8").read().split())
check("and the method says it too, where somebody reads it once",
      "refuses a card over %d words" % plain.CARD_WORDS in method)
check("with the same two numbers the door actually uses",
      "over %d" % plain.PARAGRAPH_WORDS in method)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a card is read on a tablet, and the shape of one is a door")
