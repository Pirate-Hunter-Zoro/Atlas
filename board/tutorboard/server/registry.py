"""The sessions this server is serving: a Repo and a Hub per session, made on
first use and dropped after IDLE_SECONDS without an SSE client.

    Registry(atlas).get(sid)      the Entry for `sid`, or None
    Registry(atlas).subject(id)   a sessionless Repo over a subject, for the
                                  unprefixed subject routes (`?subject=`)
    Registry(atlas).atlas_repo()  a sessionless Repo over the Atlas root, for
                                  the cross-subject routes
    Registry(atlas).sweep()       drop idle entries; `sweep_loop` runs it
    runner_route(subject, line)   hand a line to the tutor of another subject

A SESSIONLESS Repo has no session directory on disk: its `session` is
`sessions/.none`, which `sessions.ID_RE` never matches. Document ink goes to
its root's `.ink/`; a route that would write a card, a turn or an inbox line
refuses it or goes through `runner_route`.

An entry's Repo roots at the session's bound subject, or at the Atlas root
while it is unbound. A bind changes session.json and nothing else, so `get`
re-reads the root on every request and swaps in a new Repo when it moved;
the Hub and its TikZ worker stay, so a stream open on the board survives.
"""

import json
import os
import threading
import time

from .. import sessions, subjects
from ..course import repo as course_repo
from ..lesson import turns
from .hub import Hub
from .tikz import TikzWorker

IDLE_SECONDS = 600.0
SWEEP_SECONDS = 30.0


class Entry(object):
    def __init__(self, sid, repo, hub, worker):
        self.sid = sid
        self.repo = repo
        self.hub = hub
        self.worker = worker
        self.touched = time.monotonic()

    def stop(self):
        self.hub.stop()
        self.worker.stop()


class Registry(object):
    def __init__(self, atlas, start=True):
        self.atlas = os.path.abspath(atlas)
        self.entries = {}
        self.lock = threading.Lock()
        # False in a test that drives `Hub.tick` itself.
        self.start = start

    def get(self, sid):
        """The Entry serving session `sid`, made on first use; None when
        there is no such session (a bad id, or deleted since)."""
        where = sessions.path(sid, self.atlas)
        with self.lock:
            entry = self.entries.get(sid)
            if not where:
                if entry:
                    del self.entries[sid]
                    entry.stop()
                return None
            if entry is None:
                entry = self._make(sid, where)
                self.entries[sid] = entry
            else:
                root = course_repo.stored_root(where)
                if root != entry.repo.root:
                    repo = course_repo.Repo(root, session=where)
                    entry.repo = repo
                    entry.hub.repo = repo
                    entry.worker.repo = repo
                    entry.worker.dirty.set()
            entry.touched = time.monotonic()
            return entry

    def _make(self, sid, where):
        repo = course_repo.Repo(course_repo.stored_root(where), session=where)
        worker = TikzWorker(repo)
        hub = Hub(repo, worker)
        if self.start:
            worker.start()
            try:
                hub.payload = json.dumps(hub.build())
            except Exception:                                # noqa: BLE001
                hub.payload = "{}"
            threading.Thread(target=hub.poll_loop, daemon=True).start()
        return Entry(sid, repo, hub, worker)

    def loaded(self):
        """The ids being served now."""
        return sorted(self.entries)

    def sweep(self, now=None):
        """Drop every entry with no SSE client that nothing has asked for in
        IDLE_SECONDS. Returns the ids dropped."""
        now = time.monotonic() if now is None else now
        gone = []
        with self.lock:
            for sid, entry in list(self.entries.items()):
                if entry.hub.clients:
                    entry.touched = now
                    continue
                if now - entry.touched >= IDLE_SECONDS:
                    del self.entries[sid]
                    entry.stop()
                    gone.append(sid)
        return gone

    def sweep_loop(self):
        while True:
            time.sleep(SWEEP_SECONDS)
            try:
                self.sweep()
            except Exception:                                # noqa: BLE001
                pass

    # -- the unprefixed routes ---------------------------------------------
    def sessionless(self, root):
        """A Repo over `root` with no session: reads, and document ink in
        `<root>/.ink/`. Nothing it is handed may write a session."""
        return sessionless(root, self.atlas)

    def subject(self, ident):
        """A sessionless Repo over the subject `ident` names, or None when it
        names none. An ask from it reaches a session through `runner_route`."""
        found = subjects.find(ident, self.atlas) if ident else None
        return self.sessionless(found["root"]) if found else None

    def atlas_repo(self):
        """A sessionless Repo over the Atlas root, for the cross-subject routes."""
        return self.sessionless(self.atlas)


# The session directory of a sessionless Repo. Never created by a write: a
# route handed one refuses card ink, turns and inbox lines.
NONE = ".none"


def sessionless(root, atlas):
    repo = course_repo.Repo(root, session=os.path.join(sessions.store(atlas), NONE),
                            create=False)
    repo.doc_ink = os.path.join(repo.root, sessions.INK)
    # The one TikZ cache every session shares (`server/tikz.py`).
    repo.tikz = os.path.join(sessions.store(atlas), ".tikz")
    repo.atlas = os.path.abspath(atlas)
    repo.sessionless = True
    return repo


def is_sessionless(repo):
    """Was `repo` made by `sessionless`, i.e. is there no session to write?"""
    return bool(getattr(repo, "sessionless", False))


def base_of(repo):
    """The Atlas root `repo` belongs to: a stored or sessionless Repo knows
    it; any other answers `subjects.root()`."""
    return getattr(repo, "atlas", None) or subjects.root()


def subject_of(repo):
    """The id of the subject `repo` is rooted at, or "" (the Atlas root)."""
    found = subjects.find(repo.root, base_of(repo))
    return found["id"] if found else ""


def newest_open(atlas, subject):
    """The id of the newest open session bound to `subject`, or ""."""
    for rec in sessions.all(atlas):
        if rec.get("subject") == subject and not rec.get("ended"):
            return rec.get("id") or ""
    return ""


def open_bound(atlas, subject, title):
    """A new session bound to `subject`; its id."""
    rec = sessions.new(title, base=atlas)
    where = sessions.path(rec["id"], atlas)
    course_repo.Repo(atlas, session=where, create=False).set_state(subject=subject)
    return rec["id"]


# ---------------------------------------------------------------------------
# the one way into another subject's tutor
# ---------------------------------------------------------------------------
def runner_route(subject, line, base=None, ask="", turn=False, before=None):
    """Hand `line` to the tutor of `subject`. A STUB: T21 replaces it with
    the runner's queue.

    Every route that asks a subject other than its own session's for work --
    a library [revise] or [rework], a meeting deck, a deck from sittings, a
    write-up commissioned from the front door, a mission -- calls this and
    nothing else. The line goes to the newest open session bound to
    `subject`; with none, to a new session bound to it, titled
    `<subject name>: <ask>`.

    `line` is the inbox text, or a record whose `text`, `signal` and other
    keys are kept. Its `id` is the session's next turn id unless it has one.
    `before(repo, id)` runs once the session is chosen and before anything
    is written into it; whatever it raises propagates, and a dict it returns
    is merged into the record. `turn` also writes the record into the
    session's transcript, as the student's.

    Returns {"session": id, "repo": Repo, "id": turn id, "record": record}.
    Raises LookupError when `subject` names no subject.
    """
    from . import spawn                                  # local: spawn is heavy
    base = os.path.abspath(base or subjects.root())
    found = subjects.find(subject, base) if subject else None
    if not found:
        raise LookupError("no subject %r" % (subject,))
    sid = newest_open(base, found["id"])
    if not sid:
        title = "%s: %s" % (found["name"], (ask or "an ask").strip()[:80])
        sid = open_bound(base, found["id"], title)
    repo = sessions.repo(sid, base)
    rec = dict(line) if isinstance(line, dict) else {"text": str(line or "")}
    tid = rec.get("id") or turns.next_turn_id(repo)
    now = time.time()
    record = {"id": tid, "rev": 0, "kind": "text", "answers": None, "t": now,
              "iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
              "from": "student", "text": "", "signal": None, "read": False}
    record.update(rec)
    record["id"] = tid
    if before:
        more = before(repo, tid)
        if isinstance(more, dict):
            record.update(more)
            record["id"] = tid
    if turn:
        record["rev"] = turns.turn_revision(repo, tid)
        turns.write_turn(repo, record)
    os.makedirs(repo.inbox, exist_ok=True)
    with open(repo.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    spawn.wake_tutor(repo)
    return {"session": sid, "repo": repo, "id": tid, "record": record}
