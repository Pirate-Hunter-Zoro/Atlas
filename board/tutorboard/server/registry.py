"""The sessions this server is serving: a Repo and a Hub per session, made on
first use and dropped after IDLE_SECONDS without an SSE client.

    Registry(atlas).get(sid)      the Entry for `sid`, or None
    Registry(atlas).subject(id)   a Repo for a subject, for the unprefixed
                                  library routes (`?subject=`)
    Registry(atlas).sweep()       drop idle entries; `sweep_loop` runs it

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

    # -- the unprefixed library ---------------------------------------------
    def subject(self, ident, create=False, title=None):
        """A Repo for the subject `ident` names, or None when it names none.

        The newest open session bound to it serves, so ink and asks land
        where that session sees them. With none: `create` makes one, bound to
        it (an ask from the library is the owner asking); otherwise a Repo
        over the subject with no session directory on disk, for reads only.
        """
        found = subjects.find(ident, self.atlas) if ident else None
        if not found:
            return None
        sid = newest_open(self.atlas, found["id"])
        if not sid and create:
            sid = open_bound(self.atlas, found["id"],
                             title or "%s: library" % found["name"])
        if sid:
            entry = self.get(sid)
            if entry:
                return entry.repo
        none = os.path.join(sessions.store(self.atlas), ".none")
        repo = course_repo.Repo(found["root"], session=none, create=False)
        repo.doc_ink = os.path.join(repo.root, ".ink")
        return repo


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
