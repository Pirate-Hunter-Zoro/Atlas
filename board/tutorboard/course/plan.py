"""plan.py -- where a project writes down what it is doing next.

A course that follows a book has `chapters.tsv`, and that one file is the whole
reason Galois Theory is painless: the contents drawer lists eleven chapters, a
tap opens one, and nobody types a command or decides anything. A project has no
such file, so the drawer said this, in as many words:

    "No chapters or problem sets in this repository, so sittings here are made
     as you go."

Which is the pain, rendered as a paragraph of interface. Every sitting in those
repositories began with somebody deciding what it was about, at a keyboard, in a
terminal -- and a cold tutor beginning by reading a 1,500-line README, following
a pointer out of it, and reading a 1,300-line task list to find out what comes
next.

**But a working project does write down what it is doing next.** It is not called
a syllabus and it is not in this repository, and those are the only two reasons
nothing was reading it. PSYCH-ASR's README names
`~/Research-Journey/planning/PSYCH-ASR_TODO.txt`; that file opens with a block
headed `>>> NEXT ACTION (start here in a fresh session) <<<` and a numbered list
of steps. That is a syllabus. It is maintained, it is accurate, and it was being
read by nobody but a person.

So this module answers two questions and nothing else: **where is the plan**, and
**what are the next few things in it**. Both are discovered -- from the
repository's own `tutorboard.json` if it says, and otherwise from what the README
already points at, because a README that names its task list has declared it as
plainly as any config key would and is a file somebody actually maintains.

Standard library only, like everything else.
"""

import json
import os
import re
import time

# `paths` is bound as `toolpaths` because THIS module defines a public
# `paths(root)` -- every plan a workspace has -- and the import would shadow it.
# Same trap as `map` being a builtin, same answer: the module keeps its name and
# the import is the one that moves.
from .. import atlas
from .. import paths as toolpaths

# What a plan is called, when nothing names one. Ordered: a repository with both
# a ROADMAP and a TODO means the TODO, because the TODO is the one that changes.
COMMON = ("TODO.md", "TODO.txt", "TASKS.md", "PLAN.md", "ROADMAP.md", "NEXT.md")

# A path-shaped token in a README that looks like a plan. Deliberately narrow:
# it must END in one of the plan words plus an extension, so `planning/` alone
# does not match and neither does a sentence about planning.
POINTER = re.compile(
    r"[~\w./-]*(?:TODO|TASKS|ROADMAP|PLAN|BACKLOG)[\w.-]*\.(?:md|txt|org)\b",
    re.IGNORECASE)

# How many steps are worth putting in a drawer. A plan has forty items in it and
# a person opening a drawer wants to know what is next, not to read the plan --
# which is on disk and can be opened whole.
#
# It was 12 while a plan was read in one form only. `TRD-EHR_TODO.txt` has five
# `STEP`s and thirteen unchecked checklist items, and a cap of 12 over both
# would have cut six of them -- which is the same defect the merge was written
# to end, half-fixed and harder to see. Doubled rather than made per-kind: two
# numbers are two things to get wrong, and the picture is protected by
# `map.MAX_CHIPS` at six to a box whatever this says.
MAX_STEPS = 24

# The blurb under a step in the drawer, and in the line a tutor is woken with.
# Enough to tell two steps apart; not enough to be the step.
SUMMARY = 240


def _named(root):
    """A plan this repository declares outright, if it declares one."""
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            said = (json.load(fh) or {}).get("plan")
    except (OSError, ValueError):
        return None
    return _resolve(root, said) if said else None


def _allowed(target, root):
    """May a path written in a file be read? Three places, and nowhere else.

    A path out of a file is a path somebody could have written anything into,
    and this one is read, listed in a drawer and named in a prompt. So the
    bound is explicit and it is small:

    1. inside this workspace;
    2. anywhere inside the repository -- which is the bound that WIDENED when
       eleven repositories became one. A README pointing at another project's
       plan used to be pointing at a sibling directory; it now points across
       the tree at `../../projects/libr-local-llm/LOCAL-LLM_TODO.txt`, and that
       is a normal thing to do rather than an exception;
    3. the two directories that are deliberately OUTSIDE the tree -- the PHI
       directory and the artifact directory -- because a workspace README's
       whole job is to say where its data went, and a plan may legitimately
       live beside it.

    Widened, not removed. `/etc/passwd` is still not a plan.
    """
    return toolpaths.within(target, root, atlas.root(),
                            *toolpaths.outside_tree())


def _resolve(root, rel):
    """A path from a README or a config, made real -- or None."""
    rel = str(rel or "").strip().strip("`'\"")
    if not rel:
        return None
    root = os.path.realpath(root)

    if rel.startswith("~"):
        tries = [os.path.expanduser(rel)]
    elif os.path.isabs(rel):
        tries = [rel]
    else:
        # The workspace first, then the repository root, so `courses/Probability
        # /chapters.tsv` written from anywhere resolves the way it reads.
        tries = [os.path.join(root, rel),
                 os.path.join(os.path.dirname(root), rel),
                 os.path.join(atlas.root(), rel)]

    if not os.path.dirname(rel.lstrip("~/")):
        # A bare filename, which is how a README names a plan it expects the
        # reader to already know the location of: "its live task list is
        # LOCAL-LLM_TODO.txt". Look through the repository for it -- one listing
        # of each family and one of each workspace, which is exactly the two
        # levels the tree has. Bounded and shallow: two directory listings
        # deep, not a tree walk.
        tries += _beside(atlas.root(), os.path.basename(rel))

    for path in tries:
        target = os.path.realpath(path)
        if not os.path.isfile(target):
            continue
        if _allowed(target, root):
            return target
    return None


def _beside(base, name):
    """Where a bare plan filename could be: two levels down from the root.

    `base` is the repository root, so the first level is the families and the
    second is the workspaces. It was the courses' parent directory and its
    children when they were siblings -- the same two listings, one shape up.
    """
    out = []
    try:
        for fam in sorted(os.listdir(base)):
            if fam.startswith("."):
                continue
            here = os.path.join(base, fam)
            if not os.path.isdir(here):
                continue
            out.append(os.path.join(here, name))
            try:
                for sub in sorted(os.listdir(here)):
                    if not sub.startswith(".") and os.path.isdir(os.path.join(here, sub)):
                        out.append(os.path.join(here, sub, name))
            except OSError:
                continue
    except OSError:
        return []
    return out


def _all_pointed_at(root):
    """EVERY plan this repository's README names, in the order it names them.

    A repository usually has one. A NARRATIVE HUB has three: Research-Journey
    holds `TRD-EHR_TODO.txt`, `PSYCH-ASR_TODO.txt` and `LOCAL-LLM_TODO.txt`, one
    per project it covers, and taking the first match made its drawer say
    "What's next" over TRD-EHR's plan alone -- silently, with nothing on screen
    saying the other two existed. A list that is wrong is worse than a list that
    is empty, because nothing about it looks wrong.
    """
    try:
        with open(os.path.join(root, "README.md"), "r", encoding="utf-8") as fh:
            text = fh.read(200000)
    except OSError:
        return []
    out = []
    for match in POINTER.finditer(text):
        found = _resolve(root, match.group(0))
        if found and found not in out:
            out.append(found)
    return out


def _pointed_at(root):
    """The plan this repository's README names, if it names one.

    A README that says where the work is planned has declared it as plainly as a
    config key would, and it is the file somebody actually keeps up to date. The
    match is anchored on the filename rather than on the prose around it, so
    what is found is a path and not a sentence.
    """
    try:
        with open(os.path.join(root, "README.md"), "r", encoding="utf-8") as fh:
            text = fh.read(200000)
    except OSError:
        return None
    for match in POINTER.finditer(text):
        found = _resolve(root, match.group(0))
        if found:
            return found
    return None


def paths(root):
    """Every plan this repository has, in the order it names them.

    Declared first, pointed at second, conventional third -- and a declaration
    stops the search, because a repository that says which file it plans in has
    answered the question. Otherwise all of them: a hub covering three projects
    has three, and showing one of them as though it were the whole of what comes
    next is the failure this returns a list to prevent.
    """
    said = _named(root)
    if said:
        return [said]
    found = _all_pointed_at(root)
    if found:
        # A README names the plans of the projects it depends on as well as its
        # own -- PSYCH-ASR points at LOCAL-LLM_TODO.txt because it runs on that
        # infrastructure. So if one of them is named after THIS repository, it is
        # this repository's plan and the rest are mentions. Only where none of
        # them is -- a narrative hub, holding the plans for three projects and
        # owning none -- are they all offered.
        mine = [p for p in found if _about(root, p)]
        return mine or found
    return [os.path.join(root, n) for n in COMMON
            if os.path.isfile(os.path.join(root, n))][:1]


def _about(root, target):
    """Is this plan named after the repository it was found from?

    `PSYCH-ASR_TODO.txt` is PSYCH-ASR's; `LOCAL-LLM_TODO.txt` is not, even
    though PSYCH-ASR's README names it. Either name may contain the other --
    the repository `libr-local-llm` keeps its plan in `LOCAL-LLM_TODO.txt` --
    so containment in either direction is the test, on names reduced to their
    letters and digits.
    """
    def flat(text):
        return re.sub(r"[^a-z0-9]+", "", (text or "").lower())
    who = flat(_project_of(target))
    me = flat(os.path.basename(os.path.realpath(root)))
    return bool(who) and bool(me) and (who in me or me in who)


def _project_of(target):
    """`planning/PSYCH-ASR_TODO.txt` -> `PSYCH-ASR`."""
    return re.sub(r"[-_]?(TODO|TASKS|PLAN|ROADMAP|BACKLOG)\b.*$", "",
                  os.path.splitext(os.path.basename(target))[0], flags=re.I)


def path(root):
    """The first of them, for anything that can only hold one."""
    every = paths(root)
    return every[0] if every else None


def where(root):
    """The plan's path as a person would write it: relative, or `~`-prefixed."""
    target = path(root)
    return _short(root, target) if target else ""


def _short(root, target):
    if not target:
        return ""
    root = os.path.realpath(root)
    if target.startswith(root + os.sep):
        return os.path.relpath(target, root)
    home = os.path.realpath(os.path.expanduser("~"))
    if target.startswith(home + os.sep):
        return "~/" + os.path.relpath(target, home)
    return target


# A numbered step, which is what these plans are written in:
#   "  STEP 1. THE TYPIST BAKE-OFF -- VARY THE ASR MODEL. (Added 2026-09-09.)"
STEP = re.compile(r"^\s{0,4}(?:STEP|PHASE|TASK)\s+([0-9]+[a-z]?)[.):]\s*(\S.*)$")

# A markdown checklist, which is what most plans are written in. Only the
# UNCHECKED ones: a plan lists what is left, and a drawer of finished work is a
# drawer of things nobody can do.
TODO_ITEM = re.compile(r"^\s{0,6}[-*+]\s+\[( |x|X)\]\s+(\S.*)$")

# A heading, as the last resort. `##` and deeper only -- the title of the
# document is not a step in it.
HEADING = re.compile(r"^(#{2,4})\s+(\S.*)$")

# Where these plans put the thing to do next, and it is worth honouring: a file
# that says "start here in a fresh session" has answered the question this
# module exists to ask.
#
# A RESUME MARKER IS NOT ONE OF THESE. `TRD-EHR_TODO.txt` carries
# `<<< RESUME HERE 2026-09-01 >>>` on a checklist item eleven hundred lines
# further down, and it says where somebody stopped reading rather than what the
# plan does next. The block at the top says that, in those words, and it is the
# one this honours. Order is the file's own from there.
START_HERE = re.compile(r"NEXT ACTION|START HERE|WHAT WE DO NEXT|READ THIS FIRST",
                        re.IGNORECASE)


def _trim(text):
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text[:SUMMARY].rstrip() + ("…" if len(text) > SUMMARY else "")


def _title(text):
    """A step's own name, without the sentence that follows it.

    These plans write `STEP 1. THE TYPIST BAKE-OFF -- VARY THE ASR MODEL. (Added
    2026-09-09.)`, and the drawer wants the first clause of that. The date stamp
    is provenance for a reader of the file and noise in a title bar.
    """
    text = re.sub(r"\s*\((?:Added|Updated|Corrected)[^)]*\)\s*", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip(" .")
    # The first sentence. These plans shout their titles -- "INTEGRATE HIS
    # SECTIONS. Same treatment as the 2026-09-02 round: take..." -- so a split
    # that only fires after a lower-case letter never fires at all, and the
    # drawer gets a paragraph where it wanted a name.
    cut = re.split(r"\.\s+", text, maxsplit=1)[0]
    return cut.strip(" .")[:110]


# Read off disk on every payload otherwise, four times a second, for a file
# somebody edits once an evening. Same rule as `walk.units` and
# `reading.documents`.
CACHE_SECONDS = 30
_cache = {}


def steps(root):
    """The next few things this project has written down, in the plan's order.

    Never invented and never re-ordered. If the plan says step 4 is first, step 4
    is first -- a drawer that quietly sorts somebody's plan is a drawer that
    disagrees with the file they maintain.
    """
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = _steps(root)
    _cache[key] = (time.time(), found)
    return found


def _steps(root):
    out = []
    every = paths(root)
    for target in every:
        out += _steps_in(target, len(every) > 1)
    return out[:MAX_STEPS]


def _steps_in(target, say_which):
    """The steps in one plan file. `say_which` when there is more than one.

    A hub's drawer has to name the project each step belongs to, or "1. INTEGRATE
    HIS SECTIONS" sits under "What's next" with nothing saying which of three
    papers it is about.
    """
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []

    # Start at the block that says to start there, where the plan has one.
    begin = 0
    for i, line in enumerate(lines[:400]):
        if START_HERE.search(line):
            begin = i
            break

    # EVERY FORM THE PLAN WROTE, TOGETHER, IN THE PLAN'S OWN ORDER.
    #
    # This tried each kind in turn and stopped at the first that matched
    # anything. `TRD-EHR_TODO.txt` opens with `STEP 1.` through `STEP 5.`, all
    # about paper 1's manuscript, so those five were the whole of what the board
    # knew about it: the file's thirteen unchecked `- [ ]` items -- the
    # falsification battery, the 5-fold CV, the entire counterfactual half --
    # reached the board nowhere, and a checklist item written today was
    # invisible for the same reason.
    #
    # Headings stay the last resort they always were. A document with `##`
    # sections and no steps in it is a different kind of file, and reading its
    # headings as tasks is what that branch is for -- reading them as tasks
    # ALONGSIDE real steps would put the plan's own section titles in the drawer
    # next to the work.
    out = _collect(lines, begin, (("step", STEP), ("item", TODO_ITEM)))
    if not out:
        out = _collect(lines, begin, (("heading", HEADING),))
    # Which plan this came out of. `PSYCH-ASR_TODO.txt` becomes `PSYCH-ASR`,
    # which is what its owner calls the project and what a drawer has room for.
    who = _project_of(target)
    for x in out:
        x["from"] = who or os.path.basename(target)
        x["file"] = target
        if say_which and who:
            x["label"] = "%s · %s" % (who, x["label"])
    return _distinct(out)


def _distinct(found):
    """One label, one step -- because `label` is what a step is looked up BY.

    `/session` looks a step up by its label before it opens a sitting on it, so
    two steps answering to one label is one of them unreachable. A numbered
    `STEP 3.` and a checklist item somebody wrote as `- [ ] 3. …` are the way it
    happens.

    Suffixed rather than dropped: a step the plan wrote is a step, and the one
    that loses the collision is still the person's to open.
    """
    seen, out = {}, []
    for step in found:
        label = step["label"]
        seen[label] = seen.get(label, 0) + 1
        if seen[label] > 1:
            step = dict(step, label="%s (%d)" % (label, seen[label]))
        out.append(step)
    return out


def _collect(lines, begin, kinds):
    """Every step in one plan, in one pass, whatever form each one is written in.

    `kinds` is `(name, regex)` pairs, tried in order on each line so that a line
    matching two of them is the first kind -- which only arises for a heading
    that is also something else, and the plan's own word for it wins.
    """
    # WHERE EACH ENTRY OF THE PLAN BEGINS, whatever kind it is. Two things need
    # this and both of them were wrong when it was a per-kind scan: the ORDER,
    # which is the file's, and the STOP LINE, which is the next entry of any
    # kind rather than the next one of the same kind. A step whose body ran on
    # over the checklist items after it was matched against every module they
    # mention, and `map._attach` put its chip on boxes the step says nothing
    # about.
    #
    # A finished `- [x]` item is in this list and is not a step. It is not a
    # thing to do, and it is still the end of whatever prose came before it.
    marks = []
    for i in range(begin, len(lines)):
        for kind, rx in kinds:
            m = rx.match(lines[i])
            if m:
                marks.append((i, kind, m))
                break

    found = []
    for at, (i, kind, m) in enumerate(marks):
        if kind == "item" and m.group(1).strip():
            continue                        # already done; not a thing to do
        if kind == "step":
            # The plan's own number, because a person reading the file and a
            # person reading the drawer have to be talking about the same step.
            num, head = m.group(1), m.group(2)
        else:
            # A checklist item has no number of its own, so it takes its place
            # in the MERGED sequence -- the first item after five steps is 6,
            # not a second 1 on a picture that already has one.
            num, head = str(len(found) + 1), m.group(2)
        # The body is whatever follows until the next entry, and it is the half
        # that says what the step actually involves.
        stop = marks[at + 1][0] if at + 1 < len(marks) else len(lines)
        body = []
        for line in lines[i + 1:stop]:
            body.append(line)
            if len(" ".join(body)) > SUMMARY * 3:
                break
        found.append({
            "num": num,
            "title": _title(head),
            "label": "%s. %s" % (num, _title(head)) if kind == "step" else _title(head),
            "summary": _trim(head + " " + " ".join(body)),
            "line": i + 1,
        })
        if len(found) >= MAX_STEPS:
            break
    return found


def status(root, state):
    """What the board shows, and what a cold turn is told.

    None where there is no plan at all, which is a real answer about a course
    that follows a book -- it has a syllabus instead, and `syllabus.py` is what
    reads that.
    """
    found = steps(root)
    if not found:
        return None
    here = ((state or {}).get("chapter") or "").strip()
    return {
        "where": "; ".join(_short(root, p) for p in paths(root)),
        "steps": found,
        "here": here,
        "next": found[0]["label"],
    }


