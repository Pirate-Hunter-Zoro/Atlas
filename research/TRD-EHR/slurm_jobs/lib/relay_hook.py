"""relay_hook.py -- what a failed Python step says about itself, behind RELAY:.

`sitecustomize.py` beside this file installs `hook` in every Python a recipe
starts: `relay_trap.sh` puts this directory on PYTHONPATH, so no entrypoint
imports anything. On an uncaught exception, after the usual traceback, it
prints to stderr:

    RELAY: error <type> at <file>:<line> in <function>
    RELAY: step <module>, recipe <recipe>
    RELAY: raised in <library file>:<line>          (when a library raised it)
    RELAY: missing <where>                          (a file that is not there)
    RELAY: input <where> rows <n>                   (paths the failing code held)
    RELAY: shape <function>.<name> <type> (<r>, <c>) (arrays and frames it held)

Nothing on success. A relay report is public, so it never prints a value, a
row or the exception's message. A path is named by the `.env` key whose
location holds it; its basename only under a key in RELAY_OPEN_KEYS, where
the aggregate artifacts live. Everything else is `<withheld>`, with its
extension: per-patient files are named by patient id.

    RELAY_ROOT       the workspace (relay_trap.sh sets it)
    RELAY_STAGE      the recipe (relay_trap.sh sets it)
    RELAY_PATH_KEYS  the environment variables that name data locations
    RELAY_OPEN_KEYS  those of them whose files may be named
    RELAY_NAMES      0 names no file at all, only extensions and counts

`python -m relay_hook [--look KEY/sub/dir] [--module a.b]` is the diagnostic
probe a diagnostic recipe runs: the same naming rules, and exit 0.

Standard library only. The twin copies in each workspace's
`slurm_jobs/lib/` are byte-identical (`board/test/relayhook.py`).
"""

import os
import re
import sys

MAX_LINE = 190
MAX_SHAPES = 6
MAX_INPUTS = 6
MAX_FRAMES = 3
COUNT_BYTES = 256 * 1024 * 1024
MAX_PROBE = 30

_IDLIKE = re.compile(r"\d{6,}|^[0-9a-fA-F-]{8,}$")
_FENCED = ("phi", "data")


def _env_words(name):
    return [w for w in os.environ.get(name, "").split() if w]


def _root():
    # Real paths throughout, so a symlink on the way to the data or the
    # workspace cannot hide a path from its key.
    return os.path.realpath(os.environ.get("RELAY_ROOT") or os.getcwd())


def _under(path, top):
    return path == top or path.startswith(top.rstrip(os.sep) + os.sep)


def _ext(path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    # Written without its dot: `.rttm`-shaped text is what the PHI policy
    # refuses, and an extension alone names nothing.
    return " ext " + ext if ext else ""


def _idlike(rel):
    for seg in rel.split(os.sep):
        stem = os.path.splitext(seg)[0]
        if _IDLIKE.search(stem):
            return True
    return False


def classify(path):
    """`(key, its location)` for the longest location in RELAY_PATH_KEYS that
    holds `path`, or `("", "")`."""
    best, where = "", ""
    for key in _env_words("RELAY_PATH_KEYS"):
        value = os.environ.get(key, "")
        if not value:
            continue
        loc = os.path.realpath(value)
        if _under(path, loc) and len(loc) > len(where):
            best, where = key, loc
    return best, where


def describe(path):
    """`path` as a report may say it: `KEY/rest`, `KEY/<withheld> ext x`, a
    workspace-relative path, or `<outside the workspace>`. Never a location."""
    try:
        p = os.path.realpath(os.fspath(path))
    except (TypeError, ValueError):
        return "<unnamed>"
    names = os.environ.get("RELAY_NAMES", "1") != "0"
    key, loc = classify(p)
    if key:
        rest = os.path.relpath(p, loc)
        if rest == ".":
            return key
        if names and key in _env_words("RELAY_OPEN_KEYS") and not _idlike(rest):
            return "%s/%s" % (key, rest)
        return "%s/<withheld>%s" % (key, _ext(p))
    root = _root()
    if _under(p, root):
        rel = os.path.relpath(p, root)
        if (names and not _idlike(rel)
                and not any(s in _FENCED for s in rel.split(os.sep))):
            return rel
        return "workspace/<withheld>%s" % _ext(p)
    return "<outside the workspace>%s" % _ext(p)


def _nameable(path):
    """May this file be opened to count it? Only where its name may be said:
    under an open key, or in the workspace outside its data. A location a
    key names itself, a person-level CSV, is never opened."""
    if os.environ.get("RELAY_NAMES", "1") == "0":
        return False
    p = os.path.realpath(path)
    key, loc = classify(p)
    if key:
        return (key in _env_words("RELAY_OPEN_KEYS")
                and not _idlike(os.path.relpath(p, loc)))
    root = _root()
    rel = os.path.relpath(p, root)
    return (_under(p, root) and not _idlike(rel)
            and not any(s in _FENCED for s in rel.split(os.sep)))


def _count(path):
    """` rows <n>`, ` entries <n>` or ` bytes <n>`, or "" where it may not be
    read. Counts only, never content."""
    try:
        if os.path.isdir(path):
            if not _nameable(path):
                return ""
            return " entries %d" % len(os.listdir(path))
        size = os.path.getsize(path)
    except OSError:
        return ""
    if not _nameable(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv", ".jsonl", ".txt") and size <= COUNT_BYTES:
        try:
            with open(path, "rb") as fh:
                n = sum(1 for _ in fh)
        except OSError:
            return ""
        return " rows %d" % (n - 1 if ext in (".csv", ".tsv") and n else n)
    return " bytes %d" % size


def _type_name(etype):
    mod = getattr(etype, "__module__", "") or ""
    name = getattr(etype, "__qualname__", None) or getattr(etype, "__name__", "?")
    return name if mod in ("builtins", "__main__", "") else "%s.%s" % (mod, name)


def _library_path(filename):
    """A library file by its path inside its package: `pandas/io/common.py`."""
    for mark in ("site-packages", "dist-packages"):
        cut = filename.rfind(os.sep + mark + os.sep)
        if cut >= 0:
            return filename[cut + len(mark) + 2:]
    m = re.search(r"[\\/]lib[\\/]python[\d.]+[\\/](.*)$", filename)
    return m.group(1) if m else os.path.basename(filename)


def _stage():
    main = sys.modules.get("__main__")
    spec = getattr(main, "__spec__", None)
    if spec is not None and getattr(spec, "name", ""):
        return spec.name
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 in ("", "-c", "-"):
        return "python %s" % (argv0 or "-")
    p = os.path.realpath(argv0)
    root = _root()
    return os.path.relpath(p, root) if _under(p, root) else os.path.basename(p)


def _frames(tb):
    out = []
    while tb is not None:
        out.append((tb.tb_frame, tb.tb_lineno))
        tb = tb.tb_next
    return out


def _code_file(frame):
    """Is this frame's code a file? `<frozen runpy>` and `<string>` are not,
    and made absolute they would read as files in the working directory."""
    name = frame.f_code.co_filename or ""
    return bool(name) and not name.startswith("<")


def _pathish(value):
    if isinstance(value, str):
        if not value or len(value) > 1024 or "\n" in value or "\0" in value:
            return None
        return value
    if hasattr(value, "__fspath__"):
        try:
            got = os.fspath(value)
        except (TypeError, ValueError):
            return None
        return got if isinstance(got, str) else None
    return None


def _shape(value):
    try:
        shape = getattr(value, "shape", None)
    except Exception:                                         # noqa: BLE001
        return None
    if isinstance(shape, tuple) and all(isinstance(n, int) for n in shape):
        return tuple(shape)
    return None


def lines(etype, value, tb):
    """The RELAY lines for one uncaught exception, prefix not included."""
    root = _root()
    frames = _frames(tb)
    mine = [(f, n) for f, n in frames if _code_file(f)
            and _under(os.path.realpath(f.f_code.co_filename), root)]
    out = []
    if mine:
        f, n = mine[-1]
        rel = os.path.relpath(os.path.realpath(f.f_code.co_filename), root)
        out.append("error %s at %s:%d in %s"
                   % (_type_name(etype), rel, n, f.f_code.co_name))
    else:
        out.append("error %s, raised outside the workspace" % _type_name(etype))
    recipe = os.environ.get("RELAY_STAGE", "")
    out.append("step %s%s" % (_stage(), ", recipe " + recipe if recipe else ""))
    if frames and _code_file(frames[-1][0]) and (
            not mine or frames[-1][0] is not mine[-1][0]):
        f, n = frames[-1]
        out.append("raised in %s:%d"
                   % (_library_path(os.path.realpath(f.f_code.co_filename)), n))
    if isinstance(value, OSError):
        word = "missing" if isinstance(value, FileNotFoundError) else "path"
        for name in (getattr(value, "filename", None),
                     getattr(value, "filename2", None)):
            p = _pathish(name)
            if p:
                out.append("%s %s" % (word, describe(p)))
    seen, inputs, shapes = set(), [], []
    for f, _ in reversed(mine[-MAX_FRAMES:]):
        try:
            names = sorted(f.f_locals.items(), key=lambda kv: str(kv[0]))
        except Exception:                                     # noqa: BLE001
            continue
        for name, val in names:
            if str(name).startswith("__"):
                continue
            if isinstance(val, type):
                continue
            shape = _shape(val)
            if shape is not None and len(shapes) < MAX_SHAPES:
                shapes.append("shape %s.%s %s %s" % (
                    f.f_code.co_name, name, type(val).__name__, shape))
                continue
            p = _pathish(val)
            if p is None or len(inputs) >= MAX_INPUTS:
                continue
            full = os.path.realpath(p)
            if full in seen or full == root or not os.path.exists(full):
                continue
            seen.add(full)
            inputs.append("input %s%s" % (describe(full), _count(full)))
    return out + inputs + shapes


def say(line, stream=None):
    stream = stream or sys.stderr
    stream.write("RELAY: %s\n" % line[:MAX_LINE])


def hook(etype, value, tb, prior=None):
    (prior or sys.__excepthook__)(etype, value, tb)
    try:
        for line in lines(etype, value, tb):
            say(line)
        sys.stderr.flush()
    except Exception:                                         # noqa: BLE001
        pass


def install():
    """Install the hook once, in front of whatever excepthook was there."""
    if getattr(sys.excepthook, "_relay", False):
        return
    prior = sys.excepthook

    def relay_excepthook(etype, value, tb):
        hook(etype, value, tb, prior)
    relay_excepthook._relay = True
    sys.excepthook = relay_excepthook


# ---------------------------------------------------------------------------
# the probe a diagnostic recipe runs
# ---------------------------------------------------------------------------
def _sha():
    import subprocess
    try:
        p = subprocess.run(["git", "-C", _root(), "rev-parse", "--short",
                            "HEAD"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True,
                           timeout=20)
        return p.stdout.strip() or "unknown"
    except Exception:                                         # noqa: BLE001
        return "unknown"


def _listing(top, depth, budget):
    """`KEY/sub rows n` lines for a nameable directory, `depth` levels."""
    out = []
    try:
        names = sorted(os.listdir(top))
    except OSError:
        return out
    for name in names:
        if len(out) >= budget:
            out.append("... %d more under %s" % (len(names) - len(out),
                                                  describe(top)))
            break
        full = os.path.join(top, name)
        if name.startswith("."):
            continue
        out.append("has %s%s" % (describe(full), _count(full)))
        if depth > 1 and os.path.isdir(full) and _nameable(full):
            out.extend(_listing(full, depth - 1, max(0, budget - len(out))))
    return out[:budget + 1]


def probe(look="", module=""):
    """The diagnostic's RELAY lines: the checkout, which data locations are
    set and exist, a listing of the nameable ones, and whether `module`
    imports. Reads names and counts only."""
    out = ["probe checkout %s, recipe %s"
           % (_sha(), os.environ.get("RELAY_STAGE", "") or "none")]
    unset = []
    for key in _env_words("RELAY_PATH_KEYS"):
        value = os.environ.get(key, "")
        if not value:
            unset.append(key)
            continue
        kind = ("dir" if os.path.isdir(value) else "file"
                if os.path.isfile(value) else "missing")
        out.append("env %s %s" % (key, kind))
    if unset:
        out.append("env unset: %s" % " ".join(unset))
    if module:
        import importlib.util
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        out.append("module %s %s" % (module, "found" if found else "missing"))
    tops = []
    if look:
        key, _, sub = look.partition("/")
        if ".." in sub.split("/") or sub.startswith("/"):
            out.append("look refused: a path under %s, not out of it" % key)
        elif key in _env_words("RELAY_OPEN_KEYS") and os.environ.get(key):
            tops.append((os.path.join(os.environ[key], sub), 3))
        else:
            out.append("look %s refused: only %s are listed" % (
                key, ", ".join(_env_words("RELAY_OPEN_KEYS")) or "none"))
    else:
        tops = [(os.environ[k], 2) for k in _env_words("RELAY_OPEN_KEYS")
                if os.environ.get(k)]
    for top, depth in tops:
        if not os.path.isdir(top):
            out.append("look %s missing" % describe(top))
            continue
        out.extend(_listing(top, depth, MAX_PROBE - len(out)))
    for line in out[:MAX_PROBE + 5]:
        say(line, sys.stdout)
    return 0


def main(argv):
    look, module, i = "", "", 0
    while i < len(argv):
        if argv[i] == "--look" and i + 1 < len(argv):
            look = argv[i + 1]
            i += 2
        elif argv[i] == "--module" and i + 1 < len(argv):
            module = argv[i + 1]
            i += 2
        else:
            i += 1
    return probe(look, module)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
