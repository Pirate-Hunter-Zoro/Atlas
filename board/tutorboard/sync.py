"""sync.py -- the Mac's git sync, and where what reaches it lands.

    wake(subject, session, line)   the one door for a machinery line
    notices(atlas)                 the lines no session took, newest first
    atlas_of(subject)              the Atlas root holding a subject
    health(atlas)                  the not-synced and brew lines, GET /sync.json
    Sync(atlas)                    the server's sync thread

`wake` is how a coding step reaches the Mac (D16): with a
stored session, reopen it if ended, append to its inbox and queue a turn;
with none, or a gone one, append to `sessions/.notices.jsonl` and start
nothing. `wake=False` writes a non-waking line.

The thread runs in `serve.py` only with `TUTORBOARD_SYNC=1`: every `EVERY`
seconds one `git ls-remote` for `main` and `refs/heads/code/*`. When origin's
main is new here it is pulled fast-forward; when HEAD is ahead of it too (a
local End commit beside a laptop's `--end`), it is merged (`gitops.merge_in`)
and pushed, so the two never diverge. The merge waits while anything is
staged (`skipped: staged changes`), and while HEAD holds unpushed commits the
board did not make (`skipped: unpushed commits of your own`): origin is
public, and those are the owner's to push. Every outcome is recorded in
`<state>/pull.json`, which `health` reads. ai-config, its own repository, is
fast-forwarded every few minutes and relinked when it moved
(`gitops.sync_private`). A moved code ref is
fetched and recorded in session.json `code`; a step wakes the session with
`[code] step N: ...` and brings unchanged held files to the new tip; a
deleted ref releases them with a non-waking `[unheld]` line. A Mac-local
session's `refs/heads/code/*` is listed here too, every pass and without the
network, and recorded with `local`; its files are this working tree's own, so
nothing is brought or put back, and the thread never releases it (`board code
--end` and `--abandon` clear `code` themselves; a record whose local ref is
gone is dropped and nothing moves). Only a ref whose registration here says
`local` is one: a branch checked out from origin's ref is not. A step the
tutor's own turn made (`by: tutor`) is recorded with a non-waking
`[stepped]` line, so an edit in do mode never wakes a turn of its own.

The runner is reached through `sys.modules`, never imported.
"""

import hashlib
import json
import os
import sys
import threading
import time

from . import subjects

# The thread's cadence, and how long one ls-remote may take.
EVERY = 20
LS_TIMEOUT = 10
# The pull's own bound, once the thread has decided to pull.
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
    `atlas`. False where none does (a CLI, a test)."""
    service = sys.modules.get("tutorboard.runner.service")
    runner = getattr(service, "RUNNER", None)
    if runner is None:
        return False
    if os.path.realpath(runner.atlas) != os.path.realpath(atlas):
        return False
    return runner.wake(sid)


def wake(subject, session, line, wake=True, signal="code", request=None,
         now=None):
    """Deliver one machinery line about `subject` (its root); returns the
    line with `session` or `notice` set. `signal` is how `turn_signal` reads
    it; `request` an id the line is about."""
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
# the health: GET /sync.json, home's #health and the board's #healthbar
# ---------------------------------------------------------------------------
HEALTH_TTL = 20.0
_HEALTH = {}


def forget():
    """Drop the cached health, so the next ask reads pull.json again."""
    _HEALTH.clear()


def pull_health(state_dir=None):
    """pull.json as the Mac's health: `{ok, said, step, at}`, `said` being
    "not synced: <git's words>" when the last pull, merge or ls-remote
    failed or was skipped; None where the sync thread has written none."""
    from . import paths
    path = os.path.join(state_dir or paths.STATE_DIR, PULL_STATE)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict):
        return None
    if rec.get("ok") is not False:
        return {"ok": True, "said": "", "step": rec.get("step"),
                "at": rec.get("at")}
    said = str(rec.get("said") or "the %s failed" % (rec.get("step") or "pull"))
    if not said.startswith("not synced"):
        said = "not synced: " + said
    return {"ok": False, "said": said[:400], "step": rec.get("step"),
            "at": rec.get("at")}


def health(atlas, state_dir=None, brew=True, fresh=False):
    """The Mac's sync health: `{ok, synced, down, pull, lines}`. `lines` are
    the sentences to show, worst first, `[]` when all is well: the not-synced
    line, then (with `brew`) the machine's `brew:` and `tools:` lines
    (`brewcare.lines`). The board's payload asks without `brew`, so a lesson
    shows only what stops its work reaching origin."""
    from . import brewcare
    key = (os.path.realpath(atlas), state_dir, bool(brew))
    t = time.time()
    hit = _HEALTH.get(key)
    if not fresh and hit and t - hit[0] < HEALTH_TTL:
        return json.loads(hit[1])
    pull = pull_health(state_dir)
    synced = not (pull and not pull["ok"])
    lines = [] if synced else [pull["said"]]
    if brew:
        lines += brewcare.lines(state_dir)
    out = {"ok": True, "synced": synced, "down": not synced, "pull": pull,
           "lines": lines}
    _HEALTH[key] = (t, json.dumps(out))
    return out


# ---------------------------------------------------------------------------
# the server's sync thread
# ---------------------------------------------------------------------------
class Sync(object):
    """One per server, with `TUTORBOARD_SYNC=1`. `start()` runs it on a
    daemon thread until `stop()`; `once()` is one pass."""

    def __init__(self, atlas, every=EVERY, state_dir=None, say=None):
        from . import paths
        self.atlas = os.path.abspath(atlas)
        self.every = every
        self.state = os.path.join(state_dir or paths.STATE_DIR, PULL_STATE)
        self.say = say or (lambda msg: sys.stderr.write(msg + "\n"))
        self.main = None          # origin's main at the last ls-remote
        self.code = {}            # refs/heads/code/<id> -> sha, at the last ls-remote
        self.local = {}           # refs/heads/code/<id> -> sha this checkout keeps
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
            return None, {}, gitops.why(out, "ls-remote failed (%d)" % code)
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

    def local_refs(self):
        """`{ref: sha}` for the `refs/heads/code/*` this checkout keeps
        itself: Mac-local coding sessions, never pushed, each with a
        registration here that says `local`. No network. None when git
        cannot say."""
        from . import code as coding, gitops
        code, out = gitops._git(self.atlas, "for-each-ref",
                                "--format=%(objectname) %(refname)",
                                CODE_PREFIX.rstrip("/"))
        if code != 0:
            return None
        refs = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) != 2 or not parts[1].startswith(CODE_PREFIX):
                continue
            # A branch made from origin's ref (`git checkout code/<id>`) is
            # not the session's: origin's is.
            rec = coding.read(parts[1][len(CODE_PREFIX):], self.atlas)
            if rec and rec.get("local"):
                refs[parts[1]] = parts[0]
        return refs

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
        key = (ok, step, said,
               remote if step in ("pull", "merge", "push") else None)
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
        """Ask origin; when its main is new here, pull it, or merge it and
        push where HEAD is ahead too; the code refs are heard first.
        `{"pulled": True|False|None, "heard": [...]}`; `pulled` is None when
        the ls-remote failed, False when nothing came in or it failed."""
        from . import gitops
        main, refs, error = self.ls_remote()
        pulled = None
        if error:
            if self._record(False, "ls-remote", error):
                self.say("sync: origin did not answer: %s" % error)
        else:
            self.main, self.code = main, refs
            pulled = False
        local = self.local_refs()
        if local is not None:
            self.local = local
        # Before the pull: a released session's held files go back as HEAD
        # has them, so main's --end commit fast-forwards over them. Local
        # refs are heard with origin silent too.
        heard_code = []
        try:
            heard_code = self.hear_code(None if error else refs, local)
        except Exception as exc:                             # noqa: BLE001
            self.say("sync: hearing the code refs failed: %r" % (exc,))
        if not error:
            # ai-config is ignored by Atlas, so a pull never brings it back,
            # and never moves it forward either: that is sync_private's, on
            # its own slower clock.
            gitops.adopt_private(self.atlas)
            try:
                gitops.sync_private(self.atlas, os.path.dirname(self.state),
                                    say=self.say)
            except Exception as exc:                         # noqa: BLE001
                self.say("sync: moving ai-config forward failed: %r" % (exc,))
            if main and not self.contains(main) and self._ahead_of(main):
                pulled = self._merge(main)
            elif main and not self.contains(main):
                said = []
                ok = gitops.pull(self.atlas, quiet=True, timeout=PULL_TIMEOUT,
                                 say=said.append)
                self.pulls += 1
                pulled = ok is True
                why = said[-1] if said else "pull refused"
                # Said once per new failure, not every pass it repeats.
                if self._record(pulled, "pull", "" if pulled else why,
                                remote=main) and not pulled:
                    self.say("sync: the pull of %s failed: %s"
                             % (main[:12], why))
            elif self._last is not None and not self._last[0][0] \
                    and self._last[0][1] == "push":
                # A merge this thread made, not pushed yet.
                self._push(main)
            elif self._last is not None and not self._last[0][0]:
                # The remote answers again after a failure.
                self._record(True, "ls-remote", "", remote=main)
        forget()
        return {"pulled": pulled, "heard": heard_code}

    def _ahead_of(self, main):
        """Is HEAD, on main tracking origin's main (all a board push
        publishes), ahead of origin's `main` as well as behind it? Fetches
        origin's main first. False when git cannot say, and the fast-forward
        pull then says why."""
        from . import gitops
        code, branch = gitops._git(self.atlas, "symbolic-ref", "--quiet",
                                   "--short", "HEAD")
        if code != 0 or branch != gitops.MAIN:
            return False
        code, up = gitops._git(self.atlas, "rev-parse", "--abbrev-ref",
                               "@{upstream}")
        if code != 0 or up != "origin/" + gitops.MAIN:
            return False
        code, _ = gitops._git(self.atlas, "fetch", "--quiet", "origin",
                              gitops.MAIN, timeout=PULL_TIMEOUT)
        if code != 0:
            return False
        if gitops._git(self.atlas, "cat-file", "-e",
                       main + "^{commit}")[0] != 0:
            return False
        return not self._ancestor("HEAD", main)

    def _merge(self, main):
        """Merge origin's `main` into a HEAD ahead of it, then push. True when
        HEAD now holds origin's main. Nothing is merged while anything is
        staged or while HEAD holds unpushed commits the board did not make
        (`gitops.foreign`), and git refuses an overlap with uncommitted
        work: each is recorded in pull.json and changes nothing here."""
        from . import gitops
        self.pulls += 1
        mine = gitops.foreign(self.atlas, main)
        if mine is None:
            ok, why = False, "not merged: git could not list what is unpushed"
        elif mine:
            # The owner's own unpushed commits: never published, and no merge
            # is laid over them.
            ok, why = False, gitops._foreign_said(mine)
        else:
            ok, why = gitops.merge_in(self.atlas, main,
                                      "origin/%s" % gitops.MAIN)
        if not ok:
            why = "; ".join(l.strip() for l in why.splitlines()
                            if l.strip()) or "merge refused"
            if self._record(False, "merge", why, remote=main):
                self.say("sync: origin's %s was not merged: %s"
                         % (main[:12], why))
            return False
        self._push(main)
        return True

    def _push(self, main):
        """Push what `_merge` made; a failure is recorded as step `push`, and
        the next pass tries again."""
        from . import gitops
        code, branch = gitops._git(self.atlas, "symbolic-ref", "--quiet",
                                   "--short", "HEAD")
        if code != 0 or branch != gitops.MAIN:
            ok, said = False, "not pushed: HEAD is not on %s" % gitops.MAIN
        else:
            ok, said = gitops.push(self.atlas, timeout=PULL_TIMEOUT,
                                   board=True)
        if ok:
            self._record(True, "merge", "", remote=main)
            return True
        why = "; ".join(l.strip() for l in said.splitlines()
                        if l.strip()) or "push failed"
        if self._record(False, "push", why, remote=main):
            self.say("sync: the merge with %s is here and not pushed: %s"
                     % ((main or "")[:12], why))
        return False

    # -- coding sessions --------------------------------------------------
    def hear_code(self, refs, local=None):
        """Hear `refs` (`{ref: sha}`, every `refs/heads/code/*` origin has;
        None when origin did not answer) and `local` (those this checkout
        keeps itself; None when unknown). A moved one is recorded and woken,
        fetched first from origin; a session whose ref is gone from origin
        is released. A local one is never released: its record is dropped
        when the ref is gone. The records heard."""
        from . import code as coding, sessions
        held = sessions.coding(self.atlas)
        out = []
        heard = dict(refs or {})
        # A ref this checkout keeps is the session's own, whatever origin has.
        heard.update(local or {})
        for ref_name, sha in sorted(heard.items()):
            sid = ref_name[len(CODE_PREFIX):]
            if not coding.SESSION_RE.match(sid):
                continue
            mine = ref_name in (local or {})
            old = held.get(sid)
            if old is not None and old.get("sha") == sha \
                    and bool(old.get("local")) == mine:
                continue
            if old is None and self._noticed.get(ref_name) == sha:
                continue
            got = self.hear_step(sid, sha, old, local=mine)
            if got:
                out.append(got)
        for sid, old in sorted(held.items()):
            if old.get("local"):
                if local is not None and old.get("ref") not in local:
                    sessions.set_code(sid, None, base=self.atlas)
                continue
            if refs is not None and old.get("ref") not in refs:
                out.append(self.release(sid, old))
        return out

    def _fetch(self, sid):
        from . import code as coding, gitops
        code, out = gitops._git(self.atlas, "fetch", "--quiet", "origin",
                                "+%s:%s" % (coding.ref(sid), coding.tracking(sid)),
                                timeout=gitops.NET_TIMEOUT)
        return "" if code == 0 else ((out.splitlines() or ["fetch failed"])[-1])

    def hear_step(self, sid, sha, old, local=False):
        """Take `sha`, the new tip of `code/<sid>`, `local` when this
        checkout keeps the ref itself. The line woken or noticed, `{}` when
        the commit wakes nothing, None when it could not be read."""
        from . import code as coding, gitops, sessions
        err = "" if local else self._fetch(sid)
        if err:
            self.say("sync: could not fetch code/%s: %s" % (sid, err))
            return None
        said = coding.step_of(self.atlas, sha)
        old = old or {}
        subject = said["subject"] or old.get("subject") or ""
        if coding.subject_of(subject + "/x") != subject:
            subject = ""
        paths = [p for p in (said["paths"] or old.get("paths") or [])
                 if subject and coding.subject_of(p) == subject and p != subject
                 and ".." not in p.split("/")]
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
        # A local step was taken from this working tree: nothing to bring.
        seen, note = (sha, "") if local else self._bring(old, sha, paths)
        rec = {"ref": coding.ref(sid), "sha": sha, "paths": paths,
               "step": said["step"] or int(old.get("step") or 0),
               "subject": subject, "prev": prev, "seen": seen,
               "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        if local:
            rec["local"] = True
        sessions.set_code(sid, rec, base=self.atlas)
        if not said["step"]:
            return {}
        rng = "%s..%s" % (prev[:12], sha[:12]) if prev else sha[:12]
        if said.get("tutor"):
            # The tutor's own edit, taken as its turn ended: told, never
            # woken, or each do-mode edit would wake a turn about itself.
            text = ("[stepped] step %d on code/%s is your own edit, taken as "
                    "your last turn ended: `git diff %s -- %s`. It woke no "
                    "turn." % (said["step"], sid, rng, " ".join(paths) or "."))
            sessions._line(sessions.path(sid, self.atlas), text, "stepped",
                           ref=coding.ref(sid))
            return {"session": sid, "id": coding.ref(sid), "state": "stepped",
                    "text": text}
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
        text = ("[unheld] code/%s is gone from origin: the coding session "
                "that pushed it ended or was abandoned.%s" % (sid, note))
        if where:
            sessions._line(where, text, "unheld", ref=old.get("ref"))
        return {"session": sid, "id": old.get("ref"), "state": "unheld",
                "text": text}

    # -- the thread --------------------------------------------------------
    def run(self):
        while not self._stop.is_set():
            try:
                got = self.once()
                for rec in got["heard"]:
                    self.say("sync: heard %s (%s)" % (
                        rec.get("request") or rec.get("session")
                        or rec.get("id") or "?",
                        str(rec.get("state") or rec.get("signal")
                            or "?").lower()))
            except Exception as exc:                         # noqa: BLE001
                self.say("sync: a pass failed: %r" % (exc,))
            self._stop.wait(self.every)

    def stop(self):
        self._stop.set()

    def start(self):
        t = threading.Thread(target=self.run, name="sync", daemon=True)
        t.start()
        return t
