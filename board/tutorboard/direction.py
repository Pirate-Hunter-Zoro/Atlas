"""The direction of the work, changed from the board in one tap.

A project is not always going where it was going. Somebody three hours into an
evening realises the whole shape of it is wrong -- the scope, the question, the
thing being built -- and until now saying so meant a terminal: edit the plan by
hand, redraw the map, stop the assistant, start another one, and hope the one
that comes back does not carry on with the old idea out of its own conversation.
Asked for in these words: *"we may be balls deep in a project and I might
realize we need a massive direction change and overhaul... I want maximum power,
minimum pain."*

So it is a button, and what the button does is the whole of this file:

- **What they said is written down**, at the root of the workspace, where it
  crosses machines like `HANDOFF.md` does and is read at the start of every turn
  from then on. A direction that lives only in one assistant's conversation is a
  direction that lasts until the allocation ends.
- **It outranks everything below it.** The plan, the map, the handoff and
  whatever the last turn was aiming at were all written for the old direction.
  The turn woken by the change is told to REDO them rather than to work around
  them, and told in the imperative, because a turn that asks permission to
  replan hands back a plan and does nothing.
- **The assistant is replaced, not persuaded.** `spawn.fresh_tutor` stops the
  one that is running and starts another, so what comes back has read the new
  direction and nothing else. That is the half a prompt cannot do.

ONE direction at a time, and it is the current one. There is no stack and no
history here: what the direction used to be is in the archived lesson that was
open when it changed, and a file that accumulates every change anybody ever made
is a file nobody reads and every turn pays for.
"""

import os
import re
import time


# The stamp says WHEN, and nothing else. Which chapter it was set in does not
# matter -- a direction is about the workspace, not about a sitting, and a
# direction parked with a chapter would quietly stop applying.
_STAMP = re.compile(r"^<!--\s*set:\s*(.*?)\s*-->\s*\n?", re.IGNORECASE)

# As much as somebody will type with a thumb, and then some. Their words are
# never refused for length: this is the moment they are trying to change
# everything, and an error message is the worst possible answer to it.
MAX_CHARS = 8000

# What the board's title bar and the archive have room for.
LABEL_CHARS = 60


def path(root):
    return os.path.join(root, "DIRECTION.md")


def read(root):
    """(what they said, when they said it). ("", "") if nothing is set."""
    try:
        with open(path(root), "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return "", ""
    m = _STAMP.match(text)
    when = m.group(1) if m else ""
    return _STAMP.sub("", text, count=1).strip(), when


def write(root, text, when=None):
    """Replace it with what they just said. Returns (kept, when)."""
    text = (text or "").strip()[:MAX_CHARS]
    if not text:
        return "", ""
    when = when or time.strftime("%Y-%m-%d %H:%M")
    target = path(root)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("<!-- set: %s -->\n%s\n" % (when, text))
    os.replace(tmp, target)
    return text, when


def clear(root):
    """Back to whatever the repository's own documents say. Rarely wanted."""
    try:
        os.remove(path(root))
        return True
    except OSError:
        return False


def label(text):
    """The sitting's name, out of what they typed. Never longer than the bar."""
    first = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", (text or "").strip()))[0]
    if len(first) > LABEL_CHARS:
        first = first[:LABEL_CHARS].rsplit(" ", 1)[0] + "…"
    return "New direction — " + first if first else "New direction"


def standing(root):
    """The section of the briefing that says what this work is now FOR, or "".

    Placed at the TOP of the briefing rather than beside the handoff, because
    everything under it -- the plan, the map, the chapter, the note the last turn
    left -- may have been written for the direction this replaced. A turn that
    reads it last has already believed three documents it should have doubted.
    """
    text, when = read(root)
    if not text:
        return ""
    return (
        "\n--- THE DIRECTION OF THIS WORK, in their own words%s ---\n%s\n\n"
        "This is what the workspace is for NOW, and it outranks every other "
        "document here. Where the plan, the map, the README, HANDOFF.md or "
        "NEXT.md still describe the old direction, they are out of date rather "
        "than right, and bringing them true is part of the work rather than a "
        "separate job. Do not argue the change; they have decided. Say plainly "
        "in a card if something they asked for contradicts a rule in "
        "AI_INSTRUCTIONS.md, and do the rest of it anyway."
        % ((", set %s" % when) if when else "", text))


# What the turn woken BY the change is told, on top of the standing section
# above. It is an order of work rather than a description, because the failure
# here is known and it has a name: handed a change of scope, a model writes four
# hundred words about what it would do and does none of it.
CHANGED = (
    "THEY HAVE JUST CHANGED THE DIRECTION OF THIS WORK. Their words are below "
    "and they replace what this workspace was for. Everything written before "
    "now -- the plan, the map, the handoff, the note from the last turn, the "
    "lesson that was open -- was written for the old one.\n"
    "Do this, in this order, and do not stop before the end:\n"
    "1. `board write` ONE plain sentence saying you are re-planning. It lands "
    "at once, so the board is not blank while you work. Keep the path it "
    "prints.\n"
    "2. Read what is actually there: the plan file the briefing names, the map, "
    "and the README if the change makes it wrong.\n"
    "3. REWRITE THE PLAN so its next steps are this direction's steps. Delete "
    "what the change makes pointless, keep what still stands, and put the new "
    "first step at the top. It is their file and it is in git; rewrite it "
    "rather than appending a note to the bottom.\n"
    "4. Redraw the map with `board map` if the boxes no longer describe the "
    "work, and fix the README's opening paragraph if it now says something "
    "untrue.\n"
    "5. `board write --over <that path>` with the report: what the plan says "
    "now, what changed in it, what the first step is, and the ONE thing you "
    "need from them. Plain words, under 200, no headings.\n"
    "Do not ask permission to start and do not hand back a plan of what you "
    "would do instead of doing it. If the change is too big for one turn, do "
    "the FIRST PART of it and say what is left. "
)
