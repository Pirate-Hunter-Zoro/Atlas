"""What this public repository may not carry, asked of a list of paths.

Every commit to Atlas is public and git remembers, so this is checked before
anything is written: `.githooks/pre-commit` asks `check` of the staged paths
(plus a tutor turn's refusals and a coding session's held paths; see `main`),
and `board/test/tracked.py` asks it of the whole index. Third-party material inside a course is `other_peoples_work`. Messages say
what a path is, so the reader can judge the refusal.

The constraint: standard library only.
"""

import os
import subprocess
import sys

from . import paths


# Far below GitHub's limits on purpose: this stops a habit.
MAX_BYTES = 25 * 1024 * 1024

# Audio and video, and the transcripts cut from them: recordings stay on disk.
AUDIO_SUFFIXES = (".m4a", ".wav", ".mp3", ".flac", ".mp4", ".mov",
                  ".rttm", ".srt", ".vtt")

# Job output a command regenerates and nobody reads.
ARTIFACT_SUFFIXES = (".joblib", ".pkl", ".pickle", ".ckpt", ".pt", ".pth",
                     ".safetensors", ".gguf", ".h5", ".parquet")

def other_peoples_work(rel):
    """What third-party material this path is, or None.

    Matched on DIRECTORY components, so `notes/lectures.md` is the owner's
    file and `lectures/deck.pdf` is not. The `.gitkeep` holding an empty
    directory open is the one exemption.
    """
    low = rel.lower()
    parts = low.split("/")
    dirs, base = parts[:-1], parts[-1]
    if base == ".gitkeep":
        return None
    if "references" in dirs and low.endswith(".pdf"):
        return "a reference library PDF"
    if "textbook" in dirs:
        return "a set textbook, or a piece of one"
    if "reading" in dirs:
        return "an excerpt cut out of a set textbook"
    if "lectures" in dirs:
        return "a professor's lecture slide deck"
    # Scoped to courses, as the ignore rule is: `assignment*` elsewhere is as
    # likely to be the owner's code as anybody's sheet.
    if parts[0] == "courses" and any(p.startswith("assignment")
                                     for p in parts[1:]):
        return "an assignment sheet as it was distributed"
    return None


def problems(rel, size=0):
    """Every rule this one repository-relative path breaks, as sentences."""
    out = []
    low = rel.lower()
    parts = low.split("/")
    dirs = parts[:-1]
    base = parts[-1]

    if size and size > MAX_BYTES:
        out.append("%s is %d MB. Nothing tracked here may be over %d MB: a file "
                   "that big is output, and output lives outside the tree."
                   % (rel, size // (1024 * 1024), MAX_BYTES // (1024 * 1024)))
    if low.endswith(AUDIO_SUFFIXES):
        out.append("%s is audio, video or a transcript cut from one. A "
                   "recording stays on disk; nothing of that shape is tracked."
                   % rel)
    if low.endswith(ARTIFACT_SUFFIXES):
        out.append("%s is a model dump or a serialized result. It is job "
                   "output, and output lives outside the tree." % rel)
    if ".lake" in dirs:
        out.append("%s is inside Lean's .lake/, which `lake build` recreates."
                   % rel)
    if "node_modules" in dirs:
        out.append("%s is inside node_modules/." % rel)
    if "__pycache__" in dirs or low.endswith(".pyc"):
        out.append("%s is a compiled Python cache." % rel)

    what = other_peoples_work(rel)
    if what:
        out.append("%s is %s. Somebody else wrote it and this repository is "
                   "public. It stays on disk and out of git." % (rel, what))

    if parts[0] == "sessions" and len(parts) > 1:
        out.append("%s is session state. sessions/ is the Mac's own and never "
                   "tracked." % rel)
    if ".ink" in dirs:
        out.append("%s is document ink. A subject's .ink/ stays on the Mac."
                   % rel)
    if "materials" in dirs:
        out.append("%s is a material: a third-party or uploaded file, kept "
                   "on disk and never tracked." % rel)

    if base in ("settings.local.json", "settings.local.json.bak"):
        out.append("%s is a machine's own permission allowlist. It names real "
                   "paths on that machine." % rel)
    if parts[0] == "ai-config" and len(parts) > 1:
        out.append("%s is the private assistant configuration, tracked by its "
                   "own git. /ai-config/ belongs in the root .gitignore."
                   % rel)
    if base == ".env":
        out.append("%s is a .env, which holds a machine's secrets. Track a "
                   ".env.example with the keys and no values." % rel)
    if base == "keys.env" or base.endswith(("-api-key", "_api_key", ".key")):
        out.append("%s is shaped like a provider credential. Keys live in "
                   "~/.config/tutor-board/keys.env, outside the tree." % rel)
    if base == "save-and-push.sh" and low != "board/scripts/save-and-push.sh":
        out.append("%s is a second copy of save-and-push.sh. The one that runs "
                   "is board/scripts/save-and-push.sh." % rel)
    return out


def check(paths, root=None, size=None):
    """Every failure over these repository-relative paths, as sentences.

    `size(rel)` gives a path's size in bytes; by default the file's size under
    `root` on disk, and 0 where it is not there.
    """
    if size is None:
        def size(rel):
            try:
                return os.path.getsize(os.path.join(root or ".", rel))
            except OSError:
                return 0
    out = []
    for rel in paths:
        if rel:
            out.extend(problems(rel, size(rel)))
    return out


# ---------------------------------------------------------------------------
# The commit-time gate: `.githooks/pre-commit` runs `main`
# ---------------------------------------------------------------------------
def _git(args, cwd, data=None):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, input=data,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    if p.returncode != 0:
        return None
    return p.stdout


def staged(top):
    """`[(status, mode, sha, path)]` for every staged change, renames split."""
    raw = _git(["diff", "--cached", "--raw", "-z", "--no-renames",
                "--no-abbrev", "--ignore-submodules=none"], top)
    if raw is None:
        raise RuntimeError("git diff --cached failed")
    fields = raw.decode("utf-8", "replace").split("\0")
    out = []
    i = 0
    while i + 1 < len(fields):
        head, path = fields[i], fields[i + 1]
        i += 2
        if not head.startswith(":"):
            continue
        bits = head[1:].split()
        if len(bits) < 5:
            continue
        out.append((bits[4][:1], bits[1], bits[3], path))
    return out


def blob_sizes(top, entries):
    """`{path: bytes}` for each staged blob, read from the index."""
    want = [(sha, path) for status, mode, sha, path in entries
            if status != "D" and mode != "160000"]
    if not want:
        return {}
    said = _git(["cat-file", "--batch-check"], top,
                ("\n".join(sha for sha, _ in want) + "\n").encode())
    lines = (said or b"").decode("utf-8", "replace").splitlines()
    out = {}
    for (sha, path), line in zip(want, lines):
        bits = line.split()
        if len(bits) == 3 and bits[0] == sha and bits[2].isdigit():
            out[path] = int(bits[2])
    return out


def turn_refusals(top, entries):
    """What a tutor turn may not commit: RULES.md, and the deletion of a
    subject's tutorboard.json."""
    out = []
    for status, mode, sha, rel in entries:
        if os.path.basename(rel) == "RULES.md":
            out.append("%s is the owner's. A tutor turn does not commit it; "
                       "write TUTOR.md with `board memo` instead." % rel)
        elif os.path.basename(rel) == "tutorboard.json" and status == "D":
            out.append("%s is the owner's. A tutor turn does not delete it."
                       % rel)
    return out


# Where a tutor turn changes the board's own code: a worktree, never the main
# checkout, which serves the iPad live.
WORKTREES = paths.WORKTREES


def main_worktree(top):
    """Is `top` the main worktree of its repository, where `git rev-parse
    --git-dir` is `--git-common-dir`? Yes when git cannot say (fail closed)."""
    gd = _git(["rev-parse", "--git-dir"], top)
    cd = _git(["rev-parse", "--git-common-dir"], top)
    if gd is None or cd is None:
        return True
    gd = os.path.realpath(os.path.join(top, gd.decode("utf-8", "replace").strip()))
    cd = os.path.realpath(os.path.join(top, cd.decode("utf-8", "replace").strip()))
    return gd == cd


def board_refusals(top, entries):
    """A tutor turn's commit that touches `board/` in the main worktree."""
    hit = [e[3] for e in entries if e[3] == "board" or e[3].startswith("board/")]
    if not hit or not main_worktree(top):
        return []
    more = " (and %d more)" % (len(hit) - 1) if len(hit) > 1 else ""
    return ["%s%s is the board's own code, and this is the main checkout, which "
            "serves the iPad live. A tutor turn changes board/ in a git worktree "
            "under %s and merges it from there." % (hit[0], more, WORKTREES)]


def _common(path):
    said = _git(["rev-parse", "--git-common-dir"], path)
    if said is None:
        return None
    return os.path.realpath(os.path.join(path, said.decode().strip()))


def gate(top, home, turn):
    """Every refusal for the commit staged in `top`, as sentences. The audit
    runs only where `top` is a checkout of `home` (the hook's repository);
    another repository using this hook (ai-config) gets only the tutor-turn
    refusals."""
    entries = staged(top)
    if not entries:
        return []
    out = []
    present = [e[3] for e in entries if e[0] != "D"]
    if _common(top) == _common(home):
        sizes = blob_sizes(top, entries)
        out.extend(check(present, top, size=lambda rel: sizes.get(rel, 0)))
        if turn:
            out.extend(board_refusals(top, entries))
    if turn:
        out.extend(turn_refusals(top, entries))
    return out


def coding_refusals(top, entries, exempt=None):
    """A commit on main in `top` that changes a file a coding session holds:
    session.json `code` of the board's sessions here (`gitops.held_paths`),
    and `board code` registrations for this checkout (`code.registrations`).
    Those files reach main through `board code <id> --end` only, which names
    its own session in `exempt` (`gitops.END_ENV`)."""
    from . import code, gitops
    held = {}
    for sid, theirs in gitops.held_paths(top).items():
        held.setdefault(sid, set()).update(theirs)
    for rec in code.registrations(top):
        held.setdefault(rec["session"], set()).update(
            p for p in rec.get("paths") or [] if isinstance(p, str) and p)
    held.pop(exempt or None, None)
    if not held:
        return []
    said = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], top)
    if said is None or said.decode("utf-8", "replace").strip() != gitops.MAIN:
        return []
    out = []
    for sid, theirs in sorted(held.items()):
        hit = sorted(e[3] for e in entries
                     if any(e[3] == h or e[3].startswith(h + "/")
                            for h in theirs))
        if hit:
            out.append("%s%s held by coding session %s: held files reach main "
                       "only through `board code %s --end`."
                       % (", ".join(hit[:6]), " and %d more" % (len(hit) - 6)
                          if len(hit) > 6 else "", sid, sid))
    return out


def main(argv=None):
    """The pre-commit hook: `python3 -m tutorboard.audit <hook's repository>`."""
    argv = sys.argv[1:] if argv is None else argv
    home = os.path.realpath(argv[0]) if argv else os.getcwd()
    top = os.getcwd()
    said = _git(["rev-parse", "--show-toplevel"], top)
    if said is not None:
        top = said.decode("utf-8", "replace").strip()
    turn = bool(os.environ.get("TUTORBOARD_TURN"))
    try:
        refusals = gate(top, home, turn)
        from . import gitops
        refusals += coding_refusals(top, staged(top),
                                    os.environ.get(gitops.END_ENV) or None)
    except Exception as exc:                                 # noqa: BLE001
        # Fail closed: a gate that cannot run has checked nothing.
        refusals = ["the commit-time gate could not run (%s: %s)."
                    % (type(exc).__name__, exc)]
    if not refusals:
        return 0
    sys.stderr.write("pre-commit: nothing was committed.\n")
    for r in refusals[:40]:
        sys.stderr.write("  - %s\n" % r)
    if len(refusals) > 40:
        sys.stderr.write("  ... and %d more\n" % (len(refusals) - 40))
    sys.stderr.write("Unstage or fix what is named and commit again.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
