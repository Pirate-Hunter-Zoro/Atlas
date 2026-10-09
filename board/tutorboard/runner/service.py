"""The runner: every tutor turn, inside the board server.

    Runner(atlas)        one per server; `app.main` installs it, recovers, starts
    runner.wake(sid)     a waking inbox line landed: queue a turn
    runner.end(sid)      End: queue the wrap-up turn
    runner.recover()     at startup: kill a turn that outlived its server, and
                         queue what each session is owed or has waiting
    runner.quiesce()     stop taking jobs, only while none runs or waits
    runner.shutdown()    the server is stopping: kill the turns in flight
    wake(repo)           the installed runner's wake for a stored session;
                         False where nothing is installed (a CLI, a test)

One FIFO of jobs per session, and at most `concurrency` turns at once across
every session (config.json `concurrency`, default 2). A job is a TURN or the
WRAPUP. Two wakes of a session whose turn has not started are one turn: the
turn takes every unread line when it starts. A line written `"wake": false`
never queues anything; the next turn takes it with the rest.

A turn is one fresh provider process (`loop.take_turn`) in the Atlas root, with
TUTORBOARD_SESSION, TUTORBOARD_TURN=1 and CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1,
and `board` on PATH from this server's own tree. Its message is written into
the session's agent.json as `owed` before the inbox lines are marked read, and
its process group as `turn_pid` once it exists, so a server killed mid-turn
loses nothing: `recover` kills the group and queues the owed message, unless
the turn had already written its card. The wrap-up runs only on End.
"""

import collections
import os
import signal
import sys
import threading
import time
import traceback

from tutorboard import paths, processes, sessions
from tutorboard.agents import recipes
from tutorboard.course import config as course_config
from tutorboard.lesson import cards as lesson_cards, inbox
from tutorboard.runner import daemon, loop

DEFAULT_CONCURRENCY = 2
TURN = "turn"
WRAPUP = "wrapup"
# How long a turn's group is given to go on SIGTERM before SIGKILL.
KILL_GRACE = 5.0

# The runner of this process, or None. Set by `install`.
RUNNER = None


def install(runner):
    """Make `runner` the one `wake` reaches. Returns it."""
    global RUNNER
    RUNNER = runner
    return runner


def wake(repo):
    """Queue a turn for the stored session `repo` serves. False when no
    runner is installed here or `repo` is no session of its tree."""
    runner = RUNNER
    if runner is None or not getattr(repo, "stored", False):
        return False
    where = os.path.abspath(repo.live)
    if os.path.dirname(where) != sessions.store(runner.atlas):
        return False
    return runner.wake(os.path.basename(where))


def configured_concurrency():
    """config.json `concurrency`, else DEFAULT_CONCURRENCY; at least 1."""
    try:
        n = int(paths.config().get("concurrency") or DEFAULT_CONCURRENCY)
    except (TypeError, ValueError):
        n = DEFAULT_CONCURRENCY
    return max(1, n)


def kill_group(pgid, needle=None, grace=KILL_GRACE):
    """SIGTERM the process group `pgid`, then SIGKILL what is left after
    `grace` seconds. Only while its leader still looks like `needle` (the
    recipe's executable), since a pid outlives nothing. True if one was
    signalled."""
    try:
        pgid = int(pgid)
    except (TypeError, ValueError):
        return False
    if pgid <= 1 or not processes.pid_alive(pgid, needle):
        return False
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError:
        return False
    end = time.time() + grace
    while time.time() < end:
        try:
            os.killpg(pgid, 0)
        except OSError:
            return True
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass
    return True


class Runner(object):
    def __init__(self, atlas, concurrency=None, port=None):
        self.atlas = os.path.abspath(atlas)
        self.concurrency = concurrency or configured_concurrency()
        # The port this server listens on, handed to turns so `board write`
        # can poke the board the moment a card lands.
        self.port = port
        self.queues = {}                       # sid -> deque of jobs
        self.ready = collections.deque()       # sids with a job, nothing running
        self.running = {}                      # sid -> {"job", "pgid", "cmd"}
        self.cv = threading.Condition()
        self.stopping = False
        self.threads = []

    # -- queueing --------------------------------------------------------
    def queue(self, sid, job):
        """Append `job` to session `sid`'s FIFO. False when the same job is
        already queued there and not started, which is the same work."""
        with self.cv:
            q = self.queues.setdefault(sid, collections.deque())
            if job in q:
                return False
            q.append(job)
            if sid not in self.running and sid not in self.ready:
                self.ready.append(sid)
            self.cv.notify()
            return True

    def wake(self, sid):
        """A line that wakes landed in session `sid`: queue a turn."""
        if not sessions.path(sid, self.atlas):
            return False
        return self.queue(sid, TURN)

    def end(self, sid):
        """End was tapped on session `sid`: queue its wrap-up."""
        if not sessions.path(sid, self.atlas):
            return False
        return self.queue(sid, WRAPUP)

    def attach(self, where):
        """Put this server on the record of the session at `where` when the
        record names no live process, so the board says a tutor is listening
        rather than that nothing is attached."""
        st = daemon.agent_record_at(where) or {}
        if st.get("pid") == os.getpid() or processes.pid_alive(st.get("pid")):
            return False
        name = st.get("agent") or recipes.resolve(recipes.load_config())[0]
        daemon.agent_state(where, pid=os.getpid(), host=recipes.this_host(),
                           agent=name, state="listening")
        return True

    def busy(self, sid=None):
        """Is a turn running or queued -- for `sid`, or for any session?"""
        with self.cv:
            if sid is None:
                return bool(self.running) or any(self.queues.values())
            return sid in self.running or bool(self.queues.get(sid))

    def state(self):
        """`{"running": [...], "queued": {sid: [jobs]}}`, for /health and tests."""
        with self.cv:
            return {"running": sorted(self.running),
                    "queued": {s: list(q) for s, q in self.queues.items() if q}}

    # -- the workers -----------------------------------------------------
    def start(self):
        for n in range(self.concurrency):
            t = threading.Thread(target=self._work, name="turn-%d" % n, daemon=True)
            t.start()
            self.threads.append(t)
        return self

    def _work(self):
        while True:
            with self.cv:
                while not self.ready and not self.stopping:
                    self.cv.wait()
                if self.stopping:
                    return
                sid = self.ready.popleft()
                job = self.queues[sid].popleft()
                self.running[sid] = {"job": job, "pgid": None, "cmd": None}
            again = False
            try:
                again = self._run(sid, job)
            except Exception:                                # noqa: BLE001
                sys.stderr.write("runner: session %s, %s failed:\n%s"
                                 % (sid, job, traceback.format_exc()))
            with self.cv:
                self.running.pop(sid, None)
                q = self.queues.setdefault(sid, collections.deque())
                if again and not self.stopping and TURN not in q:
                    q.append(TURN)
                if q:
                    if sid not in self.ready:
                        self.ready.append(sid)
                else:
                    del self.queues[sid]
                self.cv.notify_all()

    # -- one job ---------------------------------------------------------
    def _ctx(self, sid, repo, landed=None):
        cfg = recipes.load_config()
        course = {"root": repo.root, "dir": os.path.basename(repo.root),
                  "name": course_config.read_config(repo.root)["name"]}
        # Who wrote last, so an `[unfinished]` report stays with it
        # (`loop.for_this_turn`); every other turn re-resolves.
        name = ((daemon.agent_record_at(repo.live) or {}).get("agent")
                or recipes.resolve(cfg)[0])
        env = dict(os.environ)
        env["TUTORBOARD_SESSION"] = repo.live
        env["TUTORBOARD_TURN"] = "1"
        env["CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"] = "1"
        env["TUTORBOARD_COURSES"] = self.atlas
        # `board` is this server's own, whatever PATH says.
        env["PATH"] = os.pathsep.join([os.path.join(paths.TOOL, "bin"),
                                       env.get("PATH", "")])
        if self.port:
            env["TUTORBOARD_PORT"] = str(self.port)
        else:
            env.pop("TUTORBOARD_PORT", None)
        logpath = os.path.join(repo.live, "agent.log")
        log = open(logpath, "a", buffering=1)
        ctx = loop.Ctx(cfg=cfg, course=course, repo=repo, root=repo.root,
                       cwd=self.atlas, live=repo.live, log=log, logpath=logpath,
                       agent_name=name, spec=cfg["agents"].get(name) or {},
                       turns=self._turns(repo.live), env=env, sid=sid)
        ctx.on_start = self._on_start(sid, ctx, landed)
        return ctx

    @staticmethod
    def _turns(live):
        rec = daemon.agent_record_at(live) or {}
        try:
            return int(rec.get("turns") or 0)
        except (TypeError, ValueError):
            return 0

    def _on_start(self, sid, ctx, landed):
        def started(p):
            exe = os.path.basename(str((p.args or [""])[0]))
            with self.cv:
                if sid in self.running:
                    self.running[sid].update(pgid=p.pid, cmd=exe)
            daemon.agent_state(ctx.live, turn_pid=p.pid, turn_cmd=exe)
            if landed:
                ctx.log.write("-- %s spawned %.3f s after the message landed\n"
                              % (ctx.agent_name, max(0.0, time.time() - landed)))
        return started

    def _run(self, sid, job):
        """Run `job` on session `sid`. True when the session owes another
        turn straight away."""
        if not sessions.path(sid, self.atlas):
            return False
        repo = sessions.repo(sid, self.atlas)
        if job == WRAPUP:
            return self._wrap(sid, repo)
        owed = daemon.owed_message(repo.live)
        if not owed and not inbox.waiting(repo):
            return False
        landed = None
        text = ""
        if inbox.waiting(repo):
            def before(said):
                daemon.agent_state(repo.live, owed="\n\n".join(
                    x for x in (owed, said) if x))
            text, taken = inbox.take(repo, before)
            times = [float(m.get("t") or 0) for m in taken if inbox.wakes(m)]
            landed = max(times) if times else None
        message = "\n\n".join(x for x in (owed, text) if x)
        if not message:
            return False
        ctx = self._ctx(sid, repo, landed)
        try:
            if owed:
                ctx.log.write("-- answering the message the last turn still owed\n")
            daemon.agent_state(repo.live, pid=os.getpid(),
                               host=recipes.this_host(), agent=ctx.agent_name)
            got = loop.take_turn(ctx, message)
            daemon.agent_state(repo.live, turn_pid=None, turn_cmd=None)
            if got.get("owed") is None:
                return False
            if got.get("error") is None:
                return True               # the [unfinished] report: now
            # A failure the turn repaired itself (the fallback): answer it again
            # now only where another agent would take it, or the same failure
            # repeats for ever. Otherwise it stays owed for the next wake.
            nxt, _ = recipes.resolve(recipes.load_config())
            if nxt and nxt != ctx.agent_name:
                return True
            ctx.log.write("-- the message stays owed; the next turn answers it\n")
            return False
        finally:
            ctx.log.close()

    def _wrap(self, sid, repo):
        """The wrap-up: only for a session bound to a subject that has had
        a turn. Then `sessions.end` once more, so what it wrote is committed."""
        if os.path.realpath(repo.root) == os.path.realpath(self.atlas):
            return False
        if not lesson_cards.newest(repo.cards)[0]:
            return False
        ctx = self._ctx(sid, repo)
        try:
            daemon.agent_state(repo.live, pid=os.getpid(),
                               host=recipes.this_host(), agent=ctx.agent_name)
            loop.wrap_up(ctx)
            daemon.agent_state(repo.live, turn_pid=None, turn_cmd=None)
            try:
                _rec, ok, said = sessions.end(sid, base=self.atlas)
                ctx.log.write("-- %s\n" % said)
            except (sessions.NoSession, OSError) as exc:
                ctx.log.write("!! the session could not be ended again: %s\n" % exc)
        finally:
            ctx.log.close()
        return False

    # -- startup and shutdown ---------------------------------------------
    def recover(self):
        """After a start: every session whose turn outlived the server that
        ran it has that turn's group killed and its state put back to
        listening; what it owed is queued, unless the turn had already
        written its card; and every session with waking lines is queued.
        Returns the ids queued."""
        queued = []
        for rec in sessions.all(self.atlas):
            sid = rec.get("id")
            where = sessions.path(sid, self.atlas)
            if not where:
                continue
            st = daemon.agent_record_at(where) or {}
            repo = sessions.repo(sid, self.atlas)
            owed = st.get("owed") if isinstance(st.get("owed"), str) else None
            cut = st.get("state") in ("working", "wrapping up") or st.get("turn_pid")
            if st.get("turn_pid"):
                kill_group(st["turn_pid"], st.get("turn_cmd"))
            if cut:
                owed = self._still_owed(repo, st, owed)
                daemon.agent_state(where, state="listening", turn_pid=None,
                                   turn_cmd=None, owed=owed, pid=os.getpid(),
                                   host=recipes.this_host())
            if owed or inbox.waiting(repo):
                if self.queue(sid, TURN):
                    queued.append(sid)
        return queued

    @staticmethod
    def _still_owed(repo, st, owed):
        """What a cut turn still owes: nothing when it wrote its card before
        it was cut, its `[unfinished]` line when it left the placeholder, and
        the message itself otherwise."""
        if not owed:
            return None
        try:
            started = float(st.get("turn_started") or 0)
        except (TypeError, ValueError):
            started = 0.0
        path, meta = lesson_cards.newest(repo.cards)
        try:
            fresh = bool(path) and started > 0 and os.path.getmtime(path) >= started
        except OSError:
            fresh = False
        if not fresh:
            return owed
        if lesson_cards.is_pending(meta):
            return loop.unfinished_line(owed, os.path.relpath(path, repo.root))
        return None

    def quiesce(self):
        """Stop taking jobs, but only while none runs or waits. True when
        stopped: the server may then exit, and a line that lands after this
        stays in its inbox for the next start's `recover`."""
        with self.cv:
            if self.running or any(self.queues.values()):
                return False
            self.stopping = True
            self.cv.notify_all()
            return True

    def shutdown(self):
        """The server is stopping: no further job starts, and every turn in
        flight is killed. What it owed stays in agent.json for `recover`."""
        with self.cv:
            self.stopping = True
            groups = [(r.get("pgid"), r.get("cmd")) for r in self.running.values()]
            self.cv.notify_all()
        for pgid, cmd in groups:
            if pgid:
                kill_group(pgid, cmd)
