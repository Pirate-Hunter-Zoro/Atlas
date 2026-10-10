"""Colibri, the local model: its server's state, and its task queue.

A task runs `coli-code`, which needs a server: a Slurm job holding 429 GB of
weights warm behind a loopback gateway. Filing a task starts a generation if
none is up. On the cluster `observe` reads `squeue` and the serve log's two
sentinels (`API listening on`, then `COLIBRI-SERVE READY` after a real
generation, because Slurm cannot tell loading from warm); the relay publishes
the public part in `relay/status.json`. On the Mac `status` reads only that
file (D27), and `ask` files a task. States: off, queued, loading, warm, and
unknown (Mac only). Of two generations in a chain, warm beats loading, then
more walltime wins.

The constraint: nothing a task touches leaves the cluster. The queue lives in
ignored `relay/state/colibri/`, and the public block names no node or path.
"""

import json
import os
import re
import subprocess
import time

from . import jobs, machine, subjects


# The job, the workspace and the two sentinels, read from the environment
# first exactly as `scripts/colibri-env.sh` does.
JOB_NAME = os.environ.get("COLI_JOB_NAME") or "colibri_serve"
WORKSPACE = "libr-local-llm"                   # a slug: `subjects.find`
LISTENING = "API listening on"
LOADED = "COLIBRI-SERVE LOADED"
READY = "COLIBRI-SERVE READY"
FAILED = "COLIBRI-SERVE FAILED"

# The states `relay/status.json` may carry; anything else reads as unknown.
STATES = ("off", "queued", "loading", "warm")

# A start this machine submitted counts as "just submitted" this long.
SUBMIT_GRACE = 45.0

# A walltime end that moved less than this is kept, so jitter makes no commit.
ENDS_SLACK = 180


def log_dir():
    """Where the serve job writes (`COLI_LOG_DIR`, else the workspace's
    `slurm_jobs/logs`), or None without the tree."""
    said = os.environ.get("COLI_LOG_DIR")
    if said:
        return said
    try:
        found = subjects.find(WORKSPACE)
    except Exception:                                        # noqa: BLE001
        return None
    return os.path.join(found["root"], "slurm_jobs", "logs") if found else None


def _run(args, timeout=10):
    """A command's stdout, or None if it could not be asked. One place, so a
    test can stand in for `squeue`."""
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def time_left(said):
    """Slurm's `%L` as seconds, or None for `UNLIMITED`, `INVALID` or blank:
    "nothing limits it", not zero, which is a ceiling already passed."""
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
    """Every generation Slurm knows: id, state, node, reason, time left,
    start. `[]` where `squeue` could not be asked. A task runs inside this
    allocation, so the time left is its ceiling."""
    return [r for r in (_all_jobs() or []) if not standing_by(r)]


def _started(said):
    """Slurm's `%S`, `YYYY-MM-DDTHH:MM:SS` local, as epoch seconds, or None."""
    try:
        return time.mktime(time.strptime((said or "").strip()[:19],
                                         "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError, OverflowError):
        return None


def _all_jobs():
    """Every row `squeue` lists under the job name, clones included, or None
    where `squeue` could not be asked -- which is not the same as no jobs."""
    out = _run(["squeue", "-u", os.environ.get("USER", ""), "-n", JOB_NAME,
                "-h", "-o", "%i|%T|%N|%r|%L|%S"])
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
                     "left": time_left(parts[4] if len(parts) > 4 else ""),
                     "start": _started(parts[5] if len(parts) > 5 else "")})
    return rows


def standing_by(row):
    """Is this a clone waiting on its parent's dependency? Not a usable or a
    queued server."""
    return (row.get("state") == "PENDING"
            and row.get("reason", "").lstrip("(").startswith("Dependency"))


def _serving(rows):
    """Which generation to report, and which is queued behind it: warm beats
    loading, then more walltime left; an unwarmed one is the fallback."""
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
    """The names this generation's stdout could be under, best first. Per
    job, because a chain runs two at once; the fixed name comes second for
    jobs from older sbatch files."""
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
    """The generation behind this one, as a clause or nothing."""
    if not nxt:
        return ""
    if nxt["state"] != "RUNNING":
        return "; the next generation is queued"
    if _tail(_out(nxt["id"]), LOADED):
        return "; the next generation is loaded on %s and takes over in a moment" \
               % (nxt["node"] or "another node")
    return "; the next generation is loading on %s" % (nxt["node"] or "another node")


def observe(rows=None):
    """The server's state off `squeue` and the logs, on the cluster. None where
    `squeue` could not be asked. `rows` is `_all_jobs()` where the caller has
    it. `detail` names nodes, so it never leaves the cluster."""
    rows = _all_jobs() if rows is None else rows
    if rows is None:
        return None
    job, nxt = _serving([r for r in rows if not standing_by(r)])
    if not job:
        # Off is the normal state: a generation runs only while there is a task.
        return {"state": "off", "job": None, "node": "", "next": None,
                "left": None, "reason": "",
                "detail": "no server is running; filing a task starts one"}
    tail = _next_clause(nxt)
    said = {"job": job["id"], "node": job["node"], "left": job["left"],
            "next": (nxt["id"] if nxt else None), "reason": ""}
    if job["state"] != "RUNNING":
        # Slurm's own reason: a 950 GB ask can pend behind a nearly-full node.
        said.update(state="queued", node="", reason=job["reason"],
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


# ---------------------------------------------------------------------------
# relay/status.json: what the cluster publishes, and what the Mac reads
# ---------------------------------------------------------------------------
# The public block is `{state, ends, queue, task, load_s, reason}`: `ends` is
# epoch seconds, so it does not change every pass. No node name, no path.
# `memo` (`relay/state.json` `colibri`) times each cold load.
_REASON_RE = re.compile(r"^[A-Za-z]{1,40}$")


def relay_status(prev=None, memo=None, now=None):
    """The public block for `relay/status.json`. `prev` is the block HEAD
    has, `memo` a dict this updates. Where `squeue` cannot be asked, the
    state and walltime are `prev`'s."""
    now = float(now or time.time())
    prev = prev if isinstance(prev, dict) else {}
    memo = memo if memo is not None else {}
    rows = _all_jobs()
    out = {"state": prev.get("state") if prev.get("state") in STATES
           else "unknown", "ends": prev.get("ends"),
           "reason": prev.get("reason") or ""}
    if rows is not None:
        got = observe(rows)
        out["state"] = got["state"]
        out["reason"] = (got.get("reason") if _REASON_RE.match(
            got.get("reason") or "") else "") if got["state"] == "queued" else ""
        ends = None
        if got.get("left") is not None and got["state"] in ("loading", "warm"):
            ends = int(now + got["left"])
            old = prev.get("ends")
            if isinstance(old, int) and abs(old - ends) < ENDS_SLACK:
                ends = old
        out["ends"] = ends
        _time_loads(rows, memo, now)
    out["load_s"] = memo.get("load_s") if isinstance(
        memo.get("load_s"), int) else prev.get("load_s")
    queued, running = 0, None
    root = queue_root()
    for rec in (tasks(root) if root else []):
        if rec.get("queue") == "queued":
            queued += 1
        elif rec.get("queue") == "running" and running is None:
            running = str(rec.get("id"))
    out["queue"] = queued
    out["task"] = running
    return out


def _time_loads(rows, memo, now):
    """Time a cold load: a generation seen running and not warm is `cold`,
    with its start (Slurm's, else the first pass that saw it); the first pass
    that sees it warm records `load_s`, now less that start."""
    cold = memo.get("cold") if isinstance(memo.get("cold"), dict) else {}
    alive = set()
    for r in rows:
        if r.get("state") != "RUNNING":
            continue
        jid = str(r["id"])
        alive.add(jid)
        warm = _tail(_out(jid), READY)
        if not warm:
            if jid not in cold:
                cold[jid] = float(r.get("start") or now)
            continue
        if jid in cold:
            took = int(now - cold.pop(jid))
            if took > 0:
                memo["load_s"] = took
    memo["cold"] = dict((k, v) for k, v in cold.items() if k in alive)


def status(base=None, now=None):
    """The server's state on the Mac, read only from `relay/status.json` in
    the Atlas tree `base` (D27). `{state, left, queue, task, load_s, detail,
    at}`; `state` is `unknown` where the relay has not said."""
    from . import relay
    now = float(now or time.time())
    doc = relay.read_status(base or subjects.root())
    got = doc.get("colibri")
    got = got if isinstance(got, dict) else {}
    state = got.get("state") if got.get("state") in STATES else "unknown"
    ends = got.get("ends")
    left = (max(0, int(ends - now)) if isinstance(ends, (int, float))
            and not isinstance(ends, bool) and state in ("loading", "warm")
            else None)
    load_s = got.get("load_s") if isinstance(got.get("load_s"), int) else None
    queue = got.get("queue") if isinstance(got.get("queue"), int) else 0
    task = got.get("task") if isinstance(got.get("task"), str) else None
    reason = got.get("reason") if isinstance(got.get("reason"), str) else ""
    return {"state": state, "left": left, "queue": queue, "task": task,
            "load_s": load_s, "at": doc.get("at"),
            "detail": _words(state, left, reason, load_s)}


def _minutes(secs):
    m = int(round(secs / 60.0))
    if m < 90:
        return "%d min" % max(1, m)
    return "%d h %02d min" % (m // 60, m % 60)


def _words(state, left, reason, load_s):
    if state == "warm":
        return "warm" + (", %s left" % _minutes(left) if left else "")
    if state == "loading":
        return "loading" + (", a cold load takes about %s" % _minutes(load_s)
                            if load_s else "")
    if state == "queued":
        return "queued" + (" (%s)" % reason if reason else "")
    if state == "off":
        return "no server is running; filing a task starts one"
    return "the relay has not said what Colibri is doing"


def estimate(st, every=None):
    """What filing a task now costs in waiting, from `status`'s `st`: the
    relay's next pass, then a cold load timed by the relay where none is up."""
    from . import relay
    every = every or relay.PASS_MINUTES
    pass_in = "the relay's next pass (every %d min) queues it" % every
    if st.get("state") == "warm":
        return "Colibri is warm: %s and it starts" % pass_in
    if st.get("state") in ("loading", "queued"):
        return "a generation is coming up: %s, and it starts once that is warm" \
            % pass_in
    if st.get("load_s"):
        return ("a cold start: %s, then a load of about %s (the last one the "
                "relay timed)" % (pass_in, _minutes(st["load_s"])))
    return ("a cold start: %s, then a load the relay has not timed yet "
            "(over an hour)" % pass_in)


def ask(root, brief, label="", session="", push=True):
    """The Mac's `board colibri` and POST /colibri: a `colibri` relay request
    from subject `root`, checked, committed and pushed. `{ok, id, said,
    problems}`; `problems` lists why a request was not filed."""
    brief = (brief or "").strip()
    if not brief:
        return {"ok": False, "problems": ["say what the task is"]}
    if len(brief) > jobs.MAX_BRIEF:
        return {"ok": False, "problems": [
            "the task is %d characters and the cap is %d"
            % (len(brief), jobs.MAX_BRIEF)]}
    if label and not jobs.LABEL_RE.match(label):
        return {"ok": False, "problems": [
            "a label is 1-40 characters of a-z, 0-9 and hyphen"]}
    if session and not jobs.SESSION_RE.match(session):
        return {"ok": False, "problems": ["%r is not a session id" % session]}
    taken = set(r["id"] for r in jobs.requests(root))
    req = {"id": jobs.new_id(label, "colibri", taken), "kind": "colibri",
           "brief": brief, "filed": round(time.time(), 3)}
    if label:
        req["label"] = label
    if session:
        req["session"] = session
    ok, problems = jobs.check(root, req)
    if problems:
        return {"ok": False, "problems": list(problems)}
    hidden = jobs.request_visible(root)
    if hidden:
        return {"ok": False, "problems": [hidden]}
    changed = jobs.dirty(root)
    if changed:
        return {"ok": False, "problems": [jobs.dirty_said(root, changed)]}
    path, done, said = jobs.file_request(root, ok, push=push)
    if not done:
        return {"ok": False, "id": ok["id"], "problems": [
            "the request is written at %s but did not reach the cluster: %s"
            % (os.path.relpath(path, root), said)]}
    return {"ok": True, "id": ok["id"], "problems": [],
            "said": "request %s filed and pushed; the relay's next pass "
                    "queues it" % ok["id"]}


# A report's state as the panel words it: queued until a generation claims
# the task, working while it runs, done once checked clean.
PHASES = {"submitted": "queued", "running": "working", "completed": "done",
          "failed": "failed", "refused": "refused"}


def phase(state, task="", running=None):
    """`filed`, `queued`, `working`, `done`, `failed` or `refused` for a
    report's `state`. `running` is the task status.json says is running: a
    task the relay has just claimed is working before its report says so."""
    if not state:
        return "filed"
    if running and task and task == running and state == "submitted":
        return "working"
    return PHASES.get(state, state)


def tasks_on_mac(root, limit=20, running=None):
    """The `colibri` requests filed from subject `root`, newest first, each
    with its report's progress: what the Colibri panel lists. `running` is
    status.json's running task (`phase`)."""
    reps = jobs.reports(root)
    out = []
    for req in jobs.requests(root):
        if req.get("kind") != "colibri":
            continue
        rid = str(req.get("id") or "")
        rep = reps.get(rid) or {}
        out.append({"id": rid, "label": req.get("label") or "",
                    "brief": str(req.get("brief") or "")[:200],
                    "filed": req.get("filed") or 0,
                    "state": rep.get("state") or "filed",
                    "phase": phase(rep.get("state"), rep.get("task") or "",
                                   running),
                    "task": rep.get("task") or "",
                    "attempts": rep.get("attempts") or 0,
                    "deaths": rep.get("deaths") or 0,
                    "note": rep.get("note") or "",
                    "relay": [str(x) for x in rep.get("relay") or []][:6]})
    out.sort(key=lambda r: -_stamp(r["filed"]))
    return out[:limit]


# ---------------------------------------------------------------------------
# on demand: the task queue, the generation that works it, and the relay hook
# ---------------------------------------------------------------------------
# Colibri is not kept warm: filing a task starts a generation, which works the
# queue one task at a time and exits after `COLI_IDLE_MIN` idle minutes. Each
# generation submits its own clone, so a death costs one cold load and the
# clone resumes the task; three deaths fail it. `sacct` is refused, so the
# generation's last act writes `<state>/gen-<job>.exit`: gone with 0 there is
# a clean exit, gone without it a death.

HOP = 75            # coli-code: the generation its step ran in ended under it
NOTHING_YET = 76    # coli-code: no generation worth stepping into yet
LOAD_FAILED = 3     # the worker: this generation's engine never warmed
POLL = 30.0


# ---------------------------------------------------------------------------
# the task queue: one record per task, in `<queue root>/relay/state/colibri/`
# ---------------------------------------------------------------------------
# Ignored, because a task may name session content. A generation claims the
# oldest queued task, runs it and marks it; a dead one leaves it `running`
# with its job in `gen` for the clone to resume or, on the third death, fail.

TASK = "task"
TASK_STATES = ("queued", "running", "done", "failed")

# Deaths on one task before it is failed and not retried.
DEATH_CAP = 3

# What `task` (the short form a list shows) is cut to; `brief` is whole.
TASK_CHARS = 400

# A resumed client exiting faster than this did nothing (prefill alone takes
# minutes); the resume is retried fresh.
RESUME_FLOOR = 120.0

# A task id is the only name that reaches the filesystem: matched, not
# sanitised.
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")

# Task record fields. `baseline` is what git saw changed in the workspace at
# filing; `checked`, `changed` and `relay` are the relay's check. `thread` is
# read from old records and never written.
FIELDS = ("id", "kind", "agent", "task", "brief", "label", "thread",
          "workspace", "request", "queue", "attempts", "deaths", "gen",
          "session", "at", "from", "host", "ended", "ended_at", "reason",
          "looked", "turn_at", "baseline", "out", "checked", "changed",
          "relay")


def queue_dir(root):
    """The queue's directory under the queue root: `relay/state/colibri/`."""
    return os.path.join(root, jobs.COLIBRI)


def _task_path(root, tid):
    return os.path.join(queue_dir(root), "%s.json" % tid)


def write_task(root, rec):
    """Store one task record, atomically and never raising. True if stored."""
    tid = str(rec.get("id") or "")
    if not ID_RE.match(tid):
        return False
    target = _task_path(root, tid)
    tmp = "%s.tmp-%d" % (target, os.getpid())
    try:
        os.makedirs(queue_dir(root), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(dict((k, rec[k]) for k in FIELDS if k in rec), fh)
        os.replace(tmp, target)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _stamp(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def task_id(now=None):
    """`coli-<date>-<time>-<4 hex>`, which `ID_RE` accepts."""
    now = float(now or time.time())
    return "coli-%s-%s" % (time.strftime("%Y%m%d-%H%M%S", time.localtime(now)),
                           os.urandom(2).hex())


def file_task(root, label, brief, workspace, request="", now=None,
              baseline=None):
    """Write one queued task under `root`. The record, or None.
    `baseline` is `relay.workspace_changes` of its workspace, or None."""
    import uuid
    now = float(now or time.time())
    rec = {
        "id": task_id(now), "kind": TASK, "agent": "colibri",
        "task": (brief or "").strip()[:TASK_CHARS],
        "brief": (brief or "").strip(), "label": label or "",
        "workspace": workspace or "", "request": request or "",
        "queue": "queued", "attempts": 0, "deaths": 0, "gen": "",
        "session": str(uuid.uuid4()), "at": now, "from": "colibri queue",
        "host": machine.node_name(), "ended": "", "ended_at": 0.0,
        "reason": "", "looked": 0.0, "baseline": baseline, "out": "",
        "checked": 0.0, "changed": 0, "relay": [],
    }
    return rec if write_task(root, rec) else None


def tasks(root):
    """Every task in the queue, OLDEST first: the order they are worked in.
    Records still in the old place are moved in first."""
    jobs.migrate_state(root)
    out = []
    try:
        names = os.listdir(queue_dir(root))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(queue_dir(root), name), "r",
                      encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if (isinstance(rec, dict) and rec.get("kind") == TASK
                and ID_RE.match(str(rec.get("id") or ""))):
            out.append(rec)
    out.sort(key=lambda r: _stamp(r.get("at")))
    return out


def next_task(root):
    """The oldest queued task, or None."""
    for rec in tasks(root):
        if rec.get("queue") == "queued":
            return rec
    return None


def _current(root, rec):
    """That task as it is on disk now, or the one handed over: other writers
    touch it during the hours it runs."""
    try:
        with open(_task_path(root, str(rec.get("id") or "")), "r",
                  encoding="utf-8") as fh:
            got = json.load(fh)
        if isinstance(got, dict) and got.get("id") == rec.get("id"):
            return got
    except (OSError, ValueError):
        pass
    return dict(rec)


def claim_task(root, rec, gen, now=None):
    """Take a queued task for generation `gen`, once: an exclusive create per
    attempt, against the state read back off disk. The record, or None."""
    now = float(now or time.time())
    tid = str(rec.get("id") or "")
    if not ID_RE.match(tid):
        return None
    out = _current(root, rec)
    if out.get("queue") != "queued":
        return None
    attempt = int(out.get("attempts") or 0) + 1
    flag = os.path.join(queue_dir(root), "%s.task.%d" % (tid, attempt))
    try:
        os.makedirs(queue_dir(root), exist_ok=True)
        fd = os.open(flag, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        return None
    try:
        os.write(fd, ("%s %f\n" % (gen, now)).encode("utf-8"))
    finally:
        os.close(fd)
    out.update(queue="running", gen=str(gen), attempts=attempt, turn_at=now)
    return out if write_task(root, out) else None


def finish_task(root, rec, ok, reason="", now=None):
    """A task ended on its own terms: `done`, or `failed` and not retried."""
    now = float(now or time.time())
    out = _current(root, rec)
    out.update(queue="done" if ok else "failed", reason="" if ok else reason,
               ended_at=now, turn_at=0.0)
    write_task(root, out)
    return out


def requeue_task(root, rec, death=False, reason="", now=None):
    """Put a task back in the queue, counting a death where there was one."""
    out = _current(root, rec)
    out.update(queue="queued", gen="", turn_at=0.0)
    if death:
        out["deaths"] = int(out.get("deaths") or 0) + 1
    if reason:
        out["reason"] = reason
    write_task(root, out)
    return out


def task_verdict(rec, alive, ended_clean):
    """What a running task's generation leaving means. Pure.

        alive        job ids Slurm still lists
        ended_clean  job id -> did that generation end on purpose (exit 0)

    `"leave"` (not running, or its generation is there), `"requeue"` (ended on
    purpose, costing the task nothing), `"death"` (resume on the next one), or
    `("failed", reason)` on the third death.
    """
    if rec.get("queue") != "running":
        return "leave"
    gen = str(rec.get("gen") or "")
    if gen and gen in set(str(a) for a in alive):
        return "leave"
    if gen and ended_clean(gen):
        return "requeue"
    if int(rec.get("deaths") or 0) + 1 >= DEATH_CAP:
        return ("failed", "Colibri died under this task %d times, so it is "
                "not retried" % DEATH_CAP)
    return "death"


def recover_tasks(root, alive, ended_clean, now=None):
    """Apply `task_verdict` to every task. `[(id, verdict)]` for those it moved."""
    moved = []
    for rec in tasks(root):
        v = task_verdict(rec, alive, ended_clean)
        if v == "leave":
            continue
        if v == "requeue":
            requeue_task(root, rec, now=now)
        elif v == "death":
            requeue_task(root, rec, death=True,
                         reason="its generation died; resumed by the next",
                         now=now)
        else:
            out = finish_task(root, rec, False, v[1], now)
            out["deaths"] = int(rec.get("deaths") or 0) + 1
            write_task(root, out)
        moved.append((rec.get("id"), v))
    return moved


def update_task(root, rec, **fields):
    """Set `fields` on a task as it is on disk now. The record."""
    out = _current(root, rec)
    out.update(fields)
    write_task(root, out)
    return out


def idle_limit():
    """Seconds of empty queue before an on-demand generation exits."""
    try:
        return float(os.environ.get("COLI_IDLE_MIN") or 20) * 60.0
    except ValueError:
        return 20 * 60.0


def queue_root():
    """The libr-local-llm workspace holding the queue: `COLI_QUEUE_ROOT`, then
    `LLM_REPO`, then the walk; None where this machine lacks it."""
    for key in ("COLI_QUEUE_ROOT", "LLM_REPO"):
        said = os.environ.get(key)
        if said and os.path.isdir(said):
            return said
    try:
        found = subjects.find(WORKSPACE)
    except Exception:                                        # noqa: BLE001
        return None
    return found["root"] if found else None


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
    """`flock` on `<state>/queue.lock`, so filing and an idle exit never race
    (a task filed as the generation exits would wait for ever)."""

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
    """A job this machine submitted in the last `SUBMIT_GRACE` seconds, or "",
    because `sbatch` returns before `squeue` lists the job."""
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


def file(label, brief, workspace_root, request="", start=None, now=None):
    """Queue a task, and start a generation if none is queued or running.
    `(record, said)`; the record is None where nothing was queued. `label` is
    checked by the caller."""
    brief = (brief or "").strip()
    if not brief:
        return None, "a task needs a brief"
    root = queue_root()
    if not root:
        return None, "this machine has no %s workspace to queue in" % WORKSPACE
    with _Lock():
        rec = file_task(root, label, brief,
                                 subjects.identify(workspace_root), request, now,
                                 baseline=_baseline(workspace_root))
        if rec is None:
            return None, "the task could not be written under %s" % root
        return rec, "queued; " + _ensure(start)


def _baseline(workspace_root):
    """What git already sees changed in the task's workspace, so the finish
    check counts only the task's own; None counts every change."""
    from . import relay
    try:
        return relay.workspace_changes(workspace_root)
    except Exception:                                        # noqa: BLE001
        return None


def _started_at():
    try:
        with open(os.path.join(state_dir(), "started.json"), "r") as fh:
            return float((json.load(fh) or {}).get("at") or 0)
    except (OSError, ValueError, AttributeError):
        return 0.0


def _ensure(start=None):
    """Start a generation if none is queued or running, under the queue lock.
    Nothing starts where `squeue` cannot be asked, because an unreachable
    controller looks like an empty queue."""
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
    return said


def kick(start=None):
    """Start a generation for a task filed when none could start; "" or what
    happened. Only a task queued after the last start asks, so a generation
    that cannot load is not resubmitted every pass."""
    root = queue_root()
    if not root:
        return ""
    with _Lock():
        since = _started_at()
        owed = [r for r in tasks(root)
                if r.get("queue") == "queued" and float(r.get("at") or 0) > since]
        if not owed:
            return ""
        return _ensure(start)


# A task is read-only analysis: outputs go under the workspace's ignored,
# fenced `phi/`, it never changes a tracked file, and the relay fails one that
# leaves a change git can see. Only its public `RELAY:` lines come back.
FENCE = "phi/"

_TASK_RULES = (
    "YOUR WORK IS READ-ONLY ANALYSIS. Write every output -- transcripts, "
    "grades, tables, notes, scratch files -- under this workspace's `%s` "
    "directory, which git ignores and the PHI policy fences by name. Never "
    "edit, create, delete or rename a tracked file, and write nothing git "
    "would see: when you finish, this workspace is checked, and any change "
    "git can see fails the task. If this workspace has no `%s` directory, "
    "write nothing and say so. Do not commit or push." % (FENCE, FENCE))

_TASK_RELAY = (
    "End your last message with what you found, as lines that each begin "
    "`RELAY:`. They are published in a public repository: aggregate numbers "
    "only -- counts, rates, scores -- and no patient-level values, no "
    "identifiers, no quoted session text, no paths.")

TASK_PROMPT = (
    "This is a task from the Colibri queue, set going by the owner. Nobody is "
    "watching this session, so do not stop to ask; do the task, here.\n\n"
    "%s\n\n" + _TASK_RULES + "\n\n"
    "Write files as you finish them rather than holding them: the node under "
    "you can go away, and this conversation is then resumed on another.\n\n"
    + _TASK_RELAY
)

TASK_RESUME_PROMPT = (
    "Your conversation is resumed. The node under you ended; nothing you did "
    "caused it, and your work on disk is untouched. Carry on from where you "
    "stopped, and redo only the tool call that was in flight. The task "
    "again:\n\n%s\n\n" + _TASK_RULES + "\n\n"
    "Write files as you finish them. " + _TASK_RELAY
)


def output_path(rec):
    """Where a task's client output goes, `COLI_SESSION_ROOT/tasks/<id>.out`
    behind the fence, or None where that root is not a `phi/` directory: the
    output can quote session content."""
    root = os.environ.get("COLI_SESSION_ROOT") or ""
    tid = str(rec.get("id") or "")
    if not root or "phi" not in os.path.normpath(root).split(os.sep):
        return None
    if not tid or "/" in tid or tid.startswith("."):
        return None
    return os.path.join(root, "tasks", tid + ".out")


def run_task(rec, job):
    """Run one task through `coli-code` inside generation `job`; its exit code.
    Output goes behind the fence (`output_path`), never to the counts-only job
    log. A task begun before resumes by name, falling back to a fresh
    conversation when the resume fails in seconds."""
    cmd = _tool("coli-code", "COLI_CODE")
    where = subjects.find(rec.get("workspace") or "")
    if not cmd or not where:
        return 2
    env = dict(os.environ, COLI_SESSION_ID=str(rec.get("session") or ""),
               COLI_JOB=str(job))
    resume = int(rec.get("attempts") or 0) > 1
    out = output_path(rec)
    if out:
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
        except OSError:
            out = None
    root = queue_root()
    if root:
        update_task(root, rec, out=out or "")

    def go(cont):
        argv = [cmd, "-d", where["root"], "--yes"] + (["-c"] if cont else [])
        prompt = (TASK_RESUME_PROMPT if cont else TASK_PROMPT) % rec.get("brief")
        t0 = time.time()
        sink = None
        try:
            sink = open(out, "a") if out else None
        except OSError:
            sink = None
        try:
            rc = subprocess.run(argv + ["--", prompt], stdin=subprocess.DEVNULL,
                                stdout=sink or subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env).returncode
        except OSError:
            rc = 2
        finally:
            if sink:
                sink.close()
        return rc, time.time() - t0

    rc, ran = go(resume)
    if resume and rc not in (0, HOP, NOTHING_YET) and ran < RESUME_FLOOR:
        rc, ran = go(False)
    return rc


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def recover(job):
    """Resume or fail what dead generations left running. Skipped where
    `squeue` cannot be asked or omits this job, which would read as every
    generation dead."""
    rows = _all_jobs()
    if rows is None:
        return []
    alive = [r["id"] for r in rows]
    if job and str(job) not in alive:
        return []
    return recover_tasks(queue_root(), alive, ended_clean)


def work(job, demand=True, server_pid=None, idle=None, run=None, ready=None,
         clock=time.time, sleep=time.sleep, poll=POLL, say=None):
    """The queue's worker inside generation `job`; returns its exit code: 0 is
    a clean idle exit, anything else a death the clone repairs. `demand`
    False (`--stay`) never exits on idle."""

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
        rec = next_task(root)
        if rec is not None:
            got = claim_task(root, rec, job, clock())
            if got is None:
                sleep(poll)
                continue
            tell("start id=%s attempt=%d deaths=%d" % (
                got["id"], got["attempts"], int(got.get("deaths") or 0)))
            rc = run(got, job)
            if rc == 0:
                finish_task(root, got, True, now=clock())
                tell("done id=%s" % got["id"])
            elif rc == HOP:
                tell("hop id=%s: the generation ended under it" % got["id"])
                return 1
            elif rc == NOTHING_YET:
                requeue_task(root, got, now=clock())
                tell("wait id=%s: no server to step into yet" % got["id"])
                sleep(poll)
            else:
                finish_task(root, got, False,
                                     "coli-code exited %d" % rc, clock())
                tell("failed id=%s exit=%d" % (got["id"], rc))
            last = clock()
            continue
        if demand and clock() - last >= idle:
            with _Lock():
                if next_task(root) is None:
                    open(_closing_path(job), "w").close()
                    tell("idle: the queue has been empty for %d min" % (idle // 60))
                    return 0
            continue
        sleep(poll)


# --------------------------------------------------------------- the relay
# The relay's hook. A `colibri` request is filed as a task, and each pass asks
# `relay_pass` for reports. A finished task is checked (`relay.check_task`):
# any change git sees since its baseline fails it and stays on the cluster.
# Reports carry state, counts and public `RELAY:` lines, never the brief or a
# path.

def relay_report(rec):
    """A task as a relay report: state, counts and its public `RELAY:` lines,
    never the brief."""
    q = rec.get("queue")
    state = {"queued": "submitted", "running": "running",
             "failed": "failed"}.get(q, "running")
    note = ""
    if q == "done":
        if rec.get("checked"):
            state = "completed"
            note = ("Colibri finished, and its workspace has no change git can "
                    "see.")
        else:
            note = "Colibri finished; the check of its workspace is next."
    elif q == "failed":
        note = rec.get("reason") or "the task failed"
        if int(rec.get("changed") or 0):
            note += (". %d path(s) changed; they stay on the cluster, "
                     "uncommitted, for the owner, and nothing was committed."
                     % int(rec["changed"]))
    elif rec.get("deaths"):
        note = "resumed after %d death(s) of its generation" % int(rec["deaths"])
    out = {"id": rec.get("request"), "kind": "colibri", "state": state,
           "task": rec.get("id"), "attempts": int(rec.get("attempts") or 0),
           "deaths": int(rec.get("deaths") or 0),
           "submitted": float(rec.get("at") or 0), "note": note}
    if rec.get("checked"):
        out["changed"] = int(rec.get("changed") or 0)
        out["relay"] = [str(l) for l in rec.get("relay") or []]
    if rec.get("gen"):
        out["jobid"] = str(rec["gen"])
    if q in ("done", "failed"):
        out["ended"] = float(rec.get("ended_at") or 0)
    return out


def relay_file(ws_root, req, start=None, now=None):
    """File a checked `colibri` request as a task. Its first report."""
    rec, said = file(req.get("label"), req.get("brief"), ws_root,
                     request=req.get("id") or "", start=start, now=now)
    if rec is None:
        return {"id": req.get("id"), "kind": "colibri", "state": "refused",
                "problems": [said], "note": said}
    return relay_report(rec)


def settle(root, rec, got, now=None):
    """Apply a check's verdict to a done task: no change keeps it done, any
    fails it with `relay.CHANGED`. Either way it is not checked again."""
    from . import relay
    changed = int(got.get("changed") or 0)
    rec = update_task(root, rec, checked=float(now or time.time()),
                               changed=changed,
                               relay=list(got.get("relay") or []))
    if changed:
        rec = finish_task(root, rec, False, relay.CHANGED, now)
    return rec


def relay_pass(check=None, now=None, start=None):
    """`[(workspace root, report)]` for every task a request filed. A done
    task whose `check` returns None stays unchecked until next pass. Tasks
    filed on the cluster by `board colibri` are checked the same way, with no
    report. Tasks filed when nothing could start are `kick`ed here."""
    root = queue_root()
    if not root:
        return []
    kick(start)
    out = []
    for rec in tasks(root):
        where = subjects.find(rec.get("workspace") or "")
        if not where:
            continue
        if (rec.get("queue") == "done" and not rec.get("checked")
                and check is not None):
            got = check(where["root"], rec)
            if got is not None:
                rec = settle(root, rec, got, now)
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
