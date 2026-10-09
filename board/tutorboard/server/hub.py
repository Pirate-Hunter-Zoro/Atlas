"""One payload per session, built once, pushed to every browser that has the
board open: in full to a browser that connects, then as deltas.

The payload is the session's and nothing else's: session.json, the newest
WINDOW cards and their ink, the turns, the unread count, the slate, the
drafts, the agent, the write-up's status and the subject's macros; and one
shared key, `relay`, the cluster's health. What the subject holds -- its
problem sets, results, jobs and Colibri -- is `GET /subject.json`
(`subject_info`), fetched when the board opens and when the drawer does. Older cards are `GET /cards?before=<n>` (`older_cards`).

A push after the first payload is a delta:

    {"delta": true, "seq": n, "cards_changed": [card, ...],
     "cards_removed": [id, ...], <every top-level key that changed>: value}

`cards_removed` names cards whose files are gone. A card that only slid out
of the window is not removed: the browser keeps what it has.
"""

import json
import os
import stat
import threading
import time

from .. import assistants, cluster, colibri, coursemacros, fenced, paths
from .. import relay, writeups
from .. import jobs as slurm_jobs
from ..course import config, homework, library
from ..lesson import cards, git, notes, slate, state, turns, uploads

# The payload is rebuilt only when something says it changed: a route's dirty
# mark (`worker.dirty`), a change the sentinel sees in the session files it
# stats every SENTINEL_SECONDS, or SLOW_SECONDS passing, for sources nothing
# marks (the agent record's judgement, built papers).
SENTINEL_SECONDS = 1.0
SLOW_SECONDS = 30.0

# How many of the newest cards a payload carries; `/cards?before=` pages the
# rest, this many at a time.
WINDOW = 40

# Keys of the payload that are carried but never pushed on their own. See `tick`.
QUIET = ("notes", "notes_sent")

# Payload keys whose sources are gone (D27): null until the client code that
# reads them is deleted.
GONE = ("map", "plan", "reading", "direction")


def sentinel(live):
    """The mtime and size of every watched path under `live`, and of each entry
    of a watched directory. Equal answers mean nothing watched changed."""
    out = []
    for rel in paths.SESSION_WATCHED:
        where = os.path.join(live, rel)
        try:
            st = os.stat(where)
        except OSError:
            out.append((rel, None, None))
            continue
        out.append((rel, st.st_mtime_ns, st.st_size))
        if not stat.S_ISDIR(st.st_mode):
            continue
        try:
            entries = list(os.scandir(where))
        except OSError:
            continue
        for e in entries:
            try:
                es = e.stat()
            except OSError:
                continue
            out.append((rel + "/" + e.name, es.st_mtime_ns, es.st_size))
    out.sort(key=lambda t: t[0])
    return out


class Hub:
    """No lock: each subscriber is a (queue, condition) pair, and appending to,
    removing from or copying the list of them is one atomic step."""

    def __init__(self, repo, worker):
        self.repo = repo
        self.worker = worker
        self.clients = []
        self.payload = "{}"
        self.seq = 0
        # What the browsers were last pushed: each top-level key's JSON, and
        # each card's in the window. A delta is the difference from these.
        self.sent = {}
        self.sent_cards = {}
        # Every card id on disk at the last build.
        self.ids = set()
        # Set by `stop`: the session registry dropped this hub, so its loop
        # ends and any stream still on it closes, to reconnect to a new one.
        self.stopped = threading.Event()

    def stop(self):
        self.stopped.set()
        self.worker.dirty.set()

    def subscribe(self):
        client = ([], threading.Condition())
        self.clients.append(client)
        return client

    def unsubscribe(self, client):
        try:
            self.clients.remove(client)
        except ValueError:
            pass

    def build(self):
        """The session's payload. Reads the session directory, the cards in
        the window, the write-up the session pins and the subject's macros;
        nothing walks or globs the subject."""
        repo = self.repo
        jobs = []
        on_board, older, ids = cards.window(repo, jobs, WINDOW)
        if jobs:
            self.worker.submit(jobs)
        self.ids = set(ids)
        board_state = repo.state()
        board_state.setdefault("course", config.read_config(repo.root)["name"])
            # The session's mode; `stance_now` repeats it for the old busy
            # strip.
        board_state["mode"] = config.mode_of(board_state)
        board_state["stance_now"] = board_state["mode"]
        ink, ink_sent = notes.card_ink(repo, [c["id"] for c in on_board])
        data = {
            "state": board_state,
            "cards": on_board,
            # How many cards are older than the window: `/cards?before=`.
            "cards_older": older,
            "turns": turns.load_turns(repo),
            # What is in the inbox that nothing has taken (`notes.waiting`).
            "waiting": notes.waiting(repo),
            "slate": slate.load_slate(repo),
            "text_drafts": notes.load_text_drafts(repo),
            "notes": ink,
            "notes_sent": ink_sent,
            "uploads": uploads.load_uploads(repo),
            "push": state.load_push(repo),
            "export": state.load_export(repo),
            # Which of the session's own documents exist now: its records and
            # a stat each (`state.load_papers`).
            "papers": state.load_papers(repo),
            "agent": state.load_agent(repo),
            # The write-up: the set session.json pins, and documents asked
            # for from this session (`writeups.waiting`).
            "hw": _safe(state.load_hw, repo, board_state),
            "writeups": _safe(writeups.waiting, repo),
            # The subject's macros, so KaTeX matches LaTeX.
            "macros": coursemacros.for_workspace(repo.root),
            # The cluster's health, the same for every session.
            "relay": _safe(relay.health, cluster.atlas_of(repo.root)),
        }
        for key in GONE:
            data[key] = None
        return data

    def poll_loop(self):
        """Rebuild on a dirty mark, a sentinel change, or every SLOW_SECONDS.

        The mark is cleared before the sentinel is read and the sentinel before
        the build, so a change landing mid-build triggers one more pass.
        """
        seen = None
        built = 0.0
        dirty = self.worker.dirty
        while not self.stopped.is_set():
            marked = dirty.is_set()
            if marked:
                dirty.clear()
            now = sentinel(self.repo.live)
            if marked or now != seen or time.monotonic() - built >= SLOW_SECONDS:
                seen = now
                built = time.monotonic()
                try:
                    self.tick()
                except Exception:
                    pass
            dirty.wait(SENTINEL_SECONDS)

    def tick(self):
        """Build the payload, keep it whole for the next browser, and push
        what changed. Ink alone is not pushed: the page that drew it has it."""
        data = self.build()
        window = dict((c["id"], _blob(c)) for c in data["cards"])
        keys = dict((k, _blob(v)) for k, v in data.items() if k != "cards")
        changed = [c for c in data["cards"]
                   if self.sent_cards.get(c["id"]) != window[c["id"]]]
        removed = sorted(i for i in self.sent_cards if i not in self.ids)
        moved = [k for k in keys if self.sent.get(k) != keys[k]]
        if changed or removed or [k for k in moved if k not in QUIET]:
            self.seq += 1
            delta = {"delta": True, "seq": self.seq,
                     "cards_changed": changed, "cards_removed": removed}
            for k in moved:
                delta[k] = data[k]
            self.sent = keys
            self.sent_cards = window
            self.payload = json.dumps(dict(data, seq=self.seq))
            self.push(json.dumps(delta))
        elif moved:
            self.payload = json.dumps(dict(data, seq=self.seq))

    def push(self, payload):
        targets = list(self.clients)
        for q, cv in targets:
            with cv:
                q.append(payload)
                cv.notify()


def _blob(value):
    return json.dumps(value, sort_keys=True)


def _safe(load, *args):
    """`load(*args)`, or None when it raises: one source must not take the
    payload down with it."""
    try:
        return load(*args)
    except Exception:                                        # noqa: BLE001
        return None


def older_cards(repo, worker, before, limit=WINDOW):
    """`GET /cards?before=<n>`: the newest `limit` cards numbered below `n`,
    their ink, and how many are older still."""
    jobs = []
    got, older, _ids = cards.window(repo, jobs, limit, before="%04d" % before)
    if jobs and worker is not None:
        worker.submit(jobs)
    ink, ink_sent = notes.card_ink(repo, [c["id"] for c in got])
    return {"ok": True, "cards": got, "older": older,
            "notes": ink, "notes_sent": ink_sent}


def subject_info(repo):
    """`GET /subject.json`: what the subject holds that a board shows, read
    when asked rather than on every tick. Problem sets, results, running
    jobs and Colibri; and the subject's uncommitted count, the providers
    and the fences, which the save badge and the tutor chooser paint."""
    root = repo.root
    try:
        sets = [{"name": x["name"], "rel": x["rel"]} for x in homework.sets(root)][:60]
    except Exception:                                        # noqa: BLE001
        sets = []
    return {
        "ok": True,
        "sets": sets,
        "results": _safe(library.figures_status, repo),
        "jobs": _safe(slurm_jobs.running, root) or [],
        "colibri": _safe(colibri.status, cluster.atlas_of(root)),
        "unsaved": _safe(git.repo_dirty, repo),
        "assistants": _safe(assistants.listing),
        "fenced": list(_safe(fenced.holds, root) or []),
    }


# ---------------------------------------------------------------------------
# multipart parsing (hand rolled; cgi.FieldStorage is deprecated)
# ---------------------------------------------------------------------------
