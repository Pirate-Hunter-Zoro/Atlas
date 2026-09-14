"""The course a person last asked for.

A decision, not a derivation. Resuming a course touches its files, so "most
recently used" is self-reinforcing and cannot stand in for this.
"""

import json
import os
import time

from . import paths


def chosen_id(rec=None):
    """`family/dir` out of a choice record, or the bare `dir` if it has no family.

    One place decides how a record is spelled as an address, because two
    spellings of one name is two bugs. A record written before the move has no
    `family`; it still names a workspace, and `atlas.find` still finds it by
    the bare directory, so it degrades to the old answer rather than to none.
    """
    rec = chosen_course() if rec is None else (rec or {})
    name = rec.get("dir") or ""
    fam = rec.get("family") or ""
    if not name:
        return ""
    return ("%s/%s" % (fam, name)) if fam else name


def chosen_course():
    """The course a PERSON last asked for, or {} if nobody ever has.

    A decision, not a derivation. `tutor <course>` writes it and so does a tap
    in the hub, and it is what decides which course the one address opens --
    otherwise it is whichever board happens to answer first, which is
    alphabetical order wearing a disguise.
    """
    try:
        with open(paths.CHOSEN, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def remember_chosen(name, root, host=None, at=None, family=None):
    """Record that this course was asked for. A note, never a requirement.

    `host` is the machine it was asked for ON, when the person picked one. Which
    courses exist is a property of a machine -- they are whatever is cloned next
    to the board -- so "Probability" can mean two different clones, and until the
    hub could offer the choice the answer was whichever machine won an argument.
    Empty means "wherever it is", which is the old behaviour and the right one
    when nobody has said.

    `family` is the second level of the tree, and it is here because `dir`
    alone stopped being unique the moment eleven repositories became one:
    `courses/Probability` and a future `practice/Probability` are two different
    workspaces with one directory name, and a record naming only "Probability"
    cannot tell a reader which was tapped. It is written and it is OPTIONAL to
    read -- see `chosen_course` -- because a file already on disk from before
    the move has no family in it and must not strand the app on nothing.

    `at` is for a RELAYED record -- one tap, copied to every machine that can
    hear it -- and it is the originator's timestamp, kept rather than restamped.
    That matters more than it looks: these times are compared across machines to
    find the person's latest word, and two machines' clocks are not the same
    clock. One tap that lands as one identical record everywhere has nothing left
    to disagree about.
    """
    try:
        os.makedirs(paths.CONFIG_DIR, exist_ok=True)
        tmp = paths.CHOSEN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"dir": name, "root": root, "family": family or "",
                       "at": float(at or time.time()), "host": host or ""}, fh)
        os.replace(tmp, paths.CHOSEN)
        return True
    except (OSError, TypeError, ValueError):
        return False
