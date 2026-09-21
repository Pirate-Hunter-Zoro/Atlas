"""What a mission has been doing, while it is still doing it.

THE ASK, IN THE OWNER'S WORDS:

    "Whenever an agent is dispatched in some way, make it so that if I click on
     that box that says 'A Mission is still going' I can see what has been going
     on and been accomplished thus far. Be it colibri, or anything."

`missions.py` answers *is it still running*. That is the wrong half of the
question after the first hour. A mission had run five hours, taken one pick-up,
and there was nothing whatsoever on the glass: no card, no file outside `live/`,
no progress of any kind -- because a turn's output lands at the END, and on a
model that prefills for hours the end is hours away. A person looking at the
board could see only that it was still going.

TWO HALVES, AND THE FIRST ONE NEEDS NO HELP FROM THE ASSISTANT. Elapsed time,
turns, pick-ups, stalls, the ceiling, the node, whether a turn is in flight --
`missions.py` records every one of them. Cards written, commits made and files
left dirty are derivable from the workspace. That half is true of a mission
that has written nothing, which is the case this exists for.

THE SECOND HALF IS A TRAIL, NOT A REPORT. One append-only file per mission,
beside its record, written a line at a time: by the machinery at a dispatch, a
turn opening and a pick-up claimed, and by the assistant with `board step` as
it finishes things. A trail survives a hop because it is on disk in the
workspace, which is the whole reason the record is there rather than in a
daemon's memory -- and the turn that picks the mission up reads the trail back
and does not redo what is on it.

IT IS NEVER TRACKED, AND THAT IS NOT AN ACCIDENT OF PLACEMENT. The trail is
the assistant's own words about work in a workspace that may hold identifiable
content, so it goes under `live/missions/`, which every workspace's
`.gitignore` excludes wholesale -- `board/test/tracked.py` fails the suite if
it ever stops being true.

AND NO PATH UNDER A FENCE REACHES THE PANEL. `fenced.py` is the one list, and
here it is applied to FILENAMES: in `research/PSYCH-ASR` the names themselves
carry participant ids, so a list of what a mission touched is content even
though no file was opened to build it. Nothing in this module reads inside a
fenced directory, and the panel says a name was withheld rather than dropping
it silently.
"""

import json
import os
import re
import subprocess
import time

from . import fenced
from .lesson import cards as lesson_cards


# What one line of the trail is truncated to. A step is one sentence about one
# finished thing; the whole of what was done is in the cards and the diff.
STEP_CHARS = 240

# How many lines of the trail a panel carries, newest last. Eighteen hours of
# steps is a log, and a log is not progress.
STEPS_KEEP = 40

# How many cards, commits and filenames are worth saying. Past these the COUNT
# is the fact -- the same rule `lesson/git.py` follows for a briefing.
CARDS_KEEP = 8
COMMITS_KEEP = 8
FILES_KEEP = 14

# The derived half is two `git` calls per mission, and a panel left open on a
# tablet re-asks. A commit does not land twice in fifteen seconds.
TTL = 15.0
_CACHE = {}


def steps_path(root, mid):
    """Where one mission's trail lives. Beside its record, never tracked."""
    return os.path.join(root, "live", "missions", "%s.steps" % mid)


def add(root, mid, said, who="agent", now=None):
    """Append one line to a mission's trail. Atomically, and never raising.

    ONE `write` ON A FILE OPENED `O_APPEND`, which is what makes this safe
    without a lock: the daemon writing a pick-up and the assistant writing a
    step are two processes on a shared filesystem, and an append of one short
    line cannot interleave. The record beside it is replaced rather than
    appended to for the opposite reason -- it has fields that get overwritten.
    """
    said = re.sub(r"\s+", " ", str(said or "")).strip()[:STEP_CHARS]
    if not said or not mid:
        return False
    line = json.dumps({"at": float(now or time.time()),
                       "who": "board" if who == "board" else "agent",
                       "said": said}) + "\n"
    try:
        os.makedirs(os.path.dirname(steps_path(root, mid)), exist_ok=True)
        fd = os.open(steps_path(root, mid),
                     os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
    except OSError:
        return False
    try:
        os.write(fd, line.encode("utf-8"))
    except OSError:
        return False
    finally:
        os.close(fd)
    return True


def read(root, mid):
    """One mission's trail, oldest first, at most `STEPS_KEEP` lines.

    A half-written line is skipped rather than raising: the file is appended to
    by two processes and read by a third, and a panel that throws on a torn
    line is a panel that is blank exactly while something is happening.
    """
    out = []
    try:
        with open(steps_path(root, mid), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("said"):
                    out.append({"at": float(rec.get("at") or 0),
                                "who": "board" if rec.get("who") == "board"
                                       else "agent",
                                "said": str(rec["said"])[:STEP_CHARS]})
    except OSError:
        return []
    return out[-STEPS_KEEP:]


def drop(root, mid):
    """Forget a mission's trail, because its record has been pruned."""
    try:
        os.remove(steps_path(root, mid))
    except OSError:
        pass


def open_ids(recs):
    """The ids of the missions in one workspace that have not ended.

    A workspace runs one mission at a time, so this is almost always one id --
    but `board step` must not have to guess, and a step written to a mission
    that finished yesterday is a line nobody will ever read.
    """
    return [str(r.get("id")) for r in recs or [] if not r.get("ended")]


# ---------------------------------------------------------------------------
# What the workspace shows for itself
# ---------------------------------------------------------------------------
# None of this needs the assistant to have said anything, which is the point:
# the mission that prompted the whole feature had written nothing at all.


def cards_since(root, since):
    """`(rows, total)` for the cards written in this workspace since `since`.

    A card is the assistant saying something, so a card that landed after the
    dispatch is progress whatever else is true. The id and the title, which is
    what `news.py` already puts on the strip -- never the body, because a body
    is a lesson and this is a strip two lines high.
    """
    where = os.path.join(root, "live", "cards")
    found = []
    try:
        names = os.listdir(where)
    except OSError:
        return [], 0
    for name in names:
        m = lesson_cards.CARD_RE.match(name)
        if not m:
            continue
        try:
            at = os.stat(os.path.join(where, name)).st_mtime
        except OSError:
            continue
        if at <= since:
            continue
        title = ""
        try:
            with open(os.path.join(where, name), "r", encoding="utf-8") as fh:
                meta, _ = lesson_cards.parse_front_matter(fh.read(2000))
            title = (meta.get("title") or "").strip()[:80]
        except (OSError, ValueError):
            title = ""
        found.append({"id": m.group(1), "at": at, "title": title})
    found.sort(key=lambda c: -c["at"])
    return found[:CARDS_KEEP], len(found)


def _git(args, root, timeout=10):
    try:
        p = subprocess.run(["git", "--no-optional-locks"] + list(args),
                           cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def changes_since(root, since):
    """What a mission has actually changed: commits, and what is still dirty.

    `{"commits": [...], "files": [...], "dirty": n, "withheld": n}`.

    SCOPED BY PATHSPEC, not filtered afterwards, because nine workspaces share
    one repository and a pathspec is the only thing that makes the answer about
    this one. `lesson/git.py` draws the same distinction for the same reason.

    `live/` is dropped: it is the board's own scratch, and reporting the cards
    the turn just wrote as *files it changed* counts the same work twice.

    A DIRTY FILE OLDER THAN THE MISSION IS SOMEBODY ELSE'S. `git status` has no
    clock, so the mtime is the only thing that says which of the two it is.

    AND A NAME UNDER A FENCE IS WITHHELD RATHER THAN LISTED. In the one
    workspace that has a fence the filenames carry participant ids, so the
    count is the honest answer and the name is not. `withheld` is that count,
    said out loud, because a name silently missing from a list is one somebody
    scrolls looking for.
    """
    out = {"commits": [], "files": [], "dirty": 0, "withheld": 0}
    said = _git(["log", "--since=@%d" % int(since), "--no-merges",
                 "--pretty=%at%x00%s", "--", root], root)
    if said is None:
        return out
    for line in said.splitlines():
        at, _, subject = line.partition("\0")
        if not subject.strip():
            continue
        try:
            when = int(at)
        except ValueError:
            when = 0
        out["commits"].append({"at": when, "subject": subject.strip()[:100]})
    out["commits"] = out["commits"][:COMMITS_KEEP]

    # `git status --porcelain` prints paths relative to the GIT ROOT, so in a
    # repository holding nine workspaces every name arrives with the
    # workspace's own directory on the front of it.
    #
    # BOTH ENDS RESOLVED BEFORE THEY ARE SUBTRACTED. This home directory is
    # reached by two names -- one of them a symlink -- and `git` answers in the
    # one it was given, so a raw subtraction produces a relative path with
    # eleven `..` on the front of it and a filename nobody can read.
    top = (_git(["rev-parse", "--show-toplevel"], root) or "").strip() or root
    top = os.path.realpath(top)
    here_root = os.path.realpath(root)
    # `--untracked-files=all` RATHER THAN THE DEFAULT, and it is the difference
    # between a panel and a shrug: git collapses an untracked directory into one
    # entry, so a mission that wrote four new modules into a new package reads
    # as one changed path named after the directory. A fence cannot be applied
    # to a name that is not there either. Scoped by the same pathspec, and what
    # a workspace does not want walked is in its own `.gitignore`.
    said = _git(["status", "--porcelain", "--untracked-files=all",
                 "--", root], root)
    if said is None:
        return out
    names = []
    for line in said.splitlines():
        if not line.strip():
            continue
        rel = line[3:].strip().strip('"')
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        try:
            here = os.path.relpath(os.path.join(top, rel), here_root)
        except ValueError:
            here = rel
        if here == "live" or here.startswith("live" + os.sep):
            continue
        # TOUCHED SINCE THE MISSION STARTED, because `git status` has no clock
        # and the question is what THIS mission did. A workspace is dirty for
        # all sorts of reasons -- somebody editing in their own editor is the
        # ordinary one -- and a panel crediting a mission with a file it never
        # opened is the same lie `brief.beside_sense` is written to avoid, in
        # the other direction. A path that cannot be stat'ed is kept: a
        # deletion is a change and has no mtime to read.
        try:
            if os.path.getmtime(os.path.join(here_root, here)) <= since:
                continue
        except OSError:
            pass
        if fenced.refused(here):
            out["withheld"] += 1
            continue
        names.append(here)
    out["dirty"] = len(names)
    out["files"] = sorted(names)[:FILES_KEEP]
    return out


def of(root, rec, working=False, now=None):
    """Everything a person tapping one running mission gets to see.

    `rec` is a JUDGED mission record -- `missions.of` put `state` on it -- and
    `working` is `missions.mid_turn`, asked by the caller because this module
    knows nothing about `agent.json` and must not learn.

    Cached on the mission and its state, because the two `git` calls are the
    expensive part and a panel left open on a tablet re-asks.
    """
    now = float(now or time.time())
    mid = str(rec.get("id") or "")
    at = float(rec.get("at") or 0)
    key = (os.path.realpath(root), mid, rec.get("state") or "")
    hit = _CACHE.get(key)
    if hit and now - hit[0] < TTL:
        got = dict(hit[1])
    else:
        cards, ncards = cards_since(root, max(at, float(rec.get("card_at") or 0)))
        got = changes_since(root, at)
        got["cards"] = cards
        got["card_count"] = ncards
        _CACHE[key] = (now, dict(got))
    got["steps"] = read(root, mid)
    got["id"] = mid
    got["task"] = rec.get("task") or ""
    got["agent"] = rec.get("agent") or ""
    got["state"] = rec.get("state") or ""
    got["reason"] = rec.get("reason") or ""
    got["at"] = at
    got["elapsed"] = max(0.0, now - at) if at else 0.0
    got["from"] = rec.get("from") or ""
    got["host"] = rec.get("host") or ""
    got["ship"] = bool(rec.get("ship"))
    got["shipped"] = float(rec.get("shipped") or 0)
    # A pick-up is not a turn, and the count a person wants is turns: the first
    # one plus one per hop. `stalls` is how many of those produced nothing, and
    # it is the number that says a mission is in trouble while still running.
    got["carries"] = int(rec.get("carries") or 0)
    got["turns"] = got["carries"] + 1
    got["stalls"] = int(rec.get("stalls") or 0)
    got["working"] = bool(working)
    got["session"] = rec.get("session") or ""
    ceiling = float(rec.get("ceiling") or 0)
    got["ceiling"] = ceiling
    got["left"] = max(0.0, ceiling - now) if ceiling else 0.0
    life = float(rec.get("life") or 0)
    got["life"] = life
    got["budget"] = max(0.0, life - now) if life else 0.0
    got["fenced"] = list(fenced.holds(root))
    return got


def forget():
    """Drop the derived cache. For a test, and for a dispatch."""
    _CACHE.clear()
