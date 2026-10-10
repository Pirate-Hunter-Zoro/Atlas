"""relay_hook.py -- what a failed Python step says about itself, behind RELAY:.

`sitecustomize.py` beside this file installs `hook` in every Python a recipe
starts: the relay's wrapper (`jobs.wrapper`) and `relay_trap.sh` put this
directory, board/cluster/lib, on PYTHONPATH, so no entrypoint imports
anything. On an uncaught exception, after the usual traceback, it prints to
stderr:

    RELAY: error <type> at <file>:<line> in <function>
    RELAY: step <module>, recipe <recipe>
    RELAY: raised in <library file>:<line>          (when a library raised it)
    RELAY: missing <where>                          (a file that is not there)
    RELAY: input <where> rows <n>                   (paths the failing code held)
    RELAY: shape <function>.<name> <type> (<r>, <c>) (arrays and frames it held)

Nothing on success. A relay report is public, so it never prints a value, a
row or the exception's message.

A PATH IS PRINTED ONE SEGMENT AT A TIME, AND A SEGMENT ONLY FROM AN ALLOWLIST.
The location is its `.env` key. Under an open key, a file or directory name
is printed only if it is in the allowlist; from the first name that is not,
the rest is one placeholder, `<dir>` or `<file>` with its extension when the
extension is a known one (`<file 2 deep>` for two). No heuristic decides what
looks like an id: per-patient trees name files and directories by patient id
in every shape there is, so only a name the repository itself publishes is
ever said. The allowlist is built here, from tracked files only:

    relay/requests/*     every segment of each request's `produces` and
                         `export` paths
    *.sbatch             every segment of each `results/...` path a recipe
                         names
    encoders, allow      the config's names the files above do not carry

THE CONFIG is the subject's tutorboard.json `relay.fingerprint` (`config`):
the RELAY_CONFIG JSON the wrapper exports, else the file under RELAY_ROOT.

    path_keys   the environment variables that name data locations
    open_keys   those of them whose allowlisted names may be printed
    names       false names nothing at all, only keys, extensions and counts
    encoders    directory names the pipeline derives (TRD-EHR: EMBEDDERS in
                scripts/pipeline/predictions/plot_cross_embedder.py)
    allow       other fixed directory names the code writes by name

Inside the subject a path git tracks is code, and printed as it is. Code
frames are reported only for tracked files.

    RELAY_ROOT       the subject (the wrapper or relay_trap.sh sets it)
    RELAY_STAGE      the recipe (likewise)
    RELAY_CONFIG     the config, as JSON (the wrapper)

`python -m relay_hook [--look KEY/sub/dir] [--module a.b]` is the diagnostic
probe a diagnostic recipe runs: the same rules, and exit 0. It lists only
allowlisted children; the rest of a directory is counts by extension.

Standard library only; it runs on the cluster's python3, which may be 3.7.
"""

import json
import os
import re
import sys

MAX_LINE = 190
MAX_SHAPES = 6
MAX_INPUTS = 6
MAX_FRAMES = 3
COUNT_BYTES = 256 * 1024 * 1024
MAX_PROBE = 30
# Entries looked at when counting inside a directory whose name is withheld.
COUNT_ENTRIES = 200000

# The extensions a placeholder may carry. An extension is part of a name, so it
# is printed from a list too: `x.ID0001XQ` has no extension worth saying.
EXTENSIONS = frozenset((
    "csv tsv json jsonl txt parquet feather pkl pickle joblib npy npz db "
    "sqlite png pdf svg html md log out err yaml yml toml pt bin safetensors "
    "h5 gz zip tar wav rttm py sh sbatch").split())

_SEGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")
_RESULTS_PATH = re.compile(
    r"(?<![A-Za-z0-9_.$-])results(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)+")
_PYTHON_M = re.compile(r"\bpython[0-9.]*\s+-m\s+([A-Za-z_][A-Za-z0-9_.]*)")
_CACHE = {}


def config():
    """The subject's `relay.fingerprint`, a dict. RELAY_CONFIG where it is set,
    else tutorboard.json under RELAY_ROOT; {} where neither has one. A config
    that is there but cannot be read names nothing (`names` false)."""
    raw = os.environ.get("RELAY_CONFIG")
    key = ("config", raw, _root())
    if key not in _CACHE:
        if raw:
            try:
                got = json.loads(raw)
            except ValueError:
                got = None
        else:
            doc = _read_json(os.path.join(_root(), "tutorboard.json"))
            relay = doc.get("relay") if isinstance(doc, dict) else None
            got = (relay.get("fingerprint", {}) if isinstance(relay, dict)
                   else {})
        _CACHE[key] = got if isinstance(got, dict) else {"names": False}
    return _CACHE[key]


def _words(name):
    """A config list, as words. A string is split on whitespace."""
    value = config().get(name)
    if isinstance(value, str):
        value = value.split()
    if not isinstance(value, list):
        return []
    return [w for w in value if isinstance(w, str) and w]


def _names_on():
    return config().get("names", True) is not False


def _root():
    # Real paths throughout, so a symlink on the way to the data or the
    # workspace cannot hide a path from its key.
    return os.path.realpath(os.environ.get("RELAY_ROOT") or os.getcwd())


def _under(path, top):
    return path == top or path.startswith(top.rstrip(os.sep) + os.sep)


# ---------------------------------------------------------------------------
# the allowlist, from tracked files
# ---------------------------------------------------------------------------
def _git(root, argv):
    import subprocess
    try:
        p = subprocess.run(["git", "-C", root] + argv, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30)
    except Exception:                                         # noqa: BLE001
        return None
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else None


def tracked(root=None):
    """`(files, dirs)`: the workspace-relative paths git tracks under the
    workspace, and every directory holding one. Empty outside a checkout."""
    root = root or _root()
    key = ("tracked", root)
    if key not in _CACHE:
        files, dirs = set(), set()
        out = _git(root, ["ls-files", "-z"])
        for rel in (out or "").split("\0"):
            if not rel:
                continue
            files.add(rel)
            parts = rel.split("/")
            for i in range(1, len(parts)):
                dirs.add("/".join(parts[:i]))
        _CACHE[key] = (files, dirs)
    return _CACHE[key]


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _strings(value):
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def _segments_of(path):
    parts = [s for s in path.replace("\\", "/").split("/") if s]
    if ".." in parts:
        return []
    return [s for s in parts if s != "." and _SEGMENT.match(s)]


def published_paths(root=None):
    """Every path the tracked sources publish: request produces and exports,
    and the `results/` paths recipes name."""
    root = root or _root()
    files, _ = tracked(root)
    paths = []
    for rel in sorted(files):
        if rel.startswith("relay/requests/") and rel.endswith(".json"):
            req = _read_json(os.path.join(root, rel))
            if isinstance(req, dict):
                paths += _strings(req.get("produces"))
                paths += _strings(req.get("export"))
        elif rel.endswith(".sbatch"):
            try:
                with open(os.path.join(root, rel), "r", encoding="utf-8",
                          errors="replace") as fh:
                    paths += _RESULTS_PATH.findall(fh.read())
            except OSError:
                pass
    return paths


def allowlist():
    """The path segments a report may print. Empty where `names` is false."""
    root = _root()
    key = ("allow", root, os.environ.get("RELAY_CONFIG"))
    if key not in _CACHE:
        words = set()
        if _names_on():
            words.update(_words("encoders"))
            words.update(_words("allow"))
            for p in published_paths(root):
                words.update(_segments_of(p))
        _CACHE[key] = frozenset(w for w in words if _SEGMENT.match(w)
                                and w not in (".", ".."))
    return _CACHE[key]


def recipe_modules(root=None):
    """The modules a tracked recipe runs with `python -m`."""
    root = root or _root()
    files, _ = tracked(root)
    out = set()
    for rel in files:
        if not rel.endswith(".sbatch"):
            continue
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8",
                      errors="replace") as fh:
                out.update(_PYTHON_M.findall(fh.read()))
        except OSError:
            pass
    out.discard("relay_hook")
    return out


# ---------------------------------------------------------------------------
# naming a path
# ---------------------------------------------------------------------------
def _ext_word(name):
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    return ext if ext in EXTENSIONS else ""


def _ext(path):
    # Written without its dot: `.rttm`-shaped text is what the PHI policy
    # refuses, and an extension alone names nothing.
    ext = _ext_word(os.path.basename(path))
    return " ext " + ext if ext else ""


def classify(path):
    """`(key, its location)` for the longest location in `path_keys` that
    holds `path`, or `("", "")`."""
    best, where = "", ""
    for key in _words("path_keys"):
        value = os.environ.get(key, "")
        if not value:
            continue
        loc = os.path.realpath(value)
        if _under(path, loc) and len(loc) > len(where):
            best, where = key, loc
    return best, where


def _parts(rel):
    return [s for s in rel.split(os.sep) if s and s != "."]


def _render(parts, full, prefix_ok):
    """`parts` joined, as far as `prefix_ok(i)` allows each; from the first
    segment it does not, one placeholder: `<file>` (with its extension) or
    `<dir>`, and `<file N deep>` where it stands for N segments. Nothing
    follows a placeholder, so `/<...>` never reads as a path to the scrub."""
    cut = next((i for i in range(len(parts)) if not prefix_ok(i)), None)
    if cut is None:
        return "/".join(parts)
    kind = "dir" if os.path.isdir(full) else "file"
    deep = len(parts) - cut
    hidden = "<%s>" % kind if deep == 1 else "<%s %d deep>" % (kind, deep)
    said = "/".join(parts[:cut] + [hidden])
    return said + _ext(full) if kind == "file" else said


def _open_ok(key, parts):
    """May each of `parts`, under `key`, be printed?"""
    allow = allowlist() if key in _words("open_keys") else ()
    return lambda i: parts[i] in allow


def _workspace_ok(parts):
    """A segment in the workspace: tracked, or in the allowlist."""
    if not _names_on():
        return lambda i: False
    files, dirs = tracked()
    allow = allowlist()

    def ok(i):
        prefix = "/".join(parts[:i + 1])
        return prefix in files or prefix in dirs or parts[i] in allow
    return ok


def describe(path):
    """`path` as a report may say it: `KEY/rest`, a workspace-relative path,
    or `<outside the workspace>`, every segment allowlisted or a placeholder.
    Never a location."""
    try:
        p = os.path.realpath(os.fspath(path))
    except (TypeError, ValueError):
        return "<unnamed>"
    key, loc = classify(p)
    if key:
        parts = _parts(os.path.relpath(p, loc))
        if not parts:
            return key
        return "%s/%s" % (key, _render(parts, p, _open_ok(key, parts)))
    root = _root()
    if _under(p, root):
        parts = _parts(os.path.relpath(p, root))
        if not parts:
            return "workspace"
        return _render(parts, p, _workspace_ok(parts))
    return "<outside the workspace>%s" % _ext(p)


def _nameable(path):
    """May this file be opened to count it, or this directory listed? Only
    where every segment of it may be said: under an open key, or in the
    workspace. A location a key names itself, a person-level CSV, is never
    opened."""
    if not _names_on():
        return False
    p = os.path.realpath(path)
    key, loc = classify(p)
    if key:
        if key not in _words("open_keys"):
            return False
        parts = _parts(os.path.relpath(p, loc))
        ok = _open_ok(key, parts)
        return all(ok(i) for i in range(len(parts)))
    root = _root()
    if not _under(p, root):
        return False
    parts = _parts(os.path.relpath(p, root))
    ok = _workspace_ok(parts)
    return all(ok(i) for i in range(len(parts)))


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


# ---------------------------------------------------------------------------
# the hook
# ---------------------------------------------------------------------------
def _type_name(etype):
    mod = getattr(etype, "__module__", "") or ""
    name = getattr(etype, "__qualname__", None) or getattr(etype, "__name__", "?")
    return name if mod in ("builtins", "__main__", "") else "%s.%s" % (mod, name)


def _library_path(filename):
    """A library file by its path inside its package, `pandas/io/common.py`,
    or "" where it is not in a library."""
    for mark in ("site-packages", "dist-packages"):
        cut = filename.rfind(os.sep + mark + os.sep)
        if cut >= 0:
            return filename[cut + len(mark) + 2:]
    m = re.search(r"[\\/]lib[\\/]python[\d.]+[\\/](.*)$", filename)
    return m.group(1) if m else ""


def _tracked_rel(filename):
    """A code file's workspace-relative path where git tracks it, or ""."""
    root = _root()
    p = os.path.realpath(filename)
    if not _under(p, root):
        return ""
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    return rel if rel in tracked(root)[0] else ""


def _stage():
    main = sys.modules.get("__main__")
    spec = getattr(main, "__spec__", None)
    if spec is not None and getattr(spec, "name", ""):
        return spec.name
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 in ("", "-c", "-"):
        return "python %s" % (argv0 or "-")
    return _tracked_rel(argv0) or describe(argv0)


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
            and _tracked_rel(f.f_code.co_filename)]
    out = []
    if mine:
        f, n = mine[-1]
        out.append("error %s at %s:%d in %s"
                   % (_type_name(etype), _tracked_rel(f.f_code.co_filename),
                      n, f.f_code.co_name))
    else:
        out.append("error %s, raised outside the workspace" % _type_name(etype))
    recipe = os.environ.get("RELAY_STAGE", "")
    out.append("step %s%s" % (_stage(), ", recipe " + recipe if recipe else ""))
    if frames and _code_file(frames[-1][0]) and (
            not mine or frames[-1][0] is not mine[-1][0]):
        f, n = frames[-1]
        lib = _library_path(os.path.realpath(f.f_code.co_filename))
        if lib:
            out.append("raised in %s:%d" % (lib, n))
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
            try:
                full = os.path.realpath(p)
            except (ValueError, UnicodeError, OSError):
                continue
            if full in seen or full == root or not os.path.exists(full):
                continue
            seen.add(full)
            inputs.append("input %s%s" % (describe(full), _count(full)))
    return out + inputs + shapes


def say(line, stream=None):
    stream = stream or sys.stderr
    stream.write("RELAY: %s\n" % line[:MAX_LINE])


class _Disarmed(object):
    """Stderr for the prior excepthook. The traceback it prints carries the
    exception's own message, and the relay publishes every log line that
    starts with `RELAY:`, so a message holding a newline and that word would
    publish itself. Such a line gets a leading space, which the relay skips."""

    def __init__(self, stream):
        self._stream, self._fresh = stream, True

    def write(self, text):
        out = []
        for piece in str(text).splitlines(True):
            if self._fresh and piece.lstrip().startswith("RELAY:"):
                piece = " " + piece
            out.append(piece)
            self._fresh = piece.endswith(("\n", "\r"))
        return self._stream.write("".join(out))

    def flush(self):
        return self._stream.flush()

    def __getattr__(self, name):
        return getattr(self._stream, name)


def hook(etype, value, tb, prior=None):
    real = sys.stderr
    sys.stderr = _Disarmed(real)
    try:
        (prior or sys.__excepthook__)(etype, value, tb)
    finally:
        sys.stderr = real
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
    out = _git(_root(), ["rev-parse", "--short", "HEAD"])
    return (out or "").strip() or "unknown"


def _wrapped(head, words):
    """`head word word ...`, as many lines as MAX_LINE needs."""
    out, line = [], head
    for w in words:
        if len(line) + 1 + len(w) > MAX_LINE:
            out.append(line)
            line = head
        line += " " + w
    if line != head:
        out.append(line)
    return out


def _ext_counts(counter):
    return ", ".join("%s %d" % (k or "other", counter[k])
                     for k in sorted(counter))


def _withheld(top, hidden):
    """The children of `top` whose names are withheld, as counts: files by
    extension, and directories by what they hold, one level in."""
    where = describe(top)
    files, inner = {}, {}
    ndirs = inner_dirs = scanned = 0
    for name in hidden:
        full = os.path.join(top, name)
        if not os.path.isdir(full):
            k = _ext_word(name)
            files[k] = files.get(k, 0) + 1
            continue
        ndirs += 1
        try:
            with os.scandir(full) as it:
                for e in it:
                    scanned += 1
                    if scanned > COUNT_ENTRIES:
                        break
                    if e.name.startswith("."):
                        continue
                    if e.is_dir():
                        inner_dirs += 1
                    else:
                        k = _ext_word(e.name)
                        inner[k] = inner.get(k, 0) + 1
        except OSError:
            continue
    out = []
    if files:
        out.append("has %s/<file> x%d: %s"
                   % (where, sum(files.values()), _ext_counts(files)))
    if ndirs:
        out.append("has %s/<dir> x%d: files %d%s, dirs %d%s"
                   % (where, ndirs, sum(inner.values()),
                      " (%s)" % _ext_counts(inner) if inner else "",
                      inner_dirs,
                      ", counted %d" % COUNT_ENTRIES
                      if scanned > COUNT_ENTRIES else ""))
    return out


def _listing(top, depth, budget):
    """`KEY/sub rows n` lines for a nameable directory, `depth` levels: its
    allowlisted children by name, the rest as counts."""
    out = []
    if budget <= 0 or not _nameable(top):
        return out
    try:
        names = sorted(n for n in os.listdir(top) if not n.startswith("."))
    except OSError:
        return out
    allow = allowlist()
    shown = [n for n in names if n in allow]
    hidden = [n for n in names if n not in allow]
    for i, name in enumerate(shown):
        if len(out) >= budget:
            out.append("... %d more named under %s" % (len(shown) - i,
                                                       describe(top)))
            break
        full = os.path.join(top, name)
        said = describe(full)
        out.append("has %s%s" % (said, _count(full)))
        # A child that is another key's location is listed under that key.
        if depth > 1 and os.path.isdir(full) and "/" in said:
            out.extend(_listing(full, depth - 1, budget - len(out)))
    if hidden:
        out.extend(_withheld(top, hidden))
    return out


def _look(look):
    """`(directory, problem)`: where LOOK points, or why it is refused. The
    value is never echoed: only its key and allowlisted segments."""
    open_keys = _words("open_keys")
    parts = [s for s in (look or "").strip().split("/") if s not in ("", ".")]
    key = parts[0] if parts else ""
    sub = parts[1:]
    if key not in open_keys or not os.environ.get(key):
        return "", "look refused: only %s are listed" % (
            ", ".join(open_keys) or "none")
    if ".." in sub:
        return "", "look refused: a path under %s, not out of it" % key
    allow = allowlist()
    cut = next((i for i, s in enumerate(sub) if s not in allow), None)
    if cut is not None:
        deep = len(sub) - cut
        return "", "look refused: %s names a directory that is not a " \
            "published output" % "/".join([key] + sub[:cut] + [
                "<dir>" if deep == 1 else "<dir %d deep>" % deep])
    top = os.path.join(os.environ[key], *sub)
    if not os.path.isdir(top):
        return "", "look %s missing" % describe(top)
    if not _nameable(top):
        return "", "look refused: %s is not under %s" % (describe(top), key)
    return top, ""


def probe(look="", module=""):
    """The diagnostic's RELAY lines: the checkout, which data locations are
    set and exist, a listing of the open ones, and whether `module` is
    found. Reads names and counts only."""
    out = ["probe checkout %s, recipe %s"
           % (_sha(), os.environ.get("RELAY_STAGE", "") or "none")]
    kinds = {"dir": [], "file": [], "missing": [], "unset": []}
    for key in _words("path_keys"):
        value = os.environ.get(key, "")
        kinds["unset" if not value else "dir" if os.path.isdir(value)
              else "file" if os.path.isfile(value) else "missing"].append(key)
    for kind in ("dir", "file", "missing", "unset"):
        out += _wrapped("env %s:" % kind, kinds[kind])
    if module:
        if module not in recipe_modules():
            out.append("module refused: not one a tracked recipe runs")
        else:
            import importlib.util
            try:
                found = importlib.util.find_spec(module) is not None
            except (ImportError, ValueError):
                found = False
            out.append("module %s %s" % (module,
                                         "found" if found else "missing"))
    tops = []
    if look:
        top, problem = _look(look)
        if problem:
            out.append(problem)
        else:
            tops.append((top, 3))
    else:
        for k in _words("open_keys"):
            value = os.environ.get(k)
            if not value:
                continue
            if not os.path.isdir(value):
                out.append("look %s missing" % k)
                continue
            tops.append((value, 2))
    for top, depth in tops:
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
