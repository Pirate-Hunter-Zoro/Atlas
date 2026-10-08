"""What this public repository may not carry, asked of a list of paths.

Every commit to Atlas is public, and a file that was public for an hour has
been published: deleting it afterwards is not a fix, because git remembers.
So the rule is checked twice, by one function:

- `.githooks/pre-commit` asks `check` of the STAGED paths, before anything is
  written. It also runs `leaving.refused`, the participant-code scan and, in a
  tutor turn, the refusals for `phi`, `relay.exports` and RULES.md. See `main`.
- `board/test/tracked.py` asks `check` of the whole index on every run of the
  suite, and asks `held` which directories git must be blind to.

A course is tracked content like any subject. What inside one belongs to
somebody else -- the textbook, chapter readings, lecture decks, assignment
sheets -- is refused by `other_peoples_work`.

Each rule is here because what it refuses was found in one of the repositories
Atlas was made from. The messages say what the path is, because the person
reading one is deciding whether the refusal is right.

Relay-path code: the hook runs on the cluster's python3, which may be 3.7.
Standard library only.
"""

import json
import os
import re
import subprocess
import sys


# GitHub refuses a file over 100 MB and warns above 50. This is far under both
# on purpose: the limit that matters is the one that stops a habit.
MAX_BYTES = 25 * 1024 * 1024

# PHI by the shape of the filename: session audio and its transcripts. The
# filenames carry participant ids.
PHI_SUFFIXES = (".m4a", ".wav", ".mp3", ".flac", ".mp4", ".mov",
                ".rttm", ".srt", ".vtt")

# Job output a command regenerates and nobody reads.
ARTIFACT_SUFFIXES = (".joblib", ".pkl", ".pickle", ".ckpt", ".pt", ".pth",
                     ".safetensors", ".gguf", ".h5", ".parquet")

# The subject directories. A subject is a directory directly under one of
# these; `research` and `practice` remain until they merge into `projects`.
SUBJECT_KINDS = ("courses", "projects", "research", "practice")

# Directories that may sit inside a subject on disk and that git must never
# see, found by name up to HELD_DEPTH levels below the subject.
HELD_NAMES = ("phi", "results")
HELD_DEPTH = 3

# A participant session code: BL then three digits. Writing ABOUT the rule is
# done as "BL###", which does not match.
PARTICIPANT = re.compile(r"BL[0-9]{3}")


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
    if low.endswith(PHI_SUFFIXES):
        out.append("%s is audio or a transcript artifact. Session data is "
                   "identifiable and lives in a subject's ignored phi/; "
                   "nothing of that shape is tracked anywhere." % rel)
    if "_session" in base and any(c.isdigit() for c in base):
        out.append("%s looks like a session file named after a participant. "
                   "If it is not, rename it; if it is, it belongs in phi/."
                   % rel)
    if low.endswith(ARTIFACT_SUFFIXES):
        out.append("%s is a model dump or a serialized result. It is job "
                   "output, so it lives in its subject's ignored results/."
                   % rel)
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
                   "paths on lab storage." % rel)
    if parts[0] == "ai-config" and len(parts) > 1:
        out.append("%s is the private assistant configuration, tracked by its "
                   "own git. /ai-config/ belongs in the root .gitignore."
                   % rel)
    if base == ".env":
        out.append("%s is a .env, which names where identifiable data lives. "
                   "Track a .env.example with the keys and no values." % rel)
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
# The directories that may sit inside the tree and must stay invisible
# ---------------------------------------------------------------------------
def _dirs(path):
    """(name, is_symlink) for each directory entry here; nothing on error."""
    try:
        entries = list(os.scandir(path))
    except OSError:
        return []
    out = []
    for e in entries:
        try:
            if e.is_symlink():
                out.append((e.name, True))
            elif e.is_dir():
                out.append((e.name, False))
        except OSError:
            continue
    return sorted(out)


def held(root):
    """Every directory git must be blind to, as sorted `(rel, what)` pairs.

    Each `phi` or `results` directory up to HELD_DEPTH levels under a subject.
    The walk never enters a held directory or one fenced by name, so nothing
    inside them is listed. Nor `exports/`: that is the tracked cluster channel,
    and a `results/` inside it holds figures the relay exported on purpose.
    """
    from . import fenced
    stop = set(HELD_NAMES) | set(fenced.NEVER) | {".git", "exports"}
    out = []
    for kind in SUBJECT_KINDS:
        for subject, link in _dirs(os.path.join(root, kind)):
            if link or subject.startswith("."):
                continue
            todo = [(kind + "/" + subject, 0)]
            while todo:
                rel, depth = todo.pop()
                for name, link in _dirs(os.path.join(root, rel)):
                    here = rel + "/" + name
                    if name.lower() in HELD_NAMES:
                        out.append((here, "a subject's %s/, which never leaves "
                                    "the machine it is on" % name.lower()))
                        continue
                    if (not link and depth + 1 < HELD_DEPTH
                            and name.lower() not in stop):
                        todo.append((here, depth + 1))
    return sorted(set(out))


def exposed(root, rel, what):
    """Why git can see this held directory, or None when it cannot.

    GIT IS ASKED. `git status --porcelain --untracked-files=all` lists every
    file git would offer to add, so an empty answer is git saying it is blind
    to the tree; `git ls-files` adds anything already tracked in there. Only
    the count is reported: a filename in there may itself
    carry a participant id.
    """
    path = os.path.join(root, rel)
    if os.path.islink(path):
        return ("%s is a SYMLINK. A symlink is a tracked file standing in for "
                "%s, and it hands every reader of this public repository a map "
                "to the real thing." % (rel, what))
    if not os.path.isdir(path):
        return None
    listed = []
    for ask in (["status", "--porcelain", "--untracked-files=all", "--", rel],
                ["ls-files", "--", rel]):
        said = _git(ask, root)
        if said is None:
            return "could not ask git whether it can see %s." % rel
        listed.extend(l for l in said.decode("utf-8", "replace").split("\n")
                      if l.strip())
    if not listed:
        return None
    return ("GIT CAN SEE %s: %d path(s). It is %s, inside a public repository, "
            "so an ignore rule is all that stands between it and a push. Commit "
            "nothing until `git status --porcelain --untracked-files=all -- %s` "
            "is empty." % (rel, len(listed), what, rel))


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


def _subject(rel):
    parts = rel.split("/")
    if len(parts) > 2 and parts[0] in SUBJECT_KINDS:
        return parts[0] + "/" + parts[1]
    return None


def _json(blob):
    try:
        said = json.loads(blob.decode("utf-8")) if blob is not None else None
    except ValueError:
        return None
    return said if isinstance(said, dict) else None


def says_phi_true(top, subject):
    """Does this subject's tutorboard.json say `"phi": true`, on disk or staged."""
    rel = subject + "/tutorboard.json"
    try:
        with open(os.path.join(top, rel), "rb") as fh:
            disk = fh.read()
    except OSError:
        disk = None
    for blob in (disk, _git(["show", ":" + rel], top)):
        if (_json(blob) or {}).get("phi") is True:
            return True
    return False


def participant_codes(top, paths):
    """Where a staged path in a `"phi": true` subject carries a session code.

    The filename and the added lines are scanned. The refusal names the file
    and the line number, never the text, so the code is not printed again.
    """
    subjects = {}
    for rel in paths:
        s = _subject(rel)
        if s is not None:
            subjects.setdefault(s, []).append(rel)
    hot = [rel for s in sorted(subjects) if says_phi_true(top, s)
           for rel in subjects[s]]
    if not hot:
        return []
    out = []
    for rel in hot:
        if PARTICIPANT.search(rel):
            out.append("a staged filename carries a participant code: %s"
                       % PARTICIPANT.sub("BL###", rel))
    diff = _git(["-c", "core.quotePath=false", "diff", "--cached",
                 "--no-color", "--no-ext-diff", "-U0",
                 "--no-renames", "--"] + hot, top) or b""
    where, line = None, 0
    for text in diff.decode("utf-8", "replace").split("\n"):
        if text.startswith("+++ "):
            where = text[6:] if text.startswith("+++ b/") else None
        elif text.startswith("@@"):
            m = re.search(r"\+(\d+)", text)
            line = int(m.group(1)) if m else 0
        elif text.startswith("+") and where:
            if PARTICIPANT.search(text):
                out.append("a staged line carries a participant code: %s:%d"
                           % (PARTICIPANT.sub("BL###", where), line))
            line += 1
    return out


def turn_refusals(top, entries):
    """What a tutor turn may not commit: RULES.md, and an existing
    tutorboard.json's `phi` or `relay.exports`."""
    out = []
    missing = object()
    for status, mode, sha, rel in entries:
        if os.path.basename(rel) == "RULES.md":
            out.append("%s is the owner's. A tutor turn does not commit it; "
                       "write TUTOR.md with `board memo` instead." % rel)
            continue
        if os.path.basename(rel) != "tutorboard.json":
            continue
        before = _git(["show", "HEAD:" + rel], top)
        if before is None:
            continue                       # a new subject's file: allowed
        old = _json(before)
        new = _json(_git(["show", ":" + rel], top)) if status != "D" else {}
        if old is None or new is None:
            out.append("%s will not parse, so a tutor turn cannot show it "
                       "leaves `phi` and `relay.exports` alone." % rel)
            continue
        if old.get("phi", missing) != new.get("phi", missing):
            out.append("%s: a tutor turn may not change `phi`. That is the "
                       "owner's decision." % rel)
        if ((old.get("relay") or {}).get("exports", missing)
                != (new.get("relay") or {}).get("exports", missing)):
            out.append("%s: a tutor turn may not change `relay.exports`, "
                       "which decides what leaves the cluster." % rel)
    return out


def _common(path):
    said = _git(["rev-parse", "--git-common-dir"], path)
    if said is None:
        return None
    return os.path.realpath(os.path.join(path, said.decode().strip()))


def gate(top, home, turn):
    """Every refusal for the commit staged in `top`, as sentences.

    `home` is the repository the hook lives in. The audit, the PHI policy and
    the participant scan are about Atlas, so they run only where `top` is a
    checkout of that repository; another repository pointed at this hook (the
    private ai-config) gets only the tutor-turn refusals.
    """
    from . import leaving
    entries = staged(top)
    if not entries:
        return []
    out = []
    present = [e[3] for e in entries if e[0] != "D"]
    if _common(top) == _common(home):
        sizes = blob_sizes(top, entries)
        out.extend(check(present, top, size=lambda rel: sizes.get(rel, 0)))
        hit = leaving.refused(top, present, top)
        if isinstance(hit, str):
            out.append(hit)
        else:
            out.extend("%s reaches for session content, which is PHI and must "
                       "not go to a remote." % p for p in hit)
        out.extend(participant_codes(top, present))
    if turn:
        out.extend(turn_refusals(top, entries))
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
