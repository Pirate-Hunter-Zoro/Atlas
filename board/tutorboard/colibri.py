"""Is the local model up, and what is it doing on its way there.

`coli-code` is the recipe the `colibri` agent runs, and it needs a server: a
Slurm job on a compute node holding 429 GB of weights warm behind a loopback
gateway. On a terminal the answer to "there is no server" is one line of advice
-- *start one: coli-up* -- and on an iPad that is a dead end.

So this module answers two questions and nothing else. WHICH OF FOUR STATES the
server is in, in words a board can paint; and START ONE, returning at once.

    off      nothing is submitted. There is a control, and it offers to start one
    queued   the job exists and Slurm has not run it yet; the reason is Slurm's
    loading  the job is running. 429 GB off the filer, then a warm-up generation
    warm     it has answered a request, which is the only proof that it can

`squeue` IS THE SOURCE OF TRUTH and nothing here writes a state file. A state
file goes stale the moment a job ends and `squeue` never does -- the same choice
`coli-up`, `coli-code` and the `ollama-*` three already made. It is asked once
per poll and the board polls four times a second, so the answer is cached for
`TTL` seconds; `machines.held_nodes` is the pattern, not the function.

FOUR STATES AND ONE FACT. The fact is the chain: a generation two hours from its
walltime submits the next one, which loads 406.7 GB on another node while this one
goes on answering, and only once that one says `COLIBRI-SERVE LOADED` does this one
give its node back. So `squeue` lists TWO generations for an hour at a time, and
the one to report is the one that can ANSWER -- warm beats loading, and between two
warm ones the one with more walltime left is the one that is not about to hand
over. The other is reported as a clause on the end of the sentence, because "this
server goes away in twenty minutes" is not sayable without it.

THE DIFFERENCE BETWEEN `loading` AND `warm` IS WORTH PAINTING and cannot be got
from Slurm. The gateway binds its port before it loads anything -- deliberately,
so a bad argument fails in milliseconds rather than after 429 GB -- so a TCP
probe answers instantly and says nothing about whether the thing can generate.
The job prints two lines instead, and they are what is read here: `API listening
on` when the engine is up, and `COLIBRI-SERVE READY` when it has completed a
real generation. Between them the model answers at roughly a fifth of its steady
rate, which is worth knowing before somebody sends an hour of work into it.
"""

import json
import os
import subprocess
import time

from . import atlas


# The job, the workspace it belongs to, and the two sentinels. All four match
# `scripts/colibri-env.sh`, which is the one file in that project that answers
# "where is colibri and what does it serve" -- so every one of them is read from
# the environment first, exactly as that file does it.
JOB_NAME = os.environ.get("COLI_JOB_NAME") or "colibri_serve"
WORKSPACE = "libr-local-llm"
LISTENING = "API listening on"
LOADED = "COLIBRI-SERVE LOADED"
READY = "COLIBRI-SERVE READY"
FAILED = "COLIBRI-SERVE FAILED"

TTL = 15.0
_CACHE = {"at": 0.0, "was": None}

# The window in which a start that has been asked for but is not yet in the
# queue still says so. `sbatch` returns a job id in about a second, so this is
# short -- and it is in memory rather than on disk for the same reason the rest
# of this file reads `squeue`: a record of an intention outlives the intention.
SUBMIT_GRACE = 45.0
_ASKED = {"at": 0.0}


def log_dir():
    """Where the serve job writes, or None if this machine has not got the tree.

    `COLI_LOG_DIR` first, because that is what the project's own scripts honour.
    Otherwise the workspace's own `slurm_jobs/logs`, found by the walk rather
    than by counting directories: nothing registers a workspace, and a machine
    with half the tree checked out has no colibri at all.
    """
    said = os.environ.get("COLI_LOG_DIR")
    if said:
        return said
    try:
        for w in atlas.workspaces():
            if w["dir"] == WORKSPACE:
                return os.path.join(w["root"], "slurm_jobs", "logs")
    except Exception:                                        # noqa: BLE001
        return None
    return None


def _run(args, timeout=10):
    """A command's stdout, or None if it could not be asked at all.

    One place, so a test can put a `squeue` in front of this module without a
    cluster, and so "no Slurm here" is one answer rather than four.
    """
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def time_left(said):
    """Slurm's `%L` as seconds, or None where it does not mean a number.

    `UNLIMITED`, `INVALID` and a blank are all None, which is "nothing here
    limits it" rather than zero -- and the difference matters, because a mission
    is failed by a ceiling that has passed and a zero is a ceiling that passed
    the instant it was written. The spellings are Slurm's own: `d-hh:mm:ss`,
    `hh:mm:ss`, `mm:ss`.
    """
    said = (said or "").strip()
    if not said or not said[0].isdigit():
        return None
    days = 0
    if "-" in said:
        first, said = said.split("-", 1)
        try:
            days = int(first)
        except ValueError:
            return None
    parts = said.split(":")
    if len(parts) > 3:
        return None
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    secs = 0
    for n in nums:                      # mm:ss, hh:mm:ss -- rightmost is seconds
        secs = secs * 60 + n
    if len(nums) == 1:
        secs *= 60                      # a bare number is minutes
    return days * 86400 + secs


def _jobs():
    """Every generation of the chain Slurm knows about: id, state, node, reason, left.

    THE TIME LEFT IS WHY THIS ASKS FOR MORE THAN IT PAINTS. A colibrì turn runs
    inside this allocation -- `coli-code` steps into it with `srun --overlap` --
    so a job set going on the local model cannot outlive the walltime here, and
    nothing anywhere used to say what that was. `missions.py` stamps it on a
    mission at dispatch, and under a chain it is the ceiling of THIS generation
    rather than of the chain: the server comes back on another node, the client
    does not.
    """
    return [r for r in (_all_jobs() or []) if not standing_by(r)]


def _all_jobs():
    """Every row `squeue` lists under the job name, clones included, or None
    where `squeue` could not be asked -- which is not the same as no jobs."""
    out = _run(["squeue", "-u", os.environ.get("USER", ""), "-n", JOB_NAME,
                "-h", "-o", "%i|%T|%N|%r|%L"])
    if out is None:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 2 or not parts[0]:
            continue
        rows.append({"id": parts[0].strip(), "state": parts[1].strip().upper(),
                     "node": (parts[2].strip() if len(parts) > 2 else ""),
                     "reason": (parts[3].strip() if len(parts) > 3 else ""),
                     "left": time_left(parts[4] if len(parts) > 4 else "")})
    return rows


def standing_by(row):
    """Is this a clone waiting on its parent's dependency? It is not a server
    anybody can use, and it is not "a generation already queued"."""
    return (row.get("state") == "PENDING"
            and row.get("reason", "").lstrip("(").startswith("Dependency"))


def _serving(rows):
    """Which generation to report, and which one is queued behind it.

    Warm beats loading; between two warm ones, more walltime left wins, because
    that is the one that is not handing over. A generation that has not warmed is
    still better than nothing and is the fallback rather than a refusal.
    """
    running = [r for r in rows if r["state"] == "RUNNING"]
    warm = [r for r in running if _tail(_out(r["id"]), READY)]
    pick = None
    if warm or running:
        pick = max(warm or running, key=lambda r: r["left"] or 0)
    elif rows:
        pick = rows[0]
    other = [r for r in rows if pick is None or r["id"] != pick["id"]]
    return pick, (other[0] if other else None)


def _out(job):
    """The names this generation's stdout could be under, best first.

    PER JOB, BECAUSE A CHAIN RUNS TWO OF THEM AT ONCE. One pair of files would
    have an overlapping successor judged by the incumbent's `COLIBRI-SERVE READY`
    -- a server reported warm while it is still reading off the filer. The fixed
    name is still answered second, so a job submitted by an older copy of
    `colibri_serve.sbatch` does not make the board go blind.
    """
    return ["colibri_serve_out-%s.txt" % job, "colibri_serve_out.txt"]


def _err(job):
    return ["colibri_serve_err-%s.txt" % job, "colibri_serve_err.txt"]


def _tail(names, needle, limit=200000):
    """Is this sentinel in that log. The tail only: these files grow all day."""
    where = log_dir()
    if not where:
        return False
    for name in ([names] if isinstance(names, str) else names):
        path = os.path.join(where, name)
        try:
            size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if size > limit:
                    fh.seek(size - limit)
                return needle in fh.read()
        except OSError:
            continue
    return False


def _next_clause(nxt):
    """What the generation behind this one is doing, as a clause or nothing.

    This is the whole of what a chain adds to the glass, and it is what makes
    "the server goes away in twenty minutes" sayable at all.
    """
    if not nxt:
        return ""
    if nxt["state"] != "RUNNING":
        return "; the next generation is queued"
    if _tail(_out(nxt["id"]), LOADED):
        return "; the next generation is loaded on %s and takes over in a moment" \
               % (nxt["node"] or "another node")
    return "; the next generation is loading on %s" % (nxt["node"] or "another node")


def _read():
    """The state, uncached. Four states, a sentence for each, and the chain."""
    rows = _jobs()
    job, nxt = _serving(rows)
    if not job:
        if time.time() - _ASKED["at"] <= SUBMIT_GRACE:
            # ASKED FOR AND NOT YET IN THE QUEUE. `sbatch` takes about a second
            # and the board polls four times a second, so without this a tap
            # reports "nothing is running" back to the person who just tapped it
            # -- which is how a second tap happens.
            return {"state": "queued", "job": None, "node": "", "next": None,
                    "left": None, "detail": "submitting the job"}
        # OFF IS THE NORMAL STATE: a generation runs while there is a task.
        return {"state": "off", "job": None, "node": "", "next": None,
                "left": None,
                "detail": "no server is running; filing a task starts one"}
    tail = _next_clause(nxt)
    said = {"job": job["id"], "node": job["node"], "left": job["left"],
            "next": (nxt["id"] if nxt else None)}
    if job["state"] != "RUNNING":
        said.update(state="queued", node="",
                    # Slurm's own word for why, not a guess. A 950 GB ask can pend
                    # indefinitely behind a nearly-full node and the reason is the
                    # only thing that says so.
                    detail=(job["reason"] or "waiting for an allocation") + tail)
        return said
    if _tail(_out(job["id"]), READY):
        said.update(state="warm",
                    detail="warm on %s" % (job["node"] or "a compute node") + tail)
        return said
    if _tail(_err(job["id"]), LISTENING):
        said.update(state="loading",
                    detail="listening, still warming — the first generation "
                           "runs at about a fifth of the steady rate" + tail)
        return said
    if _tail(_out(job["id"]), FAILED):
        said.update(state="off",
                    detail="the job is running but the engine failed to load" + tail)
        return said
    said.update(state="loading", detail="reading 429 GB off the filer" + tail)
    return said


def status(fresh=False):
    """The state, cached. Safe to ask on every poll."""
    now = time.time()
    if fresh or _CACHE["was"] is None or now - _CACHE["at"] > TTL:
        _CACHE["was"] = _read()
        _CACHE["at"] = now
    return dict(_CACHE["was"])


def forget():
    """Drop the cache, because something just changed it."""
    _CACHE["at"] = 0.0


def up_command():
    """`coli-up`, if this machine has it. Named so a refusal can say what is missing."""
    import shutil
    return shutil.which("coli-up")


def submitted():
    """Somebody has just asked for a start that Slurm has not listed yet.

    Set by `spawn.wake_colibri` and read by `_read`, in memory rather than on
    disk for the same reason the rest of this file reads `squeue`: a record of
    an intention outlives the intention.
    """
    _ASKED["at"] = time.time()
    forget()


# ---------------------------------------------------------------------------
# on demand: the task queue, the generation that works it, and the relay hook
# ---------------------------------------------------------------------------
# COLIBRI IS NOT KEPT WARM. Filing a task starts a generation if none is queued
# or running; the generation loads, works the queue one task at a time, and
# exits cleanly once the queue has been empty for `COLI_IDLE_MIN` minutes. The
# queue is mission records (`missions.TASK`) in libr-local-llm's ignored
# `live/missions/`. Each generation submits its own clone at start
# (`coli_submit_clone` in `scripts/colibri-env.sh`), so a death costs one cold
# load and the clone resumes the task by name; three deaths fail it.
#
# `sacct` IS REFUSED ON THIS CLUSTER, so a clean exit is told from a death the
# way the relay tells a job's end: the generation's last act writes its exit
# code to `<state>/gen-<job>.exit`. Left `squeue` with a 0 there: on purpose.
# Left without it: died.

HOP = 75            # coli-code: the generation its step ran in ended under it
NOTHING_YET = 76    # coli-code: no generation worth stepping into yet
LOAD_FAILED = 3     # the worker: this generation's engine never warmed
POLL = 30.0


def idle_limit():
    """Seconds of empty queue before an on-demand generation exits."""
    try:
        return float(os.environ.get("COLI_IDLE_MIN") or 20) * 60.0
    except ValueError:
        return 20 * 60.0


def queue_root():
    """The libr-local-llm workspace, whose `live/missions/` is the queue.

    `COLI_QUEUE_ROOT` first, which is how a test says "this tree"; then
    `LLM_REPO`, which `colibri-env.sh` exports inside a generation; then the
    walk. None where this machine has not got that workspace.
    """
    for key in ("COLI_QUEUE_ROOT", "LLM_REPO"):
        said = os.environ.get(key)
        if said and os.path.isdir(said):
            return said
    try:
        for w in atlas.workspaces():
            if w["dir"] == WORKSPACE:
                return w["root"]
    except Exception:                                        # noqa: BLE001
        return None
    return None


def state_dir():
    """`COLI_STATE_DIR`, as `colibri-env.sh` spells it. Ignored by git."""
    said = os.environ.get("COLI_STATE_DIR")
    if said:
        return said
    root = queue_root()
    return os.path.join(root, "slurm_jobs", "state") if root else None


def exit_code(job):
    """What generation `job` wrote as its last act, or None if it wrote nothing."""
    where = state_dir()
    if not where:
        return None
    try:
        with open(os.path.join(where, "gen-%s.exit" % job), "r") as fh:
            return int(fh.read().strip() or "x")
    except (OSError, ValueError):
        return None


def ended_clean(job):
    return exit_code(job) == 0


def mark_exit(job, code):
    """`coli_mark_exit`, for a caller in Python. The sbatch uses the shell one."""
    where = state_dir()
    os.makedirs(where, exist_ok=True)
    with open(os.path.join(where, "gen-%s.exit" % job), "w") as fh:
        fh.write("%d\n" % int(code))


def _closing_path(job):
    return os.path.join(state_dir(), "closing-%s" % job)


def closing(job):
    """Has this generation decided to exit? Then it is not one a task can wait for."""
    return os.path.exists(_closing_path(job))


class _Lock(object):
    """`flock` on `<state>/queue.lock`: filing and an idle exit are one at a time.

    Without it, a task filed in the second an idle generation decides to exit
    sees that generation running, starts none, and waits for ever.
    """

    def __enter__(self):
        import fcntl
        os.makedirs(state_dir(), exist_ok=True)
        self.fh = open(os.path.join(state_dir(), "queue.lock"), "a")
        fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        import fcntl
        try:
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()
        return False


def live_generations(rows=None):
    """Generations that are serving or will serve: no clone standing by on its
    parent, and none that has decided to exit."""
    rows = _jobs() if rows is None else rows
    return [r for r in rows if not standing_by(r) and not closing(r["id"])]


def _recent_start():
    """A job this machine submitted in the last `SUBMIT_GRACE` seconds, or "".

    `sbatch` returns before `squeue` is certain to list the job, so a second
    filer inside that window reads this rather than the queue.
    """
    try:
        with open(os.path.join(state_dir(), "started.json"), "r") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return ""
    if time.time() - float(got.get("at") or 0) <= SUBMIT_GRACE:
        return str(got.get("job") or "")
    return ""


def _tool(name, env):
    """`coli-up` or `coli-code`: `$COLI_UP`/`$COLI_CODE`, then the project's
    own `bin/`, then the path."""
    import shutil
    said = os.environ.get(env)
    if said:
        return said
    root = queue_root()
    if root and os.access(os.path.join(root, "bin", name), os.X_OK):
        return os.path.join(root, "bin", name)
    return shutil.which(name)


def start_generation():
    """`coli-up --detach`: submit one on-demand generation and return. `(job, said)`."""
    import re
    cmd = _tool("coli-up", "COLI_UP")
    if not cmd:
        return "", "coli-up is not on this machine"
    try:
        p = subprocess.run([cmd, "--detach"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "", "coli-up did not run: %s" % type(exc).__name__
    m = re.search(r"as job (\d+)", p.stdout or "")
    if p.returncode != 0 or not m:
        return "", "coli-up refused: %s" % (p.stdout or "").strip()[-300:]
    return m.group(1), "generation %s submitted" % m.group(1)


def file(thread, brief, workspace_root, request="", start=None, now=None):
    """Queue a task, and start a generation if none is queued or running.

    `(record, said)`; the record is None where nothing was queued. The thread
    is the caller's to check against that workspace's thread file -- `board
    colibri` and the relay both have it in hand already.
    """
    from . import missions
    brief = (brief or "").strip()
    if not brief:
        return None, "a task needs a brief"
    root = queue_root()
    if not root:
        return None, "this machine has no %s workspace to queue in" % WORKSPACE
    with _Lock():
        rec = missions.file_task(root, thread, brief,
                                 atlas.identify(workspace_root), request, now)
        if rec is None:
            return None, "the task could not be written under %s" % root
        return rec, "queued; " + _ensure(start)


def _started_at():
    try:
        with open(os.path.join(state_dir(), "started.json"), "r") as fh:
            return float((json.load(fh) or {}).get("at") or 0)
    except (OSError, ValueError, AttributeError):
        return 0.0


def _ensure(start=None):
    """Start a generation if none is queued or running. Under the queue lock.

    Never guessed: where `squeue` cannot be asked, nothing is started, because
    an unreachable controller looks exactly like an empty queue.
    """
    rows = _all_jobs()
    if rows is None:
        return "squeue could not be asked, so no generation was started"
    live = live_generations([r for r in rows if not standing_by(r)])
    if live:
        return "generation %s is %s" % (live[0]["id"], live[0]["state"].lower())
    recent = _recent_start()
    if recent:
        return "generation %s was just submitted" % recent
    job, said = (start or start_generation)()
    if not job:
        return "no generation started: %s" % said
    with open(os.path.join(state_dir(), "started.json"), "w") as fh:
        json.dump({"job": job, "at": time.time()}, fh)
    forget()
    return said


def kick(start=None):
    """Start a generation for a task filed when none could start. "" or what
    happened.

    Once per task, not once per pass: only a task queued AFTER the last start
    asks for one. A generation that cannot load is otherwise a 68-minute job
    submitted every five minutes for ever.
    """
    from . import missions
    root = queue_root()
    if not root:
        return ""
    with _Lock():
        since = _started_at()
        owed = [r for r in missions.tasks(root)
                if r.get("queue") == "queued" and float(r.get("at") or 0) > since]
        if not owed:
            return ""
        return _ensure(start)


TASK_PROMPT = (
    "This is a task from the Colibri queue, set going by the owner. Nobody is "
    "watching this session, so do not stop to ask; do the task, here.\n\n"
    "%s\n\n"
    "Write files as you finish them rather than holding them: the node under "
    "you can go away, and this conversation is then resumed on another. Do not "
    "commit or push. A hosted turn reviews your diff and ships it."
)

TASK_RESUME_PROMPT = (
    "Your conversation is resumed. The node under you ended; nothing you did "
    "caused it, and your work on disk is untouched. Carry on from where you "
    "stopped, and redo only the tool call that was in flight. The task "
    "again:\n\n%s\n\n"
    "Write files as you finish them. Do not commit or push."
)


def run_task(rec, job):
    """Run one task through `coli-code`, inside generation `job`. Its exit code.

    The client's output goes nowhere: it may quote session content, and this
    process's own output is the job log, which is counts-only. The transcript
    is behind the fence under `COLI_SESSION_ROOT`. A task begun before resumes
    its conversation by name, and falls back to a fresh one where the resume
    fails in seconds -- the conversation was never written.
    """
    from . import missions
    cmd = _tool("coli-code", "COLI_CODE")
    where = atlas.find(rec.get("workspace") or "")
    if not cmd or not where:
        return 2
    env = dict(os.environ, COLI_SESSION_ID=str(rec.get("session") or ""),
               COLI_JOB=str(job))
    resume = int(rec.get("attempts") or 0) > 1

    def go(cont):
        argv = [cmd, "-d", where["root"], "--yes"] + (["-c"] if cont else [])
        prompt = (TASK_RESUME_PROMPT if cont else TASK_PROMPT) % rec.get("brief")
        t0 = time.time()
        try:
            rc = subprocess.run(argv + ["--", prompt], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env).returncode
        except OSError:
            rc = 2
        return rc, time.time() - t0

    rc, ran = go(resume)
    if resume and rc not in (0, HOP, NOTHING_YET) and ran < missions.CARRY_FLOOR:
        rc, ran = go(False)
    return rc


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def recover(job):
    """Resume or fail what dead generations left running. Skipped, never
    guessed, where `squeue` cannot be asked or does not list this job: an
    unreachable controller would otherwise read as every generation dead."""
    from . import missions
    rows = _all_jobs()
    if rows is None:
        return []
    alive = [r["id"] for r in rows]
    if job and str(job) not in alive:
        return []
    return missions.recover_tasks(queue_root(), alive, ended_clean)


def work(job, demand=True, server_pid=None, idle=None, run=None, ready=None,
         clock=time.time, sleep=time.sleep, poll=POLL, say=None):
    """The queue's worker, inside generation `job`. Returns the job's exit code.

    0 is a clean idle exit; anything else is a death the clone repairs. With
    `demand` False (the warm chain, `--stay`) it never exits on idle.
    """
    from . import missions

    def tell(line):
        # Ids and states only. This goes to the job log, which is counts-only.
        (say or (lambda s: print(s, flush=True)))("COLIBRI-TASK " + line)

    root = queue_root()
    if not root:
        tell("none: no queue on this machine")
        return 2
    idle = idle_limit() if idle is None else idle
    run = run or run_task
    ready = ready or (lambda: _tail(_out(job), READY))
    up = (lambda: True) if server_pid is None else (lambda: _pid_alive(server_pid))
    while not ready():
        if _tail(_out(job), FAILED) or not up():
            tell("none: the engine did not load")
            return LOAD_FAILED
        sleep(poll)
    last = clock()
    while True:
        if not up():
            tell("stop: the engine went away")
            return 1
        for tid, verdict in recover(job):
            tell("recovered id=%s verdict=%s" % (
                tid, verdict if isinstance(verdict, str) else verdict[0]))
        rec = missions.next_task(root)
        if rec is not None:
            got = missions.claim_task(root, rec, job, clock())
            if got is None:
                sleep(poll)
                continue
            tell("start id=%s attempt=%d deaths=%d" % (
                got["id"], got["attempts"], int(got.get("deaths") or 0)))
            rc = run(got, job)
            if rc == 0:
                missions.finish_task(root, got, True, now=clock())
                tell("done id=%s" % got["id"])
            elif rc == HOP:
                tell("hop id=%s: the generation ended under it" % got["id"])
                return 1
            elif rc == NOTHING_YET:
                missions.requeue_task(root, got, now=clock())
                tell("wait id=%s: no server to step into yet" % got["id"])
                sleep(poll)
            else:
                missions.finish_task(root, got, False,
                                     "coli-code exited %d" % rc, clock())
                tell("failed id=%s exit=%d" % (got["id"], rc))
            last = clock()
            continue
        if demand and clock() - last >= idle:
            with _Lock():
                if missions.next_task(root) is None:
                    open(_closing_path(job), "w").close()
                    tell("idle: the queue has been empty for %d min" % (idle // 60))
                    return 0
            continue
        sleep(poll)


# --------------------------------------------------------------- the relay
# THE HOOK THE RELAY PASS CALLS. A `colibri` request (`jobs.validate`) is filed
# here, and every pass asks `relay_pass` for the reports of the tasks requests
# filed. Colibri may read PHI, so its output never goes into a report: a
# finished task is reviewed by a hosted follow-up turn, which ships the diff
# through `board push` (`names_phi` runs there, before anything leaves the
# machine), and the report carries only state and that turn's public note.

REVIEW_BRIEF = (
    "A Colibri task finished in this workspace, on thread `%(thread)s`, and its "
    "changes are uncommitted here. You are not the model that made them, and "
    "that is deliberate: Colibri may read PHI and you review what it wrote. "
    "The task was:\n\n%(brief)s\n\n"
    "Read `git status` and the diff. If the change is right and carries no "
    "session content, ship it with `board push \"%(thread)s: <what changed>\"`; "
    "`board push` runs the PHI check before anything leaves the machine. If it "
    "is wrong, leave it uncommitted and say why. Your note is published in a "
    "public repository: what changed and whether it shipped, aggregate numbers "
    "only, no patient-level values, no identifiers, no quoted session text."
)


def review_request(rec):
    """The hosted follow-up turn, shaped as a relay `turn` request."""
    return {"id": "review-" + str(rec.get("id")), "kind": "turn",
            "thread": rec.get("thread") or "",
            "brief": REVIEW_BRIEF % {"thread": rec.get("thread") or "",
                                     "brief": rec.get("brief") or ""}}


def relay_report(rec):
    """A task as a relay report: state and the public note, never the brief."""
    q = rec.get("queue")
    state = {"queued": "submitted", "running": "running",
             "failed": "failed"}.get(q, "running")
    note = ""
    if q == "done":
        if rec.get("reviewed"):
            state, note = "completed", rec.get("note") or ""
        else:
            note = "Colibri finished; the hosted review is next."
    elif q == "failed":
        note = rec.get("reason") or "the task failed"
    elif rec.get("deaths"):
        note = "resumed after %d death(s) of its generation" % int(rec["deaths"])
    out = {"id": rec.get("request"), "kind": "colibri", "state": state,
           "task": rec.get("id"), "attempts": int(rec.get("attempts") or 0),
           "deaths": int(rec.get("deaths") or 0),
           "submitted": float(rec.get("at") or 0), "note": note}
    if rec.get("gen"):
        out["jobid"] = str(rec["gen"])
    if q in ("done", "failed"):
        out["ended"] = float(rec.get("ended_at") or 0)
    return out


def relay_file(ws_root, req, start=None, now=None):
    """File a checked `colibri` request as a task. Its first report."""
    rec, said = file(req.get("thread"), req.get("brief"), ws_root,
                     request=req.get("id") or "", start=start, now=now)
    if rec is None:
        return {"id": req.get("id"), "kind": "colibri", "state": "refused",
                "problems": [said], "note": said}
    return relay_report(rec)


def relay_pass(review=None, limit=1, now=None, start=None):
    """`[(workspace root, report)]` for every task a request filed. The hook.

    `review(workspace root, turn request)` is the relay's own headless turn
    runner; it returns that turn's public note, or None if it did not run (it
    is asked again next pass). At most `limit` reviews run per pass, because
    only one turn runs at a time. A task filed by `board colibri` on the
    cluster is reviewed the same way and has no report. A task filed when no
    generation could start gets one here (`kick`).
    """
    from . import missions
    root = queue_root()
    if not root:
        return []
    kick(start)
    out, ran = [], 0
    for rec in missions.tasks(root):
        where = atlas.find(rec.get("workspace") or "")
        if not where:
            continue
        if (rec.get("queue") == "done" and not rec.get("reviewed")
                and review is not None and ran < limit):
            ran += 1
            note = review(where["root"], review_request(rec))
            if note is not None:
                rec = missions.review_task(root, rec, note, now)
        if rec.get("request"):
            out.append((where["root"], relay_report(rec)))
    return out


def main(argv):
    """`python3 -m tutorboard.colibri work --job J [--server-pid P] [--stay]`."""
    import argparse
    ap = argparse.ArgumentParser(prog="tutorboard.colibri")
    sub = ap.add_subparsers(dest="cmd")
    w = sub.add_parser("work", help="work the task queue inside a generation")
    w.add_argument("--job", required=True)
    w.add_argument("--server-pid", type=int)
    w.add_argument("--stay", action="store_true",
                   help="the warm chain: never exit on an empty queue")
    a = ap.parse_args(argv)
    if a.cmd != "work":
        ap.print_help()
        return 2
    return work(a.job, demand=not a.stay, server_pid=a.server_pid)


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
