"""The cards on the board, which are files.

Everything here reads them back cheaply: what is on the board, in order,
with TikZ handed off to be drawn.

The constraint: a card appears only once its file has a body (`has_body`),
because a truncated file mid-write would otherwise reach the glass empty.
"""

import os
import re
import time

from .. import reasoning
from ..course import library
from ..server import tikz


POLL_SECONDS = 0.25
CARD_RE = re.compile(r"^(\d{4})[-_.](.*)\.(md|markdown|tex)$")

# A writer's temporary names: `board write` renames into place, and a crash
# can leave one behind, which is not a card.
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
        digest = tikz.digest(kind, src, repo.root)
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


# Parsed cards keyed by path, valid while (mtime, size) hold: the poll is
# frequent and the filesystem may be networked.
_CARD_CACHE = {}


def has_body(body):
    """Is there anything on this card to read? An empty card is a file still
    being written (`open("w")` truncates first). `board write` renames into
    place, but an interactive tutor or a shell redirect writes in place.
    """
    return bool((body or "").strip())


def card_files(repo):
    """`[(id, name)]` of every card file in the session, in card order."""
    try:
        names = sorted(os.listdir(repo.cards))
    except OSError:
        return []
    out = []
    for name in names:
        if PART_RE.match(name):
            continue
        m = CARD_RE.match(name)
        if m:
            out.append((m.group(1), name))
    return out


def load_cards(repo, jobs):
    """Every card on the board, in order."""
    return _parse(repo, card_files(repo), jobs)


def window(repo, jobs, limit, before=None):
    """`(cards, older, ids)`: the newest `limit` cards numbered below `before`
    (every card when None), how many card files are older still, and the id
    of every card file on disk. Only the cards in the window are read."""
    files = card_files(repo)
    pool = files
    if before is not None:
        pool = [f for f in files if f[0] < before]
    pick = pool[-limit:] if limit else pool
    return _parse(repo, pick, jobs, every=files), len(pool) - len(pick), \
        [f[0] for f in files]


def _parse(repo, files, jobs, every=None):
    """The cards of `files` (`card_files` entries), each parsed once per
    (mtime, size). `every` is the whole listing, for pruning the cache."""
    cards = []
    for ident, name in files:
        path = os.path.join(repo.cards, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        stamp = (st.st_mtime, st.st_size)
        hit = _CARD_CACHE.get(path)
        if hit and hit[0] == stamp:
            # Placeholders carry compile status, so the body is re-scanned
            # even on a hit (a regex, not a read).
            card = dict(hit[1])
            card["body"] = extract_tikz(hit[2], jobs, repo)
            cards.append(card)
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError:
            continue
        meta, rawbody = parse_front_matter(raw)
        # An empty parse is not cached: the (mtime, size) stamp can lag the
        # write on a network filer.
        if not has_body(rawbody):
            continue
        # An interactive tutor's own file has no `board write` gate.
        rawbody = reasoning.card_body(rawbody)
        # Path-named figures become ids once, before caching.
        root = getattr(repo, "root", None)
        if root:
            rawbody = library.embed_result_ids(root, rawbody)
        body = extract_tikz(rawbody, jobs, repo)
        cards.append({
            "id": ident,
            "slug": CARD_RE.match(name).group(2),
            "kind": (meta.get("kind") or "lesson").lower(),
            "title": meta.get("title", ""),
            "tag": meta.get("tag", ""),
            # The fallback that wrote it, when the provider could not.
            "by": meta.get("by", ""),
            "body": body,
            "mtime": st.st_mtime,
        })
        _CARD_CACHE[path] = (stamp, dict(cards[-1]), rawbody)
    listed = set(os.path.join(repo.cards, n) for _i, n in (
        files if every is None else every))
    for gone in [k for k in _CARD_CACHE
                 if k not in listed and os.path.dirname(k) == repo.cards]:
        del _CARD_CACHE[gone]
    return cards


# ---------------------------------------------------------------------------
# a turn ends on a report
# ---------------------------------------------------------------------------
# A doing turn writes a `pending` card first and its report over it. One
# left pending wakes `[unfinished]` once; still pending, it is replaced by a
# `stopped` card listing what is on disk.
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
    `changed` is `git status` under the work's paths; `elsewhere` counts other
    uncommitted paths in the workspace; `jobs` is one line per job registered
    during the turn."""
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
    """Replace the placeholder at `path` with a `stopped` card (naming
    `thread` as `stopped_thread`), via `os.replace` so a poll never sees an
    empty file. True if written."""
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
    """The thread whose turn stopped without a report, or "", while that card
    is the newest."""
    _path, meta = newest(cards_dir)
    if ((meta or {}).get("kind") or "").lower() != STOPPED:
        return ""
    return str(meta.get("thread") or "").strip()
