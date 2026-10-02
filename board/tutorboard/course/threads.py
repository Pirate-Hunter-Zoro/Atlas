"""threads.py -- a project's spine: deliverables, and the threads under them.

A course has a spine because a book gives it one. A project has none, so the
board drew one out of the directory tree, and nobody thinks about their
research as `scripts-pipeline-predictions`. This file is the spine a project
writes for itself:

    deliverable   something handed to another person -- a paper, a deck
    thread        one question the deliverable needs, with its code, its
                  outputs, where it is written up, its tasks and its decisions

It lives at `threads.json` in the workspace root, tracked. Not in `live/`:
several workspaces ignore `live/` wholesale, and git cannot let a file back out
of an ignored directory.

THREE THINGS HERE, AND ONLY THREE:

    validate   pure: does the document say something a thread file can mean
    resolve    the file checked against the tree, every time it is read
    stage      pure: a thread's status, from the file, git, the job registry
               and which paths exist

Status is never typed, apart from `closed`. Everything else about where a
thread stands is a fact on disk, and a fact cannot go stale.

Standard library only, like everything else.
"""

import json
import os
import re
import subprocess
import time

from .. import paths as toolpaths

VERSION = 1
NAME = "threads.json"

# An id is what everything keys off -- a sitting's `thread`, a job's `thread`,
# the browser's memory of which box it was on -- so it is narrow and stable.
ID_RE = re.compile(r"^[a-z0-9-]{1,40}$")

# A thread's `doc` is a document id, the one `reading.ident` gives -- never a
# path. A deliverable's `doc` IS a path: it is the file being handed over, and
# it may not exist yet.
DOC_RE = re.compile(r"^[a-z0-9-]{1,40}$")

MAX_TITLE = 90
MAX_QUESTION = 300
MAX_TEXT = 240
MAX_PATHS = 40
MAX_BLOCKED = 8
MAX_THREADS = 44
MAX_TASKS = 40

# What sacct calls a job that has stopped. Anything else -- PENDING, RUNNING,
# no state at all -- is a job still out. LOST is the board's own word, for a job
# Slurm has no record of at all: left out, it would hold its thread at
# `running` for ever.
# REFUSED is the relay's, for a request the cluster would not run. DIED and
# ENDED are `jobs.ending`'s, for a job that left squeue without its exit file,
# wrapped and not.
TERMINAL = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
            "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "LOST",
            "REFUSED", "DIED", "ENDED")

# A relay request the cluster has not reported on yet. Not terminal: the
# thread waits on it, and says `requested` rather than `running`.
REQUESTED = "REQUESTED"

# The six stages, and the first true one wins.
STAGES = ("done", "running", "requested", "written", "result", "open")

# What may be copied from `results/` into tracked `exports/`: aggregate
# artifacts a reader can open, never a database or a pickle.
EXPORT_EXTS = (".png", ".pdf", ".svg", ".csv", ".json")

CACHE_SECONDS = 30
_cache = {}


def path(root):
    """Where a workspace's thread file lives."""
    return os.path.join(root, NAME)


def has(root):
    return os.path.isfile(path(root))


def _text(value, limit):
    return str(value or "").strip()[:limit]


def _rel(value):
    """A path inside the workspace, or None."""
    rel = str(value or "").strip().replace("\\", "/").lstrip("/")
    while rel.startswith("./"):
        rel = rel[2:]
    rel = rel.rstrip("/")
    if not rel or rel == "." or ".." in rel.split("/") or rel.startswith("~"):
        return None
    return rel


def _paths(value, where, field, problems):
    if value is None:
        return []
    if not isinstance(value, list):
        problems.append("%s: `%s` must be a list of paths" % (where, field))
        return []
    out = []
    for p in value:
        rel = _rel(p)
        if rel is None:
            problems.append("%s: %r in `%s` is not a path inside this workspace"
                            % (where, p, field))
            continue
        if rel not in out:
            out.append(rel)
    if len(out) > MAX_PATHS:
        problems.append("%s: %d paths in `%s`, and the cap is %d"
                        % (where, len(out), field, MAX_PATHS))
    return out[:MAX_PATHS]


def _exports(value, where, problems):
    """A thread's `exports`: `[{path, aggregate}]`, each under `results/`.

    `aggregate` is the owner's word that the file holds no row-level data, and
    only a path carrying it may be published. A bare string is a path asked
    for and not yet answered.
    """
    if value is None:
        return []
    if not isinstance(value, list):
        problems.append("%s: `exports` must be a list of {path, aggregate}"
                        % where)
        return []
    out, seen = [], set()
    for e in value:
        if isinstance(e, str):
            e = {"path": e, "aggregate": False}
        if not isinstance(e, dict):
            problems.append("%s: an `exports` entry is not an object" % where)
            continue
        rel = _rel(e.get("path"))
        if rel is None or not rel.startswith("results/"):
            problems.append("%s: export %r must be a path under results/, the "
                            "way it is copied into exports/results/"
                            % (where, e.get("path")))
            continue
        if os.path.splitext(rel)[1].lower() not in EXPORT_EXTS:
            problems.append("%s: export %s is not one of %s"
                            % (where, rel, ", ".join(EXPORT_EXTS)))
            continue
        agg = e.get("aggregate", False)
        if not isinstance(agg, bool):
            problems.append("%s: export %s: `aggregate` must be true or false"
                            % (where, rel))
            agg = False
        if rel in seen:
            continue
        seen.add(rel)
        out.append({"path": rel, "aggregate": agg})
    if len(out) > MAX_PATHS:
        problems.append("%s: %d exports, and the cap is %d"
                        % (where, len(out), MAX_PATHS))
    return out[:MAX_PATHS]


def exportable(t, rel):
    """May `rel` be published off this thread? Only once the owner said so."""
    return any(e["path"] == rel and e["aggregate"]
               for e in (t or {}).get("exports") or [])


def validate(raw):
    """`(clean, problems)`. A file with any problem is not written.

    REFUSED WHOLE, with every problem at once: fixing a thread file one refusal
    per round trip is how a five-minute job becomes an evening. Nothing here
    touches the filesystem.
    """
    problems = []
    if not isinstance(raw, dict):
        return None, ["the top level must be an object, not a %s"
                      % type(raw).__name__]

    if raw.get("version") != VERSION:
        problems.append("version must be %d, not %r" % (VERSION, raw.get("version")))

    dels_in = raw.get("deliverables")
    if not isinstance(dels_in, list) or not dels_in:
        problems.append("`deliverables` must be a non-empty list: every thread "
                        "hangs off something handed to another person")
        dels_in = []
    deliverables, dseen = [], set()
    for i, one in enumerate(dels_in):
        where = "deliverable %d" % (i + 1)
        if not isinstance(one, dict):
            problems.append("%s is not an object" % where)
            continue
        did = str(one.get("id") or "").strip()
        if not ID_RE.match(did):
            problems.append("%s: id %r must be 1-40 characters of a-z, 0-9 and "
                            "hyphen" % (where, did))
            continue
        where = "deliverable `%s`" % did
        if did in dseen:
            problems.append("%s appears twice" % where)
            continue
        dseen.add(did)
        title = _text(one.get("title"), MAX_TITLE)
        if not title:
            problems.append("%s has no `title`" % where)
        doc = ""
        if one.get("doc"):
            doc = _rel(one.get("doc")) or ""
            if not doc:
                problems.append("%s: `doc` %r is not a path inside this "
                                "workspace" % (where, one.get("doc")))
        deliverables.append({"id": did, "title": title, "doc": doc})

    threads_in = raw.get("threads")
    if not isinstance(threads_in, list):
        problems.append("`threads` must be a list")
        threads_in = []
    threads, seen = [], set()
    for i, one in enumerate(threads_in):
        where = "thread %d" % (i + 1)
        if not isinstance(one, dict):
            problems.append("%s is not an object" % where)
            continue
        tid = str(one.get("id") or "").strip()
        if not ID_RE.match(tid):
            problems.append("%s: id %r must be 1-40 characters of a-z, 0-9 and "
                            "hyphen. Sittings and jobs key off it." % (where, tid))
            continue
        where = "thread `%s`" % tid
        if tid in seen:
            problems.append("%s appears twice; an id names one thread" % where)
            continue
        seen.add(tid)

        deliv = str(one.get("deliverable") or "").strip()
        if deliv not in dseen:
            problems.append("%s: deliverable %r is not one this file declares"
                            % (where, deliv))
        title = _text(one.get("title"), MAX_TITLE)
        if not title:
            problems.append("%s has no `title`" % where)
        question = str(one.get("question") or "").strip()
        if len(question) > MAX_QUESTION:
            problems.append("%s: `question` is %d characters and the cap is %d"
                            % (where, len(question), MAX_QUESTION))

        files = _paths(one.get("files"), where, "files", problems)
        outputs = _paths(one.get("outputs"), where, "outputs", problems)
        exports = _exports(one.get("exports"), where, problems)
        check = ""
        if one.get("check"):
            check = _rel(one.get("check")) or ""
            if not check:
                problems.append("%s: `check` %r is not a path inside this "
                                "workspace" % (where, one.get("check")))

        writes = []
        w_in = one.get("writes") or []
        if not isinstance(w_in, list):
            problems.append("%s: `writes` must be a list of {file, anchor}" % where)
            w_in = []
        for w in w_in:
            if not isinstance(w, dict):
                problems.append("%s: a `writes` entry is not an object" % where)
                continue
            rel = _rel(w.get("file"))
            anchor = str(w.get("anchor") or "").strip()
            if rel is None:
                problems.append("%s: `writes` file %r is not a path inside this "
                                "workspace" % (where, w.get("file")))
                continue
            if not anchor:
                problems.append("%s: `writes` on %s has no `anchor` -- the "
                                "heading the write-up sits under" % (where, rel))
                continue
            writes.append({"file": rel, "anchor": anchor[:MAX_TEXT]})

        tasks = []
        t_in = one.get("tasks") or []
        if not isinstance(t_in, list):
            problems.append("%s: `tasks` must be a list of {text, done}" % where)
            t_in = []
        for t in t_in:
            if not isinstance(t, dict):
                problems.append("%s: a task is not an object" % where)
                continue
            text = _text(t.get("text"), MAX_TEXT)
            if not text:
                problems.append("%s: a task has no `text`" % where)
                continue
            done = t.get("done", False)
            if not isinstance(done, bool):
                problems.append("%s: task %r: `done` must be true or false"
                                % (where, text))
                done = False
            tasks.append({"text": text, "done": done})
        if len(tasks) > MAX_TASKS:
            problems.append("%s: %d tasks, and the cap is %d. Close the done "
                            "ones out or split the thread."
                            % (where, len(tasks), MAX_TASKS))

        decisions = []
        d_in = one.get("decisions") or []
        if not isinstance(d_in, list):
            problems.append("%s: `decisions` must be a list of {q, rule}" % where)
            d_in = []
        for d in d_in:
            if not isinstance(d, dict):
                problems.append("%s: a decision is not an object" % where)
                continue
            q = _text(d.get("q"), MAX_TEXT)
            if not q:
                problems.append("%s: a decision has no `q`" % where)
                continue
            rule = d.get("rule")
            if rule is not None and not isinstance(rule, str):
                problems.append("%s: decision %r: `rule` is a sentence or null"
                                % (where, q))
                rule = None
            rule = (rule or "").strip()[:MAX_QUESTION] or None
            decisions.append({"q": q, "rule": rule})

        doc = str(one.get("doc") or "").strip()
        if doc and not DOC_RE.match(doc):
            problems.append("%s: `doc` %r is not a document id. It is the short "
                            "name `board read` lists, never a path."
                            % (where, one.get("doc")))
            doc = ""

        blocked = one.get("blockedBy") or []
        if not isinstance(blocked, list):
            problems.append("%s: `blockedBy` must be a list of thread ids" % where)
            blocked = []
        blocked = [str(b or "").strip() for b in blocked if str(b or "").strip()]

        closed = one.get("closed", False)
        if not isinstance(closed, bool):
            problems.append("%s: `closed` must be true or false" % where)
            closed = False

        threads.append({
            "id": tid, "deliverable": deliv, "title": title,
            "question": question[:MAX_QUESTION],
            "files": files, "outputs": outputs, "exports": exports,
            "check": check,
            "writes": writes, "tasks": tasks[:MAX_TASKS], "decisions": decisions,
            "doc": doc, "blockedBy": blocked[:MAX_BLOCKED], "closed": closed,
        })

    if len(threads) > MAX_THREADS:
        problems.append("%d threads, and past %d it is not a picture any more"
                        % (len(threads), MAX_THREADS))
    for t in threads:
        for b in t["blockedBy"]:
            if b == t["id"]:
                problems.append("thread `%s` is blocked by itself" % b)
            elif b not in seen:
                problems.append("thread `%s` is blockedBy `%s`, which this "
                                "file does not declare" % (t["id"], b))

    if problems:
        return None, problems
    return {"version": VERSION, "deliverables": deliverables,
            "threads": threads}, []


def read(root):
    """`(clean, problems)`; `(None, [])` where there is no file."""
    target = path(root)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError:
        return None, []
    except ValueError as exc:
        return None, ["%s is not valid JSON: %s" % (target, exc)]
    return validate(raw)


def write(root, raw):
    """Validate and store. `(problems, path)`; nothing is written if any."""
    clean, problems = validate(raw)
    target = path(root)
    if problems:
        return problems, target
    try:
        tmp = target + ".new"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, target)
    except OSError as exc:
        return ["could not write %s: %s" % (target, exc)], target
    forget(root)
    return [], target


def forget(root):
    """Drop every cached reading of this workspace's thread file."""
    _cache.pop(os.path.realpath(root), None)
    try:
        from . import map as course_map                      # local: a cycle
        course_map._cache.pop(os.path.realpath(root), None)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        from . import plan
        plan._cache.pop(os.path.realpath(root), None)
    except Exception:                                        # noqa: BLE001
        pass


def thread(clean, tid):
    for t in (clean or {}).get("threads") or []:
        if t["id"] == tid:
            return t
    return None


def proposal(root, one):
    """`(state, problems)` for a thread proposed on a card, against this
    workspace's thread file: `there` where the file has that id, `bad` where
    adding it would be refused (every problem), `new` where one tap adds it."""
    clean, broken = read(root) if root else (None, [])
    if broken:
        return "bad", list(broken)
    raw = clean or {"version": VERSION, "deliverables": [], "threads": []}
    if thread(clean, str((one or {}).get("id") or "")):
        return "there", []
    _ok, problems = validate(dict(raw, threads=list(raw["threads"]) + [one]))
    return ("bad", problems) if problems else ("new", [])


# A commit subject's lead word: `<word>: the rest`. No slash, so a workspace id
# (`research/TRD-EHR: ...`) is never read as a thread.
PREFIX_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]{0,59}):\s")


def commit_prefix(clean, message, where=""):
    """`(thread id, problem)` for the subject `board push` was handed. Pure.

    The lead word before a colon must be a thread of `clean`. No lead word is
    `("", None)`: a save with no thread named is still a save. `where` is the
    workspace id, taken off the front first because the push puts it there.
    """
    text = (message or "").strip()
    if where and text.startswith(where + ":"):
        text = text[len(where) + 1:].lstrip()
    m = PREFIX_RE.match(text)
    if not m or not clean:
        return "", None
    word = m.group(1)
    if thread(clean, word):
        return word, None
    ids = sorted(t["id"] for t in clean.get("threads") or [])
    return "", ("`%s` is not a thread in %s. Lead the message with one of: %s "
                "-- or leave the prefix off." % (word, NAME,
                                                 ", ".join(ids) or "(none)"))


# ---------------------------------------------------------------------------
# resolution: the file checked against the tree
# ---------------------------------------------------------------------------
def here(root, rel):
    """Does this workspace really hold that path, inside itself? A `results/`
    path counts where `exports/results/` holds it (`paths.present`)."""
    return bool(toolpaths.present(root, rel))


def resolve(root, clean):
    """The file as it is TRUE today. Never what is on disk.

    A `files` path that has gone drops out, and so does a `doc` that is no
    longer offered and a `blockedBy` on a closed thread. A thread itself never
    drops out: it is a question, and a question survives its code moving.
    `outputs` and `writes` are left alone, because a path that does not exist
    yet is what an unfinished thread is.
    """
    out = []
    closed = set(t["id"] for t in clean["threads"] if t["closed"])
    for t in clean["threads"]:
        t = dict(t)
        t["files"] = [f for f in t["files"] if here(root, f)]
        if t["doc"] and not _doc_found(root, t["doc"]):
            t["doc"] = ""
        t["blockedBy"] = [b for b in t["blockedBy"] if b not in closed]
        out.append(t)
    return out


def next_task(resolved):
    """`(thread, task)`: the first open task of the first thread not blocked.

    Pure, over what `resolve` returns, so a `blockedBy` on a closed thread is
    already gone. A closed thread is skipped, and so is an unblocked one with
    no open task. `(None, None)` where nothing is left.
    """
    for t in resolved or []:
        if t["closed"] or t["blockedBy"]:
            continue
        for task in t["tasks"]:
            if not task["done"]:
                return t, task
    return None, None


def _doc_found(root, ident):
    try:
        from . import reading                                # local: a cycle
        found, _name = reading.find(root, ident)
        return bool(found)
    except Exception:                                        # noqa: BLE001
        return False


def _stem(rel):
    """A path without its extension: `paper1/manuscript.md` and its built
    `paper1/manuscript.pdf` are one document."""
    head, tail = os.path.split(rel or "")
    return "/".join(p for p in (head, os.path.splitext(tail)[0]) if p)


def _claims(clean, docs):
    """The stems a thread file claims: each deliverable's `doc`, each thread's
    `doc`, and each path a thread names in `files` or `writes`."""
    by_id = dict((d["id"], d.get("rel") or "") for d in docs)
    out = set(_stem(d["doc"]) for d in clean["deliverables"] if d["doc"])
    for t in clean["threads"]:
        if t["doc"] in by_id:
            out.add(_stem(by_id[t["doc"]]))
        out.update(t["files"])                       # a directory, whole
        out.update(_stem(f) for f in t["files"])
        out.update(_stem(w["file"]) for w in t["writes"])
    out.discard("")
    return out


def _claimed(doc, claims):
    """Is this document on a thread or a deliverable?

    By its own stem, by a claimed directory above it, or -- for a piece under
    `parts/` or `sections/` -- by the whole it is cut from, because a piece is
    re-cut from its whole and belongs wherever the whole does.
    """
    rel = doc.get("rel") or ""
    stems = [_stem(rel)]
    try:
        from .library import _piece_of                       # local: a cycle
        whole = _piece_of(rel)
    except Exception:                                        # noqa: BLE001
        whole = None
    if whole:
        stems.append("/".join(p for p in whole if p))
    for s in stems:
        if s in claims:
            return True
        if any(s.startswith(c + "/") for c in claims):
            return True
    return False


def check(root, documents=True):
    """What the file claims that the tree does not. `board thread --check`."""
    clean, problems = read(root)
    if problems:
        return problems
    if not clean:
        return []
    out = []
    for d in clean["deliverables"]:
        if d["doc"] and not here(root, d["doc"]):
            out.append("deliverable `%s` is %s, which is not there yet"
                       % (d["id"], d["doc"]))
    for t in clean["threads"]:
        for f in t["files"]:
            if not here(root, f):
                out.append("`%s` names %s, which is not there any more"
                           % (t["id"], f))
        if t["doc"] and not _doc_found(root, t["doc"]):
            out.append("`%s` points at the document `%s`, which this "
                       "workspace does not offer any more" % (t["id"], t["doc"]))
        for w in t["writes"]:
            if not here(root, w["file"]):
                out.append("`%s` is written up in %s, which is not there"
                           % (t["id"], w["file"]))
        if t["closed"] and any(not x["done"] for x in t["tasks"]):
            out.append("`%s` is closed with %d open task(s) on it"
                       % (t["id"], sum(1 for x in t["tasks"] if not x["done"])))
    if documents:
        try:
            from . import reading
            docs = reading.documents(root)
        except Exception:                                    # noqa: BLE001
            docs = []
        claims = _claims(clean, docs)
        for d in docs:
            if _claimed(d, claims):
                continue
            out.append("the document `%s` (%s) is on no thread and no "
                       "deliverable. Put its id in a thread's `doc` if it "
                       "belongs on one." % (d["id"], d.get("rel")))
    return out


# ---------------------------------------------------------------------------
# status: derived, never typed
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


def unfinished(jobs, tid=None):
    """The registered jobs of one thread -- or of every thread, with no `tid` --
    that have not finished."""
    return [j for j in merged(jobs).values()
            if (tid is None or j.get("thread") == tid) and not finished(j)]


def _under(p, base):
    return p == base or p.startswith(base + "/")


def stage(t, present, texts, dirty, jobs):
    """One thread's status and flags. A PURE function of what it is handed.

        t        a thread, as `validate` returns it
        present  the set of workspace-relative paths that exist
        texts    {path: text} for the files the thread writes up in
        dirty    workspace-relative paths git reports as changed
        jobs     the job registry, as records

    Returns `{"status", "unsaved", "decisions", "tasks"}` -- the status is the
    first true row of done, running, requested, written, result, open. A job
    still out is `running`; a relay request the cluster has not reported on,
    with nothing else out, is `requested`.
    """
    outputs_there = all(o in present for o in t["outputs"])
    anchors_there = all(w["anchor"] in (texts.get(w["file"]) or "")
                        for w in t["writes"])
    if t["closed"]:
        status = "done"
    elif any(str(j.get("state") or "").upper() != REQUESTED
             for j in unfinished(jobs, t["id"])):
        status = "running"
    elif unfinished(jobs, t["id"]):
        status = "requested"
    elif (t["outputs"] or t["writes"]) and outputs_there and anchors_there:
        status = "written" if t["writes"] else "result"
    elif t["outputs"] and outputs_there:
        status = "result"
    else:
        status = "open"
    mine = list(t["files"]) + list(t["outputs"]) + [w["file"] for w in t["writes"]]
    unsaved = any(_under(p, base) for p in dirty for base in mine)
    return {
        "status": status,
        "unsaved": unsaved,
        "decisions": sum(1 for d in t["decisions"] if d["rule"] is None),
        "tasks": sum(1 for x in t["tasks"] if not x["done"]),
    }


def jobs_of(root):
    """The job registry as records, from wherever `jobs.registry` keeps it.
    Empty if none."""
    from .. import jobs as job_registry
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


def registered_of(root):
    """Every job the registry's merged view holds: local jobs, relay requests
    and their reports. See `jobs.view`."""
    from .. import jobs as job_registry
    try:
        return list(job_registry.view(root).values())
    except Exception:                                        # noqa: BLE001
        return jobs_of(root)


def missions_of(root):
    """The mission running here, if it names a thread, as a job record.

    A mission is long work the way a job is, and carries a thread id the same
    way, so a thread with one live says `running` too.
    """
    try:
        from .. import missions
        rec = missions.live_mission(root)
    except Exception:                                        # noqa: BLE001
        return []
    if not rec or not rec.get("thread"):
        return []
    return [{"jobid": "mission:%s" % rec.get("id"), "thread": rec["thread"]}]


def dirty_of(root):
    """Workspace-relative paths git shows as changed or untracked."""
    try:
        prefix = subprocess.run(
            ["git", "rev-parse", "--show-prefix"], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            universal_newlines=True, timeout=10).stdout.strip()
        raw = subprocess.run(
            ["git", "status", "--porcelain", "-z", "--untracked-files=all",
             "--", "."], cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, universal_newlines=True,
            timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    out, fields, i = [], raw.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        code, rel = entry[:2], entry[3:]
        if code[0] in "RC":
            i += 1                       # the original path follows a rename
        if prefix and rel.startswith(prefix):
            rel = rel[len(prefix):]
        out.append(rel.rstrip("/"))
    return out


def stages(root):
    """`{thread id: stage}` for this workspace, read off disk. Cached briefly."""
    key = os.path.realpath(root)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    clean, problems = read(root)
    found = {}
    if clean and not problems:
        threads = resolve(root, clean)
        present, texts = set(), {}
        for t in threads:
            for o in t["outputs"]:
                if here(root, o):
                    present.add(o)
            for w in t["writes"]:
                if w["file"] not in texts:
                    try:
                        with open(os.path.join(root, w["file"]), "r",
                                  encoding="utf-8", errors="replace") as fh:
                            texts[w["file"]] = fh.read()
                    except OSError:
                        texts[w["file"]] = ""
        dirty = dirty_of(root)
        jobs = registered_of(root) + missions_of(root)
        # The thread as written, not as resolved: resolving drops a deleted
        # file from `files`, and that deletion is an unsaved change.
        for t in clean["threads"]:
            found[t["id"]] = stage(t, present, texts, dirty, jobs)
    _cache[key] = (time.time(), found)
    return found


# ---------------------------------------------------------------------------
# migration from the written map
# ---------------------------------------------------------------------------
def from_map(written, deliverable_id, deliverable_title=""):
    """A `live/map.json` document, as a thread file. Pure.

    Each box becomes a thread: `files` (with `dir` folded in), `doc` and
    `blockedBy` carry over; `status` and the edges are dropped, because status
    is derived and an arrow is what `blockedBy` draws. The box's plain name and
    its real identifier become the title, and what it does and its note become
    the question until somebody writes the real one.
    """
    threads = []
    for n in written.get("nodes") or []:
        files = list(n.get("files") or [])
        d = (n.get("dir") or "").strip("/")
        if d and not any(_under(f, d) for f in files):
            files.append(d)
        title = n.get("name") or n["id"]
        if n.get("also"):
            title = "%s (%s)" % (title, n["also"])
        question = " ".join(x.strip() for x in (n.get("does"), n.get("note"))
                            if x and x.strip())
        threads.append({
            "id": n["id"], "deliverable": deliverable_id,
            "title": title[:MAX_TITLE], "question": question[:MAX_QUESTION],
            "files": files, "outputs": [], "exports": [], "check": "",
            "writes": [],
            "tasks": [],
            "decisions": [], "doc": n.get("doc") or "",
            "blockedBy": list(n.get("blockedBy") or []), "closed": False,
        })
    return {
        "version": VERSION,
        "deliverables": [{"id": deliverable_id,
                          "title": (deliverable_title or written.get("title")
                                    or deliverable_id)[:MAX_TITLE],
                          "doc": ""}],
        "threads": threads,
    }
