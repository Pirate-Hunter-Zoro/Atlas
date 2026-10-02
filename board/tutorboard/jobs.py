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

A MACHINE WITHOUT SLURM FILES A REQUEST INSTEAD (the relay section below), and
`view` is the one registry a reader sees: local jobs, requests, and the
cluster's reports on them, merged.

Standard library only, like everything else.
"""

import json
import os
import re
import shlex
import shutil
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
           now=None, export=()):
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
    append(root, rec)
    return rec, ""


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
            live = [s for s in states
                    if s.rstrip("+") not in course_threads.TERMINAL]
            out[base] = ("RUNNING" if "RUNNING" in live else live[0], "", "")
    return out


# A claim older than this on an ending still not marked reported is a reader
# that died holding it, and the next pass takes it over.
CLAIM_STALE = 10 * 60


def _marker(root, jobid):
    return os.path.join(root, "live", "jobs.reported",
                        str(jobid).replace("/", "_"))


def _claim(root, jobid, now=None):
    """Exactly one reader reports each ending. True for the one that may."""
    target = _marker(root, jobid)
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


def _unclaim(root, jobid):
    try:
        os.remove(_marker(root, jobid))
    except OSError:
        pass


def poll(root, run=subprocess.run, now=None):
    """Ask sacct about every unfinished job. Returns the ones that ended now.

    A state change short of the end (PENDING to RUNNING) is appended too, so the
    board can say which. Nothing is appended for a job whose state is unchanged.
    """
    now = float(now or time.time())
    out = []
    every = course_threads.merged(course_threads.jobs_of(root)).values()
    # An ending recorded but never reported -- its reader died, or its inbox
    # line could not be written -- is offered again, without asking sacct.
    for j in every:
        if (course_threads.finished(j) and not j.get("reported")
                and _claim(root, j["jobid"], now)):
            out.append(dict(j))
    open_jobs = [j for j in every if not course_threads.finished(j)]
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
            # The ending is recorded before it is claimed, so a reader that
            # dies between the two leaves a finished job, not a running one.
            end_rec = {"jobid": j["jobid"], "thread": j.get("thread"),
                       "state": state, "exit": code, "ended": end}
            append(root, end_rec)
            if not _claim(root, j["jobid"], now):
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
    if failed(rec):
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
    check is `[coach]` (`holds.wake`).
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
    elif rid.startswith("check-"):
        # `relay/reports/check-<thread>-<n>.json` is a held step's check
        # (`holds.is_check`), so a request named so would share its report.
        problems.append("id %s starts with `check-`, which names a held "
                        "step's check report" % rid)
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
        for key in ("exit", "ended", "note", "produced", "exported", "relay",
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

    `(path, ok, said)`. `commit_alone` makes the commit.
    """
    target = os.path.join(requests_dir(root), req["id"] + ".json")
    if os.path.exists(target):
        return target, False, "%s is already there" % target
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(req, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    course_threads.forget(root)
    ok, said = commit_alone(root, target, "relay request %s" % req["id"],
                            run=run, push=push)
    return target, ok, said


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
