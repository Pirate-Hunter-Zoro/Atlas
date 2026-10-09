"""The prompts a turn is given, one Markdown file each in `prompts/`.

A file holds the prompt's exact text plus one final newline, which `_read`
drops. `%(inbox)s` is filled by the loop. The first and unfinished prompts
end on `TURN_TAIL`, which is its own file. Every turn is fresh, so there is no
resume prompt.
"""

import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def _read(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
        text = fh.read()
    return text[:-1] if text.endswith("\n") else text


# The wrap-up turn, the only one the student never sees.
HANDOFF_PROMPT = _read("handoff.md")
HANDOFF_CLAUSE = _read("handoff-clause.md")
NO_HANDOFF_CLAUSE = _read("no-handoff-clause.md")
# The line every teaching turn ends on.
TURN_TAIL = _read("turn-tail.md")

HEADLESS_FIRST_PROMPT = _read("first.md") + TURN_TAIL
HEADLESS_UNFINISHED_PROMPT = _read("unfinished.md") + TURN_TAIL
# A step of a coding session at the cluster: a lesson turn about a diff.
HEADLESS_CODE_PROMPT = _read("code.md") + TURN_TAIL
HEADLESS_REVISE_PROMPT = _read("revise.md")
HEADLESS_REWORK_PROMPT = _read("rework.md")
HEADLESS_WRITEUP_PROMPT = _read("writeup.md")
HEADLESS_SHIP_PROMPT = _read("ship.md")
