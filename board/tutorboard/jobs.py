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
    found = ([full] if os.path.isfile(full) else []) + _array_exits(full)
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
            if state != j.get("state"):
                append(root, {"jobid": j["jobid"], "thread": j.get("thread"),
                              "state": state, "seen": now}, path=path)
            continue
        # Gone from squeue, or there in a terminal state it is about to leave
        # by: either way the wrapper's file, written before the job left, says
        # how it ended.
        got = ending(root, j, now)
        if got is None:
            continue
        state, code, end = got
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


def sense(root, rec):
    """The `[job]` inbox line: what ended, what it was to produce, and what to
    do. The log is named, never copied in -- the inbox is tracked in some
    workspaces, and a job's output is not the inbox's to carry."""
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


def drop(root, rec, now=None):
    """Put the `[job]` line in the inbox, where `board wait` picks it up."""
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
        "from": "student", "text": sense(root, rec), "signal": "job",
        "read": False,
    }
    with open(target.messages_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")
    return line


def report(root, run=subprocess.run, now=None):
    """One pass: poll, and drop a `[job]` line for every job that ended."""
    ended, out = poll(root, run=run, now=now), []
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
KINDS = ("recipe", "turn")
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
               "filed"),
    "turn": ("id", "kind", "thread", "brief", "filed"),
}
MAX_BRIEF = 2000
MAX_VALUE = 200


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


def validate(req, clean, tracked, declared, taken=(), turns=False):
    """`(request, problems)`: may this request run? PURE, and both machines
    call it -- the Mac before it commits, the cluster before it submits.

        req       the request, as parsed JSON
        clean     the workspace's thread file, as `threads.validate` returns it
        tracked   workspace-relative paths tracked and unchanged at HEAD
        declared  `{recipe: (declared, problems)}`, `declarations` per recipe
        taken     request ids already filed
        turns     has this workspace opted in to `turn` requests

    Refused whole, with every problem at once, like the thread file.
    """
    problems = []
    if not isinstance(req, dict):
        return None, ["a request is an object, not a %s" % type(req).__name__]
    kind = req.get("kind")
    if kind not in KINDS:
        return None, ["`kind` must be one of %s, not %r"
                      % (", ".join(KINDS), kind)]
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
    filed = req.get("filed")
    if filed is not None and (isinstance(filed, bool)
                              or not isinstance(filed, (int, float))):
        problems.append("`filed` is seconds since the epoch")

    tid = req.get("thread")
    one = course_threads.thread(clean, tid) if clean else None
    if not one:
        problems.append("thread %r is not one this workspace's thread file "
                        "declares" % (tid,))
    out = {"id": rid, "kind": kind, "thread": tid}
    if filed is not None:
        out["filed"] = filed

    if kind == "turn":
        brief = req.get("brief")
        if not isinstance(brief, str) or not brief.strip():
            problems.append("a turn request needs a `brief`")
        elif len(brief) > MAX_BRIEF:
            problems.append("the brief is %d characters and the cap is %d"
                            % (len(brief), MAX_BRIEF))
        if not turns:
            problems.append("this workspace has not opted in to turns: "
                            "`relay.turns: true` in its tutorboard.json")
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
    return (None, problems) if problems else (out, [])


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
    turns = False
    try:
        with open(os.path.join(root, "tutorboard.json"), "r",
                  encoding="utf-8") as fh:
            turns = ((json.load(fh) or {}).get("relay") or {}).get("turns") is True
    except (OSError, ValueError, AttributeError):
        pass
    taken = set(r["id"] for r in requests(root))
    return {"clean": clean, "tracked": tracked, "declared": declared,
            "taken": taken, "turns": turns}


def check(root, req, mine=False):
    """`validate`, with this workspace's context. `(request, problems)`.

    `mine` is the cluster checking a request already filed, whose own id is
    therefore taken by itself.
    """
    recipe = req.get("recipe") if isinstance(req, dict) else None
    ctx = context(root, [recipe] if isinstance(recipe, str) else [])
    taken = ctx["taken"]
    if mine and isinstance(req, dict):
        taken = taken - set([req.get("id")])
    return validate(req, ctx["clean"], ctx["tracked"], ctx["declared"],
                    taken, ctx["turns"])


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


def _read_json_dir(path):
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
            out.append(rec)
    return out


def requests(root):
    """Every request filed in this workspace, as written."""
    return _read_json_dir(requests_dir(root))


def reports(root):
    """`{request id: report}`, as the cluster wrote them."""
    return dict((r["id"], r) for r in _read_json_dir(reports_dir(root)))


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
        if req.get("kind") == "turn":
            cmd = "turn: " + str(req.get("brief") or "")[:120]
        else:
            cmd = " ".join([str(req.get("recipe") or "")] + [
                "%s=%s" % (k, v) for k, v in sorted(
                    (req.get("env") or {}).items())])
        rec = {
            "jobid": "relay:" + rid, "request": rid,
            "kind": req.get("kind") or "", "thread": req.get("thread"),
            "cmd": cmd[:CMD_CHARS], "state": state,
            "produces": list(req.get("produces") or []),
            "export": list(req.get("export") or []),
            "submitted": float(rep.get("submitted") or req.get("filed") or 0),
        }
        for key in ("exit", "ended", "note", "produced", "missing",
                    "exported", "export_refused", "relay", "error",
                    "problems"):
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


def file_request(root, req, run=subprocess.run, push=True):
    """Write `relay/requests/<id>.json` and commit that one file, then push.

    `(path, ok, said)`. The commit goes through the tool's own
    `save-and-push.sh` with the request as its whole pathspec, so nothing else
    in the tree rides along. `push=False` commits it with plain git, and
    pushes nothing.
    """
    from . import atlas, paths
    target = os.path.join(requests_dir(root), req["id"] + ".json")
    if os.path.exists(target):
        return target, False, "%s is already there" % target
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(req, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    course_threads.forget(root)
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = ""
    if not top:
        return target, False, "%s is not in a git repository" % root
    rel = os.path.relpath(os.path.realpath(target), os.path.realpath(top))
    where = atlas.identify(root)
    msg = ("%s: relay request %s" % (where, req["id"]) if where
           else "relay request %s" % req["id"])
    script = os.path.join(paths.TOOL, "scripts", "save-and-push.sh")
    if push and os.path.exists(script):
        cmd = ["bash", script, msg, "--", rel]
    else:
        cmd = ["bash", "-c", 'set -e; git add -- "$2"; '
               'git commit -q -m "$1" --only -- "$2"', "_", msg, rel]
    try:
        p = run(cmd, cwd=top, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=180)
    except subprocess.TimeoutExpired:
        return target, False, "timed out after 3 minutes"
    except OSError as exc:
        return target, False, str(exc)
    return target, p.returncode == 0, (p.stdout or "").strip()[-800:]
