"""What a subject's `tutorboard.json` says, and the sitting axes still read
beside it (stance, aim, kind, agent) until T15 collapses them into a mode.
"""

import json
import os
import re
import shlex

from .. import atlas
from . import repo as course_repo


# Who writes the code. A sitting's own word only: `tutorboard.json` no longer
# carries one.
STANCES = ("teach", "do")


def read_config(root):
    """What a subject's `tutorboard.json` says: `name`, `phi`, `check`, `relay`.

    Everything is optional. `stance`, `aim`, `subtitle` and `mode` left in a
    file are ignored; `agent` passes through until T15. `name` defaults
    to the directory name with dashes as spaces. `phi` stays literal -- True or
    False exactly as written, None for anything else -- because only a literal
    False opens check output (`holds.output_open`, which also wants False at
    HEAD, no fence and the policy loaded). `relay` is the file's object, else
    {}. `check` is validated by `clean_check`; `check_problems` and
    `check_line` are derived from it.
    """
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            said = json.load(fh) or {}
    except (OSError, ValueError):
        said = {}
    if not isinstance(said, dict):
        said = {}
    phi = said.get("phi")
    relay = said.get("relay")
    cfg = {
        "name": said.get("name")
        or os.path.basename(os.path.abspath(root)).replace("-", " "),
        "phi": phi if isinstance(phi, bool) else None,
        "relay": relay if isinstance(relay, dict) else {},
        # The per-kind provider, as written; `workspace_agent` reads it. T15
        # deletes per-kind agents and this key with them.
        "agent": said.get("agent"),
    }
    cfg["check"], cfg["check_problems"] = clean_check(said.get("check"))
    cfg["check_line"] = check_line(cfg["check"])
    return cfg


# ---------------------------------------------------------------------------
# a workspace's CHECK: what `board send` runs on a held step
# ---------------------------------------------------------------------------
#
#     "check": "uv run --extra test python -m pytest tests -q"
#
# A string is one shell command for the whole workspace: it runs as `bash -c`
# and has no placeholders. The object form says the same without a shell, and
# can also check only what is held:
#
#     "check": {"all": ["go", "test", "./..."],
#               "one": ["go", "test", "./{dir}/..."],
#               "path": ["/usr/local/go/bin"]}
#
# `all` checks the whole workspace and `one` checks the held paths, through the
# placeholders `{dir}`, `{file}` and `{module}` (`holds.check_spec` fills them).
# `argv[0]` is one of `CHECK_PROGRAMS` or a workspace script, which the hold
# requires tracked and unchanged at HEAD. It runs without a shell, with `path`
# put in front of PATH.
CHECK_PROGRAMS = ("go", "lake", "uv", "python3", "bash", "make")
CHECK_HOLES = ("{dir}", "{file}", "{module}")
_HOLE_RE = re.compile(r"\{[^}]*\}")


def check_program(word):
    """Is this an allowed `argv[0]`: a named program, or a workspace script?

    A script is a workspace path with a directory or an extension in it, so a
    bare program name that is not one of `CHECK_PROGRAMS` is refused rather
    than read as a file nobody wrote."""
    word = str(word or "")
    if word in CHECK_PROGRAMS:
        return True
    rel = word.replace("\\", "/")
    return (bool(rel) and not rel.startswith(("/", "~", "-"))
            and ".." not in rel.split("/") and "{" not in rel
            and ("/" in rel or "." in os.path.basename(rel)))


def _leaves(word):
    """Does this word of a check name a path outside the workspace? An
    absolute or home path, or a `..` step, anywhere in it: after `--opt=`,
    or inside a `bash -c` line. A check runs from the workspace root, and its
    output is judged by that workspace's fence, so it may not reach into
    another one."""
    for part in _WORD_SPLIT.split(str(word).replace("\\", "/")):
        if part.startswith(("/", "~", "$")) or ".." in part.split("/"):
            return True
    return False


_WORD_SPLIT = re.compile(r"[\s;&|()<>'\"=`:,]+")


def check_line(chk):
    """The workspace check as one command line, for the brief. "" if none."""
    if not chk:
        return ""
    if chk.get("line"):
        return chk["line"]
    return " ".join(chk.get("all") or chk.get("one") or [])


def clean_check(raw):
    """`(check, problems)` for a `tutorboard.json` `check`. None if absent."""
    if raw is None or raw == "":
        return None, []
    if isinstance(raw, str):
        line = raw.strip()
        if not line or _HOLE_RE.search(line):
            return None, ["`check`, as a string, is one shell command with no "
                          "placeholders; `{dir}`, `{file}` and `{module}` need "
                          "the object form"]
        try:
            words = shlex.split(line)
        except ValueError:
            return None, ["`check` is not a command a shell can read"]
        out = [w for w in words if _leaves(w)]
        if out:
            return None, ["`check` names %s, outside the workspace"
                          % ", ".join(out[:3])]
        return {"all": ["bash", "-c", line], "line": line}, []
    if not isinstance(raw, dict):
        return None, ["`check` must be a shell command, or an object with "
                      "`all` and/or `one`"]
    out, problems = {}, []
    for key in ("all", "one"):
        argv = raw.get(key)
        if argv is None:
            continue
        if (not isinstance(argv, list) or not argv
                or not all(isinstance(w, str) and w for w in argv)):
            problems.append("`check.%s` must be a list of words" % key)
            continue
        if not check_program(argv[0]):
            problems.append("`check.%s` starts with %r, which is neither one of "
                            "%s nor a workspace script"
                            % (key, argv[0], ", ".join(CHECK_PROGRAMS)))
            continue
        out_of = [w for w in argv if _leaves(w)]
        if out_of:
            problems.append("`check.%s` names %s, outside the workspace"
                            % (key, ", ".join(out_of[:3])))
            continue
        holes = [x for w in argv for x in _HOLE_RE.findall(w)]
        wrong = [x for x in holes if x not in CHECK_HOLES or key == "all"]
        if wrong:
            problems.append("`check.%s` has %s; only `one` may hold one, and "
                            "only %s" % (key, ", ".join(sorted(set(wrong))),
                                         ", ".join(CHECK_HOLES)))
            continue
        out[key] = list(argv)
    path = raw.get("path")
    if path is not None:
        if (not isinstance(path, list)
                or not all(isinstance(d, str) and os.path.isabs(d) for d in path)):
            problems.append("`check.path` must be a list of absolute directories")
        else:
            out["path"] = list(path)
    if not (out.get("all") or out.get("one")):
        return None, problems or ["`check` names neither `all` nor `one`"]
    return out, problems


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
# `STANCES`, at the top of this file.


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
        its family's default aim   -- `atlas.FAMILIES`, through `aim_for`

    and nothing below the first two is a guess: each is something written down
    somewhere, by somebody, about this workspace or the family it is in.

    The last of those can only ever resolve to `teach` now, and `aim_for` is
    where that is decided rather than here: a family default is a style and is
    never on its own the answer to who writes the code.
    """
    own = clean_stance((state or {}).get("stance"))
    if own:
        return own
    mine = clean_aim((state or {}).get("aim"))
    if mine:
        return AIM_STANCE.get(mine, "teach")
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
    #
    # AND EACH ANSWERS TWO QUESTIONS SEPARATELY. How the document reads is
    # fixed -- the subject explained, never the evening narrated. What it covers
    # is not: a paper about the concepts an evening covered is a legitimate ask,
    # and one refusal answering both questions turned it away.
    "paper": "They asked you to WRITE IT UP as a document: the product of this "
             "sitting is a paper kept in writeups/, not an answer. Draft it, "
             "show them sections as you go, and take corrections. It is an "
             "explainer about the machinery -- how this works, and the "
             "mathematics -- written for somebody who was not in the room, and "
             "never a narration of this sitting: no first person, and no "
             "reference to its cards or its questions. What it COVERS may be "
             "one part of the repository, a chapter, or the concepts this "
             "sitting covered.",
    "slides": "They asked you to BUILD A DECK about this: the product of this "
              "sitting is slides kept in writeups/. Draft them, show them on "
              "the board a page at a time, and take corrections. The deck "
              "explains the machinery to somebody who was not in the room and "
              "is never a narration of this sitting: no first person, and no "
              "reference to its cards or its questions. What it COVERS may be "
              "one part of the repository, a chapter, or the concepts this "
              "sitting covered.",
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
# the KIND of a sitting: learn, coach or build
# ---------------------------------------------------------------------------
#
# Every sitting, in every workspace, is one of three kinds, and a kind is not a
# third axis beside stance and aim. It names an aim, and the aim names the
# stance:
#
#     learn  -> aim teach -> stance teach   a board lesson; no code
#     coach  -> aim coach -> stance teach   they write the part being learned,
#                                           one step per card; the tutor
#                                           writes the plumbing
#     build  -> aim build -> stance do      the work is done; the card a report
#
# Read back the other way by `kind_for`, so a sitting opened with an aim and no
# kind still has one. Learn and coach share the teach stance, and where nothing
# says which, a thread's sitting is coach when the thread's files are code.
KINDS = ("learn", "coach", "build")
KIND_AIM = {"learn": "teach", "coach": "coach", "build": "build"}
AIM_KIND = {"teach": "learn", "trace": "learn", "drill": "learn",
            "coach": "coach",
            "build": "build", "paper": "build", "slides": "build"}

# What each kind asks of the turn, in one line. The whole of each is
# `live/TEACHING.md`'s; this is which section to hold to. Here rather than in
# `brief`, so the brief and the waking line say the same words.
KIND_SENSE = {
    "learn": "a LEARN sitting: a board lesson run by live/TEACHING.md -- "
             "exercises, their handwriting, a compiled write-up. You write none "
             "of the code or proof being learned.",
    "coach": "a COACH sitting: they write the code the sitting exists to teach "
             "(the estimator, the solver, the proof) and you guide one step per "
             "card (live/TEACHING.md, *A coach sitting*). You write the "
             "plumbing yourself: figures, dataframe reshaping, serialization, "
             "test and job scaffolding. Read their diff and run the check "
             "yourself, except in a sitting held at the cluster, where the "
             "check runs there and its result comes to you.",
    "build": "a BUILD sitting: you or your agents do the work and the card is "
             "a report of what changed.",
}


def clean_kind(kind):
    """A kind from a request, or None if it is not one. Never raises."""
    kind = str(kind or "").strip().lower()
    return kind if kind in KINDS else None


def kind_aim(kind, aim=None):
    """The aim a kind opens with. An aim that already belongs to it is kept,
    so `build` with `paper` stays a paper."""
    kind = clean_kind(kind)
    aim = clean_aim(aim)
    if not kind:
        return aim
    if aim and AIM_KIND.get(aim) == kind:
        return aim
    return KIND_AIM[kind]


def _is_code(root, rel):
    """Is this workspace path source code, or a directory holding some?"""
    from . import walk                                       # local: a cycle
    target = os.path.join(root, rel)
    if os.path.isdir(target):
        seen = 0
        for _dir, _subs, names in os.walk(target):
            for n in names:
                if os.path.splitext(n)[1] in walk.SOURCE:
                    return True
                seen += 1
                if seen > 400:
                    return False
        return False
    return os.path.splitext(rel)[1] in walk.SOURCE


def kind_for(root, state, files=None):
    """What kind this sitting is: its own, else read off its aim, else its stance.

    `files` are the thread's files, which answer learn-or-coach for a teach
    stance with nothing else to go on. "" for a sitting on no thread with
    nothing to say.
    """
    state = state or {}
    own = clean_kind(state.get("kind"))
    if own:
        return own
    # Only the sitting's OWN aim answers before the stance and the files: an
    # aim inherited from a family says how a workspace teaches, not whether
    # this thread is code.
    own_aim = clean_aim(state.get("aim"))
    if own_aim:
        return AIM_KIND[own_aim]
    if stance_for(root, state) == "do":
        return "build"
    if state.get("thread"):
        return "coach" if any(_is_code(root, f) for f in files or []) else "learn"
    return AIM_KIND.get(aim_for(root, state), "")


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


def workspace_agent(cfg, kind=None):
    """The assistant `tutorboard.json` names for a sitting of this kind, or None.

    `agent` is a name, which holds for every sitting in the workspace, or an
    object keyed by kind -- `{"learn": "deepseek", "build": "claude"}` -- where
    a kind it does not name falls through to the machine's default. The name is
    passed on as written, lowercased, so `resolve_agent` can refuse one this
    machine has not got rather than quietly teach with another.
    """
    said = (cfg or {}).get("agent")
    if isinstance(said, dict):
        said = said.get(clean_kind(kind) or "")
    if not isinstance(said, str):
        return None
    return said.strip().lower() or None


def sitting_kind(root):
    """The kind of the sitting open in this workspace, off its `state.json`, or ""."""
    if not root:
        return ""
    state = course_repo.session_state(root)
    try:
        return kind_for(root, state) or ""
    except Exception:                                        # noqa: BLE001
        return ""


def sitting_agent(root):
    """Which assistant THIS SITTING asked for, off its own `state.json`, or None.

    Read here so that the launcher and the server ask one function. It sits
    beside `node` and `aim` under the rule `_mark` states: a box chosen for an
    evening's work is not a statement about what the repository is, and neither
    is an assistant. `tutorboard.json` is the layer that IS such a statement.
    """
    if not root:
        return None
    return clean_agent(course_repo.session_state(root).get("agent"))


def sitting_box(state):
    """Which box of the map this sitting is on: its thread, else its node.

    A workspace with a thread file opens sittings on THREADS, and `state.json`
    carries `thread`. `node` is left only for a box of a derived map, which is
    a part of the tree rather than a question.
    """
    state = state or {}
    return str(state.get("thread") or state.get("node") or "").strip()


def family_aim(root, base=None):
    """The default style of the family this workspace sits in, or "".

    Read from `atlas.FAMILIES`. It is not a registry of workspaces: nothing
    there names one, and making a course is still `mkdir courses/Topology`.
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
        the family's default    -- `atlas.FAMILIES`, and only where it teaches

    A SITTING NOBODY OPENED FROM THE MAP HAD NO STYLE AT ALL. `tutor galois`,
    `board open`, a chapter tapped in the contents drawer and a board resumed
    after a reboot all left `aim` unset, so the sitting ran on stance alone --
    which is `teach` nearly everywhere and is the wrong answer for a project.

    A FAMILY DEFAULT IS A STYLE, NEVER AN INSTRUCTION TO WRITE CODE, and that is
    the one asymmetry in this function. `read_config` already states the rule it
    follows from: writing the code for somebody who wanted to learn it is the one
    failure here that cannot be undone by the next card, so it is only ever done
    because a repository asked for it in writing. A sentence about a DIRECTORY is
    not a repository asking. `projects` defaults to `build`, and `libr-local-llm`
    declares only a name -- so a plain lecture opened in a workspace somebody
    arrives at wanting to understand was a DOING turn, and being taught cost a
    tap on `teach` first. That is the wrong way round, and a tap is exactly what
    this whole tool exists to remove.

    So a doing aim inherited from a family is dropped and the sitting runs on
    stance, which is `teach` unless the sitting says otherwise. A teaching
    default still applies. `tutorboard.json` holds no aim or stance
    (`read_config`).
    """
    own = clean_aim((state or {}).get("aim"))
    if own:
        return own
    fam = family_aim(root, base)
    return "" if AIM_STANCE.get(fam) == "do" else fam
