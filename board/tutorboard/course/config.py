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


# ---------------------------------------------------------------------------
# what THIS sitting is for
# ---------------------------------------------------------------------------
#
# A stance says who writes the code. An AIM says what the sitting is for, and
# the two are not the same question: "teach me how this works" and "tell me what
# to write and I'll code it" are both `stance: teach` and they are not the same
# evening. Asked for as a list of things every sitting should be able to be:
# *"All tutoring sessions should have the capability of being a math tutor, a
# coder, a coding coacher, a presentation creator, a paper creator, and the
# ability to show any or all sections of said papers or presentations."*
#
# So the sitting carries one, chosen on the map at the moment of opening it, and
# `sense` puts it in the line the tutor is woken with. Six, and no more: a
# seventh would be a distinction nobody makes with a thumb.
#
#     teach   work it through properly -- the mathematics, done not described
#     build   the tutor writes the code and reports what it changed
#     coach   one step at a time, in English; the person types it
#     trace   read what is already there, line by line
#     drill   questions asked cold over a scope
#     paper   produce a document -- a write-up or a deck -- rather than an answer
#
# `slides` is `paper` with a different product and is spelled out separately at
# the point of use, because what the tutor has to do differs and the word for it
# should not.
AIMS = ("teach", "build", "coach", "trace", "drill", "paper", "slides")


def clean_aim(aim):
    """An aim from a request, or None if it is not one. Never raises.

    Dropped rather than refused, for the same reason a misspelled stance is: the
    request is about which sitting to open, and failing the whole of it over a
    word would leave somebody on the lesson they were trying to leave.
    """
    aim = str(aim or "").strip().lower()
    return aim if aim in AIMS else None


# What each aim actually asks the tutor to do, in one sentence, in the line it is
# woken with. Written here rather than in `sense` so that the words a person taps
# on the map and the words the tutor is given cannot drift apart.
AIM_MEANS = {
    "teach": "They asked to be TAUGHT this: work it through properly, one step "
             "at a time, and make them do the step. Do not write their code.",
    "build": "They asked you to BUILD it: write the code yourself, run it, and "
             "report what you changed and what it did. The card is a report, "
             "not an exercise.",
    "coach": "They asked to be TOLD WHAT TO WRITE: name the calls, the "
             "arguments and the order in English, one step per card, and let "
             "them type it. Do not write the code for them.",
    "trace": "They asked to be WALKED THROUGH code that already exists: trace "
             "it by hand with them, predict returns, say which branch runs. "
             "Nothing new is written in this sitting.",
    "drill": "They asked to be SET PROBLEMS on this, cold. Ask; do not explain "
             "first.",
    "paper": "They asked you to WRITE IT UP as a document: the product of this "
             "sitting is a paper kept in the repository, not an answer. Draft "
             "it, show them sections as you go, and take corrections.",
    "slides": "They asked you to BUILD A DECK about this: the product of this "
              "sitting is slides kept in the repository. Draft them, show them "
              "on the board a page at a time, and take corrections.",
}
