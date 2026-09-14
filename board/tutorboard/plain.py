"""A card that cannot be read on a tablet is not a card. The door that says so.

`live/TEACHING.md` has asked for plain cards since the day a correct one came
back with five headings, five hundred words and the answer to *what did you just
do* nowhere in the first paragraph. Asking is not enough, and this file exists
because of what happened to the handoff: a prompt asked for 350 words for
weeks, every turn edited the file a little, each edit was reasonable on its own,
and the thing reached 3,824. `HANDOFF.md` is now capped by a door rather than by
a request, and so is this.

So the SHAPE of a card is checked where a card is written, and a wall is refused
rather than trimmed. Two shapes count as a wall, because they fail in different
ways and either one alone would let the other through:

- **Too much of it.** Past a point the card is a document, and a document goes in
  a file the board can open -- not on the glass over the lesson.
- **Too dense.** Four hundred words in nine short paragraphs is fine; two
  hundred in one block is the thing that gets scrolled past. A long paragraph on
  a tablet held at arm's length is a grey rectangle.

WHAT IS NOT PROSE IS NOT COUNTED. A fenced code block, a displayed equation and
a table are read differently and are allowed to be as long as the thing they
describe; counting them would refuse a traceback the person asked for. A list is
counted line by line, because a list of one-line definitions is exactly what a
self-contained problem card is made of.
"""

import re


# Past this, the card is a document. Chosen against the card that produced the
# complaint (about 500 words) and against the longest card anybody has wanted --
# a problem restated in full with every definition under it, which runs to
# roughly 300.
CARD_WORDS = 450

# One block of prose, unbroken. Anything past this is the grey rectangle.
PARAGRAPH_WORDS = 110

# What is read rather than scanned, and is therefore not counted at all.
FENCE = re.compile(r"^\s*(```|~~~)")
DISPLAY_MATH = re.compile(r"\$\$.*?\$\$|\\\[.*?\\\]", re.DOTALL)
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# A line that stands on its own: a list item, a table row, a heading, a quote.
# Each is measured by itself, so a list of twelve definitions is twelve short
# things rather than one long one.
OWN_LINE = re.compile(r"^\s{0,6}(?:[-*+]\s|\d+[.)]\s|#{1,6}\s|>|\||!\[|\s*$)")


def _prose(text):
    """The card with everything that is not prose taken out."""
    text = FRONT_MATTER.sub("", text or "")
    text = DISPLAY_MATH.sub(" ", text)
    out = []
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def words(text):
    return len(re.findall(r"\S+", text or ""))


def paragraphs(text):
    """Every unbroken block of prose in the card, longest first.

    A line that carries its own marker -- a list item, a table row, a heading --
    ends the block it follows and is measured alone.
    """
    found = []
    block = []
    for line in _prose(text).splitlines():
        if OWN_LINE.match(line):
            if block:
                found.append(" ".join(block))
                block = []
            if line.strip():
                found.append(line)
            continue
        block.append(line.strip())
    if block:
        found.append(" ".join(block))
    return sorted((words(p) for p in found), reverse=True)


def wall(text):
    """Is this card a wall of text? (what is wrong, the number) or None.

    `long` is the whole card; `dense` is its worst paragraph. The whole card is
    asked first: a card that is both is a card to cut, and telling somebody to
    split a paragraph in a document that should not exist sends them the wrong
    way.
    """
    n = words(_prose(text))
    if n > CARD_WORDS:
        return ("long", n)
    blocks = paragraphs(text)
    if blocks and blocks[0] > PARAGRAPH_WORDS:
        return ("dense", blocks[0])
    return None


def says_why(kind, n):
    """Why the card was refused, and what to do about it. Plain, and short."""
    if kind == "long":
        return (
            "board write: %d words. A card is read on a tablet by somebody who "
            "has been doing something else, and past %d it is a document rather "
            "than a card. Nothing was written.\n"
            "Cut it to the one thing this turn is about: the answer in the first "
            "sentence, the reasoning under it, one question, stop. What will not "
            "fit is either the next turn's card or a file in the repository the "
            "board can open -- not the glass over the lesson.\n"
            "If this one genuinely has to be that long, pass --force."
            % (n, CARD_WORDS))
    return (
        "board write: one paragraph of %d words. Past %d it is a grey rectangle "
        "on a tablet and it gets scrolled past. Nothing was written.\n"
        "Break it up: one idea per sentence, a blank line between ideas, and the "
        "answer in the first sentence rather than at the end. A list of "
        "definitions is a list, one line each.\n"
        "If this one genuinely has to be that long, pass --force."
        % (n, PARAGRAPH_WORDS))
