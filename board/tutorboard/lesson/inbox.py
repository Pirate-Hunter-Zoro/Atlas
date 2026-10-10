"""A session's inbox, `inbox/messages.jsonl`: what was sent, and what a turn took.

A line is unread until a turn takes it. A line written `"wake": false` (a
bind, a mode change, a filing) never wakes a turn by itself; the next turn
takes it with the rest, so the tutor still reads it.

    wakes(m)              is this line unread work that wakes a turn?
    unread(repo)          every unread line
    waiting(repo)         the unread lines that wake a turn
    take(repo, before)    the unread lines as a turn reads them, marked read
    render(msgs, repo)    lines as a turn reads them

Marking read rewrites each taken line IN PLACE, padded to its old length, so a
line another writer appends meanwhile (the server, `board job`, a route) is
never lost: appends only ever land past what was read.
"""

import fcntl
import json
import os


def wakes(m):
    """Is `m` an unread line that wakes a turn?"""
    return isinstance(m, dict) and not m.get("read") and m.get("wake") is not False


def _lines(path):
    """`[(offset, raw bytes, parsed or None)]` for every whole line of `path`.
    A last line with no newline is still being written and is left out."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return []
    out, pos = [], 0
    while True:
        end = data.find(b"\n", pos)
        if end < 0:
            break
        raw = data[pos:end]
        try:
            m = json.loads(raw.decode("utf-8")) if raw.strip() else None
        except (ValueError, UnicodeDecodeError):
            m = None
        out.append((pos, raw, m if isinstance(m, dict) else None))
        pos = end + 1
    return out


def unread(repo):
    """Every unread line, oldest first."""
    return [m for _, _, m in _lines(repo.messages_path) if m and not m.get("read")]


def waiting(repo):
    """The unread lines that wake a turn, oldest first."""
    return [m for _, _, m in _lines(repo.messages_path) if wakes(m)]


def render(msgs, repo):
    """Lines as a turn reads them: `[<iso>] <text>`, then a line for each file
    and the handwritten page, by absolute path."""
    out = []
    for m in msgs:
        out.append("[%s] %s" % (m.get("iso", "?"), m.get("text", "")))
        for f in m.get("files", []) or []:
            out.append("    file: %s" % os.path.join(repo.uploads, f))
        if m.get("slate"):
            out.append("    slate: %s" % m["slate"])
    return "\n".join(out)


def take(repo, before=None):
    """Take every unread line: `(text, lines)`, with `text` "" when there is
    nothing. `before(text)` runs once the text is known and before any line
    is marked read -- the runner writes the message as owed there, so a crash
    between the two loses nothing. Another taker waits on the file lock."""
    path = repo.messages_path
    try:
        fh = open(path, "r+b")
    except OSError:
        return "", []
    with fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            lines = _lines(path)
            picked = [(pos, raw, m) for pos, raw, m in lines
                      if m is not None and not m.get("read")]
            if not picked:
                return "", []
            msgs = [m for _, _, m in picked]
            text = render(msgs, repo)
            if before:
                before(text)
            _mark_read(fh, path, picked)
            return text, msgs
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _mark_read(fh, path, picked):
    patches = []
    for pos, raw, m in picked:
        new = json.dumps(dict(m, read=True)).encode("utf-8")
        if len(new) > len(raw):
            patches = None
            break
        patches.append((pos, new + b" " * (len(raw) - len(new))))
    if patches is not None:
        for pos, new in patches:
            fh.seek(pos)
            fh.write(new)
        fh.flush()
        return
    # A line written more tightly than json.dumps writes it: rewrite the file
    # whole. Rare (every writer here uses json.dumps), and still under the lock.
    taken = set(pos for pos, _, _ in picked)
    fh.seek(0)
    whole = fh.read()
    out, done = [], 0
    for pos, raw, m in _lines(path):
        done = pos + len(raw) + 1
        if pos in taken and m is not None:
            raw = json.dumps(dict(m, read=True)).encode("utf-8")
        out.append(raw + b"\n")
    tail = whole[done:]
    fh.seek(0)
    fh.write(b"".join(out) + tail)
    fh.truncate()
    fh.flush()
