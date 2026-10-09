"""The repository underneath a lesson: what is uncommitted, what save does,
and what somebody changed beside the lesson.

The constraint: everything is scoped to the workspace by pathspec, because
Atlas holds every workspace and the root's status or log answers for all.
"""

import glob as _glob
import json
import os
import subprocess
import time

from .. import gitops, leaving, paths, subjects, worktree
from ..course import homework
from ..course import repo as course_repo


# Keyed by workspace root, so one workspace never answers for another.
_DIRTY = {}
DIRTY_TTL = 8.0


def repo_dirty(repo):
    """How many files are uncommitted in this workspace, or None if unknown:
    the board's unsaved-work badge. Scoped by `save_pathspec`, the scope
    `run_push` commits.
    """
    now = time.time()
    key = os.path.realpath(repo.root)
    hit = _DIRTY.get(key)
    if hit and hit[1] is not None and now - hit[0] < DIRTY_TTL:
        return hit[1]
    value = None
    if worktree.git_dir(repo.root):
        try:
            # `--no-optional-locks`: a poll must not take `.git/index.lock`,
            # which a timeout kill would leave behind, blocking every commit.
            p = subprocess.run(["git", "--no-optional-locks", "status",
                                "--porcelain", "--", repo.root], cwd=repo.root,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               timeout=10)
            if p.returncode == 0:
                lines = [l for l in p.stdout.decode("utf-8", "replace").splitlines()
                         if l.strip()]
                value = len(lines)
        except (OSError, subprocess.TimeoutExpired):
            value = None
    _DIRTY[key] = (now, value)
    return value


def hw_needs_building(repo):
    """The sitting's problem set if its PDF is missing or older than its
    `.tex`, else None. Two stats."""
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        return None
    if not st or not st.get("rel") or not st.get("name"):
        return None
    tex_path = os.path.join(repo.root, st["rel"])
    if not os.path.exists(tex_path):
        return None
    pdf = homework.compiled_pdf(repo.root, tex_path)
    if pdf and os.path.getmtime(pdf) >= os.path.getmtime(tex_path):
        return None
    return st["name"]


def run_hw_build(repo):
    """Compile the write-up because somebody asked (always runs) and return
    the `hw.json` record, with `pdf` and any LaTeX tail."""
    try:
        st = homework.status(repo.root, repo.state())
    except Exception:                                        # noqa: BLE001
        st = None
    if not st or not st.get("rel") or not st.get("name"):
        return {"ok": False,
                "detail": "this session has no write-up yet, so there is nothing "
                          "to build. The first `board writeup add` starts one."}
    try:
        homework.build(repo.root, repo.live, st)
    except OSError as exc:
        return {"ok": False, "set": st.get("name"), "detail": str(exc)}
    rec = homework.last_build(repo.live) or {"ok": False, "detail": "no record"}
    rec.setdefault("set", st.get("name"))
    return rec


def build_before_push(repo):
    """Compile the write-up when its PDF is missing or older than the `.tex`,
    so a commit never pairs tonight's proof with last week's PDF. Errors reach
    the iPad through `hw.json`."""
    name = hw_needs_building(repo)
    if not name:
        return None
    try:
        st = homework.status(repo.root, repo.state())
        code, _pdf, out = homework.build(repo.root, repo.live, st)
    except Exception as exc:                                 # noqa: BLE001
        out, code = str(exc), 1
    return {"set": name, "ok": code == 0, "detail": out[-800:]}


def save_pathspec(root, top, only=None):
    """What a save from the workspace at `root` commits, as pathspecs relative
    to `top`, its repository. `(specs, refused)`.

    The workspace's directory, or `only`'s paths, refusing any outside it.
    The tool and nested workspaces are excluded; `.nfs*` is the root
    .gitignore's. Each exclude literally names a directory inside a narrowed
    path, because otherwise git 2.52's `add -A` adds no untracked file.
    """
    real_top = os.path.realpath(top)
    real_root = os.path.realpath(root)

    def rel(path):
        r = os.path.relpath(os.path.realpath(path), real_top)
        return "." if r == os.curdir else r

    refused = []
    if only:
        specs = []
        for p in only:
            if paths.within(os.path.abspath(p), real_root):
                specs.append(rel(os.path.abspath(p)))
            else:
                refused.append(p)
    else:
        specs = [rel(real_root)]

    nested = [paths.TOOL]
    try:
        nested += subjects.roots()
    except OSError:
        pass
    narrowed = [os.path.join(real_top, s) for s in specs]
    for other in nested:
        real = os.path.realpath(other)
        if real == real_root or not paths.within(real, real_root):
            continue
        if any(real != n and paths.within(real, n) for n in narrowed):
            specs.append(":(exclude)" + rel(real))
    return specs, refused


def repo_top(root):
    """The repository the workspace at `root` is in, asked of git, because a
    worktree's or submodule's git directory is not under it."""
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10)
        found = p.stdout.decode("utf-8", "replace").strip()
        if p.returncode == 0 and found:
            return found
    except (OSError, subprocess.TimeoutExpired):
        pass
    return root


def run_push(repo, message=None):
    """Commit and push this workspace (`save_pathspec`), and record it.

    No co-author trailer: the work is the owner's. Never commits into an
    outstanding rebase or merge, read from the repository's git directory;
    the board says what is in the way.
    """
    busy = worktree.busy_reason(repo.root)
    if busy:
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": ("nothing was committed: %s in this repository, so a "
                       "commit now would land in the middle of it. Nothing has "
                       "been lost -- finish or abort that in the terminal and "
                       "press save again." % busy),
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    # The same PHI content scan as `board push` (`leaving.py`), with no
    # override: a tablet tap must not wave a PHI fence through.
    phi = leaving.reason(repo.root)
    if phi:
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": phi,
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    # A stale lock from a killed git is removed: its own advice cannot be
    # followed from an iPad.
    lock_verdict, lock_said = worktree.lock_reason(repo.root)
    cleared = None
    if lock_verdict == "held":
        record = {
            "ok": False,
            "at": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detail": "nothing was committed: " + lock_said,
        }
        with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        return record
    if lock_verdict == "stale":
        cleared = worktree.clear_stale_lock(repo.root)
    # An out-of-date write-up is rebuilt into the commit.
    built = build_before_push(repo)

    # The workspace leads the message, and the commit is of the repository
    # the workspace is in, carrying only `save_pathspec`.
    said = message or gitops.SAVE
    where = subjects.identify(repo.root)
    lead = subjects.prefix(repo.root)
    if lead and not said.startswith(lead + ":"):
        said = "%s: %s" % (lead, said)

    top = repo_top(repo.root)
    specs, _ = save_pathspec(repo.root, top)
    ok, out = gitops.save(top, specs, said)
    code = 0 if ok else 1

    record = {
        "ok": code == 0,
        "at": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": where,
        "detail": out[-1200:],
    }
    if cleared:
        record["cleared_lock"] = True
        record["detail"] = cleared + "\n" + record["detail"]
    if built:
        # On the board, not only in a log.
        record["built"] = built["set"]
        record["built_ok"] = built["ok"]
        if not built["ok"]:
            record["detail"] = (
                "the write-up did not compile, so its PDF is behind the source "
                "that was pushed:\n" + built["detail"] + "\n\n" + record["detail"])
    with open(os.path.join(repo.live, "push.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    return record


# ---------------------------------------------------------------------------
# what somebody did while the board was not looking
# ---------------------------------------------------------------------------
# What changed beside the lesson, for the brief: every turn is cold, so this
# is the only way a tutor learns of a laptop commit. Scoped to the workspace;
# named as the person's work, never the tutor's, because a tutor claiming
# someone else's commit is undetectable and corrosive. Subjects, filenames
# and a count, never the diff, so the brief does not grow.

_BESIDE = {}
BESIDE_TTL = 20.0

# Past these, the count is the fact.
BESIDE_COMMITS = 8
BESIDE_FILES = 12

# The furthest back this looks: older commits are history, not news.
BESIDE_WINDOW = 3 * 86400


def _seen_until(repo):
    """When the tutor's knowledge of this workspace stops: its newest card,
    else the sitting's opening, capped at `BESIDE_WINDOW`."""
    newest = 0
    try:
        for name in os.listdir(repo.cards):
            if not name.endswith((".md", ".markdown", ".tex")):
                continue
            try:
                newest = max(newest, os.path.getmtime(
                    os.path.join(repo.cards, name)))
            except OSError:
                continue
    except OSError:
        newest = 0

    if not newest:
        said = (repo.state() or {}).get("opened") or ""
        for shape in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                newest = time.mktime(time.strptime(said, shape))
                break
            except (ValueError, OverflowError):
                continue

    floor = time.time() - BESIDE_WINDOW
    return max(newest or floor, floor)


def beside_the_lesson(repo):
    """What somebody did to this workspace that the tutor has not been told:
    `{"commits": [...], "uncommitted": [...], "files": n, "since": t}`, or
    None outside git. Cached; the payload is polled often."""
    now = time.time()
    key = os.path.realpath(repo.root)
    hit = _BESIDE.get(key)
    if hit and now - hit[0] < BESIDE_TTL:
        return hit[1]

    value = None
    if worktree.git_dir(repo.root):
        since = _seen_until(repo)
        value = {"since": since, "commits": [], "uncommitted": [], "files": 0}
        try:
            # Scoped by pathspec, not filtered afterwards.
            p = subprocess.run(
                ["git", "--no-optional-locks", "log",
                 "--since=@%d" % int(since), "--no-merges",
                 "--pretty=%at%x00%s", "--", repo.root],
                cwd=repo.root, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=10)
            if p.returncode == 0:
                for line in p.stdout.decode("utf-8", "replace").splitlines():
                    at, _, subject = line.partition("\0")
                    if not subject.strip():
                        continue
                    try:
                        when = int(at)
                    except ValueError:
                        when = 0
                    value["commits"].append({"at": when,
                                             "subject": subject.strip()[:100]})
        except (OSError, subprocess.TimeoutExpired):
            pass

        theirs = uncommitted(repo.root, session=repo.session)
        if theirs is not None:
            # Counted after the filter, so count and list agree.
            value["files"] = len(theirs)
            value["uncommitted"] = theirs[:BESIDE_FILES]

    _BESIDE[key] = (now, value)
    return value


def uncommitted(root, paths=None, session=None):
    """Uncommitted paths under `paths` (default: the workspace), relative to
    `root`; None where git cannot be asked. The session directory is left
    out: it is the board's own scratch."""
    try:
        # Porcelain paths are relative to the git root; re-relativise them.
        top = root
        tp = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                            cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=10)
        if tp.returncode == 0:
            said = tp.stdout.decode("utf-8", "replace").strip()
            if said:
                top = said
        spec = [os.path.join(root, p) if not os.path.isabs(p) else p
                for p in (paths or [root])]
        p = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain", "--"] + spec,
            cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    names = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        # `XY <path>`, and a rename is `XY <old> -> <new>`.
        rel = line[3:].strip().strip('"')
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        try:
            # Both sides resolved, since git strips symlinks (`/var` is
            # `/private/var` on a Mac).
            here = os.path.relpath(os.path.realpath(os.path.join(top, rel)),
                                   os.path.realpath(root))
        except ValueError:
            here = rel
        names.append(here)
    bound = session or course_repo.session_dir(root)
    if not bound:
        return names
    scratch = os.path.relpath(bound, root)
    return [n for n in names
            if not n.startswith(scratch + os.sep) and n != scratch]
