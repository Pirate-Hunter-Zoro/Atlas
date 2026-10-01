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

THE PER-BOARD TUTOR DAEMON POLLS IT. Each pass `report` asks `sacct` about the
jobs that have not finished. A job that has reached a terminal state is claimed
once (`O_EXCL`, so two daemons never report the same job twice), its ending is
appended, and a `[job]` line is dropped in the inbox. That line wakes a turn the
way `[direction]` does, and the turn reports what finished.

Standard library only, like everything else.
"""

import json
import os
import shlex
import subprocess
import time

from .course import threads as course_threads

NAME = "jobs.jsonl"

# A job sacct has never heard of, this long after it was submitted, is LOST.
# sacct knows a job from the moment sbatch accepts it, so a quarter of an hour
# of silence is a different cluster, a purged database or a typed id.
LOST_AFTER = 15 * 60

# How often the daemon asks. A job is minutes to hours long; a minute late on
# its ending costs nothing, and sacct is a database call on a shared server.
POLL_SECONDS = 60

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


def append(root, rec):
    path = registry(root, create=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    course_threads._cache.pop(os.path.realpath(root), None)
    return path


def records(root):
    """`{jobid: record}`, folded."""
    return course_threads.merged(course_threads.jobs_of(root))


# ---------------------------------------------------------------------------
# submitting
# ---------------------------------------------------------------------------
def submit(root, thread, argv, produces=(), cwd=None, run=subprocess.run,
           now=None):
    """Run `sbatch`, and register the job to `thread`. `(record, error)`.

    `argv` must start with `sbatch`. `--parsable` is added where it is missing,
    so the id is read rather than scraped out of a sentence.
    """
    argv = list(argv or [])
    if not argv or os.path.basename(argv[0]) != "sbatch":
        return None, ("`board job` submits with sbatch, and this is %r. Put "
                      "the sbatch command after `--`." % (argv[:1] or [""])[0])
    cwd = os.path.abspath(cwd or os.getcwd())
    sent = argv[:1] + ([] if "--parsable" in argv else ["--parsable"]) + argv[1:]
    try:
        p = run(sent, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=120)
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
    rec = {
        "thread": thread,
        "jobid": jobid,
        "cmd": shlex.join(argv)[:CMD_CHARS],
        "cwd": _relative(root, cwd),
        "produces": list(produces or []),
        "log": _relative(root, stdout_of(jobid, cwd, run=run)),
        "submitted": float(now or time.time()),
    }
    append(root, rec)
    return rec, ""


def _relative(root, path):
    """A path inside the workspace as workspace-relative, anything else whole."""
    if not path:
        return ""
    path = os.path.abspath(path)
    base = os.path.abspath(root)
    if path == base:
        return "."
    if path.startswith(base + os.sep):
        return os.path.relpath(path, base)
    return path


def stdout_of(jobid, cwd, run=subprocess.run):
    """Where the job writes its output, as Slurm says, or "".

    Asked once, at submission, while `scontrol` still knows the job: it forgets
    a finished one within minutes, and the log is what a failure is reported
    with.
    """
    try:
        p = run(["scontrol", "show", "job", "-o", str(jobid)], cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    fields = {}
    for word in (p.stdout or "").split():
        k, _, v = word.partition("=")
        fields.setdefault(k, v)
    out = fields.get("StdOut", "")
    if not out:
        return ""
    base = str(jobid).split("_")[0]
    for pat, val in (("%j", base), ("%A", base), ("%x", fields.get("JobName", "")),
                     ("%u", fields.get("UserId", "").split("(")[0]),
                     ("%%", "%")):
        out = out.replace(pat, val)
    return out if os.path.isabs(out) else os.path.join(cwd, out)


# ---------------------------------------------------------------------------
# polling
# ---------------------------------------------------------------------------
def sacct(ids, run=subprocess.run):
    """`{base jobid: (state, exit, end)}` for the jobs sacct knows. None when
    sacct could not be asked at all, which is not the same as knowing nothing.

    An array job is several rows under one id. It is finished only when every
    row is, and it ended badly if any row did.
    """
    if not ids:
        return {}
    try:
        p = run(["sacct", "-X", "-n", "-P", "-j", ",".join(ids),
                 "-o", "JobID,State,ExitCode,End"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    rows = {}
    for line in (p.stdout or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 4 or not parts[0]:
            continue
        base = parts[0].split("_")[0].split(".")[0]
        rows.setdefault(base, []).append(
            (parts[1].split()[0].upper() if parts[1].strip() else "",
             parts[2], parts[3]))
    out = {}
    for base, got in rows.items():
        states = [s for s, _, _ in got]
        if all(s.rstrip("+") in course_threads.TERMINAL for s in states):
            bad = [g for g in got if g[0] != "COMPLETED"]
            pick = bad[0] if bad else got[0]
            out[base] = (pick[0], pick[1], max(e for _, _, e in got))
        else:
            live = [s for s in states if s not in course_threads.TERMINAL]
            out[base] = ("RUNNING" if "RUNNING" in live else live[0], "", "")
    return out


def _claim(root, jobid):
    """Exactly one reader reports each ending. True for the one that may."""
    d = os.path.join(root, "live", "jobs.reported")
    os.makedirs(d, exist_ok=True)
    try:
        fd = os.open(os.path.join(d, str(jobid).replace("/", "_")),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    except OSError:
        return False
    os.close(fd)
    return True


def poll(root, run=subprocess.run, now=None):
    """Ask sacct about every unfinished job. Returns the ones that ended now.

    A state change short of the end (PENDING to RUNNING) is appended too, so the
    board can say which. Nothing is appended for a job whose state is unchanged.
    """
    now = float(now or time.time())
    out = []
    open_jobs = course_threads.unfinished(course_threads.jobs_of(root))
    if not open_jobs:
        return out
    by_base = {}
    for j in open_jobs:
        by_base.setdefault(str(j["jobid"]).split("_")[0], []).append(j)
    said = sacct(sorted(by_base), run=run)
    if said is None:
        return out
    for base, recs in sorted(by_base.items()):
        for j in recs:
            got = said.get(base)
            if got is None:
                if now - float(j.get("submitted") or now) < LOST_AFTER:
                    continue
                got = ("LOST", "", "")
            state, code, end = got
            if state.rstrip("+") not in course_threads.TERMINAL:
                if state and state != j.get("state"):
                    append(root, {"jobid": j["jobid"], "thread": j.get("thread"),
                                  "state": state, "seen": now})
                continue
            if not _claim(root, j["jobid"]):
                continue
            end_rec = {"jobid": j["jobid"], "thread": j.get("thread"),
                       "state": state, "exit": code, "ended": end,
                       "reported": now}
            append(root, end_rec)
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
    if produced:
        lines += ["", "What it was to produce:"] + produced
    lines += ["", "DO THIS: write one card reporting what finished, what it "
              "produced, and any non-zero exit."]
    if failed(rec):
        lines.append("It did NOT end cleanly. Read the last 40 lines of its "
                     "log and put the error on the card, in your own words, "
                     "with the line it failed at.")
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
    ended = poll(root, run=run, now=now)
    for rec in ended:
        drop(root, rec, now=now)
    return ended


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
    for j in course_threads.unfinished(course_threads.jobs_of(root)):
        out.append({"jobid": j.get("jobid"), "thread": j.get("thread"),
                    "title": titles.get(j.get("thread"), j.get("thread") or ""),
                    "state": j.get("state") or "PENDING",
                    "submitted": j.get("submitted") or 0})
    out.sort(key=lambda j: -float(j["submitted"] or 0))
    return out
