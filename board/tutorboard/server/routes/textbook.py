"""A course's textbook: an upload filed into textbook/ and indexed.

    POST /textbook {upload}   session   one upload in the session's uploads/,
                                        filed into the bound course's
                                        textbook/ and indexed (`course/book.py`)
                                        on the one Ingester thread; progress in
                                        textbook/ingest.json, and a waking
                                        `[textbook]` line when it ends
    GET  /textbook.json       subject   `book.status`: the PDF, the index's
                                        counts and doubts, the last run

Refused: a session bound to no course, a second, different PDF, and a run
already going for that course. The same PDF again is not a second one.
"""

import json
import os
import threading

from . import NOT_MINE
from ..registry import is_sessionless
from ... import sessions, subjects, sync
from ...course import book


def get(h, repo, path):
    if path == "/textbook.json":
        root = repo.root
        found = subjects.find(root, getattr(repo, "atlas", None))
        out = book.status(root) if found else {"ok": True, "pdfs": [],
                                               "indexed": False}
        out["course"] = bool(found and found["kind"] == "course")
        out["running"] = ingester().running(root)
        return h.send_json(out)
    return NOT_MINE


def post(h, repo, path):
    if path == "/textbook":
        return start(h, repo)
    return NOT_MINE


def start(h, repo):
    """`POST /textbook {upload}`: file the upload, then index it on the
    Ingester. 400 in its own words; 409 for a second book or a run going."""
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:                                        # noqa: BLE001
        payload = None
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    if is_sessionless(repo) or not getattr(repo, "stored", False):
        return h.send_json({"ok": False, "error": "a textbook arrives in a "
                            "session: /s/<id>/textbook"}, status=400)
    sid = os.path.basename(repo.live)
    base = os.path.dirname(os.path.dirname(repo.live))
    rec = sessions.get(sid, base) or {}
    found = subjects.find(rec.get("subject"), base) if rec.get("subject") else None
    if not found or found["kind"] != "course":
        return h.send_json({"ok": False, "error": "a textbook belongs to a "
                            "course: bind this session to one first"}, status=400)
    root = found["root"]
    work = ingester()
    # The course is claimed before anything is filed, so a second request
    # racing this one is refused rather than filing a second PDF.
    if not work.claim(root):
        return h.send_json({"ok": False, "error": "this course's textbook is "
                            "already being indexed"}, status=409)
    try:
        src = sessions._upload(sessions.path(sid, base), payload.get("upload"))
        pdf = book.file_upload(root, src)
    except sessions.Refused as exc:
        work.release(root)
        return h.send_json({"ok": False, "error": str(exc)}, status=400)
    except book.Refused as exc:
        work.release(root)
        return h.send_json({"ok": False, "error": str(exc)}, status=409)
    except Exception:
        work.release(root)
        raise
    work.enqueue(root, sid)
    h.note("textbook %s -> %s, indexing" % (os.path.basename(pdf), found["id"]))
    h.hub.worker.dirty.set()
    return h.send_json({"ok": True, "subject": found["id"],
                        "pdf": os.path.basename(pdf), "started": True})


# ---------------------------------------------------------------------------
# the one ingester
# ---------------------------------------------------------------------------
class Ingester(threading.Thread):
    """Indexes queued textbooks one at a time, then wakes the session that
    asked with a `[textbook]` line: counts and doubts, or what failed."""

    daemon = True

    def __init__(self, run=None, wake=None):
        threading.Thread.__init__(self, name="textbook")
        self.cv = threading.Condition()
        self.queue = []
        self.busy = set()
        self.run_one = run or (lambda root: book.ingest(root))
        self.wake = wake or (lambda root, sid, line: sync.wake(
            root, sid, line, signal="textbook"))

    def running(self, root):
        with self.cv:
            return os.path.realpath(root) in self.busy

    def claim(self, root):
        """Mark `root` busy; False where it already is."""
        with self.cv:
            real = os.path.realpath(root)
            if real in self.busy:
                return False
            self.busy.add(real)
            return True

    def release(self, root):
        """Give up a claim that will not be queued."""
        with self.cv:
            self.busy.discard(os.path.realpath(root))

    def enqueue(self, root, sid):
        """Queue a claimed `root`."""
        with self.cv:
            self.queue.append((os.path.realpath(root), sid))
            self.cv.notify()

    def submit(self, root, sid):
        """Claim and queue `root`; False where it is already going."""
        if not self.claim(root):
            return False
        self.enqueue(root, sid)
        return True

    def run(self):
        while True:
            with self.cv:
                while not self.queue:
                    self.cv.wait()
                root, sid = self.queue.pop(0)
            name = ", ".join(os.path.basename(p) for p in book.pdfs(root)) or None
            try:
                line = book.line_for(root, report=self.run_one(root))
            except Exception as exc:          # never let the worker die  # noqa: BLE001
                line = book.line_for(root, error=str(exc) or type(exc).__name__,
                                     name=name)
            try:
                self.wake(root, sid, line)
            except Exception:                                # noqa: BLE001
                pass
            with self.cv:
                self.busy.discard(root)


_INGESTER = None
_INGESTER_LOCK = threading.Lock()


def ingester():
    """The process's one Ingester, started on first use."""
    global _INGESTER
    with _INGESTER_LOCK:
        if _INGESTER is None:
            _INGESTER = Ingester()
            _INGESTER.start()
        return _INGESTER
