"""jobs.py -- long work registered to a thread, and reporting itself.

A Slurm job a turn submits with a bare `sbatch` is work the board cannot see:
the thread it belongs to reads `open` while it runs, and nobody hears when it
ends. So a turn submits through `board job`, which runs the `sbatch` and
appends one record to the workspace's job registry:

    {thread, jobid, cmd, cwd, produces, log, submitted}

THE REGISTRY IS APPEND-ONLY. The poll that sees a job change state appends a
record carrying `state` (and, at the end, `exit` and `ended`) for the same job
id, and a reader folds the records in file order -- `threads.merged`. Two
writers never rewrite each other's lines.

WHERE IT LIVES is `live/jobs.jsonl` where git can see it there, and
`jobs.jsonl` at the workspace root where `live/` is ignored wholesale. It is
tracked either way, because a job outlives the machine that submitted it.

THE CLUSTER'S RELAY POLLS IT (`tutorboard/relay.py`, every five minutes).
`sacct` is refused on this cluster, so a job's end is read from `squeue` and
an exit-code file: `submit_recipe` wraps every recipe so its last act writes
its exit code to `relay/state/<key>.exit`, which is ignored. A job that has
left `squeue` with that file ended with that code; one that left without it
DIED (timeout, node failure, a cancel). A raw `sbatch` has no wrapper, so its
leaving is ENDED, exit unknown. An ending is claimed once (`O_EXCL`, so two
passes never report the same job twice), appended, and a `[job]` line is
dropped in the inbox. That line wakes a turn the way `[direction]` does.

A MACHINE WITHOUT SLURM FILES A REQUEST INSTEAD (the relay section below), and
`view` is the one registry a reader sees: local jobs, requests, and the
cluster's reports on them, merged.

Standard library only, like everything else.
"""

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import time

from . import fenced
from .course import threads as course_threads

NAME = "jobs.jsonl"

# A job missing from `squeue` this soon after submission, with no exit file,
# is given one more pass before it is called DIED.
GRACE = 60

# Where a wrapped job's exit code, its wrapper and the relay's own registry
# live in a workspace. Ignored by the root .gitignore.
STATE = os.path.join("relay", "state")

CMD_CHARS = 600


def registry(root, create=False):
    """The registry's path in this workspace. Never creates the file.

    Whichever already exists wins. With neither, a reader is handed a path that
    holds nothing; a writer (`create`) gets `live/jobs.jsonl` unless git
    ignores it there, and then `jobs.jsonl` at the root. Git is asked only
    then, because the board reads the registry on every payload.
    """
    top = os.path.join(root, NAME)
    inner = os.path.join(root, "live", NAME)
    if os.path.isfile(top):
        return top
    if os.path.isfile(inner) or not create:
        return inner
    return top if ignored(root, "live/" + NAME) else inner


def ignored(root, rel):
    """Would git ignore this workspace-relative path? Asked of git."""
    try:
        p = subprocess.run(["git", "check-ignore", "-q", rel], cwd=root,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0


def append(root, rec, path=None):
    """Append one record to the registry, or to `path` (the relay's own)."""
    path = path or registry(root, create=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    course_threads._cache.pop(os.path.realpath(root), None)
    return path


def _lines(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out


def records(root, path=None):
    """`{jobid: record}`, folded. `path` reads the relay's registry instead."""
    raw = _lines(path) if path else course_threads.jobs_of(root)
    return course_threads.merged(raw)


def state_dir(root):
    return os.path.join(root, STATE)


def relay_registry(root):
    """The jobs the relay submitted for requests. Ignored: their tracked
    record is the request's report, and the cluster commits nothing else."""
    return os.path.join(state_dir(root), "jobs.jsonl")


# ---------------------------------------------------------------------------
# submitting
# ---------------------------------------------------------------------------
def submit(root, thread, argv, produces=(), cwd=None, run=subprocess.run,
           now=None, export=(), env=None, path=None, extra=None):
    """Run `sbatch`, and register the job to `thread`. `(record, error)`.

    `argv` must start with `sbatch`. `--parsable` is added where it is missing,
    so the id is read rather than scraped out of a sentence. `env` is the
    environment sbatch runs in; `path` the registry it is recorded in; `extra`
    fields the record carries besides (a `cmd` there overrides the argv's).
    """
    argv = list(argv or [])
    if not argv or os.path.basename(argv[0]) != "sbatch":
        return None, ("`board job` submits with sbatch, and this is %r. Put "
                      "the sbatch command after `--`." % (argv[:1] or [""])[0])
    cwd = os.path.abspath(cwd or os.getcwd())
    sent = argv[:1] + ([] if "--parsable" in argv else ["--parsable"]) + argv[1:]
    kw = {"env": env} if env is not None else {}
    try:
        p = run(sent, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=120, **kw)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "sbatch did not run: %s" % exc
    if p.returncode != 0:
        return None, ("sbatch refused it (exit %d): %s"
                      % (p.returncode, (p.stderr or p.stdout or "").strip()[-400:]))
    words = (p.stdout or "").strip().split()
    jobid = words[-1].split(";")[0] if words else ""
    if not jobid.split("_")[0].isdigit():
        return None, ("sbatch ran but printed no job id (%r), so nothing was "
                      "registered" % (p.stdout or "").strip()[-200:])
    out, err = logs_of(jobid, cwd, run=run)
    rec = {
        "thread": thread,
        "jobid": jobid,
        "cmd": " ".join(shlex.quote(a) for a in _redacted(argv))[:CMD_CHARS],
        "cwd": _relative(root, cwd),
        "produces": list(produces or []),
        "log": _relative(root, out),
        "submitted": float(now or time.time()),
    }
    if err and err != out:
        rec["err"] = _relative(root, err)
    if export:
        rec["export"] = list(export)
    rec.update(extra or {})
    if path:
        # The relay's registry is ignored, so it may hold where the log really
        # is, outside the workspace too: the `RELAY:` lines are read out of it.
        rec["log_path"], rec["err_path"] = out, err
    append(root, rec, path=path)
    return rec, ""


def header_of(text):
    """The `#SBATCH` lines of a script's header, which sbatch reads, in order."""
    out = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            break
        if s.startswith("#SBATCH"):
            out.append(s)
    return out


_ARRAY_RE = re.compile(r"^#SBATCH\s+(?:--array[=\s]|-a\s*)\s*(\S+)")


def array_tasks(header):
    """How many tasks the header's `--array` asks for, None without one, or
    0 where the spec cannot be read (every task file is then required, and
    an unknown count reads as a death rather than a success). Pure."""
    spec = None
    for h in header or ():
        m = _ARRAY_RE.match(h.strip())
        if m:
            spec = m.group(1)
    if spec is None:
        return None
    total = 0
    for part in spec.split("%", 1)[0].split(","):
        m = re.fullmatch(r"(\d+)(?:-(\d+)(?::(\d+))?)?", part.strip())
        if not m:
            return 0
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        step = int(m.group(3) or 1)
        if hi < lo or step < 1:
            return 0
        total += len(range(lo, hi + 1, step))
    return total


def wrapper(header, command, exitfile, name=""):
    """A batch script: `header`, then `command`, then the exit code written to
    `exitfile` as its last act. Pure.

    No trap: a job killed at its time limit must leave NO file, because that
    absence is how a death is told from an ending. An array task writes
    `<stem>_<task>.exit`.
    """
    lines = ["#!/bin/bash"] + list(header)
    if name and not any(re.match(r"#SBATCH\s+(--job-name|-J)\b", h)
                        for h in header):
        lines.append("#SBATCH --job-name=%s" % name)
    stem = exitfile[:-len(".exit")] if exitfile.endswith(".exit") else exitfile
    lines += [
        "# Written by the relay: runs the command below, then records its exit",
        "# code. That file is how the end of this job is read without sacct.",
        " ".join(shlex.quote(c) for c in command),
        "code=$?",
        'out=%s"${SLURM_ARRAY_TASK_ID:+_$SLURM_ARRAY_TASK_ID}".exit'
        % shlex.quote(stem),
        'printf \'%s\\n\' "$code" > "$out.tmp" && mv -f "$out.tmp" "$out"',
        'exit "$code"',
    ]
    return "\n".join(lines) + "\n"


def local_key(now=None):
    """The key of a job `board job` submits directly: never a request id."""
    return "local-%d-%d" % (int(float(now or time.time()) * 1000), os.getpid())


def submit_script(root, thread, header, command, key, label, produces=(),
                  export=(), env=None, run=subprocess.run, now=None,
                  sbatch_env=None, path=None, extra=None):
    """Write the wrapper for `command` at `relay/state/<key>.sbatch` and submit
    it from the workspace root. `(record, error)`.

    `env` is the `{NAME: value}` the job gets through `--export=ALL,...`,
    checked by `validate` before it gets here.
    """
    env = dict(env or {})
    sdir = state_dir(root)
    os.makedirs(sdir, exist_ok=True)
    exitfile = os.path.join(sdir, key + ".exit")
    for stale in [exitfile] + _array_exits(exitfile):
        try:
            os.remove(stale)
        except OSError:
            pass
    script = os.path.join(sdir, key + ".sbatch")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-",
                  os.path.splitext(os.path.basename(label.split()[0]))[0])[:40]
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(wrapper(header, command, exitfile, name=name))
    sent = ["sbatch"]
    if env:
        sent.append("--export=ALL," + ",".join(
            "%s=%s" % (k, env[k]) for k in sorted(env)))
    sent.append(script)
    shown = " ".join([label] + ["%s=%s" % (k, env[k]) for k in sorted(env)])
    fields = {"cmd": shown[:CMD_CHARS], "key": key,
              "exitfile": _relative(root, exitfile)}
    tasks = array_tasks(header)
    if tasks is not None:
        fields["array_tasks"] = tasks
    fields.update(extra or {})
    return submit(root, thread, sent, produces=produces, cwd=root, run=run,
                  now=now, export=export, env=sbatch_env, path=path,
                  extra=fields)


def submit_recipe(root, thread, recipe, env=None, produces=(), export=(),
                  key=None, run=subprocess.run, now=None, sbatch_env=None,
                  path=None, extra=None):
    """Submit a tracked recipe, wrapped so its ending can be read.

    The recipe runs where it is, under `bash`, from the workspace root: its
    `#SBATCH` lines, `$SLURM_SUBMIT_DIR` and log paths are what a bare sbatch
    of it would give.
    """
    full = os.path.join(root, recipe)
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            header = header_of(fh.read())
    except OSError as exc:
        return None, "the recipe %s cannot be read: %s" % (recipe, exc)
    return submit_script(root, thread, header, ["bash", full],
                         key or local_key(now), recipe, produces=produces,
                         export=export, env=env, run=run, now=now,
                         sbatch_env=sbatch_env, path=path, extra=extra)


def _redacted(argv):
    """The argv with every `--export` value reduced to its variable names.

    The registry can be tracked in a public repository, and an exported value
    is where a path to protected storage goes.
    """
    out, hide = [], False
    for a in argv:
        if hide:
            out.append(_names(a))
            hide = False
        elif a == "--export":
            out.append(a)
            hide = True
        elif a.startswith("--export="):
            out.append("--export=" + _names(a[len("--export="):]))
        else:
            out.append(a)
    return out


def _names(spec):
    return ",".join(p.split("=", 1)[0] + ("=..." if "=" in p else "")
                    for p in spec.split(","))


def _relative(root, path):
    """A path inside the workspace as workspace-relative; anything else by its
    file name alone, because the registry may be public and an outside path
    names storage it has no business naming."""
    if not path:
        return ""
    real = os.path.realpath(path)
    base = os.path.realpath(root)
    if real == base:
        return "."
    if real.startswith(base + os.sep):
        return os.path.relpath(real, base)
    return os.path.basename(real)


def logs_of(jobid, cwd, run=subprocess.run):
    """`(stdout, stderr)`: where the job writes, as Slurm says, "" for unknown.

    An array task's `%a` becomes `*`, because the id sbatch prints is the
    array's and each task writes its own file: the path is a glob.

    Asked once, at submission, while `scontrol` still knows the job: it forgets
    a finished one within minutes, and the log is what a failure is reported
    with.
    """
    try:
        p = run(["scontrol", "show", "job", "-o", str(jobid)], cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "", ""
    fields = {}
    for word in (p.stdout or "").split():
        k, _, v = word.partition("=")
        fields.setdefault(k, v)
    base = str(jobid).split("_")[0]

    def filled(path):
        if not path:
            return ""
        for pat, val in (("%j", base), ("%A", base), ("%a", "*"),
                         ("%x", fields.get("JobName", "")),
                         ("%u", fields.get("UserId", "").split("(")[0]),
                         ("%%", "%")):
            path = path.replace(pat, val)
        return path if os.path.isabs(path) else os.path.join(cwd, path)
    return filled(fields.get("StdOut", "")), filled(fields.get("StdErr", ""))


# ---------------------------------------------------------------------------
# polling
# ---------------------------------------------------------------------------
def squeue(run=subprocess.run, user=None):
    """`{base jobid: state}` for this user's jobs Slurm still holds. None when
    squeue could not be asked at all, which is not the same as knowing nothing.

    `sacct` is refused on this cluster, so this is all Slurm says: a job is
    PENDING, RUNNING, or gone. An array is under its base id while any of its
    tasks is, RUNNING if any task is.
    """
    import getpass
    try:
        p = run(["squeue", "-h", "-u", user or getpass.getuser(),
                 "-o", "%i|%T"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=60)
    except (OSError, subprocess.SubprocessError, KeyError):
        return None
    if p.returncode != 0:
        return None
    out = {}
    for line in (p.stdout or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 2 or not parts[0]:
            continue
        base = parts[0].split("_")[0].split(".")[0]
        state = parts[1].strip().upper() or "PENDING"
        if out.get(base) != "RUNNING":
            out[base] = state
    return out


def _array_exits(exitfile):
    stem = exitfile[:-len(".exit")] if exitfile.endswith(".exit") else exitfile
    return sorted(glob.glob(glob.escape(stem) + "_*.exit"))


def exit_of(root, rec):
    """`(code, mtime)` the wrapper wrote for this job, or None if it wrote
    none. An array is the worst of its tasks' codes."""
    rel = rec.get("exitfile")
    if not rel:
        return None
    full = os.path.join(root, rel)
    # Listing the directory first makes an NFS client revalidate it, so a
    # file written on a compute node seconds ago is not missed on a cached
    # negative lookup.
    try:
        os.listdir(os.path.dirname(full))
    except OSError:
        pass
    tasks = rec.get("array_tasks")
    arrayed = _array_exits(full)
    if tasks is not None and not isinstance(tasks, bool):
        # An array task killed at its limit writes no file of its own, so a
        # task file missing is a death, whatever the others wrote.
        if not tasks or len(arrayed) < int(tasks):
            return None
    found = ([full] if os.path.isfile(full) else []) + arrayed
    codes, latest = [], 0.0
    for path in found:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                codes.append(int(fh.read().strip() or "1"))
            latest = max(latest, os.path.getmtime(path))
        except (OSError, ValueError):
            codes.append(1)
    if not codes:
        return None
    bad = [c for c in codes if c != 0]
    return (bad[0] if bad else 0), latest


def ending(root, rec, now):
    """`(state, exit, ended)` for a job that has left `squeue`, or None while
    it is too fresh to call.

    With the wrapper's file: COMPLETED on 0, FAILED otherwise. Wrapped and
    without it: DIED -- a time limit, a node failure or a cancel. Not wrapped
    (a raw sbatch): ENDED, exit unknown.
    """
    got = exit_of(root, rec)
    if got is not None:
        code, when = got
        return (("COMPLETED" if code == 0 else "FAILED"), "%d:0" % code,
                time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(when)))
    if now - float(rec.get("submitted") or now) < GRACE:
        return None
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now))
    if rec.get("exitfile"):
        return "DIED", "", stamp
    return "ENDED", "", stamp


# A job gone from squeue with no exit file is called DIED only once it has
# been gone this long, seen by at least two passes: the wrapper writes the
# file on a compute node, and another node's NFS view can lag behind it.
GONE_GRACE = 60


# A claim older than this on an ending still not marked reported is a reader
# that died holding it, and the next pass takes it over.
CLAIM_STALE = 10 * 60


def _marker(root, jobid, claims=None):
    return os.path.join(claims or os.path.join(root, "live", "jobs.reported"),
                        str(jobid).replace("/", "_"))


def _claim(root, jobid, now=None, claims=None):
    """Exactly one reader reports each ending. True for the one that may."""
    target = _marker(root, jobid, claims)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            age = float(now or time.time()) - os.path.getmtime(target)
            if age < CLAIM_STALE:
                return False
            os.remove(target)
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError:
        return False
    os.close(fd)
    return True


def _unclaim(root, jobid, claims=None):
    try:
        os.remove(_marker(root, jobid, claims))
    except OSError:
        pass


def relay_claims(root):
    return os.path.join(state_dir(root), "jobs.reported")


def poll(root, run=subprocess.run, now=None, path=None, claims=None):
    """Ask squeue about every unfinished job. Returns the ones that ended now.

    `path` and `claims` are the relay's registry and claim directory; the
    default is the workspace's own. A state change short of the end (PENDING
    to RUNNING) is appended too, so the board can say which. Nothing is
    appended for a job whose state is unchanged.
    """
    now = float(now or time.time())
    out = []
    every = records(root, path).values()
    # An ending recorded but never reported -- its reader died, or its inbox
    # line could not be written -- is offered again, without asking squeue.
    for j in every:
        if (course_threads.finished(j) and not j.get("reported")
                and _claim(root, j["jobid"], now, claims)):
            out.append(dict(j))
    open_jobs = [j for j in every if not course_threads.finished(j)
                 and str(j.get("state") or "").upper()
                 != course_threads.REQUESTED]
    if not open_jobs:
        return out
    said = squeue(run=run)
    if said is None:
        return out
    for j in open_jobs:
        base = str(j["jobid"]).split("_")[0]
        state = said.get(base)
        if state is not None and state.rstrip("+") not in course_threads.TERMINAL:
            if state != j.get("state") or j.get("gone_at"):
                append(root, {"jobid": j["jobid"], "thread": j.get("thread"),
                              "state": state, "seen": now, "gone_at": 0},
                       path=path)
            continue
        # Gone from squeue, or there in a terminal state it is about to leave
        # by: either way the wrapper's file, written before the job left, says
        # how it ended.
        got = ending(root, j, now)
        if got is None:
            continue
        state, code, end = got
        if state == "DIED":
            gone = j.get("gone_at")
            if not gone:
                append(root, {"jobid": j["jobid"], "gone_at": now}, path=path)
                continue
            if now - float(gone) < GONE_GRACE:
                continue
        # The ending is recorded before it is claimed, so a reader that dies
        # between the two leaves a finished job, not a running one.
        end_rec = {"jobid": j["jobid"], "thread": j.get("thread"),
                   "state": state, "exit": code, "ended": end}
        append(root, end_rec, path=path)
        if not _claim(root, j["jobid"], now, claims):
            continue
        done = dict(j)
        done.update(end_rec)
        out.append(done)
    return out


def failed(rec):
    """Did it end any way but cleanly?"""
    state = str(rec.get("state") or "").split()[:1]
    code = str(rec.get("exit") or "0:0")
    return (state != ["COMPLETED"]) or code.split(":")[0] not in ("", "0")


def _thread_title(root, tid):
    title = tid or "no thread"
    try:
        clean, _ = course_threads.read(root)
        one = course_threads.thread(clean, tid) if clean else None
        if one:
            title = "%s (%s)" % (one["id"], one["title"])
    except Exception:                                        # noqa: BLE001
        pass
    return title


def _relay_said(value):
    """A report's `relay` lines as a list, whichever shape the cluster wrote."""
    if isinstance(value, str):
        return [l for l in value.splitlines() if l.strip()]
    return [str(l) for l in (value or []) if str(l).strip()]


def relay_sense(root, rec):
    """The inbox line for a cluster report: `sense` for a request.

    Everything the turn reports is in the report, because the log stays on the
    cluster: the state, the exit, which `produces` paths now exist there, which
    exports landed here, the `RELAY:` lines and the note. A failure the Mac
    repairs opens `[repair]` rather than `[job]` (`repairs`).
    """
    tid = rec.get("thread")
    state = str(rec.get("state") or "")
    repair = repairs(root, rec)
    lines = [
        "[%s] A cluster report on thread %s has come back: %s."
        % (REPAIR if repair else "job", _thread_title(root, tid),
           state.lower() or "unknown"),
        "",
        "  request  %s (%s)" % (rec.get("request"), rec.get("kind") or "recipe"),
        "  state    %s" % state,
    ]
    if rec.get("slurm"):
        lines.append("  job      %s, on the cluster" % rec["slurm"])
    lines += ["  exit     %s" % (rec.get("exit") or "unknown"),
              "  ended    %s" % (rec.get("ended") or "unknown"),
              "  command  %s" % rec.get("cmd", "")]
    if rec.get("error"):
        lines.append("  error    %s" % rec["error"])
    made = set(rec.get("produced") or [])
    if rec.get("produces"):
        lines += ["", "What it was to produce, as the cluster found it:"]
        lines += ["  %s %s" % ("present" if p in made else "MISSING", p)
                  for p in rec["produces"]]
    landed = list(rec.get("exported") or [])
    if landed or rec.get("export"):
        lines += ["", "Exports, copied into exports/ (pull brought them):"]
        lines += ["  landed   %s" % p for p in landed]
        lines += ["  NOT      %s" % p for p in rec.get("export") or []
                  if p not in landed and "exports/" + p not in landed]
    said = _relay_said(rec.get("relay"))
    if said:
        lines += ["", "What the job printed behind RELAY:"]
        lines += ["  " + l for l in said]
    if rec.get("problems"):
        lines += ["", "Why the cluster refused it:"]
        lines += ["  - %s" % p for p in rec["problems"]]
    if rec.get("note"):
        lines += ["", "The cluster's note:", "  " + str(rec["note"])]
    lines += ["", "DO THIS: write one card reporting what finished, what it "
              "produced, any non-zero exit, and the RELAY: lines."]
    move_on = True
    if state == "REFUSED" and rec.get("fixes"):
        lines += _refused_fix_said(rec)
        move_on = False
    elif state == "REFUSED":
        lines.append("The cluster would not run it. Fix what it lists and file "
                     "it again through `board job`.")
    elif repair:
        said, move_on = _repair_said(root, rec)
        lines += said
    elif rec.get("kind") == "colibri" and rec.get("changed"):
        lines.append("It FAILED its check: the Colibri task changed %d "
                     "tracked path(s) in its workspace, and its work belongs "
                     "in ignored locations. Nothing was committed; the changes "
                     "stay on the cluster, uncommitted, for the owner to "
                     "settle, and the report names none of them."
                     % int(rec["changed"]))
    elif failed(rec):
        lines.append("It did NOT end cleanly. Its log stays on the cluster, "
                     "and the RELAY: lines are what it says here.")
    elif rec.get("fixes"):
        lines.append("It ended cleanly, so the repair of %s is done: the card "
                     "says what the fix was." % rec["fixes"])
    if move_on:
        lines.append("Then move the thread on with `board thread`: tick the "
                     "task this request was, and add the next one. A "
                     "follow-up goes through `board job`, never a bare "
                     "sbatch.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# a failed relay job: repaired on the Mac
# ---------------------------------------------------------------------------
# A FAILED RECIPE WAKES A `[repair]` TURN ON THE MAC, a doing turn whatever the
# workspace teaches under (`board brief`, `doing_now` in bin/tutor). It reads
# the report, the `RELAY:` lines its recipe's failure helper printed
# (`slurm_jobs/lib/relay_trap.sh`), and the failing code, and then either
# fixes it here -- check, `board push`, rerun through `board job --fixes` --
# or, where the report does not say enough, files a DIAGNOSTIC: a tracked
# recipe that prints `RELAY:` lines and produces nothing (`board diagnose`).
# A completed diagnostic wakes the same kind of turn to apply what it found.
#
# No model runs beside the data. `MAX_FIXES` automatic attempts per failure,
# diagnostics and reruns alike, counted off `relay/requests/`, and then the
# owner decides; `board job --fresh` is the owner's way to start again.

# The signal a repair turn is woken with.
REPAIR = "repair"


def ended_failed(rec):
    """Did this relayed record end, and not cleanly? A refused, pending or
    running request has not failed."""
    state = str(rec.get("state") or "")
    return state == "FAILED" or (state == "COMPLETED" and failed(rec))


def _filed_key(r):
    f = r.get("filed")
    f = 0.0 if isinstance(f, bool) or not isinstance(f, (int, float)) else f
    return (float(f), str(r.get("id") or ""))


def _request(root, rid):
    return next((r for r in requests(root) if r.get("id") == rid), None)


def attempts(root, origin):
    """The requests filed to repair `origin`, oldest first. Each diagnostic
    and each rerun counts against `MAX_FIXES`."""
    return sorted((r for r in requests(root) if r.get("fixes") == origin),
                  key=_filed_key)


def is_diagnostic(root, rec):
    """Is this request, filed against a failure, a diagnostic rather than a
    rerun? A rerun runs the failed request's own recipe; anything else asks."""
    origin = rec.get("fixes")
    if not origin:
        return False
    first = _request(root, origin) or {}
    mine = _request(root, rec.get("request") or rec.get("id")) or {}
    return (mine.get("kind") == "recipe"
            and course_threads._rel(mine.get("recipe"))
            != course_threads._rel(first.get("recipe")))


def _last_run(root, origin):
    """The newest request that ran `origin`'s own recipe: its last rerun, or
    `origin` itself."""
    first = _request(root, origin) or {}
    recipe = course_threads._rel(first.get("recipe"))
    runs = [r for r in attempts(root, origin) if r.get("kind") == "recipe"
            and course_threads._rel(r.get("recipe")) == recipe]
    return runs[-1] if runs else first


def repairs(root, rec):
    """Does this report wake a repair turn? A recipe that failed, and a
    diagnostic that came back."""
    if rec.get("kind") != "recipe":
        return False
    if ended_failed(rec):
        return True
    return (str(rec.get("state") or "") == "COMPLETED"
            and is_diagnostic(root, rec))


def diagnostics(root):
    """`[(recipe, its variables)]`: this workspace's diagnostic recipes, the
    `.sbatch` files named `diagnose*`."""
    out = []
    for depth in range(1, 5):
        pattern = os.path.join(root, *(["*"] * depth + ["diagnose*.sbatch"]))
        for path in sorted(glob.glob(pattern)):
            rel = course_threads._rel(os.path.relpath(path, root))
            if not rel or rel.startswith(("live/", "relay/", "results/")):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    names, _ = declarations(fh.read())
            except OSError:
                names = {}
            out.append((rel, sorted(names)))
    return out


_SITE_RE = re.compile(r"\bat ([A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+):(\d+)")
_STEP_LINE_RE = re.compile(r"\bfailed: exit \d+ after line (\d+)")


def failure_sites(relay):
    """`(["file:line", ...], recipe line or "")` out of a report's RELAY
    lines: where the Python failed, and the recipe line the shell stopped
    after (`slurm_jobs/lib/relay_hook.py`, `relay_trap.sh`)."""
    sites, step = [], ""
    for line in _relay_said(relay):
        body = line.split("RELAY:", 1)[-1].strip()
        m = _SITE_RE.search(body)
        if m and body.startswith("error"):
            site = "%s:%s" % m.groups()
            if site not in sites:
                sites.append(site)
        m = _STEP_LINE_RE.search(body)
        if m and body.startswith("recipe"):
            step = m.group(1)
    return sites, step


def report_path(rid):
    """The report of request `rid`, workspace-relative."""
    return "%s/reports/%s.json" % (RELAY, rid)


def _rerun_argv(tid, origin, req):
    """`board job` for the request `req`, as the rerun of `origin`."""
    req = req or {}
    argv = ["board", "job", tid or "", "--fixes", origin]
    for p in _strings(req.get("produces")):
        argv += ["--produces", p]
    for p in _strings(req.get("export")):
        argv += ["--export", p]
    argv += ["--", str(req.get("recipe") or "<recipe>")]
    env = req.get("env") if isinstance(req.get("env"), dict) else {}
    argv += ["%s=%s" % (k, env[k]) for k in sorted(env)]
    return argv


def _thread_files_and_check(root, tid):
    """`(the thread's files, its own check script, the workspace's check)`,
    each workspace-relative or `""`."""
    from .course import config as course_config
    files, own = [], ""
    try:
        clean, _ = course_threads.read(root)
        one = course_threads.thread(clean, tid) if clean else None
        files = [f for f in (course_threads._rel(p)
                             for p in (one or {}).get("files") or []) if f]
        own = str((one or {}).get("check") or "")
    except Exception:                                        # noqa: BLE001
        pass
    try:
        line = course_config.read_config(root).get("check_line") or ""
    except Exception:                                        # noqa: BLE001
        line = ""
    return files, own, str(line)


def _repair_said(root, rec):
    """What a repair turn does with this report: fix and rerun, ask with a
    diagnostic, or stop at the cap."""
    tid, rid = rec.get("thread"), rec["request"]
    origin = rec.get("fixes") or rid
    used = attempts(root, origin)
    diag = is_diagnostic(root, rec)
    if diag and not failed(rec):
        head = ("This was a diagnostic for %s, and it came back: its RELAY: "
                "lines above are what it found." % origin)
    elif diag:
        head = ("This diagnostic for %s did NOT end cleanly; its RELAY: lines "
                "say why." % origin)
    elif rec.get("fixes"):
        head = "This rerun of %s did NOT end cleanly." % origin
    else:
        head = "It did NOT end cleanly."
    if len(used) >= MAX_FIXES:
        lines = [head + " That was the last of %d automatic attempts for %s, "
                 "diagnostics and reruns alike. File no diagnostic and no "
                 "rerun. The card says what failed, what each attempt found, "
                 "and that the owner decides next: `board job --fresh` is "
                 "theirs. Leave the thread's tasks as they are."
                 % (MAX_FIXES, origin), "", "The attempts:"]
        states = dict((r["request"], r) for r in relayed(root))
        for r in used:
            got = states.get(r.get("id")) or {}
            lines.append("  %s: %s, %s" % (
                r.get("id"), "diagnostic" if is_diagnostic(
                    root, dict(r, request=r.get("id"))) else "rerun",
                str(got.get("state") or "requested").lower()))
        return lines, False

    k = len(used) + 1
    last = k == MAX_FIXES
    first = _request(root, origin) or {}
    rerun = _rerun_argv(tid, origin, _last_run(root, origin))
    recipe = rerun[rerun.index("--") + 1]
    files, own, check = _thread_files_and_check(root, tid)
    if recipe not in files and recipe != "<recipe>":
        files = files + [recipe]
    tests = []
    if check:
        tests.append("the workspace's check, %s" % check)
    if own:
        tests.append("the thread's own check, %s" % own)
    failing = rid if not (diag and not failed(rec)) else (
        _last_run(root, origin).get("id") or origin)
    sites, step = failure_sites(
        (dict((r["request"], r) for r in relayed(root)).get(failing) or rec)
        .get("relay"))
    if sites:
        where = "then the code it failed in, %s" % ", ".join(sites[:3])
    else:
        where = ("it names no file and line, because its recipe printed no "
                 "RELAY: lines of its own; then the code its error points at")
    if step:
        where += " (the recipe stopped after its line %s)" % step
    lines = [
        head,
        "",
        "THIS TURN REPAIRS IT, HERE: a doing turn, whatever this workspace "
        "teaches under. Read the whole report first, %s; %s; and the recipe, "
        "%s. Then one of:" % (report_path(failing), where,
                              first.get("recipe") or recipe),
        "",
        "A. The report says enough to fix it. Before the card:",
        "  1. Fix it here, in the thread's files and its recipe: %s. Change "
        "nothing else." % (", ".join(files) or "(none listed)"),
        "  2. Run %s. If a check fails, stop: no rerun, and the card says "
        "what you tried and that the owner decides."
        % (" and ".join(tests) or "the tests the thread names (this "
                                   "workspace declares no check)"),
        "  3. Ship it: board push \"%s: <what changed>\" -- <the paths you "
        "changed>. If the push is refused, stop the same way: a rerun of "
        "code the cluster has not pulled runs the old code." % tid,
        "  4. Rerun with this exact command. Where the fix is a VAR value, "
        "change that value and nothing else:",
        "",
        "     " + " ".join(shlex.quote(a) for a in rerun),
        "",
    ]
    if last:
        lines.append("B. This is the last attempt, so there is no diagnostic "
                     "after it: if the report does not say enough, file "
                     "nothing, and the card says what is missing and that "
                     "the owner decides.")
    else:
        found = diagnostics(root)
        lines.append("B. It does not say enough. Ask the cluster with a "
                     "diagnostic: a tracked recipe that prints RELAY: lines "
                     "and produces nothing.")
        lines += ["     board diagnose %s --fixes %s -- %s%s"
                  % (shlex.quote(tid or ""), origin, d,
                     "".join(" [%s=...]" % n for n in names))
                  for d, names in found] or [
            "     board diagnose %s --fixes %s -- <diagnose.sbatch> "
            "[VAR=value ...]" % (shlex.quote(tid or ""), origin)]
        lines.append("   A question no diagnostic here answers is a new one: "
                     "write it as a recipe beside the others that prints "
                     "names and counts behind RELAY: -- never a value, a row "
                     "or a message -- ship it with `board push`, then file it.")
    lines += ["",
              "This is automatic attempt %d of %d for %s; a diagnostic and a "
              "rerun each count. The card says what failed and where, which "
              "of A or B you did, and what you changed. Leave the thread's "
              "tasks as they are until the rerun reports."
              % (k, MAX_FIXES, origin)]
    return lines, False


def _refused_fix_said(rec):
    """A refused diagnostic or rerun: the repair stops, and the owner
    decides."""
    return ["The cluster would not run this attempt to repair %s. Do not file "
            "it again, and file no other diagnostic or rerun for %s: the card "
            "lists what it refused and that the owner decides next. Leave the "
            "thread's tasks as they are." % (rec["fixes"], rec["fixes"])]


def repair_brief(root, rids):
    """`board brief`'s section for a repair turn: for each request it was
    woken for, the request, its recipe, where it failed, and the report to
    read whole. `rids` is one id or a list of them."""
    if isinstance(rids, str) or rids is None:
        rids = [rids] if rids else []
    rids = [r for i, r in enumerate(rids) if r and r not in rids[:i]]
    out = ["--- THIS TURN REPAIRS A FAILED CLUSTER JOB ---",
           "A doing turn, whatever the stance above says: its product is the "
           "fix, checked and filed, not a lesson about it. The [repair] line "
           "in the inbox has the steps and the exact rerun command."]
    if len(rids) > 1:
        out.append("This turn was woken for %d [repair] requests: %s. Repair "
                   "each, every one under its own [repair] line."
                   % (len(rids), ", ".join(rids)))
    recs = dict((r["request"], r) for r in relayed(root))
    for rid in rids:
        rec = recs.get(rid)
        if not rec:
            out.append("  request  %s (no report here yet)" % rid)
            continue
        out += _repair_lines(root, rid, rec, recs)
    return out


def _repair_lines(root, rid, rec, recs):
    req = _request(root, rid) or {}
    origin = rec.get("fixes") or rid
    failing = rec
    out = ["  request  %s%s" % (rid, ", an attempt to repair %s" % origin
                                if rec.get("fixes") else "")]
    out.append("  recipe   %s" % (req.get("recipe") or "unknown"))
    if is_diagnostic(root, rec) and not failed(rec):
        last = _last_run(root, origin)
        failing = recs.get(last.get("id")) or rec
        out.append("  answers  why %s failed, running %s" % (
            failing["request"], last.get("recipe") or "its recipe"))
    sites, step = failure_sites(failing.get("relay"))
    err = " (%s)" % failing["error"] if failing.get("error") else ""
    if sites:
        out.append("  failed   at %s%s" % (", ".join(sites[:3]), err))
    else:
        out.append("  failed   with no source location in its RELAY: "
                   "lines%s; a diagnostic recipe is how to ask" % err)
    if step:
        out.append("  stopped  after line %s of the recipe" % step)
    out.append("  report   %s -- read the whole of it, not the inbox line"
               % report_path(rid))
    if failing is not rec:
        out.append("  failure  %s" % report_path(failing["request"]))
    out.append("  attempts %d of %d automatic attempts for %s are filed"
               % (len(attempts(root, origin)), MAX_FIXES, origin))
    return out


def _messages(root):
    from .course.repo import Repo
    out = []
    try:
        with open(Repo(root).messages_path, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    out.append(msg)
    except OSError:
        pass
    return out


_STAMP_RE = re.compile(r"^(\[[^\]\n]*\]\s*)(?:\[carry\]\s*)?")


def batch_repairs(root, out):
    """The requests of every `[repair]` message in the batch `out`, the text
    `board inbox` printed for one turn, in order. A message is in the batch
    where its first printed line, `[<iso>] <text>`, is a line of `out`; a
    `[carry]` tag after the stamp is read through."""
    printed = set()
    for line in (out or "").splitlines():
        m = _STAMP_RE.match(line.strip())
        if m:
            printed.add(m.group(1).strip() + " " + line.strip()[m.end():])
    rids = []
    for msg in _messages(root):
        if msg.get("signal") != REPAIR:
            continue
        text = str(msg.get("text") or "").splitlines()
        head = "[%s] %s" % (msg.get("iso", "?"), text[0] if text else "")
        rid = str(msg.get("request") or "")
        if head.strip() in printed and rid and rid not in rids:
            rids.append(rid)
    return rids


def last_repair(root):
    """The request the newest `[repair]` inbox line was dropped for, or ""."""
    rid = ""
    for msg in _messages(root):
        if msg.get("signal") == REPAIR:
            rid = str(msg.get("request") or "")
    return rid


def open_fix(root, thread, recipe, env=None):
    """`""`, or the request a plain `board job <thread> -- <recipe> [VAR=v]`
    would rerun outside its repair: the newest request on the thread with
    this recipe, whatever its values, where the newest run of the repair it
    belongs to ended failed. Keyed on thread and recipe alone, so a repair
    capped at `MAX_FIXES` cannot restart by changing a VAR. Such a rerun
    carries `--fixes`, so the cap counts it; `--fresh` is the owner's way
    past. `env` is accepted and not read."""
    recipe = course_threads._rel(recipe) or ""
    reqs = requests(root)
    by_id = dict((r.get("id"), r) for r in reqs)
    runs = [r for r in reqs if r.get("kind") == "recipe"
            and r.get("thread") == thread
            and course_threads._rel(r.get("recipe")) == recipe]
    if not runs:
        return ""
    newest = max(runs, key=_filed_key)
    origin = newest.get("fixes") or newest.get("id")
    if not isinstance(origin, str) or origin not in by_id:
        return ""
    last = _last_run(root, origin)
    rec = next((r for r in relayed(root)
                if r["request"] == last.get("id")), None)
    return origin if rec and ended_failed(rec) else ""


def sense(root, rec):
    """The `[job]` inbox line: what ended, what it was to produce, and what to
    do. The log is named, never copied in -- the inbox is tracked in some
    workspaces, and a job's output is not the inbox's to carry."""
    if rec.get("request") and str(rec.get("jobid", "")).startswith("relay:"):
        return relay_sense(root, rec)
    produced = []
    for p in rec.get("produces") or []:
        produced.append("  %s %s" % ("present" if os.path.exists(
            os.path.join(root, p)) else "MISSING", p))
    title = rec.get("thread") or "no thread"
    try:
        clean, _ = course_threads.read(root)
        one = course_threads.thread(clean, rec.get("thread")) if clean else None
        if one:
            title = "%s (%s)" % (one["id"], one["title"])
    except Exception:                                        # noqa: BLE001
        pass
    lines = [
        "[job] A job registered to thread %s has ended." % title,
        "",
        "  job      %s" % rec.get("jobid"),
        "  state    %s" % rec.get("state"),
        "  exit     %s" % (rec.get("exit") or "unknown"),
        "  ended    %s" % (rec.get("ended") or "unknown"),
        "  command  %s" % rec.get("cmd", ""),
    ]
    if rec.get("log"):
        lines.append("  log      %s" % rec["log"])
    if rec.get("err"):
        lines.append("  errors   %s" % rec["err"])
    if "*" in (rec.get("log") or "") + (rec.get("err") or ""):
        lines.append("  (a `*` is one file per array task: glob it)")
    if produced:
        lines += ["", "What it was to produce:"] + produced
    lines += ["", "DO THIS: write one card reporting what finished, what it "
              "produced, and any non-zero exit."]
    if str(rec.get("state") or "") == "DIED":
        lines.append("It left the queue without writing its exit code: a time "
                     "limit, a node failure or a cancel.")
    elif str(rec.get("state") or "") == "ENDED":
        lines.append("It was a raw sbatch, so how it ended is unknown: read "
                     "the end of its log before you say.")
    if failed(rec) and str(rec.get("state") or "") != "ENDED":
        lines.append("It did NOT end cleanly. Read the last 40 lines of its "
                     "%s and put the error on the card, in your own words, "
                     "with the line it failed at."
                     % ("errors file" if rec.get("err") else "log"))
    lines.append("Then move the thread on with `board thread`: tick the task "
                 "this job was, and add the next one. A follow-up job goes "
                 "through `board job`, never a bare sbatch.")
    return "\n".join(lines)


def drop(root, rec, now=None, text=None, signal="job"):
    """Put the `[job]` line in the inbox, where `board wait` picks it up.

    `text` and `signal` put another machinery line the same way: a step's
    check is `[coach]` (`holds.wake`), a failure to repair `[repair]`. A
    relay record's request id rides along, so `board brief` can name it.
    """
    from .course.repo import Repo
    from .lesson import turns
    now = float(now or time.time())
    target = Repo(root)
    os.makedirs(target.inbox, exist_ok=True)
    line = {
        # From the lesson's own id series, and NOT in `turns.jsonl`: the
        # machinery is reporting, nobody said anything. The same shape as a
        # `[ship]` line.
        "id": turns.next_turn_id(target), "rev": 0, "kind": "text",
        "answers": None, "t": now, "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": text if text is not None else sense(root, rec),
        "signal": signal,
        "read": False,
    }
    if rec and rec.get("request"):
        line["request"] = str(rec["request"])
    with open(target.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")
    return line


def report(root, run=subprocess.run, now=None):
    """One pass: poll, and drop a `[job]` line for every job that ended.

    On a machine without Slurm the endings are the cluster's, and `hear` drops
    their lines: the same line, the same inbox, the same wake.
    """
    heard = [] if has_slurm() else hear(root, now=now)
    ended, out = poll(root, run=run, now=now), heard
    for rec in ended:
        try:
            drop(root, rec, now=now)
        except Exception:                                    # noqa: BLE001
            # No line, so no claim: the next pass offers it again.
            _unclaim(root, rec["jobid"])
            continue
        append(root, {"jobid": rec["jobid"], "thread": rec.get("thread"),
                      "reported": float(now or time.time())})
        out.append(rec)
    return out


# ---------------------------------------------------------------------------
# what the board shows
# ---------------------------------------------------------------------------
def running(root):
    """The unfinished jobs, newest first, for the busy strip."""
    titles = {}
    try:
        clean, _ = course_threads.read(root)
        for t in (clean or {}).get("threads") or []:
            titles[t["id"]] = t["title"]
    except Exception:                                        # noqa: BLE001
        pass
    out = []
    for j in course_threads.unfinished(list(view(root).values())):
        out.append({"jobid": j.get("slurm") or j.get("jobid"),
                    "thread": j.get("thread"),
                    "title": titles.get(j.get("thread"), j.get("thread") or ""),
                    "state": j.get("state") or "PENDING",
                    "submitted": j.get("submitted") or 0})
    out.sort(key=lambda j: -float(j["submitted"] or 0))
    return out


# ---------------------------------------------------------------------------
# the relay: a request the Mac commits, a report the cluster commits
# ---------------------------------------------------------------------------
# A MACHINE WITHOUT SLURM NEVER SUBMITS. It writes `relay/requests/<id>.json`,
# commits that one file and pushes it; the cluster's relay pulls it, checks it
# again with the same `validate`, runs it and commits `relay/reports/<id>.json`.
# One file per request, never edited after the commit that adds it, so two
# machines never write the same file. The shapes are HANDOFF.md's "The relay".

RELAY = "relay"
# `turn` is a kind only so that `validate` can refuse it by name: no hosted
# model runs on an institute machine (`NO_TURN`).
KINDS = ("recipe", "turn", "colibri")
REPORT_STATES = ("refused", "submitted", "running", "completed", "failed")

# A report's state, as the registry's Slurm-shaped one. `REFUSED` is terminal;
# a request with no report at all is `REQUESTED`, which is not.
_AS_SLURM = {"refused": "REFUSED", "submitted": "PENDING",
             "running": "RUNNING", "completed": "COMPLETED",
             "failed": "FAILED"}

REQUEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
VAR_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")
# `#RELAY-VAR NAME PATTERN` in a recipe's header, the way `#SBATCH` is: one
# line per variable the recipe accepts, the value fully matching PATTERN.
VAR_LINE_RE = re.compile(r"^#RELAY-VAR\s+(\S+)\s+(\S.*?)\s*$")
# What no recipe may accept from a request, whatever it declares: each changes
# what runs rather than what it runs on, and ALL and NONE are --export words.
FORBIDDEN_VARS = ("ALL", "NONE", "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH",
                  "PYTHONPATH", "PYTHONSTARTUP", "BASH_ENV", "ENV", "HOME",
                  "SHELL", "IFS", "PROMPT_COMMAND")
REQUEST_KEYS = {
    "recipe": ("id", "kind", "thread", "recipe", "env", "produces", "export",
               "filed", "fixes"),
    "colibri": ("id", "kind", "thread", "brief", "filed"),
}
MAX_BRIEF = 2000
MAX_VALUE = 200
NO_TURN = ("a `turn` request asks for a hosted model on the cluster, and no "
           "hosted model call runs on an institute machine, for any vendor "
           "(projects/libr-local-llm/docs/deepseek-egress.md): file a recipe, "
           "or a `colibri` task where the workspace takes them")
# A failed recipe request gets at most this many automatic attempts to repair
# it, diagnostics and reruns alike. `fixes` on each names the request that
# failed first, so the chain stays flat and the count is the requests on disk
# whose `fixes` names it.
MAX_FIXES = 3


def has_slurm():
    """Can this machine submit? `TUTOR_SLURM=0|1` decides where it is set,
    so a test on the cluster can stand in for the Mac."""
    forced = os.environ.get("TUTOR_SLURM", "").strip()
    if forced in ("0", "1"):
        return forced == "1"
    return shutil.which("sbatch") is not None


def requests_dir(root):
    return os.path.join(root, RELAY, "requests")


def reports_dir(root):
    return os.path.join(root, RELAY, "reports")


def declarations(text):
    """`({NAME: pattern}, problems)` out of a recipe's header. Pure.

    The header runs to the first line that is neither blank nor a comment.
    """
    declared, problems = {}, []
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            break
        m = VAR_LINE_RE.match(s)
        if not m:
            continue
        name, pattern = m.group(1), m.group(2)
        if not VAR_NAME_RE.match(name) or name in FORBIDDEN_VARS:
            problems.append("the recipe declares %r, which a request may not "
                            "set" % name)
            continue
        try:
            re.compile(pattern)
        except re.error as exc:
            problems.append("the recipe's pattern for %s does not compile: %s"
                            % (name, exc))
            continue
        declared[name] = pattern
    return declared, problems


def _plain_list(value, field, problems):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        problems.append("`%s` must be a list of paths" % field)
        return []
    return value


def validate(req, clean, tracked, declared, taken=(), colibri=False):
    """`(request, problems)`: may this request run? PURE, and both machines
    call it -- the Mac before it commits, the cluster before it submits.

        req       the request, as parsed JSON
        clean     the workspace's thread file, as `threads.validate` returns it
        tracked   workspace-relative paths tracked and unchanged at HEAD
        declared  `{recipe: (declared, problems)}`, `declarations` per recipe
        taken     request ids already filed
        colibri   has this workspace opted in to `colibri` requests, which
                  queue a Colibri task (`colibri.relay_file`)

    Refused whole, with every problem at once, like the thread file.
    """
    problems = []
    if not isinstance(req, dict):
        return None, ["a request is an object, not a %s" % type(req).__name__]
    kind = req.get("kind")
    if kind == "turn":
        return None, [NO_TURN]
    if kind not in KINDS:
        return None, ["`kind` must be one of %s, not %r"
                      % (", ".join(k for k in KINDS if k != "turn"), kind)]
    extra = sorted(k for k in req if k not in REQUEST_KEYS[kind])
    if extra:
        problems.append("a %s request has no %s" % (
            kind, ", ".join("`%s`" % k for k in extra)))
    rid = req.get("id")
    if not isinstance(rid, str) or not REQUEST_ID_RE.match(rid):
        problems.append("id %r must be 1-80 characters of a-z, 0-9 and hyphen"
                        % (rid,))
    elif rid in set(taken or ()):
        problems.append("id %s is already filed; an id names one request" % rid)
    elif rid.startswith("check-"):
        # `relay/reports/check-<thread>-<n>.json` is a held step's check
        # (`holds.is_check`), so a request named so would share its report.
        problems.append("id %s starts with `check-`, which names a held "
                        "step's check report" % rid)
    filed = req.get("filed")
    if filed is not None and (isinstance(filed, bool)
                              or not isinstance(filed, (int, float))):
        problems.append("`filed` is seconds since the epoch")
    fixes = req.get("fixes")
    if "fixes" in req and (not isinstance(fixes, str)
                           or not REQUEST_ID_RE.match(fixes) or fixes == rid):
        problems.append("`fixes` names a request id")

    tid = req.get("thread")
    one = course_threads.thread(clean, tid) if clean else None
    if not one:
        problems.append("thread %r is not one this workspace's thread file "
                        "declares" % (tid,))
    out = {"id": rid, "kind": kind, "thread": tid}
    if filed is not None:
        out["filed"] = filed

    if kind == "colibri":
        brief = req.get("brief")
        if not isinstance(brief, str) or not brief.strip():
            problems.append("a %s request needs a `brief`" % kind)
        elif len(brief) > MAX_BRIEF:
            problems.append("the brief is %d characters and the cap is %d"
                            % (len(brief), MAX_BRIEF))
        # Colibri reads PHI, unattended, so a workspace opts in to it.
        if not colibri:
            problems.append("this workspace has not opted in to Colibri tasks: "
                            "`relay.colibri: true` in its tutorboard.json")
        out["brief"] = brief.strip() if isinstance(brief, str) else ""
        return (None, problems) if problems else (out, [])

    recipe = course_threads._rel(req.get("recipe"))
    if not recipe or not recipe.endswith(".sbatch"):
        problems.append("recipe %r must be a .sbatch file inside this "
                        "workspace" % (req.get("recipe"),))
    elif recipe not in set(tracked or ()):
        problems.append("recipe %s is not tracked and unchanged at HEAD, so "
                        "the cluster would not run what this names" % recipe)
    names, said = (declared or {}).get(recipe) or ({}, [])
    problems.extend("recipe %s: %s" % (recipe, p) for p in said)

    env = req.get("env", {})
    if not isinstance(env, dict):
        problems.append("`env` must be an object of NAME: value")
        env = {}
    for key in sorted(env):
        value = env[key]
        if key not in names:
            problems.append("env %s is not declared by the recipe%s" % (
                key, "; it declares " + ", ".join(sorted(names))
                if names else ", which declares no variables"))
            continue
        if not isinstance(value, str):
            problems.append("env %s must be a string" % key)
            continue
        if (len(value) > MAX_VALUE or any(c in value for c in ",=\n\r\0")
                or not re.fullmatch(names[key], value)):
            problems.append("env %s=%r does not match the recipe's pattern %s"
                            % (key, value, names[key]))

    produces = []
    for p in _plain_list(req.get("produces"), "produces", problems):
        rel = course_threads._rel(p)
        if rel is None:
            problems.append("produces %r is not a path inside this workspace"
                            % p)
        else:
            produces.append(rel)
    export = []
    for p in _plain_list(req.get("export"), "export", problems):
        rel = course_threads._rel(p)
        if rel is None or not rel.startswith("results/"):
            problems.append("export %r must be a path under results/" % p)
        elif os.path.splitext(rel)[1].lower() not in course_threads.EXPORT_EXTS:
            problems.append("export %s is not one of %s" % (
                rel, ", ".join(course_threads.EXPORT_EXTS)))
        elif one and not course_threads.exportable(one, rel):
            problems.append("export %s is not marked aggregate on thread %s. "
                            "`board thread export %s %s` asks the owner"
                            % (rel, tid, tid, rel))
        else:
            export.append(rel)
    out.update({"recipe": recipe, "env": dict(env), "produces": produces,
                "export": export})
    if fixes is not None:
        out["fixes"] = fixes
    return (None, problems) if problems else (out, [])


def fix_problems(req, filed, failed_ids, mine=False):
    """Every problem with this request's `fixes`, `[]` without one. PURE.

        req         the request
        filed       the requests already filed, as `requests` reads them
        failed_ids  the ids of the requests whose report says they failed
                    (`ended_failed`)
        mine        the cluster checking a request already filed: only the
                    attempts filed before it count against the cap

    `fixes` names a recipe request on the same thread that is itself no fix
    and has failed: the one that failed first. An attempt past `MAX_FIXES`,
    diagnostic or rerun, is refused on both machines, which is what stops a
    job that keeps failing.
    """
    if not isinstance(req, dict) or req.get("fixes") is None:
        return []
    origin, rid = req.get("fixes"), req.get("id")
    if not isinstance(origin, str):
        return []                                   # `validate` says why
    by_id = dict((r.get("id"), r) for r in filed or () if isinstance(r, dict))
    target = by_id.get(origin)
    if not target:
        return ["`fixes` names %s, which is not a filed request" % origin]
    problems = []
    if target.get("kind") != "recipe":
        problems.append("`fixes` names %s, which is a %s request, not a "
                        "recipe" % (origin, target.get("kind") or "kindless"))
    if target.get("thread") != req.get("thread"):
        problems.append("`fixes` names %s, which is on thread %s, not %s"
                        % (origin, target.get("thread"), req.get("thread")))
    if target.get("fixes"):
        problems.append("`fixes` names %s, which fixes %s itself; name the "
                        "request that failed first" % (origin,
                                                       target["fixes"]))
    elif origin not in set(failed_ids or ()):
        problems.append("`fixes` names %s, which has no report here saying "
                        "it failed" % origin)
    before = [r for r in by_id.values()
              if r.get("fixes") == origin and r.get("id") != rid
              and (not mine or _filed_key(r) < _filed_key(req))]
    if len(before) >= MAX_FIXES:
        problems.append("request %s has had %d automatic attempts, "
                        "diagnostics and reruns, and the cap is %d; the owner "
                        "starts again with `board job --fresh`"
                        % (origin, len(before), MAX_FIXES))
    return problems


def _git_lines(root, argv):
    try:
        p = subprocess.run(["git"] + argv, cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if p.returncode != 0:
        return []
    return [x for x in (p.stdout or "").split("\0") if x]


def context(root, recipes=()):
    """What `validate` is handed, read off this workspace. Impure.

    A recipe is tracked only if it is unchanged at HEAD: an uncommitted edit is
    one the cluster would never see.
    """
    tracked = set(_git_lines(root, ["ls-files", "-z", "--", "."]))
    changed = set(_git_lines(root, ["diff", "--name-only", "-z", "--relative",
                                    "HEAD", "--", "."]))
    tracked -= changed
    declared = {}
    for r in recipes:
        rel = course_threads._rel(r)
        if not rel:
            continue
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8",
                      errors="replace") as fh:
                declared[rel] = declarations(fh.read())
        except OSError:
            declared[rel] = ({}, [])
    clean, _ = course_threads.read(root)
    relay = relay_opts(root)
    filed = requests(root)
    taken = set(r["id"] for r in filed)
    failed_ids = set(r["request"] for r in relayed(root) if ended_failed(r))
    return {"clean": clean, "tracked": tracked, "declared": declared,
            "taken": taken, "colibri": relay.get("colibri") is True,
            "filed": filed,
            "failed": failed_ids}


def _relay_of(path):
    """The `relay` object of one JSON file, `{}` where it has none."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            relay = (json.load(fh) or {}).get("relay") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return relay if isinstance(relay, dict) else {}


def relay_opts(root):
    """This workspace's relay opt-ins, `colibri` and `sync`, from its own
    `tutorboard.json` alone. There is no machine-wide default: nothing opts a
    workspace into sync but its own file (the sync code goes in T38c)."""
    return dict(_relay_of(os.path.join(root, "tutorboard.json")))


def check(root, req, mine=False):
    """`validate`, with this workspace's context. `(request, problems)`.

    `mine` is the cluster checking a request already filed, whose own id is
    therefore taken by itself.
    """
    if isinstance(req, dict):
        req = dict((k, v) for k, v in req.items() if k != FILE_KEY)
    recipe = req.get("recipe") if isinstance(req, dict) else None
    ctx = context(root, [recipe] if isinstance(recipe, str) else [])
    taken = ctx["taken"]
    if mine and isinstance(req, dict):
        taken = taken - set([req.get("id")])
    ok, problems = validate(req, ctx["clean"], ctx["tracked"],
                            ctx["declared"], taken, ctx["colibri"])
    extra = fix_problems(req, ctx["filed"], ctx["failed"], mine)
    if extra:
        return None, problems + extra
    return ok, problems


def _slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-",
                                     str(text or "").lower())).strip("-")


def new_id(thread, label, taken=(), now=None):
    """`<date>-<thread>-<label>`, cut to fit and made unique with `-2`, `-3`."""
    day = time.strftime("%Y-%m-%d", time.localtime(float(now or time.time())))
    stem = "-".join(x for x in (day, _slug(thread), _slug(label)) if x)[:72]
    stem = stem.rstrip("-")
    taken, rid, n = set(taken or ()), stem, 1
    while rid in taken:
        n += 1
        rid = "%s-%d" % (stem, n)
    return rid


def _read_json_dir(path, stem=None):
    """Every JSON object in `path`. `stem` names a key that gets the file's
    own name, less `.json`, which no payload can forge."""
    out = []
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(path, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            rec.setdefault("id", name[:-len(".json")])
            if stem:
                rec[stem] = name[:-len(".json")]
            out.append(rec)
    return out


# The key `requests` adds: the request file's own name, less `.json`.
FILE_KEY = "_file"


def requests(root):
    """Every request filed in this workspace, as written, each with its file's
    name under `FILE_KEY`."""
    return _read_json_dir(requests_dir(root), stem=FILE_KEY)


def reports(root):
    """`{request id: report}`, as the cluster wrote them."""
    return dict((r["id"], r) for r in _read_json_dir(reports_dir(root)))


def _strings(value):
    """A request's path list as strings, and `[]` for anything that is not a
    list: `relayed` is read on every check on both machines, so one malformed
    request file must not stop every check in the workspace."""
    return [str(v) for v in value] if isinstance(value, list) else []


def relayed(root):
    """The requests, each folded with its report, as registry records.

    `jobid` is `relay:<id>`, so it never collides with a Slurm id; `slurm` is
    the id the cluster's report gives, where it has one.
    """
    got = reports(root)
    out = []
    for req in requests(root):
        rid = str(req.get("id") or "")
        rep = got.get(rid) or {}
        state = _AS_SLURM.get(str(rep.get("state") or "").lower(),
                              course_threads.REQUESTED)
        if req.get("kind") in ("turn", "colibri"):
            cmd = "%s: %s" % (req["kind"], str(req.get("brief") or "")[:120])
        else:
            env = req.get("env")
            cmd = " ".join([str(req.get("recipe") or "")] + [
                "%s=%s" % (k, v) for k, v in sorted(
                    (env if isinstance(env, dict) else {}).items(),
                    key=lambda kv: str(kv[0]))])
        rec = {
            "jobid": "relay:" + rid, "request": rid,
            "kind": req.get("kind") or "", "thread": req.get("thread"),
            "cmd": cmd[:CMD_CHARS], "state": state,
            "produces": _strings(req.get("produces")),
            "export": _strings(req.get("export")),
            # A malformed `filed` reads as 0 rather than stopping every reader.
            "submitted": _when(rep.get("submitted") or req.get("filed") or 0),
        }
        if req.get("fixes"):
            rec["fixes"] = req["fixes"]
        for key in ("exit", "ended", "note", "produced", "missing",
                    "exported", "export_refused", "relay", "error",
                    "problems", "changed"):
            if rep.get(key) not in (None, "", []):
                rec[key] = rep[key]
        if rep.get("jobid"):
            rec["slurm"] = str(rep["jobid"])
        out.append(rec)
    return out


def view(root):
    """THE REGISTRY, ONE VIEW OF THREE SOURCES: `{key: record}`.

    The local `jobs.jsonl`, the requests under `relay/requests/`, and the
    cluster's reports under `relay/reports/`. A request whose report names a
    Slurm job this machine registered itself (the cluster, submitting it) is
    that job, once, carrying its request id.
    """
    out = records(root)
    for rec in relayed(root):
        slurm = rec.get("slurm")
        if slurm and slurm in out:
            out[slurm] = dict(out[slurm], request=rec["request"])
            continue
        out[rec["jobid"]] = rec
    return out


def request_visible(root):
    """`""`, or the sentence saying git would not see a request here."""
    rel = RELAY + "/requests/x.json"
    if ignored(root, rel):
        return ("git ignores %s/requests/ in this workspace, so a request "
                "would never reach the cluster. Add `!%s/` to %s after the "
                "rule that hides it." % (RELAY, RELAY,
                                         os.path.join(root, ".gitignore")))
    return ""


def nested_git(root):
    """The first directory at or under `root` holding a `.git`, else "".

    A subject is Atlas's own content; a nested repository inside one is
    something Atlas cannot see, so no request is filed from it. The walk never
    enters a dot directory, `live/`, `results/`, `node_modules/` or a fenced
    name (`fenced.NEVER`): only whether `.git` exists is asked of each level.
    """
    for here, dirs, files in os.walk(root):
        if ".git" in dirs or ".git" in files:
            return here
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("live", "results", "node_modules")
                   and not fenced.in_fence(d)]
    return ""


def file_request(root, req, run=subprocess.run, push=True):
    """Write `relay/requests/<id>.json` and commit that one file, then push.

    `(path, ok, said)`. `commit_alone` makes the commit.
    """
    target = os.path.join(requests_dir(root), req["id"] + ".json")
    if os.path.exists(target):
        return target, False, "%s is already there" % target
    nested = nested_git(root)
    if nested:
        return target, False, ("%s holds its own .git, and the relay reads "
                               "requests only from Atlas's tree" % nested)
    leak = request_leak(root, req)
    if leak:
        return target, False, leak
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(req, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    course_threads.forget(root)
    # Before the commit, so the report to this request is a change `hear`
    # sees, even when it arrives in the first pull after filing.
    _baseline(root)
    ok, said = commit_alone(root, target, "relay request %s" % req["id"],
                            run=run, push=push)
    return target, ok, said


def request_leak(root, req):
    """"" or why this request may not be published. A request is public the
    moment it is pushed, and its brief is free text a turn may have written:
    an absolute or home path (where lab storage gets named) is refused, and
    so is anything the lab's PHI policy matches."""
    from . import atlas, leaving
    brief = req.get("brief") if isinstance(req, dict) else None
    if isinstance(brief, str) and _BRIEF_PATH_RE.search(brief):
        return ("the brief names an absolute or home path, and a request is "
                "public; say it relative to the workspace")
    try:
        top = _git_text(root, ["rev-parse", "--show-toplevel"])
        names_phi = leaving.policy(top or atlas.root())
    except Exception:                                        # noqa: BLE001
        names_phi = None
    if names_phi is not None:
        text = json.dumps(dict((k, v) for k, v in req.items()
                               if k != FILE_KEY), sort_keys=True,
                          ensure_ascii=False)
        try:
            flagged = names_phi(text) or (isinstance(brief, str)
                                          and names_phi(brief))
        except Exception:                                    # noqa: BLE001
            flagged = True
        if flagged:
            return ("the PHI policy matches this request, and a request is "
                    "public, so it was not filed")
    return ""


# The path `relay.public` redacts in a report.
_BRIEF_PATH_RE = re.compile(r"(?<![\w.~:/-])(?:~/|/)(?:[^\s/:'\"]+/)*"
                            r"[^\s/:'\",;)]+")


def commit_alone(root, target, what, run=subprocess.run, push=True):
    """Commit the one file `target`, written or removed, then push. `(ok, said)`.

    The commit goes through the tool's own `save-and-push.sh` with that file as
    its whole pathspec, so nothing else in the tree rides along. The message is
    `<workspace>: <what>`. `push=False` commits it with plain git, and pushes
    nothing.
    """
    from . import atlas, paths
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = ""
    if not top:
        return False, "%s is not in a git repository" % root
    # The directory resolved, not the file: a removed file has no realpath.
    rel = os.path.relpath(
        os.path.join(os.path.realpath(os.path.dirname(target)),
                     os.path.basename(target)), os.path.realpath(top))
    where = atlas.identify(root)
    msg = "%s: %s" % (where, what) if where else what
    script = os.path.join(paths.TOOL, "scripts", "save-and-push.sh")
    if push and os.path.exists(script):
        cmd = ["bash", script, msg, "--", rel]
    else:
        cmd = ["bash", "-c", 'set -e; git add -A -- "$2"; '
               'git commit -q -m "$1" --only -- "$2"', "_", msg, rel]
    try:
        p = run(cmd, cwd=top, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=180)
    except subprocess.TimeoutExpired:
        return False, "timed out after 3 minutes"
    except OSError as exc:
        return False, str(exc)
    return p.returncode == 0, (p.stdout or "").strip()[-800:]


# ---------------------------------------------------------------------------
# the Mac hears the cluster
# ---------------------------------------------------------------------------
# A REPORT A PULL BROUGHT TO AN END DROPS THE SAME `[job]` LINE A LOCAL ENDING
# DOES, in the same inbox, so `board wait` wakes the same turn and
# `turn_signal` reads it as `job` -- or as `repair`, for a failure the Mac
# repairs (`repairs`). Nothing else wakes a turn for the relay.
#
# "Brought by a pull" is read off git, not off the pull: whichever process
# moved HEAD -- the timer, the transcript beat, a hand `git pull` -- the next
# `hear` diffs `relay/reports/` from the commit it last heard to HEAD. A fresh
# clone hears nothing of the reports it arrived with: the first `hear` records
# HEAD and says nothing. Each ending is claimed once per (request, state), so
# two hearers never drop it twice.

ENDED_REPORTS = ("refused", "completed", "failed")
HEARD = "relay.heard"

# The pull's cadence on a machine without Slurm: every two minutes while a
# request is out, every five minutes otherwise, so a cluster commit is here
# within one relay pass and one poll. The timer fires every twenty seconds and
# `pull_due` decides.
PULL_BUSY = 120
PULL_IDLE = 300


def outstanding(root, tid=None):
    """The requests here the cluster has not ended, oldest first."""
    out = [r for r in relayed(root)
           if (tid is None or r.get("thread") == tid)
           and not course_threads.finished(r)]
    out.sort(key=lambda r: float(r.get("submitted") or 0))
    return out


def pull_interval(roots):
    """Seconds between pulls: `PULL_BUSY` while any request is out."""
    for root in roots or ():
        try:
            if outstanding(root):
                return PULL_BUSY
        except Exception:                                    # noqa: BLE001
            continue
    return PULL_IDLE


# A timer's fire drifts by a few seconds; without the slack a two-minute
# cadence on a two-minute timer would pull every four.
PULL_SLACK = 15


def pull_due(last, now, interval):
    """Is a pull due? A stamp from the future (a clock moved) is due too."""
    last, now = float(last or 0), float(now)
    return last <= 0 or last > now or now - last >= interval - PULL_SLACK


def _when(value):
    """A report's time as epoch seconds, whether written as a number or ISO."""
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(str(value)[:19], fmt))
        except (TypeError, ValueError):
            continue
    return 0.0


def last_report(root, tid):
    """The newest ended report on this thread, as a registry record, or None."""
    got = reports(root)
    best, at = None, -1.0
    for rec in relayed(root):
        rep = got.get(rec["request"])
        if rec.get("thread") != tid or not rep:
            continue
        if str(rep.get("state") or "").lower() not in ENDED_REPORTS:
            continue
        when = (_when(rep.get("ended")) or _when(rep.get("submitted"))
                or float(rec.get("submitted") or 0))
        if when >= at:
            best, at = rec, when
    return best


def thread_relay(root, tid):
    """`board brief`'s lines: the thread's requests still out, and its last
    report. `[]` where it has neither."""
    out = []
    waiting = outstanding(root, tid)
    if waiting:
        out.append("Waiting on the cluster (the pull hears each ending as a "
                   "[job] line):")
        out.extend("  %s  %s  %s" % (r["request"], r["state"].lower(), r["cmd"])
                   for r in waiting)
    last = last_report(root, tid)
    if last:
        bits = [last["state"].lower()]
        if last.get("exit") not in (None, ""):
            bits.append("exit %s" % last["exit"])
        if last.get("ended"):
            bits.append("ended %s" % last["ended"])
        out.append("The last cluster report: %s, %s." % (last["request"],
                                                         ", ".join(bits)))
        out.extend("  RELAY: %s" % l.split("RELAY:", 1)[-1].strip()
                   for l in _relay_said(last.get("relay"))[:6])
        if last.get("note"):
            out.append("  note: %s" % str(last["note"])[:400])
    return out


def _git_text(root, argv):
    try:
        p = subprocess.run(["git"] + argv, cwd=root, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _heard_path(root):
    return os.path.join(root, "live", "jobs.reported", HEARD)


def _set_heard(root, commit):
    path = _heard_path(root)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = "%s.%d" % (path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(commit + "\n")
        os.replace(tmp, path)
    except OSError:
        pass


def _baseline(root):
    """Record HEAD as heard where nothing has been, and git ignores the ledger:
    an untracked file here is a dirty tree to every guard that refuses to
    commit over one."""
    if os.path.exists(_heard_path(root)):
        return
    head = _git_text(root, ["rev-parse", "HEAD"])
    if head and ignored(root, "live/jobs.reported/" + HEARD):
        _set_heard(root, head)


def _claim_once(root, key):
    """True for the one hearer that may drop this ending. Never taken over."""
    target = _marker(root, key)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.close(os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
    except OSError:
        return False
    return True


def hear(root, now=None):
    """Drop a `[job]` line for each report that reached an end since the
    commit last heard. The records heard. Never raises; quiet outside git."""
    try:
        head = _git_text(root, ["rev-parse", "HEAD"])
        if not head:
            return []
        try:
            with open(_heard_path(root), "r", encoding="utf-8") as fh:
                last = fh.read().strip()
        except OSError:
            last = ""
        if last == head:
            return []
        if not last:
            # Only where the relay is in use.
            if os.path.isdir(os.path.join(root, RELAY)):
                _baseline(root)
            return []
        changed = _git_lines(root, ["diff", "--name-only", "-z", "--relative",
                                    last, head, "--", RELAY + "/reports"])
        if not changed:
            _set_heard(root, head)
            return []
        by_id = dict((r["request"], r) for r in relayed(root))
        got = reports(root)
        out, missed = [], False
        from . import holds
        for rel in sorted(changed):
            rid = os.path.basename(rel)[:-len(".json")] if rel.endswith(
                ".json") else ""
            if holds.is_check(rid):
                # A held step's check: `holds.wake` drops its `[coach]` line.
                continue
            rep = got.get(rid)
            if not rep:
                continue
            state = str(rep.get("state") or "").lower()
            if state not in ENDED_REPORTS:
                continue
            key = "relay-%s.%s" % (rid, state)
            if not _claim_once(root, key):
                continue
            rec = by_id.get(rid) or {
                "jobid": "relay:" + rid, "request": rid, "kind": "",
                "thread": rep.get("thread"), "cmd": "",
                "state": _AS_SLURM.get(state, state.upper())}
            try:
                drop(root, rec, now=now,
                     signal=REPAIR if repairs(root, rec) else "job")
            except Exception:                                # noqa: BLE001
                _unclaim(root, key)
                missed = True
                continue
            out.append(rec)
        if not missed:
            _set_heard(root, head)
        return out
    except Exception:                                        # noqa: BLE001
        return []
