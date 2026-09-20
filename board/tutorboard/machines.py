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

from . import atlas, choice, fenced, machine, missions, news, paths, ports
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
            # WHETHER THIS BOX HOLDS CONTENT ONLY ONE ASSISTANT MAY READ, said
            # here so a chooser can say it before the tap. The fence was real
            # and per-PATH: every walk refused a fenced directory and nothing
            # anywhere said that a WORKSPACE had one, so the `who:` row offered
            # a hosted model beside the local one in a workspace holding
            # session content, identically to one holding a textbook. The names
            # themselves, not a flag: "fenced" is a warning and `phi/` is a
            # thing a person can go and look at. See `fenced.holds`.
            "fenced": list(fenced.holds(root)),
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


def _mark_news(cards, repo):
    """Hang `news` and `news_at` on each card. Never raises; see `news`."""
    try:
        waiting = {n["id"]: n for n in news.waiting(repo)}
    except Exception:                                # noqa: BLE001
        waiting = {}
    for c in cards:
        hit = waiting.get(c.get("id"))
        c["news"] = bool(hit)
        c["news_at"] = hit["when"] if hit else 0
        c["news_title"] = (hit or {}).get("title") or ""


def _mark_missions(cards, repo):
    """Hang `mission` on each card: the newest one in that workspace, or None.

    The newest is the whole of it. A card on the front door has room for one
    line and the strip on the board carries the list; what this field answers is
    "is anything going on in there", which is what a person scanning eleven
    boxes is asking. Never raises, for the same reason `_mark_news` does not.
    """
    try:
        running = missions.waiting(repo)
    except Exception:                                # noqa: BLE001
        running = []
    first = {}
    for m in running:
        first.setdefault(m.get("ws"), m)
    for c in cards:
        hit = first.get(c.get("id"))
        c["mission"] = None if not hit else {
            "id": hit.get("id"), "state": hit.get("state"),
            "task": hit.get("task") or "", "agent": hit.get("agent") or "",
            "at": hit.get("at") or 0, "ship": bool(hit.get("ship")),
            "shipped": hit.get("shipped") or 0,
            "reason": hit.get("reason") or "",
        }


def _mark_holder(cards, ask):
    """Hang `holder` on each card: the assistant listening in it, or "".

    WHAT A DISPATCH WILL DISPLACE, SAID BEFORE THE TAP RATHER THAN AFTER IT.
    `⇥ put an assistant to work elsewhere` stops whoever is there when it is
    given a different name, and that stop is a model call -- the outgoing
    daemon writes its handoff on the way out, and the request is held for the
    whole of it. A panel that cannot see the holder cannot say which of those
    two waits a tap just bought, so it says the short one and reads as a hang.
    Same reason `fenced` rides here: a chooser must be able to say what a
    choice costs while there is still a choice.

    ASKED FOR RATHER THAN ALWAYS. This is an `agent.json` per workspace off a
    shared filer -- 37 ms for eight of them against 0.4 ms for the rest of a
    cached payload -- and the front door polls the same route every 20 seconds
    while drawing none of it. So the dispatch panel asks and the door does not.

    OUTSIDE THE ATLAS CACHE, for `_mark_news`'s reason: a name half a minute
    old is a name somebody taps on. Never raises.
    """
    for c in cards:
        if not ask:
            # NOT ASKED FOR IS NOT "NOBODY IS THERE", and the rows are the
            # cached objects themselves -- a name left by a caller that did ask
            # would be read by one that did not as a fact it never requested.
            c.pop("holder", None)
            continue
        try:
            c["holder"] = missions.holder(c["root"])
        except Exception:                            # noqa: BLE001
            c["holder"] = ""


def _pinned(root):
    """The commit a vendor tree is sitting at, short -- or "".

    The one honest fact about a tree that is pulled rather than written: it is
    somebody else's repository at one commit, and which commit is the only
    thing about it this side chose.
    """
    try:
        p = subprocess.run(["git", "--no-optional-locks", "rev-parse",
                            "--short", "HEAD"],
                           cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        if p.returncode == 0:
            return p.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def _trees():
    """A card each for the vendor trees: read, drawn, never handed work.

    A SEPARATE LIST from `workspaces` in the payload, exactly as it is in
    `atlas`. A tree on the same list as a workspace is a tree something
    eventually offers a sitting in, and the whole point of the split is that
    nothing can do that by accident.

    What a card says is what can be measured without reading the tree's mind:
    the commit it is pinned at, how much source there is in it, and when it
    last moved. No plan, no next step, no cards outstanding -- none of those
    exist for something nobody hands work in to.
    """
    from .course import walk                          # circular at module scope
    out = []
    for t in atlas.trees():
        root = t["root"]
        try:
            files = len(walk.units(root))
        except Exception:                            # noqa: BLE001
            files = 0
        out.append({
            "id": t["id"], "family": t["family"], "repo": t["dir"],
            "name": t["dir"], "files": files, "at": _pinned(root),
            # `walk.units` stops at `MAX_UNITS`, and colibrì is past it. A card
            # that says "250 source files" when it means "at least 250" is a
            # number somebody would quote.
            "capped": files >= walk.MAX_UNITS,
            "touched": _last_touched(root),
        })
    return out


def atlas_payload(repo, holders=False):
    """Everything the front door draws, in family order.

    `families` carries the regions and their order, straight out of
    `atlas.json`; `workspaces` carries a card each. A VENDOR FAMILY HAS NO
    WORKSPACES AND IS NOT EMPTY: its contents are in `trees`, which is a second
    list for the same reason `atlas.trees` is a second function -- a tree is
    read and drawn and is never a thing work is handed in to.
    """
    now = time.time()
    if _ATLAS["value"] is not None and now - _ATLAS["at"] < ATLAS_TTL:
        # The one thing that must never be stale is which card is the current
        # one: it is what the door opens, and it moves the instant a board is
        # switched. Everything else in here can be half a minute old.
        for c in _ATLAS["value"]["workspaces"]:
            c["current"] = paths.same_dir(c["root"], repo.root)
        _mark_news(_ATLAS["value"]["workspaces"], repo)
        _mark_missions(_ATLAS["value"]["workspaces"], repo)
        _mark_holder(_ATLAS["value"]["workspaces"], holders)
        return _ATLAS["value"]

    from .course import plan as course_plan          # circular at module scope
    from .course import syllabus
    from .course import map as course_map

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
        # THE ONE FIELD THE WRITTEN MAP LENDS THE FRONT DOOR, and it is one on
        # purpose. A workspace somebody has drawn has a sentence for the whole
        # of itself -- "Stage 1 -- audio to a graded transcript" -- which is a
        # better label for a card than a directory name, and is the only thing
        # on this page that could not have been derived. Everything else about
        # the map stays behind the card: the atlas is a picture of the
        # repository, not a picture of every picture in it.
        c["drawn"] = ""
        try:
            drawn = course_map.written_status(root)
            if drawn["has"] and not drawn["problems"]:
                c["drawn"] = clipped(drawn["title"])
        except Exception:                            # noqa: BLE001
            c["drawn"] = ""

    # AND WHICH OF THEM ANSWERED WHILE NOBODY WAS LOOKING. Outside the cache
    # above and re-asked on every hit, for the same reason `current` is: a badge
    # saying an answer is waiting, half a minute after it was read, is a badge
    # that teaches somebody to ignore badges.
    _mark_news(cards, repo)
    # AND WHAT IS STILL RUNNING IN EACH. Outside the cache for the same reason:
    # a mission that finished half a minute ago and still says `running` is the
    # one field on this page somebody would act on immediately.
    _mark_missions(cards, repo)
    # AND WHO IS ATTACHED IN EACH, which a dispatch displaces. Outside the
    # cache for the same reason again; see `_mark_holder`.
    _mark_holder(cards, holders)

    out = {"families": [dict(f) for f in atlas.families()], "workspaces": cards,
           "trees": _trees()}
    for f in out["families"]:
        f.pop("dir", None)               # a filesystem path is not the page's
    _ATLAS["at"] = now
    _ATLAS["value"] = out
    return out
