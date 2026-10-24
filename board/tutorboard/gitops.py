"""Every commit, push and pull the board makes, in one place.

    commit(root, paths, message, refuse=None, exempt=None)
                                                named paths only, no trailers
    push(root, board=False)                     fetch, merge, push; never forced
    foreign(root, base)                         unpushed commits the board did not make
    merge_in(root, theirs)                      a merge around uncommitted work
    pull(root)                                  fast-forward only, guarded
    lockfiles_moved(root, before, after)        the subjects to rebuild after one
    save(root, paths, message)                  commit, then push
    save_message(paths), is_save(message)       a save's message, and reading one back
    adopt_private(base)                         clone ai-config where it is missing

The Mac's timed pull is `sync.Sync`; `save-and-push.sh` wraps `save`;
code.py keeps its own git for a coding session's ref. While a session has
`code` set, `commit` on main refuses its held paths (`held_refusal`), and so
does the pre-commit hook (`audit.coding_refusals`): they reach main only through
`board code <id> --end`, the one caller of `commit(exempt=<id>)`, which sets
`END_ENV` for the hook.

The constraint: nothing here commits into an operation somebody started in
a terminal (rebase, merge, cherry-pick, revert, bisect, detached HEAD;
`worktree.busy_reason`).
"""

import json
import os
import re
import subprocess
import sys

from tutorboard import worktree

# A save rather than a piece of work, read back by `is_save`: a commit whose
# message (bare, or after the subject's own prefix) is one of these or starts
# with `SAVE_PREFIX` (`save_message`). History carries all of them.
SAVE = "lesson complete"
SAVES = (SAVE, "lesson transcript", "stopping point")
SAVE_PREFIX = "save:"
# How many changed paths a save's message names before it counts the rest.
SAVE_NAMES = 3

# A longer network wait is an invisible credential prompt or a dead remote.
NET_TIMEOUT = 120
LOCAL_TIMEOUT = 60
# A commit runs the hooks, and Atlas's pre-commit gate reads the staged diff.
COMMIT_TIMEOUT = 180

_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false"}

# The session whose own held paths a commit may carry: set only by `board code
# <id> --end`, read by the pre-commit hook.
END_ENV = "BOARD_CODE_END"


def save_message(paths):
    """The message of a save that names none: `save: <changed files>`, the
    first `SAVE_NAMES` of `paths` and a count of the rest."""
    paths = [p for p in (paths or []) if p]
    if not paths:
        return SAVE_PREFIX + " nothing changed"
    named = ", ".join(paths[:SAVE_NAMES])
    more = len(paths) - SAVE_NAMES
    return "%s %s%s" % (SAVE_PREFIX, named,
                        " and %d more" % more if more > 0 else "")


def is_save(message, prefixes=()):
    """Is a commit with this message (its first line) a save rather than a
    piece of work: one of `SAVES`, or `save: ...`, bare or after a prefix
    naming one of `prefixes` (a subject's id or slug, `subjects.prefix`).
    Nothing else: any other head (`board: `, `HANDOFF: `) is work."""
    said = (str(message or "").strip().splitlines() or [""])[0]
    tries = [said]
    head, colon, rest = said.partition(":")
    slugs = set(str(p).strip().split("/")[-1] for p in prefixes or () if p)
    if colon and head.strip() and head.strip().split("/")[-1] in slugs:
        tries.append(rest)
    for one in tries:
        low = one.strip().lower().rstrip(".").strip()
        if low in SAVES or low.startswith(SAVE_PREFIX):
            return True
    return False


def _git(root, *args, **kw):
    """`(code, output)` of one git command in `root`, stdout and stderr
    together. `env` adds to the environment. Never raises: a timeout is code
    124, a missing git 127."""
    env = dict(os.environ, **_ENV)
    env.update(kw.get("env") or {})
    try:
        p = subprocess.run(["git"] + list(args), cwd=root, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=kw.get("timeout", LOCAL_TIMEOUT))
    except subprocess.TimeoutExpired:
        return 124, "git %s timed out" % args[0]
    except OSError as exc:
        return 127, str(exc)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def _lines(text):
    return sorted(set(l for l in text.splitlines() if l.strip()))


def why(out, default="git failed"):
    """The line of git's output that says what went wrong: the first
    `fatal:` or `error:` line, else the last line. A refused remote ends
    with "...and the repository exists.", which says nothing."""
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    for l in lines:
        if l.lower().startswith(("fatal:", "error:")):
            return l
    return lines[-1] if lines else default


def _hooks(root):
    """Turn on a repository's own `.githooks/` when `core.hooksPath` is unset,
    so the attribution stripper and the commit-time gate run from its first
    commit. A repository without `.githooks/` is left as it is: a hook path
    pointing into another repository would run that repository's gate here."""
    if not os.path.isdir(os.path.join(root, ".githooks")):
        return None
    code, now = _git(root, "config", "core.hooksPath")
    if code == 0 and now:
        return None
    _git(root, "config", "core.hooksPath", ".githooks")
    return "enabled .githooks for this clone"


# The Mac's session store under an Atlas root, and a session id in it.
SESSIONS = "sessions"
_SESSION_ID = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")
MAIN = "main"


def held_paths(root):
    """`{session id: [held paths]}` for every session under `root` whose
    session.json has `code` set. Empty where `root` has no session store
    (any other repository)."""
    store = os.path.join(root, SESSIONS)
    try:
        names = sorted(os.listdir(store))
    except OSError:
        return {}
    out = {}
    for sid in names:
        if not _SESSION_ID.match(sid):
            continue
        try:
            with open(os.path.join(store, sid, "session.json"), "r",
                      encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        code = rec.get("code") if isinstance(rec, dict) else None
        if not isinstance(code, dict):
            continue
        held = [p.strip("/") for p in code.get("paths") or []
                if isinstance(p, str) and p.strip("/")]
        if held:
            out[sid] = held
    return out


def _under(rel, base):
    return rel == base or rel.startswith(base + "/")


def held_refusal(root, paths, exempt=None):
    """Why a commit of `paths` on main here would take files a coding session
    holds, or "". Only the files the commit would change count: a commit of a
    whole subject whose held files are untouched goes through. Session
    `exempt`'s own paths are not refused: its `--end`."""
    held = dict((sid, p) for sid, p in held_paths(root).items()
                if sid != exempt)
    if not held:
        return ""
    code, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or branch != MAIN:
        return ""
    _, changed = _git(root, "diff", "HEAD", "--name-only", "--", *paths)
    _, new = _git(root, "ls-files", "--others", "--exclude-standard", "--",
                  *paths)
    files = _lines(changed + "\n" + new)
    said = []
    for sid, theirs in sorted(held.items()):
        mine = [f for f in files if any(_under(f, h) for h in theirs)]
        if mine:
            said.append(
                "nothing was committed: %s %s held by coding session %s. "
                "Its changes go to code/%s (`board push` from that "
                "session) and reach main with `board code %s --end`; commit "
                "other paths with `board push \"msg\" -- <paths>`."
                % (", ".join(mine[:6]) + (" and %d more" % (len(mine) - 6)
                                          if len(mine) > 6 else ""),
                   "is" if len(mine) == 1 else "are", sid, sid, sid))
    return "\n".join(said)


def commit(root, paths, message, refuse=None, exempt=None):
    """Commit the named `paths` (relative to `root`) and nothing else.
    `(ok, said)`; nothing to commit is ok.

    `git add -A -- paths`, then a commit of exactly those paths: whatever else
    is staged stays staged and out of this commit. The message goes in as
    given, with no trailers. `refuse(paths)` may return a reason, and then
    nothing is committed; so does a change on main to a path a coding session
    holds (`held_refusal`). `exempt`, a session id, lifts that refusal for its
    own paths here and in the pre-commit hook (`END_ENV`); only `board code
    <id> --end` passes it.

    `--only` is used only when something outside the paths is staged. It takes
    each path from the working tree, so it drops a staged removal of a file
    still on disk (`git rm --cached`); that case is named, never silent.
    """
    paths = [p for p in (paths or []) if p]
    if not paths:
        return False, "no paths named, so nothing was committed"
    if refuse is not None:
        why = refuse(list(paths))
        if why:
            return False, why
    code, _ = _git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return False, "not a git repository: %s" % root
    busy = worktree.busy_reason(root)
    if busy:
        return False, ("nothing was committed: %s in this repository. Nothing "
                       "has been lost -- finish or abort it, then save again."
                       % busy)
    held = held_refusal(root, paths, exempt)
    if held:
        return False, held
    said = []
    hooked = _hooks(root)
    if hooked:
        said.append(hooked)
    code, out = _git(root, "add", "-A", "--", *paths)
    if code != 0:
        return False, "git add failed: %s" % out
    _, staged = _git(root, "diff", "--cached", "--name-only")
    _, mine = _git(root, "diff", "--cached", "--name-only", "--", *paths)
    if not mine.strip():
        said.append("nothing to commit")
        return True, "\n".join(said)
    if _lines(staged) == _lines(mine):
        cmd = ["commit", "-q", "-m", message]
    else:
        cmd = ["commit", "-q", "--only", "-m", message, "--"] + paths
        _, gone = _git(root, "diff", "--cached", "--name-only",
                       "--diff-filter=D", "--", *paths)
        kept = [f for f in _lines(gone) if os.path.exists(os.path.join(root, f))]
        if kept:
            said.append(
                "NOT UNTRACKED: %s\n  staged for removal, still on disk, and "
                "something outside the pathspec is staged -- so this commit "
                "uses --only, which takes those paths from the working tree "
                "and drops the removal.\n  Nothing has been lost. Commit the "
                "removal by itself: stage only it and commit with no pathspec."
                % " ".join(kept))
    _, before = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    code, out = _git(root, *cmd, timeout=COMMIT_TIMEOUT,
                     env={END_ENV: exempt or ""})
    if code != 0:
        said.append("git commit failed: %s" % out)
        return False, "\n".join(said)
    _note(root, before)
    said.append("committed: %s" % (message.splitlines() or [""])[0])
    return True, "\n".join(said)


# The commits `commit` made, one sha a line, in the git common directory: a
# board push (`push(board=True)`, `sync.Sync`) publishes only these, never a
# commit the owner made and has not pushed. Kept to the newest LEDGER_KEEP.
LEDGER = "board-commits"
LEDGER_KEEP = 2000


def _ledger(root):
    code, out = _git(root, "rev-parse", "--git-common-dir")
    if code != 0 or not out:
        return None
    return os.path.join(os.path.abspath(os.path.join(root, out)), LEDGER)


def _note(root, before):
    """Add the commit `commit` just made on `before` (HEAD's sha then, ""
    when unborn) to the ledger. Noted only when HEAD's parent is `before`:
    a commit of the owner's landing just after ours is never taken for
    ours, and ours then goes unnoted, which only refuses a board push."""
    path = _ledger(root)
    code, out = _git(root, "log", "-1", "--format=%H %P", "HEAD")
    if path is None or code != 0 or not out:
        return
    sha, _, parents = out.partition(" ")
    if parents.split()[:1] != before.split()[:1]:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(sha + "\n")
        with open(path, "r", encoding="utf-8") as fh:
            kept = fh.read().splitlines()
        if len(kept) > 2 * LEDGER_KEEP:
            tmp = "%s.%d" % (path, os.getpid())
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write("\n".join(kept[-LEDGER_KEEP:]) + "\n")
            os.replace(tmp, path)
    except OSError:
        pass


def foreign(root, base, tip="HEAD"):
    """`["<sha12> <subject>", ...]`: the commits in `base..tip` the board
    did not make (`commit`'s ledger), oldest first. Merges are not listed;
    what they bring from a branch of the owner's is. None when git cannot
    say, which a board push takes as a refusal."""
    code, out = _git(root, "log", "--no-merges", "--reverse",
                     "--format=%H %s", "%s..%s" % (base, tip))
    if code != 0:
        return None
    path = _ledger(root)
    made = set()
    try:
        with open(path or "", "r", encoding="utf-8") as fh:
            made = set(l.strip() for l in fh if l.strip())
    except OSError:
        pass
    out = [l.partition(" ") for l in out.splitlines() if l.strip()]
    return ["%s %s" % (sha[:12], subj) for sha, _, subj in out
            if sha not in made]


# What a board push or the sync thread says when HEAD holds unpushed commits
# the board did not make: they are the owner's to publish, and origin is
# public.
FOREIGN = "skipped: unpushed commits of your own"


def _foreign_said(mine):
    return "%s (%s%s); push them yourself and the board's go with them" % (
        FOREIGN, "; ".join(mine[:3]),
        " and %d more" % (len(mine) - 3) if len(mine) > 3 else "")


def push(root, timeout=NET_TIMEOUT, board=False):
    """Push the current branch to origin. `(ok, said)`. Never forced.

    With an upstream: fetch it, merge it in when it is ahead (`merge_in`: a
    merge, so nothing committed here is rewritten, made around uncommitted
    work, which git protects), then push. A merge refused or conflicting
    pushes nothing and leaves everything here as it was. With no upstream:
    `push -u`.

    `board`, for a push nobody typed (`sessions.end`, `sync.Sync`): only main
    with an upstream, and only when every unpushed commit is one `commit`
    made (`foreign`); otherwise nothing is merged or pushed (`FOREIGN`). The
    sha checked last is the sha pushed, so a commit landing meanwhile stays.
    """
    code, _ = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return True, "committed locally; no 'origin' remote to push to"
    code, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or branch == "HEAD":
        return False, "HEAD is detached, so there is no branch to push"
    code, up = _git(root, "rev-parse", "--abbrev-ref", "@{upstream}")
    if board and (branch != MAIN or code != 0 or up != "origin/" + MAIN):
        return False, ("not pushed: HEAD is on %s, and the board pushes only "
                       "%s tracking origin/%s" % (branch, MAIN, MAIN))
    said = []
    if code == 0 and up:
        _, ahead = _git(root, "rev-list", "--count", "@{upstream}..HEAD")
        if ahead.strip() == "0":
            return True, "already up to date"
        code, out = _git(root, "fetch", "origin", branch, timeout=timeout)
        if code != 0:
            return False, ("could not fetch origin/%s, so nothing was pushed:\n%s"
                           % (branch, "\n".join(out.splitlines()[-5:])))
        if board:
            mine = foreign(root, "@{upstream}")
            if mine is None:
                return False, "not pushed: git could not list what is unpushed"
            if mine:
                return False, "not pushed: " + _foreign_said(mine)
        _, behind = _git(root, "rev-list", "--count", "HEAD..@{upstream}")
        if behind.strip() not in ("", "0"):
            _, theirs = _git(root, "rev-parse", "--verify", "@{upstream}")
            ok, why = merge_in(root, theirs, up, timeout=timeout)
            if not ok:
                return False, ("%s is ahead and was not merged in, so nothing "
                               "was pushed: %s" % (up, why))
            said.append(why)
        if board:
            # The sha checked is the sha pushed: a commit of the owner's
            # landing after the check (or the merge) is never published.
            code, tip = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
            mine = foreign(root, "@{upstream}", tip) if code == 0 else None
            if mine is None:
                return False, "not pushed: git could not list what is unpushed"
            if mine:
                said.append("not pushed: " + _foreign_said(mine))
                return False, "\n".join(said)
            code, out = _git(root, "push", "origin",
                             "%s:refs/heads/%s" % (tip, MAIN), timeout=timeout)
        # Named, so `push.default` cannot make it push nothing or more.
        elif up == "origin/" + branch:
            code, out = _git(root, "push", "origin", branch, timeout=timeout)
        else:
            code, out = _git(root, "push", timeout=timeout)
    else:
        code, out = _git(root, "push", "-u", "origin", branch, timeout=timeout)
    if code != 0:
        said.append("push failed:\n%s" % "\n".join(out.splitlines()[-5:]))
        return False, "\n".join(said)
    said.append("pushed %s to origin" % branch)
    return True, "\n".join(said)


# What `merge_in` says while anything is staged: git refuses a true merge
# then, and what is staged is the owner's.
STAGED = "skipped: staged changes"


def _is_build(path):
    """Generated output, where a conflict keeps this machine's side."""
    return path.startswith("build/") or "/build/" in path


def merge_in(root, theirs, label=None, timeout=NET_TIMEOUT):
    """Merge commit `theirs` into HEAD. `(ok, said)`. Never raises.

    The merge is tested and made without touching the working tree: `git
    merge-tree --write-tree` writes the merged tree, `commit-tree` makes the
    merge commit, and a fast-forward to it moves HEAD, the index and the
    files. Git refuses that fast-forward where an uncommitted change, an
    untracked file or an ignored one (`--no-overwrite-ignore`: data folders
    are ignored) overlaps what the merge brings, and then nothing here
    changes. No merge is ever left standing and none is ever aborted, so
    uncommitted work is never reset.

    Refused, changing nothing: during an operation in progress (rebase,
    merge, ...), on a detached HEAD, with unresolved conflicts in the index,
    while anything is staged (`STAGED`), and
    where the merge conflicts outside generated `build/` output. A conflict
    only there keeps this machine's side.
    """
    label = label or (theirs or "")[:12]
    busy = worktree.busy_reason(root)
    if busy:
        return False, "not merged: %s here, so it is left exactly as it is" % busy
    code, branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if code != 0:
        return False, "not merged: HEAD is detached"
    code, head = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if code != 0:
        return False, "not merged: HEAD has no commit"
    code, them = _git(root, "rev-parse", "--verify", "--quiet",
                      "%s^{commit}" % theirs)
    if code != 0:
        return False, "not merged: %s is not a commit here" % label
    if _git(root, "merge-base", "--is-ancestor", them, head)[0] == 0:
        return True, "already holds %s" % label
    code, out = _git(root, "ls-files", "--unmerged")
    if code != 0 or out:
        return False, ("not merged: the index holds unresolved conflicts; "
                       "resolve them first" if code == 0 else
                       "not merged: git could not read the index")
    code, _ = _git(root, "diff", "--cached", "--quiet")
    if code == 1:
        return False, STAGED
    if code != 0:
        return False, "not merged: git could not read the index"
    target = them
    kept = False
    if _git(root, "merge-base", "--is-ancestor", head, them)[0] != 0:
        tree, conflicts, err = _merge_tree(root, head, them)
        if err:
            return False, "not merged: git could not test the merge: %s" % err
        if conflicts:
            real = [f for f in conflicts if not _is_build(f)]
            if real:
                return False, ("not merged: it conflicts outside build output; "
                               "merge by hand:\n" + "\n".join(real))
            tree, conflicts, err = _merge_tree(root, head, them, ours=True)
            if err or conflicts:
                return False, ("not merged: the build output conflicts and "
                               "could not keep this machine's copy: %s"
                               % (err or ", ".join(conflicts)))
            kept = True
        target, err = _made(root, tree, head, them, "Merge %s into %s"
                            % (label, branch))
        if err:
            return False, "not merged: git commit-tree failed: %s" % err
    code, out = _git(root, "merge", "--ff-only", "--no-autostash",
                     "--no-overwrite-ignore", "--quiet", target)
    if code != 0:
        last = [l for l in out.splitlines() if l.strip()]
        return False, ("git refused to bring %s in, so nothing here changed: %s"
                       % (label, " ".join(l.strip() for l in last[:8])
                          or "merge refused"))
    said = ["merged %s" % label + ("; kept this machine's build output"
                                   if kept else "")]
    moved = _vendor_follow(root, head, target, timeout)
    if moved:
        said.append(moved)
    return True, "\n".join(said)


# The last merge commit `merge_in` made, by what it was made of: while git
# refuses its fast-forward (an overlap with uncommitted or ignored work) the
# sync thread retries every pass, and reuses that commit instead of leaving
# a new unreachable one each time.
_last_made = (None, None)


def _made(root, tree, head, them, message):
    """`(sha, error)` of a merge commit of `tree` on `head` and `them`."""
    global _last_made
    key = (os.path.realpath(root), tree, head, them, message)
    made, sha = _last_made
    if made == key and _git(root, "cat-file", "-e",
                            "%s^{commit}" % sha)[0] == 0:
        return sha, None
    code, out = _git(root, "commit-tree", tree, "-p", head, "-p", them,
                     "-m", message)
    if code != 0:
        return None, why(out, "commit-tree failed (%d)" % code)
    _last_made = (key, out)
    return out, None


def _merge_tree(root, head, them, ours=False):
    """`(tree, conflicted paths, error)` of merging `them` into `head`, as
    `git merge-tree --write-tree` finds it: it writes objects only, never
    the working tree, the index or a ref."""
    args = ["merge-tree", "--write-tree", "--name-only", "--no-messages"]
    if ours:
        args += ["-X", "ours"]
    code, out = _git(root, *(args + [head, them]))
    lines = out.splitlines()
    if code == 129 or "usage: git merge-tree" in out:
        return None, [], ("this git is too old to test a merge without touching "
                          "the tree (merge-tree --write-tree needs 2.38, with "
                          "-X 2.40)")
    if code not in (0, 1) or not lines:
        return None, [], why(out, "merge-tree failed (%d)" % code)
    tree = lines[0].strip()
    if not re.match(r"^[0-9a-f]{40,64}$", tree):
        return None, [], tree or "merge-tree wrote no tree"
    return tree, ([] if code == 0 else _lines("\n".join(lines[1:]))), ""


def save(root, paths, message, refuse=None):
    """`commit`, then `push` when the commit did not fail. `(ok, said)`."""
    ok, said = commit(root, paths, message, refuse=refuse)
    if not ok:
        return False, said
    ok, pushed = push(root)
    return ok, "%s\n%s" % (said, pushed)


def _vendor_moved(root, before, after):
    """True when a gitlink under `vendor/` differs between two commits."""
    code, out = _git(root, "diff", "--raw", "--no-renames", before, after,
                     "--", "vendor")
    if code != 0:
        return False
    for line in out.splitlines():
        modes = line.split()[:2]
        if any(m.lstrip(":") == "160000" for m in modes):
            return True
    return False


# What `scripts/setup.sh` builds a subject's environment from, at the
# subject's root; the NESTED ones count one directory down too, where setup
# finds their markers (`toolplan.marker_dirs`). One a pull moved leaves that
# environment stale.
NESTED = ("mise.toml", "mise.lock", "Cargo.lock", "pubspec.lock", "build.zig.zon")
LOCKFILES = ("uv.lock", "go.sum", "lake-manifest.json", "lean-toolchain") + NESTED


def lockfiles_moved(root, before, after):
    """The ids (`<parent>/<slug>`) of the subjects still in `root` whose
    lockfile differs between two commits, sorted; [] when nothing moved."""
    from tutorboard import subjects, toolplan                # local: a cycle
    if not before or not after or before == after:
        return []
    code, out = _git(root, "diff", "--name-only", "--no-renames", before, after)
    if code != 0:
        return []
    parents = set(p for p, _ in subjects.DIRS)
    moved = set()
    for path in out.splitlines():
        parts = path.split("/")
        if len(parts) == 3:
            hit = parts[2] in LOCKFILES
        elif len(parts) == 4:
            hit = (parts[3] in NESTED and not parts[2].startswith(".")
                   and parts[2] not in toolplan.SKIP)
        else:
            hit = False
        if (hit and parts[0] in parents
                and os.path.isdir(os.path.join(root, parts[0], parts[1]))):
            moved.add("%s/%s" % (parts[0], parts[1]))
    return sorted(moved)


def pull(root, quiet=False, timeout=60, say=None):
    """Fast-forward `root` to its upstream. True when it ran, False when it was
    refused or failed, None where there is nothing to pull (no repository, no
    origin). Never raises.

    Refused, changing nothing, during a rebase, merge, cherry-pick, revert or
    bisect and on a detached HEAD. A pull that moved a gitlink under `vendor/`
    then runs `git submodule update --init -- vendor`, so this machine's vendor
    checkouts stay clean; nothing here bumps a vendor pointer.

    `timeout` bounds the pull. `say`, where given, hears every line `quiet`
    would otherwise drop.
    """
    def tell(msg):
        if say is not None:
            say(msg.strip())
        elif not quiet:
            print(msg)
    if not worktree.git_dir(root):
        return None
    busy = worktree.busy_reason(root)
    if busy:
        tell("  not synced: %s here, so the repository is left exactly as it is"
             % busy)
        return False
    # A lock a killed git left behind stops a pull as surely as a commit; one
    # somebody is holding is left, and the pull below fails and says so.
    cleared = worktree.clear_stale_lock(root)
    if cleared:
        tell("  " + cleared)
    code, _ = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return None
    _, before = _git(root, "rev-parse", "HEAD")
    # `pull --ff-only`, in its two halves, so the merge can refuse to
    # overwrite an ignored file (data folders are ignored); pull cannot.
    code, out = _git(root, "fetch", "--quiet", timeout=timeout)
    if code in (124, 127):
        tell("  could not reach the remote; working with what is here")
        return False
    if code == 0:
        code, out = _git(root, "merge", "--ff-only", "--no-autostash",
                         "--no-overwrite-ignore", "--quiet", "@{upstream}",
                         timeout=timeout)
    if code != 0:
        tell("  not synced: %s" % why(out, "pull failed"))
        if say is None:
            tell("  the session will start anyway, on what is here")
        return False
    _, after = _git(root, "rev-parse", "HEAD")
    if before != after:
        _, n = _git(root, "rev-list", "--count", "%s..%s" % (before, after))
        tell("  pulled %s commit(s) from another machine" % n)
        moved = _vendor_follow(root, before, after, timeout)
        if moved:
            tell("  " + moved)
    return True


def _vendor_follow(root, before, after, timeout):
    """Where a gitlink under `vendor/` moved between two commits, run `git
    submodule update --init -- vendor`, so the vendor checkouts stay clean.
    The sentence to say, or ""."""
    if not _vendor_moved(root, before, after):
        return ""
    code, out = _git(root, "submodule", "update", "--init", "--", "vendor",
                     timeout=max(timeout, NET_TIMEOUT))
    if code != 0:
        last = out.splitlines()
        return "vendor checkouts not updated: %s" % (
            last[-1] if last else "submodule update failed")
    return "vendor checkouts moved to the pulled pointers"


# ai-config is the one private repository nested inside Atlas and ignored by
# it. bootstrap.sh carries the same URL.
AI_CONFIG = "ai-config"
AI_CONFIG_URL = "https://github.com/Pirate-Hunter-Zoro/ai-config.git"

# How often the ear moves an existing ai-config forward. Atlas's pull never
# does, because Atlas ignores it, and a fetch every 20 s pass is one more round
# trip for a repository that changes a few times a week.
PRIVATE_EVERY = 300
PRIVATE_STAMP = "ai-config-pull.json"
# install.sh's own bound: it links files and copies a few units.
PRIVATE_LINK_TIMEOUT = 180


def sync_private(base, state_dir, now=None, every=PRIVATE_EVERY, say=None,
                 run=subprocess.run, timeout=60):
    """Fast-forward `base`'s ai-config when it is due, then relink it if it moved.

    None when there is no ai-config repository or the last try was under
    `every` seconds ago. Otherwise `{"pulled": True|False|None, "moved": bool,
    "linked": True|False|None, "why": str}`: `pulled` is `pull`'s answer (False
    for the same refusals -- a merge in progress, a detached HEAD, local edits
    git will not carry; None when ai-config has no origin to pull from);
    `linked` None when nothing moved, else whether `scripts/install.sh` ran
    clean, which is what puts a new file or link in place. The time of each try
    is kept in `state_dir/PRIVATE_STAMP`, so a restarted server waits out the
    same interval. `say` hears a pull that moved and a failure, nothing else.
    Never raises on git or the script.
    """
    import time
    repo = os.path.join(base, AI_CONFIG)
    if not os.path.exists(os.path.join(repo, ".git")):
        return None
    now = time.time() if now is None else now
    stamp = os.path.join(state_dir, PRIVATE_STAMP)
    try:
        with open(stamp, encoding="utf-8") as fh:
            last = float(json.load(fh).get("at") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        last = 0.0
    if now - last < every:
        return None

    _, before = _git(repo, "rev-parse", "HEAD")
    said = []
    ok = pull(repo, quiet=True, timeout=timeout, say=said.append)
    _, after = _git(repo, "rev-parse", "HEAD")
    moved = ok is True and before != after
    rec = {"pulled": ok, "moved": moved, "linked": None,
           "why": "" if ok is True else "no origin" if ok is None
           else (said[-1] if said else "pull refused")}
    if moved:
        script = os.path.join(repo, "scripts", "install.sh")
        try:
            p = run(["bash", script], cwd=repo, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True,
                    timeout=PRIVATE_LINK_TIMEOUT,
                    env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
            rec["linked"] = p.returncode == 0
        except (OSError, subprocess.SubprocessError):
            rec["linked"] = False
    try:
        os.makedirs(state_dir, exist_ok=True)
        tmp = stamp + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(dict(rec, at=now, head=after), fh)
        os.replace(tmp, stamp)
    except OSError:
        pass
    if say is not None:
        if moved:
            say("ai-config: moved to %s%s" % (
                after[:12], "" if rec["linked"] else
                ", but scripts/install.sh failed; run it by hand"))
        elif ok is False:
            say("ai-config: not moved forward: %s" % rec["why"])
    return rec


def adopt_private(base, quiet=True, run=subprocess.run):
    """Clone or adopt ai-config when this checkout lacks its repository,
    through `bootstrap.sh --private-only`. True if it ran."""
    if os.path.exists(os.path.join(base, AI_CONFIG, ".git")):
        return False
    script = os.path.join(base, "board", "bootstrap.sh")
    if not os.path.isfile(script):
        return False
    try:
        p = run(["bash", script, "--private-only"], cwd=base,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=600,
                env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.SubprocessError):
        return False
    if not quiet:
        print((p.stdout or "").rstrip())
    return True


def main(argv=None):
    """`save-and-push.sh "message" -- <paths>`: commit the named paths of the
    repository the working directory is in, then push. Paths are relative to
    that repository's root. Exit 0 on success or nothing to commit."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv or argv.index("--") > 1 or argv[-1] == "--":
        print('usage: save-and-push.sh ["message"] -- <path>...  '
              "(a commit carries named paths only)")
        return 2
    cut = argv.index("--")
    paths = argv[cut + 1:]
    code, top = _git(os.getcwd(), "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        print("not a git repository: %s" % os.getcwd())
        return 1
    message = argv[0] if cut == 1 and argv[0] else save_message(paths)
    ok, said = save(top, paths, message)
    print(said)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
