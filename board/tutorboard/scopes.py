"""What a document written in this workspace can be ABOUT.

A PAPER OR A DECK IS COMMISSIONED FROM THE FRONT DOOR NOW, which is the whole
reason this module exists. Asked for in these words: *"the ability to write a
paper or a slide deck should just be an option on the homescreen, and from there
I want to be able to specify which projects/course, and which sections/results."*

From a sitting, `POST /writeup` needed nothing like this: the scope with nobody
naming one is the evening, and the evening is on the board in front of them. The
front door has no sitting and no board. It has a list of workspaces, and the
second half of the ask -- *which sections, which results* -- has to come from
somewhere the person is not expected to type.

SO THE ANSWER IS WHAT DISCOVERY ALREADY FOUND, AND NOTHING ELSE. A course knows
its chapters because `chapters.tsv` or `chapters/chNN-*/` is sitting there; it
knows its problem sets because `homework.sets` walks them; a project knows its
own parts; a research workspace knows the directories its figures came out of;
and every workspace knows what it has already written. None of that is
registered anywhere and none of it is walked twice -- every function called below
is the one the board's own pages already call, and three of them are cached.
Which is why there is no cache here: adding one would be a second copy of an
answer that is already remembered one level down.

A KEY IS OPAQUE AND IS LOOKED UP, NEVER JOINED ONTO A PATH. It comes back from a
browser, so it obeys the rule every other name in this system obeys -- `find`
compares it against the keys of the scopes this workspace actually offers, and a
miss is a miss. `course/library.find` is the rule and this is the same rule for a
shorter list.

Standard library only, like everything else.
"""

import os
import re

from .course import config
from .course import homework
from .course import library
from .course import results
from .course import review
from .course import syllabus


# How many rows any one group is ever given, and it is a stop rather than a
# taste. A dozen was the taste and it was wrong: Galois Theory has twenty
# chapters, so its second half -- the primitive element theorem, solvability,
# the whole point of the course -- could not be asked for from the door at all,
# which is the one thing this feature exists to do. The strip scrolls; a list
# somebody scrolls past is a smaller failure than a chapter nobody can name.
#
# It is still a stop, because a workspace with four hundred figures is a picker
# nobody can use, and what it drops it SAYS: `scopes()` carries the count and
# the sheet paints it. The tree's own caps -- `review.MAX_UNITS`,
# `results.MAX_FIGURES`, `library.MAX_DOCS` -- are the caps on WALKING and are
# above this one on purpose. This is the cap on OFFERING.
MOST = 40

# How much of a name becomes a key. Long enough that two chapters of a real
# course never collide; short enough that a key is a key rather than a sentence.
KEY_CHARS = 48

# The key for the one scope every workspace has, whatever else it has not got.
WHOLE = "workspace"

_SLUG = re.compile(r"[^a-z0-9]+")


def _key(kind, said, taken):
    """An opaque, stable key for one scope, unique within this list.

    STABLE, because the front door may hold a picker open across a reload and
    because a key is what the record of an ask is resolved from. So it is
    derived from the name of the thing and never from a position -- a counter
    handed out by walking a directory names a different chapter the moment a
    fifth one lands.

    AND THE TRUNCATION IS WHAT MAKES TWO THINGS ONE, so the collision is settled
    after it rather than before. Two contrast directories under one long results
    path -- `..._pipeline/bupropion_vs_ssri` and `..._pipeline/bupropion_vs_snri`
    -- are the same 48 characters, and a key that is dropped for colliding is a
    scope with no way to ask for it at all. They are suffixed instead, the way
    `map._unique` suffixes a box id: the second one answers to `-2`, and both
    are on the list. `taken` is the caller's set of what it has already minted.
    """
    slug = _SLUG.sub("-", str(said or "").lower()).strip("-")[:KEY_CHARS]
    got = "%s:%s" % (kind, slug) if slug else kind
    if got not in taken:
        return got
    for n in range(2, 40):
        more = "%s-%d" % (got, n)
        if more not in taken:
            return more
    return ""


def _chapters(root):
    """A course's chapters, in the order the course puts them in."""
    out = []
    taken = set()
    every = syllabus.chapters(root)
    for c in every[:MOST]:
        label = syllabus.label(c)
        if not label:
            continue
        key = _key("chapter", c.get("slug") or label, taken)
        if not key:
            continue
        taken.add(key)
        out.append({
            "key": key,
            "label": label,
            "what": "a chapter of this course",
            "about": ("%s, as this course covers it. The material for it is in "
                      "this repository -- its notes, its problem set, its "
                      "sources -- so read that first and write the document "
                      "from it. Explain the mathematics of the chapter from the "
                      "ground up for somebody who has not read it. Not the "
                      "order anybody was taught it in, and not anybody's "
                      "answers." % label),
        })
    return out, max(0, len(every) - MOST)


def _sets(root):
    """A course's problem sets. The set is the subject, never the answers."""
    out = []
    taken = set()
    every = homework.sets(root)
    for s in every[:MOST]:
        key = _key("set", s["name"], taken)
        if not key:
            continue
        taken.add(key)
        out.append({
            "key": key,
            "label": s["name"],
            "what": "a problem set -- %s" % s["rel"],
            "about": ("The problem set `%s`, at `%s`. Take the problems in it "
                      "and the method each one needs, and write the document "
                      "about THAT: what the problem is asking, what machinery "
                      "answers it, and why. It is not a mark sheet -- say "
                      "nothing about who answered what."
                      % (s["name"], s["rel"])),
        })
    return out, max(0, len(every) - MOST)


def _parts(root):
    """A project's own top-level pieces.

    `review.units` is the discovery, and it answers with chapters for a course
    and parts for a project -- never both. So only the parts are taken here: a
    course's chapters are their own group above, and a chapter offered twice
    under two keys is two buttons that do the same thing.
    """
    out = []
    taken = set()
    every = [u for u in review.units(root) if u.get("kind") == "part"]
    for u in every:
        key = _key("part", u["name"], taken)
        if not key:
            continue
        taken.add(key)
        out.append({
            "key": key,
            "label": u["label"],
            "what": "a part of this repository",
            "about": ("`%s`, one part of this repository. Read what is in it "
                      "and explain what it does, how it is put together and why "
                      "it is arranged the way it is. Work from the code that is "
                      "there rather than from what any document says about it."
                      % u["name"]),
        })
        if len(out) >= MOST:
            break
    return out, max(0, len(every) - MOST)


def _results(root):
    """Figures, grouped by the directory they came out of.

    THE DIRECTORY IS THE UNIT, NOT THE FIGURE, and `results._where` says why one
    level down: a pipeline writes `propensity_by_arm.png` once per contrast
    under the same name every time, so the directory is the thing that tells
    three of them apart and is the thing somebody means when they say *this
    result*. A document about one PNG is not an ask anybody makes.
    """
    groups = {}
    order = []
    for fig in results.figures(root):
        where = fig.get("where") or ""
        if where not in groups:
            groups[where] = []
            order.append(where)
        groups[where].append(fig)
    out = []
    taken = set()
    for where in order[:MOST]:
        n = len(groups[where])
        key = _key("results", where or "all", taken)
        if not key:
            continue
        taken.add(key)
        out.append({
            "key": key,
            "label": where or "results",
            "what": "%d figure%s" % (n, "" if n == 1 else "s"),
            "about": ("The figures in `%s` -- %d of them. Read every one, say "
                      "what it shows, and explain the analysis they came out "
                      "of: what was being asked, what was done to the data, and "
                      "what the figures answer. The figures are the evidence, "
                      "so put them in the document."
                      % (where or "this workspace's results directory", n)),
        })
    return out, max(0, len(order) - MOST)


def _documents(root):
    """What has already been written here. A paper about a paper is a real ask."""
    out = []
    taken = set()
    every = library.documents(root)
    for doc in every[:MOST]:
        key = _key("doc", doc["id"], taken)
        if not key:
            continue
        taken.add(key)
        out.append({
            "key": key,
            "label": doc["title"],
            "what": ("a document already written -- %s" % doc["dir"]
                     if doc.get("dir") else "a document already written"),
            "about": ("`%s`, a document this workspace has already written, at "
                      "`%s`. It is the SUBJECT of the new one and not a draft "
                      "to be edited: read it and write about what it says, what "
                      "it rests on and what it leaves open. Leave the file "
                      "itself exactly as you found it."
                      % (doc["title"], doc["rel"])),
        })
    return out, max(0, len(every) - MOST)


def _whole(root):
    """The scope every workspace has. Last, because it is the widest."""
    name = config.read_config(root)["name"] or os.path.basename(
        os.path.realpath(root))
    return {
        "key": WHOLE,
        "label": name,
        "what": "everything here",
        "about": ("THE WHOLE OF %s. What the workspace is for, how it is put "
                  "together, what it has produced and where it has got to. Read "
                  "the repository before you write a line of it -- its "
                  "`README.md`, its `AI_INSTRUCTIONS.md`, its own documents -- "
                  "because nothing about this ask is the record of a lesson."
                  % name),
    }


def scopes(root):
    """Everything a document in this workspace can be held over.

    A list of `{key, label, what, about}`, in one fixed order: chapters, problem
    sets, parts, results, documents, and the whole workspace last. Fixed because
    the order is the narrowing -- a chapter is the smallest honest subject and
    the workspace is the widest -- and because a picker whose buttons move
    between two openings is one nobody learns.

    `about` is the sentence handed to the assistant and is NOT for the glass:
    `POST /writeup/scopes` sends the other three and keeps this one, so what
    comes back from the browser is a key rather than an instruction somebody
    could have written themselves.

    Never raises. A workspace whose walk fails somewhere still offers the one
    scope it cannot fail to have.
    """
    out, _more = offered(root)
    return out


def offered(root):
    """The scopes, and how many rows the stop above kept off the list.

    TWO VALUES BECAUSE A SILENT CAP IS A LIE. A workspace with more chapters
    than `MOST` gets a picker that is complete as far as it goes and says
    nothing about the rest, which reads as *this is all there is*. The count
    goes back with the list and the sheet paints it in a line.
    """
    out, more = [], 0
    for group in (_chapters, _sets, _parts, _results, _documents):
        try:
            rows, dropped = group(root)
        except Exception:                                    # noqa: BLE001
            # A group that cannot be read is a group that is not offered. The
            # alternative is a front door that answers 500 because one
            # workspace on the machine has an unreadable directory in it.
            continue
        out.extend(rows)
        more += dropped
    out.append(_whole(root))
    return out, more


def find(root, key):
    """The scope with this key, or None.

    A KEY, NEVER A PATH. What arrives from the browser is compared against the
    keys this workspace actually offers, and a miss is a miss -- which is the
    rule `course/library.find` states and the reason the keys above are opaque.
    """
    wanted = str(key or "").strip()
    if not wanted:
        return None
    for rec in scopes(root):
        if rec["key"] == wanted:
            return rec
    return None
