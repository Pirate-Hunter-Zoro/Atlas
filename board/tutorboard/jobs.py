"""jobs.py -- long work, labelled, and reporting itself.

`board job` runs `sbatch` and appends `{label, jobid, cmd, cwd, produces,
log, submitted}` to the subject's registry, `relay/state/jobs.jsonl`
(ignored). The relay polls it: `sacct` is refused on this cluster, so an end
is read from `squeue` plus the exit file every wrapped recipe writes last;
gone without the file is DIED, an unwrapped job ENDED with exit unknown. An
ending is claimed once (`O_EXCL`) and drops a `[job]` line that wakes a
turn. Without Slurm, `board job` files a relay request instead, and `view`
merges local jobs, requests and reports.

The constraint: the registry is append-only. State changes append records
folded by job id in file order (`exports.merged`), so two writers never
rewrite each other's lines.
"""

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import time

from . import cluster, exports, fenced

NAME = "jobs.jsonl"

# Grace before a fresh job missing from squeue without an exit file is DIED.
GRACE = 60

# Runtime state (exit codes, registry, claims, Colibri queue); ignored.
STATE = os.path.join("relay", "state")
REPORTED = os.path.join(STATE, "reported")
COLIBRI = os.path.join(STATE, "colibri")

# Where those records lived before, relative to a subject root.
OLD_LIVE = "live"
OLD_RELAY_CLAIMS = os.path.join(STATE, "jobs.reported")

CMD_CHARS = 600


def registry(root):
    """`relay/state/jobs.jsonl` in this subject, after `migrate_state`. Never
    creates the file."""
    migrate_state(root)
    return os.path.join(root, STATE, NAME)


def claims_dir(root):
    """Where every claim lives: job endings, heard reports, coach wakes."""
    return os.path.join(root, REPORTED)


# ---------------------------------------------------------------------------
# moving runtime state out of live/
# ---------------------------------------------------------------------------
def _old_live(root, live=None):
    """The old `live/`: `<root>/live`, or `live` when one is named."""
    return live or os.path.join(root, OLD_LIVE)


def _old_claim_dirs(root, live=None):
    return [os.path.join(_old_live(root, live), "jobs.reported"),
            os.path.join(root, OLD_RELAY_CLAIMS)]


def _tracked(root, rel):
    """Does git track `rel` in this subject? False where git cannot say."""
    try:
        p = subprocess.run(["git", "ls-files", "--error-unmatch", "--", rel],
                           cwd=root, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return True
    return p.returncode == 0


def _old_registries(root, live=None):
    """The old registries present here: `live/jobs.jsonl`, and an untracked
    root `jobs.jsonl` (a tracked one is the owner's, and the relay must not
    commit its move)."""
    out = []
    inner = os.path.join(_old_live(root, live), NAME)
    if os.path.isfile(inner):
        out.append(inner)
    top = os.path.join(root, NAME)
    if os.path.isfile(top) and not _tracked(root, NAME):
        out.append(top)
    return out


def _old_tasks(root, live=None):
    """`[(path, id)]` of Colibri task records under `live/missions/`."""
    where = os.path.join(_old_live(root, live), "missions")
    try:
        names = sorted(os.listdir(where))
    except OSError:
        return []
    out = []
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(where, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("kind") == "task":
            out.append((path, name[:-len(".json")]))
    return out


def _pending(root, live=None):
    """Is anything left in an old place? Cheap: a few stats and one listing."""
    if _old_registries(root, live) or _old_tasks(root, live):
        return True
    for d in _old_claim_dirs(root, live) + [
            os.path.join(_old_live(root, live), "coach.woken")]:
        if os.path.isdir(d):
            return True
    return False


def _move(src, dst):
    """Rename `src` to `dst`, or drop `src` where `dst` exists (one claim in
    two places is one claim). True if anything changed."""
    try:
        if os.path.lexists(dst):
            os.remove(src)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.rename(src, dst)
        return True
    except OSError:
        return False


def _rmdir(path):
    try:
        os.rmdir(path)
    except OSError:
        pass


def migrate_state(root, live=None):
    """Move this subject's runtime state out of `live/` into `relay/state/`:
    registries are appended, claims land in `reported/`, Colibri task
    records in `colibri/`. `live` names an old `live/` elsewhere.

    Idempotent and cheap when there is nothing to move, so every reader calls
    it first. Under a `flock`, so two readers never append one registry
    twice. Returns the number of paths moved.
    """
    if not root or not _pending(root, live):
        return 0
    state = os.path.join(root, STATE)
    try:
        os.makedirs(state, exist_ok=True)
        lock = open(os.path.join(state, ".migrate.lock"), "a")
    except OSError:
        return 0
    moved = 0
    try:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        # Renamed where there is none yet, else appended: records fold by id.
        target = os.path.join(state, NAME)
        for old in _old_registries(root, live):
            try:
                if not os.path.exists(target):
                    os.rename(old, target)
                else:
                    with open(old, "r", encoding="utf-8") as fh:
                        text = fh.read()
                    if text and not text.endswith("\n"):
                        text += "\n"
                    with open(target, "a", encoding="utf-8") as fh:
                        fh.write(text)
                    os.remove(old)
                moved += 1
            except OSError:
                continue
        # The claims, under their own names.
        claims = claims_dir(root)
        for d in _old_claim_dirs(root, live):
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for name in names:
                moved += _move(os.path.join(d, name),
                               os.path.join(claims, name))
            _rmdir(d)
        woken = os.path.join(_old_live(root, live), "coach.woken")
        try:
            names = os.listdir(woken)
        except OSError:
            names = []
        for name in names:
            moved += _move(os.path.join(woken, name),
                           os.path.join(claims, "coach-" + name))
        if names:
            _rmdir(woken)
        # The Colibri queue: each task record and its claim flags.
        queue = os.path.join(root, COLIBRI)
        for path, tid in _old_tasks(root, live):
            where = os.path.dirname(path)
            try:
                flags = [n for n in os.listdir(where)
                         if n.startswith(tid + ".task.")]
            except OSError:
                flags = []
            for name in flags:
                moved += _move(os.path.join(where, name),
                               os.path.join(queue, name))
            moved += _move(path, os.path.join(queue, tid + ".json"))
    finally:
        lock.close()
    return moved


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
    """Append one record to the registry."""
    path = registry(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
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


def records(root, relay=None):
    """`{jobid: record}`, folded. `relay` True keeps the relay's jobs (records
    carrying `request`), False the others, None all."""
    out = exports.merged(_lines(registry(root)))
    if relay is None:
        return out
    return dict((k, v) for k, v in out.items()
                if bool(v.get("request")) == bool(relay))


def state_dir(root):
    return os.path.join(root, STATE)


# ---------------------------------------------------------------------------
# submitting
# ---------------------------------------------------------------------------
def submit(root, label, argv, produces=(), cwd=None, run=subprocess.run,
           now=None, export=(), env=None, extra=None):
    """Run `sbatch` and register the job under `label`. `(record, error)`.

    `argv` must start with `sbatch`; `--parsable` is added so the id is read,
    not scraped. `extra` fields ride on the record (its `cmd` wins).
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
        "label": label or "",
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
    # The registry is ignored, so it may name a log outside the workspace.
    rec["log_path"], rec["err_path"] = out, err
    append(root, rec)
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
    """Task count of the header's `--array`: None without one, 0 when
    unreadable (every task file is then required). Pure."""
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


# The shared failure fingerprint: `relay_trap.sh`, `relay_hook.py` and the
# `sitecustomize.py` that installs the hook in every Python a job starts.
FINGERPRINT_LIB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cluster",
    "lib")


def fingerprint(root, recipe):
    """`{root, stage, config, lib}` that `wrapper` exports, so a recipe is
    fingerprinted whether or not it sources `relay_trap.sh`."""
    from .course import config
    said = config.read_config(root).get("relay", {}).get("fingerprint")
    return {"root": os.path.realpath(root), "stage": recipe,
            "config": json.dumps(said if isinstance(said, dict) else {},
                                 sort_keys=True),
            "lib": FINGERPRINT_LIB}


def wrapper(header, command, exitfile, name="", fp=None):
    """A batch script: `header`, `command`, then the exit code written to
    `exitfile` as its last act. Pure.

    No trap, because a job killed at its limit must leave no file: that
    absence tells a death from an ending. An array task writes
    `<stem>_<task>.exit`. With `fp` it exports the fingerprint variables and
    puts board/cluster/lib on PYTHONPATH, and prints a `RELAY:` line on a
    non-zero exit.
    """
    lines = ["#!/bin/bash"] + list(header)
    if name and not any(re.match(r"#SBATCH\s+(--job-name|-J)\b", h)
                        for h in header):
        lines.append("#SBATCH --job-name=%s" % name)
    stem = exitfile[:-len(".exit")] if exitfile.endswith(".exit") else exitfile
    lines += [
        "# Written by the relay: runs the command below, then records its exit",
        "# code. That file is how the end of this job is read without sacct.",
    ]
    if fp:
        lines += [
            "export RELAY_ROOT=%s" % shlex.quote(fp["root"]),
            "export RELAY_STAGE=%s" % shlex.quote(fp["stage"]),
            "export RELAY_CONFIG=%s" % shlex.quote(fp["config"]),
            "export RELAY_WRAPPED=1",
            'export PYTHONPATH=%s"${PYTHONPATH:+:$PYTHONPATH}"'
            % shlex.quote(fp["lib"]),
        ]
    lines += [
        " ".join(shlex.quote(c) for c in command),
        "code=$?",
    ]
    if fp:
        lines += [
            'if [ "$code" -ne 0 ]; then',
            '    sha="$(git -C "$RELAY_ROOT" rev-parse --short HEAD 2>/dev/null)"',
            "    printf 'RELAY: recipe %s failed: exit %s, checkout %s\\n' "
            '"$RELAY_STAGE" "$code" "${sha:-unknown}" >&2',
            "fi",
        ]
    lines += [
        'out=%s"${SLURM_ARRAY_TASK_ID:+_$SLURM_ARRAY_TASK_ID}".exit'
        % shlex.quote(stem),
        'printf \'%s\\n\' "$code" > "$out.tmp" && mv -f "$out.tmp" "$out"',
        'exit "$code"',
    ]
    return "\n".join(lines) + "\n"


def local_key(now=None):
    """The key of a job `board job` submits directly: never a request id."""
    return "local-%d-%d" % (int(float(now or time.time()) * 1000), os.getpid())


def submit_script(root, label, header, command, key, shown_as, produces=(),
                  export=(), env=None, run=subprocess.run, now=None,
                  sbatch_env=None, extra=None, fp=None):
    """Write the wrapper at `relay/state/<key>.sbatch` and submit it from the
    workspace root. `(record, error)`. `env` is already `validate`d."""
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
                  os.path.splitext(os.path.basename(shown_as.split()[0]))[0])[:40]
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(wrapper(header, command, exitfile, name=name, fp=fp))
    sent = ["sbatch"]
    if env:
        sent.append("--export=ALL," + ",".join(
            "%s=%s" % (k, env[k]) for k in sorted(env)))
    sent.append(script)
    shown = " ".join([shown_as] + ["%s=%s" % (k, env[k]) for k in sorted(env)])
    fields = {"cmd": shown[:CMD_CHARS], "key": key,
              "exitfile": _relative(root, exitfile)}
    tasks = array_tasks(header)
    if tasks is not None:
        fields["array_tasks"] = tasks
    fields.update(extra or {})
    return submit(root, label, sent, produces=produces, cwd=root, run=run,
                  now=now, export=export, env=sbatch_env, extra=fields)


def submit_recipe(root, label, recipe, env=None, produces=(), export=(),
                  key=None, run=subprocess.run, now=None, sbatch_env=None,
                  extra=None):
    """Submit a tracked recipe, wrapped, run under `bash` from the workspace
    root as a bare sbatch of it would be."""
    full = os.path.join(root, recipe)
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            header = header_of(fh.read())
    except OSError as exc:
        return None, "the recipe %s cannot be read: %s" % (recipe, exc)
    return submit_script(root, label, header, ["bash", full],
                         key or local_key(now), recipe, produces=produces,
                         export=export, env=env, run=run, now=now,
                         sbatch_env=sbatch_env, extra=extra,
                         fp=fingerprint(root, recipe))


def _redacted(argv):
    """The argv with every `--export` value reduced to its names, because an
    exported value can be a protected storage path."""
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
    """A workspace path made relative; any other path by file name alone,
    because an outside path names storage."""
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
    """`(stdout, stderr)` log paths as Slurm says, "" for unknown; an array's
    `%a` becomes `*`. Asked at submission, because `scontrol` forgets a
    finished job within minutes.
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
    """`{base jobid: state}` for this user's jobs Slurm still knows, or None
    when squeue could not be asked (not the same as knowing nothing). An
    array is RUNNING if any task is.
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
    # Listing first makes NFS revalidate the directory, so a fresh file is not
    # missed on a cached negative lookup.
    try:
        os.listdir(os.path.dirname(full))
    except OSError:
        pass
    tasks = rec.get("array_tasks")
    arrayed = _array_exits(full)
    if tasks is not None and not isinstance(tasks, bool):
        # A task killed at its limit writes no file, so a missing one is a death.
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
    """`(state, exit, ended)` for a job that left `squeue`, or None while too
    fresh: COMPLETED or FAILED from the exit file, DIED when wrapped without
    one, ENDED (exit unknown) when unwrapped."""
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


# Gone this long, over two passes, before DIED: another node's NFS view lags.
GONE_GRACE = 60


# A claim this old on an unreported ending belongs to a dead reader.
CLAIM_STALE = 10 * 60


def _marker(root, key):
    return os.path.join(claims_dir(root), str(key).replace("/", "_"))


def _adopt(root, key):
    """The claim on `key` at its new place, adopted from an old place so a
    job from before the move is still claimed once. The new path."""
    target = _marker(root, key)
    if os.path.lexists(target):
        return target
    name = os.path.basename(target)
    for d in _old_claim_dirs(root):
        old = os.path.join(d, name)
        if os.path.lexists(old):
            _move(old, target)
            break
    return target


def _claim(root, jobid, now=None):
    """Exactly one reader reports each ending. True for the one that may."""
    target = _adopt(root, jobid)
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


def poll(root, run=subprocess.run, now=None, relay=False):
    """Ask squeue about every unfinished job; return the ones that ended now.

    `relay` True polls the relay's jobs, False the others (whose endings
    `report` drops in the inbox); each job is polled by exactly one. State
    changes short of the end are appended too; unchanged ones are not.
    """
    now = float(now or time.time())
    out = []
    every = records(root, relay=relay).values()
    # An ending recorded but never reported is offered again.
    for j in every:
        if (exports.finished(j) and not j.get("reported")
                and _claim(root, j["jobid"], now)):
            out.append(dict(j))
    open_jobs = [j for j in every if not exports.finished(j)
                 and str(j.get("state") or "").upper()
                 != exports.REQUESTED]
    if not open_jobs:
        return out
    said = squeue(run=run)
    if said is None:
        return out
    for j in open_jobs:
        base = str(j["jobid"]).split("_")[0]
        state = said.get(base)
        if state is not None and state.rstrip("+") not in exports.TERMINAL:
            if state != j.get("state") or j.get("gone_at"):
                append(root, {"jobid": j["jobid"], "label": j.get("label"),
                              "state": state, "seen": now, "gone_at": 0})
            continue
        # Gone, or about to leave: the exit file says how it ended.
        got = ending(root, j, now)
        if got is None:
            continue
        state, code, end = got
        if state == "DIED":
            gone = j.get("gone_at")
            if not gone:
                append(root, {"jobid": j["jobid"], "gone_at": now})
                continue
            if now - float(gone) < GONE_GRACE:
                continue
        # Recorded before claimed, so a dying reader leaves a finished job.
        end_rec = {"jobid": j["jobid"], "label": j.get("label"),
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


def title_of(rec):
    """How a line names the work a record is: its label, else the thread an
    older request named, else the request or job id."""
    rec = rec or {}
    return str(rec.get("label") or rec.get("thread") or rec.get("request")
               or rec.get("jobid") or "unlabelled work")


def _relay_said(value):
    """A report's `relay` lines as a list, whichever shape the cluster wrote."""
    if isinstance(value, str):
        return [l for l in value.splitlines() if l.strip()]
    return [str(l) for l in (value or []) if str(l).strip()]


def relay_sense(root, rec):
    """The inbox line for a cluster report. Everything the turn reports is in
    it, because the log stays on the cluster; a log cut appears only where
    phi is false. A failure the Mac repairs opens `[repair]`.
    """
    state = str(rec.get("state") or "")
    repair = repairs(root, rec)
    lines = [
        "[%s] A cluster report on %s has come back: %s."
        % (REPAIR if repair else "job", title_of(rec),
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
    if rec.get("commit"):
        lines.append("  filed at %s" % str(rec["commit"])[:12])
    if rec.get("ran_at"):
        lines.append("  ran at   %s, the cluster's HEAD" % rec["ran_at"])
    if rec.get("error"):
        lines.append("  error    %s" % rec["error"])
    moved = ran_elsewhere(root, rec)
    if moved:
        lines += ["", moved]
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
    excerpt = _relay_said(rec.get("output"))
    if excerpt:
        cut = rec.get("output_cut") or 0
        lines += ["", "Its log, %s line(s)%s (the subject's phi is false):"
                  % (rec.get("output_total") or len(excerpt),
                     ", %s cut from the middle" % cut if cut else "")]
        lines += ["    " + l for l in excerpt]
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
    elif rec.get("kind") == "libr-ai" and not failed(rec) and excerpt:
        lines.append("This was a task for IT's model server "
                     "(`libr-ai`): its log above is the model's answer. Check it "
                     "against the files before the card repeats any of it.")
    elif failed(rec) and excerpt:
        lines.append("It did NOT end cleanly. Its RELAY: lines and its log, "
                     "above, are what it says.")
    elif failed(rec):
        lines.append("It did NOT end cleanly. Its log stays on the cluster, "
                     "and the RELAY: lines are what it says here.")
    elif rec.get("fixes"):
        lines.append("It ended cleanly, so the repair of %s is done: the card "
                     "says what the fix was." % rec["fixes"])
    if move_on:
        lines.append("A follow-up goes through `board job`, never a bare "
                     "sbatch.")
    return "\n".join(lines)


# The relay's own traffic: a commit between `commit` and `ran_at` touching
# only these changed nothing the request ran.
_TRAFFIC_RE = re.compile(r"(^|/)(relay/requests|relay/reports|exports)/"
                         r"|^relay/status\.json$")


def ran_elsewhere(root, rec):
    """"", or the sentence saying a report ran at code other than its
    request's `commit` beyond relay traffic, or that this checkout cannot
    tell."""
    commit, ran = str(rec.get("commit") or ""), str(rec.get("ran_at") or "")
    if not (COMMIT_RE.match(commit) and COMMIT_RE.match(ran)):
        return ""
    if commit.startswith(ran) or ran.startswith(commit):
        return ""
    top = _git_text(root, ["rev-parse", "--show-toplevel"]) or root
    if _git_text(top, ["cat-file", "-e", ran + "^{commit}"]) is None:
        return ("It ran at %s, which this checkout does not have, and was "
                "filed after %s: say so on the card, since the code it ran "
                "cannot be checked here." % (ran, commit[:12]))
    changed = [p for p in _git_lines(top, ["diff", "--name-only", "-z",
                                           commit, ran])
               if not _TRAFFIC_RE.search(p)]
    if not changed:
        return ""
    return ("It ran at %s, not at %s, the commit it was filed after: %d "
            "file(s) changed between them (%s). Say on the card which code "
            "the result belongs to." % (
                ran, commit[:12], len(changed), ", ".join(changed[:5])
                + (", ..." if len(changed) > 5 else "")))


# ---------------------------------------------------------------------------
# a failed relay job: repaired on the Mac
# ---------------------------------------------------------------------------
# A failed recipe wakes a `[repair]` doing turn on the Mac. It reads the
# report's `RELAY:` lines and the code, then fixes and reruns (`board job
# --fixes`) or files a diagnostic recipe (`board diagnose`). No model runs
# beside the data. `MAX_FIXES` attempts per failure, counted off
# `relay/requests/`; then the owner decides (`--fresh`).

# The signal a repair turn is woken with.
REPAIR = "repair"


def ended_failed(rec):
    """Did this relayed record end, and not cleanly?"""
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
    """Is this repair request a diagnostic rather than a rerun of the failed
    recipe?"""
    origin = rec.get("fixes")
    if not origin:
        return False
    first = _request(root, origin) or {}
    mine = _request(root, rec.get("request") or rec.get("id")) or {}
    return (mine.get("kind") == "recipe"
            and exports.rel(mine.get("recipe"))
            != exports.rel(first.get("recipe")))


def _last_run(root, origin):
    """The newest request that ran `origin`'s own recipe: its last rerun, or
    `origin` itself."""
    first = _request(root, origin) or {}
    recipe = exports.rel(first.get("recipe"))
    runs = [r for r in attempts(root, origin) if r.get("kind") == "recipe"
            and exports.rel(r.get("recipe")) == recipe]
    return runs[-1] if runs else first


def repairs(root, rec):
    """Does this report wake a repair turn: a failed recipe or a returned
    diagnostic?"""
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
            rel = exports.rel(os.path.relpath(path, root))
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
_STEP_LINE_RE = re.compile(r"\b(?:failed: exit \d+|stopped) after line (\d+)")


def failure_sites(relay):
    """`(["file:line", ...], recipe line or "")` out of a report's RELAY
    lines: where Python failed, and the recipe line the shell stopped after."""
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


def _rerun_argv(origin, req):
    """`board job` argv rerunning `req` as a repair of `origin`."""
    req = req or {}
    argv = ["board", "job"]
    if isinstance(req.get("label"), str) and req["label"]:
        argv += ["--label", req["label"]]
    argv += ["--fixes", origin]
    for p in _strings(req.get("produces")):
        argv += ["--produces", p]
    for p in _strings(req.get("export")):
        argv += ["--export", p]
    argv += ["--", str(req.get("recipe") or "<recipe>")]
    env = req.get("env") if isinstance(req.get("env"), dict) else {}
    argv += ["%s=%s" % (k, env[k]) for k in sorted(env)]
    return argv


def subject_check(root):
    """The subject's `check` line, or `""`."""
    from .course import config as course_config
    try:
        return str(course_config.read_config(root).get("check_line") or "")
    except Exception:                                        # noqa: BLE001
        return ""


def _repair_said(root, rec):
    """What a repair turn does with this report: fix and rerun, ask with a
    diagnostic, or stop at the cap."""
    rid = rec["request"]
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
                 "theirs." % (MAX_FIXES, origin), "", "The attempts:"]
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
    rerun = _rerun_argv(origin, _last_run(root, origin))
    recipe = rerun[rerun.index("--") + 1]
    check = subject_check(root)
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
        "  1. Fix it here, in the code the failure points at and the recipe, "
        "%s. Change nothing else." % recipe,
        "  2. Run %s. If a check fails, stop: no rerun, and the card says "
        "what you tried and that the owner decides."
        % ("the subject's check, %s" % check if check else
           "the tests beside the code you changed (this subject declares no "
           "`check` in its tutorboard.json)"),
        "  3. Ship it: board push \"<what changed>\" -- <the paths you "
        "changed>. If the push is refused, stop the same way: a rerun of "
        "code the cluster has not pulled runs the old code.",
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
        lines += ["     board diagnose --fixes %s -- %s%s"
                  % (origin, d, "".join(" [%s=...]" % n for n in names))
                  for d, names in found] or [
            "     board diagnose --fixes %s -- <diagnose.sbatch> "
            "[VAR=value ...]" % origin]
        lines.append("   A question no diagnostic here answers is a new one: "
                     "write it as a recipe beside the others that prints "
                     "names and counts behind RELAY: -- never a value, a row "
                     "or a message -- ship it with `board push`, then file it.")
    lines += ["",
              "This is automatic attempt %d of %d for %s; a diagnostic and a "
              "rerun each count. The card says what failed and where, which "
              "of A or B you did, and what you changed."
              % (k, MAX_FIXES, origin)]
    return lines, False


def _refused_fix_said(rec):
    """A refused diagnostic or rerun: the repair stops, and the owner
    decides."""
    return ["The cluster would not run this attempt to repair %s. Do not file "
            "it again, and file no other diagnostic or rerun for %s: the card "
            "lists what it refused and that the owner decides next."
            % (rec["fixes"], rec["fixes"])]


def repair_brief(root, rids):
    """`board brief`'s section for a repair turn, per request it was woken
    for. `rids` is one id or a list."""
    if isinstance(rids, str) or rids is None:
        rids = [rids] if rids else []
    rids = [r for i, r in enumerate(rids) if r and r not in rids[:i]]
    out = ["--- THIS TURN REPAIRS A FAILED CLUSTER JOB ---",
           "A doing turn, whatever the mode above says: its product is the "
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
    check = subject_check(root)
    out.append("  check    %s" % (check or "none: the subject's tutorboard.json "
                                  "declares no `check`"))
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


def _messages(root, path=None):
    """The inbox lines of the session bound for `root`, or of the inbox at
    `path` (the server runs every session at once)."""
    from .course import repo as course_repo
    path = path or course_repo.session_path(root, "inbox", "messages.jsonl")
    out = []
    if not path:
        return out
    try:
        with open(path, "r", encoding="utf-8") as fh:
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


def batch_repairs(root, out, path=None):
    """The requests of every `[repair]` message in the batch `out` (what
    `board inbox` printed for one turn), in order. `path` is the session's
    inbox."""
    printed = set()
    for line in (out or "").splitlines():
        m = _STAMP_RE.match(line.strip())
        if m:
            printed.add(m.group(1).strip() + " " + line.strip()[m.end():])
    rids = []
    for msg in _messages(root, path):
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


def open_fix(root, recipe, env=None):
    """`""`, or the request a plain `board job -- <recipe>` would rerun
    outside its open repair. Keyed on the recipe alone, so a capped repair
    cannot restart by changing a VAR or label; such a rerun must carry
    `--fixes`. `env` is accepted and not read."""
    recipe = exports.rel(recipe) or ""
    reqs = requests(root)
    by_id = dict((r.get("id"), r) for r in reqs)
    runs = [r for r in reqs if r.get("kind") == "recipe"
            and exports.rel(r.get("recipe")) == recipe]
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
    """The `[job]` inbox line: what ended, what it was to produce, what to do.
    The log is named, never copied, because some inboxes are tracked."""
    if rec.get("request") and str(rec.get("jobid", "")).startswith("relay:"):
        return relay_sense(root, rec)
    produced = []
    for p in rec.get("produces") or []:
        produced.append("  %s %s" % ("present" if os.path.exists(
            os.path.join(root, p)) else "MISSING", p))
    lines = [
        "[job] A job, %s, has ended." % title_of(rec),
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
    lines.append("A follow-up job goes through `board job`, never a bare "
                 "sbatch.")
    return "\n".join(lines)


def drop(root, rec, now=None, text=None, signal="job"):
    """Put a machinery line where `cluster.wake` routes it: the filing
    session's inbox (which wakes a turn), else a home notice. A relay record's
    request id and session ride along for `board brief`."""
    rec = rec or {}
    return cluster.wake(root, rec.get("session"),
                        text if text is not None else sense(root, rec),
                        wake=True, signal=signal, request=rec.get("request"),
                        now=now)


def report(root, run=subprocess.run, now=None):
    """One pass: poll, and drop a `[job]` line for every job that ended.
    Without Slurm, `hear` drops the cluster's endings the same way."""
    heard = [] if has_slurm() else hear(root, now=now)
    ended, out = poll(root, run=run, now=now), heard
    for rec in ended:
        try:
            drop(root, rec, now=now)
        except Exception:                                    # noqa: BLE001
            # No line, so no claim: the next pass offers it again.
            _unclaim(root, rec["jobid"])
            continue
        append(root, {"jobid": rec["jobid"],
                      "reported": float(now or time.time())})
        out.append(rec)
    return out


# ---------------------------------------------------------------------------
# what the board shows
# ---------------------------------------------------------------------------
def running(root):
    """The unfinished jobs, newest first, for the busy strip."""
    out = []
    for j in view(root).values():
        if exports.finished(j):
            continue
        out.append({"jobid": j.get("slurm") or j.get("jobid"),
                    "thread": j.get("thread"), "label": j.get("label"),
                    "title": j.get("label") or j.get("thread") or "",
                    "state": j.get("state") or "PENDING",
                    "submitted": j.get("submitted") or 0})
    out.sort(key=lambda j: -float(j["submitted"] or 0))
    return out


# ---------------------------------------------------------------------------
# the relay: a request the Mac commits, a report the cluster commits
# ---------------------------------------------------------------------------
# Without Slurm nothing is submitted: the Mac commits and pushes
# `relay/requests/<id>.json`, the cluster validates it again, runs it and
# commits `relay/reports/<id>.json`. One file per request, never edited, so
# two machines never write the same file.

RELAY = "relay"
# `turn` exists only so `validate` refuses it by name (`NO_TURN`): no hosted
# model runs on an institute machine. `libr-ai` is IT's own model server
# (`libr_ai.py`), for subjects whose phi is false.
KINDS = ("recipe", "turn", "colibri", "libr-ai")
REPORT_STATES = ("refused", "submitted", "running", "completed", "failed")

# Report states. `REFUSED` is terminal; `REQUESTED` (no report yet) is not.
_AS_SLURM = {"refused": "REFUSED", "submitted": "PENDING",
             "running": "RUNNING", "completed": "COMPLETED",
             "failed": "FAILED"}

REQUEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
VAR_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")
# `#RELAY-VAR NAME PATTERN` in a recipe's header, the way `#SBATCH` is: one
# line per variable the recipe accepts, the value fully matching PATTERN.
VAR_LINE_RE = re.compile(r"^#RELAY-VAR\s+(\S+)\s+(\S.*?)\s*$")
# Never accepted from a request: these change what runs. Nor any RELAY_
# name, which is the wrapper's fingerprint.
FORBIDDEN_VARS = ("ALL", "NONE", "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH",
                  "PYTHONPATH", "PYTHONSTARTUP", "BASH_ENV", "ENV", "HOME",
                  "SHELL", "IFS", "PROMPT_COMMAND")
# `thread` is accepted and ignored. `commit` is the Mac's HEAD at filing; the
# cluster refuses a request whose commit its HEAD lacks.
REQUEST_KEYS = {
    "recipe": ("id", "kind", "label", "session", "thread", "recipe", "env",
               "produces", "export", "filed", "fixes", "commit"),
    "colibri": ("id", "kind", "label", "session", "thread", "brief", "filed",
                "commit"),
    "libr-ai": ("id", "kind", "label", "session", "thread", "brief", "model",
                "filed", "commit"),
}
# A model on IT's server, as Open WebUI names it: `gpt-oss:120b`.
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
# A label names the work; a session is the Mac session it was filed from.
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_BRIEF = 2000
MAX_VALUE = 200
NO_TURN = ("a `turn` request asks for a hosted model on the cluster, and the "
           "system never runs one there: every model turn runs on the Mac. "
           "File a recipe, a `colibri` task where the workspace takes them, or "
           "a `libr-ai` task from a subject whose phi is false")
# Automatic repair attempts per failed request. `fixes` always names the
# first failure, so the count is the requests on disk naming it.
MAX_FIXES = 3


def has_slurm():
    """Can this machine submit? `TUTOR_SLURM=0|1` overrides, for tests."""
    forced = os.environ.get("TUTOR_SLURM", "").strip()
    if forced in ("0", "1"):
        return forced == "1"
    return shutil.which("sbatch") is not None


def requests_dir(root):
    return os.path.join(root, RELAY, "requests")


def reports_dir(root):
    return os.path.join(root, RELAY, "reports")


def declarations(text):
    """`({NAME: pattern}, problems)` out of a recipe's header (up to the
    first line neither blank nor a comment). Pure."""
    declared, problems = {}, []
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            break
        m = VAR_LINE_RE.match(s)
        if not m:
            continue
        name, pattern = m.group(1), m.group(2)
        if (not VAR_NAME_RE.match(name) or name in FORBIDDEN_VARS
                or name.startswith("RELAY_")):
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


def validate(req, allowed, tracked, declared, taken=(), colibri=False,
             phi_false=False):
    """`(request, problems)`: may this request run? Pure; the Mac calls it
    before committing and the cluster before submitting.

        req       the request, as parsed JSON
        allowed   the subject's approved exports, `exports.approvals`
        tracked   workspace-relative paths tracked and unchanged at HEAD
        declared  `{recipe: (declared, problems)}`, `declarations` per recipe
        taken     request ids already filed
        colibri   has this workspace opted in to `colibri` requests
        phi_false does its tutorboard.json say `"phi": false`, which a
                  `libr-ai` request needs

    Refused whole, with every problem at once.
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
    filed = req.get("filed")
    if filed is not None and (isinstance(filed, bool)
                              or not isinstance(filed, (int, float))):
        problems.append("`filed` is seconds since the epoch")
    fixes = req.get("fixes")
    if "fixes" in req and (not isinstance(fixes, str)
                           or not REQUEST_ID_RE.match(fixes) or fixes == rid):
        problems.append("`fixes` names a request id")
    commit = req.get("commit")
    if "commit" in req and (not isinstance(commit, str)
                            or not COMMIT_RE.match(commit)):
        problems.append("`commit` is a commit's hex sha")

    out = {"id": rid, "kind": kind}
    label = req.get("label")
    if label is not None:
        if not isinstance(label, str) or not LABEL_RE.match(label):
            problems.append("label %r must be 1-40 characters of a-z, 0-9 and "
                            "hyphen" % (label,))
        else:
            out["label"] = label
    session = req.get("session")
    if session is not None:
        if not isinstance(session, str) or not SESSION_RE.match(session):
            problems.append("session %r is not a session id" % (session,))
        else:
            out["session"] = session
    if filed is not None:
        out["filed"] = filed
    if isinstance(commit, str) and COMMIT_RE.match(commit):
        out["commit"] = commit

    if kind in ("colibri", "libr-ai"):
        brief = req.get("brief")
        if not isinstance(brief, str) or not brief.strip():
            problems.append("a %s request needs a `brief`" % kind)
        elif len(brief) > MAX_BRIEF:
            problems.append("the brief is %d characters and the cap is %d"
                            % (len(brief), MAX_BRIEF))
        # Colibri reads PHI, unattended, so a workspace opts in to it.
        if kind == "colibri" and not colibri:
            problems.append("this workspace has not opted in to Colibri tasks: "
                            "`relay.colibri: true` in its tutorboard.json")
        # IT's server keeps every chat, so only a subject with no PHI uses it.
        if kind == "libr-ai" and not phi_false:
            problems.append("IT's model server keeps every chat, so it takes "
                            "work only from a subject whose tutorboard.json "
                            "says `\"phi\": false`; a PHI subject uses Colibri")
        if kind == "libr-ai" and "model" in req:
            model = req.get("model")
            if not isinstance(model, str) or not MODEL_RE.match(model):
                problems.append("model %r is not a model name" % (model,))
            else:
                out["model"] = model
        out["brief"] = brief.strip() if isinstance(brief, str) else ""
        return (None, problems) if problems else (out, [])

    recipe = exports.rel(req.get("recipe"))
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
        rel = exports.rel(p)
        if rel is None:
            problems.append("produces %r is not a path inside this workspace"
                            % p)
        else:
            produces.append(rel)
    export = []
    for p in _plain_list(req.get("export"), "export", problems):
        rel = exports.rel(p)
        if rel is None or not rel.startswith("results/"):
            problems.append("export %r must be a path under results/" % p)
            continue
        ok_, why = exports.approved(allowed, rel)
        if ok_:
            export.append(rel)
        else:
            problems.append(why)
    out.update({"recipe": recipe, "env": dict(env), "produces": produces,
                "export": export})
    if fixes is not None:
        out["fixes"] = fixes
    return (None, problems) if problems else (out, [])


def fix_problems(req, filed, failed_ids, mine=False):
    """Every problem with this request's `fixes`, `[]` without one. Pure.

        req         the request
        filed       the requests already filed, as `requests` reads them
        failed_ids  ids of requests whose report says they failed
        mine        the cluster checking a filed request: only earlier
                    attempts count against the cap

    `fixes` must name a failed recipe request that is itself no fix. An
    attempt past `MAX_FIXES` is refused on both machines, which is what stops
    a job that keeps failing.
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
    """What `validate` is handed, read off this workspace. A recipe counts as
    tracked only if unchanged at HEAD, because the cluster never sees an
    uncommitted edit."""
    tracked = set(_git_lines(root, ["ls-files", "-z", "--", "."]))
    changed = set(_git_lines(root, ["diff", "--name-only", "-z", "--relative",
                                    "HEAD", "--", "."]))
    tracked -= changed
    declared = {}
    for r in recipes:
        rel = exports.rel(r)
        if not rel:
            continue
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8",
                      errors="replace") as fh:
                declared[rel] = declarations(fh.read())
        except OSError:
            declared[rel] = ({}, [])
    relay = relay_opts(root)
    filed = requests(root)
    taken = set(r["id"] for r in filed)
    failed_ids = set(r["request"] for r in relayed(root) if ended_failed(r))
    return {"allowed": exports.approvals(root), "tracked": tracked, "declared": declared,
            "taken": taken, "colibri": relay.get("colibri") is True,
            "phi_false": phi_false(root),
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


def phi_false(root):
    """Does this workspace's own `tutorboard.json` say `"phi": false`,
    literally? Anything else, a missing file included, is no."""
    try:
        with open(os.path.join(root, "tutorboard.json"), "r",
                  encoding="utf-8") as fh:
            said = json.load(fh)
    except (OSError, ValueError):
        return False
    return isinstance(said, dict) and said.get("phi") is False


def relay_opts(root):
    """This workspace's relay opt-in, `colibri`, from its own
    `tutorboard.json` alone. There is no machine-wide default."""
    return dict(_relay_of(os.path.join(root, "tutorboard.json")))


def check(root, req, mine=False, pending=()):
    """`validate` with this workspace's context. `(request, problems)`.
    `mine`: the cluster checking a filed request, whose id is its own.
    `pending`: requests filed in the same batch, whose ids are taken and
    whose `fixes` count against the cap."""
    if isinstance(req, dict):
        req = dict((k, v) for k, v in req.items() if k != FILE_KEY)
    recipe = req.get("recipe") if isinstance(req, dict) else None
    ctx = context(root, [recipe] if isinstance(recipe, str) else [])
    pending = [r for r in pending or () if isinstance(r, dict)]
    taken = ctx["taken"] | set(r.get("id") for r in pending)
    if mine and isinstance(req, dict):
        taken = taken - set([req.get("id")])
    ok, problems = validate(req, ctx["allowed"], ctx["tracked"],
                            ctx["declared"], taken, ctx["colibri"],
                            ctx["phi_false"])
    extra = fix_problems(req, list(ctx["filed"]) + pending, ctx["failed"],
                         mine)
    extra += pin_problems(root, req)
    if extra:
        return None, problems + extra
    return ok, problems


def head(root, short=False):
    """This checkout's HEAD sha, short where asked; "" outside git."""
    return _git_text(root, ["rev-parse"] + (["--short"] if short else [])
                     + ["HEAD"]) or ""


def pin_problems(root, req):
    """`[]`, or why HEAD here lacks the commit the request was filed after,
    so the cluster never runs code older than the push. No `commit`, no pin."""
    commit = req.get("commit") if isinstance(req, dict) else None
    if not isinstance(commit, str) or not COMMIT_RE.match(commit):
        return []                                   # `validate` says why
    try:
        p = subprocess.run(["git", "merge-base", "--is-ancestor", commit,
                            "HEAD"], cwd=root, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        code = p.returncode
    except (OSError, subprocess.SubprocessError):
        code = -1
    if code == 0:
        return []
    # An open coding session pushes to code/<session>: a request from it may
    # pin a commit on that ref when the held paths here match it.
    session = req.get("session")
    if isinstance(session, str) and session:
        from . import code as coding
        if coding.pin_ok(root, session, commit):
            return []
    return ["HEAD here (%s) does not contain commit %s, the commit this "
            "request was filed after, so it would not run the code it was "
            "filed for" % (head(root, short=True) or "unknown", commit[:12])]


def dirty(root):
    """Tracked paths under `root` that differ from HEAD, staged or not,
    relative to `root`. `[]` outside git."""
    return sorted(set(_git_lines(root, ["diff", "--name-only", "-z",
                                        "--relative", "HEAD", "--", "."])))


def dirty_said(root, paths):
    """The refusal `file_request` and `board job` give over a dirty tree."""
    return ("%d tracked file(s) here differ from HEAD (%s), and the cluster "
            "runs what is pushed: board push first. Nothing was filed."
            % (len(paths), ", ".join(paths[:5])
               + (", ..." if len(paths) > 5 else "")))


def _slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-",
                                     str(text or "").lower())).strip("-")


def new_id(label, what, taken=(), now=None):
    """`<date>-<label>-<what>`, cut to fit and made unique with `-2`, `-3`.
    `label` may be empty."""
    day = time.strftime("%Y-%m-%d", time.localtime(float(now or time.time())))
    stem = "-".join(x for x in (day, _slug(label), _slug(what)) if x)[:72]
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
    """A request's path list as strings, `[]` for a non-list, so one malformed
    file cannot stop every check."""
    return [str(v) for v in value] if isinstance(value, list) else []


def relayed(root):
    """The requests folded with their reports, as registry records. `jobid`
    is `relay:<id>`, never a Slurm id; `slurm` is the report's."""
    got = reports(root)
    out = []
    for req in requests(root):
        rid = str(req.get("id") or "")
        rep = got.get(rid) or {}
        state = _AS_SLURM.get(str(rep.get("state") or "").lower(),
                              exports.REQUESTED)
        if req.get("kind") in ("turn", "colibri", "libr-ai"):
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
            "label": req.get("label") or rep.get("label"),
            "session": req.get("session") or rep.get("session"),
            "cmd": cmd[:CMD_CHARS], "state": state,
            "produces": _strings(req.get("produces")),
            "export": _strings(req.get("export")),
            # A malformed `filed` reads as 0 rather than stopping every reader.
            "submitted": _when(rep.get("submitted") or req.get("filed") or 0),
        }
        if req.get("fixes"):
            rec["fixes"] = req["fixes"]
        if isinstance(req.get("commit"), str):
            rec["commit"] = req["commit"]
        for key in ("exit", "ended", "note", "produced", "missing",
                    "exported", "export_refused", "relay", "error",
                    "problems", "changed", "ran_at", "output",
                    "output_total", "output_cut"):
            if rep.get(key) not in (None, "", []):
                rec[key] = rep[key]
        if rep.get("jobid"):
            rec["slurm"] = str(rep["jobid"])
        out.append(rec)
    return out


def view(root):
    """The registry, one view of three sources: `{key: record}`.

    `jobs.jsonl`, `relay/requests/` and `relay/reports/`. A request whose
    report names a job this machine registered is that job, once.
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
    """The first directory at or under `root` holding a `.git`, else "": no
    request is filed from a nested repository Atlas cannot see. Dot dirs,
    `live/`, `results/`, `node_modules/` and fenced names are not entered.
    """
    for here, dirs, files in os.walk(root):
        if ".git" in dirs or ".git" in files:
            return here
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("live", "results", "node_modules")
                   and not fenced.in_fence(d)]
    return ""


def file_request(root, req, push=True):
    """Write `relay/requests/<id>.json` and commit that one file, then push.
    `(path, ok, said)`: `file_requests` with one request."""
    paths, ok, said = file_requests(root, [req], push=push)
    return paths[0], ok, said


def file_requests(root, reqs, push=True):
    """Write and commit `relay/requests/<id>.json` for every request, alone in
    one commit, then push once. `(paths, ok, said)`.

    Each is stamped with `commit`, HEAD before their commit. All or nothing:
    refused while a tracked file under `root` differs from HEAD, or where a
    request exists already or may not be published.
    """
    reqs = list(reqs)
    targets = [os.path.join(requests_dir(root), r["id"] + ".json")
               for r in reqs]
    if not reqs:
        return targets, False, "no requests to file"
    if len(set(targets)) != len(targets):
        return targets, False, "two requests here share an id"
    for target in targets:
        if os.path.exists(target):
            return targets, False, "%s is already there" % target
    nested = nested_git(root)
    if nested:
        return targets, False, ("%s holds its own .git, and the relay reads "
                                "requests only from Atlas's tree" % nested)
    for req in reqs:
        leak = request_leak(root, req)
        if leak:
            return targets, False, "%s: %s" % (req["id"], leak) \
                if len(reqs) > 1 else leak
    changed = dirty(root)
    if changed:
        return targets, False, dirty_said(root, changed)
    commit = head(root)
    if not COMMIT_RE.match(commit):
        return targets, False, ("%s has no commit to pin the request to"
                                % root)
    os.makedirs(requests_dir(root), exist_ok=True)
    for req, target in zip(reqs, targets):
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(dict(req, commit=commit), fh, indent=2, sort_keys=True,
                      ensure_ascii=False)
            fh.write("\n")
    # Before the commit, so `hear` sees a report in the first pull after.
    _baseline(root)
    ids = [r["id"] for r in reqs]
    what = ("relay request %s" % ids[0] if len(ids) == 1 else
            "%d relay requests, %s" % (len(ids), ", ".join(ids) if len(ids) <= 5
                                       else "%s to %s" % (ids[0], ids[-1])))
    ok, said = commit_only(root, targets, what, push=push)
    return targets, ok, said


def request_leak(root, req):
    """"" or why this request may not be published: it is public once pushed,
    so absolute or home paths and anything the PHI policy matches are
    refused."""
    from . import leaving, subjects
    brief = req.get("brief") if isinstance(req, dict) else None
    if isinstance(brief, str) and _BRIEF_PATH_RE.search(brief):
        return ("the brief names an absolute or home path, and a request is "
                "public; say it relative to the workspace")
    try:
        top = _git_text(root, ["rev-parse", "--show-toplevel"])
        names_phi = leaving.policy(top or subjects.root())
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


def commit_only(root, targets, what, push=True):
    """Commit exactly `targets` (written or removed), then push. `(ok, said)`.
    The message is `<workspace>: <what>`. `push=False` does neither."""
    from . import gitops, subjects
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = ""
    if not top:
        return False, "%s is not in a git repository" % root
    # The directory resolved, not the file: a removed file has no realpath.
    rels = [os.path.relpath(
        os.path.join(os.path.realpath(os.path.dirname(t)),
                     os.path.basename(t)), os.path.realpath(top))
        for t in targets]
    where = subjects.identify(root)
    msg = "%s: %s" % (where, what) if where else what
    if push:
        ok, said = gitops.save(top, rels, msg)
    else:
        ok, said = gitops.commit(top, rels, msg)
    return ok, said[-800:]


# ---------------------------------------------------------------------------
# the Mac hears the cluster
# ---------------------------------------------------------------------------
# A report a pull brought to an end drops the same `[job]` (or `[repair]`)
# line a local ending does, through `cluster.wake`. `cluster.Ear` calls `hear`
# for every subject each pass. "Brought by a pull" is a diff of
# `relay/reports/` from the last heard commit to HEAD, whoever moved HEAD; a
# fresh clone records HEAD and hears nothing. Claimed once per (request,
# state).

ENDED_REPORTS = ("refused", "completed", "failed")
HEARD = "relay.heard"


def _named(rec, name):
    """Is this record's work named `name`, by its label or the thread an
    older request carried?"""
    return name in (rec.get("label"), rec.get("thread"))


def outstanding(root, tid=None):
    """The requests here the cluster has not ended, oldest first: all of
    them, or those `tid` names (`_named`)."""
    out = [r for r in relayed(root)
           if (tid is None or _named(r, tid))
           and not exports.finished(r)]
    out.sort(key=lambda r: float(r.get("submitted") or 0))
    return out


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
    """The newest ended report on work named `tid` (`_named`), as a registry
    record, or None."""
    got = reports(root)
    best, at = None, -1.0
    for rec in relayed(root):
        rep = got.get(rec["request"])
        if not _named(rec, tid) or not rep:
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
    """The commit last heard: `relay/state/reported/relay.heard`, taken over
    from an old place where it is still there."""
    return _adopt(root, HEARD)


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


def _rel_path(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _baseline(root):
    """Record HEAD as heard where nothing has been. The ledger is ignored,
    because an untracked file is a dirty tree to every commit guard."""
    if os.path.exists(_heard_path(root)):
        return
    head = _git_text(root, ["rev-parse", "HEAD"])
    if head and ignored(root, _rel_path(root, _heard_path(root))):
        _set_heard(root, head)


def _claim_once(root, key):
    """True for the one hearer that may drop this ending. Never taken over.
    A claim written in an old place before the move still counts."""
    target = _adopt(root, key)
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
        migrate_state(root)
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
        for rel in sorted(changed):
            rid = os.path.basename(rel)[:-len(".json")] if rel.endswith(
                ".json") else ""
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
                "thread": rep.get("thread"), "label": rep.get("label"),
                "session": rep.get("session"), "cmd": "",
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
