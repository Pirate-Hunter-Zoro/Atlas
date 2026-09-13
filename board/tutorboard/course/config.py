"""What a repository says it is.

A course declares its name, and whether the tutor is there to teach the work or
to do it. It does NOT declare a subject any more: there was a `mode`, `math` or
`code`, and it decided both how the board looked and how the lesson was shaped.
It is gone. Every repository is taught the one way -- the way the mathematics
courses were always taught -- and a repository whose subject happens to be code
says so by having code in it, not by turning off half the board.

A `mode` left over in a `tutorboard.json` is read and ignored, because those
files live in the course repositories rather than here and a stale key must
never be the reason a board behaves differently from its neighbour.
"""

import json
import os


DEFAULT_CONFIG = {"name": None, "subtitle": "", "stance": "teach"}


def read_config(root):
    """A course declares itself in tutorboard.json at its root.

    Everything is optional. What is not declared is defaulted, and the default
    is only ever about how the board behaves, never about whether it works.
    """
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh) or {})
    except (OSError, ValueError):
        pass

    if not cfg.get("name"):
        cfg["name"] = os.path.basename(os.path.abspath(root)).replace("-", " ")

    # A subject is not a setting. Whatever a course file still says here is
    # dropped on the way through, so nothing downstream can branch on it again.
    cfg.pop("mode", None)

    stance = (cfg.get("stance") or "").lower()
    # Never guessed. Writing the code for somebody who wanted to learn it is the
    # one failure here that cannot be undone by the next card, so it is only ever
    # done because a repository asked for it in writing.
    cfg["stance"] = "do" if stance == "do" else "teach"
    return cfg


# ---------------------------------------------------------------------------
# the stance of THIS SITTING, which is not always the stance of the repository
# ---------------------------------------------------------------------------
#
# A repository was allowed one answer to "is the tutor here to teach the work or
# to do it", and a real project does not have one. PSYCH-ASR is the case that
# broke it: the grid-search plumbing around a bake-off is drudgery its owner has
# written fifty times and wants written for them, and the correction algorithm in
# `transcript/corrections.py` is the thing they actually need to understand. One
# repository, both answers, and one word in `tutorboard.json` to say them in --
# so the work went to a terminal, and once it was there the teaching went with
# it and the board saw neither.
#
# So the repository's word is the DEFAULT and a sitting may say otherwise. What
# does not change is that neither is ever guessed: a sitting stance is written by
# the person opening the sitting, on the board or at a terminal, and a sitting
# that says nothing inherits rather than infers.
STANCES = ("teach", "do")


def clean_stance(stance):
    """A stance from a request, or None if it is not one. Never raises."""
    stance = str(stance or "").strip().lower()
    return stance if stance in STANCES else None


def stance_for(root, state):
    """What this sitting's stance actually is: its own, or the repository's.

    Read here rather than in each caller so that there is one answer to it. A
    walkthrough is the exception and it is not this function's exception to
    make -- `sense` holds it, because what a walkthrough refuses is not a stance
    but a method: there is nothing to write either way when the machinery is
    already on disk.
    """
    own = clean_stance((state or {}).get("stance"))
    return own or read_config(root).get("stance") or "teach"
