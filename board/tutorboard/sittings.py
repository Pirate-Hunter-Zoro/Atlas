"""Slides from sittings: what past sittings did, ticked, and a brief for the deck.

Asked for in these words:

    "I just want to be able to select from tutoring sessions what we've done
     over all sessions and get to pick a list of the things I want to include
     in the presentation. I leave it up to the AI tutor to actually decide what
     slides are dedicated to which things accomplished, but various figures,
     etc. that are relevant should be accessible to the tutor as well as it
     makes the slides. I want to be able to mark up on the slide to specify if
     there's something else I want or what to take out, etc, and get it
     re-rendered. I don't want to be limited to one slide per project."

THREE PIECES, AND ONLY THE FIRST TWO ARE NEW. The meeting deck is one frame per
workspace by construction, and its ink is direction for the project; neither
fits. A document asked for from a sitting (`POST /writeup`) and the library's
correction loop already fit everything else. So this module does what neither
of those knows how to do:

  * `listing` -- every sitting in every workspace, filed or open, as a row
    somebody can tick. Shells are hidden and consecutive sittings on one chapter
    are one row, because four folders called `predictions` are one piece of
    work.
  * `items` -- what the ticked sittings DID, as rows somebody can untick: the
    commits inside the window, the plan steps it finished, the bullets of the
    handoff that sitting wrote that are about the work rather than the student,
    and "everything this sitting covered" for a course whose commits say
    nothing.
  * `write_brief` -- the file the tutor reads before it plans the slides: the
    ticked items with their sources, the figures already copied beside the deck,
    and a catalog of the rest it may pull with `board deckfig`.

The deck itself is written by the `[writeup]` turn and read, inked and redrawn
in the host workspace's library, unchanged. Nothing here goes near
`proposals.py`: the meeting deck's ink is direction, and this deck's ink is a
revision.

AN ID, NEVER A PATH. A sitting arrives as `<workspace id>@<first folder>` and an
item as ten hex characters, and both are matched against what this module found
on the server -- a miss is a miss and nothing from a request is joined onto a
directory. A deck touching a fenced workspace is written inside it
(`host_for`). Every path the brief names passes `fenced.refused`, and every figure
comes through `results.find`, which asks the fence again before a file is
opened.

Standard library only, like everything else.
"""

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import atlas, fenced, handoff, meeting, paths, writeups
from .course import config, document, library, plan, results

# How many rows of one workspace the sheet shows before it folds the rest behind
# "show N older sittings". Every row is sent and every row can be picked: the
# ask was "over all sessions". Galois Theory files a sitting per chapter and per
# change of direction, and unfolded that is a scroll through last term.
MOST_ROWS = 20

# How much of each kind one sitting offers. A sitting is an evening, and an
# evening that produced forty commits produced a changelog rather than forty
# things worth a slide.
MOST_COMMITS = 20
MOST_STEPS = 10
MOST_HANDOFF = 12

# How many figures are copied beside the deck, and how many more are listed. The
# first is `results.MAX_FIGURES`, the drawer's number, for the drawer's reason;
# the second keeps a catalog a turn reads whole from becoming the results page.
MOST_FIGURES = results.MAX_FIGURES
MOST_CATALOG = 300

# What a line on the sheet is clipped to, and what the brief carries of one.
ITEM_CHARS = 220
BODY_CHARS = 600

# How many decks the front door lists as already made.
MOST_DECKS = 5

# Where a deck goes and what is beside it. `_` keeps the brief out of the
# library's walk (`course/library.py` skips a leading underscore), so the
# library offers the deck and not its instructions.
DECK_PREFIX = "deck-"
BRIEF_MD = library.DECK_BRIEF
BRIEF_JSON = "_brief.json"
FIGURES = "figures"

# UNTRACKED, BECAUSE THE REPOSITORY IS PUBLIC. A save commits the whole tree,
# and a deck filed under Galois Theory can hold a figure made from TRD-EHR's
# records. The source stays tracked: a rework is refused against an uncommitted
# one, and the source is what git can undo.
IGNORE = ("figures/", "*.pdf", "_brief.*")

# A commit that only says a save happened. The subjects the board's own saves
# write, which is what a course's history is almost entirely made of.
NOISE = ("lesson complete", "lesson transcript", "stopping point")

SITTING_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]*@[A-Za-z0-9][A-Za-z0-9_.-]*$")
ITEM_RE = re.compile(r"^[0-9a-f]{10}$")
FILED_RE = re.compile(r"^(\d{8}-\d{6})(?:-(.*))?$")
EMBED_RE = re.compile(r"/result/([A-Za-z0-9][A-Za-z0-9_-]*)")
STAMP_RE = re.compile(r"^<!--\s*chapter:\s*(.*?)\s*-->")


# ---------------------------------------------------------------------------
# when a sitting was
# ---------------------------------------------------------------------------
def _opened(st):
    """`state.opened` as an epoch, or None. It is local `YYYY-MM-DD HH:MM`."""
    raw = str((st or {}).get("opened") or "").strip()
    try:
        return time.mktime(time.strptime(raw[:16], "%Y-%m-%d %H:%M"))
    except ValueError:
        return None


def _filed_at(name):
    """When an archive folder was filed, off its stamp, or None."""
    m = FILED_RE.match(name or "")
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1), "%Y%m%d-%H%M%S"))
    except ValueError:
        return None


def _count_cards(folder):
    try:
        return len([n for n in os.listdir(folder) if document.CARD_RE.match(n)])
    except OSError:
        return 0


def _count_turns(path):
    """Lines in a transcript, which is how many sends there were. Not parsed:
    a shell is told apart from a sitting by whether anything happened in it."""
    try:
        with open(path, "rb") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def _first_card_at(folder):
    try:
        return min(os.path.getmtime(os.path.join(folder, n))
                   for n in os.listdir(folder) if document.CARD_RE.match(n))
    except (OSError, ValueError):
        return None


def _one(sitting, now):
    """One sitting as this module reads it, or None for a shell."""
    folder = sitting.get("filed") or ""
    st = sitting.get("state") or {}
    cards = _count_cards(sitting["cards"])
    turns = _count_turns(sitting["turns"])
    # A SHELL: a sitting opened and filed before anything happened in it --
    # a change of chapter, or a board restarted onto the same label. Nothing in
    # it could be on a slide.
    if cards == 0 and turns <= 1:
        return None
    end = _filed_at(folder) if folder else now
    if end is None:
        return None
    start = _opened(st) or _first_card_at(sitting["cards"]) or end
    m = FILED_RE.match(folder)
    # MISSING state.json AND state {} ARE BOTH ORDINARY: an archive written
    # before the state was filed with it, and a sitting nobody labelled. The
    # folder's own label is what the archive called it.
    chapter = (st.get("chapter") or st.get("course") or
               ((m.group(2) or "") if m else "") or "").strip()
    return {"folder": folder, "live": not folder, "state": st,
            "cards_dir": sitting["cards"], "turns": sitting["turns"],
            "cards": cards, "start": min(start, end), "end": end,
            "chapter": chapter}


def _base(member):
    """A row's name without its date: `document.heading_for`'s own bits."""
    st = member["state"] or {}
    bits = [st.get("chapter") or st.get("course") or member["chapter"] or "Lesson"]
    kind = st.get("session") or ""
    if kind and kind != "lecture":
        bits.append(kind.replace("_", " "))
    return " -- ".join(bits)


def _label(members):
    """What a row is called: `document.heading_for`, widened for a merge."""
    first, last = members[0], members[-1]
    if last["live"]:
        return _base(last) + " (open now)"
    if len(members) == 1:
        return document.heading_for({"state": first["state"] or
                                     {"chapter": first["chapter"]},
                                     "filed": first["folder"]})
    a = time.strftime("%Y-%m-%d", time.localtime(first["start"]))
    b = time.strftime("%Y-%m-%d", time.localtime(last["end"]))
    return "%s (%d sittings, %s)" % (_base(first), len(members),
                                     a if a == b else "%s to %s" % (a, b))


def _name_of(ws):
    return config.read_config(ws["root"])["name"] or ws["dir"]


def _rows(base):
    """Every row, every workspace, with what `items` needs. Newest first within
    a workspace; workspaces ordered by their newest row."""
    now = time.time()
    ids = set()
    groups = []
    for ws in atlas.workspaces(base):
        ids.add(ws["id"])
        root = ws["root"]
        found = []
        for s in document._filed(root):
            one = _one(s, now)
            if one:
                found.append(one)
        # CONSECUTIVE SITTINGS ON ONE CHAPTER ARE ONE ROW. A chapter taught over
        # three evenings is one thing somebody did, and three rows of the same
        # name are a question nobody can answer.
        merged = []
        for one in found:
            if merged and merged[-1][-1]["chapter"] == one["chapter"] \
                    and one["chapter"]:
                merged[-1].append(one)
            else:
                merged.append([one])
        live = _one(document._live_sitting(root), now)
        if live:
            merged.append([live])
        if not merged:
            continue
        rel = os.path.relpath(root, base)
        name = _name_of(ws)
        held = list(fenced.holds(root))
        rows = []
        for members in merged:
            rows.append({
                "id": "%s@%s" % (ws["id"], members[0]["folder"] or "live"),
                "ws": ws["id"], "ws_name": name, "ws_dir": ws["dir"],
                "root": root, "rel": rel,
                "label": _label(members),
                "chapter": members[0]["chapter"],
                "cards": sum(m["cards"] for m in members),
                "start": members[0]["start"], "end": members[-1]["end"],
                "live": members[-1]["live"], "members": members,
                "fenced": held, "commits": 0,
            })
        # NO TWO ROWS SHARE A MOMENT. `opened` is to the minute and a filing to
        # the second, so a sitting opened the minute the last one was filed
        # starts up to a minute before that one ended -- and a commit in that
        # minute would be offered, and briefed, twice.
        for before, row in zip(rows, rows[1:]):
            row["start"] = min(max(row["start"], before["end"]), row["end"])
        rows.reverse()
        groups.append((max(r["end"] for r in rows), ws, rows))
    groups.sort(key=lambda g: -g[0])
    return groups, ids


def noise(subject, ids):
    """Is this commit a save rather than a piece of work?

    A WORKSPACE'S PREFIX IS NOT ENOUGH. `courses/Probability: lesson complete`
    is a save, and `courses/Probability: homework 3 through problem 31` is the
    homework; the prefix only says whose it is, and what follows it decides.
    """
    said = str(subject or "").strip()
    if ":" in said:
        head, rest = said.split(":", 1)
        if head.strip() in ids:
            said = rest.strip()
    return said.lower().rstrip(".") in NOISE


# ONE WORKSPACE'S HISTORY, KEPT, AND TOPPED UP RATHER THAN RE-READ. A pathspec
# `git log` over this repository costs seconds for a course whose every save is
# a commit -- Galois Theory's is over three -- and the sheet asks for every
# workspace at once. So the whole of it is read once per board, and after that
# only what landed since the head it was read at. Keyed by the workspace's path
# in the repository; a head that is not an ancestor of the last one (a rewrite)
# is read again whole.
_LOGS = {}
_LOCK = threading.Lock()


def _run(base, args):
    try:
        p = subprocess.run(["git"] + args, cwd=base, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return p.returncode, p.stdout.decode("utf-8", "replace")


def _parse(raw):
    out = []
    for line in raw.splitlines():
        bits = line.split("\0")
        if len(bits) != 3:
            continue
        out.append({"sha": bits[0][:8], "at": int(bits[1] or 0),
                    "subject": meeting._clip(bits[2].strip(), meeting.SUBJECT)})
    return out


def history(base, rel, head=None):
    """Every commit that touched `rel`, newest first, as `meeting.landed` has
    them. Cached against the repository's head; see `_LOGS`."""
    head = head if head is not None else _run(base, ["rev-parse", "HEAD"])[1].strip()
    key = (os.path.realpath(base), rel)
    with _LOCK:
        hit = _LOGS.get(key)
    if hit and head and hit["head"] == head:
        return hit["commits"]
    commits = None
    if hit and head and hit["head"] and _run(
            base, ["merge-base", "--is-ancestor", hit["head"], head])[0] == 0:
        code, raw = _run(base, ["log", "--no-merges", "%s..%s" % (hit["head"], head),
                                "--pretty=%H%x00%at%x00%s", "--", rel])
        if code == 0:
            commits = _parse(raw) + hit["commits"]
    if commits is None:
        # No `--since`: `meeting.landed(..., 0)` would say `--since=@0`, which
        # git reads as no date at all and answers with nothing.
        code, raw = _run(base, ["log", "--no-merges", "--pretty=%H%x00%at%x00%s",
                                head or "HEAD", "--", rel])
        commits = _parse(raw) if code == 0 else []
    with _LOCK:
        _LOGS[key] = {"head": head, "commits": commits}
    return commits


def forget():
    """Drop the kept histories. For a test that commits under the process."""
    with _LOCK:
        _LOGS.clear()


def _in(commits, row, ids):
    """The row's commits. HALF-OPEN, `start <= at < end`, so a commit on the
    line between two sittings is the later one's and is offered once. The open
    sitting's end is now, and a commit made this second is still its own."""
    return [c for c in commits
            if row["start"] <= c["at"] < row["end"] + (1 if row["live"] else 0)
            and not noise(c["subject"], ids)]


def _shown(base):
    """Every row the sheet offers, newest workspace first."""
    groups, ids = _rows(base)
    out = []
    head = _run(base, ["rev-parse", "HEAD"])[1].strip()
    # IN PARALLEL, because each is a wait on the disk rather than on a CPU, and
    # the slowest workspace is then the whole of the wait instead of the sum.
    rels = sorted(set(rows[0]["rel"] for _, _, rows in groups))
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(rels)))) as pool:
        logs = dict(zip(rels, pool.map(lambda r: history(base, r, head), rels)))
    for _, ws, rows in groups:
        for r in rows:
            r["log"] = logs.get(r["rel"]) or []
            r["commits"] = len(_in(r["log"], r, ids))
        out.extend(rows)
    return out, ids


def listing(base):
    """`{ok, sittings, fold}` -- what the sheet draws as its first question.
    `fold` is how many rows of a workspace it shows before folding the rest."""
    rows, _ = _shown(base)
    return {"ok": True, "fold": MOST_ROWS,
            "sittings": [{"id": r["id"], "ws": r["ws"], "ws_name": r["ws_name"],
                          "label": r["label"], "cards": r["cards"],
                          "commits": r["commits"], "fenced": r["fenced"],
                          "live": r["live"]} for r in rows]}


# ---------------------------------------------------------------------------
# what a sitting did
# ---------------------------------------------------------------------------
def _ident(ws, sitting, kind, key):
    raw = "%s|%s|%s|%s" % (ws, sitting, kind, key)
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:10]


def _plain(text):
    """A handoff line as a sentence: emphasis marks off, whitespace folded."""
    text = re.sub(r"\*\*|__", "", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _paragraphs(text):
    """`[(heading, paragraph)]` out of a handoff: every bullet, and every
    paragraph under a heading that has no bullets. The handoffs are written both
    ways -- TRD-EHR's is prose under three headings -- and a rule that read only
    bullets would offer nothing from the one this was asked for in."""
    out, heading, para = [], "", []

    def flush():
        nonlocal heading
        if para:
            said = _plain(" ".join(para))
            if said.endswith(":") and len(said) < 80:
                # "Where they got to:" is a heading written as a sentence.
                heading = said.rstrip(":").strip()
            elif len(said) >= 12:
                out.append((heading, said))
            del para[:]

    for line in (text or "").splitlines():
        s = line.strip()
        if STAMP_RE.match(s):
            continue
        h = re.match(r"^#{1,6}\s+(.*)$", s)
        if h:
            flush()
            heading = _plain(h.group(1))
            continue
        if not s:
            flush()
            continue
        if re.match(r"^\|.*\|$", s) or s.startswith("```"):
            # A table row or a fence is not a sentence anybody ticks. A line
            # that only STARTS with a bar is a wrapped `|beta|`.
            flush()
            continue
        b = re.match(r"^(?:[-*+]|\d+[.)])\s+(.*)$", s)
        if b:
            flush()
            para.append(b.group(1))
            continue
        para.append(s)
    flush()
    return out


# WHAT A HANDOFF SAYS THAT IS NOT SOMETHING DONE. A handoff is the tutor's note
# to the next tutor, and most of it is about the student and the next move --
# "How this student works", "Teach next", "Open question", "BOARD STATE." --
# which ticked into a deck would be slides about the tutoring rather than the
# work. Matched against the heading a paragraph sits under and against the
# paragraph's own lead (`HOW THEY WORK. They answer by...`, `Next: problem 31`).
NOT_DONE_RE = re.compile(
    r"\b(?:how (?:they|this student|the student|he|she|you) works?"
    r"|(?:this|the) student|teach next|next|pick up|how to start"
    r"|read these first|open questions?|open and unanswered|board state"
    r"|(?:got|was|went) wrong|mistakes? to avoid|error pattern"
    r"|nothing was (?:taught|got)|misread\w*|in flight|live now)\b", re.I)


def _lead(para):
    """A paragraph's own heading, where it opens with one: the words before its
    first full stop, colon or dash when those are short (`How this student
    works. Five or six lines...`), else its first six words."""
    text = (para or "").strip()
    m = re.match(r"^(.{3,60}?)(?:[.:]\s|\s[\u2014-]{1,2}\s)", text)
    return m.group(1) if m else " ".join(text.split()[:6])


def not_done(heading, para):
    """Is this handoff paragraph about the student or the next move, rather
    than a thing the sitting did?"""
    if heading and NOT_DONE_RE.search(heading):
        return True
    return bool(NOT_DONE_RE.search(_lead(para)))


def _stamped(text, chapter):
    m = STAMP_RE.match((text or "").lstrip())
    return bool(m and chapter and m.group(1).strip() == chapter.strip())


def _handoff_of(base, row, newest):
    """`(text, source)` of the handoff this sitting wrote, or `("", "")`.

    THE NEWEST SITTING ON A CHAPTER reads the file on disk -- the live one when
    its stamp names the chapter, else the parked one -- and only where it was
    written after the sitting opened: a handoff older than the sitting is the
    one it was handed, not the one it left. AN OLDER SITTING, or a newest one
    with no such file, reads the last revision committed inside its window
    whose stamp names its chapter. None, and the sitting offers no bullets.
    """
    root, chapter = row["root"], row["chapter"]
    if not chapter:
        return "", ""
    if newest:
        path = handoff.handoff_path(root)
        text, about = handoff.read_handoff(root)
        try:
            fresh = os.path.getmtime(path) >= row["start"]
        except OSError:
            fresh = False
        if text.strip() and fresh and about is not None \
                and about.strip() == chapter.strip():
            return text, "HANDOFF.md"
        parked = handoff.parked_handoff(root, chapter)
        try:
            if os.path.getmtime(parked) >= row["start"]:
                with open(parked, "r", encoding="utf-8") as fh:
                    return fh.read(), os.path.relpath(parked, root)
        except OSError:
            pass
    rel = os.path.join(row["rel"], "HANDOFF.md")
    raw = meeting._git(base, ["log", "--since=@%d" % int(row["start"]),
                              "--until=@%d" % int(row["end"]), "--no-merges",
                              "--pretty=%H", "--", rel])
    for sha in raw.split()[:10]:
        text = meeting._git(base, ["show", "%s:%s" % (sha, rel)])
        if _stamped(text, chapter):
            return text, "HANDOFF.md at %s" % sha[:8]
    return "", ""


def _step_key(title):
    """A plan step's title as a comparison key: what the step IS, without the
    dates and notes a plan hangs on it. `THE GRID, WHICH IS A CUBE. (Added
    2026-09-09, corrected 2026-09-11.)` and the same line re-dated are one
    step."""
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", str(title or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _open_steps(text):
    """`[(key, title)]`: every step a plan still lists as left to do -- a
    `STEP n.` line, or an unticked checklist item. Headings are not steps."""
    out, seen = [], set()
    for line in (text or "").splitlines():
        m = plan.STEP.match(line)
        title = ""
        if m:
            title = m.group(2)
        else:
            m2 = plan.TODO_ITEM.match(line)
            if m2 and m2.group(1) == " ":
                title = m2.group(2)
        title = re.sub(r"\s+", " ", title).strip(" .-\u2014").strip()
        # The plan's bookkeeping -- "(Added 2026-09-09, corrected 09-11.)" --
        # is not what the step is, and not a thing to put on a slide.
        title = re.sub(r"(?:\s*\([^)]*\)[.]?)+$", "", title).strip(" .-\u2014")
        key = _step_key(title)
        if len(title) < 6 or not key or key in seen:
            continue
        seen.add(key)
        out.append((key, meeting._clip(title, meeting.SUBJECT)))
    return out


def _plan_at(base, rel, when):
    """A plan file as it was committed at `when`, or None where it was not."""
    sha = meeting._git(base, ["rev-list", "-1", "--before=@%d" % int(when),
                              "HEAD", "--", rel]).strip()
    if not sha:
        return None
    text = meeting._git(base, ["show", "%s:%s" % (sha, rel)])
    return text if text.strip() else None


def finished_steps(base, row):
    """Plan steps this sitting FINISHED: listed as left when it opened, and gone
    -- or ticked -- when it ended.

    NOT EVERY DELETED LINE. `meeting.closed` reads a plan's diff, where a step
    re-dated, renumbered or rewritten is a deleted line too, and a sitting that
    taught nothing would be offered seven finished steps on the strength of an
    edit. Here the two ends of the window are compared by what each step is
    (`_step_key`), so only a step that went away counts. A plan that is not
    there at one end says nothing, rather than that all of it was done.
    """
    try:
        targets = plan.paths(row["root"])
    except Exception:                                        # noqa: BLE001
        return []
    out = []
    for target in targets:
        if not paths.within(target, base):
            continue
        rel = os.path.relpath(target, base)
        before = _plan_at(base, rel, row["start"])
        if row["live"]:
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as fh:
                    after = fh.read()
            except OSError:
                after = None
        else:
            # Half-open, as the commits are: what was committed before the end.
            after = _plan_at(base, rel, row["end"] - 1)
        if not before or not after:
            continue
        was, now = _open_steps(before), _open_steps(after)
        left = [_step_words(key) for key, _ in now]
        gone = [title for key, title in was
                if not any(_same_step(_step_words(key), k) for k in left)]
        # A PLAN REWRITTEN IS NOT A PLAN DONE. A change of direction replaces
        # most of a plan in one commit, and every step it dropped would read as
        # finished; more than half of it, and more than two steps, going in one
        # sitting is that, not an evening's work.
        if len(gone) > 2 and 2 * len(gone) > len(was):
            continue
        out += gone
    return out


_STEP_COMMON = frozenset(("the", "and", "for", "with", "its", "into", "from",
                          "this", "that", "only", "any", "not", "are", "all"))


def _step_words(key):
    return set(w for w in key.split() if len(w) > 2 and w not in _STEP_COMMON)


def _same_step(a, b):
    """Two plan steps' word sets name one step: the same words, or most of them
    -- `THE STOPWATCH -- AND THE REFERENCE RTTM IT UNBLOCKS` rewritten as `THE
    REFERENCE RTTM, AND THE STOPWATCH AXIS IT UNBLOCKS` is not a step done."""
    if not a or not b:
        return False
    return len(a & b) >= 0.6 * max(len(a), len(b))


def _body(base, sha):
    """A commit's message, whole, clipped for the brief. Fetched by the server
    because `git` is not something an unattended tutor may run."""
    return meeting._clip(meeting._git(base, ["show", "-s", "--format=%B", sha]),
                         BODY_CHARS)


def _items_of(base, row, rows, ids):
    ws, sid = row["ws"], row["id"]
    out = []

    def add(kind, key, text, detail, **more):
        one = {"id": _ident(ws, sid, kind, key), "sitting": sid, "kind": kind,
               "text": text, "detail": detail}
        if any(o["id"] == one["id"] for o in out):
            return
        one.update(more)
        out.append(one)

    for c in _in(row.get("log") or [], row, ids)[:MOST_COMMITS]:
        add("commit", c["sha"], c["subject"], c["sha"], sha=c["sha"])
    for title in finished_steps(base, row)[:MOST_STEPS]:
        add("step", title, title, "")
    same = [r for r in rows if r["ws"] == ws and r["chapter"] == row["chapter"]]
    newest = bool(same) and max(same, key=lambda r: r["end"])["id"] == sid
    text, source = _handoff_of(base, row, newest)
    n = 0
    for heading, para in _paragraphs(text):
        if n >= MOST_HANDOFF:
            break
        if not_done(heading, para):
            continue
        add("handoff", para, meeting._clip(para, ITEM_CHARS), heading,
            full=meeting._clip(para, BODY_CHARS), source=source)
        n += 1
    add("whole", "whole",
        "Everything this sitting covered (%d card%s)"
        % (row["cards"], "" if row["cards"] == 1 else "s"), "")
    return out


PUBLIC = ("id", "sitting", "kind", "text", "detail")


def gather(base, picks):
    """`(groups, rows)` for the picked sittings, with every internal field.

    A pick is compared against the rows the sheet offers and a miss is dropped
    -- `../` or a workspace this machine has not got is simply not a row.
    """
    rows, ids = _shown(base)
    by_id = dict((r["id"], r) for r in rows)
    groups, seen = [], set()
    for pick in picks or []:
        pick = str(pick or "")
        if pick in seen or not SITTING_RE.match(pick) or pick not in by_id:
            continue
        seen.add(pick)
        row = by_id[pick]
        groups.append({"sitting": pick, "label": row["label"],
                       "ws": row["ws"], "ws_name": row["ws_name"],
                       "row": row, "items": _items_of(base, row, rows, ids)})
    return groups, rows


def items(base, picks):
    """`{ok, groups}` -- what the sheet draws as its second question."""
    groups, _ = gather(base, picks)
    return {"ok": True, "groups": [
        {"sitting": g["sitting"], "label": g["label"], "ws_name": g["ws_name"],
         "items": [dict((k, i[k]) for k in PUBLIC) for i in g["items"]]}
        for g in groups]}


def ticked(groups, wanted):
    """The groups cut down to the ticked items. Ids are matched, never parsed."""
    want = set(str(w) for w in (wanted or []) if ITEM_RE.match(str(w or "")))
    out = []
    for g in groups:
        keep = [i for i in g["items"] if i["id"] in want]
        if keep:
            one = dict(g)
            one["items"] = keep
            out.append(one)
    return out


def fenced_in(groups):
    """The workspaces among these groups that hold a fence, in order."""
    out = []
    for g in groups:
        if g["row"].get("fenced") and g["ws"] not in out:
            out.append(g["ws"])
    return out


def mixed_fences(groups):
    """A refusal, in a sentence, where the ticks reach into two fenced
    workspaces -- or "". See `host_for`: a deck lives inside ONE fence."""
    held = fenced_in(groups)
    if len(held) < 2:
        return ""
    return ("%s and %s both hold data that never leaves them, and one deck "
            "cannot sit inside both. Make a deck from each."
            % (", ".join(held[:-1]), held[-1]))


def host_for(groups):
    """The workspace the deck is written in. Returns the workspace id, or "".

    A FENCED WORKSPACE HOSTS ANY DECK THAT TOUCHES IT. The deck's `.tex` is
    tracked and the repository is public; the push's PHI scan reads only what
    sits under a fenced workspace's root (`leaving._reason`), and the fenced
    workspace's own ignore rules only cover its own tree. So a deck drawing on
    PSYCH-ASR's sittings is written inside PSYCH-ASR, whatever else is ticked,
    and its source is scanned before it can leave. `mixed_fences` refuses two.

    Otherwise the workspace holding the most ticked items; a tie goes to the one
    the sheet listed first.
    """
    held = fenced_in(groups)
    if held:
        return held[0]
    count, order = {}, []
    for g in groups:
        if g["ws"] not in count:
            count[g["ws"]] = 0
            order.append(g["ws"])
        count[g["ws"]] += len(g["items"])
    if not order:
        return ""
    return max(order, key=lambda w: (count[w], -order.index(w)))


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def ws_slug(ws_id):
    """A workspace id as the front of a filename. Result ids are unique per
    workspace only, so two workspaces' `roc-curve-…` need their owner on them."""
    return re.sub(r"[^a-z0-9]+", "-", str(ws_id or "").lower()).strip("-") or "ws"


def _figures_of(g):
    """Every figure this sitting has a claim to, as `(rank, record)`.

    Rank 0 is a figure the sitting USED -- embedded in one of its cards, or named
    in the words of a ticked item -- and rank 1 one merely written inside its
    window. A job writes thirty figures in a minute, and a cap taken newest first
    across both would drop the one the lesson was actually about.
    """
    row = g["row"]
    try:
        idx = results.index(row["root"])
    except Exception:                                        # noqa: BLE001
        return []
    figs = dict((k, v) for k, v in idx.items() if v.get("kind") == "figure")
    hit = {}
    for m in row["members"]:
        for card in document.read_cards(m["cards_dir"]):
            for rid in EMBED_RE.findall(card.get("body") or ""):
                if rid.lower() in figs:
                    hit[rid.lower()] = 0
    words = " ".join((i.get("full") or i["text"]) for i in g["items"])
    for rid, rec in figs.items():
        if rec.get("file") and rec["file"] in words:
            hit[rid] = 0
        elif rid not in hit and row["start"] <= (rec.get("at") or 0) <= row["end"]:
            hit[rid] = 1
    return [(rank, figs[rid]) for rid, rank in hit.items()]


def figures_for(groups):
    """`(chosen, left_out, catalog, catalog_left)`. Used first, then newest."""
    chosen, keys = [], {}
    for g in groups:
        for rank, rec in _figures_of(g):
            key = (g["ws"], rec["id"])
            if key in keys:
                keys[key]["rank"] = min(keys[key]["rank"], rank)
                continue
            one = {"ws": g["ws"], "root": g["row"]["root"], "rec": rec,
                   "rank": rank}
            keys[key] = one
            chosen.append(one)
    chosen.sort(key=lambda f: (f["rank"], -(f["rec"].get("at") or 0)))
    left = max(0, len(chosen) - MOST_FIGURES)
    chosen = chosen[:MOST_FIGURES]
    catalog, roots = [], []
    for g in groups:
        if g["ws"] not in [r[0] for r in roots]:
            roots.append((g["ws"], g["row"]["root"]))
    taken = set((f["ws"], f["rec"]["id"]) for f in chosen)
    for ws, root in roots:
        try:
            idx = results.index(root)
        except Exception:                                    # noqa: BLE001
            continue
        for rec in idx.values():
            if rec.get("kind") == "figure" and (ws, rec["id"]) not in taken:
                catalog.append({"ws": ws, "rec": rec})
    # WHAT THE TICKED ITEMS TALK ABOUT FIRST, newest after that. A catalog cut
    # newest-first drops the older figure a sitting discussed without embedding
    # it, which is the one somebody will ink for.
    said = set(_words(" ".join((i.get("full") or i["text"])
                               for g in groups for i in g["items"])))

    def overlap(rec):
        hay = _words(" ".join(str(rec.get(k) or "")
                              for k in ("file", "name", "where")))
        return len(said.intersection(hay))

    catalog.sort(key=lambda f: (-overlap(f["rec"]), -(f["rec"].get("at") or 0)))
    return chosen, left, catalog[:MOST_CATALOG], max(0, len(catalog) - MOST_CATALOG)


# Words too common in figure names and handoffs to say one is about the other.
_COMMON = frozenset(("the", "and", "for", "with", "from", "that", "this", "png",
                     "pdf", "svg", "jpg", "figure", "figures", "fig", "plot",
                     "results", "result", "output", "outputs"))


def _words(text):
    """The distinctive words of a text, lower case, three letters or more."""
    return set(w for w in re.split(r"[^a-z0-9]+", str(text or "").lower())
               if len(w) >= 3 and w not in _COMMON)


def figure_named(root, wanted):
    """The id of the one figure `wanted` names in this workspace, or a list of
    the ids it could mean (empty where it names none).

    An exact id first. Otherwise every word of `wanted` must begin a word of
    the figure's file name, pretty name or folder -- so "roc" or "forest plot"
    reaches `roc_curve.png` or `subgroup_forest_plot.png` when the catalog did
    not list it, and "old" does not reach `bold.png`. Ids only ever come back out of
    `results.index`; nothing here is a path.
    """
    want = str(wanted or "").strip().lower()
    try:
        idx = results.index(root)
    except Exception:                                        # noqa: BLE001
        return []
    figs = dict((k, v) for k, v in idx.items() if v.get("kind") == "figure")
    if want in figs:
        return want
    words = [w for w in re.split(r"[^a-z0-9]+", want) if w]
    if not words:
        return []
    hits = []
    for rid, rec in figs.items():
        hay = " ".join(str(rec.get(k) or "") for k in ("file", "name", "where"))
        have = [t for t in re.split(r"[^a-z0-9]+", hay.lower()) if t]
        if all(any(t.startswith(w) for t in have) for w in words):
            hits.append((-(rec.get("at") or 0), rid))
    hits.sort()
    if len(hits) == 1:
        return hits[0][1]
    return [rid for _, rid in hits[:8]]


def png_size(path):
    """`(width, height)` off a PNG's IHDR, or None. Sixteen bytes read."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def snapshot(root_from, rid, ws, deck_dir):
    """Copy one figure beside a deck, through `results.find`. The path it went
    to, relative to the deck, or "" where the id is not one that workspace
    offers."""
    target, _ = results.find(root_from, rid)
    if not target:
        return ""
    ext = os.path.splitext(target)[1].lower() or ".png"
    name = "%s--%s%s" % (ws_slug(ws), rid, ext)
    dest = os.path.join(deck_dir, FIGURES, name)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(target, dest)
    except OSError:
        return ""
    return FIGURES + "/" + name


# ---------------------------------------------------------------------------
# the deck's directory and its brief
# ---------------------------------------------------------------------------
def deck_slug(root, now=None):
    """`deck-YYMMDD-HHMM`, with `-2` onward where that minute is taken."""
    stem = DECK_PREFIX + time.strftime("%y%m%d-%H%M", time.localtime(now))
    out, n = stem, 1
    while os.path.exists(os.path.join(root, writeups.WRITEUPS, out)):
        n += 1
        out = "%s-%d" % (stem, n)
    return out


def _allowed(base, path):
    """The path, or "" if any part of it is a fenced name."""
    rel = os.path.relpath(path, base)
    return "" if fenced.refused(rel) or fenced.refused(path) else path


def title_for(groups):
    names = []
    for g in groups:
        if g["ws_name"] not in names:
            names.append(g["ws_name"])
    n = sum(len(g["items"]) for g in groups)
    return "%s: %d thing%s from %d sitting%s" % (
        ", ".join(names), n, "" if n == 1 else "s",
        len(groups), "" if len(groups) == 1 else "s")


def _cell(text):
    return str(text or "").replace("|", "/").replace("\n", " ")


KIND_SAID = {"commit": "commit", "step": "a plan step that was finished",
             "handoff": "from the handoff", "whole": "the whole sitting"}


def write_brief(base, root, slug, groups, wid="", host=""):
    """Write the deck's directory: `.gitignore`, figure snapshots, `_brief.md`
    and `_brief.json`. Returns the record written to `_brief.json`.

    Written BEFORE the turn is asked, so the turn starts from a file rather than
    from a sentence that has to hold eleven items across three workspaces.
    """
    deck = os.path.join(root, writeups.WRITEUPS, slug)
    os.makedirs(deck, exist_ok=True)
    with open(os.path.join(deck, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("# written by the board: figures can be made from records, and\n"
                 "# this repository is public. The .tex is tracked.\n"
                 + "\n".join(IGNORE) + "\n")

    chosen, left, catalog, catalog_left = figures_for(groups)
    made = []
    for f in chosen:
        rel = snapshot(f["root"], f["rec"]["id"], f["ws"], deck)
        if not rel:
            continue
        size = png_size(os.path.join(deck, rel))
        made.append({"file": rel, "ws": f["ws"], "id": f["rec"]["id"],
                     "where": f["rec"].get("where") or "",
                     "name": f["rec"].get("name") or "",
                     "date": f["rec"].get("iso") or "",
                     "size": ("%d x %d" % size) if size else ""})

    rel_tex = "%s/%s/%s.tex" % (writeups.WRITEUPS, slug, slug)
    out = ["# The brief for `%s`" % rel_tex, "",
           "Somebody ticked the things below from past tutoring sittings, on the "
           "front door, and asked for a slide deck of them. Written by the board "
           "on %s. You write `%s` and build it; nothing else in this directory "
           "is yours to edit." % (time.strftime("%Y-%m-%d %H:%M"), rel_tex), "",
           "## What goes in", ""]
    fences = []
    for g in groups:
        row = g["row"]
        out.append("### %s -- %s" % (g["ws_name"], g["label"]))
        out.append("")
        reads = []
        for m in row["members"]:
            for what, path in (("cards", m["cards_dir"]),
                               ("transcript", m["turns"])):
                if os.path.exists(path) and _allowed(base, path):
                    reads.append("%s `%s`" % (what, path))
        hand = handoff.handoff_path(row["root"])
        if os.path.exists(hand) and _allowed(base, hand):
            reads.append("the workspace's handoff `%s`" % hand)
        if reads:
            out.append("To read more: " + "; ".join(reads) + ".")
            out.append("")
        for i in g["items"]:
            if i["kind"] == "commit":
                out.append("- **%s** (commit `%s` in %s)"
                           % (i["text"], i["sha"], g["ws"]))
                body = _body(base, i["sha"])
                if body and body.strip() != i["text"].strip():
                    out.append("  > " + body.replace("\n", "\n  > "))
            elif i["kind"] == "handoff":
                out.append("- %s (%s, under \"%s\")"
                           % (i.get("full") or i["text"], i.get("source") or
                              "the handoff", i["detail"] or "no heading"))
            elif i["kind"] == "whole":
                out.append("- **%s.** Read the cards and the transcript named "
                           "above, and take the concepts, results and numbers "
                           "from them." % i["text"])
            else:
                out.append("- **%s** (%s)" % (i["text"], KIND_SAID[i["kind"]]))
        out.append("")
        for name in row["fenced"]:
            line = "- %s holds `%s/`: never open anything under it." % (g["ws"], name)
            if line not in fences:
                fences.append(line)
    if fences:
        out += ["## Fences", ""] + fences + [""]

    out += ["## Figures already copied beside the deck", ""]
    if made:
        out += ["| file | workspace | where | name | date | pixels |",
                "|---|---|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s | %s | %s |"
                % (f["file"], f["ws"], _cell(f["where"]), _cell(f["name"]),
                   f["date"], f["size"]) for f in made]
    else:
        out.append("None: those sittings wrote no figure this board can show.")
    if left:
        out.append("")
        out.append("%d more figure%s belonged to these sittings and %s left "
                   "out; they are in the catalog below."
                   % (left, "" if left == 1 else "s",
                      "was" if left == 1 else "were"))
    out += ["",
            "OPEN A FIGURE BEFORE YOU USE IT, and say on the slide what it "
            "shows. These are the pipeline's output, not yours: a figure nobody "
            "opened is a figure nobody can vouch for.", ""]

    out += ["## Other figures you may pull", "",
            "`board deckfig %s/%s <workspace> <result id>` copies one into "
            "`figures/` and prints the path to put in `\\includegraphics`."
            % (writeups.WRITEUPS, slug), ""]
    if catalog:
        out += ["| workspace | result id | where | name | date |",
                "|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | %s |"
                % (f["ws"], f["rec"]["id"], _cell(f["rec"].get("where")),
                   _cell(f["rec"].get("name")), f["rec"].get("iso") or "")
                for f in catalog]
    else:
        out.append("There are none.")
    if catalog_left:
        out += ["", "%d more exist and are not listed. The ones the ticked "
                "items mention come first. For one that is not listed, give "
                "`board deckfig` a word from its file name instead of an id, "
                "and it finds it or lists the ids that word matches."
                % catalog_left]
    out += ["",
            "## How to plan the slides", "",
            "- YOU PLAN THEM. An item gets as many slides as it needs, and "
            "items that belong together share slides. There is no "
            "one-slide-per-workspace rule and no one-slide-per-item rule.",
            "- Order them by the story, not by workspace or by date.",
            "- Write for somebody who was not in the room. Use the numbers the "
            "sources give, and never a number they do not.",
            "- Present the work -- what was built, shown, measured or proved -- "
            "not the conversation that produced it.", "",
            "## How to write it", "",
            "- `\\documentclass[aspectratio=169]{beamer}`, and a `\\title` that "
            "says what the deck is about.",
            "- ONE PAGE PER FRAME. No `allowframebreaks`, and nothing that "
            "spills: a mark on a slide finds its slide by page number, and a "
            "frame that became two pages sends the next correction to the "
            "wrong slide.",
            "- A figure is `\\includegraphics[width=\\linewidth,height=0.75"
            "\\textheight,keepaspectratio]{figures/<file>}`.",
            "- Build from the workspace root with `latexmk -pdf -cd "
            "-interaction=nonstopmode %s`. `-cd` is what makes `figures/` "
            "resolve and puts the PDF beside the source. A LaTeX error is "
            "yours to fix before the turn ends." % rel_tex, ""]
    with open(os.path.join(deck, BRIEF_MD), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))

    rec = {"slug": slug, "wid": wid, "host": host, "at": time.time(),
           "title": title_for(groups),
           "workspaces": [g["ws"] for n, g in enumerate(groups)
                          if g["ws"] not in [x["ws"] for x in groups[:n]]],
           "items": [{"id": i["id"], "sitting": g["sitting"], "kind": i["kind"],
                      "text": i["text"]} for g in groups for i in g["items"]],
           "figures": [f["file"] for f in made]}
    with open(os.path.join(deck, BRIEF_JSON), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    return rec


# ---------------------------------------------------------------------------
# where each deck got to
# ---------------------------------------------------------------------------
def _read_brief(deck):
    try:
        with open(os.path.join(deck, BRIEF_JSON), "r", encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def drawn_from(deck):
    """The workspaces a deck's brief says it was made from, or []. What `board
    deckfig` may copy a figure out of: a deck about TRD-EHR does not get to pull
    PSYCH-ASR's results because somebody inked "add the ROC curve"."""
    rec = _read_brief(deck) or {}
    out = [str(w) for w in rec.get("workspaces") or [] if isinstance(w, str)]
    for i in rec.get("items") or []:
        ws = str((i or {}).get("sitting") or "").split("@", 1)[0]
        if ws and ws not in out:
            out.append(ws)
    return out


def _the_doc(root, slug):
    """The library's record of this deck, looked up rather than computed."""
    want = "%s/%s" % (writeups.WRITEUPS, slug)
    for doc in library.documents(root):
        if doc.get("dir") == want and doc.get("stem") == slug and doc.get("pdf"):
            return doc
    return None


# HOW LONG A DECK'S DIRECTORY STAYS QUIET, after its turn is over, before the
# missing PDF is the answer. The daemon marks the inbox read a moment before it
# says it is working, and a build that has just finished writes its PDF a moment
# after the turn's last edit; two minutes covers both and is not a wait anybody
# watches.
QUIET = 120


def _turn_over(root, wid):
    """Has the host's tutor taken this ask and finished with it?

    TAKEN is the inbox line marked read -- `board inbox` does that as a turn
    starts. FINISHED is nothing working there now: `agent.json` not saying
    `working`, or saying it with nothing attached. A turn still queued, or one
    running (this or the next), is not over, and the deck is still being
    written.
    """
    if not wid:
        return False
    taken = False
    try:
        with open(os.path.join(root, "live", "inbox", "messages.jsonl"), "r",
                  encoding="utf-8") as fh:
            for line in fh:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if isinstance(m, dict) and m.get("id") == wid:
                    taken = bool(m.get("read"))
    except OSError:
        return False
    if not taken:
        return False
    from . import missions                            # local: a heavy import
    agent = missions._agent(root)
    if agent.get("state") != "working":
        return True
    try:
        return not missions._listening(agent)
    except Exception:                                        # noqa: BLE001
        return False


def _newest_in(folder):
    newest = 0
    try:
        for here, _, files in os.walk(folder):
            for n in files:
                try:
                    newest = max(newest, os.path.getmtime(os.path.join(here, n)))
                except OSError:
                    continue
    except OSError:
        pass
    return newest


def _unbuilt(root, slug, rec, at):
    """`(state, why)` for a deck with no PDF.

    NOT THE CEILING ALONE. `writeups._landed` freezes `done` on the first
    document to change, and a `.tex` is one -- so a deck that failed to build
    would read "being written" for two hours to somebody with no terminal. Once
    the turn is over (`_turn_over`) and nothing in the deck's directory has
    moved for `QUIET`, the missing PDF is the answer, and it says which kind.
    """
    deck = os.path.join(root, writeups.WRITEUPS, slug)
    tex = os.path.isfile(os.path.join(deck, slug + ".tex"))
    judged = writeups.state(root, rec.get("wid") or "")
    gone = judged == "failed" or time.time() - at >= writeups.CEILING
    if not gone and time.time() - _newest_in(deck) >= QUIET \
            and _turn_over(root, rec.get("wid") or ""):
        gone = True
    if not gone:
        return "being written", ""
    if tex:
        return "did not land", ("The deck was written but did not build. "
                                "Ask for it again.")
    return "did not land", ("The tutor ended without writing the deck. "
                            "Ask for it again.")


def decks(base):
    """`{ok, decks}`: the newest few, each `ready`, `being written` or `did not
    land`, with the library id of a ready one.

    READY IS THE DECK'S OWN PDF, not the writeup record's verdict:
    `writeups._landed` credits the first document to change in the host, and a
    `.tex` written before it is built is exactly such a change.
    """
    found = []
    for ws in atlas.workspaces(base):
        here = os.path.join(ws["root"], writeups.WRITEUPS)
        try:
            names = os.listdir(here)
        except OSError:
            continue
        for name in names:
            if not name.startswith(DECK_PREFIX):
                continue
            rec = _read_brief(os.path.join(here, name))
            if rec and rec.get("slug") == name:
                found.append((rec.get("at") or 0, ws, rec))
    found.sort(key=lambda f: -f[0])
    out = []
    for at, ws, rec in found[:MOST_DECKS]:
        slug, root = rec["slug"], ws["root"]
        # THE PDF FIRST, because it is one `stat`, and the library's walk runs
        # `pdfinfo` over every document in the workspace. Asked every ten
        # seconds while the sheet is open, a deck still being written must not
        # cost that.
        doc = None
        if os.path.isfile(os.path.join(root, writeups.WRITEUPS, slug,
                                       slug + ".pdf")):
            doc = _the_doc(root, slug)
            if not doc:
                # Built since the library last walked: its list is cached for
                # thirty seconds, and a deck that is there must not wait for it.
                library.forget()
                doc = _the_doc(root, slug)
        why = ""
        if doc:
            state = "ready"
        else:
            state, why = _unbuilt(root, slug, rec, at)
        out.append({"title": (doc or {}).get("title") or rec.get("title") or slug,
                    "slug": slug, "host": ws["dir"], "host_id": ws["id"],
                    "host_name": _name_of(ws), "state": state, "why": why,
                    "doc": (doc or {}).get("id") or "", "at": at})
    return {"ok": True, "decks": out}
