"""What this machine can teach, and which workspace was chosen on it.

Which workspaces exist is a property of a MACHINE -- they are whatever is
checked out in the repository on it -- so the list the hub draws is a directory
listing, built when it is asked for and never written down anywhere.

`atlas.py` owns the walk now. This module owns what the board needs to SAY
about each thing that walk finds: is a board up on it, on which node, how many
cards are in it, what it calls itself.
"""

import json
import os
import subprocess
import time

from . import atlas, choice, machine, paths, ports
from .course import config
from .lesson import cards


_SLURM = {"at": 0.0, "nodes": None}


def held_nodes():
    """Nodes this user still holds, cached for a few seconds.

    `sibling_courses` asks once per course and the hub asks often, so without a
    cache this is a `squeue` per repository per poll.
    """
    now = time.time()
    if now - _SLURM["at"] > 15.0:
        _SLURM["nodes"] = machine.slurm_nodes()
        _SLURM["at"] = now
    return _SLURM["nodes"]


def board_port(repo):
    """The port THIS board is listening on, off its own record."""
    rec = read_board_record(repo.root) or {}
    port = rec.get("port")
    try:
        return int(port) if port else ports.default_port(os.path.basename(repo.root))
    except (TypeError, ValueError):
        return ports.default_port(os.path.basename(repo.root))


def workspaces(repo):
    """Every workspace in the repository, and what is true of each right now.

    This used to be `sibling_courses`, and it used to be one listing of
    `os.path.dirname(repo.root)`: a course was a directory sitting next to the
    board. Eleven repositories are one now, two levels deep, so the walk is
    `atlas.workspaces()` and the family is part of what comes back.

    What has NOT changed is that nothing is registered. A directory holding
    `tutorboard.json`, `AI_INSTRUCTIONS.md` or `live/` is a workspace, found by
    looking -- which is still the right answer by construction, because it
    lists what the machine SERVING the board actually has on disk. A host with
    half the tree checked out offers half the subjects, and no list anywhere
    has to be edited to say so.

    `repo` stays the bare directory name and stays the key the hub and the
    atlas page use: a port is derived from it, `.board.json` records it, and
    the names are unique across the repository. `id` is the qualified
    `family/name`, which is what an address spells and what a choice records.
    """
    out = []
    for w in atlas.workspaces():
        root = w["root"]
        live = os.path.join(root, "live")
        cfg = config.read_config(root)
        entry = {
            "repo": w["dir"],
            "id": w["id"],
            "family": w["family"],
            "family_name": w["family_name"],
            "root": root,
            # By the directory it is, not by the name this caller spells it
            # with: the same home is reachable under two paths here.
            "current": paths.same_dir(root, repo.root),
            "course": cfg["name"],
            "chapter": "",
            "cards": 0,
            "running": False,
            "node": None,
        }
        try:
            with open(os.path.join(live, "state.json"), "r", encoding="utf-8") as fh:
                st = json.load(fh)
            entry["course"] = st.get("course") or entry["course"]
            entry["chapter"] = st.get("chapter") or ""
        except (OSError, ValueError):
            pass
        try:
            entry["cards"] = len([n for n in os.listdir(os.path.join(live, "cards"))
                                  if cards.CARD_RE.match(n)])
        except OSError:
            pass
        try:
            with open(os.path.join(live, ".board.json"), "r", encoding="utf-8") as fh:
                info = json.load(fh)
            entry["node"] = info.get("node")
            if info.get("node") == machine.node_name():
                try:
                    os.kill(info.get("pid", -1), 0)
                    entry["running"] = True
                except OSError:
                    pass
            else:
                # A record naming another node proves nothing: the home
                # directory is shared, so a board that died with an allocation
                # leaves one behind that looks exactly like a live board. The
                # hub said "live on compute304" for hours after compute304
                # stopped being a machine this user had. Ask Slurm; `None` means
                # there is no Slurm to ask, which is unknown rather than gone.
                held = held_nodes()
                entry["running"] = held is None or info["node"] in held
                if not entry["running"]:
                    entry["node"] = None
        except (OSError, ValueError):
            pass
        out.append(entry)
    return out


# The name it had while every course was a sibling of the board. Kept so an
# older board on another machine, pulling this tool before its own repository
# has moved, does not lose the hub entirely.
sibling_courses = workspaces


def read_board_record(root):
    """A course's `.board.json`, or None. Which machine, which pid, which port."""
    try:
        with open(os.path.join(root, "live", ".board.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def chosen_target():
    """The course a person last asked for, and the port it is actually serving on.

    Another machine cannot read this one's filesystem, so it cannot know either
    of these things -- it can only knock on ports and take whichever answers
    first, which is alphabetical order pretending to be a decision. So every
    board publishes the answer: the choice comes from `chosen.json`, and the port
    comes from that course's own board record, which is the only place the truth
    lives once a port collision has moved a board off its usual number.
    """
    rec = choice.chosen_course()
    name = rec.get("dir")
    if not name:
        return None
    # The root off the record, and failing that off discovery -- never
    # `dirname(paths.TOOL)` any more, which was only ever right while the
    # courses were siblings of the board. A record written before the move
    # names a path that is no longer there, and `atlas.find` is what turns the
    # name in it back into a place.
    root = rec.get("root")
    if not root or not os.path.isdir(root):
        found = atlas.find(choice.chosen_id(rec) or name)
        root = found["root"] if found else ""
    port = None
    try:
        with open(os.path.join(root, "live", ".board.json"), "r", encoding="utf-8") as fh:
            port = (json.load(fh) or {}).get("port")
    except (OSError, ValueError):
        port = None
    # `at` so another machine can tell this record from its OWN. The choice is
    # written on whichever machine was serving the hub when the course was
    # tapped, so there can be two records of it and only the times can say which
    # is the person's latest word -- without that, a course tapped on one machine
    # was invisible to another reading only its own file, and the tap did every
    # correct thing while the address stayed put.
    # And the HOST, because the hub can ask for a course ON a named machine. A
    # record that did not publish one arrived with the host silently blank, and
    # the machine the person actually picked could not be honoured.
    return {"dir": name, "id": choice.chosen_id(rec),
            "family": rec.get("family") or "",
            "port": port or ports.default_port(name),
            "at": rec.get("at") or 0, "host": rec.get("host") or ""}


# ---------------------------------------------------------------------------
# TikZ -> SVG worker
# ---------------------------------------------------------------------------
# The course's own macros load first and win; board-macros.tex is all
# \providecommand, so it only fills in whatever the course did not define. Without
# it a command that renders fine in the prose fails inside a tikz fence, which is
# the most confusing way for a diagram to break.


# ---------------------------------------------------------------------------
# The atlas: every workspace at once, for the front door
# ---------------------------------------------------------------------------
# One picture of everything, which is the thing that was asked for first:
#
#     "Every time I open the application, I want to be taken to a very visually
#      pleasing map of EVERYTHING. I can choose what course or project I want to
#      go to next."
#
# So this is `workspaces()` plus the four things a CARD has to say that the hub's
# list never did: what is next, how much is outstanding, when it was last
# touched, and what it was last opened for. Each of those already existed as a
# function somewhere; none of them had ever been asked for all nine at once.
#
# Cached hard. The home page polls every twenty seconds, `plan.steps` reads a
# file per workspace and the commit date is a `git log` per workspace -- and the
# answers change on the scale of minutes, not of polls.
_ATLAS = {"at": 0.0, "value": None}
ATLAS_TTL = 30.0

# The truncation the map's boxes already use, for the same reason: this is read
# inside a card on a tablet.
NEXT_CHARS = 110


def _last_touched(root):
    """When this workspace was last committed to, as a unix time, or 0.

    Scoped to the workspace with a pathspec. There is one repository now, so an
    unscoped `git log` would give every card the same date -- the date of
    whatever was committed last, anywhere -- which is a field that looks like
    information and is noise.
    """
    try:
        p = subprocess.run(["git", "--no-optional-locks", "log", "-1",
                            "--format=%ct", "--", root],
                           cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        if p.returncode == 0:
            return float(p.stdout.decode("utf-8", "replace").strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0.0


def atlas_payload(repo):
    """Everything the front door draws, in family order.

    `families` carries the regions and their order, straight out of
    `atlas.json`; `workspaces` carries a card each. Vendor families are in the
    families list -- the front door may want to say that `vendor/` exists -- and
    have no workspaces under them, because discovery skips them.
    """
    now = time.time()
    if _ATLAS["value"] is not None and now - _ATLAS["at"] < ATLAS_TTL:
        # The one thing that must never be stale is which card is the current
        # one: it is what the door opens, and it moves the instant a board is
        # switched. Everything else in here can be half a minute old.
        for c in _ATLAS["value"]["workspaces"]:
            c["current"] = paths.same_dir(c["root"], repo.root)
        return _ATLAS["value"]

    from .course import plan as course_plan          # circular at module scope
    from .course import syllabus

    def clipped(said):
        said = (said or "").strip()
        return said if len(said) <= NEXT_CHARS else said[:NEXT_CHARS - 1] + "…"

    cards = workspaces(repo)
    for c in cards:
        root = c["root"]
        # "What is next" has TWO answers, because a workspace plans in one of
        # two ways and neither is a fallback for the other. A course that
        # follows a book is planned by `chapters.tsv` -- what is next is the
        # chapter after the one it is in. A project is planned by a task list --
        # what is next is the first open step. Asking only about steps left
        # every course's card blank, which on a front door reads as "nothing to
        # do here" rather than "this one is a book".
        c["open"], c["next"], c["next_label"], c["kind"] = 0, "", "", "project"
        try:
            chapters = syllabus.chapters(root)
        except Exception:                            # noqa: BLE001
            chapters = []
        if chapters:
            c["kind"] = "book"
            here = (c.get("chapter") or "").strip()
            at = -1
            for i, ch in enumerate(chapters):
                if here and (syllabus.label(ch) == here
                             or str(ch.get("num")) in here
                             or (ch.get("title") or "") in here):
                    at = i
                    break
            nxt = chapters[at + 1] if 0 <= at < len(chapters) - 1 else (
                None if at >= 0 else chapters[0])
            c["open"] = len(chapters) - (at + 1)
            if nxt:
                c["next"] = clipped(syllabus.label(nxt))
                c["next_label"] = syllabus.label(nxt)
            c["of"] = len(chapters)
        else:
            try:
                steps = course_plan.steps(root)
            except Exception:                        # noqa: BLE001
                steps = []
            # NEVER let one workspace's broken plan blank the whole front door.
            # A page that throws is a blank screen where the app used to be, and
            # this one is the way back into a lesson.
            c["open"] = len(steps)
            if steps:
                c["next"] = clipped(steps[0].get("title") or steps[0].get("label"))
                c["next_label"] = steps[0].get("label") or ''
        c["touched"] = _last_touched(root)
        try:
            st = {}
            with open(os.path.join(root, "live", "state.json"), "r",
                      encoding="utf-8") as fh:
                st = json.load(fh) or {}
            c["aim"] = st.get("aim") or ""
            c["session"] = st.get("session") or ""
        except (OSError, ValueError):
            c["aim"] = ""
            c["session"] = ""
        c["stance"] = (config.read_config(root) or {}).get("stance") or "teach"

    out = {"families": [dict(f) for f in atlas.families()], "workspaces": cards}
    for f in out["families"]:
        f.pop("dir", None)               # a filesystem path is not the page's
    _ATLAS["at"] = now
    _ATLAS["value"] = out
    return out
