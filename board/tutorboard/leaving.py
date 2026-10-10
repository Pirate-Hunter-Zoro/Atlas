"""What is about to leave this machine, and whether any of it may not.

A push from this tool is unattended, so this is the machine check before a
public remote. Git already keeps phi files out of the index; this catches phi
content (a fixture cut from a transcript) using the lab's own
`ai-config/policy/phi.py` `names_phi`, loaded from the repository, never
copied. `names_phi` is a regex over paths and artifact shapes, so a bare
sentence of dialogue is not catchable here.

Checked per file, by the workspace it is in: only files in workspaces that
hold a fence (`fenced.holds`) are read, because prose about a fence is not a
hole in one. A refusal names the file; `--anyway` is the human override.

The constraint: a workspace with a fence and no loadable policy is refused
outright, because a guard that switches off when its rule is missing cannot
be trusted.
"""

import importlib.util
import os
import subprocess

from . import fenced, subjects


POLICY = os.path.join("ai-config", "policy", "phi.py")

# Bytes read per file: a transcript fixture shows itself early.
READ_BYTES = 200000

# Files named per refusal, to stay readable on a tablet.
NAME_MOST = 6

_POLICY = {"root": None, "fn": None}


def policy(root=None):
    """`names_phi` from the repository's policy file, or None. Loaded by path
    (`ai-config` is no module name), cached per root."""
    base = root or subjects.root() or ""
    if _POLICY["root"] == base:
        return _POLICY["fn"]
    fn = None
    path = os.path.join(base, POLICY) if base else ""
    if path and os.path.isfile(path):
        try:
            spec = importlib.util.spec_from_file_location("atlas_phi_policy", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, "names_phi", None)
        except Exception:                                    # noqa: BLE001
            # Not loading is reported by `reason`, not raised.
            fn = None
    _POLICY["root"] = base
    _POLICY["fn"] = fn if callable(fn) else None
    return _POLICY["fn"]


def fenced_roots(base=None):
    """Every workspace in the repository that holds a fence, as absolute paths."""
    out = []
    try:
        for where in subjects.roots(base):
            if fenced.holds(where):
                out.append(os.path.realpath(where))
    except Exception:                                        # noqa: BLE001
        return []
    return out


def _git(args, cwd, timeout=30):
    try:
        p = subprocess.run(["git", "--no-optional-locks"] + args, cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def _top(root):
    said = _git(["rev-parse", "--show-toplevel"], root, timeout=10)
    return (said or "").strip() or root


def pending(root):
    """Every path a push from here would commit, relative to the repository:
    `git status --porcelain -uall`, because a new untracked fixture is the
    risk and `git diff` cannot see it."""
    out = _git(["status", "--porcelain", "-uall", "-z"], _top(root))
    if out is None:
        return []
    names = []
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        rec = parts[i]
        i += 1
        if len(rec) < 4:
            continue
        code, path = rec[:2], rec[3:]
        if code[0] == "R" or code[1] == "R":
            # A rename's record is followed by its source in the next field.
            i += 1
        if not path or code == "!!":
            continue
        names.append(path)
    return names


def _added_lines(top, path):
    """The text of this path a push would add, bounded: a tracked file's added
    lines, an untracked file whole."""
    diff = _git(["diff", "HEAD", "-U0", "--", path], top) or ""
    return "\n".join(l[1:] for l in diff.splitlines()
                     if l.startswith("+") and not l.startswith("+++"))


def _whole(top, path):
    try:
        with open(os.path.join(top, path), "r", encoding="utf-8",
                  errors="replace") as fh:
            return fh.read(READ_BYTES)
    except OSError:
        return ""


def _tracked(top, path):
    return _git(["ls-files", "--error-unmatch", "--", path], top) is not None


def reason(root, base=None):
    """Why this push must not go, or None. Never raises. A fence without a
    loadable policy is `no_policy`'s refusal."""
    try:
        return _reason(root, base)
    except Exception:                                        # noqa: BLE001
        return None


def no_policy(guarded):
    """The refusal for a fence with no policy to check what would leave it."""
    return ("nothing was committed: %s hold%s a fenced directory, and the PHI "
            "policy %s is missing or will not load, so nothing can check what "
            "would leave. Restore ai-config (bash board/bootstrap.sh) and try "
            "again."
            % (", ".join(os.path.basename(g) for g in guarded[:NAME_MOST]),
               "s" if len(guarded) == 1 else "", POLICY))


def probe(rel, base=None):
    """`(policy, fence)` for one repository-relative path, `phi-probe.sh`'s
    question: does the policy name it (None if it will not load), and which
    fenced name refuses it in its subject (`fenced.refused_in`). Nothing on
    disk is read."""
    base = base or subjects.root() or ""
    rel = str(rel or "").replace("\\", "/")
    names_phi = policy(base)
    said = bool(names_phi(rel)) if names_phi else None
    if os.path.isabs(rel) or not rel:
        return said, fenced.refused_in(base, rel or base)
    subject = os.path.join(base, *rel.split("/")[:2])
    return said, fenced.refused_in(subject, os.path.join(base, rel))


def refused(root, paths, base=None):
    """Which of these repository-relative paths `reason`'s rule refuses: `[]`
    without a fence, `no_policy`'s string where the policy will not load.
    Never raises."""
    try:
        guarded = fenced_roots(base)
        if not guarded:
            return []
        names_phi = policy(base)
        if not names_phi:
            return no_policy(guarded)
        return _refused(root, paths, names_phi, guarded)
    except Exception:                                        # noqa: BLE001
        return "nothing was committed: the PHI check over these paths failed."


def _refused(root, paths, names_phi, guarded):
    top = _top(root)
    hit = []
    for path in paths:
        full = os.path.realpath(os.path.join(top, path))
        if not any(full == g or full.startswith(g + os.sep) for g in guarded):
            continue
        # The path first: a fixture named after its session already says it.
        if names_phi(path):
            hit.append(path)
            continue
        text = (_added_lines(top, path) if _tracked(top, path)
                else _whole(top, path))
        if text and names_phi(text):
            hit.append(path)
    return hit


def _reason(root, base=None):
    guarded = fenced_roots(base)
    if not guarded:
        return None
    if not policy(base):
        return no_policy(guarded)
    hit = refused(root, pending(root), base)
    if isinstance(hit, str):
        return hit
    if not hit:
        return None
    shown = hit[:NAME_MOST]
    more = len(hit) - len(shown)
    return ("nothing was committed: %s reach%s for session content, which is "
            "PHI and must not go to a remote — %s%s. Nothing has been lost. "
            "Look at %s; if it is genuinely not session content, push with "
            "--anyway."
            % ("one file" if len(hit) == 1 else "%d files" % len(hit),
               "es" if len(hit) == 1 else "",
               ", ".join(shown),
               " and %d more" % more if more else "",
               "it" if len(hit) == 1 else "them"))


# ---------------------------------------------------------------------------
# THE OTHER QUESTION GIT ANSWERS: is this file safe to let something overwrite?
# ---------------------------------------------------------------------------
# Is this file safe to overwrite? An overhaul is refused unless its source is
# committed as it stands, so the overhaul is one revertible diff; never
# committed on the owner's behalf. Here because `pending` is the one porcelain
# parser; `worktree.py` stays git-free.
def uncommitted(root, rel):
    """Is this path, relative to `root`, something a commit would still carry?
    False when committed, and False outside any repository (no undo to
    protect)."""
    if not rel:
        return False
    top = _top(root)
    try:
        mine = os.path.relpath(os.path.realpath(os.path.join(root, rel)),
                               os.path.realpath(top))
    except ValueError:
        return False
    if not git_here(root):
        return False
    mine = mine.replace(os.sep, "/")
    for path in pending(root):
        if path.replace(os.sep, "/") == mine:
            return True
    return False


def git_here(root):
    """Is there a repository over this path at all?"""
    return _git(["rev-parse", "--git-dir"], root, timeout=10) is not None
