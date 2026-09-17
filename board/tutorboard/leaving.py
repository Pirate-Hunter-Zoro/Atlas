"""What is about to leave this machine, and whether any of it may not.

A push from this tool is unattended. `board finish` raises the offer, the tutor
may push on its own, and a mission can be told to ship itself — so the last
thing between a commit and a public remote is a machine check, and there was
none.

WHAT IS ACTUALLY AT RISK, and it is one step past what git already guards.
`research/PSYCH-ASR/.gitignore` keeps the fenced directory out of the index and
`test/tracked.py` audits every tracked file, so **a diff cannot contain a phi
FILE**. A diff can contain phi CONTENT: a test fixture cut out of a transcript,
a hard-coded example, a docstring quoting a span — written by the one assistant
that is allowed to read that directory, and pushed by a turn that is not.

`ai-config/policy/phi.py` already answers this question and nothing called it.
`names_phi` is the policy, it is owned by the lab rather than by this tool, and
it is loaded from the repository rather than copied in here: a second copy of a
rule is a rule that goes quietly false on one side. A repository with no policy
file refuses nothing — this is a check that the lab's own tree switches on by
having one, not a promise this module makes on its own.

WHAT IT CATCHES, SAID PLAINLY, because a guard that is believed to do more than
it does is worse than none. `names_phi` matches the fenced directory by name,
the old data tree, and the artifact shapes — `.rttm`, `.diarized.json`,
`.transcript.txt`, session media. It is a regex: it catches a diff that REACHES
for session content or carries a piece of one with its shape still on it. A bare
sentence of dialogue with no path and no extension around it is not catchable
this way, and pretending otherwise is the failure mode. That is the other half
of why the ship turn is a hosted assistant reading the diff: the machine check
has no judgement in it, which is exactly what lets it run unattended, and the
turn has judgement, which is what covers what a regex cannot see.

PER FILE, BY THE WORKSPACE IT IS IN, and that is the decision this module
exists to hold. A push here commits the whole repository, so "is the pushing
workspace fenced" is the wrong question — a mission's fixture in `PSYCH-ASR`
would go out under a push from anywhere. Checking EVERYTHING was the
alternative, and it is wrong in the other direction and would have been found
out immediately: this file, the fence's own documentation and `HANDOFF.md` all
name `phi/` in prose, so a check over every changed line refuses the commit that
documents the check. Prose about a fence is not a hole in one.

So each changed path is looked up against the workspaces that actually hold a
fence — `fenced.holds`, cached, already asked on every payload — and only those
files are read. In this repository that is one workspace, so an ordinary push
costs one `git status` and nothing else.

THE REFUSAL NAMES THE FILE. `worktree.busy_reason` is the shape and the reason
is the same: this runs where nobody is reading a terminal, so it says what is in
the way, changes nothing, and leaves the sentence somewhere the board can paint
it. A person who looks and disagrees pushes with `--anyway`, which is a human
decision and is recorded as one.
"""

import importlib.util
import os
import subprocess

from . import atlas, fenced


POLICY = os.path.join("ai-config", "policy", "phi.py")

# How much of one file is read. A fixture that carries a transcript carries it in
# the first few kilobytes; a megabyte of generated output is not what this is
# looking for and reading it on every push is a cost paid for nothing.
READ_BYTES = 200000

# How many files are named in one refusal. The point is to be actionable, and a
# list of forty paths on a tablet is not.
NAME_MOST = 6

_POLICY = {"root": None, "fn": None}


def policy(root=None):
    """`names_phi` out of the repository's own policy file, or None.

    Loaded by path rather than imported: `ai-config` is not a module name, and
    the policy is deliberately not part of this tool. Cached per repository
    root, because this is asked on every push and the answer is a file on disk.
    """
    base = root or atlas.root() or ""
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
            # A policy file that will not load is not a reason to stop somebody
            # pushing. It IS a reason to say so, which `reason` does.
            fn = None
    _POLICY["root"] = base
    _POLICY["fn"] = fn if callable(fn) else None
    return _POLICY["fn"]


def fenced_roots(base=None):
    """Every workspace in the repository that holds a fence, as absolute paths."""
    out = []
    try:
        for w in atlas.workspaces(base):
            if fenced.holds(w["root"]):
                out.append(os.path.realpath(w["root"]))
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
    """Every path a push from here would commit, relative to the repository.

    `git status --porcelain -uall`, because the risk is a file nothing has ever
    tracked -- a fixture written an hour ago by the assistant that could read the
    directory it came out of. `git diff` cannot see one of those at all.
    """
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
    """The text of this path that a push would add, bounded.

    A tracked file's ADDED lines, so rewriting a line that was already committed
    is not read again and a file's whole history does not have to be. An
    untracked one has no diff, so it is read: all of it is new.
    """
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
    """Why this push must not go, or None if there is nothing in the way.

    Never raises: a check that throws on the way to a push is a push that does
    not happen for a reason nobody can read. Where the policy file is missing
    this is None and says so nowhere, which is the honest answer — the rule
    belongs to the repository and a repository without one is not making a
    promise this module can keep for it.
    """
    try:
        return _reason(root, base)
    except Exception:                                        # noqa: BLE001
        return None


def _reason(root, base=None):
    names_phi = policy(base)
    if not names_phi:
        return None
    guarded = fenced_roots(base)
    if not guarded:
        return None
    top = _top(root)
    hit = []
    for path in pending(root):
        full = os.path.realpath(os.path.join(top, path))
        if not any(full == g or full.startswith(g + os.sep) for g in guarded):
            continue
        # The PATH first, because a fixture named after the session it came out
        # of has already said what it is.
        if names_phi(path):
            hit.append(path)
            continue
        text = (_added_lines(top, path) if _tracked(top, path)
                else _whole(top, path))
        if text and names_phi(text):
            hit.append(path)
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
