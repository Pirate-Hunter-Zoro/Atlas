"""A card that cannot be read on a tablet is not a card. The door that says so.

TEACHING.md asks for plain cards, and asking alone lets a text grow without
bound, so the shape is checked where a card is written and a wall is refused,
not trimmed. Two shapes count: too long (a document belongs in a file) and
too dense (one long unbroken paragraph). Code blocks, displayed equations
and tables are not counted; list items are measured one by one.
"""

import re


# Past this, the card is a document (a full problem restatement runs ~300).
CARD_WORDS = 450

# One block of prose, unbroken. Anything past this is the grey rectangle.
PARAGRAPH_WORDS = 110

# What is read rather than scanned, and is therefore not counted at all.
FENCE = re.compile(r"^\s*(```|~~~)")
DISPLAY_MATH = re.compile(r"\$\$.*?\$\$|\\\[.*?\\\]", re.DOTALL)
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# A line that stands alone (list item, table row, heading, quote) is measured
# by itself.
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
    """Every unbroken block of prose in the card, longest first; a marked
    line ends the block it follows."""
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
    `long` (the whole card) is asked before `dense` (its worst paragraph)."""
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
