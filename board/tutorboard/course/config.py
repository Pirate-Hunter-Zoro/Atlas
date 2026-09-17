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
import re

from .. import atlas


# Who writes the code. Declared here rather than beside `clean_stance` below,
# because `read_config` has to be able to say whether a repository ANSWERED the
# question or was given the default -- see `said_stance`.
STANCES = ("teach", "do")

DEFAULT_CONFIG = {"name": None, "subtitle": "", "stance": "teach"}


def read_config(root):
    """A course declares itself in tutorboard.json at its root.

    Everything is optional. What is not declared is defaulted, and the default
    is only ever about how the board behaves, never about whether it works.
    """
    cfg = dict(DEFAULT_CONFIG)
    # What the FILE said, kept apart from what it is defaulted to. The two are
    # different answers and `said_stance` below turns on the difference.
    said = {}
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            said = json.load(fh) or {}
    except (OSError, ValueError):
        said = {}
    if isinstance(said, dict):
        cfg.update(said)
    else:
        said = {}

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
    # AND WHETHER IT WAS SAID AT ALL, which the default above cannot express. A
    # family declares a default style in `atlas.json`, and that default can only
    # apply to a repository that has not answered for itself -- so "teach because
    # it says teach" and "teach because nothing said anything" have to be
    # different answers here. See `stance_for`.
    cfg["said_stance"] = str(said.get("stance") or "").strip().lower() in STANCES
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
# that says nothing inherits rather than infers. The two words themselves are
# `STANCES`, at the top of this file, because `read_config` needs them too.


def clean_stance(stance):
    """A stance from a request, or None if it is not one. Never raises."""
    stance = str(stance or "").strip().lower()
    return stance if stance in STANCES else None


def stance_for(root, state):
    """What this sitting's stance actually is, and it is DERIVED, not parallel.

    Read here rather than in each caller so that there is one answer to it. A
    walkthrough is the exception and it is not this function's exception to
    make -- `sense` holds it, because what a walkthrough refuses is not a stance
    but a method: there is nothing to write either way when the machinery is
    already on disk.

    AN AIM ALREADY ANSWERS THIS. `build` with a stance of `teach` is a
    contradiction, and while the two were resolved separately the browser was
    sending both -- deciding on its own authority something the repository and
    the family had already said. So the order is:

        this sitting's own stance  -- somebody tapped it, for this evening
        this sitting's aim         -- `AIM_STANCE`; build writes, coach does not
        the repository's stance    -- `tutorboard.json`, where it says so
        its family's default aim   -- `atlas.json`, through `aim_for`

    and nothing below the first two is a guess: each is something written down
    somewhere, by somebody, about this workspace or the family it is in.
    """
    own = clean_stance((state or {}).get("stance"))
    if own:
        return own
    mine = clean_aim((state or {}).get("aim"))
    if mine:
        return AIM_STANCE.get(mine, "teach")
    cfg = read_config(root)
    if cfg.get("said_stance"):
        return cfg.get("stance") or "teach"
    return AIM_STANCE.get(aim_for(root, state), "teach")


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
    # These two say what the document IS ABOUT as well as what to do, because
    # these are the words a person taps and the words the tutor is given, and
    # they must not drift from `sense.MAKE_SENSE`. That is why this dictionary is
    # in this file rather than in `sense`.
    "paper": "They asked you to WRITE IT UP as a document: the product of this "
             "sitting is a paper kept in writeups/, not an answer. Draft it, "
             "show them sections as you go, and take corrections. It is an "
             "explainer about the machinery -- how this works, and the "
             "mathematics -- written for somebody who was not in the room. It "
             "is not a write-up of this sitting.",
    "slides": "They asked you to BUILD A DECK about this: the product of this "
              "sitting is slides kept in writeups/. Draft them, show them on "
              "the board a page at a time, and take corrections. The deck "
              "explains the machinery to somebody who was not in the room; it "
              "is not a record of this sitting.",
}


# THE TWO AIMS THAT ARE HELD OVER A SCOPE rather than simply chosen. A
# walkthrough needs a list of files and a drill needs a part of the repository to
# ask over, so choosing one of those IS choosing what it is over -- which is a
# tap on the map and a new sitting. Everything that offers the aims as a choice
# for the sitting already open leaves these two out and says why.
AIMS_OVER = ("trace", "drill")

# WHICH AIMS WRITE AND WHICH TEACH, so that a stance never has to be chosen
# beside an aim that has already answered. `build`, `paper` and `slides` produce
# a change to the repository; the other four produce cards.
AIM_STANCE = {
    "build": "do",
    "paper": "do",
    "slides": "do",
    "teach": "teach",
    "coach": "teach",
    "trace": "teach",
    "drill": "teach",
}


# ---------------------------------------------------------------------------
# WHICH ASSISTANT, and why only the shape of the name is checked here
# ---------------------------------------------------------------------------
#
# The registry is in `bin/tutor` and belongs there: an agent entry is a command
# recipe, so a second model is a second entry whose `cmd` carries the flag, and
# this file has no business knowing what commands a machine has. What a request
# can be checked against here is that it is a NAME -- something safe to write
# into `state.json` and match against the registry later.
#
# An unknown one is DROPPED by `resolve_agent` rather than refused, which is the
# rule a misspelled stance already follows and for a sharper reason: a sitting is
# being opened, and leaving a course with no tutor at all over a word from a
# browser is worse than ignoring the word.
AGENT_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,31}$")


def clean_agent(agent):
    """An assistant name from a request, or None if it is not one. Never raises."""
    agent = str(agent or "").strip().lower()
    return agent if AGENT_RE.match(agent) else None


def sitting_agent(root):
    """Which assistant THIS SITTING asked for, off its own `state.json`, or None.

    Read here so that the launcher and the server ask one function. It sits
    beside `node` and `aim` under the rule `_mark` states: a box chosen for an
    evening's work is not a statement about what the repository is, and neither
    is an assistant. `tutorboard.json` is the layer that IS such a statement.
    """
    if not root:
        return None
    try:
        with open(os.path.join(root, "live", "state.json"), "r",
                  encoding="utf-8") as fh:
            return clean_agent((json.load(fh) or {}).get("agent"))
    except (OSError, ValueError, AttributeError):
        return None


def family_aim(root, base=None):
    """The default style of the family this workspace sits in, or "".

    `atlas.json` "names and orders the five families and says which hold somebody
    else's work" -- and a default style is a property of a family in exactly that
    sense. It is still not a registry of workspaces: nothing there names one, and
    making a course is still `mkdir courses/Topology`.
    """
    try:
        fam = atlas.family_of(root, base)
        for one in atlas.families(base):
            if one["id"] == fam:
                return clean_aim(one.get("aim")) or ""
    except Exception:                                        # noqa: BLE001
        return ""
    return ""


def aim_for(root, state, base=None):
    """What this sitting is FOR, with the whole precedence in one function.

        the sitting's own aim   -- tapped on the map, or `board aim`
        the workspace's own     -- `tutorboard.json`
        the family's default    -- `atlas.json`

    A SITTING NOBODY OPENED FROM THE MAP HAD NO STYLE AT ALL. `tutor galois`,
    `board open`, a chapter tapped in the contents drawer and a board resumed
    after a reboot all left `aim` unset, so the sitting ran on stance alone --
    which is `teach` nearly everywhere and is the wrong answer for a project.
    """
    own = clean_aim((state or {}).get("aim"))
    if own:
        return own
    said = clean_aim(read_config(root).get("aim"))
    if said:
        return said
    return family_aim(root, base)
