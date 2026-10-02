"""relay.py -- the cluster's half of the relay: one pass, every five minutes.

The Mac commits `relay/requests/<id>.json`; this pulls it, checks it again with
`jobs.check`, submits it through `jobs.submit_recipe`, polls it with
`jobs.poll`, and commits `relay/reports/<id>.json` and `exports/`. GitHub is
the only channel. HANDOFF.md's "The relay" is the contract.

ONE PASS, IN ORDER, UNDER ONE LOCK (`relay/.lock` at the repository root,
`flock`, so a second pass at once skips rather than waits):

1. Pull, fast-forward only. A tree with edits or unpushed commits outside the
   cluster's own paths is skipped, and `relay/state.json` says why. Then
   `pull_vendor` moves `vendor/colibri`.
2. Each request with no report is validated, then submitted or refused.
3. Unfinished jobs are polled with `jobs.poll`: `squeue` plus the wrapper's
   exit file, because `sacct` is refused here. An ended job's exports are
   copied and checked, and its report written.
4. One `turn` request at a time runs as a Slurm job of its own, a headless
   Claude turn in that workspace (`tutor relay --turn`).
5. Only `relay/reports/` and `exports/` are committed; the pass rebases onto
   origin and pushes. A rejected push is retried by the next pass. Never force.

A REPORT IS PUBLIC. It carries state, the Slurm id, times, the exit code, which
`produces` paths exist, which exports landed, the lines the job printed behind
`RELAY:`, and the exception type of a crash. Never a log tail. Every string in
it goes through `public` first: absolute paths become `<path>`, and the lab's
`names_phi` policy withholds what it matches.

Standard library only.
"""

import fcntl
import getpass
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

from . import atlas, jobs, leaving, paths
from .course import threads as course_threads

LOCK = os.path.join("relay", ".lock")
STATE = os.path.join("relay", "state.json")

# An export is at most this big.
CAP = 5 * 1024 * 1024
# What of a job's log reaches a report: `RELAY:` lines only, this many, this
# long, out of at most this much of the log's end.
MAX_LINES = 40
MAX_LINE = 200
READ_TAIL = 2 * 1024 * 1024
MAX_NOTE = 2000

# A cluster turn is a Slurm job of its own, so it outlives the pass.
TURN_PARTITION = "c3_short"
TURN_TIME = "01:00:00"
TURN_SECONDS = 50 * 60

# What the scrontab entry asks for. A pass is git and a few sbatch calls.
SCRON_TIME = "00:15:00"
SCRON_BEGIN = "# BEGIN tutor-relay"
SCRON_END = "# END tutor-relay"

GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false"}


# ---------------------------------------------------------------------------
# what is public
# ---------------------------------------------------------------------------
_PATH_RE = re.compile(r"(?<![\w.~:/-])(?:~/|/)(?:[^\s/:'\"]+/)*[^\s/:'\",;)]+")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def public(text, names_phi=None, limit=MAX_LINE):
    """`text` fit for a public report, or None where the PHI policy matches it.

    Control characters go, an absolute or home path becomes `<path>` (a path
    is where lab storage gets named), and it is cut to `limit`.
    """
    s = _CTRL_RE.sub("", str(text or "")).strip()
    s = _PATH_RE.sub("<path>", s)
    if names_phi is not None:
        try:
            if names_phi(s):
                return None
        except Exception:                                    # noqa: BLE001
            return None
    if len(s) > limit:
        s = s[:limit - 1].rstrip() + "…"
    return s


def relay_lines(text, names_phi=None):
    """The lines a job printed behind `RELAY:`, made public. The last
    `MAX_LINES` of them, prefix dropped; nothing else of the log."""
    out = []
    for line in (text or "").splitlines():
        if not line.startswith("RELAY:"):
            continue
        said = public(line[len("RELAY:"):], names_phi)
        if said:
            out.append(said)
    return out[-MAX_LINES:]


_EXC_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
                     r"(?::|$)")


def crash_type(text):
    """The exception type of the last Python traceback in `text`, or "".
    The type only: its message can print anything."""
    lines = (text or "").splitlines()
    starts = [i for i, l in enumerate(lines)
              if l.startswith("Traceback (most recent call last)")]
    if not starts:
        return ""
    for line in lines[starts[-1] + 1:]:
        if not line or line[0].isspace():
            continue
        m = _EXC_RE.match(line.strip())
        return m.group(1)[:80] if m else ""
    return ""


def _tail(path):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - READ_TAIL))
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _logs(rec):
    """`(stdout text, stderr text)` of a job, globbing an array's files."""
    import glob

    def read(p):
        if not p:
            return ""
        found = glob.glob(p) if "*" in p else [p]
        return "\n".join(_tail(f) for f in sorted(found))
    out = read(rec.get("log_path"))
    err = read(rec.get("err_path")) if rec.get("err_path") != rec.get(
        "log_path") else ""
    return out, err


# ---------------------------------------------------------------------------
# git, in the cluster checkout
# ---------------------------------------------------------------------------
def _git(base, *args, timeout=120, raw=False):
    try:
        p = subprocess.run(["git"] + list(args), cwd=base,
                           env=dict(os.environ, **GIT_ENV),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL if raw else subprocess.STDOUT,
                           universal_newlines=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout or "") if raw else (p.stdout or "").strip()


def _rel(base, path):
    return os.path.relpath(os.path.realpath(path), os.path.realpath(base))


def spaces(base):
    """`[(workspace root, its path relative to the repository)]`."""
    return [(w["root"], _rel(base, w["root"])) for w in atlas.workspaces(base)]


def owned(base, rel, where=None):
    """Is this repository-relative path one the cluster writes? A workspace's
    `relay/reports/` and `exports/`, and the `vendor/colibri` pointer the
    pass moves."""
    if rel == "vendor/colibri":
        return True
    for _, ws in where if where is not None else spaces(base):
        for mine in ("relay/reports/", "exports/"):
            if rel.startswith(ws + "/" + mine):
                return True
    return False


def tolerated(base, rel, where=None):
    """A tracked file the pass may find changed and leave so: a workspace's job
    registry, which only a machine with Slurm appends to (the poll, and
    `board job` here). It is not the relay's to commit."""
    for root, ws in where if where is not None else spaces(base):
        if rel == ws + "/" + _rel(root, jobs.registry(root)):
            return True
    return False


def _dirty(base):
    """Repository-relative paths with tracked changes, staged or not."""
    code, out = _git(base, "status", "--porcelain", "-z", "--untracked-files=no",
                     "--ignore-submodules=dirty", raw=True)
    if code != 0:
        return None
    got, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1                       # the original path follows a rename
        got.append(entry[3:])
    return got


def upstream(base):
    """`(remote, branch, "remote/branch")`, or None without one."""
    code, branch = _git(base, "symbolic-ref", "--quiet", "--short", "HEAD")
    if code != 0 or not branch:
        return None
    code, remote = _git(base, "config", "branch.%s.remote" % branch)
    code2, merge = _git(base, "config", "branch.%s.merge" % branch)
    if code or code2 or not remote or not merge:
        return None
    theirs = merge.split("refs/heads/", 1)[-1]
    return remote, theirs, "%s/%s" % (remote, theirs)


def _count(base, spec):
    code, out = _git(base, "rev-list", "--count", spec)
    return int(out) if code == 0 and out.isdigit() else 0


def sync(base, where, pull_vendor=None):
    """Step 1. `(skip reason or "", error or "")`."""
    from . import worktree
    busy = worktree.busy_reason(base)
    if busy:
        return "%s in the repository" % busy, ""
    up = upstream(base)
    if not up:
        return "HEAD is detached or its branch has no upstream", ""
    remote, theirs, ref = up
    dirty = _dirty(base)
    if dirty is None:
        return "git status failed", ""
    stray = [p for p in dirty if not owned(base, p, where)
             and not tolerated(base, p, where)]
    if stray:
        return ("the tree has edits outside the cluster's paths: %s"
                % ", ".join(stray[:5]) + (" and %d more" % (len(stray) - 5)
                                          if len(stray) > 5 else "")), ""
    code, out = _git(base, "fetch", "--quiet", remote, theirs)
    error = "" if code == 0 else "fetch from %s failed: %s" % (
        remote, out.splitlines()[-1] if out else "no output")
    ahead = _count(base, "%s..HEAD" % ref)
    if ahead:
        code, out = _git(base, "diff", "--name-only", "%s...HEAD" % ref)
        theirs_not = [p for p in out.splitlines() if p
                      and not owned(base, p, where)]
        if code != 0 or theirs_not:
            return ("the branch has commits origin lacks, outside the "
                    "cluster's paths: %s" % ", ".join(theirs_not[:5])), error
    if not error and _count(base, "HEAD..%s" % ref):
        if ahead:
            code, out = _git(base, "rebase", "--autostash", "--quiet", ref)
            if code != 0:
                _git(base, "rebase", "--abort")
                return "", "rebase onto %s failed: %s" % (
                    ref, out.splitlines()[-1] if out else "")
        else:
            code, out = _git(base, "merge", "--ff-only", "--quiet", ref)
            if code != 0:
                return "", "fast-forward to %s failed: %s" % (
                    ref, out.splitlines()[-1] if out else "")
    if pull_vendor is not None:
        try:
            pull_vendor(quiet=True)
        except Exception as exc:                             # noqa: BLE001
            error = error or "pull_vendor: %s" % exc
    return "", error


def publish(base, where, message, push=True):
    """Step 5. Commit the cluster's paths, rebase, push. `(sha, error)`."""
    mine = []
    for root, ws in where:
        for sub in ("relay/reports", "exports"):
            if os.path.isdir(os.path.join(root, sub)):
                mine.append(ws + "/" + sub)
    if mine:
        _git(base, "add", "-A", "--", *mine)
        code, staged = _git(base, "diff", "--cached", "--name-only", "--", *mine)
        if code == 0 and staged:
            code, out = _git(base, "commit", "--quiet", "-m", message, "--",
                             *mine)
            if code != 0:
                return "", "commit failed: %s" % (out.splitlines() or [""])[-1]
    up = upstream(base)
    if not up or not push:
        return "", ""
    remote, theirs, ref = up
    if not _count(base, "%s..HEAD" % ref):
        return "", ""
    code, out = _git(base, "fetch", "--quiet", remote, theirs)
    if code == 0 and _count(base, "HEAD..%s" % ref):
        code, out = _git(base, "rebase", "--autostash", "--quiet", ref)
        if code != 0:
            _git(base, "rebase", "--abort")
            return "", "rebase before the push failed: %s" % (
                out.splitlines() or [""])[-1]
    code, out = _git(base, "push", "--quiet", remote, "HEAD:%s" % theirs,
                     timeout=180)
    if code != 0:
        return "", "push rejected, retried next pass: %s" % (
            out.splitlines() or [""])[-1]
    return _git(base, "rev-parse", "HEAD")[1], ""


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------
def write_report(ws, rid, rep):
    target = os.path.join(jobs.reports_dir(ws), rid + ".json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, target)
    course_threads.forget(ws)
    return target


def _base_report(req, state, now):
    return {"id": req.get("id"), "kind": req.get("kind"),
            "thread": req.get("thread"), "state": state,
            "updated": round(float(now), 3)}


def refuse(ws, req, problems, now, names_phi=None):
    rep = _base_report(req, "refused", now)
    rep["problems"] = [public(p, names_phi, 400) or "(withheld by the PHI "
                       "policy)" for p in problems]
    return write_report(ws, str(req.get("id")), rep)


def export(ws, rec, clean, names_phi=None):
    """Copy a finished job's exports into `exports/`. `(landed, refused)`.

    Each path is checked again here, in code, whatever the request said: under
    `results/`, an allowed extension, marked aggregate on the thread now, a
    regular file of at most 5 MB, a target git would track, and nothing the
    PHI policy matches in its path or, for text, its content.
    """
    landed, refused = [], []
    one = course_threads.thread(clean, rec.get("thread")) if clean else None
    for rel in rec.get("export") or []:
        rel = course_threads._rel(rel)

        def no(why):
            refused.append({"path": rel, "why": why})
        if not rel or not rel.startswith("results/"):
            no("not a path under results/")
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in course_threads.EXPORT_EXTS:
            no("not one of %s" % ", ".join(course_threads.EXPORT_EXTS))
            continue
        if not one or not course_threads.exportable(one, rel):
            no("not marked aggregate on the thread")
            continue
        if names_phi is not None and names_phi(rel):
            no("the PHI policy matches its path")
            continue
        src = os.path.join(ws, rel)
        if os.path.islink(src) or not os.path.isfile(src):
            no("not there as a regular file")
            continue
        size = os.path.getsize(src)
        if size > CAP:
            no("%.1f MB, over the %d MB cap" % (size / 1048576.0,
                                                CAP // 1048576))
            continue
        if ext in (".csv", ".json", ".svg") and names_phi is not None:
            with open(src, "r", encoding="utf-8", errors="replace") as fh:
                if names_phi(fh.read()):
                    no("the PHI policy matches its content")
                    continue
        dst_rel = "exports/" + rel
        if jobs.ignored(ws, dst_rel):
            no("git would ignore %s; the workspace's .gitignore needs "
               "`!exports/**`" % dst_rel)
            continue
        dst = os.path.join(ws, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst + ".tmp")
        os.replace(dst + ".tmp", dst)
        landed.append(rel)
    return landed, refused


def finish(ws, rec, req, clean, now, names_phi=None):
    """The report for a job that has ended."""
    state = "completed" if rec.get("state") == "COMPLETED" else "failed"
    rep = _base_report(req, state, now)
    rep.update({"jobid": str(rec.get("jobid")),
                "submitted": rec.get("submitted"),
                "ended": rec.get("ended") or "",
                "exit": rec.get("exit") or ""})
    produces = list(req.get("produces") or [])
    rep["produced"] = [p for p in produces if course_threads.here(ws, p)]
    rep["missing"] = [p for p in produces if p not in rep["produced"]]
    out, err = _logs(rec)
    rep["relay"] = relay_lines(out + "\n" + err, names_phi)
    crashed = crash_type(err) or crash_type(out)
    if crashed:
        rep["error"] = crashed
    if req.get("kind") == "turn":
        rep["note"] = turn_note(ws, req, rec, names_phi)
    else:
        if state == "completed":
            landed, refused = export(ws, dict(rec, export=req.get("export")),
                                     clean, names_phi)
        else:
            landed = []
            refused = [{"path": p, "why": "the job did not complete"}
                       for p in req.get("export") or []]
        rep["exported"] = landed
        if refused:
            rep["export_refused"] = refused
        rep["note"] = recipe_note(rec, rep)
    return write_report(ws, str(req["id"]), rep)


def recipe_note(rec, rep):
    """One public sentence, written by code, saying how the job ended."""
    state = rec.get("state")
    if state == "DIED":
        head = ("It left the queue without writing its exit code: a time "
                "limit, a node failure or a cancel.")
    elif state == "COMPLETED":
        head = "It completed, exit 0."
    else:
        head = "It failed, exit %s." % (str(rec.get("exit") or "?")
                                        .split(":")[0])
    bits = [head]
    if rep.get("produced") or rep.get("missing"):
        bits.append("%d of %d outputs present." % (
            len(rep["produced"]), len(rep["produced"]) + len(rep["missing"])))
    if rep.get("exported") or rep.get("export_refused"):
        bits.append("%d exported, %d refused." % (
            len(rep.get("exported") or []), len(rep.get("export_refused") or [])))
    if state != "COMPLETED":
        bits.append("The log stays on the cluster; a `turn` request can "
                    "read it.")
    return " ".join(bits)


# ---------------------------------------------------------------------------
# turns
# ---------------------------------------------------------------------------
def note_path(ws, rid):
    return os.path.join(jobs.state_dir(ws), rid + ".note")


def turn_note(ws, req, rec, names_phi=None):
    """The turn's note, made public, or a sentence saying why there is none."""
    try:
        with open(note_path(ws, str(req["id"])), "r", encoding="utf-8",
                  errors="replace") as fh:
            text = fh.read()
    except OSError:
        text = ""
    if not text.strip():
        return ("The turn left no note (%s, exit %s)."
                % (str(rec.get("state") or "").lower() or "ended",
                   str(rec.get("exit") or "?").split(":")[0]))
    said = public(text, names_phi, MAX_NOTE)
    if said is None:
        return ("The turn's note was withheld: the PHI policy matched it. It "
                "stays on the cluster at relay/state/%s.note." % req["id"])
    return said


def turn_prompt(ws, req, title=""):
    return (
        "You are a headless turn on the cluster, started by the relay. Nobody "
        "is at a terminal, and nobody will read stdout except to keep your "
        "last message.\n\n"
        "Workspace: %(ws)s. Thread: %(thread)s%(title)s. The owner asked, "
        "from the Mac:\n\n%(brief)s\n\n"
        "Work beside the data under this workspace's AI_INSTRUCTIONS.md and "
        "the PHI rules in the repository's root README.md. Long work goes "
        "through `board job`, never a bare sbatch. Do not commit, push or "
        "edit tracked files.\n\n"
        "YOUR LAST MESSAGE IS THE REPORT'S NOTE, AND IT IS PUBLISHED in a "
        "public repository. Aggregate numbers only: no patient-level values, "
        "no rows, no patient or participant identifiers, no paths to lab "
        "storage, no log lines. Under %(cap)d characters. Say what you found "
        "and what the owner should do next."
        % {"ws": os.path.basename(ws), "thread": req.get("thread"),
           "title": " (%s)" % title if title else "",
           "brief": req.get("brief") or "", "cap": MAX_NOTE - 200})


def turn_header(ws, rid):
    return ["#SBATCH --partition=%s" % TURN_PARTITION,
            "#SBATCH --time=%s" % TURN_TIME,
            "#SBATCH --cpus-per-task=2",
            "#SBATCH --mem=8G",
            "#SBATCH --output=%s" % os.path.join(jobs.state_dir(ws),
                                                 rid + ".log")]


def tutor_cmd(ws, rid):
    return [sys.executable, os.path.join(paths.TOOL, "bin", "tutor"),
            "relay", "--turn", ws, rid]


def run_turn(ws, rid, run=subprocess.run):
    """Inside the turn's job: one headless Claude turn, its last message
    written to `relay/state/<id>.note`. The exit code is the turn's."""
    from . import seeing
    req = next((r for r in jobs.requests(ws) if r.get("id") == rid), None)
    if not req or req.get("kind") != "turn":
        print("no turn request %s in %s" % (rid, ws), file=sys.stderr)
        return 2
    clean, _ = course_threads.read(ws)
    one = course_threads.thread(clean, req.get("thread")) if clean else None
    prompt = turn_prompt(ws, req, (one or {}).get("title", ""))
    # Claude, always: a routing variable inherited from a DeepSeek sitting
    # would make this some other model beside the data.
    env = dict((k, v) for k, v in os.environ.items()
               if k not in seeing.ROUTING)
    try:
        p = run(["claude", "-p", prompt, "--output-format", "json"], cwd=ws,
                env=env, stdout=subprocess.PIPE, stderr=None,
                stdin=subprocess.DEVNULL, universal_newlines=True,
                timeout=TURN_SECONDS)
    except subprocess.TimeoutExpired:
        print("the turn ran past %d minutes" % (TURN_SECONDS // 60),
              file=sys.stderr)
        return 124
    except OSError as exc:
        print("claude did not start: %s" % exc, file=sys.stderr)
        return 127
    text = p.stdout or ""
    try:
        text = str((json.loads(text) or {}).get("result") or "")
    except (ValueError, AttributeError):
        pass
    os.makedirs(jobs.state_dir(ws), exist_ok=True)
    with open(note_path(ws, rid), "w", encoding="utf-8") as fh:
        fh.write(text.strip() + "\n")
    return p.returncode


def _turn_busy(where):
    for root, _ in where:
        for rec in jobs.records(root, jobs.relay_registry(root)).values():
            if rec.get("kind") == "turn" and not course_threads.finished(rec):
                return True
    return False


# ---------------------------------------------------------------------------
# the pass
# ---------------------------------------------------------------------------
def state_path(base):
    return os.path.join(base, STATE)


def read_state(base):
    try:
        with open(state_path(base), "r", encoding="utf-8") as fh:
            got = json.load(fh)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(base, st):
    path = state_path(base)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)


def sbatch_env():
    """The environment a submission runs in: this one, less the Slurm
    variables a pass inherits from its own scrontab job."""
    return dict((k, v) for k, v in os.environ.items()
                if not k.startswith(("SLURM_", "SBATCH_", "SRUN_")))


def run_pass(base=None, run=subprocess.run, now=None, pull_vendor=None,
             push=True):
    """One pass. Returns a summary dict; `relay/state.json` records it.

    `run` is how Slurm is asked (sbatch, scontrol, squeue), so a test can
    answer from a table; git is always the real one.
    """
    base = os.path.realpath(base or atlas.root())
    lock = os.path.join(base, LOCK)
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    fh = open(lock, "a+")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return {"skipped": "another pass holds the lock"}
        return _locked_pass(base, run, now, pull_vendor, push)
    finally:
        fh.close()


def _locked_pass(base, run, now, pull_vendor, push):
    t0 = float(now or time.time())
    st = read_state(base)
    summary = {"submitted": [], "refused": [], "ended": [], "turn": "",
               "skipped": "", "error": ""}
    errors = []
    try:
        where = spaces(base)
        skip, err = sync(base, where, pull_vendor)
        if err:
            errors.append(err)
        if skip:
            summary["skipped"] = skip
        else:
            atlas.forget()
            where = spaces(base)
            _work(base, where, run, t0, summary)
            ids = summary["submitted"] + summary["refused"] + summary["ended"]
            msg = ("relay: %d report(s) -- %s" % (len(ids), ", ".join(ids[:6]))
                   if ids else "relay: reports")
            sha, err = publish(base, where, msg[:200], push=push)
            if err:
                errors.append(err)
            if sha:
                st["last_pushed"] = sha
                st["pushed_at"] = time.time()
    except Exception as exc:                                 # noqa: BLE001
        errors.append("%s: %s" % (type(exc).__name__, exc))
    summary["error"] = "; ".join(errors)
    st.update({"last_pass": t0, "host": socket.gethostname(),
               "skipped": summary["skipped"],
               "push_pending": any("push rejected" in e for e in errors),
               "counts": dict((k, len(summary[k])) for k in
                              ("submitted", "refused", "ended")),
               "turn": summary["turn"]})
    if errors:
        st["last_error"] = summary["error"]
        st["error_at"] = t0
    _save_state(base, st)
    return summary


def _work(base, where, run, now, summary):
    names_phi = leaving.policy(base)
    env = sbatch_env()
    pending_turns = []
    for ws, _ in where:
        reqs = jobs.requests(ws)
        if not reqs:
            continue
        reps = jobs.reports(ws)
        by_id = dict((str(r.get("id")), r) for r in reqs)
        # --- 2. requests with no report ---------------------------------
        for req in sorted(reqs, key=lambda r: (r.get("filed") or 0,
                                               str(r.get("id")))):
            rid = str(req.get("id"))
            if rid in reps:
                continue
            ok, problems = jobs.check(ws, req, mine=True)
            if problems:
                refuse(ws, req, problems, now, names_phi)
                summary["refused"].append(rid)
                continue
            if ok["kind"] == "turn":
                pending_turns.append((ws, ok))
                continue
            rec, why = jobs.submit_recipe(
                ws, ok["thread"], ok["recipe"], env=ok["env"],
                produces=ok["produces"], export=ok["export"], key=rid,
                run=run, now=now, sbatch_env=env,
                path=jobs.relay_registry(ws),
                extra={"request": rid, "kind": "recipe"})
            if not rec:
                refuse(ws, req, [why], now, names_phi)
                summary["refused"].append(rid)
                continue
            rep = _base_report(req, "submitted", now)
            rep.update({"jobid": rec["jobid"], "submitted": rec["submitted"]})
            write_report(ws, rid, rep)
            summary["submitted"].append(rid)
        # --- 3. poll ----------------------------------------------------
        _poll(ws, by_id, run, now, summary, names_phi)
    for ws, _ in where:
        if not jobs.requests(ws):
            # A workspace with no requests can still have jobs `board job`
            # submitted here directly; their endings wake its inbox.
            jobs.report(ws, run=run, now=now)
    # --- 4. one turn at a time ---------------------------------------------
    if pending_turns and not _turn_busy(where):
        ws, req = sorted(pending_turns, key=lambda p: (p[1].get("filed") or 0,
                                                      p[1]["id"]))[0]
        rid = req["id"]
        if names_phi is None:
            refuse(ws, req, ["the PHI guard's policy (ai-config/policy/phi.py) "
                             "is not installed in this checkout, so no turn "
                             "runs here"], now)
            summary["refused"].append(rid)
            return
        rec, why = jobs.submit_script(
            ws, req["thread"], turn_header(ws, rid), tutor_cmd(ws, rid), rid,
            "relay-turn", run=run, now=now, sbatch_env=env,
            path=jobs.relay_registry(ws),
            extra={"request": rid, "kind": "turn"})
        if not rec:
            refuse(ws, req, [why], now, names_phi)
            summary["refused"].append(rid)
            return
        rep = _base_report(req, "submitted", now)
        rep.update({"jobid": rec["jobid"], "submitted": rec["submitted"]})
        write_report(ws, rid, rep)
        summary["turn"] = rid
        summary["submitted"].append(rid)


def _poll(ws, by_id, run, now, summary, names_phi):
    jobs.report(ws, run=run, now=now)
    path, claims = jobs.relay_registry(ws), jobs.relay_claims(ws)
    ended = jobs.poll(ws, run=run, now=now, path=path, claims=claims)
    reps = jobs.reports(ws)
    for rec in jobs.records(ws, path).values():
        rid = rec.get("request")
        rep = reps.get(rid) or {}
        if (not course_threads.finished(rec) and rec.get("state") == "RUNNING"
                and rep.get("state") == "submitted"):
            rep = dict(rep, state="running", updated=round(now, 3),
                       started=rec.get("seen") or now)
            write_report(ws, rid, rep)
    clean, _ = course_threads.read(ws)
    for rec in ended:
        rid = rec.get("request")
        req = by_id.get(rid)
        try:
            if not req:
                raise KeyError("request %s is gone" % rid)
            finish(ws, rec, req, clean, now, names_phi)
        except Exception:                                    # noqa: BLE001
            # No report, so no claim: the next pass offers it again.
            jobs._unclaim(ws, rec["jobid"], claims)
            continue
        jobs.append(ws, {"jobid": rec["jobid"], "request": rid,
                         "reported": float(now)}, path=path)
        summary["ended"].append(rid)


# ---------------------------------------------------------------------------
# status, and where
# ---------------------------------------------------------------------------
def _ago(t, now=None):
    if not t:
        return "never"
    d = max(0, int(float(now or time.time()) - float(t)))
    if d < 120:
        return "%d s ago" % d
    if d < 7200:
        return "%d min ago" % (d // 60)
    return "%.1f h ago" % (d / 3600.0)


def where_line(base=None, now=None):
    """One line for `tutor where`, or "" where the relay never ran."""
    st = read_state(os.path.realpath(base or atlas.root()))
    if not st.get("last_pass"):
        return ""
    said = "relay: last pass %s on %s" % (_ago(st["last_pass"], now),
                                          st.get("host") or "?")
    if st.get("skipped"):
        said += ", SKIPPED: %s" % st["skipped"]
    if st.get("last_pushed"):
        said += "; last pushed %s" % st["last_pushed"][:8]
    if st.get("push_pending"):
        said += "; a push is pending"
    if st.get("last_error"):
        said += "; last error %s: %s" % (_ago(st.get("error_at"), now),
                                         st["last_error"][:160])
    return said


def status(base=None, now=None):
    """What `tutor relay --status` prints: the last pass, and every
    workspace's requests by state."""
    base = os.path.realpath(base or atlas.root())
    lines = [where_line(base, now) or "relay: no pass has run here"]
    for ws, rel in spaces(base):
        reqs = jobs.requests(ws)
        if not reqs:
            continue
        reps = jobs.reports(ws)
        counts = {}
        for r in reqs:
            s = (reps.get(str(r.get("id"))) or {}).get("state") or "requested"
            counts[s] = counts.get(s, 0) + 1
        out = [j for j in jobs.records(ws, jobs.relay_registry(ws)).values()
               if not course_threads.finished(j)]
        lines.append("  %-28s %s%s" % (rel, ", ".join(
            "%d %s" % (counts[k], k) for k in sorted(counts)),
            "; jobs out: %s" % ", ".join(
                "%s (%s)" % (j["jobid"], j.get("state") or "PENDING")
                for j in out) if out else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the scrontab entry
# ---------------------------------------------------------------------------
def scrontab_block(python=None, tutor=None, log=None):
    """The entry, between markers so `install` can replace it."""
    python = python or sys.executable
    tutor = tutor or os.path.join(paths.TOOL, "bin", "tutor")
    log = log or os.path.join(paths.STATE_DIR, "relay-scron.log")
    return "\n".join([
        SCRON_BEGIN + " (written by `tutor relay --install`)",
        "#SCRON --partition=%s" % TURN_PARTITION,
        "#SCRON --time=%s" % SCRON_TIME,
        "#SCRON --cpus-per-task=1",
        "#SCRON --mem=2G",
        "#SCRON --job-name=tutor-relay",
        "#SCRON --output=%s" % log,
        "#SCRON --open-mode=append",
        "*/5 * * * * %s %s relay --once --quiet" % (python, tutor),
        SCRON_END,
    ]) + "\n"


def merged_crontab(old, block):
    """`old` with the relay's block replaced, or appended. Pure."""
    lines, out, inside = (old or "").splitlines(), [], False
    for line in lines:
        if line.startswith(SCRON_BEGIN):
            inside = True
            continue
        if inside:
            if line.startswith(SCRON_END):
                inside = False
            continue
        out.append(line)
    text = "\n".join(out).rstrip("\n")
    return (text + "\n" if text else "") + block


def install(run=subprocess.run):
    """Write the entry into this user's scrontab. `(ok, said)`."""
    p = run(["scrontab", "-l"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    old = p.stdout if p.returncode == 0 else ""
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    new = merged_crontab(old, scrontab_block())
    tmp = os.path.join(paths.STATE_DIR, "scrontab.%s" % getpass.getuser())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    q = run(["scrontab", tmp], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
    return q.returncode == 0, (q.stdout or "").strip()
