"""cluster.py -- where what the cluster says lands on the Mac, and the ear
that hears it.

    wake(subject, session, line)   the one door for a cluster line
    notices(atlas)                 the lines no session took, newest first
    atlas_of(subject)              the Atlas root holding a subject
    Ear(atlas)                     the server's cluster thread

`wake` is how a job's ending reaches the Mac (D16): with a stored session,
reopen it if ended, append to its inbox and queue a turn; with none, or a
gone one, append to `sessions/.notices.jsonl` and start nothing. `wake=False`
writes a non-waking line.

The ear runs in `serve.py` only with `TUTORBOARD_CLUSTER=1`: every `EVERY`
seconds one `git ls-remote` for `main` and `refs/heads/code/*`, a pull
(`gitops.pull`) only when origin's main is new here, failures recorded in
`<state>/pull.json`, then `jobs.hear` for every subject. ai-config, its own
repository, is fast-forwarded every few minutes and relinked when it moved
(`gitops.sync_private`). A moved code ref is
fetched and recorded in session.json `code`; a step wakes the session with
`[code] step N: ...` and brings unchanged held files to the new tip; a
deleted ref releases them with a non-waking `[unheld]` line.

The constraint: this runs on the cluster's python3 too (jobs imports it), so
no walrus or `match`, and the runner is reached through `sys.modules`, never
imported.
"""

import hashlib
import json
import os
import sys
import threading
import time

from . import fenced, subjects

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
CODE_PREFIX = "refs/heads/code/"


def atlas_of(subject):
    """The Atlas root holding `subject`: the parent of its `courses/` or
    `projects/`, else `subject` itself -- the Atlas root an unbound
    session's Repo names, or a tree that stands alone."""
    subject = os.path.abspath(subject)
    parent = os.path.dirname(subject)
    if os.path.basename(parent) in dict(subjects.DIRS):
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
    """Deliver one machinery line about `subject` (its root); returns the
    line with `session` or `notice` set. `signal` is how `turn_signal` reads
    it; `request` a relay request id for `board brief`."""
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
        # From the lesson's id series, not in `turns.jsonl`: nobody spoke.
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
        self.code = {}            # refs/heads/code/<id> -> sha, at the last ls-remote
        self._noticed = {}        # code refs heard for no session here
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
        heard_code = []
        if not error:
            self.main, self.code = main, refs
            pulled = False
            # Before the pull: a released session's held files go back as
            # HEAD has them, so main's --end commit fast-forwards over them.
            try:
                heard_code = self.hear_code(refs)
            except Exception as exc:                         # noqa: BLE001
                self.say("cluster: hearing the code refs failed: %r" % (exc,))
            # ai-config is ignored by Atlas, so a pull never brings it back,
            # and never moves it forward either: that is sync_private's, on
            # its own slower clock.
            gitops.adopt_private(self.atlas)
            try:
                gitops.sync_private(self.atlas, os.path.dirname(self.state),
                                    say=self.say)
            except Exception as exc:                         # noqa: BLE001
                self.say("cluster: moving ai-config forward failed: %r" % (exc,))
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
        return {"pulled": pulled, "heard": heard_code + self.hear()}

    # -- coding sessions at the cluster ------------------------------------
    def hear_code(self, refs):
        """Hear `refs` (`{ref: sha}`, every `refs/heads/code/*` origin has):
        a moved one is fetched, recorded and woken; a session whose ref is
        gone is released. The records heard."""
        from . import code as coding, sessions
        held = sessions.coding(self.atlas)
        out = []
        for ref_name, sha in sorted(refs.items()):
            sid = ref_name[len(CODE_PREFIX):]
            if not coding.SESSION_RE.match(sid):
                continue
            old = held.get(sid)
            if old is not None and old.get("sha") == sha:
                continue
            if old is None and self._noticed.get(ref_name) == sha:
                continue
            got = self.hear_step(sid, sha, old)
            if got:
                out.append(got)
        for sid, old in sorted(held.items()):
            if old.get("ref") not in refs:
                out.append(self.release(sid, old))
        return out

    def _fetch(self, sid):
        from . import code as coding, gitops
        code, out = gitops._git(self.atlas, "fetch", "--quiet", "origin",
                                "+%s:%s" % (coding.ref(sid), coding.tracking(sid)),
                                timeout=gitops.NET_TIMEOUT)
        return "" if code == 0 else ((out.splitlines() or ["fetch failed"])[-1])

    def hear_step(self, sid, sha, old):
        """Take `sha`, the new tip of `code/<sid>`. The line woken or noticed,
        `{}` when the commit wakes nothing, None when it could not be read."""
        from . import code as coding, gitops, sessions
        err = self._fetch(sid)
        if err:
            self.say("cluster: could not fetch code/%s: %s" % (sid, err))
            return None
        said = coding.step_of(self.atlas, sha)
        old = old or {}
        subject = said["subject"] or old.get("subject") or ""
        if coding.subject_of(subject + "/x") != subject:
            subject = ""
        paths = [p for p in (said["paths"] or old.get("paths") or [])
                 if subject and coding.subject_of(p) == subject and p != subject
                 and ".." not in p.split("/") and not fenced.in_fence(p)]
        prev = old.get("sha") or ""
        if not prev or not self._ancestor(prev, sha):
            code, parent = gitops._git(self.atlas, "rev-parse", "--verify",
                                       "--quiet", sha + "^")
            prev = parent if code == 0 else ""
        line = "[code] step %d: %s" % (said["step"], said["title"])
        if not sessions.path(sid, self.atlas):
            if not said["step"]:
                self._noticed[CODE_PREFIX + sid] = sha
                return {}
            text = "%s (code/%s at %s; no session %s here)" % (
                line, sid, sha[:12], sid)
            self._noticed[CODE_PREFIX + sid] = sha
            if any(n.get("text") == text for n in notices(self.atlas, 0)):
                return {}
            root = os.path.join(self.atlas, subject) if subject else self.atlas
            return wake(root, sid, text, signal="code")
        seen, note = self._bring(old, sha, paths)
        rec = {"ref": coding.ref(sid), "sha": sha, "paths": paths,
               "step": said["step"] or int(old.get("step") or 0),
               "subject": subject, "prev": prev, "seen": seen,
               "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        sessions.set_code(sid, rec, base=self.atlas)
        if not said["step"]:
            return {}
        rng = "%s..%s" % (prev[:12], sha[:12]) if prev else sha[:12]
        text = ("%s\ncode/%s moved to %s. Read the change yourself: "
                "`git diff %s -- %s`; the step's check is in `git log -1 %s`.%s"
                % (line, sid, sha[:12], rng, " ".join(paths) or ".",
                   sha[:12], note))
        root = os.path.join(self.atlas, subject) if subject else self.atlas
        return wake(root, sid, text, signal="code")

    def _ancestor(self, a, b):
        from . import gitops
        return gitops._git(self.atlas, "merge-base", "--is-ancestor", a, b)[0] == 0

    def _since(self, old):
        """The commit this working tree's held files were last brought to:
        `seen`, else HEAD."""
        return old.get("seen") or self._head() or ""

    def _bring(self, old, sha, paths):
        """Bring the held files here to `sha` when nobody changed them since
        `seen`. `(seen, note)`: the commit they now hold, and a sentence when
        they were left."""
        from . import code as coding
        since = self._since(old)
        if not paths or not since:
            return old.get("seen") or "", ""
        mine = coding.edited(self.atlas, since, paths)
        if mine is None:
            return old.get("seen") or "", ""
        if mine:
            return old.get("seen") or "", (
                " The held files here were left as they are: this checkout "
                "changed %s since %s." % (", ".join(mine[:6]), since[:12]))
        err = coding.apply(self.atlas, since, sha, paths)
        if err:
            return old.get("seen") or "", " The held files here were not " \
                "brought to it: %s." % err
        return sha, ""

    def release(self, sid, old):
        """`code/<sid>` is gone from origin: put the held files back as HEAD
        has them (unless this checkout changed them since `seen`), clear
        `code`, and say so with a non-waking line."""
        from . import code as coding, sessions
        paths = list(old.get("paths") or [])
        note = ""
        seen = old.get("seen") or ""
        head = self._head() or ""
        if seen and paths and head:
            mine = coding.edited(self.atlas, seen, paths)
            if mine:
                note = (" The held files here were left as they are: this "
                        "checkout changed %s." % ", ".join(mine[:6]))
            elif mine is not None:
                err = coding.apply(self.atlas, seen, head, paths)
                note = (" The held files here are back as HEAD has them; a "
                        "pull brings main's." if not err else
                        " The held files here were not put back: %s." % err)
        sessions.set_code(sid, None, base=self.atlas)
        where = sessions.path(sid, self.atlas)
        text = ("[unheld] code/%s is gone from origin: the coding session at "
                "the cluster ended or was abandoned.%s" % (sid, note))
        if where:
            sessions._line(where, text, "unheld", ref=old.get("ref"))
        return {"session": sid, "id": old.get("ref"), "state": "unheld",
                "text": text}

    def hear(self):
        """Every subject's ended reports, each woken through `wake`. The
        records heard."""
        from . import jobs
        out = []
        for _parent, _kind, _slug, root in subjects.walk(self.atlas):
            out.extend(jobs.hear(root))
        return out

    # -- the thread --------------------------------------------------------
    def run(self):
        while not self._stop.is_set():
            try:
                got = self.once()
                for rec in got["heard"]:
                    self.say("cluster: heard %s (%s)" % (
                        rec.get("request") or rec.get("session")
                        or rec.get("id") or "?",
                        str(rec.get("state") or rec.get("signal")
                            or "?").lower()))
            except Exception as exc:                         # noqa: BLE001
                self.say("cluster: a pass failed: %r" % (exc,))
            self._stop.wait(self.every)

    def stop(self):
        self._stop.set()

    def start(self):
        t = threading.Thread(target=self.run, name="cluster", daemon=True)
        t.start()
        return t
