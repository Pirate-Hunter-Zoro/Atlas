"""cluster.py -- where what the cluster says lands on the Mac, and the ear
that hears it.

    wake(subject, session, line)   the one door for a cluster line
    notices(atlas)                 the lines no session took, newest first
    atlas_of(subject)              the Atlas root holding a subject
    Ear(atlas)                     the server's cluster thread

`wake` is how a job's ending (`jobs.drop`) and a held step's check
(`holds.wake`) reach the Mac (D16):

  * `session` names a stored session: it is reopened if ended, the line is
    appended to its inbox, and the server's runner queues a turn for it.
  * no session, or one that no longer exists: the line is appended to
    `sessions/.notices.jsonl` and no turn starts. `/notices.json` serves it.

`wake=False` writes the line `"wake": false`: it queues nothing, and the
session's next turn takes it with the rest.

THE EAR runs inside `serve.py` only with `TUTORBOARD_CLUSTER=1`. Every `EVERY`
seconds it asks origin for `main` and `refs/heads/code/*` with one
`git ls-remote` (no prompt, `LS_TIMEOUT` seconds). It pulls through
`gitops.pull` only when origin's main is a commit HEAD does not contain, and
records a failed ls-remote or pull in `<state>/pull.json`. Then it hears every
subject: `jobs.hear` and `holds.wake`, each of which wakes through `wake`.
The code refs are kept on the ear (`code`); hearing them is T38b's.

Runs on the cluster's python3 too (jobs and holds import it): no walrus, no
`match`. The runner is reached through `sys.modules`, never imported, so the
cluster never loads it.
"""

import hashlib
import json
import os
import sys
import threading
import time

from . import subjects

# The ear's cadence, and how long one ls-remote may take.
EVERY = 20
LS_TIMEOUT = 10
# The pull's own bound, once the ear has decided to pull.
PULL_TIMEOUT = 60

STORE = "sessions"
NOTICES = ".notices.jsonl"
# The newest notices `/notices.json` serves.
NOTICES_SERVED = 100
PULL_STATE = "pull.json"


def atlas_of(subject):
    """The Atlas root holding `subject`: the parent of its `courses/` or
    `projects/` (or a legacy parent), else `subject` itself -- the Atlas root
    an unbound session's Repo names, or a tree that stands alone."""
    subject = os.path.abspath(subject)
    parent = os.path.dirname(subject)
    known = [d for d, _ in subjects.DIRS] + list(subjects.LEGACY)
    if os.path.basename(parent) in known:
        return os.path.dirname(parent)
    return subject


def _subject_id(atlas, subject):
    rel = os.path.relpath(os.path.abspath(subject), atlas).replace(os.sep, "/")
    return None if rel == "." else rel


def notices_path(atlas):
    return os.path.join(atlas, STORE, NOTICES)


def notices(atlas, limit=NOTICES_SERVED):
    """The notices under `atlas`, newest first, at most `limit` (0: all)."""
    try:
        with open(notices_path(atlas), "r", encoding="utf-8") as fh:
            raw = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for line in raw:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    out.reverse()
    return out[:limit] if limit else out


def _append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def _notice(atlas, subject, session, line, signal, request, now):
    text = str(line)
    rec = {"id": "%d-%s" % (int(now * 1000), hashlib.sha1(
               text.encode("utf-8")).hexdigest()[:8]),
           "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S",
                                          time.localtime(now)),
           "subject": _subject_id(atlas, subject), "session": session,
           "signal": signal, "text": text}
    if request:
        rec["request"] = str(request)
    _append(notices_path(atlas), rec)
    return dict(rec, notice=True)


def _queue(atlas, sid):
    """Queue a turn for `sid` on this process's runner, where one runs over
    `atlas`. False where none does (a CLI, the cluster, a test)."""
    service = sys.modules.get("tutorboard.runner.service")
    runner = getattr(service, "RUNNER", None)
    if runner is None:
        return False
    if os.path.realpath(runner.atlas) != os.path.realpath(atlas):
        return False
    return runner.wake(sid)


def wake(subject, session, line, wake=True, signal="job", request=None,
         now=None):
    """Deliver one machinery line about `subject` (its root). The line, with
    `session` set where a session took it and `notice` where none did.

    `line` is the text. `signal` is how `turn_signal` reads it (`job`,
    `repair`, `coach`); `request` is a relay request id, so `board brief`
    can name it; `session` is the session id the request was filed from, or
    None.
    """
    from . import sessions
    from .lesson import turns
    now = float(now or time.time())
    atlas = atlas_of(subject)
    sid = str(session or "").strip() or None
    if not sid or not sessions.path(sid, atlas):
        return _notice(atlas, subject, sid, line, signal, request, now)
    sessions.reopen(sid, base=atlas)
    target = sessions.repo(sid, atlas)
    os.makedirs(target.inbox, exist_ok=True)
    msg = {
        # From the lesson's own id series, and NOT in `turns.jsonl`: the
        # machinery is reporting, nobody said anything.
        "id": turns.next_turn_id(target), "rev": 0, "kind": "text",
        "answers": None, "t": now,
        "iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "from": "student", "text": str(line), "signal": signal,
        "read": False, "session": sid,
    }
    if not wake:
        msg["wake"] = False
    if request:
        msg["request"] = str(request)
    _append(target.messages_path, msg)
    if wake:
        _queue(atlas, sid)
    return msg


# ---------------------------------------------------------------------------
# the ear: the server's cluster thread
# ---------------------------------------------------------------------------
class Ear(object):
    """One per server, with `TUTORBOARD_CLUSTER=1`. `start()` runs it on a
    daemon thread until `stop()`; `once()` is one pass."""

    def __init__(self, atlas, every=EVERY, state_dir=None, say=None):
        from . import paths
        self.atlas = os.path.abspath(atlas)
        self.every = every
        self.state = os.path.join(state_dir or paths.STATE_DIR, PULL_STATE)
        self.say = say or (lambda msg: sys.stderr.write(msg + "\n"))
        self.main = None          # origin's main at the last ls-remote
        self.code = {}            # refs/heads/code/<id> -> sha (T38b hears them)
        self.pulls = 0
        self._last = None         # (key, record) pull.json holds now
        self._stop = threading.Event()

    # -- git ---------------------------------------------------------------
    def ls_remote(self):
        """`(main, code, error)`: origin's main sha (None when it has none),
        `{ref: sha}` for its code refs, and the reason when the ask failed."""
        from . import gitops
        code, out = gitops._git(self.atlas, "ls-remote", "origin",
                                "refs/heads/main", "refs/heads/code/*",
                                timeout=LS_TIMEOUT)
        if code != 0:
            last = out.splitlines()
            return None, {}, (last[-1] if last
                              else "ls-remote failed (%d)" % code)
        main, refs = None, {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            sha, ref = parts
            if ref == "refs/heads/main":
                main = sha
            elif ref.startswith("refs/heads/code/"):
                refs[ref] = sha
        return main, refs, None

    def contains(self, sha):
        """Does HEAD here already contain commit `sha`? False when the
        commit is not here at all."""
        from . import gitops
        code, _ = gitops._git(self.atlas, "merge-base", "--is-ancestor", sha,
                              "HEAD")
        return code == 0

    def _head(self):
        from . import gitops
        code, out = gitops._git(self.atlas, "rev-parse", "HEAD")
        return out if code == 0 else None

    def _record(self, ok, step, said, remote=None):
        """Write pull.json when what it says changes. True when written."""
        key = (ok, step, said, remote if step == "pull" else None)
        if self._last is not None and self._last[0] == key:
            return False
        now = time.time()
        rec = {"ok": ok, "step": step, "said": said, "remote": remote,
               "head": self._head(), "t": now,
               "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))}
        try:
            os.makedirs(os.path.dirname(self.state), exist_ok=True)
            tmp = "%s.%d" % (self.state, os.getpid())
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=1)
            os.replace(tmp, self.state)
        except OSError:
            return False
        self._last = (key, rec)
        return True

    # -- one pass ------------------------------------------------------------
    def once(self):
        """Ask origin, pull when its main is new here, then hear every
        subject. `{"pulled": True|False|None, "heard": [...]}`; `pulled` is
        None when the ls-remote failed, False when no pull ran or it failed."""
        from . import gitops
        main, refs, error = self.ls_remote()
        pulled = None
        if error:
            if self._record(False, "ls-remote", error):
                self.say("cluster: origin did not answer: %s" % error)
        else:
            self.main, self.code = main, refs
            pulled = False
            # ai-config is ignored by Atlas, so a pull never brings it back.
            gitops.adopt_private(self.atlas)
            if main and not self.contains(main):
                said = []
                ok = gitops.pull(self.atlas, quiet=True, timeout=PULL_TIMEOUT,
                                 say=said.append)
                self.pulls += 1
                pulled = ok is True
                why = said[-1] if said else "pull refused"
                # Said once per new failure, not every pass it repeats.
                if self._record(pulled, "pull", "" if pulled else why,
                                remote=main) and not pulled:
                    self.say("cluster: the pull of %s failed: %s"
                             % (main[:12], why))
            elif self._last is not None and not self._last[0][0]:
                # The remote answers again after a failure.
                self._record(True, "ls-remote", "", remote=main)
        return {"pulled": pulled, "heard": self.hear()}

    def hear(self):
        """Every subject's ended reports and held steps, each woken through
        `wake`. The records heard."""
        from . import holds, jobs
        out = []
        for _parent, _kind, _slug, root in subjects.walk(self.atlas):
            out.extend(jobs.hear(root))
            try:
                out.extend(holds.wake(root))
            except Exception:                                # noqa: BLE001
                continue
        return out

    # -- the thread --------------------------------------------------------
    def run(self):
        while not self._stop.is_set():
            try:
                got = self.once()
                for rec in got["heard"]:
                    self.say("cluster: heard %s (%s)" % (
                        rec.get("request") or rec.get("id") or "?",
                        str(rec.get("state") or "coach").lower()))
            except Exception as exc:                         # noqa: BLE001
                self.say("cluster: a pass failed: %r" % (exc,))
            self._stop.wait(self.every)

    def stop(self):
        self._stop.set()

    def start(self):
        t = threading.Thread(target=self.run, name="cluster", daemon=True)
        t.start()
        return t
