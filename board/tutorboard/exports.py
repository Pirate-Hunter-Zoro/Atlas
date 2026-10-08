"""exports.py -- what a finished cluster job may publish, and the job states.

THE OWNER APPROVES AN EXPORT IN THE SUBJECT'S tutorboard.json, `relay.exports`:

    {"relay": {"exports": [{"glob": "results/figs/*.png"},
                           {"glob": "results/summary.csv", "aggregate": true}]}}

Each entry's `glob` is a subject-relative pattern under `results/`, matched
with `fnmatch` (so `*` also crosses `/`). A png, pdf or svg is approved by any
matching entry. A csv or json can hold rows, so it is approved only by a
matching entry carrying `"aggregate": true`, the owner's word that it holds
none. The relay's other checks (the 5 MB cap, the extension list, the PHI
policy on path and content) stay in `relay.export`, whatever this says.

The list counts only where it is committed: `approvals` reads tutorboard.json
at HEAD and on disk and keeps the entries both hold. A turn cannot commit a
change to `relay.exports` (the pre-commit audit), so an approval is the
owner's, and a revocation on disk takes effect before it is committed.

The job-state words and the registry fold live here too, so the relay path
reads them without the thread file.

Runs on the cluster's python3, which may be 3.7. Standard library only.
"""

import fnmatch
import json
import os
import subprocess

CONFIG = "tutorboard.json"

# What may be copied from `results/` into tracked `exports/`: aggregate
# artifacts a reader can open, never a database or a pickle.
EXPORT_EXTS = (".png", ".pdf", ".svg", ".csv", ".json")
# Of those, the ones that can carry rows: approved only with `aggregate`.
ROW_EXTS = (".csv", ".json")

# What sacct calls a job that has stopped. Anything else -- PENDING, RUNNING,
# no state at all -- is a job still out. LOST is the board's own word, for a job
# Slurm has no record of at all. REFUSED is the relay's, for a request the
# cluster would not run. DIED and ENDED are `jobs.ending`'s, for a job that
# left squeue without its exit file, wrapped and not.
TERMINAL = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
            "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "LOST",
            "REFUSED", "DIED", "ENDED")

# A relay request the cluster has not reported on yet. Not terminal.
REQUESTED = "REQUESTED"


def rel(value):
    """A path inside the subject, normalized, or None."""
    out = str(value or "").strip().replace("\\", "/").lstrip("/")
    while out.startswith("./"):
        out = out[2:]
    out = out.rstrip("/")
    if not out or out == "." or ".." in out.split("/") or out.startswith("~"):
        return None
    return out


# ---------------------------------------------------------------------------
# approval: tutorboard.json `relay.exports`
# ---------------------------------------------------------------------------
def entries(value):
    """`(entries, problems)` for a `relay.exports` value. Pure.

    An entry is `{"glob": <pattern under results/>}`, with an optional
    boolean `aggregate`. A malformed entry approves nothing and is named in
    `problems`."""
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["relay.exports must be a list of {\"glob\": ...} entries"]
    out, problems = [], []
    for e in value:
        if not isinstance(e, dict):
            problems.append("relay.exports: %r is not an object" % (e,))
            continue
        extra = sorted(k for k in e if k not in ("glob", "aggregate"))
        if extra:
            problems.append("relay.exports: an entry has no %s"
                            % ", ".join("`%s`" % k for k in extra))
            continue
        pattern = e.get("glob")
        clean = rel(pattern) if isinstance(pattern, str) else None
        if clean is None or clean != pattern or not clean.startswith(
                "results/"):
            problems.append("relay.exports: %r must be a pattern under "
                            "results/" % (pattern,))
            continue
        agg = e.get("aggregate", False)
        if not isinstance(agg, bool):
            problems.append("relay.exports: %s: `aggregate` must be true or "
                            "false" % pattern)
            continue
        one = {"glob": pattern}
        if agg:
            one["aggregate"] = True
        if one not in out:
            out.append(one)
    return out, problems


def _relay_exports(doc):
    relay = doc.get("relay") if isinstance(doc, dict) else None
    return relay.get("exports") if isinstance(relay, dict) else None


def _on_disk(root):
    try:
        with open(os.path.join(root, CONFIG), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _at_head(root):
    try:
        p = subprocess.run(["git", "show", "HEAD:./" + CONFIG], cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def approvals(root):
    """The subject's approved export entries: those its tutorboard.json holds
    both at HEAD and on disk. `[]` outside git or with no file."""
    disk, _ = entries(_relay_exports(_on_disk(root)))
    head, _ = entries(_relay_exports(_at_head(root)))
    return [e for e in head if e in disk]


def approved(allowed, path):
    """`(ok, why)`: does this approval list let `path` be published? Pure.

    `why` is "" when it does, else one sentence naming tutorboard.json."""
    path = rel(path)
    if path is None or not path.startswith("results/"):
        return False, "export %r must be a path under results/" % (path,)
    ext = os.path.splitext(path)[1].lower()
    if ext not in EXPORT_EXTS:
        return False, "export %s is not one of %s" % (
            path, ", ".join(EXPORT_EXTS))
    hits = [e for e in allowed or ()
            if isinstance(e, dict) and isinstance(e.get("glob"), str)
            and fnmatch.fnmatchcase(path, e["glob"])]
    if not hits:
        return False, ("export %s matches no relay.exports glob in the "
                       "subject's committed tutorboard.json; the owner adds "
                       "one" % path)
    if ext in ROW_EXTS and not any(e.get("aggregate") is True for e in hits):
        return False, ("export %s is a %s, which can hold rows: its "
                       "relay.exports entry in tutorboard.json needs "
                       "\"aggregate\": true, the owner's word that it holds "
                       "none" % (path, ext[1:]))
    return True, ""


def exportable(t, path):
    """The thread file's rule, kept for `course/threads.py` and for proving
    the migration (`scripts/migrate-exports.py`): may `path` be published off
    thread `t`? Only where the thread marks that exact path aggregate."""
    return any(e["path"] == path and e["aggregate"]
               for e in (t or {}).get("exports") or [])


# ---------------------------------------------------------------------------
# job states, and the registry fold
# ---------------------------------------------------------------------------
def merged(jobs):
    """`{jobid: record}`, each job's records folded in file order.

    A later record for the same job id overrides an earlier one, so the poll
    that sees a job end appends one line carrying `state` rather than rewriting
    the file.
    """
    last = {}
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        key = str(j.get("jobid") or "")
        if not key:
            continue
        rec = dict(last.get(key) or {})
        rec.update(j)
        last[key] = rec
    return last


def finished(j):
    """Has sacct (or the board) called this job finished?"""
    state = str(j.get("state") or "").split()
    return bool(state) and state[0].upper().rstrip("+") in TERMINAL


def jobs_of(root):
    """The job registry as records, from wherever `jobs.registry` keeps it.
    Empty if none."""
    from . import jobs as job_registry
    out = []
    try:
        with open(job_registry.registry(root), "r", encoding="utf-8") as fh:
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
