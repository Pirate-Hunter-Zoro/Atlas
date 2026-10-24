"""A turn is the student's half of the conversation.

Numbered, revisable and append-only on disk; a corrected answer supersedes
its earlier revision in place, and only the newest revision is shown.
"""

import json
import os
import re
import time

from . import cards, notes




def load_turns(repo, path=None):
    """Newest revision of each turn, in the order the turns first appeared."""
    order, latest = [], {}
    try:
        with open(path or repo.turns_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                tid = rec.get("id")
                if not tid:
                    continue
                if tid not in latest:
                    order.append(tid)
                    rec["t0"] = rec.get("t")
                if rec.get("rev", 1) >= latest.get(tid, {}).get("rev", 0):
                    # A revision keeps the original's place in the transcript.
                    rec["t0"] = latest.get(tid, rec).get("t0", rec.get("t"))
                    latest[tid] = rec
    except OSError:
        return []
    return [latest[t] for t in order]


# A turn id is unique for the life of the course: the high-water mark comes
# from every place that can name a turn (the inbox is never rotated) and is
# kept in a file archiving does not move.
TURN_SEQ = ".turnseq"
TURN_ID_RE = re.compile(r"^t(\d+)")


def _turn_n(value):
    m = TURN_ID_RE.match(str(value or ""))
    return int(m.group(1)) if m else 0


def turn_hwm(repo):
    """The highest turn number this course has ever issued."""
    n = 0
    try:
        with open(os.path.join(repo.live, TURN_SEQ), "r", encoding="utf-8") as fh:
            n = int((fh.read() or "0").strip() or 0)
    except (OSError, ValueError):
        n = 0
    # The current lesson's transcript.
    for rec in load_turns(repo):
        n = max(n, _turn_n(rec.get("id")))
    # The inbox, which is never rotated and is therefore the real history.
    for rec in notes.load_messages(repo, limit=10 ** 9):
        n = max(n, _turn_n(rec.get("id")))
    # Frozen answers, named <turn>-r<rev>.
    try:
        for name in os.listdir(repo.answers):
            n = max(n, _turn_n(name))
    except OSError:
        pass
    return n


def bump_turn_hwm(repo, tid):
    n = _turn_n(tid)
    if not n:
        return
    try:
        with open(os.path.join(repo.live, TURN_SEQ), "r", encoding="utf-8") as fh:
            have = int((fh.read() or "0").strip() or 0)
    except (OSError, ValueError):
        have = 0
    if n <= have:
        return
    try:
        with open(os.path.join(repo.live, TURN_SEQ), "w", encoding="utf-8") as fh:
            fh.write("%d\n" % n)
    except OSError:
        pass


def next_turn_id(repo):
    return "t%04d" % (turn_hwm(repo) + 1)


def turn_revision(repo, tid):
    """Which revision the next write of `tid` is, read from the transcript
    and the inbox, which keeps turns the transcript archived."""
    rev = 0
    for rec in load_turns(repo):
        if rec.get("id") == tid:
            rev = max(rev, rec.get("rev", 1))
    for rec in notes.load_messages(repo, limit=10 ** 9):
        if rec.get("id") == tid:
            rev = max(rev, rec.get("rev", 1))
    return rev + 1


def newest_question(repo):
    """The card a turn sent now is answering."""
    newest = None
    try:
        names = sorted(os.listdir(repo.cards))
    except OSError:
        return None
    for name in names:
        m = cards.CARD_RE.match(name)
        if not m:
            continue
        try:
            with open(os.path.join(repo.cards, name), "r", encoding="utf-8") as fh:
                meta, _ = cards.parse_front_matter(fh.read())
        except OSError:
            continue
        if (meta.get("kind") or "lesson").lower() == "question":
            newest = m.group(1)
    return newest


def write_turn(repo, rec):
    with open(repo.turns_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    # So the counter survives this lesson being filed away.
    bump_turn_hwm(repo, rec.get("id"))


# ---------------------------------------------------------------------------
# past lessons
# ---------------------------------------------------------------------------
