"""walk.py -- what a walkthrough is held over.

A walkthrough teaches machinery that already exists: its scope is a piece of
the repository's own source, and the lesson is reading it (predict, trace,
say which branch runs). This module lists what can be named (`units`, and
`parts` for a project's top-level pieces) and resolves names against the
subject's source, then the Atlas root.

The constraint: a name from the board is checked against what is on disk
before it reaches anything, so nothing invented reaches a tutor's prompt.
"""

import os
import re
import time

from .. import fenced, subjects

# Not parts of a project: build output, dependencies, leftovers, hidden names.
PART_IGNORE = {
    "live", "node_modules", "__pycache__", "build", "dist", "target",
    "venv", ".venv", "env", "site-packages", "archive", "uploads",
    "answers", "logs", "tmp", "out", "coverage", "vendor", "textbook",
}

# How many parts a picker on a tablet is offered.
MAX_PARTS = 60

# Walkable source, by language. Documents are not machinery.
SOURCE = (".py", ".go", ".js", ".mjs", ".ts", ".jsx", ".tsx", ".R", ".r",
          ".sh", ".bash", ".lean", ".sql", ".jl", ".rs", ".c", ".h", ".cpp",
          ".hpp", ".java", ".m")

# `PART_IGNORE` plus more. `slurm_jobs` is deliberately walkable: a job script
# is machinery.
IGNORE = set(PART_IGNORE) | {"data", "test_data", "results", "notebooks",
                               "latex", "textbook", "chapters",
                               "handwritten", "transcripts", "references"}

# Empty and generated files are never offered.
MIN_BYTES = 200

# A guard for the tablet picker, well past the largest repository's count.
MAX_UNITS = 250

# A definition per language, by grep rather than a parser; every pattern is
# anchored at line start so it never says yes falsely.
DEFINITION = {
    ".py": r"^\s*(?:async\s+def|def|class)\s+%s\b",
    ".go": r"^\s*(?:func(?:\s+\([^)]*\))?|type)\s+%s\b",
    ".js": r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+%s\b",
    ".lean": r"^\s*(?:theorem|lemma|def|structure|instance)\s+%s\b",
    ".sh": r"^\s*(?:function\s+)?%s\s*\(\)",
    ".R": r"^\s*%s\s*(?:<-|=)\s*function\b",
    ".rs": r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait|impl)\s+%s\b",
}
DEFINITION[".mjs"] = DEFINITION[".ts"] = DEFINITION[".jsx"] = DEFINITION[".tsx"] = DEFINITION[".js"]
DEFINITION[".bash"] = DEFINITION[".sh"]
DEFINITION[".r"] = DEFINITION[".R"]


# A shebang counts as a declaration for a file with no extension (colibrì's
# `bin/coli*` are suffixless bash), and names the language `_has_definition`
# uses. `SCRIPT` is an unrecognised interpreter: offered, but no symbol in it
# can be verified, so it is not a `DEFINITION` key.
SCRIPT = "#!"

# Searched over the whole `#!` line; `bash` before `sh`, its substring.
INTERPRETERS = (
    ("python", ".py"),
    ("bash", ".sh"),
    ("zsh", ".sh"),
    ("Rscript", ".R"),
    ("node", ".js"),
    ("julia", ".jl"),
    ("sh", ".sh"),
)

# Read this much, so a file with no newline is never read whole.
SHEBANG_BYTES = 256


def _shebang(root, rel):
    """What a `#!` line declares this extensionless file to be: the
    extension its interpreter stands in for, `SCRIPT` for an unknown one, or
    "" for no shebang."""
    try:
        with open(os.path.join(root, rel), "rb") as fh:
            first = fh.read(SHEBANG_BYTES).split(b"\n", 1)[0]
    except OSError:
        return ""
    line = first.decode("utf-8", "replace")
    if not line.startswith(SCRIPT):
        return ""
    for word, ext in INTERPRETERS:
        if word in line:
            return ext
    return SCRIPT


def _language(root, rel):
    """What this file is, as a `SOURCE`/`DEFINITION` key: its extension, else
    its `#!` declaration, else "". One function, so `_walkable` and
    `_has_definition` agree."""
    ext = os.path.splitext(rel)[1]
    return ext if ext else _shebang(root, rel)


def _walkable(root, rel):
    """Is this path machinery somebody could be walked through? An extension
    answers first, a `#!` line for a file without one; neither is a refusal."""
    name = os.path.basename(rel)
    if name.startswith(".") or name == "__init__.py":
        # `__init__.py` is a namespace; forty of them bury the real files.
        return False
    said = _language(root, rel)
    if said not in SOURCE and said != SCRIPT:
        return False
    try:
        return os.path.getsize(os.path.join(root, rel)) >= MIN_BYTES
    except OSError:
        return False


# Cached briefly: unlike other discovery this walks the whole repository, and
# the payload is rebuilt on every change.
CACHE_SECONDS = 30
_cache = {}


def units(root):
    """Every source file in this repository, as something a walkthrough can
    cover. Files, not functions: what is offered is listable without reading;
    `resolve` carries a function name."""
    root = os.path.abspath(root)
    hit = _cache.get(root)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    found = _scan(root)
    _cache[root] = (time.time(), found)
    return found


def _scan(root):
    out = []
    for here, dirs, files in os.walk(root):
        # The fence prunes before anything is listed (`fenced.NEVER`).
        dirs[:] = sorted(d for d in dirs
                         if not d.startswith(".") and d not in IGNORE
                         and not fenced.in_fence(d))
        rel_dir = os.path.relpath(here, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        for name in sorted(files):
            rel = os.path.join(rel_dir, name) if rel_dir else name
            if fenced.in_fence(rel) or not _walkable(root, rel):
                continue
            out.append({"name": rel, "label": rel, "short": name,
                        "dir": rel_dir or ".", "kind": "file",
                        "path": rel, "symbol": ""})
            if len(out) >= MAX_UNITS:
                return out
    return out


def kind(root):
    """`files`, or nothing at all to walk through."""
    return "files" if units(root) else ""


def _has_definition(root, rel, symbol):
    """Does this file define something by that name? Asked before a symbol is
    carried into a label or prompt, so the tutor never hunts missing code."""
    pattern = DEFINITION.get(_language(root, rel))
    if not pattern:
        return False
    rx = re.compile(pattern % re.escape(symbol), re.MULTILINE)
    try:
        with open(os.path.join(root, rel), "r", encoding="utf-8",
                  errors="replace") as fh:
            return bool(rx.search(fh.read()))
    except OSError:
        return False


def _candidates(name):
    """Every file path a typed or tapped name could mean, most specific first:
    a dotted name's last part is read both as a module and as a name inside
    the module before it."""
    raw = str(name or "").strip().strip("/")
    if not raw:
        return []
    out = []

    # `path/to/file.py::grade`: a resolved scope's spelling.
    if "::" in raw:
        path, _, symbol = raw.partition("::")
        return [(path.strip(), symbol.strip())]

    out.append((raw, ""))
    if os.path.splitext(raw)[1] in SOURCE:
        # Already a filename: its dot is an extension.
        return out

    parts = raw.split(".")
    if len(parts) > 1:
        stem = "/".join(parts)
        for ext in SOURCE:
            out.append((stem + ext, ""))
        if len(parts) > 2:
            # The last component as a name inside the module before it.
            head, symbol = "/".join(parts[:-1]), parts[-1]
            for ext in SOURCE:
                out.append((head + ext, symbol))
    return out


# The Atlas root is the fallback, so the tutor can trace any path in Atlas.
# A unit under `board/` or `vendor/` is `readonly`: the board is edited only
# in a worktree, and vendor trees are pulled at a commit.
READ_ONLY = ("board", "vendor")

# Top-level directories of the Atlas root a name is never resolved into: the
# owner's private configuration repository and the Mac-only sessions.
PRIVATE = ("ai-config", "sessions")


def readonly(rel):
    """Is this Atlas-relative path under `board/` or `vendor/`?"""
    head = str(rel or "").replace("\\", "/").strip("/").split("/", 1)[0]
    # Lower-cased: on a case-insensitive disk `Board/x.py` is `board/x.py`.
    return head.lower() in READ_ONLY


def _atlas_rel(base, root, rel):
    """`rel` under `root`, spelt relative to the Atlas root `base`, or ""."""
    full = os.path.realpath(os.path.join(root, rel))
    try:
        out = os.path.relpath(full, base)
    except ValueError:
        return ""
    if out == os.pardir or out.startswith(os.pardir + os.sep):
        return ""
    return out.replace(os.sep, "/")


def _in_atlas(base, path):
    """The Atlas-relative file a typed path names, or "", checked the way the
    listing checks: no absolute path, `..`, hidden, ignored, fenced or private
    component, the real file inside the root, and `_walkable`. `vendor` is
    allowed only at the top of Atlas.
    """
    raw = str(path or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or ":" in raw:
        return ""
    parts = raw.split("/")
    if any(not x or x in (".", "..") or x.startswith(".") for x in parts):
        return ""
    low = [x.lower() for x in parts]
    if fenced.in_fence(raw) or low[0] in PRIVATE:
        return ""
    rest = low[1:] if low[0] == "vendor" else low
    if any(x in IGNORE for x in rest[:-1]):
        return ""
    rel = "/".join(parts)
    if _atlas_rel(base, base, rel) != rel:
        # A symlink out of the root, or to another name inside it, is refused.
        return ""
    full = os.path.join(base, rel)
    if not os.path.isfile(full) or not _walkable(base, rel):
        return ""
    return rel


def _unit(root, rel, base):
    """One resolved unit at `rel` under `root`, before its symbol is set."""
    return {"name": rel, "label": rel, "short": os.path.basename(rel),
            "dir": os.path.dirname(rel) or ".", "kind": "file",
            "path": rel, "symbol": "", "root": root,
            "readonly": readonly(_atlas_rel(base, root, rel))}


def resolve(root, wanted, base=None):
    """Match names from a request against this subject's source, then Atlas's.

    Returns (chosen, unknown); an unmatched name is reported, never dropped.
    A name is a repository-relative path, an unambiguous bare filename
    (subject-local only), or a dotted module path with an optional symbol,
    kept only when the file defines it. Names not in `root` are tried under
    `base` (default `subjects.root()`). Every unit carries `root` and
    `readonly`. A fenced component is refused everywhere.
    """
    root = os.path.realpath(root)
    base = os.path.realpath(base or subjects.root())
    every = units(root)
    by_path = {u["path"].lower(): u for u in every}
    by_base = {}
    for u in every:
        # An ambiguous bare filename resolves to nothing.
        by_base.setdefault(u["short"].lower(), []).append(u)

    chosen, unknown, seen = [], [], set()
    for name in wanted or []:
        found = None
        maybe = _candidates(name)
        if any(fenced.in_fence(path) for path, _ in maybe):
            # A typed path through the fence is refused outright, whatever
            # other reading of it exists.
            unknown.append(name)
            continue
        for path, symbol in maybe:
            key = path.lower()
            u = by_path.get(key)
            if u is None:
                hits = by_base.get(key) or []
                u = hits[0] if len(hits) == 1 else None
            if u is None:
                continue
            if symbol and not _has_definition(root, u["path"], symbol):
                # The file is real, the symbol is not: try the next reading.
                continue
            found = dict(_unit(root, u["path"], base), symbol=symbol)
            break
        if not found:
            # Not this subject's: the same readings under Atlas.
            for path, symbol in maybe:
                rel = _in_atlas(base, path)
                if not rel:
                    continue
                if symbol and not _has_definition(base, rel, symbol):
                    continue
                found = dict(_unit(base, rel, base), symbol=symbol)
                break
        if not found:
            unknown.append(name)
            continue
        if (found["root"], found["path"], found["symbol"]) in seen:
            continue
        seen.add((found["root"], found["path"], found["symbol"]))
        found["name"] = label(found)
        found["label"] = found["name"]
        found["short"] = found["symbol"] or found["short"]
        chosen.append(found)

    # The subject's own first, in listing order; then Atlas's, by path.
    order = {u["path"]: i for i, u in enumerate(every)}
    chosen.sort(key=lambda u: (u["root"] != root,
                               order.get(u["path"], 0) if u["root"] == root
                               else 0, u["path"], u["symbol"]))
    return chosen, unknown


def label(u):
    """What one resolved unit is called: `psych_asr/evaluate/grade.py::grade`,
    the file and, where there is one, the thing inside it."""
    return u["path"] + ("::" + u["symbol"] if u.get("symbol") else "")


def parts(root):
    """A project's top-level pieces, `[{name, label, short, kind: "part"}]`:
    its directories, else its top-level source files. Capped at `MAX_PARTS`."""
    out = []
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return out
    for name in names:
        if name.startswith(".") or name in PART_IGNORE:
            continue
        if os.path.isdir(os.path.join(root, name)):
            out.append({"name": name, "label": name + "/", "short": name,
                        "kind": "part"})
    if out:
        return out[:MAX_PARTS]
    for name in names:
        if name.startswith(".") or name in PART_IGNORE:
            continue
        path = os.path.join(root, name)
        if os.path.isfile(path) and not name.endswith((".md", ".txt", ".json",
                                                       ".lock", ".log")):
            out.append({"name": name, "label": name, "short": name,
                        "kind": "part"})
    return out[:MAX_PARTS]
