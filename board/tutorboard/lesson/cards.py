"""The cards on the board, which are files.

A card appears the instant its file has something IN it, so everything here is
about reading them back cheaply: what is on the board, in order, with the TikZ
in them handed off to be drawn.

It used to be "the instant its file exists", and the difference cost an evening.
See `has_body`.
"""

import hashlib
import os
import re
import time

from .. import reasoning


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
            card["body"] = extract_tikz(hit[2], jobs, repo)
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
        body = extract_tikz(rawbody, jobs, repo)
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
