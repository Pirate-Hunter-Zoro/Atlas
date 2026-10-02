"""The cards on the board, which are files.

A card appears the instant its file has something IN it, so everything here is
about reading them back cheaply: what is on the board, in order, with the TikZ
in them handed off to be drawn.

It used to be "the instant its file exists", and the difference cost an evening.
See `has_body`.
"""

import hashlib
import json
import os
import re
import time

from .. import reasoning
from ..course import results


POLL_SECONDS = 0.25
CARD_RE = re.compile(r"^(\d{4})[-_.](.*)\.(md|markdown|tex)$")

# Names a writer leaves while it is writing. `board write` writes to one of these
# and renames, which is atomic within a directory -- so a card is whole or absent
# and never both. The pattern is here as well because a crash between the two
# steps leaves the part file behind, and a part file is not a card.
PART_RE = re.compile(r"^\.")

# ---------------------------------------------------------------------------
# card parsing
# ---------------------------------------------------------------------------
def parse_front_matter(text):
    """Minimal `key: value` front matter between --- fences. No YAML dependency."""
    meta = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            head = text[3:end]
            body = text[end + 4:]
            if body.startswith("\n"):
                body = body[1:]
            for line in head.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip('"').strip("'")
    return meta, body


TIKZ_BLOCK = re.compile(
    r"^[ \t]*```[ \t]*(tikz|tikzcd|latex)[ \t]*\n(.*?)^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)


def extract_tikz(body, jobs, repo):
    """Replace fenced tikz blocks with a placeholder token the client turns into
    an <img>. Queue anything not already cached for compilation."""
    def sub(match):
        kind = match.group(1)
        src = match.group(2)
        digest = hashlib.sha1((kind + "\x00" + src).encode("utf-8")).hexdigest()[:16]
        svg = os.path.join(repo.tikz, digest + ".svg")
        if os.path.exists(svg):
            status = "ready"
        elif os.path.exists(os.path.join(repo.tikz, digest + ".err")):
            status = "error"
        else:
            status = "pending"
            jobs.append((digest, kind, src))
        return "\n\n@@FIGURE:%s:%s@@\n\n" % (digest, status)

    return TIKZ_BLOCK.sub(sub, body)


# ---------------------------------------------------------------------------
# a thread proposed on a card, accepted with one tap
# ---------------------------------------------------------------------------
# A rethink that finds a NEW question proposes it as a thread, in a fenced
# `thread` block holding the JSON `board thread add` reads. The block is drawn
# as the proposal and a control, `@@THREAD:<id>:<state>@@`; the tap posts the
# card and the id, and the server reads the thread back off the card file
# itself -- nothing the browser sends is made into the thread.
THREAD_BLOCK = re.compile(
    r"^[ \t]*```[ \t]*thread[ \t]*\n(.*?)^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)


def proposals(body):
    """Every thread proposed on a card body, parsed: `[(dict or None, raw)]`."""
    out = []
    for m in THREAD_BLOCK.finditer(body or ""):
        try:
            one = json.loads(m.group(1))
        except ValueError:
            one = None
        out.append((one if isinstance(one, dict) else None, m.group(1)))
    return out


def extract_threads(body, root):
    """Replace each `thread` block with the proposal in words and its control.

    The state is read off the thread file every time, so a card proposing a
    thread that has since been added says so: `new` (one tap adds it),
    `there` (the file has that id) or `bad` (the file would refuse it, and the
    first problem is said).
    """
    if "```" not in (body or "") or "thread" not in body:
        return body
    from ..course import threads                             # local: a cycle

    def sub(match):
        try:
            one = json.loads(match.group(1))
        except ValueError:
            one = None
        if not isinstance(one, dict):
            return ("\n\n**A proposed thread** that is not valid JSON, so it "
                    "cannot be added from here.\n\n@@THREAD::bad@@\n\n")
        state, problems = threads.proposal(root, one)
        tid = str(one.get("id") or "")
        tasks = [t.get("text") if isinstance(t, dict) else t
                 for t in (one.get("tasks") or [])]
        lines = ["**Proposed thread** `%s`: %s" % (tid, one.get("title") or "")]
        if one.get("question"):
            lines.append(str(one["question"]))
        if tasks and tasks[0]:
            lines.append("First task: %s" % tasks[0])
        if problems:
            lines.append("It cannot be added as written: %s" % problems[0])
        safe = tid if threads.ID_RE.match(tid) else ""
        return ("\n\n" + "\n\n".join(lines)
                + "\n\n@@THREAD:%s:%s@@\n\n" % (safe, state))

    return THREAD_BLOCK.sub(sub, body)


def proposed(cards_dir, card_id, tid):
    """The thread `tid` as proposed on card `card_id`, read off its file, or None."""
    if not re.match(r"^\d{4}$", str(card_id or "")):
        return None
    try:
        names = os.listdir(cards_dir)
    except OSError:
        return None
    for name in sorted(names):
        m = CARD_RE.match(name)
        if not m or m.group(1) != card_id or PART_RE.match(name):
            continue
        try:
            with open(os.path.join(cards_dir, name), "r", encoding="utf-8") as fh:
                _meta, body = parse_front_matter(fh.read())
        except OSError:
            return None
        for one, _raw in proposals(body):
            if one and one.get("id") == tid:
                return one
    return None


# Parsed cards, keyed by path, valid while (mtime, size) hold. The poll runs four
# times a second and this home directory is a shared network filesystem, so
# re-reading and re-parsing every card in the lesson on every tick is real cost
# for files that have not changed -- and it grows with the length of the lesson.
_CARD_CACHE = {}


def has_body(body):
    """Is there anything on this card to read.

    A CARD WITH NO BODY IS A FILE SOMEBODY IS STILL WRITING, NOT A CARD.

    `open(path, "w")` truncates before it writes, and this poll runs four times
    a second over a shared network filesystem -- so a poll can land between the
    truncate and the content and see a card with nothing in it. On the glass that
    is worse than a blank card: there is nothing to type, so the type-out skips
    it, so no hold is taken, so the writing surface comes down and the next board
    appears BEFORE the response. Then the real body lands and types, underneath a
    board that is already there.

    Measured in a Galois sitting: card 0041 on the glass empty at 10:38:38, its
    real body typed at 10:39:14. Reported as "I just submitted a written response
    and the next board showed up before the tutor response showed up" -- on a
    board whose own trace showed both cards typing perfectly, because they did.

    `board write` renames into place now, so this should never fire for a card
    this tool wrote. It stays because it is not the only writer: an INTERACTIVE
    tutor writes the file itself -- the brief tells it to -- and a plain shell
    redirect truncates exactly the same way.
    """
    return bool((body or "").strip())


def load_cards(repo, jobs):
    cards = []
    try:
        names = sorted(os.listdir(repo.cards))
    except OSError:
        names = []
    seen = set()
    for name in names:
        if PART_RE.match(name):
            continue
        m = CARD_RE.match(name)
        if not m:
            continue
        path = os.path.join(repo.cards, name)
        seen.add(path)
        try:
            st = os.stat(path)
        except OSError:
            continue
        stamp = (st.st_mtime, st.st_size)
        hit = _CARD_CACHE.get(path)
        if hit and hit[0] == stamp:
            # The figure placeholders carry compile status, which changes when a
            # diagram finishes -- so the body is re-scanned even on a hit. It is
            # a regex over a string already in memory, not a read and a parse.
            card = dict(hit[1])
            card["body"] = extract_tikz(
                extract_threads(hit[2], getattr(repo, "root", None)), jobs, repo)
            cards.append(card)
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError:
            continue
        meta, rawbody = parse_front_matter(raw)
        # Not cached either: the stamp it would be cached under is `(mtime,
        # size)` read through this filer's attribute cache, so an empty parse
        # pinned there outlives the write that caused it by however long those
        # attributes take to refresh. That is where the 36 seconds came from.
        if not has_body(rawbody):
            continue
        # Whoever wrote this file. `board write` refuses a card that is the
        # model deliberating, but an interactive tutor writes the file itself --
        # the brief tells it to -- and that door has no gate on it.
        rawbody = reasoning.card_body(rawbody)
        # A figure named by its path becomes its id here, once, before the body
        # is cached -- see `results.embed_ids`.
        root = getattr(repo, "root", None)
        if root:
            rawbody = results.embed_ids(root, rawbody)
        # A proposed thread is re-read on every poll, like a figure's status:
        # whether it is still `new` is a fact about the thread file, not the card.
        body = extract_tikz(extract_threads(rawbody, root), jobs, repo)
        cards.append({
            "id": m.group(1),
            "slug": m.group(2),
            "kind": (meta.get("kind") or "lesson").lower(),
            "title": meta.get("title", ""),
            "tag": meta.get("tag", ""),
            "body": body,
            "mtime": st.st_mtime,
        })
        _CARD_CACHE[path] = (stamp, dict(cards[-1]), rawbody)
    for gone in [k for k in _CARD_CACHE if k not in seen and k.startswith(repo.cards)]:
        del _CARD_CACHE[gone]
    return cards


# ---------------------------------------------------------------------------
# a turn ends on a report
# ---------------------------------------------------------------------------
# A doing turn writes a `pending` card first -- one sentence, so the board is
# never blank -- and writes its report over it. A turn that exits with the
# newest card still `pending` has not reported. The daemon wakes it once more
# with `[unfinished]`; if that also leaves the card `pending`, the card is
# replaced by a `stopped` one listing what is on disk, so the board and the
# disk cannot disagree without the card saying so.
PENDING = "pending"
STOPPED = "stopped"

# How many uncommitted paths a stopped card names; the rest are counted.
STOPPED_NAMES = 12


def newest(cards_dir):
    """`(path, meta)` of the highest-numbered card in `cards_dir`, or `(None, {})`."""
    try:
        names = sorted(n for n in os.listdir(cards_dir)
                       if CARD_RE.match(n) and not PART_RE.match(n))
    except OSError:
        return None, {}
    for name in reversed(names):
        path = os.path.join(cards_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                meta, body = parse_front_matter(fh.read())
        except OSError:
            continue
        if not has_body(body):
            continue
        return path, meta
    return None, {}


def is_pending(meta):
    return ((meta or {}).get("kind") or "").lower() == PENDING


def stopped_body(changed, jobs=None, thread="", elsewhere=0):
    """The card that replaces a placeholder whose turn never reported.

    `changed` is `git status` under the work's paths, workspace-relative: the
    thread's paths where the sitting is on one. `elsewhere` counts what else
    is uncommitted in the workspace, so a narrowed list never reads as all
    there is. `jobs` is whatever was registered while the turn ran, one line
    each.
    """
    lines = ["The turn stopped without reporting. Here is what changed on disk.", ""]
    under = (" on `%s`" % thread) if thread else ""
    if changed:
        lines += ["Uncommitted%s:" % under, ""]
        lines += ["- `%s`" % name for name in changed[:STOPPED_NAMES]]
        if len(changed) > STOPPED_NAMES:
            lines.append("- and %d more" % (len(changed) - STOPPED_NAMES))
    elif thread:
        lines.append("Nothing under `%s`'s paths is uncommitted." % thread)
    else:
        lines.append("Nothing under this work is uncommitted.")
    if elsewhere:
        lines += ["", "And %d more path%s uncommitted elsewhere in this workspace."
                  % (elsewhere, "" if elsewhere == 1 else "s")]
    if jobs:
        lines += ["", "Jobs registered since:", ""]
        lines += ["- %s" % job for job in jobs]
    return "\n".join(lines)


def write_stopped(path, changed, jobs=None, thread="", elsewhere=0):
    """Replace the placeholder at `path` with a `stopped` card. True if written.

    The card names its `thread` in its front matter, which is how the map
    badges that thread's box (`stopped_thread`). Same directory and
    `os.replace`, as `board write` does, so a poll sees the old card or the new
    one and never an empty file.
    """
    head = "---\nkind: %s\n%s---\n" % (
        STOPPED, ("thread: %s\n" % thread) if thread else "")
    tmp = os.path.join(os.path.dirname(path),
                       ".%s.%d.part" % (os.path.basename(path), os.getpid()))
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(head + stopped_body(changed, jobs, thread,
                                         elsewhere).rstrip() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def stopped_thread(cards_dir):
    """The thread whose turn stopped without a report, or "".

    Only while that `stopped` card is the newest: the next card written is the
    next turn, and the badge goes with it.
    """
    _path, meta = newest(cards_dir)
    if ((meta or {}).get("kind") or "").lower() != STOPPED:
        return ""
    return str(meta.get("thread") or "").strip()
